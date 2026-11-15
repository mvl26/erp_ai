import uuid
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from helpdesk.test_utils import create_agent, make_ticket

from erp_ai.agent.tools import read
from erp_ai.agent.tools.registry import ToolContext, ToolSpec, _first_invalid_key
from erp_ai.constants import AGENT_USER, ROLE_INSTRUCTOR
from erp_ai.test_utils import keep_agent_settings, set_agent_settings

EXCLUDED_TEAM = "T24 Excluded Team"
AGENT_A = "t24.agent.a@example.com"
INSTRUCTOR = "t24.instructor@example.com"
OUTSIDER = "t24.outsider@example.com"
SCHEMA_TYPES = {"string", "integer", "boolean", "array"}
EMPTY_QUERY_REFUSAL = "câu tìm cần ít nhất một từ dài 2 ký tự"
RESULT_KEYS = {"name", "subject", "ticket_type", "agent_group", "resolution_date", "resolution_details"}
# A real HD Team: the query form of the send predicate only knows teams that exist (policy.excluded_team_names).
SEARCH_EXCLUDED_TEAM = "T153 Nhóm loại trừ"


def _ctx(ticket_name="TKT-0"):
	return ToolContext(
		ticket_name=ticket_name,
		effective_level="L1",
		instructor=None,
		run_id="run-1",
		category_mapping={},
		agent_user=AGENT_USER,
	)


