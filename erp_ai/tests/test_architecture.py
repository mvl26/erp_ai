"""Architecture tests (ADR-001..005, NFR-1, NFR-5, D-23): static scans of the source tree.

Nothing here imports product code or touches the database: files are read as text and parsed with `ast`.

Scanned files ("product code"): every `.py` file under `erp_ai/` except `test_*.py` (this also drops
`test_utils.py`), anything under a `tests/` directory and `__pycache__`. `eval/` is product code (it is an
entry layer, ADR-001), so it is scanned. The legacy-comment rule also scans `.json`, `.js` and `.html`
files of the same tree. `docs/` lives outside `erp_ai/` and is never scanned.

Every rule is a pure function over `{relative path: source}`, so the second class below can feed it
synthetic violating code (must be caught) and clean code (must not be flagged).
"""

import ast
import json
import re
import shlex
import sys
import unittest
from pathlib import Path
from typing import ClassVar

from erp_ai.constants import AGENT_STATUS_EVENT, PANEL_METHODS

PACKAGE_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = PACKAGE_ROOT.parent
CI_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "ci.yml"
PACKAGE = "erp_ai"

CLIENT_FILE = "gateway/client.py"
CREDENTIALS_FILE = "gateway/credentials.py"
QUEUE_FILE = "agent/queue.py"
POLICY_FILE = "agent/policy.py"
SOURCE_TOOL_FILE = "agent/tools/source.py"
PROCESS_RUNNER_FILE = "agent/changes/process_runner.py"
PROCESS_RUNNER_WRAPPER = "_run_wrapped"  # its callers pass cwd=/env= through to subprocess.run
# ADR-013, ADR-022, D-12: the only files that start processes.
SUBPROCESS_FILES = (SOURCE_TOOL_FILE, PROCESS_RUNNER_FILE)
READ_TOOL_FILE = "agent/tools/read.py"
HANDLERS_FILE = "handlers.py"
TOOLS_PREFIX = "agent/tools/"

# ADR-001 (layers), ADR-003 (handlers), ADR-005 (tools): (scope module, forbidden modules, reason).
LAYER_RULES = (
	(
		"erp_ai.gateway",
		(
			"erp_ai.agent",
			"erp_ai.eval",
			"erp_ai.handlers",
			"erp_ai.ticket_panel",
			"erp_ai.tasks",
			"erp_ai.install",
			"erp_ai.erp_ai_agent",
		),
		"ADR-001: gateway must not import agent, eval, handlers, ticket_panel, scheduler, install or doctype controllers",
	),
	(
		"erp_ai.agent",
		(
			"erp_ai.eval",
			"erp_ai.handlers",
			"erp_ai.ticket_panel",
			"erp_ai.tasks",
			"erp_ai.install",
			"erp_ai.erp_ai_agent",
		),
		"ADR-001: agent core must not import eval, handlers, ticket_panel, scheduler, install or doctype controllers",
	),
	(
		"erp_ai.agent.tools",
		("erp_ai.gateway", "erp_ai.agent.runner", "erp_ai.agent.queue", "erp_ai.agent.changes"),
		"ADR-001/ADR-005/ADR-011: tools never call the model, run the agent, enqueue jobs or reach the change job/state machine",
	),
	(
		"erp_ai.agent.changes",
		(
			"erp_ai.gateway",
			"erp_ai.agent.runner",
			"erp_ai.agent.run_status",
			"erp_ai.eval",
			"erp_ai.handlers",
			"erp_ai.tasks",
			"erp_ai.install",
			"erp_ai.erp_ai_agent",
		),
		"ADR-012/ADR-013: the change job and state machine never call the model, run the agent or import entry layers and doctype controllers",
	),
	(
		"erp_ai.handlers",
		("erp_ai.gateway", "erp_ai.agent.runner"),
		"ADR-001/ADR-003: handlers enqueue by path string, never import gateway or runner",
	),
	(
		"erp_ai.ticket_panel",
		("erp_ai.gateway", "erp_ai.agent.runner", "erp_ai.agent.queue"),
		"ADR-001/ADR-010: the panel is an entry layer, it never calls the model, runs the agent or enqueues",
	),
)
# NOT forbidden on purpose: erp_ai.eval -> erp_ai.agent.runner (entry layer -> agent core, ADR-001).

ENQUEUE_NAMES = ("enqueue", "enqueue_doc")
ENQUEUE_REQUIRED_KEYWORDS = ("queue", "timeout", "enqueue_after_commit", "job_id", "deduplicate")
ENQUEUE_TARGETS = ("erp_ai.agent.runner.run_for_ticket", "erp_ai.agent.changes.apply_job.run_change")

CONFIG_DOCTYPES = ("ERP AI Setting", "ERP AI Credential")
CONFIG_DOCTYPE_CONSTANTS = ("SETTING_DOCTYPE", "CREDENTIAL_DOCTYPE")
CONFIG_CONTROLLER_FILES = (
	"erp_ai_agent/doctype/erp_ai_setting/erp_ai_setting.py",
	"erp_ai_agent/doctype/erp_ai_credential/erp_ai_credential.py",
)
CONFIG_VARIABLE_NAMES = ("settings", "setting", "credential", "credentials")
DOC_GETTERS = ("get_doc", "get_single", "get_cached_doc", "new_doc")

TOOL_FORBIDDEN_CALL_SUFFIXES = ("db.set_value", "set_user", "db.multisql", "db_update")
SQL_READ_ONLY = re.compile(r"^\s*(select|show|describe)\b", re.IGNORECASE)

# ADR-001: product code imports only the standard library, frappe, helpdesk and itself; `anthropic` (declared
# in pyproject.toml `dependencies`) only in gateway/client.py (NFR-5). Anything else, any other app, is a violation.
ALLOWED_TOP_LEVEL_MODULES = frozenset({PACKAGE, "frappe", "helpdesk", *sys.stdlib_module_names})
ANTHROPIC_MODULE = "anthropic"

POLICY_FIELDS = (
	"permission_level",
	"excluded_teams",
	"ai_opt_out",
	"auto_assign_enabled",
	"code_change_enabled",
	"code_change_apps",
)

SECRET_READERS = ("get_decrypted_password", "get_password")
SECRET_NAMES = ("api_key", "apikey", "secret", "password", "token")
LOG_SINK_CALLS = ("print", "frappe.log_error", "frappe.msgprint", "frappe.throw")
LOG_SINK_METHODS = ("debug", "info", "warning", "error", "exception", "critical")

STATUS_SCRIPT_FILE = "public/js/agent_status_indicator.js"
CONSTANTS_FILE = "constants.py"
# Design 3.7: Helpdesk loads the page script through `new Function`, so none of these may appear in it.
STATUS_SCRIPT_FORBIDDEN = (
	r"innerHTML",
	r"outerHTML",
	r"insertAdjacentHTML",
	r"document\.write",
	r"eval\(",
	r"new Function",
	r"doc_unsubscribe",
	r"localStorage",
	r"sessionStorage",
	r"document\.cookie",
	r"fetch\(",
	r"XMLHttpRequest",
	r"frappe\.call",
	r"updateField",
	r"open_doc:",
	r"600",
	r"HD Form Script",
	r"^\s*(import|export)\b",
	# ADR-009: the panel script must not parse markup, poll, unbind listeners or create navigable elements.
	r"DOMParser",
	r"createContextualFragment",
	r"setInterval",
	r"MutationObserver",
	r"\.off\(",
	r"removeListener",
	r"removeAllListeners",
	r'createElement\("a"',
	r'createElement\("img"',
	r'createElement\("iframe"',
	r'createElement\("script"',
	r"\.src =",
	r"\.href =",
	r"innerText =",
)
# Regexes: the socket guard keeps setupForm (run many times) from registering listeners twice; the
# `state.ticket = null` leave-page step keeps a left ticket's signals from showing (ADR-008 decision 6).
STATUS_SCRIPT_REQUIRED = (
	r"textContent",
	r"doc_subscribe",
	r'"connect"',
	r"setTimeout",
	r"try \{",
	r"catch \(",
	r"expires_in_s",
	r"if \(state\.socket !== socket\)",
	r"state\.ticket = null",
	r"if \(state\.ticket\)",
	# T12: message thread, labels, B-8 guidance, close button, indicator moved into the panel and back.
	r"threadEl",
	r"renderMessages",
	r'TEXT_EMPTY_THREAD = "Chưa có tin nào\."',
	r'TEXT_BOT_LABEL = "Bot"',
	r'TEXT_CLOSE = "Đóng"',
	r"Bot có thể không trả lời khi đang tắt, đang ở chế độ chỉ ghi nhận, "
	r"phiếu không dùng AI hoặc thuộc nhóm loại trừ, hoặc đã hết lượt hôm nay\.",
	r'TEXT_LOAD_FAILED = "Không tải được dữ liệu của khu vực\. Hãy đóng rồi mở lại\."',
	r"\(docked \? state\.panel\.slotEl : document\.body\)\.appendChild\(el\)",
	# T12: stale-result guard (design F1 reload).
	r"seq !== panel\.seq \|\| ticket !== state\.ticket \|\| !panel\.open",
	# T12 use sites (the pins above match declarations; these match where each is used).
	r"renderMessages\(data\)",
	r"if \(isStale\(\)\) \{\s*return;",
	r"dockIndicator\(true\)",
	r"dockIndicator\(false\)",
	r"textContent = TEXT_BOT_GUIDANCE",
	r"textContent = TEXT_EMPTY_THREAD",
	r"textContent = TEXT_CLOSE",
	r"\? TEXT_BOT_LABEL :",
	# A failed reload clears both lists (no new AI fields beside an old thread); reset tolerates an old panel state.
	r"panel\.threadEl\.replaceChildren\(\);\s*panel\.errorEl\.textContent = TEXT_LOAD_FAILED",
	r"panel\.threadEl\?\.replaceChildren\(\)",
	# T13 send box: fixed texts, then the use sites (declaration-only pins were rejected in review).
	r'TEXT_SEND_FAILED = "Không gửi được tin\. Chữ bạn gõ vẫn còn, hãy thử lại\."',
	r'TEXT_EMPTY_MESSAGE = "Hãy nhập nội dung trước khi gửi\."',
	r'TEXT_TOO_LONG = "Tin dài quá 2000 ký tự\."',
	r'TEXT_SENDING = "Đang gửi…"',
	r"MAX_MESSAGE_CHARS = 2000",
	r'event\.key === "Enter" && !event\.shiftKey && !event\.isComposing',
	r'sendEl\.addEventListener\("click"',
	r"const value = panel\.inputEl\.value\.trim\(\)",
	r"if \(!value\) \{\s*panel\.errorEl\.textContent = TEXT_EMPTY_MESSAGE;\s*return;",
	r"value\.length > MAX_MESSAGE_CHARS\) \{\s*panel\.errorEl\.textContent = TEXT_TOO_LONG;\s*return;",
	r"if \(panel\.sending \|\| !panel\.open",
	r"panel\.sending = true",
	r"panel\.sending = false",
	r'state\s*\.call\("erp_ai\.ticket_panel\.send_message", \{ ticket, text: value \}\)',
	r'panel\.inputEl\.value = "";\s*panel\.errorEl\.textContent = "";\s*reload\(\)',
	# Failure only shows the fixed text: nothing else (such as clearing the box) happens in that branch.
	r"if \(!isStale\(\)\) \{\s*panel\.errorEl\.textContent = TEXT_SEND_FAILED;\s*\}",
	r"sendEl\.textContent = TEXT_SENDING",
	r"sendEl\.textContent = TEXT_SEND\b",
	r"inputEl\.placeholder = TEXT_INPUT_PLACEHOLDER",
	# T13 r1: fixed values of the remaining texts, and the box is locked while a send is pending.
	r'TEXT_SEND = "Gửi";',
	r'TEXT_INPUT_PLACEHOLDER =\s*"Nhập câu hỏi cho bot\. Enter để gửi, Shift\+Enter để xuống dòng\."',
	r"panel\.sendEl\.disabled = true;\s*panel\.sendEl\.textContent = TEXT_SENDING",
	r"panel\.inputEl\.disabled = true",
	# T13 r1: each wiring point pinned at its use site (a declaration or a copy elsewhere must not satisfy it).
	r"const isStale = \(\) => ticket !== state\.ticket;",
	r"unlock = \(\) => \{\s*panel\.sending = false;\s*panel\.inputEl\.disabled = false;\s*panel\.sendEl\.disabled = false;\s*panel\.sendEl\.textContent = TEXT_SEND;\s*\}",
	r'unlock\(\);\s*if \(isStale\(\)\) \{\s*return;\s*\}\s*panel\.inputEl\.value = ""',
	r"onSendFailed = \(\) => \{\s*try \{\s*unlock\(\);\s*if \(!isStale\(\)\)",
	r"\.then\(onSent, onSendFailed\)",
	r"catch \(e\) \{\s*onSendFailed\(\);",
	r"isComposing\) \{\s*event\.preventDefault\(\);\s*submit\(\);",
	r'addEventListener\("click", \(\) => \{\s*try \{\s*submit\(\);',
	r"formEl,\s*slotEl",
	# T14 live updates (design F3): both listeners are named handlers registered once per socket, in the guard block.
	r'state\.socket = socket;\s*socket\.on\(EVENT, onStatus\);\s*socket\.on\("docinfo_update", onDocinfo\);\s*socket\.on\("doc_update", onDocUpdate\);',
	r"docinfo_update",
	r"doc_update",
	# Payload keys: frappe comment.py:59-67 (key, doc.reference_doctype/name) and document.py:1370-1385 (doctype, name).
	r'const onDocinfo = \(msg\) => \{\s*try \{\s*if \(\s*msg\?\.key === "comments" &&\s*msg\.doc\?\.reference_doctype === "HD Ticket" &&\s*String\(msg\.doc\.reference_name\) === state\.ticket\s*\) \{\s*reload\(\);',
	r'const onDocUpdate = \(msg\) => \{\s*try \{\s*if \(msg\?\.doctype === "HD Ticket" && String\(msg\.name\) === state\.ticket\) \{\s*reload\(\);',
	# Reconnect: re-join the room, then refill an open panel.
	r'socket\.emit\("doc_subscribe", "HD Ticket", state\.ticket\);\s*\}\s*if \(state\.panel\.open\) \{\s*reload\(\);',
	# Reset (ticket change or leaving the page): cancel pending loads, close the panel (returns the indicator), clear texts and the input.
	r"const panel = state\.panel;\s*panel\.seq\+\+;\s*closePanel\(\);",
	r'if \(panel\.inputEl\) \{\s*panel\.inputEl\.value = "";\s*\}',
	r"String\(doc\.name\) !== state\.ticket\) \{\s*reset\(\);\s*state\.ticket = String\(doc\.name\)",
	r"reset\(\);\s*state\.ticket = null",
	# Narrow screen: one resize listener for the page lifetime, closing the panel under the width limit.
	r"const onResize = \(\) => \{\s*try \{\s*if \(window\.innerWidth < NARROW_SCREEN_PX\) \{\s*closePanel\(\);",
	r'if \(!state\.resizeBound\) \{\s*state\.resizeBound = true;\s*window\.addEventListener\("resize", onResize\);',
	r"if \(window\.innerWidth < NARROW_SCREEN_PX\) \{\s*return \{ actions: \[\] \};",
)

# ADR-009: every `call(` in the page script passes a string literal naming one of PANEL_METHODS.
STATUS_SCRIPT_CALL = re.compile(r"\bcall\(\s*(\"([^\"]*)\")?")


def check_status_script_calls(script: str, allowed_methods) -> list:
	"""Violations: a `call(` whose first argument is not a literal in `allowed_methods`."""
	violations = []
	for match in STATUS_SCRIPT_CALL.finditer(script):
		line = script.count("\n", 0, match.start()) + 1
		if match.group(1) is None:
			violations.append(f"line {line}: first argument of call( is not a string literal")
		elif match.group(2) not in allowed_methods:
			violations.append(f"line {line}: {match.group(2)} is not in PANEL_METHODS")
	return violations


# ADR-008 (status signals) and ADR-007 (the one form script): who may publish, import, write or delete.
RUN_STATUS_FILE = "agent/run_status.py"
RUN_STATUS_MODULE = "erp_ai.agent.run_status"
RUNNER_FILE = "agent/runner.py"
INSTALL_FILE = "install.py"
HOOKS_FILE = "hooks.py"
REALTIME_NAMES = ("publish_realtime", "publish_progress", "emit_via_redis")
REALTIME_MODULE = "frappe.realtime"
# Attribute/function names that write a record, the cache, a file or the transaction (NFR-6, ADR-008 decision 5).
RUN_STATUS_WRITE_NAMES = (
	"insert",
	"save",
	"delete",
	"delete_doc",
	"set_value",
	"db_set",
	"sql",
	"multisql",
	"commit",
	"rollback",
	"write",
	"write_text",
	"write_bytes",
	"open",
	"touch",
	"mkdir",
)
RUN_STATUS_FORBIDDEN_ATTRIBUTES = ("frappe.db", "frappe.cache")
OPEN_DOC_ROOM_PREFIX = "open_doc:"
ALL_ROOM = "all"
FORM_SCRIPT_DOCTYPE_NAME = "HD Form Script"
AGENT_STATUS_SCRIPT_NAME = "ERP AI Agent Status"
# ADR-007: Helpdesk's SPA ignores these hooks; the one channel is the form script record (install.py).
PAGE_INJECTION_HOOKS = (
	"app_include_js",
	"web_include_js",
	"app_include_css",
	"web_include_css",
	"after_request",
	"website_route_rules",
	"fixtures",
)
UNINSTALL_HOOK = "erp_ai.install.before_uninstall"
UNINSTALL_FUNCTION = "before_uninstall"
DELETE_NAMES = ("delete", "delete_doc", "delete_doc_if_exists")
SQL_DELETE = re.compile(r"^\s*delete\b", re.IGNORECASE)

LEGACY_NAMES = ("HD Ticket Comment", "commented_by", "comment_email", "comment_by")
# Design 3.5 (amendment 1c) tells `get_record` to DROP comment_email/comment_by from a Comment; this one
# hide-list constant is the only place these names may appear.
LEGACY_ALLOWED_ASSIGNMENTS = {READ_TOOL_FILE: "COMMENT_HIDDEN_FIELDS"}

SUBPROCESS_RUN_FUNCTIONS = ("run", "call", "check_call", "check_output")
OS_SHELL_FUNCTIONS = ("system", "popen", "posix_spawn", "posix_spawnp")
OS_SHELL_PREFIXES = ("exec", "spawn")  # os.execv*, os.execl*, os.spawnv*, os.spawnl*

CI_BENCH_BRANCH = "version-15"
CI_REQUIRED_APPS = (
	# (app, branch required on `bench get-app`, or None when the default branch is accepted)
	("telephony", None),
	("helpdesk", "v15.1.0"),
	("erpnext", "version-15"),
)

# frappe/test_runner.py:160 skips any file with this name when running `run-tests --app`
FRAPPE_SKIPPED_TEST_FILENAMES = ("test_runner.py",)


# ---------------------------------------------------------------------------------------------------
# Scanning helpers
# ---------------------------------------------------------------------------------------------------


def is_product_file(rel: Path, suffixes=(".py",)) -> bool:
	if rel.suffix not in suffixes:
		return False
	if "__pycache__" in rel.parts or "node_modules" in rel.parts:
		return False
	if "tests" in rel.parts[:-1]:
		return False
	return not rel.name.startswith("test_")


def load_product_sources(root: Path = PACKAGE_ROOT, suffixes=(".py",)) -> dict:
	"""`{posix path relative to erp_ai/: source text}` for every product file."""
	sources = {}
	for path in sorted(root.rglob("*")):
		rel = path.relative_to(root)
		if path.is_file() and is_product_file(rel, suffixes):
			sources[rel.as_posix()] = path.read_text(encoding="utf-8")
	return sources


def only_python(sources: dict) -> dict:
	return {rel: src for rel, src in sources.items() if rel.endswith(".py")}


def scoped(sources: dict, prefix: str) -> dict:
	return {rel: src for rel, src in sources.items() if rel.startswith(prefix)}


def module_name(rel: str) -> str:
	parts = list(Path(rel).with_suffix("").parts)
	if parts and parts[-1] == "__init__":
		parts.pop()
	return ".".join([PACKAGE, *parts])


def module_in(module: str, prefix: str) -> bool:
	return module == prefix or module.startswith(prefix + ".")


def imported_modules(tree: ast.AST, module: str, is_package: bool) -> list:
	"""`[(lineno, dotted module)]`; `from a import b` yields both `a` and `a.b` (b may be a submodule)."""
	found = []
	for node in ast.walk(tree):
		if isinstance(node, ast.Import):
			found.extend((node.lineno, alias.name) for alias in node.names)
		elif isinstance(node, ast.ImportFrom):
			base = node.module or ""
			if node.level:
				package = module.split(".") if is_package else module.split(".")[:-1]
				package = package[: len(package) - (node.level - 1)]
				base = ".".join([*package, base] if base else package)
			found.append((node.lineno, base))
			found.extend((node.lineno, f"{base}.{alias.name}") for alias in node.names)
	return found


