import json

import frappe
from frappe.tests.utils import FrappeTestCase

from erp_ai.agent import change_text
from erp_ai.agent.change_text import (
	apply_message,
	message_text,
	proposal_notes,
	safe_person_name,
	undo_message,
)
from erp_ai.agent.tools.change_guard import FileOp
from erp_ai.constants import CHANGE_OP_CREATE, CHANGE_OP_DELETE, CHANGE_OP_EDIT, CHANGE_OP_RENAME


class TestChangeText(FrappeTestCase):
	def test_apply_message_template_and_preview(self):
		subject, body = apply_message("AICHG-00007", "HD-0042", "erp_ai/agent/policy.py", "Nguyễn Văn An")
		self.assertEqual(subject, "erp_ai: áp dụng AICHG-00007 (erp_ai/agent/policy.py)")
		self.assertEqual(
			body,
			"Đề xuất: AICHG-00007\n"
			"Phiếu: HD-0042\n"
			"Người duyệt: Nguyễn Văn An\n"
			"Commit do ERP AI Agent tạo sau khi người duyệt bấm Duyệt.",
		)
		self.assertEqual(
			message_text(subject, body),
			"erp_ai: áp dụng AICHG-00007 (erp_ai/agent/policy.py)\n"
			"\n"
			"Đề xuất: AICHG-00007\n"
			"Phiếu: HD-0042\n"
			"Người duyệt: Nguyễn Văn An\n"
			"Commit do ERP AI Agent tạo sau khi người duyệt bấm Duyệt.",
		)

		self.assertEqual(change_text.APPROVER_PLACEHOLDER, "<người duyệt>")
		preview = message_text(
			*apply_message("AICHG-00007", "HD-0042", "erp_ai/agent/policy.py", "<người duyệt>")
		)
		self.assertEqual(
			preview,
			"erp_ai: áp dụng AICHG-00007 (erp_ai/agent/policy.py)\n"
			"\n"
			"Đề xuất: AICHG-00007\n"
			"Phiếu: HD-0042\n"
			"Người duyệt: <người duyệt>\n"
			"Commit do ERP AI Agent tạo sau khi người duyệt bấm Duyệt.",
		)
		real = message_text(subject, body)
		self.assertEqual(
			[(a, b) for a, b in zip(preview.splitlines(), real.splitlines(), strict=True) if a != b],
			[("Người duyệt: <người duyệt>", "Người duyệt: Nguyễn Văn An")],
		)

	def test_undo_message_has_apply_commit_and_undoer(self):
		sha = "0123456789abcdef0123456789abcdef01234567"
		subject, body = undo_message(
			"AICHG-00007", "HD-0042", "erp_ai/agent/new_tool.py", sha, "Trần Thị Bình"
		)
		self.assertEqual(subject, "erp_ai: hoàn tác AICHG-00007 (erp_ai/agent/new_tool.py)")
		self.assertEqual(
			body,
			"Đề xuất: AICHG-00007\n"
			"Phiếu: HD-0042\n"
			"Commit áp dụng: 0123456789abcdef0123456789abcdef01234567\n"
			"Người hoàn tác: Trần Thị Bình\n"
			"Commit do ERP AI Agent tạo sau khi người hoàn tác bấm Hoàn tác.",
		)
		self.assertEqual(
			message_text(subject, body),
			"erp_ai: hoàn tác AICHG-00007 (erp_ai/agent/new_tool.py)\n"
			"\n"
			"Đề xuất: AICHG-00007\n"
			"Phiếu: HD-0042\n"
			"Commit áp dụng: 0123456789abcdef0123456789abcdef01234567\n"
			"Người hoàn tác: Trần Thị Bình\n"
			"Commit do ERP AI Agent tạo sau khi người hoàn tác bấm Hoàn tác.",
		)

	def test_safe_person_name(self):
		anonymous = "(không hiện tên)"
		self.assertEqual(change_text.ANONYMOUS_PERSON, anonymous)
		cases = [
			# plain name is kept
			("Nguyễn Văn An", "Nguyễn Văn An"),
			# '@' anywhere -> anonymous
			("an@example.com", anonymous),
			("Nguyễn @An", anonymous),
			# '://' -> anonymous
			("https://evil.example/x", anonymous),
			("An ftp://host", anonymous),
			# newlines become one space
			("Nguyễn\nVăn\r\nAn", "Nguyễn Văn An"),
			("Nguyen" + chr(0x2028) + "An", "Nguyen An"),
			# control characters become a space (NUL and BEL are not whitespace for str.split)
			("Nguyễn\x00Văn\x07An\x1b", "Nguyễn Văn An"),
			("Nguyễn\tAn", "Nguyễn An"),
			# whitespace collapsed and trimmed
			("   Nguyễn    Văn   An  ", "Nguyễn Văn An"),
			# cut to 80 characters
			("a" * 200, "a" * 80),
			("Đ" * 200, "Đ" * 80),
			# cut, then no trailing space
			("a" * 79 + " bcd", "a" * 79),
			# '@' or '://' after the 80th character still -> anonymous
			("a" * 100 + "@", anonymous),
			("a" * 100 + "://", anonymous),
			# empty, blank, only control characters, None -> anonymous
			("", anonymous),
			("   ", anonymous),
			("\n\x00\x07", anonymous),
			(None, anonymous),
		]
		for raw, expected in cases:
			with self.subTest(raw=raw):
				self.assertEqual(safe_person_name(raw), expected)


