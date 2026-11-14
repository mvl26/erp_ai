"""Generic record tools: the agent account reads, creates and updates records through Frappe permissions.

Granted by the `site_admin` row of the registry grant table. With `ctx.unrestricted` (the unrestricted switch
of ERP AI Setting) the role, account and DocType limits are lifted and the `site_unrestricted` tools delete,
submit, cancel and call whitelisted methods. The app's own DocTypes and secret fields stay closed in every mode.
"""

import json

import frappe
from frappe.utils import strip_html

from erp_ai.agent.tools import read
from erp_ai.agent.tools.registry import ToolContext, ToolSpec
from erp_ai.constants import AGENT_USER, ROLE_AGENT, ROLE_INSTRUCTOR

GROUP = "site_admin"
UNRESTRICTED_GROUP = "site_unrestricted"
OWN_APP_PREFIX = "erp_ai."
SAVEPOINT = "erp_ai_site_api"
USER_DOCTYPE = "User"
ROLE_PROFILE_DOCTYPE = "Role Profile"
ROLE_DOCTYPE = "Role"
DOCTYPE_DOCTYPE = "DocType"
# Changing these grants permissions the way a forbidden role would: denied unless the unrestricted switch is on.
PERMISSION_DOCTYPES = frozenset({"Custom Role", "Custom DocPerm", DOCTYPE_DOCTYPE, ROLE_DOCTYPE})
# Roles that would let an account command the bot or administer the site; never assignable here.
FORBIDDEN_ROLES = frozenset({"System Manager", "Administrator", ROLE_INSTRUCTOR, ROLE_AGENT, "Guest", "All"})
PROTECTED_USERS = frozenset({"Administrator", "Guest", AGENT_USER})
SECRET_FIELDS = frozenset({"new_password", "api_key", "api_secret", "reset_password_key"})
# Whitelisted methods that hand back keys or passwords; `call_method` refuses them before the call.
SECRET_METHODS = frozenset(
	{
		"frappe.core.doctype.user.user.generate_keys",
		"frappe.client.get_password",
		"frappe.utils.password.get_decrypted_password",
		"frappe.utils.backups.get_backup_encryption_key",
		"frappe.integrations.oauth2.get_token",
	}
)
# A method whose last dotted segment holds one of these is refused too.
SECRET_METHOD_WORDS = ("password", "generate_keys", "secret")
SECRET_METHOD_REASON = "hàm này trả khóa API hoặc mật khẩu, không gọi qua công cụ"
# Keys whose value never reaches the model in a `call_method` result, compared casefolded.
SECRET_RESULT_KEYS = frozenset(
	key.casefold()
	for key in SECRET_FIELDS
	| {"password", "secret", "token", "access_token", "refresh_token", "client_secret", "encryption_key"}
)
SCRUBBED_VALUE = "[đã ẩn]"
SYSTEM_FIELDS = frozenset(
	{"doctype", "docstatus", "owner", "creation", "modified", "modified_by", "idx", "parent", "parenttype"}
)
# Records that run code or call out are always saved switched off; a person switches them on.
FORCED_VALUES = {"Server Script": {"disabled": 1}, "Webhook": {"enabled": 0}}
FILTER_OPERATORS = frozenset({"=", "!=", "like", "not like", "in", "not in", ">", "<", ">=", "<=", "is"})
REASON_MAX = 300
TITLE_WRITE_FAILED = "erp_ai: công cụ bản ghi lưu lỗi"
UNEXPECTED_ERROR_REASON = "lỗi hệ thống khi lưu, không có gì thay đổi"
DOCTYPE_ECHO_MAX = 80
DEFAULT_LIMIT = 20
MAX_LIMIT = 50
MAX_FIELDS = 20
MAX_FILTERS = 10
NAME_MAX = 140
# Before/after values of a write: each value cut to VALUE_MAX characters; a deleted record shows at most
# DELETED_FIELDS_MAX of its non-empty fields.
VALUE_MAX = 200
DELETED_FIELDS_MAX = 20


