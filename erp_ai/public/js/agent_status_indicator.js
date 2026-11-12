function setupForm({ doc, router }) {
	try {
		const EVENT = "erp_ai:agent_status";
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
			bound: false,
		});

		const ensureElement = () => {
			if (state.el) {
				return state.el;
			}
			const el = document.createElement("div");
			el.setAttribute("role", "status");
			el.setAttribute("aria-live", "polite");
			el.hidden = true;
			Object.assign(el.style, {
				position: "fixed",
				right: "24px",
				bottom: "88px",
				zIndex: "40",
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

		const reset = () => {
			for (const run of state.runs.values()) {
				clearTimeout(run.timer);
			}
			state.runs.clear();
			state.finished.clear();
			if (state.el) {
				state.el.hidden = true;
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
						timer: setTimeout(() => finish(runId), ms),
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
			socket.on("connect", () => socket.emit("doc_subscribe", "HD Ticket", state.ticket));
			router?.afterEach((to) => {
				if (to?.name !== "TicketAgent" || String(to?.params?.ticketId) !== state.ticket) {
					reset();
				}
			});
		}
	} catch (e) {
		// The indicator must never break the ticket page (ADR-007 decision 5).
	}
	return { actions: [] };
}
