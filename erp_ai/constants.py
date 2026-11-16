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
	# CHG-008 (ADR-044 QĐ 1): the panel's one decision method, for every action of `ticket_panel.PANEL_DECISIONS`.
	"erp_ai.ticket_panel.decide_proposal",
)
PANEL_MAX_MESSAGE_CHARS = 2000
# CHG-008 design D-7: the most proposal cards the panel returns for one ticket, newest first.
PANEL_MAX_PROPOSALS = 200

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

# The conversation between people and the bot lives in this DocType, not in HD Ticket comments. What the bot
# concluded and did on a ticket is ticket information (its fields), never a message here.
MESSAGE_DOCTYPE = "ERP AI Message"

# FEAT-008: the bot's lesson store (ERP AI Lesson and its history rows).
LESSON_DOCTYPE = "ERP AI Lesson"
LESSON_EVENT_DOCTYPE = "ERP AI Lesson Event"
LESSON_STATUS_PENDING = "Chờ duyệt"
LESSON_STATUS_ACTIVE = "Đang dùng"
LESSON_STATUS_DISABLED = "Đã tắt"
LESSON_STATUS_REJECTED = "Bị từ chối"
LESSON_SOURCE_CORRECTION = "Người sửa"
LESSON_SOURCE_RESOLVED = "Phiếu đã giải quyết"
LESSON_SOURCE_TEACHING = "Người dạy"
LESSON_SOURCE_OUTCOME = "Kết quả duyệt và rà soát"
LESSON_STEPS = ("Tạo", "Cập nhật", "Duyệt", "Từ chối", "Tắt", "Bật")

# CHG-009 (design 2, 3.8; ADR-048): the run_event row of ERP AI Log, its event codes, the codes of a refused call
# or an early stop, how long a received call may wait, the Error Log title of a failed event write.
LOG_ENTRY_RUN_EVENT = "run_event"
EVENT_CALL_RECEIVED = "call_received"
EVENT_CALL_MERGED = "call_merged"
EVENT_CALL_BUSY = "call_busy"
EVENT_RUN_DONE = "run_done"
EVENT_RUN_FAILED = "run_failed"
SKIP_AGENT_DISABLED = "agent_disabled"
SKIP_CREATED_BY_AGENT = "created_by_agent"
SKIP_PREFILLED = "prefilled"
SKIP_DAILY_LIMIT = "daily_limit"
SKIP_LEVEL_L0 = "level_L0"
SKIP_NOT_SENDABLE = "not_sendable"
BOT_CALL_EXPIRY_S = 2 * JOB_TIMEOUT_S
TITLE_EVENT_FAILED = "erp_ai: ghi trạng thái bot lỗi"

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