def dotted_name(node):
	"""`frappe.db.sql` -> "frappe.db.sql"; `frappe.logger(x).warning` -> "frappe.logger().warning"."""
	if isinstance(node, ast.Name):
		return node.id
	if isinstance(node, ast.Attribute):
		base = dotted_name(node.value)
		return f"{base}.{node.attr}" if base else None
	if isinstance(node, ast.Call):
		base = dotted_name(node.func)
		return f"{base}()" if base else None
	return None


def import_aliases(tree: ast.AST) -> dict:
	"""`{local name: real dotted name}` for imports: `import subprocess as sp` -> {"sp": "subprocess"};
	`from subprocess import run as r` -> {"r": "subprocess.run"}."""
	aliases = {}
	for node in ast.walk(tree):
		if isinstance(node, ast.Import):
			for alias in node.names:
				if alias.asname:
					aliases[alias.asname] = alias.name
		elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
			for alias in node.names:
				aliases[alias.asname or alias.name] = f"{node.module}.{alias.name}"
	return aliases


def resolved_name(node, aliases: dict) -> str:
	"""dotted_name with its first segment replaced by the real module it was imported as."""
	name = dotted_name(node) or ""
	head, dot, rest = name.partition(".")
	return aliases[head] + dot + rest if head in aliases else name


def referenced_name(node):
	"""The bare name of a Name/Attribute node (`frappe.enqueue` -> "enqueue"), else None."""
	if isinstance(node, ast.Name):
		return node.id
	if isinstance(node, ast.Attribute):
		return node.attr
	return None


def constant_strings(tree: ast.AST):
	for node in ast.walk(tree):
		if isinstance(node, ast.Constant) and isinstance(node.value, str):
			yield node


def parse(rel: str, source: str) -> ast.AST:
	return ast.parse(source, filename=rel)


def violation(rel: str, node, message: str) -> str:
	return f"{rel}:{getattr(node, 'lineno', 0)}: {message}"


# ---------------------------------------------------------------------------------------------------
# Rules (each returns a list of "file:line: message"; empty = rule holds)
# ---------------------------------------------------------------------------------------------------


def check_layer_imports(sources: dict, rules=LAYER_RULES) -> list:
	violations = []
	for rel, source in only_python(sources).items():
		module = module_name(rel)
		imports = imported_modules(parse(rel, source), module, rel.endswith("__init__.py"))
		for scope, forbidden, reason in rules:
			if not module_in(module, scope):
				continue
			for lineno, target in imports:
				if any(module_in(target, name) for name in forbidden):
					violations.append(f"{rel}:{lineno}: imports {target} ({reason})")
	return violations


def check_import_boundaries(sources: dict) -> list:
	"""ADR-001 allowlist: stdlib, frappe, helpdesk, erp_ai; NFR-5/ADR-002: `anthropic` only in gateway/client.py."""
	violations = []
	for rel, source in only_python(sources).items():
		imports = imported_modules(parse(rel, source), module_name(rel), rel.endswith("__init__.py"))
		for lineno, target in imports:
			if module_in(target, ANTHROPIC_MODULE):
				if rel != CLIENT_FILE:
					violations.append(f"{rel}:{lineno}: imports {target} outside {CLIENT_FILE} (NFR-5)")
			elif target.split(".")[0] not in ALLOWED_TOP_LEVEL_MODULES:
				violations.append(
					f"{rel}:{lineno}: imports {target}, not stdlib/frappe/helpdesk/erp_ai (ADR-001: no other app or library)"
				)
	return violations


def check_single_enqueue_site(sources: dict) -> list:
	violations = []
	for rel, source in only_python(sources).items():
		if rel == QUEUE_FILE:
			continue
		for node in ast.walk(parse(rel, source)):
			if referenced_name(node) in ENQUEUE_NAMES:
				violations.append(violation(rel, node, f"uses {referenced_name(node)} outside {QUEUE_FILE}"))
			elif isinstance(node, ast.ImportFrom):
				for alias in node.names:
					if alias.name in ENQUEUE_NAMES:
						violations.append(violation(rel, node, f"imports {alias.name} outside {QUEUE_FILE}"))
	return violations


def check_enqueue_call_shape(sources: dict) -> list:
	"""ADR-003/ADR-013 QĐ 2: exactly two calls, one per target (runner, change job), each with all five parameters."""
	source = sources.get(QUEUE_FILE)
	if source is None:
		return [f"{QUEUE_FILE}: file missing"]
	calls = [
		node
		for node in ast.walk(parse(QUEUE_FILE, source))
		if isinstance(node, ast.Call) and referenced_name(node.func) in ENQUEUE_NAMES
	]
	if len(calls) != len(ENQUEUE_TARGETS):
		return [f"{QUEUE_FILE}: expected exactly two enqueue calls, found {len(calls)}"]
	violations = []
	targets = []
	for call in calls:
		first = call.args[0] if call.args else None
		if isinstance(first, ast.Constant) and first.value in ENQUEUE_TARGETS:
			targets.append(first.value)
		else:
			violations.append(
				violation(QUEUE_FILE, call, f"first argument must be one of the strings {ENQUEUE_TARGETS!r}")
			)
		given = {keyword.arg for keyword in call.keywords}
		for name in ENQUEUE_REQUIRED_KEYWORDS:
			if name not in given:
				violations.append(violation(QUEUE_FILE, call, f"missing keyword {name}="))
	if not violations and sorted(targets) != sorted(ENQUEUE_TARGETS):
		violations.append(
			f"{QUEUE_FILE}: expected one call to each of {ENQUEUE_TARGETS!r}, found {targets!r}"
		)
	return violations


def _is_config_doc_expr(node, config_vars: set) -> bool:
	"""True for `frappe.get_doc("ERP AI Setting")`, `get_doc({"doctype": ...})`, `get_doc(doctype=...)`,
	`frappe.get_single(SETTING_DOCTYPE)` / `constants.SETTING_DOCTYPE`, or a tracked name."""
	if isinstance(node, ast.Name):
		return node.id in config_vars
	if isinstance(node, ast.Call) and referenced_name(node.func) in DOC_GETTERS:
		first = node.args[0] if node.args else None
		if isinstance(first, ast.Dict):  # get_doc({"doctype": ...})
			first = next(
				(
					value
					for key, value in zip(first.keys, first.values, strict=True)
					if isinstance(key, ast.Constant) and key.value == "doctype"
				),
				None,
			)
		elif first is None:  # get_doc(doctype=...)
			first = next((keyword.value for keyword in node.keywords if keyword.arg == "doctype"), None)
		if isinstance(first, ast.Constant):
			return first.value in CONFIG_DOCTYPES
		return referenced_name(first) in CONFIG_DOCTYPE_CONSTANTS
	return False


def check_no_save_on_config(sources: dict) -> list:
	"""ADR-004: no `.save()` on ERP AI Setting / ERP AI Credential objects in product code."""
	violations = []
	for rel, source in only_python(sources).items():
		tree = parse(rel, source)
		config_vars = set(CONFIG_VARIABLE_NAMES)
		for node in ast.walk(tree):
			if isinstance(node, ast.Assign) and _is_config_doc_expr(node.value, set()):
				config_vars.update(t.id for t in node.targets if isinstance(t, ast.Name))
		for node in ast.walk(tree):
			if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)):
				continue
			if node.func.attr != "save":
				continue
			receiver = node.func.value
			if rel in CONFIG_CONTROLLER_FILES or _is_config_doc_expr(receiver, config_vars):
				violations.append(
					violation(rel, node, "`.save()` on an ERP AI configuration object (ADR-004)")
				)
	return violations


def check_tools_never_bypass_permissions(sources: dict) -> list:
	"""ADR-005: inside agent/tools/**, no ignore_permissions, db.set_value, writing db.sql, set_user, get_all.

	Exception (design 3.5, `denied_doctypes`): `get_all("DocType", ...)` lists the app's own DocType names,
	which is metadata, not user data.
	"""
	violations = []
	for rel, source in only_python(scoped(sources, TOOLS_PREFIX)).items():
		for node in ast.walk(parse(rel, source)):
			if referenced_name(node) == "ignore_permissions" or (
				isinstance(node, ast.Constant) and node.value == "ignore_permissions"
			):
				violations.append(violation(rel, node, "ignore_permissions in a tool"))
			elif isinstance(node, ast.keyword) and node.arg == "ignore_permissions":
				violations.append(violation(rel, node.value, "ignore_permissions= in a tool"))
			if not isinstance(node, ast.Call):
				continue
			name = dotted_name(node.func) or ""
			if name.endswith(TOOL_FORBIDDEN_CALL_SUFFIXES):
				violations.append(violation(rel, node, f"{name} in a tool"))
			elif name.endswith("db.sql"):
				first = node.args[0] if node.args else None
				read_only = (
					isinstance(first, ast.Constant)
					and isinstance(first.value, str)
					and SQL_READ_ONLY.match(first.value)
					and ";" not in first.value.strip().removesuffix(";")
				)
				if not read_only:
					violations.append(violation(rel, node, "db.sql that is not a constant SELECT in a tool"))
			elif name.endswith("get_all"):
				first = node.args[0] if node.args else None
				if not (isinstance(first, ast.Constant) and first.value == "DocType"):
					violations.append(violation(rel, node, f"{name} instead of get_list in a tool"))
	return violations


def check_subprocess_only_in_source_tool(sources: dict) -> list:
	"""ADR-005, ADR-013, ADR-022: processes start only in SUBPROCESS_FILES."""
	violations = []
	for rel, source in only_python(sources).items():
		if rel in SUBPROCESS_FILES:
			continue
		tree = parse(rel, source)
		aliases = import_aliases(tree)
		for lineno, target in imported_modules(tree, module_name(rel), False):
			if module_in(target, "subprocess"):
				violations.append(f"{rel}:{lineno}: imports {target} outside {SUBPROCESS_FILES}")
		for node in ast.walk(tree):
			if isinstance(node, ast.Call):
				name = resolved_name(node.func, aliases)
				function = name.split(".")[-1]
				if name.startswith("subprocess.") or (
					name.startswith("os.")
					and (function in OS_SHELL_FUNCTIONS or function.startswith(OS_SHELL_PREFIXES))
				):
					violations.append(violation(rel, node, f"{name} outside {SUBPROCESS_FILES}"))
	return violations


def check_subprocess_call_shape(sources: dict) -> list:
	"""ADR-005/ADR-013: every subprocess call in SUBPROCESS_FILES has timeout=, a list command, no shell;
	in process_runner.py every call also has the timeout-wrapped shape (ADR-013 QĐ 3, 7; D-3)."""
	if SOURCE_TOOL_FILE not in sources:
		return [f"{SOURCE_TOOL_FILE}: file missing"]
	violations = []
	for rel in SUBPROCESS_FILES:
		if rel in sources:
			violations.extend(subprocess_call_shape_problems(rel, sources[rel]))
	return violations


def subprocess_call_shape_problems(rel: str, source: str) -> list:
	violations = []
	tree = parse(rel, source)
	aliases = import_aliases(tree)
	for node in ast.walk(tree):
		if not isinstance(node, ast.Call):
			continue
		name = resolved_name(node.func, aliases)
		if rel == PROCESS_RUNNER_FILE and name == PROCESS_RUNNER_WRAPPER:
			keywords = {keyword.arg: keyword.value for keyword in node.keywords}
			violations.extend(
				violation(rel, node, f"{name} {problem}") for problem in cwd_env_problems(keywords, aliases)
			)
			continue
		if not name.startswith("subprocess.") or name.split(".")[-1] not in (
			*SUBPROCESS_RUN_FUNCTIONS,
			"Popen",
		):
			continue
		keywords = {keyword.arg: keyword.value for keyword in node.keywords}
		if name.split(".")[-1] not in SUBPROCESS_RUN_FUNCTIONS:
			violations.append(violation(rel, node, f"{name}: only run()-style calls with timeout"))
		if "timeout" not in keywords:
			violations.append(violation(rel, node, f"{name} without timeout="))
		shell = keywords.get("shell")
		if shell is not None and not (isinstance(shell, ast.Constant) and shell.value is False):
			violations.append(violation(rel, node, f"{name} with shell="))
		command = node.args[0] if node.args else keywords.get("args")
		if isinstance(command, ast.Constant | ast.JoinedStr):
			violations.append(violation(rel, node, f"{name} with a string command, not a list"))
		if rel == PROCESS_RUNNER_FILE or is_timeout_wrapped(command):
			violations.extend(
				violation(rel, node, f"{name} {problem}")
				for problem in timeout_wrapped_call_problems(keywords, aliases)
			)
	return violations


def is_timeout_wrapped(command) -> bool:
	"""ADR-022 QĐ 4: a `[TIMEOUT_EXECUTABLE, ...]` / `["timeout", ...]` command is a new FEAT-004 git call."""
	first = command.elts[0] if isinstance(command, ast.List) and command.elts else None
	return (isinstance(first, ast.Name) and first.id == "TIMEOUT_EXECUTABLE") or (
		isinstance(first, ast.Constant) and first.value == "timeout"
	)


def timeout_wrapped_call_problems(keywords: dict, aliases: dict) -> list:
	"""Own process group, explicit cwd= and an env= that never copies os.environ (ADR-022 QĐ 4, Ràng buộc)."""
	problems = []
	group = keywords.get("start_new_session")
	if not (isinstance(group, ast.Constant) and group.value is True):
		problems.append("without start_new_session=True")
	return problems + cwd_env_problems(keywords, aliases)


def cwd_env_problems(keywords: dict, aliases: dict) -> list:
	"""An explicit cwd= and an env= that never copies os.environ (ADR-022 QĐ 4; design 8.2)."""
	problems = []
	if "cwd" not in keywords:
		problems.append("without cwd=")
	env = keywords.get("env")
	if env is None:
		problems.append("without env=")
	elif any(resolved_name(part, aliases) == "os.environ" for part in ast.walk(env)):
		problems.append("env= uses os.environ")
	return problems


def check_policy_fields_only_in_policy(sources: dict) -> list:
	"""ADR-003/ADR-005: level and send-policy fields are read only by agent/policy.py."""
	violations = []
	for rel, source in only_python(sources).items():
		if rel == POLICY_FILE:
			continue
		tree = parse(rel, source)
		aliases = import_aliases(tree)
		for node in ast.walk(tree):
			name = referenced_name(node)
			if name in POLICY_FIELDS:
				if resolved_name(node, aliases) == f"{module_name(POLICY_FILE)}.{name}":
					continue  # `policy.auto_assign_enabled(...)` is the function of policy.py, not a field read
				violations.append(violation(rel, node, f"reads {name} outside {POLICY_FILE}"))
			elif isinstance(node, ast.Constant) and node.value in POLICY_FIELDS:
				violations.append(violation(rel, node, f"reads {node.value!r} outside {POLICY_FILE}"))
	return violations


def check_handlers_imports(sources: dict) -> list:
	"""handlers.py must not import gateway or runner (the layer rule for scope erp_ai.handlers)."""
	rules = tuple(rule for rule in LAYER_RULES if rule[0] == "erp_ai.handlers")
	return check_layer_imports({rel: src for rel, src in sources.items() if rel == HANDLERS_FILE}, rules)


def _identifiers(node) -> set:
	found = set()
	for child in ast.walk(node):
		name = referenced_name(child)
		if name:
			found.add(name)
	return found


def _has_explicit_message(call: ast.Call) -> bool:
	"""`log_error(title, message)` or `log_error(title, message=...)`; a missing, None or empty message is not."""
	message = call.args[1] if len(call.args) >= 2 else None
	if message is None:
		message = next((keyword.value for keyword in call.keywords if keyword.arg == "message"), None)
	if message is None:
		return False
	return not (isinstance(message, ast.Constant) and not message.value)


def check_secret_handling(sources: dict) -> list:
	"""NFR-5/ADR-002: password reads only in gateway/credentials.py; no key in logs; no local-var tracebacks."""
	violations = []
	for rel, source in only_python(sources).items():
		for node in ast.walk(parse(rel, source)):
			name = referenced_name(node)
			if name in SECRET_READERS and rel != CREDENTIALS_FILE:
				violations.append(violation(rel, node, f"{name} outside {CREDENTIALS_FILE}"))
			elif isinstance(node, ast.alias) and node.name in SECRET_READERS and rel != CREDENTIALS_FILE:
				violations.append(violation(rel, node, f"imports {node.name} outside {CREDENTIALS_FILE}"))
			if not isinstance(node, ast.Call):
				continue
			call_name = dotted_name(node.func) or ""
			if call_name.endswith("get_traceback") and any(
				keyword.arg == "with_context"
				and not (isinstance(keyword.value, ast.Constant) and keyword.value.value is False)
				for keyword in node.keywords
			):
				violations.append(
					violation(rel, node, "get_traceback(with_context=...) leaks local variables")
				)
			if call_name.split(".")[-1] == "log_error" and not _has_explicit_message(node):
				violations.append(
					violation(
						rel,
						node,
						"log_error without an explicit message (frappe then logs get_traceback(with_context=True))",
					)
				)
			is_sink = call_name in LOG_SINK_CALLS or call_name.split(".")[-1] in LOG_SINK_METHODS
			if is_sink:
				arguments = [*node.args, *(keyword.value for keyword in node.keywords)]
				leaked = set().union(*(_identifiers(argument) for argument in arguments)) & set(SECRET_NAMES)
				if leaked:
					violations.append(violation(rel, node, f"{call_name} is given {sorted(leaked)}"))
	return violations


def _allowed_legacy_nodes(rel: str, tree: ast.AST) -> set:
	target = LEGACY_ALLOWED_ASSIGNMENTS.get(rel)
	allowed = set()
	for node in ast.walk(tree):
		if isinstance(node, ast.Assign) and any(
			isinstance(t, ast.Name) and t.id == target for t in node.targets
		):
			allowed.update(id(child) for child in ast.walk(node.value))
	return allowed


def _legacy_pattern(name: str):
	return re.compile(rf"(?<![A-Za-z0-9_]){re.escape(name)}(?![A-Za-z0-9_])")


def check_no_legacy_ticket_comment(sources: dict) -> list:
	"""D8 / design amendment 1f: no HD Ticket Comment, no spoofable author fields in product code."""
	patterns = [(name, _legacy_pattern(name)) for name in LEGACY_NAMES]
	violations = []
	for rel, source in sources.items():
		if not rel.endswith(".py"):
			for number, line in enumerate(source.splitlines(), start=1):
				violations.extend(
					f"{rel}:{number}: mentions {name}" for name, pattern in patterns if pattern.search(line)
				)
			continue
		tree = parse(rel, source)
		allowed = _allowed_legacy_nodes(rel, tree)
		for node in ast.walk(tree):
			if id(node) in allowed:
				continue
			if isinstance(node, ast.Constant) and isinstance(node.value, str):
				texts = [node.value]
			elif isinstance(node, ast.keyword) and node.arg:
				texts = [node.arg]
			elif referenced_name(node):
				texts = [referenced_name(node)]
			else:
				continue
			violations.extend(
				violation(rel, node, f"mentions {name}")
				for name, pattern in patterns
				if any(pattern.search(text) for text in texts)
			)
	return violations


def check_no_frappe_skipped_test_files(rel_paths) -> list:
	"""D-34: no file, at any depth, is named like a file Frappe skips when collecting tests."""
	return [
		f"{rel}: file name {Path(rel).name} is skipped by Frappe's test runner, rename it"
		for rel in rel_paths
		if Path(rel).name in FRAPPE_SKIPPED_TEST_FILENAMES
	]


def check_ci_workflow(text: str) -> list:
	"""D-23: bench init on version-15; helpdesk v15.1.0, erpnext version-15, telephony installed before erp_ai."""
	violations = []
	commands = []
	for number, raw in enumerate(text.splitlines(), start=1):
		line = raw.strip()
		if line.startswith("bench "):
			try:
				commands.append((number, shlex.split(line)))
			except ValueError:
				violations.append(f"ci.yml:{number}: cannot parse {line!r}")

	def option(tokens, flag):
		for index, token in enumerate(tokens):
			if token == flag and index + 1 < len(tokens):
				return tokens[index + 1]
			if token.startswith(flag + "="):
				return token.split("=", 1)[1]
		return None

	def first(predicate):
		return next((number for number, tokens in commands if predicate(tokens)), None)

	init_line = first(
		lambda t: t[:2] == ["bench", "init"] and option(t, "--frappe-branch") == CI_BENCH_BRANCH
	)
	if init_line is None:
		violations.append(f"ci.yml: no `bench init --frappe-branch {CI_BENCH_BRANCH}`")
	erp_install = first(lambda t: "install-app" in t and t[-1] == "erp_ai")
	if erp_install is None:
		violations.append("ci.yml: no `install-app erp_ai`")
	for app, branch in CI_REQUIRED_APPS:
		get_line = first(
			lambda t, app=app, branch=branch: t[:2] == ["bench", "get-app"]
			and app in t
			and (branch is None or option(t, "--branch") == branch)
		)
		install_line = first(lambda t, app=app: "install-app" in t and t[-1] == app)
		if get_line is None:
			violations.append(f"ci.yml: no `bench get-app {app}`" + (f" --branch {branch}" if branch else ""))
		if install_line is None:
			violations.append(f"ci.yml: no `install-app {app}`")
		if get_line and install_line and get_line > install_line:
			violations.append(f"ci.yml: get-app {app} comes after install-app {app}")
		if install_line and erp_install and install_line > erp_install:
			violations.append(f"ci.yml: install-app {app} comes after install-app erp_ai")
	return violations


