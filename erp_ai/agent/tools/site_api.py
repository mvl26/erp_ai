"""Generic record tools: the agent account reads, creates and updates records through Frappe permissions.

Granted by the `site_admin` row of the registry grant table. With `ctx.unrestricted` (the unrestricted switch
of ERP AI Setting) the role, account and DocType limits are lifted and the `site_unrestricted` tools delete,
submit, cancel and call whitelisted methods. The app's own DocTypes and secret fields stay closed in every mode.
"""

import json
import re

import frappe
from frappe.model import table_fields
from frappe.model.base_document import BaseDocument
from frappe.utils import cint, strip_html

from erp_ai.agent import policy
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
# Customize Form saves Property Setters, permlevel ones included (R10d).
PERMISSION_DOCTYPES = frozenset(
	{
		"Custom Role",
		"Custom DocPerm",
		DOCTYPE_DOCTYPE,
		ROLE_DOCTYPE,
		"User Permission",
		"DocShare",
		"Customize Form",
	}
)
# Closed to these tools in every mode: a Deleted Document holds a whole deleted record, a ticket of an excluded team
# and its content included (R10b).
RECORD_DENIED_DOCTYPES = frozenset({"Deleted Document"})
PROPERTY_SETTER_DOCTYPE = "Property Setter"
CUSTOM_FIELD_DOCTYPE = "Custom Field"
PERMLEVEL_PROPERTY = "permlevel"
PERMLEVEL_REASON = "Property Setter đổi permlevel là sửa phân quyền, không làm qua công cụ"
# Setting a field's permlevel changes permissions too (AC-5, C-6): refused unless the unrestricted switch is on.
PERMLEVEL_DOCTYPES = (PROPERTY_SETTER_DOCTYPE, CUSTOM_FIELD_DOCTYPE)
# The stored fields of a Property Setter / Custom Field that the schema checks compare a write with.
SCHEMA_FIELDS = {
	PROPERTY_SETTER_DOCTYPE: ("doc_type", "field_name", "property"),
	CUSTOM_FIELD_DOCTYPE: ("dt", "fieldname", "fieldtype", "options", "permlevel"),
}
TICKET_LINK_SCHEMA_REASON = "Custom Field / Property Setter đổi trường liên kết tới phiếu là gỡ chặn phiếu loại trừ, không làm qua công cụ"
# Changing these on a field of policy.ticket_link_columns takes it out of the exclusion (R10c): refused in every
# mode. Moving a Custom Field to another DocType or fieldname takes its Link away too.
TICKET_LINK_PROPERTIES = ("fieldtype", "options")
CUSTOM_FIELD_TARGET_KEYS = ("dt", "fieldname")
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
SECRET_ARGUMENT_REASON = "tham số nhắc tới trường khóa API hoặc mật khẩu, không gọi qua công cụ"
# Splits argument text into bare names, so `api_key as k` and `tabUser`.`api_key` both yield `api_key`.
IDENTIFIER_PATTERN = re.compile(r"\w+")
# `fields`/`fieldname` entries that select every column (`*`, `tabX.*`, `` `tabX`.* ``) return keyless rows
# that `_scrub` cannot hide; `count(*)` and a `*` in a filter value are not column selectors.
COLUMN_KEYS = frozenset({"fields", "fieldname"})
COLUMN_SELECTOR_PATTERN = re.compile(r"\s*(?:(?:`[^`]+`|\w+)\s*\.\s*)?\*\s*")
COLUMN_SELECTOR_REASON = "tham số chọn mọi cột bằng *, hãy liệt kê tên trường cần lấy"
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
EXCLUDED_LIST_NOTE = (
	"Phiếu nhóm loại trừ, phiếu không dùng AI và mọi bản ghi của chúng không bao giờ có trong danh sách."
)
MAX_FIELDS = 20
MAX_FILTERS = 10
NAME_MAX = 140
# Before/after values of a write: each value cut to VALUE_MAX characters; a deleted record shows at most
# DELETED_FIELDS_MAX of its non-empty fields.
VALUE_MAX = 200
DELETED_FIELDS_MAX = 20
EMPTY_VALUES = (None, "", [])
# Full before/after of a write, for the audit log only: a User snapshot always holds just its name and roles.
SNAPSHOT_TABLES = {USER_DOCTYPE: ("roles",)}
SNAPSHOT_ROW_DROPPED = (SYSTEM_FIELDS - {"docstatus"}) | {"name", "parentfield"}


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
		return always_denied_doctypes() | RECORD_DENIED_DOCTYPES
	# The read tool hides User from the model; these tools manage users, so only User is taken off that list.
	return frozenset(read.denied_doctypes() - {USER_DOCTYPE}) | PERMISSION_DOCTYPES | RECORD_DENIED_DOCTYPES


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
	# Names are stripped for the check only (" System Manager" is the stored name); non-text stays as given.
	roles = [role.strip() if isinstance(role, str) else role for role in (row.get("role") for row in rows)]
	if doctype == USER_DOCTYPE:
		profiles = [values.get("role_profile_name"), *(row.get("role_profile") for row in profile_rows)]
		for profile in profiles:
			roles.extend(_profile_roles(profile.strip() if isinstance(profile, str) else profile))
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