def _fail(reason: str, doctype=None) -> dict:
	result = {"ok": False, "reason": reason[:REASON_MAX]}
	if doctype is not None:
		result["doctype"] = str(doctype)[:DOCTYPE_ECHO_MAX]
	return result


def always_denied_doctypes() -> frozenset:
	"""Closed in every mode: every DocType of the app's module, read at call time, so a new one is closed too.
	The bot never changes its own switches, keys, audit log or change proposals."""
	return frozenset(frappe.get_all("DocType", {"module": read.AI_MODULE}, pluck="name"))


def _denied_doctypes(ctx: ToolContext) -> frozenset:
	if ctx.unrestricted:
		return always_denied_doctypes()
	# The read tool hides User from the model; these tools manage users, so only User is taken off that list.
	return frozenset(read.denied_doctypes() - {USER_DOCTYPE}) | PERMISSION_DOCTYPES


def _stored_name(doctype: str, name):
	"""The name as stored when the record exists (MariaDB matches names case-insensitively), else the name given."""
	if not isinstance(name, str) or not name:
		return name
	return frappe.db.get_value(doctype, name, "name") or name


def _named_in(name, names) -> bool:
	"""Case-insensitive membership: `name` should already be the stored name where one exists."""
	return isinstance(name, str) and name.casefold() in {item.casefold() for item in names}


def _doctype_refusal(doctype: str, ctx: ToolContext) -> dict | None:
	if _named_in(doctype, _denied_doctypes(ctx)):
		return _fail("DocType này không được phép dùng qua công cụ", doctype)
	if not frappe.db.exists("DocType", doctype):
		return _fail("không tìm thấy DocType", doctype)
	if frappe.get_meta(doctype).istable:
		return _fail("DocType là bảng con, hãy sửa qua bản ghi cha", doctype)
	return None


def _is_secret(meta, fieldname: str) -> bool:
	field = meta.get_field(fieldname)
	return fieldname in SECRET_FIELDS or bool(field and field.fieldtype == "Password")


def _forced_values(doctype: str, ctx: ToolContext) -> dict:
	return {} if ctx.unrestricted else FORCED_VALUES.get(doctype, {})


def _is_draft(doc) -> bool:
	return doc.docstatus == 0


def _profile_roles(profile) -> list[str]:
	stored = isinstance(profile, str) and frappe.db.exists(ROLE_PROFILE_DOCTYPE, profile)
	if not stored:
		return []
	return [row.role for row in frappe.get_doc(ROLE_PROFILE_DOCTYPE, stored).roles]


def _wanted_roles(doctype: str, values: dict) -> list | None:
	"""Every role the values would grant, Role Profiles expanded; None when a row has the wrong shape."""
	if doctype not in (USER_DOCTYPE, ROLE_PROFILE_DOCTYPE):
		return []
	rows = values.get("roles") or []
	profile_rows = values.get("role_profiles") or [] if doctype == USER_DOCTYPE else []
	if not all(isinstance(row, dict) for row in [*rows, *profile_rows]):
		return None
	roles = [row.get("role") for row in rows]
	if doctype == USER_DOCTYPE:
		profiles = [values.get("role_profile_name"), *(row.get("role_profile") for row in profile_rows)]
		for profile in profiles:
			roles.extend(_profile_roles(profile))
	return roles


def _values_refusal(doctype: str, values: dict, ctx: ToolContext) -> dict | None:
	meta = frappe.get_meta(doctype)
	for key in values:
		if key in SYSTEM_FIELDS or _is_secret(meta, key):
			return _fail(f"trường không được ghi qua công cụ: {key}", doctype)
		if key != "name" and not meta.has_field(key):
			return _fail(f"DocType không có trường: {key}", doctype)
	if ctx.unrestricted:
		return None
	roles = _wanted_roles(doctype, values)
	if roles is None:
		return _fail("mỗi dòng của roles / role_profiles phải là một object", doctype)
	stored_roles = {_stored_name(ROLE_DOCTYPE, role) for role in roles}
	forbidden = sorted(role for role in stored_roles if _named_in(role, FORBIDDEN_ROLES))
	if forbidden:
		return _fail(f"vai trò không được gán qua công cụ: {', '.join(forbidden)}", doctype)
	return None


