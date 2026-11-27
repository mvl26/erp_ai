import json
import re
from pathlib import Path

import frappe
from frappe.tests.utils import FrappeTestCase

APP_DIR = Path(__file__).resolve().parent.parent
DOCTYPE_DIR = APP_DIR / "erp_ai_agent" / "doctype"
MAX_DESCRIPTION_CHARS = 400
MIN_STORED_VALUE_CHARS = 4
BREAK_TYPES = ("Section Break", "Column Break", "Tab Break")
SAFE_EMAIL_DOMAINS = ("congty.vn", "example.com")
EMAIL_PATTERN = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
SYSTEM_WRITES = "Hệ thống tự ghi"
NOT_EDITABLE = "không sửa được"
VIETNAMESE_ACCENTS = re.compile(
	"[àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ]", re.IGNORECASE
)

# Keyed by DocType name: expected visible-field count, required phrases per field,
# and the Section Breaks as (fieldname, label, first field of the group).
DOCTYPE_CONFIG = {
	"ERP AI Setting": {
		"folder": "erp_ai_setting",
		# 2026-11-27 server_script_read_enabled (+1);
		# CHG-015: default_assignee (+1); CHG-011: tag_assignees (+1); CHG-010: console_enabled (+1); FEAT-008: lessons_enabled,
		# lessons_max_per_request, lessons_max_chars, lesson_teach_marker (+4); base 77
		"field_count": 85,
		"phrases": {
			"enabled": ("Tắt", "4 đơn giá", "từ khóa kích hoạt"),
			# FEAT-007 spec-addendum-3.md:88 (T64): from L2 up, ERP writes go through a proposal or a `Tự làm` row.
			# T64 review round 1: keep the L3 gate (AC-3(2)), the automatic budget fallback and the
			# design.md:184 sentence word for word.
			"permission_level": (
				"L0",
				"L1",
				"L2",
				"L3",
				"ngân sách",
				"đề xuất",
				"Tự làm",
				"L3: mức của công cụ bản ghi chung",
				"tự hạ về L1",
				"Mức thực tế của từng phiếu",
				"đọc dữ liệu",
				"không ghi gì lên phiếu",
				"Từ L2: ghi ERP ngoài phiếu",
				"(L0 giữ nguyên)",
			),
			# FEAT-007 design.md:182: the AC-16 watermark of section_activation.
			# T125 (design-w0-fixes-7.md ruling 2b): a site enabled before the upgrade gets the upgrade moment.
			"agent_enabled_at": ("Hệ thống tự ghi", "không sửa được", "thời điểm nâng cấp"),
			"unrestricted_enabled": (
				"L1",
				"người ra lệnh",
				"xóa",
				"System Manager",
				"Vẫn đóng",
				"mật khẩu",
				"Log",
				"cần gấp",
				"vượt ngân sách",
				"gọi hàm",
				"cố gắng",
			),
			"record_tools_enabled": (
				"L3",
				"người ra lệnh",
				"không qua duyệt",
				"danh mục trắng",
				"Log",
				"Sau cập nhật",
			),
			"act_now_enabled": ("người ra lệnh", "không hỏi lại", "ngưỡng độ tin cậy", "Không thêm công cụ"),
			"one_click_approval_enabled": (
				"một lần bấm",
				"không hộp xác nhận",
				"chuyển tiếp",
				"liên kết cũ",
			),
			# 2026-11-27: the seventh permission switch, read-only access to Server Script.
			"server_script_read_enabled": ("chỉ đọc", "không sửa", "che", "Log"),
			"console_enabled": (
				"bench console",
				"ERP AI Instructor",
				"khung Trao đổi với bot",
				"một giao dịch",
				"không hoàn tác được",
			),
			"site_environment": ("production", "site test", "không bị chặn"),
			# 2026-11-27: the caps still never apply to the permission switches; there are seven switches now, so
			# the phrase drops the count "năm" (FORBIDDEN_PHRASES keeps the old count out).
			**{f"level_cap_{category}": ("Mức quyền", "quyền mở rộng", "chưa biết") for category in "abcdef"},
			"confidence_threshold": ("từ 0 đến 100", "chỉ đăng một comment hỏi", "Làm luôn"),
			"auto_approve_streak": ("từ 1 đến 100", "Tự làm", "đếm lại từ 0"),
			# FEAT-007 spec-addendum-4.md AC-29 (T64): no row = proposal awaiting approval; "Đổi trường" and
			# the excluded-team group need a row; a child table is never a target.
			"catalog_rules": (
				"Không có dòng nào",
				"Cấm",
				"Cần duyệt",
				"Tự làm",
				"bị chặn khi lưu",
				"chờ Duyệt",
				"Đổi trường",
				"bị từ chối",
				"bảng con",
			),
			"user_templates": ("tạo tài khoản theo mẫu", "System Manager", "Guest"),
			"max_turns_per_run": ("từ 1 đến 20", "dừng"),
			"max_runs_per_ticket_per_day": ("từ 1 đến 50", "00:00"),
			"max_keys_per_call": ("từ 1 đến 10", "báo lỗi"),
			"request_timeout_s": ("từ 5 đến 300", "giây", "khóa kế tiếp"),
			"monthly_budget_usd": ("USD", "L1", "Nhập 0", "không phải"),
			"spent_this_month_usd": ("mỗi ngày", "tổng chi phí"),
			"price_input_per_mtok": ("USD", "triệu token", "không được âm"),
			"price_cache_write_per_mtok": ("USD", "triệu token", "không được âm"),
			"price_cache_read_per_mtok": ("USD", "triệu token", "không được âm"),
			"price_output_per_mtok": ("USD", "triệu token", "không được âm"),
			# CHG-004: the effort the gateway asks of every model but Haiku
			"model_classify_default": ("phân loại", "model", "claude-haiku", "trần token", "effort medium"),
			"trigger_keyword": ("@ai", "không phân biệt hoa thường"),
			"thinking_text": ("Để trống", "giây"),
			"answer_delay_min_s": ("giây", "từ 0 đến 30", "bình luận"),
			"answer_delay_max_s": ("giây", "từ 0 đến 30", "bình luận"),
			"excluded_teams": ("mỗi dòng", "không phân biệt hoa thường"),
			"excluded_title_prefixes": ("Mỗi dòng", "[HR]", "không gửi cho model"),
			"category_mapping": ("JSON", "A đến F", "[GẤP]", "Urgent"),
			"auto_assign_enabled": (
				"Bật",
				"L1",
				"Quy tắc định tuyến",
				"Assignment Rule",
				"chưa có ai được gán",
				"Task",
				"Tắt",
				"HD Agent",
			),
			"routing_rules": ("đầu mục", "SLA", "phút", "bị chặn khi lưu"),
			# CHG-011: the table of tag → person, read top-down before the routing rules (user's option b); say
			# whose tags count and that a blank row also serves D/E.
			"tag_assignees": (
				"Tự gán người",
				"đúng một tag",
				"HD Agent gắn",
				"từ trên xuống",
				"D/E",
				"Quy tắc định tuyến",
				# CHG-016: the sentence names whose category the row must match
				"đầu mục của phiếu",
			),
			# CHG-015: the person a ticket no rule gives goes to.
			# CHG-016: and the switch it needs
			"default_assignee": (
				"bảng Gán người theo tag",
				"Quy tắc định tuyến",
				"HD Agent",
				"Task C/D",
				"Tự gán người",
			),
			"prompt_digest": ("lập luận", "phân loại"),
			**{
				fieldname: ("fieldname", "Để trống", "không lưu được")
				for fieldname in (
					"field_ticket_nature",
					"field_erp_module",
					"field_origin",
					"field_project",
					"field_item_code",
					"field_serial_no",
				)
			},
			"field_due_date": ("fieldname", "Để trống", "không lưu được", "kiểu Date hoặc Datetime"),
			"origin_board_value": ("Chỉ đạo BGĐ", "đổi trạng thái", "Nguồn phát sinh"),
			"alert_recipients": ("mỗi dòng", "canhbao@congty.vn", "dấu phẩy"),
			"privilege_alert_checked_until": ("Hệ thống tự ghi", "không sửa được", "chưa cảnh báo lần nào"),
			"credentials": ("không trùng", "Kiểm tra khóa"),
			"code_change_enabled": (
				"L3",
				"người ra lệnh",
				"được duyệt",
				"commit git local",
				"không push",
				"Tắt",
				"không còn mở công cụ bản ghi",
			),
			"code_change_apps": (
				"Mỗi dòng",
				"apps/",
				"frappe, erpnext, helpdesk, hrms",
				"mọi site trên bench",
				"erp_ai",
				"Bỏ trống",
			),
			# FEAT-007 design.md:172-175: the four switches; the three that change a status or write an article
			# say they wait for the origin field.
			"reply_enabled": ("mặc định tắt",),
			**{
				fieldname: ("mặc định tắt", "chỉ bật sau khi đã đặt trường Nguồn phát sinh")
				for fieldname in (
					"resolve_on_tasks_done_enabled",
					"close_silent_f_enabled",
					"kb_draft_enabled",
				)
			},
			"close_silent_f_days": ("ngày", "từ 1 đến 30"),
			"knowledge_search_limit": ("kết quả", "từ 1 đến 20"),
			"report_row_limit": ("dòng", "từ 1 đến 100"),
			"manuals_dir": ("apps/", "Để trống", "chưa có kho HDSD", "mã nguồn"),
			"allowed_reports": ("Mỗi dòng", "Để trống", "bị chặn khi lưu"),
			# FEAT-007 design.md:174, 177-181: section_operations.
			"coo_report_recipients": ("08:00", "Để trống"),
			"daily_report_weekends": ("08:00", "thứ Bảy", "Chủ nhật"),
			"monthly_reviewers": ("Mỗi dòng", "vẫn được tạo"),
			"review_sample_size": ("phiếu", "từ 1 đến 50"),
			"d_ticket_watcher": ("đầu mục D", "Để trống"),
			"due_reminder_hours": ("giờ", "từ 1 đến 168"),
			"ba_note_due_hours": ("giờ", "từ 1 đến 168"),
			"task_due_days": ("ngày", "từ 1 đến 30"),
			"max_tasks_per_run": ("Task", "từ 1 đến 20"),
			"kpi_targets": ("JSON", "gd2", "gd4", "không lưu được"),
			"daily_report_sent_on": ("Hệ thống tự ghi", "không sửa được"),
			"budget_alert_sent_month": ("Hệ thống tự ghi", "không sửa được"),
			# FEAT-007 design.md:182-183: section_prompts (AC-38).
			**{
				fieldname: ("Để trống", "bắt buộc", "20000", "không bị ghi đè")
				for fieldname in (
					"prompt_override_classify",
					"prompt_override_reasoning",
					"prompt_override_category_guide",
				)
			},
			"prompt_revisions": ("Hệ thống tự ghi", "Không sửa được"),
			# FEAT-008: the lesson store switch, its two caps and the teaching marker.
			"lessons_enabled": ("bài học", "Tắt", "bài đã lưu vẫn giữ"),
			"lessons_max_per_request": ("từ 1 đến 20", "không lưu được", "Mặc định 5"),
			"lessons_max_chars": ("từ 1300 đến 20000", "không lưu được", "Mặc định 2000"),
			# The rule of a person with authority is active at once; a message of anyone else is ignored (no lesson).
			"lesson_teach_marker": (
				"không phân biệt hoa thường",
				"Để trống",
				"thẩm quyền",
				"bài học Đang dùng",
				"bị bỏ qua",
			),
		},
		# 2026-11-27 layout: the 15 sections keep their fieldnames; 10 new ones split the long or mixed ones.
		"section_count": 25,
		"read_only_fields": (
			"spent_this_month_usd",
			"agent_enabled_at",
			"daily_report_sent_on",
			"budget_alert_sent_month",
			"prompt_revisions",
			"privilege_alert_checked_until",
		),
		# In form order (SETTING_LAYOUT gives the tab and the columns of each).
		"sections": (
			("section_activation", "Bật agent và mức quyền", "enabled"),
			("section_permissions", "Quyền mở rộng (mặc định tắt)", "unrestricted_enabled"),
			("section_autonomy", "Mức tối đa theo đầu mục", "level_cap_a"),
			("section_confidence", "Ngưỡng độ tin cậy và Tự làm", "confidence_threshold"),
			("section_catalog", "Danh mục trắng và mẫu tài khoản", "catalog_rules"),
			("section_model", "Model, từ khóa và chỉ báo trả lời", "model_classify_default"),
			("section_credentials", "Khóa API", "credentials"),
			("section_limits", "Giới hạn mỗi lần chạy", "max_turns_per_run"),
			("section_budget", "Ngân sách và đơn giá", "monthly_budget_usd"),
			("section_routing", "Phiếu bỏ qua và ánh xạ đầu mục", "excluded_teams"),
			("section_assignment", "Tự gán người và bảng tag", "auto_assign_enabled"),
			("section_routing_rules", "Quy tắc định tuyến và người nhận mặc định", "routing_rules"),
			("section_ticket_fields", "Tên trường có sẵn trên phiếu", "field_ticket_nature"),
			("section_knowledge", "Trả lời, đóng phiếu và tri thức", "reply_enabled"),
			("section_reports", "Báo cáo bot được chạy", "allowed_reports"),
			("section_digest", "Trích yếu HDSD", "prompt_digest"),
			("section_lessons", "Bài học của bot", "lessons_enabled"),
			("section_operations", "Báo cáo 08:00 hằng ngày", "coo_report_recipients"),
			("section_review", "Rà soát tháng", "monthly_reviewers"),
			("section_reminders", "Theo dõi và nhắc hạn", "d_ticket_watcher"),
			("section_kpi", "Mục tiêu KPI", "kpi_targets"),
			("section_report_marks", "Mốc gửi do hệ thống ghi", "daily_report_sent_on"),
			("section_alerts", "Người nhận cảnh báo", "alert_recipients"),
			("section_code_change", "App được phép sửa code", "code_change_apps"),
			("section_prompts", "Ghi đè prompt", "prompt_override_classify"),
		),
	},
	"ERP AI Credential": {
		"folder": "erp_ai_credential",
		"field_count": 18,
		"phrases": {
			"label": ("không trùng", "không phân biệt hoa thường"),
			"provider": ("nhà cung cấp", "Anthropic", "OpenAI", "bỏ qua"),
			"api_key": ("khóa bí mật", "mã hóa", "không hiện lại", "Log"),
			"model_classify": ("Setting", "phân loại", "claude-haiku", "trần token", "effort medium"),
			"model_reason": ("lập luận", "không dùng", "effort medium"),
			"try_order": ("99", "nhỏ", "Để trống", "hoặc 0", "lớn hơn 99"),
			"purpose": ("ghi chú", "không ảnh hưởng"),
			"budget_month_usd": ("USD", "Nhập 0", "không giới hạn", "ngược"),
			"spent_month_usd": ("mỗi ngày", "Log"),
			"enabled": ("Tắt", "không được thử", "không xóa"),
			"status": ("Tạm nghỉ", "Hết hạn mức", "Lỗi khóa", "Hoạt động"),
			"paused_until": ("tạm nghỉ",),
			"tokens_remaining": ("số token còn lại", "lần gọi gần nhất"),
			"limit_reset_at": ("hạn mức", "nhà cung cấp", "đặt lại"),
			"error_count": ("lỗi liên tiếp", "về 0"),
			"last_error": ("không bao giờ chứa khóa",),
			"last_success_at": ("thành công",),
			"note": ("ghi chú",),
		},
		"section_count": 4,
		"read_only_fields": (
			"spent_month_usd",
			"paused_until",
			"tokens_remaining",
			"limit_reset_at",
			"error_count",
			"last_error",
			"last_success_at",
		),
		"sections": (
			("section_key", "Khóa và model", "label"),
			("section_usage", "Thứ tự thử và ngân sách", "try_order"),
			("section_state", "Trạng thái khóa", "status"),
			("section_note", "Ghi chú", "note"),
		),
	},
	# FEAT-007 design.md:204-210: one row of the whitelist catalog (child of ERP AI Setting).
	"ERP AI Catalog Rule": {
		"folder": "erp_ai_catalog_rule",
		"field_count": 5,
		"phrases": {
			"action": ("Tạo tài khoản theo mẫu", "Tạo Custom Field", "Đổi trường"),
			"target_doctype": ("Đổi trường", "Tạo Custom Field", "phải trống", "bị chặn khi lưu"),
			"fields": ("Mỗi dòng", "fieldname", "Đổi trường", "ít nhất một dòng"),
			"categories": ("A đến F", "dấu phẩy", "bỏ trùng"),
			"mode": ("Cấm", "Cần duyệt", "Tự làm", "Mặc định Cần duyệt"),
		},
		"section_count": 2,
		"read_only_fields": (),
		"sections": (
			("section_action", "Hành động và DocType đích", "action"),
			("section_scope", "Đầu mục và chế độ", "categories"),
		),
	},
	# CHG-011: one row of the table of tag → person (child of ERP AI Setting).
	"ERP AI Tag Assignee": {
		"folder": "erp_ai_tag_assignee",
		# CHG-014: + description (the tag table is the list of tags the bot gives); CHG-018: + bot_added
		"field_count": 5,
		"phrases": {
			"tag": ("bot tự tạo", "không phân biệt hoa thường", "không dấu phẩy"),
			# CHG-016: the bot reads the first 200 characters
			"description": ("đúng một tag", "dòng đầu tiên", "không nêu tên người", "200 ký tự"),
			"assignee": ("HD Agent", "tài khoản agent", "bỏ qua", "Để trống"),
			"category": ("Để trống", "mọi đầu mục", "dòng nằm trên"),
			# CHG-018: the bot's rows wait for a System Manager's review
			"bot_added": ("chỉ đưa tên tag", "bỏ đánh dấu", "tối đa 20"),
		},
		"section_count": 2,
		"read_only_fields": (),
		"sections": (
			("section_assignee", "Tag và người phụ trách", "tag"),
			("section_scope", "Phạm vi áp dụng", "category"),
		),
	},
	# FEAT-007 design.md:225: one account template (child of ERP AI Setting, AC-30 (1)).
	"ERP AI User Template": {
		"folder": "erp_ai_user_template",
		"field_count": 3,
		"phrases": {
			"template_name": ("không trùng", "không phân biệt hoa thường", "tạo tài khoản theo mẫu"),
			"roles": ("Mỗi dòng", "ít nhất một", "System Manager", "Guest", "bị chặn khi lưu"),
			"note": ("ghi chú", "không ảnh hưởng"),
		},
		"section_count": 2,
		"read_only_fields": (),
		"sections": (
			("section_template", "Mẫu và vai trò", "template_name"),
			("section_note", "Ghi chú", "note"),
		),
	},
	# FEAT-007 design.md:227, D-3: one prompt override change (child of ERP AI Setting, AC-38), system-written.
	"ERP AI Prompt Revision": {
		"folder": "erp_ai_prompt_revision",
		"field_count": 5,
		"phrases": {
			"part": ("Hệ thống tự ghi", "classify", "reasoning", "category_guide"),
			"changed_by": ("Hệ thống tự ghi", "người"),
			"changed_at": ("Hệ thống tự ghi", "thời điểm"),
			"old_value": ("Hệ thống tự ghi", "giá trị cũ", "bản dựng sẵn"),
			"new_length": ("Hệ thống tự ghi", "ký tự"),
		},
		"section_count": 2,
		"read_only_fields": ("part", "changed_by", "changed_at", "old_value", "new_length"),
		"sections": (
			("section_change", "Lần sửa", "part"),
			("section_value", "Giá trị cũ", "old_value"),
		),
	},
	# Bot conversation moved off HD Ticket comments: one row per message, written by the one writer, never edited.
	"ERP AI Message": {
		"folder": "erp_ai_message",
		# BUG-009: + author_role, the role the author had when the message was sent
		"field_count": 5,
		"phrases": {
			"ticket": ("phiếu",),
			"content": ("chữ thường",),
			"run_id": ("lần chạy",),
			"source_comment": ("@ai",),
			# the user's rule 2026-11-18: an order needs the right when sent and when the bot reads it
			"author_role": ("chỉ thị", "dữ liệu", "lúc tin được gửi", "ERP AI Instructor", "vẫn còn quyền"),
		},
		"section_count": 2,
		"read_only_fields": ("ticket", "content", "run_id", "source_comment", "author_role"),
		"sections": (
			("section_message", "Tin nhắn", "ticket"),
			("section_source", "Nguồn gốc", "run_id"),
		),
	},
	# FEAT-008: one lesson of the bot; every field is system-written, no role may create or edit it.
	"ERP AI Lesson": {
		"folder": "erp_ai_lesson",
		"field_count": 10,
		"phrases": {
			"lesson_status": ("Chờ duyệt", "Đang dùng", "Đã tắt", "Bị từ chối"),
			"situation": ("tình huống", "300 ký tự", "che khóa"),
			"lesson_text": ("1000 ký tự", "che khóa", "bot cần nhớ"),
			"lesson_source": ("người sửa", "phiếu đã giải quyết", "người dạy", "rà soát"),
			"ticket": ("phiếu", "Xóa phiếu", "không bị chặn"),
			"change_proposal": ("đề xuất", "Để trống"),
			"author": ("tài khoản", "người"),
			"reviewed_by": ("duyệt", "từ chối", "Để trống"),
			"reviewed_at": ("thời điểm", "duyệt", "Để trống"),
			"history": ("bước", "người làm", "thời điểm"),
		},
		"section_count": 2,
		"read_only_fields": (
			"lesson_status",
			"situation",
			"lesson_text",
			"lesson_source",
			"ticket",
			"change_proposal",
			"author",
			"reviewed_by",
			"reviewed_at",
			"history",
		),
		"sections": (
			("section_lesson", "Bài học", "lesson_status"),
			("section_origin", "Nguồn và người quyết", "lesson_source"),
		),
	},
	# FEAT-008: one step in the history of a lesson (child of ERP AI Lesson), system-written.
	"ERP AI Lesson Event": {
		"folder": "erp_ai_lesson_event",
		"field_count": 3,
		"phrases": {
			"step": ("Tạo", "Cập nhật", "Duyệt", "Từ chối", "Tắt", "Bật"),
			"actor": ("tài khoản", "bot"),
			"happened_at": ("thời điểm", "bước"),
		},
		"section_count": 2,
		"read_only_fields": ("step", "actor", "happened_at"),
		"sections": (
			("section_step", "Bước", "step"),
			("section_actor", "Người và lúc", "actor"),
		),
	},
	"ERP AI Log": {
		"folder": "erp_ai_log",
		"field_count": 44,
		"phrases": {
			"ticket": ("HD Ticket", "mã phiếu", "lọc"),
			"run_id": ("cùng một lần chạy", "gom"),
			"entry_type": (
				"classify",
				"reason",
				"skip",
				"change",
				"bot_action",
				"phân loại",
				"lập luận",
				"bước của đề xuất",
				# CHG-009 design 2 (ADR-048 QĐ 1): the run_event row.
				"run_event",
				"lời gọi bot được nhận, gộp, từ chối",
				"lần chạy xong/lỗi",
				"ngăn trao đổi",
			),
			"turn": ("Lượt 0", "lượt 1", "lập luận"),
			"trigger": (
				"ticket_insert",
				"comment_mention",
				"requester_reply",
				"kb_draft",
				"support_chat",
				"change_action",
				"setting_save",
				"scheduled_job",
				"bình luận",
				"bước của đề xuất",
			),
			"instructor": ("ERP AI Instructor", "giao việc", "chủ phiếu", "ticket_insert", "dòng reason"),
			"model": ("model", "lần gọi"),
			"change_proposal": ("ERP AI Change Proposal", "dòng change", "để trống"),
			"change_step": (
				"propose",
				"approve",
				"reject",
				"apply",
				"fail",
				"stale",
				"undo",
				"mỗi bước một dòng",
			),
			"actor": ("người thực hiện", "người duyệt", "agent", "không suy từ"),
			"site_environment": ("production", "test", "Setting", "giữ nguyên"),
			"input_tokens": ("token", "gửi lên"),
			"output_tokens": ("token", "model trả về"),
			"cache_creation_input_tokens": ("ghi vào cache", "token"),
			"cache_read_input_tokens": ("đọc từ cache", "token"),
			"cost_usd": ("USD", "đơn giá", "Setting", "đã chi trong tháng"),
			"credential_label": ("nhãn", "khóa", "thử cuối cùng", "gateway_error"),
			"keys_tried": ("danh sách", "nhãn khóa", "kết quả"),
			"latency_ms": ("mili giây", "lần gọi", "ghi 0"),
			"stop_reason": (
				"ví dụ",
				"tool_use",
				"end_turn",
				"max_turns",
				"time_budget",
				"gateway_error",
				"unparseable",
				"not_sendable",
				"daily_limit",
				"level_L0",
				# CHG-009 design 2 (ADR-003 Amd 1, ADR-048 QĐ 4): the skip codes with the refusal kind, and the
				# run_event codes.
				"not_sendable:<loại>",
				"agent_disabled",
				"call_received",
				"call_merged",
				"call_busy",
				"run_done",
				"run_failed",
				"created_by_agent",
				"prefilled",
			),
			"tools_called": ("tool", "trong lượt này"),
			"actions": ("hành động", "phiếu"),
			"value_before": ("JSON", "trước khi"),
			"value_after": ("JSON", "sau khi"),
			"skipped_fields": ("bỏ qua", "phân loại"),
			"lessons_used": ("JSON", "tên", "bài học", "Hệ thống tự ghi", "không sửa được"),
			"predicted_category": ("đầu mục", "A đến F"),
			"predicted_confidence": ("Cao", "Trung bình", "Thấp", "ai_confidence"),
			# FEAT-007 design-w0-fixes-2.md section 1: -1 = unknown (wins over design.md:234).
			"predicted_confidence_pct": ("-1", "không biết"),
			"predicted_ticket_type": ("loại phiếu", "dự đoán"),
			"predicted_agent_group": ("nhóm xử lý", "dự đoán"),
			"predicted_priority": ("ưu tiên", "dự đoán"),
			"predicted_complexity": ("độ phức tạp", "1 đến 3", "ghi 0"),
			"predicted_importance": ("độ quan trọng", "1 đến 3", "ghi 0"),
			"predicted_score_reason": ("lý do", "không có điểm"),
			# CHG-016: CHG-011 and CHG-015 give the person too
			"predicted_assignee": ("người phụ trách", "dự đoán", "bảng tag", "người nhận mặc định"),
			"applied": ("đã ghi", "phiếu"),
			"created_labels": (
				"lúc tạo phiếu",
				"trước khi",
				"JSON",
				"ticket_type",
				"agent_group",
				"priority",
				"dòng classify",
			),
			"split_requested": ("2 yêu cầu", "xác nhận", "không đăng lần hai", "không tạo, sửa, đóng"),
			"split_requests": ("JSON", "phiếu gộp", "Để trống"),
			"human_corrected_to": ("loại phiếu", "nhóm xử lý", "ưu tiên", "AI đã dự đoán"),
			"human_corrected_by": ("người đổi", "AI đã dự đoán"),
			"human_corrected_at": ("lần sửa đầu", "AI đã dự đoán"),
			"error": ("lỗi", "không có khóa"),
		},
		"section_count": 6,
		"read_only_fields": (
			"ticket",
			"run_id",
			"entry_type",
			"turn",
			"trigger",
			"instructor",
			"model",
			"change_proposal",
			"change_step",
			"actor",
			"site_environment",
			"input_tokens",
			"output_tokens",
			"cache_creation_input_tokens",
			"cache_read_input_tokens",
			"cost_usd",
			"credential_label",
			"keys_tried",
			"latency_ms",
			"stop_reason",
			"tools_called",
			"actions",
			"value_before",
			"value_after",
			"skipped_fields",
			"lessons_used",
			"predicted_category",
			"predicted_confidence",
			"predicted_confidence_pct",
			"predicted_ticket_type",
			"predicted_agent_group",
			"predicted_priority",
			"predicted_complexity",
			"predicted_importance",
			"predicted_score_reason",
			"predicted_assignee",
			"applied",
			"created_labels",
			"split_requested",
			"split_requests",
			"human_corrected_to",
			"human_corrected_by",
			"human_corrected_at",
			"error",
		),
		"sections": (
			("section_run", "Lần chạy", "ticket"),
			("section_usage", "Token, chi phí và khóa", "input_tokens"),
			("section_changes", "Tool và thay đổi trên phiếu", "tools_called"),
			("section_prediction", "Dự đoán phân loại", "predicted_category"),
			("section_correction", "Người sửa sau dự đoán", "human_corrected_to"),
			("section_error", "Lỗi", "error"),
		),
	},
	# FEAT-007 design.md:254-270, 461-468: one row per ISO week, written by the weekly KPI job.
	"ERP AI KPI Week": {
		"folder": "erp_ai_kpi_week",
		"field_count": 17,
		"phrases": {
			"week_start": ("thứ Hai", "mỗi tuần một dòng", "KPI-", "tối đa 8 tuần"),
			"week_end": ("Chủ nhật",),
			"computed_at": ("thời điểm", "ranh giới của tuần"),
			"first_response_median_min": ("KPI 1", "trung vị", "phút", "Rỗng khi không phiếu nào"),
			# R21a (kpi.py _first_response): the rates divide by every ticket of the week, the sample counts only
			# the answered ones, so a rate is empty only when the week has no ticket.
			"first_response_within_15_pct": (
				"KPI 1",
				"15 phút",
				"chưa phản hồi",
				"Rỗng khi tuần không có phiếu",
			),
			"first_response_within_5_pct": (
				"KPI 1",
				"5 phút",
				"chưa phản hồi",
				"Rỗng khi tuần không có phiếu",
			),
			"first_response_sample": ("KPI 1", "số phiếu", "mẫu"),
			"complete_fields_pct": ("KPI 2", "đang mở", "ưu tiên", "Rỗng khi mẫu 0"),
			"complete_fields_sample": ("KPI 2", "đang mở"),
			"closed_without_human_pct": ("KPI 3", "của bot", "Rỗng khi mẫu 0"),
			"closed_sample": ("KPI 3", "đóng trong tuần"),
			"b_resolution_avg_hours": ("KPI 4", "đầu mục B", "giờ lịch", "Rỗng khi mẫu 0"),
			"b_resolution_sample": ("KPI 4", "đầu mục B"),
			"c_task_in_3_days_pct": ("KPI 5", "đầu mục C", "72 giờ", "Rỗng khi mẫu 0"),
			"c_task_sample": ("KPI 5", "đầu mục C"),
			"stale_over_5_days": ("KPI 6", "quá 5 ngày", "đúng 5 ngày không tính"),
			"stale_over_7_days": ("KPI 6", "quá 7 ngày", "đúng 7 ngày không tính"),
		},
		"section_count": 2,
		"read_only_fields": (),
		"sections": (
			("section_week", "Tuần và lúc tính", "week_start"),
			("section_kpi", "Sáu KPI của tuần", "first_response_median_min"),
		),
	},
	# FEAT-007 design.md:272-274, 477: the monthly random review of tickets; the ticket list is locked.
	"ERP AI Review Month": {
		"folder": "erp_ai_review_month",
		"field_count": 5,
		"phrases": {
			"month": ("Hệ thống tự ghi", "không sửa được", "REV-", "tháng"),
			"period_start": ("Hệ thống tự ghi", "không sửa được", "ngày đầu"),
			"period_end": ("Hệ thống tự ghi", "không sửa được", "ngày cuối"),
			"candidate_count": ("Hệ thống tự ghi", "không sửa được", "phiếu", "mẫu"),
			"items": ("danh sách phiếu", "không đổi được", "Đúng", "Sai"),
		},
		"section_count": 2,
		"read_only_fields": ("month", "period_start", "period_end", "candidate_count"),
		"sections": (
			("section_period", "Tháng rà soát", "month"),
			("section_items", "Phiếu được chọn", "items"),
		),
	},
}