def _key(text) -> str:
	"""A field or property name as the schema checks compare it: stripped and casefolded."""
	return str(text).strip().casefold()


def _is_permlevel(text) -> bool:
	return _key(text) == PERMLEVEL_PROPERTY


def _schema_write(doctype: str, values: dict, name) -> tuple[str | None, dict, dict]:
	"""`(kind, stored, written)` of a Property Setter or Custom Field write (`kind` says which): the stored record
	`name` (`{}` for a new one) and the record as `values` would leave it, keys taken by _key; `(None, {}, {})` for
	any other DocType."""
	kind = next((item for item in SCHEMA_FIELDS if _named_in(doctype, (item,))), None)
	if kind is None:
		return None, {}, {}
	stored = frappe.db.get_value(kind, name, SCHEMA_FIELDS[kind], as_dict=True) if name is not None else None
	stored = dict(stored or {})
	return kind, stored, {**stored, **{_key(key): value for key, value in values.items()}}


def permlevel_refusal(doctype: str, values: dict, *, name: str | None = None) -> str | None:
	"""PERMLEVEL_REASON when `values` would set a field's permlevel (C-6), else None. A Property Setter is refused
	when it sets `permlevel`, or (`name` given) already does; a Custom Field when a permlevel key holds another
	level than the stored one (0 for a new field)."""
	kind, stored, written = _schema_write(doctype, values, name)
	if kind == PROPERTY_SETTER_DOCTYPE:
		if any(_is_permlevel(record.get("property", "")) for record in (stored, written)):
			return PERMLEVEL_REASON
	elif kind == CUSTOM_FIELD_DOCTYPE:
		levels = [cint(value) for key, value in values.items() if _is_permlevel(key)]
		if any(level != cint(stored.get("permlevel")) for level in levels):
			return PERMLEVEL_REASON
	return None


def _points_at_ticket(doctype, fieldname) -> bool:
	"""`fieldname` is a column of policy.ticket_link_columns(doctype), compared by _key."""
	if not isinstance(doctype, str) or not doctype or fieldname in EMPTY_VALUES:
		return False
	columns = policy.ticket_link_columns(doctype)
	return _key(fieldname) in {_key(column) for pair in columns for column in pair if column}


def ticket_link_schema_refusal(
	doctype: str, values: dict, *, name: str | None = None, delete: bool = False
) -> str | None:
	"""TICKET_LINK_SCHEMA_REASON when the write would change the fieldtype or options of a field that points at a
	ticket (policy.ticket_link_columns), or move, rename or delete its Custom Field (R10c), else None. Same
	mechanism as permlevel_refusal: a Property Setter is refused when it sets, or (`name` given) already sets, a
	property of TICKET_LINK_PROPERTIES on such a field; a Custom Field of such a field, before or after the write,
	on `delete` or when a key of TICKET_LINK_PROPERTIES or CUSTOM_FIELD_TARGET_KEYS holds another value than the
	stored one."""
	kind, stored, written = _schema_write(doctype, values, name)
	if kind == PROPERTY_SETTER_DOCTYPE:
		refused = any(
			_key(record.get("property", "")) in TICKET_LINK_PROPERTIES
			and _points_at_ticket(record.get("doc_type"), record.get("field_name"))
			for record in (stored, written)
		)
	elif kind == CUSTOM_FIELD_DOCTYPE:
		keys = (*TICKET_LINK_PROPERTIES, *CUSTOM_FIELD_TARGET_KEYS)
		changed = delete or any(
			_key(key) in keys and value != stored.get(_key(key)) for key, value in values.items()
		)
		refused = changed and any(
			_points_at_ticket(record.get("dt"), record.get("fieldname")) for record in (stored, written)
		)
	else:
		refused = False
	return TICKET_LINK_SCHEMA_REASON if refused else None