def _shown_value(value):
	if value is None or isinstance(value, bool | int | float):
		return value
	text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, default=str)
	return text[:VALUE_MAX]


def _shown(doc, keys) -> dict:
	"""The value of each key as held by `doc`, secret and system fields left out, each cut to VALUE_MAX."""
	record = doc.as_dict()
	return {
		key: _shown_value(record.get(key))
		for key in keys
		if key not in SYSTEM_FIELDS and not _is_secret(doc.meta, key)
	}


def _deleted_values(doc) -> dict:
	"""The non-empty fields of a record about to be deleted, at most DELETED_FIELDS_MAX."""
	filled = [key for key, value in doc.as_dict().items() if value not in (None, "", [])]
	return dict(list(_shown(doc, filled).items())[:DELETED_FIELDS_MAX])


def _write(doctype: str, save) -> dict:
	"""Run `save` (returns the name, the value before and the value after) in its own savepoint; a refused write
	leaves nothing behind."""
	frappe.db.savepoint(SAVEPOINT)
	try:
		name, value_before, value_after = save()
	except frappe.PermissionError:
		frappe.db.rollback(save_point=SAVEPOINT)
		return _fail("thiếu quyền trên DocType hoặc bản ghi này", doctype)
	except frappe.ValidationError as exc:
		frappe.db.rollback(save_point=SAVEPOINT)
		detail = strip_html(str(exc)).strip() or type(exc).__name__
		return _fail(f"hệ thống từ chối: {detail}", doctype)
	except Exception as exc:
		# DuplicateEntryError, TypeError, hook errors: undo the partial write; only the error type reaches Error Log.
		frappe.db.rollback(save_point=SAVEPOINT)
		frappe.log_error(TITLE_WRITE_FAILED, f"site_api doctype={doctype} error={type(exc).__name__}")
		if isinstance(exc, frappe.DuplicateEntryError):
			return _fail("đã có bản ghi cùng tên", doctype)
		return _fail(UNEXPECTED_ERROR_REASON, doctype)
	frappe.db.release_savepoint(SAVEPOINT)
	return {
		"ok": True,
		"doctype": doctype,
		"name": name,
		"value_before": value_before,
		"value_after": value_after,
	}


def create_record(args: dict, ctx: ToolContext) -> dict:
	doctype, values = _stored_name(DOCTYPE_DOCTYPE, args["doctype"]), args["values"]
	if refusal := _doctype_refusal(doctype, ctx) or _values_refusal(doctype, values, ctx):
		return refusal

	def save():
		written = {**values, **_forced_values(doctype, ctx)}
		doc = frappe.get_doc({**written, "doctype": doctype}).insert()
		return doc.name, None, _shown(doc, written)

	return _write(doctype, save)


def update_record(args: dict, ctx: ToolContext) -> dict:
	doctype, name, values = _stored_name(DOCTYPE_DOCTYPE, args["doctype"]), args["name"], args["values"]
	if refusal := _doctype_refusal(doctype, ctx) or _values_refusal(doctype, values, ctx):
		return refusal
	if "name" in values:
		return _fail("không đổi tên bản ghi qua công cụ: name", doctype)
	protected = () if ctx.unrestricted else PROTECTED_USERS | {ctx.agent_user}
	if doctype == USER_DOCTYPE and _named_in(_stored_name(USER_DOCTYPE, name), protected):
		return _fail("tài khoản này không được sửa qua công cụ", doctype)
	if not frappe.get_meta(doctype).issingle and not frappe.db.exists(doctype, name):
		return _fail("không tìm thấy bản ghi", doctype)

	def save():
		doc = frappe.get_doc(doctype, name)
		if not _is_draft(doc):
			frappe.throw("chứng từ đã submit hoặc đã hủy, không sửa qua công cụ")
		written = {**values, **_forced_values(doctype, ctx)}
		value_before = _shown(doc, written)
		doc.update(written)
		doc.save()
		return doc.name, value_before, _shown(doc, written)

	return _write(doctype, save)