class TestReadTools(FrappeTestCase):
	def setUp(self):
		# Runs after the rollback: HD Team.after_insert caches an Assignment Rule in Redis.
		self.addCleanup(frappe.cache.hdel, "assignment_rule_map", "HD Ticket")
		self.addCleanup(frappe.db.rollback)
		self.addCleanup(frappe.set_user, "Administrator")
		frappe.set_user("Administrator")
		set_agent_settings(excluded_teams=EXCLUDED_TEAM)
		# A real HD Team: the in-query exclusion (policy.excluded_team_names) only knows teams that exist.
		if not frappe.db.exists("HD Team", EXCLUDED_TEAM):
			frappe.get_doc(
				{"doctype": "HD Team", "team_name": EXCLUDED_TEAM, "users": [{"user": "Administrator"}]}
			).insert(ignore_permissions=True)
		if not frappe.db.exists("Role", ROLE_INSTRUCTOR):
			frappe.get_doc({"doctype": "Role", "role_name": ROLE_INSTRUCTOR}).insert()
		create_agent(AGENT_A)
		create_agent(INSTRUCTOR)
		frappe.get_doc("User", INSTRUCTOR).add_roles(ROLE_INSTRUCTOR)
		self.ticket = make_ticket(subject="T24 open ticket", description="<p>Máy <b>in</b> hỏng</p>").name
		self.excluded = self._excluded_ticket("T24 excluded ticket")

	def _excluded_ticket(self, subject, **values):
		name = make_ticket(subject=subject, **values).name
		# db.set_value skips link validation; the team itself is created in setUp.
		frappe.db.set_value("HD Ticket", name, "agent_group", EXCLUDED_TEAM)
		return name

	def _comment(self, ticket, author, content="x", **extra):
		doc = frappe.get_doc("HD Ticket", ticket)
		frappe.set_user(author)
		try:
			if extra:
				return doc.add_comment("Comment", content, **extra).name
			return doc.new_comment(content)
		finally:
			frappe.set_user("Administrator")

	def _resolve(self, name, details="Đã thay mực"):
		frappe.db.set_value("HD Ticket", name, {"status_category": "Resolved", "resolution_details": details})

	def _full_name(self, user):
		return frappe.db.get_value("User", user, "full_name")

	def _outsider(self):
		if not frappe.db.exists("User", OUTSIDER):
			frappe.get_doc(
				{"doctype": "User", "email": OUTSIDER, "first_name": "Out", "send_welcome_email": 0}
			).insert()
		frappe.set_user(OUTSIDER)

	# --- get_ticket ---

	def test_get_ticket_returns_fields_default_current_ticket(self):
		result = read.get_ticket({}, _ctx(self.ticket))
		self.assertTrue(result["ok"], result)
		self.assertEqual(result["ticket"]["name"], self.ticket)
		self.assertEqual(result["ticket"]["subject"], "T24 open ticket")
		self.assertNotIn("<", result["ticket"]["description"])
		other = make_ticket(subject="T24 other").name
		self.assertEqual(read.get_ticket({"name": other}, _ctx(self.ticket))["ticket"]["name"], other)

	def test_get_ticket_description_truncated_to_prompt_limit(self):
		frappe.db.set_value("HD Ticket", self.ticket, "description", "<p>" + "d" * 6500 + "</p>")
		description = read.get_ticket({}, _ctx(self.ticket))["ticket"]["description"]
		self.assertEqual(len(description), 6000)

	def _restrict_to_permlevel_zero(self):
		# Non-Administrator who can read the ticket but holds no permlevel 7/8 read access.
		patcher = patch("frappe.model.document.Document.get_permlevel_access", return_value=[0])
		patcher.start()
		self.addCleanup(patcher.stop)
		frappe.set_user(AGENT_A)

	def test_get_record_hides_fields_above_users_permlevel(self):
		self._resolve(self.ticket, "secret-resolution")  # resolution_details is permlevel 8
		meta = frappe.get_meta("HD Ticket")
		self.assertEqual(meta.get_field("resolution_details").permlevel, 8)
		self.assertEqual(meta.get_field("status_category").permlevel, 7)
		self._restrict_to_permlevel_zero()
		record = read.get_record({"doctype": "HD Ticket", "name": self.ticket}, _ctx(self.ticket))
		self.assertTrue(record["ok"], record)
		self.assertEqual(record["record"]["subject"], "T24 open ticket")
		self.assertIsNone(record["record"].get("resolution_details"))
		self.assertIsNone(record["record"].get("status_category"))

	def test_get_ticket_hides_fields_above_users_permlevel(self):
		# get_ticket's fixed fields are permlevel 0 today; raise `priority` so the call must hide it.
		self.assertTrue(read.get_ticket({}, _ctx(self.ticket))["ticket"]["priority"])
		frappe.make_property_setter(
			{
				"doctype": "HD Ticket",
				"fieldname": "priority",
				"property": "permlevel",
				"value": 7,
				"property_type": "Int",
			}
		)
		self.addCleanup(lambda: (frappe.db.rollback(), frappe.clear_cache(doctype="HD Ticket")))
		frappe.clear_cache(doctype="HD Ticket")
		self._restrict_to_permlevel_zero()
		result = read.get_ticket({}, _ctx(self.ticket))
		self.assertTrue(result["ok"], result)
		self.assertEqual(result["ticket"]["subject"], "T24 open ticket")
		self.assertIsNone(result["ticket"]["priority"])

	def test_get_ticket_missing_or_no_permission_refused(self):
		self.assertFalse(read.get_ticket({"name": "NOPE-999"}, _ctx(self.ticket))["ok"])
		self._outsider()
		self.assertFalse(read.get_ticket({}, _ctx(self.ticket))["ok"])

	def test_no_permission_refused_on_every_tool(self):
		self._comment(self.ticket, AGENT_A)
		comment = frappe.get_all("Comment", {"reference_name": self.ticket}, pluck="name")[0]
		self._resolve(self.ticket)
		self._outsider()
		ctx = _ctx(self.ticket)
		self.assertFalse(read.list_comments({}, ctx)["ok"])
		self.assertFalse(read.get_record({"doctype": "HD Ticket", "name": self.ticket}, ctx)["ok"])
		self.assertFalse(read.get_record({"doctype": "Comment", "name": comment}, ctx)["ok"])
		self.assertFalse(read.search_resolved_tickets({"query": "T24"}, ctx)["ok"])

	# --- list_comments ---

	def test_list_comments_reads_core_comment_author_from_owner(self):
		# comment_email / comment_by are client-set: forge them to the instructor.
		self._comment(self.ticket, AGENT_A, "Máy hỏng", comment_email=INSTRUCTOR, comment_by=INSTRUCTOR)
		self._comment(self.ticket, INSTRUCTOR, "Hãy đổi mực")
		result = read.list_comments({}, _ctx(self.ticket))
		self.assertTrue(result["ok"], result)
		by_content = {c["content"]: c for c in result["comments"]}
		self.assertEqual(by_content["Máy hỏng"]["author"], self._full_name(AGENT_A))
		self.assertEqual(by_content["Máy hỏng"]["role"], "dữ liệu")
		self.assertEqual(by_content["Hãy đổi mực"]["author"], self._full_name(INSTRUCTOR))
		self.assertEqual(by_content["Hãy đổi mực"]["role"], "chỉ thị")
		for comment in result["comments"]:
			self.assertEqual(set(comment), {"author", "role", "creation", "content"})

	def test_list_comments_other_ticket_and_non_comment_types_excluded(self):
		other = make_ticket(subject="T24 other").name
		self._comment(other, AGENT_A, "of other ticket")
		frappe.get_doc("HD Ticket", self.ticket).add_comment("Info", "system note")
		self.assertEqual(read.list_comments({}, _ctx(self.ticket))["comments"], [])
		named = read.list_comments({"ticket": other}, _ctx(self.ticket))
		self.assertEqual([c["content"] for c in named["comments"]], ["of other ticket"])

	def test_list_comments_strips_html(self):
		self._comment(self.ticket, AGENT_A, "<p>Xin <b>chào</b></p>")
		content = read.list_comments({}, _ctx(self.ticket))["comments"][0]["content"]
		self.assertNotIn("<", content)
		self.assertIn("chào", content)

	def test_list_comments_truncates_content(self):
		self._comment(self.ticket, AGENT_A, "a" * 2500)
		content = read.list_comments({}, _ctx(self.ticket))["comments"][0]["content"]
		self.assertEqual(len(content), 2000)
		self.assertEqual(read.COMMENT_MAX_CHARS, 2000)

	def test_list_comments_limit(self):
		for index in range(3):
			self._comment(self.ticket, AGENT_A, f"c{index}")
		ctx = _ctx(self.ticket)
		self.assertEqual(len(read.list_comments({"limit": 2}, ctx)["comments"]), 2)
		self.assertEqual(len(read.list_comments({}, ctx)["comments"]), 3)
		for bad in (0, 51, -1, True, "5", 2.5):
			self.assertFalse(read.list_comments({"limit": bad}, ctx)["ok"], bad)

	# --- search_resolved_tickets ---

	def test_search_resolved_only_matching_resolved_with_trimmed_details(self):
		match = make_ticket(subject="T24 zq7printer jam", description="<p>paper stuck</p>").name
		by_description = make_ticket(subject="T24 other", description="the zq7printer is dead").name
		unresolved = make_ticket(subject="T24 zq7printer open").name
		unrelated = make_ticket(subject="T24 keyboard").name
		self._resolve(match, "<p>" + "d" * 2000 + "</p>")
		self._resolve(by_description)
		self._resolve(unrelated)
		result = read.search_resolved_tickets({"query": "zq7printer"}, _ctx(self.ticket))
		self.assertTrue(result["ok"], result)
		names = {row["name"] for row in result["tickets"]}
		self.assertEqual(names, {match, by_description})
		self.assertNotIn(unresolved, names)
		row = next(r for r in result["tickets"] if r["name"] == match)
		self.assertEqual(
			set(row),
			{"name", "subject", "ticket_type", "agent_group", "resolution_date", "resolution_details"},
		)
		self.assertEqual(len(row["resolution_details"]), 1500)
		self.assertNotIn("<", row["resolution_details"])

	def test_search_resolved_query_is_literal_and_limit_applies(self):
		names = [make_ticket(subject=f"T24 lit {i}").name for i in range(3)]
		for name in names:
			self._resolve(name)
		ctx = _ctx(self.ticket)
		self.assertEqual(
			read.search_resolved_tickets({"query": "%%"}, ctx), {"ok": False, "reason": EMPTY_QUERY_REFUSAL}
		)
		# Every word scores on its own: "lit" finds the three; "t2_" is no word of them, `_` is no wildcard.
		found = read.search_resolved_tickets({"query": "T2_ lit"}, ctx)["tickets"]
		self.assertEqual(sorted(row["name"] for row in found), sorted(names))
		self.assertEqual(read.search_resolved_tickets({"query": "T2_"}, ctx)["tickets"], [])
		self.assertEqual(len(read.search_resolved_tickets({"query": "T24 lit"}, ctx)["tickets"]), 3)
		limited = read.search_resolved_tickets({"query": "T24 lit", "limit": 2}, ctx)
		self.assertEqual(len(limited["tickets"]), 2)

	def test_search_resolved_limit_skips_newest_excluded_and_fills_from_older(self):
		older = make_ticket(subject="T24 skip older").name
		newest = self._excluded_ticket("T24 skip newest")
		self._resolve(older)
		self._resolve(newest)
		frappe.db.set_value("HD Ticket", older, "modified", "2000-01-01 00:00:00", update_modified=False)
		result = read.search_resolved_tickets({"query": "T24 skip", "limit": 1}, _ctx(self.ticket))
		self.assertEqual([r["name"] for r in result["tickets"]], [older])

	def test_like_pattern_leaves_escaping_to_frappe(self):
		# Frappe escapes `\\` and `%` of a like value itself (db_query); escaping here too finds nothing.
		self.assertEqual(read._like_pattern("a\\b%c_d"), "%a\\b%c_d%")

	def test_search_resolved_argument_bounds(self):
		ctx = _ctx(self.ticket)
		for args in (
			{},
			{"query": "a"},
			{"query": "x" * 101},
			{"query": 5},
			{"query": "ok", "limit": 0},
			{"query": "ok", "limit": 11},
			{"query": "ok", "limit": True},
		):
			self.assertFalse(read.search_resolved_tickets(args, ctx)["ok"], args)

	# --- get_record ---

	def test_denied_doctypes_refused(self):
		module_doctypes = frappe.get_all("DocType", {"module": "ERP AI agent"}, pluck="name")
		self.assertIn("ERP AI Log", module_doctypes)
		for doctype in sorted(set(read.DENIED_DOCTYPES) | set(module_doctypes)):
			with self.subTest(doctype=doctype):
				result = read.get_record({"doctype": doctype, "name": "x"}, _ctx(self.ticket))
				self.assertFalse(result["ok"])
				self.assertIn("bị cấm", result["reason"])
		self.assertEqual(
			read.DENIED_DOCTYPES,
			{
				"ERP AI Setting",
				"ERP AI Credential",
				"ERP AI Log",
				"Salary Slip",
				"Employee",
				"Purchase Invoice",
				"Payment Entry",
				"GL Entry",
				"User",
				"Role Permission",
				"Custom DocPerm",
			},
		)

	def test_echoed_doctype_is_bounded(self):
		result = read.get_record({"doctype": "X" * 5000, "name": "x"}, _ctx(self.ticket))
		self.assertFalse(result["ok"])
		self.assertLessEqual(len(result["reason"]), 200)
		props = {s.name: s.schema["input_schema"]["properties"] for s in read.TOOLS}
		self.assertEqual(props["get_record"]["doctype"]["maxLength"], 140)

	def test_every_doctype_of_ai_module_denied(self):
		# All current AI DocTypes are also listed by name; prove the module rule on its own.
		module = frappe.db.get_value("DocType", "ToDo", "module")
		with patch.object(read, "AI_MODULE", module):
			result = read.get_record({"doctype": "ToDo", "name": "x"}, _ctx(self.ticket))
		self.assertIn("bị cấm", result["reason"])

	def test_doctype_outside_allowlist_refused(self):
		for doctype in ("ToDo", "HD Ticket Comment", "File", "Communication"):
			with self.subTest(doctype=doctype):
				result = read.get_record({"doctype": doctype, "name": "x"}, _ctx(self.ticket))
				self.assertFalse(result["ok"])
				self.assertIn("chưa được mở", result["reason"])
		self.assertEqual(
			read.ALLOWED_READ_DOCTYPES,
			{"HD Ticket", "Comment", "HD Team", "HD Ticket Type", "HD Ticket Priority", "HD Article"},
		)

	def test_get_record_returns_allowed_record(self):
		result = read.get_record({"doctype": "HD Ticket", "name": self.ticket}, _ctx(self.ticket))
		self.assertTrue(result["ok"], result)
		self.assertEqual(result["record"]["name"], self.ticket)
		missing = read.get_record({"doctype": "HD Ticket", "name": "NOPE-1"}, _ctx(self.ticket))
		self.assertFalse(missing["ok"])

	def test_password_fields_never_returned(self):
		# Real detection: Email Account really has Password fields.
		self.assertIn("password", read._password_fieldnames("Email Account"))
		self.assertNotIn("subject", read._password_fieldnames("HD Ticket"))
		# Wiring: pretend `subject` is a Password field; it must be stripped from the record.
		with patch.object(read, "_password_fieldnames", return_value={"subject"}):
			record = read.get_record({"doctype": "HD Ticket", "name": self.ticket}, _ctx(self.ticket))
		self.assertTrue(record["ok"], record)
		self.assertNotIn("subject", record["record"])
		self.assertIn("status", record["record"])

	def test_get_record_comment_only_for_ticket_comments(self):
		ticket_comment = self._comment(
			self.ticket, AGENT_A, "ok", comment_email=INSTRUCTOR, comment_by=INSTRUCTOR
		)
		ctx = _ctx(self.ticket)
		result = read.get_record({"doctype": "Comment", "name": ticket_comment}, ctx)
		self.assertTrue(result["ok"], result)
		self.assertEqual(result["record"]["content"], "ok")
		self.assertNotIn("comment_email", result["record"])
		self.assertNotIn("comment_by", result["record"])
		other_doc = frappe.get_doc(
			{
				"doctype": "Comment",
				"comment_type": "Comment",
				"reference_doctype": "User",
				"reference_name": AGENT_A,
				"content": "not a ticket",
			}
		).insert()
		info = frappe.get_doc("HD Ticket", self.ticket).add_comment("Info", "system")
		for label, name in (("other doctype", other_doc.name), ("Info type", info.name)):
			with self.subTest(label):
				refused = read.get_record({"doctype": "Comment", "name": name}, ctx)
				self.assertFalse(refused["ok"])
				self.assertIn("chưa được mở", refused["reason"])

	# --- NFR-4 ---

	def test_excluded_tickets_never_returned(self):
		excluded_comment = self._comment(self.excluded, AGENT_A, "secret")
		open_comment = self._comment(self.ticket, AGENT_A, "public")
		self._resolve(self.excluded, "excluded solution")
		self._resolve(self.ticket, "open solution")
		ctx = _ctx(self.ticket)
		with self.subTest("get_ticket"):
			self.assertFalse(read.get_ticket({"name": self.excluded}, ctx)["ok"])
			self.assertTrue(read.get_ticket({"name": self.ticket}, ctx)["ok"])
		with self.subTest("get_record HD Ticket"):
			self.assertFalse(read.get_record({"doctype": "HD Ticket", "name": self.excluded}, ctx)["ok"])
			self.assertTrue(read.get_record({"doctype": "HD Ticket", "name": self.ticket}, ctx)["ok"])
		with self.subTest("get_record Comment"):
			self.assertFalse(read.get_record({"doctype": "Comment", "name": excluded_comment}, ctx)["ok"])
			self.assertTrue(read.get_record({"doctype": "Comment", "name": open_comment}, ctx)["ok"])
		with self.subTest("list_comments"):
			self.assertFalse(read.list_comments({"ticket": self.excluded}, ctx)["ok"])
			self.assertTrue(read.list_comments({"ticket": self.ticket}, ctx)["ok"])
		with self.subTest("search_resolved_tickets"):
			found = {r["name"] for r in read.search_resolved_tickets({"query": "T24 "}, ctx)["tickets"]}
			self.assertIn(self.ticket, found)
			self.assertNotIn(self.excluded, found)

	def test_opted_out_ticket_never_returned(self):
		frappe.db.set_value("HD Ticket", self.ticket, "ai_opt_out", 1)
		self.assertFalse(read.get_ticket({}, _ctx(self.ticket))["ok"])

	# --- registration ---

	def test_tools_registered_with_valid_schemas(self):
		self.assertEqual(
			{spec.name for spec in read.TOOLS},
			{"get_ticket", "list_comments", "search_resolved_tickets", "get_record"},
		)
		for spec in read.TOOLS:
			self.assertIsInstance(spec, ToolSpec)
			self.assertEqual(spec.group, "read")
			schema = spec.schema
			self.assertEqual(schema["name"], spec.name)
			self.assertTrue(schema["description"])
			for prop in schema["input_schema"]["properties"].values():
				self.assertIn(prop["type"], SCHEMA_TYPES)
		schemas = {spec.name: spec.schema["input_schema"] for spec in read.TOOLS}
		self.assertIsNone(_first_invalid_key({"limit": 50}, schemas["list_comments"]))
		self.assertEqual(_first_invalid_key({"limit": 51}, schemas["list_comments"]), "limit")
		search = schemas["search_resolved_tickets"]
		self.assertEqual(_first_invalid_key({"query": "x"}, search), "query")
		self.assertEqual(_first_invalid_key({"query": "ab", "limit": 11}, search), "limit")
		self.assertEqual(_first_invalid_key({"doctype": "HD Ticket"}, schemas["get_record"]), "name")

	def test_handlers_never_raise_on_bad_arguments(self):
		ctx = _ctx(self.ticket)
		bad = {"name": 5, "ticket": 5, "doctype": 5, "query": None, "limit": None}
		for handler in (read.get_ticket, read.list_comments, read.search_resolved_tickets, read.get_record):
			for args in ({}, bad, None):
				try:
					result = handler(args, ctx)
				except Exception as error:
					self.fail(f"{handler.__name__}({args}) raised {error!r}")
				self.assertIn("ok", result)


