"""Puts one script tag in the Helpdesk SPA page of an agent, so the Miyano bot starts on any page and not only
after a ticket page runs the form script (ADR-052). The tag loads public/js/miyano_bot_loader.js, which runs the
widget file of the form script (public/js/agent_status_indicator.js) once, with no ticket."""

import os

import frappe
from helpdesk.utils import is_agent

LOADER_PATH = "/assets/erp_ai/js/miyano_bot_loader.js"
SPA_PATH = "/helpdesk"
BODY_END = "</body>"
TITLE_LOADER_FAILED = "Miyano bot loader failed"


def loader_tag() -> str:
	"""The tag; its `v` is the loader file's age, so a new loader is fetched after an update."""
	try:
		version = int(os.path.getmtime(frappe.get_app_path("erp_ai", "public", "js", "miyano_bot_loader.js")))
	except OSError:
		version = 0
	return f'<script src="{LOADER_PATH}?v={version}" defer></script>'


def _is_spa_page(request) -> bool:
	return request.method == "GET" and (request.path == SPA_PATH or request.path.startswith(SPA_PATH + "/"))


def inject_bot_loader(response=None, request=None, **_) -> None:
	"""after_request hook: add the loader tag to an agent's HTML answer of the Helpdesk SPA. Any other answer is
	left as it is, and a failure here never breaks the page."""
	try:
		if response is None or request is None or not _is_spa_page(request):
			return
		if response.status_code != 200 or "text/html" not in (response.content_type or ""):
			return
		if frappe.session.user == "Guest" or not is_agent():
			return
		html = response.get_data(as_text=True)
		if LOADER_PATH in html or BODY_END not in html:
			return
		head, _sep, tail = html.rpartition(BODY_END)
		response.set_data(head + loader_tag() + BODY_END + tail)
	except Exception as exc:
		frappe.log_error(TITLE_LOADER_FAILED, f"path={getattr(request, 'path', '')} error={type(exc).__name__}")