BRANCH_NOTE = "Commit sẽ vào nhánh develop của app helpdesk."
UPSTREAM_NOTE = (
	"Nhánh này theo origin/develop và đang đi trước 2 commit (tính theo lần fetch cuối trên máy chủ)."
)
NO_UPSTREAM_NOTE = "Nhánh này không theo nhánh remote nào."
CORE_WARNING_FRAPPE = (
	"Cảnh báo app lõi: frappe dùng chung cho mọi site trên bench này, nên thay đổi ảnh hưởng tất cả"
	" các site. bench update không giữ commit local: nó dừng nếu kho có thay đổi chưa commit; khi kho"
	" sạch, nó kéo bằng git pull (merge) từ remote upstream hoặc remote đầu tiên, có thể tạo merge"
	" commit hoặc xung đột; bench update --reset xóa vĩnh viễn commit chưa đẩy. Đẩy commit lên fork là"
	" việc của người, làm trước khi chạy bench update."
)
RESTART_NOTE = "Sau khi áp dụng cần người chạy bench restart."
COMMAND_NOTE = "Lệnh bench không hoàn tác được."
APPLY_SHA = "0123456789abcdef0123456789abcdef01234567"
UNDO_SHA = "fedcba9876543210fedcba9876543210fedcba98"
TOKEN_URL = "https://x-access-token:ghp_FAKE123@github.com/org/helpdesk.git"


def code_fields(**overrides):
	fields = {
		"change_kind": "Thay đổi code",
		"app": "helpdesk",
		"file_path": "helpdesk/helpdesk/hooks.js",
		"target_branch": "develop",
		"upstream_ref": "origin/develop",
		"ahead_count": 2,
		"is_core_app": 0,
		"change_status": "Chờ duyệt",
		"apply_commit_sha": "",
		"undo_commit_sha": "",
	}
	fields.update(overrides)
	return fields