# ---------------------------------------------------------------------------------------------------
# Tests on the real tree
# ---------------------------------------------------------------------------------------------------


def _call_keywords(call: ast.Call) -> dict:
	return {kw.arg: kw.value for kw in call.keywords if kw.arg}


def _is_constant(node, value) -> bool:
	return isinstance(node, ast.Constant) and node.value == value and type(node.value) is type(value)


def check_publish_realtime_only_in_run_status(sources: dict) -> list:
	"""ADR-008: only run_status.py touches frappe.realtime; its publish calls pin `room=` and `after_commit=False`."""
	violations = []
	for rel, source in only_python(sources).items():
		tree = parse(rel, source)
		aliases = import_aliases(tree)
		if rel != RUN_STATUS_FILE:
			for node in ast.walk(tree):
				if referenced_name(node) in REALTIME_NAMES:
					violations.append(
						violation(rel, node, f"uses {referenced_name(node)} outside {RUN_STATUS_FILE}")
					)
				elif isinstance(node, ast.ImportFrom):
					for alias in node.names:
						if alias.name in REALTIME_NAMES:
							violations.append(
								violation(rel, node, f"imports {alias.name} outside {RUN_STATUS_FILE}")
							)
				elif (
					isinstance(node, ast.Name | ast.Attribute)
					and resolved_name(node, aliases) == REALTIME_MODULE
				):
					violations.append(
						violation(rel, node, f"uses {REALTIME_MODULE} outside {RUN_STATUS_FILE}")
					)
				elif isinstance(node, ast.Constant) and isinstance(node.value, str):
					# getattr(frappe, "publish_realtime"), frappe.get_attr("frappe.realtime..."), import_module(...)
					for name in (*REALTIME_NAMES, REALTIME_MODULE):
						if name in node.value:
							violations.append(
								violation(rel, node, f"names {name} in a string outside {RUN_STATUS_FILE}")
							)
			for lineno, target in imported_modules(tree, module_name(rel), rel.endswith("__init__.py")):
				if module_in(target, REALTIME_MODULE):
					violations.append(f"{rel}:{lineno}: imports {target} outside {RUN_STATUS_FILE}")
			continue
		called = set()
		for node in ast.walk(tree):
			if (
				isinstance(node, ast.Call)
				and resolved_name(node.func, aliases).rpartition(".")[2] == "publish_realtime"
			):
				called.add(id(node.func))
				keywords = _call_keywords(node)
				if "room" not in keywords:
					violations.append(violation(rel, node, "publish_realtime without an explicit room="))
				if not _is_constant(keywords.get("after_commit"), False):
					violations.append(violation(rel, node, "publish_realtime without after_commit=False"))
		for node in ast.walk(tree):
			# any other mention (alias import, `publish = frappe.publish_realtime`) hides calls from the check above
			if (referenced_name(node) == "publish_realtime" and id(node) not in called) or (
				isinstance(node, ast.alias) and node.name == "publish_realtime" and node.asname
			):
				violations.append(violation(rel, node, "binds publish_realtime to another name"))
	return violations


def check_run_status_imported_only_by_runner(sources: dict) -> list:
	"""ADR-008 decision 2: tools, handlers, tasks, gateway and eval never import the status module."""
	violations = []
	for rel, source in only_python(sources).items():
		if rel in (RUNNER_FILE, RUN_STATUS_FILE):
			continue
		tree = parse(rel, source)
		for lineno, target in imported_modules(tree, module_name(rel), rel.endswith("__init__.py")):
			if module_in(target, RUN_STATUS_MODULE):
				violations.append(f"{rel}:{lineno}: imports {target}; only {RUNNER_FILE} may (ADR-008)")
		for node in constant_strings(tree):
			if RUN_STATUS_MODULE in node.value:
				violations.append(
					violation(rel, node, f"names {RUN_STATUS_MODULE}; only {RUNNER_FILE} may (ADR-008)")
				)
	return violations


def check_run_status_writes_nothing(sources: dict) -> list:
	"""NFR-6, ADR-008 decision 5: the status module writes no record, cache entry, file or transaction state."""
	source = sources.get(RUN_STATUS_FILE)
	if source is None:
		return []
	violations = []
	tree = parse(RUN_STATUS_FILE, source)
	aliases = import_aliases(tree)
	for node in ast.walk(tree):
		if isinstance(node, ast.Call) and referenced_name(node.func) in RUN_STATUS_WRITE_NAMES:
			violations.append(
				violation(RUN_STATUS_FILE, node, f"calls {referenced_name(node.func)}: writes (NFR-6)")
			)
		elif (
			isinstance(node, ast.Name | ast.Attribute)
			and resolved_name(node, aliases) in RUN_STATUS_FORBIDDEN_ATTRIBUTES
		):
			violations.append(
				violation(RUN_STATUS_FILE, node, f"uses {resolved_name(node, aliases)}: writes (NFR-6)")
			)
	for lineno, target in imported_modules(tree, module_name(RUN_STATUS_FILE), False):
		if module_in(target, "erp_ai.gateway"):
			violations.append(f"{RUN_STATUS_FILE}:{lineno}: imports {target} (ADR-008)")
	return violations


def check_no_open_doc_or_all_room(sources: dict) -> list:
	"""R-1: no `open_doc:` room, no room="all" and no publish without an explicit room."""
	violations = []
	for rel, source in sources.items():
		if not rel.endswith(".py"):
			if OPEN_DOC_ROOM_PREFIX in source:
				violations.append(f"{rel}:0: contains {OPEN_DOC_ROOM_PREFIX} (R-1)")
			continue
		tree = parse(rel, source)
		aliases = import_aliases(tree)
		constants = {
			target.id: node.value.value
			for node in tree.body
			if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant)
			for target in node.targets
			if isinstance(target, ast.Name)
		}
		for node in constant_strings(tree):
			if OPEN_DOC_ROOM_PREFIX in node.value:
				violations.append(violation(rel, node, f"contains {OPEN_DOC_ROOM_PREFIX} (R-1)"))
		for node in ast.walk(tree):
			if (
				isinstance(node, ast.Call)
				and resolved_name(node.func, aliases).rpartition(".")[2] in REALTIME_NAMES
			):
				room = _call_keywords(node).get("room")
				if (
					room is None
					or _is_constant(room, None)
					or _is_constant(room, ALL_ROOM)
					or (
						isinstance(room, ast.Name)
						and room.id in constants
						and constants[room.id] in (None, ALL_ROOM)
					)
				):
					violations.append(
						violation(rel, node, "publishes without a document room or to room all (R-1)")
					)
	return violations


def check_form_script_only_in_install(sources: dict) -> list:
	"""ADR-007: the HD Form Script doctype is named only by install.py."""
	violations = []
	for rel, source in sources.items():
		if rel == INSTALL_FILE:
			continue
		if not rel.endswith(".py"):
			if FORM_SCRIPT_DOCTYPE_NAME in source:
				violations.append(
					f"{rel}:0: names {FORM_SCRIPT_DOCTYPE_NAME} outside {INSTALL_FILE} (ADR-007)"
				)
			continue
		tree = parse(rel, source)
		for node in constant_strings(tree):
			if FORM_SCRIPT_DOCTYPE_NAME in node.value:
				violations.append(
					violation(rel, node, f"names {FORM_SCRIPT_DOCTYPE_NAME} outside {INSTALL_FILE} (ADR-007)")
				)
		for lineno, target in imported_modules(tree, module_name(rel), rel.endswith("__init__.py")):
			if "hd_form_script" in target:
				violations.append(f"{rel}:{lineno}: imports {target} outside {INSTALL_FILE} (ADR-007)")
	return violations


def check_hooks_have_no_page_injection(sources: dict) -> list:
	"""ADR-007: hooks.py injects nothing into the page; the status script is not referenced there."""
	source = sources.get(HOOKS_FILE)
	if source is None:
		return []
	violations = []
	tree = parse(HOOKS_FILE, source)
	for node in tree.body:
		targets = node.targets if isinstance(node, ast.Assign) else [getattr(node, "target", None)]
		for target in targets:
			if isinstance(target, ast.Name) and target.id in PAGE_INJECTION_HOOKS:
				value = getattr(node, "value", None)
				strings = [n.value for n in constant_strings(value)] if value is not None else []
				if target.id == "fixtures" and not any(FORM_SCRIPT_DOCTYPE_NAME in text for text in strings):
					continue
				if target.id == "website_route_rules" and not any("helpdesk" in text for text in strings):
					continue
				violations.append(
					violation(HOOKS_FILE, node, f"sets {target.id} (ADR-007: no page injection)")
				)
	for node in constant_strings(tree):
		if "agent_status_indicator" in node.value or AGENT_STATUS_SCRIPT_NAME in node.value:
			violations.append(violation(HOOKS_FILE, node, "references the status script (ADR-007)"))
	return violations


def check_install_deletes_only_status_script(sources: dict) -> list:
	"""ADR-007 decision 4: install.py has exactly one delete, in before_uninstall, of the status script record."""
	source = sources.get(INSTALL_FILE)
	if source is None:
		return []
	tree = parse(INSTALL_FILE, source)
	constants = {}
	for node in tree.body:
		if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant):
			for target in node.targets:
				if isinstance(target, ast.Name):
					constants[target.id] = node.value.value

	def resolve(arg):
		if isinstance(arg, ast.Constant):
			return arg.value
		return constants.get(arg.id) if isinstance(arg, ast.Name) else None

	owners = {}
	for function in ast.walk(tree):
		if isinstance(function, ast.FunctionDef | ast.AsyncFunctionDef):
			for node in ast.walk(function):
				owners[id(node)] = function.name
	violations = []
	deletes = []
	for node in ast.walk(tree):
		if isinstance(node, ast.Call) and referenced_name(node.func) in DELETE_NAMES:
			deletes.append(node)
		elif isinstance(node, ast.Constant) and isinstance(node.value, str) and SQL_DELETE.match(node.value):
			violations.append(violation(INSTALL_FILE, node, "SQL delete in install code (ADR-007)"))
	if len(deletes) != 1:
		violations.append(f"{INSTALL_FILE}:0: expected exactly one delete, found {len(deletes)} (ADR-007)")
	for call in deletes:
		if owners.get(id(call)) != UNINSTALL_FUNCTION:
			violations.append(violation(INSTALL_FILE, call, f"delete outside {UNINSTALL_FUNCTION} (ADR-007)"))
		args = [resolve(arg) for arg in call.args[:2]]
		if referenced_name(call.func) != "delete_doc" or args != [
			FORM_SCRIPT_DOCTYPE_NAME,
			AGENT_STATUS_SCRIPT_NAME,
		]:
			violations.append(
				violation(
					INSTALL_FILE,
					call,
					f"delete must be delete_doc of {FORM_SCRIPT_DOCTYPE_NAME} {AGENT_STATUS_SCRIPT_NAME}",
				)
			)
	return violations


# ---------------------------------------------------------------------------------------------------
# FEAT-003 (ADR-009, ADR-010 Amendment 1): the ticket-page panel script and the two whitelisted methods
# ---------------------------------------------------------------------------------------------------

PANEL_FILE = "ticket_panel.py"
PANEL_MODULE = "erp_ai.ticket_panel"
STATUS_SCRIPT_STATE_NAME = "__erpAiAgentStatus"
STATUS_SCRIPT_ONCE_BLOCK = "if (state.socket !== socket) {"
STATUS_SCRIPT_SOCKET_EVENTS = ("docinfo_update", "doc_update", "connect", "disconnect")
STATUS_SCRIPT_QUERY_CALLS = re.compile(r"\b(querySelector(?:All)?|getElementById|getElementsBy\w+)\(")
STATUS_SCRIPT_ALLOWED_QUERIES = {"querySelector": "#app", "getElementById": "app"}
# ADR-010 Amendment 1 (read writes nothing, one comment call) and Decision 8 (no agent gates in the panel).
PANEL_FORBIDDEN_NAMES = frozenset(
	{
		"ignore_permissions",
		"set_user",
		"get_all",
		"get_values",
		"sql",
		"set_value",
		"db_set",
		"insert",
		"save",
		"commit",
		"rollback",
		"cache",
		"publish_realtime",
	}
)
PANEL_FORBIDDEN_PREFIXES = ("delete",)
PANEL_SEND_FUNCTION = "send_message"
PANEL_COMMENT_CALL = "new_comment"
PANEL_GATE_NAMES = (
	"is_enabled",
	"can_send_ticket",
	"effective_level",
	"runs_today",
	"enqueue",
	"permission_level",
	"excluded_teams",
	"ai_opt_out",
)


def mask_js(script: str) -> str:
	"""The script with comments and the inside of string literals blanked (same length, newlines kept), so
	positions and braces can be found without matching text that sits in a string or a comment."""
	out = []
	i, n = 0, len(script)
	while i < n:
		ch = script[i]
		pair = script[i : i + 2]
		if pair == "//":
			end = script.find("\n", i)
			end = n if end == -1 else end
			out.append(" " * (end - i))
			i = end
		elif pair == "/*":
			end = script.find("*/", i + 2)
			end = n if end == -1 else end + 2
			out.append("".join(c if c == "\n" else " " for c in script[i:end]))
			i = end
		elif ch in "\"'`":
			j = i + 1
			while j < n and script[j] != ch:
				j += 2 if script[j] == "\\" else 1
			out.append(ch + "".join(c if c == "\n" else " " for c in script[i + 1 : j]) + script[j : j + 1])
			i = j + 1
		else:
			out.append(ch)
			i += 1
	return "".join(out)


def js_line(script: str, offset: int) -> int:
	return script.count("\n", 0, offset) + 1


def whitelisted_functions(sources: dict) -> list:
	"""`[(rel, function node, decorator node)]` for every function decorated with `frappe.whitelist`."""
	found = []
	for rel, source in only_python(sources).items():
		tree = parse(rel, source)
		aliases = import_aliases(tree)
		for node in ast.walk(tree):
			if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
				continue
			for decorator in node.decorator_list:
				target = decorator.func if isinstance(decorator, ast.Call) else decorator
				if resolved_name(target, aliases) == "frappe.whitelist":
					found.append((rel, node, decorator))
	return found


def whitelisted_paths(sources: dict) -> set:
	return {f"{module_name(rel)}.{node.name}" for rel, node, _decorator in whitelisted_functions(sources)}


def check_call_allow_list(script: str, allowed_methods, sources: dict) -> list:
	"""ADR-009: the literals passed to `call(` are exactly the allowed methods, each a whitelisted function."""
	violations = check_status_script_calls(script, allowed_methods)
	literals = {m.group(2) for m in STATUS_SCRIPT_CALL.finditer(script) if m.group(1) is not None}
	for missing in sorted(set(allowed_methods) - literals):
		violations.append(f"{missing} is in PANEL_METHODS but the script never calls it")
	paths = whitelisted_paths(sources)
	for literal in sorted(literals):
		if literal not in paths:
			violations.append(f"{literal} does not point to a @frappe.whitelist function")
	return violations


def check_status_script_queries(script: str) -> list:
	"""ADR-009: element lookups only for the Vue root (`#app`), never into Helpdesk's own DOM."""
	violations = []
	masked = mask_js(script)
	for match in STATUS_SCRIPT_QUERY_CALLS.finditer(masked):
		line = js_line(script, match.start())
		argument = re.match(r"\s*([\"'])(.*?)\1\s*\)", script[match.end() :])
		if argument is None or STATUS_SCRIPT_ALLOWED_QUERIES.get(match.group(1)) != argument.group(2):
			violations.append(f"line {line}: {match.group(1)}( is only allowed with the Vue root (#app)")
	return violations


def check_status_script_window_state(script: str) -> list:
	"""ADR-009: one `window.__erpAi…` state object and no other property written on `window`."""
	violations = []
	names = set(re.findall(r"__erpAi\w*", script))
	if names != {STATUS_SCRIPT_STATE_NAME}:
		violations.append(f"window state names are {sorted(names)}, expected only {STATUS_SCRIPT_STATE_NAME}")
	masked = mask_js(script)
	for match in re.finditer(r"\bwindow\.(\w+)\s*=(?!=)", masked):
		if match.group(1) != STATUS_SCRIPT_STATE_NAME:
			violations.append(f"line {js_line(script, match.start())}: window.{match.group(1)} is written")
	for match in re.finditer(r"\bwindow\s*\[", masked):
		violations.append(f"line {js_line(script, match.start())}: window[...] access hides a second state")
	return violations


def _matching_brace(masked: str, open_at: int) -> int:
	depth = 0
	for i in range(open_at, len(masked)):
		if masked[i] == "{":
			depth += 1
		elif masked[i] == "}":
			depth -= 1
			if depth == 0:
				return i
	return -1


def socket_on_registrations(script: str) -> list:
	"""`[(line, inside the once-per-socket block, event name or None)]` for every `.on(` call."""
	masked = mask_js(script)
	start = masked.find(STATUS_SCRIPT_ONCE_BLOCK)
	block = (-1, -1)
	if start != -1:
		open_at = start + len(STATUS_SCRIPT_ONCE_BLOCK) - 1
		block = (open_at, _matching_brace(masked, open_at))
	declared = re.search(r"const EVENT = \"([^\"]*)\"", script)
	found = []
	for match in re.finditer(r"\.on\(", masked):
		argument = re.match(r"\s*(?:\"([^\"]*)\"|([A-Za-z_$][\w$]*))", script[match.end() :])
		name = None
		if argument is not None and argument.group(1) is not None:
			name = argument.group(1)
		elif argument is not None and argument.group(2) == "EVENT" and declared:
			name = declared.group(1)
		inside = block[0] < match.start() < block[1]
		found.append((js_line(script, match.start()), inside, name))
	return found


def check_socket_on_only_in_once_block(script: str, status_event: str) -> list:
	"""ADR-009: every `.on(` sits in the `if (state.socket !== socket)` block and names an allowed event."""
	violations = []
	if mask_js(script).find(STATUS_SCRIPT_ONCE_BLOCK) == -1:
		violations.append(f"the once-per-socket block {STATUS_SCRIPT_ONCE_BLOCK} is missing")
	allowed = {status_event, *STATUS_SCRIPT_SOCKET_EVENTS}
	for line, inside, name in socket_on_registrations(script):
		if not inside:
			violations.append(f"line {line}: .on( is outside the once-per-socket block")
		if name not in allowed:
			violations.append(f"line {line}: event {name!r} is not one of {sorted(allowed)}")
	return violations


def check_whitelisted_methods_declare_http_methods(sources: dict) -> list:
	"""ADR-010: every `@frappe.whitelist` in the app names its HTTP methods and never allows guests."""
	violations = []
	for rel, node, decorator in whitelisted_functions(sources):
		if not isinstance(decorator, ast.Call):
			violations.append(
				violation(rel, decorator, f"{node.name}: bare @frappe.whitelist, methods= missing")
			)
			continue
		keywords = {kw.arg: kw.value for kw in decorator.keywords}
		if "allow_guest" in keywords:
			violations.append(violation(rel, decorator, f"{node.name}: allow_guest is not allowed"))
		methods = keywords.get("methods")
		if not (
			isinstance(methods, ast.List | ast.Tuple)
			and methods.elts
			and all(isinstance(e, ast.Constant) and isinstance(e.value, str) for e in methods.elts)
		):
			violations.append(violation(rel, decorator, f"{node.name}: methods= must list HTTP methods"))
	return violations


def check_ticket_panel_whitelist(sources: dict, expected=PANEL_METHODS) -> list:
	"""ADR-010 Amendment 1: exactly the two panel methods, each `methods=["POST"]` and nothing else."""
	if PANEL_FILE not in sources:
		return [f"{PANEL_FILE} is missing"]
	violations = []
	own = whitelisted_functions({PANEL_FILE: sources[PANEL_FILE]})
	paths = sorted(f"{PANEL_MODULE}.{node.name}" for _rel, node, _decorator in own)
	if paths != sorted(expected):
		violations.append(f"whitelisted functions are {paths}, expected {sorted(expected)}")
	for rel, node, decorator in own:
		methods = None
		if isinstance(decorator, ast.Call):
			methods = {kw.arg: kw.value for kw in decorator.keywords}.get("methods")
		values = (
			[e.value if isinstance(e, ast.Constant) else None for e in methods.elts]
			if isinstance(methods, ast.List | ast.Tuple)
			else None
		)
		if values != ["POST"]:
			violations.append(violation(rel, decorator, f'{node.name}: methods must be exactly ["POST"]'))
	return violations


