AGENT_USER = "ai.agent@miyano.com.vn"
ROLE_AGENT = "ERP AI Agent"
ROLE_INSTRUCTOR = "ERP AI Instructor"
HELPDESK_AGENT_ROLE = "Agent"

SETTING_DOCTYPE = "ERP AI Setting"
CREDENTIAL_DOCTYPE = "ERP AI Credential"
LOG_DOCTYPE = "ERP AI Log"
PROPOSAL_DOCTYPE = "ERP AI Change Proposal"

LEVELS = ("L0", "L1", "L2", "L3")
CATEGORIES = ("A", "B", "C", "D", "E", "F")
CONFIDENCE_VALUES = ("Cao", "Trung bình", "Thấp")
CLASSIFIED_BY_AI = "AI"
CLASSIFIED_BY_HUMAN = "Người"

KEY_STATUS_ACTIVE = "Hoạt động"
KEY_STATUS_PAUSED = "Tạm nghỉ"
KEY_STATUS_QUOTA_EXHAUSTED = "Hết hạn mức"
KEY_STATUS_BAD_KEY = "Lỗi khóa"

CHANGE_STATUS_PENDING = "Chờ duyệt"
CHANGE_STATUS_REJECTED = "Đã từ chối"
CHANGE_STATUS_APPROVED = "Đã duyệt"
CHANGE_STATUS_APPLYING = "Đang áp dụng"
CHANGE_STATUS_APPLIED = "Đã áp dụng"
CHANGE_STATUS_FAILED = "Lỗi"
CHANGE_STATUS_STALE = "Hết hiệu lực"
CHANGE_STATUS_UNDOING = "Đang hoàn tác"
CHANGE_STATUS_UNDONE = "Đã hoàn tác"

CHANGE_KIND_CODE = "Thay đổi code"
CHANGE_KIND_COMMAND = "Lệnh bench"
CHANGE_STEPS = ("propose", "approve", "reject", "apply", "fail", "stale", "undo")

TRIGGER_TICKET_INSERT = "ticket_insert"
TRIGGER_COMMENT_MENTION = "comment_mention"
TRIGGER_CHANGE_ACTION = "change_action"
TRIGGER_REQUESTER_REPLY = "requester_reply"
TRIGGER_KB_DRAFT = "kb_draft"

JOB_TIMEOUT_S = 600
ANSWER_DELAY_MAX_S = 30
JOB_SAFETY_MARGIN_S = 60
PROBE_TIMEOUT_S = 10
COMMAND_TIMEOUT_S = JOB_TIMEOUT_S - JOB_SAFETY_MARGIN_S
RUN_BACKSTOP_S = COMMAND_TIMEOUT_S + JOB_SAFETY_MARGIN_S // 2

CORE_APPS = ("frappe", "erpnext", "helpdesk", "hrms")
BOT_GIT_NAME = "ERP AI Agent"
BOT_GIT_EMAIL = "erp-ai-agent@bot.invalid"

CLASSIFICATION_FIELDS = ("ticket_type", "agent_group", "priority")

TITLE_WRONG_USER = "erp_ai: sai tài khoản job"
TITLE_RUN_FAILED = "erp_ai: lần chạy lỗi"
TITLE_ALARM = "erp_ai: CẢNH BÁO"
TITLE_NOTICE = "erp_ai: thông báo"
TITLE_STATUS_FAILED = "erp_ai: chỉ báo trạng thái lỗi"
TITLE_CHANGE_FAILED = "erp_ai: áp dụng thay đổi lỗi"

AGENT_STATUS_EVENT = "erp_ai:agent_status"

LOGGER_NAME = "erp_ai"

PANEL_METHODS = (
	"erp_ai.ticket_panel.get_panel_data",
	"erp_ai.ticket_panel.send_message",
)
PANEL_MAX_MESSAGE_CHARS = 2000

# CHG-002: block proposals (design 2.1, 2.5, design-addendum-1 A-1.2; ADR-040 QĐ 5, 7).
OPERATION_DOCTYPE = "ERP AI Change Operation"
CHANGE_OP_EDIT = "Sửa"
CHANGE_OP_CREATE = "Tạo"
CHANGE_OP_DELETE = "Xóa"
CHANGE_OP_RENAME = "Đổi tên"
CHANGE_OPS = (CHANGE_OP_EDIT, CHANGE_OP_CREATE, CHANGE_OP_DELETE, CHANGE_OP_RENAME)
RESTART_STATUS_SENT = "Đã gửi"
RESTART_STATUS_CONFIRMED = "Đã xác nhận"
RESTART_STATUS_UNCONFIRMED = "Chưa xác nhận"
RESTART_STATUS_LAUNCH_FAILED = "Lỗi khởi chạy"
CHANGE_MAX_FILE_OPS = 50
CHANGE_MAX_TOTAL_BYTES = 8 * 1024 * 1024
CHANGE_MAX_COMMANDS = 6
CHANGE_FILE_MAX_BYTES = 2 * 1024 * 1024
RESTART_WEB_STOP_S = 40
RESTART_TIMEOUT_S = JOB_TIMEOUT_S + RESTART_WEB_STOP_S + JOB_SAFETY_MARGIN_S
RESTART_LAUNCH_TIMEOUT_S = 10

# Bot conversation DocType (bot-messages): the human<->bot messages live here, not in HD Ticket comments.
MESSAGE_DOCTYPE = "ERP AI Message"
MESSAGE_KIND_CHAT = "chat"
MESSAGE_KIND_ROUTING = "routing"
MESSAGE_KIND_PROPOSAL = "proposal"
MESSAGE_KIND_RESULT = "result"
MESSAGE_KINDS = (
	MESSAGE_KIND_CHAT,
	MESSAGE_KIND_ROUTING,
	MESSAGE_KIND_PROPOSAL,
	MESSAGE_KIND_RESULT,
)

# FEAT-007 (F-1): catalog actions and modes, KPI ids, ticket-content DocTypes; one block, keep it last.
ACTION_CREATE_USER = "Tạo tài khoản theo mẫu"
ACTION_ADD_TEAM_MEMBER = "Thêm người vào nhóm Helpdesk"
ACTION_ADD_HOLIDAY = "Thêm ngày nghỉ"
ACTION_SET_ITEM_GROUP = "Đổi nhóm hàng"
ACTION_CREATE_CUSTOM_FIELD = "Tạo Custom Field"
ACTION_UPDATE_FIELDS = "Đổi trường"
CATALOG_ACTIONS = (
	ACTION_CREATE_USER,
	ACTION_ADD_TEAM_MEMBER,
	ACTION_ADD_HOLIDAY,
	ACTION_SET_ITEM_GROUP,
	ACTION_CREATE_CUSTOM_FIELD,
	ACTION_UPDATE_FIELDS,
)
MODE_DENY = "Cấm"
MODE_NEEDS_APPROVAL = "Cần duyệt"
MODE_AUTO = "Tự làm"
CATALOG_MODES = (MODE_DENY, MODE_NEEDS_APPROVAL, MODE_AUTO)
KPI_IDS = (
	"first_response_minutes",
	"complete_fields_pct",
	"closed_without_human_pct",
	"b_resolution_hours",
	"c_task_in_3_days_pct",
	"stale_over_5_days",
)
TICKET_CONTENT_DOCTYPES = ("HD Ticket", "Comment", "Communication", "File")
