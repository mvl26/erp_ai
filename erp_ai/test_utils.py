import json
import os
import shutil
import tempfile
from unittest.mock import patch

import frappe
from frappe.permissions import AUTOMATIC_ROLES
from helpdesk.test_utils import create_agent

from erp_ai.agent.run_log import write_entry
from erp_ai.constants import AGENT_STATUS_EVENT, AGENT_USER, HELPDESK_AGENT_ROLE, ROLE_AGENT, SETTING_DOCTYPE
from erp_ai.gateway import GatewayError, ModelResult


def make_model_result(**kw) -> ModelResult:
	fields = {
		"content": [],
		"text": "",
		"stop_reason": "end_turn",
		"model": "fake-model",
		"usage": {
			"input_tokens": 0,
			"output_tokens": 0,
			"cache_creation_input_tokens": 0,
			"cache_read_input_tokens": 0,
		},
		"cost_usd": 0.0,
		"credential_label": "fake",
		"keys_tried": [],
		"latency_ms": 0,
		"request_id": "req_fake",
	}
	fields.update(kw)
	return ModelResult(**fields)


class FakeGateway:
	"""Thay `erp_ai.gateway.call_model`: trả lần lượt các kết quả đã xếp, ném nếu là GatewayError.

	`on_call(task, kwargs)` chạy trước khi trả kết quả (ghi thứ tự lời gọi, đẩy đồng hồ giả).
	"""

	def __init__(self, *results, on_call=None):
		self.results = list(results)
		self.on_call = on_call
		self.calls = []

	@property
	def call_count(self) -> int:
		return len(self.calls)

	def __call__(self, task, **kwargs):
		self.calls.append({"task": task, **kwargs})
		if self.on_call is not None:
			self.on_call(task, kwargs)
		result = self.results.pop(0) if self.results else make_model_result()
		if isinstance(result, GatewayError):
			raise result
		return result


def record_status_signals(testcase) -> list[dict]:
	"""Patch `frappe.realtime.emit_via_redis`; return the list that collects `{"event", "message", "room"}` of every agent status signal.

	Other events are dropped, so nothing reaches Redis. The patch is removed by `addCleanup`.
	"""
	signals = []

	def record(event, message, room=None):
		if event == AGENT_STATUS_EVENT:
			signals.append({"event": event, "message": message, "room": room})

	emit_patch = patch("frappe.realtime.emit_via_redis", side_effect=record)
	emit_patch.start()
	testcase.addCleanup(emit_patch.stop)
	return signals


def set_agent_settings(**fields) -> None:
	"""Set ERP AI Setting values directly in the DB (no validate), for tests."""
	for fieldname, value in fields.items():
		frappe.db.set_single_value(SETTING_DOCTYPE, fieldname, value)


def add_credential(label, **fields) -> str:
	"""Append a key row to ERP AI Setting without validation and return the child row name."""
	settings = frappe.get_single(SETTING_DOCTYPE)
	settings.append("credentials", {"label": label, "api_key": f"sk-{label}", **fields})
	settings.flags.ignore_validate = True
	settings.save(ignore_permissions=True)
	return settings.credentials[-1].name


class _FakeRawResponse:
	def __init__(self, message, headers, request_id):
		self._message = message
		self.headers = headers
		self.request_id = request_id

	def parse(self):
		return _FakeMessage(self._message, self.request_id)


class _FakeMessage:
	def __init__(self, message, request_id):
		self._message = message
		self._request_id = request_id

	def model_dump(self) -> dict:
		return dict(self._message)


class _FakeRawMessages:
	def __init__(self, owner):
		self._owner = owner

	def create(self, **request):
		self._owner.requests.append(request)
		if self._owner.error is not None:
			raise self._owner.error
		return _FakeRawResponse(self._owner.message, self._owner.headers, self._owner.request_id)


class _FakeMessages:
	def __init__(self, owner):
		self.with_raw_response = _FakeRawMessages(owner)