# FEAT-004 design 2.4: exact contract of the code-change block of ERP AI Setting.
CODE_CHANGE_FIELDS = {
	"code_change_enabled": {
		"fieldtype": "Check",
		"label": "Cho phép sửa code và lệnh bench",
		"default": "0",
		# FEAT-007 design.md:162: the switch no longer opens the record tools (record_tools_enabled does).
		"description": "Sửa code và lệnh bench. Bật thì ở L3 và khi có người ra lệnh, bot đề xuất sửa file, "
		"tạo file, lệnh bench; mọi thay đổi phải được duyệt bởi ERP AI Instructor trên form đề xuất. "
		"Mỗi thay đổi đã áp dụng là một commit git local; bot không push. "
		"Ô này không còn mở công cụ bản ghi. Tắt thì bot không có ba công cụ đó.",
	},
	"code_change_apps": {
		"fieldtype": "Small Text",
		"label": "App được phép sửa",
		"default": None,
		"description": "Mỗi dòng một tên thư mục app trong apps/. Có thể thêm app lõi frappe, erpnext, helpdesk, hrms; "
		"sửa app lõi ảnh hưởng mọi site trên bench. Không bao giờ được thêm erp_ai. "
		"Bỏ trống thì không file nào được sửa.",
	},
}

# CHG-010 Task 1: the console switch. Read from the JSON on disk (the site is not migrated for it).
CONSOLE_FIELD_SPEC = {
	"fieldtype": "Check",
	"label": "Cho phép chạy bench console (qua duyệt)",
	"default": "0",
	# CHG-010 final review F-9: the text says the script runs as Administrator; the first clause is shorter to
	# stay within the 400-character cap.
	"description": "Bật thì bot được soạn script Python chạy như bench console khi không có API hay công cụ "
	"nào làm được. Mỗi script là một đề xuất Chờ duyệt, chỉ duyệt bằng nút Duyệt trong khung "
	"Trao đổi với bot (vai trò ERP AI Instructor). Chạy một lần trong một giao dịch, lỗi thì không lưu gì, "
	"không hoàn tác được. Độc lập với ô sửa code. Tắt thì script đã duyệt cũng không chạy. "
	"Script chạy với quyền Administrator.",
}