def _existing_refusal(doctype: str, name: str, ctx: ToolContext) -> dict | None:
	if refusal := _doctype_refusal(doctype, ctx):
		return refusal
	if not frappe.db.exists(doctype, name):
		return _fail("không tìm thấy bản ghi", doctype)
	return None


def delete_record(args: dict, ctx: ToolContext) -> dict:
	doctype, name = _stored_name(DOCTYPE_DOCTYPE, args["doctype"]), args["name"]
	if refusal := _existing_refusal(doctype, name, ctx):
		return refusal

	def delete():
		value_before = _deleted_values(frappe.get_doc(doctype, name))
		frappe.delete_doc(doctype, name)
		return name, value_before, None

	return _write(doctype, delete)


def _is_submittable(doctype: str) -> bool:
	return bool(frappe.get_meta(doctype).is_submittable)


def submit_record(args: dict, ctx: ToolContext) -> dict:
	doctype, name, action = _stored_name(DOCTYPE_DOCTYPE, args["doctype"]), args["name"], args["action"]
	if refusal := _existing_refusal(doctype, name, ctx):
		return refusal
	if not _is_submittable(doctype):
		return _fail("DocType này không submit được", doctype)

	def run():
		doc = frappe.get_doc(doctype, name)
		value_before = {"docstatus": doc.docstatus}
		getattr(doc, action)()
		return doc.name, value_before, {"docstatus": doc.docstatus}

	return _write(doctype, run)


def _is_secret_method(method: str) -> bool:
	last_segment = method.rsplit(".", 1)[-1].casefold()
	return method in SECRET_METHODS or any(word in last_segment for word in SECRET_METHOD_WORDS)


def _parsed(value):
	"""`value` with every string that parses as a JSON object or array replaced by its parsed form, recursively."""
	if isinstance(value, str):
		try:
			loaded = json.loads(value)
		except ValueError:
			return value
		return _parsed(loaded) if isinstance(loaded, dict | list) else value
	if isinstance(value, dict):
		return {str(key): _parsed(item) for key, item in value.items()}
	if isinstance(value, list | tuple):
		return [_parsed(item) for item in value]
	return value


def _scrub(value):
	"""`value` with the value of every key in SECRET_RESULT_KEYS replaced, in nested dicts, lists and tuples."""
	if isinstance(value, dict):
		return {
			key: SCRUBBED_VALUE
			if isinstance(key, str) and key.casefold() in SECRET_RESULT_KEYS
			else _scrub(item)
			for key, item in value.items()
		}
	if isinstance(value, list | tuple):
		return [_scrub(item) for item in value]
	return value


def _method_refusal(method: str, arguments: dict) -> dict | None:
	"""Early refusal only: the app's DocTypes are closed for the agent account by their controllers."""
	if method.startswith(OWN_APP_PREFIX):
		return _fail("không gọi hàm của erp_ai qua công cụ")
	if _is_secret_method(method):
		return _fail(SECRET_METHOD_REASON)
	text = json.dumps(_parsed(arguments), ensure_ascii=False, default=str).casefold()
	if any(doctype.casefold() in text for doctype in always_denied_doctypes()):
		return _fail("tham số nhắc tới DocType không được phép dùng qua công cụ")
	return None