class TestSearchResolvedTickets(FrappeTestCase):
	"""AC-48: every query word scores on the whole text of the ticket; excluded tickets never reach the scan."""

	def setUp(self):
		# Runs after the rollback: HD Team.after_insert caches an Assignment Rule in Redis.
		self.addCleanup(frappe.cache.hdel, "assignment_rule_map", "HD Ticket")
		self.addCleanup(frappe.db.rollback)
		self.addCleanup(frappe.set_user, "Administrator")
		frappe.set_user("Administrator")
		keep_agent_settings(self)
		set_agent_settings(excluded_teams=SEARCH_EXCLUDED_TEAM)
		if not frappe.db.exists("HD Team", SEARCH_EXCLUDED_TEAM):
			frappe.get_doc(
				{
					"doctype": "HD Team",
					"team_name": SEARCH_EXCLUDED_TEAM,
					"users": [{"user": "Administrator"}],
				}
			).insert(ignore_permissions=True)
		create_agent(AGENT_A)  # the assignee of a ToDo must be a real user
		# Words no other ticket of the site holds.
		self.tag = f"zq{uuid.uuid4().hex[:8]}"

	def word(self, suffix):
		return f"{self.tag}{suffix}"

	def resolved(self, subject, description="<p>x</p>", details="Đã thay mực", modified=None, **values):
		name = make_ticket(subject=subject, description=description).name
		frappe.db.set_value(
			"HD Ticket", name, {"status_category": "Resolved", "resolution_details": details, **values}
		)
		if modified:
			frappe.db.set_value("HD Ticket", name, "modified", modified, update_modified=False)
		return name

	def names(self, query, limit=read.MAX_SEARCH_LIMIT):
		result = read.search_resolved_tickets({"query": query, "limit": limit}, _ctx())
		self.assertTrue(result["ok"], result)
		return [row["name"] for row in result["tickets"]]

	def test_excluded_ticket_not_returned(self):
		# The two words are not side by side in the ticket: found only when each word is searched.
		subject, description = f"{self.word('may')} in hỏng", f"<p>Đã đổi {self.word('muc')}</p>"
		normal = self.resolved(subject, description)
		self.resolved(subject, description, agent_group=SEARCH_EXCLUDED_TEAM)
		self.resolved(subject, description, ai_opt_out=1)
		self.assertEqual(self.names(f"{self.word('may')} {self.word('muc')}"), [normal])

	def test_ranked_by_word_matches(self):
		one, two, three = self.word("one"), self.word("two"), self.word("three")
		newest_one = self.resolved(f"{one} máy", modified="2030-01-04 00:00:00")
		newer_two = self.resolved(f"{two} {one}", modified="2030-01-03 00:00:00")
		older_two = self.resolved(one, details=f"<p>{two}</p>", modified="2030-01-02 00:00:00")
		oldest_three = self.resolved(f"{one} {two}", f"<p>{three}</p>", modified="2030-01-01 00:00:00")
		self.assertEqual(self.names(f"{one} {two} {three}"), [oldest_three, newer_two, older_two, newest_one])

	def test_excluded_match_does_not_change_result_count(self):
		common, extra = self.word("chung"), self.word("them")
		normal = [
			self.resolved(f"{common} {index}", modified=f"2030-01-0{index + 1} 00:00:00")
			for index in range(3)
		]
		self.assertEqual(sorted(self.names(common, 3)), sorted(normal))
		# An excluded ticket matching more words is never listed and takes no place.
		self.resolved(f"{common} {extra}", agent_group=SEARCH_EXCLUDED_TEAM, modified="2030-02-01 00:00:00")
		self.assertEqual(sorted(self.names(f"{common} {extra}", 3)), sorted(normal))
		# Three newer excluded tickets do not fill the scan either.
		with patch.object(read, "SEARCH_SCAN_MAX", 3):
			for index in range(3):
				self.resolved(
					f"{common} {extra} {index}",
					agent_group=SEARCH_EXCLUDED_TEAM,
					modified=f"2030-03-0{index + 1} 00:00:00",
				)
			self.assertEqual(sorted(self.names(f"{common} {extra}", 3)), sorted(normal))

	def test_match_beyond_eighth_word_found(self):
		filler = " ".join(f"tu{index}" for index in range(10))
		late = self.word("cuoi")
		in_description = self.resolved(f"{self.word('dau')} máy", f"<p>{filler} {late}</p>")
		in_details = self.resolved("Máy in", f"<p>{filler}</p>", details=f"<p>{filler} {late}</p>")
		self.assertEqual(sorted(self.names(late)), sorted([in_description, in_details]))

	def test_words_of_adjacent_fields_not_joined(self):
		common, a, b, m, n, e, d = (self.word(suffix) for suffix in ("x", "a", "b", "m", "n", "e", "d"))
		# Glued without a space, subject|description gives a+b, two description blocks m+n, description|resolution
		# e+d. The older ticket holds each glued word as a real word.
		apart = self.resolved(
			f"{common} {a}", f"<p>{b} {m}</p><p>{n} {e}</p>", f"<p>{d}</p>", "2030-01-02 00:00:00"
		)
		joined = self.resolved(f"{common} {a}{b}", f"<p>{m}{n}</p>", f"<p>{e}{d}</p>", "2030-01-01 00:00:00")
		for glued in (f"{a}{b}", f"{m}{n}", f"{e}{d}"):
			with self.subTest(glued):
				# `apart` scores 1 (only `common`), so it ranks after the older `joined` (2).
				self.assertEqual(self.names(f"{common} {glued}"), [joined, apart])

	def test_word_with_underscore_found(self):
		word = f"{self.tag}_ma_loi"
		ticket = self.resolved(f"Lỗi {word} khi in")
		self.assertEqual(self.names(word), [ticket])

	def without_details(self, assigned):
		"""A resolved ticket with no resolution detail, assigned (ToDo rows, as Frappe assigns) to `assigned`."""
		name = self.resolved(f"{self.word('tim')} máy in", details="")
		for user in assigned:
			frappe.get_doc(
				{
					"doctype": "ToDo",
					"reference_type": "HD Ticket",
					"reference_name": name,
					"allocated_to": user,
					"description": "t154",
				}
			).insert(ignore_permissions=True)
		return name

	def comment(self, ticket, owner, content, creation, comment_type="Comment"):
		"""A comment of `owner` on the ticket at `creation`, saved without hooks."""
		frappe.get_doc(
			{
				"doctype": "Comment",
				"comment_type": comment_type,
				"reference_doctype": "HD Ticket",
				"reference_name": ticket,
				"content": content,
				"owner": owner,
				"creation": creation,
				"modified": creation,
			}
		).db_insert()

	def found(self, ticket):
		result = read.search_resolved_tickets({"query": self.word("tim")}, _ctx())
		self.assertTrue(result["ok"], result)
		return next(row for row in result["tickets"] if row["name"] == ticket)

	def test_empty_resolution_returns_resolver_comments(self):
		ticket = self.without_details([AGENT_A])
		contents = ("<p>c0</p>", "<p>c1</p>", "<p>Đã <b>thay</b> mực</p>", "<p>" + "a" * 2500 + "</p>")
		for index, content in enumerate(contents):
			self.comment(ticket, AGENT_A, content, f"2030-01-0{index + 1} 00:00:00")
		# Newer, but not a ticket comment, or not written by an assignee.
		self.comment(ticket, AGENT_A, "<p>hệ thống</p>", "2030-02-01 00:00:00", comment_type="Info")
		self.comment(ticket, INSTRUCTOR, "<p>không phụ trách</p>", "2030-02-02 00:00:00")
		row = self.found(ticket)
		self.assertEqual(set(row), RESULT_KEYS | {"resolver_comments"})
		self.assertEqual(row["resolution_details"], "")
		self.assertEqual(row["resolver_comments"], ["a" * read.COMMENT_MAX_CHARS, "Đã thay mực", "c1"])
		self.assertEqual(read.RESOLVER_COMMENTS_MAX, 3)
		# A ticket with a resolution detail has no such key.
		detailed = self.resolved(f"{self.word('tim')} khác")
		frappe.get_doc(
			{
				"doctype": "ToDo",
				"reference_type": "HD Ticket",
				"reference_name": detailed,
				"allocated_to": AGENT_A,
				"description": "t154",
			}
		).insert(ignore_permissions=True)
		self.comment(detailed, AGENT_A, "<p>c</p>", "2030-01-01 00:00:00")
		self.assertEqual(set(self.found(detailed)), RESULT_KEYS)

	def test_empty_resolution_no_comment(self):
		assigned = self.without_details([AGENT_A])
		self.comment(assigned, INSTRUCTOR, "<p>người khác</p>", "2030-01-01 00:00:00")
		unassigned = self.without_details([])
		self.comment(unassigned, AGENT_A, "<p>chưa giao</p>", "2030-01-01 00:00:00")
		for ticket in (assigned, unassigned):
			with self.subTest(ticket=ticket):
				self.assertEqual(self.found(ticket)["resolver_comments"], [])

	def test_bot_comments_excluded(self):
		ticket = self.without_details([AGENT_USER, AGENT_A])
		self.comment(ticket, AGENT_A, "<p>người phụ trách</p>", "2030-01-01 00:00:00")
		for index in range(3):
			self.comment(ticket, AGENT_USER, f"<p>bot {index}</p>", f"2030-01-0{index + 2} 00:00:00")
		self.assertEqual(self.found(ticket)["resolver_comments"], ["người phụ trách"])
		bot_only = self.without_details([AGENT_USER])
		self.comment(bot_only, AGENT_USER, "<p>bot</p>", "2030-01-01 00:00:00")
		self.assertEqual(self.found(bot_only)["resolver_comments"], [])
