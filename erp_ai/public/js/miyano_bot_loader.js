// ADR-052: starts the Miyano bot on any page of the Helpdesk SPA. erp_ai.page_loader adds this file to the page of an
// agent; it runs the widget file (the same file the form script record holds) once, with no ticket. A ticket page then
// runs the form script as before and the two share one state object.
(() => {
	const WIDGET_PATH = "/assets/erp_ai/js/agent_status_indicator.js";
	const WAIT_MS = 250;
	const MAX_TRIES = 120;

	const call = (method, args) =>
		fetch("/api/method/" + method, {
			method: "POST",
			credentials: "same-origin",
			headers: {
				"Content-Type": "application/json",
				"X-Frappe-CSRF-Token": window.csrf_token || "",
			},
			body: JSON.stringify(args || {}),
		})
			.then((response) => (response.ok ? response.json() : Promise.reject(response)))
			.then((data) => data.message);

	const start = (router) =>
		fetch(WIDGET_PATH, { cache: "no-cache", credentials: "same-origin" })
			.then((response) => (response.ok ? response.text() : Promise.reject(response)))
			.then((source) =>
				new Function(source + "\nreturn setupForm")()({ doc: null, call, router })
			);

	const wait = (tries) => {
		const globals = document.querySelector("#app")?.__vue_app__?.config?.globalProperties;
		if (globals?.$router && globals?.$socket) {
			start(globals.$router).catch(() => {});
		} else if (tries < MAX_TRIES) {
			setTimeout(() => wait(tries + 1), WAIT_MS);
		}
	};

	wait(0);
})();