def _panel_identifiers(tree: ast.AST):
	"""`(node, name)` for every identifier-like use: names, attributes, keyword names, imported names."""
	for node in ast.walk(tree):
		if isinstance(node, ast.Name):
			yield node, node.id
		elif isinstance(node, ast.Attribute):
			yield node, node.attr
		elif isinstance(node, ast.keyword) and node.arg:
			yield node, node.arg
		elif isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
			yield node, node.name
		elif isinstance(node, ast.Import | ast.ImportFrom):
			for alias in node.names:
				yield node, alias.name.rpartition(".")[2]


def _comment_calls(root: ast.AST) -> list:
	return [
		n
		for n in ast.walk(root)
		if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == PANEL_COMMENT_CALL
	]


def check_ticket_panel_forbidden_calls(sources: dict) -> list:
	"""ADR-010 Amendment 1: no permission bypass, user switch, raw query, write, commit, cache or realtime in
	the panel module; exactly one `.new_comment(` and it sits in `send_message`."""
	if PANEL_FILE not in sources:
		return [f"{PANEL_FILE} is missing"]
	tree = parse(PANEL_FILE, sources[PANEL_FILE])
	violations = []
	for node, name in _panel_identifiers(tree):
		if name in PANEL_FORBIDDEN_NAMES or name.startswith(PANEL_FORBIDDEN_PREFIXES):
			violations.append(violation(PANEL_FILE, node, f"{name} is not allowed in the panel module"))
	for node in constant_strings(tree):
		if node.value in PANEL_FORBIDDEN_NAMES:
			violations.append(
				violation(PANEL_FILE, node, f"string {node.value!r} is not allowed in the panel")
			)
	total = _comment_calls(tree)
	if len(total) != 1:
		violations.append(
			f"{PANEL_FILE}: expected exactly one .{PANEL_COMMENT_CALL}( call, found {len(total)}"
		)
	send = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == PANEL_SEND_FUNCTION]
	if len(send) != 1 or len(_comment_calls(send[0])) != 1:
		violations.append(
			f"{PANEL_FILE}: the one .{PANEL_COMMENT_CALL}( call must be inside {PANEL_SEND_FUNCTION}"
		)
	return violations


def check_ticket_panel_does_not_evaluate_agent_gates(sources: dict) -> list:
	"""ADR-010 Decision 8: the panel never evaluates the agent's gates (the comment handler and runner do)."""
	if PANEL_FILE not in sources:
		return [f"{PANEL_FILE} is missing"]
	tree = parse(PANEL_FILE, sources[PANEL_FILE])
	violations = []
	for node, name in _panel_identifiers(tree):
		for gate in PANEL_GATE_NAMES:
			if gate in name:
				violations.append(violation(PANEL_FILE, node, f"{name} evaluates an agent gate ({gate})"))
	for node in constant_strings(tree):
		for gate in PANEL_GATE_NAMES:
			if re.search(rf"\b{gate}\b", node.value):
				violations.append(violation(PANEL_FILE, node, f"string mentions agent gate {gate}"))
	return violations


# ---------------------------------------------------------------------------------------------------
# FEAT-006 rules (ADR-019..021 "Ràng buộc", AC-7c, AC-10, AC-14)
# ---------------------------------------------------------------------------------------------------

ROUTE_FILE = "agent/tools/route_ticket.py"
ROUTE_MODULE_NAME = "route_ticket"
REGISTRY_FILE = "agent/tools/registry.py"
RUN_LOG_FILE = "agent/run_log.py"
LOG_DOCTYPE_FILE = "erp_ai_agent/doctype/erp_ai_log/erp_ai_log.json"
AUTHORITY_FILE = "agent/authority.py"
AGENT_PREFIX = "agent/"

ROUTE_NOT_A_TOOL_NAMES = ("TOOLS", "ToolSpec")
ROUTE_SAVE_FUNCTION = "apply_route"
ASSIGN_MODULE = "frappe.desk.form.assign_to"
ASSIGN_CALL_SUFFIXES = ("assign_to.add", "assign_to.add_multiple", "assign_agent")
ASSIGN_AGENT_NAME = "assign_agent"
ROUTE_WRITE_FUNCTIONS = ("apply_route", "assign_owner", "post_routing_comment", "create_routed_task")
TODO_DOCTYPE = "ToDo"
DOC_CREATE_CALLS = ("get_doc", "new_doc")
SHARE_BYPASS_NAMES = ("ignore_share_permission", "add_docshare")
SHARE_BYPASS_SUFFIXES = ("assign_to._add", "frappe.share.add")
ENTRY_TYPES_EXPECTED = ("classify", "reason", "skip", "change")

# `_assign` is the denormalised JSON column of HD Ticket. Routing must read ToDo through site_facts instead.
# authority.py (FEAT-002, "who may instruct the bot") predates routing and is the one reader allowed.
ASSIGN_FIELD = re.compile(r"(?<![A-Za-z0-9])_assign(?![A-Za-z0-9_])")
ASSIGN_FIELD_ALLOWED_FILE = AUTHORITY_FILE
ASSIGN_FIELD_ALLOWED_FUNCTION = "_assigned_by_other"

SLA_DATE_FIELDS = ("response_by", "resolution_by")
SLA_WRITE_CALLS = ("setattr", "set", "set_value", "db_set", "update")

# Names of the people the old hard-coded routing table listed (spec 16.2), matched as whole words.
DEFAULT_PEOPLE = ("Việt", "Tiến", "Hiếu", "Lan", "Hà", "Thư", "Chi")
PERSON_NAME = re.compile(r"(?<!\w)(?:" + "|".join(DEFAULT_PEOPLE) + r")(?!\w)")
# Same letters, other meaning: "Việt Nam" (prompts.py), "Tiếng Việt" (prompts.py), "Thư mục" (tools/source.py).
NAME_COINCIDENCES = re.compile(r"(?<!\w)(?:Việt Nam|Tiếng Việt|Thư mục)(?!\w)")
# The bot's own account as a string literal; `erp_ai.agent...` module paths do not match (`_` is a word char).
AGENT_ACCOUNT = re.compile(r"(?<![\w.])ai\.agent(?!\w)")


def _missing(rel: str) -> list:
	return [f"{rel}: file missing"]


def _node_names(node) -> list:
	"""Every bare name a node carries: Name/Attribute, import alias, keyword argument, string constant."""
	names = []
	if (name := referenced_name(node)) is not None:
		names.append(name)
	if isinstance(node, ast.alias):
		names.append(node.name.split(".")[-1])
	elif isinstance(node, ast.keyword) and node.arg:
		names.append(node.arg)
	elif isinstance(node, ast.Constant) and isinstance(node.value, str):
		names.append(node.value)
	return names


def check_route_module_is_not_a_tool(sources: dict) -> list:
	"""ADR-019: route_ticket.py is no tool: no TOOLS / ToolSpec in it, not listed by the registry."""
	registry, route = sources.get(REGISTRY_FILE), sources.get(ROUTE_FILE)
	if registry is None:
		return _missing(REGISTRY_FILE)
	if route is None:
		return _missing(ROUTE_FILE)
	violations = []
	for node in constant_strings(parse(REGISTRY_FILE, registry)):
		if ROUTE_MODULE_NAME in node.value:
			violations.append(
				violation(REGISTRY_FILE, node, f"the registry lists {ROUTE_MODULE_NAME} (ADR-019)")
			)
	for node in ast.walk(parse(ROUTE_FILE, route)):
		for name in _node_names(node):
			if name in ROUTE_NOT_A_TOOL_NAMES and not isinstance(node, ast.Constant):
				violations.append(violation(ROUTE_FILE, node, f"{name} in the routing module (ADR-019)"))
	# No other tool module may expose a routing write function as a tool handler either.
	for rel, source in only_python(scoped(sources, TOOLS_PREFIX)).items():
		if rel == ROUTE_FILE:
			continue
		for node in ast.walk(parse(rel, source)):
			handlers = []
			if isinstance(node, ast.keyword) and node.arg == "handler":
				handlers.append(node.value)
			elif (
				isinstance(node, ast.Call) and referenced_name(node.func) == "ToolSpec" and len(node.args) > 3
			):
				handlers.append(node.args[3])
			for handler in handlers:
				if referenced_name(handler) in ROUTE_WRITE_FUNCTIONS:
					violations.append(
						violation(rel, handler, f"{referenced_name(handler)} is a tool handler (ADR-019)")
					)
	return violations


def check_route_module_single_ticket_save(sources: dict) -> list:
	"""ADR-020 QĐ 1/6: exactly one `.save()` in route_ticket.py, inside apply_route; no `db_update` at all."""
	route = sources.get(ROUTE_FILE)
	if route is None:
		return _missing(ROUTE_FILE)
	tree = parse(ROUTE_FILE, route)
	inside = set()
	for node in tree.body:
		if isinstance(node, ast.FunctionDef) and node.name == ROUTE_SAVE_FUNCTION:
			inside = {id(child) for child in ast.walk(node)}
	saves = [
		node
		for node in ast.walk(tree)
		if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "save"
	]
	violations = [
		violation(ROUTE_FILE, node, f"`.save()` outside {ROUTE_SAVE_FUNCTION} (ADR-020)")
		for node in saves
		if id(node) not in inside
	]
	if len(saves) != 1:
		violations.append(
			f"{ROUTE_FILE}: found {len(saves)} `.save()` calls, exactly one ticket save (ADR-020)"
		)
	violations.extend(
		violation(ROUTE_FILE, node, "`db_update` in the routing module (ADR-020)")
		for node in ast.walk(tree)
		if isinstance(node, ast.Call) and referenced_name(node.func) == "db_update"
	)
	return violations


def check_assign_to_only_in_route_module(sources: dict) -> list:
	"""ADR-021 QĐ 3 / ADR-015: `assign_to.add` is called only in route_ticket.py."""
	violations = []
	for rel, source in only_python(sources).items():
		if rel == ROUTE_FILE:
			continue
		tree = parse(rel, source)
		aliases = import_aliases(tree)
		for lineno, target in imported_modules(tree, module_name(rel), rel.endswith("__init__.py")):
			if module_in(target, ASSIGN_MODULE):
				violations.append(f"{rel}:{lineno}: imports {target} outside {ROUTE_FILE} (ADR-021)")
		for node in ast.walk(tree):
			if isinstance(node, ast.Name | ast.Attribute) and resolved_name(node, aliases).endswith(
				ASSIGN_CALL_SUFFIXES
			):
				violations.append(violation(rel, node, f"assigns people outside {ROUTE_FILE} (ADR-021)"))
			elif isinstance(node, ast.Constant) and node.value == ASSIGN_AGENT_NAME:
				violations.append(
					violation(rel, node, f"names {ASSIGN_AGENT_NAME} outside {ROUTE_FILE} (ADR-021)")
				)
			elif _creates_todo(node):
				violations.append(violation(rel, node, f"creates a ToDo outside {ROUTE_FILE} (ADR-021)"))
	return violations


def _creates_todo(node) -> bool:
	"""`get_doc("ToDo", ...)`, `get_doc({"doctype": "ToDo", ...})`, `new_doc("ToDo")`."""
	if not (isinstance(node, ast.Call) and referenced_name(node.func) in DOC_CREATE_CALLS and node.args):
		return False
	first = node.args[0]
	if isinstance(first, ast.Dict):
		return any(
			isinstance(key, ast.Constant)
			and key.value == "doctype"
			and isinstance(value, ast.Constant)
			and value.value == TODO_DOCTYPE
			for key, value in zip(first.keys, first.values, strict=True)
		)
	return isinstance(first, ast.Constant) and first.value == TODO_DOCTYPE


def check_no_share_bypass(sources: dict) -> list:
	"""ADR-021 QĐ 3: sharing is never forced (ignore_share_permission, assign_to._add, add_docshare, frappe.share.add)."""
	violations = []
	for rel, source in only_python(sources).items():
		tree = parse(rel, source)
		aliases = import_aliases(tree)
		for node in ast.walk(tree):
			bypass = [name for name in _node_names(node) if name in SHARE_BYPASS_NAMES]
			if isinstance(node, ast.Name | ast.Attribute) and resolved_name(node, aliases).endswith(
				SHARE_BYPASS_SUFFIXES
			):
				bypass.append(resolved_name(node, aliases))
			violations.extend(
				violation(rel, node, f"{name} bypasses sharing rules (ADR-021)") for name in bypass
			)
	return violations


def check_no_assign_column_for_decisions(sources: dict) -> list:
	"""ADR-019 QĐ 5: nothing under agent/ reads `_assign` (except authority.py, see ASSIGN_FIELD_ALLOWED_FILE)."""
	violations = []
	for rel, source in only_python(scoped(sources, AGENT_PREFIX)).items():
		tree = parse(rel, source)
		exempt = set()
		if rel == ASSIGN_FIELD_ALLOWED_FILE:
			for func in ast.walk(tree):
				if isinstance(func, ast.FunctionDef) and func.name == ASSIGN_FIELD_ALLOWED_FUNCTION:
					exempt |= {id(child) for child in ast.walk(func)}
		for node in ast.walk(tree):
			if id(node) in exempt:
				continue
			if referenced_name(node) == "_assign" or (
				isinstance(node, ast.Constant)
				and isinstance(node.value, str)
				and ASSIGN_FIELD.search(node.value)
			):
				violations.append(violation(rel, node, "reads `_assign` (decide from ToDo, ADR-019)"))
	return violations


def _sla_date_writes(tree: ast.AST):
	for node in ast.walk(tree):
		targets = []
		if isinstance(node, ast.Assign):
			targets = node.targets
		elif isinstance(node, ast.AugAssign | ast.AnnAssign):
			targets = [node.target]
		for target in targets:
			for part in ast.walk(target):
				if referenced_name(part) in SLA_DATE_FIELDS or (
					isinstance(part, ast.Constant) and part.value in SLA_DATE_FIELDS
				):
					yield part, "assigns"
		# The field name held in a constant (`F = "response_by"`, `F = ("response_by", ...)`), written later.
		if isinstance(node, ast.Assign | ast.AnnAssign | ast.AugAssign) and node.value is not None:
			held = node.value.elts if isinstance(node.value, ast.Tuple | ast.List | ast.Set) else [node.value]
			for part in held:
				if isinstance(part, ast.Constant) and part.value in SLA_DATE_FIELDS:
					yield part, "holds the name of"
		if isinstance(node, ast.keyword) and node.arg in SLA_DATE_FIELDS:
			yield node.value, "passes"
		elif isinstance(node, ast.Dict):
			for key in node.keys:
				if isinstance(key, ast.Constant) and key.value in SLA_DATE_FIELDS:
					yield key, "sets"
		elif isinstance(node, ast.Call) and (dotted_name(node.func) or "").split(".")[-1] in SLA_WRITE_CALLS:
			for arg in node.args:
				if isinstance(arg, ast.Constant) and arg.value in SLA_DATE_FIELDS:
					yield arg, "writes"


def check_feature_never_assigns_sla_dates(sources: dict) -> list:
	"""AC-10: Helpdesk computes `response_by`/`resolution_by`; nothing under agent/ writes them."""
	violations = []
	for rel, source in only_python(scoped(sources, AGENT_PREFIX)).items():
		for node, verb in _sla_date_writes(parse(rel, source)):
			violations.append(violation(rel, node, f"{verb} an SLA date (AC-10)"))
	return violations


def check_no_default_people_in_agent_python(sources: dict) -> list:
	"""AC-14: no hard-coded person (spec 16.2 names, the bot account) in a string under agent/."""
	violations = []
	for rel, source in only_python(scoped(sources, AGENT_PREFIX)).items():
		for node in constant_strings(parse(rel, source)):
			text = NAME_COINCIDENCES.sub(" ", node.value)
			for match in (*PERSON_NAME.finditer(text), *AGENT_ACCOUNT.finditer(text)):
				violations.append(violation(rel, node, f"hard-coded person {match.group(0)!r} (AC-14)"))
	return violations


def check_entry_types_unchanged(sources: dict) -> list:
	"""ADR-019 QĐ 7 + ADR-012 QĐ 6: the log keeps its four entry types, in the code and in the DocType options."""
	run_log, doctype = sources.get(RUN_LOG_FILE), sources.get(LOG_DOCTYPE_FILE)
	if run_log is None:
		return _missing(RUN_LOG_FILE)
	if doctype is None:
		return _missing(LOG_DOCTYPE_FILE)
	violations = []
	found = None
	for node in parse(RUN_LOG_FILE, run_log).body:
		if isinstance(node, ast.Assign) and any(
			getattr(t, "id", None) == "ENTRY_TYPES" for t in node.targets
		):
			try:
				found = ast.literal_eval(node.value)
			except ValueError:
				found = "not a literal"
	if found != ENTRY_TYPES_EXPECTED:
		violations.append(f"{RUN_LOG_FILE}: ENTRY_TYPES is {found!r}, expected {ENTRY_TYPES_EXPECTED!r}")
	options = [
		field.get("options")
		for field in json.loads(doctype)["fields"]
		if field.get("fieldname") == "entry_type"
	]
	if options != ["\n".join(ENTRY_TYPES_EXPECTED)]:
		violations.append(f"{LOG_DOCTYPE_FILE}: entry_type options are {options!r}")
	return violations


