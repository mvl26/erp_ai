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
		const INDICATOR_FLOATING_STYLE = {
			position: "fixed",
			right: "24px",
			bottom: "88px",
			zIndex: "40",
		};
		const INDICATOR_DOCKED_STYLE = {
			position: "static",
			right: "",
			bottom: "",
			zIndex: "",
		};
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
		const socket =
			document.querySelector("#app")?.__vue_app__?.config?.globalProperties?.$socket;
		if (!socket || typeof socket.on !== "function" || !doc?.name) {
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

		const buildPanel = () => {
			const panel = state.panel;
			if (panel.el) {
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
				header,
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
			document.body.appendChild(el);
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

		const togglePanel = () => {
			try {
				const panel = state.panel;
				if (panel.open) {
					closePanel();
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

		// A press outside the open panel closes it (the panel is no dialog: the page stays usable around it).
		const onPointerDown = (event) => {
			try {
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

		const onResize = () => {
			try {
				if (window.innerWidth < NARROW_SCREEN_PX) {
					closePanel();
				}
			} catch (e) {
				// A resize callback must never throw to the console (AC-10 g).
			}
		};

		if (String(doc.name) !== state.ticket) {
			reset();
			state.ticket = String(doc.name);
		}
		socket.emit("doc_subscribe", "HD Ticket", state.ticket);

		if (state.socket !== socket) {
			state.socket = socket;
			socket.on(EVENT, onStatus);
			socket.on("docinfo_update", onDocinfo);
			socket.on("doc_update", onDocUpdate);
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
		if (window.innerWidth < NARROW_SCREEN_PX) {
			return { actions: [] };
		}
		return { actions: [{ label: ACTION_LABEL, onClick: togglePanel }] };
	} catch (e) {
		// The indicator must never break the ticket page (ADR-007 decision 5).
	}
	return { actions: [] };
}
