function setupForm({ doc, call, router }) {
	try {
		const EVENT = "erp_ai:agent_status";
		const ACTION_LABEL = "Trao đổi với bot";
		const TEXT_PANEL_TITLE = "Thông tin AI của phiếu & trao đổi với bot";
		const TEXT_CLOSE = "Đóng";
		const TEXT_AI_SECTION = "Thông tin AI của phiếu";
		const TEXT_CHAT_SECTION = "Trao đổi với bot";
		const TEXT_EMPTY_FIELD = "Chưa có";
		const TEXT_EMPTY_THREAD = "Chưa có tin nào.";
		// The one status sentence of the script, shown while an indicator is live (design 4.1);
		// every other sentence comes from the server.
		const TEXT_STATUS_RUNNING = "Đang xử lý…";
		const TEXT_LOADING = "Đang tải…";
		const TEXT_BOT_LABEL = "Bot";
		const TEXT_BOT_GUIDANCE =
			'Bot có thể không trả lời khi đang tắt, đang ở chế độ chỉ ghi nhận, phiếu không dùng AI hoặc thuộc nhóm loại trừ, đã hết lượt hôm nay, hoặc đang trả lời tin trước của phiếu này (khi đó hãy gửi lại sau). Nhận định và hướng xử lý của bot là tin trong ngăn này; người có vai trò ERP AI Instructor bấm "Duyệt hướng xử lý" dưới tin đó (nút chỉ có khi bot còn việc tự làm) thì bot làm theo.';
		// ADR-050: the newest guidance of the bot gets the approve button; a click sends this fixed text (server
		// prompts.APPROVE_GUIDANCE_TEXT) through the send box, as the person who clicked.
		const KIND_GUIDANCE = "guidance";
		const TEXT_APPROVE_GUIDANCE = "Duyệt hướng xử lý";
		const APPROVE_GUIDANCE_TEXT =
			"Duyệt hướng xử lý: bot làm ngay các bước trong hướng xử lý gần nhất, đúng phạm vi đã nêu.";
		// CHG-017: the two buttons under a finished plan; the server (ticket_panel.decide_result) checks who may click.
		const TEXT_RESULT_APPROVE = "Duyệt";
		const TEXT_RESULT_REJECT = "Không duyệt";
		const TEXT_RESULT_LINKS = "Bot đã tạo hoặc sửa (bấm để mở):";
		const TEXT_RESULT_FAILED = "Không ghi được kết quả duyệt; hãy thử lại.";
		const TEXT_LOAD_FAILED = "Không tải được dữ liệu của khu vực. Hãy đóng rồi mở lại.";
		const TEXT_INPUT_PLACEHOLDER =
			"Nhập câu hỏi cho bot. Enter để gửi, Shift+Enter để xuống dòng.";
		const TEXT_SEND = "Gửi";
		const TEXT_SENDING = "Đang gửi…";
		const TEXT_EMPTY_MESSAGE = "Hãy nhập nội dung trước khi gửi.";
		const TEXT_TOO_LONG = "Tin dài quá 2000 ký tự.";
		const TEXT_SEND_FAILED = "Không gửi được tin. Chữ bạn gõ vẫn còn, hãy thử lại.";
		const TEXT_CONSOLE_SCRIPT = "Script sẽ chạy (quyền Administrator):";
		const TEXT_CONSOLE_OUTPUT = "Kết quả:";
		const TEXT_OPEN_PROPOSAL = "Xem nội dung thay đổi";
		const OPEN_PROPOSAL_LABEL = "Mở đề xuất để Duyệt hoặc Từ chối";
		const TEXT_NEEDS_INSTRUCTOR = "Cần người có vai trò ERP AI Instructor duyệt.";
		// Server PANEL_REFUSALS["console_off"]: why a console card its viewer can open has no Duyệt.
		const TEXT_CONSOLE_OFF = "Chạy bench console đang tắt.";
		const TEXT_UNDO_AT_FORM = "Hoàn tác ở form";
		const TEXT_DECIDED_BY = "Người duyệt: ";
		const TEXT_RESTART = "Restart: ";
		const TEXT_FAILURE_REASON = "Lý do lỗi: ";
		const TEXT_APPROVE = "Duyệt";
		const TEXT_REJECT = "Từ chối";
		const TEXT_DECIDE_FAILED =
			"Không duyệt hoặc từ chối được đề xuất; hãy xem trạng thái hiện tại trên thẻ.";
		// The actions of the panel's decision method (server PANEL_DECISIONS), not method paths.
		const ACTION_APPROVE = "approve";
		const ACTION_REJECT = "reject";
		const STATUS_PENDING = "Chờ duyệt";
		const STATUS_APPLIED = "Đã áp dụng";
		const PROPOSAL_FORM_PREFIX = "/app/erp-ai-change-proposal/";
		const MAX_MESSAGE_CHARS = 2000;
		const NARROW_SCREEN_PX = 640;
		// The click that follows a press on the header action, after that press closed the panel from outside.
		const OUTSIDE_CLOSE_GRACE_MS = 500;
		// How close to the end a reader counts as "at the newest message".
		const BOTTOM_SLACK_PX = 40;
		// CHG-019: the Miyano bot (mascot, launcher, card with the support chat); plain DOM, one per page load.
		const SVG_NS = "http://www.w3.org/2000/svg";
		const MASCOT_COLOR = "#12b5d8";
		const TEXT_BOT_TITLE = "Miyano bot";
		const TEXT_BOT_LAUNCHER = "Trò chuyện với Miyano bot";
		const TEXT_BOT_DRAG_HINT = "Kéo để di chuyển, bấm để mở";
		const TEXT_BOT_ASK_TITLE = "Hỏi Miyano bot";
		const TEXT_BOT_HELLO = "Xin chào! Hãy hỏi tôi cách dùng helpdesk hoặc ERP.";
		const TEXT_BOT_THINKING = "Miyano bot đang suy nghĩ…";
		const TEXT_BOT_FAILED = "Miyano bot chưa trả lời được. Hãy thử lại.";
		const TEXT_BOT_PLACEHOLDER = "Nhập câu hỏi, Enter để gửi";
		const TEXT_BOT_NEW_TICKET = "Tạo phiếu từ cuộc trò chuyện này";
		const TEXT_BOT_RESTART = "Cuộc trò chuyện mới";
		const TEXT_BOT_QUESTION = "Câu hỏi";
		const TEXT_BOT_COPIED = "Đã chép cuộc trò chuyện. Hãy dán (Ctrl+V) vào mô tả phiếu.";
		const MAX_QUESTION_CHARS = 1000;
		const SUBJECT_CHARS = 140;
		const BOT_WIDTH_PX = 72;
		const BOT_HEIGHT_PX = 58;
		const BOT_EDGE_PX = 8;
		const BOT_OFFSET_PX = 24;
		const BOT_DRAG_PX = 5;
		const BOT_CARD_WIDTH_PX = 360;
		const BOT_CARD_HEIGHT_PX = 480;
		const BOT_CARD_GAP_PX = 12;
		// ADR-051 decision 3: the bot's only stored values; the keys are the old Vue bot's, so a person's choices carry over.
		const BOT_POSITION_KEY = "miyano_bot_position";
		const BOT_SOUND_KEY = "miyano_bot_sound";
		const BOT_CHAT_KEY = "miyano_support_chat";
		const BOT_REPLY_TYPE = "Bot Reply";
		const MAX_BADGE = 99;
		const TEXT_BOT_FOR_YOU = "Dành cho bạn";
		const TEXT_BOT_NEW = "mới";
		const TEXT_BOT_SHOW = "Xem ▾";
		const TEXT_BOT_HIDE = "Thu gọn ▴";
		const TEXT_BOT_READ_ALL = "Đọc hết";
		const TEXT_BOT_ASSIGNED = "Giao cho bạn";
		const TEXT_BOT_REPLIED = "Bot đã trả lời";
		const TEXT_BOT_MUTE = "Tắt tiếng";
		const TEXT_BOT_UNMUTE = "Bật tiếng";
		// Two short rising sine notes (A5 then E6), quiet enough not to startle.
		const CHIME_NOTES_HZ = [880, 1318.5];
		const CHIME_GAP_S = 0.12;
		const CHIME_LENGTH_S = 0.35;
		const CHIME_VOLUME = 0.15;
		const BOT_CSS = [
			".miyano-bot-launcher{position:fixed;z-index:40;padding:0;border:0;background:transparent;cursor:grab;touch-action:none;user-select:none;transition:transform .15s}",
			".miyano-bot-launcher:hover{transform:scale(1.05)}",
			".miyano-bot-launcher:focus-visible{outline:2px solid #12b5d8;outline-offset:2px}",
			".miyano-bot-mascot{display:block;width:100%;height:100%;filter:drop-shadow(0 2px 4px rgba(0,0,0,.25));pointer-events:none}",
			".miyano-bot-card{position:fixed;z-index:40;display:flex;flex-direction:column;overflow:hidden;background:#fff;border:1px solid #e5e7eb;border-radius:12px;box-shadow:0 12px 32px rgba(15,23,42,.18);font-size:13px;line-height:1.5;color:#1f2937}",
			".miyano-bot-card[hidden],.miyano-bot-card [hidden]{display:none}",
			".miyano-bot-card,.miyano-bot-card *{box-sizing:border-box}",
			".miyano-bot-head{display:flex;flex:none;align-items:center;gap:8px;padding:8px 12px;border-bottom:1px solid #e5e7eb}",
			".miyano-bot-head-mascot{width:28px;height:22px;flex:none}",
			".miyano-bot-head-title{flex:1;font-size:14px;color:#111827}",
			".miyano-bot-ticket{flex:1;min-height:0;overflow-y:auto;padding:8px 12px}",
			".miyano-bot-chat{display:flex;flex:1;flex-direction:column;min-height:0}",
			".miyano-bot-chat-head{display:flex;flex:none;align-items:center;gap:8px;padding:8px 12px 0}",
			".miyano-bot-thread{display:flex;flex:1;flex-direction:column;gap:8px;min-height:0;overflow-y:auto;padding:8px 12px}",
			".miyano-bot-turn{padding:6px 8px;border-radius:8px;white-space:pre-wrap;overflow-wrap:anywhere}",
			".miyano-bot-turn--user{margin-left:24px;background:#f3f4f6}",
			".miyano-bot-turn--bot{margin-right:24px;border:1px solid #e5e7eb}",
			".miyano-bot-muted{margin:0;color:#6b7280}",
			".miyano-bot-error{padding:0 12px;font-size:12px;color:#b91c1c}",
			".miyano-bot-note{padding:0 12px;font-size:12px;color:#4b5563}",
			".miyano-bot-error:empty,.miyano-bot-note:empty{display:none}",
			".miyano-bot-foot{display:flex;flex:none;flex-direction:column;gap:6px;padding:8px 12px;border-top:1px solid #e5e7eb}",
			".miyano-bot-row{display:flex;align-items:flex-end;gap:8px}",
			".miyano-bot-input{flex:1;min-width:0;padding:6px 8px;border:1px solid #d1d5db;border-radius:6px;background:#fff;font:inherit;color:inherit;resize:none;outline:none}",
			".miyano-bot-input:focus{border-color:#12b5d8}",
			".miyano-bot-input:disabled{background:#f3f4f6}",
			".miyano-bot-btn{display:inline-flex;align-items:center;justify-content:center;height:28px;padding:0 12px;border:1px solid transparent;border-radius:8px;font:inherit;font-weight:500;white-space:nowrap;cursor:pointer}",
			".miyano-bot-btn:disabled{opacity:.5;cursor:not-allowed}",
			".miyano-bot-btn--solid{background:#171717;color:#fff}",
			".miyano-bot-btn--subtle{background:#f3f4f6;color:#374151}",
			".miyano-bot-btn--ghost{background:transparent;color:#4b5563}",
			".miyano-bot-badge{position:absolute;top:-4px;right:-4px;display:flex;align-items:center;justify-content:center;min-width:20px;height:20px;padding:0 4px;border-radius:999px;background:#171717;color:#fff;font-size:12px;font-weight:500;pointer-events:none}",
			".miyano-bot-badge[hidden]{display:none}",
			".miyano-bot-notices{flex:none;padding:8px 12px;border-bottom:1px solid #e5e7eb}",
			".miyano-bot-notices-head{display:flex;align-items:center;gap:8px}",
			".miyano-bot-notices-toggle{display:flex;flex:1;align-items:center;gap:8px;padding:0;border:0;background:none;font:inherit;font-weight:500;color:#111827;text-align:left;cursor:pointer}",
			".miyano-bot-notices-toggle-label{margin-left:auto;font-weight:400;color:#6b7280}",
			".miyano-bot-notices-readall{flex:none;padding:0;border:0;background:none;font:inherit;font-size:12px;color:#2563eb;cursor:pointer}",
			".miyano-bot-notice-list{margin-top:4px}",
			".miyano-bot-notice-list{display:flex;flex-direction:column;max-height:128px;overflow-y:auto}",
			".miyano-bot-notice{display:flex;align-items:flex-start;gap:8px;width:100%;padding:6px 8px;border:0;border-radius:6px;background:none;font:inherit;text-align:left;cursor:pointer}",
			".miyano-bot-notice:hover{background:#f3f4f6}",
			".miyano-bot-notice-main{flex:1;min-width:0}",
			".miyano-bot-notice-title{display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-weight:500;color:#111827}",
			".miyano-bot-notice-sub{display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:12px;color:#6b7280}",
			".miyano-bot-notice-count{flex:none;padding:0 6px;border-radius:999px;background:#e5e7eb;font-size:12px;font-weight:500}",
			".miyano-bot-link{display:block;max-width:100%;padding:0;border:0;background:none;font:inherit;font-size:12px;text-align:left;text-decoration:underline;color:#4b5563;cursor:pointer;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}",
		].join("\n");
		const INDICATOR_FLOATING_STYLE = {
			position: "fixed",
			left: "",
			top: "",
			right: "24px",
			bottom: "88px",
			transform: "",
			zIndex: "40",
		};
		const INDICATOR_DOCKED_STYLE = {
			position: "static",
			left: "",
			top: "",
			right: "",
			bottom: "",
			transform: "",
			zIndex: "",
		};
		// The Miyano bot of this script (state.bot.host) replaces the header action: the chat mounts in its card,
		// the status line sits beside the bot. On a narrow screen it is not built and the header action stays.
		const HOST_TOGGLE_EVENT = "miyano-bot:toggle";
		const HOST_MOVE_EVENT = "miyano-bot:move";
		const HOST_GAP_PX = 12;
		const HOST_PANEL_STYLE = {
			position: "static",
			top: "",
			right: "",
			width: "auto",
			maxHeight: "",
			overflowY: "visible",
			padding: "8px 0 0",
			border: "none",
			borderTop: "1px solid #e5e7eb",
			borderRadius: "0",
			boxShadow: "none",
		};
		const host = () => state.bot?.host || null;
		// The panel's look, one style element inside the panel; every rule under `.erp-ai-panel`, so nothing of
		// Helpdesk's page changes. Button colours: blue starts work, green confirms a result, red outline refuses.
		const PANEL_CSS = [
			".erp-ai-panel{position:fixed;right:24px;top:72px;width:420px;max-height:calc(100vh - 96px);z-index:40;overflow-y:auto;padding:0 16px;background:#fff;border:1px solid #e5e7eb;border-radius:12px;box-shadow:0 12px 32px rgba(15,23,42,.14),0 2px 6px rgba(15,23,42,.06);font-size:13px;line-height:1.5;color:#1f2937}",
			".erp-ai-panel[hidden]{display:none}",
			".erp-ai-panel,.erp-ai-panel *{box-sizing:border-box}",
			// Header and send box stick to the panel's edges while the rest scrolls.
			".erp-ai-panel .erp-ai-head{position:sticky;top:0;z-index:1;display:flex;align-items:center;justify-content:space-between;gap:8px;margin:0 -16px;padding:10px 12px 10px 16px;border-bottom:1px solid #f0f0f0;background:#fff}",
			".erp-ai-panel .erp-ai-head-title{font-size:14px;color:#111827}",
			".erp-ai-panel .erp-ai-section{display:block;margin:14px 0 6px;font-size:11px;letter-spacing:.05em;text-transform:uppercase;color:#6b7280}",
			".erp-ai-panel .erp-ai-fields{padding:2px 10px 8px;border:1px solid #f0f0f0;border-radius:8px;background:#f9fafb}",
			".erp-ai-panel .erp-ai-field{margin-top:6px}",
			".erp-ai-panel .erp-ai-field-label{display:block;font-size:12px;color:#4b5563}",
			".erp-ai-panel .erp-ai-pre{white-space:pre-wrap;overflow-wrap:anywhere}",
			".erp-ai-panel .erp-ai-status{display:flex;align-items:center;gap:8px;flex-wrap:wrap;font-weight:bold}",
			".erp-ai-panel .erp-ai-hint{margin-top:6px;padding:8px 10px;border-left:3px solid #cbd5e1;border-radius:6px;background:#f8fafc;font-size:12px;color:#64748b}",
			".erp-ai-panel .erp-ai-thread{display:flex;flex-direction:column}",
			".erp-ai-panel .erp-ai-msg{max-width:92%;margin-top:10px;padding:8px 10px;border-radius:10px}",
			".erp-ai-panel .erp-ai-msg--bot{align-self:flex-start;background:#eef2ff;border:1px solid #e0e7ff;border-top-left-radius:4px}",
			".erp-ai-panel .erp-ai-msg--user{align-self:flex-end;background:#f3f4f6;border:1px solid #e5e7eb;border-top-right-radius:4px}",
			".erp-ai-panel .erp-ai-msg-head{display:flex;align-items:baseline;flex-wrap:wrap;gap:6px;margin-bottom:2px;font-size:12px;color:#374151}",
			".erp-ai-panel .erp-ai-msg-time{font-size:11px;color:#9ca3af}",
			".erp-ai-panel .erp-ai-actions{display:flex;flex-wrap:wrap;align-items:center;gap:6px;margin-top:8px}",
			".erp-ai-panel .erp-ai-links{margin-top:8px;padding:6px 8px;border-radius:8px;background:rgba(255,255,255,.75)}",
			".erp-ai-panel .erp-ai-links-title{font-size:12px;color:#4b5563}",
			".erp-ai-panel .erp-ai-sys{align-self:center;margin-top:10px;text-align:center;font-size:11.5px;color:#6b7280}",
			".erp-ai-panel .erp-ai-sys--failed{color:#b91c1c}",
			".erp-ai-panel .erp-ai-card{margin-top:10px;padding:8px 10px;border:1px solid #e5e7eb;border-radius:10px;background:#fff;box-shadow:0 1px 2px rgba(0,0,0,.04)}",
			".erp-ai-panel .erp-ai-card-head{display:block;margin-bottom:2px;color:#111827}",
			".erp-ai-panel .erp-ai-card pre{margin:4px 0 0;padding:6px 8px;border:1px solid #f0f0f0;border-radius:6px;background:#f9fafb;font-size:12px}",
			".erp-ai-panel .erp-ai-note{color:#6b7280}",
			".erp-ai-panel .erp-ai-error{font-size:12px;color:#b91c1c}",
			".erp-ai-panel .erp-ai-error:not(:empty){margin-top:8px}",
			".erp-ai-panel .erp-ai-empty{margin-top:12px;text-align:center;color:#9ca3af}",
			".erp-ai-panel .erp-ai-form{position:sticky;bottom:0;z-index:1;display:flex;align-items:flex-end;gap:8px;margin:12px -16px 0;padding:10px 12px;border-top:1px solid #f0f0f0;background:#fafafa}",
			".erp-ai-panel .erp-ai-input{flex:1;min-height:40px;max-height:160px;padding:8px 10px;border:1px solid #d1d5db;border-radius:8px;background:#fff;font:inherit;line-height:1.4;color:inherit;resize:vertical;outline:none;transition:border-color .15s,box-shadow .15s}",
			".erp-ai-panel .erp-ai-input:focus{border-color:#3b82f6;box-shadow:0 0 0 3px rgba(59,130,246,.18)}",
			".erp-ai-panel .erp-ai-input:disabled{background:#f3f4f6;color:#9ca3af}",
			".erp-ai-panel .erp-ai-btn{display:inline-flex;align-items:center;justify-content:center;height:28px;padding:0 12px;border:1px solid transparent;border-radius:8px;font:inherit;font-size:13px;font-weight:500;line-height:1;white-space:nowrap;cursor:pointer;transition:background-color .15s,border-color .15s,box-shadow .15s}",
			".erp-ai-panel .erp-ai-btn:focus-visible{outline:none;box-shadow:0 0 0 3px rgba(59,130,246,.35)}",
			".erp-ai-panel .erp-ai-btn:disabled{opacity:.5;cursor:not-allowed}",
			".erp-ai-panel .erp-ai-btn--dark{background:#171717;color:#fff}",
			".erp-ai-panel .erp-ai-btn--dark:hover:not(:disabled){background:#383838}",
			".erp-ai-panel .erp-ai-btn--blue{background:#2563eb;color:#fff}",
			".erp-ai-panel .erp-ai-btn--blue:hover:not(:disabled){background:#1d4ed8}",
			".erp-ai-panel .erp-ai-btn--green{background:#16a34a;color:#fff}",
			".erp-ai-panel .erp-ai-btn--green:hover:not(:disabled){background:#15803d}",
			".erp-ai-panel .erp-ai-btn--danger{background:#fff;border-color:#fecaca;color:#dc2626}",
			".erp-ai-panel .erp-ai-btn--danger:hover:not(:disabled){background:#fef2f2;border-color:#fca5a5}",
			".erp-ai-panel .erp-ai-btn--subtle{background:#f3f4f6;color:#374151}",
			".erp-ai-panel .erp-ai-btn--subtle:hover:not(:disabled){background:#e5e7eb}",
			".erp-ai-panel .erp-ai-btn--ghost{background:transparent;color:#4b5563}",
			".erp-ai-panel .erp-ai-btn--ghost:hover:not(:disabled){background:#f3f4f6}",
			".erp-ai-panel .erp-ai-form .erp-ai-btn{height:40px;padding:0 16px}",
			".erp-ai-panel .erp-ai-link{display:block;padding:2px 0;border:0;background:none;font:inherit;text-align:left;color:#2563eb;cursor:pointer}",
			".erp-ai-panel .erp-ai-link:hover{text-decoration:underline}",
		].join("\n");
		const BUTTON_CLASS = "erp-ai-btn erp-ai-btn--";
		const newPanelState = () => ({
			el: null,
			open: false,
			slotEl: null,
			statusTextEl: null,
			botStatus: null,
			statusExpired: false,
			expiryTimer: null,
			aiListEl: null,
			threadEl: null,
			proposalErrorEl: null,
			deciding: false,
			decisionButtons: [],
			errorEl: null,
			inputEl: null,
			sendEl: null,
			seq: 0,
			sending: false,
			loadingEl: null,
			stickToBottom: false,
			closedByPressAt: 0,
		});
		const newBotState = () => ({
			host: null,
			launcher: null,
			card: null,
			ticketWrap: null,
			chatEl: null,
			threadEl: null,
			inputEl: null,
			sendEl: null,
			restartEl: null,
			newTicketEl: null,
			errorEl: null,
			noteEl: null,
			noticesEl: null,
			noticeListEl: null,
			noticesToggleEl: null,
			noticesCountEl: null,
			noticesLabelEl: null,
			noticesReadAllEl: null,
			noticesOpen: false,
			badgeEl: null,
			soundEl: null,
			notices: { unread: null, tickets: [] },
			soundOn: true,
			audio: null,
			open: false,
			asking: false,
			turns: [],
			saved: null,
			pos: { left: 0, top: 0 },
			drag: null,
			resizeBound: false,
		});
		const socket =
			document.querySelector("#app")?.__vue_app__?.config?.globalProperties?.$socket;
		// Without a ticket (doc is null) the page loader (ADR-052) starts only the bot, on whatever page is open.
		const ticketName = doc?.name ? String(doc.name) : null;
		if (!socket || typeof socket.on !== "function") {
			return { actions: [] };
		}

		const state = (window.__erpAiAgentStatus = window.__erpAiAgentStatus || {
			ticket: null,
			runs: new Map(),
			finished: new Set(),
			el: null,
			nameEl: null,
			textEl: null,
			socket: null,
			call: null,
			panel: newPanelState(),
			resizeBound: false,
			outsideBound: false,
		});
		state.call = call;
		// A state object left by an older script version has no panel part.
		state.panel = state.panel || newPanelState();
		state.router = router;
		state.bot = state.bot || newBotState();

		// Storage may be blocked (private window): every read falls back, every write is allowed to fail.
		const loadPosition = () => {
			try {
				const saved = JSON.parse(localStorage.getItem(BOT_POSITION_KEY));
				return Number.isFinite(saved?.left) && Number.isFinite(saved?.top) ? saved : null;
			} catch (e) {
				return null;
			}
		};

		const savePosition = (position) => {
			try {
				localStorage.setItem(BOT_POSITION_KEY, JSON.stringify(position));
			} catch (e) {
				// The position then lasts until the page reloads.
			}
		};

		const loadSound = () => {
			try {
				return localStorage.getItem(BOT_SOUND_KEY) !== "false";
			} catch (e) {
				return true;
			}
		};

		const saveSound = (on) => {
			try {
				localStorage.setItem(BOT_SOUND_KEY, String(on));
			} catch (e) {
				// The choice then lasts until the page reloads.
			}
		};

		const loadTurns = () => {
			try {
				const saved = JSON.parse(sessionStorage.getItem(BOT_CHAT_KEY));
				return (Array.isArray(saved) ? saved : [])
					.filter(
						(turn) =>
							(turn?.role === "user" || turn?.role === "assistant") &&
							typeof turn?.content === "string"
					)
					.map((turn) => ({
						role: turn.role,
						content: turn.content,
						articles: readArticles(turn.articles),
					}));
			} catch (e) {
				return [];
			}
		};

		const saveTurns = () => {
			try {
				sessionStorage.setItem(BOT_CHAT_KEY, JSON.stringify(state.bot.turns));
			} catch (e) {
				// The chat then lasts until the page reloads.
			}
		};

		// Browsers keep audio suspended until the page has had a click or key press, so the audio context is made
		// and resumed on the first press (unlockAudio); a chime asked for before that stays silent.
		const unlockAudio = () => {
			try {
				const bot = state.bot;
				bot.audio = bot.audio || new AudioContext();
				if (bot.audio.state === "suspended") {
					bot.audio.resume();
				}
			} catch (e) {
				// No audio then.
			}
		};

		const playChime = () => {
			try {
				const bot = state.bot;
				if (!bot.soundOn || !bot.audio || bot.audio.state !== "running") {
					return;
				}
				const audio = bot.audio;
				const start = audio.currentTime;
				CHIME_NOTES_HZ.forEach((hz, i) => {
					const at = start + i * CHIME_GAP_S;
					const osc = audio.createOscillator();
					const gain = audio.createGain();
					osc.type = "sine";
					osc.frequency.value = hz;
					gain.gain.setValueAtTime(0, at);
					gain.gain.linearRampToValueAtTime(CHIME_VOLUME, at + 0.01);
					gain.gain.exponentialRampToValueAtTime(0.0001, at + CHIME_LENGTH_S);
					osc.connect(gain).connect(audio.destination);
					osc.start(at);
					osc.stop(at + CHIME_LENGTH_S + 0.05);
				});
			} catch (e) {
				// A sound must never break the page (ADR-051 decision 4).
			}
		};

		const renderSound = () => {
			const bot = state.bot;
			const label = bot.soundOn ? TEXT_BOT_MUTE : TEXT_BOT_UNMUTE;
			bot.soundEl.textContent = bot.soundOn ? "🔊" : "🔇";
			bot.soundEl.title = label;
			bot.soundEl.setAttribute("aria-label", label);
			bot.soundEl.setAttribute("aria-pressed", String(!bot.soundOn));
		};

		const botButton = (variant, text, onClick) => {
			const button = document.createElement("button");
			button.type = "button";
			button.className = "miyano-bot-btn miyano-bot-btn--" + variant;
			button.textContent = text;
			button.addEventListener("click", () => {
				try {
					onClick();
				} catch (e) {
					// A widget handler must never break the page (ADR-051 decision 4).
				}
			});
			return button;
		};

		const svgPart = (name, attributes) => {
			const part = document.createElementNS(SVG_NS, name);
			for (const [key, value] of Object.entries(attributes)) {
				part.setAttribute(key, value);
			}
			return part;
		};

		const makeMascot = (className) => {
			const svg = document.createElementNS(SVG_NS, "svg");
			svg.setAttribute("viewBox", "0 0 100 80");
			svg.setAttribute("aria-hidden", "true");
			svg.setAttribute("class", className);
			const arms = svgPart("g", {
				fill: "none",
				stroke: MASCOT_COLOR,
				"stroke-width": "5",
				"stroke-linecap": "round",
			});
			arms.append(
				svgPart("path", { d: "M28 50 L14 40" }),
				svgPart("path", { d: "M72 50 L86 40" })
			);
			const body = svgPart("g", { fill: MASCOT_COLOR });
			body.append(
				svgPart("circle", { cx: "11", cy: "37", r: "8" }),
				svgPart("circle", { cx: "89", cy: "37", r: "8" }),
				svgPart("path", {
					d: "M28 8 L50 30 L72 8 L72 74 L28 74 Z",
					stroke: MASCOT_COLOR,
					"stroke-width": "6",
					"stroke-linejoin": "round",
				})
			);
			svg.append(
				arms,
				body,
				svgPart("ellipse", { cx: "43", cy: "45", rx: "3.2", ry: "4.2", fill: "#fff" }),
				svgPart("ellipse", { cx: "57", cy: "45", rx: "3.2", ry: "4.2", fill: "#fff" }),
				svgPart("path", {
					d: "M37 53 Q50 66 63 53",
					fill: "none",
					stroke: "#fff",
					"stroke-width": "4",
					"stroke-linecap": "round",
				})
			);
			return svg;
		};

		const clampBot = (value, min, max) => Math.min(Math.max(value, min), Math.max(min, max));

		// A fixed box that scrolls inside: above the bot in the lower half of the window, below it otherwise.
		const placeBotCard = () => {
			const bot = state.bot;
			const w = window.innerWidth;
			const h = window.innerHeight;
			const width = Math.min(BOT_CARD_WIDTH_PX, w - 2 * BOT_EDGE_PX);
			const style = {
				width: width + "px",
				left:
					clampBot(
						bot.pos.left + BOT_WIDTH_PX - width,
						BOT_EDGE_PX,
						w - width - BOT_EDGE_PX
					) + "px",
				top: "",
				bottom: "",
			};
			if (bot.pos.top + BOT_HEIGHT_PX / 2 > h / 2) {
				style.bottom = h - bot.pos.top + BOT_CARD_GAP_PX + "px";
				style.height =
					Math.min(BOT_CARD_HEIGHT_PX, bot.pos.top - BOT_CARD_GAP_PX - BOT_EDGE_PX) +
					"px";
			} else {
				const below = bot.pos.top + BOT_HEIGHT_PX;
				style.top = below + BOT_CARD_GAP_PX + "px";
				style.height =
					Math.min(BOT_CARD_HEIGHT_PX, h - below - BOT_CARD_GAP_PX - BOT_EDGE_PX) + "px";
			}
			Object.assign(bot.card.style, style);
		};

		// Kept in memory only: a reload puts the bot back in the corner (no storage, ADR-051 decision 3).
		const placeBot = (wanted) => {
			const bot = state.bot;
			const w = window.innerWidth;
			const h = window.innerHeight;
			bot.pos = {
				left: clampBot(
					wanted?.left ?? w - BOT_WIDTH_PX - BOT_OFFSET_PX,
					BOT_EDGE_PX,
					w - BOT_WIDTH_PX - BOT_EDGE_PX
				),
				top: clampBot(
					wanted?.top ?? h - BOT_HEIGHT_PX - BOT_OFFSET_PX,
					BOT_EDGE_PX,
					h - BOT_HEIGHT_PX - BOT_EDGE_PX
				),
			};
			bot.launcher.style.left = bot.pos.left + "px";
			bot.launcher.style.top = bot.pos.top + "px";
			placeBotCard();
			window.dispatchEvent(new CustomEvent(HOST_MOVE_EVENT));
		};

		const renderBotChat = () => {
			const bot = state.bot;
			const nodes = [];
			if (bot.turns.length === 0) {
				const hello = document.createElement("p");
				hello.className = "miyano-bot-muted";
				hello.textContent = TEXT_BOT_HELLO;
				nodes.push(hello);
			}
			for (const turn of bot.turns) {
				const row = document.createElement("div");
				row.className =
					turn.role === "user"
						? "miyano-bot-turn miyano-bot-turn--user"
						: "miyano-bot-turn miyano-bot-turn--bot";
				row.textContent = turn.content;
				for (const article of turn.articles || []) {
					const link = document.createElement("button");
					link.type = "button";
					link.className = "miyano-bot-link";
					link.textContent = article.title;
					link.addEventListener("click", () => {
						try {
							state.router?.push({
								name: "Article",
								params: { articleId: article.name },
							});
						} catch (e) {
							// A widget handler must never break the page (ADR-051 decision 4).
						}
					});
					row.append(link);
				}
				nodes.push(row);
			}
			if (bot.asking) {
				const thinking = document.createElement("p");
				thinking.className = "miyano-bot-muted";
				thinking.textContent = TEXT_BOT_THINKING;
				nodes.push(thinking);
			}
			bot.threadEl.replaceChildren(...nodes);
			bot.threadEl.scrollTop = bot.threadEl.scrollHeight;
			bot.restartEl.hidden = bot.turns.length === 0;
			bot.restartEl.disabled = bot.asking;
			bot.newTicketEl.hidden = bot.turns.length === 0;
			bot.inputEl.disabled = bot.asking;
			bot.sendEl.disabled = bot.asking;
		};

		const readArticles = (articles) =>
			(Array.isArray(articles) ? articles : [])
				.filter((a) => typeof a?.name === "string" && typeof a?.title === "string")
				.map((a) => ({ name: a.name, title: a.title }));

		const askBot = () => {
			const bot = state.bot;
			const question = bot.inputEl.value.trim();
			if (!question || bot.asking || !state.call) {
				return;
			}
			const history = bot.turns.map(({ role, content }) => ({ role, content }));
			bot.errorEl.textContent = "";
			bot.noteEl.textContent = "";
			bot.turns.push({ role: "user", content: question });
			saveTurns();
			bot.inputEl.value = "";
			bot.asking = true;
			renderBotChat();
			// The question stays in the box so it can be sent again.
			const onFailed = () => {
				try {
					bot.asking = false;
					bot.turns.pop();
					saveTurns();
					bot.inputEl.value = question;
					bot.errorEl.textContent = TEXT_BOT_FAILED;
					renderBotChat();
				} catch (e) {
					// A widget handler must never break the page (ADR-051 decision 4).
				}
			};
			const onAnswered = (reply) => {
				try {
					if (typeof reply?.answer !== "string") {
						onFailed();
						return;
					}
					bot.asking = false;
					bot.turns.push({
						role: "assistant",
						content: reply.answer,
						articles: readArticles(reply.articles),
					});
					saveTurns();
					renderBotChat();
				} catch (e) {
					onFailed();
				}
			};
			try {
				state
					.call("erp_ai.support_chat.ask", { question, history })
					.then(onAnswered, onFailed);
			} catch (e) {
				onFailed();
			}
		};

		// The first question is the subject (the new-ticket page reads ?subject=); the chat goes to the clipboard.
		const createTicketFromChat = () => {
			const bot = state.bot;
			const first = bot.turns.find((turn) => turn.role === "user")?.content ?? "";
			const transcript = bot.turns
				.map(
					(turn) =>
						(turn.role === "user" ? TEXT_BOT_QUESTION : TEXT_BOT_TITLE) +
						": " +
						turn.content
				)
				.join("\n\n");
			navigator.clipboard?.writeText(transcript).then(
				() => {
					bot.noteEl.textContent = TEXT_BOT_COPIED;
				},
				() => {}
			);
			state.router?.push({
				name: "TicketAgentNew",
				query: { subject: first.replace(/\s+/g, " ").slice(0, SUBJECT_CHARS) },
			});
		};

		const renderNotices = () => {
			const bot = state.bot;
			const { tickets } = bot.notices;
			// The badge never counts what the list does not show, so the two cannot disagree.
			const unread = tickets.length === 0 ? 0 : bot.notices.unread;
			bot.badgeEl.hidden = !(unread > 0);
			bot.badgeEl.textContent = unread > MAX_BADGE ? MAX_BADGE + "+" : String(unread);
			bot.launcher.setAttribute(
				"aria-label",
				unread > 0
					? TEXT_BOT_LAUNCHER + ", " + unread + " " + TEXT_BOT_NEW
					: TEXT_BOT_LAUNCHER
			);
			bot.noticesEl.hidden = tickets.length === 0;
			// Folded by default: the chat keeps the card; the list opens on a press.
			bot.noticesCountEl.textContent = unread + " " + TEXT_BOT_NEW;
			bot.noticesLabelEl.textContent = bot.noticesOpen ? TEXT_BOT_HIDE : TEXT_BOT_SHOW;
			bot.noticesToggleEl.setAttribute("aria-expanded", String(bot.noticesOpen));
			bot.noticeListEl.hidden = !bot.noticesOpen;
			bot.noticesReadAllEl.hidden = !bot.noticesOpen;
			const rows = tickets.map((notice) => {
				const row = document.createElement("button");
				row.type = "button";
				row.className = "miyano-bot-notice";
				const main = document.createElement("span");
				main.className = "miyano-bot-notice-main";
				const title = document.createElement("span");
				title.className = "miyano-bot-notice-title";
				title.textContent =
					"#" +
					notice.ticket +
					" · " +
					(notice.type === BOT_REPLY_TYPE ? TEXT_BOT_REPLIED : TEXT_BOT_ASSIGNED);
				const sub = document.createElement("span");
				sub.className = "miyano-bot-notice-sub";
				sub.textContent = notice.creation.slice(0, 16) + " · " + notice.subject;
				main.append(title, sub);
				const count = document.createElement("span");
				count.className = "miyano-bot-notice-count";
				count.textContent = notice.unread + " " + TEXT_BOT_NEW;
				row.append(main, count);
				row.addEventListener("click", () => {
					try {
						// Hide the row and drop the count at once; the server's answer then replaces both.
						bot.notices = {
							unread: Math.max(0, bot.notices.unread - notice.unread),
							tickets: bot.notices.tickets.filter(
								(item) => item.ticket !== notice.ticket
							),
						};
						renderNotices();
						state.router?.push({
							name: "TicketAgent",
							params: { ticketId: notice.ticket },
						});
						markNoticesRead(notice.ticket, true);
					} catch (e) {
						// A widget handler must never break the page (ADR-051 decision 4).
					}
				});
				return row;
			});
			bot.noticeListEl.replaceChildren(...rows);
		};

		// The unread count after the first load only ever goes up with a new notice: that is when the chime plays.
		const refreshNotices = () => {
			const bot = state.bot;
			// Only the newest request counts: an older answer still on its way must not put a stale count back.
			bot.refreshSeq = (bot.refreshSeq || 0) + 1;
			const seq = bot.refreshSeq;
			const onNotices = (data) => {
				try {
					if (seq !== bot.refreshSeq) {
						return;
					}
					const tickets = (Array.isArray(data?.tickets) ? data.tickets : [])
						.filter((notice) => typeof notice?.ticket === "string")
						.map((notice) => ({
							ticket: notice.ticket,
							unread: Number(notice.unread) || 0,
							type: String(notice.type ?? ""),
							subject: String(notice.subject ?? ""),
							creation: String(notice.creation ?? ""),
						}));
					const unread = Number(data?.unread) || 0;
					const before = bot.notices.unread;
					bot.notices = { unread, tickets };
					renderNotices();
					if (before !== null && unread > before) {
						playChime();
					}
				} catch (e) {
					// A widget handler must never break the page (ADR-051 decision 4).
				}
			};
			try {
				state.call("erp_ai.support_chat.get_notices", {}).then(onNotices, () => {});
			} catch (e) {
				// A widget handler must never break the page (ADR-051 decision 4).
			}
		};

		// The Helpdesk bell reloads on the socket's `notification` event, which the server sends only for a new
		// notice. After notices are marked read here, run its listeners (not ours) so the bell drops them at once.
		const refreshHelpdeskBell = () => {
			try {
				for (const listener of state.socket?.listeners?.("notification") || []) {
					if (listener !== onNotification) {
						listener();
					}
				}
			} catch (e) {
				// A widget handler must never break the page (ADR-051 decision 4).
			}
		};

		const markNoticesRead = (ticket, withBotReplies, onlyBotReplies = false) => {
			try {
				state
					.call("erp_ai.support_chat.mark_notices_read", {
						ticket,
						with_bot_replies: withBotReplies,
						only_bot_replies: onlyBotReplies,
					})
					.then(() => {
						refreshNotices();
						refreshHelpdeskBell();
					}, refreshNotices);
			} catch (e) {
				// A widget handler must never break the page (ADR-051 decision 4).
			}
		};

		// Opening a ticket counts its assignment as seen; its bot replies count once the card shows its chat.
		const readSeenNotices = () => {
			if (state.ticket && state.bot.card) {
				markNoticesRead(state.ticket, state.bot.open);
			}
		};

		const setBotOpen = (value) => {
			const bot = state.bot;
			bot.open = value;
			bot.card.hidden = !value;
			bot.launcher.setAttribute("aria-expanded", String(value));
			window.dispatchEvent(new CustomEvent(HOST_TOGGLE_EVENT, { detail: { open: value } }));
			if (value) {
				// Notices read on another tab or device show up the moment the card opens.
				refreshNotices();
			}
			if (value && !state.ticket) {
				bot.threadEl.scrollTop = bot.threadEl.scrollHeight;
				bot.inputEl.focus({ preventScroll: true });
			}
			if (value && !state.ticket) {
				// Opening the bot away from a ticket counts the bot's replies as seen; assignments stay listed.
				markNoticesRead(null, false, true);
			}
			readSeenNotices();
		};

		// On a ticket page the card holds that ticket's chat (the panel); elsewhere it holds the support chat.
		const syncBotView = () => {
			const bot = state.bot;
			if (!bot.card) {
				return;
			}
			bot.ticketWrap.hidden = !state.ticket;
			bot.chatEl.hidden = Boolean(state.ticket);
			readSeenNotices();
		};

		const onBotPointerDown = (event) => {
			try {
				const bot = state.bot;
				if (event.button !== 0) {
					return;
				}
				bot.drag = {
					id: event.pointerId,
					startX: event.clientX,
					startY: event.clientY,
					dx: event.clientX - bot.pos.left,
					dy: event.clientY - bot.pos.top,
					moved: false,
				};
				bot.launcher.setPointerCapture(event.pointerId);
			} catch (e) {
				// A widget handler must never break the page (ADR-051 decision 4).
			}
		};

		const onBotPointerMove = (event) => {
			try {
				const bot = state.bot;
				const drag = bot.drag;
				if (!drag || event.pointerId !== drag.id) {
					return;
				}
				const far =
					Math.abs(event.clientX - drag.startX) > BOT_DRAG_PX ||
					Math.abs(event.clientY - drag.startY) > BOT_DRAG_PX;
				if (!drag.moved && !far) {
					return;
				}
				drag.moved = true;
				bot.launcher.style.cursor = "grabbing";
				placeBot({ left: event.clientX - drag.dx, top: event.clientY - drag.dy });
			} catch (e) {
				// A widget handler must never break the page (ADR-051 decision 4).
			}
		};

		// A press that moved past the threshold was a drag and is remembered; one that did not opens the card.
		const onBotPointerUp = (event) => {
			try {
				const bot = state.bot;
				const drag = bot.drag;
				if (!drag || event.pointerId !== drag.id) {
					return;
				}
				bot.drag = null;
				bot.launcher.style.cursor = "";
				if (drag.moved) {
					bot.saved = { ...bot.pos };
					savePosition(bot.saved);
				} else {
					setBotOpen(!bot.open);
				}
			} catch (e) {
				// A widget handler must never break the page (ADR-051 decision 4).
			}
		};

		const onBotKeyDown = (event) => {
			try {
				if (event.key === "Enter" || event.key === " ") {
					event.preventDefault();
					setBotOpen(!state.bot.open);
				}
			} catch (e) {
				// A widget handler must never break the page (ADR-051 decision 4).
			}
		};

		const onBotResize = () => {
			try {
				const bot = state.bot;
				const narrow = window.innerWidth < NARROW_SCREEN_PX;
				bot.launcher.hidden = narrow;
				if (narrow && bot.open) {
					setBotOpen(false);
				}
				placeBot(bot.saved);
			} catch (e) {
				// A resize callback must never throw to the console (AC-10 g).
			}
		};

		const buildBot = () => {
			const bot = state.bot;
			if (bot.card) {
				return;
			}
			const root = document.createElement("div");
			const styleEl = document.createElement("style");
			styleEl.textContent = BOT_CSS;
			const launcher = document.createElement("button");
			launcher.type = "button";
			launcher.className = "miyano-bot-launcher";
			launcher.title = TEXT_BOT_DRAG_HINT;
			launcher.setAttribute("aria-label", TEXT_BOT_LAUNCHER);
			launcher.setAttribute("aria-expanded", "false");
			Object.assign(launcher.style, {
				width: BOT_WIDTH_PX + "px",
				height: BOT_HEIGHT_PX + "px",
			});
			const badgeEl = document.createElement("span");
			badgeEl.className = "miyano-bot-badge";
			badgeEl.hidden = true;
			launcher.append(makeMascot("miyano-bot-mascot"), badgeEl);
			launcher.addEventListener("pointerdown", onBotPointerDown);
			launcher.addEventListener("pointermove", onBotPointerMove);
			launcher.addEventListener("pointerup", onBotPointerUp);
			launcher.addEventListener("pointercancel", () => {
				bot.drag = null;
			});
			launcher.addEventListener("keydown", onBotKeyDown);

			const card = document.createElement("div");
			card.className = "miyano-bot-card";
			card.setAttribute("role", "dialog");
			card.setAttribute("aria-label", TEXT_BOT_TITLE);
			card.hidden = true;
			const head = document.createElement("div");
			head.className = "miyano-bot-head";
			const title = document.createElement("strong");
			title.className = "miyano-bot-head-title";
			title.textContent = TEXT_BOT_TITLE;
			const soundEl = botButton("ghost", "", () => {
				bot.soundOn = !bot.soundOn;
				saveSound(bot.soundOn);
				renderSound();
				unlockAudio();
				if (bot.soundOn && bot.audio) {
					// Switching the sound on plays the chime once, so the person hears what they turned on.
					bot.audio.resume().then(playChime, () => {});
				}
			});
			head.append(
				makeMascot("miyano-bot-head-mascot"),
				title,
				soundEl,
				botButton("ghost", TEXT_CLOSE, () => setBotOpen(false))
			);

			// Only unread notices are listed: a seen ticket drops out, and with none left the section hides.
			const noticesEl = document.createElement("div");
			noticesEl.className = "miyano-bot-notices";
			noticesEl.hidden = true;
			const noticesHead = document.createElement("div");
			noticesHead.className = "miyano-bot-notices-head";
			const noticesToggleEl = document.createElement("button");
			noticesToggleEl.type = "button";
			noticesToggleEl.className = "miyano-bot-notices-toggle";
			const noticesTitle = document.createElement("span");
			noticesTitle.textContent = TEXT_BOT_FOR_YOU;
			const noticesCountEl = document.createElement("span");
			noticesCountEl.className = "miyano-bot-notice-count";
			const noticesLabelEl = document.createElement("span");
			noticesLabelEl.className = "miyano-bot-notices-toggle-label";
			noticesToggleEl.append(noticesTitle, noticesCountEl, noticesLabelEl);
			noticesToggleEl.addEventListener("click", () => {
				bot.noticesOpen = !bot.noticesOpen;
				renderNotices();
			});
			const noticesReadAllEl = document.createElement("button");
			noticesReadAllEl.type = "button";
			noticesReadAllEl.className = "miyano-bot-notices-readall";
			noticesReadAllEl.textContent = TEXT_BOT_READ_ALL;
			noticesReadAllEl.hidden = true;
			noticesReadAllEl.addEventListener("click", () => {
				bot.notices = { unread: 0, tickets: [] };
				renderNotices();
				markNoticesRead(null, true);
			});
			noticesHead.append(noticesToggleEl, noticesReadAllEl);
			const noticeListEl = document.createElement("div");
			noticeListEl.className = "miyano-bot-notice-list";
			noticeListEl.hidden = true;
			noticesEl.append(noticesHead, noticeListEl);

			// The ticket's own chat mounts in this part (host().slot).
			const ticketWrap = document.createElement("div");
			ticketWrap.className = "miyano-bot-ticket";
			const slot = document.createElement("div");
			ticketWrap.append(slot);

			const chatEl = document.createElement("div");
			chatEl.className = "miyano-bot-chat";
			const chatHead = document.createElement("div");
			chatHead.className = "miyano-bot-chat-head";
			const chatTitle = document.createElement("strong");
			chatTitle.className = "miyano-bot-head-title";
			chatTitle.textContent = TEXT_BOT_ASK_TITLE;
			const restartEl = botButton("ghost", TEXT_BOT_RESTART, () => {
				if (!bot.asking) {
					bot.turns = [];
					saveTurns();
					bot.errorEl.textContent = "";
					bot.noteEl.textContent = "";
					renderBotChat();
				}
			});
			chatHead.append(chatTitle, restartEl);
			const threadEl = document.createElement("div");
			threadEl.className = "miyano-bot-thread";
			threadEl.setAttribute("aria-live", "polite");
			const errorEl = document.createElement("div");
			errorEl.className = "miyano-bot-error";
			errorEl.setAttribute("role", "alert");
			const noteEl = document.createElement("div");
			noteEl.className = "miyano-bot-note";
			const foot = document.createElement("div");
			foot.className = "miyano-bot-foot";
			const newTicketEl = botButton("subtle", TEXT_BOT_NEW_TICKET, createTicketFromChat);
			const row = document.createElement("div");
			row.className = "miyano-bot-row";
			const inputEl = document.createElement("textarea");
			inputEl.rows = 2;
			inputEl.maxLength = MAX_QUESTION_CHARS;
			inputEl.className = "miyano-bot-input";
			inputEl.placeholder = TEXT_BOT_PLACEHOLDER;
			inputEl.setAttribute("aria-label", TEXT_BOT_PLACEHOLDER);
			inputEl.addEventListener("keydown", (event) => {
				try {
					if (event.key === "Enter" && !event.shiftKey && !event.isComposing) {
						event.preventDefault();
						askBot();
					}
				} catch (e) {
					// A widget handler must never break the page (ADR-051 decision 4).
				}
			});
			const sendEl = botButton("solid", TEXT_SEND, askBot);
			row.append(inputEl, sendEl);
			foot.append(newTicketEl, row);
			chatEl.append(chatHead, threadEl, errorEl, noteEl, foot);
			card.append(head, noticesEl, ticketWrap, chatEl);
			root.append(styleEl, launcher, card);
			document.body.appendChild(root);

			Object.assign(bot, {
				launcher,
				card,
				ticketWrap,
				chatEl,
				threadEl,
				inputEl,
				sendEl,
				restartEl,
				newTicketEl,
				errorEl,
				noteEl,
				noticesEl,
				noticeListEl,
				noticesToggleEl,
				noticesCountEl,
				noticesLabelEl,
				noticesReadAllEl,
				badgeEl,
				soundEl,
			});
			bot.host = {
				launcher,
				slot,
				isOpen: () => bot.open,
				open: () => setBotOpen(true),
				close: () => setBotOpen(false),
			};
			if (!bot.resizeBound) {
				bot.resizeBound = true;
				window.addEventListener("resize", onBotResize);
			}
			if (!bot.visibleBound) {
				bot.visibleBound = true;
				document.addEventListener("visibilitychange", () => {
					if (document.visibilityState === "visible") {
						refreshNotices();
					}
				});
			}
			if (!bot.audioBound) {
				bot.audioBound = true;
				document.addEventListener("pointerdown", unlockAudio, {
					capture: true,
					once: true,
				});
				document.addEventListener("keydown", unlockAudio, { capture: true, once: true });
			}
			bot.saved = loadPosition();
			bot.soundOn = loadSound();
			bot.turns = loadTurns();
			placeBot(bot.saved);
			renderSound();
			renderBotChat();
			refreshNotices();
			syncBotView();
		};

		// Helpdesk's `[hidden]{display:none}` loses to an inline display, so both are written together.
		const setIndicatorVisible = (el, visible) => {
			el.hidden = !visible;
			el.style.display = visible ? "flex" : "none";
		};

		const ensureElement = () => {
			if (state.el) {
				return state.el;
			}
			const el = document.createElement("div");
			el.setAttribute("role", "status");
			el.setAttribute("aria-live", "polite");
			Object.assign(el.style, INDICATOR_FLOATING_STYLE, {
				alignItems: "center",
				gap: "8px",
				padding: "8px 12px",
				background: "#ffffff",
				border: "1px solid #e5e7eb",
				borderRadius: "8px",
				boxShadow: "0 1px 4px rgba(0, 0, 0, 0.12)",
				fontSize: "13px",
			});
			setIndicatorVisible(el, false);
			const dots = document.createElement("span");
			dots.style.display = "inline-flex";
			dots.style.gap = "3px";
			for (let i = 0; i < 3; i++) {
				const dot = document.createElement("span");
				Object.assign(dot.style, {
					width: "6px",
					height: "6px",
					borderRadius: "50%",
					background: "#9ca3af",
					display: "inline-block",
				});
				if (typeof dot.animate === "function") {
					dot.animate([{ opacity: 0.25 }, { opacity: 1 }, { opacity: 0.25 }], {
						duration: 1200,
						iterations: Infinity,
						delay: i * 200,
					});
				}
				dots.appendChild(dot);
			}
			const nameEl = document.createElement("strong");
			const textEl = document.createElement("span");
			el.append(dots, nameEl, textEl);
			document.body.appendChild(el);
			state.el = el;
			state.nameEl = nameEl;
			state.textEl = textEl;
			return el;
		};

		// A live indicator wins, else the server's text; past the deadline, its failed time (A-4).
		const showBotStatus = () => {
			const panel = state.panel;
			if (!panel.statusTextEl) {
				return;
			}
			const status = panel.botStatus;
			let text = "";
			if (status) {
				const expired = panel.statusExpired && status.expired_text;
				text = expired ? status.expired_text : status.text || "";
			}
			panel.statusTextEl.textContent = state.runs.size > 0 ? TEXT_STATUS_RUNNING : text;
		};

		const render = () => {
			const el = ensureElement();
			// The status line follows the indicator, shown or hidden (design 4.1).
			showBotStatus();
			if (state.runs.size === 0) {
				setIndicatorVisible(el, false);
				return;
			}
			let latest = null;
			for (const run of state.runs.values()) {
				if (!latest || run.at >= latest.at) {
					latest = run;
				}
			}
			state.nameEl.textContent = latest.name || "";
			state.textEl.textContent = latest.text || "";
			placeIndicatorNearHost();
			setIndicatorVisible(el, true);
		};

		const finish = (runId) => {
			const run = state.runs.get(runId);
			if (run) {
				clearTimeout(run.timer);
				state.runs.delete(runId);
			}
			state.finished.add(runId);
			render();
		};

		// Beside the host bot: on its left in the right half of the window, else on its right.
		const placeIndicatorNearHost = () => {
			const bot = host()?.launcher?.getBoundingClientRect();
			if (!bot || !state.el || state.panel.open) {
				return;
			}
			const onLeft = bot.left > window.innerWidth / 2;
			Object.assign(state.el.style, {
				left: onLeft ? "" : bot.right + HOST_GAP_PX + "px",
				right: onLeft ? window.innerWidth - bot.left + HOST_GAP_PX + "px" : "",
				top: bot.top + bot.height / 2 + "px",
				bottom: "",
				transform: "translateY(-50%)",
			});
		};

		// In the host bot's card the panel is plain content; alone it is its own fixed card.
		const mountPanel = (el) => {
			const slot = host()?.slot;
			if (!slot) {
				if (el.parentElement !== document.body) {
					document.body.appendChild(el);
				}
				return;
			}
			if (el.parentElement !== slot) {
				slot.appendChild(el);
			}
			Object.assign(el.style, HOST_PANEL_STYLE);
		};

		const buildPanel = () => {
			const panel = state.panel;
			if (panel.el) {
				mountPanel(panel.el);
				return panel.el;
			}
			const el = document.createElement("div");
			el.className = "erp-ai-panel";
			el.hidden = true;
			const styleEl = document.createElement("style");
			styleEl.textContent = PANEL_CSS;
			const header = document.createElement("div");
			header.className = "erp-ai-head";
			const title = document.createElement("strong");
			title.className = "erp-ai-head-title";
			title.textContent = TEXT_PANEL_TITLE;
			const closeEl = document.createElement("button");
			closeEl.type = "button";
			closeEl.className = BUTTON_CLASS + "ghost";
			closeEl.textContent = TEXT_CLOSE;
			closeEl.addEventListener("click", () => {
				try {
					if (host()) {
						host().close();
						return;
					}
					closePanel();
				} catch (e) {
					// A panel handler must never break the ticket page (ADR-009 decision 4).
				}
			});
			header.append(title, closeEl);
			const aiTitle = document.createElement("strong");
			aiTitle.className = "erp-ai-section";
			aiTitle.textContent = TEXT_AI_SECTION;
			const aiListEl = document.createElement("div");
			aiListEl.className = "erp-ai-fields";
			const chatTitle = document.createElement("strong");
			chatTitle.className = "erp-ai-section";
			chatTitle.textContent = TEXT_CHAT_SECTION;
			// The status line, above messages and cards, holds the docked indicator (A-7).
			const statusEl = document.createElement("div");
			statusEl.className = "erp-ai-status";
			const statusTextEl = document.createElement("span");
			const slotEl = document.createElement("div");
			statusEl.append(statusTextEl, slotEl);
			const guidanceEl = document.createElement("div");
			guidanceEl.className = "erp-ai-hint";
			guidanceEl.textContent = TEXT_BOT_GUIDANCE;
			const threadEl = document.createElement("div");
			threadEl.className = "erp-ai-thread";
			const proposalErrorEl = document.createElement("div");
			proposalErrorEl.className = "erp-ai-error";
			const errorEl = document.createElement("div");
			errorEl.className = "erp-ai-error";
			const formEl = document.createElement("div");
			formEl.className = "erp-ai-form";
			const inputEl = document.createElement("textarea");
			inputEl.rows = 2;
			inputEl.className = "erp-ai-input";
			inputEl.placeholder = TEXT_INPUT_PLACEHOLDER;
			inputEl.addEventListener("keydown", (event) => {
				try {
					if (event.key === "Enter" && !event.shiftKey && !event.isComposing) {
						event.preventDefault();
						submit();
					}
				} catch (e) {
					// A panel handler must never break the ticket page (ADR-009 decision 4).
				}
			});
			const sendEl = document.createElement("button");
			sendEl.type = "button";
			sendEl.className = BUTTON_CLASS + "dark";
			sendEl.textContent = TEXT_SEND;
			sendEl.addEventListener("click", () => {
				try {
					submit();
				} catch (e) {
					// A panel handler must never break the ticket page (ADR-009 decision 4).
				}
			});
			formEl.append(inputEl, sendEl);
			el.append(
				styleEl,
				...(host() ? [] : [header]),
				aiTitle,
				aiListEl,
				chatTitle,
				statusEl,
				guidanceEl,
				threadEl,
				proposalErrorEl,
				errorEl,
				formEl
			);
			mountPanel(el);
			panel.el = el;
			panel.slotEl = slotEl;
			panel.statusTextEl = statusTextEl;
			panel.aiListEl = aiListEl;
			panel.threadEl = threadEl;
			panel.proposalErrorEl = proposalErrorEl;
			panel.errorEl = errorEl;
			panel.inputEl = inputEl;
			panel.sendEl = sendEl;
			return el;
		};

		const dockIndicator = (docked) => {
			const el = ensureElement();
			Object.assign(el.style, docked ? INDICATOR_DOCKED_STYLE : INDICATOR_FLOATING_STYLE);
			(docked ? state.panel.slotEl : document.body).appendChild(el);
			if (!docked) {
				placeIndicatorNearHost();
			}
		};

		const closePanel = () => {
			const panel = state.panel;
			panel.open = false;
			if (panel.el) {
				panel.el.hidden = true;
				dockIndicator(false);
			}
		};

		const renderAiFields = (data) => {
			const fields = data?.ai_fields;
			if (!Array.isArray(fields)) {
				throw new Error("ai_fields is not a list");
			}
			const nodes = fields.map((field) => {
				const row = document.createElement("div");
				row.className = "erp-ai-field";
				const label = document.createElement("strong");
				label.className = "erp-ai-field-label";
				label.textContent = field?.label || "";
				const body = document.createElement("div");
				body.className = "erp-ai-pre";
				body.textContent = field?.text ?? TEXT_EMPTY_FIELD;
				row.append(label, body);
				return row;
			});
			state.panel.aiListEl.replaceChildren(...nodes);
		};

		const clearExpiryTimer = () => {
			const panel = state.panel;
			clearTimeout(panel.expiryTimer);
			panel.expiryTimer = null;
		};

		// An open call's deadline only changes the text, one timer per load (design 4.1, A-4).
		const renderBotStatus = (data) => {
			const panel = state.panel;
			clearExpiryTimer();
			panel.statusExpired = false;
			const status = data?.bot_status;
			panel.botStatus = status && typeof status === "object" ? status : null;
			const ms = Number(panel.botStatus?.expires_in_s) * 1000;
			if (ms > 0) {
				panel.expiryTimer = setTimeout(() => {
					try {
						panel.statusExpired = true;
						showBotStatus();
					} catch (e) {
						// A timer callback must never throw to the console (AC-10 g).
					}
				}, ms);
			}
			showBotStatus();
		};

		// A system line: a centred note between the messages, never a message (ADR-048 QĐ 7).
		const systemLine = (line) => {
			const row = document.createElement("div");
			row.className =
				line?.kind === "failed" ? "erp-ai-sys erp-ai-sys--failed" : "erp-ai-sys";
			row.textContent = String(line?.text ?? "");
			return row;
		};

		// One message of the thread; `approve` puts the approve button under it (the newest guidance, ADR-050).
		const messageRow = (message, approve, confirm) => {
			const row = document.createElement("div");
			row.className = message?.is_bot
				? "erp-ai-msg erp-ai-msg--bot"
				: "erp-ai-msg erp-ai-msg--user";
			const head = document.createElement("div");
			head.className = "erp-ai-msg-head";
			const who = document.createElement("strong");
			who.textContent = [message?.is_bot ? TEXT_BOT_LABEL : "", message?.author]
				.filter(Boolean)
				.join(" · ");
			const when = document.createElement("span");
			when.className = "erp-ai-msg-time";
			when.textContent = message?.created_at ?? "";
			head.append(who, when);
			const body = document.createElement("div");
			body.className = "erp-ai-pre";
			body.textContent = message?.text ?? "";
			row.append(head, body);
			// The buttons under a message sit in one row (CHG-017: only one of the two kinds shows).
			const actions = document.createElement("div");
			actions.className = "erp-ai-actions";
			if (approve) {
				const approveEl = document.createElement("button");
				approveEl.type = "button";
				approveEl.className = BUTTON_CLASS + "blue";
				approveEl.textContent = TEXT_APPROVE_GUIDANCE;
				approveEl.addEventListener("click", () => {
					try {
						const panel = state.panel;
						if (panel.sending || !panel.inputEl) {
							return;
						}
						panel.inputEl.value = APPROVE_GUIDANCE_TEXT;
						submit();
					} catch (e) {
						// A panel handler must never break the ticket page (ADR-009 decision 4).
					}
				});
				actions.append(approveEl);
			}
			if (confirm) {
				// The records the bot wrote, above the buttons; the server builds each desk path (CHG-017).
				const links = (
					Array.isArray(message?.result_links) ? message.result_links : []
				).filter((link) => typeof link?.url === "string" && link.url.startsWith("/app/"));
				if (links.length > 0) {
					const box = document.createElement("div");
					box.className = "erp-ai-links";
					const title = document.createElement("div");
					title.className = "erp-ai-links-title";
					title.textContent = TEXT_RESULT_LINKS;
					box.append(title);
					for (const link of links) {
						const a = document.createElement("button");
						a.type = "button";
						a.className = "erp-ai-link";
						a.textContent = String(link.label ?? link.url);
						a.addEventListener("click", () => {
							try {
								window.open(link.url, "_blank", "noopener");
							} catch (e) {
								// A panel handler must never break the ticket page (ADR-009 decision 4).
							}
						});
						box.append(a);
					}
					row.append(box);
				}
				actions.append(
					resultButton(TEXT_RESULT_APPROVE, "approve"),
					resultButton(TEXT_RESULT_REJECT, "reject")
				);
			}
			if (actions.childElementCount > 0) {
				row.append(actions);
			}
			return row;
		};

		// The first open of a ticket has nothing to show until its data comes back.
		const loadingRow = () => {
			const row = document.createElement("div");
			row.className = "erp-ai-empty";
			row.textContent = TEXT_LOADING;
			state.panel.loadingEl = row;
			return row;
		};

		// The panel scrolls as a whole; its bottom holds the newest message, right above the send box.
		const isAtBottom = () => {
			const el = state.panel.el;
			return !!el && el.scrollHeight - el.scrollTop - el.clientHeight <= BOTTOM_SLACK_PX;
		};

		const scrollToBottom = () => {
			const el = state.panel.el;
			if (el) {
				el.scrollTop = el.scrollHeight;
			}
		};

		const clearProposals = () => {
			const panel = state.panel;
			panel.decisionButtons = [];
			panel.proposalErrorEl?.replaceChildren();
		};

		// Opens the proposal's own form in a new tab; the form checks the reader again (design D-4).
		const openProposal = (name) => {
			try {
				window.open(PROPOSAL_FORM_PREFIX + encodeURIComponent(name), "_blank", "noopener");
			} catch (e) {
				// A panel handler must never break the ticket page (ADR-009 decision 4).
			}
		};

		const proposalButton = (label, name) => {
			const button = document.createElement("button");
			button.type = "button";
			button.className = BUTTON_CLASS + "subtle";
			button.textContent = label;
			button.addEventListener("click", () => {
				try {
					openProposal(name);
				} catch (e) {
					// A panel handler must never break the ticket page (ADR-009 decision 4).
				}
			});
			return button;
		};

		// Duyệt / Từ chối: one click, no confirm dialog; locked while one waits (design 4.2).
		const decisionButton = (label, name, action) => {
			const panel = state.panel;
			const button = document.createElement("button");
			button.type = "button";
			button.className = BUTTON_CLASS + (action === ACTION_APPROVE ? "blue" : "danger");
			button.textContent = label;
			button.disabled = panel.deciding;
			button.addEventListener("click", () => {
				try {
					decide(name, action);
				} catch (e) {
					// A panel handler must never break the ticket page (ADR-009 decision 4).
				}
			});
			panel.decisionButtons.push(button);
			return button;
		};

		const proposalActions = (card) => {
			const row = document.createElement("div");
			row.className = "erp-ai-actions";
			const name = String(card?.name ?? "");
			if (!name) {
				return row;
			}
			const canOpen = card?.can_open === true;
			if (card?.can_decide === true) {
				row.append(
					decisionButton(TEXT_APPROVE, name, ACTION_APPROVE),
					decisionButton(TEXT_REJECT, name, ACTION_REJECT)
				);
				if (canOpen) {
					row.append(proposalButton(TEXT_OPEN_PROPOSAL, name));
				}
			} else if (card?.status === STATUS_PENDING) {
				// A console proposal cannot be approved on its form, so it never gets this button.
				if (canOpen && card?.is_console !== true) {
					row.append(proposalButton(OPEN_PROPOSAL_LABEL, name));
				} else {
					// A console card its viewer can open waits for the console switch; the button only shows it.
					const note = document.createElement("span");
					note.className = "erp-ai-note";
					note.textContent = canOpen ? TEXT_CONSOLE_OFF : TEXT_NEEDS_INSTRUCTOR;
					row.append(note);
					if (canOpen) {
						row.append(proposalButton(TEXT_OPEN_PROPOSAL, name));
					}
				}
			} else if (canOpen) {
				row.append(
					proposalButton(
						card?.status === STATUS_APPLIED ? TEXT_UNDO_AT_FORM : TEXT_OPEN_PROPOSAL,
						name
					)
				);
			}
			return row;
		};

		const proposalCard = (card) => {
			const el = document.createElement("div");
			el.className = "erp-ai-card";
			const head = document.createElement("strong");
			head.className = "erp-ai-card-head";
			head.textContent = [card?.name, card?.status].filter(Boolean).join(" · ");
			el.append(head);
			const addLine = (text, preWrap) => {
				const line = document.createElement("div");
				if (preWrap) {
					line.className = "erp-ai-pre";
				}
				line.textContent = text;
				el.append(line);
			};
			if (card?.target) {
				addLine(String(card.target), false);
			}
			if (Array.isArray(card?.notes)) {
				for (const note of card.notes) {
					addLine(String(note ?? ""), true);
				}
			}
			if (card?.is_console === true) {
				const addBlock = (label, value) => {
					addLine(label, false);
					const pre = document.createElement("pre");
					pre.style.whiteSpace = "pre-wrap";
					pre.style.maxHeight = "240px";
					pre.style.overflow = "auto";
					pre.textContent = String(value);
					el.append(pre);
				};
				if (card?.script) {
					addBlock(TEXT_CONSOLE_SCRIPT, card.script);
				}
				if (card?.output) {
					addBlock(TEXT_CONSOLE_OUTPUT, card.output);
				}
			}
			if (card?.decided_by) {
				addLine(TEXT_DECIDED_BY + card.decided_by, false);
			}
			if (card?.restart_status) {
				addLine(TEXT_RESTART + card.restart_status, false);
			}
			if (card?.failure_reason) {
				addLine(TEXT_FAILURE_REASON + card.failure_reason, true);
			}
			el.append(proposalActions(card));
			return el;
		};

		// Messages and cards in one thread by `created` (a card after a message of the same time). A card that
		// fails to build leaves the messages without cards; it never fails the rest of the panel (AC-11).
		// A system line carries no time, only the message it follows (CHG-009 D-5): it stays under that message,
		// with no anchor first in the thread, with an unknown anchor last.
		const renderThread = (data) => {
			const panel = state.panel;
			const messages = data?.messages;
			if (!Array.isArray(messages)) {
				throw new Error("messages is not a list");
			}
			const lines = data?.bot_status?.lines;
			// Each line goes under its message: no anchor first, an unknown anchor last.
			const first = [];
			const last = [];
			const below = new Map(messages.map((message) => [message?.name, []]));
			for (const line of Array.isArray(lines) ? lines : []) {
				const after = line?.after_message;
				const place =
					after === null || after === undefined ? first : below.get(after) || last;
				place.push(systemLine(line));
			}
			let newestGuidance = -1;
			messages.forEach((message, index) => {
				if (message?.is_bot && message?.kind === KIND_GUIDANCE) {
					newestGuidance = index;
				}
			});
			const entries = messages.map((message, index) => ({
				created: String(message?.created ?? ""),
				rank: 0,
				nodes: [
					messageRow(
						message,
						index === newestGuidance && message?.approvable,
						index === newestGuidance && message?.result_confirmable
					),
					...(below.get(message?.name) || []),
				],
			}));
			const proposals = data?.proposals;
			if (Array.isArray(proposals) && proposals.length > 0) {
				let cardNodes = [];
				try {
					panel.decisionButtons = [];
					cardNodes = proposals.map(proposalCard);
				} catch (e) {
					cardNodes = [];
					panel.decisionButtons = [];
					panel.proposalErrorEl.replaceChildren();
				}
				cardNodes.forEach((node, i) => {
					entries.push({
						created: String(proposals[i]?.created ?? ""),
						rank: 1,
						nodes: [node],
					});
				});
			} else {
				clearProposals();
			}
			entries.sort((a, b) =>
				a.created < b.created ? -1 : a.created > b.created ? 1 : a.rank - b.rank
			);
			if (entries.length === 0) {
				const empty = document.createElement("div");
				empty.className = "erp-ai-empty";
				empty.textContent = TEXT_EMPTY_THREAD;
				panel.threadEl.replaceChildren(empty, ...first, ...last);
				return;
			}
			panel.threadEl.replaceChildren(
				...first,
				...entries.flatMap((entry) => entry.nodes),
				...last
			);
		};

		const reload = () => {
			const panel = state.panel;
			if (!panel.open || !state.ticket) {
				return;
			}
			const seq = ++panel.seq;
			const ticket = state.ticket;
			const isStale = () => seq !== panel.seq || ticket !== state.ticket || !panel.open;
			const showLoadFailed = () => {
				if (!isStale()) {
					panel.loadingEl?.remove();
					panel.errorEl.textContent = TEXT_LOAD_FAILED;
				}
			};
			try {
				state
					.call("erp_ai.ticket_panel.get_panel_data", { ticket })
					.then((data) => {
						try {
							if (isStale()) {
								return;
							}
							// Read before the new content changes the height.
							const atBottom = panel.stickToBottom || isAtBottom();
							renderAiFields(data);
							renderBotStatus(data);
							renderThread(data);
							panel.errorEl.textContent = "";
							if (atBottom) {
								scrollToBottom();
							}
							panel.stickToBottom = false;
						} catch (e) {
							panel.botStatus = null;
							showBotStatus();
							panel.aiListEl.replaceChildren();
							clearProposals();
							panel.threadEl.replaceChildren();
							panel.errorEl.textContent = TEXT_LOAD_FAILED;
							return;
						}
					})
					.catch(showLoadFailed);
			} catch (e) {
				showLoadFailed();
			}
		};

		// One click = one POST, then one reload whatever the answer (ADR-044 QĐ 7); no timer.
		const decide = (name, action) => {
			const panel = state.panel;
			if (panel.deciding || !panel.open || !state.ticket) {
				return;
			}
			const ticket = state.ticket;
			const isStale = () => ticket !== state.ticket;
			const lockDecisions = (locked) => {
				for (const button of panel.decisionButtons) {
					button.disabled = locked;
				}
			};
			// A left ticket was reset (deciding cleared, cards gone): a late answer does nothing.
			const onDecided = () => {
				try {
					if (isStale()) {
						return;
					}
					panel.deciding = false;
					reload();
				} catch (e) {
					// A panel handler must never break the ticket page (ADR-009 decision 4).
				}
			};
			// Fixed sentence, not the server's text (D-2); buttons work again until the reload.
			const onDecideFailed = () => {
				try {
					if (isStale()) {
						return;
					}
					panel.deciding = false;
					lockDecisions(false);
					panel.proposalErrorEl.textContent = TEXT_DECIDE_FAILED;
					reload();
				} catch (e) {
					// A panel handler must never break the ticket page (ADR-009 decision 4).
				}
			};
			panel.deciding = true;
			lockDecisions(true);
			panel.proposalErrorEl.textContent = "";
			try {
				state
					.call("erp_ai.ticket_panel.decide_proposal", { name, action })
					.then(onDecided, onDecideFailed);
			} catch (e) {
				onDecideFailed();
			}
		};

		const submit = () => {
			const panel = state.panel;
			if (panel.sending || !panel.open || !state.ticket) {
				return;
			}
			const value = panel.inputEl.value.trim();
			if (!value) {
				panel.errorEl.textContent = TEXT_EMPTY_MESSAGE;
				return;
			}
			if (value.length > MAX_MESSAGE_CHARS) {
				panel.errorEl.textContent = TEXT_TOO_LONG;
				return;
			}
			const ticket = state.ticket;
			const isStale = () => ticket !== state.ticket;
			const unlock = () => {
				panel.sending = false;
				panel.inputEl.disabled = false;
				panel.sendEl.disabled = false;
				panel.sendEl.textContent = TEXT_SEND;
			};
			const onSent = () => {
				try {
					unlock();
					if (isStale()) {
						return;
					}
					panel.inputEl.value = "";
					panel.errorEl.textContent = "";
					reload();
				} catch (e) {
					// A panel handler must never break the ticket page (ADR-009 decision 4).
				}
			};
			const onSendFailed = () => {
				try {
					unlock();
					if (!isStale()) {
						panel.errorEl.textContent = TEXT_SEND_FAILED;
					}
				} catch (e) {
					// A panel handler must never break the ticket page (ADR-009 decision 4).
				}
			};
			panel.errorEl.textContent = "";
			panel.sending = true;
			panel.inputEl.disabled = true;
			panel.sendEl.disabled = true;
			panel.sendEl.textContent = TEXT_SENDING;
			try {
				state
					.call("erp_ai.ticket_panel.send_message", { ticket, text: value })
					.then(onSent, onSendFailed);
			} catch (e) {
				onSendFailed();
			}
		};

		// Duyệt / Không duyệt under a finished plan: one server call, locked while it runs (CHG-017).
		const resultButton = (label, action) => {
			const button = document.createElement("button");
			button.type = "button";
			button.className = BUTTON_CLASS + (action === "approve" ? "green" : "danger");
			button.textContent = label;
			button.addEventListener("click", () => {
				try {
					const panel = state.panel;
					const ticket = state.ticket;
					if (panel.deciding || !ticket) {
						return;
					}
					panel.deciding = true;
					panel.errorEl.textContent = "";
					const done = (failed) => {
						try {
							panel.deciding = false;
							if (ticket !== state.ticket) {
								return;
							}
							panel.errorEl.textContent = failed ? TEXT_RESULT_FAILED : "";
							reload();
						} catch (e) {
							// A panel handler must never break the ticket page (ADR-009 decision 4).
						}
					};
					state.call("erp_ai.ticket_panel.decide_result", { ticket, action }).then(
						() => done(false),
						() => done(true)
					);
				} catch (e) {
					state.panel.deciding = false;
				}
			});
			return button;
		};

		// A header click flips the panel; the host bot (onHostToggle) first leaves the state its card wants in hostWants.
		const togglePanel = () => {
			try {
				const panel = state.panel;
				const wanted = panel.hostWants ?? !panel.open;
				panel.hostWants = undefined;
				if (!wanted) {
					closePanel();
					return;
				}
				if (panel.open) {
					return;
				}
				// The press of this same click, outside the open panel, has just closed it: stay closed.
				if (Date.now() - panel.closedByPressAt < OUTSIDE_CLOSE_GRACE_MS) {
					return;
				}
				buildPanel();
				panel.open = true;
				panel.el.hidden = false;
				dockIndicator(true);
				if (panel.threadEl.childElementCount === 0) {
					panel.threadEl.replaceChildren(loadingRow());
				}
				// Open on the newest message and the send box; the reload keeps it there once the data is in.
				panel.stickToBottom = true;
				scrollToBottom();
				panel.inputEl.focus({ preventScroll: true });
				reload();
			} catch (e) {
				// A panel handler must never break the ticket page (ADR-009 decision 4).
			}
		};

		// The host bot opened or closed its card: show or take away this ticket's chat in it.
		const onHostToggle = (event) => {
			try {
				if (!state.ticket || !host()) {
					return;
				}
				state.panel.hostWants = Boolean(event?.detail?.open);
				togglePanel();
			} catch (e) {
				// A host event must never break the ticket page (ADR-009 decision 4).
			}
		};

		const onHostMove = () => {
			try {
				placeIndicatorNearHost();
			} catch (e) {
				// A host event must never break the ticket page (ADR-009 decision 4).
			}
		};

		// A press outside the open panel closes it (the panel is no dialog: the page stays usable around it).
		const onPointerDown = (event) => {
			try {
				// In the host bot's card, the bot's own close button and launcher close the chat.
				if (host()) {
					return;
				}
				const panel = state.panel;
				if (!panel.open || !panel.el || panel.el.contains(event?.target)) {
					return;
				}
				closePanel();
				panel.closedByPressAt = Date.now();
			} catch (e) {
				// A page listener must never throw to the console (AC-10 g).
			}
		};

		const reset = () => {
			for (const run of state.runs.values()) {
				clearTimeout(run.timer);
			}
			state.runs.clear();
			state.finished.clear();
			if (state.el) {
				setIndicatorVisible(state.el, false);
			}
			const panel = state.panel;
			panel.seq++;
			closePanel();
			panel.aiListEl?.replaceChildren();
			panel.threadEl?.replaceChildren();
			clearExpiryTimer();
			panel.botStatus = null;
			panel.statusExpired = false;
			if (panel.statusTextEl) {
				panel.statusTextEl.textContent = "";
			}
			panel.deciding = false;
			clearProposals();
			if (panel.inputEl) {
				panel.inputEl.value = "";
			}
			if (panel.errorEl) {
				panel.errorEl.textContent = "";
			}
		};

		const onStatus = (msg) => {
			try {
				if (!msg || String(msg.ticket_id) !== state.ticket) {
					return;
				}
				const runId = msg.run_id;
				if (state.finished.has(runId)) {
					return;
				}
				if (msg.state === "done") {
					finish(runId);
					if (state.panel.open) {
						reload();
					}
					return;
				}
				if (msg.state !== "thinking" && msg.state !== "working") {
					return;
				}
				let run = state.runs.get(runId);
				if (!run) {
					const ms = Number(msg.expires_in_s) * 1000;
					if (!(ms > 0)) {
						return;
					}
					run = {
						timer: setTimeout(() => {
							try {
								finish(runId);
							} catch (e) {
								// A timer callback must never throw to the console (AC-10 g).
							}
						}, ms),
						text: "",
						name: "",
						at: 0,
					};
					state.runs.set(runId, run);
				}
				run.text = msg.text;
				run.name = msg.agent_name || msg.agent_user;
				run.at = Date.now();
				render();
			} catch (e) {
				// The indicator must never break the ticket page (ADR-007 decision 5).
			}
		};

		const onDocinfo = (msg) => {
			try {
				if (
					msg?.key === "comments" &&
					msg.doc?.reference_doctype === "HD Ticket" &&
					String(msg.doc.reference_name) === state.ticket
				) {
					reload();
				}
			} catch (e) {
				// A socket callback must never throw to the console (AC-10 g).
			}
		};

		const onDocUpdate = (msg) => {
			try {
				if (msg?.doctype === "HD Ticket" && String(msg.name) === state.ticket) {
					reload();
				}
			} catch (e) {
				// A socket callback must never throw to the console (AC-10 g).
			}
		};

		// A new Notification Log row for this person: refresh the list, and count the open ticket's as seen.
		const onNotification = () => {
			try {
				refreshNotices();
				readSeenNotices();
			} catch (e) {
				// A socket callback must never throw to the console (AC-10 g).
			}
		};

		const onResize = () => {
			try {
				if (window.innerWidth < NARROW_SCREEN_PX) {
					closePanel();
				}
			} catch (e) {
				// A resize callback must never throw to the console (AC-10 g).
			}
		};

		if (window.innerWidth >= NARROW_SCREEN_PX) {
			buildBot();
		}
		if (ticketName !== null && ticketName !== state.ticket) {
			reset();
			state.ticket = ticketName;
		}
		syncBotView();
		if (state.ticket) {
			socket.emit("doc_subscribe", "HD Ticket", state.ticket);
		}
		if (ticketName !== null) {
			// Opening a ticket counts as seeing its notices.
			readSeenNotices();
		}

		if (state.socket !== socket) {
			state.socket = socket;
			socket.on(EVENT, onStatus);
			socket.on("docinfo_update", onDocinfo);
			socket.on("doc_update", onDocUpdate);
			socket.on("notification", onNotification);
			socket.on("connect", () => {
				try {
					// Re-join the room after a reconnect; never subscribe with no ticket open.
					if (state.ticket) {
						socket.emit("doc_subscribe", "HD Ticket", state.ticket);
					}
					if (state.panel.open) {
						reload();
					}
				} catch (e) {
					// A socket callback must never throw to the console (AC-10 g).
				}
			});
			router?.afterEach((to) => {
				try {
					if (
						to?.name !== "TicketAgent" ||
						String(to?.params?.ticketId) !== state.ticket
					) {
						// Left the viewed ticket: forget it so its signals are ignored (ADR-008 decision 6).
						reset();
						state.ticket = null;
						syncBotView();
					}
				} catch (e) {
					// A router hook must never throw to the console (AC-10 g).
				}
			});
		}
		// Capture phase: the press is seen even when the page stops it on its way down.
		if (!state.outsideBound) {
			state.outsideBound = true;
			document.addEventListener("pointerdown", onPointerDown, true);
		}
		if (!state.resizeBound) {
			state.resizeBound = true;
			window.addEventListener("resize", onResize);
		}
		if (!state.hostBound) {
			state.hostBound = true;
			window.addEventListener(HOST_TOGGLE_EVENT, onHostToggle);
			window.addEventListener(HOST_MOVE_EVENT, onHostMove);
		}
		if (host()) {
			// Moved to this ticket with the bot's card already open (its open state is never stored, so not on F5).
			if (host().isOpen()) {
				onHostToggle({ detail: { open: true } });
			}
			return { actions: [] };
		}
		if (window.innerWidth < NARROW_SCREEN_PX) {
			return { actions: [] };
		}
		return { actions: [{ label: ACTION_LABEL, onClick: togglePanel }] };
	} catch (e) {
		// The indicator must never break the ticket page (ADR-007 decision 5).
	}
	return { actions: [] };
}