class TestProposalNotes(FrappeTestCase):
	def test_notes_branch_upstream_and_core_warning(self):
		# non-core app tracking a remote: branch + upstream, no core warning
		self.assertEqual(proposal_notes(code_fields()), [BRANCH_NOTE, UPSTREAM_NOTE])
		# no upstream: the "no remote" sentence replaces the upstream one
		self.assertEqual(proposal_notes(code_fields(upstream_ref="")), [BRANCH_NOTE, NO_UPSTREAM_NOTE])
		self.assertEqual(
			proposal_notes(code_fields(upstream_ref=None, ahead_count=None)),
			[BRANCH_NOTE, NO_UPSTREAM_NOTE],
		)
		# ahead_count missing while an upstream is set -> 0
		self.assertEqual(
			proposal_notes(code_fields(ahead_count=None)),
			[
				BRANCH_NOTE,
				"Nhánh này theo origin/develop và đang đi trước 0 commit"
				" (tính theo lần fetch cuối trên máy chủ).",
			],
		)
		# core app: the warning with its 3 points comes after the branch sentences
		notes = proposal_notes(
			code_fields(
				app="frappe",
				file_path="frappe/frappe/hooks.js",
				target_branch="version-15",
				upstream_ref="upstream/version-15",
				ahead_count=1,
				is_core_app=1,
			)
		)
		self.assertEqual(
			notes,
			[
				"Commit sẽ vào nhánh version-15 của app frappe.",
				"Nhánh này theo upstream/version-15 và đang đi trước 1 commit"
				" (tính theo lần fetch cuối trên máy chủ).",
				CORE_WARNING_FRAPPE,
			],
		)
		self.assertIn("dùng chung cho mọi site trên bench này", notes[2])
		self.assertIn("bench update --reset xóa vĩnh viễn commit chưa đẩy", notes[2])
		self.assertIn("Đẩy commit lên fork là việc của người", notes[2])
		# core warning without an upstream
		self.assertEqual(
			proposal_notes(code_fields(app="frappe", upstream_ref="", is_core_app=1)),
			["Commit sẽ vào nhánh develop của app frappe.", NO_UPSTREAM_NOTE, CORE_WARNING_FRAPPE],
		)
		# is_core_app is the only trigger: a core-named app without the flag gets no warning
		self.assertEqual(
			proposal_notes(code_fields(app="frappe", is_core_app=0)),
			["Commit sẽ vào nhánh develop của app frappe.", UPSTREAM_NOTE],
		)

	def test_notes_skip_branch_sentences_when_branch_unknown(self):
		self.assertEqual(proposal_notes(code_fields(target_branch="")), [])
		self.assertEqual(proposal_notes(code_fields(target_branch=None, upstream_ref="")), [])

	def test_notes_commit_sentence_by_status(self):
		base = [BRANCH_NOTE, UPSTREAM_NOTE]
		applied = code_fields(change_status="Đã áp dụng", apply_commit_sha=APPLY_SHA)
		self.assertEqual(proposal_notes(applied), [*base, f"Commit áp dụng: {APPLY_SHA}."])
		undone = code_fields(
			change_status="Đã hoàn tác", apply_commit_sha=APPLY_SHA, undo_commit_sha=UNDO_SHA
		)
		self.assertEqual(proposal_notes(undone), [*base, f"Commit hoàn tác: {UNDO_SHA}."])
		# other states add no commit sentence even when both sha are filled
		for status in ("Chờ duyệt", "Đã duyệt", "Đang áp dụng", "Đang hoàn tác", "Lỗi", "Hết hiệu lực"):
			with self.subTest(status=status):
				fields = code_fields(
					change_status=status, apply_commit_sha=APPLY_SHA, undo_commit_sha=UNDO_SHA
				)
				self.assertEqual(proposal_notes(fields), base)
		# the right state with an empty sha adds nothing
		self.assertEqual(proposal_notes(code_fields(change_status="Đã áp dụng")), base)
		self.assertEqual(
			proposal_notes(code_fields(change_status="Đã hoàn tác", apply_commit_sha=APPLY_SHA)), base
		)

	def test_notes_python_file_needs_restart(self):
		self.assertEqual(
			proposal_notes(code_fields(file_path="helpdesk/helpdesk/api.py")),
			[BRANCH_NOTE, UPSTREAM_NOTE, RESTART_NOTE],
		)
		self.assertEqual(
			proposal_notes(
				code_fields(
					file_path="helpdesk/helpdesk/api.py",
					change_status="Đã áp dụng",
					apply_commit_sha=APPLY_SHA,
				)
			),
			[BRANCH_NOTE, UPSTREAM_NOTE, f"Commit áp dụng: {APPLY_SHA}.", RESTART_NOTE],
		)
		self.assertEqual(proposal_notes(code_fields(file_path=None)), [BRANCH_NOTE, UPSTREAM_NOTE])

	def test_notes_bench_command_and_unknown_kind(self):
		command = {
			"change_kind": "Lệnh bench",
			"app": "helpdesk",
			"file_path": "",
			"target_branch": "",
			"upstream_ref": "",
			"ahead_count": 0,
			"is_core_app": 0,
			"change_status": "Đã áp dụng",
			"apply_commit_sha": "",
			"undo_commit_sha": "",
		}
		self.assertEqual(proposal_notes(command), [COMMAND_NOTE])
		# no git or restart sentence for a command even if those fields were filled
		self.assertEqual(
			proposal_notes(
				{
					**command,
					"target_branch": "develop",
					"file_path": "helpdesk/helpdesk/api.py",
					"apply_commit_sha": APPLY_SHA,
				}
			),
			[COMMAND_NOTE],
		)
		self.assertEqual(proposal_notes(code_fields(change_kind="khác")), [])
		self.assertEqual(proposal_notes({}), [])

	def test_notes_never_contain_urls(self):
		# a URL in a shown field drops the sentence that would carry it
		self.assertEqual(proposal_notes(code_fields(upstream_ref=TOKEN_URL)), [BRANCH_NOTE])
		self.assertEqual(proposal_notes(code_fields(target_branch=TOKEN_URL)), [])
		self.assertEqual(proposal_notes(code_fields(app=TOKEN_URL, is_core_app=1)), [UPSTREAM_NOTE])
		self.assertEqual(
			proposal_notes(code_fields(change_status="Đã áp dụng", apply_commit_sha=TOKEN_URL)),
			[BRANCH_NOTE, UPSTREAM_NOTE],
		)
		self.assertEqual(
			proposal_notes(
				code_fields(
					change_status="Đã hoàn tác", apply_commit_sha=APPLY_SHA, undo_commit_sha=TOKEN_URL
				)
			),
			[BRANCH_NOTE, UPSTREAM_NOTE],
		)
		# every combination keeps "://" and the token out of every sentence
		for status in ("Chờ duyệt", "Đã áp dụng", "Đã hoàn tác"):
			for is_core in (0, 1):
				for upstream in ("origin/develop", "", TOKEN_URL):
					fields = code_fields(
						change_status=status,
						is_core_app=is_core,
						upstream_ref=upstream,
						apply_commit_sha=APPLY_SHA,
						undo_commit_sha=UNDO_SHA,
					)
					with self.subTest(status=status, is_core=is_core, upstream=upstream):
						notes = proposal_notes(fields)
						self.assertTrue(notes)
						text = "\n".join(notes)
						self.assertNotIn("://", text)
						self.assertNotIn("ghp_FAKE123", text)
						self.assertNotIn("github.com", text)