class FakeAnthropicClient:
	"""Thay `anthropic.Anthropic` trong test: không mạng, ghi lại mọi `messages.create(**request)`."""

	def __init__(self, message=None, headers=None, request_id="req_fake", error=None):
		self.message = message if message is not None else {"type": "message", "content": []}
		self.headers = headers or {}
		self.request_id = request_id
		self.error = error
		self.requests = []
		self.messages = _FakeMessages(self)


def fake_anthropic_client(**kwargs) -> FakeAnthropicClient:
	return FakeAnthropicClient(**kwargs)


def make_log_entry(**fields) -> str:
	"""Write an ERP AI Log row through `run_log.write_entry` (current session user must be allowed) and return its name."""
	values = {"run_id": "ERPAI-TEST-run", "entry_type": "skip", "trigger": "ticket_insert", "turn": 0}
	values.update(fields)
	return write_entry(**values)


PREFIX = "ERPAI-TEST-"
PINNED_AGENT_ROLES = (ROLE_AGENT, HELPDESK_AGENT_ROLE)
SLA_RESPONSE_HOURS_BY_PRIORITY = {"Low": 4, "Medium": 3, "High": 2, "Urgent": 1}
WEEKDAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")


def _agent_role_rows() -> list[dict]:
	return frappe.get_all(
		"Has Role",
		filters={"parent": AGENT_USER, "parenttype": "User"},
		fields=["*"],
		order_by="creation, name",
	)


def pin_agent_roles(testcase) -> None:
	"""Pin the agent account's Has Role set to exactly {ERP AI Agent, Agent} (plus automatic roles) for one test.

	`addCleanup` puts back the exact rows that were there. Call it
	after `testcase.addCleanup(frappe.db.rollback)` so the restore runs first (cleanups run last-in first-out).
	"""
	rows = _agent_role_rows()
	if not frappe.db.exists("User", AGENT_USER):
		raise AssertionError(f"{AGENT_USER} does not exist on this site")

	def restore():
		frappe.db.delete("Has Role", {"parent": AGENT_USER, "parenttype": "User"})
		for row in rows:
			frappe.get_doc({**row, "doctype": "Has Role"}).db_insert()

	# Registered before `restore` so it runs after it, and still runs when `restore` fails.
	testcase.addCleanup(frappe.clear_cache, user=AGENT_USER)
	testcase.addCleanup(restore)

	keep = set(PINNED_AGENT_ROLES) | set(AUTOMATIC_ROLES)
	frappe.db.delete("Has Role", {"parent": AGENT_USER, "parenttype": "User", "role": ("not in", list(keep))})
	present = {row["role"] for row in rows}
	for role in PINNED_AGENT_ROLES:
		if role not in present:
			frappe.get_doc(
				{
					"doctype": "Has Role",
					"parent": AGENT_USER,
					"parenttype": "User",
					"parentfield": "roles",
					"role": role,
				}
			).db_insert()
	frappe.clear_cache(user=AGENT_USER)


def make_routing_rules(**overrides) -> str:
	"""JSON of `routing_rules` in the design 3.3 shape, with no people filled in; `overrides` replace top-level keys."""
	rules = {
		"assignees": {cat: {"default": "", "prefixes": {}} for cat in "ABCF"},
		"departments": {},
		"importance_priority": {"1": "", "2": "High", "3": "High"},
		"expected_sla": {
			"A": {"response_min": 15, "resolution_min": 480},
			"B": {"response_min": 15, "resolution_min": 240},
			"C": {"response_min": 60, "resolution_min": 1440},
			"D": {"response_min": 60, "resolution_min": None},
			"E": {"response_min": 60, "resolution_min": None},
			"F": {"response_min": 5, "resolution_min": 60},
		},
	}
	rules.update(overrides)
	return json.dumps(rules, ensure_ascii=False)


def _unique(label: str) -> str:
	return f"{PREFIX}{label}-{frappe.generate_hash(length=8)}"