def call_method(args: dict, ctx: ToolContext) -> dict:
	method, arguments = args["method"], args.get("arguments") or {}
	if refusal := _method_refusal(method, arguments):
		return refusal
	try:
		function = frappe.get_attr(method)
		frappe.is_whitelisted(function)
	except Exception:
		return _fail("không phải hàm whitelist gọi được")
	outcome = {}

	def run():
		outcome["result"] = frappe.call(function, **arguments)
		# The record the method touched is unknown: only the call itself is shown.
		return method, None, {"method": method, "argument_keys": sorted(arguments)}

	written = _write(None, run)
	if not written["ok"]:
		return written
	return {
		"ok": True,
		"method": method,
		"result": _scrub(outcome["result"]),
		"value_before": written["value_before"],
		"value_after": written["value_after"],
	}


def get_record(args: dict, ctx: ToolContext) -> dict:
	doctype, name = _stored_name(DOCTYPE_DOCTYPE, args["doctype"]), args["name"]
	if refusal := _doctype_refusal(doctype, ctx):
		return refusal
	meta = frappe.get_meta(doctype)
	if not meta.issingle and not frappe.db.exists(doctype, name):
		return _fail("không tìm thấy bản ghi", doctype)
	doc = frappe.get_doc(doctype, name)
	if not doc.has_permission("read"):
		return _fail("thiếu quyền đọc bản ghi này", doctype)
	doc.apply_fieldlevel_read_permissions()
	record = {key: value for key, value in doc.as_dict().items() if not _is_secret(meta, key)}
	return {"ok": True, "doctype": doctype, "record": record}


def _is_scalar(value) -> bool:
	return isinstance(value, str | int | float | bool)


def _filter_ok(row, columns: set) -> bool:
	if not isinstance(row, list) or len(row) != 3:
		return False
	field, operator, value = row
	if field not in columns or operator not in FILTER_OPERATORS:
		return False
	if operator in ("in", "not in"):
		return isinstance(value, list) and all(_is_scalar(item) for item in value)
	return _is_scalar(value)


def list_records(args: dict, ctx: ToolContext) -> dict:
	doctype = _stored_name(DOCTYPE_DOCTYPE, args["doctype"])
	if refusal := _doctype_refusal(doctype, ctx):
		return refusal
	meta = frappe.get_meta(doctype)
	if meta.issingle:
		return _fail("DocType đơn, hãy dùng api_get_record", doctype)
	columns = {column for column in meta.get_valid_columns() if not _is_secret(meta, column)}
	fields = args.get("fields") or ["name"]
	filters = args.get("filters") or []
	bad_field = next((field for field in fields if field not in columns), None)
	if bad_field is not None:
		return _fail(f"trường không đọc được: {bad_field}", doctype)
	if not all(_filter_ok(row, columns) for row in filters):
		return _fail(
			"filters phải là danh sách [trường, toán tử, giá trị] với trường và toán tử hợp lệ", doctype
		)
	try:
		rows = frappe.get_list(
			doctype,
			filters=filters,
			fields=fields,
			limit_page_length=args.get("limit", DEFAULT_LIMIT),
			order_by="modified desc",
		)
	except frappe.PermissionError:
		return _fail("thiếu quyền đọc DocType này", doctype)
	return {"ok": True, "doctype": doctype, "records": [dict(row) for row in rows]}


_DOCTYPE = {"type": "string", "minLength": 1, "maxLength": NAME_MAX}
_NAME = {"type": "string", "minLength": 1, "maxLength": NAME_MAX}
_VALUES_NOTE = (
	"values là object {tên trường: giá trị}; bảng con là mảng các object và thay toàn bộ các dòng cũ. "
	"Không nhận mật khẩu, khóa API, docstatus. Không gán được System Manager, Administrator, "
	"ERP AI Instructor, ERP AI Agent. Server Script và Webhook luôn được lưu ở trạng thái tắt."
)