def file_op(kind, path, new_path=None):
	return FileOp(kind, path, new_path, None, None, None, None)


BLOCK_OPS = (
	file_op(CHANGE_OP_EDIT, "helpdesk/helpdesk/hooks.py"),
	file_op(CHANGE_OP_CREATE, "helpdesk/helpdesk/api/new.py"),
	file_op(CHANGE_OP_DELETE, "helpdesk/helpdesk/old.py"),
	file_op(CHANGE_OP_RENAME, "helpdesk/helpdesk/a.py", "helpdesk/helpdesk/b.py"),
)


class TestBlockMessage(FrappeTestCase):
	def test_none_operations_is_byte_identical_to_old(self):
		path = "erp_ai/agent/policy.py"
		self.assertEqual(
			apply_message("AICHG-00007", "HD-0042", path, "An", operations=None),
			apply_message("AICHG-00007", "HD-0042", path, "An"),
		)
		self.assertEqual(
			message_text(*apply_message("AICHG-00007", "HD-0042", path, "An", None)),
			"erp_ai: áp dụng AICHG-00007 (erp_ai/agent/policy.py)\n"
			"\n"
			"Đề xuất: AICHG-00007\n"
			"Phiếu: HD-0042\n"
			"Người duyệt: An\n"
			"Commit do ERP AI Agent tạo sau khi người duyệt bấm Duyệt.",
		)
		self.assertEqual(
			message_text(*undo_message("AICHG-00007", "HD-0042", path, APPLY_SHA, "Bình", operations=None)),
			"erp_ai: hoàn tác AICHG-00007 (erp_ai/agent/policy.py)\n"
			"\n"
			"Đề xuất: AICHG-00007\n"
			"Phiếu: HD-0042\n"
			f"Commit áp dụng: {APPLY_SHA}\n"
			"Người hoàn tác: Bình\n"
			"Commit do ERP AI Agent tạo sau khi người hoàn tác bấm Hoàn tác.",
		)

	def test_body_lists_each_item_after_ticket_line(self):
		items = (
			"sửa helpdesk/helpdesk/hooks.py\n"
			"tạo helpdesk/helpdesk/api/new.py\n"
			"xóa helpdesk/helpdesk/old.py\n"
			"đổi tên helpdesk/helpdesk/a.py → helpdesk/helpdesk/b.py\n"
		)
		subject, body = apply_message("AICHG-00009", "HD-0050", "4 file", "An", operations=BLOCK_OPS)
		self.assertEqual(subject, "erp_ai: áp dụng AICHG-00009 (4 file)")
		self.assertEqual(
			body,
			"Đề xuất: AICHG-00009\n"
			"Phiếu: HD-0050\n"
			f"{items}"
			"Người duyệt: An\n"
			"Commit do ERP AI Agent tạo sau khi người duyệt bấm Duyệt.",
		)
		subject, body = undo_message(
			"AICHG-00009", "HD-0050", "4 file", APPLY_SHA, "Bình", operations=BLOCK_OPS
		)
		self.assertEqual(subject, "erp_ai: hoàn tác AICHG-00009 (4 file)")
		self.assertEqual(
			body,
			"Đề xuất: AICHG-00009\n"
			"Phiếu: HD-0050\n"
			f"{items}"
			f"Commit áp dụng: {APPLY_SHA}\n"
			"Người hoàn tác: Bình\n"
			"Commit do ERP AI Agent tạo sau khi người hoàn tác bấm Hoàn tác.",
		)

	def test_label_path_or_n_files(self):
		self.assertEqual(change_text.block_label(BLOCK_OPS[:1]), "helpdesk/helpdesk/hooks.py")
		self.assertEqual(change_text.block_label([BLOCK_OPS[3]]), "helpdesk/helpdesk/a.py")
		self.assertEqual(change_text.block_label(BLOCK_OPS[:2]), "2 file")
		self.assertEqual(change_text.block_label(BLOCK_OPS), "4 file")


