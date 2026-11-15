import json

import frappe
from frappe.tests.utils import FrappeTestCase

from erp_ai.agent.changes import block, transitions
from erp_ai.agent.tools.change_guard import FileOp
from erp_ai.constants import CHANGE_KIND_CODE, CHANGE_KIND_COMMAND, PROPOSAL_DOCTYPE

UNKNOWN_KIND = "Loại lạ"
BEFORE = "x = 1\n"
AFTER = 'x = "Đã sửa"\n'
BASE_HASH = "b" * 64
AFTER_HASH = "a" * 64
ARGV = ["build", "--app", "myapp"]
# The 14 digest fields (design 2.3, ADR-012 QĐ 7) of a legacy file change and a legacy bench command,
# every one set, so the stored values are exactly those the pinned digests below were computed from.
LEGACY_CODE_FIELDS = {
	"change_kind": CHANGE_KIND_CODE,
	"app": "myapp",
	"file_path": "myapp/myapp/ok.py",
	"is_new_file": 0,
	"command_args": "",
	"base_hash": BASE_HASH,
	"content_before": BEFORE,
	"content_after": AFTER,
	"after_hash": AFTER_HASH,
	"target_branch": "main",
	"upstream_ref": "origin/main",
	"ahead_count": 2,
	"is_core_app": 1,
	"commit_message": "myapp: sửa ok.py\n\nNgười duyệt: <người duyệt>",
}
LEGACY_COMMAND_FIELDS = {
	"change_kind": CHANGE_KIND_COMMAND,
	"app": "myapp",
	"file_path": "",
	"is_new_file": 0,
	"command_args": json.dumps(ARGV),
	"base_hash": "",
	"content_before": "",
	"content_after": "",
	"after_hash": "",
	"target_branch": "",
	"upstream_ref": "",
	"ahead_count": 0,
	"is_core_app": 0,
	"commit_message": "",
}
# sha256 of json.dumps(<the 14 values above in DIGEST_FIELDS order>, ensure_ascii=False), computed by hand
# from the documented formula before T18 touched `content_digest`: an old approved proposal still matches.
LEGACY_CODE_DIGEST = "9722b100bd5969ba19030fb4d9cdfb6388442d1930b34295129d9cb09abe6d38"
LEGACY_COMMAND_DIGEST = "b03878cb26c7e7ee70f6a5e376937df7df6f35e72a12eb0f605af1d42d98d73a"


def _proposal(fields, **overrides):
	"""An in-memory proposal (never inserted), so no controller hook rewrites the given values."""
	return frappe.get_doc({"doctype": PROPOSAL_DOCTYPE, **fields, **overrides})


def _block_proposal(change_kind=CHANGE_KIND_CODE):
	return _proposal(
		{"change_kind": change_kind},
		operations=[
			{"idx": 2, "operation": "Tạo", "file_path": "myapp/myapp/new.py", "content_after": AFTER},
			{
				"idx": 1,
				"operation": "Sửa",
				"file_path": "myapp/myapp/ok.py",
				"content_before": BEFORE,
				"content_after": AFTER,
				"base_hash": BASE_HASH,
				"after_hash": AFTER_HASH,
			},
		],
		command_list=json.dumps([["--site", "miyano", "migrate"], ["restart"]]),
	)