def _schema_refusal(
	doctype: str, name, values: dict, ctx: ToolContext, *, delete: bool = False
) -> dict | None:
	"""R10c in every mode, then C-6 unless the unrestricted switch is on."""
	reason = ticket_link_schema_refusal(doctype, values, name=name, delete=delete)
	if reason is None and not ctx.unrestricted:
		reason = permlevel_refusal(doctype, values, name=name)
	return _fail(reason, doctype) if reason else None


def _shown_value(value):
	if value is None or isinstance(value, bool | int | float):
		return value
	text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, default=str)
	return text[:VALUE_MAX]


def _child_password_fields(meta, fieldname: str) -> frozenset:
	"""The Password fields of the child DocType behind table field `fieldname`; empty for any other field."""
	field = meta.get_field(fieldname)
	if not field or field.fieldtype not in table_fields:
		return frozenset()
	return frozenset(
		child.fieldname for child in frappe.get_meta(field.options).fields if child.fieldtype == "Password"
	)


def _plain(value):
	"""`value` with every Document (a child row) turned into its dict, in nested lists and tuples."""
	if isinstance(value, BaseDocument):
		return value.as_dict()
	if isinstance(value, list | tuple):
		return [_plain(item) for item in value]
	return value


def _without_secrets(value, meta, fieldname: str):
	"""`value` with the secrets of its child rows scrubbed at every depth (F-2), compared after decoding the way
	Frappe hands rows over (Document, dict or JSON text); `value` itself when it holds none, so it shows as before."""
	decoded = _parsed(_plain(value))
	scrubbed = _scrub(decoded, _child_password_fields(meta, fieldname))
	return value if scrubbed == decoded else scrubbed


def _shown(doc, keys) -> dict:
	"""The value of each key as held by `doc`, secret and system fields left out, secrets of child rows scrubbed,
	each cut to VALUE_MAX."""
	record = doc.as_dict()
	return {
		key: _shown_value(_without_secrets(record.get(key), doc.meta, key))
		for key in keys
		if key not in SYSTEM_FIELDS and not _is_secret(doc.meta, key)
	}


def _filled_fields(record: dict) -> list:
	return [key for key, value in record.items() if value not in EMPTY_VALUES]


def _deleted_values(doc) -> dict:
	"""The non-empty fields of a record about to be deleted, at most DELETED_FIELDS_MAX."""
	return dict(list(_shown(doc, _filled_fields(doc.as_dict())).items())[:DELETED_FIELDS_MAX])


def _snapshot_value(value):
	return json.loads(frappe.as_json(value))


def _snapshot_row(row) -> dict:
	record = row.as_dict(no_private_properties=True)
	return {
		key: _snapshot_value(value)
		for key, value in record.items()
		if key not in SNAPSHOT_ROW_DROPPED and not _is_secret(row.meta, key)
	}


def _snapshot(doc, fields) -> dict:
	"""The record's name and each of `fields` as held by `doc`, child tables as rows in `idx` order; secret fields
	are left out on the record and on every row, nothing is cut."""
	if doc.doctype == USER_DOCTYPE:
		fields = SNAPSHOT_TABLES[USER_DOCTYPE]
	tables = {field.fieldname for field in doc.meta.get_table_fields()}
	snapshot = {"name": doc.name}
	for field in fields:
		if _is_secret(doc.meta, field):
			continue
		if field in tables:
			rows = sorted(doc.get(field) or [], key=lambda row: row.idx or 0)
			snapshot[field] = [_snapshot_row(row) for row in rows]
		else:
			snapshot[field] = _snapshot_value(doc.get(field))
	return snapshot


def _write(doctype: str, save) -> dict:
	"""Run `save` (returns the name, the value before, the value after and the full snapshot or None) in its own
	savepoint; a refused write leaves nothing behind and carries no snapshot."""
	frappe.db.savepoint(SAVEPOINT)
	try:
		name, value_before, value_after, snapshot = save()
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
	result = {
		"ok": True,
		"doctype": doctype,
		"name": name,
		"value_before": value_before,
		"value_after": value_after,
	}
	if snapshot is not None:
		result["_snapshot"] = snapshot
	return result


def _snapshot_fields(doctype: str, values: dict) -> tuple:
	return (*values, *SNAPSHOT_TABLES.get(doctype, ()))


def _excluded_refusal(doctype: str, name) -> dict | None:
	"""ADR-034, in every mode: the stored record belongs to an excluded ticket (A-U2-3)."""
	if policy.is_ticket_record_excluded(doctype, name):
		return _fail(policy.EXCLUDED_TICKET_REASON, doctype)
	return None