# 2026-11-27 layout (docs/superpowers/specs/2026-11-27-erp-ai-setting-layout-design.md): the form of ERP AI Setting
# as tab -> section -> columns, every column its data fields in form order. A section of short fields has a left and
# a right column; a section with a wide field has one.
SETTING_LAYOUT = (
	(
		"tab_activation",
		"Kích hoạt & quyền",
		(
			("section_activation", (("enabled", "permission_level"), ("agent_enabled_at",))),
			(
				"section_permissions",
				(
					(
						"unrestricted_enabled",
						"record_tools_enabled",
						"act_now_enabled",
						"code_change_enabled",
					),
					(
						"console_enabled",
						"one_click_approval_enabled",
						"server_script_read_enabled",
						"site_environment",
					),
				),
			),
		),
	),
	(
		"tab_autonomy",
		"Mức tự chủ",
		(
			(
				"section_autonomy",
				(
					("level_cap_a", "level_cap_b", "level_cap_c"),
					("level_cap_d", "level_cap_e", "level_cap_f"),
				),
			),
			("section_confidence", (("confidence_threshold",), ("auto_approve_streak",))),
			("section_catalog", (("catalog_rules", "user_templates"),)),
		),
	),
	(
		"tab_model",
		"Model & chi phí",
		(
			(
				"section_model",
				(
					("model_classify_default", "trigger_keyword"),
					("thinking_text", "answer_delay_min_s", "answer_delay_max_s"),
				),
			),
			("section_credentials", (("credentials",),)),
			(
				"section_limits",
				(
					("max_turns_per_run", "max_runs_per_ticket_per_day"),
					("max_keys_per_call", "request_timeout_s"),
				),
			),
			(
				"section_budget",
				(
					("monthly_budget_usd", "spent_this_month_usd"),
					(
						"price_input_per_mtok",
						"price_cache_write_per_mtok",
						"price_cache_read_per_mtok",
						"price_output_per_mtok",
					),
				),
			),
		),
	),
	(
		"tab_routing",
		"Phiếu & định tuyến",
		(
			("section_routing", (("excluded_teams", "excluded_title_prefixes", "category_mapping"),)),
			("section_assignment", (("auto_assign_enabled", "tag_assignees"),)),
			("section_routing_rules", (("routing_rules", "default_assignee"),)),
			(
				"section_ticket_fields",
				(
					("field_ticket_nature", "field_erp_module", "field_origin", "origin_board_value"),
					("field_due_date", "field_project", "field_item_code", "field_serial_no"),
				),
			),
		),
	),
	(
		"tab_knowledge",
		"Trả lời & tri thức",
		(
			(
				"section_knowledge",
				(
					(
						"reply_enabled",
						"resolve_on_tasks_done_enabled",
						"close_silent_f_enabled",
						"close_silent_f_days",
					),
					("kb_draft_enabled", "knowledge_search_limit", "manuals_dir"),
				),
			),
			("section_reports", (("allowed_reports", "report_row_limit"),)),
			("section_digest", (("prompt_digest",),)),
			(
				"section_lessons",
				(
					("lessons_enabled",),
					("lessons_max_per_request", "lessons_max_chars", "lesson_teach_marker"),
				),
			),
		),
	),
	(
		"tab_reports",
		"Báo cáo & cảnh báo",
		(
			("section_operations", (("coo_report_recipients", "daily_report_weekends"),)),
			("section_review", (("monthly_reviewers", "review_sample_size"),)),
			(
				"section_reminders",
				(
					("d_ticket_watcher", "due_reminder_hours", "ba_note_due_hours"),
					("task_due_days", "max_tasks_per_run"),
				),
			),
			("section_kpi", (("kpi_targets",),)),
			("section_report_marks", (("daily_report_sent_on",), ("budget_alert_sent_month",))),
			("section_alerts", (("alert_recipients", "privilege_alert_checked_until"),)),
		),
	),
	(
		"tab_advanced",
		"Nâng cao",
		(
			("section_code_change", (("code_change_apps",),)),
			(
				"section_prompts",
				(
					(
						"prompt_override_classify",
						"prompt_override_reasoning",
						"prompt_override_category_guide",
						"prompt_revisions",
					),
				),
			),
		),
	),
)
# Rarely changed after setup: these sections start folded.
SETTING_COLLAPSIBLE_SECTIONS = ("section_ticket_fields", "section_code_change", "section_prompts")
# A short field fits half the width; every other field (Table, Code, Long Text, Small Text) is wide.
SHORT_FIELD_TYPES = ("Check", "Select", "Int", "Float", "Data", "Link", "Date", "Datetime")
# A Small Text that holds one short phrase, not a list: it fits a column like a Data field.
ONE_LINE_TEXT_FIELDS = ("thinking_text",)