TOOLS: list[ToolSpec] = [
	ToolSpec(
		name="api_list_records",
		group=GROUP,
		schema={
			"name": "api_list_records",
			"description": (
				"Liệt kê bản ghi của một DocType theo quyền của tài khoản agent. "
				"filters là mảng các bộ ba [trường, toán tử, giá trị]; fields mặc định chỉ có name."
			),
			"input_schema": {
				"type": "object",
				"properties": {
					"doctype": _DOCTYPE,
					"filters": {"type": "array", "maxItems": MAX_FILTERS, "items": {"type": "array"}},
					"fields": {"type": "array", "maxItems": MAX_FIELDS, "items": {"type": "string"}},
					"limit": {"type": "integer", "minimum": 1, "maximum": MAX_LIMIT},
				},
				"required": ["doctype"],
			},
		},
		handler=list_records,
	),
	ToolSpec(
		name="api_get_record",
		group=GROUP,
		schema={
			"name": "api_get_record",
			"description": (
				"Đọc một bản ghi bất kỳ theo quyền của tài khoản agent, gồm cả bảng con. "
				"Với DocType đơn (ví dụ System Settings), name là tên DocType."
			),
			"input_schema": {
				"type": "object",
				"properties": {"doctype": _DOCTYPE, "name": _NAME},
				"required": ["doctype", "name"],
			},
		},
		handler=get_record,
	),
	ToolSpec(
		name="api_create_record",
		group=GROUP,
		schema={
			"name": "api_create_record",
			"description": (
				"Tạo một bản ghi mới của DocType bất kỳ (User, Custom Field, Property Setter, Workflow…) "
				"theo quyền của tài khoản agent. " + _VALUES_NOTE
			),
			"input_schema": {
				"type": "object",
				"properties": {"doctype": _DOCTYPE, "values": {"type": "object"}},
				"required": ["doctype", "values"],
			},
		},
		handler=create_record,
	),
	ToolSpec(
		name="api_update_record",
		group=GROUP,
		schema={
			"name": "api_update_record",
			"description": (
				"Sửa các trường nêu trong values của một bản ghi nháp, các trường khác giữ nguyên. "
				"Không sửa chứng từ đã submit, không đổi tên bản ghi. " + _VALUES_NOTE
			),
			"input_schema": {
				"type": "object",
				"properties": {"doctype": _DOCTYPE, "name": _NAME, "values": {"type": "object"}},
				"required": ["doctype", "name", "values"],
			},
		},
		handler=update_record,
	),
	ToolSpec(
		name="api_delete_record",
		group=UNRESTRICTED_GROUP,
		schema={
			"name": "api_delete_record",
			"description": "Xóa một bản ghi theo quyền của tài khoản agent. Không hoàn tác được.",
			"input_schema": {
				"type": "object",
				"properties": {"doctype": _DOCTYPE, "name": _NAME},
				"required": ["doctype", "name"],
			},
		},
		handler=delete_record,
	),
	ToolSpec(
		name="api_submit_record",
		group=UNRESTRICTED_GROUP,
		schema={
			"name": "api_submit_record",
			"description": "Submit hoặc hủy (cancel) một chứng từ theo quyền của tài khoản agent.",
			"input_schema": {
				"type": "object",
				"properties": {
					"doctype": _DOCTYPE,
					"name": _NAME,
					"action": {"type": "string", "enum": ["submit", "cancel"]},
				},
				"required": ["doctype", "name", "action"],
			},
		},
		handler=submit_record,
	),
	ToolSpec(
		name="api_call_method",
		group=UNRESTRICTED_GROUP,
		schema={
			"name": "api_call_method",
			"description": (
				"Gọi một hàm whitelist của Frappe hoặc app khác bằng đường dẫn Python đầy đủ "
				"(ví dụ frappe.client.get_value), arguments là object tham số. Không gọi được hàm của erp_ai hay hàm trả khóa API, mật khẩu; "
				"giá trị khóa và mật khẩu trong kết quả được ẩn."
			),
			"input_schema": {
				"type": "object",
				"properties": {
					"method": {"type": "string", "minLength": 3, "maxLength": 200},
					"arguments": {"type": "object"},
				},
				"required": ["method"],
			},
		},
		handler=call_method,
	),
]