def _linked_tickets(columns, values: dict) -> list[str]:
	"""Names of the tickets `values` point at, over the `(type column, name column)` pairs of
	policy.ticket_link_columns; the type is compared by its stored DocType name."""
	tickets = []
	for type_column, name_column in columns:
		ticket = values.get(name_column)
		if ticket in EMPTY_VALUES:
			continue
		if type_column and _stored_name(DOCTYPE_DOCTYPE, values.get(type_column)) != policy.TICKET_DOCTYPE:
			continue
		tickets.append(str(ticket))
	return tickets


def _link_refusal(doctype: str, values: dict, name=None) -> dict | None:
	"""C-7, in every mode: `values` would link the record to a ticket that fails can_send_ticket. On an update
	(`name` given) the stored value stands in for each link column `values` does not set."""
	pairs = policy.ticket_link_columns(doctype)
	columns = [column for pair in pairs for column in pair if column]
	if not any(column in values for column in columns):
		return None
	stored = frappe.db.get_value(doctype, name, columns, as_dict=True) if name is not None else None
	if any(
		not policy.can_send_ticket(ticket) for ticket in _linked_tickets(pairs, {**(stored or {}), **values})
	):
		return _fail(policy.EXCLUDED_TICKET_REASON, doctype)
	return None


def create_record(args: dict, ctx: ToolContext) -> dict:
	doctype, values = _stored_name(DOCTYPE_DOCTYPE, args["doctype"]), args["values"]
	if refusal := (
		_doctype_refusal(doctype, ctx)
		or _values_refusal(doctype, values, ctx)
		or _schema_refusal(doctype, None, values, ctx)
		or _link_refusal(doctype, values)
	):
		return refusal

	def save():
		written = {**values, **_forced_values(doctype, ctx)}
		doc = frappe.get_doc({**written, "doctype": doctype}).insert()
		after = _snapshot(doc, _snapshot_fields(doctype, values))
		return doc.name, None, _shown(doc, written), {"before": None, "after": after}

	return _write(doctype, save)


def update_record(args: dict, ctx: ToolContext) -> dict:
	doctype, name, values = _stored_name(DOCTYPE_DOCTYPE, args["doctype"]), args["name"], args["values"]
	if refusal := (
		_doctype_refusal(doctype, ctx)
		or _values_refusal(doctype, values, ctx)
		or _schema_refusal(doctype, name, values, ctx)
	):
		return refusal
	if "name" in values:
		return _fail("không đổi tên bản ghi qua công cụ: name", doctype)
	protected = () if ctx.unrestricted else PROTECTED_USERS | {ctx.agent_user}
	if doctype == USER_DOCTYPE and _named_in(_stored_name(USER_DOCTYPE, name), protected):
		return _fail("tài khoản này không được sửa qua công cụ", doctype)
	if not frappe.get_meta(doctype).issingle and not frappe.db.exists(doctype, name):
		return _fail("không tìm thấy bản ghi", doctype)
	if refusal := _excluded_refusal(doctype, name) or _link_refusal(doctype, values, name):
		return refusal

	def save():
		doc = frappe.get_doc(doctype, name)
		if not _is_draft(doc):
			frappe.throw("chứng từ đã submit hoặc đã hủy, không sửa qua công cụ")
		written = {**values, **_forced_values(doctype, ctx)}
		value_before = _shown(doc, written)
		before = _snapshot(doc, _snapshot_fields(doctype, values))
		doc.update(written)
		doc.save()
		after = _snapshot(doc, _snapshot_fields(doctype, values))
		return doc.name, value_before, _shown(doc, written), {"before": before, "after": after}

	return _write(doctype, save)


def _existing_refusal(doctype: str, name: str, ctx: ToolContext) -> dict | None:
	if refusal := _doctype_refusal(doctype, ctx):
		return refusal
	if not frappe.db.exists(doctype, name):
		return _fail("không tìm thấy bản ghi", doctype)
	return _excluded_refusal(doctype, name)