def make_sla(testcase, *, condition: str = "", default: bool = False, enabled: bool = True) -> str:
	"""Insert a self-made HD Service Level Agreement (own holiday list) and return its name. Rolled back by the test."""
	holiday_list = frappe.get_doc(
		{
			"doctype": "HD Service Holiday List",
			"holiday_list_name": _unique("Holidays"),
			"from_date": "2020-01-01",
			"to_date": "2099-12-31",
		}
	).insert(ignore_permissions=True)
	sla = frappe.get_doc(
		{
			"doctype": "HD Service Level Agreement",
			"service_level": _unique("SLA"),
			"holiday_list": holiday_list.name,
			"condition": condition,
			"default_sla": 1 if default else 0,
			"enabled": 1 if enabled else 0,
			"apply_sla_for_resolution": 1,
			"support_and_resolution": [
				{"workday": day, "start_time": "00:00:00", "end_time": "23:59:00"} for day in WEEKDAYS
			],
			"priorities": [
				{
					"priority": priority,
					"default_priority": 1 if priority == "Medium" else 0,
					"response_time": 3600 * hours,
					"resolution_time": 4 * 3600 * hours,
				}
				for priority, hours in SLA_RESPONSE_HOURS_BY_PRIORITY.items()
			],
		}
	)
	sla.insert(ignore_permissions=True)
	return sla.name


def make_active_agent(testcase) -> str:
	"""Create a user with the Agent role and an active HD Agent row; return the user ID. Rolled back by the test."""
	email = f"{_unique('agent').lower()}@example.com"
	create_agent(email)
	return email


def make_team(testcase, *, with_rule: bool = False, rule_users: tuple[str, ...] = ()) -> str:
	"""Insert a self-made HD Team and return its name.

	Helpdesk always creates an Assignment Rule for a new team; `with_rule=False` removes it again, so the team
	has none. `rule_users` are the members (and rule users); empty means one fresh active agent.
	"""
	members = tuple(rule_users) or (make_active_agent(testcase),)
	team = frappe.get_doc(
		{"doctype": "HD Team", "team_name": _unique("Team"), "users": [{"user": user} for user in members]}
	).insert(ignore_permissions=True)
	if not with_rule:
		rule = team.assignment_rule
		frappe.db.set_value("HD Team", team.name, "assignment_rule", None, update_modified=False)
		frappe.delete_doc("Assignment Rule", rule, force=True, ignore_permissions=True)
	return team.name


SOURCE_ROOT_PATH = "erp_ai.agent.tools.source.get_source_root"


class TempAppsRoot:
	"""A temporary `apps/` root that `source.get_source_root` returns for one test; the real `apps/` is never touched.

	Layout under `base` (a fresh `tempfile.mkdtemp()`, removed by `addCleanup`):
	`apps/<app>/ok.py`, `.env`, `x.pem`, `site_config.json` for every app in `apps`; in the first app
	`link_out.py` (symlink to `outside/plain.py`) and `dir_out` (symlink to `outside/`); `outside/plain.py`
	and `sites/site_config.json` sit next to `apps/`, outside the root.
	"""

	def __init__(self, testcase, apps=("myapp",)):
		self.base = os.path.realpath(tempfile.mkdtemp())
		testcase.addCleanup(shutil.rmtree, self.base, True)
		self.root = os.path.join(self.base, "apps")
		self.outside = os.path.join(self.base, "outside")
		os.makedirs(self.root)
		self.write("plain.py", "x = 1\n", root=self.outside)
		self.write("site_config.json", "{}\n", root=os.path.join(self.base, "sites"))
		for app in apps:
			for name in ("ok.py", ".env", "x.pem", "site_config.json"):
				self.write(os.path.join(app, name), "x = 1\n")
		if apps:
			os.symlink(
				os.path.join(self.outside, "plain.py"), os.path.join(self.root, apps[0], "link_out.py")
			)
			os.symlink(self.outside, os.path.join(self.root, apps[0], "dir_out"))
		patcher = patch(SOURCE_ROOT_PATH, return_value=self.root)
		patcher.start()
		testcase.addCleanup(patcher.stop)

	def write(self, rel, text, root=None) -> str:
		"""Write `text` to `rel` under `root` (default: the temp `apps/`), creating parents; return the full path."""
		path = os.path.join(root or self.root, rel)
		os.makedirs(os.path.dirname(path), exist_ok=True)
		with open(path, "w", encoding="utf-8") as handle:
			handle.write(text)
		return path
