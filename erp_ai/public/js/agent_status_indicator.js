function setupForm({ doc, call, router }) {
	try {
		const EVENT = "erp_ai:agent_status";
		const ACTION_LABEL = "Trao đổi với bot";
		const TEXT_PANEL_TITLE = "Hướng giải quyết & trao đổi với bot";
		const TEXT_CLOSE = "Đóng";
		const TEXT_AI_SECTION = "Hướng giải quyết của AI";
		const TEXT_EMPTY_FIELD = "Chưa có";
		const TEXT_LOAD_FAILED = "Không tải được dữ liệu của khu vực. Hãy đóng rồi mở lại.";
		const NARROW_SCREEN_PX = 640;
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
		const newPanelState = () => ({
			el: null,
			open: false,
			slotEl: null,
			aiListEl: null,
			errorEl: null,
			seq: 0,
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
		});
		state.call = call;
		// A state object left by an older script version has no panel part.
		state.panel = state.panel || newPanelState();

		const ensureElement = () => {
			if (state.el) {
				return state.el;
			}
			const el = document.createElement("div");
			el.setAttribute("role", "status");
			el.setAttribute("aria-live", "polite");
			el.hidden = true;
			Object.assign(el.style, INDICATOR_FLOATING_STYLE, {
				display: "flex",
				alignItems: "center",
				gap: "8px",
				padding: "8px 12px",
				background: "#ffffff",
				border: "1px solid #e5e7eb",
				borderRadius: "8px",
				boxShadow: "0 1px 4px rgba(0, 0, 0, 0.12)",
				fontSize: "13px",
			});
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

		const render = () => {
			const el = ensureElement();
			if (state.runs.size === 0) {
				el.hidden = true;
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
			el.hidden = false;
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
			Object.assign(el.style, {
				position: "fixed",
				right: "24px",
				top: "72px",
				width: "380px",
				maxHeight: "calc(100vh - 120px)",
				overflowY: "auto",
				zIndex: "40",
				padding: "12px",
				background: "#ffffff",
				border: "1px solid #e5e7eb",
				borderRadius: "8px",
				boxShadow: "0 1px 4px rgba(0, 0, 0, 0.12)",
				fontSize: "13px",
			});
			el.hidden = true;
			const header = document.createElement("div");
			Object.assign(header.style, {
				display: "flex",
				justifyContent: "space-between",
				alignItems: "center",
				marginBottom: "8px",
			});
			const title = document.createElement("strong");
			title.textContent = TEXT_PANEL_TITLE;
			const closeEl = document.createElement("button");
			closeEl.type = "button";
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
			aiTitle.textContent = TEXT_AI_SECTION;
			const aiListEl = document.createElement("div");
			const errorEl = document.createElement("div");
			errorEl.style.color = "#b91c1c";
			const slotEl = document.createElement("div");
			el.append(header, aiTitle, aiListEl, errorEl, slotEl);
			document.body.appendChild(el);
			panel.el = el;
			panel.slotEl = slotEl;
			panel.aiListEl = aiListEl;
			panel.errorEl = errorEl;
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
				row.style.marginTop = "8px";
				const label = document.createElement("strong");
				label.textContent = field?.label || "";
				const body = document.createElement("div");
				body.style.whiteSpace = "pre-wrap";
				body.textContent = field?.text ?? TEXT_EMPTY_FIELD;
				row.append(label, body);
				return row;
			});
			state.panel.aiListEl.replaceChildren(...nodes);
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
							renderAiFields(data);
							panel.errorEl.textContent = "";
						} catch (e) {
							panel.errorEl.textContent = TEXT_LOAD_FAILED;
						}
					})
					.catch(showLoadFailed);
			} catch (e) {
				showLoadFailed();
			}
		};

		const togglePanel = () => {
			try {
				const panel = state.panel;
				if (panel.open) {
					closePanel();
					return;
				}
				buildPanel();
				panel.open = true;
				panel.el.hidden = false;
				dockIndicator(true);
				reload();
			} catch (e) {
				// A panel handler must never break the ticket page (ADR-009 decision 4).
			}
		};

		const reset = () => {
			for (const run of state.runs.values()) {
				clearTimeout(run.timer);
			}
			state.runs.clear();
			state.finished.clear();
			if (state.el) {
				state.el.hidden = true;
			}
			const panel = state.panel;
			panel.seq++;
			closePanel();
			if (panel.aiListEl) {
				panel.aiListEl.replaceChildren();
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

		if (String(doc.name) !== state.ticket) {
			reset();
			state.ticket = String(doc.name);
		}
		socket.emit("doc_subscribe", "HD Ticket", state.ticket);

		if (state.socket !== socket) {
			state.socket = socket;
			socket.on(EVENT, onStatus);
			socket.on("connect", () => {
				try {
					// Re-join the room after a reconnect; never subscribe with no ticket open.
					if (state.ticket) {
						socket.emit("doc_subscribe", "HD Ticket", state.ticket);
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
		if (window.innerWidth < NARROW_SCREEN_PX) {
			return { actions: [] };
		}
		return { actions: [{ label: ACTION_LABEL, onClick: togglePanel }] };
	} catch (e) {
		// The indicator must never break the ticket page (ADR-007 decision 5).
	}
	return { actions: [] };
}