def delete_record(args: dict, ctx: ToolContext) -> dict:
	doctype, name = _stored_name(DOCTYPE_DOCTYPE, args["doctype"]), args["name"]
	if refusal := _existing_refusal(doctype, name, ctx) or _schema_refusal(
		doctype, name, {}, ctx, delete=True
	):
		return refusal

	def delete():
		doc = frappe.get_doc(doctype, name)
		value_before = _deleted_values(doc)
		before = _snapshot(doc, _filled_fields(doc.as_dict(no_private_properties=True)))
		frappe.delete_doc(doctype, name)
		return name, value_before, None, {"before": before, "after": None}

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
		before = _snapshot(doc, ("docstatus",))
		getattr(doc, action)()
		after = _snapshot(doc, ("docstatus",))
		return doc.name, value_before, {"docstatus": doc.docstatus}, {"before": before, "after": after}

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


def _scrub(value, extra_keys=frozenset()):
	"""`value` with the value of every key in SECRET_RESULT_KEYS (or `extra_keys`) replaced, in nested dicts, lists
	and tuples."""
	if isinstance(value, dict):
		return {
			key: SCRUBBED_VALUE
			if isinstance(key, str) and (key.casefold() in SECRET_RESULT_KEYS or key in extra_keys)
			else _scrub(item, extra_keys)
			for key, item in value.items()
		}
	if isinstance(value, list | tuple):
		return [_scrub(item, extra_keys) for item in value]
	return value


def _selects_every_column(value) -> bool:
	"""True when a `fields`/`fieldname` value anywhere in the parsed `value` holds a `*` column selector."""
	if isinstance(value, dict):
		return any(
			(key.casefold() in COLUMN_KEYS and _is_column_selector(item)) or _selects_every_column(item)
			for key, item in value.items()
		)
	if isinstance(value, list):
		return any(_selects_every_column(item) for item in value)
	return False


def _is_column_selector(value) -> bool:
	if isinstance(value, str):
		if any(COLUMN_SELECTOR_PATTERN.fullmatch(part) for part in value.split(",")):
			return True
		try:
			loaded = json.loads(value)
		except ValueError:
			return False
		return isinstance(loaded, str) and _is_column_selector(loaded)
	if isinstance(value, list):
		return any(_is_column_selector(item) for item in value)
	return False


def _method_refusal(method: str, arguments: dict) -> dict | None:
	"""Early refusal only: the app's DocTypes are closed for the agent account by their controllers.

	A secret field named in the arguments is refused here because a bare value (`get_value` with
	`as_dict=0`) carries no key for `_scrub` to hide; this is best effort, not a guarantee."""
	if method.startswith(OWN_APP_PREFIX):
		return _fail("không gọi hàm của erp_ai qua công cụ")
	if _is_secret_method(method):
		return _fail(SECRET_METHOD_REASON)
	parsed = _parsed(arguments)
	if _selects_every_column(parsed):
		return _fail(COLUMN_SELECTOR_REASON)
	text = json.dumps(parsed, ensure_ascii=False, default=str).casefold()
	if any(doctype.casefold() in text for doctype in always_denied_doctypes()):
		return _fail("tham số nhắc tới DocType không được phép dùng qua công cụ")
	if not SECRET_RESULT_KEYS.isdisjoint(IDENTIFIER_PATTERN.findall(text)):
		return _fail(SECRET_ARGUMENT_REASON)
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
		return method, None, {"method": method, "argument_keys": sorted(arguments)}, None

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
	# ADR-034: in every mode, before any read of the record.
	if policy.is_ticket_record_excluded(doctype, name):
		return _fail(policy.EXCLUDED_TICKET_REASON, doctype)
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
	# ADR-034 Ràng buộc 2: the exclusion is part of the query, so `limit` and the order never reveal it. The
	# model gives no or_filters: the only OR group is the policy's.
	extra, or_filters = policy.ticket_content_filters(doctype)
	try:
		rows = frappe.get_list(
			doctype,
			filters=[*filters, *extra],
			or_filters=or_filters,
			fields=fields,
			limit_page_length=args.get("limit", DEFAULT_LIMIT),
			order_by="modified desc",
		)
	except frappe.PermissionError:
		return _fail("thiếu quyền đọc DocType này", doctype)
	result = {"ok": True, "doctype": doctype, "records": [dict(row) for row in rows]}
	if policy.is_ticket_content_doctype(doctype):
		# Always present, so the reason is given without revealing whether anything was hidden.
		result["excluded_note"] = EXCLUDED_LIST_NOTE
	return result


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
				"tham số nhắc tới trường khóa hoặc mật khẩu, hoặc chọn mọi cột bằng * (`*`, `tabX.*` trong fields/fieldname), "
				"bị từ chối và giá trị dưới khóa bí mật trong kết quả được ẩn, "
				"nhưng đây chỉ là chặn ở mức cố gắng, không bảo đảm mọi bí mật đều bị chặn."
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