FEAT007_LOG_COLUMNS = {
	"created_labels": "Small Text",
	"predicted_confidence_pct": "Int",
	"split_requested": "Check",
	"split_requests": "Small Text",
	"site_environment": "Data",
}


# Wordings that contradicted the code that writes the field (T5 review round 1).
FORBIDDEN_PHRASES = {
	# FEAT-007 design.md:162, 184: record tools moved from the code-change switch to their own switch.
	"ERP AI Setting": {
		# FEAT-007 spec-addendum-3.md:88 (T64): L2 no longer "has the same tools as L1".
		# 2026-11-27: seven permission switches now, so no text counts them as five.
		"permission_level": ("ô Cho phép sửa code", "L2 có công cụ như L1", "năm quyền"),
		"site_environment": ("năm quyền",),
		**{f"level_cap_{category}": ("năm quyền",) for category in "abcdef"},
		**{
			fieldname: ("năm quyền",)
			for fieldname in (
				"prompt_override_classify",
				"prompt_override_reasoning",
				"prompt_override_category_guide",
			)
		},
		# FEAT-007 spec-addendum-4.md AC-29 (T64): an empty catalog no longer means "no ERP writes".
		"catalog_rules": ("bot không ghi ERP ngoài phiếu",),
		"code_change_enabled": ("tạo và sửa bản ghi trực tiếp",),
		# FEAT-008: a taught rule never waits for approval; resolved tickets are a batch-2 source.
		"lesson_teach_marker": ("chờ duyệt",),
		"lessons_enabled": ("phiếu đã giải quyết",),
	},
	"ERP AI Log": {
		"instructor": ("người ra lệnh", "khi phiếu mới tạo"),
		"tools_called": ("lần chạy này",),
		"predicted_confidence": ("thường khiến", "không được áp dụng"),
		"stop_reason": ("là lỗi khi gọi nhà cung cấp",),
		"latency_ms": ("có thể để trống",),
	},
	"ERP AI KPI Week": {
		# FEAT-007 design-w1-fixes-14.md Điểm 3: the median is empty when no ticket of the week has a response (kpi.py:61), not only when the sample is 0.
		"first_response_median_min": ("Rỗng khi mẫu 0",),
	},
}