class TestArchitecture(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		cls.sources = load_product_sources()

	def test_scan_covers_the_product_tree_and_skips_tests(self):
		self.assertGreater(len(self.sources), 0)
		for expected in (
			HANDLERS_FILE,
			QUEUE_FILE,
			POLICY_FILE,
			CLIENT_FILE,
			SOURCE_TOOL_FILE,
			READ_TOOL_FILE,
		):
			self.assertIn(expected, self.sources)
		self.assertEqual([rel for rel in self.sources if "/tests/" in f"/{rel}"], [])
		self.assertEqual([rel for rel in self.sources if Path(rel).name.startswith("test_")], [])

	def test_layer_imports(self):
		scanned = only_python(self.sources)
		self.assertGreater(len(scanned), 0)
		for scope, _forbidden, _reason in LAYER_RULES:
			prefix = module_name(scope.removeprefix(PACKAGE + ".").replace(".", "/") + ".py")
			self.assertTrue(
				any(module_in(module_name(rel), scope) for rel in scanned),
				f"no file in scope {scope} / {prefix}",
			)
		self.assertEqual(check_layer_imports(self.sources), [])
		self.assertEqual(check_import_boundaries(self.sources), [])

	def test_single_enqueue_call_site(self):
		scanned = only_python(self.sources)
		self.assertGreater(len(scanned), 0)
		self.assertEqual(check_single_enqueue_site(self.sources), [])
		self.assertEqual(check_enqueue_call_shape(self.sources), [])

	def test_no_save_on_settings_in_product_code(self):
		scanned = only_python(self.sources)
		self.assertGreater(len(scanned), 0)
		for controller in CONFIG_CONTROLLER_FILES:
			self.assertIn(controller, scanned)
		self.assertEqual(check_no_save_on_config(self.sources), [])

	def test_tools_never_bypass_permissions(self):
		scanned = only_python(scoped(self.sources, TOOLS_PREFIX))
		self.assertGreater(len(scanned), 0)
		self.assertEqual(check_tools_never_bypass_permissions(self.sources), [])

	def test_subprocess_only_in_source_tool(self):
		scanned = only_python(self.sources)
		self.assertGreater(len(scanned), 0)
		self.assertIn("subprocess", self.sources[SOURCE_TOOL_FILE])
		self.assertIn("subprocess", self.sources[PROCESS_RUNNER_FILE])
		self.assertEqual(check_subprocess_only_in_source_tool(self.sources), [])
		self.assertEqual(check_subprocess_call_shape(self.sources), [])
		wrapped = [
			node
			for node in ast.walk(parse(SOURCE_TOOL_FILE, self.sources[SOURCE_TOOL_FILE]))
			if isinstance(node, ast.Call) and node.args and is_timeout_wrapped(node.args[0])
		]
		self.assertEqual(
			len(wrapped),
			1,
			"run_git_read must pass its argv inline so the shape rule sees it; "
			"a later task that adds another timeout-wrapped call in source.py updates this count",
		)

	def test_level_and_send_policy_fields_only_in_policy(self):
		scanned = only_python(self.sources)
		self.assertGreater(len(scanned), 0)
		self.assertIn("permission_level", self.sources[POLICY_FILE])
		self.assertEqual(check_policy_fields_only_in_policy(self.sources), [])

	def test_handlers_do_not_import_gateway_or_runner(self):
		scanned = {rel: src for rel, src in self.sources.items() if rel == HANDLERS_FILE}
		self.assertGreater(len(scanned), 0)
		self.assertEqual(check_handlers_imports(self.sources), [])

	def test_secret_handling_rules(self):
		scanned = only_python(self.sources)
		self.assertGreater(len(scanned), 0)
		self.assertIn("get_decrypted_password", self.sources[CREDENTIALS_FILE])
		self.assertEqual(check_secret_handling(self.sources), [])

	def test_no_legacy_ticket_comment_or_spoofable_author(self):
		scanned = load_product_sources(suffixes=(".py", ".json", ".js", ".html"))
		self.assertGreater(len(scanned), 0)
		self.assertGreater(len(only_python(scanned)), 0)
		self.assertEqual(check_no_legacy_ticket_comment(scanned), [])

	def test_ci_installs_required_apps(self):
		text = CI_WORKFLOW.read_text(encoding="utf-8")
		self.assertGreater(len(text.splitlines()), 0)
		self.assertEqual(check_ci_workflow(text), [])

	def test_no_test_file_named_like_frappe_skips(self):
		rel_paths = [
			path.relative_to(PACKAGE_ROOT).as_posix()
			for path in sorted(PACKAGE_ROOT.rglob("*.py"))
			if "__pycache__" not in path.parts
		]
		self.assertGreater(len(rel_paths), 0)
		self.assertEqual(check_no_frappe_skipped_test_files(rel_paths), [])
		self.assertIn("agent/test_agent_runner.py", rel_paths)

	def test_status_script_static_rules(self):
		script = load_product_sources(suffixes=(".js",)).get(STATUS_SCRIPT_FILE)
		self.assertIsNotNone(script, f"{STATUS_SCRIPT_FILE} is missing")
		self.assertIn("function setupForm({ doc, call, router })", script)
		for pattern in STATUS_SCRIPT_FORBIDDEN:
			self.assertIsNone(re.search(pattern, script, re.MULTILINE), f"forbidden in script: {pattern}")
		for pattern in STATUS_SCRIPT_REQUIRED:
			self.assertIsNotNone(re.search(pattern, script), f"missing in script: {pattern}")

	def test_status_script_calls_use_literal_panel_methods(self):
		script = load_product_sources(suffixes=(".js",)).get(STATUS_SCRIPT_FILE)
		self.assertIsNotNone(script, f"{STATUS_SCRIPT_FILE} is missing")
		self.assertGreater(len(STATUS_SCRIPT_CALL.findall(script)), 0, "no call( found in script")
		self.assertEqual(check_status_script_calls(script, PANEL_METHODS), [])

	def test_status_script_call_check_catches_variable_and_unknown_method(self):
		allowed = ("erp_ai.ticket_panel.get_panel_data",)
		self.assertEqual(
			check_status_script_calls('state.call("erp_ai.ticket_panel.get_panel_data", {})', allowed), []
		)
		self.assertEqual(len(check_status_script_calls("state.call(METHOD, {})", allowed)), 1)
		self.assertEqual(len(check_status_script_calls('state.call("other.method", {})', allowed)), 1)
		self.assertEqual(len(check_status_script_calls("state\n.call(\n  METHOD)", allowed)), 1)

	def status_script(self):
		script = load_product_sources(suffixes=(".js",)).get(STATUS_SCRIPT_FILE)
		self.assertIsNotNone(script, f"{STATUS_SCRIPT_FILE} is missing")
		return script

	def test_status_script_calls_only_panel_methods(self):
		script = self.status_script()
		literals = {m.group(2) for m in STATUS_SCRIPT_CALL.finditer(script) if m.group(1) is not None}
		self.assertEqual(literals, set(PANEL_METHODS))
		self.assertEqual(
			whitelisted_paths(self.sources) & set(PANEL_METHODS),
			set(PANEL_METHODS),
		)
		self.assertEqual(check_call_allow_list(script, PANEL_METHODS, self.sources), [])

	def test_status_script_queries_only_app_root(self):
		script = self.status_script()
		self.assertIn('document.querySelector("#app")', script)
		self.assertEqual(check_status_script_queries(script), [])

	def test_status_script_has_one_window_state(self):
		script = self.status_script()
		self.assertIn(f"window.{STATUS_SCRIPT_STATE_NAME} = window.{STATUS_SCRIPT_STATE_NAME} ||", script)
		self.assertEqual(check_status_script_window_state(script), [])

	def test_status_script_socket_events_only_in_once_block(self):
		script = self.status_script()
		registered = socket_on_registrations(script)
		self.assertEqual(
			{name for _line, inside, name in registered if inside},
			{AGENT_STATUS_EVENT, "docinfo_update", "doc_update", "connect"},
		)
		self.assertEqual(check_socket_on_only_in_once_block(script, AGENT_STATUS_EVENT), [])

	def test_whitelisted_methods_declare_http_methods_without_guest(self):
		found = {(rel, node.name) for rel, node, _decorator in whitelisted_functions(self.sources)}
		self.assertTrue({(PANEL_FILE, "get_panel_data"), (PANEL_FILE, "send_message")} <= found, found)
		self.assertEqual(check_whitelisted_methods_declare_http_methods(self.sources), [])

	def test_ticket_panel_has_exactly_two_whitelisted_methods(self):
		self.assertEqual(
			sorted(PANEL_METHODS),
			["erp_ai.ticket_panel.get_panel_data", "erp_ai.ticket_panel.send_message"],
		)
		self.assertEqual(check_ticket_panel_whitelist(self.sources), [])

	def test_ticket_panel_forbidden_calls(self):
		self.assertIn(".new_comment(", self.sources[PANEL_FILE])
		self.assertEqual(check_ticket_panel_forbidden_calls(self.sources), [])

	def test_ticket_panel_does_not_evaluate_agent_gates(self):
		self.assertIn(PANEL_FILE, self.sources)
		self.assertEqual(check_ticket_panel_does_not_evaluate_agent_gates(self.sources), [])

	def test_layer_rules_forbid_ticket_panel_from_gateway_and_agent(self):
		rules = {scope: forbidden for scope, forbidden, _reason in LAYER_RULES}
		for scope in ("erp_ai.gateway", "erp_ai.agent"):
			self.assertIn("erp_ai.ticket_panel", rules[scope])
		self.assertEqual(
			rules["erp_ai.ticket_panel"], ("erp_ai.gateway", "erp_ai.agent.runner", "erp_ai.agent.queue")
		)

	def test_status_event_name_matches_script(self):
		match = re.search(r'^AGENT_STATUS_EVENT = "([^"]+)"', self.sources[CONSTANTS_FILE], re.MULTILINE)
		self.assertIsNotNone(match, "AGENT_STATUS_EVENT not found in constants.py")
		script = load_product_sources(suffixes=(".js",)).get(STATUS_SCRIPT_FILE)
		self.assertIsNotNone(script, f"{STATUS_SCRIPT_FILE} is missing")
		self.assertIn(f'"{match.group(1)}"', script)

	def test_publish_realtime_only_in_run_status(self):
		self.assertIn(RUN_STATUS_FILE, self.sources)
		self.assertIn("publish_realtime", self.sources[RUN_STATUS_FILE])
		self.assertEqual(check_publish_realtime_only_in_run_status(self.sources), [])

	def test_run_status_imported_only_by_runner(self):
		self.assertIn(RUN_STATUS_FILE, self.sources)
		runner_imports = imported_modules(
			parse(RUNNER_FILE, self.sources[RUNNER_FILE]), module_name(RUNNER_FILE), False
		)
		self.assertIn(RUN_STATUS_MODULE, [target for _lineno, target in runner_imports])
		self.assertEqual(check_run_status_imported_only_by_runner(self.sources), [])

	def test_run_status_writes_nothing(self):
		self.assertIn(RUN_STATUS_FILE, self.sources)
		self.assertEqual(check_run_status_writes_nothing(self.sources), [])

	def test_no_open_doc_or_all_room(self):
		scanned = load_product_sources(suffixes=(".py", ".json", ".js", ".html"))
		self.assertIn(RUN_STATUS_FILE, scanned)
		self.assertIn(STATUS_SCRIPT_FILE, scanned)
		self.assertEqual(check_no_open_doc_or_all_room(scanned), [])

	def test_form_script_only_in_install(self):
		scanned = load_product_sources(suffixes=(".py", ".json", ".js", ".html"))
		self.assertIn(FORM_SCRIPT_DOCTYPE_NAME, scanned[INSTALL_FILE])
		self.assertIn(STATUS_SCRIPT_FILE, scanned)
		self.assertEqual(check_form_script_only_in_install(scanned), [])

	def test_hooks_have_no_page_injection(self):
		self.assertIn(HOOKS_FILE, self.sources)
		self.assertEqual(check_hooks_have_no_page_injection(self.sources), [])

	def test_install_deletes_only_status_script_on_uninstall(self):
		self.assertIn(INSTALL_FILE, self.sources)
		self.assertEqual(check_install_deletes_only_status_script(self.sources), [])
		self.assertIn(f'before_uninstall = "{UNINSTALL_HOOK}"', self.sources[HOOKS_FILE])

	# FEAT-006: routing (ADR-019..021) ------------------------------------------------------------

	def test_route_module_not_in_tool_modules_and_has_no_tools(self):
		self.assertIn("TOOL_MODULES", self.sources[REGISTRY_FILE])
		self.assertIn(ROUTE_FILE, self.sources)
		self.assertEqual(check_route_module_is_not_a_tool(self.sources), [])

	def test_route_module_single_ticket_save(self):
		self.assertIn(".save()", self.sources[ROUTE_FILE])
		self.assertEqual(check_route_module_single_ticket_save(self.sources), [])

	def test_assign_to_only_in_route_module(self):
		self.assertIn("assign_to.add(", self.sources[ROUTE_FILE])
		self.assertEqual(check_assign_to_only_in_route_module(self.sources), [])

	def test_no_share_bypass(self):
		self.assertGreater(len(only_python(self.sources)), 0)
		self.assertEqual(check_no_share_bypass(self.sources), [])

	def test_auto_assign_switch_only_in_policy(self):
		self.assertIn("auto_assign_enabled", POLICY_FIELDS)
		self.assertIn("auto_assign_enabled", self.sources[POLICY_FILE])
		# The runner gets the switch only by calling the policy function, never by reading the field.
		self.assertIn("policy.auto_assign_enabled(", self.sources[RUNNER_FILE])
		self.assertEqual(check_policy_fields_only_in_policy(self.sources), [])

	def test_entry_types_unchanged(self):
		scanned = load_product_sources(suffixes=(".py", ".json"))
		self.assertIn(LOG_DOCTYPE_FILE, scanned)
		self.assertEqual(check_entry_types_unchanged(scanned), [])

	def test_assign_field_not_used_for_decision(self):
		self.assertEqual(
			(ASSIGN_FIELD_ALLOWED_FILE, ASSIGN_FIELD_ALLOWED_FUNCTION), (AUTHORITY_FILE, "_assigned_by_other")
		)
		self.assertIn("_assign", self.sources[AUTHORITY_FILE])
		self.assertEqual(check_no_assign_column_for_decisions(self.sources), [])

	def test_route_module_bypass_rules_apply(self):
		route_only = {ROUTE_FILE: self.sources[ROUTE_FILE]}
		self.assertTrue(ROUTE_FILE.startswith(TOOLS_PREFIX))
		self.assertEqual(check_tools_never_bypass_permissions(route_only), [])
		self.assertEqual(check_no_share_bypass(route_only), [])

	def test_feature_never_assigns_sla_dates(self):
		self.assertGreater(len(only_python(scoped(self.sources, AGENT_PREFIX))), 0)
		self.assertEqual(check_feature_never_assigns_sla_dates(self.sources), [])

	def test_no_default_people_in_agent_python(self):
		self.assertIn("Việt Nam", self.sources["agent/prompts.py"])  # the coincidence the scan must tolerate
		self.assertEqual(check_no_default_people_in_agent_python(self.sources), [])


# ---------------------------------------------------------------------------------------------------
# Tests of the scanners themselves (STD-TEST-8): violating code is caught, clean code is not flagged
# ---------------------------------------------------------------------------------------------------

ENQUEUE_GOOD_KEYWORDS = "queue='long', timeout=1, enqueue_after_commit=True, job_id='j', deduplicate=True"


class TestScannersCatchViolations(unittest.TestCase):
	def assertCaught(self, violations, *fragments):
		self.assertGreater(len(violations), 0, "scanner missed the violation")
		for fragment in fragments:
			self.assertTrue(any(fragment in text for text in violations), f"{fragment!r} not in {violations}")

	# layer imports -----------------------------------------------------------------------------

	def test_layer_imports_catches_each_forbidden_direction(self):
		cases = {
			"gateway/cost.py": "from erp_ai.agent import policy\n",
			"gateway/__init__.py": "from erp_ai import eval\n",
			"agent/policy.py": "from erp_ai.eval import run_eval\n",
			"agent/runner.py": "import erp_ai.handlers\n",
			"agent/tools/read.py": "from erp_ai import gateway\n",
			"agent/tools/registry.py": "from erp_ai.agent.runner import run_for_ticket\n",
			"agent/tools/write_ticket.py": "from erp_ai.agent import runner\n",
			"handlers.py": "from erp_ai.gateway import call_model\n",
			"gateway/breaker.py": "from erp_ai.erp_ai_agent.doctype.erp_ai_setting import erp_ai_setting\n",
			"agent/authority.py": "from erp_ai.erp_ai_agent import doctype\n",
			"ticket_panel.py": "from erp_ai.gateway import call_model\n",
			"gateway/cache.py": "from erp_ai import ticket_panel\n",
			"agent/context.py": "from erp_ai.ticket_panel import get_panel_data\n",
		}
		for rel, source in cases.items():
			with self.subTest(rel=rel):
				rel = rel.partition("#")[0]
				self.assertCaught(check_layer_imports({rel: source}), rel)

	def test_layer_imports_catches_changes_directions(self):
		forbidden_from_changes = (
			"erp_ai.gateway",
			"erp_ai.agent.runner",
			"erp_ai.agent.run_status",
			"erp_ai.eval",
			"erp_ai.handlers",
			"erp_ai.tasks",
			"erp_ai.install",
			"erp_ai.erp_ai_agent",
		)
		for target in forbidden_from_changes:
			with self.subTest(target=target):
				source = f"import {target}.x\n"
				self.assertCaught(check_layer_imports({"agent/changes/transitions.py": source}), target)
		for rel in ("agent/tools/propose_change.py", "agent/tools/change_guard.py"):
			with self.subTest(rel=rel):
				source = "from erp_ai.agent.changes import transitions\n"
				self.assertCaught(check_layer_imports({rel: source}), "erp_ai.agent.changes")
		allowed = {
			"agent/changes/transitions.py": (
				"from erp_ai.agent.run_log import write_entry\nfrom erp_ai.constants import PROPOSAL_DOCTYPE\n"
			),
			"agent/changes/apply_job.py": (
				"from erp_ai.agent import policy, queue\nfrom erp_ai.agent.changes import transitions\n"
				"from erp_ai.agent.tools import change_guard, source\nfrom erp_ai.agent import change_text\n"
			),
			"erp_ai_agent/doctype/erp_ai_change_proposal/erp_ai_change_proposal.py": (
				"from erp_ai.agent.changes import transitions\n"
			),
		}
		self.assertEqual(check_layer_imports(allowed), [])

	def test_layer_imports_catches_lazy_and_relative_imports(self):
		lazy = "def f():\n\tfrom erp_ai.agent.runner import run_for_ticket\n"
		self.assertCaught(check_layer_imports({"handlers.py": lazy}), "erp_ai.agent.runner")
		relative = "from ... import gateway\n"
		self.assertCaught(check_layer_imports({"agent/tools/read.py": relative}), "erp_ai.gateway")
		sibling = "from .. import runner\n"
		self.assertCaught(check_layer_imports({"agent/tools/read.py": sibling}), "erp_ai.agent.runner")

	def test_layer_imports_allows_permitted_directions(self):
		allowed = {
			"eval/run_eval.py": "from erp_ai.agent.runner import CLASSIFY_MAX_TOKENS\nfrom erp_ai import gateway\n",
			"agent/runner.py": "from erp_ai import gateway\nfrom erp_ai.agent.tools.registry import execute_tool\n",
			"tasks.py": "from erp_ai import alerts, gateway\n",
			"handlers.py": "from erp_ai.agent import policy\nfrom erp_ai.agent.queue import enqueue_agent_run\n",
			"agent/tools/read.py": "from erp_ai.agent import authority, policy, prompts\n",
			"gateway/__init__.py": "from erp_ai import alerts\nfrom erp_ai.gateway import breaker\n",
		}
		self.assertEqual(check_layer_imports(allowed), [])

	def test_import_boundaries_catch_anthropic_and_other_apps(self):
		self.assertCaught(check_import_boundaries({"agent/runner.py": "import anthropic\n"}), "anthropic")
		self.assertCaught(
			check_import_boundaries({"gateway/__init__.py": "from anthropic import Anthropic\n"})
		)
		self.assertCaught(
			check_import_boundaries({"agent/runner.py": "import workflowcore.x\n"}), "workflowcore"
		)
		self.assertEqual(check_import_boundaries({CLIENT_FILE: "import anthropic\n"}), [])

	def test_import_boundaries_allowlist_catches_any_other_top_level_module(self):
		cases = {
			"erpnext": "import erpnext\n",
			"telephony": "from telephony.x import y\n",
			"hrms": "import hrms\n",
			"requests": "import requests.adapters\n",
			"erpnext.stock": "def f():\n\tfrom erpnext import stock\n",
		}
		for fragment, source in cases.items():
			with self.subTest(fragment=fragment):
				self.assertCaught(check_import_boundaries({"agent/runner.py": source}), fragment)

	def test_import_boundaries_allowlist_accepts_stdlib_frappe_helpdesk_and_relative(self):
		clean = (
			"from __future__ import annotations\n"
			"import json\nimport os.path\nfrom datetime import datetime\n"
			"import frappe\nfrom frappe.utils import now\nfrom helpdesk.helpdesk.doctype import hd_ticket\n"
			"from erp_ai import alerts\nfrom . import policy\nfrom .prompts import build\n"
		)
		self.assertEqual(check_import_boundaries({"agent/runner.py": clean}), [])

	# enqueue -----------------------------------------------------------------------------------

	def test_single_enqueue_catches_calls_aliases_and_enqueue_doc(self):
		for source in (
			"import frappe\nfrappe.enqueue('x')\n",
			"import frappe\nfrappe.enqueue_doc('HD Ticket', 'T')\n",
			"from frappe import enqueue\nenqueue('x')\n",
			"import frappe\njob = frappe.enqueue\n",
		):
			with self.subTest(source=source):
				self.assertCaught(check_single_enqueue_site({"handlers.py": source}))

	def test_single_enqueue_allows_queue_module_and_wrapper_calls(self):
		sources = {
			QUEUE_FILE: "import frappe\nfrappe.enqueue('x')\n",
			"handlers.py": "from erp_ai.agent.queue import enqueue_agent_run\nenqueue_agent_run('T', 'ticket_insert')\n",
		}
		self.assertEqual(check_single_enqueue_site(sources), [])

	def test_enqueue_targets_pinned(self):
		self.assertEqual(
			ENQUEUE_TARGETS,
			("erp_ai.agent.runner.run_for_ticket", "erp_ai.agent.changes.apply_job.run_change"),
		)

	@staticmethod
	def enqueue_call(target: str, keywords: str = ENQUEUE_GOOD_KEYWORDS) -> str:
		return f"frappe.enqueue({target!r}, {keywords})\n"

	def test_enqueue_call_shape_accepts_runner_and_change_job(self):
		good = "import frappe\n" + "".join(self.enqueue_call(target) for target in ENQUEUE_TARGETS)
		self.assertEqual(check_enqueue_call_shape({QUEUE_FILE: good}), [])

	def test_enqueue_call_shape_requires_exactly_two_calls(self):
		runner, change = (self.enqueue_call(target) for target in ENQUEUE_TARGETS)
		for label, body in (("one", runner), ("three", runner + change + change)):
			with self.subTest(calls=label):
				self.assertCaught(
					check_enqueue_call_shape({QUEUE_FILE: "import frappe\n" + body}), "exactly two"
				)

	def test_enqueue_call_shape_requires_each_target_once(self):
		for target in ENQUEUE_TARGETS:
			with self.subTest(target=target):
				body = "import frappe\n" + self.enqueue_call(target) * 2
				violations = check_enqueue_call_shape({QUEUE_FILE: body})
				self.assertCaught(violations, "each of")
				self.assertFalse(any("first argument" in text for text in violations), violations)

	def test_enqueue_call_shape_rejects_target_outside_set(self):
		runner = self.enqueue_call(ENQUEUE_TARGETS[0])
		for bad in ("erp_ai.other.fn", "erp_ai.agent.changes.apply_job", "erp_ai.agent.runner.run"):
			with self.subTest(target=bad):
				body = "import frappe\n" + runner + self.enqueue_call(bad)
				self.assertCaught(check_enqueue_call_shape({QUEUE_FILE: body}), "first argument")
		not_literal = "import frappe\n" + runner + f"frappe.enqueue(TARGET, {ENQUEUE_GOOD_KEYWORDS})\n"
		self.assertCaught(check_enqueue_call_shape({QUEUE_FILE: not_literal}), "first argument")

	def test_enqueue_call_shape_requires_five_parameters_on_each_call(self):
		for index, target in enumerate(ENQUEUE_TARGETS):
			for name in ENQUEUE_REQUIRED_KEYWORDS:
				with self.subTest(target=target, missing=name):
					keywords = ", ".join(
						part for part in ENQUEUE_GOOD_KEYWORDS.split(", ") if not part.startswith(f"{name}=")
					)
					calls = [self.enqueue_call(other) for other in ENQUEUE_TARGETS]
					calls[index] = self.enqueue_call(target, keywords)
					violations = check_enqueue_call_shape({QUEUE_FILE: "import frappe\n" + "".join(calls)})
					self.assertCaught(violations, f"missing keyword {name}=")
					self.assertEqual(len(violations), 1, violations)

	# no save on configuration ------------------------------------------------------------------

	def test_no_save_catches_setting_and_credential_saves(self):
		cases = (
			"import frappe\ns = frappe.get_doc('ERP AI Setting')\ns.save()\n",
			"import frappe\nfrappe.get_single('ERP AI Setting').save()\n",
			"import frappe\nfrom erp_ai.constants import SETTING_DOCTYPE\nd = frappe.get_cached_doc(SETTING_DOCTYPE)\nd.save()\n",
			"import frappe\nc = frappe.new_doc('ERP AI Credential')\nc.save(ignore_permissions=True)\n",
			"import frappe\nfrom erp_ai import constants\nd = frappe.get_doc(constants.SETTING_DOCTYPE)\nd.save()\n",
			"import frappe\nd = frappe.get_doc({'doctype': 'ERP AI Credential', 'label': 'x'})\nd.save()\n",
			"import frappe\nd = frappe.get_doc(doctype='ERP AI Credential')\nd.save()\n",
			"import frappe\nfrappe.get_doc({'doctype': CREDENTIAL_DOCTYPE}).save()\n",
			"def f(settings):\n\tsettings.save()\n",
		)
		for source in cases:
			with self.subTest(source=source):
				self.assertCaught(check_no_save_on_config({"tasks.py": source}), "ADR-004")
		controller = "class ERPAISetting:\n\tdef x(self):\n\t\tself.save()\n"
		self.assertCaught(check_no_save_on_config({CONFIG_CONTROLLER_FILES[0]: controller}), "ADR-004")

	def test_no_save_allows_other_documents_and_set_value(self):
		source = (
			"import frappe\n"
			"ticket = frappe.get_doc('HD Ticket', 'T')\n"
			"ticket.save()\n"
			"frappe.db.set_value('ERP AI Credential', 'row', {'status': 'x'})\n"
		)
		self.assertEqual(check_no_save_on_config({"agent/tools/write_ticket.py": source}), [])

	# tools never bypass permissions ------------------------------------------------------------

	def test_tools_bypass_catches_every_forbidden_call(self):
		cases = (
			"import frappe\nframe = frappe.get_doc('HD Ticket', 'T').save(ignore_permissions=True)\n",
			"import frappe\nfrappe.flags.ignore_permissions = True\n",
			"import frappe\nfrappe.db.set_value('HD Ticket', 'T', 'status', 'Open')\n",
			"import frappe\nfrappe.db.sql('UPDATE `tabHD Ticket` SET status = 1')\n",
			"import frappe\nfrappe.db.sql(query)\n",
			"import frappe\nfrappe.db.sql('SELECT 1; UPDATE `tabHD Ticket` SET status = 1')\n",
			"import frappe\nfrappe.set_user('Administrator')\n",
			"import frappe\nfrappe.get_all('HD Ticket', fields=['name'])\n",
			"import frappe\nfrappe.db.get_all('HD Ticket')\n",
			"def f(doc):\n\tdoc.db_update()\n",
		)
		for source in cases:
			with self.subTest(source=source):
				self.assertCaught(check_tools_never_bypass_permissions({"agent/tools/read.py": source}))

	def test_tools_bypass_allows_get_list_read_sql_and_doctype_metadata(self):
		source = (
			"import frappe\n"
			"frappe.get_list('HD Ticket', fields=['name'])\n"
			"frappe.db.sql('SELECT name FROM `tabHD Ticket`')\n"
			"frappe.get_all('DocType', {'module': 'ERP AI agent'}, pluck='name')\n"
		)
		self.assertEqual(check_tools_never_bypass_permissions({"agent/tools/read.py": source}), [])

	def test_tools_bypass_ignores_code_outside_tools(self):
		source = "import frappe\nfrappe.db.set_value('X', 'y', 'z', 1)\nfrappe.get_all('X')\n"
		self.assertEqual(check_tools_never_bypass_permissions({"agent/runner.py": source}), [])

	# subprocess --------------------------------------------------------------------------------

	def test_subprocess_catches_imports_and_os_shell(self):
		for source in (
			"import subprocess\n",
			"from subprocess import run\n",
			"import os\nos.system('ls')\n",
			"import os\nos.popen('ls')\n",
		):
			with self.subTest(source=source):
				self.assertCaught(check_subprocess_only_in_source_tool({"agent/runner.py": source}))
		self.assertEqual(
			check_subprocess_only_in_source_tool(
				{SOURCE_TOOL_FILE: "import subprocess\nsubprocess.run(['git'])\n"}
			),
			[],
		)

	def test_subprocess_catches_aliased_imports_and_more_os_exec_names(self):
		for source in (
			"import subprocess as sp\nsp.run(['ls'])\n",
			"from subprocess import run as r\nr(['ls'])\n",
			"import os\nos.posix_spawn('a', ['a'], {})\n",
			"import os\nos.execvpe('a', ['a'], {})\n",
			"import os\nos.spawnlp(os.P_WAIT, 'a', 'a')\n",
			"from os import system\nsystem('ls')\n",
			"import os as o\no.system('ls')\n",
		):
			with self.subTest(source=source):
				self.assertCaught(
					check_subprocess_only_in_source_tool({"agent/runner.py": source}), "outside"
				)

	def test_subprocess_call_shape_checks_aliased_calls(self):
		for source in (
			"import subprocess as sp\nsp.run(['git'])\n",
			"from subprocess import run\nrun(['git'])\n",
			"from subprocess import check_output as co\nco('git log', timeout=3)\n",
		):
			with self.subTest(source=source):
				self.assertCaught(check_subprocess_call_shape({SOURCE_TOOL_FILE: source}))
		good = "from subprocess import run\nrun(['git'], timeout=3)\n"
		self.assertEqual(check_subprocess_call_shape({SOURCE_TOOL_FILE: good}), [])

	def test_subprocess_call_shape_requires_timeout_list_and_no_shell(self):
		good = "import subprocess\nsubprocess.run(['git', 'log'], timeout=30, capture_output=True)\n"
		self.assertEqual(check_subprocess_call_shape({SOURCE_TOOL_FILE: good}), [])
		cases = {
			"timeout=": "import subprocess\nsubprocess.run(['git'])\n",
			"shell=": "import subprocess\nsubprocess.run(['git'], timeout=3, shell=True)\n",
			"string command": "import subprocess\nsubprocess.run('git log', timeout=3)\n",
			"only run()": "import subprocess\nsubprocess.Popen(['git'], timeout=3)\n",
		}
		for fragment, source in cases.items():
			with self.subTest(fragment=fragment):
				self.assertCaught(check_subprocess_call_shape({SOURCE_TOOL_FILE: source}), fragment)

	def test_subprocess_call_shape_timeout_wrapped_git_needs_group_cwd_and_own_env(self):
		head = "import os\nimport subprocess\nsubprocess.run([TIMEOUT_EXECUTABLE, '-s', 'KILL', '5', 'git'], timeout=10"
		good = f"{head}, cwd=repo, env=git_env(identity=False), start_new_session=True)\n"
		self.assertEqual(check_subprocess_call_shape({SOURCE_TOOL_FILE: good}), [])
		literal = good.replace("TIMEOUT_EXECUTABLE", "'timeout'")
		self.assertEqual(check_subprocess_call_shape({SOURCE_TOOL_FILE: literal}), [])
		cases = (
			("without start_new_session=True", f"{head}, cwd=repo, env=git_env(identity=False))\n"),
			(
				"without start_new_session=True",
				f"{head}, cwd=repo, env=git_env(identity=False), start_new_session=False)\n",
			),
			("without cwd=", f"{head}, env=git_env(identity=False), start_new_session=True)\n"),
			("without env=", f"{head}, cwd=repo, start_new_session=True)\n"),
			("env= uses os.environ", f"{head}, cwd=repo, env={{**os.environ}}, start_new_session=True)\n"),
			("env= uses os.environ", f"{head}, cwd=repo, env=dict(os.environ), start_new_session=True)\n"),
			("env= uses os.environ", f"{head}, cwd=repo, env=os.environ, start_new_session=True)\n"),
		)
		for fragment, source in cases:
			for variant in (source, source.replace("TIMEOUT_EXECUTABLE", "'timeout'")):
				with self.subTest(variant=variant):
					self.assertCaught(check_subprocess_call_shape({SOURCE_TOOL_FILE: variant}), fragment)
		plain_git = (
			"import os\nimport subprocess\nsubprocess.run(['git', 'log'], timeout=3, env={**os.environ})\n"
		)
		self.assertEqual(check_subprocess_call_shape({SOURCE_TOOL_FILE: plain_git}), [])

	def test_subprocess_allowed_in_process_runner_only_besides_source_tool(self):
		self.assertEqual(SUBPROCESS_FILES, ("agent/tools/source.py", "agent/changes/process_runner.py"))
		allowed = "import subprocess\nsubprocess.run(['bench'], timeout=3)\n"
		self.assertEqual(check_subprocess_only_in_source_tool({PROCESS_RUNNER_FILE: allowed}), [])
		for rel in ("agent/changes/apply_job.py", "agent/changes/file_writer.py", "agent/changes/runner.py"):
			with self.subTest(rel=rel):
				self.assertCaught(check_subprocess_only_in_source_tool({rel: allowed}), "outside")

	def test_subprocess_call_shape_applies_to_process_runner(self):
		head = (
			"import os\nimport subprocess\n"
			"subprocess.run([TIMEOUT_EXECUTABLE, '-s', 'KILL', '5', BENCH_EXECUTABLE], timeout=35"
		)
		good = f"{head}, cwd=get_bench_path(), env=_minimal_env(), start_new_session=True)\n"
		self.assertEqual(check_subprocess_call_shape({SOURCE_TOOL_FILE: "", PROCESS_RUNNER_FILE: good}), [])
		bench_first = (
			"import subprocess\nsubprocess.run([source.TIMEOUT_EXECUTABLE, '-s', 'KILL', '5', 'bench'], "
			"timeout=35, cwd=root, env=_minimal_env(), start_new_session=True)\n"
		)
		self.assertEqual(
			check_subprocess_call_shape({SOURCE_TOOL_FILE: "", PROCESS_RUNNER_FILE: bench_first}), []
		)
		cases = (
			(
				"without timeout=",
				"import subprocess\nsubprocess.run(['bench'], cwd=r, env={}, start_new_session=True)\n",
			),
			("with shell=", f"{head}, cwd=r, env={{}}, start_new_session=True, shell=True)\n"),
			(
				"string command",
				"import subprocess\nsubprocess.run('bench migrate', timeout=3, cwd=r, env={}, start_new_session=True)\n",
			),
			(
				"only run()",
				"import subprocess\nsubprocess.Popen(['bench'], timeout=3, cwd=r, env={}, start_new_session=True)\n",
			),
			("without start_new_session=True", f"{head}, cwd=r, env=_minimal_env())\n"),
			(
				"without start_new_session=True",
				f"{head}, cwd=r, env=_minimal_env(), start_new_session=False)\n",
			),
			("without cwd=", f"{head}, env=_minimal_env(), start_new_session=True)\n"),
			("without env=", f"{head}, cwd=r, start_new_session=True)\n"),
			("env= uses os.environ", f"{head}, cwd=r, env={{**os.environ}}, start_new_session=True)\n"),
			("env= uses os.environ", f"{head}, cwd=r, env=dict(os.environ), start_new_session=True)\n"),
			("env= uses os.environ", f"{head}, cwd=r, env=os.environ, start_new_session=True)\n"),
			(
				"without start_new_session=True",
				"import subprocess\nsubprocess.run(['bench'], timeout=3, cwd=r, env={})\n",
			),
			(
				"without cwd=",
				"import subprocess\nsubprocess.run(['bench'], timeout=3, env={}, start_new_session=True)\n",
			),
			(
				"env= uses os.environ",
				"import os\nimport subprocess\nsubprocess.run(['bench'], timeout=3, cwd=r, env=os.environ, start_new_session=True)\n",
			),
		)
		for fragment, source in cases:
			with self.subTest(fragment=fragment, source=source):
				violations = check_subprocess_call_shape({SOURCE_TOOL_FILE: "", PROCESS_RUNNER_FILE: source})
				self.assertCaught(violations, fragment)
				self.assertTrue(all(text.startswith(PROCESS_RUNNER_FILE) for text in violations), violations)
		plain = (
			"import os\nimport subprocess\nsubprocess.run(['git', 'log'], timeout=3, env={**os.environ})\n"
		)
		self.assertEqual(check_subprocess_call_shape({SOURCE_TOOL_FILE: plain}), [])
		self.assertCaught(
			check_subprocess_call_shape({SOURCE_TOOL_FILE: "", PROCESS_RUNNER_FILE: plain}),
			"env= uses os.environ",
			"without cwd=",
			"without start_new_session=True",
		)

	def test_subprocess_call_shape_accepts_git_writes_in_process_runner(self):
		"""ADR-022 QĐ 2, 4: the git add/commit/rm call of process_runner.py passes the shape rule."""
		head = (
			"import subprocess\nsubprocess.run([source.TIMEOUT_EXECUTABLE, '-s', 'KILL', '5', 'git', "
			"*source.git_global_options(read=False), 'add', '--', rel], timeout=10, cwd=repo_root"
		)
		good = f"{head}, env=source.git_env(identity=True), start_new_session=True)\n"
		self.assertEqual(check_subprocess_call_shape({SOURCE_TOOL_FILE: "", PROCESS_RUNNER_FILE: good}), [])
		self.assertEqual(check_subprocess_only_in_source_tool({PROCESS_RUNNER_FILE: good}), [])
		cases = (
			("without start_new_session=True", f"{head}, env=source.git_env(identity=True))\n"),
			("without env=", f"{head}, start_new_session=True)\n"),
			(
				"env= uses os.environ",
				f"import os\n{head}, env={{**os.environ, **source.git_env(identity=True)}}, start_new_session=True)\n",
			),
		)
		for fragment, source in cases:
			with self.subTest(fragment=fragment):
				self.assertCaught(
					check_subprocess_call_shape({SOURCE_TOOL_FILE: "", PROCESS_RUNNER_FILE: source}), fragment
				)

	def test_subprocess_call_shape_checks_run_wrapped_callers_in_process_runner(self):
		"""Design 8.2 "env= không chứa os.environ": process_runner.py builds cwd=/env= in its
		`_run_wrapped(...)` callers, so each caller gets the same cwd=/env= checks as subprocess.run."""
		head = "import os\nimport subprocess\n_run_wrapped(['git', 'add', '--', rel], limit_s=5"
		for env in ("source.git_env(identity=True)", "_minimal_env()"):
			good = f"{head}, cwd=repo_root, env={env}, backstop_s=5, max_lines=20)\n"
			with self.subTest(good=good):
				self.assertEqual(
					check_subprocess_call_shape({SOURCE_TOOL_FILE: "", PROCESS_RUNNER_FILE: good}), []
				)
		cases = (
			("_run_wrapped without cwd=", f"{head}, env=_minimal_env())\n"),
			("_run_wrapped without env=", f"{head}, cwd=repo_root)\n"),
			("_run_wrapped without env=", f"{head}, **options)\n"),
			("_run_wrapped env= uses os.environ", f"{head}, cwd=repo_root, env=os.environ)\n"),
			("_run_wrapped env= uses os.environ", f"{head}, cwd=repo_root, env=dict(os.environ))\n"),
			(
				"_run_wrapped env= uses os.environ",
				f"{head}, cwd=repo_root, env={{**os.environ, **source.git_env(identity=True)}})\n",
			),
			(
				"_run_wrapped env= uses os.environ",
				"from os import environ\n_run_wrapped(['bench'], cwd=r, env=dict(environ), limit_s=5)\n",
			),
		)
		for fragment, source in cases:
			with self.subTest(fragment=fragment, source=source):
				violations = check_subprocess_call_shape({SOURCE_TOOL_FILE: "", PROCESS_RUNNER_FILE: source})
				self.assertCaught(violations, fragment)
				self.assertTrue(all(text.startswith(PROCESS_RUNNER_FILE) for text in violations), violations)
		elsewhere = f"{head}, cwd=repo_root, env=os.environ)\n"
		self.assertEqual(check_subprocess_call_shape({SOURCE_TOOL_FILE: elsewhere}), [])

	# policy fields -----------------------------------------------------------------------------

	def test_policy_fields_caught_outside_policy_and_allowed_inside(self):
		cases = (
			"def f(settings):\n\treturn settings.permission_level\n",
			"import frappe\nfrappe.db.get_single_value('ERP AI Setting', 'permission_level')\n",
			"import frappe\nfrappe.db.get_single_value('ERP AI Setting', 'excluded_teams')\n",
			"def f(ticket):\n\treturn ticket.ai_opt_out\n",
			"def f(ticket):\n\treturn ticket.get('ai_opt_out')\n",
			"def f(settings):\n\treturn settings.code_change_enabled\n",
			"import frappe\nfrappe.db.get_single_value('ERP AI Setting', 'code_change_apps')\n",
		)
		for source in cases:
			with self.subTest(source=source):
				self.assertCaught(check_policy_fields_only_in_policy({"agent/tools/read.py": source}))
		inside = "def f(settings):\n\treturn settings.permission_level\n"
		self.assertEqual(check_policy_fields_only_in_policy({POLICY_FILE: inside}), [])
		prose = "def f():\n\t'''The only reader of permission_level.'''\n"
		self.assertEqual(check_policy_fields_only_in_policy({"handlers.py": prose}), [])

	# handlers ----------------------------------------------------------------------------------

	def test_handlers_import_check_catches_gateway_runner_and_allows_policy_queue(self):
		for source in (
			"from erp_ai import gateway\n",
			"import erp_ai.gateway.client\n",
			"from erp_ai.agent import runner\n",
			"def f():\n\tfrom erp_ai.agent.runner import run_for_ticket\n",
		):
			with self.subTest(source=source):
				self.assertCaught(check_handlers_imports({HANDLERS_FILE: source}))
		clean = "from erp_ai.agent import policy\nfrom erp_ai.agent.queue import enqueue_agent_run\n"
		self.assertEqual(check_handlers_imports({HANDLERS_FILE: clean}), [])
		self.assertEqual(check_handlers_imports({"tasks.py": "from erp_ai import gateway\n"}), [])

	# secrets -----------------------------------------------------------------------------------

	def test_secret_handling_catches_password_reads_and_key_logging(self):
		cases = {
			"get_decrypted_password": "from frappe.utils.password import get_decrypted_password\n",
			"get_password": "def f(doc):\n\treturn doc.get_password('api_key')\n",
			"api_key": "import frappe\ndef f(api_key):\n\tfrappe.logger('x').warning('key %s', api_key)\n",
			"password": "def f(row):\n\tprint(f'{row.password}')\n",
			"token": "import frappe\ndef f(token):\n\tfrappe.log_error('t', token)\n",
			"with_context": "import frappe\nfrappe.get_traceback(with_context=True)\n",
		}
		for fragment, source in cases.items():
			with self.subTest(fragment=fragment):
				self.assertCaught(check_secret_handling({"gateway/__init__.py": source}), fragment)

	def test_secret_handling_catches_log_error_without_explicit_message(self):
		cases = (
			"import frappe\nfrappe.log_error(TITLE)\n",
			"import frappe\nfrappe.log_error(title=T)\n",
			"import frappe\nfrappe.log_error()\n",
			"from frappe import log_error\nlog_error(TITLE)\n",
			"import frappe\nfrappe.log_error(TITLE, '')\n",
			"import frappe\nfrappe.log_error(TITLE, message=None)\n",
		)
		for source in cases:
			with self.subTest(source=source):
				self.assertCaught(check_secret_handling({"tasks.py": source}), "log_error")

	def test_secret_handling_allows_log_error_with_explicit_message(self):
		safe = (
			"import frappe\n"
			"frappe.log_error(TITLE, 'msg')\n"
			"frappe.log_error(TITLE, f'error={type(exc).__name__}')\n"
			"frappe.log_error(title=T, message='m')\n"
			"frappe.log_error(TITLE, message=text)\n"
		)
		self.assertEqual(check_secret_handling({"tasks.py": safe}), [])

	def test_secret_handling_allows_credentials_module_and_label_logging(self):
		reader = "from frappe.utils.password import get_decrypted_password\nget_decrypted_password('a', 'b', 'api_key')\n"
		self.assertEqual(check_secret_handling({CREDENTIALS_FILE: reader}), [])
		safe = (
			"import frappe\n"
			"def f(row, exc):\n"
			"\tfrappe.logger('x').warning('key=%s %s', row.label, type(exc).__name__)\n"
			"\tfrappe.get_traceback(with_context=False)\n"
		)
		self.assertEqual(check_secret_handling({"gateway/__init__.py": safe}), [])

	# legacy comment ----------------------------------------------------------------------------

	def test_legacy_comment_names_caught_in_strings_attributes_and_json(self):
		cases = (
			"x = 'HD Ticket Comment'\n",
			"def f(c):\n\treturn c.commented_by\n",
			"def f(c):\n\treturn c['comment_email']\n",
			"fields = ['name', 'comment_by']\n",
			"def f():\n\tcommented_by = 1\n",
			"def f(**kw):\n\tg(comment_email=1)\n",
		)
		for source in cases:
			with self.subTest(source=source):
				self.assertCaught(check_no_legacy_ticket_comment({"agent/authority.py": source}))
		self.assertCaught(check_no_legacy_ticket_comment({"x/y.json": '{"doctype": "HD Ticket Comment"}'}))
		self.assertCaught(check_no_legacy_ticket_comment({"x/y.js": "frm.doc.comment_by"}))

	def test_legacy_comment_allows_hide_list_and_similar_words(self):
		hide = 'COMMENT_HIDDEN_FIELDS = ("comment_email", "comment_by")\n'
		self.assertEqual(check_no_legacy_ticket_comment({READ_TOOL_FILE: hide}), [])
		self.assertCaught(check_no_legacy_ticket_comment({"agent/authority.py": hide}))
		self.assertCaught(check_no_legacy_ticket_comment({READ_TOOL_FILE: "x = 'comment_by'\n" + hide}))
		similar = "owner = 'x'\ncomment_type = 'Comment'\nfields = ['commenter', 'comment_by_x', 'ticket_comment']\n"
		self.assertEqual(check_no_legacy_ticket_comment({"agent/authority.py": similar}), [])

	# CI ----------------------------------------------------------------------------------------

	GOOD_CI = (
		"          bench init --skip-assets --frappe-branch version-15 --python py ~/frappe-bench\n"
		"          bench get-app telephony\n"
		"          bench get-app helpdesk --branch v15.1.0\n"
		"          bench get-app erpnext --branch version-15\n"
		"          bench get-app erp_ai $GITHUB_WORKSPACE\n"
		"          bench --site test_site install-app telephony\n"
		"          bench --site test_site install-app helpdesk\n"
		"          bench --site test_site install-app erpnext\n"
		"          bench --site test_site install-app erp_ai\n"
	)

	def test_ci_check_accepts_complete_workflow(self):
		self.assertEqual(check_ci_workflow(self.GOOD_CI), [])

	def test_ci_check_catches_each_missing_or_wrong_piece(self):
		cases = {
			"bench init": self.GOOD_CI.replace("--frappe-branch version-15 ", ""),
			"bench init ": self.GOOD_CI.replace("--frappe-branch version-15", "--frappe-branch develop"),
			"get-app helpdesk": self.GOOD_CI.replace("--branch v15.1.0", "--branch v15.0.0"),
			"get-app erpnext": self.GOOD_CI.replace("bench get-app erpnext --branch version-15\n", ""),
			"get-app telephony": self.GOOD_CI.replace("bench get-app telephony\n", ""),
			"install-app helpdesk": self.GOOD_CI.replace(
				"          bench --site test_site install-app helpdesk\n", ""
			),
			"install-app erp_ai": self.GOOD_CI.replace("install-app erp_ai", "migrate"),
			"comes after install-app erp_ai": self.GOOD_CI.replace(
				"          bench --site test_site install-app telephony\n", ""
			)
			+ "          bench --site test_site install-app telephony\n",
		}
		for fragment, text in cases.items():
			with self.subTest(fragment=fragment):
				self.assertCaught(check_ci_workflow(text), fragment)

	def test_ci_check_ignores_commented_commands(self):
		commented = self.GOOD_CI.replace("bench get-app erpnext", "# bench get-app erpnext")
		self.assertCaught(check_ci_workflow(commented), "get-app erpnext")

	# Frappe-skipped test file names ------------------------------------------------------------

	def test_frappe_skipped_test_name_check_catches_any_depth(self):
		violating = [
			"agent/test_runner.py",
			"tests/test_runner.py",
			"erp_ai_agent/doctype/x/test_runner.py",
			"test_runner.py",
		]
		clean = [
			"agent/test_agent_runner.py",
			"tests/test_runner_utils.py",
			"agent/runner.py",
			"agent/my_test_runner.py",
		]
		violations = check_no_frappe_skipped_test_files(violating)
		self.assertEqual(len(violations), len(violating))
		for rel in violating:
			self.assertCaught(violations, rel)
		self.assertEqual(check_no_frappe_skipped_test_files(clean), [])

	# status signals and form script (ADR-007, ADR-008) -----------------------------------------

	GOOD_PUBLISH = (
		"import frappe\nfrom frappe.realtime import get_doc_room\n"
		"frappe.publish_realtime('e', message={}, room=get_doc_room('HD Ticket', 'T'), after_commit=False)\n"
	)

	def test_publish_realtime_scanner_catches_violations(self):
		# publish_realtime / frappe.realtime only in run_status.py, with room= and after_commit=False
		self.assertEqual(check_publish_realtime_only_in_run_status({RUN_STATUS_FILE: self.GOOD_PUBLISH}), [])
		for source in (
			"import frappe\nfrappe.publish_realtime('e', room='r', after_commit=False)\n",
			"from frappe import publish_realtime\n",
			"import frappe\nfrappe.publish_progress(1)\n",
			"from frappe.realtime import emit_via_redis\n",
			"import frappe\nfrappe.realtime.get_doc_room('HD Ticket', 'T')\n",
			"from frappe.realtime import get_doc_room\n",
			"import frappe\ngetattr(frappe, 'publish_realtime')('e')\n",
			"import frappe\nfrappe.get_attr('frappe.publish_realtime')('e')\n",
			"import importlib\nimportlib.import_module('frappe.realtime')\n",
			"import frappe as f\nf.realtime.get_doc_room('HD Ticket', 'T')\n",
			"from frappe import realtime as rt\nrt.get_doc_room('HD Ticket', 'T')\n",
		):
			with self.subTest(source=source):
				self.assertCaught(check_publish_realtime_only_in_run_status({"agent/runner.py": source}))
		for fragment, source in {
			"room=": "import frappe\nfrappe.publish_realtime('e', after_commit=False)\n",
			"after_commit=False": "import frappe\nfrappe.publish_realtime('e', room='r')\n",
		}.items():
			with self.subTest(fragment=fragment):
				self.assertCaught(
					check_publish_realtime_only_in_run_status({RUN_STATUS_FILE: source}), fragment
				)
		self.assertCaught(
			check_publish_realtime_only_in_run_status(
				{
					RUN_STATUS_FILE: "import frappe\nfrappe.publish_realtime('e', room='r', after_commit=True)\n"
				}
			),
			"after_commit=False",
		)
		# aliased or rebound publish_realtime inside run_status is still pinned to room= and after_commit=False
		for fragment, source in {
			"room=": "from frappe import publish_realtime as publish\npublish('e', after_commit=False)\n",
			"binds publish_realtime": "from frappe import publish_realtime as publish\n",
		}.items():
			with self.subTest(fragment=fragment, source=source):
				self.assertCaught(
					check_publish_realtime_only_in_run_status({RUN_STATUS_FILE: source}), fragment
				)
		self.assertCaught(
			check_publish_realtime_only_in_run_status(
				{
					RUN_STATUS_FILE: "import frappe\npublish = frappe.publish_realtime\n"
					"publish('e', room='r', after_commit=False)\n"
				}
			),
			"binds publish_realtime",
		)
		self.assertCaught(
			check_publish_realtime_only_in_run_status(
				{RUN_STATUS_FILE: "import frappe as f\nf.publish_realtime('e', room='r')\n"}
			),
			"after_commit=False",
		)

	def test_run_status_import_scanner_catches_violations(self):
		# the status module is imported only by the runner
		for rel, source in {
			"agent/tools/read.py": "from erp_ai.agent import run_status\n",
			"handlers.py": "from erp_ai.agent.run_status import RunStatus\n",
			"tasks.py": "import erp_ai.agent.run_status\n",
			"agent/queue.py": "from . import run_status\n",
			"eval/run_eval.py": "import importlib\nimportlib.import_module('erp_ai.agent.run_status')\n",
		}.items():
			with self.subTest(rel=rel):
				self.assertCaught(check_run_status_imported_only_by_runner({rel: source}), rel)
		self.assertEqual(
			check_run_status_imported_only_by_runner(
				{RUNNER_FILE: "from erp_ai.agent.run_status import RunStatus\n"}
			),
			[],
		)

	def test_run_status_writes_nothing_scanner_catches_violations(self):
		# the status module writes nothing
		for source in (
			"import frappe\nfrappe.db.set_value('X', 'y', 'z', 1)\n",
			"import frappe\nfrappe.delete_doc('X', 'y')\n",
			"import frappe\nfrappe.cache.set_value('k', 1)\n",
			"import frappe\nfrappe.get_doc({}).insert()\n",
			"def f(doc):\n\tdoc.save()\n",
			"def f():\n\twith open('x', 'w') as handle:\n\t\thandle.write('1')\n",
			"from erp_ai.gateway import call_model\n",
			"import frappe\nfrappe.db.commit()\n",
		):
			with self.subTest(source=source):
				self.assertCaught(check_run_status_writes_nothing({RUN_STATUS_FILE: source}))
		# no banned write name is called here: only the frappe.cache / frappe.db attribute rule catches these
		for fragment, source in (
			("uses frappe.cache", "import frappe\nfrappe.cache.hset('k', 'f', 1)\n"),
			("uses frappe.cache", "import frappe\nfrappe.cache.get_value('k')\n"),
			("uses frappe.db", "import frappe\nfrappe.db.set_single_value('X', 'f', 1)\n"),
			("uses frappe.cache", "import frappe as f\nf.cache.hset('k', 'f', 1)\n"),
			("uses frappe.db", "from frappe import db\ndb.set_single_value('X', 'f', 1)\n"),
			("uses frappe.cache", "from frappe import cache\ncache().hset('k', 'f', 1)\n"),
		):
			with self.subTest(fragment=fragment, source=source):
				self.assertCaught(check_run_status_writes_nothing({RUN_STATUS_FILE: source}), fragment)
		clean = self.GOOD_PUBLISH + "def f(errors):\n\terrors.append('x')\n"
		self.assertEqual(check_run_status_writes_nothing({RUN_STATUS_FILE: clean}), [])
		self.assertEqual(check_run_status_writes_nothing({"agent/runner.py": "def f(d):\n\td.save()\n"}), [])

	def test_document_room_scanner_catches_violations(self):
		# no open_doc: room, no room "all", no publish without a document room
		for rel, source in {
			"agent/runner.py": "room = 'open_doc:HD Ticket/T'\n",
			"x/y.js": "socket.emit('open_doc:HD Ticket')",
			RUN_STATUS_FILE: "import frappe\nfrappe.publish_realtime('e', room='all', after_commit=False)\n",
			"tasks.py": "import frappe\nfrappe.publish_realtime('e', after_commit=False)\n",
			"handlers.py": "import frappe\nfrappe.publish_realtime('e', room=None)\n",
			"agent/queue.py": "from frappe import publish_realtime as publish\npublish('e', after_commit=False)\n",
			"agent/policy.py": "import frappe as f\nf.publish_realtime('e', after_commit=False)\n",
			"agent/tools/read.py": "import frappe\nROOM = 'all'\n"
			"frappe.publish_realtime('e', room=ROOM, after_commit=False)\n",
		}.items():
			with self.subTest(rel=rel):
				self.assertCaught(check_no_open_doc_or_all_room({rel: source}), rel)
		self.assertEqual(check_no_open_doc_or_all_room({RUN_STATUS_FILE: self.GOOD_PUBLISH}), [])

	def test_form_script_scanner_catches_violations(self):
		# HD Form Script only in install.py
		for rel, source in {
			"agent/runner.py": "import frappe\nfrappe.get_doc('HD Form Script', 'x')\n",
			"tasks.py": "DT = 'HD Form Script'\n",
			"x/y.json": '{"doctype": "HD Form Script"}',
			"x/y.html": "<p>HD Form Script</p>",
			"handlers.py": "from helpdesk.helpdesk.doctype.hd_form_script import hd_form_script\n",
		}.items():
			with self.subTest(rel=rel):
				self.assertCaught(check_form_script_only_in_install({rel: source}), rel)
		self.assertEqual(check_form_script_only_in_install({INSTALL_FILE: "DT = 'HD Form Script'\n"}), [])

	def test_hooks_scanner_catches_violations(self):
		# hooks.py injects nothing into the page
		for fragment, source in {
			"app_include_js": "app_include_js = '/assets/erp_ai/js/agent_status_indicator.js'\n",
			"web_include_js": "web_include_js = ['x.js']\n",
			"app_include_css": "app_include_css = 'x.css'\n",
			"after_request": "after_request = ['erp_ai.x.inject']\n",
			"website_route_rules": "website_route_rules = [{'from_route': '/helpdesk/<path:app_path>', 'to_route': 'x'}]\n",
			"fixtures": "fixtures = [{'dt': 'HD Form Script'}]\n",
			"status script": "doc_events = {'x': 'agent_status_indicator'}\n",
		}.items():
			with self.subTest(fragment=fragment):
				self.assertCaught(check_hooks_have_no_page_injection({HOOKS_FILE: source}), fragment)
		self.assertCaught(
			check_hooks_have_no_page_injection({HOOKS_FILE: f"x = '{AGENT_STATUS_SCRIPT_NAME}'\n"}),
			"references the status script",
		)
		hooks_ok = (
			"fixtures = [{'dt': 'Custom Field'}]\n"
			"website_route_rules = [{'from_route': '/a', 'to_route': 'b'}]\n"
			"# app_include_js = '/assets/erp_ai/js/x.js'\n"
			"before_uninstall = 'erp_ai.install.before_uninstall'\n"
		)
		self.assertEqual(check_hooks_have_no_page_injection({HOOKS_FILE: hooks_ok}), [])

	def test_install_scanner_catches_violations(self):
		# install.py has exactly one delete: delete_doc of the status script in before_uninstall
		good_install = (
			"import frappe\n"
			"FORM_SCRIPT_DOCTYPE = 'HD Form Script'\n"
			"AGENT_STATUS_SCRIPT = 'ERP AI Agent Status'\n"
			"def before_uninstall():\n"
			"\tfrappe.delete_doc(FORM_SCRIPT_DOCTYPE, AGENT_STATUS_SCRIPT, ignore_permissions=True)\n"
		)
		self.assertEqual(check_install_deletes_only_status_script({INSTALL_FILE: good_install}), [])
		moved_outside = (
			"import frappe\n"
			"FORM_SCRIPT_DOCTYPE = 'HD Form Script'\n"
			"AGENT_STATUS_SCRIPT = 'ERP AI Agent Status'\n"
			"def before_uninstall():\n"
			"\tpass\n"
			"def ensure_setup():\n"
			"\tfrappe.delete_doc(FORM_SCRIPT_DOCTYPE, AGENT_STATUS_SCRIPT, ignore_permissions=True)\n"
		)
		for fragment, source in (
			("found 0", good_install.replace("frappe.delete_doc(", "print(")),
			("found 2", good_install + "\tfrappe.delete_doc('ToDo', 'x')\n"),
			("outside before_uninstall", moved_outside),
			("outside before_uninstall", good_install + "def ensure_setup():\n\tfrappe.db.delete('X', {})\n"),
			("SQL delete", good_install + "def f():\n\tfrappe.db.sql('DELETE FROM `tabX`')\n"),
			("delete must be", good_install.replace("AGENT_STATUS_SCRIPT,", "'Other',")),
			("delete must be", good_install.replace("frappe.delete_doc(", "frappe.db.delete(")),
			("delete must be", good_install.replace("FORM_SCRIPT_DOCTYPE,", "'HD Ticket',")),
		):
			with self.subTest(fragment=fragment, source=source):
				self.assertCaught(check_install_deletes_only_status_script({INSTALL_FILE: source}), fragment)

	# ticket panel (ADR-009, ADR-010 Amendment 1) -------------------------------------------------

	PANEL_SOURCES: ClassVar[dict] = {
		"ticket_panel.py": (
			"import frappe\n"
			"@frappe.whitelist(methods=['POST'])\n"
			"def get_panel_data(ticket):\n\treturn 1\n"
			"@frappe.whitelist(methods=['POST'])\n"
			"def send_message(ticket, text):\n\treturn frappe.get_doc('HD Ticket', ticket).new_comment(text)\n"
		)
	}

	def test_call_allow_list_scanner_catches_unlisted_method(self):
		allowed = tuple(PANEL_METHODS)
		good = 'state.call("erp_ai.ticket_panel.get_panel_data", {});\nstate.call("erp_ai.ticket_panel.send_message", {});'
		self.assertEqual(check_call_allow_list(good, allowed, self.PANEL_SOURCES), [])
		self.assertCaught(
			check_call_allow_list(
				good + 'state.call("erp_ai.handlers.other", {});', allowed, self.PANEL_SOURCES
			),
			"erp_ai.handlers.other is not in PANEL_METHODS",
			"does not point to a @frappe.whitelist function",
		)
		self.assertCaught(
			check_call_allow_list(good.split("\n")[0], allowed, self.PANEL_SOURCES),
			"erp_ai.ticket_panel.send_message is in PANEL_METHODS but the script never calls it",
		)
		self.assertCaught(
			check_call_allow_list(good + "state.call(METHOD, {});", allowed, self.PANEL_SOURCES),
			"not a string literal",
		)
		undecorated = {
			"ticket_panel.py": self.PANEL_SOURCES["ticket_panel.py"].replace(
				"@frappe.whitelist(methods=['POST'])\ndef send", "def send"
			)
		}
		self.assertCaught(
			check_call_allow_list(good, allowed, undecorated),
			"erp_ai.ticket_panel.send_message does not point to a @frappe.whitelist function",
		)

	def test_socket_on_scanner_catches_outside_once_block(self):
		block = 'if (state.socket !== socket) {\n\tsocket.on(EVENT, a);\n\tsocket.on("connect", () => { b(); });\n}\n'
		head = 'const EVENT = "erp_ai:agent_status";\n'
		self.assertEqual(check_socket_on_only_in_once_block(head + block, "erp_ai:agent_status"), [])
		self.assertCaught(
			check_socket_on_only_in_once_block(
				head + block + 'socket.on("doc_update", c);\n', "erp_ai:agent_status"
			),
			"outside the once-per-socket block",
		)
		self.assertCaught(
			check_socket_on_only_in_once_block(
				head + block.replace("EVENT, a", '"typing", a'), "erp_ai:agent_status"
			),
			"event 'typing' is not one of",
		)
		self.assertCaught(
			check_socket_on_only_in_once_block(head + "socket.on(EVENT, a);\n", "erp_ai:agent_status"),
			"block if (state.socket !== socket) { is missing",
		)
		self.assertCaught(
			check_socket_on_only_in_once_block(
				head + block.replace("EVENT, a", "OTHER, a"), "erp_ai:agent_status"
			),
			"event None is not one of",
		)
		# an `.on(` in a comment or string is not a registration
		self.assertEqual(
			check_socket_on_only_in_once_block(
				head + block + '// socket.on("x", y)\nconst s = "socket.on(";\n', "erp_ai:agent_status"
			),
			[],
		)

	def test_status_script_query_scanner_catches_other_selectors(self):
		self.assertEqual(check_status_script_queries('document.querySelector("#app")'), [])
		self.assertEqual(check_status_script_queries('document.getElementById("app")'), [])
		for source in (
			'document.querySelector(".ticket")',
			'document.querySelector("#app .x")',
			'document.querySelectorAll("#app")',
			'document.getElementById("other")',
			'document.getElementsByClassName("x")',
			"document.querySelector(selector)",
		):
			with self.subTest(source=source):
				self.assertCaught(check_status_script_queries(source), "only allowed with the Vue root")

	def test_status_script_window_scanner_catches_second_state(self):
		good = "window.__erpAiAgentStatus = window.__erpAiAgentStatus || {};\nwindow.addEventListener(1, 2);"
		self.assertEqual(check_status_script_window_state(good), [])
		self.assertCaught(
			check_status_script_window_state(good + "window.__erpAiPanel = {};"), "window state names are"
		)
		self.assertCaught(
			check_status_script_window_state(good + "window.other = 1;"), "window.other is written"
		)
		self.assertCaught(check_status_script_window_state(good + 'window["x"] = 1;'), "window[...]")
		self.assertCaught(check_status_script_window_state("var a = 1;"), "window state names are")

	def test_whitelist_scanner_catches_guest_bare_and_missing_methods(self):
		for decorator, fragment in (
			("@frappe.whitelist()", "methods= must list"),
			("@frappe.whitelist", "bare @frappe.whitelist"),
			("@frappe.whitelist(allow_guest=True, methods=['POST'])", "allow_guest"),
			("@frappe.whitelist(allow_guest=False, methods=['POST'])", "allow_guest"),
			("@frappe.whitelist(methods=[])", "methods= must list"),
			("@whitelist(methods=METHODS)", "methods= must list"),
		):
			with self.subTest(decorator=decorator):
				source = f"import frappe\nfrom frappe import whitelist\n{decorator}\ndef f():\n\tpass\n"
				self.assertCaught(check_whitelisted_methods_declare_http_methods({"x.py": source}), fragment)
		ok = "import frappe\n@frappe.whitelist(methods=['POST'])\ndef f():\n\tpass\n"
		self.assertEqual(check_whitelisted_methods_declare_http_methods({"x.py": ok}), [])

	def test_ticket_panel_whitelist_scanner_catches_third_method_and_get(self):
		self.assertEqual(check_ticket_panel_whitelist(self.PANEL_SOURCES), [])
		source = self.PANEL_SOURCES["ticket_panel.py"]
		extra = source + "@frappe.whitelist(methods=['POST'])\ndef third():\n\tpass\n"
		self.assertCaught(check_ticket_panel_whitelist({PANEL_FILE: extra}), "whitelisted functions are")
		self.assertCaught(
			check_ticket_panel_whitelist({PANEL_FILE: source.replace("'POST'", "'GET'", 1)}),
			'exactly ["POST"]',
		)
		self.assertCaught(
			check_ticket_panel_whitelist({PANEL_FILE: source.replace("['POST']", "['POST', 'GET']", 1)}),
			'exactly ["POST"]',
		)
		self.assertCaught(
			check_ticket_panel_whitelist({PANEL_FILE: source.replace("def get_panel_data", "def get_data")}),
			"whitelisted functions are",
		)

	def test_ticket_panel_forbidden_scanner_catches_each_name(self):
		for snippet in (
			"frappe.get_doc('X', 1, ignore_permissions=True)",
			"frappe.set_user('a')",
			"frappe.get_all('X')",
			"frappe.db.get_values('X')",
			"frappe.db.sql('select 1')",
			"frappe.db.set_value('X', 1, 'a', 2)",
			"doc.db_set('a', 1)",
			"doc.insert()",
			"doc.save()",
			"frappe.delete_doc('X', 1)",
			"frappe.db.delete('X')",
			"frappe.db.commit()",
			"frappe.db.rollback()",
			"frappe.cache.get('k')",
			"frappe.publish_realtime('e')",
		):
			with self.subTest(snippet=snippet):
				source = self.PANEL_SOURCES["ticket_panel.py"] + f"def extra():\n\t{snippet}\n"
				self.assertCaught(
					check_ticket_panel_forbidden_calls({PANEL_FILE: source}), "not allowed in the panel"
				)
		source = self.PANEL_SOURCES["ticket_panel.py"]
		self.assertCaught(
			check_ticket_panel_forbidden_calls({PANEL_FILE: source + "def x(d):\n\td.new_comment('a')\n"}),
			"found 2",
		)
		self.assertCaught(
			check_ticket_panel_forbidden_calls({PANEL_FILE: source.replace("new_comment", "other")}),
			"found 0",
		)
		moved = source.replace("return frappe.get_doc('HD Ticket', ticket).new_comment(text)", "return 1")
		moved += "def helper(d):\n\td.new_comment('a')\n"
		self.assertCaught(
			check_ticket_panel_forbidden_calls({PANEL_FILE: moved}), "must be inside send_message"
		)
		self.assertEqual(check_ticket_panel_forbidden_calls({PANEL_FILE: source}), [])

	def test_ticket_panel_gate_scanner_catches_each_gate(self):
		for gate in PANEL_GATE_NAMES:
			for snippet in (f"policy.{gate}()", f"{gate} = 1", f"d.get('{gate}')"):
				with self.subTest(snippet=snippet):
					source = self.PANEL_SOURCES["ticket_panel.py"] + f"def extra(d, policy):\n\t{snippet}\n"
					self.assertCaught(
						check_ticket_panel_does_not_evaluate_agent_gates({PANEL_FILE: source}), gate
					)
		self.assertCaught(
			check_ticket_panel_does_not_evaluate_agent_gates(
				{PANEL_FILE: "from erp_ai.agent.queue import enqueue_agent_run\n"}
			),
			"enqueue",
		)
		self.assertEqual(check_ticket_panel_does_not_evaluate_agent_gates(self.PANEL_SOURCES), [])

	# FEAT-006: routing rules --------------------------------------------------------------------

	ROUTE_SOURCES: ClassVar[dict] = {
		REGISTRY_FILE: 'TOOL_MODULES = (\n\t"erp_ai.agent.tools.read",\n\t"erp_ai.agent.tools.write_ticket",\n)\n',
		ROUTE_FILE: (
			"import frappe\n"
			"from frappe.desk.form import assign_to\n\n"
			"def apply_route(decision, classification, ctx):\n"
			"\tdoc = frappe.get_doc('HD Ticket', ctx.ticket_name)\n"
			"\tdoc.save()\n\n"
			"def assign_owner(user, ctx):\n"
			"\tassign_to.add({'assign_to': [user], 'doctype': 'HD Ticket', 'name': ctx.ticket_name})\n"
		),
	}

	def test_route_module_scanner_catches_registry_listing_and_tool_names(self):
		self.assertEqual(check_route_module_is_not_a_tool(self.ROUTE_SOURCES), [])
		listed = {
			**self.ROUTE_SOURCES,
			REGISTRY_FILE: 'TOOL_MODULES = ("erp_ai.agent.tools.route_ticket",)\n',
		}
		self.assertCaught(check_route_module_is_not_a_tool(listed), "lists route_ticket")
		for extra in (
			"TOOLS = []\n",
			"from erp_ai.agent.tools.registry import ToolSpec\n",
			"spec = ToolSpec\n",
		):
			with self.subTest(extra=extra):
				routed = {**self.ROUTE_SOURCES, ROUTE_FILE: self.ROUTE_SOURCES[ROUTE_FILE] + extra}
				self.assertCaught(check_route_module_is_not_a_tool(routed), "routing module")
		self.assertCaught(check_route_module_is_not_a_tool({ROUTE_FILE: ""}), REGISTRY_FILE)
		wrapper = "TOOLS = [ToolSpec(name='n', group='g', schema={}, handler=%s)]\n"
		for handler in (
			"apply_route",
			"route_ticket.assign_owner",
			"post_routing_comment",
			"create_routed_task",
		):
			with self.subTest(handler=handler):
				others = {**self.ROUTE_SOURCES, "agent/tools/write_ticket.py": wrapper % handler}
				self.assertCaught(
					check_route_module_is_not_a_tool(others), "write_ticket.py", handler.split(".")[-1]
				)
		positional = {
			**self.ROUTE_SOURCES,
			"agent/tools/write_ticket.py": "TOOLS = [ToolSpec('n', 'g', {}, apply_route)]\n",
		}
		self.assertCaught(check_route_module_is_not_a_tool(positional), "write_ticket.py", "apply_route")
		harmless = {**self.ROUTE_SOURCES, "agent/tools/write_ticket.py": wrapper % "set_classification"}
		self.assertEqual(check_route_module_is_not_a_tool(harmless), [])

	def test_route_single_save_scanner_catches_second_and_misplaced_saves(self):
		self.assertEqual(check_route_module_single_ticket_save(self.ROUTE_SOURCES), [])
		route = self.ROUTE_SOURCES[ROUTE_FILE]
		second = route + "\ndef other(doc):\n\tdoc.save()\n"
		self.assertCaught(
			check_route_module_single_ticket_save({ROUTE_FILE: second}), "outside apply_route", "found 2"
		)
		twice = route.replace("\tdoc.save()\n", "\tdoc.save()\n\tdoc.save()\n")
		self.assertCaught(check_route_module_single_ticket_save({ROUTE_FILE: twice}), "found 2")
		moved = route.replace("def apply_route", "def other_name")
		self.assertCaught(check_route_module_single_ticket_save({ROUTE_FILE: moved}), "outside apply_route")
		none = route.replace("\tdoc.save()\n", "\tpass\n")
		self.assertCaught(check_route_module_single_ticket_save({ROUTE_FILE: none}), "found 0")
		for extra in (
			"\ndef assign_owner_again(doc):\n\tdoc.db_update()\n",
			"\ndef retry(doc):\n\tdoc.db_update(x=1)\n",
		):
			with self.subTest(extra=extra):
				self.assertCaught(
					check_route_module_single_ticket_save({ROUTE_FILE: route + extra}), "db_update"
				)
		inside = route.replace("\tdoc.save()\n", "\tdoc.save()\n\tdoc.db_update()\n")
		self.assertCaught(check_route_module_single_ticket_save({ROUTE_FILE: inside}), "db_update")

	def test_assign_to_scanner_catches_every_way_to_call_it_outside_route_module(self):
		for source in (
			"from frappe.desk.form import assign_to\nassign_to.add({})\n",
			"from frappe.desk.form.assign_to import add\nadd({})\n",
			"from frappe.desk.form.assign_to import add as put\nput({})\n",
			"import frappe\nfrappe.desk.form.assign_to.add({})\n",
			"from frappe.desk.form import assign_to as a\na.add_multiple({})\n",
			"from frappe.desk.form import assign_to\n",
			# no import of the module at all: only the call suffix can catch these
			"def f(a):\n\ta.assign_to.add_multiple({})\n",
			"def f(a):\n\ta.assign_to.add({})\n",
			"def f(doc):\n\tdoc.assign_agent('u')\n",
			"import frappe\nfrappe.get_doc('HD Ticket', t).assign_agent(u)\n",
			"f = getattr(doc, 'assign_agent')\n",
			# ADR-021: no ToDo created by hand either
			"import frappe\nfrappe.get_doc('ToDo').insert()\n",
			"import frappe\nfrappe.get_doc({'doctype': 'ToDo', 'allocated_to': u}).insert()\n",
			"import frappe\nfrappe.new_doc('ToDo')\n",
		):
			with self.subTest(source=source):
				self.assertCaught(
					check_assign_to_only_in_route_module({"agent/runner.py": source}), "agent/runner.py"
				)
		self.assertEqual(check_assign_to_only_in_route_module(self.ROUTE_SOURCES), [])
		clean = (
			"import frappe\nitems = [].add\nfrappe.get_all('ToDo', filters={})\n"
			"frappe.get_doc('HD Ticket', t).save()\nfrappe.get_doc({'doctype': 'Task'}).insert()\n"
		)
		self.assertEqual(check_assign_to_only_in_route_module({"agent/runner.py": clean}), [])

	def test_share_bypass_scanner_catches_each_forbidden_name(self):
		for source in (
			"assign_to.add({}, ignore_share_permission=True)\n",
			"d = {'ignore_share_permission': 1}\n",
			"from frappe.desk.form import assign_to\nassign_to._add({})\n",
			"from frappe.desk.form.assign_to import _add\n_add({})\n",
			"from frappe.share import add_docshare\nadd_docshare('T', 'x', 'u')\n",
			"import frappe\nfrappe.share.add('T', 'x', 'u')\n",
			"from frappe import share\nshare.add('T', 'x', 'u')\n",
			"from frappe.share import add\nadd('T', 'x', 'u')\n",
		):
			with self.subTest(source=source):
				self.assertCaught(check_no_share_bypass({"agent/tools/route_ticket.py": source}), "sharing")
		self.assertEqual(check_no_share_bypass(self.ROUTE_SOURCES), [])
		self.assertEqual(check_no_share_bypass({"x.py": "s = set()\ns.add(1)\nshare = 1\n"}), [])

	def test_policy_scanner_catches_auto_assign_switch_read_outside_policy(self):
		for source in (
			"def f(settings):\n\treturn settings.auto_assign_enabled\n",
			"def f(settings):\n\treturn getattr(settings, 'auto_assign_enabled', 0)\n",
			"def f(settings):\n\treturn settings.get('auto_assign_enabled')\n",
			"import frappe\nfrappe.db.get_single_value('ERP AI Setting', 'auto_assign_enabled')\n",
			"auto_assign_enabled = 1\n",
		):
			with self.subTest(source=source):
				self.assertCaught(
					check_policy_fields_only_in_policy({"agent/runner.py": source}), "auto_assign_enabled"
				)
		through_policy = "from erp_ai.agent import policy\n\ndef f(settings):\n\treturn policy.auto_assign_enabled(settings)\n"
		self.assertEqual(check_policy_fields_only_in_policy({"agent/runner.py": through_policy}), [])
		self.assertEqual(
			check_policy_fields_only_in_policy({POLICY_FILE: "def x(s):\n\treturn s.auto_assign_enabled\n"}),
			[],
		)

	def test_entry_types_scanner_catches_new_type_in_code_or_doctype(self):
		run_log = 'ENTRY_TYPES = ("classify", "reason", "skip", "change")\n'
		doctype = json.dumps(
			{"fields": [{"fieldname": "entry_type", "options": "classify\nreason\nskip\nchange"}]}
		)
		good = {RUN_LOG_FILE: run_log, LOG_DOCTYPE_FILE: doctype}
		self.assertEqual(check_entry_types_unchanged(good), [])
		extra = {**good, RUN_LOG_FILE: 'ENTRY_TYPES = ("classify", "reason", "skip", "change", "route")\n'}
		self.assertCaught(check_entry_types_unchanged(extra), "ENTRY_TYPES")
		without_change = {**good, RUN_LOG_FILE: 'ENTRY_TYPES = ("classify", "reason", "skip")\n'}
		self.assertCaught(check_entry_types_unchanged(without_change), "ENTRY_TYPES")
		options = json.dumps(
			{"fields": [{"fieldname": "entry_type", "options": "classify\nreason\nskip\nchange\nroute"}]}
		)
		self.assertCaught(check_entry_types_unchanged({**good, LOG_DOCTYPE_FILE: options}), "options")
		old_options = json.dumps(
			{"fields": [{"fieldname": "entry_type", "options": "classify\nreason\nskip"}]}
		)
		self.assertCaught(check_entry_types_unchanged({**good, LOG_DOCTYPE_FILE: old_options}), "options")
		computed = {**good, RUN_LOG_FILE: "ENTRY_TYPES = tuple(x)\n"}
		self.assertCaught(check_entry_types_unchanged(computed), "ENTRY_TYPES")
		self.assertCaught(check_entry_types_unchanged({RUN_LOG_FILE: run_log}), LOG_DOCTYPE_FILE)

	def test_assign_column_scanner_catches_reads_and_allows_authority(self):
		for source in (
			"import frappe\nfrappe.db.get_value('HD Ticket', t, '_assign')\n",
			"def f(doc):\n\treturn doc._assign\n",
			"def f(doc):\n\treturn doc.get('_assign')\n",
			"import frappe\nfrappe.db.sql('select _assign from `tabHD Ticket`')\n",
			"_assign = 1\n",
		):
			with self.subTest(source=source):
				self.assertCaught(
					check_no_assign_column_for_decisions({"agent/routing.py": source}), "_assign"
				)
		source = "import frappe\nfrappe.db.get_value('HD Ticket', t, '_assign')\n"
		allowed = f"def {ASSIGN_FIELD_ALLOWED_FUNCTION}(a, t):\n\treturn frappe.db.get_value('HD Ticket', t, '_assign')\n"
		self.assertEqual(check_no_assign_column_for_decisions({AUTHORITY_FILE: allowed}), [])
		self.assertEqual(check_no_assign_column_for_decisions({"handlers.py": source}), [])
		# authority.py is exempt only inside its one function
		self.assertCaught(check_no_assign_column_for_decisions({AUTHORITY_FILE: source}), "_assign")
		other = allowed.replace(ASSIGN_FIELD_ALLOWED_FUNCTION, "is_instruction")
		self.assertCaught(check_no_assign_column_for_decisions({AUTHORITY_FILE: other}), "_assign")
		both = allowed + "\ndef other(t):\n\treturn frappe.db.get_value('HD Ticket', t, '_assign')\n"
		self.assertCaught(check_no_assign_column_for_decisions({AUTHORITY_FILE: both}), "_assign")
		self.assertEqual(
			check_no_assign_column_for_decisions(
				{"agent/site_facts.py": "x = 'assigned_by'\ny = 'reassign'\n"}
			),
			[],
		)
		# the pattern's own edges: a letter or digit before, a letter, digit or `_` after, is another word
		for text in ("ai_assign", "9_assign", "_assigned", "_assign_to", "_assign9", "x_assign_y"):
			with self.subTest(text=text):
				self.assertEqual(check_no_assign_column_for_decisions({"agent/a.py": f"x = {text!r}\n"}), [])
		for text in ("(_assign)", " _assign ", "`_assign`", "select _assign,x", "_assign"):
			with self.subTest(text=text):
				self.assertCaught(
					check_no_assign_column_for_decisions({"agent/a.py": f"x = {text!r}\n"}), "_assign"
				)

	def test_route_module_bypass_rules_catch_violations_in_route_module(self):
		route = self.ROUTE_SOURCES[ROUTE_FILE]
		self.assertEqual(check_tools_never_bypass_permissions({ROUTE_FILE: route}), [])
		for extra in (
			"def x(doc):\n\tdoc.save(ignore_permissions=True)\n",
			"def x():\n\tfrappe.db.set_value('HD Ticket', 'T', 'a', 1)\n",
			"def x():\n\tfrappe.set_user('Administrator')\n",
			"def x():\n\tfrappe.db.sql('update `tabHD Ticket` set a = 1')\n",
			"def x():\n\tfrappe.get_all('ToDo')\n",
		):
			with self.subTest(extra=extra):
				self.assertCaught(check_tools_never_bypass_permissions({ROUTE_FILE: route + extra}))

	def test_sla_dates_scanner_catches_each_way_to_write_them(self):
		for source in (
			"def f(doc):\n\tdoc.response_by = 1\n",
			"def f(doc):\n\tdoc.resolution_by += 1\n",
			"def f(doc):\n\tdoc['response_by'] = 1\n",
			"def f(doc):\n\tdoc.update({'resolution_by': 1})\n",
			"def f(doc):\n\tdoc.update(response_by=1)\n",
			"def f(doc):\n\tsetattr(doc, 'response_by', 1)\n",
			"import frappe\nfrappe.db.set_value('HD Ticket', t, 'resolution_by', 1)\n",
			"def f(doc):\n\tdoc.db_set('response_by', 1)\n",
			"response_by: int = 1\n",
			"def f(doc):\n\tdoc.set('response_by', 1)\n",
			"def f(doc):\n\tdoc.set('resolution_by', 1)\n",
			# the field name held in a constant, then used by a generic writer
			"F = 'resolution_by'\n",
			"F: str = 'response_by'\n",
			"FIELDS = ('response_by', 'x')\n",
			"FIELDS = ['x', 'resolution_by']\n",
			"FIELDS = {'response_by'}\n",
			"def f(doc, v):\n\tF = 'response_by'\n\tdoc.set(F, v)\n",
		):
			with self.subTest(source=source):
				self.assertCaught(
					check_feature_never_assigns_sla_dates({"agent/routing.py": source}), "SLA date"
				)
		reads = (
			"def f(doc):\n\tx = doc.get('resolution_by')\n\ty = doc.response_by\n"
			"\treturn doc.response_by, doc.get('resolution_by'), x, y, s.set('other', 1)\n"
		)
		self.assertEqual(check_feature_never_assigns_sla_dates({"agent/site_facts.py": reads}), [])
		self.assertEqual(check_feature_never_assigns_sla_dates({"tasks.py": "x.response_by = 1\n"}), [])

	def test_default_people_scanner_matches_whole_words_only(self):
		for text in (
			"Việt",
			"Tiến",
			"Hiếu",
			"Lan",
			"Hà",
			"Thư",
			"Chi",
			"gán cho Hiếu",
			"A: Lan, Hà",
			"ai.agent",
		):
			with self.subTest(text=text):
				source = f"DEFAULT = {text!r}\n"
				self.assertCaught(
					check_no_default_people_in_agent_python({"agent/routing.py": source}), "AC-14"
				)
		self.assertCaught(
			check_no_default_people_in_agent_python(
				{"agent/run_status.py": "U = 'ai.agent@miyano.com.vn'\n"}
			),
			"ai.agent",
		)
		self.assertCaught(
			check_no_default_people_in_agent_python({"agent/prompts.py": 'P = f"Giao cho {x} là Hiếu"\n'}),
			"Hiếu",
		)
		self.assertCaught(
			check_no_default_people_in_agent_python({"agent/prompts.py": '"""Việt Nam, nhờ Việt xử lý"""\n'}),
			"Việt",
		)
		clean = (
			"A = 'Công ty Miyano Việt Nam'\nB = 'Tiếng Việt, ngắn'\nC = 'Thư mục nằm ngoài mã nguồn'\n"
			"D = 'erp_ai.agent.runner.run_for_ticket'\nE = 'Chiều', 'Hàng', 'Lanh', 'Thưa', 'Chính', 'Hiếm'\n"
			"F = 'chi tiết', 'lan can', 'ai.agents'\n"
			"G = 'ThanhLan', 'ThiHà', 'AnhChi', '2Thư', 'ai_Việt', 'xHiếu', 'NhàTiến'\n"
		)
		self.assertEqual(check_no_default_people_in_agent_python({"agent/prompts.py": clean}), [])
		outside = "DEFAULT = 'Hiếu'\n"
		self.assertEqual(check_no_default_people_in_agent_python({"constants.py": outside}), [])


if __name__ == "__main__":
	unittest.main()