BLOCK_RESTART_NOTE = "Sau khi áp dụng, hệ thống sẽ restart bench (lệnh cuối)."
BLOCK_COMMANDS_NOTE = "Lệnh trong khối không hoàn tác được; hoàn tác chỉ trả lại phần file."
MIGRATE_COMMAND = ["--site", "miyano", "migrate"]


def op_row(idx, operation, file_path, new_path=""):
	return frappe._dict(idx=idx, operation=operation, file_path=file_path, new_path=new_path)


def block_fields(rows, commands, **overrides):
	"""Fields of a block proposal; `commands` is an argv list (stored as JSON) or a raw stored value."""
	fields = code_fields(
		file_path="",
		operations=list(rows),
		command_list=commands if commands is None or isinstance(commands, str) else json.dumps(commands),
	)
	fields.update(overrides)
	return fields


ONE_EDIT = [op_row(1, CHANGE_OP_EDIT, "helpdesk/helpdesk/hooks.py")]


class TestBlockNotes(FrappeTestCase):
	def test_counts_then_items_then_commands_in_order(self):
		# rows arrive out of `idx` order; the notes list them in `idx` order
		rows = [
			op_row(3, CHANGE_OP_DELETE, "helpdesk/helpdesk/old.py"),
			op_row(1, CHANGE_OP_EDIT, "helpdesk/helpdesk/hooks.py"),
			op_row(5, CHANGE_OP_EDIT, "helpdesk/helpdesk/api.py"),
			op_row(2, CHANGE_OP_CREATE, "helpdesk/helpdesk/api/new.py"),
			op_row(4, CHANGE_OP_RENAME, "helpdesk/helpdesk/a.py", "helpdesk/helpdesk/b.py"),
		]
		commands = [MIGRATE_COMMAND, ["build", "--app", "helpdesk"], ["restart"]]
		self.assertEqual(
			proposal_notes(block_fields(rows, commands)),
			[
				"Gồm 2 sửa, 1 tạo, 1 xóa, 1 đổi tên; 3 lệnh.",
				"sửa helpdesk/helpdesk/hooks.py",
				"tạo helpdesk/helpdesk/api/new.py",
				"XÓA helpdesk/helpdesk/old.py",
				"ĐỔI TÊN helpdesk/helpdesk/a.py → helpdesk/helpdesk/b.py",
				"sửa helpdesk/helpdesk/api.py",
				"lệnh: bench --site miyano migrate",
				"lệnh: bench build --app helpdesk",
				"lệnh: bench restart",
				BLOCK_RESTART_NOTE,
				BLOCK_COMMANDS_NOTE,
				BRANCH_NOTE,
				UPSTREAM_NOTE,
			],
		)
		# one item, no command: count line, the item, then the branch sentences
		self.assertEqual(
			proposal_notes(block_fields(ONE_EDIT, [])),
			[
				"Gồm 1 sửa, 0 tạo, 0 xóa, 0 đổi tên; 0 lệnh.",
				"sửa helpdesk/helpdesk/hooks.py",
				BRANCH_NOTE,
				UPSTREAM_NOTE,
			],
		)
		# the core warning and the commit sentence keep their place after the block lines
		self.assertEqual(
			proposal_notes(
				block_fields(
					ONE_EDIT,
					[MIGRATE_COMMAND],
					app="frappe",
					upstream_ref="",
					is_core_app=1,
					change_status="Đã áp dụng",
					apply_commit_sha=APPLY_SHA,
				)
			),
			[
				"Gồm 1 sửa, 0 tạo, 0 xóa, 0 đổi tên; 1 lệnh.",
				"sửa helpdesk/helpdesk/hooks.py",
				"lệnh: bench --site miyano migrate",
				BLOCK_COMMANDS_NOTE,
				"Commit sẽ vào nhánh develop của app frappe.",
				NO_UPSTREAM_NOTE,
				CORE_WARNING_FRAPPE,
				f"Commit áp dụng: {APPLY_SHA}.",
			],
		)

	def test_restart_line_iff_restart_listed(self):
		# commands without restart: no restart line, the not-undoable line stays
		self.assertEqual(
			proposal_notes(block_fields(ONE_EDIT, [["build", "--app", "helpdesk"]])),
			[
				"Gồm 1 sửa, 0 tạo, 0 xóa, 0 đổi tên; 1 lệnh.",
				"sửa helpdesk/helpdesk/hooks.py",
				"lệnh: bench build --app helpdesk",
				BLOCK_COMMANDS_NOTE,
				BRANCH_NOTE,
				UPSTREAM_NOTE,
			],
		)
		# a .py item without restart listed: no restart line (D-4 follows the list, not the extension)
		self.assertNotIn(BLOCK_RESTART_NOTE, proposal_notes(block_fields(ONE_EDIT, [MIGRATE_COMMAND])))
		# a commands-only block with just restart (R-6): the restart line shows, no branch sentence
		self.assertEqual(
			proposal_notes(
				block_fields([], [["restart"]], change_kind="Lệnh bench", target_branch="", upstream_ref="")
			),
			[
				"Gồm 0 sửa, 0 tạo, 0 xóa, 0 đổi tên; 1 lệnh.",
				"lệnh: bench restart",
				BLOCK_RESTART_NOTE,
				BLOCK_COMMANDS_NOTE,
			],
		)
		# the restart line shows once, right after the last command line
		notes = proposal_notes(block_fields(ONE_EDIT, [MIGRATE_COMMAND, ["restart"]]))
		self.assertEqual(notes.count(BLOCK_RESTART_NOTE), 1)
		self.assertEqual(notes.index(BLOCK_RESTART_NOTE), notes.index("lệnh: bench restart") + 1)

	def test_commands_not_undoable_line(self):
		no_command = [
			"Gồm 1 sửa, 0 tạo, 0 xóa, 0 đổi tên; 0 lệnh.",
			"sửa helpdesk/helpdesk/hooks.py",
			BRANCH_NOTE,
			UPSTREAM_NOTE,
		]
		# empty, missing, empty-list or malformed command_list: no command, no not-undoable line
		for command_list in ("[]", "", None, "not json", '{"args": ["restart"]}'):
			with self.subTest(command_list=command_list):
				self.assertEqual(proposal_notes(block_fields(ONE_EDIT, command_list)), no_command)
		# a commands-only block gets the block line, not the old "Lệnh bench không hoàn tác được."
		self.assertEqual(
			proposal_notes(
				block_fields(
					[],
					[MIGRATE_COMMAND, ["build", "--app", "helpdesk"]],
					change_kind="Lệnh bench",
					target_branch="",
					upstream_ref="",
				)
			),
			[
				"Gồm 0 sửa, 0 tạo, 0 xóa, 0 đổi tên; 2 lệnh.",
				"lệnh: bench --site miyano migrate",
				"lệnh: bench build --app helpdesk",
				BLOCK_COMMANDS_NOTE,
			],
		)

	def test_legacy_py_note_only_for_legacy(self):
		# a block with .py items never carries the old sentence, even with a legacy file_path left over
		for commands in ([], [MIGRATE_COMMAND, ["restart"]]):
			with self.subTest(commands=commands):
				notes = proposal_notes(
					block_fields(
						[op_row(1, CHANGE_OP_CREATE, "helpdesk/helpdesk/api/new.py")],
						commands,
						file_path="helpdesk/helpdesk/api/new.py",
					)
				)
				self.assertNotIn(RESTART_NOTE, notes)
		# the legacy shape (no rows, no command_list) keeps exactly the old output
		for empty in ({}, {"operations": [], "command_list": ""}, {"operations": None, "command_list": None}):
			with self.subTest(empty=empty):
				self.assertEqual(
					proposal_notes(code_fields(file_path="helpdesk/helpdesk/api.py", **empty)),
					[BRANCH_NOTE, UPSTREAM_NOTE, RESTART_NOTE],
				)
				self.assertEqual(
					proposal_notes({"change_kind": "Lệnh bench", "app": "helpdesk", **empty}),
					[COMMAND_NOTE],
				)

	def test_no_remote_url(self):
		rows = [
			op_row(1, CHANGE_OP_EDIT, "helpdesk/helpdesk/hooks.py"),
			op_row(2, CHANGE_OP_RENAME, "helpdesk/helpdesk/a.py", "helpdesk/helpdesk/b.py"),
		]
		commands = [MIGRATE_COMMAND, ["restart"]]
		# a URL in the remote drops only the upstream sentence; the block lines stay whole
		self.assertEqual(
			proposal_notes(block_fields(rows, commands, upstream_ref=TOKEN_URL)),
			[
				"Gồm 1 sửa, 0 tạo, 0 xóa, 1 đổi tên; 2 lệnh.",
				"sửa helpdesk/helpdesk/hooks.py",
				"ĐỔI TÊN helpdesk/helpdesk/a.py → helpdesk/helpdesk/b.py",
				"lệnh: bench --site miyano migrate",
				"lệnh: bench restart",
				BLOCK_RESTART_NOTE,
				BLOCK_COMMANDS_NOTE,
				BRANCH_NOTE,
			],
		)
		for overrides in (
			{"upstream_ref": TOKEN_URL},
			{"target_branch": TOKEN_URL},
			{"app": TOKEN_URL, "is_core_app": 1},
			{"change_status": "Đã áp dụng", "apply_commit_sha": TOKEN_URL},
		):
			with self.subTest(**overrides):
				text = "\n".join(proposal_notes(block_fields(rows, commands, **overrides)))
				self.assertNotIn("://", text)
				self.assertNotIn("ghp_FAKE123", text)
				self.assertNotIn("github.com", text)
