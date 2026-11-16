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
		"field_count": 77,
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
			"site_environment": ("production", "site test", "không bị chặn"),
			**{
				f"level_cap_{category}": ("Mức quyền", "năm quyền mở rộng", "chưa biết")
				for category in "abcdef"
			},
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
			"model_classify_default": ("phân loại", "model", "claude-haiku", "trần token"),
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
		},
		"section_count": 14,
		"read_only_fields": (
			"spent_this_month_usd",
			"agent_enabled_at",
			"daily_report_sent_on",
			"budget_alert_sent_month",
			"prompt_revisions",
			"privilege_alert_checked_until",
		),
		"sections": (
			("section_activation", "Bật và mức quyền", "enabled"),
			("section_permissions", "Năm quyền mở rộng (mặc định tắt)", "unrestricted_enabled"),
			("section_autonomy", "Mức tự chủ theo đầu mục và độ tin cậy", "level_cap_a"),
			("section_catalog", "Danh mục trắng", "catalog_rules"),
			("section_limits", "Giới hạn mỗi lần chạy", "max_turns_per_run"),
			("section_budget", "Ngân sách và đơn giá", "monthly_budget_usd"),
			("section_model", "Model, từ khóa và chỉ báo trả lời", "model_classify_default"),
			("section_routing", "Phân loại và nhóm loại trừ", "excluded_teams"),
			("section_ticket_fields", "Trường sẵn có của phiếu", "field_ticket_nature"),
			("section_code_change", "Sửa code và lệnh bench", "code_change_apps"),
			("section_knowledge", "Trả lời, đóng phiếu và tri thức", "reply_enabled"),
			("section_operations", "Báo cáo và vận hành", "coo_report_recipients"),
			("section_prompts", "Ghi đè prompt", "prompt_override_classify"),
			("section_alerts", "Cảnh báo và khóa API", "alert_recipients"),
		),
	},
	"ERP AI Credential": {
		"folder": "erp_ai_credential",
		"field_count": 18,
		"phrases": {
			"label": ("không trùng", "không phân biệt hoa thường"),
			"provider": ("nhà cung cấp", "Anthropic", "OpenAI", "bỏ qua"),
			"api_key": ("khóa bí mật", "mã hóa", "không hiện lại", "Log"),
			"model_classify": ("Setting", "phân loại", "claude-haiku", "trần token"),
			"model_reason": ("lập luận", "không dùng"),
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
	"ERP AI Log": {
		"folder": "erp_ai_log",
		"field_count": 43,
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
			),
			"turn": ("Lượt 0", "lượt 1", "lập luận"),
			"trigger": (
				"ticket_insert",
				"comment_mention",
				"requester_reply",
				"kb_draft",
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
			),
			"tools_called": ("tool", "trong lượt này"),
			"actions": ("hành động", "phiếu"),
			"value_before": ("JSON", "trước khi"),
			"value_after": ("JSON", "sau khi"),
			"skipped_fields": ("bỏ qua", "phân loại"),
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
			"predicted_assignee": ("người phụ trách", "dự đoán"),
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
		"permission_level": ("ô Cho phép sửa code", "L2 có công cụ như L1"),
		# FEAT-007 spec-addendum-4.md AC-29 (T64): an empty catalog no longer means "no ERP writes".
		"catalog_rules": ("bot không ghi ERP ngoài phiếu",),
		"code_change_enabled": ("tạo và sửa bản ghi trực tiếp",),
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
		for doctype, _config, doctype_json in self.each_doctype():
			with self.subTest(doctype=doctype):
				for section in section_breaks(doctype_json):
					self.assertEqual(
						set(section), {"fieldname", "fieldtype", "label"}, f"{doctype}.{section['fieldname']}"
					)

	def test_code_change_block_follows_feat006_fields(self):
		doctype_json = load_doctype(DOCTYPE_CONFIG["ERP AI Setting"])
		order = doctype_json["field_order"]
		start = order.index("prompt_digest")
		# FEAT-007 design.md:98, 106 (NFR-8): the switch moved to section_permissions; the block keeps the app list.
		# design.md:104-106: section_ticket_fields (AC-24) sits between section_routing and section_code_change.
		# design.md:107 (row 11 after row 10): section_knowledge follows the code-change block.
		# design.md:108 (row 12 after row 11): section_operations follows section_knowledge; design.md:109-110:
		# section_prompts (row 13) follows it, then section_alerts (row 14).
		self.assertEqual(
			order[start : start + 41],
			[
				"prompt_digest",
				"section_ticket_fields",
				"field_ticket_nature",
				"field_erp_module",
				"field_origin",
				"origin_board_value",
				"field_due_date",
				"field_project",
				"field_item_code",
				"field_serial_no",
				"section_code_change",
				"code_change_apps",
				"section_knowledge",
				"reply_enabled",
				"resolve_on_tasks_done_enabled",
				"close_silent_f_enabled",
				"close_silent_f_days",
				"kb_draft_enabled",
				"knowledge_search_limit",
				"manuals_dir",
				"allowed_reports",
				"report_row_limit",
				"section_operations",
				"coo_report_recipients",
				"daily_report_weekends",
				"monthly_reviewers",
				"review_sample_size",
				"d_ticket_watcher",
				"due_reminder_hours",
				"ba_note_due_hours",
				"task_due_days",
				"max_tasks_per_run",
				"kpi_targets",
				"daily_report_sent_on",
				"budget_alert_sent_month",
				"section_prompts",
				"prompt_override_classify",
				"prompt_override_reasoning",
				"prompt_override_category_guide",
				"prompt_revisions",
				"section_alerts",
			],
		)
		start = order.index("section_permissions")
		self.assertEqual(
			order[start : start + 7],
			[
				"section_permissions",
				"unrestricted_enabled",
				"record_tools_enabled",
				"act_now_enabled",
				"code_change_enabled",
				"one_click_approval_enabled",
				"site_environment",
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