class TestAdapter(FrappeTestCase):
	"""CHG-002 T18 (design 2.3, AC-42): an old single-file or single-command proposal read as a block."""

	def test_legacy_edit_one_op(self):
		doc = _proposal(LEGACY_CODE_FIELDS)
		self.assertFalse(block.is_block(doc))
		self.assertEqual(
			block.operations_of(doc),
			(
				FileOp(
					kind="Sửa",
					path="myapp/myapp/ok.py",
					new_path=None,
					before=BEFORE,
					after=AFTER,
					base_hash=BASE_HASH,
					after_hash=AFTER_HASH,
				),
			),
		)
		self.assertEqual(block.commands_of(doc), [])

	def test_legacy_new_file_one_create_op(self):
		doc = _proposal(LEGACY_CODE_FIELDS, is_new_file=1, content_before="", base_hash="")
		self.assertEqual(
			block.operations_of(doc),
			(
				FileOp(
					kind="Tạo",
					path="myapp/myapp/ok.py",
					new_path=None,
					before=None,
					after=AFTER,
					base_hash=None,
					after_hash=AFTER_HASH,
				),
			),
		)
		self.assertEqual(block.commands_of(doc), [])

	def test_legacy_edit_empty_contents_and_path(self):
		# Empty stored text stays the empty text of an edit; an empty path is not invented away.
		doc = _proposal(
			LEGACY_CODE_FIELDS, file_path=None, content_before=None, content_after=None, base_hash=None
		)
		self.assertEqual(
			block.operations_of(doc),
			(
				FileOp(
					kind="Sửa",
					path="",
					new_path=None,
					before="",
					after="",
					base_hash=None,
					after_hash=AFTER_HASH,
				),
			),
		)

	def test_legacy_command_one_argv(self):
		doc = _proposal(LEGACY_COMMAND_FIELDS)
		self.assertFalse(block.is_block(doc))
		self.assertEqual(block.operations_of(doc), ())
		self.assertEqual(block.commands_of(doc), [ARGV])

	def test_legacy_command_empty_args_no_command(self):
		for empty in ("", None):
			with self.subTest(command_args=empty):
				doc = _proposal(LEGACY_COMMAND_FIELDS, command_args=empty)
				self.assertEqual(block.operations_of(doc), ())
				self.assertEqual(block.commands_of(doc), [])

	def test_block_rows_in_idx_order(self):
		for kind in (CHANGE_KIND_CODE, CHANGE_KIND_COMMAND):
			with self.subTest(change_kind=kind):
				doc = _block_proposal(kind)
				self.assertTrue(block.is_block(doc))
				self.assertEqual(
					block.operations_of(doc),
					(
						FileOp(
							kind="Sửa",
							path="myapp/myapp/ok.py",
							new_path=None,
							before=BEFORE,
							after=AFTER,
							base_hash=BASE_HASH,
							after_hash=AFTER_HASH,
						),
						FileOp(
							kind="Tạo",
							path="myapp/myapp/new.py",
							new_path=None,
							before=None,
							after=AFTER,
							base_hash=None,
							after_hash=None,
						),
					),
				)
				self.assertEqual(block.commands_of(doc), [["--site", "miyano", "migrate"], ["restart"]])

	def test_unknown_change_kind_raises_value_error(self):
		shapes = {
			"legacy": _proposal(LEGACY_CODE_FIELDS, change_kind=UNKNOWN_KIND),
			"block": _block_proposal(UNKNOWN_KIND),
		}
		for shape, doc in shapes.items():
			for reader in (block.operations_of, block.commands_of):
				with self.subTest(shape=shape, reader=reader.__name__):
					with self.assertRaises(ValueError) as caught:
						reader(doc)
					self.assertEqual(
						str(caught.exception), "change_kind không hỗ trợ ở đường code: 'Loại lạ'"
					)


class TestLegacyDigest(FrappeTestCase):
	"""CHG-002 T18 (design 2.4, A3 RQ-5): the old shape's digest keeps its bytes and refuses other kinds."""

	def test_legacy_digest_is_byte_identical(self):
		for fields, expected in (
			(LEGACY_CODE_FIELDS, LEGACY_CODE_DIGEST),
			(LEGACY_COMMAND_FIELDS, LEGACY_COMMAND_DIGEST),
		):
			with self.subTest(change_kind=fields["change_kind"]):
				self.assertEqual(transitions.content_digest(_proposal(fields)), expected)

	def test_unknown_change_kind_legacy_digest_raises(self):
		doc = _proposal(LEGACY_CODE_FIELDS, change_kind=UNKNOWN_KIND)
		with self.assertRaises(ValueError) as caught:
			transitions.content_digest(doc)
		self.assertEqual(str(caught.exception), "change_kind không hỗ trợ ở đường code: 'Loại lạ'")

	def test_unknown_change_kind_block_digest_is_not_refused_here(self):
		# Branch order (A3 RQ-5): a block takes the block digest before any kind check.
		self.assertRegex(transitions.content_digest(_block_proposal(UNKNOWN_KIND)), r"^[0-9a-f]{64}$")