def load_doctype(config):
	path = DOCTYPE_DIR / config["folder"] / f"{config['folder']}.json"
	return json.loads(path.read_text(encoding="utf-8"))


def visible_fields(doctype_json):
	return [
		field
		for field in doctype_json["fields"]
		if field["fieldtype"] not in BREAK_TYPES and not field.get("hidden")
	]


def section_breaks(doctype_json):
	return [field for field in doctype_json["fields"] if field["fieldtype"] == "Section Break"]


def form_order(doctype_json):
	"""field_order without Column and Tab Breaks: the data fields and the Section Breaks, in form order."""
	types = {field["fieldname"]: field["fieldtype"] for field in doctype_json["fields"]}
	return [name for name in doctype_json["field_order"] if types[name] not in ("Column Break", "Tab Break")]


def data_order(doctype_json):
	"""field_order without any break: the data fields only, in form order."""
	types = {field["fieldname"]: field["fieldtype"] for field in doctype_json["fields"]}
	return [name for name in doctype_json["field_order"] if types[name] not in BREAK_TYPES]


def form_tree(doctype_json):
	"""field_order as ((tab, label, ((section, (column, ...)), ...)), ...), a column being its data fields.

	Fields before the first Tab Break fall in a tab named None, fields before the first Section Break of a tab in a
	section named None, so a form without tabs still gives a tree to compare."""
	by_name = {field["fieldname"]: field for field in doctype_json["fields"]}
	tabs = []
	for name in doctype_json["field_order"]:
		fieldtype = by_name[name]["fieldtype"]
		if fieldtype == "Tab Break":
			tabs.append((name, by_name[name].get("label"), []))
			continue
		if not tabs:
			tabs.append((None, None, []))
		sections = tabs[-1][2]
		if fieldtype == "Section Break":
			sections.append((name, [[]]))
			continue
		if not sections:
			sections.append((None, [[]]))
		columns = sections[-1][1]
		if fieldtype == "Column Break":
			columns.append([])
		else:
			columns[-1].append(name)
	return tuple(
		(
			tab,
			label,
			tuple((section, tuple(tuple(column) for column in columns)) for section, columns in sections),
		)
		for tab, label, sections in tabs
	)


def is_short_field(field):
	return field["fieldtype"] in SHORT_FIELD_TYPES or field["fieldname"] in ONE_LINE_TEXT_FIELDS


class TestDoctypeDescriptions(FrappeTestCase):
	def each_doctype(self):
		return [(doctype, config, load_doctype(config)) for doctype, config in DOCTYPE_CONFIG.items()]

	def test_every_visible_field_has_description(self):
		for doctype, config, doctype_json in self.each_doctype():
			with self.subTest(doctype=doctype):
				fields = visible_fields(doctype_json)
				self.assertEqual(len(fields), config["field_count"])
				missing = [f["fieldname"] for f in fields if not (f.get("description") or "").strip()]
				self.assertEqual(
					missing, [], f"{doctype}: thiếu mô tả {len(missing)}/{len(fields)}: {missing}"
				)

	def test_descriptions_at_most_400_chars(self):
		for doctype, _config, doctype_json in self.each_doctype():
			with self.subTest(doctype=doctype):
				too_long = {
					f["fieldname"]: len(f["description"])
					for f in visible_fields(doctype_json)
					if len(f.get("description") or "") > MAX_DESCRIPTION_CHARS
				}
				self.assertEqual(too_long, {}, f"{doctype}: mô tả dài quá {MAX_DESCRIPTION_CHARS} ký tự")

	def test_required_phrases_present(self):
		for doctype, config, doctype_json in self.each_doctype():
			with self.subTest(doctype=doctype):
				by_name = {f["fieldname"]: f for f in visible_fields(doctype_json)}
				self.assertEqual(set(config["phrases"]), set(by_name), f"{doctype}: cấu hình test lệch field")
				missing = {}
				for fieldname, phrases in config["phrases"].items():
					description = by_name[fieldname].get("description") or ""
					absent = [p for p in phrases if p.lower() not in description.lower()]
					if absent:
						missing[fieldname] = absent
				self.assertEqual(missing, {}, f"{doctype}: thiếu cụm")

	def test_forbidden_phrases_absent(self):
		for doctype, forbidden in FORBIDDEN_PHRASES.items():
			by_name = {f["fieldname"]: f for f in visible_fields(load_doctype(DOCTYPE_CONFIG[doctype]))}
			present = {}
			for fieldname, phrases in forbidden.items():
				description = (by_name[fieldname].get("description") or "").lower()
				found = [p for p in phrases if p.lower() in description]
				if found:
					present[fieldname] = found
			self.assertEqual(present, {}, f"{doctype}: còn cụm sai")

	def test_read_only_fields_say_system_writes(self):
		for doctype, config, doctype_json in self.each_doctype():
			with self.subTest(doctype=doctype):
				by_name = {f["fieldname"]: f for f in visible_fields(doctype_json)}
				read_only = {f for f, field in by_name.items() if field.get("read_only")}
				self.assertEqual(read_only, set(config["read_only_fields"]))
				for fieldname in read_only:
					description = by_name[fieldname].get("description") or ""
					self.assertIn(SYSTEM_WRITES, description, f"{doctype}.{fieldname}")
					self.assertIn(NOT_EDITABLE, description, f"{doctype}.{fieldname}")

	def test_section_breaks_labelled_in_vietnamese(self):
		for doctype, config, doctype_json in self.each_doctype():
			with self.subTest(doctype=doctype):
				breaks = section_breaks(doctype_json)
				self.assertGreaterEqual(len(breaks), 2)
				self.assertEqual(len(breaks), config["section_count"])
				expected = [(name, label) for name, label, _first in config["sections"]]
				self.assertEqual([(b["fieldname"], b.get("label")) for b in breaks], expected)
				for section in breaks:
					self.assertTrue(VIETNAMESE_ACCENTS.search(section["label"]), section["fieldname"])
					self.assertNotIn("(USD)", section["label"])
				order = doctype_json["field_order"]
				for name, _label, first in config["sections"]:
					self.assertEqual(order.index(first), order.index(name) + 1, f"{doctype}: {name}")

	def test_descriptions_have_no_sensitive_data(self):
		for doctype, _config, doctype_json in self.each_doctype():
			with self.subTest(doctype=doctype):
				for field in visible_fields(doctype_json):
					description = field.get("description") or ""
					where = f"{doctype}.{field['fieldname']}"
					self.assertNotIn("sk-", description, where)
					self.assertNotIn("miyano", description.lower(), where)
					for email in EMAIL_PATTERN.findall(description):
						self.assertTrue(email.lower().endswith(SAFE_EMAIL_DOMAINS), f"{where}: {email}")

	def test_descriptions_contain_no_stored_setting_values(self):
		setting = frappe.get_single("ERP AI Setting")
		doctype_json = load_doctype(DOCTYPE_CONFIG["ERP AI Setting"])
		stored = {}
		for field in visible_fields(doctype_json):
			# A Select value is one of the fixed options a description may name (site_environment), not site data.
			if field["fieldtype"] in ("Table", "Password", "Select"):
				continue
			value = setting.get(field["fieldname"])
			if isinstance(value, str) and len(value.strip()) >= MIN_STORED_VALUE_CHARS:
				stored[field["fieldname"]] = value.strip().lower()
		for field in visible_fields(doctype_json):
			description = (field.get("description") or "").lower()
			for source, value in stored.items():
				self.assertNotIn(
					value, description, f"{field['fieldname']} chứa giá trị đang lưu của {source}"
				)

	def test_skipped_fields_still_follows_value_after(self):
		doctype_json = load_doctype(DOCTYPE_CONFIG["ERP AI Log"])
		order = doctype_json["field_order"]
		self.assertEqual(order.index("skipped_fields"), order.index("value_after") + 1)
		names = [f["fieldname"] for f in doctype_json["fields"]]
		self.assertEqual(names, order)

	def test_feat007_log_columns_have_design_types(self):
		# FEAT-007 design.md 2.3, design-w0-fixes.md F-5: the five added columns and their types.
		by_name = {f["fieldname"]: f for f in load_doctype(DOCTYPE_CONFIG["ERP AI Log"])["fields"]}
		actual = {name: by_name.get(name, {}).get("fieldtype") for name in FEAT007_LOG_COLUMNS}
		self.assertEqual(actual, FEAT007_LOG_COLUMNS)

	def test_section_breaks_carry_only_label(self):
		# 2026-11-27: a section of ERP AI Setting may also start folded (collapsible: 1), nothing else.
		for doctype, _config, doctype_json in self.each_doctype():
			with self.subTest(doctype=doctype):
				for section in section_breaks(doctype_json):
					where = f"{doctype}.{section['fieldname']}"
					keys = {"fieldname", "fieldtype", "label"}
					if doctype == "ERP AI Setting" and section["fieldname"] in SETTING_COLLAPSIBLE_SECTIONS:
						keys.add("collapsible")
						self.assertEqual(section.get("collapsible"), 1, where)
					self.assertEqual(set(section), keys, where)

	def test_setting_tabs_sections_columns(self):
		# 2026-11-27 layout: seven tabs by purpose, each section in its tab, each column its fields in order.
		doctype_json = load_doctype(DOCTYPE_CONFIG["ERP AI Setting"])
		self.assertEqual(form_tree(doctype_json), SETTING_LAYOUT)
		self.assertEqual(
			[field["fieldname"] for field in doctype_json["fields"]], doctype_json["field_order"]
		)
		# Every data field is placed exactly once; the layout names no field the DocType lacks.
		placed = [
			name
			for _tab, _label, sections in SETTING_LAYOUT
			for _section, columns in sections
			for column in columns
			for name in column
		]
		self.assertEqual(sorted(placed), sorted(data_order(doctype_json)))
		self.assertEqual(len(placed), len(set(placed)))
		sections = [
			section for _tab, _label, tab_sections in SETTING_LAYOUT for section, _columns in tab_sections
		]
		self.assertEqual(
			sections, [name for name, _label, _first in DOCTYPE_CONFIG["ERP AI Setting"]["sections"]]
		)

	def test_setting_short_fields_split_in_two_columns(self):
		# A section of two or more short fields has a left and a right column, neither empty; a wide field
		# (Table, Code, Long Text, a Small Text list) never sits in a column: its section has one column.
		doctype_json = load_doctype(DOCTYPE_CONFIG["ERP AI Setting"])
		by_name = {field["fieldname"]: field for field in doctype_json["fields"]}
		for _tab, _label, sections in form_tree(doctype_json):
			for section, columns in sections:
				with self.subTest(section=section):
					fields = [by_name[name] for column in columns for name in column]
					wide = [field["fieldname"] for field in fields if not is_short_field(field)]
					short = [field["fieldname"] for field in fields if is_short_field(field)]
					if wide:
						self.assertEqual(len(columns), 1, f"{section}: wide field {wide} in a column")
						self.assertLessEqual(
							len(short), 1, f"{section}: short fields {short} stacked by {wide}"
						)
					elif len(short) >= 2:
						self.assertEqual(
							len(columns), 2, f"{section}: short fields {short} not in two columns"
						)
						self.assertTrue(all(columns), f"{section}: an empty column")
					else:
						self.assertEqual(len(columns), 1, section)

	def test_setting_tab_and_column_breaks_shape(self):
		# A Tab Break carries a Vietnamese label and opens with a labelled section; a Column Break carries nothing.
		# The form opens on a tab: a field before the first Tab Break would land in an extra "Details" tab.
		doctype_json = load_doctype(DOCTYPE_CONFIG["ERP AI Setting"])
		order = doctype_json["field_order"]
		by_name = {field["fieldname"]: field for field in doctype_json["fields"]}
		self.assertEqual(by_name[order[0]]["fieldtype"], "Tab Break")
		for index, name in enumerate(order):
			field = by_name[name]
			with self.subTest(fieldname=name):
				if field["fieldtype"] == "Tab Break":
					self.assertEqual(set(field), {"fieldname", "fieldtype", "label"})
					self.assertTrue(name.startswith("tab_"))
					self.assertTrue(VIETNAMESE_ACCENTS.search(field["label"]))
					self.assertEqual(by_name[order[index + 1]]["fieldtype"], "Section Break")
				elif field["fieldtype"] == "Column Break":
					self.assertEqual(set(field), {"fieldname", "fieldtype"})
					self.assertTrue(name.startswith("column_break_"))

	def test_console_switch_field_on_disk(self):
		# CHG-010 Task 1: read from the JSON file; the site's meta is not migrated for the new field.
		doctype_json = load_doctype(DOCTYPE_CONFIG["ERP AI Setting"])
		by_name = {f["fieldname"]: f for f in doctype_json["fields"]}
		field = by_name["console_enabled"]
		self.assertEqual({key: field.get(key) for key in CONSOLE_FIELD_SPEC}, CONSOLE_FIELD_SPEC)
		self.assertFalse(field.get("read_only"))
		# 2026-11-27: console_enabled opens the right column of section_permissions; a Column Break is layout only.
		order = form_order(doctype_json)
		self.assertEqual(order.index("console_enabled"), order.index("code_change_enabled") + 1)
		self.assertLess(order.index("section_permissions"), order.index("console_enabled"))
		self.assertLess(order.index("console_enabled"), order.index("section_autonomy"))

	def test_code_change_block_follows_feat006_fields(self):
		doctype_json = load_doctype(DOCTYPE_CONFIG["ERP AI Setting"])
		# 2026-11-27 layout: Column and Tab Breaks are left out; the sections are grouped in tabs by purpose, so
		# the section order changed (SETTING_LAYOUT pins the whole tree). Each section keeps its fields and their
		# order; the long sections are split into labelled sections that follow each other.
		order = form_order(doctype_json)
		start = order.index("default_assignee")
		# FEAT-007 design.md:98, 106 (NFR-8): the switch moved to section_permissions; the block keeps the app list.
		# design.md:104-106: section_ticket_fields (AC-24) follows the routing block (default_assignee is its last
		# field since prompt_digest moved to the knowledge tab).
		# design.md:107: the nine knowledge fields, then section_operations with its twelve fields (design.md:108),
		# section_code_change and section_prompts (design.md:109) in the last tab.
		self.assertEqual(
			order[start:],
			[
				"default_assignee",
				"section_ticket_fields",
				"field_ticket_nature",
				"field_erp_module",
				"field_origin",
				"origin_board_value",
				"field_due_date",
				"field_project",
				"field_item_code",
				"field_serial_no",
				"section_knowledge",
				"reply_enabled",
				"resolve_on_tasks_done_enabled",
				"close_silent_f_enabled",
				"close_silent_f_days",
				"kb_draft_enabled",
				"knowledge_search_limit",
				"manuals_dir",
				"section_reports",
				"allowed_reports",
				"report_row_limit",
				"section_digest",
				"prompt_digest",
				"section_lessons",
				"lessons_enabled",
				"lessons_max_per_request",
				"lessons_max_chars",
				"lesson_teach_marker",
				"section_operations",
				"coo_report_recipients",
				"daily_report_weekends",
				"section_review",
				"monthly_reviewers",
				"review_sample_size",
				"section_reminders",
				"d_ticket_watcher",
				"due_reminder_hours",
				"ba_note_due_hours",
				"task_due_days",
				"max_tasks_per_run",
				"section_kpi",
				"kpi_targets",
				"section_report_marks",
				"daily_report_sent_on",
				"budget_alert_sent_month",
				"section_alerts",
				"alert_recipients",
				"privilege_alert_checked_until",
				"section_code_change",
				"code_change_apps",
				"section_prompts",
				"prompt_override_classify",
				"prompt_override_reasoning",
				"prompt_override_category_guide",
				"prompt_revisions",
			],
		)
		start = order.index("section_permissions")
		self.assertEqual(
			# CHG-010: console_enabled follows code_change_enabled; 2026-11-27: server_script_read_enabled is the 7th.
			order[start : start + 10],
			[
				"section_permissions",
				"unrestricted_enabled",
				"record_tools_enabled",
				"act_now_enabled",
				"code_change_enabled",
				"console_enabled",
				"one_click_approval_enabled",
				"server_script_read_enabled",
				"site_environment",
				# 2026-11-27: the section ends here (the next tab opens with section_autonomy).
				"section_autonomy",
			],
		)
		self.assertLess(order.index("routing_rules"), order.index("section_code_change"))
		by_name = {f["fieldname"]: f for f in doctype_json["fields"]}
		actual = {
			fieldname: {key: by_name[fieldname].get(key) for key in expected}
			for fieldname, expected in CODE_CHANGE_FIELDS.items()
		}
		self.assertEqual(actual, CODE_CHANGE_FIELDS)
		self.assertFalse(any(by_name[name].get("read_only") for name in CODE_CHANGE_FIELDS))
