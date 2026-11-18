"""Architecture tests (ADR-001..005, NFR-1, NFR-5, D-23): static scans of the source tree.

Nothing here touches the database, and product code is read as text and parsed with `ast`. Exceptions:
the module imports constants from `erp_ai.constants` (no frappe call);
`test_agent_modules_import_alone_in_fresh_process` imports a few modules in a child Python process (never
in this one) to catch import cycles that test order would hide; and
`test_privilege_alert_reads_shared_generic_write_tools` imports the runner's tool tables (ADR-024).

Scanned files ("product code"): every `.py` file under `erp_ai/` except `test_*.py` (this also drops
`test_utils.py`), anything under a `tests/` directory and `__pycache__`. `eval/` is product code (it is an
entry layer, ADR-001), so it is scanned. The legacy-comment rule also scans `.json`, `.js` and `.html`
files of the same tree. `docs/` lives outside `erp_ai/` and is never scanned.

Every rule is a pure function over `{relative path: source}`, so the second class below can feed it
synthetic violating code (must be caught) and clean code (must not be flagged).
"""

import ast
import itertools
import json
import os
import re
import shlex
import subprocess
import sys
import unittest
from pathlib import Path
from typing import ClassVar, NamedTuple
from unittest.mock import patch

from erp_ai.agent import change_link, messages, prompts
from erp_ai.constants import (
	AGENT_STATUS_EVENT,
	AGENT_USER,
	CHANGE_STATUS_APPLIED,
	CHANGE_STATUS_PENDING,
	LESSON_STATUS_ACTIVE,
	PANEL_METHODS,
)

PACKAGE_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = PACKAGE_ROOT.parent
CI_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "ci.yml"
PACKAGE = "erp_ai"
FRESH_IMPORT_MODULES = (
	"erp_ai.agent.policy",
	"erp_ai.agent.tools.read",
	"erp_ai.agent.tools.source",
	"erp_ai.agent.tools.registry",
	"erp_ai.erp_ai_agent.doctype.erp_ai_setting.erp_ai_setting",
)

CLIENT_FILE = "gateway/client.py"
CREDENTIALS_FILE = "gateway/credentials.py"
QUEUE_FILE = "agent/queue.py"
POLICY_FILE = "agent/policy.py"
SOURCE_TOOL_FILE = "agent/tools/source.py"
PROCESS_RUNNER_FILE = "agent/changes/process_runner.py"
PROCESS_RUNNER_WRAPPER = "_run_wrapped"  # its callers pass cwd=/env= through to subprocess.run
# ADR-013, ADR-022, D-12: the only files that start processes.
SUBPROCESS_FILES = (SOURCE_TOOL_FILE, PROCESS_RUNNER_FILE)
READ_TOOL_FILE = "agent/tools/read.py"
HANDLERS_FILE = "handlers.py"
TOOLS_PREFIX = "agent/tools/"
CHANGE_TEXT_FILE = "agent/change_text.py"
CHANGE_TEXT_MODULE = "erp_ai.agent.change_text"
# Design 8.2 [Sửa vòng 1]: change_text imports only the standard library and erp_ai.constants. Every other
# erp_ai module is read from the tree (so a new one is covered); third-party code is check_import_boundaries'.
CHANGE_TEXT_FORBIDDEN = (
	"frappe",
	"helpdesk",
	*sorted(
		f"{PACKAGE}.{path.stem}"
		for path in PACKAGE_ROOT.iterdir()
		if path.stem.isidentifier()
		and not path.stem.startswith("__")
		and path.stem != "constants"
		and (path.is_dir() or path.suffix == ".py")
	),
)

# ADR-001 (layers), ADR-003 (handlers), ADR-005 (tools): (scope module, forbidden modules, reason).
LAYER_RULES = (
	(
		"erp_ai.gateway",
		(
			"erp_ai.agent",
			"erp_ai.eval",
			"erp_ai.handlers",
			"erp_ai.ticket_panel",
			"erp_ai.tasks",
			"erp_ai.install",
			"erp_ai.erp_ai_agent",
		),
		"ADR-001: gateway must not import agent, eval, handlers, ticket_panel, scheduler, install or doctype controllers",
	),
	(
		"erp_ai.agent",
		(
			"erp_ai.eval",
			"erp_ai.handlers",
			"erp_ai.ticket_panel",
			"erp_ai.tasks",
			"erp_ai.install",
			"erp_ai.erp_ai_agent",
		),
		"ADR-001: agent core must not import eval, handlers, ticket_panel, scheduler, install or doctype controllers",
	),
	(
		"erp_ai.agent.tools",
		("erp_ai.gateway", "erp_ai.agent.runner", "erp_ai.agent.queue", "erp_ai.agent.changes"),
		"ADR-001/ADR-005/ADR-011: tools never call the model, run the agent, enqueue jobs or reach the change job/state machine",
	),
	(
		"erp_ai.agent.changes",
		(
			"erp_ai.gateway",
			"erp_ai.agent.runner",
			"erp_ai.agent.run_status",
			"erp_ai.eval",
			"erp_ai.handlers",
			"erp_ai.tasks",
			"erp_ai.install",
			"erp_ai.erp_ai_agent",
		),
		"ADR-012/ADR-013: the change job and state machine never call the model, run the agent or import entry layers and doctype controllers",
	),
	(
		"erp_ai.handlers",
		("erp_ai.gateway", "erp_ai.agent.runner"),
		"ADR-001/ADR-003: handlers enqueue by path string, never import gateway or runner",
	),
	(
		"erp_ai.ticket_panel",
		(
			"erp_ai.gateway",
			"erp_ai.agent.runner",
			"erp_ai.agent.queue",
			"erp_ai.agent.authority",
			"erp_ai.agent.tools",
			"erp_ai.agent.changes.transitions",
		),
		"ADR-001/ADR-010/ADR-044: the panel is an entry layer, it never calls the model, runs the agent, enqueues, judges authority, calls a tool or moves a proposal's state itself",
	),
	(
		"erp_ai.agent.policy",
		("erp_ai.agent.tools",),
		"STD-DESIGN-6: policy là tầng dưới của tools, không import ngược",
	),
	(
		"erp_ai.agent.bot_status",
		(
			"erp_ai.gateway",
			"erp_ai.agent.runner",
			"erp_ai.agent.queue",
			"erp_ai.agent.run_status",
			"erp_ai.agent.tools",
			"erp_ai.agent.policy",
			"erp_ai.agent.run_log",
		),
		"ADR-048 QĐ 6: the panel's status reader never calls the model, runs, queues or signals the agent, calls a tool, judges a gate or writes a log row",
	),
	(
		CHANGE_TEXT_MODULE,
		CHANGE_TEXT_FORBIDDEN,
		"design 8.2/ADR-022: change_text imports only the standard library and erp_ai.constants",
	),
)
# NOT forbidden on purpose: erp_ai.eval -> erp_ai.agent.runner (entry layer -> agent core, ADR-001).

ENQUEUE_NAMES = ("enqueue", "enqueue_doc")
ENQUEUE_REQUIRED_KEYWORDS = ("queue", "timeout", "enqueue_after_commit", "job_id", "deduplicate")
ENQUEUE_TARGETS = (
	"erp_ai.agent.runner.run_for_ticket",
	"erp_ai.agent.changes.apply_job.run_change",
	"erp_ai.agent.daily_report.run_daily_report",
	"erp_ai.agent.kpi.run_weekly_kpi",
	"erp_ai.agent.monthly_review.run_monthly_review",
	"erp_ai.agent.lifecycle.run_task_lifecycle",
)

CONFIG_DOCTYPES = ("ERP AI Setting", "ERP AI Credential")
CONFIG_DOCTYPE_CONSTANTS = ("SETTING_DOCTYPE", "CREDENTIAL_DOCTYPE")
CONFIG_CONTROLLER_FILES = (
	"erp_ai_agent/doctype/erp_ai_setting/erp_ai_setting.py",
	"erp_ai_agent/doctype/erp_ai_credential/erp_ai_credential.py",
)
CONFIG_VARIABLE_NAMES = ("settings", "setting", "credential", "credentials")
DOC_GETTERS = ("get_doc", "get_single", "get_cached_doc", "new_doc")

TOOL_FORBIDDEN_CALL_SUFFIXES = ("db.set_value", "set_user", "db.multisql", "db_update")
SQL_READ_ONLY = re.compile(r"^\s*(select|show|describe)\b", re.IGNORECASE)

# ADR-001: product code imports only the standard library, frappe, helpdesk and itself; `anthropic` (declared
# in pyproject.toml `dependencies`) only in gateway/client.py (NFR-5); the one named exception is
# NAMED_LIBRARY_IMPORTS below. Anything else, any other app, is a violation.
ALLOWED_TOP_LEVEL_MODULES = frozenset({PACKAGE, "frappe", "helpdesk", *sys.stdlib_module_names})
ANTHROPIC_MODULE = "anthropic"
# ADR-040 Phán quyết C-3: the one named exception to ADR-001, `{file: top-level libraries it may import}`
# (versions pinned by frappe, not by erp_ai); how restart_check uses them is check_restart_check_library_use's.
RESTART_CHECK_FILE = "agent/changes/restart_check.py"
NAMED_LIBRARY_IMPORTS = {RESTART_CHECK_FILE: frozenset({"psutil", "redis"})}
RESTART_CHECK_LIBRARIES = tuple(sorted(NAMED_LIBRARY_IMPORTS[RESTART_CHECK_FILE]))
RESTART_CHECK_ALLOWED_NAMES = frozenset(
	{"psutil", "redis", "psutil.Process", "psutil.Error", "redis.exceptions", "redis.exceptions.RedisError"}
)
RESTART_CHECK_FORBIDDEN_METHODS = frozenset(
	{"kill", "terminate", "send_signal", "suspend", "resume", "nice", "ionice", "rlimit", "cpu_affinity"}
)
RESTART_CHECK_FORBIDDEN_MODULES = ("subprocess", "signal", "os.kill", "os.killpg")

POLICY_FIELDS = (
	"permission_level",
	"excluded_teams",
	"ai_opt_out",
	"excluded_title_prefixes",
	"auto_assign_enabled",
	"code_change_enabled",
	"code_change_apps",
	"unrestricted_enabled",
	"record_tools_enabled",
	"act_now_enabled",
	"one_click_approval_enabled",
	"console_enabled",
	"level_cap_a",
	"level_cap_b",
	"level_cap_c",
	"level_cap_d",
	"level_cap_e",
	"level_cap_f",
	"confidence_threshold",
	"lessons_enabled",
	"lessons_max_per_request",
	"lessons_max_chars",
	"lesson_teach_marker",
)
SETTING_CONTROLLER_FILE = "erp_ai_agent/doctype/erp_ai_setting/erp_ai_setting.py"

SECRET_READERS = ("get_decrypted_password", "get_password")
SECRET_NAMES = ("api_key", "apikey", "secret", "password", "token")
LOG_SINK_CALLS = ("print", "frappe.log_error", "frappe.msgprint", "frappe.throw")
LOG_SINK_METHODS = ("debug", "info", "warning", "error", "exception", "critical")

STATUS_SCRIPT_FILE = "public/js/agent_status_indicator.js"
STATUS_INDICATOR_VISIBILITY = "setIndicatorVisible"
STATUS_INDICATOR_FUNCTIONS = ("ensureElement", "render", "reset", "dockIndicator")
# `el.style.display = …` or `Object.assign(el.style, …, { display: … })` on the indicator itself.
STATUS_INDICATOR_DISPLAY_WRITE = re.compile(
	r"\b(?:state\.)?el\.style\.display\s*=(?!=)|Object\.assign\((?:state\.)?el\.style\b[^;]*?\bdisplay\s*:"
)
CONSTANTS_FILE = "constants.py"
# Design 3.7: Helpdesk loads the page script through `new Function`, so none of these may appear in it.
STATUS_SCRIPT_FORBIDDEN = (
	r"innerHTML",
	r"outerHTML",
	r"insertAdjacentHTML",
	r"document\.write",
	r"eval\(",
	r"new Function",
	r"doc_unsubscribe",
	r"localStorage",
	r"sessionStorage",
	r"document\.cookie",
	r"fetch\(",
	r"XMLHttpRequest",
	r"frappe\.call",
	r"updateField",
	r"open_doc:",
	r"600",
	r"HD Form Script",
	r"^\s*(import|export)\b",
	# ADR-009: the panel script must not parse markup, poll, unbind listeners or create navigable elements.
	r"DOMParser",
	r"createContextualFragment",
	r"setInterval",
	r"MutationObserver",
	r"\.off\(",
	r"removeListener",
	r"removeAllListeners",
	r'createElement\("a"',
	r'createElement\("img"',
	r'createElement\("iframe"',
	r'createElement\("script"',
	r"\.src =",
	r"\.href =",
	r"innerText =",
	# CHG-008 T4: the panel only reads proposals; deciding goes through its own method, never the controller.
	r"change_decision",
	r"erp_ai_change_proposal\.",
	# CHG-008 T5 (AC-5): Duyệt / Từ chối is one click, never a confirm dialog of the browser or of Frappe.
	r"\bconfirm\(",
)
# Regexes: the socket guard keeps setupForm (run many times) from registering listeners twice; the
# `state.ticket = null` leave-page step keeps a left ticket's signals from showing (ADR-008 decision 6).
STATUS_SCRIPT_REQUIRED = (
	r"textContent",
	r"doc_subscribe",
	r'"connect"',
	r"setTimeout",
	r"try \{",
	r"catch \(",
	r"expires_in_s",
	r"if \(state\.socket !== socket\)",
	r"state\.ticket = null",
	r"if \(state\.ticket\)",
	# T12: message thread, labels, B-8 guidance, close button, indicator moved into the panel and back.
	r"threadEl",
	# CHG-010: one thread of messages and cards, so renderThread replaces renderMessages and renderProposals.
	r"renderThread",
	r'TEXT_EMPTY_THREAD = "Chưa có tin nào\."',
	r'TEXT_BOT_LABEL = "Bot"',
	r'TEXT_CLOSE = "Đóng"',
	r"Bot có thể không trả lời khi đang tắt, đang ở chế độ chỉ ghi nhận, "
	r"phiếu không dùng AI hoặc thuộc nhóm loại trừ, đã hết lượt hôm nay, "
	r"hoặc đang trả lời tin trước của phiếu này \(khi đó hãy gửi lại sau\)\. "
	r"Nhận định và hướng xử lý của bot là tin trong ngăn này; người có vai trò ERP AI Instructor bấm "
	r"\"Duyệt hướng xử lý\" dưới tin đó \(nút chỉ có khi bot còn việc tự làm\) thì bot làm theo\.",
	# ADR-050: the approve button under the newest guidance of the bot sends the fixed approval text through submit.
	r'TEXT_APPROVE_GUIDANCE = "Duyệt hướng xử lý";',
	r"message\?\.is_bot && message\?\.kind === KIND_GUIDANCE",
	# CHG-010: the button shows only under a guidance the server marks approvable.
	r"index === newestGuidance && message\?\.approvable",
	r"panel\.inputEl\.value = APPROVE_GUIDANCE_TEXT;\s*submit\(\);",
	r'TEXT_LOAD_FAILED = "Không tải được dữ liệu của khu vực\. Hãy đóng rồi mở lại\."',
	r"\(docked \? state\.panel\.slotEl : document\.body\)\.appendChild\(el\)",
	# T12: stale-result guard (design F1 reload).
	r"seq !== panel\.seq \|\| ticket !== state\.ticket \|\| !panel\.open",
	# T12 use sites (the pins above match declarations; these match where each is used).
	# CHG-010: the use site is renderThread(data) now.
	r"renderThread\(data\)",
	r"if \(isStale\(\)\) \{\s*return;",
	r"dockIndicator\(true\)",
	r"dockIndicator\(false\)",
	r"textContent = TEXT_BOT_GUIDANCE",
	r"textContent = TEXT_EMPTY_THREAD",
	r"textContent = TEXT_CLOSE",
	r"\? TEXT_BOT_LABEL :",
	# A failed reload clears both lists (no new AI fields beside an old thread); reset tolerates an old panel state.
	r"panel\.threadEl\.replaceChildren\(\);\s*panel\.errorEl\.textContent = TEXT_LOAD_FAILED",
	r"panel\.threadEl\?\.replaceChildren\(\)",
	# T13 send box: fixed texts, then the use sites (declaration-only pins were rejected in review).
	r'TEXT_SEND_FAILED = "Không gửi được tin\. Chữ bạn gõ vẫn còn, hãy thử lại\."',
	r'TEXT_EMPTY_MESSAGE = "Hãy nhập nội dung trước khi gửi\."',
	r'TEXT_TOO_LONG = "Tin dài quá 2000 ký tự\."',
	r'TEXT_SENDING = "Đang gửi…"',
	r"MAX_MESSAGE_CHARS = 2000",
	r'event\.key === "Enter" && !event\.shiftKey && !event\.isComposing',
	r'sendEl\.addEventListener\("click"',
	r"const value = panel\.inputEl\.value\.trim\(\)",
	r"if \(!value\) \{\s*panel\.errorEl\.textContent = TEXT_EMPTY_MESSAGE;\s*return;",
	r"value\.length > MAX_MESSAGE_CHARS\) \{\s*panel\.errorEl\.textContent = TEXT_TOO_LONG;\s*return;",
	r"if \(panel\.sending \|\| !panel\.open",
	r"panel\.sending = true",
	r"panel\.sending = false",
	r'state\s*\.call\("erp_ai\.ticket_panel\.send_message", \{ ticket, text: value \}\)',
	r'panel\.inputEl\.value = "";\s*panel\.errorEl\.textContent = "";\s*reload\(\)',
	# Failure only shows the fixed text: nothing else (such as clearing the box) happens in that branch.
	r"if \(!isStale\(\)\) \{\s*panel\.errorEl\.textContent = TEXT_SEND_FAILED;\s*\}",
	r"sendEl\.textContent = TEXT_SENDING",
	r"sendEl\.textContent = TEXT_SEND\b",
	r"inputEl\.placeholder = TEXT_INPUT_PLACEHOLDER",
	# T13 r1: fixed values of the remaining texts, and the box is locked while a send is pending.
	r'TEXT_SEND = "Gửi";',
	r'TEXT_INPUT_PLACEHOLDER =\s*"Nhập câu hỏi cho bot\. Enter để gửi, Shift\+Enter để xuống dòng\."',
	r"panel\.sendEl\.disabled = true;\s*panel\.sendEl\.textContent = TEXT_SENDING",
	r"panel\.inputEl\.disabled = true",
	# T13 r1: each wiring point pinned at its use site (a declaration or a copy elsewhere must not satisfy it).
	r"const isStale = \(\) => ticket !== state\.ticket;",
	r"unlock = \(\) => \{\s*panel\.sending = false;\s*panel\.inputEl\.disabled = false;\s*panel\.sendEl\.disabled = false;\s*panel\.sendEl\.textContent = TEXT_SEND;\s*\}",
	r'unlock\(\);\s*if \(isStale\(\)\) \{\s*return;\s*\}\s*panel\.inputEl\.value = ""',
	r"onSendFailed = \(\) => \{\s*try \{\s*unlock\(\);\s*if \(!isStale\(\)\)",
	r"\.then\(onSent, onSendFailed\)",
	r"catch \(e\) \{\s*onSendFailed\(\);",
	r"isComposing\) \{\s*event\.preventDefault\(\);\s*submit\(\);",
	r'addEventListener\("click", \(\) => \{\s*try \{\s*submit\(\);',
	# CHG-008 T4 (design 4.3): the proposals section, between the thread and the error line, and the fixed texts.
	# CHG-010: no separate proposals section; the cards sit in threadEl and proposalErrorEl follows it.
	# CHG-009 design 4.1, 8.2 (A-7): the send box closes the panel; the indicator's slot moved into the status line.
	r"threadEl,\s*proposalErrorEl,\s*errorEl,\s*formEl\s*\)",
	# CHG-010: console cards show the script and its result; cards are ordered with the messages by time.
	# CHG-010 final review F-9: the label says the script runs as Administrator.
	r'TEXT_CONSOLE_SCRIPT = "Script sẽ chạy \(quyền Administrator\):"',
	r'TEXT_CONSOLE_OUTPUT = "Kết quả:"',
	# CHG-010 final review F-5: an empty script or output (None from the server) draws no block.
	r"if \(card\?\.script\) \{\s*addBlock\(TEXT_CONSOLE_SCRIPT, card\.script\);",
	r"if \(card\?\.output\) \{\s*addBlock\(TEXT_CONSOLE_OUTPUT, card\.output\);",
	# CHG-010 final review F-6: a pending console card the viewer can open but not decide is held by the console
	# switch (server PANEL_REFUSALS["console_off"]); the viewer keeps the button that only shows it.
	r'TEXT_CONSOLE_OFF = "Chạy bench console đang tắt\."',
	r"note\.textContent = canOpen \? TEXT_CONSOLE_OFF : TEXT_NEEDS_INSTRUCTOR;\s*row\.append\(note\);\s*"
	r"if \(canOpen\) \{\s*row\.append\(proposalButton\(TEXT_OPEN_PROPOSAL, name\)\);",
	r'maxHeight = "240px"',
	r'overflow = "auto"',
	r"\.sort\(\(a, b\) =>[^;]*\.created",
	r"card\?\.is_console !== true",
	r'TEXT_OPEN_PROPOSAL = "Xem nội dung thay đổi"',
	r'OPEN_PROPOSAL_LABEL = "Mở đề xuất để Duyệt hoặc Từ chối"',
	r'TEXT_NEEDS_INSTRUCTOR = "Cần người có vai trò ERP AI Instructor duyệt\."',
	r'TEXT_UNDO_AT_FORM = "Hoàn tác ở form"',
	r'PROPOSAL_FORM_PREFIX = "/app/erp-ai-change-proposal/"',
	r'window\.open\(PROPOSAL_FORM_PREFIX \+ encodeURIComponent\(name\), "_blank", "noopener"\)',
	r"deciding: false",
	r"decisionButtons: \[\]",
	r"Array\.isArray\(proposals\)",
	# CHG-008 T5 (design 4.2, 4.3; AC-5, AC-11): Duyệt / Từ chối post once, lock both buttons while waiting, show
	# the fixed error sentence on failure and reload the panel once in both branches.
	r'TEXT_APPROVE = "Duyệt";',
	r'TEXT_REJECT = "Từ chối";',
	r'TEXT_DECIDE_FAILED =\s*"Không duyệt hoặc từ chối được đề xuất; hãy xem trạng thái hiện tại trên thẻ\."',
	r"decisionButton\(TEXT_APPROVE, name, ACTION_APPROVE\),\s*decisionButton\(TEXT_REJECT, name, ACTION_REJECT\)",
	r"button\.disabled = panel\.deciding;",
	r"panel\.decisionButtons\.push\(button\)",
	r'addEventListener\("click", \(\) => \{\s*try \{\s*decide\(name, action\);',
	r"if \(panel\.deciding \|\| !panel\.open \|\| !state\.ticket\) \{\s*return;",
	r'panel\.deciding = true;\s*lockDecisions\(true\);\s*panel\.proposalErrorEl\.textContent = "";',
	r'state\s*\.call\("erp_ai\.ticket_panel\.decide_proposal", \{ name, action \}\)\s*\.then\(onDecided, onDecideFailed\)',
	r"onDecided = \(\) => \{\s*try \{\s*if \(isStale\(\)\) \{\s*return;\s*\}\s*panel\.deciding = false;\s*reload\(\);",
	r"onDecideFailed = \(\) => \{\s*try \{\s*if \(isStale\(\)\) \{\s*return;\s*\}\s*panel\.deciding = false;\s*"
	r"lockDecisions\(false\);\s*panel\.proposalErrorEl\.textContent = TEXT_DECIDE_FAILED;\s*reload\(\);",
	r"catch \(e\) \{\s*onDecideFailed\(\);",
	# T6 review ruling: a card without a name has no button; a failed card render clears only the proposals.
	r'const name = String\(card\?\.name \?\? ""\);\s*if \(!name\) \{\s*return row;',
	# CHG-010: a failed card build renders the messages without cards and clears the card error line (AC-11).
	r'renderThread\(data\);\s*panel\.errorEl\.textContent = "";',
	r"try \{\s*panel\.decisionButtons = \[\];\s*cardNodes = proposals\.map\(proposalCard\);\s*\} catch \(e\) \{\s*cardNodes = \[\];\s*panel\.decisionButtons = \[\];\s*panel\.proposalErrorEl\.replaceChildren\(\);",
	# T14 live updates (design F3): both listeners are named handlers registered once per socket, in the guard block.
	r'state\.socket = socket;\s*socket\.on\(EVENT, onStatus\);\s*socket\.on\("docinfo_update", onDocinfo\);\s*socket\.on\("doc_update", onDocUpdate\);',
	r"docinfo_update",
	r"doc_update",
	# Payload keys: frappe comment.py:59-67 (key, doc.reference_doctype/name) and document.py:1370-1385 (doctype, name).
	r'const onDocinfo = \(msg\) => \{\s*try \{\s*if \(\s*msg\?\.key === "comments" &&\s*msg\.doc\?\.reference_doctype === "HD Ticket" &&\s*String\(msg\.doc\.reference_name\) === state\.ticket\s*\) \{\s*reload\(\);',
	r'const onDocUpdate = \(msg\) => \{\s*try \{\s*if \(msg\?\.doctype === "HD Ticket" && String\(msg\.name\) === state\.ticket\) \{\s*reload\(\);',
	# A finished run refills an open panel: a bot reply no longer fires docinfo_update (ERP AI Message).
	r'if \(msg\.state === "done"\) \{\s*finish\(runId\);\s*if \(state\.panel\.open\) \{\s*reload\(\);\s*\}\s*return;',
	# Reconnect: re-join the room, then refill an open panel.
	r'socket\.emit\("doc_subscribe", "HD Ticket", state\.ticket\);\s*\}\s*if \(state\.panel\.open\) \{\s*reload\(\);',
	# Reset (ticket change or leaving the page): cancel pending loads, close the panel (returns the indicator), clear texts and the input.
	r"const panel = state\.panel;\s*panel\.seq\+\+;\s*closePanel\(\);",
	r'if \(panel\.inputEl\) \{\s*panel\.inputEl\.value = "";\s*\}',
	r"String\(doc\.name\) !== state\.ticket\) \{\s*reset\(\);\s*state\.ticket = String\(doc\.name\)",
	r"reset\(\);\s*state\.ticket = null",
	# Narrow screen: one resize listener for the page lifetime, closing the panel under the width limit.
	r"const onResize = \(\) => \{\s*try \{\s*if \(window\.innerWidth < NARROW_SCREEN_PX\) \{\s*closePanel\(\);",
	r'if \(!state\.resizeBound\) \{\s*state\.resizeBound = true;\s*window\.addEventListener\("resize", onResize\);',
	r"if \(window\.innerWidth < NARROW_SCREEN_PX\) \{\s*return \{ actions: \[\] \};",
	# CHG-009 T5 (design 4.1, 8.2; AC-1, AC-3, A-4, A-7): one status line under the section title, above the guidance,
	# the thread and the cards, holding the docked indicator; a live indicator wins, an open call past its deadline
	# reads its failed time by a timer that only changes the text; the status is set before the thread that carries
	# its system lines.
	r'TEXT_STATUS_RUNNING = "Đang xử lý…"',
	r"statusEl\.append\(statusTextEl, slotEl\)",
	r"chatTitle,\s*statusEl,\s*guidanceEl,\s*threadEl",
	r"state\.runs\.size > 0 \? TEXT_STATUS_RUNNING",
	r"panel\.statusExpired && status\.expired_text",
	# CHG-010: the thread (messages, system lines and cards) is drawn by renderThread, still after the status.
	r"renderBotStatus\(data\);\s*renderThread\(data\)",
	r"statusExpired = true;\s*showBotStatus\(\)",
	# Panel UX: a press outside the open panel closes it, one capture listener for the page lifetime; the click of
	# the same press on the header action does not reopen it; the panel is opened only by that action.
	r'if \(!state\.outsideBound\) \{\s*state\.outsideBound = true;\s*document\.addEventListener\("pointerdown", onPointerDown, true\);',
	r"if \(!panel\.open \|\| !panel\.el \|\| panel\.el\.contains\(event\?\.target\)\) \{\s*return;\s*\}\s*closePanel\(\);\s*panel\.closedByPressAt = Date\.now\(\);",
	r"if \(Date\.now\(\) - panel\.closedByPressAt < OUTSIDE_CLOSE_GRACE_MS\) \{\s*return;",
	# Panel UX: the first open of a ticket shows a loading line; each open lands on the newest message and the send
	# box; a refresh keeps a reader at the bottom there, and leaves one who scrolled up where they are.
	r"if \(panel\.threadEl\.childElementCount === 0\) \{\s*panel\.threadEl\.replaceChildren\(loadingRow\(\)\);",
	r"panel\.stickToBottom = true;",
	r"const atBottom = panel\.stickToBottom \|\| isAtBottom\(\);",
	r'panel\.errorEl\.textContent = "";\s*if \(atBottom\) \{\s*scrollToBottom\(\);',
)
# CHG-009 design 8.2: each pin above with the wiring it guards broken, as (pattern, regex to break, replacement).
STATUS_LINE_VIOLATIONS = (
	(r'TEXT_STATUS_RUNNING = "Đang xử lý…"', r'"Đang xử lý…"', '"Đang chạy…"'),
	(
		r"statusEl\.append\(statusTextEl, slotEl\)",
		r"statusEl\.append\(statusTextEl, slotEl\)",
		"statusEl.append(statusTextEl)",
	),
	(
		r"chatTitle,\s*statusEl,\s*guidanceEl,\s*threadEl",
		r"chatTitle,(\s*)statusEl,(\s*)guidanceEl,(\s*)threadEl",
		r"chatTitle,\1guidanceEl,\2threadEl,\3statusEl",
	),
	(r"state\.runs\.size > 0 \? TEXT_STATUS_RUNNING", r"state\.runs\.size > 0 \?", "false ?"),
	(r"panel\.statusExpired && status\.expired_text", r"panel\.statusExpired && ", ""),
	# CHG-010: renderThread replaced renderMessages at this use site.
	(
		r"renderBotStatus\(data\);\s*renderThread\(data\)",
		r"renderBotStatus\(data\);(\s*)renderThread\(data\);",
		r"renderThread(data);\1renderBotStatus(data);",
	),
	(
		r"statusExpired = true;\s*showBotStatus\(\)",
		r"(statusExpired = true;\s*)showBotStatus\(\)",
		r"\1reload()",
	),
)

# ADR-009: every `call(` in the page script passes a string literal naming one of PANEL_METHODS.
STATUS_SCRIPT_CALL = re.compile(r"\bcall\(\s*(\"([^\"]*)\")?")


def check_status_script_calls(script: str, allowed_methods) -> list:
	"""Violations: a `call(` whose first argument is not a literal in `allowed_methods`."""
	violations = []
	for match in STATUS_SCRIPT_CALL.finditer(script):
		line = script.count("\n", 0, match.start()) + 1
		if match.group(1) is None:
			violations.append(f"line {line}: first argument of call( is not a string literal")
		elif match.group(2) not in allowed_methods:
			violations.append(f"line {line}: {match.group(2)} is not in PANEL_METHODS")
	return violations


# ADR-008 (status signals) and ADR-007 (the one form script): who may publish, import, write or delete.
RUN_STATUS_FILE = "agent/run_status.py"
RUN_STATUS_MODULE = "erp_ai.agent.run_status"
RUNNER_FILE = "agent/runner.py"
INSTALL_FILE = "install.py"
HOOKS_FILE = "hooks.py"
REALTIME_NAMES = ("publish_realtime", "publish_progress", "emit_via_redis")
REALTIME_MODULE = "frappe.realtime"
# Attribute/function names that write a record, the cache, a file or the transaction (NFR-6, ADR-008 decision 5).
RUN_STATUS_WRITE_NAMES = (
	"insert",
	"save",
	"delete",
	"delete_doc",
	"set_value",
	"db_set",
	"sql",
	"multisql",
	"commit",
	"rollback",
	"write",
	"write_text",
	"write_bytes",
	"open",
	"touch",
	"mkdir",
)
RUN_STATUS_FORBIDDEN_ATTRIBUTES = ("frappe.db", "frappe.cache")
OPEN_DOC_ROOM_PREFIX = "open_doc:"
ALL_ROOM = "all"
FORM_SCRIPT_DOCTYPE_NAME = "HD Form Script"
AGENT_STATUS_SCRIPT_NAME = "ERP AI Agent Status"
# ADR-007: Helpdesk's SPA ignores these hooks; the one channel is the form script record (install.py).
PAGE_INJECTION_HOOKS = (
	"app_include_js",
	"web_include_js",
	"app_include_css",
	"web_include_css",
	"after_request",
	"website_route_rules",
	"fixtures",
)
UNINSTALL_HOOK = "erp_ai.install.before_uninstall"
UNINSTALL_FUNCTION = "before_uninstall"
DELETE_NAMES = ("delete", "delete_doc", "delete_doc_if_exists")
SQL_DELETE = re.compile(r"^\s*delete\b", re.IGNORECASE)

LEGACY_NAMES = ("HD Ticket Comment", "commented_by", "comment_email", "comment_by")
# Design 3.5 (amendment 1c) tells `get_record` to DROP comment_email/comment_by from a Comment; this one
# hide-list constant is the only place these names may appear.
LEGACY_ALLOWED_ASSIGNMENTS = {READ_TOOL_FILE: "COMMENT_HIDDEN_FIELDS"}

SUBPROCESS_RUN_FUNCTIONS = ("run", "call", "check_call", "check_output")
OS_SHELL_FUNCTIONS = ("system", "popen", "posix_spawn", "posix_spawnp")
OS_SHELL_PREFIXES = ("exec", "spawn")  # os.execv*, os.execl*, os.spawnv*, os.spawnl*

CI_BENCH_BRANCH = "version-15"
CI_REQUIRED_APPS = (
	# (app, branch required on `bench get-app`, or None when the default branch is accepted)
	("telephony", None),
	("helpdesk", "v15.1.0"),
	("erpnext", "version-15"),
)

# frappe/test_runner.py:160 skips any file with this name when running `run-tests --app`
FRAPPE_SKIPPED_TEST_FILENAMES = ("test_runner.py",)


# ---------------------------------------------------------------------------------------------------
# Scanning helpers
# ---------------------------------------------------------------------------------------------------


def is_product_file(rel: Path, suffixes=(".py",)) -> bool:
	if rel.suffix not in suffixes:
		return False
	if "__pycache__" in rel.parts or "node_modules" in rel.parts:
		return False
	if "tests" in rel.parts[:-1]:
		return False
	return not rel.name.startswith("test_")


def load_product_sources(root: Path = PACKAGE_ROOT, suffixes=(".py",)) -> dict:
	"""`{posix path relative to erp_ai/: source text}` for every product file."""
	sources = {}
	for path in sorted(root.rglob("*")):
		rel = path.relative_to(root)
		if path.is_file() and is_product_file(rel, suffixes):
			sources[rel.as_posix()] = path.read_text(encoding="utf-8")
	return sources


def only_python(sources: dict) -> dict:
	return {rel: src for rel, src in sources.items() if rel.endswith(".py")}


def scoped(sources: dict, prefix: str) -> dict:
	return {rel: src for rel, src in sources.items() if rel.startswith(prefix)}


def module_name(rel: str) -> str:
	parts = list(Path(rel).with_suffix("").parts)
	if parts and parts[-1] == "__init__":
		parts.pop()
	return ".".join([PACKAGE, *parts])


def module_in(module: str, prefix: str) -> bool:
	return module == prefix or module.startswith(prefix + ".")


def imported_modules(tree: ast.AST, module: str, is_package: bool) -> list:
	"""`[(lineno, dotted module)]`; `from a import b` yields both `a` and `a.b` (b may be a submodule)."""
	found = []
	for node in ast.walk(tree):
		if isinstance(node, ast.Import):
			found.extend((node.lineno, alias.name) for alias in node.names)
		elif isinstance(node, ast.ImportFrom):
			base = node.module or ""
			if node.level:
				package = module.split(".") if is_package else module.split(".")[:-1]
				package = package[: len(package) - (node.level - 1)]
				base = ".".join([*package, base] if base else package)
			found.append((node.lineno, base))
			found.extend((node.lineno, f"{base}.{alias.name}") for alias in node.names)
	return found


def dotted_name(node):
	"""`frappe.db.sql` -> "frappe.db.sql"; `frappe.logger(x).warning` -> "frappe.logger().warning"."""
	if isinstance(node, ast.Name):
		return node.id
	if isinstance(node, ast.Attribute):
		base = dotted_name(node.value)
		return f"{base}.{node.attr}" if base else None
	if isinstance(node, ast.Call):
		base = dotted_name(node.func)
		return f"{base}()" if base else None
	return None


def import_aliases(tree: ast.AST) -> dict:
	"""`{local name: real dotted name}` for imports: `import subprocess as sp` -> {"sp": "subprocess"};
	`from subprocess import run as r` -> {"r": "subprocess.run"}."""
	aliases = {}
	for node in ast.walk(tree):
		if isinstance(node, ast.Import):
			for alias in node.names:
				if alias.asname:
					aliases[alias.asname] = alias.name
		elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
			for alias in node.names:
				aliases[alias.asname or alias.name] = f"{node.module}.{alias.name}"
	return aliases


def resolved_name(node, aliases: dict) -> str:
	"""dotted_name with its first segment replaced by the real module it was imported as."""
	name = dotted_name(node) or ""
	head, dot, rest = name.partition(".")
	return aliases[head] + dot + rest if head in aliases else name


def referenced_name(node):
	"""The bare name of a Name/Attribute node (`frappe.enqueue` -> "enqueue"), else None."""
	if isinstance(node, ast.Name):
		return node.id
	if isinstance(node, ast.Attribute):
		return node.attr
	return None


def constant_strings(tree: ast.AST):
	for node in ast.walk(tree):
		if isinstance(node, ast.Constant) and isinstance(node.value, str):
			yield node


def parse(rel: str, source: str) -> ast.AST:
	return ast.parse(source, filename=rel)


def violation(rel: str, node, message: str) -> str:
	return f"{rel}:{getattr(node, 'lineno', 0)}: {message}"


# ---------------------------------------------------------------------------------------------------
# Rules (each returns a list of "file:line: message"; empty = rule holds)
# ---------------------------------------------------------------------------------------------------


def check_layer_imports(sources: dict, rules=LAYER_RULES) -> list:
	violations = []
	for rel, source in only_python(sources).items():
		module = module_name(rel)
		imports = imported_modules(parse(rel, source), module, rel.endswith("__init__.py"))
		for scope, forbidden, reason in rules:
			if not module_in(module, scope):
				continue
			for lineno, target in imports:
				if any(module_in(target, name) for name in forbidden):
					violations.append(f"{rel}:{lineno}: imports {target} ({reason})")
	return violations


def check_import_boundaries(sources: dict) -> list:
	"""ADR-001 allowlist: stdlib, frappe, helpdesk, erp_ai; NFR-5/ADR-002: `anthropic` only in gateway/client.py;
	ADR-040 C-3: a library in NAMED_LIBRARY_IMPORTS only in its file, and a dead exception (the file is gone,
	or no longer imports a listed name) is itself a violation. "Gone" is read from disk, so a partial
	`sources` (the self-checks) does not count as a deleted file."""
	violations = []
	for rel, source in only_python(sources).items():
		imports = imported_modules(parse(rel, source), module_name(rel), rel.endswith("__init__.py"))
		named = NAMED_LIBRARY_IMPORTS.get(rel, ())
		for lineno, target in imports:
			if module_in(target, ANTHROPIC_MODULE):
				if rel != CLIENT_FILE:
					violations.append(f"{rel}:{lineno}: imports {target} outside {CLIENT_FILE} (NFR-5)")
			elif target.split(".")[0] not in ALLOWED_TOP_LEVEL_MODULES and target.split(".")[0] not in named:
				violations.append(
					f"{rel}:{lineno}: imports {target}, not stdlib/frappe/helpdesk/erp_ai (ADR-001: no other app or library)"
				)
	for rel, names in NAMED_LIBRARY_IMPORTS.items():
		if rel not in sources:
			if not (PACKAGE_ROOT / rel).is_file():
				violations.append(f"{rel}: file gone, dead exception in NAMED_LIBRARY_IMPORTS (ADR-040 C-3)")
			continue
		imported = {
			target.split(".")[0]
			for _lineno, target in imported_modules(parse(rel, sources[rel]), module_name(rel), False)
		}
		violations.extend(
			f"{rel}: no longer imports {name}, dead exception in NAMED_LIBRARY_IMPORTS (ADR-040 C-3)"
			for name in sorted(names - imported)
		)
	return violations


def _is_restart_library(name: str) -> bool:
	return any(module_in(name, library) for library in RESTART_CHECK_LIBRARIES)


def check_restart_check_library_use(sources: dict) -> list:
	"""ADR-040 C-3: restart_check.py only reads. psutil/redis only as psutil.Process, psutil.Error,
	redis.exceptions(.RedisError), in imports and attribute references; no signalling or tuning method call
	(kill, terminate, ...); no subprocess, os.kill, os.killpg or signal (design 4.4: no subprocess)."""
	source = sources.get(RESTART_CHECK_FILE)
	if source is None:
		return _missing(RESTART_CHECK_FILE)
	tree = parse(RESTART_CHECK_FILE, source)
	aliases = import_aliases(tree)
	violations = []
	for node in ast.walk(tree):
		if isinstance(node, ast.Import | ast.ImportFrom):
			base = "" if isinstance(node, ast.Import) or node.level else f"{node.module}."
			for alias in node.names:
				name = base + alias.name
				if _is_restart_library(name) and name not in RESTART_CHECK_ALLOWED_NAMES:
					violations.append(violation(RESTART_CHECK_FILE, node, f"imports {name} (ADR-040 C-3)"))
				elif any(module_in(name, forbidden) for forbidden in RESTART_CHECK_FORBIDDEN_MODULES):
					violations.append(
						violation(RESTART_CHECK_FILE, node, f"imports {name} (ADR-040 C-3: read only)")
					)
		elif isinstance(node, ast.Attribute) and "()" not in (name := resolved_name(node, aliases)):
			# a chain through a call (`psutil.Process(pid).create_time`) is a method of an allowed object
			if _is_restart_library(name) and name not in RESTART_CHECK_ALLOWED_NAMES:
				violations.append(violation(RESTART_CHECK_FILE, node, f"uses {name} (ADR-040 C-3)"))
			elif any(module_in(name, forbidden) for forbidden in RESTART_CHECK_FORBIDDEN_MODULES):
				violations.append(
					violation(RESTART_CHECK_FILE, node, f"uses {name} (ADR-040 C-3: read only)")
				)
		if (
			isinstance(node, ast.Call)
			and isinstance(node.func, ast.Attribute)
			and node.func.attr in RESTART_CHECK_FORBIDDEN_METHODS
		):
			violations.append(
				violation(
					RESTART_CHECK_FILE,
					node,
					f"calls .{node.func.attr}() (ADR-040 C-3: never signal a process)",
				)
			)
	return violations


def check_single_enqueue_site(sources: dict) -> list:
	violations = []
	for rel, source in only_python(sources).items():
		if rel == QUEUE_FILE:
			continue
		for node in ast.walk(parse(rel, source)):
			if referenced_name(node) in ENQUEUE_NAMES:
				violations.append(violation(rel, node, f"uses {referenced_name(node)} outside {QUEUE_FILE}"))
			elif isinstance(node, ast.ImportFrom):
				for alias in node.names:
					if alias.name in ENQUEUE_NAMES:
						violations.append(violation(rel, node, f"imports {alias.name} outside {QUEUE_FILE}"))
	return violations


def check_enqueue_call_shape(sources: dict) -> list:
	"""ADR-003/ADR-013 QĐ 2, ADR-033 QĐ 6: exactly one call per target, each with all five parameters."""
	source = sources.get(QUEUE_FILE)
	if source is None:
		return [f"{QUEUE_FILE}: file missing"]
	calls = [
		node
		for node in ast.walk(parse(QUEUE_FILE, source))
		if isinstance(node, ast.Call) and referenced_name(node.func) in ENQUEUE_NAMES
	]
	if len(calls) != len(ENQUEUE_TARGETS):
		return [
			f"{QUEUE_FILE}: expected exactly {len(ENQUEUE_TARGETS)} enqueue calls, one per target, "
			f"found {len(calls)}"
		]
	violations = []
	targets = []
	for call in calls:
		first = call.args[0] if call.args else None
		if isinstance(first, ast.Constant) and first.value in ENQUEUE_TARGETS:
			targets.append(first.value)
		else:
			violations.append(
				violation(QUEUE_FILE, call, f"first argument must be one of the strings {ENQUEUE_TARGETS!r}")
			)
		given = {keyword.arg for keyword in call.keywords}
		for name in ENQUEUE_REQUIRED_KEYWORDS:
			if name not in given:
				violations.append(violation(QUEUE_FILE, call, f"missing keyword {name}="))
	if not violations and sorted(targets) != sorted(ENQUEUE_TARGETS):
		violations.append(
			f"{QUEUE_FILE}: expected one call to each of {ENQUEUE_TARGETS!r}, found {targets!r}"
		)
	return violations


def _is_config_doc_expr(node, config_vars: set) -> bool:
	"""True for `frappe.get_doc("ERP AI Setting")`, `get_doc({"doctype": ...})`, `get_doc(doctype=...)`,
	`frappe.get_single(SETTING_DOCTYPE)` / `constants.SETTING_DOCTYPE`, or a tracked name."""
	if isinstance(node, ast.Name):
		return node.id in config_vars
	if isinstance(node, ast.Call) and referenced_name(node.func) in DOC_GETTERS:
		first = node.args[0] if node.args else None
		if isinstance(first, ast.Dict):  # get_doc({"doctype": ...})
			first = next(
				(
					value
					for key, value in zip(first.keys, first.values, strict=True)
					if isinstance(key, ast.Constant) and key.value == "doctype"
				),
				None,
			)
		elif first is None:  # get_doc(doctype=...)
			first = next((keyword.value for keyword in node.keywords if keyword.arg == "doctype"), None)
		if isinstance(first, ast.Constant):
			return first.value in CONFIG_DOCTYPES
		return referenced_name(first) in CONFIG_DOCTYPE_CONSTANTS
	return False


def check_no_save_on_config(sources: dict) -> list:
	"""ADR-004: no `.save()` on ERP AI Setting / ERP AI Credential objects in product code."""
	violations = []
	for rel, source in only_python(sources).items():
		tree = parse(rel, source)
		config_vars = set(CONFIG_VARIABLE_NAMES)
		for node in ast.walk(tree):
			if isinstance(node, ast.Assign) and _is_config_doc_expr(node.value, set()):
				config_vars.update(t.id for t in node.targets if isinstance(t, ast.Name))
		for node in ast.walk(tree):
			if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)):
				continue
			if node.func.attr != "save":
				continue
			receiver = node.func.value
			if rel in CONFIG_CONTROLLER_FILES or _is_config_doc_expr(receiver, config_vars):
				violations.append(
					violation(rel, node, "`.save()` on an ERP AI configuration object (ADR-004)")
				)
	return violations


def check_tools_never_bypass_permissions(sources: dict) -> list:
	"""ADR-005: inside agent/tools/**, no ignore_permissions, db.set_value, writing db.sql, set_user, get_all.

	Exception (design 3.5, `denied_doctypes`): `get_all("DocType", ...)` lists the app's own DocType names,
	which is metadata, not user data.
	ADR-005 + ADR-034: the query builder checks no permission either, so every `frappe.qb` reference and
	every `frappe.query_builder` import in a tool is a violation (design-w0-fixes-5 point 1).
	"""
	violations = []
	for rel, source in only_python(scoped(sources, TOOLS_PREFIX)).items():
		tree = parse(rel, source)
		aliases = import_aliases(tree)
		for lineno, target in imported_modules(tree, module_name(rel), False):
			if module_in(target, "frappe.query_builder") or target == "frappe.qb":
				violations.append(f"{rel}:{lineno}: imports {target} in a tool (ADR-034)")
		for node in ast.walk(tree):
			if isinstance(node, ast.Attribute) and resolved_name(node, aliases) == "frappe.qb":
				violations.append(violation(rel, node, "frappe.qb in a tool (ADR-034)"))
			if referenced_name(node) == "ignore_permissions" or (
				isinstance(node, ast.Constant) and node.value == "ignore_permissions"
			):
				violations.append(violation(rel, node, "ignore_permissions in a tool"))
			elif isinstance(node, ast.keyword) and node.arg == "ignore_permissions":
				violations.append(violation(rel, node.value, "ignore_permissions= in a tool"))
			if not isinstance(node, ast.Call):
				continue
			name = dotted_name(node.func) or ""
			if name.endswith(TOOL_FORBIDDEN_CALL_SUFFIXES):
				violations.append(violation(rel, node, f"{name} in a tool"))
			elif name.endswith("db.sql"):
				first = node.args[0] if node.args else None
				read_only = (
					isinstance(first, ast.Constant)
					and isinstance(first.value, str)
					and SQL_READ_ONLY.match(first.value)
					and ";" not in first.value.strip().removesuffix(";")
				)
				if not read_only:
					violations.append(violation(rel, node, "db.sql that is not a constant SELECT in a tool"))
			elif name.endswith("get_all"):
				first = node.args[0] if node.args else None
				if not (isinstance(first, ast.Constant) and first.value == "DocType"):
					violations.append(violation(rel, node, f"{name} instead of get_list in a tool"))
	return violations


def check_tools_never_pass_trusted_messages(sources: dict) -> list:
	"""Inside agent/tools/**, no call passes `trusted=True`: the bot's tools never skip the DocType permission."""
	violations = []
	for rel, source in only_python(scoped(sources, TOOLS_PREFIX)).items():
		for node in ast.walk(parse(rel, source)):
			if isinstance(node, ast.keyword) and node.arg == "trusted" and _is_constant(node.value, True):
				violations.append(violation(rel, node.value, "trusted=True in a tool"))
	return violations


def check_subprocess_only_in_source_tool(sources: dict) -> list:
	"""ADR-005, ADR-013, ADR-022: processes start only in SUBPROCESS_FILES."""
	violations = []
	for rel, source in only_python(sources).items():
		if rel in SUBPROCESS_FILES:
			continue
		tree = parse(rel, source)
		aliases = import_aliases(tree)
		for lineno, target in imported_modules(tree, module_name(rel), False):
			if module_in(target, "subprocess"):
				violations.append(f"{rel}:{lineno}: imports {target} outside {SUBPROCESS_FILES}")
		for node in ast.walk(tree):
			if isinstance(node, ast.Call):
				name = resolved_name(node.func, aliases)
				function = name.split(".")[-1]
				if name.startswith("subprocess.") or (
					name.startswith("os.")
					and (function in OS_SHELL_FUNCTIONS or function.startswith(OS_SHELL_PREFIXES))
				):
					violations.append(violation(rel, node, f"{name} outside {SUBPROCESS_FILES}"))
	return violations


def check_subprocess_call_shape(sources: dict) -> list:
	"""ADR-005/ADR-013: every subprocess call in SUBPROCESS_FILES has timeout=, a list command, no shell;
	in process_runner.py every call also has the timeout-wrapped shape (ADR-013 QĐ 3, 7; D-3)."""
	if SOURCE_TOOL_FILE not in sources:
		return [f"{SOURCE_TOOL_FILE}: file missing"]
	violations = []
	for rel in SUBPROCESS_FILES:
		if rel in sources:
			violations.extend(subprocess_call_shape_problems(rel, sources[rel]))
	return violations


def subprocess_call_shape_problems(rel: str, source: str) -> list:
	violations = []
	tree = parse(rel, source)
	aliases = import_aliases(tree)
	for node in ast.walk(tree):
		if not isinstance(node, ast.Call):
			continue
		name = resolved_name(node.func, aliases)
		if rel == PROCESS_RUNNER_FILE and name == PROCESS_RUNNER_WRAPPER:
			keywords = {keyword.arg: keyword.value for keyword in node.keywords}
			violations.extend(
				violation(rel, node, f"{name} {problem}") for problem in cwd_env_problems(keywords, aliases)
			)
			continue
		if not name.startswith("subprocess.") or name.split(".")[-1] not in (
			*SUBPROCESS_RUN_FUNCTIONS,
			"Popen",
		):
			continue
		keywords = {keyword.arg: keyword.value for keyword in node.keywords}
		if name.split(".")[-1] not in SUBPROCESS_RUN_FUNCTIONS:
			violations.append(violation(rel, node, f"{name}: only run()-style calls with timeout"))
		if "timeout" not in keywords:
			violations.append(violation(rel, node, f"{name} without timeout="))
		shell = keywords.get("shell")
		if shell is not None and not (isinstance(shell, ast.Constant) and shell.value is False):
			violations.append(violation(rel, node, f"{name} with shell="))
		command = node.args[0] if node.args else keywords.get("args")
		if isinstance(command, ast.Constant | ast.JoinedStr):
			violations.append(violation(rel, node, f"{name} with a string command, not a list"))
		if rel == PROCESS_RUNNER_FILE or is_timeout_wrapped(command):
			violations.extend(
				violation(rel, node, f"{name} {problem}")
				for problem in timeout_wrapped_call_problems(keywords, aliases)
			)
	return violations


def is_timeout_wrapped(command) -> bool:
	"""ADR-022 QĐ 4: a `[TIMEOUT_EXECUTABLE, ...]` / `["timeout", ...]` command is a new FEAT-004 git call."""
	first = command.elts[0] if isinstance(command, ast.List) and command.elts else None
	return (isinstance(first, ast.Name) and first.id == "TIMEOUT_EXECUTABLE") or (
		isinstance(first, ast.Constant) and first.value == "timeout"
	)


def timeout_wrapped_call_problems(keywords: dict, aliases: dict) -> list:
	"""Own process group, explicit cwd= and an env= that never copies os.environ (ADR-022 QĐ 4, Ràng buộc)."""
	problems = []
	group = keywords.get("start_new_session")
	if not (isinstance(group, ast.Constant) and group.value is True):
		problems.append("without start_new_session=True")
	return problems + cwd_env_problems(keywords, aliases)


def cwd_env_problems(keywords: dict, aliases: dict) -> list:
	"""An explicit cwd= and an env= that never copies os.environ (ADR-022 QĐ 4; design 8.2)."""
	problems = []
	if "cwd" not in keywords:
		problems.append("without cwd=")
	env = keywords.get("env")
	if env is None:
		problems.append("without env=")
	elif any(resolved_name(part, aliases) == "os.environ" for part in ast.walk(env)):
		problems.append("env= uses os.environ")
	return problems


def check_policy_fields_only_in_policy(sources: dict) -> list:
	"""ADR-003/ADR-005: level and send-policy fields are read only by agent/policy.py."""
	violations = []
	for rel, source in only_python(sources).items():
		if rel in (POLICY_FILE, SETTING_CONTROLLER_FILE):
			continue  # the controller of ERP AI Setting owns its own fields (INT_LIMITS, validation)
		tree = parse(rel, source)
		aliases = import_aliases(tree)
		for node in ast.walk(tree):
			name = referenced_name(node)
			if name in POLICY_FIELDS:
				if resolved_name(node, aliases) == f"{module_name(POLICY_FILE)}.{name}":
					continue  # `policy.auto_assign_enabled(...)` is the function of policy.py, not a field read
				violations.append(violation(rel, node, f"reads {name} outside {POLICY_FILE}"))
			elif isinstance(node, ast.Constant) and node.value in POLICY_FIELDS:
				violations.append(violation(rel, node, f"reads {node.value!r} outside {POLICY_FILE}"))
	return violations


ORDERING_OPS = (ast.Lt, ast.LtE, ast.Gt, ast.GtE)
CONFIDENCE_EXACT_NAMES = ("threshold", "do_tin_cay_pct")
CONFIDENCE_RANGE_BOUNDS = ("CONFIDENCE_PCT_MIN", "CONFIDENCE_PCT_MAX")
SPEND_NAMES = ("spent_this_month_usd", "monthly_budget_usd", "month_spend_usd")


def operand_names(node) -> set:
	"""referenced_name of every Name/Attribute inside one compare operand, plus every str Constant inside it."""
	names = set()
	for child in ast.walk(node):
		name = referenced_name(child)
		if name:
			names.add(name)
		elif isinstance(child, ast.Constant) and isinstance(child.value, str):
			names.add(child.value)
	return names


def ordering_compares(tree: ast.AST):
	"""Every Compare node with at least one <, <=, >, >= (is/in/==/!= alone are not a threshold or budget decision)."""
	for node in ast.walk(tree):
		if isinstance(node, ast.Compare) and any(isinstance(op, ORDERING_OPS) for op in node.ops):
			yield node


def is_confidence_name(name: str) -> bool:
	lowered = name.lower()
	return (
		lowered in CONFIDENCE_EXACT_NAMES
		or "confidence_threshold" in lowered
		or lowered.endswith("confidence_pct")
	)


def check_threshold_compared_only_in_policy(sources: dict) -> list:
	"""ADR-030 QĐ 4: a confidence value is compared with a threshold only in agent/policy.py."""
	violations = []
	for rel, source in only_python(sources).items():
		if rel == POLICY_FILE:
			continue
		for compare in ordering_compares(parse(rel, source)):
			operands = [compare.left, *compare.comparators]
			matched = [o for o in operands if any(is_confidence_name(n) for n in operand_names(o))]
			if not matched:
				continue
			others = [o for o in operands if all(o is not m for m in matched)]
			if (
				len(matched) == 1
				and others
				and all(referenced_name(o) in CONFIDENCE_RANGE_BOUNDS for o in others)
			):
				continue  # range check of a parsed pct against its declared bounds (classification.py)
			name = sorted(n for n in operand_names(matched[0]) if is_confidence_name(n))[0]
			violations.append(violation(rel, compare, f"compares {name} outside {POLICY_FILE}"))
	return violations


def check_no_spent_comparison_outside_policy(sources: dict) -> list:
	"""AC-61, ADR-030: spend is compared with the budget only in agent/policy.py (policy.is_over_budget)."""
	violations = []
	for rel, source in only_python(sources).items():
		if rel == POLICY_FILE:
			continue
		for compare in ordering_compares(parse(rel, source)):
			for operand in [compare.left, *compare.comparators]:
				names = sorted(operand_names(operand) & set(SPEND_NAMES))
				if names:
					violations.append(violation(rel, compare, f"compares {names[0]} outside {POLICY_FILE}"))
					break
	return violations


def check_handlers_imports(sources: dict) -> list:
	"""handlers.py must not import gateway or runner (the layer rule for scope erp_ai.handlers)."""
	rules = tuple(rule for rule in LAYER_RULES if rule[0] == "erp_ai.handlers")
	return check_layer_imports({rel: src for rel, src in sources.items() if rel == HANDLERS_FILE}, rules)


def _identifiers(node) -> set:
	found = set()
	for child in ast.walk(node):
		name = referenced_name(child)
		if name:
			found.add(name)
	return found


def _has_explicit_message(call: ast.Call) -> bool:
	"""`log_error(title, message)` or `log_error(title, message=...)`; a missing, None or empty message is not."""
	message = call.args[1] if len(call.args) >= 2 else None
	if message is None:
		message = next((keyword.value for keyword in call.keywords if keyword.arg == "message"), None)
	if message is None:
		return False
	return not (isinstance(message, ast.Constant) and not message.value)


def check_secret_handling(sources: dict) -> list:
	"""NFR-5/ADR-002: password reads only in gateway/credentials.py; no key in logs; no local-var tracebacks."""
	violations = []
	for rel, source in only_python(sources).items():
		for node in ast.walk(parse(rel, source)):
			name = referenced_name(node)
			if name in SECRET_READERS and rel != CREDENTIALS_FILE:
				violations.append(violation(rel, node, f"{name} outside {CREDENTIALS_FILE}"))
			elif isinstance(node, ast.alias) and node.name in SECRET_READERS and rel != CREDENTIALS_FILE:
				violations.append(violation(rel, node, f"imports {node.name} outside {CREDENTIALS_FILE}"))
			if not isinstance(node, ast.Call):
				continue
			call_name = dotted_name(node.func) or ""
			if call_name.endswith("get_traceback") and any(
				keyword.arg == "with_context"
				and not (isinstance(keyword.value, ast.Constant) and keyword.value.value is False)
				for keyword in node.keywords
			):
				violations.append(
					violation(rel, node, "get_traceback(with_context=...) leaks local variables")
				)
			if call_name.split(".")[-1] == "log_error" and not _has_explicit_message(node):
				violations.append(
					violation(
						rel,
						node,
						"log_error without an explicit message (frappe then logs get_traceback(with_context=True))",
					)
				)
			is_sink = call_name in LOG_SINK_CALLS or call_name.split(".")[-1] in LOG_SINK_METHODS
			if is_sink:
				arguments = [*node.args, *(keyword.value for keyword in node.keywords)]
				leaked = set().union(*(_identifiers(argument) for argument in arguments)) & set(SECRET_NAMES)
				if leaked:
					violations.append(violation(rel, node, f"{call_name} is given {sorted(leaked)}"))
	return violations


def _allowed_legacy_nodes(rel: str, tree: ast.AST, allowlist: dict = LEGACY_ALLOWED_ASSIGNMENTS) -> set:
	target = allowlist.get(rel)
	allowed = set()
	for node in ast.walk(tree):
		if isinstance(node, ast.Assign) and any(
			isinstance(t, ast.Name) and t.id == target for t in node.targets
		):
			allowed.update(id(child) for child in ast.walk(node.value))
	return allowed


def _legacy_pattern(name: str):
	return re.compile(rf"(?<![A-Za-z0-9_]){re.escape(name)}(?![A-Za-z0-9_])")


def check_no_legacy_ticket_comment(sources: dict) -> list:
	"""D8 / design amendment 1f: no HD Ticket Comment, no spoofable author fields in product code."""
	patterns = [(name, _legacy_pattern(name)) for name in LEGACY_NAMES]
	violations = []
	for rel, source in sources.items():
		if not rel.endswith(".py"):
			for number, line in enumerate(source.splitlines(), start=1):
				violations.extend(
					f"{rel}:{number}: mentions {name}" for name, pattern in patterns if pattern.search(line)
				)
			continue
		tree = parse(rel, source)
		allowed = _allowed_legacy_nodes(rel, tree)
		for node in ast.walk(tree):
			if id(node) in allowed:
				continue
			if isinstance(node, ast.Constant) and isinstance(node.value, str):
				texts = [node.value]
			elif isinstance(node, ast.keyword) and node.arg:
				texts = [node.arg]
			elif referenced_name(node):
				texts = [referenced_name(node)]
			else:
				continue
			violations.extend(
				violation(rel, node, f"mentions {name}")
				for name, pattern in patterns
				if any(pattern.search(text) for text in texts)
			)
	return violations


def check_no_frappe_skipped_test_files(rel_paths) -> list:
	"""D-34: no file, at any depth, is named like a file Frappe skips when collecting tests."""
	return [
		f"{rel}: file name {Path(rel).name} is skipped by Frappe's test runner, rename it"
		for rel in rel_paths
		if Path(rel).name in FRAPPE_SKIPPED_TEST_FILENAMES
	]


def check_ci_workflow(text: str) -> list:
	"""D-23: bench init on version-15; helpdesk v15.1.0, erpnext version-15, telephony installed before erp_ai."""
	violations = []
	commands = []
	for number, raw in enumerate(text.splitlines(), start=1):
		line = raw.strip()
		if line.startswith("bench "):
			try:
				commands.append((number, shlex.split(line)))
			except ValueError:
				violations.append(f"ci.yml:{number}: cannot parse {line!r}")

	def option(tokens, flag):
		for index, token in enumerate(tokens):
			if token == flag and index + 1 < len(tokens):
				return tokens[index + 1]
			if token.startswith(flag + "="):
				return token.split("=", 1)[1]
		return None

	def first(predicate):
		return next((number for number, tokens in commands if predicate(tokens)), None)

	init_line = first(
		lambda t: t[:2] == ["bench", "init"] and option(t, "--frappe-branch") == CI_BENCH_BRANCH
	)
	if init_line is None:
		violations.append(f"ci.yml: no `bench init --frappe-branch {CI_BENCH_BRANCH}`")
	erp_install = first(lambda t: "install-app" in t and t[-1] == "erp_ai")
	if erp_install is None:
		violations.append("ci.yml: no `install-app erp_ai`")
	for app, branch in CI_REQUIRED_APPS:
		get_line = first(
			lambda t, app=app, branch=branch: t[:2] == ["bench", "get-app"]
			and app in t
			and (branch is None or option(t, "--branch") == branch)
		)
		install_line = first(lambda t, app=app: "install-app" in t and t[-1] == app)
		if get_line is None:
			violations.append(f"ci.yml: no `bench get-app {app}`" + (f" --branch {branch}" if branch else ""))
		if install_line is None:
			violations.append(f"ci.yml: no `install-app {app}`")
		if get_line and install_line and get_line > install_line:
			violations.append(f"ci.yml: get-app {app} comes after install-app {app}")
		if install_line and erp_install and install_line > erp_install:
			violations.append(f"ci.yml: install-app {app} comes after install-app erp_ai")
	return violations


# ---------------------------------------------------------------------------------------------------
# Tests on the real tree
# ---------------------------------------------------------------------------------------------------


def _call_keywords(call: ast.Call) -> dict:
	return {kw.arg: kw.value for kw in call.keywords if kw.arg}


def _is_constant(node, value) -> bool:
	return isinstance(node, ast.Constant) and node.value == value and type(node.value) is type(value)


def check_publish_realtime_only_in_run_status(sources: dict) -> list:
	"""ADR-008: only run_status.py touches frappe.realtime; its publish calls pin `room=` and `after_commit=False`."""
	violations = []
	for rel, source in only_python(sources).items():
		tree = parse(rel, source)
		aliases = import_aliases(tree)
		if rel != RUN_STATUS_FILE:
			for node in ast.walk(tree):
				if referenced_name(node) in REALTIME_NAMES:
					violations.append(
						violation(rel, node, f"uses {referenced_name(node)} outside {RUN_STATUS_FILE}")
					)
				elif isinstance(node, ast.ImportFrom):
					for alias in node.names:
						if alias.name in REALTIME_NAMES:
							violations.append(
								violation(rel, node, f"imports {alias.name} outside {RUN_STATUS_FILE}")
							)
				elif (
					isinstance(node, ast.Name | ast.Attribute)
					and resolved_name(node, aliases) == REALTIME_MODULE
				):
					violations.append(
						violation(rel, node, f"uses {REALTIME_MODULE} outside {RUN_STATUS_FILE}")
					)
				elif isinstance(node, ast.Constant) and isinstance(node.value, str):
					# getattr(frappe, "publish_realtime"), frappe.get_attr("frappe.realtime..."), import_module(...)
					for name in (*REALTIME_NAMES, REALTIME_MODULE):
						if name in node.value:
							violations.append(
								violation(rel, node, f"names {name} in a string outside {RUN_STATUS_FILE}")
							)
			for lineno, target in imported_modules(tree, module_name(rel), rel.endswith("__init__.py")):
				if module_in(target, REALTIME_MODULE):
					violations.append(f"{rel}:{lineno}: imports {target} outside {RUN_STATUS_FILE}")
			continue
		called = set()
		for node in ast.walk(tree):
			if (
				isinstance(node, ast.Call)
				and resolved_name(node.func, aliases).rpartition(".")[2] == "publish_realtime"
			):
				called.add(id(node.func))
				keywords = _call_keywords(node)
				if "room" not in keywords:
					violations.append(violation(rel, node, "publish_realtime without an explicit room="))
				if not _is_constant(keywords.get("after_commit"), False):
					violations.append(violation(rel, node, "publish_realtime without after_commit=False"))
		for node in ast.walk(tree):
			# any other mention (alias import, `publish = frappe.publish_realtime`) hides calls from the check above
			if (referenced_name(node) == "publish_realtime" and id(node) not in called) or (
				isinstance(node, ast.alias) and node.name == "publish_realtime" and node.asname
			):
				violations.append(violation(rel, node, "binds publish_realtime to another name"))
	return violations


def check_run_status_imported_only_by_runner(sources: dict) -> list:
	"""ADR-008 decision 2: tools, handlers, tasks, gateway and eval never import the status module."""
	violations = []
	for rel, source in only_python(sources).items():
		# CHG-018: `messages` announces a new message through `announce_message`.
		if rel in (RUNNER_FILE, RUN_STATUS_FILE, "agent/messages.py"):
			continue
		tree = parse(rel, source)
		for lineno, target in imported_modules(tree, module_name(rel), rel.endswith("__init__.py")):
			if module_in(target, RUN_STATUS_MODULE):
				violations.append(f"{rel}:{lineno}: imports {target}; only {RUNNER_FILE} may (ADR-008)")
		for node in constant_strings(tree):
			if RUN_STATUS_MODULE in node.value:
				violations.append(
					violation(rel, node, f"names {RUN_STATUS_MODULE}; only {RUNNER_FILE} may (ADR-008)")
				)
	return violations


def check_run_status_writes_nothing(sources: dict) -> list:
	"""NFR-6, ADR-008 decision 5: the status module writes no record, cache entry, file or transaction state."""
	source = sources.get(RUN_STATUS_FILE)
	if source is None:
		return []
	violations = []
	tree = parse(RUN_STATUS_FILE, source)
	aliases = import_aliases(tree)
	for node in ast.walk(tree):
		if isinstance(node, ast.Call) and referenced_name(node.func) in RUN_STATUS_WRITE_NAMES:
			violations.append(
				violation(RUN_STATUS_FILE, node, f"calls {referenced_name(node.func)}: writes (NFR-6)")
			)
		elif (
			isinstance(node, ast.Name | ast.Attribute)
			and resolved_name(node, aliases) in RUN_STATUS_FORBIDDEN_ATTRIBUTES
		):
			violations.append(
				violation(RUN_STATUS_FILE, node, f"uses {resolved_name(node, aliases)}: writes (NFR-6)")
			)
	for lineno, target in imported_modules(tree, module_name(RUN_STATUS_FILE), False):
		if module_in(target, "erp_ai.gateway"):
			violations.append(f"{RUN_STATUS_FILE}:{lineno}: imports {target} (ADR-008)")
	return violations


def check_no_open_doc_or_all_room(sources: dict) -> list:
	"""R-1: no `open_doc:` room, no room="all" and no publish without an explicit room."""
	violations = []
	for rel, source in sources.items():
		if not rel.endswith(".py"):
			if OPEN_DOC_ROOM_PREFIX in source:
				violations.append(f"{rel}:0: contains {OPEN_DOC_ROOM_PREFIX} (R-1)")
			continue
		tree = parse(rel, source)
		aliases = import_aliases(tree)
		constants = {
			target.id: node.value.value
			for node in tree.body
			if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant)
			for target in node.targets
			if isinstance(target, ast.Name)
		}
		for node in constant_strings(tree):
			if OPEN_DOC_ROOM_PREFIX in node.value:
				violations.append(violation(rel, node, f"contains {OPEN_DOC_ROOM_PREFIX} (R-1)"))
		for node in ast.walk(tree):
			if (
				isinstance(node, ast.Call)
				and resolved_name(node.func, aliases).rpartition(".")[2] in REALTIME_NAMES
			):
				room = _call_keywords(node).get("room")
				if (
					room is None
					or _is_constant(room, None)
					or _is_constant(room, ALL_ROOM)
					or (
						isinstance(room, ast.Name)
						and room.id in constants
						and constants[room.id] in (None, ALL_ROOM)
					)
				):
					violations.append(
						violation(rel, node, "publishes without a document room or to room all (R-1)")
					)
	return violations


def check_form_script_only_in_install(sources: dict) -> list:
	"""ADR-007: the HD Form Script doctype is named only by install.py."""
	violations = []
	for rel, source in sources.items():
		if rel == INSTALL_FILE:
			continue
		if not rel.endswith(".py"):
			if FORM_SCRIPT_DOCTYPE_NAME in source:
				violations.append(
					f"{rel}:0: names {FORM_SCRIPT_DOCTYPE_NAME} outside {INSTALL_FILE} (ADR-007)"
				)
			continue
		tree = parse(rel, source)
		for node in constant_strings(tree):
			if FORM_SCRIPT_DOCTYPE_NAME in node.value:
				violations.append(
					violation(rel, node, f"names {FORM_SCRIPT_DOCTYPE_NAME} outside {INSTALL_FILE} (ADR-007)")
				)
		for lineno, target in imported_modules(tree, module_name(rel), rel.endswith("__init__.py")):
			if "hd_form_script" in target:
				violations.append(f"{rel}:{lineno}: imports {target} outside {INSTALL_FILE} (ADR-007)")
	return violations


def check_hooks_have_no_page_injection(sources: dict) -> list:
	"""ADR-007: hooks.py injects nothing into the page; the status script is not referenced there."""
	source = sources.get(HOOKS_FILE)
	if source is None:
		return []
	violations = []
	tree = parse(HOOKS_FILE, source)
	for node in tree.body:
		targets = node.targets if isinstance(node, ast.Assign) else [getattr(node, "target", None)]
		for target in targets:
			if isinstance(target, ast.Name) and target.id in PAGE_INJECTION_HOOKS:
				value = getattr(node, "value", None)
				strings = [n.value for n in constant_strings(value)] if value is not None else []
				if target.id == "fixtures" and not any(FORM_SCRIPT_DOCTYPE_NAME in text for text in strings):
					continue
				if target.id == "website_route_rules" and not any("helpdesk" in text for text in strings):
					continue
				violations.append(
					violation(HOOKS_FILE, node, f"sets {target.id} (ADR-007: no page injection)")
				)
	for node in constant_strings(tree):
		if "agent_status_indicator" in node.value or AGENT_STATUS_SCRIPT_NAME in node.value:
			violations.append(violation(HOOKS_FILE, node, "references the status script (ADR-007)"))
	return violations


def check_install_deletes_only_status_script(sources: dict) -> list:
	"""ADR-007 decision 4: install.py has exactly one delete, in before_uninstall, of the status script record."""
	source = sources.get(INSTALL_FILE)
	if source is None:
		return []
	tree = parse(INSTALL_FILE, source)
	constants = {}
	for node in tree.body:
		if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant):
			for target in node.targets:
				if isinstance(target, ast.Name):
					constants[target.id] = node.value.value

	def resolve(arg):
		if isinstance(arg, ast.Constant):
			return arg.value
		return constants.get(arg.id) if isinstance(arg, ast.Name) else None

	owners = {}
	for function in ast.walk(tree):
		if isinstance(function, ast.FunctionDef | ast.AsyncFunctionDef):
			for node in ast.walk(function):
				owners[id(node)] = function.name
	violations = []
	deletes = []
	for node in ast.walk(tree):
		if isinstance(node, ast.Call) and referenced_name(node.func) in DELETE_NAMES:
			deletes.append(node)
		elif isinstance(node, ast.Constant) and isinstance(node.value, str) and SQL_DELETE.match(node.value):
			violations.append(violation(INSTALL_FILE, node, "SQL delete in install code (ADR-007)"))
	if len(deletes) != 1:
		violations.append(f"{INSTALL_FILE}:0: expected exactly one delete, found {len(deletes)} (ADR-007)")
	for call in deletes:
		if owners.get(id(call)) != UNINSTALL_FUNCTION:
			violations.append(violation(INSTALL_FILE, call, f"delete outside {UNINSTALL_FUNCTION} (ADR-007)"))
		args = [resolve(arg) for arg in call.args[:2]]
		if referenced_name(call.func) != "delete_doc" or args != [
			FORM_SCRIPT_DOCTYPE_NAME,
			AGENT_STATUS_SCRIPT_NAME,
		]:
			violations.append(
				violation(
					INSTALL_FILE,
					call,
					f"delete must be delete_doc of {FORM_SCRIPT_DOCTYPE_NAME} {AGENT_STATUS_SCRIPT_NAME}",
				)
			)
	return violations


# ---------------------------------------------------------------------------------------------------
# FEAT-003 (ADR-009, ADR-010 Amendment 1): the ticket-page panel script and the two whitelisted methods
# ---------------------------------------------------------------------------------------------------

PANEL_FILE = "ticket_panel.py"
PANEL_MODULE = "erp_ai.ticket_panel"
STATUS_SCRIPT_STATE_NAME = "__erpAiAgentStatus"
STATUS_SCRIPT_ONCE_BLOCK = "if (state.socket !== socket) {"
STATUS_SCRIPT_SOCKET_EVENTS = ("docinfo_update", "doc_update", "connect", "disconnect")
STATUS_SCRIPT_QUERY_CALLS = re.compile(r"\b(querySelector(?:All)?|getElementById|getElementsBy\w+)\(")
STATUS_SCRIPT_ALLOWED_QUERIES = {"querySelector": "#app", "getElementById": "app"}
# ADR-010 Amendment 1 (read writes nothing, one message call: `messages.add_message`, no Comment) and Decision 8 (no agent gates in the panel).
PANEL_FORBIDDEN_NAMES = frozenset(
	{
		"ignore_permissions",
		"set_user",
		"get_all",
		"get_values",
		"sql",
		"set_value",
		"db_set",
		"insert",
		"save",
		"commit",
		"rollback",
		"cache",
		"publish_realtime",
		"new_comment",
	}
)
PANEL_FORBIDDEN_PREFIXES = ("delete",)
PANEL_SEND_FUNCTION = "send_message"
PANEL_COMMENT_CALL = "add_message"
PANEL_GATE_NAMES = (
	"is_enabled",
	"can_send_ticket",
	"effective_level",
	"runs_today",
	"enqueue",
	"permission_level",
	"excluded_teams",
	"ai_opt_out",
)


def mask_js(script: str) -> str:
	"""The script with comments and the inside of string literals blanked (same length, newlines kept), so
	positions and braces can be found without matching text that sits in a string or a comment."""
	out = []
	i, n = 0, len(script)
	while i < n:
		ch = script[i]
		pair = script[i : i + 2]
		if pair == "//":
			end = script.find("\n", i)
			end = n if end == -1 else end
			out.append(" " * (end - i))
			i = end
		elif pair == "/*":
			end = script.find("*/", i + 2)
			end = n if end == -1 else end + 2
			out.append("".join(c if c == "\n" else " " for c in script[i:end]))
			i = end
		elif ch in "\"'`":
			j = i + 1
			while j < n and script[j] != ch:
				j += 2 if script[j] == "\\" else 1
			out.append(ch + "".join(c if c == "\n" else " " for c in script[i + 1 : j]) + script[j : j + 1])
			i = j + 1
		else:
			out.append(ch)
			i += 1
	return "".join(out)


def js_line(script: str, offset: int) -> int:
	return script.count("\n", 0, offset) + 1


def whitelisted_functions(sources: dict) -> list:
	"""`[(rel, function node, decorator node)]` for every function decorated with `frappe.whitelist`."""
	found = []
	for rel, source in only_python(sources).items():
		tree = parse(rel, source)
		aliases = import_aliases(tree)
		for node in ast.walk(tree):
			if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
				continue
			for decorator in node.decorator_list:
				target = decorator.func if isinstance(decorator, ast.Call) else decorator
				if resolved_name(target, aliases) == "frappe.whitelist":
					found.append((rel, node, decorator))
	return found


def whitelisted_paths(sources: dict) -> set:
	return {f"{module_name(rel)}.{node.name}" for rel, node, _decorator in whitelisted_functions(sources)}


def check_call_allow_list(script: str, allowed_methods, sources: dict) -> list:
	"""ADR-009: the literals passed to `call(` are exactly the allowed methods, each a whitelisted function."""
	violations = check_status_script_calls(script, allowed_methods)
	literals = {m.group(2) for m in STATUS_SCRIPT_CALL.finditer(script) if m.group(1) is not None}
	for missing in sorted(set(allowed_methods) - literals):
		violations.append(f"{missing} is in PANEL_METHODS but the script never calls it")
	paths = whitelisted_paths(sources)
	for literal in sorted(literals):
		if literal not in paths:
			violations.append(f"{literal} does not point to a @frappe.whitelist function")
	return violations


def check_status_script_queries(script: str) -> list:
	"""ADR-009: element lookups only for the Vue root (`#app`), never into Helpdesk's own DOM."""
	violations = []
	masked = mask_js(script)
	for match in STATUS_SCRIPT_QUERY_CALLS.finditer(masked):
		line = js_line(script, match.start())
		argument = re.match(r"\s*([\"'])(.*?)\1\s*\)", script[match.end() :])
		if argument is None or STATUS_SCRIPT_ALLOWED_QUERIES.get(match.group(1)) != argument.group(2):
			violations.append(f"line {line}: {match.group(1)}( is only allowed with the Vue root (#app)")
	return violations


def check_status_script_window_state(script: str) -> list:
	"""ADR-009: one `window.__erpAi…` state object and no other property written on `window`."""
	violations = []
	names = set(re.findall(r"__erpAi\w*", script))
	if names != {STATUS_SCRIPT_STATE_NAME}:
		violations.append(f"window state names are {sorted(names)}, expected only {STATUS_SCRIPT_STATE_NAME}")
	masked = mask_js(script)
	for match in re.finditer(r"\bwindow\.(\w+)\s*=(?!=)", masked):
		if match.group(1) != STATUS_SCRIPT_STATE_NAME:
			violations.append(f"line {js_line(script, match.start())}: window.{match.group(1)} is written")
	for match in re.finditer(r"\bwindow\s*\[", masked):
		violations.append(f"line {js_line(script, match.start())}: window[...] access hides a second state")
	return violations


def _matching_brace(masked: str, open_at: int) -> int:
	depth = 0
	for i in range(open_at, len(masked)):
		if masked[i] == "{":
			depth += 1
		elif masked[i] == "}":
			depth -= 1
			if depth == 0:
				return i
	return -1


def socket_on_registrations(script: str) -> list:
	"""`[(line, inside the once-per-socket block, event name or None)]` for every `.on(` call."""
	masked = mask_js(script)
	start = masked.find(STATUS_SCRIPT_ONCE_BLOCK)
	block = (-1, -1)
	if start != -1:
		open_at = start + len(STATUS_SCRIPT_ONCE_BLOCK) - 1
		block = (open_at, _matching_brace(masked, open_at))
	declared = re.search(r"const EVENT = \"([^\"]*)\"", script)
	found = []
	for match in re.finditer(r"\.on\(", masked):
		argument = re.match(r"\s*(?:\"([^\"]*)\"|([A-Za-z_$][\w$]*))", script[match.end() :])
		name = None
		if argument is not None and argument.group(1) is not None:
			name = argument.group(1)
		elif argument is not None and argument.group(2) == "EVENT" and declared:
			name = declared.group(1)
		inside = block[0] < match.start() < block[1]
		found.append((js_line(script, match.start()), inside, name))
	return found


def check_socket_on_only_in_once_block(script: str, status_event: str) -> list:
	"""ADR-009: every `.on(` sits in the `if (state.socket !== socket)` block and names an allowed event."""
	violations = []
	if mask_js(script).find(STATUS_SCRIPT_ONCE_BLOCK) == -1:
		violations.append(f"the once-per-socket block {STATUS_SCRIPT_ONCE_BLOCK} is missing")
	allowed = {status_event, *STATUS_SCRIPT_SOCKET_EVENTS}
	for line, inside, name in socket_on_registrations(script):
		if not inside:
			violations.append(f"line {line}: .on( is outside the once-per-socket block")
		if name not in allowed:
			violations.append(f"line {line}: event {name!r} is not one of {sorted(allowed)}")
	return violations


def _js_arrow_body_span(masked: str, name: str):
	"""`(start, end)` of the body of `const <name> = (...) => { … }` in the masked script, or None."""
	match = re.search(rf"\bconst {name} = \([^)]*\) => \{{", masked)
	if not match:
		return None
	end = _matching_brace(masked, match.end() - 1)
	return None if end == -1 else (match.end(), end)


def check_status_indicator_hides(script: str) -> list:
	"""BUG-003: Helpdesk's `[hidden]{display:none}` loses to an inline `display`, so the indicator is shown and
	hidden only through one helper that writes `hidden` and `style.display` together."""
	violations = []
	masked = mask_js(script)
	helper = STATUS_INDICATOR_VISIBILITY
	span = _js_arrow_body_span(masked, helper)
	if span is None:
		violations.append(f"{helper} is missing")
	else:
		body = script[span[0] : span[1]]
		for required in ("el.hidden = !visible;", 'el.style.display = visible ? "flex" : "none";'):
			if required not in body:
				violations.append(f"{helper} does not write {required}")
	spans = {}
	for name in STATUS_INDICATOR_FUNCTIONS:
		spans[name] = _js_arrow_body_span(masked, name)
		if spans[name] is None:
			violations.append(f"function {name} is missing")
			continue
		start, end = spans[name]
		for match in re.finditer(r"\.hidden\s*=(?!=)", masked[start:end]):
			violations.append(
				f"line {js_line(script, start + match.start())}: {name} sets hidden without display,"
				" an inline display keeps the indicator on screen"
			)
		for match in STATUS_INDICATOR_DISPLAY_WRITE.finditer(masked[start:end]):
			violations.append(
				f"line {js_line(script, start + match.start())}: {name} writes display outside {helper}"
			)
	if spans.get("render"):
		body = masked[spans["render"][0] : spans["render"][1]]
		if not re.search(
			rf"if \(state\.runs\.size === 0\) \{{\s*{helper}\(el, false\);\s*return;\s*\}}", body
		):
			violations.append("render does not hide the indicator when no run is active")
		if not body.rstrip().endswith(f"{helper}(el, true);"):
			violations.append(f"render does not end with {helper}(el, true)")
	if spans.get("ensureElement"):
		body = masked[spans["ensureElement"][0] : spans["ensureElement"][1]]
		hide_at = body.rfind(f"{helper}(el, false)")
		if hide_at == -1 or hide_at < body.rfind("Object.assign(el.style"):
			violations.append("ensureElement does not hide the new indicator after its inline style")
	for name, call in (("render", "(el, false)"), ("render", "(el, true)"), ("reset", "(state.el, false)")):
		if spans.get(name) and f"{helper}{call}" not in masked[spans[name][0] : spans[name][1]]:
			violations.append(f"{name} does not call {helper}{call}")
	for const in ("INDICATOR_FLOATING_STYLE", "INDICATOR_DOCKED_STYLE"):
		match = re.search(rf"\bconst {const} = \{{", masked)
		if not match:
			violations.append(f"{const} is missing")
		elif re.search(r"\bdisplay\s*:", masked[match.end() : _matching_brace(masked, match.end() - 1)]):
			violations.append(f"{const} sets display, docking would show a hidden indicator")
	return violations


def check_whitelisted_methods_declare_http_methods(sources: dict) -> list:
	"""ADR-010: every `@frappe.whitelist` in the app names its HTTP methods and never allows guests."""
	violations = []
	for rel, node, decorator in whitelisted_functions(sources):
		if not isinstance(decorator, ast.Call):
			violations.append(
				violation(rel, decorator, f"{node.name}: bare @frappe.whitelist, methods= missing")
			)
			continue
		keywords = {kw.arg: kw.value for kw in decorator.keywords}
		if "allow_guest" in keywords:
			violations.append(violation(rel, decorator, f"{node.name}: allow_guest is not allowed"))
		methods = keywords.get("methods")
		if not (
			isinstance(methods, ast.List | ast.Tuple)
			and methods.elts
			and all(isinstance(e, ast.Constant) and isinstance(e.value, str) for e in methods.elts)
		):
			violations.append(violation(rel, decorator, f"{node.name}: methods= must list HTTP methods"))
	return violations


def check_ticket_panel_whitelist(sources: dict, expected=PANEL_METHODS) -> list:
	"""ADR-010 Amendment 1, ADR-044 QĐ 1: exactly the panel methods of `PANEL_METHODS` (read, send, decide), each
	`methods=["POST"]` and nothing else."""
	if PANEL_FILE not in sources:
		return [f"{PANEL_FILE} is missing"]
	violations = []
	own = whitelisted_functions({PANEL_FILE: sources[PANEL_FILE]})
	paths = sorted(f"{PANEL_MODULE}.{node.name}" for _rel, node, _decorator in own)
	if paths != sorted(expected):
		violations.append(f"whitelisted functions are {paths}, expected {sorted(expected)}")
	for rel, node, decorator in own:
		methods = None
		if isinstance(decorator, ast.Call):
			methods = {kw.arg: kw.value for kw in decorator.keywords}.get("methods")
		values = (
			[e.value if isinstance(e, ast.Constant) else None for e in methods.elts]
			if isinstance(methods, ast.List | ast.Tuple)
			else None
		)
		if values != ["POST"]:
			violations.append(violation(rel, decorator, f'{node.name}: methods must be exactly ["POST"]'))
	return violations


def _panel_identifiers(tree: ast.AST):
	"""`(node, name)` for every identifier-like use: names, attributes, keyword names, imported names."""
	for node in ast.walk(tree):
		if isinstance(node, ast.Name):
			yield node, node.id
		elif isinstance(node, ast.Attribute):
			yield node, node.attr
		elif isinstance(node, ast.keyword) and node.arg:
			yield node, node.arg
		elif isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
			yield node, node.name
		elif isinstance(node, ast.Import | ast.ImportFrom):
			for alias in node.names:
				yield node, alias.name.rpartition(".")[2]


def _comment_calls(root: ast.AST) -> list:
	return [
		n
		for n in ast.walk(root)
		if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == PANEL_COMMENT_CALL
	]


def check_ticket_panel_forbidden_calls(sources: dict) -> list:
	"""ADR-010 Amendment 1: no permission bypass, user switch, raw query, write, commit, cache or realtime in
	the panel module; exactly one `.add_message(` and it sits in `send_message`."""
	if PANEL_FILE not in sources:
		return [f"{PANEL_FILE} is missing"]
	tree = parse(PANEL_FILE, sources[PANEL_FILE])
	violations = []
	for node, name in _panel_identifiers(tree):
		if name in PANEL_FORBIDDEN_NAMES or name.startswith(PANEL_FORBIDDEN_PREFIXES):
			violations.append(violation(PANEL_FILE, node, f"{name} is not allowed in the panel module"))
	for node in constant_strings(tree):
		if node.value in PANEL_FORBIDDEN_NAMES:
			violations.append(
				violation(PANEL_FILE, node, f"string {node.value!r} is not allowed in the panel")
			)
	total = _comment_calls(tree)
	if len(total) != 1:
		violations.append(
			f"{PANEL_FILE}: expected exactly one .{PANEL_COMMENT_CALL}( call, found {len(total)}"
		)
	send = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == PANEL_SEND_FUNCTION]
	if len(send) != 1 or len(_comment_calls(send[0])) != 1:
		violations.append(
			f"{PANEL_FILE}: the one .{PANEL_COMMENT_CALL}( call must be inside {PANEL_SEND_FUNCTION}"
		)
	return violations


def check_ticket_panel_does_not_evaluate_agent_gates(sources: dict) -> list:
	"""ADR-010 Decision 8: the panel never evaluates the agent's gates (the comment handler and runner do)."""
	if PANEL_FILE not in sources:
		return [f"{PANEL_FILE} is missing"]
	tree = parse(PANEL_FILE, sources[PANEL_FILE])
	violations = []
	for node, name in _panel_identifiers(tree):
		for gate in PANEL_GATE_NAMES:
			if gate in name:
				violations.append(violation(PANEL_FILE, node, f"{name} evaluates an agent gate ({gate})"))
	for node in constant_strings(tree):
		for gate in PANEL_GATE_NAMES:
			if re.search(rf"\b{gate}\b", node.value):
				violations.append(violation(PANEL_FILE, node, f"string mentions agent gate {gate}"))
	return violations


# ---------------------------------------------------------------------------------------------------
# FEAT-006 rules (ADR-019..021 "Ràng buộc", AC-7c, AC-10, AC-14)
# ---------------------------------------------------------------------------------------------------

ROUTE_FILE = "agent/tools/route_ticket.py"
ROUTE_MODULE_NAME = "route_ticket"
REGISTRY_FILE = "agent/tools/registry.py"
RUN_LOG_FILE = "agent/run_log.py"
LOG_DOCTYPE_FILE = "erp_ai_agent/doctype/erp_ai_log/erp_ai_log.json"
AUTHORITY_FILE = "agent/authority.py"
AGENT_PREFIX = "agent/"

ROUTE_NOT_A_TOOL_NAMES = ("TOOLS", "ToolSpec")
ROUTE_SAVE_FUNCTION = "apply_route"
ASSIGN_MODULE = "frappe.desk.form.assign_to"
ASSIGN_CALL_SUFFIXES = ("assign_to.add", "assign_to.add_multiple", "assign_agent")
ASSIGN_AGENT_NAME = "assign_agent"
ROUTE_WRITE_FUNCTIONS = ("apply_route", "assign_owner", "post_routing_comment", "create_routed_task")
TODO_DOCTYPE = "ToDo"
DOC_CREATE_CALLS = ("get_doc", "new_doc")
SHARE_BYPASS_NAMES = ("ignore_share_permission", "add_docshare")
SHARE_BYPASS_SUFFIXES = ("assign_to._add", "frappe.share.add")
# CHG-009 (ADR-048 QĐ 1): run_event added last.
ENTRY_TYPES_EXPECTED = ("classify", "reason", "skip", "change", "bot_action", "run_event")

# `_assign` is the denormalised JSON column of HD Ticket. Routing must read ToDo through site_facts instead.
# authority.py (FEAT-002, "who may instruct the bot") predates routing and is the one reader allowed.
ASSIGN_FIELD = re.compile(r"(?<![A-Za-z0-9])_assign(?![A-Za-z0-9_])")
ASSIGN_FIELD_ALLOWED_FILE = AUTHORITY_FILE
ASSIGN_FIELD_ALLOWED_FUNCTION = "_assigned_by_other"

SLA_DATE_FIELDS = ("response_by", "resolution_by")
SLA_WRITE_CALLS = ("setattr", "set", "set_value", "db_set", "update")

# Names of the people the old hard-coded routing table listed (spec 16.2), matched as whole words.
DEFAULT_PEOPLE = ("Việt", "Tiến", "Hiếu", "Lan", "Hà", "Thư", "Chi")
PERSON_NAME = re.compile(r"(?<!\w)(?:" + "|".join(DEFAULT_PEOPLE) + r")(?!\w)")
# Same letters, other meaning: "Việt Nam" (prompts.py), "Tiếng Việt" (prompts.py), "Thư mục" (tools/source.py).
NAME_COINCIDENCES = re.compile(r"(?<!\w)(?:Việt Nam|Tiếng Việt|Thư mục)(?!\w)")
# The bot's own account as a string literal; `erp_ai.agent...` module paths do not match (`_` is a word char).
AGENT_ACCOUNT = re.compile(r"(?<![\w.])ai\.agent(?!\w)")


def _missing(rel: str) -> list:
	return [f"{rel}: file missing"]


def _node_names(node) -> list:
	"""Every bare name a node carries: Name/Attribute, import alias, keyword argument, string constant."""
	names = []
	if (name := referenced_name(node)) is not None:
		names.append(name)
	if isinstance(node, ast.alias):
		names.append(node.name.split(".")[-1])
	elif isinstance(node, ast.keyword) and node.arg:
		names.append(node.arg)
	elif isinstance(node, ast.Constant) and isinstance(node.value, str):
		names.append(node.value)
	return names


def check_route_module_is_not_a_tool(sources: dict) -> list:
	"""ADR-019: route_ticket.py is no tool: no TOOLS / ToolSpec in it, not listed by the registry."""
	registry, route = sources.get(REGISTRY_FILE), sources.get(ROUTE_FILE)
	if registry is None:
		return _missing(REGISTRY_FILE)
	if route is None:
		return _missing(ROUTE_FILE)
	violations = []
	for node in constant_strings(parse(REGISTRY_FILE, registry)):
		if ROUTE_MODULE_NAME in node.value:
			violations.append(
				violation(REGISTRY_FILE, node, f"the registry lists {ROUTE_MODULE_NAME} (ADR-019)")
			)
	for node in ast.walk(parse(ROUTE_FILE, route)):
		for name in _node_names(node):
			if name in ROUTE_NOT_A_TOOL_NAMES and not isinstance(node, ast.Constant):
				violations.append(violation(ROUTE_FILE, node, f"{name} in the routing module (ADR-019)"))
	# No other tool module may expose a routing write function as a tool handler either.
	for rel, source in only_python(scoped(sources, TOOLS_PREFIX)).items():
		if rel == ROUTE_FILE:
			continue
		for node in ast.walk(parse(rel, source)):
			handlers = []
			if isinstance(node, ast.keyword) and node.arg == "handler":
				handlers.append(node.value)
			elif (
				isinstance(node, ast.Call) and referenced_name(node.func) == "ToolSpec" and len(node.args) > 3
			):
				handlers.append(node.args[3])
			for handler in handlers:
				if referenced_name(handler) in ROUTE_WRITE_FUNCTIONS:
					violations.append(
						violation(rel, handler, f"{referenced_name(handler)} is a tool handler (ADR-019)")
					)
	return violations


def check_route_module_single_ticket_save(sources: dict) -> list:
	"""ADR-020 QĐ 1/6: exactly one `.save()` in route_ticket.py, inside apply_route; no `db_update` at all."""
	route = sources.get(ROUTE_FILE)
	if route is None:
		return _missing(ROUTE_FILE)
	tree = parse(ROUTE_FILE, route)
	inside = set()
	for node in tree.body:
		if isinstance(node, ast.FunctionDef) and node.name == ROUTE_SAVE_FUNCTION:
			inside = {id(child) for child in ast.walk(node)}
	saves = [
		node
		for node in ast.walk(tree)
		if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "save"
	]
	violations = [
		violation(ROUTE_FILE, node, f"`.save()` outside {ROUTE_SAVE_FUNCTION} (ADR-020)")
		for node in saves
		if id(node) not in inside
	]
	if len(saves) != 1:
		violations.append(
			f"{ROUTE_FILE}: found {len(saves)} `.save()` calls, exactly one ticket save (ADR-020)"
		)
	violations.extend(
		violation(ROUTE_FILE, node, "`db_update` in the routing module (ADR-020)")
		for node in ast.walk(tree)
		if isinstance(node, ast.Call) and referenced_name(node.func) == "db_update"
	)
	return violations


def check_assign_to_only_in_route_module(sources: dict) -> list:
	"""ADR-021 QĐ 3 / ADR-015: `assign_to.add` is called only in route_ticket.py."""
	violations = []
	for rel, source in only_python(sources).items():
		if rel == ROUTE_FILE:
			continue
		tree = parse(rel, source)
		aliases = import_aliases(tree)
		for lineno, target in imported_modules(tree, module_name(rel), rel.endswith("__init__.py")):
			if module_in(target, ASSIGN_MODULE):
				violations.append(f"{rel}:{lineno}: imports {target} outside {ROUTE_FILE} (ADR-021)")
		for node in ast.walk(tree):
			if isinstance(node, ast.Name | ast.Attribute) and resolved_name(node, aliases).endswith(
				ASSIGN_CALL_SUFFIXES
			):
				violations.append(violation(rel, node, f"assigns people outside {ROUTE_FILE} (ADR-021)"))
			elif isinstance(node, ast.Constant) and node.value == ASSIGN_AGENT_NAME:
				violations.append(
					violation(rel, node, f"names {ASSIGN_AGENT_NAME} outside {ROUTE_FILE} (ADR-021)")
				)
			elif _creates_todo(node):
				violations.append(violation(rel, node, f"creates a ToDo outside {ROUTE_FILE} (ADR-021)"))
	return violations


def _creates_todo(node) -> bool:
	"""`get_doc("ToDo", ...)`, `get_doc({"doctype": "ToDo", ...})`, `new_doc("ToDo")`."""
	if not (isinstance(node, ast.Call) and referenced_name(node.func) in DOC_CREATE_CALLS and node.args):
		return False
	first = node.args[0]
	if isinstance(first, ast.Dict):
		return any(
			isinstance(key, ast.Constant)
			and key.value == "doctype"
			and isinstance(value, ast.Constant)
			and value.value == TODO_DOCTYPE
			for key, value in zip(first.keys, first.values, strict=True)
		)
	return isinstance(first, ast.Constant) and first.value == TODO_DOCTYPE


def check_no_share_bypass(sources: dict) -> list:
	"""ADR-021 QĐ 3: sharing is never forced (ignore_share_permission, assign_to._add, add_docshare, frappe.share.add)."""
	violations = []
	for rel, source in only_python(sources).items():
		tree = parse(rel, source)
		aliases = import_aliases(tree)
		for node in ast.walk(tree):
			bypass = [name for name in _node_names(node) if name in SHARE_BYPASS_NAMES]
			if isinstance(node, ast.Name | ast.Attribute) and resolved_name(node, aliases).endswith(
				SHARE_BYPASS_SUFFIXES
			):
				bypass.append(resolved_name(node, aliases))
			violations.extend(
				violation(rel, node, f"{name} bypasses sharing rules (ADR-021)") for name in bypass
			)
	return violations


def check_no_assign_column_for_decisions(sources: dict) -> list:
	"""ADR-019 QĐ 5: nothing under agent/ reads `_assign` (except authority.py, see ASSIGN_FIELD_ALLOWED_FILE)."""
	violations = []
	for rel, source in only_python(scoped(sources, AGENT_PREFIX)).items():
		tree = parse(rel, source)
		exempt = set()
		if rel == ASSIGN_FIELD_ALLOWED_FILE:
			for func in ast.walk(tree):
				if isinstance(func, ast.FunctionDef) and func.name == ASSIGN_FIELD_ALLOWED_FUNCTION:
					exempt |= {id(child) for child in ast.walk(func)}
		for node in ast.walk(tree):
			if id(node) in exempt:
				continue
			if referenced_name(node) == "_assign" or (
				isinstance(node, ast.Constant)
				and isinstance(node.value, str)
				and ASSIGN_FIELD.search(node.value)
			):
				violations.append(violation(rel, node, "reads `_assign` (decide from ToDo, ADR-019)"))
	return violations


def _sla_date_writes(tree: ast.AST):
	for node in ast.walk(tree):
		targets = []
		if isinstance(node, ast.Assign):
			targets = node.targets
		elif isinstance(node, ast.AugAssign | ast.AnnAssign):
			targets = [node.target]
		for target in targets:
			for part in ast.walk(target):
				if referenced_name(part) in SLA_DATE_FIELDS or (
					isinstance(part, ast.Constant) and part.value in SLA_DATE_FIELDS
				):
					yield part, "assigns"
		# The field name held in a constant (`F = "response_by"`, `F = ("response_by", ...)`), written later.
		if isinstance(node, ast.Assign | ast.AnnAssign | ast.AugAssign) and node.value is not None:
			held = node.value.elts if isinstance(node.value, ast.Tuple | ast.List | ast.Set) else [node.value]
			for part in held:
				if isinstance(part, ast.Constant) and part.value in SLA_DATE_FIELDS:
					yield part, "holds the name of"
		if isinstance(node, ast.keyword) and node.arg in SLA_DATE_FIELDS:
			yield node.value, "passes"
		elif isinstance(node, ast.Dict):
			for key in node.keys:
				if isinstance(key, ast.Constant) and key.value in SLA_DATE_FIELDS:
					yield key, "sets"
		elif isinstance(node, ast.Call) and (dotted_name(node.func) or "").split(".")[-1] in SLA_WRITE_CALLS:
			for arg in node.args:
				if isinstance(arg, ast.Constant) and arg.value in SLA_DATE_FIELDS:
					yield arg, "writes"


def check_feature_never_assigns_sla_dates(sources: dict) -> list:
	"""AC-10: Helpdesk computes `response_by`/`resolution_by`; nothing under agent/ writes them."""
	violations = []
	for rel, source in only_python(scoped(sources, AGENT_PREFIX)).items():
		for node, verb in _sla_date_writes(parse(rel, source)):
			violations.append(violation(rel, node, f"{verb} an SLA date (AC-10)"))
	return violations


def check_no_default_people_in_agent_python(sources: dict) -> list:
	"""AC-14: no hard-coded person (spec 16.2 names, the bot account) in a string under agent/."""
	violations = []
	for rel, source in only_python(scoped(sources, AGENT_PREFIX)).items():
		for node in constant_strings(parse(rel, source)):
			text = NAME_COINCIDENCES.sub(" ", node.value)
			for match in (*PERSON_NAME.finditer(text), *AGENT_ACCOUNT.finditer(text)):
				violations.append(violation(rel, node, f"hard-coded person {match.group(0)!r} (AC-14)"))
	return violations


def check_entry_types_unchanged(sources: dict) -> list:
	"""ADR-019 QĐ 7 + ADR-012 QĐ 6 + FEAT-007 U3 + ADR-048 QĐ 1: the log keeps its six entry types, in the code and in the DocType options."""
	run_log, doctype = sources.get(RUN_LOG_FILE), sources.get(LOG_DOCTYPE_FILE)
	if run_log is None:
		return _missing(RUN_LOG_FILE)
	if doctype is None:
		return _missing(LOG_DOCTYPE_FILE)
	violations = []
	found = None
	for node in parse(RUN_LOG_FILE, run_log).body:
		if isinstance(node, ast.Assign) and any(
			getattr(t, "id", None) == "ENTRY_TYPES" for t in node.targets
		):
			try:
				found = ast.literal_eval(node.value)
			except ValueError:
				found = "not a literal"
	if found != ENTRY_TYPES_EXPECTED:
		violations.append(f"{RUN_LOG_FILE}: ENTRY_TYPES is {found!r}, expected {ENTRY_TYPES_EXPECTED!r}")
	options = [
		field.get("options")
		for field in json.loads(doctype)["fields"]
		if field.get("fieldname") == "entry_type"
	]
	if options != ["\n".join(ENTRY_TYPES_EXPECTED)]:
		violations.append(f"{LOG_DOCTYPE_FILE}: entry_type options are {options!r}")
	return violations


def check_log_trigger_options_match_run_log(sources: dict, expected: list) -> list:
	"""FEAT-007 U3 F-5: the `trigger` options of ERP AI Log are the run_log trigger constants, in order."""
	doctype = sources.get(LOG_DOCTYPE_FILE)
	if doctype is None:
		return _missing(LOG_DOCTYPE_FILE)
	options = [
		field.get("options") for field in json.loads(doctype)["fields"] if field.get("fieldname") == "trigger"
	]
	if options != ["\n".join(expected)]:
		return [f"{LOG_DOCTYPE_FILE}: trigger options are {options!r}, run_log has {expected!r}"]
	return []


def check_policy_does_not_import_run_log(sources: dict) -> list:
	"""FEAT-007 U3 3.1: policy.py never imports run_log (run_log reads policy.site_environment; no cycle)."""
	source = sources.get(POLICY_FILE)
	if source is None:
		return _missing(POLICY_FILE)
	module = "erp_ai." + POLICY_FILE[: -len(".py")].replace("/", ".")
	return [
		f"{POLICY_FILE}:{lineno}: imports {name}"
		for lineno, name in imported_modules(parse(POLICY_FILE, source), module, False)
		if name == "erp_ai.agent.run_log"
	]


CHANGE_DECISION_FILE = "change_decision.py"


def check_decide_reads_one_click_switch_before_signature(sources: dict) -> list:
	"""FEAT-007 U3 3.3, ADR-032 QĐ 4: `decide` reads switch (5) through `policy.permission_switches` before
	it checks the signature (`signature_ok`), on every request."""
	source = sources.get(CHANGE_DECISION_FILE)
	if source is None:
		return _missing(CHANGE_DECISION_FILE)
	tree = parse(CHANGE_DECISION_FILE, source)
	decide = next((n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "decide"), None)
	if decide is None:
		return [f"{CHANGE_DECISION_FILE}: no function decide"]
	reads, signatures = [], []
	for node in ast.walk(decide):
		if isinstance(node, ast.Call):
			name = dotted_name(node.func) or ""
			if name == "policy.permission_switches":
				reads.append(node.lineno)
			elif name.endswith("signature_ok"):
				signatures.append(node.lineno)
	if not reads:
		return [f"{CHANGE_DECISION_FILE}: decide does not read policy.permission_switches"]
	if not signatures or min(reads) > min(signatures):
		return [f"{CHANGE_DECISION_FILE}: decide checks the signature before the switch (5)"]
	return []


RUN_LOG_FILE = "agent/run_log.py"


def check_action_entries_built_only_in_run_log(sources: dict) -> list:
	"""FEAT-007 U3 3.1, ADR-033 Ràng buộc: no dict literal with the keys "tool" and "ok" (an action entry)
	outside `agent/run_log.py`; the entry is built by `run_log.action_entry` and nowhere else."""
	found = []
	for rel, source in only_python(sources).items():
		if rel == RUN_LOG_FILE:
			continue
		for node in ast.walk(parse(rel, source)):
			if isinstance(node, ast.Dict):
				keys = {key.value for key in node.keys if isinstance(key, ast.Constant)}
				if {"tool", "ok"} <= keys:
					found.append(f"{rel}:{node.lineno}: hand-built action entry (use run_log.action_entry)")
	return found


def check_comment_signs_only_when_one_click(sources: dict) -> list:
	"""FEAT-007 U3 3.4: `propose_change._comment` calls `change_link.decision_path` only inside a branch
	whose test reads `one_click_approval`."""
	source = sources.get(PROPOSE_TOOL_FILE)
	if source is None:
		return _missing(PROPOSE_TOOL_FILE)
	tree = parse(PROPOSE_TOOL_FILE, source)
	comment = next(
		(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "_comment"), None
	)
	if comment is None:
		return [f"{PROPOSE_TOOL_FILE}: no function _comment"]
	guarded = set()
	for node in ast.walk(comment):
		if isinstance(node, ast.If) and "one_click_approval" in ast.dump(node.test):
			guarded.update(id(inner) for stmt in node.body for inner in ast.walk(stmt))
	return [
		f"{PROPOSE_TOOL_FILE}:{node.lineno}: _comment signs a link outside the one_click_approval branch"
		for node in ast.walk(comment)
		if isinstance(node, ast.Call)
		and (dotted_name(node.func) or "").endswith("decision_path")
		and id(node) not in guarded
	]


# ---------------------------------------------------------------------------------------------------
# FEAT-004 rules, group 1 (ADR-011, ADR-012 "Ràng buộc"; design 8.2)
# ---------------------------------------------------------------------------------------------------

CHANGES_PREFIX = "agent/changes/"
TRANSITIONS_FILE = "agent/changes/transitions.py"
TRANSITIONS_MODULE = "erp_ai.agent.changes.transitions"
PROPOSAL_CONTROLLER_FILE = "erp_ai_agent/doctype/erp_ai_change_proposal/erp_ai_change_proposal.py"
PROPOSAL_DOCTYPE_FILE = "erp_ai_agent/doctype/erp_ai_change_proposal/erp_ai_change_proposal.json"
PROPOSAL_DOCTYPE_NAME = "ERP AI Change Proposal"
PROPOSAL_DOCTYPE_CONSTANT = "PROPOSAL_DOCTYPE"
PROPOSE_TOOL_FILE = "agent/tools/propose_change.py"
PANEL_HELPER_FUNCTIONS = ("has_decider_role", "panel_decision_refusal", "proposal_head", "panel_cards")
CHANGE_GUARD_FILE = "agent/tools/change_guard.py"
CHANGE_GUARD_FUNCTION = "check_write_path"
SAFE_PATH_CALL = "erp_ai.agent.tools.source.resolve_safe_path"
SAFE_PATH_NAME = "safe_path"  # any function so named outside source.py is a second resolver (ADR-011)
ROOT_CHECK_CALLS = ("commonpath", "is_relative_to")
MODULE_SCOPE = "<module>"
# Hand-written: (file, function) allowed to root-check outside source.py. check_write_path only
# classifies a path resolve_safe_path already refused, to pick the refusal reason (ADR-011, design table 3.1).
ROOT_CHECK_ALLOWLIST = frozenset(
	{
		(CHANGE_GUARD_FILE, CHANGE_GUARD_FUNCTION),
		# Guards the output path of the offline eval export; predates FEAT-004 and is on no path the agent's
		# tools or the apply job write through.
		("eval/export_tickets.py", "_inside_repo"),
	}
)

# Design 2.1 state group (11 names) + the 4 git result fields of amendment 1 + the 4 CHG-002 design 3.6 fields,
# in transitions.STATE_FIELDS order.
STATE_FIELDS = (
	"change_status",
	"decided_by",
	"decided_at",
	"approved_digest",
	"undo_by",
	"undo_at",
	"finished_at",
	"exit_code",
	"duration_ms",
	"command_output",
	"command_results",
	"failure_reason",
	"created_dirs",
	"restart_status",
	"restart_sent_at",
	"applied_branch",
	"applied_ahead_count",
	"apply_commit_sha",
	"undo_commit_sha",
)
STATE_WRITE_CALLS = ("set", "db_set", "set_value", "update", "setattr")
STATE_KEYWORD_CALLS = (*STATE_WRITE_CALLS, "get_doc", "new_doc", "dict")

# ADR-012 Ràng buộc, design 2.1: every role on the proposal DocType and the only permissions it holds.
PROPOSAL_PERMISSIONS = {
	"ERP AI Agent": frozenset({"create", "read"}),
	"ERP AI Instructor": frozenset({"read"}),
	"System Manager": frozenset({"read"}),
}
PROPOSAL_FORBIDDEN_PERMISSIONS = ("write", "delete", "submit", "cancel", "amend")
# The check fields of a Frappe DocPerm row.
DOCPERM_FLAGS = (
	"select",
	"read",
	"write",
	"create",
	"delete",
	"submit",
	"cancel",
	"amend",
	"report",
	"export",
	"import",
	"share",
	"print",
	"email",
)
PROPOSAL_SAVE_CALLS = ("save", "db_set", "set_value")
# A tool that loads/deletes a document of a non-constant DocType and saves/deletes it writes any DocType
# (site_api.update_record / delete_record); only its deny sets keep the proposal out (ADR-011).
GENERIC_DOC_CALLS = ("get_doc", "delete_doc")
GENERIC_WRITE_CALLS = ("save", "delete")
DENY_SET_SUFFIX = "DENIED_DOCTYPES"
SITE_API_FILE = "agent/tools/site_api.py"
# ADR-023 Quyết định 3: site_api derives its deny sets; it never writes the app's DocType names by hand.
APP_DOCTYPE_CONSTANTS = ("SETTING_DOCTYPE", "CREDENTIAL_DOCTYPE", "LOG_DOCTYPE", PROPOSAL_DOCTYPE_CONSTANT)
APP_DOCTYPE_NAMES = ("ERP AI Setting", "ERP AI Credential", "ERP AI Log", PROPOSAL_DOCTYPE_NAME)
SET_LITERAL_CALLS = ("set", "frozenset", "tuple", "list")
SITE_API_ALWAYS_DENIED = "always_denied_doctypes"
# The calls that yield a derived deny set: site_api's own function and read.denied_doctypes().
SITE_API_DENY_SOURCES = (SITE_API_ALWAYS_DENIED, "denied_doctypes")
# Where the derived set comes from: the app's module, or read.denied_doctypes() (ADR-023 Ràng buộc).
SITE_API_DERIVED_FROM = ("AI_MODULE", "denied_doctypes")
SITE_API_TOOL_PREFIX = "api_"
SITE_API_WRITE_CALLS = (
	"save",
	"insert",
	"delete",
	"delete_doc",
	"submit",
	"cancel",
	"call",
	*PROPOSAL_SAVE_CALLS,
)


def check_transitions_imported_only_by_controller_and_changes(sources: dict) -> list:
	"""ADR-012 Ràng buộc: only the proposal controller and agent/changes/** reach the state machine
	(an import, `changes.transitions` through an imported package, or the dotted path as a string)."""
	reason = "ADR-012: only the proposal controller and agent/changes/ use the state machine"
	violations = []
	for rel, source in only_python(sources).items():
		if rel == PROPOSAL_CONTROLLER_FILE or rel.startswith(CHANGES_PREFIX):
			continue
		tree = parse(rel, source)
		aliases = import_aliases(tree)
		for lineno, target in imported_modules(tree, module_name(rel), rel.endswith("__init__.py")):
			if module_in(target, TRANSITIONS_MODULE):
				violations.append(f"{rel}:{lineno}: imports {target} ({reason})")
		for node in ast.walk(tree):
			if isinstance(node, ast.Attribute) and resolved_name(node, aliases) == TRANSITIONS_MODULE:
				violations.append(violation(rel, node, f"reaches {TRANSITIONS_MODULE} ({reason})"))
			elif (
				isinstance(node, ast.Constant)
				and isinstance(node.value, str)
				and module_in(node.value, TRANSITIONS_MODULE)
			):
				violations.append(violation(rel, node, f"names {node.value} ({reason})"))
	return violations


def _state_field_writes(tree: ast.AST):
	"""`(node, how)` for every write of a STATE_FIELDS name: assignment target, dict key, `set`-like call
	with the name as a positional string or attribute (`qb.set(T.change_status, v)`), or the name as a
	keyword of a document write/create call or of `dict(...)`."""
	for node in ast.walk(tree):
		targets = []
		if isinstance(node, ast.Assign):
			targets = node.targets
		elif isinstance(node, ast.AugAssign | ast.AnnAssign):
			targets = [node.target]
		for target in targets:
			for part in ast.walk(target):
				if isinstance(part, ast.Attribute) and part.attr in STATE_FIELDS:
					yield part, f"assigns .{part.attr}"
				elif isinstance(part, ast.Constant) and part.value in STATE_FIELDS:
					yield part, f"assigns [{part.value!r}]"
		if isinstance(node, ast.Dict):
			for key in node.keys:
				if isinstance(key, ast.Constant) and key.value in STATE_FIELDS:
					yield key, f"sets {key.value!r}"
		elif isinstance(node, ast.Call):
			function = (dotted_name(node.func) or "").split(".")[-1]
			if function in STATE_WRITE_CALLS:
				for arg in node.args:
					if isinstance(arg, ast.Constant) and arg.value in STATE_FIELDS:
						yield arg, f"{function}({arg.value!r})"
					elif isinstance(arg, ast.Attribute) and arg.attr in STATE_FIELDS:
						yield arg, f"{function}(.{arg.attr})"
			if function in STATE_KEYWORD_CALLS:
				for keyword in node.keywords:
					if keyword.arg in STATE_FIELDS:
						yield keyword.value, f"{function}({keyword.arg}=)"


def check_change_state_fields_written_only_in_changes(sources: dict) -> list:
	"""ADR-012 QĐ 2 / Ràng buộc ("Ghi vào"): the proposal state group (STATE_FIELDS) is written only under
	agent/changes/; reads are allowed. Design 8.2 words this more broadly; ADR-012's write-only scope is kept."""
	violations = []
	for rel, source in only_python(sources).items():
		if rel.startswith(CHANGES_PREFIX):
			continue
		for node, how in _state_field_writes(parse(rel, source)):
			violations.append(
				violation(rel, node, f"{how}: a proposal state field outside {CHANGES_PREFIX} (ADR-012)")
			)
	return violations


def _resolver_results(function, aliases: dict) -> set:
	"""Local names bound to a `resolve_safe_path(...)` result (`full = ...` or `(full := ...)`)."""
	names = set()
	for node in ast.walk(function):
		if isinstance(node, ast.Assign | ast.NamedExpr) and isinstance(node.value, ast.Call):
			if resolved_name(node.value.func, aliases) == SAFE_PATH_CALL:
				targets = node.targets if isinstance(node, ast.Assign) else [node.target]
				names.update(target.id for target in targets if isinstance(target, ast.Name))
	return names


def _tests_none(test, names: set) -> bool:
	"""`x is None`, `(x := ...) is None` or `not x` for x in `names`."""
	if isinstance(test, ast.UnaryOp) and isinstance(test.op, ast.Not):
		return isinstance(test.operand, ast.Name) and test.operand.id in names
	if not (isinstance(test, ast.Compare) and len(test.ops) == 1 and isinstance(test.ops[0], ast.Is)):
		return False
	left = test.left.target if isinstance(test.left, ast.NamedExpr) else test.left
	right = test.comparators[0]
	return (
		isinstance(left, ast.Name)
		and left.id in names
		and isinstance(right, ast.Constant)
		and right.value is None
	)


def _refuses_when_unresolved(function, aliases: dict) -> bool:
	"""An `if <resolve_safe_path result> is None:` whose body returns a call (the refusal) or raises."""
	names = _resolver_results(function, aliases)
	return any(
		isinstance(node, ast.If)
		and _tests_none(node.test, names)
		and any(
			isinstance(stmt, ast.Raise) or (isinstance(stmt, ast.Return) and isinstance(stmt.value, ast.Call))
			for stmt in node.body
		)
		for node in ast.walk(function)
	)


def _root_check_calls(node: ast.AST, function: str = MODULE_SCOPE):
	"""`(innermost enclosing function name, call)` for every `commonpath`/`is_relative_to` call, realpath nearby or
	not: source.py itself splits the root check (`_inside`) from the realpath calls of its caller."""
	for child in ast.iter_child_nodes(node):
		scope = child.name if isinstance(child, ast.FunctionDef | ast.AsyncFunctionDef) else function
		if isinstance(child, ast.Call) and referenced_name(child.func) in ROOT_CHECK_CALLS:
			yield function, child
		yield from _root_check_calls(child, scope)


def check_change_guard_uses_resolve_safe_path(sources: dict) -> list:
	"""ADR-011 Ràng buộc: `change_guard.check_write_path` calls `source.resolve_safe_path` and refuses when it
	returns None; outside source.py no function is named like it and no code checks a root
	(`commonpath`/`is_relative_to`, with or without realpath; ROOT_CHECK_ALLOWLIST holds the guard's own classification of a refused path)."""
	guard = sources.get(CHANGE_GUARD_FILE)
	if guard is None:
		return _missing(CHANGE_GUARD_FILE)
	violations = []
	tree = parse(CHANGE_GUARD_FILE, guard)
	aliases = import_aliases(tree)
	function = next(
		(
			node
			for node in tree.body
			if isinstance(node, ast.FunctionDef) and node.name == CHANGE_GUARD_FUNCTION
		),
		None,
	)
	if function is None:
		violations.append(f"{CHANGE_GUARD_FILE}: no top-level {CHANGE_GUARD_FUNCTION}() (ADR-011)")
	elif not any(
		isinstance(node, ast.Call) and resolved_name(node.func, aliases) == SAFE_PATH_CALL
		for node in ast.walk(function)
	):
		violations.append(
			violation(
				CHANGE_GUARD_FILE,
				function,
				f"{CHANGE_GUARD_FUNCTION} does not call {SAFE_PATH_CALL} (ADR-011)",
			)
		)
	elif not _refuses_when_unresolved(function, aliases):
		violations.append(
			violation(
				CHANGE_GUARD_FILE,
				function,
				f"{CHANGE_GUARD_FUNCTION} does not refuse when {SAFE_PATH_CALL} returns None (ADR-011)",
			)
		)
	for rel, source in only_python(sources).items():
		if rel == SOURCE_TOOL_FILE:
			continue
		tree = parse(rel, source)
		for node in ast.walk(tree):
			if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and SAFE_PATH_NAME in node.name:
				violations.append(violation(rel, node, f"{node.name}() is a second path resolver (ADR-011)"))
		for function, call in _root_check_calls(tree):
			if (rel, function) not in ROOT_CHECK_ALLOWLIST:
				violations.append(
					violation(
						rel,
						call,
						f"{function}() calls {referenced_name(call.func)}: a second root check (ADR-011)",
					)
				)
	return violations


def check_proposal_doctype_permissions(sources: dict) -> list:
	"""ADR-012 Ràng buộc: no role has write/delete/submit/cancel/amend on the proposal; each role holds exactly
	the permissions of PROPOSAL_PERMISSIONS (rows of one role are merged)."""
	text = sources.get(PROPOSAL_DOCTYPE_FILE)
	if text is None:
		return _missing(PROPOSAL_DOCTYPE_FILE)
	violations = []
	granted = {}
	for row in json.loads(text).get("permissions") or []:
		role = row.get("role")
		flags = {flag for flag in DOCPERM_FLAGS if row.get(flag)}
		violations.extend(
			f"{PROPOSAL_DOCTYPE_FILE}: role {role!r} has {flag} (ADR-012)"
			for flag in PROPOSAL_FORBIDDEN_PERMISSIONS
			if flag in flags
		)
		granted.setdefault(role, set()).update(flags - set(PROPOSAL_FORBIDDEN_PERMISSIONS))
	for role in sorted(set(granted) | set(PROPOSAL_PERMISSIONS), key=str):
		expected = PROPOSAL_PERMISSIONS.get(role, frozenset())
		if granted.get(role, set()) != expected:
			violations.append(
				f"{PROPOSAL_DOCTYPE_FILE}: role {role!r} has {sorted(granted.get(role, ()))}, "
				f"expected {sorted(expected)} (ADR-012)"
			)
	return violations


def _names_proposal(node) -> bool:
	return (isinstance(node, ast.Constant) and node.value == PROPOSAL_DOCTYPE_NAME) or (
		referenced_name(node) == PROPOSAL_DOCTYPE_CONSTANT
	)


def _builds_proposal(tree: ast.AST) -> bool:
	"""The module loads or creates a proposal: `get_doc`/`new_doc`(proposal, ...) or `{"doctype": proposal}`."""
	for node in ast.walk(tree):
		if isinstance(node, ast.Call) and referenced_name(node.func) in DOC_GETTERS and node.args:
			if _names_proposal(node.args[0]):
				return True
		elif isinstance(node, ast.Dict) and any(
			isinstance(key, ast.Constant) and key.value == "doctype" and _names_proposal(value)
			for key, value in zip(node.keys, node.values, strict=True)
		):
			return True
	return False


def _writes_any_doctype(tree: ast.AST) -> bool:
	"""The module loads a document of a non-constant DocType and saves/deletes it, or deletes one directly."""
	generic = set()
	for node in ast.walk(tree):
		if isinstance(node, ast.Call) and referenced_name(node.func) in GENERIC_DOC_CALLS:
			# Positional, or keywords only: `get_doc(doctype=d, name=n)`.
			first = (
				node.args[0]
				if node.args
				else next((keyword.value for keyword in node.keywords if keyword.arg == "doctype"), None)
			)
			if first is None:
				continue
			constant = isinstance(first, ast.Constant | ast.Dict) or (referenced_name(first) or "").isupper()
			if not constant and not _names_proposal(first):
				generic.add(referenced_name(node.func))
	if "delete_doc" in generic:
		return True
	return "get_doc" in generic and any(
		isinstance(node, ast.Call) and referenced_name(node.func) in GENERIC_WRITE_CALLS
		for node in ast.walk(tree)
	)


def _contains_proposal(node) -> bool:
	"""The set expression keeps the proposal DocType: named in a literal or set call, or on either side of `|`;
	on the right of `-` it is taken out, so only the left side counts."""
	if _names_proposal(node):
		return True
	if isinstance(node, ast.Set | ast.List | ast.Tuple):
		return any(_contains_proposal(element) for element in node.elts)
	if isinstance(node, ast.Call):
		return any(_contains_proposal(arg) for arg in node.args)
	if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
		return _contains_proposal(node.left) or _contains_proposal(node.right)
	if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Sub):
		return _contains_proposal(node.left)
	return False


def _deny_sets(tree: ast.AST) -> dict:
	"""`{name: (node, value)}` of module-level assignments to a `*DENIED_DOCTYPES` name."""
	found = {}
	for node in tree.body:
		if isinstance(node, ast.Assign):
			for target in node.targets:
				if isinstance(target, ast.Name) and target.id.endswith(DENY_SET_SUFFIX):
					found[target.id] = (node, node.value)
	return found


def _names_app_doctype(node) -> bool:
	return (isinstance(node, ast.Constant) and node.value in APP_DOCTYPE_NAMES) or (
		isinstance(node, ast.Name | ast.Attribute) and referenced_name(node) in APP_DOCTYPE_CONSTANTS
	)


def _literal_names_app_doctype(node) -> bool:
	"""`node` holds a set/tuple/list literal (bare or inside set()/frozenset()/...) naming an app DocType."""
	for inner in ast.walk(node):
		if isinstance(inner, ast.Set | ast.Tuple | ast.List) and any(
			_names_app_doctype(e) for e in inner.elts
		):
			return True
		if (
			isinstance(inner, ast.Call)
			and referenced_name(inner.func) in SET_LITERAL_CALLS
			and any(_names_app_doctype(arg) for arg in inner.args)
		):
			return True
	return False


def _removes_app_doctype(node) -> bool:
	"""`node` takes an app DocType out of a set: `x - {PROPOSAL_DOCTYPE}` or `x.difference(...)`."""
	for inner in ast.walk(node):
		if isinstance(inner, ast.BinOp) and isinstance(inner.op, ast.Sub):
			if any(_names_app_doctype(part) for part in ast.walk(inner.right)):
				return True
		elif isinstance(inner, ast.Call) and referenced_name(inner.func) == "difference":
			if any(_names_app_doctype(part) for arg in inner.args for part in ast.walk(arg)):
				return True
	return False


def _module_functions(tree: ast.AST) -> dict:
	return {node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)}


def _called_names(node) -> set:
	return {referenced_name(call.func) for call in ast.walk(node) if isinstance(call, ast.Call)} - {None}


def _reaches(node, targets: tuple, functions: dict, seen=frozenset()) -> bool:
	"""`node` calls one of `targets`, directly or through the module's own functions."""
	for name in _called_names(node):
		if name in targets:
			return True
		if (
			name in functions
			and name not in seen
			and _reaches(functions[name], targets, functions, seen | {name})
		):
			return True
	return False


def _returns_deny_set(name: str, functions: dict, seen=frozenset()) -> bool:
	"""A deny source, or a module function whose every `return` value is built from a deny source."""
	if name in SITE_API_DENY_SOURCES:
		return True
	function = functions.get(name)
	if function is None or name in seen:
		return False
	returns = [node for node in ast.walk(function) if isinstance(node, ast.Return)]
	return bool(returns) and all(
		node.value is not None
		and not _removes_app_doctype(node.value)
		and any(_returns_deny_set(called, functions, seen | {name}) for called in _called_names(node.value))
		for node in returns
	)


def _is_deny_gate(statement, functions: dict, seen=frozenset()) -> bool:
	"""`if <test>: ... return` where the test calls a deny set, or a module function that has such a gate itself."""
	if not isinstance(statement, ast.If) or not any(isinstance(node, ast.Return) for node in statement.body):
		return False
	if _removes_app_doctype(statement.test):
		return False
	return any(
		_returns_deny_set(name, functions) or _has_deny_gate(name, functions, seen)
		for name in _called_names(statement.test)
	)


def _has_deny_gate(name: str, functions: dict, seen=frozenset()) -> bool:
	function = functions.get(name)
	if function is None or name in seen:
		return False
	return any(_is_deny_gate(node, functions, seen | {name}) for node in ast.walk(function))


def _site_api_handlers(tree: ast.AST) -> dict:
	"""`{tool name: handler name}` of every `ToolSpec(name="api_...", handler=...)`."""
	handlers = {}
	for node in ast.walk(tree):
		if not (isinstance(node, ast.Call) and referenced_name(node.func) == "ToolSpec"):
			continue
		keywords = {keyword.arg: keyword.value for keyword in node.keywords}
		tool, handler = keywords.get("name"), keywords.get("handler")
		if (
			isinstance(tool, ast.Constant)
			and isinstance(tool.value, str)
			and tool.value.startswith(SITE_API_TOOL_PREFIX)
		):
			# Only a bare name is a function of this module; `other.handler` cannot be proven here.
			handlers[tool.value] = handler.id if isinstance(handler, ast.Name) else None
	return handlers


def _site_api_deny_violations(rel: str, tree: ast.AST) -> list:
	"""ADR-023 Quyết định 3 / ADR-011: site_api has no hand-written set of the app's DocTypes; the always-denied
	set is derived from the app's module; every `api_*` handler is refused by that derived set before any write."""
	violations = [
		violation(
			rel, node, "hand-written set of the app's DocTypes in site_api, derive the deny set (ADR-023)"
		)
		for node in tree.body
		if isinstance(node, ast.Assign | ast.AnnAssign)
		and node.value is not None
		and _literal_names_app_doctype(node.value)
	]
	functions = _module_functions(tree)
	always = functions.get(SITE_API_ALWAYS_DENIED)
	if always is None:
		violations.append(
			f"{rel}: no {SITE_API_ALWAYS_DENIED}() deny set derived from the app's module (ADR-023)"
		)
	elif _literal_names_app_doctype(always) or not any(
		referenced_name(node) in SITE_API_DERIVED_FROM for node in ast.walk(always)
	):
		violations.append(
			violation(
				rel, always, f"{SITE_API_ALWAYS_DENIED}() is not derived from the app's module (ADR-023)"
			)
		)
	handlers = _site_api_handlers(tree)
	if not handlers:
		violations.append(
			f"{rel}: saves/deletes any DocType but no {SITE_API_TOOL_PREFIX}* handler to check the deny gate"
		)
	for tool, name in handlers.items():
		handler = functions.get(name)
		if handler is None:
			violations.append(f"{rel}: handler of {tool} is not a function of the module, deny gate unproven")
			continue
		gated = False
		for statement in handler.body:
			if _is_deny_gate(statement, functions):
				gated = True
				break
			if isinstance(statement, ast.Return) or _reaches(statement, SITE_API_WRITE_CALLS, functions):
				break
		if not gated:
			violations.append(
				violation(
					rel,
					handler,
					f"{tool} handler {name} writes or returns before the derived deny gate (ADR-011)",
				)
			)
	return violations


def _proposal_deny_violations(rel: str, tree: ast.AST) -> list:
	"""ADR-011: a tool writing any DocType keeps the proposal out through its deny sets; site_api through the
	derived deny gate of ADR-023."""
	if not _writes_any_doctype(tree):
		return []
	if rel == SITE_API_FILE:
		return _site_api_deny_violations(rel, tree)
	sets = _deny_sets(tree)
	violations = []
	if not sets:
		violations.append(
			f"{rel}: saves/deletes any DocType but has no *{DENY_SET_SUFFIX} deny set (ADR-011)"
		)
	for name, (node, value) in sets.items():
		if not _contains_proposal(value):
			violations.append(
				violation(
					rel,
					node,
					f"deny set {name} lacks {PROPOSAL_DOCTYPE_CONSTANT} in a tool that saves any DocType (ADR-011)",
				)
			)
	return violations


def check_propose_change_builds_no_target_itself(sources: dict) -> list:
	"""CHG-008 design 8.2: `propose_change._comment` takes the first sentence from `change_text.proposal_target`
	and does not choose a branch itself: no `CHANGE_KIND_CODE` and no `is_new_file` in its body."""
	source = sources.get(PROPOSE_TOOL_FILE)
	if source is None:
		return _missing(PROPOSE_TOOL_FILE)
	comment = next(
		(
			n
			for n in ast.walk(parse(PROPOSE_TOOL_FILE, source))
			if isinstance(n, ast.FunctionDef) and n.name == "_comment"
		),
		None,
	)
	if comment is None:
		return [f"{PROPOSE_TOOL_FILE}: no function _comment"]
	violations = []
	if not any(
		(dotted_name(c.func) or "").endswith("proposal_target")
		for c in ast.walk(comment)
		if isinstance(c, ast.Call)
	):
		violations.append(
			f"{PROPOSE_TOOL_FILE}:{comment.lineno}: _comment does not call change_text.proposal_target"
		)
	for node in ast.walk(comment):
		if isinstance(node, ast.Name) and node.id == "CHANGE_KIND_CODE":
			violations.append(f"{PROPOSE_TOOL_FILE}:{node.lineno}: _comment compares CHANGE_KIND_CODE itself")
		elif isinstance(node, ast.Constant) and node.value == "is_new_file":
			violations.append(f"{PROPOSE_TOOL_FILE}:{node.lineno}: _comment reads is_new_file itself")
		elif isinstance(node, ast.Attribute) and node.attr == "is_new_file":
			violations.append(f"{PROPOSE_TOOL_FILE}:{node.lineno}: _comment reads is_new_file itself")
	return violations


def check_panel_cards_called_only_by_panel(sources: dict) -> list:
	"""CHG-008 design 8.2: the four panel helpers of the proposal controller are not whitelisted, and no product
	file but `ticket_panel.py` calls `panel_cards` (it does no gate of its own, so only the gated panel may)."""
	source = sources.get(PROPOSAL_CONTROLLER_FILE)
	if source is None:
		return _missing(PROPOSAL_CONTROLLER_FILE)
	violations = []
	tree = parse(PROPOSAL_CONTROLLER_FILE, source)
	defined = {n.name for n in tree.body if isinstance(n, ast.FunctionDef)}
	whitelisted = {
		node.name for _rel, node, _decorator in whitelisted_functions({PROPOSAL_CONTROLLER_FILE: source})
	}
	for name in PANEL_HELPER_FUNCTIONS:
		if name not in defined:
			violations.append(f"{PROPOSAL_CONTROLLER_FILE}: no function {name}")
		if name in whitelisted:
			violations.append(f"{PROPOSAL_CONTROLLER_FILE}: {name} must not be whitelisted")
	called_by_panel = False
	for rel, text in only_python(sources).items():
		for node in ast.walk(parse(rel, text)):
			if not isinstance(node, ast.Call):
				continue
			name = (dotted_name(node.func) or "").rpartition(".")[2]
			if name != "panel_cards":
				continue
			if rel == PANEL_FILE:
				called_by_panel = True
			else:
				violations.append(violation(rel, node, "panel_cards is called outside ticket_panel.py"))
	if PANEL_FILE in sources and not called_by_panel:
		violations.append(f"{PANEL_FILE}: does not call panel_cards")
	return violations


def check_role_instructor_only_in_decider_role(sources: dict) -> list:
	"""CHG-008 design 8.2: in the proposal controller, `ticket_panel.py` and `change_decision.py`, the role
	`ROLE_INSTRUCTOR` (name or literal) is used only inside `has_decider_role`; an import is not a use."""
	violations = []
	for rel in (PROPOSAL_CONTROLLER_FILE, PANEL_FILE, "change_decision.py"):
		if rel not in sources:
			violations.append(f"{rel} is missing")
			continue
		tree = parse(rel, sources[rel])
		allowed = {
			id(inner)
			for n in ast.walk(tree)
			if isinstance(n, ast.FunctionDef) and n.name == "has_decider_role"
			for inner in ast.walk(n)
		}
		for node in ast.walk(tree):
			if id(node) in allowed:
				continue
			if (isinstance(node, ast.Name) and node.id == "ROLE_INSTRUCTOR") or (
				isinstance(node, ast.Attribute) and node.attr == "ROLE_INSTRUCTOR"
			):
				violations.append(violation(rel, node, "ROLE_INSTRUCTOR outside has_decider_role"))
			elif isinstance(node, ast.Constant) and node.value == "ERP AI Instructor":
				violations.append(violation(rel, node, "the role literal outside has_decider_role"))
	return violations


PANEL_DECIDE_FUNCTION = "decide_proposal"
PANEL_DECIDE_METHOD = f"{PANEL_MODULE}.{PANEL_DECIDE_FUNCTION}"
PANEL_DECISIONS_NAME = "PANEL_DECISIONS"
PANEL_GATE_FUNCTION = "_require_panel_access"
PANEL_HEAD_FUNCTION = "proposal_head"
PANEL_PREDICATE_FUNCTION = "panel_decision_refusal"
# ADR-044 Ràng buộc 3: names the panel's decision path never uses itself (the controller method does that work).
PANEL_DECIDE_FORBIDDEN = (
	"permission_switches",
	"transitions",
	"enqueue_change_job",
	"undo",
	"confirm_restart",
)
# AC-8 (b): what no bot module may name, in code or in text.
AGENT_PANEL_NEEDLES = (PANEL_MODULE.rpartition(".")[2], PANEL_DECIDE_FUNCTION)


def _call_leaf(node: ast.Call) -> str:
	return (dotted_name(node.func) or "").rpartition(".")[2]


def _decide_gate_violations(decide, head, gate) -> list:
	"""The gate's ticket is `<name>.ticket` of the name `proposal_head(...)` was assigned to, and its label is decide."""
	violations = []
	assigned = {
		target.id
		for node in ast.walk(decide)
		if isinstance(node, ast.Assign) and node.value is head
		for target in node.targets
		if isinstance(target, ast.Name)
	}
	first = gate.args[0] if gate.args else None
	if not (
		isinstance(first, ast.Attribute)
		and first.attr == "ticket"
		and isinstance(first.value, ast.Name)
		and first.value.id in assigned
	):
		violations.append(
			violation(
				PANEL_FILE,
				gate,
				f"the first argument of {PANEL_GATE_FUNCTION} is not the ticket of proposal_head(...)",
			)
		)
	label = {kw.arg: kw.value for kw in gate.keywords}.get("method")
	if not (isinstance(label, ast.Constant) and label.value == "decide"):
		violations.append(
			violation(PANEL_FILE, gate, f'{PANEL_GATE_FUNCTION} is not called with method="decide"')
		)
	return violations


def check_panel_decision_follows_adr_044(sources: dict) -> list:
	"""CHG-008 design 3.2, 8.2 (ADR-044 QĐ 5, Ràng buộc 3): `decide_proposal(name, action)` takes no ticket; it
	calls, in this order and once each, `proposal_head(...)`, the panel gate with the `ticket` of that head, the
	predicate `panel_decision_refusal`, then the controller through `PANEL_DECISIONS[...]` and never `approve`/
	`reject` directly; neither it nor `PANEL_DECISIONS` names the switch reader, the state machine, the job queue,
	undo or confirm_restart."""
	source = sources.get(PANEL_FILE)
	if source is None:
		return _missing(PANEL_FILE)
	tree = parse(PANEL_FILE, source)
	definitions = _module_definitions(tree)
	decide = definitions.get(PANEL_DECIDE_FUNCTION)
	if not isinstance(decide, ast.FunctionDef):
		return [f"{PANEL_FILE}: no function {PANEL_DECIDE_FUNCTION}"]
	violations = []
	params = _parameters(decide)
	if params != ["name", "action"] or decide.args.vararg or decide.args.kwarg:
		violations.append(
			violation(
				PANEL_FILE, decide, f"{PANEL_DECIDE_FUNCTION} takes {params}, expected ['name', 'action']"
			)
		)
	calls = [node for node in ast.walk(decide) if isinstance(node, ast.Call)]
	steps = {
		PANEL_HEAD_FUNCTION: [c for c in calls if _call_leaf(c) == PANEL_HEAD_FUNCTION],
		PANEL_GATE_FUNCTION: [c for c in calls if _call_leaf(c) == PANEL_GATE_FUNCTION],
		PANEL_PREDICATE_FUNCTION: [c for c in calls if _call_leaf(c) == PANEL_PREDICATE_FUNCTION],
		f"{PANEL_DECISIONS_NAME}[...]": [
			c
			for c in calls
			if isinstance(c.func, ast.Subscript) and dotted_name(c.func.value) == PANEL_DECISIONS_NAME
		],
	}
	for label, found in steps.items():
		if len(found) != 1:
			violations.append(
				violation(
					PANEL_FILE,
					decide,
					f"{PANEL_DECIDE_FUNCTION} calls {label} {len(found)} times, expected once",
				)
			)
	for call in calls:
		# CHG-010: the panel approves through `panel_approve`, so a direct call to it is banned like `approve`
		if _call_leaf(call) in ("approve", "panel_approve", "reject"):
			violations.append(
				violation(
					PANEL_FILE,
					call,
					f"{_call_leaf(call)} is called directly, not through {PANEL_DECISIONS_NAME}",
				)
			)
	if all(len(found) == 1 for found in steps.values()):
		ordered = [found[0] for found in steps.values()]
		positions = [(node.lineno, node.col_offset) for node in ordered]
		if positions != sorted(positions):
			violations.append(
				violation(
					PANEL_FILE, decide, f"{PANEL_DECIDE_FUNCTION} order is not {' -> '.join(steps)} (D-3)"
				)
			)
		violations.extend(_decide_gate_violations(decide, ordered[0], ordered[1]))
		# CHG-010: the predicate must be told whether the proposal is a console one, or the console switch is skipped
		predicate_call = ordered[2]
		if not any(
			keyword.arg == "console" and dotted_name(keyword.value) == "head.is_console"
			for keyword in predicate_call.keywords
		):
			violations.append(
				violation(
					PANEL_FILE,
					predicate_call,
					f"{PANEL_PREDICATE_FUNCTION} is called without console=head.is_console (CHG-010)",
				)
			)
	table = definitions.get(PANEL_DECISIONS_NAME)
	if table is None:
		violations.append(f"{PANEL_FILE}: no {PANEL_DECISIONS_NAME}")
	docstrings = _docstring_ids(decide)
	for scope in (decide, table):
		for node in ast.walk(scope) if scope is not None else ():
			if isinstance(node, ast.Name | ast.Attribute):
				name = node.id if isinstance(node, ast.Name) else node.attr
			elif (
				isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in docstrings
			):
				name = node.value
			else:
				continue
			if name in PANEL_DECIDE_FORBIDDEN:
				violations.append(violation(PANEL_FILE, node, f"the panel decision names {name} (ADR-044)"))
	return violations


def check_agent_modules_never_reference_panel(sources: dict) -> list:
	"""CHG-008 AC-8 (b): no product file under agent/ names the panel module or its decision method, in code,
	text or comments, so no bot tool can reach the panel's approval path."""
	return [
		f"{rel}: names {needle}"
		for rel, text in scoped(sources, AGENT_PREFIX).items()
		for needle in AGENT_PANEL_NEEDLES
		if needle in text
	]


def check_status_script_constants_match_server(script: str) -> list:
	"""CHG-008: the script's decision actions and statuses are the server's constants, not copies that can drift."""
	expected = {
		"ACTION_APPROVE": change_link.ACTION_APPROVE,
		"ACTION_REJECT": change_link.ACTION_REJECT,
		"STATUS_PENDING": CHANGE_STATUS_PENDING,
		"STATUS_APPLIED": CHANGE_STATUS_APPLIED,
		# ADR-050: the approval message and the kind of the bot's guidance message
		"APPROVE_GUIDANCE_TEXT": prompts.APPROVE_GUIDANCE_TEXT,
		"KIND_GUIDANCE": messages.KIND_GUIDANCE,
	}
	found = []
	for name, value in expected.items():
		# prettier may break a long one after `=` (ADR-050's approval text)
		if not re.search(rf"^\s*const {name} =\s+\"{re.escape(value)}\";\s*$", script, re.MULTILINE):
			found.append(f"{STATUS_SCRIPT_FILE}: const {name} is not the server value {value!r}")
	return found


def check_status_script_decides_once(script: str) -> list:
	"""CHG-008 design 4.2, ADR-044 QĐ 7 (AC-5, AC-11): the decision method is named once, inside `decide`, which
	reloads the panel once per answer (one `reload()` in each of its two branches) and schedules nothing."""
	masked = mask_js(script)
	span = _js_arrow_body_span(masked, "decide")
	if span is None:
		return ["function decide is missing"]
	violations = []
	calls = [m for m in STATUS_SCRIPT_CALL.finditer(script) if m.group(2) == PANEL_DECIDE_METHOD]
	if len(calls) != 1:
		violations.append(f"{PANEL_DECIDE_METHOD} is called {len(calls)} times, expected once")
	for match in calls:
		if not span[0] <= match.start() < span[1]:
			violations.append(
				f"line {js_line(script, match.start())}: {PANEL_DECIDE_METHOD} is called outside decide"
			)
	body = masked[span[0] : span[1]]
	reloads = len(re.findall(r"\breload\(\)", body))
	if reloads != 2:
		violations.append(f"decide calls reload() {reloads} times, expected one per branch (2)")
	for name in ("setTimeout(", "submit("):
		if name in body:
			violations.append(f"decide calls {name}")
	return violations


def check_tool_never_saves_proposal(sources: dict) -> list:
	"""ADR-011 Ràng buộc: a tool only `.insert()`s a proposal. In agent/tools/**, a module that loads or creates a
	proposal has no `.save(`/`db_set`/`set_value` at all; any other module never passes the proposal to one; a
	module that saves/deletes a non-constant DocType has the proposal in every `*DENIED_DOCTYPES` set; site_api
	instead refuses every `api_*` call through its derived deny set before any write (ADR-023)."""
	violations = []
	for rel, source in only_python(scoped(sources, TOOLS_PREFIX)).items():
		tree = parse(rel, source)
		violations.extend(_proposal_deny_violations(rel, tree))
		builds = _builds_proposal(tree)
		for node in ast.walk(tree):
			if not isinstance(node, ast.Call) or referenced_name(node.func) not in PROPOSAL_SAVE_CALLS:
				continue
			function = referenced_name(node.func)
			if builds:
				violations.append(
					violation(
						rel,
						node,
						f"{function} in a tool that builds an {PROPOSAL_DOCTYPE_NAME} (ADR-011: insert only)",
					)
				)
			elif any(_names_proposal(arg) for arg in node.args):
				violations.append(
					violation(rel, node, f"{function} on an {PROPOSAL_DOCTYPE_NAME} in a tool (ADR-011)")
				)
	return violations


# FEAT-004 T32: file-system writes and session/publish in the change path (ADR-013 Ràng buộc) ----------
FILE_WRITER_FILE = "agent/changes/file_writer.py"
# mode is the second positional argument of these; a method `.open(` (Path.open) takes it first
OPEN_FUNCTIONS = ("open", "builtins.open", "io.open", "codecs.open", "os.fdopen")
OPEN_WRITE_MODE_CHARS = frozenset("wax+")
OS_OPEN_READ_FLAGS = frozenset(
	{"O_RDONLY", "O_CLOEXEC", "O_NOFOLLOW", "O_DIRECTORY", "O_NONBLOCK", "O_NOCTTY"}
)
FS_WRITE_FUNCTIONS = frozenset(
	{
		"os.replace",
		"os.rename",
		"os.renames",
		"os.remove",
		"os.unlink",
		"os.rmdir",
		"os.removedirs",
		"os.mkdir",
		"os.makedirs",
		"os.truncate",
		"os.ftruncate",
		"os.write",
		"os.symlink",
		"os.link",
		"os.chmod",
		"os.chown",
	}
)
FS_WRITE_MODULES = ("shutil", "tempfile")  # every function of these copies, moves, creates or removes files
PATH_WRITE_METHODS = (
	"write_text",
	"write_bytes",
	"touch",
	"unlink",
	"mkdir",
	"rmdir",
	"symlink_to",
	"hardlink_to",
)
# Exactly what ADR-013 Ràng buộc names for agent/changes/**: `frappe.set_user`, `publish_realtime`.
CHANGES_FORBIDDEN_NAMES = ("set_user", "publish_realtime")


def _is_fs_write_name(name: str) -> bool:
	return name in FS_WRITE_FUNCTIONS or name.split(".")[0] in FS_WRITE_MODULES


def _leaf_names(node) -> set:
	"""Names in an expression, an attribute chain counted by its last part (`os.O_RDONLY` -> "O_RDONLY")."""
	inner = {id(part.value) for part in ast.walk(node) if isinstance(part, ast.Attribute)}
	return {
		referenced_name(part)
		for part in ast.walk(node)
		if isinstance(part, ast.Name | ast.Attribute) and id(part) not in inner
	}


def _open_write_reason(call: ast.Call, name: str):
	"""Why `call` opens a file for writing, else None. A mode the scan cannot read counts as a write."""
	keywords = _call_keywords(call)
	hidden = "**kwargs" if any(keyword.arg is None for keyword in call.keywords) else None
	if name == "os.open":
		flags = keywords.get("flags", call.args[1] if len(call.args) > 1 else None)
		if flags is None:
			return f"os.open with flags through {hidden}" if hidden else None
		constants = [part for part in ast.walk(flags) if isinstance(part, ast.Constant) and part.value != 0]
		if constants or _leaf_names(flags) - OS_OPEN_READ_FLAGS:
			return "os.open with write flags"
		return None
	method = isinstance(call.func, ast.Attribute) and call.func.attr == "open" and name not in OPEN_FUNCTIONS
	if name not in OPEN_FUNCTIONS and not method:
		return None
	mode = keywords.get("mode")
	if mode is None:
		position = 0 if method else 1
		mode = call.args[position] if len(call.args) > position else None
	if mode is None:
		return f"{name or 'open'} with a mode through {hidden}" if hidden else None
	if isinstance(mode, ast.Constant) and isinstance(mode.value, str):
		return (
			f"{name or 'open'} with mode {mode.value!r}" if OPEN_WRITE_MODE_CHARS & set(mode.value) else None
		)
	return f"{name or 'open'} with a mode that is not a string literal"


def _fs_writes(rel: str, tree: ast.AST):
	"""`(lineno or node, message)` for every file-system write or rename/remove in a module: write-mode opens
	(positional or `mode=`, builtins/io/codecs/os.fdopen/Path.open, os.open flags), the os/shutil/tempfile
	functions however imported or referenced (`from os import replace`, `import shutil as s`, `f = os.remove`)
	and the Path write methods."""
	aliases = import_aliases(tree)
	for lineno, target in imported_modules(tree, module_name(rel), rel.endswith("__init__.py")):
		if _is_fs_write_name(target):
			yield lineno, f"imports {target}"
	inner = {id(node.value) for node in ast.walk(tree) if isinstance(node, ast.Attribute)}
	for node in ast.walk(tree):
		if isinstance(node, ast.Name | ast.Attribute) and id(node) not in inner:
			name = resolved_name(node, aliases)
			if _is_fs_write_name(name):
				yield node, f"uses {name}"
		if not isinstance(node, ast.Call):
			continue
		name = resolved_name(node.func, aliases)
		reason = _open_write_reason(node, name)
		if reason:
			yield node, reason
		elif (
			isinstance(node.func, ast.Attribute)
			and node.func.attr in PATH_WRITE_METHODS
			and not _is_fs_write_name(name)
		):
			yield node, f"calls .{node.func.attr}()"


def check_fs_writes_only_in_file_writer(sources: dict) -> list:
	"""ADR-013 Ràng buộc 2 / design 8.2: in agent/** and the proposal controller, writing, renaming or removing
	files happens only in agent/changes/file_writer.py (erp_ai/eval/ is outside this rule)."""
	violations = []
	for rel, source in only_python(sources).items():
		if rel == FILE_WRITER_FILE or not (rel.startswith(AGENT_PREFIX) or rel == PROPOSAL_CONTROLLER_FILE):
			continue
		for node, message in _fs_writes(rel, parse(rel, source)):
			text = f"{message}: a file-system write outside {FILE_WRITER_FILE} (ADR-013)"
			violations.append(
				f"{rel}:{node}: {text}" if isinstance(node, int) else violation(rel, node, text)
			)
	return violations


FILE_WRITER_CANONICAL_CHECK = "_refuse_unless_canonical"
FILE_WRITER_SECOND_RESOLVER_CALLS = ("realpath", "commonpath", "is_relative_to", "readlink")
FILE_WRITER_RECHECKERS = ("make_parents", "remove_empty_dirs", "write_atomic", "remove_file")
FILE_WRITER_RECHECKS_ALL = True  # condition 4 of the rule; T49 deletes the flag
FILE_WRITER_FS_CALLS = frozenset(
	{"os.mkdir", "os.rmdir", "os.remove", "os.unlink", "os.replace", "os.rename", "tempfile.mkstemp"}
)


def check_file_writer_rechecks_through_resolver(sources: dict) -> list:
	"""ADR-040 Phán quyết C-2: file_writer re-checks a path only by asking the one resolver.
	1. a top-level `_refuse_unless_canonical` calls `source.resolve_safe_path`;
	2. file_writer.py calls no `realpath`/`commonpath`/`is_relative_to`/`readlink` (a second resolver);
	3. every function in FILE_WRITER_RECHECKERS calls `_refuse_unless_canonical`;
	4. (FILE_WRITER_RECHECKS_ALL) every top-level function touching the file system is in FILE_WRITER_RECHECKERS."""
	writer = sources.get(FILE_WRITER_FILE)
	if writer is None:
		return _missing(FILE_WRITER_FILE)
	tree = parse(FILE_WRITER_FILE, writer)
	aliases = import_aliases(tree)
	functions = _module_functions(tree)
	violations = []
	canonical = functions.get(FILE_WRITER_CANONICAL_CHECK)
	if canonical is None:
		violations.append(f"{FILE_WRITER_FILE}: no top-level {FILE_WRITER_CANONICAL_CHECK}() (ADR-040 C-2)")
	elif not any(
		isinstance(node, ast.Call) and resolved_name(node.func, aliases) == SAFE_PATH_CALL
		for node in ast.walk(canonical)
	):
		violations.append(
			violation(
				FILE_WRITER_FILE,
				canonical,
				f"{FILE_WRITER_CANONICAL_CHECK} does not call {SAFE_PATH_CALL} (ADR-040 C-2)",
			)
		)
	for node in ast.walk(tree):
		if not isinstance(node, ast.Call):
			continue
		name = (resolved_name(node.func, aliases) or "").rsplit(".", 1)[-1]
		if name in FILE_WRITER_SECOND_RESOLVER_CALLS:
			violations.append(
				violation(FILE_WRITER_FILE, node, f"calls {name}: a second path resolver (ADR-040 C-2)")
			)
	for name in FILE_WRITER_RECHECKERS:
		function = functions.get(name)
		if function is None:
			violations.append(f"{FILE_WRITER_FILE}: no top-level {name}() (ADR-040 C-2)")
		elif FILE_WRITER_CANONICAL_CHECK not in _called_names(function):
			violations.append(
				violation(
					FILE_WRITER_FILE,
					function,
					f"{name} does not call {FILE_WRITER_CANONICAL_CHECK} (ADR-040 C-2)",
				)
			)
	if FILE_WRITER_RECHECKS_ALL:
		for name, function in functions.items():
			if name in FILE_WRITER_RECHECKERS:
				continue
			if any(
				isinstance(node, ast.Call) and resolved_name(node.func, aliases) in FILE_WRITER_FS_CALLS
				for node in ast.walk(function)
			):
				violations.append(
					violation(
						FILE_WRITER_FILE,
						function,
						f"{name} touches the file system but is not in FILE_WRITER_RECHECKERS (ADR-040 C-2)",
					)
				)
	return violations


def _names_forbidden(name: str) -> bool:
	return any(name == forbidden or name.endswith("." + forbidden) for forbidden in CHANGES_FORBIDDEN_NAMES)


def check_changes_never_set_user_or_publish(sources: dict) -> list:
	"""ADR-013 Ràng buộc ("Trong `erp_ai/agent/changes/**` không có `frappe.set_user`, `publish_realtime`"):
	exactly those two names. Any reference counts (call, alias import, `f = frappe.set_user`, the name as a
	string); reads of `frappe.session.user` are allowed."""
	reason = f"in {CHANGES_PREFIX} (ADR-013)"
	violations = []
	for rel, source in only_python(scoped(sources, CHANGES_PREFIX)).items():
		tree = parse(rel, source)
		aliases = import_aliases(tree)
		for lineno, target in imported_modules(tree, module_name(rel), rel.endswith("__init__.py")):
			if _names_forbidden(target):
				violations.append(f"{rel}:{lineno}: imports {target} {reason}")
		inner = {id(node.value) for node in ast.walk(tree) if isinstance(node, ast.Attribute)}
		for node in ast.walk(tree):
			if isinstance(node, ast.Name | ast.Attribute) and id(node) not in inner:
				name = resolved_name(node, aliases)
				if _names_forbidden(name):
					violations.append(violation(rel, node, f"uses {name} {reason}"))
			elif (
				isinstance(node, ast.Constant)
				and isinstance(node.value, str)
				and _names_forbidden(node.value)
			):
				violations.append(violation(rel, node, f"names {node.value!r} in a string {reason}"))
	return violations


# ---------------------------------------------------------------------------------------------------
# ADR-022 (FEAT-004 T44): git rules. Sets below are hand-written from ADR-022 QĐ 2 on purpose: a product
# constant that widens itself must not widen the rule (the real-code test pins the product constants).
# ---------------------------------------------------------------------------------------------------

SOURCE_MODULE = module_name(SOURCE_TOOL_FILE)
PROCESS_RUNNER_MODULE = module_name(PROCESS_RUNNER_FILE)
CONSTANTS_MODULE = module_name(CONSTANTS_FILE)
GIT_PROGRAM = "git"
GIT_LEGACY_SUBCOMMANDS = frozenset({"log", "blame"})  # the read tool of ADR-013 QĐ 8, kept as it is
GIT_READ_SET = frozenset(
	{"rev-parse", "rev-list", "status", "check-ignore", "ls-files", "merge-base", "diff-tree", "cat-file"}
)
GIT_WRITE_SET = frozenset({"add", "commit", "rm"})
GIT_ALLOWED_SUBCOMMANDS = {
	SOURCE_TOOL_FILE: GIT_LEGACY_SUBCOMMANDS | GIT_READ_SET,
	PROCESS_RUNNER_FILE: GIT_WRITE_SET,
}
GIT_FORBIDDEN_SUBCOMMANDS = (
	"push",
	"fetch",
	"pull",
	"clone",
	"checkout",
	"switch",
	"restore",
	"branch",
	"reset",
	"rebase",
	"merge",
	"cherry-pick",
	"revert",
	"am",
	"apply",
	"stash",
	"clean",
	"tag",
	"remote",
	"config",
	"update-ref",
	"symbolic-ref",
	"reflog",
	"gc",
	"maintenance",
	"worktree",
	"notes",
	"replace",
	"filter-branch",
	"prune",
)
GIT_FORBIDDEN_FRAGMENTS = ("get-url", "ls-remote", "remote.", "--amend", "update-ref")
GIT_CONFIG_PATH = re.compile(r"\.git[/\\]+config\b")
GIT_COMMAND_TEXT = re.compile(r"(?<![\w.-])git\s+([\w-]+)")  # "git push ..." handed to shlex.split
# Global git options that take the next element as their value (so it is not the subcommand).
GIT_OPTIONS_WITH_VALUE = (
	"-C",
	"-c",
	"--git-dir",
	"--work-tree",
	"--namespace",
	"--config-env",
	"--super-prefix",
)
GIT_OPTIONS_FUNCTION = "git_global_options"
GIT_ENV_FUNCTION = "git_env"
GIT_ENV_MARKERS = (
	"GIT_CONFIG_GLOBAL",
	"GIT_CONFIG_NOSYSTEM",
	"GIT_TERMINAL_PROMPT",
	"GIT_AUTHOR_",
	"GIT_COMMITTER_",
	"core.hooksPath",
	"core.fsmonitor",
)
GIT_MARKER_OWNERS = {"core.hooksPath": GIT_OPTIONS_FUNCTION, "core.fsmonitor": GIT_OPTIONS_FUNCTION}
PATHSPEC_SEPARATOR = "--"
PATHSPEC_MAGIC = ":"
COMMIT_REQUIRED_FLAGS = ("--only", "--no-gpg-sign")
COMMIT_FORBIDDEN_FLAGS = (
	"-a",
	"--all",
	"--amend",
	"--allow-empty",
	"--fixup",
	"--squash",
	"-C",
	"-c",
	"--reset-author",
)
COMMIT_FORBIDDEN_SHORT = frozenset(flag[1] for flag in COMMIT_FORBIDDEN_FLAGS if not flag.startswith("--"))
COMMIT_MESSAGE_FLAGS = ("-m", "--message")  # the next element is the message, not an option
RM_REQUIRED_FLAG = "--cached"
BOT_NAME_CONSTANT = "BOT_GIT_NAME"
BOT_EMAIL_CONSTANT = "BOT_GIT_EMAIL"
BOT_GIT_NAME_VALUE = "ERP AI Agent"
BOT_EMAIL_SUFFIX = ".invalid"
BOT_IDENTITY_ENV = {
	"GIT_AUTHOR_NAME": BOT_NAME_CONSTANT,
	"GIT_COMMITTER_NAME": BOT_NAME_CONSTANT,
	"GIT_AUTHOR_EMAIL": BOT_EMAIL_CONSTANT,
	"GIT_COMMITTER_EMAIL": BOT_EMAIL_CONSTANT,
}
USER_IDENTITY_FRAGMENTS = ("user.name", "user.email")
AGENT_USER_NAME = "AGENT_USER"
GIT_FUNCTION_NAMES = ("read_git_state", "run_git_read", "_run_git_write")
GIT_FUNCTION_PREFIX = "git_"
GIT_MODULES = (SOURCE_MODULE, PROCESS_RUNNER_MODULE)
NO_GIT_FILES = (PROPOSAL_CONTROLLER_FILE, HANDLERS_FILE, RUNNER_FILE)
BENCH_COMMANDS_NAME = "BENCH_COMMANDS"
GIT_RUNNING_BENCH_SUBCOMMANDS = (
	"update",
	"switch-to-branch",
	"get-app",
	"remove-app",
	"new-app",
	"setup",
	"init",
)
RESTART_BENCH_COMMAND = "restart"  # ADR-040 QĐ 6: the one shape added to the table
FORBIDDEN_BENCH_COMMANDS = (  # ADR-040 QĐ 6: still forbidden
	"execute",
	"console",
	"install-app",
	"uninstall-app",
	"reinstall",
	"backup",
	"restore",
	"set-config",
	"drop-site",
	"new-site",
)
APPS_ROOT_FUNCTION = "get_source_root"
APPS_ROOT_SEGMENT = re.compile(r"(?:^|[/\\])apps(?:[/\\]|$)")
APP_PATH_CALLS = ("get_app_path",)
RESOLVE_DEPTH = 20


class GitArgv(NamedTuple):
	"""One git command line: `elements` are `(file, node, spread)`; `slot` indexes the subcommand;
	`subcommands` is None when the scan cannot prove it is a constant string."""

	rel: str
	node: ast.AST
	elements: list
	git: int | None
	slot: int | None
	subcommands: frozenset | None
	root_rel: str
	root: ast.AST


def _docstring_ids(tree: ast.AST) -> set:
	ids = set()
	for node in ast.walk(tree):
		if isinstance(node, ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef) and node.body:
			first = node.body[0]
			if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant):
				ids.add(id(first.value))
	return ids


def _parameters(function) -> list:
	arguments = function.args
	names = [arg.arg for arg in (*arguments.posonlyargs, *arguments.args, *arguments.kwonlyargs)]
	return names + ([arguments.vararg.arg] if arguments.vararg else [])


class GitScan:
	"""Every git command line of the product (ADR-022 Ràng buộc).

	A command line is a list/tuple display or a `+` concatenation with a "git" element (also `/usr/bin/git`,
	a module constant, an f-string or a `*`-spread constant list of any product module, imported under any
	alias). The subcommand is the first element after "git" that is not a global option. When that element
	is a parameter of the enclosing function (`run_git_read(repo, subcommand, *args)`,
	`_run_git_write(..., subcommand_args)`), the command line is expanded at every call site of that
	function; when it is a local name, it must be gated by `if name not in <constant set>: return/raise`.
	Anything else is "not a constant" (`subcommands=None`).
	"""

	def __init__(self, sources: dict):
		self.trees = {rel: parse(rel, source) for rel, source in only_python(sources).items()}
		self.aliases = {rel: import_aliases(tree) for rel, tree in self.trees.items()}
		self.files = {module_name(rel): rel for rel in self.trees}
		self.assignments = {rel: self._module_assignments(tree) for rel, tree in self.trees.items()}
		self.parents = {
			rel: {id(child): node for node in ast.walk(tree) for child in ast.iter_child_nodes(node)}
			for rel, tree in self.trees.items()
		}
		self.problems = []
		self.templates = []  # (rel, root, elements, git index) of every command line as written
		self.argvs = []
		for rel, tree in self.trees.items():
			for root in self._roots(rel, tree):
				elements = self.flatten(rel, root)
				git = self.git_index(elements)
				if git is not None:
					self._add(rel, root, elements, git)

	@staticmethod
	def _module_assignments(tree: ast.AST) -> dict:
		names = {}
		for node in tree.body:
			if (
				isinstance(node, ast.Assign)
				and len(node.targets) == 1
				and isinstance(node.targets[0], ast.Name)
			):
				names[node.targets[0].id] = node.value
			elif (
				isinstance(node, ast.AnnAssign)
				and isinstance(node.target, ast.Name)
				and node.value is not None
			):
				names[node.target.id] = node.value
		return names

	# value resolution ------------------------------------------------------------------------------

	def lookup(self, rel: str, node):
		"""`(file, value node)` of the module constant a Name/Attribute refers to, in any product module."""
		if isinstance(node, ast.Name) and node.id in self.assignments.get(rel, {}):
			return rel, self.assignments[rel][node.id]
		if not isinstance(node, ast.Name | ast.Attribute):
			return None
		module, _dot, name = resolved_name(node, self.aliases.get(rel, {})).rpartition(".")
		target = self.files.get(module)
		if target is not None and name in self.assignments[target]:
			return target, self.assignments[target][name]
		return None

	def text(self, rel: str, node, depth: int = 0):
		"""The string a node always evaluates to, else None."""
		if depth > RESOLVE_DEPTH:
			return None
		if isinstance(node, ast.Constant):
			return node.value if isinstance(node.value, str) else None
		if isinstance(node, ast.JoinedStr):
			parts = [self.text(rel, value, depth + 1) for value in node.values]
			return None if None in parts else "".join(parts)
		if isinstance(node, ast.FormattedValue):
			plain = node.conversion == -1 and node.format_spec is None
			return self.text(rel, node.value, depth + 1) if plain else None
		if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
			left, right = self.text(rel, node.left, depth + 1), self.text(rel, node.right, depth + 1)
			return None if left is None or right is None else left + right
		found = self.lookup(rel, node)
		return self.text(*found, depth + 1) if found else None

	def prefix(self, rel: str, node) -> str:
		"""The constant text a string expression starts with (`f":(literal){rel}"` -> ":(literal)")."""
		if isinstance(node, ast.JoinedStr) and node.values:
			return self.text(rel, node.values[0]) or ""
		if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
			return self.prefix(rel, node.left)
		return self.text(rel, node) or ""

	def strings(self, rel: str, node, depth: int = 0):
		"""The frozenset of strings a constant set/tuple/list (or `frozenset(...)` of one) holds, else None."""
		if depth > RESOLVE_DEPTH:
			return None
		if (
			isinstance(node, ast.Call)
			and referenced_name(node.func) in SET_LITERAL_CALLS
			and len(node.args) == 1
			and not node.keywords
		):
			return self.strings(rel, node.args[0], depth + 1)
		if isinstance(node, ast.Set | ast.List | ast.Tuple):
			found = set()
			for element in node.elts:
				if isinstance(element, ast.Starred):
					inner = self.strings(rel, element.value, depth + 1)
					if inner is None:
						return None
					found |= inner
				else:
					value = self.text(rel, element, depth + 1)
					if value is None:
						return None
					found.add(value)
			return frozenset(found)
		if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr | ast.Add):
			left, right = self.strings(rel, node.left, depth + 1), self.strings(rel, node.right, depth + 1)
			return None if left is None or right is None else left | right
		found = self.lookup(rel, node)
		return self.strings(*found, depth + 1) if found else None

	def code_texts(self, rel: str):
		"""`(node, text)` for every string of the code (docstrings excluded, f-string pieces and resolved
		concatenations included) and every keyword-argument name (`dict(GIT_CONFIG_GLOBAL=...)`)."""
		docstrings = _docstring_ids(self.trees[rel])
		for node in ast.walk(self.trees[rel]):
			if isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in docstrings:
				yield node, node.value
			elif isinstance(node, ast.JoinedStr | ast.BinOp):
				value = self.text(rel, node)
				if value is not None:
					yield node, value
			elif isinstance(node, ast.keyword) and node.arg:
				yield node, node.arg

	# command lines ---------------------------------------------------------------------------------

	def is_construct(self, node) -> bool:
		if isinstance(node, ast.List | ast.Tuple):
			return True
		return (
			isinstance(node, ast.BinOp)
			and isinstance(node.op, ast.Add)
			and (self.is_construct(node.left) or self.is_construct(node.right))
		)

	def _roots(self, rel: str, tree: ast.AST):
		parents = self.parents[rel]
		for node in ast.walk(tree):
			if not self.is_construct(node):
				continue
			parent = parents.get(id(node))
			if isinstance(parent, ast.BinOp) and self.is_construct(parent):
				continue
			if isinstance(parent, ast.Starred) and isinstance(parents.get(id(parent)), ast.List | ast.Tuple):
				continue
			yield node

	def flatten(self, rel: str, node, depth: int = 0) -> list:
		if depth > RESOLVE_DEPTH:
			return [(rel, node, True)]
		if isinstance(node, ast.List | ast.Tuple):
			elements = []
			for element in node.elts:
				if isinstance(element, ast.Starred):
					elements += self.spread(rel, element.value, depth + 1)
				else:
					elements.append((rel, element, False))
			return elements
		if isinstance(node, ast.BinOp) and self.is_construct(node):
			return self.spread(rel, node.left, depth + 1) + self.spread(rel, node.right, depth + 1)
		return [(rel, node, True)]

	def spread(self, rel: str, node, depth: int = 0) -> list:
		"""The elements `*node` (or a `+` operand) adds; an unknown value stays one spread element."""
		if self.is_construct(node):
			return self.flatten(rel, node, depth)
		found = self.lookup(rel, node)
		if found and self.is_construct(found[1]):
			return self.flatten(*found, depth)
		return [(rel, node, True)]

	def git_index(self, elements: list):
		for index, (rel, node, spread) in enumerate(elements):
			value = None if spread else self.text(rel, node)
			if value is not None and os.path.basename(value) == GIT_PROGRAM:
				return index
		return None

	def is_options_call(self, rel: str, node) -> bool:
		return self._is_source_call(rel, node, GIT_OPTIONS_FUNCTION)

	def is_env_call(self, rel: str, node) -> bool:
		return self._is_source_call(rel, node, GIT_ENV_FUNCTION)

	def _is_source_call(self, rel: str, node, function: str) -> bool:
		if not isinstance(node, ast.Call):
			return False
		name = resolved_name(node.func, self.aliases.get(rel, {}))
		return name == f"{SOURCE_MODULE}.{function}" or (rel == SOURCE_TOOL_FILE and name == function)

	def slot(self, elements: list, start: int):
		index = start
		while index < len(elements):
			rel, node, spread = elements[index]
			if spread and self.is_options_call(rel, node):
				index += 1
				continue
			value = None if spread else self.text(rel, node)
			if value is None or not value.startswith("-"):
				return index
			index += 2 if value in GIT_OPTIONS_WITH_VALUE else 1
		return None

	def function_of(self, rel: str, node):
		parents = self.parents[rel]
		while (node := parents.get(id(node))) is not None:
			if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.Lambda):
				return node
		return None

	def _add(self, rel: str, root, elements: list, git: int) -> None:
		self.templates.append((rel, root, elements, git))
		self._check_not_mutated(rel, root)
		slot = self.slot(elements, git + 1)
		if slot is None:
			self.argvs.append(GitArgv(rel, root, elements, git, None, None, rel, root))
			return
		element_rel, node, spread = elements[slot]
		value = None if spread else self.text(element_rel, node)
		function = self.function_of(rel, root)
		subcommands = None if value is None else frozenset({value})
		if subcommands is None and isinstance(node, ast.Name) and function is not None and element_rel == rel:
			if node.id in _parameters(function) and not isinstance(function, ast.Lambda):
				self._expand(rel, root, elements, function)
				return
			if not spread:
				subcommands = self.guard(rel, function, node.id, root.lineno)
		self.argvs.append(GitArgv(rel, root, elements, git, slot, subcommands, rel, root))

	def _check_not_mutated(self, rel: str, root) -> None:
		parent = self.parents[rel].get(id(root))
		if not (
			isinstance(parent, ast.Assign)
			and len(parent.targets) == 1
			and isinstance(parent.targets[0], ast.Name)
		):
			return
		name = parent.targets[0].id
		scope = self.function_of(rel, parent) or self.trees[rel]
		for node in ast.walk(scope):
			changed = (
				isinstance(node, ast.AugAssign)
				and isinstance(node.target, ast.Name)
				and node.target.id == name
			) or (
				isinstance(node, ast.Call)
				and isinstance(node.func, ast.Attribute)
				and isinstance(node.func.value, ast.Name)
				and node.func.value.id == name
				and node.func.attr in ("append", "extend", "insert", "__iadd__")
			)
			if changed:
				self.problems.append(
					violation(rel, node, f"git command line {name!r} is changed after it is built")
				)

	def guard(self, rel: str, function, name: str, before: int):
		"""The constant set of `if ... name not in SET ...: return/raise` ahead of `before`, else None."""
		for node in ast.walk(function):
			if not (
				isinstance(node, ast.If)
				and node.lineno < before
				and isinstance(node.body[-1], ast.Return | ast.Raise)
				and self._unconditional(rel, function, node)
			):
				continue
			tests = (
				node.test.values
				if isinstance(node.test, ast.BoolOp) and isinstance(node.test.op, ast.Or)
				else [node.test]
			)
			for test in tests:
				if (
					isinstance(test, ast.Compare)
					and isinstance(test.left, ast.Name)
					and test.left.id == name
					and len(test.ops) == 1
					and isinstance(test.ops[0], ast.NotIn)
					and not self._rebound(function, name, node.lineno, before)
				):
					allowed = self.strings(rel, test.comparators[0])
					if allowed is not None:
						return allowed
		return None

	def _unconditional(self, rel: str, function, node) -> bool:
		"""`node` sits in the function body itself or only inside `try:` bodies of it."""
		parents = self.parents[rel]
		child, parent = node, parents.get(id(node))
		while parent is not function:
			if not (isinstance(parent, ast.Try) and child in parent.body):
				return False
			child, parent = parent, parents.get(id(parent))
		return True

	@staticmethod
	def _rebound(function, name: str, after: int, before: int) -> bool:
		return any(
			isinstance(node, ast.Name)
			and node.id == name
			and isinstance(node.ctx, ast.Store)
			and after < node.lineno < before
			for node in ast.walk(function)
		)

	def _expand(self, rel: str, root, elements: list, function) -> None:
		for call_rel, call in self.calls_of(rel, function):
			expanded = self.substitute(rel, elements, function, call_rel, call)
			git = self.git_index(expanded)
			slot = None if git is None else self.slot(expanded, git + 1)
			subcommands = None
			if slot is not None:
				element_rel, node, spread = expanded[slot]
				value = None if spread else self.text(element_rel, node)
				subcommands = None if value is None else frozenset({value})
			self.argvs.append(GitArgv(call_rel, call, expanded, git, slot, subcommands, rel, root))

	def calls_of(self, rel: str, function) -> list:
		"""Every direct call of `function` in the product; any other use of it is a problem."""
		target = f"{module_name(rel)}.{function.name}"
		calls = []
		for other, tree in self.trees.items():
			aliases = self.aliases[other]
			callees = {id(node.func) for node in ast.walk(tree) if isinstance(node, ast.Call)}
			inner = {id(node.value) for node in ast.walk(tree) if isinstance(node, ast.Attribute)}
			for node in ast.walk(tree):
				if not isinstance(node, ast.Name | ast.Attribute) or id(node) in inner:
					continue
				same_file = other == rel and isinstance(node, ast.Name) and node.id == function.name
				if not same_file and resolved_name(node, aliases) != target:
					continue
				if id(node) in callees:
					calls.append((other, self.parents[other][id(node)]))
				else:
					self.problems.append(
						violation(
							other,
							node,
							f"{function.name} puts its parameter in the git subcommand slot and is used other than by a direct call",
						)
					)
		return calls

	def substitute(self, rel: str, elements: list, function, call_rel: str, call: ast.Call) -> list:
		"""The template command line with each parameter replaced by what this call passes."""
		arguments = function.args
		positional = [arg.arg for arg in (*arguments.posonlyargs, *arguments.args)]
		named = positional + [arg.arg for arg in arguments.kwonlyargs]
		vararg = arguments.vararg.arg if arguments.vararg else None
		splat = next((i for i, arg in enumerate(call.args) if isinstance(arg, ast.Starred)), len(call.args))
		keywords = {keyword.arg: keyword.value for keyword in call.keywords if keyword.arg}

		def argument(name):
			index = positional.index(name) if name in positional else len(call.args)
			if index < len(call.args):
				return call.args[index] if index < splat else None
			return keywords.get(name)

		expanded = []
		for element_rel, node, spread in elements:
			if element_rel != rel or not isinstance(node, ast.Name):
				expanded.append((element_rel, node, spread))
			elif node.id == vararg and spread:
				if splat < len(positional):
					expanded.append((call_rel, call, True))
					continue
				for arg in call.args[len(positional) :]:
					if isinstance(arg, ast.Starred):
						expanded += self.spread(call_rel, arg.value)
					else:
						expanded.append((call_rel, arg, False))
			elif node.id in named:
				arg = argument(node.id)
				if arg is None:
					expanded.append((call_rel, call, True))
				else:
					expanded += self.spread(call_rel, arg) if spread else [(call_rel, arg, False)]
			else:
				expanded.append((element_rel, node, spread))
		return expanded

	def consumer(self, rel: str, root):
		"""The call that runs a command line: the call it is an argument of, or that gets the name it is bound to."""
		parents = self.parents[rel]
		node = root
		while (parent := parents.get(id(node))) is not None:
			if isinstance(parent, ast.Call) and node is not parent.func:
				return parent
			if (
				isinstance(parent, ast.Assign)
				and len(parent.targets) == 1
				and isinstance(parent.targets[0], ast.Name)
			):
				name = parent.targets[0].id
				scope = self.function_of(rel, parent) or self.trees[rel]
				for call in ast.walk(scope):
					if isinstance(call, ast.Call) and any(
						isinstance(arg, ast.Name) and arg.id == name
						for arg in (*call.args, *(keyword.value for keyword in call.keywords))
					):
						return call
				return None
			if isinstance(parent, ast.stmt):
				return None
			node = parent
		return None

	def is_legacy(self, rel: str, root) -> bool:
		"""The log/blame command of the read tool (ADR-022 QĐ 4: kept as it is, not a new git command)."""
		found = [argv for argv in self.argvs if argv.root is root and argv.root_rel == rel]
		return (
			rel == SOURCE_TOOL_FILE
			and bool(found)
			and all(
				argv.node is root
				and argv.subcommands is not None
				and argv.subcommands <= GIT_LEGACY_SUBCOMMANDS
				for argv in found
			)
		)

	def outermost_names(self, rel: str, root):
		"""Name/Attribute nodes under `root` that are not the base of a longer attribute chain."""
		inner = {id(node.value) for node in ast.walk(root) if isinstance(node, ast.Attribute)}
		for node in ast.walk(root):
			if isinstance(node, ast.Name | ast.Attribute) and id(node) not in inner:
				yield node, resolved_name(node, self.aliases[rel])


def check_git_subcommands_only_allowed_sets_per_file(sources: dict) -> list:
	"""ADR-022 QĐ 2, Ràng buộc: git runs only from source.py (log/blame + the read set) and process_runner.py
	(add/commit/rm); every subcommand is a constant string; no other product file has "git" in a command line."""
	scan = GitScan(sources)
	violations = list(scan.problems)
	for rel, root, _elements, _git in scan.templates:
		if rel not in GIT_ALLOWED_SUBCOMMANDS:
			violations.append(
				violation(
					rel,
					root,
					f'"git" in a command line outside {tuple(GIT_ALLOWED_SUBCOMMANDS)} (ADR-022 QĐ 2)',
				)
			)
	for argv in scan.argvs:
		allowed = GIT_ALLOWED_SUBCOMMANDS.get(argv.root_rel)
		if allowed is None:
			continue  # reported above
		if argv.subcommands is None:
			violations.append(
				violation(argv.rel, argv.node, "git subcommand is not a constant string (ADR-022 Ràng buộc)")
			)
		elif argv.subcommands - allowed:
			violations.append(
				violation(
					argv.rel,
					argv.node,
					f"git subcommand {sorted(argv.subcommands - allowed)} not allowed for {argv.root_rel} (ADR-022 QĐ 2)",
				)
			)
	return violations


def _path_parts(scan: GitScan, rel: str):
	"""`(node, [text or None])` for the arguments of every call and every `a / b / c` or `a + b + c` chain."""
	parents = scan.parents[rel]
	for node in ast.walk(scan.trees[rel]):
		if isinstance(node, ast.Call):
			yield node, [scan.text(rel, arg) for arg in node.args]
		elif isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div | ast.Add):
			parent = parents.get(id(node))
			if isinstance(parent, ast.BinOp) and type(parent.op) is type(node.op):
				continue
			operands, chain = [], node
			while isinstance(chain, ast.BinOp) and type(chain.op) is type(node.op):
				operands.insert(0, chain.right)
				chain = chain.left
			yield node, [scan.text(rel, part) for part in (chain, *operands)]


def check_no_forbidden_git_operations_in_product(sources: dict) -> list:
	"""ADR-022 QĐ 2, Ràng buộc: none of the 30 forbidden subcommands in a git command line; no string of the
	product names get-url, ls-remote, remote., --amend or update-ref; nothing reads .git/config."""
	scan = GitScan(sources)
	violations = []
	command_lines = [(rel, root, elements, git) for rel, root, elements, git in scan.templates]
	command_lines += [
		(argv.rel, argv.node, argv.elements, argv.git) for argv in scan.argvs if argv.git is not None
	]
	for rel, node, elements, git in command_lines:
		for element_rel, element, spread in elements[git + 1 :]:
			value = None if spread else scan.text(element_rel, element)
			if value in GIT_FORBIDDEN_SUBCOMMANDS:
				violations.append(violation(rel, node, f"git command line holds {value!r} (ADR-022 QĐ 2)"))
	for rel in scan.trees:
		for node, value in scan.code_texts(rel):
			violations.extend(
				violation(rel, node, f"string names {fragment} (ADR-022 Ràng buộc)")
				for fragment in GIT_FORBIDDEN_FRAGMENTS
				if fragment in value
			)
			if GIT_CONFIG_PATH.search(value):
				violations.append(violation(rel, node, "string names .git/config (ADR-022 Ràng buộc)"))
			if rel in SUBPROCESS_FILES:
				violations.extend(
					violation(rel, node, f"string runs git {token!r} (ADR-022 QĐ 2)")
					for token in GIT_COMMAND_TEXT.findall(value)
					if token in GIT_FORBIDDEN_SUBCOMMANDS
				)
				if value == "config" or value.endswith(("/config", "\\config")):
					violations.append(
						violation(rel, node, "string names a git config file (ADR-022 Ràng buộc)")
					)
		for node, parts in _path_parts(scan, rel):
			for first, second in itertools.pairwise(parts):
				if (
					first is not None
					and second is not None
					and os.path.basename(first.rstrip("/\\")) == ".git"
					and second.lstrip("/\\").startswith("config")
				):
					violations.append(
						violation(rel, node, "path .git + config: reads the git config (ADR-022 Ràng buộc)")
					)
	return violations


def _commit_flag_forbidden(flag: str) -> bool:
	name = flag.split("=", 1)[0]
	if name in COMMIT_FORBIDDEN_FLAGS:
		return True
	if name.startswith("--"):  # git accepts an unambiguous abbreviation of a long option
		return len(name) > 2 and any(forbidden.startswith(name) for forbidden in COMMIT_FORBIDDEN_FLAGS)
	return name.startswith("-") and bool(set(name[1:]) & COMMIT_FORBIDDEN_SHORT)


def _write_argv_problems(scan: GitScan, subcommand: str, tail: list) -> list:
	"""What is wrong with the elements after `add`/`commit`/`rm` (ADR-022 Ràng buộc; addendum 2 QĐ-A1; ADR-040:
	commit ends with "--" and 1..N paths, a spread allowed only after "--"; add and rm with exactly one path)."""
	texts = [None if spread else scan.text(rel, node) for rel, node, spread in tail]
	separators = [index for index, value in enumerate(texts) if value == PATHSPEC_SEPARATOR]
	if any(spread for _rel, _node, spread in tail[: separators[0] if separators else len(tail)]):
		return ["has an argument the scan cannot read (a spread or a list that is not constant)"]
	paths = tail[separators[0] + 1 :] if separators else []
	if subcommand == "commit":
		if len(separators) != 1 or not paths:
			return [f'must end with "{PATHSPEC_SEPARATOR}" and one or more paths']
	elif len(separators) != 1 or len(paths) != 1 or paths[0][2]:
		return [f'must end with "{PATHSPEC_SEPARATOR}" and exactly one path']
	problems = []
	for path_rel, path, spread in paths:
		if not spread and scan.prefix(path_rel, path).startswith(PATHSPEC_MAGIC):
			problems.append(
				f'path after "{PATHSPEC_SEPARATOR}" starts with "{PATHSPEC_MAGIC}" (pathspec magic)'
			)
	options, message_next = [], False
	for value in texts[: separators[0]]:
		if message_next:
			message_next = False
		elif value is None:
			problems.append(f'has an argument before "{PATHSPEC_SEPARATOR}" that is not a constant string')
		elif value in COMMIT_MESSAGE_FLAGS and subcommand == "commit":
			message_next = True
		else:
			options.append(value)
	if subcommand == "commit":
		problems += [f"without {flag}" for flag in COMMIT_REQUIRED_FLAGS if flag not in options]
		problems += [f"with forbidden {flag}" for flag in options if _commit_flag_forbidden(flag)]
	elif subcommand == "rm" and RM_REQUIRED_FLAG not in options:
		problems.append(f"without {RM_REQUIRED_FLAG}")
	return problems


def check_git_commit_add_rm_argv_shape(sources: dict) -> list:
	"""ADR-022 Ràng buộc, design-addendum-2 QĐ-A1, ADR-040: commit has --only and --no-gpg-sign and ends with "--"
	and 1..N paths, add/rm end with "--" and exactly one path, no known path starts with ":", rm has --cached,
	commit has no forbidden flag."""
	scan = GitScan(sources)
	violations = []
	for argv in scan.argvs:
		if argv.slot is None or not argv.subcommands:
			continue
		tail = argv.elements[argv.slot + 1 :]
		for subcommand in sorted(argv.subcommands & GIT_WRITE_SET):
			violations.extend(
				violation(argv.rel, argv.node, f"git {subcommand} {problem} (ADR-022 Ràng buộc)")
				for problem in _write_argv_problems(scan, subcommand, tail)
			)
	return violations


def check_git_env_single_definition(sources: dict) -> list:
	"""ADR-022 QĐ 4, Ràng buộc: the git options and environment are defined once, in source.py; every new git
	command line starts with *git_global_options(...) and runs with env=git_env(...), never os.environ."""
	scan = GitScan(sources)
	violations = []
	for rel in scan.trees:
		for node, value in scan.code_texts(rel):
			for marker in GIT_ENV_MARKERS:
				if marker not in value:
					continue
				owner = GIT_MARKER_OWNERS.get(marker, GIT_ENV_FUNCTION)
				function = scan.function_of(rel, node)
				if rel != SOURCE_TOOL_FILE or function is None or getattr(function, "name", None) != owner:
					violations.append(
						violation(rel, node, f"{marker} outside {SOURCE_TOOL_FILE} {owner}() (ADR-022 QĐ 4)")
					)
	for function_name in (GIT_OPTIONS_FUNCTION, GIT_ENV_FUNCTION):
		definitions = [
			violation(rel, node, f"defines {function_name}()")
			for rel, tree in scan.trees.items()
			for node in ast.walk(tree)
			if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and node.name == function_name
		]
		if len(definitions) != 1 or not definitions[0].startswith(f"{SOURCE_TOOL_FILE}:"):
			violations.append(
				f"{function_name}() must be defined once, in {SOURCE_TOOL_FILE}: {definitions} (ADR-022 QĐ 4)"
			)
	for rel, root, elements, git in scan.templates:
		if scan.is_legacy(rel, root):
			continue
		following = elements[git + 1] if git + 1 < len(elements) else None
		if following is None or not (following[2] and scan.is_options_call(following[0], following[1])):
			violations.append(
				violation(
					rel,
					root,
					f'git command line without *{GIT_OPTIONS_FUNCTION}(...) right after "git" (ADR-022 QĐ 4)',
				)
			)
		consumer = scan.consumer(rel, root)
		env = None if consumer is None else _call_keywords(consumer).get("env")
		if env is None or not scan.is_env_call(rel, env):
			violations.append(
				violation(
					rel,
					root,
					f"git command line not run with env={GIT_ENV_FUNCTION}(...) of {SOURCE_TOOL_FILE} (ADR-022 QĐ 4)",
				)
			)
		elif any(resolved_name(part, scan.aliases[rel]) == "os.environ" for part in ast.walk(env)):
			violations.append(violation(rel, root, "git env= uses os.environ (ADR-022 Ràng buộc)"))
	if PROCESS_RUNNER_FILE in scan.trees:
		for function_name in (GIT_OPTIONS_FUNCTION, GIT_ENV_FUNCTION):
			calls = [
				node
				for node in ast.walk(scan.trees[PROCESS_RUNNER_FILE])
				if scan._is_source_call(PROCESS_RUNNER_FILE, node, function_name)
			]
			if not calls:
				violations.append(
					f"{PROCESS_RUNNER_FILE}: never calls source.{function_name}() (ADR-022 QĐ 4: reuse, no second git setup)"
				)
	return violations


def _env_entries(scan: GitScan, rel: str):
	"""`(node, key, value node)` for dict entries, keyword arguments and `x["KEY"] = value` assignments."""
	for node in ast.walk(scan.trees[rel]):
		if isinstance(node, ast.Dict):
			for key, value in zip(node.keys, node.values, strict=True):
				if key is not None and scan.text(rel, key) is not None:
					yield key, scan.text(rel, key), value
		elif isinstance(node, ast.keyword) and node.arg:
			yield node, node.arg, node.value
		elif isinstance(node, ast.Assign):
			for target in node.targets:
				if isinstance(target, ast.Subscript) and scan.text(rel, target.slice) is not None:
					yield target, scan.text(rel, target.slice), node.value


def check_bot_identity_constants(sources: dict) -> list:
	"""ADR-022 QĐ 5: the bot identity is erp_ai.constants (name "ERP AI Agent", address ending .invalid), the four
	GIT_AUTHOR_*/GIT_COMMITTER_* variables take it, and git code never uses user.name/user.email/AGENT_USER."""
	scan = GitScan(sources)
	constants = scan.assignments.get(CONSTANTS_FILE)
	if constants is None:
		return [f"{CONSTANTS_FILE}: file missing (ADR-022 QĐ 5)"]
	violations = []
	name = scan.text(CONSTANTS_FILE, constants[BOT_NAME_CONSTANT]) if BOT_NAME_CONSTANT in constants else None
	if name != BOT_GIT_NAME_VALUE:
		violations.append(
			f"{CONSTANTS_FILE}: {BOT_NAME_CONSTANT} = {name!r}, not {BOT_GIT_NAME_VALUE!r} (ADR-022 QĐ 5)"
		)
	email = (
		scan.text(CONSTANTS_FILE, constants[BOT_EMAIL_CONSTANT]) if BOT_EMAIL_CONSTANT in constants else None
	)
	local, at, domain = (email or "").partition("@")
	if not (
		local
		and at
		and "@" not in domain
		and domain.endswith(BOT_EMAIL_SUFFIX)
		and len(domain) > len(BOT_EMAIL_SUFFIX)
	):
		violations.append(
			f"{CONSTANTS_FILE}: {BOT_EMAIL_CONSTANT} = {email!r} is not an address ending {BOT_EMAIL_SUFFIX} (ADR-022 QĐ 5)"
		)
	set_in_source = set()
	for rel in scan.trees:
		for node, key, value in _env_entries(scan, rel):
			if key not in BOT_IDENTITY_ENV:
				continue
			expected = f"{CONSTANTS_MODULE}.{BOT_IDENTITY_ENV[key]}"
			if resolved_name(value, scan.aliases[rel]) != expected:
				violations.append(violation(rel, node, f"{key} is not set from {expected} (ADR-022 QĐ 5)"))
			elif rel == SOURCE_TOOL_FILE:
				set_in_source.add(key)
	violations.extend(
		f"{SOURCE_TOOL_FILE}: {key} is never set from the bot constant (ADR-022 QĐ 5)"
		for key in BOT_IDENTITY_ENV
		if key not in set_in_source
	)
	for rel in SUBPROCESS_FILES:
		if rel not in scan.trees:
			continue
		for node, value in scan.code_texts(rel):
			if value == AGENT_USER_NAME or any(fragment in value for fragment in USER_IDENTITY_FRAGMENTS):
				violations.append(violation(rel, node, f"git code names {value!r} (ADR-022 QĐ 5)"))
		for lineno, target in imported_modules(scan.trees[rel], module_name(rel), False):
			if target.split(".")[-1] == AGENT_USER_NAME:
				violations.append(f"{rel}:{lineno}: imports {target} (ADR-022 QĐ 5)")
		for node, name in scan.outermost_names(rel, scan.trees[rel]):
			if name.split(".")[-1] == AGENT_USER_NAME:
				violations.append(violation(rel, node, f"git code uses {name} (ADR-022 QĐ 5)"))
	return violations


def _git_function_names(scan: GitScan) -> set:
	names = set(GIT_FUNCTION_NAMES)
	for module in GIT_MODULES:
		rel = scan.files.get(module)
		if rel is not None:
			names |= {
				node.name
				for node in scan.trees[rel].body
				if isinstance(node, ast.FunctionDef) and node.name.startswith(GIT_FUNCTION_PREFIX)
			}
	return names


def _is_git_function(dotted: str) -> bool:
	module, _dot, name = dotted.rpartition(".")
	return module in GIT_MODULES and (name in GIT_FUNCTION_NAMES or name.startswith(GIT_FUNCTION_PREFIX))


def _git_uses(scan: GitScan, rel: str, root, git_names: set):
	"""`(node, what)` for subprocess and git-function uses inside `root` (a module or a function)."""
	for lineno, target in imported_modules(root, module_name(rel), rel.endswith("__init__.py")):
		if (
			module_in(target, "subprocess")
			or module_in(target, PROCESS_RUNNER_MODULE)
			or _is_git_function(target)
		):
			yield lineno, f"imports {target}"
	for node, name in scan.outermost_names(rel, root):
		if module_in(name, "subprocess") or _is_git_function(name):
			yield node, f"uses {name}"
	docstrings = _docstring_ids(scan.trees[rel])
	for node in ast.walk(root):
		if (
			isinstance(node, ast.Constant)
			and id(node) not in docstrings
			and (node.value in git_names or node.value in GIT_MODULES)
		):
			yield node, f"names {node.value!r}"
	root_ids = {id(node) for node in ast.walk(root)}
	for template_rel, template, _elements, _git in scan.templates:
		if template_rel == rel and id(template) in root_ids:
			yield template, 'builds a "git" command line'


def check_no_git_in_web_and_runner(sources: dict) -> list:
	"""ADR-022 QĐ 3, Ràng buộc: the proposal controller, every @frappe.whitelist function (and the module
	functions it calls), handlers.py and agent/runner.py never import subprocess or touch a git function."""
	scan = GitScan(sources)
	git_names = _git_function_names(scan)
	scopes = [(rel, scan.trees[rel], "") for rel in NO_GIT_FILES if rel in scan.trees]
	for rel, function, _decorator in whitelisted_functions(sources):
		functions = _module_functions(scan.trees[rel])
		reached, pending = {function.name: function}, [function]
		while pending:
			for name in _called_names(pending.pop()):
				if name in functions and name not in reached:
					reached[name] = functions[name]
					pending.append(functions[name])
		scopes += [
			(rel, node, f" (reached from @frappe.whitelist {function.name})") for node in reached.values()
		]
	violations = []
	for rel, root, where in scopes:
		for node, what in _git_uses(scan, rel, root, git_names):
			text = f"{what}{where}: no git in web requests, handlers or the runner (ADR-022 QĐ 3)"
			violations.append(
				f"{rel}:{node}: {text}" if isinstance(node, int) else violation(rel, node, text)
			)
	return sorted(set(violations))


def check_bench_allowlist_has_no_git_running_subcommands(sources: dict) -> list:
	"""ADR-022 QĐ 2: change_guard's bench command table never holds a subcommand that runs git in an app repo.
	ADR-040 QĐ 6: the table holds `restart` and none of the commands that stay forbidden."""
	scan = GitScan(sources)
	if CHANGE_GUARD_FILE not in scan.trees:
		return [f"{CHANGE_GUARD_FILE}: file missing"]
	violations = []
	table = scan.assignments[CHANGE_GUARD_FILE].get(BENCH_COMMANDS_NAME)
	commands = None if table is None else scan.strings(CHANGE_GUARD_FILE, table)
	if commands is None:
		violations.append(
			f"{CHANGE_GUARD_FILE}: {BENCH_COMMANDS_NAME} is not a table of constant strings (ADR-022 QĐ 2)"
		)
	else:
		violations.extend(
			f"{CHANGE_GUARD_FILE}: {BENCH_COMMANDS_NAME} holds {command!r}, which runs git in an app repo (ADR-022 QĐ 2)"
			for command in sorted(commands & set(GIT_RUNNING_BENCH_SUBCOMMANDS))
		)
		if RESTART_BENCH_COMMAND not in commands:
			violations.append(
				f"{CHANGE_GUARD_FILE}: {BENCH_COMMANDS_NAME} lacks {RESTART_BENCH_COMMAND!r} (ADR-040 QĐ 6)"
			)
		violations.extend(
			f"{CHANGE_GUARD_FILE}: {BENCH_COMMANDS_NAME} holds {command!r}, which stays forbidden (ADR-040 QĐ 6)"
			for command in sorted(commands & set(FORBIDDEN_BENCH_COMMANDS))
		)
	for node, value in scan.code_texts(CHANGE_GUARD_FILE):
		if value in GIT_RUNNING_BENCH_SUBCOMMANDS:
			violations.append(
				violation(
					CHANGE_GUARD_FILE,
					node,
					f"bench subcommand {value!r} runs git in an app repo (ADR-022 QĐ 2)",
				)
			)
	return violations


def check_apps_root_single_function(sources: dict) -> list:
	"""ADR-022 QĐ 8: in agent/**, only source.get_source_root works out the apps/ root."""
	scan = GitScan(sources)
	violations = []
	definitions = [
		(rel, node)
		for rel, tree in scan.trees.items()
		if rel.startswith(AGENT_PREFIX)
		for node in ast.walk(tree)
		if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and node.name == APPS_ROOT_FUNCTION
	]
	if [rel for rel, _node in definitions] != [SOURCE_TOOL_FILE] or definitions[0][1] not in scan.trees[
		SOURCE_TOOL_FILE
	].body:
		violations.append(
			f"{APPS_ROOT_FUNCTION}() must be defined once, at module level of {SOURCE_TOOL_FILE}: "
			f"{[violation(rel, node, 'def') for rel, node in definitions]} (ADR-022 QĐ 8)"
		)
	for rel, tree in scan.trees.items():
		if not rel.startswith(AGENT_PREFIX):
			continue

		def in_root_function(node, rel=rel):
			function = scan.function_of(rel, node)
			return rel == SOURCE_TOOL_FILE and getattr(function, "name", None) == APPS_ROOT_FUNCTION

		for node, value in scan.code_texts(rel):
			if APPS_ROOT_SEGMENT.search(value) and not in_root_function(node):
				violations.append(
					violation(rel, node, f"path {value!r} outside {APPS_ROOT_FUNCTION}() (ADR-022 QĐ 8)")
				)
		for node in ast.walk(tree):
			if isinstance(node, ast.Call) and not in_root_function(node):
				name = resolved_name(node.func, scan.aliases[rel])
				if name.split(".")[-1] in APP_PATH_CALLS:
					violations.append(
						violation(rel, node, f"{name} outside {APPS_ROOT_FUNCTION}() (ADR-022 QĐ 8)")
					)
	return violations


# FEAT-004 T68: ADR-023 Ràng buộc. The site_api rule (no hand-written set of the app's DocTypes) is
# already part of check_tool_never_saves_proposal (_site_api_deny_violations, T59) and is not repeated.
CHANGE_LINK_FILE = "agent/change_link.py"
AGENT_WRITE_GUARD_FILE = "agent/agent_write_guard.py"
CHANGE_STATE_NAMES = ("approve", "reject", "undo")
GET_METHOD = "GET"
API_METHOD_PATH = "api/method/"
UNKNOWN_PIECE = "\0"  # stands for a piece of a string whose value is not known statically
REMOVED_GRANT_NAMES = ("_unrestricted_specs", "get_unrestricted_tool_schemas")
GRANT_TABLE_NAME = "GRANT_TABLE"
SCHEMA_FUNCTION = "get_tool_schemas"
SCHEMA_CALL_MARK = "schema"
RUNNER_SCHEMA_CALL = "schemas"
SPEC_SOURCE = "_all_specs"
IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
TOOL_MODULES_NAME = "TOOL_MODULES"
SPEC_CONSUMERS = (SCHEMA_FUNCTION, "execute_tool")
AGENT_WRITE_OPENER = "allow_agent_write"
AGENT_WRITE_OPENER_FILES = (RUN_LOG_FILE, PROPOSE_TOOL_FILE)
AGENT_WRITE_FLAG_NAME = "AGENT_WRITE_FLAG"


def _absolute_aliases(tree: ast.AST, rel: str) -> dict:
	"""import_aliases plus relative `from .x import y [as z]`, resolved against the module of `rel`."""
	aliases = import_aliases(tree)
	package = module_name(rel).split(".")
	if not rel.endswith("__init__.py"):
		package = package[:-1]
	for node in ast.walk(tree):
		if isinstance(node, ast.ImportFrom) and node.level:
			base = package[: len(package) - (node.level - 1)]
			base = ".".join([*base, node.module] if node.module else base)
			for alias in node.names:
				aliases[alias.asname or alias.name] = f"{base}.{alias.name}"
	return aliases


def _module_definitions(tree: ast.AST) -> dict:
	"""`{name: node}` of the module's own functions and assigned values."""
	found = {}
	for node in tree.body:
		if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
			found[node.name] = node
		elif isinstance(node, ast.Assign):
			found.update({target.id: node.value for target in node.targets if isinstance(target, ast.Name)})
		elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.value is not None:
			found[node.target.id] = node.value
	return found


def _reaches_change_state(rel: str, node, aliases: dict, definitions: dict, seen=frozenset()) -> bool:
	"""`node` names approve/reject/undo or erp_ai.agent.changes.transitions (reference, import or dotted
	text), directly or through the module's own functions and values."""
	if any(
		module_in(target, TRANSITIONS_MODULE)
		for _line, target in imported_modules(node, module_name(rel), rel.endswith("__init__.py"))
	):
		return True
	for inner in ast.walk(node):
		if isinstance(inner, ast.Constant) and isinstance(inner.value, str):
			if module_in(inner.value, TRANSITIONS_MODULE):
				return True
			continue
		if not isinstance(inner, ast.Name | ast.Attribute):
			continue
		name = resolved_name(inner, aliases)
		leaf = name.rpartition(".")[2] if isinstance(inner, ast.Name) else inner.attr
		if leaf in CHANGE_STATE_NAMES or module_in(name, TRANSITIONS_MODULE):
			return True
		if (
			isinstance(inner, ast.Name)
			and inner.id in definitions
			and inner.id not in seen
			and _reaches_change_state(rel, definitions[inner.id], aliases, definitions, seen | {inner.id})
		):
			return True
	return False


def change_state_whitelists(sources: dict) -> list:
	"""`[(rel, function, methods)]` of every whitelisted function that reaches the change state machine."""
	found = []
	trees = {}
	for rel, node, decorator in whitelisted_functions(sources):
		if rel not in trees:
			tree = parse(rel, sources[rel])
			trees[rel] = (_absolute_aliases(tree, rel), _module_definitions(tree))
		aliases, definitions = trees[rel]
		if _reaches_change_state(rel, node, aliases, definitions, frozenset({node.name})):
			keywords = {kw.arg: kw.value for kw in getattr(decorator, "keywords", ())}
			methods = keywords.get("methods")
			listed = methods.elts if isinstance(methods, ast.List | ast.Tuple | ast.Set) else ()
			found.append((rel, node, {e.value for e in listed if isinstance(e, ast.Constant)}))
	return found


def check_no_get_whitelist_reaches_change_state(sources: dict) -> list:
	"""ADR-023 Ràng buộc: no `@frappe.whitelist(methods=[..."GET"...])` reaches approve/reject/undo or the
	state machine (ADR-010: a state change is never a GET)."""
	return [
		violation(rel, node, f"{node.name}: GET whitelist reaches the change state (ADR-023)")
		for rel, node, methods in change_state_whitelists(sources)
		if GET_METHOD in methods
	]


def _string_shape(scan: GitScan, rel: str, node, depth: int = 0) -> str:
	"""The text of a string expression, each piece not known statically written as UNKNOWN_PIECE."""
	if depth > RESOLVE_DEPTH:
		return UNKNOWN_PIECE
	if isinstance(node, ast.JoinedStr):
		return "".join(_string_shape(scan, rel, value, depth + 1) for value in node.values)
	if isinstance(node, ast.FormattedValue):
		return _string_shape(scan, rel, node.value, depth + 1)
	if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
		return _string_shape(scan, rel, node.left, depth + 1) + _string_shape(
			scan, rel, node.right, depth + 1
		)
	if isinstance(node, ast.Constant):
		return node.value if isinstance(node.value, str) else UNKNOWN_PIECE
	found = scan.lookup(rel, node)
	return _string_shape(scan, *found, depth + 1) if found else UNKNOWN_PIECE


NO_CONSTANTS_SCAN = GitScan({})  # resolves no name: every Name/Attribute piece stays an UNKNOWN_PIECE


def _string_texts(root, docstrings: set, scan: GitScan = NO_CONSTANTS_SCAN, rel: str = "") -> list:
	"""`[(node, shape)]` of every string expression under `root` (docstrings excluded); the module constants
	of `scan` are resolved from file `rel`."""
	return [
		(node, _string_shape(scan, rel, node))
		for node in ast.walk(root)
		if (isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in docstrings)
		or isinstance(node, ast.JoinedStr)
		or (isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add))
	]


def _change_link_shapes(sources: dict) -> list:
	"""`[(node, shape)]` of every string expression of change_link.py (docstrings excluded)."""
	scan = GitScan(sources)
	tree = scan.trees[CHANGE_LINK_FILE]
	return _string_texts(tree, _docstring_ids(tree), scan, CHANGE_LINK_FILE)


def change_link_string_shapes(sources: dict) -> list:
	return [shape for _node, shape in _change_link_shapes(sources)] if CHANGE_LINK_FILE in sources else []


def check_change_link_builds_no_api_method_path(sources: dict) -> list:
	"""ADR-023 Ràng buộc: change_link builds no `/api/method/` path (a link opens the form, the form POSTs)."""
	if CHANGE_LINK_FILE not in sources:
		return _missing(CHANGE_LINK_FILE)
	return [
		violation(CHANGE_LINK_FILE, node, f"builds {shape!r}, an /api/method/ path (ADR-023)")
		for node, shape in _change_link_shapes(sources)
		if API_METHOD_PATH in shape
	]


def _node_texts(node, aliases: dict, docstrings: set) -> list:
	"""The names a node carries: a reference (alias resolved), an imported name, a keyword name, a string
	and each identifier inside it (a dotted path names its last segment, as a grep would match it)."""
	if isinstance(node, ast.Name):
		return [resolved_name(node, aliases).rpartition(".")[2]]
	if isinstance(node, ast.Attribute):
		return [node.attr]
	if isinstance(node, ast.Import | ast.ImportFrom):
		return [alias.name.rpartition(".")[2] for alias in node.names]
	if isinstance(node, ast.keyword):
		return [node.arg] if node.arg else []
	if isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in docstrings:
		return list(dict.fromkeys([node.value, *IDENTIFIER.findall(node.value)]))
	return []


def _top_level_reads(tree: ast.Module, name: str) -> list:
	"""`[(owner, node)]` for each read of `name`; owner = the enclosing top-level function's name, else None."""
	return [
		(statement.name if isinstance(statement, ast.FunctionDef | ast.AsyncFunctionDef) else None, node)
		for statement in tree.body
		for node in ast.walk(statement)
		if isinstance(node, ast.Name) and node.id == name and isinstance(node.ctx, ast.Load)
	]


def _grant_path_violations(tree: ast.Module, reader: str) -> list:
	"""Specs are listed only by SPEC_SOURCE (from TOOL_MODULES), called only by the grant function `reader`;
	each SPEC_CONSUMERS function exists and calls `reader`."""
	violations = []
	spec_reads = _top_level_reads(tree, SPEC_SOURCE)
	for owner, node in spec_reads:
		if owner != reader:
			violations.append(
				violation(
					REGISTRY_FILE,
					node,
					f"{owner}: {SPEC_SOURCE}() outside {reader} lists ungranted specs (ADR-023)",
				)
			)
	if reader not in {owner for owner, _node in spec_reads}:
		violations.append(f"{REGISTRY_FILE}: {reader} does not list specs from {SPEC_SOURCE}() (ADR-023)")
	for owner, node in _top_level_reads(tree, TOOL_MODULES_NAME):
		if owner not in (None, SPEC_SOURCE):
			violations.append(
				violation(
					REGISTRY_FILE, node, f"{owner}: reads {TOOL_MODULES_NAME} outside {SPEC_SOURCE} (ADR-023)"
				)
			)
	functions = {
		statement.name: statement
		for statement in tree.body
		if isinstance(statement, ast.FunctionDef | ast.AsyncFunctionDef)
	}
	for consumer in SPEC_CONSUMERS:
		if consumer not in functions:
			violations.append(
				f"{REGISTRY_FILE}: {consumer} missing; it must reach specs through {reader} (ADR-023)"
			)
		elif not any(owner == consumer for owner, _node in _top_level_reads(tree, reader)):
			violations.append(
				violation(REGISTRY_FILE, functions[consumer], f"{consumer} does not call {reader} (ADR-023)")
			)
	return violations


def check_registry_has_one_grant_function(sources: dict) -> list:
	"""ADR-023 Ràng buộc (ADR-011 QĐ 6): one grant table read by one grant function in registry.py; the
	removed names `_unrestricted_specs`, `get_unrestricted_tool_schemas` exist nowhere; runner.py makes one
	schema call, `.schemas()` on the Grant (U1), once."""
	violations = []
	for rel, source in only_python(sources).items():
		tree = parse(rel, source)
		aliases, docstrings = import_aliases(tree), _docstring_ids(tree)
		for node in ast.walk(tree):
			texts = [node.name] if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) else []
			for text in texts + _node_texts(node, aliases, docstrings):
				if text in REMOVED_GRANT_NAMES:
					violations.append(violation(rel, node, f"{text} is a second grant path (ADR-023)"))
				elif text == SPEC_SOURCE and rel != REGISTRY_FILE:
					violations.append(
						violation(rel, node, f"{text} reached past the grant function (ADR-023)")
					)
	for rel in (REGISTRY_FILE, RUNNER_FILE):
		if rel not in sources:
			violations.extend(_missing(rel))
	if REGISTRY_FILE in sources:
		tree = parse(REGISTRY_FILE, sources[REGISTRY_FILE])
		tables = [
			node
			for node in tree.body
			if isinstance(node, ast.Assign | ast.AnnAssign)
			and any(
				isinstance(target, ast.Name) and target.id == GRANT_TABLE_NAME
				for target in (node.targets if isinstance(node, ast.Assign) else [node.target])
			)
		]
		readers = [
			function.name
			for function in ast.walk(tree)
			if isinstance(function, ast.FunctionDef | ast.AsyncFunctionDef)
			and any(
				isinstance(node, ast.Name) and node.id == GRANT_TABLE_NAME and isinstance(node.ctx, ast.Load)
				for node in ast.walk(function)
			)
		]
		if len(tables) != 1 or len(readers) != 1:
			violations.append(
				f"{REGISTRY_FILE}: {len(tables)} {GRANT_TABLE_NAME} assignments read by {readers}; "
				"one grant table and one grant function (ADR-023)"
			)
		else:
			violations.extend(_grant_path_violations(tree, readers[0]))
	if RUNNER_FILE in sources:
		tree = parse(RUNNER_FILE, sources[RUNNER_FILE])
		aliases = import_aliases(tree)
		calls = [
			(node, resolved_name(node.func, aliases).rpartition(".")[2])
			for node in ast.walk(tree)
			if isinstance(node, ast.Call)
		]
		schema_calls = [(node, name) for node, name in calls if SCHEMA_CALL_MARK in name.lower()]
		if [name for _node, name in schema_calls] != [RUNNER_SCHEMA_CALL]:
			violations.append(
				f"{RUNNER_FILE}: schema calls {[violation(RUNNER_FILE, n, name) for n, name in schema_calls]}; "
				f"exactly one .{RUNNER_SCHEMA_CALL}() call on the grant (ADR-023)"
			)
	return violations


GRANT_REMOVED_PREFIX = "grants_"
RUNNER_REMOVED_NAMES = (*REMOVED_GRANT_NAMES, "_legacy_inputs", "_grants_group", SCHEMA_FUNCTION)
LIST_MUTATORS = ("append", "extend", "insert", "remove", "pop", "clear", "sort")


def check_runner_takes_tools_and_flags_from_grant(sources: dict) -> list:
	"""AC-3, ADR-023: runner.py takes its tool schemas and prompt flags from the Grant only: no call or
	reference to the removed grant functions or `get_tool_schemas`, no list mutation or filtering of the
	tools list that `.schemas()` returned."""
	if RUNNER_FILE not in sources:
		return []
	tree = parse(RUNNER_FILE, sources[RUNNER_FILE])
	aliases, docstrings = import_aliases(tree), _docstring_ids(tree)
	violations = []
	for node in ast.walk(tree):
		for text in _node_texts(node, aliases, docstrings):
			last = text.rpartition(".")[2]
			if last in RUNNER_REMOVED_NAMES or last.startswith(GRANT_REMOVED_PREFIX):
				violations.append(
					violation(RUNNER_FILE, node, f"uses {last}; take tools and flags from grant()")
				)
		if isinstance(node, ast.Assign) and any(
			isinstance(target, ast.Name) and target.id == "tools" for target in node.targets
		):
			if any(isinstance(child, ast.comprehension) for child in ast.walk(node.value)):
				violations.append(
					violation(RUNNER_FILE, node, "filters tools; take them from Grant.schemas()")
				)
		if (
			isinstance(node, ast.Call)
			and isinstance(node.func, ast.Attribute)
			and node.func.attr in LIST_MUTATORS
			and isinstance(node.func.value, ast.Name)
			and node.func.value.id == "tools"
		):
			violations.append(violation(RUNNER_FILE, node, f"mutates tools with .{node.func.attr}()"))
	return violations


def _agent_write_flag_value(sources: dict):
	"""The literal value of AGENT_WRITE_FLAG in agent_write_guard.py, else None."""
	value = GitScan._module_assignments(parse(AGENT_WRITE_GUARD_FILE, sources[AGENT_WRITE_GUARD_FILE])).get(
		AGENT_WRITE_FLAG_NAME
	)
	return value.value if isinstance(value, ast.Constant) and isinstance(value.value, str) else None


def agent_write_references(sources: dict) -> list:
	"""`[(rel, node, kind)]`: every reference, import, keyword or string naming `allow_agent_write`
	(kind AGENT_WRITE_OPENER) or the flag, by constant name or by value (kind AGENT_WRITE_FLAG_NAME)."""
	kinds = {AGENT_WRITE_OPENER: AGENT_WRITE_OPENER, AGENT_WRITE_FLAG_NAME: AGENT_WRITE_FLAG_NAME}
	if AGENT_WRITE_GUARD_FILE in sources and (value := _agent_write_flag_value(sources)):
		kinds[value] = AGENT_WRITE_FLAG_NAME
	found = []
	for rel, source in only_python(sources).items():
		tree = parse(rel, source)
		aliases, docstrings = import_aliases(tree), _docstring_ids(tree)
		for node in ast.walk(tree):
			found.extend(
				(rel, node, kinds[text]) for text in _node_texts(node, aliases, docstrings) if text in kinds
			)
	return found


def check_agent_write_flag_only_in_run_log_and_propose_tool(sources: dict) -> list:
	"""ADR-023 Ràng buộc (M5): the write guard's opening is used only by run_log.py and the propose tool;
	the flag is named only in agent_write_guard.py, which checks it."""
	if AGENT_WRITE_GUARD_FILE not in sources:
		return _missing(AGENT_WRITE_GUARD_FILE)
	violations = []
	if _agent_write_flag_value(sources) is None:
		violations.append(
			f"{AGENT_WRITE_GUARD_FILE}: {AGENT_WRITE_FLAG_NAME} is not a string literal, its value cannot be "
			"scanned for (ADR-023)"
		)
	for rel, node, kind in agent_write_references(sources):
		if kind == AGENT_WRITE_FLAG_NAME and rel != AGENT_WRITE_GUARD_FILE:
			violations.append(violation(rel, node, "names the agent write flag outside the guard (ADR-023)"))
		elif kind == AGENT_WRITE_OPENER and rel not in AGENT_WRITE_OPENER_FILES:
			if rel != AGENT_WRITE_GUARD_FILE or isinstance(node, ast.Name | ast.Attribute):
				violations.append(
					violation(
						rel, node, f"uses {AGENT_WRITE_OPENER} outside run_log and the propose tool (ADR-023)"
					)
				)
	return violations


# ---------------------------------------------------------------------------------------------------
# ADR-024 Ràng buộc: the privilege alert reads ERP AI Log through the runner's tool set and one watermark
# ---------------------------------------------------------------------------------------------------

TASKS_FILE = "tasks.py"
SETTING_CONTROLLER_FILE = CONFIG_CONTROLLER_FILES[0]
SETTING_DOCTYPE_FILE = "erp_ai_agent/doctype/erp_ai_setting/erp_ai_setting.json"
RUNNER_MODULE = module_name(RUNNER_FILE)
GENERIC_WRITE_TOOLS_NAME = "GENERIC_WRITE_TOOLS"
WATERMARK_FIELD = "privilege_alert_checked_until"
WATERMARK_WRITER = "_advance_privilege_watermark"
WATERMARK_FILES = (SETTING_DOCTYPE_FILE, SETTING_CONTROLLER_FILE)  # tests are never scanned, so allowed too
SETTING_WRITE_METHODS = ("save", "insert")
# The clocks ADR-024 Ràng buộc 4 bans in the alert job: datetime.now/utcnow (any alias, resolved) and SQL
# NOW(), as the query builder's Now() or written in a string.
PRIVILEGE_JOB_FUNCTION = "check_privilege_escalation"
FOREIGN_CLOCK_CALLS = ("datetime.datetime.now", "datetime.datetime.utcnow")
QUERY_BUILDER_NOW = "Now"
SQL_NOW = re.compile(r"\bnow\s*\(", re.IGNORECASE)
VERSION_DOCTYPE = "Version"
# ADR-024 Ràng buộc 1, ruling R10e (C3b): the record tool refuses Version in every mode, which enforces the rule; its
# refused set is the one constant of product code that may name it.
VERSION_ALLOWED_ASSIGNMENTS = {SITE_API_FILE: "RECORD_DENIED_DOCTYPES"}
VERSION_TABLE = re.compile(r"\btabVersion\b")
VERSION_JS = re.compile(r"""(["'`])Version\1|\btabVersion\b""")
PRIVILEGE_CONDITION_FUNCTION = "_privilege_changes_by_agent"
OWNER_FIELDS = ("modified_by", "owner")
WRITE_ENTRY_FUNCTION = "write_entry"
COMMIT_CALL = "frappe.db.commit"


def _pattern_lines(source: str, pattern: re.Pattern) -> set:
	return {source.count("\n", 0, match.start()) + 1 for match in pattern.finditer(source)}


def _text_lines(source: str, text: str) -> set:
	return _pattern_lines(source, re.compile(re.escape(text)))


def _reached_functions(functions: dict, start: str, references) -> list:
	"""`start` and every function of `functions` it reaches through `references(function)`, sorted."""
	reached, pending = set(), [start]
	while pending:
		name = pending.pop()
		if name not in reached:
			reached.add(name)
			pending.extend(other for other in references(functions[name]) if other in functions)
	return sorted(reached)


def _called_or_passed_names(node) -> set:
	"""Names `node` calls or reads as a value (a function handed over, e.g. in a tuple of checks)."""
	return _called_names(node) | {name.id for name in ast.walk(node) if isinstance(name, ast.Name)}


def _naming_lines(rel: str, source: str, text: str) -> set:
	"""Lines naming `text`: written anywhere in the file (comments too), or built by a Python string
	expression."""
	lines = _text_lines(source, text)
	if rel.endswith(".py"):
		tree = parse(rel, source)
		lines |= {node.lineno for node, folded in _string_texts(tree, set()) if text in folded}
	return lines


def _own_nodes(function):
	"""The nodes of `function`'s body, without those of functions, lambdas or classes defined inside it."""
	pending = list(function.body)
	while pending:
		node = pending.pop()
		yield node
		if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.Lambda | ast.ClassDef):
			pending.extend(ast.iter_child_nodes(node))


def check_generic_write_tools_shared(targets: dict, generic, sources: dict) -> list:
	"""ADR-024 Ràng buộc 2: every write tool whose DocType the model names (target DocType None) is in
	GENERIC_WRITE_TOOLS, and tasks.py reads that one runner tuple, never a set of its own."""
	if TASKS_FILE not in sources:
		return _missing(TASKS_FILE)
	violations = [
		f"{RUNNER_FILE}: {name} has a model-chosen DocType but is not in {GENERIC_WRITE_TOOLS_NAME} (ADR-024)"
		for name, (doctype, _key) in targets.items()
		if doctype is None and name not in generic
	]
	tree = parse(TASKS_FILE, sources[TASKS_FILE])
	aliases = import_aliases(tree)
	shared = f"{RUNNER_MODULE}.{GENERIC_WRITE_TOOLS_NAME}"
	reads = [
		node
		for node in ast.walk(tree)
		if isinstance(node, ast.Name | ast.Attribute)
		and isinstance(node.ctx, ast.Load)
		and resolved_name(node, aliases) == shared
	]
	if not reads:
		violations.append(f"{TASKS_FILE}: never reads {shared} (ADR-024)")
	violations.extend(
		violation(TASKS_FILE, node, f"defines its own {GENERIC_WRITE_TOOLS_NAME} (ADR-024)")
		for node in ast.walk(tree)
		if isinstance(node, ast.Name)
		and isinstance(node.ctx, ast.Store)
		and node.id == GENERIC_WRITE_TOOLS_NAME
	)
	return violations


def check_tasks_names_no_write_tool(sources: dict, tool_names) -> list:
	"""ADR-024 Ràng buộc 2: tasks.py writes no tool name of the runner's WRITE_TOOL_TARGETS by hand (as text, or
	built by `+`/f-string). The bare substring `api_` stays allowed: `api_key` and the `like "%api_%"` filter."""
	if TASKS_FILE not in sources:
		return _missing(TASKS_FILE)
	source = sources[TASKS_FILE]
	return [
		f"{TASKS_FILE}:{line}: writes the tool name {name!r} by hand; read {GENERIC_WRITE_TOOLS_NAME} (ADR-024)"
		for name in tool_names
		for line in sorted(_naming_lines(TASKS_FILE, source, name))
	]


def check_watermark_field_only_in_allowed_places(sources: dict) -> list:
	"""ADR-024 Ràng buộc 3, design-amd2 D-6: the watermark field is named only in the ERP AI Setting JSON and
	controller (reader `read_privilege_watermark`) and, in tasks.py, only inside WATERMARK_WRITER."""
	if TASKS_FILE not in sources:
		return _missing(TASKS_FILE)
	violations = []
	for rel, source in sources.items():
		if rel in WATERMARK_FILES:
			continue
		lines = _naming_lines(rel, source, WATERMARK_FIELD)
		span = range(0)
		if rel == TASKS_FILE:
			writer = _module_functions(parse(rel, source)).get(WATERMARK_WRITER)
			if writer is None:
				violations.append(
					f"{TASKS_FILE}: no function {WATERMARK_WRITER} writes the watermark (ADR-024)"
				)
			else:
				span = range(writer.lineno, writer.end_lineno + 1)
				if not any(line in span for line in lines):
					violations.append(
						f"{TASKS_FILE}: {WATERMARK_WRITER} does not write {WATERMARK_FIELD} (ADR-024)"
					)
		violations.extend(
			f"{rel}:{line}: names {WATERMARK_FIELD} outside the Setting and {WATERMARK_WRITER} (ADR-024)"
			for line in sorted(lines)
			if line not in span
		)
	return violations


def check_tasks_never_saves_or_inserts_setting(sources: dict) -> list:
	"""ADR-024 Ràng buộc 3: tasks.py never calls `save()`/`insert()` on an ERP AI Setting document (a save would
	run `restore_self_managed_fields` and the watermark would never move)."""
	if TASKS_FILE not in sources:
		return _missing(TASKS_FILE)
	tree = parse(TASKS_FILE, sources[TASKS_FILE])
	config_vars = set(CONFIG_VARIABLE_NAMES)
	for node in ast.walk(tree):
		if isinstance(node, ast.Assign) and _is_config_doc_expr(node.value, set()):
			config_vars.update(target.id for target in node.targets if isinstance(target, ast.Name))
	return [
		violation(TASKS_FILE, node, f"`.{node.func.attr}()` on the ERP AI Setting document (ADR-024)")
		for node in ast.walk(tree)
		if isinstance(node, ast.Call)
		and isinstance(node.func, ast.Attribute)
		and node.func.attr in SETTING_WRITE_METHODS
		and _is_config_doc_expr(node.func.value, config_vars)
	]


def check_privilege_job_reads_no_other_clock(sources: dict) -> list:
	"""ADR-024 Ràng buộc 4: the alert job PRIVILEGE_JOB_FUNCTION, and every tasks.py function it reaches
	(called or passed as a value), calls no `datetime.now`/`datetime.utcnow` (any alias) or query builder
	`Now()` and writes or reads (a module constant, alone or in a string expression) no SQL `NOW()`; its clock
	is `frappe.utils.now_datetime` or the `now` argument. The other jobs of tasks.py and `frappe.utils.now`
	(the same clock as `now_datetime`) are outside the constraint."""
	if TASKS_FILE not in sources:
		return _missing(TASKS_FILE)
	scan = GitScan(sources)
	tree = scan.trees[TASKS_FILE]
	functions, aliases, docstrings = _module_functions(tree), import_aliases(tree), _docstring_ids(tree)
	if PRIVILEGE_JOB_FUNCTION not in functions:
		return [f"{TASKS_FILE}: no function {PRIVILEGE_JOB_FUNCTION} (ADR-024)"]
	violations = []
	for name in _reached_functions(functions, PRIVILEGE_JOB_FUNCTION, _called_or_passed_names):
		function = functions[name]
		calls = [
			(node, resolved_name(node.func, aliases))
			for node in ast.walk(function)
			if isinstance(node, ast.Call)
		]
		violations.extend(
			violation(TASKS_FILE, node, f"{name} reads the clock with {called}() (ADR-024)")
			for node, called in calls
			if called in FOREIGN_CLOCK_CALLS or called.rpartition(".")[2] == QUERY_BUILDER_NOW
		)
		texts = _string_texts(function, docstrings, scan, TASKS_FILE)
		in_texts = {id(inner) for node, _text in texts for inner in ast.walk(node)}
		texts += [
			(node, _string_shape(scan, TASKS_FILE, node))
			for node in ast.walk(function)
			if isinstance(node, ast.Name | ast.Attribute)
			and id(node) not in in_texts
			and scan.lookup(TASKS_FILE, node)
		]
		violations.extend(
			violation(TASKS_FILE, node, f"{name}: SQL clock in {text!r} (ADR-024)")
			for node, text in texts
			if SQL_NOW.search(text)
		)
	return violations


def check_no_version_reads(sources: dict) -> list:
	"""ADR-024 Ràng buộc 1: product code (Python and JS) never names the `Version` DocType or its table, save the
	constant of VERSION_ALLOWED_ASSIGNMENTS."""
	violations = []
	for rel, source in sources.items():
		if rel.endswith(".py"):
			tree = parse(rel, source)
			allowed = _allowed_legacy_nodes(rel, tree, VERSION_ALLOWED_ASSIGNMENTS)
			violations.extend(
				violation(rel, node, f"reads Version through {text!r} (ADR-024)")
				for node, text in _string_texts(tree, _docstring_ids(tree))
				if id(node) not in allowed and (text.strip() == VERSION_DOCTYPE or VERSION_TABLE.search(text))
			)
		elif rel.endswith(".js"):
			violations.extend(
				f"{rel}:{line}: reads Version (ADR-024)"
				for line in sorted(_pattern_lines(source, VERSION_JS))
			)
	return violations


def check_privilege_condition_ignores_owner(sources: dict) -> list:
	"""ADR-024 Ràng buộc 1: PRIVILEGE_CONDITION_FUNCTION, and every tasks.py function it reaches, never names
	`modified_by`/`owner` (attribute, keyword, string or SQL text)."""
	if TASKS_FILE not in sources:
		return _missing(TASKS_FILE)
	tree = parse(TASKS_FILE, sources[TASKS_FILE])
	functions, docstrings = _module_functions(tree), _docstring_ids(tree)
	if PRIVILEGE_CONDITION_FUNCTION not in functions:
		return [f"{TASKS_FILE}: no function {PRIVILEGE_CONDITION_FUNCTION} (ADR-024)"]
	violations = []
	for name in _reached_functions(functions, PRIVILEGE_CONDITION_FUNCTION, _called_names):
		function = functions[name]
		texts = _string_texts(function, docstrings)
		texts += [(node, node.attr) for node in ast.walk(function) if isinstance(node, ast.Attribute)]
		texts += [(node, node.arg) for node in ast.walk(function) if isinstance(node, ast.keyword)]
		violations.extend(
			violation(TASKS_FILE, node, f"{name} filters on {field} (ADR-024)")
			for node, text in texts
			for field in OWNER_FIELDS
			if text and field in IDENTIFIER.findall(text)
		)
	return violations


def check_write_entry_inserts_and_commits(sources: dict) -> list:
	"""ADR-024 Ràng buộc 5: `run_log.write_entry` itself calls `.insert(...)` and then `frappe.db.commit()`
	(not in a helper, a nested function or a deferred callback)."""
	if RUN_LOG_FILE not in sources:
		return _missing(RUN_LOG_FILE)
	tree = parse(RUN_LOG_FILE, sources[RUN_LOG_FILE])
	function = _module_functions(tree).get(WRITE_ENTRY_FUNCTION)
	if function is None:
		return [f"{RUN_LOG_FILE}: no function {WRITE_ENTRY_FUNCTION} (ADR-024)"]
	aliases = import_aliases(tree)
	calls = [node for node in _own_nodes(function) if isinstance(node, ast.Call)]
	inserts = [node.lineno for node in calls if referenced_name(node.func) == "insert"]
	commits = [node.lineno for node in calls if resolved_name(node.func, aliases) == COMMIT_CALL]
	if not inserts or not commits or max(commits) < min(inserts):
		return [
			violation(
				RUN_LOG_FILE,
				function,
				f"{WRITE_ENTRY_FUNCTION} must insert then {COMMIT_CALL}() in its own body (ADR-024)",
			)
		]
	return []


# Compliant samples of the ADR-024 rules; each violating sample is one change of these (see the two tests).
PRIVILEGE_TASKS_SAMPLE = f"""from datetime import timedelta

import frappe
from frappe.utils import get_datetime, now_datetime

from erp_ai.agent.runner import GENERIC_WRITE_TOOLS
from erp_ai.constants import CREDENTIAL_DOCTYPE, LOG_DOCTYPE, SETTING_DOCTYPE
from erp_ai.erp_ai_agent.doctype.erp_ai_setting.erp_ai_setting import read_privilege_watermark


def _usable(action):
	return action.get("tool") in GENERIC_WRITE_TOOLS and action.get("ok")


def {PRIVILEGE_CONDITION_FUNCTION}(lower, upper):
	log = frappe.qb.DocType(LOG_DOCTYPE)
	query = frappe.qb.from_(log).select(log.name, log.actions).where(log.actions.like("%api_%"))
	return [row.name for row in query.run(as_dict=True) if _usable(row)]


def _scripts_by_agent():
	return frappe.get_all("Server Script", filters={{"owner": "bot"}}, pluck="name")


def _keys_without_value():
	return frappe.get_all(CREDENTIAL_DOCTYPE, fields=["label", "api_key"])


def {WATERMARK_WRITER}(upper):
	frappe.db.set_single_value(SETTING_DOCTYPE, "{WATERMARK_FIELD}", upper)


def check_privilege_escalation(now=None):
	upper = (get_datetime(now) if now else now_datetime()) - timedelta(seconds=300)
	lower = read_privilege_watermark()
	{PRIVILEGE_CONDITION_FUNCTION}(lower, upper)
	_scripts_by_agent()
	_keys_without_value()
	frappe.get_doc({{"doctype": "ToDo"}}).insert()
	{WATERMARK_WRITER}(upper)
"""
PRIVILEGE_SOURCES_SAMPLE = {
	TASKS_FILE: PRIVILEGE_TASKS_SAMPLE,
	SETTING_CONTROLLER_FILE: (
		"import frappe\n\n\ndef read_privilege_watermark():\n"
		f'\treturn frappe.db.get_single_value("ERP AI Setting", "{WATERMARK_FIELD}", cache=False)\n'
	),
	SETTING_DOCTYPE_FILE: f'{{"fields": [{{"fieldname": "{WATERMARK_FIELD}"}}]}}\n',
	"agent/tools/read.py": 'import frappe\n\nNOTE = "Version 15"\nROWS = frappe.get_all("ERP AI Log")\n',
	"public/js/agent_status_indicator.js": "const label = 'App Version 1';\n",
}
RUN_LOG_SAMPLE = """import frappe


def write_entry(**fields):
	doc = frappe.get_doc({**fields, "doctype": "ERP AI Log"})
	doc.insert()
	if not frappe.flags.in_test:
		frappe.db.commit()
	return doc.name
"""


# ---------------------------------------------------------------------------------------------------
# ADR-031 QĐ 7, arch-review w1a C-1/C-2: one reader of the site environment (`policy.site_environment`)
# ---------------------------------------------------------------------------------------------------

SITE_ENVIRONMENT_FIELD = "site_environment"
SITE_ENVIRONMENT_CONSTANT = "SITE_ENVIRONMENT_FIELD"
SITE_ENVIRONMENT_READER = f"{module_name(POLICY_FILE)}.{SITE_ENVIRONMENT_FIELD}"
SITE_ENVIRONMENT_NAME = re.compile(r"(?<![A-Za-z0-9_])site_environment(?![A-Za-z0-9_])")
# The Python files that may name the field, one reason each (C-2; tests and JSON are never scanned by the
# rule). The other product files that read the ERP AI Log column of the same name are listed here too (grep
# `site_environment` in erp_ai/**/*.py on the T70 base: only the Setting controller, so none so far).
SITE_ENVIRONMENT_FILES = {
	POLICY_FILE: "the one reader of the Setting field, site_environment() (ADR-031 QĐ 7)",
	SETTING_CONTROLLER_FILE: "the ERP AI Setting controller owns the field (its own form summary)",
	RUN_LOG_FILE: "writes the ERP AI Log column of the same name (ADR-033 QĐ 5)",
	INSTALL_FILE: "sets up the ERP AI Setting defaults at install",
}


def check_site_environment_readers(sources: dict) -> list:
	"""ADR-031 QĐ 7, C-2: outside SITE_ENVIRONMENT_FILES no Python file names `site_environment` (an attribute,
	a keyword, a string, a built string) or policy's SITE_ENVIRONMENT_FIELD; the one exception is the policy
	function itself (`policy.site_environment(...)`, or imported from erp_ai.agent.policy)."""
	violations = []
	for rel, source in only_python(sources).items():
		if rel in SITE_ENVIRONMENT_FILES:
			continue
		tree = parse(rel, source)
		aliases = import_aliases(tree)
		reader_imports = {
			id(alias)
			for node in ast.walk(tree)
			if isinstance(node, ast.ImportFrom) and not node.level and node.module == module_name(POLICY_FILE)
			for alias in node.names
			if alias.name == SITE_ENVIRONMENT_FIELD
		}
		lines = set()
		for node in ast.walk(tree):
			if id(node) in reader_imports or isinstance(node, ast.Constant):
				continue  # strings are checked below, built ones included
			names = _node_names(node)
			if SITE_ENVIRONMENT_FIELD in names and resolved_name(node, aliases) == SITE_ENVIRONMENT_READER:
				continue  # `policy.site_environment(...)` is the reader, not a field read
			if SITE_ENVIRONMENT_FIELD in names or SITE_ENVIRONMENT_CONSTANT in names:
				lines.add(node.lineno)
		lines |= {
			node.lineno
			for node, text in _string_texts(tree, _docstring_ids(tree))
			if SITE_ENVIRONMENT_NAME.search(text)
		}
		violations.extend(
			f"{rel}:{line}: names {SITE_ENVIRONMENT_FIELD} outside {POLICY_FILE}; read it with "
			f"policy.site_environment() (ADR-031 QĐ 7)"
			for line in sorted(lines)
		)
	return violations


# Compliant sample: each allow-listed file names the field, two callers use the reader.
SITE_ENVIRONMENT_SAMPLE = {
	POLICY_FILE: (
		'import frappe\n\nSITE_ENVIRONMENT_FIELD = "site_environment"\n\n\n'
		"def site_environment(settings=None):\n"
		"\treturn getattr(settings or frappe.get_single('ERP AI Setting'), SITE_ENVIRONMENT_FIELD, None)\n"
	),
	SETTING_CONTROLLER_FILE: "def summary(self):\n\treturn f'Môi trường site: {self.site_environment}'\n",
	RUN_LOG_FILE: (
		"from erp_ai.agent import policy\n\n\ndef write_entry(**fields):\n"
		'\treturn {**fields, "site_environment": policy.site_environment()}\n'
	),
	INSTALL_FILE: 'DEFAULTS = {"site_environment": "production"}\n',
	TASKS_FILE: (
		"import frappe\n\nfrom erp_ai.agent import policy\n\n\ndef job():\n"
		"\tsettings = frappe.get_single('ERP AI Setting')\n\treturn policy.site_environment(settings)\n"
	),
	"agent/executor.py": (
		"from erp_ai.agent.policy import site_environment\n"
		"from erp_ai.agent.policy import site_environment as env\n\n\n"
		'def gate():\n\t"""Refuse on production; site_environment is read once."""\n'
		'\treturn site_environment() == "production" or env() == "production"\n'
	),
}


# ---------------------------------------------------------------------------------------------------
# ADR-033 QĐ 4, arch-review w1a C-3 / ruling (2): the daily limit counts only RUN_LIMIT_TRIGGERS
# ---------------------------------------------------------------------------------------------------

RUN_LIMIT_TRIGGERS_NAME = "RUN_LIMIT_TRIGGERS"
LOG_TRIGGERS_NAME = "TRIGGERS"
KB_DRAFT_TRIGGER_NAME = "TRIGGER_KB_DRAFT"


def _module_strings(tree: ast.AST) -> dict:
	"""`{name: value}` of the module-level `NAME = "text"` assignments."""
	return {
		target.id: node.value.value
		for node in tree.body
		if isinstance(node, ast.Assign)
		and isinstance(node.value, ast.Constant)
		and isinstance(node.value.value, str)
		for target in node.targets
		if isinstance(target, ast.Name)
	}


def _trigger_tuple(rel: str, source: str, name: str, constants: dict) -> tuple:
	"""(trigger values or None, violations) of the module-level tuple `name` in `rel`; each element is a
	string, or a string constant of erp_ai/constants.py or of the file itself."""
	tree = parse(rel, source)
	known = {**constants, **_module_strings(tree)}
	nodes = [
		node
		for node in tree.body
		if isinstance(node, ast.Assign) and any(getattr(t, "id", None) == name for t in node.targets)
	]
	if not nodes:
		return None, [f"{rel}: {name} missing"]
	node = nodes[-1]
	if not isinstance(node.value, ast.Tuple):
		return None, [f"{rel}:{node.lineno}: {name} is not a tuple of trigger names"]
	values, violations = [], []
	for element in node.value.elts:
		if isinstance(element, ast.Constant) and isinstance(element.value, str):
			values.append(element.value)
		elif isinstance(element, ast.Name) and element.id in known:
			values.append(known[element.id])
		else:
			violations.append(
				f"{rel}:{element.lineno}: {name} element {ast.unparse(element)} is not a trigger name"
			)
	return tuple(values), violations


def check_run_limit_triggers_subset_of_log_triggers(sources: dict) -> list:
	"""ADR-033 QĐ 4, C-3: every trigger of policy.RUN_LIMIT_TRIGGERS is a trigger of run_log.TRIGGERS, and
	(w1a ruling (2), U6b-fixes Sửa 3) the KB-draft trigger is the one log trigger the daily limit leaves out."""
	for rel in (POLICY_FILE, RUN_LOG_FILE, CONSTANTS_FILE):
		if rel not in sources:
			return _missing(rel)
	constants = _module_strings(parse(CONSTANTS_FILE, sources[CONSTANTS_FILE]))
	kb_draft = constants.get(KB_DRAFT_TRIGGER_NAME)
	limited, violations = _trigger_tuple(
		POLICY_FILE, sources[POLICY_FILE], RUN_LIMIT_TRIGGERS_NAME, constants
	)
	logged, log_violations = _trigger_tuple(RUN_LOG_FILE, sources[RUN_LOG_FILE], LOG_TRIGGERS_NAME, constants)
	violations += log_violations
	if kb_draft is None:
		violations.append(f"{CONSTANTS_FILE}: {KB_DRAFT_TRIGGER_NAME} missing")
	if limited is not None and logged is not None:
		violations.extend(
			f"{POLICY_FILE}: {RUN_LIMIT_TRIGGERS_NAME} has {trigger!r}, not in {RUN_LOG_FILE} "
			f"{LOG_TRIGGERS_NAME} (ADR-033 QĐ 4)"
			for trigger in limited
			if trigger not in logged
		)
		unlimited = set(logged) - set(limited)
		if kb_draft is not None and unlimited != {kb_draft}:
			violations.append(
				f"{RUN_LOG_FILE}: {LOG_TRIGGERS_NAME} minus {POLICY_FILE} {RUN_LIMIT_TRIGGERS_NAME} is "
				f"{sorted(unlimited)!r}, must be exactly {{{kb_draft!r}}} (w1a ruling (2))"
			)
	return violations


# ADR-033 QĐ 1 / U1.md: the one function that switches a job's session to the agent account.
SESSION_SWITCH_FUNCTION = "enter_agent_session"
SET_USER_NAME = "set_user"


def _sets_agent_user(node, aliases: dict) -> bool:
	"""`set_user(AGENT_USER)` in any spelling: module path, alias, keyword or the account's literal."""
	if not isinstance(node, ast.Call) or resolved_name(node.func, aliases).split(".")[-1] != SET_USER_NAME:
		return False
	for value in (*node.args, *(keyword.value for keyword in node.keywords)):
		if isinstance(value, ast.Constant) and value.value == AGENT_USER:
			return True
		if resolved_name(value, aliases).split(".")[-1] == AGENT_USER_NAME:
			return True
	return False


def check_set_user_agent_only_in_enter_agent_session(sources: dict) -> list:
	"""ADR-033 QĐ 1: `set_user(AGENT_USER)` is called exactly once, inside authority.enter_agent_session."""
	if AUTHORITY_FILE not in sources:
		return _missing(AUTHORITY_FILE)
	violations = []
	allowed = 0
	for rel, source in only_python(sources).items():
		tree = parse(rel, source)
		aliases = import_aliases(tree)
		inside = set()
		if rel == AUTHORITY_FILE:
			for function in tree.body:
				if isinstance(function, ast.FunctionDef) and function.name == SESSION_SWITCH_FUNCTION:
					inside = {id(node) for node in ast.walk(function)}
		for node in ast.walk(tree):
			if not _sets_agent_user(node, aliases):
				continue
			if id(node) in inside:
				allowed += 1
			else:
				violations.append(
					violation(
						rel,
						node,
						f"switches to the agent account outside {AUTHORITY_FILE} "
						f"{SESSION_SWITCH_FUNCTION} (ADR-033 QĐ 1)",
					)
				)
	if allowed != 1:
		violations.append(
			f"{AUTHORITY_FILE}: {SESSION_SWITCH_FUNCTION} must call {SET_USER_NAME}({AGENT_USER_NAME}) "
			f"exactly once, found {allowed} (ADR-033 QĐ 1)"
		)
	return violations


# Compliant sample of the ADR-033 QĐ 1 rule; each violating sample is one change of it.
SESSION_SWITCH_CLEAN = {
	AUTHORITY_FILE: """import frappe

from erp_ai.constants import AGENT_USER


def enter_agent_session():
	frappe.set_user(AGENT_USER)
	return frappe.session.user == AGENT_USER
""",
	RUNNER_FILE: """import frappe

from erp_ai.agent import authority


def _run(ticket_name):
	if not authority.enter_agent_session():
		return
	frappe.set_user("Administrator")
""",
}


# ADR-030 QĐ 6 and Ràng buộc: the instructor comes only from the event that queued the run.
REMOVED_INSTRUCTOR_SCAN = "latest_instructor"
RUN_INSTRUCTOR_FUNCTION = "run_instructor"
COMMENT_FETCH_FUNCTION = "fetch_ticket_comments"
INSTRUCTION_PREDICATE = "is_instruction"
INSTRUCTOR_SCAN_FILES = (AUTHORITY_FILE, RUNNER_FILE)


def check_authority_has_no_comment_scan_for_instructor(sources: dict) -> list:
	"""ADR-030 QĐ 6: no product code names the removed comment scan, and no function of authority.py or
	runner.py both fetches the ticket's comments and asks who among them may instruct (AC-13)."""
	if AUTHORITY_FILE not in sources:
		return _missing(AUTHORITY_FILE)
	violations = []
	for rel, source in only_python(sources).items():
		tree = parse(rel, source)
		aliases, docstrings = import_aliases(tree), _docstring_ids(tree)
		for node in ast.walk(tree):
			texts = [node.name] if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) else []
			if REMOVED_INSTRUCTOR_SCAN in texts + _node_texts(node, aliases, docstrings):
				violations.append(
					violation(rel, node, f"names {REMOVED_INSTRUCTOR_SCAN}, a comment scan (ADR-030 QĐ 6)")
				)
		if rel not in INSTRUCTOR_SCAN_FILES:
			continue
		for function in ast.walk(tree):
			if not isinstance(function, ast.FunctionDef | ast.AsyncFunctionDef):
				continue
			called = {
				resolved_name(node.func, aliases).rpartition(".")[2]
				for node in ast.walk(function)
				if isinstance(node, ast.Call)
			}
			if {COMMENT_FETCH_FUNCTION, INSTRUCTION_PREDICATE} <= called:
				violations.append(
					violation(
						rel,
						function,
						f"{function.name} picks the instructor by scanning the ticket's comments (ADR-030 QĐ 6)",
					)
				)
	return violations


# Compliant sample of the ADR-030 QĐ 6 rule; each violating sample is one change of it.
INSTRUCTOR_SCAN_CLEAN = {
	AUTHORITY_FILE: """import frappe


def fetch_ticket_comments(ticket_name):
	return frappe.get_list("Comment", filters={"reference_name": ticket_name})


def is_instruction(author, ticket_name):
	return bool(author)


def run_instructor(ticket_name, trigger, message_name=None):
	author = frappe.db.get_value("ERP AI Message", message_name, "owner")
	return author if is_instruction(author, ticket_name) else None


def label_comments(ticket_name, comments):
	return [is_instruction(comment["author"], ticket_name) for comment in comments]
""",
	RUNNER_FILE: """from erp_ai.agent import authority


def _run(ticket_name, trigger, message_name):
	instructor = authority.run_instructor(ticket_name, trigger, message_name)
	comments = authority.label_comments(ticket_name, authority.fetch_ticket_comments(ticket_name))
	return instructor, comments
""",
}


# Compliant sample: policy names the three counted constants, the log lists them and the KB draft as strings.
RUN_LIMIT_SAMPLE = {
	CONSTANTS_FILE: (
		'TRIGGER_TICKET_INSERT = "ticket_insert"\n'
		'TRIGGER_COMMENT_MENTION = "comment_mention"\n'
		'TRIGGER_REQUESTER_REPLY = "requester_reply"\n'
		'TRIGGER_KB_DRAFT = "kb_draft"\n'
	),
	POLICY_FILE: (
		"from erp_ai.constants import TRIGGER_COMMENT_MENTION, TRIGGER_REQUESTER_REPLY, TRIGGER_TICKET_INSERT\n\n"
		"RUN_LIMIT_TRIGGERS = (TRIGGER_TICKET_INSERT, TRIGGER_COMMENT_MENTION, TRIGGER_REQUESTER_REPLY)\n"
	),
	RUN_LOG_FILE: 'TRIGGERS = ("ticket_insert", "comment_mention", "requester_reply", "kb_draft")\n',
}


class TestArchitecture(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		cls.sources = load_product_sources()

	def test_scan_covers_the_product_tree_and_skips_tests(self):
		self.assertGreater(len(self.sources), 0)
		for expected in (
			HANDLERS_FILE,
			QUEUE_FILE,
			POLICY_FILE,
			CLIENT_FILE,
			SOURCE_TOOL_FILE,
			READ_TOOL_FILE,
		):
			self.assertIn(expected, self.sources)
		self.assertEqual([rel for rel in self.sources if "/tests/" in f"/{rel}"], [])
		self.assertEqual([rel for rel in self.sources if Path(rel).name.startswith("test_")], [])

	def test_layer_imports(self):
		scanned = only_python(self.sources)
		self.assertGreater(len(scanned), 0)
		for scope, _forbidden, _reason in LAYER_RULES:
			prefix = module_name(scope.removeprefix(PACKAGE + ".").replace(".", "/") + ".py")
			self.assertTrue(
				any(module_in(module_name(rel), scope) for rel in scanned),
				f"no file in scope {scope} / {prefix}",
			)
		self.assertEqual(check_layer_imports(self.sources), [])
		self.assertEqual(check_import_boundaries(self.sources), [])
		self.assertIn("import psutil", self.sources["agent/changes/restart_check.py"])

	def test_restart_check_library_use(self):
		self.assertIn("agent/changes/restart_check.py", self.sources)
		self.assertEqual(check_restart_check_library_use(self.sources), [])

	def test_single_enqueue_call_site(self):
		scanned = only_python(self.sources)
		self.assertGreater(len(scanned), 0)
		self.assertEqual(check_single_enqueue_site(self.sources), [])
		self.assertEqual(check_enqueue_call_shape(self.sources), [])

	def test_no_save_on_settings_in_product_code(self):
		scanned = only_python(self.sources)
		self.assertGreater(len(scanned), 0)
		for controller in CONFIG_CONTROLLER_FILES:
			self.assertIn(controller, scanned)
		self.assertEqual(check_no_save_on_config(self.sources), [])

	def test_tools_never_bypass_permissions(self):
		scanned = only_python(scoped(self.sources, TOOLS_PREFIX))
		self.assertGreater(len(scanned), 0)
		self.assertEqual(check_tools_never_bypass_permissions(self.sources), [])

	def test_tools_never_pass_trusted_messages(self):
		self.assertEqual(check_tools_never_pass_trusted_messages(self.sources), [])

	def test_subprocess_only_in_source_tool(self):
		scanned = only_python(self.sources)
		self.assertGreater(len(scanned), 0)
		self.assertIn("subprocess", self.sources[SOURCE_TOOL_FILE])
		self.assertIn("subprocess", self.sources[PROCESS_RUNNER_FILE])
		self.assertEqual(check_subprocess_only_in_source_tool(self.sources), [])
		self.assertEqual(check_subprocess_call_shape(self.sources), [])
		wrapped = [
			node
			for node in ast.walk(parse(SOURCE_TOOL_FILE, self.sources[SOURCE_TOOL_FILE]))
			if isinstance(node, ast.Call) and node.args and is_timeout_wrapped(node.args[0])
		]
		self.assertEqual(
			len(wrapped),
			1,
			"run_git_read must pass its argv inline so the shape rule sees it; "
			"a later task that adds another timeout-wrapped call in source.py updates this count",
		)

	def test_level_and_send_policy_fields_only_in_policy(self):
		scanned = only_python(self.sources)
		self.assertGreater(len(scanned), 0)
		self.assertIn("permission_level", self.sources[POLICY_FILE])
		self.assertEqual(check_policy_fields_only_in_policy(self.sources), [])

	def test_runner_takes_tools_and_flags_from_grant(self):
		self.assertIn("grant(", self.sources[RUNNER_FILE])
		self.assertEqual(check_runner_takes_tools_and_flags_from_grant(self.sources), [])

	def test_threshold_compared_only_in_policy(self):
		self.assertIn("confidence_threshold", self.sources[POLICY_FILE])
		self.assertEqual(check_threshold_compared_only_in_policy(self.sources), [])

	def test_no_spent_comparison_outside_policy(self):
		self.assertIn("monthly_budget_usd", self.sources[POLICY_FILE])
		self.assertEqual(check_no_spent_comparison_outside_policy(self.sources), [])

	def test_handlers_do_not_import_gateway_or_runner(self):
		scanned = {rel: src for rel, src in self.sources.items() if rel == HANDLERS_FILE}
		self.assertGreater(len(scanned), 0)
		self.assertEqual(check_handlers_imports(self.sources), [])

	def test_secret_handling_rules(self):
		scanned = only_python(self.sources)
		self.assertGreater(len(scanned), 0)
		self.assertIn("get_decrypted_password", self.sources[CREDENTIALS_FILE])
		self.assertEqual(check_secret_handling(self.sources), [])

	def test_no_legacy_ticket_comment_or_spoofable_author(self):
		scanned = load_product_sources(suffixes=(".py", ".json", ".js", ".html"))
		self.assertGreater(len(scanned), 0)
		self.assertGreater(len(only_python(scanned)), 0)
		self.assertEqual(check_no_legacy_ticket_comment(scanned), [])

	def test_ci_installs_required_apps(self):
		text = CI_WORKFLOW.read_text(encoding="utf-8")
		self.assertGreater(len(text.splitlines()), 0)
		self.assertEqual(check_ci_workflow(text), [])

	def test_no_test_file_named_like_frappe_skips(self):
		rel_paths = [
			path.relative_to(PACKAGE_ROOT).as_posix()
			for path in sorted(PACKAGE_ROOT.rglob("*.py"))
			if "__pycache__" not in path.parts
		]
		self.assertGreater(len(rel_paths), 0)
		self.assertEqual(check_no_frappe_skipped_test_files(rel_paths), [])
		self.assertIn("agent/test_agent_runner.py", rel_paths)

	def test_status_script_static_rules(self):
		script = load_product_sources(suffixes=(".js",)).get(STATUS_SCRIPT_FILE)
		self.assertIsNotNone(script, f"{STATUS_SCRIPT_FILE} is missing")
		self.assertIn("function setupForm({ doc, call, router })", script)
		for pattern in STATUS_SCRIPT_FORBIDDEN:
			self.assertIsNone(re.search(pattern, script, re.MULTILINE), f"forbidden in script: {pattern}")
		for pattern in STATUS_SCRIPT_REQUIRED:
			self.assertIsNotNone(re.search(pattern, script), f"missing in script: {pattern}")

	def test_status_panel_opens_only_from_its_header_action(self):
		# A page load (F5) never opens the panel: one `panel.open = true`, inside the action's togglePanel, and the
		# open state is never stored (localStorage/sessionStorage are forbidden above).
		script = self.status_script()
		masked = mask_js(script)
		opens = [m.start() for m in re.finditer(r"\bpanel\.open = true;", masked)]
		self.assertEqual(len(opens), 1, "panel.open = true must appear exactly once")
		start = masked.find("const togglePanel = () => {")
		self.assertNotEqual(start, -1, "togglePanel is missing")
		end = _matching_brace(masked, masked.find("{", start))
		self.assertTrue(start < opens[0] < end, "the panel opens outside togglePanel")
		self.assertIn("onClick: togglePanel", script)

	def test_status_line_pins_catch_their_violation(self):
		# CHG-009 design 8.2 (AC-1, AC-3): each status-line pin fails on the script with the wiring it guards broken
		script = self.status_script()
		for pattern, broken, replacement in STATUS_LINE_VIOLATIONS:
			with self.subTest(pattern=pattern):
				self.assertIn(pattern, STATUS_SCRIPT_REQUIRED)
				violating = re.sub(broken, replacement, script, count=1)
				self.assertNotEqual(violating, script)
				self.assertIsNotNone(re.search(pattern, script))
				self.assertIsNone(re.search(pattern, violating))

	def test_status_script_calls_use_literal_panel_methods(self):
		script = load_product_sources(suffixes=(".js",)).get(STATUS_SCRIPT_FILE)
		self.assertIsNotNone(script, f"{STATUS_SCRIPT_FILE} is missing")
		self.assertGreater(len(STATUS_SCRIPT_CALL.findall(script)), 0, "no call( found in script")
		self.assertEqual(check_status_script_calls(script, PANEL_METHODS), [])

	def test_status_script_call_check_catches_variable_and_unknown_method(self):
		allowed = ("erp_ai.ticket_panel.get_panel_data",)
		self.assertEqual(
			check_status_script_calls('state.call("erp_ai.ticket_panel.get_panel_data", {})', allowed), []
		)
		self.assertEqual(len(check_status_script_calls("state.call(METHOD, {})", allowed)), 1)
		self.assertEqual(len(check_status_script_calls('state.call("other.method", {})', allowed)), 1)
		self.assertEqual(len(check_status_script_calls("state\n.call(\n  METHOD)", allowed)), 1)

	def status_script(self):
		script = load_product_sources(suffixes=(".js",)).get(STATUS_SCRIPT_FILE)
		self.assertIsNotNone(script, f"{STATUS_SCRIPT_FILE} is missing")
		return script

	def test_status_script_calls_only_panel_methods(self):
		script = self.status_script()
		literals = {m.group(2) for m in STATUS_SCRIPT_CALL.finditer(script) if m.group(1) is not None}
		self.assertEqual(literals, set(PANEL_METHODS))
		self.assertEqual(
			whitelisted_paths(self.sources) & set(PANEL_METHODS),
			set(PANEL_METHODS),
		)
		self.assertEqual(check_call_allow_list(script, PANEL_METHODS, self.sources), [])

	def test_status_script_queries_only_app_root(self):
		script = self.status_script()
		self.assertIn('document.querySelector("#app")', script)
		self.assertEqual(check_status_script_queries(script), [])

	def test_status_script_has_one_window_state(self):
		script = self.status_script()
		self.assertIn(f"window.{STATUS_SCRIPT_STATE_NAME} = window.{STATUS_SCRIPT_STATE_NAME} ||", script)
		self.assertEqual(check_status_script_window_state(script), [])

	def test_status_script_socket_events_only_in_once_block(self):
		script = self.status_script()
		registered = socket_on_registrations(script)
		self.assertEqual(
			{name for _line, inside, name in registered if inside},
			{AGENT_STATUS_EVENT, "docinfo_update", "doc_update", "connect"},
		)
		self.assertEqual(check_socket_on_only_in_once_block(script, AGENT_STATUS_EVENT), [])

	def test_status_script_indicator_hides_with_display_none(self):
		self.assertEqual(check_status_indicator_hides(self.status_script()), [])

	def test_whitelisted_methods_declare_http_methods_without_guest(self):
		found = {(rel, node.name) for rel, node, _decorator in whitelisted_functions(self.sources)}
		self.assertTrue({(PANEL_FILE, "get_panel_data"), (PANEL_FILE, "send_message")} <= found, found)
		self.assertEqual(check_whitelisted_methods_declare_http_methods(self.sources), [])

	def test_ticket_panel_has_exactly_four_whitelisted_methods(self):
		# ADR-044 QĐ 1 (CHG-008), CHG-017: the panel gains a decision method and a result method; POST only, no guest
		self.assertEqual(
			sorted(PANEL_METHODS),
			[
				"erp_ai.ticket_panel.decide_proposal",
				"erp_ai.ticket_panel.decide_result",
				"erp_ai.ticket_panel.get_panel_data",
				"erp_ai.ticket_panel.send_message",
			],
		)
		self.assertEqual(check_ticket_panel_whitelist(self.sources), [])

	def test_ticket_panel_forbidden_calls(self):
		self.assertIn(".add_message(", self.sources[PANEL_FILE])
		self.assertEqual(check_ticket_panel_forbidden_calls(self.sources), [])

	def test_ticket_panel_does_not_evaluate_agent_gates(self):
		self.assertIn(PANEL_FILE, self.sources)
		self.assertEqual(check_ticket_panel_does_not_evaluate_agent_gates(self.sources), [])

	def test_layer_rules_forbid_ticket_panel_from_gateway_and_agent(self):
		rules = {scope: forbidden for scope, forbidden, _reason in LAYER_RULES}
		for scope in ("erp_ai.gateway", "erp_ai.agent"):
			self.assertIn("erp_ai.ticket_panel", rules[scope])
		# ADR-044 (CHG-008): the panel layer rule also forbids authority, tools and the state machine
		self.assertEqual(
			rules["erp_ai.ticket_panel"],
			(
				"erp_ai.gateway",
				"erp_ai.agent.runner",
				"erp_ai.agent.queue",
				"erp_ai.agent.authority",
				"erp_ai.agent.tools",
				"erp_ai.agent.changes.transitions",
			),
		)

	def test_status_event_name_matches_script(self):
		match = re.search(r'^AGENT_STATUS_EVENT = "([^"]+)"', self.sources[CONSTANTS_FILE], re.MULTILINE)
		self.assertIsNotNone(match, "AGENT_STATUS_EVENT not found in constants.py")
		script = load_product_sources(suffixes=(".js",)).get(STATUS_SCRIPT_FILE)
		self.assertIsNotNone(script, f"{STATUS_SCRIPT_FILE} is missing")
		self.assertIn(f'"{match.group(1)}"', script)

	def test_publish_realtime_only_in_run_status(self):
		self.assertIn(RUN_STATUS_FILE, self.sources)
		self.assertIn("publish_realtime", self.sources[RUN_STATUS_FILE])
		self.assertEqual(check_publish_realtime_only_in_run_status(self.sources), [])

	def test_run_status_imported_only_by_runner(self):
		self.assertIn(RUN_STATUS_FILE, self.sources)
		runner_imports = imported_modules(
			parse(RUNNER_FILE, self.sources[RUNNER_FILE]), module_name(RUNNER_FILE), False
		)
		self.assertIn(RUN_STATUS_MODULE, [target for _lineno, target in runner_imports])
		self.assertEqual(check_run_status_imported_only_by_runner(self.sources), [])

	def test_run_status_writes_nothing(self):
		self.assertIn(RUN_STATUS_FILE, self.sources)
		self.assertEqual(check_run_status_writes_nothing(self.sources), [])

	def test_no_open_doc_or_all_room(self):
		scanned = load_product_sources(suffixes=(".py", ".json", ".js", ".html"))
		self.assertIn(RUN_STATUS_FILE, scanned)
		self.assertIn(STATUS_SCRIPT_FILE, scanned)
		self.assertEqual(check_no_open_doc_or_all_room(scanned), [])

	def test_form_script_only_in_install(self):
		scanned = load_product_sources(suffixes=(".py", ".json", ".js", ".html"))
		self.assertIn(FORM_SCRIPT_DOCTYPE_NAME, scanned[INSTALL_FILE])
		self.assertIn(STATUS_SCRIPT_FILE, scanned)
		self.assertEqual(check_form_script_only_in_install(scanned), [])

	def test_hooks_have_no_page_injection(self):
		self.assertIn(HOOKS_FILE, self.sources)
		self.assertEqual(check_hooks_have_no_page_injection(self.sources), [])

	def test_install_deletes_only_status_script_on_uninstall(self):
		self.assertIn(INSTALL_FILE, self.sources)
		self.assertEqual(check_install_deletes_only_status_script(self.sources), [])
		self.assertIn(f'before_uninstall = "{UNINSTALL_HOOK}"', self.sources[HOOKS_FILE])

	# FEAT-006: routing (ADR-019..021) ------------------------------------------------------------

	def test_route_module_not_in_tool_modules_and_has_no_tools(self):
		self.assertIn("TOOL_MODULES", self.sources[REGISTRY_FILE])
		self.assertIn(ROUTE_FILE, self.sources)
		self.assertEqual(check_route_module_is_not_a_tool(self.sources), [])

	def test_route_module_single_ticket_save(self):
		self.assertIn(".save()", self.sources[ROUTE_FILE])
		self.assertEqual(check_route_module_single_ticket_save(self.sources), [])

	def test_assign_to_only_in_route_module(self):
		self.assertIn("assign_to.add(", self.sources[ROUTE_FILE])
		self.assertEqual(check_assign_to_only_in_route_module(self.sources), [])

	def test_no_share_bypass(self):
		self.assertGreater(len(only_python(self.sources)), 0)
		self.assertEqual(check_no_share_bypass(self.sources), [])

	def test_auto_assign_switch_only_in_policy(self):
		self.assertIn("auto_assign_enabled", POLICY_FIELDS)
		self.assertIn("auto_assign_enabled", self.sources[POLICY_FILE])
		# The runner gets the switch only by calling the policy function, never by reading the field.
		self.assertIn("policy.auto_assign_enabled(", self.sources[RUNNER_FILE])
		self.assertEqual(check_policy_fields_only_in_policy(self.sources), [])

	def test_site_environment_read_only_via_policy(self):
		changed = TestScannersCatchViolations.changed
		sample = SITE_ENVIRONMENT_SAMPLE
		# C-2: the field is not a POLICY_FIELDS name (the ERP AI Log column of the same name is written by
		# run_log.py); its own rule below holds on the real tree, and policy.py defines the reader.
		self.assertNotIn(SITE_ENVIRONMENT_FIELD, POLICY_FIELDS)
		for rel in SITE_ENVIRONMENT_FILES:
			self.assertIn(rel, self.sources)
		self.assertIn(f'{SITE_ENVIRONMENT_CONSTANT} = "{SITE_ENVIRONMENT_FIELD}"', self.sources[POLICY_FILE])
		self.assertIn(f"def {SITE_ENVIRONMENT_FIELD}(settings=None) -> str:", self.sources[POLICY_FILE])
		self.assertEqual(check_site_environment_readers(self.sources), [])

		def in_function(rel: str, body: str) -> dict:
			return changed(sample, rel, f"\n\ndef _sample(settings):\n\t{body}\n")

		outside = f"names {SITE_ENVIRONMENT_FIELD} outside {POLICY_FILE}"
		self.assertRuleSamples(
			check_site_environment_readers,
			sample,
			{
				"tasks.py reads settings.site_environment": (
					in_function(TASKS_FILE, "return settings.site_environment"),
					f"{TASKS_FILE}:12: {outside}",
				),
				"getattr with the name": (
					in_function(TASKS_FILE, 'return getattr(settings, "site_environment", "production")'),
					f"{TASKS_FILE}:12",
				),
				"stored value read directly": (
					in_function(
						"agent/executor.py",
						'return frappe.db.get_single_value("ERP AI Setting", "site_environment")',
					),
					"agent/executor.py:11",
				),
				"policy constant used to read the field": (
					in_function(
						"agent/executor.py", "return getattr(settings, policy.SITE_ENVIRONMENT_FIELD)"
					),
					"agent/executor.py:11",
				),
				"constant imported from policy": (
					changed(
						sample,
						"agent/executor.py",
						"\nfrom erp_ai.agent.policy import SITE_ENVIRONMENT_FIELD\n",
					),
					"agent/executor.py:9",
				),
				"Log column read by a report": (
					changed(
						sample,
						"report.py",
						'import frappe\n\nROWS = frappe.get_all("ERP AI Log", fields=["site_environment"])\n',
					),
					"report.py:3",
				),
				"keyword argument": (
					changed(sample, "report.py", "ROWS = dict(site_environment=1)\n"),
					"report.py:1",
				),
				"built by concatenation": (
					changed(sample, "report.py", 'FIELD = "site_" + "environment"\n'),
					"report.py:1",
				),
				"named in an SQL string": (
					changed(sample, "report.py", "SQL = 'select site_environment from `tabERP AI Log`'\n"),
					"report.py:1",
				),
				"another module's reader of the same name": (
					changed(
						sample,
						"report.py",
						"from erp_ai.agent.run_log import site_environment\n\nX = site_environment()\n",
					),
					"report.py:1",
				),
			},
		)
		# An allow-listed file stays allowed whatever it does with the field.
		for rel in SITE_ENVIRONMENT_FILES:
			with self.subTest(allowed=rel):
				self.assertEqual(
					check_site_environment_readers(changed(sample, rel, "\nX = settings.site_environment\n")),
					[],
				)

	def test_run_limit_triggers_subset_of_log_triggers(self):
		changed = TestScannersCatchViolations.changed
		self.assertEqual(check_run_limit_triggers_subset_of_log_triggers(self.sources), [])
		sample = RUN_LIMIT_SAMPLE
		limit_line = (
			"RUN_LIMIT_TRIGGERS = (TRIGGER_TICKET_INSERT, TRIGGER_COMMENT_MENTION, TRIGGER_REQUESTER_REPLY)"
		)
		log_line = 'TRIGGERS = ("ticket_insert", "comment_mention", "requester_reply", "kb_draft")'
		# The log may name the constants instead of the strings.
		named = changed(
			sample,
			RUN_LOG_FILE,
			replace=(
				log_line,
				"from erp_ai.constants import TRIGGER_COMMENT_MENTION, TRIGGER_KB_DRAFT, TRIGGER_REQUESTER_REPLY, "
				"TRIGGER_TICKET_INSERT\n"
				"TRIGGERS = (TRIGGER_TICKET_INSERT, TRIGGER_COMMENT_MENTION, TRIGGER_REQUESTER_REPLY, TRIGGER_KB_DRAFT)",
			),
		)
		self.assertEqual(check_run_limit_triggers_subset_of_log_triggers(named), [])
		not_logged = f"{RUN_LIMIT_TRIGGERS_NAME} has 'change_action', not in {RUN_LOG_FILE}"
		only_kb_draft = "must be exactly {'kb_draft'}"
		self.assertRuleSamples(
			check_run_limit_triggers_subset_of_log_triggers,
			sample,
			{
				"limit names a trigger the log does not have": (
					changed(
						sample,
						POLICY_FILE,
						replace=(
							limit_line,
							"RUN_LIMIT_TRIGGERS = (TRIGGER_TICKET_INSERT, TRIGGER_COMMENT_MENTION, "
							'TRIGGER_REQUESTER_REPLY, "change_action")',
						),
					),
					not_logged,
				),
				# w1a ruling (2): the KB-draft run is never counted toward the daily limit.
				"limit counts the KB draft": (
					changed(
						sample,
						POLICY_FILE,
						replace=(limit_line, limit_line.replace(")", ", TRIGGER_KB_DRAFT)")),
					),
					only_kb_draft,
				),
				# U6b-fixes Sửa 3: the requester-reply run is counted.
				"limit leaves out the requester reply": (
					changed(
						sample,
						POLICY_FILE,
						replace=(
							limit_line,
							"RUN_LIMIT_TRIGGERS = (TRIGGER_TICKET_INSERT, TRIGGER_COMMENT_MENTION)",
						),
					),
					only_kb_draft,
				),
				"log has another trigger outside the limit": (
					changed(
						sample, RUN_LOG_FILE, replace=(log_line, log_line.replace(")", ', "other_trigger")'))
					),
					only_kb_draft,
				),
				"log drops the KB draft": (
					changed(sample, RUN_LOG_FILE, replace=(log_line, log_line.replace(', "kb_draft"', ""))),
					only_kb_draft,
				),
				"log drops a limit trigger": (
					changed(
						sample, RUN_LOG_FILE, replace=(log_line, log_line.replace('"comment_mention", ', ""))
					),
					f"{RUN_LIMIT_TRIGGERS_NAME} has 'comment_mention', not in {RUN_LOG_FILE}",
				),
				"constants lack the KB draft": (
					changed(sample, CONSTANTS_FILE, replace=('TRIGGER_KB_DRAFT = "kb_draft"\n', "")),
					f"{CONSTANTS_FILE}: {KB_DRAFT_TRIGGER_NAME} missing",
				),
				"limit missing": (
					changed(sample, POLICY_FILE, replace=(limit_line, "")),
					f"{POLICY_FILE}: {RUN_LIMIT_TRIGGERS_NAME} missing",
				),
				"log triggers missing": (
					changed(sample, RUN_LOG_FILE, replace=(log_line, "")),
					f"{RUN_LOG_FILE}: {LOG_TRIGGERS_NAME} missing",
				),
				"limit computed": (
					changed(
						sample,
						POLICY_FILE,
						replace=(limit_line, "RUN_LIMIT_TRIGGERS = tuple(VALID_TRIGGERS)"),
					),
					f"{POLICY_FILE}:3: {RUN_LIMIT_TRIGGERS_NAME} is not a tuple",
				),
				"limit names an unknown constant": (
					changed(
						sample,
						POLICY_FILE,
						replace=(limit_line, limit_line.replace(")", ", TRIGGER_UNKNOWN)")),
					),
					"element TRIGGER_UNKNOWN is not a trigger name",
				),
				"policy file missing": (
					{rel: text for rel, text in sample.items() if rel != POLICY_FILE},
					f"{POLICY_FILE}: file missing",
				),
			},
		)

	def test_entry_types_unchanged(self):
		scanned = load_product_sources(suffixes=(".py", ".json"))
		self.assertIn(LOG_DOCTYPE_FILE, scanned)
		self.assertEqual(check_entry_types_unchanged(scanned), [])

	def test_log_trigger_options_match_run_log(self):
		from erp_ai.agent import run_log

		scanned = load_product_sources(suffixes=(".py", ".json"))
		expected = [*run_log.TRIGGERS, *run_log.CHANGE_TRIGGERS, *run_log.BOT_ACTION_TRIGGERS]
		self.assertEqual(check_log_trigger_options_match_run_log(scanned, expected), [])
		self.assertTrue(check_log_trigger_options_match_run_log(scanned, expected[:-1]))

	def test_decide_reads_one_click_switch_before_signature(self):
		scanned = load_product_sources(suffixes=(".py", ".json"))
		self.assertEqual(check_comment_signs_only_when_one_click(scanned), [])
		unguarded = "def _comment(ctx, p):\n\tx = change_link.decision_path(p.name, 'approve')\n"
		self.assertTrue(check_comment_signs_only_when_one_click({PROPOSE_TOOL_FILE: unguarded}))
		guarded = "def _comment(ctx, p):\n\tif ctx.one_click_approval:\n\t\tx = change_link.decision_path(p.name, 'a')\n"
		self.assertEqual(check_comment_signs_only_when_one_click({PROPOSE_TOOL_FILE: guarded}), [])
		self.assertEqual(check_decide_reads_one_click_switch_before_signature(scanned), [])
		good = (
			"def decide(name=None, action=None, _signature=None):\n"
			"\tif not policy.permission_switches(s).one_click_approval:\n\t\traise X\n"
			"\tif not change_link.signature_ok(name, action, _signature):\n\t\traise Y\n"
		)
		self.assertEqual(
			check_decide_reads_one_click_switch_before_signature({CHANGE_DECISION_FILE: good}), []
		)
		swapped = (
			"def decide(name=None, action=None, _signature=None):\n"
			"\tif not change_link.signature_ok(name, action, _signature):\n\t\traise Y\n"
			"\tif not policy.permission_switches(s).one_click_approval:\n\t\traise X\n"
		)
		for source, fragment in ((swapped, "before"), ("def decide():\n\tpass\n", "does not read")):
			with self.subTest(fragment=fragment):
				found = check_decide_reads_one_click_switch_before_signature({CHANGE_DECISION_FILE: source})
				self.assertTrue(found and fragment in found[0], found)

	def test_action_entries_built_only_in_run_log(self):
		scanned = load_product_sources()
		self.assertEqual(check_action_entries_built_only_in_run_log(scanned), [])
		hand_built = 'entry = {"tool": "x", "doctype": None, "name": "n", "ok": True}\n'
		found = check_action_entries_built_only_in_run_log({"agent/runner.py": hand_built})
		self.assertTrue(found and "agent/runner.py:1" in found[0], found)
		self.assertEqual(check_action_entries_built_only_in_run_log({RUN_LOG_FILE: hand_built}), [])
		self.assertEqual(
			check_action_entries_built_only_in_run_log({"agent/x.py": 'schema = {"tool": 1}\n'}), []
		)

	def test_policy_does_not_import_run_log(self):
		scanned = load_product_sources(suffixes=(".py", ".json"))
		self.assertEqual(check_policy_does_not_import_run_log(scanned), [])
		bad = {POLICY_FILE: "from erp_ai.agent import run_log\n"}
		self.assertTrue(check_policy_does_not_import_run_log(bad))

	def test_assign_field_not_used_for_decision(self):
		self.assertEqual(
			(ASSIGN_FIELD_ALLOWED_FILE, ASSIGN_FIELD_ALLOWED_FUNCTION), (AUTHORITY_FILE, "_assigned_by_other")
		)
		self.assertIn("_assign", self.sources[AUTHORITY_FILE])
		self.assertEqual(check_no_assign_column_for_decisions(self.sources), [])

	def test_route_module_bypass_rules_apply(self):
		route_only = {ROUTE_FILE: self.sources[ROUTE_FILE]}
		self.assertTrue(ROUTE_FILE.startswith(TOOLS_PREFIX))
		self.assertEqual(check_tools_never_bypass_permissions(route_only), [])
		self.assertEqual(check_no_share_bypass(route_only), [])

	def test_feature_never_assigns_sla_dates(self):
		self.assertGreater(len(only_python(scoped(self.sources, AGENT_PREFIX))), 0)
		self.assertEqual(check_feature_never_assigns_sla_dates(self.sources), [])

	def test_no_default_people_in_agent_python(self):
		self.assertIn("Việt Nam", self.sources["agent/prompts.py"])  # the coincidence the scan must tolerate
		self.assertEqual(check_no_default_people_in_agent_python(self.sources), [])

	# FEAT-004: change proposals (ADR-011, ADR-012) -----------------------------------------------

	def test_transitions_imported_only_by_controller_and_changes(self):
		controller = parse(PROPOSAL_CONTROLLER_FILE, self.sources[PROPOSAL_CONTROLLER_FILE])
		imports = [
			target
			for _lineno, target in imported_modules(controller, module_name(PROPOSAL_CONTROLLER_FILE), False)
		]
		self.assertIn(TRANSITIONS_MODULE, imports)
		self.assertEqual(check_transitions_imported_only_by_controller_and_changes(self.sources), [])

	def test_change_state_fields_written_only_in_changes(self):
		self.assertEqual(len(STATE_FIELDS), 19)
		declared = [
			ast.literal_eval(node.value)
			for node in parse(TRANSITIONS_FILE, self.sources[TRANSITIONS_FILE]).body
			if isinstance(node, ast.Assign)
			and any(getattr(t, "id", None) == "STATE_FIELDS" for t in node.targets)
		]
		self.assertEqual(declared, [STATE_FIELDS])
		self.assertEqual(check_change_state_fields_written_only_in_changes(self.sources), [])

	def test_change_guard_uses_resolve_safe_path(self):
		self.assertIn("def resolve_safe_path(", self.sources[SOURCE_TOOL_FILE])
		self.assertIn(CHANGE_GUARD_FILE, self.sources)
		self.assertEqual(check_change_guard_uses_resolve_safe_path(self.sources), [])

	def test_proposal_doctype_permissions(self):
		scanned = load_product_sources(suffixes=(".py", ".json"))
		self.assertIn(PROPOSAL_DOCTYPE_FILE, scanned)
		self.assertEqual(check_proposal_doctype_permissions(scanned), [])

	def test_propose_change_builds_no_target_itself(self):
		# CHG-008 design 8.2: the card and the comment share one builder, so the tool must not rebuild it
		self.assertEqual(check_propose_change_builds_no_target_itself(self.sources), [])
		clean = self.sources[PROPOSE_TOOL_FILE]
		no_call = check_propose_change_builds_no_target_itself(
			{PROPOSE_TOOL_FILE: clean.replace("proposal_target(", "x(")}
		)
		self.assertTrue(any("does not call change_text.proposal_target" in text for text in no_call), no_call)
		for needle in ("proposal.is_new_file", 'proposal.get("is_new_file")', "CHANGE_KIND_CODE"):
			with self.subTest(needle=needle):
				source = clean.replace("\tform = f", f"\t_ = {needle}\n\tform = f", 1)
				found = check_propose_change_builds_no_target_itself({PROPOSE_TOOL_FILE: source})
				self.assertTrue(any("itself" in text for text in found), found)

	def test_panel_cards_called_only_by_panel(self):
		# CHG-008 design 8.2: `panel_cards` checks no gate, so only the gated panel method may call it
		self.assertEqual(check_panel_cards_called_only_by_panel(self.sources), [])
		controller = self.sources[PROPOSAL_CONTROLLER_FILE]
		whitelisted = controller.replace(
			"def panel_cards(", '@frappe.whitelist(methods=["POST"])\ndef panel_cards('
		)
		found = check_panel_cards_called_only_by_panel(
			{**self.sources, PROPOSAL_CONTROLLER_FILE: whitelisted}
		)
		self.assertTrue(any("must not be whitelisted" in text for text in found), found)
		other = {
			**self.sources,
			"agent/messages.py": self.sources["agent/messages.py"] + "\nx = panel_cards(1)\n",
		}
		found = check_panel_cards_called_only_by_panel(other)
		self.assertTrue(any("outside ticket_panel.py" in text for text in found), found)
		silent = {**self.sources, PANEL_FILE: self.sources[PANEL_FILE].replace("panel_cards(", "x(")}
		found = check_panel_cards_called_only_by_panel(silent)
		self.assertTrue(any("does not call panel_cards" in text for text in found), found)

	def test_role_instructor_only_in_decider_role(self):
		# CHG-008 design 8.2: one place compares the decider role, so the panel and the form cannot drift apart
		self.assertEqual(check_role_instructor_only_in_decider_role(self.sources), [])
		panel = (
			self.sources[PANEL_FILE] + "\nfrom erp_ai.constants import ROLE_INSTRUCTOR\nx = ROLE_INSTRUCTOR\n"
		)
		found = check_role_instructor_only_in_decider_role({**self.sources, PANEL_FILE: panel})
		self.assertTrue(any("outside has_decider_role" in text for text in found), found)
		literal = self.sources["change_decision.py"] + '\nY = "ERP AI Instructor"\n'
		found = check_role_instructor_only_in_decider_role({**self.sources, "change_decision.py": literal})
		self.assertTrue(any("role literal" in text for text in found), found)

	def test_panel_decision_follows_adr_044(self):
		# CHG-008 design 3.2, 8.2: the D-3 order, the gate on the proposal's own ticket, one predicate call and one
		# controller call through the action table, and nothing of the switch, state machine, queue or undo
		self.assertEqual(check_panel_decision_follows_adr_044(self.sources), [])
		panel = self.sources[PANEL_FILE]
		gate = '\t_require_panel_access(head.ticket, method="decide")\n'
		# CHG-010: the predicate call now also passes the proposal's console flag
		predicate = (
			"\trefusal = proposal_form.panel_decision_refusal(head.change_status, console=head.is_console)\n"
		)
		cases = {
			"no predicate": (
				# CHG-010: same call text with the console flag
				(
					"proposal_form.panel_decision_refusal(head.change_status, console=head.is_console)",
					"None",
				),
				"panel_decision_refusal 0 times",
			),
			"browser ticket": (
				(
					"def decide_proposal(name=None, action=None)",
					"def decide_proposal(name=None, action=None, ticket=None)",
				),
				"expected ['name', 'action']",
			),
			"gate on the name": (
				("_require_panel_access(head.ticket,", "_require_panel_access(name,"),
				"not the ticket of proposal_head",
			),
			"gate label": (('method="decide")', 'method="get")'), 'method="decide"'),
			"direct controller call": (
				("PANEL_DECISIONS[action](name)", "proposal_form.approve(name)"),
				"approve is called directly",
			),
			"state machine": (
				("\tresult = PANEL_DECISIONS", "\ttransitions.finish(name)\n\tresult = PANEL_DECISIONS"),
				"names transitions",
			),
			"switch read": (
				("\trefusal = ", "\tpolicy.permission_switches(None)\n\trefusal = "),
				"names permission_switches",
			),
			# CHG-010: a direct panel_approve call and a predicate without the console flag are caught
			"direct panel_approve call": (
				("PANEL_DECISIONS[action](name)", "proposal_form.panel_approve(name)"),
				"panel_approve is called directly",
			),
			"predicate without console flag": (
				(
					"panel_decision_refusal(head.change_status, console=head.is_console)",
					"panel_decision_refusal(head.change_status)",
				),
				"without console=head.is_console",
			),
			"undo in the table": (("proposal_form.reject,", "proposal_form.undo,"), "names undo"),
			"predicate before gate": ((gate + predicate, predicate + gate), "order is not"),
		}
		for case, ((old, new), fragment) in cases.items():
			with self.subTest(case=case):
				self.assertIn(old, panel)
				found = check_panel_decision_follows_adr_044({PANEL_FILE: panel.replace(old, new, 1)})
				self.assertTrue(any(fragment in text for text in found), found)

	def test_agent_modules_never_reference_panel(self):
		# CHG-008 AC-8 (b): no bot module names the panel or its decision method, in code, text or comments
		scanned = load_product_sources(suffixes=(".py", ".md"))
		self.assertGreater(len(scoped(scanned, AGENT_PREFIX)), 0)
		self.assertEqual(check_agent_modules_never_reference_panel(scanned), [])
		for extra, fragment in (
			("from erp_ai import ticket_panel\n", "names ticket_panel"),
			('METHOD = "erp_ai.ticket_panel.decide_proposal"\n', "names decide_proposal"),
			("# the bot could call decide_proposal\n", "names decide_proposal"),
		):
			with self.subTest(extra=extra):
				found = check_agent_modules_never_reference_panel(
					{**scanned, "agent/messages.py": scanned["agent/messages.py"] + extra}
				)
				self.assertTrue(any(fragment in text for text in found), found)

	def test_status_script_constants_match_the_server_values(self):
		# CHG-008 F-2: a drifting action or status value would fail every click or show the wrong buttons
		script = self.status_script()
		self.assertEqual(check_status_script_constants_match_server(script), [])
		for name, value in (
			("ACTION_APPROVE", change_link.ACTION_APPROVE),
			("ACTION_REJECT", change_link.ACTION_REJECT),
			("STATUS_PENDING", CHANGE_STATUS_PENDING),
			("STATUS_APPLIED", CHANGE_STATUS_APPLIED),
			("APPROVE_GUIDANCE_TEXT", prompts.APPROVE_GUIDANCE_TEXT),
			("KIND_GUIDANCE", messages.KIND_GUIDANCE),
		):
			with self.subTest(constant=name):
				drifted = re.sub(
					rf'(const {name} =\s+"){re.escape(value)}(";)',
					lambda match: f"{match.group(1)}{value}x{match.group(2)}",
					script,
					count=1,
				)
				self.assertNotEqual(drifted, script)
				found = check_status_script_constants_match_server(drifted)
				self.assertTrue(any(name in text for text in found), found)

	def test_status_script_decides_by_one_post_then_one_reload(self):
		# CHG-008 design 4.2, ADR-044 QĐ 7: one decision call, inside decide, one reload per answer, no timer
		script = self.status_script()
		self.assertEqual(check_status_script_decides_once(script), [])
		cases = {
			"no reload after a failure": (
				re.sub(r"(= TEXT_DECIDE_FAILED;)\s*reload\(\);", r"\1", script, count=1),
				"reload() 1 times",
			),
			"a second call": (script + f'\nstate.call("{PANEL_DECIDE_METHOD}", {{}});\n', "called 2 times"),
			"a timer": (
				script.replace("panel.deciding = true;", "setTimeout(reload, 1);\npanel.deciding = true;", 1),
				"setTimeout(",
			),
			"no decide": (
				script.replace("const decide = (", "const decideIt = (", 1),
				"function decide is missing",
			),
		}
		for case, (source, fragment) in cases.items():
			with self.subTest(case=case):
				self.assertNotEqual(source, script)
				found = check_status_script_decides_once(source)
				self.assertTrue(any(fragment in text for text in found), found)

	def test_tool_never_saves_proposal(self):
		self.assertIn("proposal.insert()", self.sources[PROPOSE_TOOL_FILE])
		self.assertEqual(check_tool_never_saves_proposal(self.sources), [])

	def test_fs_writes_only_in_file_writer(self):
		for rel in (FILE_WRITER_FILE, PROPOSAL_CONTROLLER_FILE, PROPOSE_TOOL_FILE, CHANGE_GUARD_FILE):
			self.assertIn(rel, self.sources)
		# The scan sees the real writer's writes, so a clean result elsewhere is not a blind scan.
		writer = parse(FILE_WRITER_FILE, self.sources[FILE_WRITER_FILE])
		found = " ".join(message for _node, message in _fs_writes(FILE_WRITER_FILE, writer))
		for expected in ("os.replace", "os.remove", "tempfile.mkstemp", "os.fdopen with mode 'wb'"):
			self.assertIn(expected, found)
		# Design §8.2, AC-47: the os.* directory and rename functions are in the scanned table.
		self.assertLessEqual(set(FS_WRITE_OS_FUNCTIONS), FS_WRITE_FUNCTIONS)
		self.assertEqual(check_fs_writes_only_in_file_writer(self.sources), [])

	def test_file_writer_rechecks_through_resolver(self):
		self.assertIn("def _refuse_unless_canonical(", self.sources[FILE_WRITER_FILE])
		self.assertEqual(check_file_writer_rechecks_through_resolver(self.sources), [])

	def test_changes_never_set_user_or_publish(self):
		self.assertIn("frappe.session.user", self.sources["agent/changes/apply_job.py"])  # a read is allowed
		self.assertGreater(len(only_python(scoped(self.sources, CHANGES_PREFIX))), 3)
		self.assertEqual(check_changes_never_set_user_or_publish(self.sources), [])

	# ADR-022 git rules (FEAT-004 T44) ------------------------------------------------------------------

	def _git_scan(self) -> GitScan:
		for rel in (SOURCE_TOOL_FILE, PROCESS_RUNNER_FILE, CONSTANTS_FILE, CHANGE_GUARD_FILE, *NO_GIT_FILES):
			self.assertIn(rel, self.sources)
		return GitScan(self.sources)

	def _found_subcommands(self, scan: GitScan, rel: str) -> set:
		return {sub for argv in scan.argvs if argv.root_rel == rel for sub in argv.subcommands or ()}

	def test_change_text_layer_rule_covers_every_other_module(self):
		rule = next((rule for rule in LAYER_RULES if rule[0] == CHANGE_TEXT_MODULE), None)
		self.assertIsNotNone(rule)
		self.assertIn(module_name(CHANGE_TEXT_FILE), {module_name(rel) for rel in self.sources})
		for rel in only_python(self.sources):
			top = ".".join(module_name(rel).split(".")[:2])
			if top not in (PACKAGE, CONSTANTS_MODULE):
				self.assertTrue(any(module_in(top, forbidden) for forbidden in rule[1]), top)

	def test_git_subcommands_only_allowed_sets_per_file(self):
		scan = self._git_scan()
		source_constants = scan.assignments[SOURCE_TOOL_FILE]
		# The product's own sets equal ADR-022 QĐ 2, so the hand-written sets here are the same contract.
		self.assertEqual(
			scan.strings(SOURCE_TOOL_FILE, source_constants["GIT_READ_SUBCOMMANDS"]), GIT_READ_SET
		)
		self.assertEqual(
			scan.strings(SOURCE_TOOL_FILE, source_constants["GIT_SUBCOMMANDS"]), GIT_LEGACY_SUBCOMMANDS
		)
		# Not a blind scan: the expanded call sites of both wrappers and the log/blame tool are seen.
		self.assertEqual(self._found_subcommands(scan, PROCESS_RUNNER_FILE), set(GIT_WRITE_SET))
		self.assertLessEqual(
			{
				"log",
				"blame",
				"rev-parse",
				"rev-list",
				"status",
				"check-ignore",
				"merge-base",
				"diff-tree",
				"cat-file",
			},
			self._found_subcommands(scan, SOURCE_TOOL_FILE),
		)
		self.assertEqual(check_git_subcommands_only_allowed_sets_per_file(self.sources), [])

	def test_no_forbidden_git_operations_in_product(self):
		scan = self._git_scan()
		self.assertGreater(len([argv for argv in scan.argvs if argv.git is not None]), 10)
		self.assertEqual(check_no_forbidden_git_operations_in_product(self.sources), [])

	def test_git_commit_add_rm_argv_shape(self):
		scan = self._git_scan()
		writes = [argv for argv in scan.argvs if argv.subcommands and argv.subcommands & GIT_WRITE_SET]
		self.assertEqual(sorted(sub for argv in writes for sub in argv.subcommands), ["add", "commit", "rm"])
		self.assertTrue(all(argv.rel == PROCESS_RUNNER_FILE for argv in writes))
		self.assertEqual(check_git_commit_add_rm_argv_shape(self.sources), [])

	def test_git_env_single_definition(self):
		scan = self._git_scan()
		new_commands = [
			(rel, root) for rel, root, _elements, _git in scan.templates if not scan.is_legacy(rel, root)
		]
		self.assertEqual(sorted(rel for rel, _root in new_commands), [PROCESS_RUNNER_FILE, SOURCE_TOOL_FILE])
		self.assertEqual(check_git_env_single_definition(self.sources), [])

	def test_bot_identity_constants(self):
		self._git_scan()
		self.assertEqual(check_bot_identity_constants(self.sources), [])

	def test_no_git_in_web_and_runner(self):
		self._git_scan()
		self.assertIn(
			PROPOSAL_CONTROLLER_FILE, {rel for rel, _node, _decorator in whitelisted_functions(self.sources)}
		)
		self.assertEqual(check_no_git_in_web_and_runner(self.sources), [])

	def test_bench_allowlist_has_no_git_running_subcommands(self):
		scan = self._git_scan()
		commands = scan.strings(CHANGE_GUARD_FILE, scan.assignments[CHANGE_GUARD_FILE][BENCH_COMMANDS_NAME])
		self.assertIn("migrate", commands)
		# ADR-040 QĐ 6: restart is listed, the still-forbidden commands are not.
		self.assertIn(RESTART_BENCH_COMMAND, commands)
		self.assertEqual(commands & set(FORBIDDEN_BENCH_COMMANDS), set())
		self.assertEqual(check_bench_allowlist_has_no_git_running_subcommands(self.sources), [])

	def test_apps_root_single_function(self):
		self._git_scan()
		self.assertEqual(check_apps_root_single_function(self.sources), [])

	# ADR-023 Ràng buộc (FEAT-004 T68) ------------------------------------------------------------------

	def test_no_get_whitelist_reaches_change_state(self):
		# Not a blind scan: the real decision methods are seen as reaching the state machine (all POST).
		reaching = {(rel, node.name) for rel, node, _methods in change_state_whitelists(self.sources)}
		for name in CHANGE_STATE_NAMES:
			self.assertIn((PROPOSAL_CONTROLLER_FILE, name), reaching)
		self.assertIn(("change_decision.py", "decide"), reaching)
		# ADR-044 (CHG-008): the panel's decision method reaches approve / reject through PANEL_DECISIONS
		self.assertIn((PANEL_FILE, PANEL_DECIDE_FUNCTION), reaching)
		self.assertEqual(check_no_get_whitelist_reaches_change_state(self.sources), [])

	def test_change_link_builds_no_api_method_path(self):
		self.assertIn(CHANGE_LINK_FILE, self.sources)
		self.assertIn("/app/erp-ai-change-proposal", change_link_string_shapes(self.sources))
		self.assertEqual(check_change_link_builds_no_api_method_path(self.sources), [])

	def test_registry_has_one_grant_function(self):
		self.assertIn(f"{GRANT_TABLE_NAME} = (", self.sources[REGISTRY_FILE])
		self.assertIn(f".{RUNNER_SCHEMA_CALL}()", self.sources[RUNNER_FILE])
		self.assertEqual(check_registry_has_one_grant_function(self.sources), [])

	def test_agent_write_flag_only_in_run_log_and_propose_tool(self):
		references = agent_write_references(self.sources)
		self.assertEqual(
			{rel for rel, _node, kind in references if kind == AGENT_WRITE_OPENER},
			set(AGENT_WRITE_OPENER_FILES),
		)
		self.assertEqual(
			{rel for rel, _node, kind in references if kind == AGENT_WRITE_FLAG_NAME},
			{AGENT_WRITE_GUARD_FILE},
		)
		self.assertEqual(check_agent_write_flag_only_in_run_log_and_propose_tool(self.sources), [])

	def assertRuleSamples(self, check, compliant: dict, violating: dict):
		"""`check` lets the compliant sources through and catches each violating case: `{case: (sources, fragment)}`."""
		self.assertEqual(check(compliant), [], "the compliant sample is flagged")
		self.assertGreater(len(violating), 0)
		for case, (sources, fragment) in violating.items():
			with self.subTest(case=case):
				TestScannersCatchViolations.assertCaught(self, check(sources), fragment)

	def test_privilege_alert_reads_shared_generic_write_tools(self):
		# The one in-process product import of this class: the runner's tool tables are values, not text.
		from erp_ai.agent.runner import GENERIC_WRITE_TOOLS, WRITE_TOOL_TARGETS

		changed = TestScannersCatchViolations.changed
		self.assertIn("api_update_record", GENERIC_WRITE_TOOLS)
		self.assertIn("api_", self.sources[TASKS_FILE])  # `api_key` and `like "%api_%"` stay allowed
		self.assertEqual(
			check_generic_write_tools_shared(WRITE_TOOL_TARGETS, GENERIC_WRITE_TOOLS, self.sources), []
		)
		self.assertEqual(check_tasks_names_no_write_tool(self.sources, WRITE_TOOL_TARGETS), [])

		# Rule 1: every tool with a model-chosen DocType is in the tuple tasks.py reads from the runner.
		targets = {"post_comment": ("Comment", "comment"), "api_update_record": (None, "name")}
		generic = ("api_update_record",)
		shared_import = "from erp_ai.agent.runner import GENERIC_WRITE_TOOLS\n"
		by_module = changed(
			changed(
				PRIVILEGE_SOURCES_SAMPLE,
				TASKS_FILE,
				replace=(shared_import, "from erp_ai.agent import runner\n"),
			),
			TASKS_FILE,
			replace=("in GENERIC_WRITE_TOOLS", "in runner.GENERIC_WRITE_TOOLS"),
		)
		self.assertEqual(check_generic_write_tools_shared(targets, generic, by_module), [])
		self.assertRuleSamples(
			lambda sources: check_generic_write_tools_shared(targets, generic, sources),
			PRIVILEGE_SOURCES_SAMPLE,
			{
				"own tuple in tasks.py": (
					changed(
						PRIVILEGE_SOURCES_SAMPLE,
						TASKS_FILE,
						replace=(shared_import, "GENERIC_WRITE_TOOLS = ('api_update_record',)\n"),
					),
					"defines its own GENERIC_WRITE_TOOLS",
				),
				"another runner tuple under the shared name": (
					changed(
						PRIVILEGE_SOURCES_SAMPLE,
						TASKS_FILE,
						replace=(
							shared_import,
							"from erp_ai.agent.runner import RECORD_TOOLS as GENERIC_WRITE_TOOLS\n",
						),
					),
					"never reads erp_ai.agent.runner.GENERIC_WRITE_TOOLS",
				),
			},
		)
		self.assertRuleSamples(
			lambda targets: check_generic_write_tools_shared(targets, generic, PRIVILEGE_SOURCES_SAMPLE),
			targets,
			{
				"new generic tool left out": (
					{**targets, "api_rename_record": (None, "name")},
					"api_rename_record",
				)
			},
		)

		# Rule 2: no tool name of WRITE_TOOL_TARGETS written in tasks.py (the bare `api_` is not a tool name).
		self.assertRuleSamples(
			lambda sources: check_tasks_names_no_write_tool(sources, WRITE_TOOL_TARGETS),
			PRIVILEGE_SOURCES_SAMPLE,
			{
				case: (changed(PRIVILEGE_SOURCES_SAMPLE, TASKS_FILE, extra), name)
				for case, extra, name in (
					("double quotes", '\nHAND = ("api_update_record",)\n', "api_update_record"),
					("single quotes", "\nHAND = ('api_delete_record',)\n", "api_delete_record"),
					("concatenation", "\nHAND = \"api_create\" + '_record'\n", "api_create_record"),
					("implicit concatenation", '\nHAND = "api_submit" "_record"\n', "api_submit_record"),
					("comment", "\n# also reads api_call_method\n", "api_call_method"),
					("non-api write tool", '\nANSWER = "post_comment"\n', "post_comment"),
				)
			},
		)

	def test_privilege_alert_watermark_and_clock_rules(self):
		changed = TestScannersCatchViolations.changed
		sample = PRIVILEGE_SOURCES_SAMPLE
		scanned = load_product_sources(suffixes=(".py", ".json", ".js", ".html"))
		for rel in (TASKS_FILE, SETTING_CONTROLLER_FILE, SETTING_DOCTYPE_FILE, RUN_LOG_FILE):
			self.assertIn(rel, scanned)
		self.assertIn(f"def {WATERMARK_WRITER}(", scanned[TASKS_FILE])
		self.assertIn("def read_privilege_watermark(", scanned[SETTING_CONTROLLER_FILE])
		self.assertEqual(check_watermark_field_only_in_allowed_places(scanned), [])
		self.assertEqual(check_tasks_never_saves_or_inserts_setting(scanned), [])
		self.assertEqual(check_privilege_job_reads_no_other_clock(scanned), [])
		self.assertEqual(check_no_version_reads(scanned), [])
		self.assertEqual(check_privilege_condition_ignores_owner(scanned), [])
		self.assertEqual(check_write_entry_inserts_and_commits(scanned), [])

		def in_function(body: str) -> str:
			return f"\n\ndef _sample():\n\t{body}\n"

		# Rule 3: the field name only in the Setting JSON/controller and in WATERMARK_WRITER of tasks.py.
		outside = "outside the Setting"
		self.assertRuleSamples(
			check_watermark_field_only_in_allowed_places,
			sample,
			{
				"reader in the job, single quotes": (
					changed(
						sample,
						TASKS_FILE,
						replace=(
							"lower = read_privilege_watermark()",
							f"lower = frappe.db.get_single_value(SETTING_DOCTYPE, '{WATERMARK_FIELD}')",
						),
					),
					outside,
				),
				"module constant by concatenation": (
					changed(sample, TASKS_FILE, '\nFIELD = "privilege_alert_" + "checked_until"\n'),
					outside,
				),
				"implicit concatenation": (
					changed(sample, TASKS_FILE, '\nFIELD = "privilege_alert_" "checked_until"\n'),
					outside,
				),
				"another product module": (
					changed(sample, "alerts.py", f'FIELD = "{WATERMARK_FIELD}"\n'),
					"alerts.py:1",
				),
				"client script": (
					changed(sample, "public/js/x.js", f'frm.set_value("{WATERMARK_FIELD}", null);\n'),
					"public/js/x.js:1",
				),
				"writer renamed": (
					changed(sample, TASKS_FILE, replace=(f"def {WATERMARK_WRITER}(", "def _move_watermark(")),
					f"no function {WATERMARK_WRITER}",
				),
				"writer without the field": (
					changed(sample, TASKS_FILE, replace=(f'"{WATERMARK_FIELD}", upper', "FIELD, upper")),
					"does not write",
				),
			},
		)

		# Rule 4: tasks.py never save()s or insert()s an ERP AI Setting document.
		self.assertRuleSamples(
			check_tasks_never_saves_or_inserts_setting,
			sample,
			{
				case: (changed(sample, TASKS_FILE, in_function(body)), "on the ERP AI Setting document")
				for case, body in (
					("get_doc literal save", 'frappe.get_doc("ERP AI Setting").save()'),
					("get_single constant save", "frappe.get_single(SETTING_DOCTYPE).save()"),
					("tracked variable insert", "doc = frappe.new_doc(SETTING_DOCTYPE)\n\tdoc.insert()"),
					(
						"dict insert",
						"frappe.get_doc({'doctype': 'ERP AI Setting'}).insert(ignore_permissions=True)",
					),
				)
			},
		)

		# Rule 5: the alert job (and every tasks.py function it reaches) reads no clock but now_datetime / its
		# `now` argument; other jobs of tasks.py are out of scope.
		job_upper = "upper = (get_datetime(now) if now else now_datetime())"

		def in_job(line: str) -> dict:
			return changed(sample, TASKS_FILE, replace=(job_upper, f"{line}\n\t{job_upper}"))

		def in_helper(helper: str, line: str) -> dict:
			return changed(sample, TASKS_FILE, replace=(f"def {helper}():\n", f"def {helper}():\n\t{line}\n"))

		passed_as_value = changed(
			in_job("for find in (_stamp,):\n\t\tfind()"),
			TASKS_FILE,
			"\n\ndef _stamp():\n\treturn frappe.qb.from_('X').select(Now())\n",
			replace=("import frappe\n", "import frappe\nfrom frappe.query_builder.functions import Now\n"),
		)
		self.assertRuleSamples(
			check_privilege_job_reads_no_other_clock,
			sample,
			{
				"datetime.now in the job": (
					changed(
						in_job("started = datetime.now()"),
						TASKS_FILE,
						replace=(
							"from datetime import timedelta",
							"from datetime import datetime, timedelta",
						),
					),
					"check_privilege_escalation reads the clock with datetime.datetime.now()",
				),
				"aliased utcnow in a helper it calls": (
					changed(
						in_helper("_scripts_by_agent", "started = dt.datetime.utcnow()"),
						TASKS_FILE,
						replace=("import frappe\n", "import datetime as dt\n\nimport frappe\n"),
					),
					"_scripts_by_agent reads the clock with datetime.datetime.utcnow()",
				),
				"query builder Now in a helper passed as a value": (
					passed_as_value,
					"_stamp reads the clock with frappe.query_builder.functions.Now()",
				),
				"SQL NOW() split by concatenation in a helper": (
					in_helper(
						"_keys_without_value", 'frappe.db.sql("select 1 where creation <= NO" + "W()")'
					),
					"_keys_without_value: SQL clock",
				),
				"lower-case now ( in an f-string in the job": (
					in_job('frappe.db.sql(f"select 1 where creation <= now ( ) - {1}")'),
					"check_privilege_escalation: SQL clock",
				),
				"module constant with NOW() read by the job": (
					changed(
						in_job("frappe.db.sql(CUTOFF_SQL)"),
						TASKS_FILE,
						'\nCUTOFF_SQL = "select 1 where creation <= NOW()"\n',
					),
					"check_privilege_escalation: SQL clock in 'select 1 where creation <= NOW()'",
				),
				"module constant with NOW() in an f-string of a helper": (
					changed(
						in_helper("_keys_without_value", 'frappe.db.sql(f"select 1 where {CUTOFF}")'),
						TASKS_FILE,
						'\nCUTOFF = "creation <= NOW()"\n',
					),
					"_keys_without_value: SQL clock in 'select 1 where creation <= NOW()'",
				),
				"job renamed": (
					changed(
						sample, TASKS_FILE, replace=("def check_privilege_escalation(", "def _run_alert(")
					),
					"no function check_privilege_escalation",
				),
			},
		)
		other_job = (
			"from datetime import datetime\n\nfrom frappe.query_builder.functions import Now\n"
			"\n\ndef recompute_monthly_spend():\n\treturn datetime.now(), datetime.utcnow(), Now()"
			'\n\n\ndef reprobe_exhausted_keys():\n\treturn frappe.db.sql("select 1 where creation <= NOW()")\n'
		)
		for case, sources in (
			("another job of tasks.py reads datetime.now and NOW()", changed(sample, TASKS_FILE, other_job)),
			("frappe.utils.now() in the job", in_job("stamp = frappe.utils.now()")),
			("the plain string 'now' in a helper", in_helper("_scripts_by_agent", 'label = "now"')),
			(
				"a module constant with NOW() read only by another job",
				changed(
					sample,
					TASKS_FILE,
					'\nSTALE_SQL = "select 1 where creation <= NOW()"\n'
					"\n\ndef reprobe_exhausted_keys():\n\treturn frappe.db.sql(STALE_SQL)\n",
				),
			),
		):
			with self.subTest(case=case):
				self.assertEqual(check_privilege_job_reads_no_other_clock(sources), [])

		# Rule 6: product code never reads the Version DocType.
		self.assertRuleSamples(
			check_no_version_reads,
			sample,
			{
				case: (changed(sample, rel, extra), f"{rel}:")
				for case, rel, extra in (
					(
						"get_all double quotes",
						"agent/a.py",
						'import frappe\nfrappe.get_all("Version", pluck="name")\n',
					),
					(
						"db.get_all single quotes",
						"agent/b.py",
						"import frappe\nfrappe.db.get_all('Version')\n",
					),
					(
						"built by concatenation",
						"agent/c.py",
						'import frappe\nfrappe.qb.DocType("Ver" + "sion")\n',
					),
					(
						"raw SQL table",
						"agent/d.py",
						'import frappe\nfrappe.db.sql("select data from `tabVersion`")\n',
					),
					("client script", "public/js/e.js", "frappe.db.get_list('Version');\n"),
				)
			},
		)

		# Rule 7: the permission condition (and the tasks.py functions it calls) never filters on modified_by/owner.
		rows = "\treturn [row.name for row"
		self.assertRuleSamples(
			check_privilege_condition_ignores_owner,
			sample,
			{
				"modified_by column": (
					changed(
						sample,
						TASKS_FILE,
						replace=('like("%api_%")', 'like("%api_%") & (log.modified_by == "x")'),
					),
					f"{PRIVILEGE_CONDITION_FUNCTION} filters on modified_by",
				),
				"owner in a called helper": (
					changed(sample, TASKS_FILE, replace=('action.get("ok")', 'action.get("owner") == "x"')),
					"_usable filters on owner",
				),
				"keyword filter": (
					changed(
						sample,
						TASKS_FILE,
						replace=(
							rows,
							"\tfrappe.get_all(LOG_DOCTYPE, filters=dict(modified_by=upper))\n" + rows,
						),
					),
					"filters on modified_by",
				),
				"SQL text": (
					changed(
						sample,
						TASKS_FILE,
						replace=(
							rows,
							'\tfrappe.db.sql("select name from `tabHas Role` where `owner` = %s", upper)\n'
							+ rows,
						),
					),
					"filters on owner",
				),
				"condition function renamed": (
					changed(
						sample, TASKS_FILE, replace=(f"def {PRIVILEGE_CONDITION_FUNCTION}(", "def _records(")
					),
					f"no function {PRIVILEGE_CONDITION_FUNCTION}",
				),
			},
		)

		# Rule 8: write_entry inserts and commits in its own body, insert first.
		run_log = {RUN_LOG_FILE: RUN_LOG_SAMPLE}
		commit_block = "\tif not frappe.flags.in_test:\n\t\tfrappe.db.commit()\n"
		self.assertEqual(
			check_write_entry_inserts_and_commits(
				changed(
					changed(run_log, RUN_LOG_FILE, replace=("frappe.db.commit()", "db.commit()")),
					RUN_LOG_FILE,
					"from frappe import db\n",
				)
			),
			[],
		)
		self.assertRuleSamples(
			check_write_entry_inserts_and_commits,
			run_log,
			{
				case: (changed(run_log, RUN_LOG_FILE, extra, replace), WRITE_ENTRY_FUNCTION)
				for case, extra, replace in (
					(
						"commit moved to a helper",
						"\n\ndef _commit():\n\tfrappe.db.commit()\n",
						("\t\tfrappe.db.commit()", "\t\t_commit()"),
					),
					(
						"commit deferred to a nested job",
						"",
						(
							commit_block,
							"\tdef _later():\n\t\tfrappe.db.commit()\n\n\tfrappe.enqueue(_later, enqueue_after_commit=True)\n",
						),
					),
					(
						"commit before insert",
						"",
						("\tdoc.insert()\n" + commit_block, "\tfrappe.db.commit()\n\tdoc.insert()\n"),
					),
					("insert replaced", "", ("doc.insert()", "doc.db_insert()")),
				)
			},
		)

	def test_set_user_agent_only_in_enter_agent_session(self):
		self.assertEqual(check_set_user_agent_only_in_enter_agent_session(self.sources), [])
		self.assertIn(f"def {SESSION_SWITCH_FUNCTION}(", self.sources[AUTHORITY_FILE])

	def test_authority_has_no_comment_scan_for_instructor(self):
		self.assertIn(f"def {RUN_INSTRUCTOR_FUNCTION}(", self.sources[AUTHORITY_FILE])
		self.assertIn(f"authority.{RUN_INSTRUCTOR_FUNCTION}(", self.sources[RUNNER_FILE])
		self.assertEqual(check_authority_has_no_comment_scan_for_instructor(self.sources), [])

	def test_agent_modules_import_alone_in_fresh_process(self):
		# STD-DESIGN-6: an import cycle stays hidden in-process when another test imported a module first.
		env = dict(os.environ, PYTHONPATH=os.pathsep.join([str(REPO_ROOT), os.environ.get("PYTHONPATH", "")]))
		for module in FRESH_IMPORT_MODULES:
			with self.subTest(module=module):
				done = subprocess.run(
					[sys.executable, "-c", f"import {module}"],
					capture_output=True,
					text=True,
					timeout=120,
					env=env,
					check=False,
				)
				self.assertEqual(done.returncode, 0, done.stderr)


# ---------------------------------------------------------------------------------------------------
# Tests of the scanners themselves (STD-TEST-8): violating code is caught, clean code is not flagged
# ---------------------------------------------------------------------------------------------------

ENQUEUE_GOOD_KEYWORDS = "queue='long', timeout=1, enqueue_after_commit=True, job_id='j', deduplicate=True"

# ADR-022 (T44): a small product that keeps every git rule; each caught case changes one file of it.
GIT_CLEAN = {
	SOURCE_TOOL_FILE: '''"""Read tools; git_commit_only never uses --amend (a docstring is not code)."""
import os
import subprocess

import frappe

from erp_ai.constants import BOT_GIT_EMAIL, BOT_GIT_NAME

GIT_SUBCOMMANDS = {"log", "blame"}
GIT_READ_SUBCOMMANDS = frozenset({"rev-parse", "status", "cat-file"})


def get_source_root():
	return os.path.realpath(os.path.dirname(os.path.dirname(frappe.get_app_path("frappe"))))


def git_source(args, ctx):
	try:
		sub = args.get("subcommand")
		if not isinstance(sub, str) or sub not in GIT_SUBCOMMANDS:
			return None
		command = ["git", "--no-pager", "-C", ctx.repo, sub, *args.get("args")]
		return subprocess.run(command, timeout=30, env={**os.environ, "GIT_PAGER": "cat"})
	except OSError:
		return None


def git_global_options(*, read):
	options = ["--no-pager", "-c", f"core.hooksPath={HOOKS}", "-c", "core.fsmonitor=false"]
	return [*options, "--no-optional-locks"] if read else options


def git_env(*, identity):
	env = {"PATH": "/usr/bin", "GIT_CONFIG_GLOBAL": "/dev/null", "GIT_CONFIG_NOSYSTEM": "1", "GIT_TERMINAL_PROMPT": "0"}
	if identity:
		env.update(
			{
				"GIT_AUTHOR_NAME": BOT_GIT_NAME,
				"GIT_COMMITTER_NAME": BOT_GIT_NAME,
				"GIT_AUTHOR_EMAIL": BOT_GIT_EMAIL,
				"GIT_COMMITTER_EMAIL": BOT_GIT_EMAIL,
			}
		)
	return env


def run_git_read(repo_root, subcommand, *args, limit_s=30):
	return subprocess.run(
		[TIMEOUT_EXECUTABLE, "-s", "KILL", str(limit_s), "git", *git_global_options(read=True), subcommand, *args],
		cwd=repo_root,
		env=git_env(identity=False),
		timeout=limit_s + 5,
		start_new_session=True,
	)


def read_git_state(repo_root, rel, names):
	run_git_read(repo_root, "rev-parse", "--verify", "-q", "HEAD")
	run_git_read(repo_root, "rev-parse", *names)
	return run_git_read(repo_root, "status", "--porcelain=v1", "--", f":(literal){rel}")


def git_blob(repo_root, commit, rel):
	return run_git_read(repo_root, "cat-file", "blob", f"{commit}:{rel}")
''',
	PROCESS_RUNNER_FILE: '''"""bench and git add/commit/rm; never `-a`/`--amend`, never `git push`."""
import subprocess

import frappe

from erp_ai.agent.tools import source


def _run_git_write(repo_root, rels, limit_s, subcommand_args):
	return _run_wrapped(
		["git", *source.git_global_options(read=False), *subcommand_args, "--", *rels],
		cwd=repo_root,
		env=source.git_env(identity=True),
		limit_s=limit_s,
	)


def git_add_new(repo_root, rel, limit_s):
	return _run_git_write(repo_root, (rel,), limit_s, ["add"])


def git_commit_only(repo_root, rels, subject, body, limit_s):
	return _run_git_write(
		repo_root, sorted(rels), limit_s, ["commit", "--only", "--no-gpg-sign", "--quiet", "-m", subject, "-m", body]
	)


def git_unstage_new(repo_root, rel, limit_s):
	return _run_git_write(repo_root, (rel,), limit_s, ["rm", "--cached", "-q"])


def run_bench(args, limit_s):
	return _run_wrapped([BENCH, *args], cwd=frappe.utils.get_bench_path(), env=_minimal_env(), limit_s=limit_s)


def _run_wrapped(command, *, cwd, env, limit_s):
	return subprocess.run([TIMEOUT, str(limit_s), *command], cwd=cwd, env=env, timeout=limit_s + 5, start_new_session=True)
''',
	CONSTANTS_FILE: 'AGENT_USER = "ai.agent@example.com"\nBOT_GIT_NAME = "ERP AI Agent"\nBOT_GIT_EMAIL = "erp-ai-agent@bot.invalid"\n',
	CHANGE_GUARD_FILE: """from erp_ai.agent.tools import source

PATH_INVALID = "đường dẫn nằm ngoài apps/"
SITE_COMMANDS = ("migrate", "clear-cache")
BUILD_COMMAND = "build"
RESTART_COMMAND = "restart"
BENCH_COMMANDS = (*SITE_COMMANDS, BUILD_COMMAND, "version", RESTART_COMMAND)


def check_write_path(rel):
	return source.read_git_state(source.get_source_root(), rel, [])


def _bench_shape(command, site):
	return [BUILD_COMMAND, "--app", site] if command == BUILD_COMMAND else ["--site", site, command]
""",
	"agent/changes/apply_job.py": """import os

from erp_ai.agent.changes import process_runner
from erp_ai.agent.tools import source


def run_change(name, repo, rel, subject, body):
	if source.git_head(repo) is None:
		return None
	return process_runner.git_commit_only(repo, (rel,), subject, body, source.GIT_TIMEOUT_S)


def _full(root, rel):
	return os.path.join(source.get_source_root(), rel)
""",
	PROPOSAL_CONTROLLER_FILE: """import frappe

from erp_ai.agent import change_text, queue


@frappe.whitelist(methods=["POST"])
def approve(name):
	return queue.enqueue_change(name)


def form_data(doc):
	return change_text.render(doc.applied_branch)
""",
	HANDLERS_FILE: "import frappe\n\nfrom erp_ai.agent import policy\n\n\ndef on_update(doc, method=None):\n\treturn policy.agent_enabled()\n",
	RUNNER_FILE: "import frappe\n\nfrom erp_ai.agent.tools import registry\n\n\ndef run_for_ticket(name):\n\treturn registry.dispatch(name)\n",
	"ticket_panel.py": """import frappe

from erp_ai.agent.tools import source


@frappe.whitelist(methods=["GET"])
def get_panel_data(name):
	return _panel(name)


def _panel(name):
	return {"name": name}


def _not_web(repo):
	return source.git_head(repo)
""",
}


class TestScannersCatchViolations(unittest.TestCase):
	def assertCaught(self, violations, *fragments):
		self.assertGreater(len(violations), 0, "scanner missed the violation")
		for fragment in fragments:
			self.assertTrue(any(fragment in text for text in violations), f"{fragment!r} not in {violations}")

	# layer imports -----------------------------------------------------------------------------

	def test_layer_imports_catches_each_forbidden_direction(self):
		cases = {
			"gateway/cost.py": "from erp_ai.agent import policy\n",
			"gateway/__init__.py": "from erp_ai import eval\n",
			"agent/policy.py": "from erp_ai.eval import run_eval\n",
			"agent/runner.py": "import erp_ai.handlers\n",
			"agent/tools/read.py": "from erp_ai import gateway\n",
			"agent/tools/registry.py": "from erp_ai.agent.runner import run_for_ticket\n",
			"agent/tools/write_ticket.py": "from erp_ai.agent import runner\n",
			"handlers.py": "from erp_ai.gateway import call_model\n",
			"gateway/breaker.py": "from erp_ai.erp_ai_agent.doctype.erp_ai_setting import erp_ai_setting\n",
			"agent/authority.py": "from erp_ai.erp_ai_agent import doctype\n",
			"ticket_panel.py": "from erp_ai.gateway import call_model\n",
			"gateway/cache.py": "from erp_ai import ticket_panel\n",
			"agent/messages.py": "from erp_ai.ticket_panel import get_panel_data\n",
		}
		for rel, source in cases.items():
			with self.subTest(rel=rel):
				rel = rel.partition("#")[0]
				self.assertCaught(check_layer_imports({rel: source}), rel)

	def test_layer_imports_catches_changes_directions(self):
		forbidden_from_changes = (
			"erp_ai.gateway",
			"erp_ai.agent.runner",
			"erp_ai.agent.run_status",
			"erp_ai.eval",
			"erp_ai.handlers",
			"erp_ai.tasks",
			"erp_ai.install",
			"erp_ai.erp_ai_agent",
		)
		for target in forbidden_from_changes:
			with self.subTest(target=target):
				source = f"import {target}.x\n"
				self.assertCaught(check_layer_imports({"agent/changes/transitions.py": source}), target)
		for rel in ("agent/tools/propose_change.py", "agent/tools/change_guard.py"):
			with self.subTest(rel=rel):
				source = "from erp_ai.agent.changes import transitions\n"
				self.assertCaught(check_layer_imports({rel: source}), "erp_ai.agent.changes")
		allowed = {
			"agent/changes/transitions.py": (
				"from erp_ai.agent.run_log import write_entry\nfrom erp_ai.constants import PROPOSAL_DOCTYPE\n"
			),
			"agent/changes/apply_job.py": (
				"from erp_ai.agent import policy, queue\nfrom erp_ai.agent.changes import transitions\n"
				"from erp_ai.agent.tools import change_guard, source\nfrom erp_ai.agent import change_text\n"
			),
			"erp_ai_agent/doctype/erp_ai_change_proposal/erp_ai_change_proposal.py": (
				"from erp_ai.agent.changes import transitions\n"
			),
		}
		self.assertEqual(check_layer_imports(allowed), [])

	def test_layer_imports_catches_policy_importing_tools(self):
		cases = (
			"from erp_ai.agent.tools import source\n",
			"import erp_ai.agent.tools.source\n",
			"from erp_ai.agent.tools.source import get_source_root\n",
			"def f():\n\tfrom erp_ai.agent.tools import source\n",
			"from .tools import source\n",
		)
		for source in cases:
			with self.subTest(source=source):
				self.assertCaught(
					check_layer_imports({POLICY_FILE: source}),
					"agent/policy.py:",
					"erp_ai.agent.tools",
					"STD-DESIGN-6: policy là tầng dưới của tools, không import ngược",
				)
		allowed = "from erp_ai.constants import LEVELS\nfrom erp_ai.agent import run_log\n"
		self.assertEqual(check_layer_imports({POLICY_FILE: allowed}), [])

	def test_layer_imports_catches_lazy_and_relative_imports(self):
		lazy = "def f():\n\tfrom erp_ai.agent.runner import run_for_ticket\n"
		self.assertCaught(check_layer_imports({"handlers.py": lazy}), "erp_ai.agent.runner")
		relative = "from ... import gateway\n"
		self.assertCaught(check_layer_imports({"agent/tools/read.py": relative}), "erp_ai.gateway")
		sibling = "from .. import runner\n"
		self.assertCaught(check_layer_imports({"agent/tools/read.py": sibling}), "erp_ai.agent.runner")

	def test_layer_imports_allows_permitted_directions(self):
		allowed = {
			"eval/run_eval.py": "from erp_ai.agent.runner import CLASSIFY_MAX_TOKENS\nfrom erp_ai import gateway\n",
			"agent/runner.py": "from erp_ai import gateway\nfrom erp_ai.agent.tools.registry import execute_tool\n",
			"tasks.py": "from erp_ai import alerts, gateway\n",
			"handlers.py": "from erp_ai.agent import policy\nfrom erp_ai.agent.queue import enqueue_agent_run\n",
			"agent/tools/read.py": "from erp_ai.agent import authority, policy, prompts\n",
			"gateway/__init__.py": "from erp_ai import alerts\nfrom erp_ai.gateway import breaker\n",
		}
		self.assertEqual(check_layer_imports(allowed), [])

	def test_import_boundaries_catch_anthropic_and_other_apps(self):
		self.assertCaught(check_import_boundaries({"agent/runner.py": "import anthropic\n"}), "anthropic")
		self.assertCaught(
			check_import_boundaries({"gateway/__init__.py": "from anthropic import Anthropic\n"})
		)
		self.assertCaught(
			check_import_boundaries({"agent/runner.py": "import workflowcore.x\n"}), "workflowcore"
		)
		self.assertEqual(check_import_boundaries({CLIENT_FILE: "import anthropic\n"}), [])

	def test_import_boundaries_allowlist_catches_any_other_top_level_module(self):
		cases = {
			"erpnext": "import erpnext\n",
			"telephony": "from telephony.x import y\n",
			"hrms": "import hrms\n",
			"requests": "import requests.adapters\n",
			"erpnext.stock": "def f():\n\tfrom erpnext import stock\n",
		}
		for fragment, source in cases.items():
			with self.subTest(fragment=fragment):
				self.assertCaught(check_import_boundaries({"agent/runner.py": source}), fragment)

	def test_import_boundaries_allowlist_accepts_stdlib_frappe_helpdesk_and_relative(self):
		clean = (
			"from __future__ import annotations\n"
			"import json\nimport os.path\nfrom datetime import datetime\n"
			"import frappe\nfrom frappe.utils import now\nfrom helpdesk.helpdesk.doctype import hd_ticket\n"
			"from erp_ai import alerts\nfrom . import policy\nfrom .prompts import build\n"
		)
		self.assertEqual(check_import_boundaries({"agent/runner.py": clean}), [])

	def test_import_boundaries_named_library_only_in_restart_check(self):
		restart = "agent/changes/restart_check.py"
		caught = {
			"psutil elsewhere": ("agent/changes/apply_job.py", "import psutil\n", "psutil"),
			"redis elsewhere": ("agent/runner.py", "import redis\n", "redis"),
			"requests in restart_check": (
				restart,
				"import psutil\nimport redis\nimport requests\n",
				"requests",
			),
			"rq in restart_check": (restart, "import psutil\nimport redis\nimport rq\n", "rq"),
		}
		for label, (rel, source, fragment) in caught.items():
			with self.subTest(label):
				self.assertCaught(check_import_boundaries({rel: source}), f"{rel}:", fragment)
		self.assertEqual(check_import_boundaries({restart: "import psutil\nimport redis\n"}), [])
		self.assertEqual(
			check_import_boundaries({restart: "from psutil import Process\nfrom redis import exceptions\n"}),
			[],
		)
		# dead exception: the file no longer imports a listed name (a comment or a string does not count)
		no_redis = "import psutil\n# import redis\nNAME = 'redis'\n"
		self.assertCaught(check_import_boundaries({restart: no_redis}), restart, "redis", "dead exception")
		with patch(f"{__name__}.NAMED_LIBRARY_IMPORTS", {"agent/changes/gone.py": frozenset({"psutil"})}):
			self.assertCaught(
				check_import_boundaries({restart: "import os\n"}), "agent/changes/gone.py", "dead exception"
			)
		self.assertEqual(NAMED_LIBRARY_IMPORTS, {restart: frozenset({"psutil", "redis"})})

	def test_restart_check_library_use_catches_signals_and_clients(self):
		restart = "agent/changes/restart_check.py"
		head = "import os\nimport psutil\nimport redis\n"
		cases = {
			# a method call that signals or tunes a process (only the attribute-call condition sees it)
			"kill": "psutil.Process(1).kill()\n",
			"terminate": "p = psutil.Process(1)\np.terminate()\n",
			"send_signal": "psutil.Process(1).send_signal(15)\n",
			"suspend": "psutil.Process(1).suspend()\n",
			"resume": "psutil.Process(1).resume()\n",
			"nice": "psutil.Process(1).nice(5)\n",
			"ionice": "psutil.Process(1).ionice(0)\n",
			"rlimit": "psutil.Process(1).rlimit(0)\n",
			"cpu_affinity": "psutil.Process(1).cpu_affinity([0])\n",
			# an attribute of psutil/redis outside the allowed set (only the attribute-reference condition)
			"psutil.process_iter": "psutil.process_iter()\n",
			"redis.Redis": "redis.Redis()\n",
			"redis.Redis#alias": "import redis as r\nr.Redis()\n",
			"redis.exceptions.ConnectionError": "E = redis.exceptions.ConnectionError\n",
			# an import of a name outside the allowed set (only the import condition)
			"psutil.process_iter#from": "from psutil import process_iter\n",
			"redis.Redis#from": "from redis import Redis as R\n",
			"redis.client": "import redis.client\n",
			# subprocess, os.kill, os.killpg, signal (only the forbidden-module condition)
			"os.kill": "os.kill(1, 15)\n",
			"os.kill#alias": "from os import kill as k\nk(1, 15)\n",
			"os.killpg": "os.killpg(1, 15)\n",
			"subprocess": "import subprocess\n",
			"signal": "import signal\n",
			"signal.SIGTERM": "import signal as s\nn = s.SIGTERM\n",
		}
		for fragment, body in cases.items():
			with self.subTest(fragment):
				self.assertCaught(
					check_restart_check_library_use({restart: head + body}),
					f"{restart}:",
					fragment.partition("#")[0],
				)
		allowed = (
			head + "from psutil import Error, Process\nfrom redis.exceptions import RedisError\n"
			"ERRORS = (redis.exceptions.RedisError, psutil.Error)\n"
			"t = psutil.Process(os.getppid()).create_time()\nos.getppid()\n"
		)
		self.assertEqual(check_restart_check_library_use({restart: allowed}), [])
		self.assertCaught(check_restart_check_library_use({}), restart, "missing")

	# enqueue -----------------------------------------------------------------------------------

	def test_single_enqueue_catches_calls_aliases_and_enqueue_doc(self):
		for source in (
			"import frappe\nfrappe.enqueue('x')\n",
			"import frappe\nfrappe.enqueue_doc('HD Ticket', 'T')\n",
			"from frappe import enqueue\nenqueue('x')\n",
			"import frappe\njob = frappe.enqueue\n",
		):
			with self.subTest(source=source):
				self.assertCaught(check_single_enqueue_site({"handlers.py": source}))

	def test_single_enqueue_allows_queue_module_and_wrapper_calls(self):
		sources = {
			QUEUE_FILE: "import frappe\nfrappe.enqueue('x')\n",
			"handlers.py": "from erp_ai.agent.queue import enqueue_agent_run\nenqueue_agent_run('T', 'ticket_insert')\n",
		}
		self.assertEqual(check_single_enqueue_site(sources), [])

	def test_enqueue_targets_pinned(self):
		self.assertEqual(
			ENQUEUE_TARGETS,
			(
				"erp_ai.agent.runner.run_for_ticket",
				"erp_ai.agent.changes.apply_job.run_change",
				"erp_ai.agent.daily_report.run_daily_report",
				"erp_ai.agent.kpi.run_weekly_kpi",
				"erp_ai.agent.monthly_review.run_monthly_review",
				"erp_ai.agent.lifecycle.run_task_lifecycle",
			),
		)

	@staticmethod
	def enqueue_call(target: str, keywords: str = ENQUEUE_GOOD_KEYWORDS) -> str:
		return f"frappe.enqueue({target!r}, {keywords})\n"

	def test_enqueue_call_shape_accepts_runner_and_change_job(self):
		good = "import frappe\n" + "".join(self.enqueue_call(target) for target in ENQUEUE_TARGETS)
		self.assertEqual(check_enqueue_call_shape({QUEUE_FILE: good}), [])

	def test_enqueue_call_shape_requires_one_call_per_target(self):
		calls = [self.enqueue_call(target) for target in ENQUEUE_TARGETS]
		for label, body in (("missing one", calls[1:]), ("one extra", calls + calls[-1:])):
			with self.subTest(calls=label):
				self.assertCaught(
					check_enqueue_call_shape({QUEUE_FILE: "import frappe\n" + "".join(body)}),
					"one per target",
				)

	def test_enqueue_call_shape_requires_each_target_once(self):
		for index, target in enumerate(ENQUEUE_TARGETS):
			with self.subTest(target=target):
				calls = [self.enqueue_call(other) for other in ENQUEUE_TARGETS]
				calls[index - 1] = self.enqueue_call(target)
				body = "import frappe\n" + "".join(calls)
				violations = check_enqueue_call_shape({QUEUE_FILE: body})
				self.assertCaught(violations, "each of")
				self.assertFalse(any("first argument" in text for text in violations), violations)

	def test_enqueue_call_shape_rejects_target_outside_set(self):
		others = "".join(self.enqueue_call(target) for target in ENQUEUE_TARGETS[:-1])
		for bad in ("erp_ai.other.fn", "erp_ai.agent.changes.apply_job", "erp_ai.agent.runner.run"):
			with self.subTest(target=bad):
				body = "import frappe\n" + others + self.enqueue_call(bad)
				self.assertCaught(check_enqueue_call_shape({QUEUE_FILE: body}), "first argument")
		not_literal = "import frappe\n" + others + f"frappe.enqueue(TARGET, {ENQUEUE_GOOD_KEYWORDS})\n"
		self.assertCaught(check_enqueue_call_shape({QUEUE_FILE: not_literal}), "first argument")

	def test_enqueue_call_shape_requires_five_parameters_on_each_call(self):
		for index, target in enumerate(ENQUEUE_TARGETS):
			for name in ENQUEUE_REQUIRED_KEYWORDS:
				with self.subTest(target=target, missing=name):
					keywords = ", ".join(
						part for part in ENQUEUE_GOOD_KEYWORDS.split(", ") if not part.startswith(f"{name}=")
					)
					calls = [self.enqueue_call(other) for other in ENQUEUE_TARGETS]
					calls[index] = self.enqueue_call(target, keywords)
					violations = check_enqueue_call_shape({QUEUE_FILE: "import frappe\n" + "".join(calls)})
					self.assertCaught(violations, f"missing keyword {name}=")
					self.assertEqual(len(violations), 1, violations)

	# no save on configuration ------------------------------------------------------------------

	def test_no_save_catches_setting_and_credential_saves(self):
		cases = (
			"import frappe\ns = frappe.get_doc('ERP AI Setting')\ns.save()\n",
			"import frappe\nfrappe.get_single('ERP AI Setting').save()\n",
			"import frappe\nfrom erp_ai.constants import SETTING_DOCTYPE\nd = frappe.get_cached_doc(SETTING_DOCTYPE)\nd.save()\n",
			"import frappe\nc = frappe.new_doc('ERP AI Credential')\nc.save(ignore_permissions=True)\n",
			"import frappe\nfrom erp_ai import constants\nd = frappe.get_doc(constants.SETTING_DOCTYPE)\nd.save()\n",
			"import frappe\nd = frappe.get_doc({'doctype': 'ERP AI Credential', 'label': 'x'})\nd.save()\n",
			"import frappe\nd = frappe.get_doc(doctype='ERP AI Credential')\nd.save()\n",
			"import frappe\nfrappe.get_doc({'doctype': CREDENTIAL_DOCTYPE}).save()\n",
			"def f(settings):\n\tsettings.save()\n",
		)
		for source in cases:
			with self.subTest(source=source):
				self.assertCaught(check_no_save_on_config({"tasks.py": source}), "ADR-004")
		controller = "class ERPAISetting:\n\tdef x(self):\n\t\tself.save()\n"
		self.assertCaught(check_no_save_on_config({CONFIG_CONTROLLER_FILES[0]: controller}), "ADR-004")

	def test_no_save_allows_other_documents_and_set_value(self):
		source = (
			"import frappe\n"
			"ticket = frappe.get_doc('HD Ticket', 'T')\n"
			"ticket.save()\n"
			"frappe.db.set_value('ERP AI Credential', 'row', {'status': 'x'})\n"
		)
		self.assertEqual(check_no_save_on_config({"agent/tools/write_ticket.py": source}), [])

	# tools never bypass permissions ------------------------------------------------------------

	def test_tools_bypass_catches_every_forbidden_call(self):
		cases = (
			"import frappe\nframe = frappe.get_doc('HD Ticket', 'T').save(ignore_permissions=True)\n",
			"import frappe\nfrappe.flags.ignore_permissions = True\n",
			"import frappe\nfrappe.db.set_value('HD Ticket', 'T', 'status', 'Open')\n",
			"import frappe\nfrappe.db.sql('UPDATE `tabHD Ticket` SET status = 1')\n",
			"import frappe\nfrappe.db.sql(query)\n",
			"import frappe\nfrappe.db.sql('SELECT 1; UPDATE `tabHD Ticket` SET status = 1')\n",
			"import frappe\nfrappe.set_user('Administrator')\n",
			"import frappe\nfrappe.get_all('HD Ticket', fields=['name'])\n",
			"import frappe\nfrappe.db.get_all('HD Ticket')\n",
			"def f(doc):\n\tdoc.db_update()\n",
		)
		for source in cases:
			with self.subTest(source=source):
				self.assertCaught(check_tools_never_bypass_permissions({"agent/tools/read.py": source}))

	def test_tools_bypass_allows_get_list_read_sql_and_doctype_metadata(self):
		source = (
			"import frappe\n"
			"frappe.get_list('HD Ticket', fields=['name'])\n"
			"frappe.db.sql('SELECT name FROM `tabHD Ticket`')\n"
			"frappe.get_all('DocType', {'module': 'ERP AI agent'}, pluck='name')\n"
		)
		self.assertEqual(check_tools_never_bypass_permissions({"agent/tools/read.py": source}), [])

	def test_tools_trusted_scanner_flags_only_trusted_true_in_tools(self):
		flagged = "from erp_ai.agent.messages import add_message\nadd_message(t, 'x', trusted=True)\n"
		self.assertCaught(
			check_tools_never_pass_trusted_messages({"agent/tools/x.py": flagged}), "agent/tools/x.py:2: "
		)
		clean = (
			"add_message(t, 'x')\n"
			"add_message(t, 'x', trusted=False)\n"
			"add_message(t, 'x', trusted=flag)\n"
		)
		self.assertEqual(check_tools_never_pass_trusted_messages({"agent/tools/x.py": clean}), [])
		self.assertEqual(check_tools_never_pass_trusted_messages({"agent/runner.py": flagged}), [])

	def test_tools_bypass_ignores_code_outside_tools(self):
		source = "import frappe\nfrappe.db.set_value('X', 'y', 'z', 1)\nfrappe.get_all('X')\n"
		self.assertEqual(check_tools_never_bypass_permissions({"agent/runner.py": source}), [])

	QUERY_BUILDER_SOURCES = (
		# (source, line of the reported violation); the first three are design-w0-fixes-5 point 1 (a)-(c).
		('import frappe\nt = frappe.qb.DocType("Error Log")\n', 2),
		('import frappe\nfrappe.qb.from_("HD Ticket").select("*").run()\n', 2),
		("from frappe.query_builder import DocType\n", 1),
		("import frappe\nfrappe.qb.get_query('HD Ticket')\n", 2),
		("import frappe\nbuilder = frappe.qb\n", 2),
		("import frappe as f\nf.qb.DocType('HD Ticket')\n", 2),
		("from frappe import qb\n", 1),
		("import frappe.query_builder\n", 1),
		("import frappe.query_builder as builder\n", 1),
		("from frappe.query_builder.functions import Count\n", 1),
	)

	def test_tools_never_bypass_permissions_flags_query_builder(self):
		for source, line in self.QUERY_BUILDER_SOURCES:
			with self.subTest(source=source):
				self.assertCaught(
					check_tools_never_bypass_permissions({"agent/tools/x.py": source}),
					f"agent/tools/x.py:{line}: ",
					"ADR-034",
				)

	def test_query_builder_outside_tools_allowed(self):
		outside = ("agent/system_read.py", "agent/tools_x.py", "agent/toolset/x.py", "eval/agent/tools/x.py")
		for rel in outside:
			for source, _line in self.QUERY_BUILDER_SOURCES:
				with self.subTest(rel=rel, source=source):
					self.assertEqual(check_tools_never_bypass_permissions({rel: source}), [])

	# subprocess --------------------------------------------------------------------------------

	def test_subprocess_catches_imports_and_os_shell(self):
		for source in (
			"import subprocess\n",
			"from subprocess import run\n",
			"import os\nos.system('ls')\n",
			"import os\nos.popen('ls')\n",
		):
			with self.subTest(source=source):
				self.assertCaught(check_subprocess_only_in_source_tool({"agent/runner.py": source}))
		self.assertEqual(
			check_subprocess_only_in_source_tool(
				{SOURCE_TOOL_FILE: "import subprocess\nsubprocess.run(['git'])\n"}
			),
			[],
		)

	def test_subprocess_catches_aliased_imports_and_more_os_exec_names(self):
		for source in (
			"import subprocess as sp\nsp.run(['ls'])\n",
			"from subprocess import run as r\nr(['ls'])\n",
			"import os\nos.posix_spawn('a', ['a'], {})\n",
			"import os\nos.execvpe('a', ['a'], {})\n",
			"import os\nos.spawnlp(os.P_WAIT, 'a', 'a')\n",
			"from os import system\nsystem('ls')\n",
			"import os as o\no.system('ls')\n",
		):
			with self.subTest(source=source):
				self.assertCaught(
					check_subprocess_only_in_source_tool({"agent/runner.py": source}), "outside"
				)

	def test_subprocess_call_shape_checks_aliased_calls(self):
		for source in (
			"import subprocess as sp\nsp.run(['git'])\n",
			"from subprocess import run\nrun(['git'])\n",
			"from subprocess import check_output as co\nco('git log', timeout=3)\n",
		):
			with self.subTest(source=source):
				self.assertCaught(check_subprocess_call_shape({SOURCE_TOOL_FILE: source}))
		good = "from subprocess import run\nrun(['git'], timeout=3)\n"
		self.assertEqual(check_subprocess_call_shape({SOURCE_TOOL_FILE: good}), [])

	def test_subprocess_call_shape_requires_timeout_list_and_no_shell(self):
		good = "import subprocess\nsubprocess.run(['git', 'log'], timeout=30, capture_output=True)\n"
		self.assertEqual(check_subprocess_call_shape({SOURCE_TOOL_FILE: good}), [])
		cases = {
			"timeout=": "import subprocess\nsubprocess.run(['git'])\n",
			"shell=": "import subprocess\nsubprocess.run(['git'], timeout=3, shell=True)\n",
			"string command": "import subprocess\nsubprocess.run('git log', timeout=3)\n",
			"only run()": "import subprocess\nsubprocess.Popen(['git'], timeout=3)\n",
		}
		for fragment, source in cases.items():
			with self.subTest(fragment=fragment):
				self.assertCaught(check_subprocess_call_shape({SOURCE_TOOL_FILE: source}), fragment)

	def test_subprocess_call_shape_timeout_wrapped_git_needs_group_cwd_and_own_env(self):
		head = "import os\nimport subprocess\nsubprocess.run([TIMEOUT_EXECUTABLE, '-s', 'KILL', '5', 'git'], timeout=10"
		good = f"{head}, cwd=repo, env=git_env(identity=False), start_new_session=True)\n"
		self.assertEqual(check_subprocess_call_shape({SOURCE_TOOL_FILE: good}), [])
		literal = good.replace("TIMEOUT_EXECUTABLE", "'timeout'")
		self.assertEqual(check_subprocess_call_shape({SOURCE_TOOL_FILE: literal}), [])
		cases = (
			("without start_new_session=True", f"{head}, cwd=repo, env=git_env(identity=False))\n"),
			(
				"without start_new_session=True",
				f"{head}, cwd=repo, env=git_env(identity=False), start_new_session=False)\n",
			),
			("without cwd=", f"{head}, env=git_env(identity=False), start_new_session=True)\n"),
			("without env=", f"{head}, cwd=repo, start_new_session=True)\n"),
			("env= uses os.environ", f"{head}, cwd=repo, env={{**os.environ}}, start_new_session=True)\n"),
			("env= uses os.environ", f"{head}, cwd=repo, env=dict(os.environ), start_new_session=True)\n"),
			("env= uses os.environ", f"{head}, cwd=repo, env=os.environ, start_new_session=True)\n"),
		)
		for fragment, source in cases:
			for variant in (source, source.replace("TIMEOUT_EXECUTABLE", "'timeout'")):
				with self.subTest(variant=variant):
					self.assertCaught(check_subprocess_call_shape({SOURCE_TOOL_FILE: variant}), fragment)
		plain_git = (
			"import os\nimport subprocess\nsubprocess.run(['git', 'log'], timeout=3, env={**os.environ})\n"
		)
		self.assertEqual(check_subprocess_call_shape({SOURCE_TOOL_FILE: plain_git}), [])

	def test_subprocess_allowed_in_process_runner_only_besides_source_tool(self):
		self.assertEqual(SUBPROCESS_FILES, ("agent/tools/source.py", "agent/changes/process_runner.py"))
		allowed = "import subprocess\nsubprocess.run(['bench'], timeout=3)\n"
		self.assertEqual(check_subprocess_only_in_source_tool({PROCESS_RUNNER_FILE: allowed}), [])
		for rel in ("agent/changes/apply_job.py", "agent/changes/file_writer.py", "agent/changes/runner.py"):
			with self.subTest(rel=rel):
				self.assertCaught(check_subprocess_only_in_source_tool({rel: allowed}), "outside")

	def test_subprocess_call_shape_applies_to_process_runner(self):
		head = (
			"import os\nimport subprocess\n"
			"subprocess.run([TIMEOUT_EXECUTABLE, '-s', 'KILL', '5', BENCH_EXECUTABLE], timeout=35"
		)
		good = f"{head}, cwd=get_bench_path(), env=_minimal_env(), start_new_session=True)\n"
		self.assertEqual(check_subprocess_call_shape({SOURCE_TOOL_FILE: "", PROCESS_RUNNER_FILE: good}), [])
		bench_first = (
			"import subprocess\nsubprocess.run([source.TIMEOUT_EXECUTABLE, '-s', 'KILL', '5', 'bench'], "
			"timeout=35, cwd=root, env=_minimal_env(), start_new_session=True)\n"
		)
		self.assertEqual(
			check_subprocess_call_shape({SOURCE_TOOL_FILE: "", PROCESS_RUNNER_FILE: bench_first}), []
		)
		cases = (
			(
				"without timeout=",
				"import subprocess\nsubprocess.run(['bench'], cwd=r, env={}, start_new_session=True)\n",
			),
			("with shell=", f"{head}, cwd=r, env={{}}, start_new_session=True, shell=True)\n"),
			(
				"string command",
				"import subprocess\nsubprocess.run('bench migrate', timeout=3, cwd=r, env={}, start_new_session=True)\n",
			),
			(
				"only run()",
				"import subprocess\nsubprocess.Popen(['bench'], timeout=3, cwd=r, env={}, start_new_session=True)\n",
			),
			("without start_new_session=True", f"{head}, cwd=r, env=_minimal_env())\n"),
			(
				"without start_new_session=True",
				f"{head}, cwd=r, env=_minimal_env(), start_new_session=False)\n",
			),
			("without cwd=", f"{head}, env=_minimal_env(), start_new_session=True)\n"),
			("without env=", f"{head}, cwd=r, start_new_session=True)\n"),
			("env= uses os.environ", f"{head}, cwd=r, env={{**os.environ}}, start_new_session=True)\n"),
			("env= uses os.environ", f"{head}, cwd=r, env=dict(os.environ), start_new_session=True)\n"),
			("env= uses os.environ", f"{head}, cwd=r, env=os.environ, start_new_session=True)\n"),
			(
				"without start_new_session=True",
				"import subprocess\nsubprocess.run(['bench'], timeout=3, cwd=r, env={})\n",
			),
			(
				"without cwd=",
				"import subprocess\nsubprocess.run(['bench'], timeout=3, env={}, start_new_session=True)\n",
			),
			(
				"env= uses os.environ",
				"import os\nimport subprocess\nsubprocess.run(['bench'], timeout=3, cwd=r, env=os.environ, start_new_session=True)\n",
			),
		)
		for fragment, source in cases:
			with self.subTest(fragment=fragment, source=source):
				violations = check_subprocess_call_shape({SOURCE_TOOL_FILE: "", PROCESS_RUNNER_FILE: source})
				self.assertCaught(violations, fragment)
				self.assertTrue(all(text.startswith(PROCESS_RUNNER_FILE) for text in violations), violations)
		plain = (
			"import os\nimport subprocess\nsubprocess.run(['git', 'log'], timeout=3, env={**os.environ})\n"
		)
		self.assertEqual(check_subprocess_call_shape({SOURCE_TOOL_FILE: plain}), [])
		self.assertCaught(
			check_subprocess_call_shape({SOURCE_TOOL_FILE: "", PROCESS_RUNNER_FILE: plain}),
			"env= uses os.environ",
			"without cwd=",
			"without start_new_session=True",
		)

	def test_subprocess_call_shape_accepts_git_writes_in_process_runner(self):
		"""ADR-022 QĐ 2, 4: the git add/commit/rm call of process_runner.py passes the shape rule."""
		head = (
			"import subprocess\nsubprocess.run([source.TIMEOUT_EXECUTABLE, '-s', 'KILL', '5', 'git', "
			"*source.git_global_options(read=False), 'add', '--', rel], timeout=10, cwd=repo_root"
		)
		good = f"{head}, env=source.git_env(identity=True), start_new_session=True)\n"
		self.assertEqual(check_subprocess_call_shape({SOURCE_TOOL_FILE: "", PROCESS_RUNNER_FILE: good}), [])
		self.assertEqual(check_subprocess_only_in_source_tool({PROCESS_RUNNER_FILE: good}), [])
		cases = (
			("without start_new_session=True", f"{head}, env=source.git_env(identity=True))\n"),
			("without env=", f"{head}, start_new_session=True)\n"),
			(
				"env= uses os.environ",
				f"import os\n{head}, env={{**os.environ, **source.git_env(identity=True)}}, start_new_session=True)\n",
			),
		)
		for fragment, source in cases:
			with self.subTest(fragment=fragment):
				self.assertCaught(
					check_subprocess_call_shape({SOURCE_TOOL_FILE: "", PROCESS_RUNNER_FILE: source}), fragment
				)

	def test_subprocess_call_shape_checks_run_wrapped_callers_in_process_runner(self):
		"""Design 8.2 "env= không chứa os.environ": process_runner.py builds cwd=/env= in its
		`_run_wrapped(...)` callers, so each caller gets the same cwd=/env= checks as subprocess.run."""
		head = "import os\nimport subprocess\n_run_wrapped(['git', 'add', '--', rel], limit_s=5"
		for env in ("source.git_env(identity=True)", "_minimal_env()"):
			good = f"{head}, cwd=repo_root, env={env}, backstop_s=5, max_lines=20)\n"
			with self.subTest(good=good):
				self.assertEqual(
					check_subprocess_call_shape({SOURCE_TOOL_FILE: "", PROCESS_RUNNER_FILE: good}), []
				)
		cases = (
			("_run_wrapped without cwd=", f"{head}, env=_minimal_env())\n"),
			("_run_wrapped without env=", f"{head}, cwd=repo_root)\n"),
			("_run_wrapped without env=", f"{head}, **options)\n"),
			("_run_wrapped env= uses os.environ", f"{head}, cwd=repo_root, env=os.environ)\n"),
			("_run_wrapped env= uses os.environ", f"{head}, cwd=repo_root, env=dict(os.environ))\n"),
			(
				"_run_wrapped env= uses os.environ",
				f"{head}, cwd=repo_root, env={{**os.environ, **source.git_env(identity=True)}})\n",
			),
			(
				"_run_wrapped env= uses os.environ",
				"from os import environ\n_run_wrapped(['bench'], cwd=r, env=dict(environ), limit_s=5)\n",
			),
		)
		for fragment, source in cases:
			with self.subTest(fragment=fragment, source=source):
				violations = check_subprocess_call_shape({SOURCE_TOOL_FILE: "", PROCESS_RUNNER_FILE: source})
				self.assertCaught(violations, fragment)
				self.assertTrue(all(text.startswith(PROCESS_RUNNER_FILE) for text in violations), violations)
		elsewhere = f"{head}, cwd=repo_root, env=os.environ)\n"
		self.assertEqual(check_subprocess_call_shape({SOURCE_TOOL_FILE: elsewhere}), [])

	# policy fields -----------------------------------------------------------------------------

	def test_policy_fields_caught_outside_policy_and_allowed_inside(self):
		cases = (
			"def f(settings):\n\treturn settings.permission_level\n",
			"import frappe\nfrappe.db.get_single_value('ERP AI Setting', 'permission_level')\n",
			"import frappe\nfrappe.db.get_single_value('ERP AI Setting', 'excluded_teams')\n",
			"def f(ticket):\n\treturn ticket.ai_opt_out\n",
			"def f(ticket):\n\treturn ticket.get('ai_opt_out')\n",
			"def f(settings):\n\treturn settings.code_change_enabled\n",
			"import frappe\nfrappe.db.get_single_value('ERP AI Setting', 'code_change_apps')\n",
		)
		for source in cases:
			with self.subTest(source=source):
				self.assertCaught(check_policy_fields_only_in_policy({"agent/tools/read.py": source}))
		inside = "def f(settings):\n\treturn settings.permission_level\n"
		self.assertEqual(check_policy_fields_only_in_policy({POLICY_FILE: inside}), [])
		prose = "def f():\n\t'''The only reader of permission_level.'''\n"
		self.assertEqual(check_policy_fields_only_in_policy({"handlers.py": prose}), [])

	# threshold and spend comparisons -----------------------------------------------------------

	def test_threshold_scanner_catches_comparison_outside_policy_and_allows_reads(self):
		catch = (
			(
				"agent/runner.py",
				"def f(settings, pct):\n\treturn pct < settings.confidence_threshold\n",
				"agent/runner.py:2: compares confidence_threshold outside agent/policy.py",
			),
			(
				"agent/tools/registry.py",
				"def f(classification, threshold):\n\treturn classification.confidence_pct < threshold\n",
				"compares confidence_pct",
			),
			(
				"agent/tools/route_ticket.py",
				"def f(c):\n\treturn c.confidence_pct < 70\n",
				"compares confidence_pct",
			),
			(
				"agent/runner.py",
				"from erp_ai.agent import policy\ndef f(s, p):\n\treturn policy.confidence_threshold(s) > p\n",
				"compares confidence_threshold",
			),
			(
				"agent/classification.py",
				"def f(data):\n\treturn 0 <= data['do_tin_cay_pct'] <= 100\n",
				"compares do_tin_cay_pct",
			),
		)
		for rel, source, fragment in catch:
			with self.subTest(source=source):
				self.assertCaught(check_threshold_compared_only_in_policy({rel: source}), fragment)
		allow = (
			(
				"agent/runner.py",
				"from erp_ai.agent import policy\n"
				"def f(settings, pct):\n"
				"\tthreshold = policy.confidence_threshold(settings)\n"
				"\treturn policy.is_below_confidence(pct, threshold, has_instructor=True, act_now=False)\n",
			),
			(
				"erp_ai_agent/doctype/erp_ai_setting/erp_ai_setting.py",
				"INT_LIMITS = {'confidence_threshold': ('Ngưỡng độ tin cậy', 0, 100)}\n"
				"def f(doc):\n"
				"\tfor fieldname, (label, low, high) in INT_LIMITS.items():\n"
				"\t\tvalue = doc.get(fieldname)\n"
				"\t\tif value < low or (high is not None and value > high):\n"
				"\t\t\treturn label\n",
			),
			(
				"agent/classification.py",
				"CONFIDENCE_PCT_MIN = 0\nCONFIDENCE_PCT_MAX = 100\n"
				"def f(confidence_pct):\n\treturn CONFIDENCE_PCT_MIN <= confidence_pct <= CONFIDENCE_PCT_MAX\n",
			),
			("agent/runner.py", "def f(c):\n\treturn c.confidence_pct is None\n"),
			(POLICY_FILE, "def f(pct, threshold):\n\treturn pct is None or pct < threshold\n"),
		)
		for rel, source in allow:
			with self.subTest(allowed=source):
				self.assertEqual(check_threshold_compared_only_in_policy({rel: source}), [])

	def test_spent_scanner_catches_comparison_outside_policy_and_allows_reads(self):
		catch = (
			(
				"agent/runner.py",
				"def f(settings):\n\treturn settings.spent_this_month_usd > settings.monthly_budget_usd\n",
				"agent/runner.py:2: compares spent_this_month_usd outside agent/policy.py",
			),
			(
				"erp_ai_agent/report/erp_ai_cost/erp_ai_cost.py",
				"import frappe\ndef f(budget):\n"
				"\treturn frappe.db.get_single_value('ERP AI Setting', 'spent_this_month_usd', cache=False) >= budget\n",
				"compares spent_this_month_usd",
			),
			(
				"agent/tools/registry.py",
				"from erp_ai.agent import policy\ndef f(settings, spend):\n\treturn spend > settings.monthly_budget_usd\n",
				"compares monthly_budget_usd",
			),
			(
				"agent/runner.py",
				"from erp_ai.agent import policy\ndef f(limit):\n\treturn policy.month_spend_usd() > limit\n",
				"compares month_spend_usd",
			),
		)
		for rel, source, fragment in catch:
			with self.subTest(source=source):
				self.assertCaught(check_no_spent_comparison_outside_policy({rel: source}), fragment)
		allow = (
			(
				"erp_ai_agent/report/erp_ai_cost/erp_ai_cost.py",
				"import frappe\ndef f():\n"
				"\tspent = frappe.db.get_single_value('ERP AI Setting', 'spent_this_month_usd', cache=False)\n"
				"\treturn [('Đã chi', spent)]\n",
			),
			(
				"tasks.py",
				"import frappe\ndef f(spent_by_label):\n"
				"\tfrappe.db.set_single_value('ERP AI Setting', 'spent_this_month_usd', sum(spent_by_label.values()))\n",
			),
			(
				"erp_ai_agent/doctype/erp_ai_setting/erp_ai_setting.py",
				"import frappe\nINT_LIMITS = {'monthly_budget_usd': ('Ngân sách tháng', 0, None)}\ndef f(doc):\n"
				"\tdoc.spent_this_month_usd = frappe.db.get_single_value('ERP AI Setting', 'spent_this_month_usd', cache=False)\n",
			),
			(
				"agent/runner.py",
				"from erp_ai.agent import policy\ndef f(settings):\n\treturn policy.is_over_budget(settings)\n",
			),
			("agent/runner.py", "def f(settings):\n\treturn settings.spent_this_month_usd is None\n"),
			(POLICY_FILE, "def f(settings, spend):\n\treturn spend > (settings.monthly_budget_usd or 0)\n"),
		)
		for rel, source in allow:
			with self.subTest(allowed=source):
				self.assertEqual(check_no_spent_comparison_outside_policy({rel: source}), [])

	def test_runner_grant_scanner_catches_old_grant_path_and_allows_grant_reads(self):
		runner = "from erp_ai.agent.tools.registry import grant\n"
		catch = (
			(runner + "def f(c):\n\treturn grants_change_tools(c)\n", "grants_change_tools"),
			(
				runner + "def f(c):\n\treturn registry.get_unrestricted_tool_schemas('L3')\n",
				"get_unrestricted_tool_schemas",
			),
			(runner + "def f(c):\n\ttools = grant(c).schemas()\n\ttools.extend(more)\n", "tools"),
			(runner + "def f(c):\n\ttools = [t for t in grant(c).schemas() if t]\n", "filters"),
			(runner + "def f(c):\n\ttools = get_tool_schemas(c)\n", "get_tool_schemas"),
		)
		for source, fragment in catch:
			with self.subTest(source=source):
				self.assertCaught(
					check_runner_takes_tools_and_flags_from_grant({RUNNER_FILE: source}), fragment
				)
		clean = (
			runner
			+ "def f(c, skipped, notes):\n"
			+ "\tgranted = grant(c.grant_inputs())\n"
			+ "\ttools = granted.schemas()\n"
			+ "\tif tools:\n\t\ttools[-1]['cache_control'] = {}\n"
			+ "\tskipped.extend(notes)\n"
			+ "\treturn tools, granted.change_block\n"
		)
		self.assertEqual(check_runner_takes_tools_and_flags_from_grant({RUNNER_FILE: clean}), [])
		self.assertEqual(
			check_runner_takes_tools_and_flags_from_grant(
				{"agent/other.py": "def f(c):\n\treturn grants_x(c)\n"}
			),
			[],
		)

	# handlers ----------------------------------------------------------------------------------

	def test_handlers_import_check_catches_gateway_runner_and_allows_policy_queue(self):
		for source in (
			"from erp_ai import gateway\n",
			"import erp_ai.gateway.client\n",
			"from erp_ai.agent import runner\n",
			"def f():\n\tfrom erp_ai.agent.runner import run_for_ticket\n",
		):
			with self.subTest(source=source):
				self.assertCaught(check_handlers_imports({HANDLERS_FILE: source}))
		clean = "from erp_ai.agent import policy\nfrom erp_ai.agent.queue import enqueue_agent_run\n"
		self.assertEqual(check_handlers_imports({HANDLERS_FILE: clean}), [])
		self.assertEqual(check_handlers_imports({"tasks.py": "from erp_ai import gateway\n"}), [])

	# secrets -----------------------------------------------------------------------------------

	def test_secret_handling_catches_password_reads_and_key_logging(self):
		cases = {
			"get_decrypted_password": "from frappe.utils.password import get_decrypted_password\n",
			"get_password": "def f(doc):\n\treturn doc.get_password('api_key')\n",
			"api_key": "import frappe\ndef f(api_key):\n\tfrappe.logger('x').warning('key %s', api_key)\n",
			"password": "def f(row):\n\tprint(f'{row.password}')\n",
			"token": "import frappe\ndef f(token):\n\tfrappe.log_error('t', token)\n",
			"with_context": "import frappe\nfrappe.get_traceback(with_context=True)\n",
		}
		for fragment, source in cases.items():
			with self.subTest(fragment=fragment):
				self.assertCaught(check_secret_handling({"gateway/__init__.py": source}), fragment)

	def test_secret_handling_catches_log_error_without_explicit_message(self):
		cases = (
			"import frappe\nfrappe.log_error(TITLE)\n",
			"import frappe\nfrappe.log_error(title=T)\n",
			"import frappe\nfrappe.log_error()\n",
			"from frappe import log_error\nlog_error(TITLE)\n",
			"import frappe\nfrappe.log_error(TITLE, '')\n",
			"import frappe\nfrappe.log_error(TITLE, message=None)\n",
		)
		for source in cases:
			with self.subTest(source=source):
				self.assertCaught(check_secret_handling({"tasks.py": source}), "log_error")

	def test_secret_handling_allows_log_error_with_explicit_message(self):
		safe = (
			"import frappe\n"
			"frappe.log_error(TITLE, 'msg')\n"
			"frappe.log_error(TITLE, f'error={type(exc).__name__}')\n"
			"frappe.log_error(title=T, message='m')\n"
			"frappe.log_error(TITLE, message=text)\n"
		)
		self.assertEqual(check_secret_handling({"tasks.py": safe}), [])

	def test_secret_handling_allows_credentials_module_and_label_logging(self):
		reader = "from frappe.utils.password import get_decrypted_password\nget_decrypted_password('a', 'b', 'api_key')\n"
		self.assertEqual(check_secret_handling({CREDENTIALS_FILE: reader}), [])
		safe = (
			"import frappe\n"
			"def f(row, exc):\n"
			"\tfrappe.logger('x').warning('key=%s %s', row.label, type(exc).__name__)\n"
			"\tfrappe.get_traceback(with_context=False)\n"
		)
		self.assertEqual(check_secret_handling({"gateway/__init__.py": safe}), [])

	# legacy comment ----------------------------------------------------------------------------

	def test_legacy_comment_names_caught_in_strings_attributes_and_json(self):
		cases = (
			"x = 'HD Ticket Comment'\n",
			"def f(c):\n\treturn c.commented_by\n",
			"def f(c):\n\treturn c['comment_email']\n",
			"fields = ['name', 'comment_by']\n",
			"def f():\n\tcommented_by = 1\n",
			"def f(**kw):\n\tg(comment_email=1)\n",
		)
		for source in cases:
			with self.subTest(source=source):
				self.assertCaught(check_no_legacy_ticket_comment({"agent/authority.py": source}))
		self.assertCaught(check_no_legacy_ticket_comment({"x/y.json": '{"doctype": "HD Ticket Comment"}'}))
		self.assertCaught(check_no_legacy_ticket_comment({"x/y.js": "frm.doc.comment_by"}))

	def test_legacy_comment_allows_hide_list_and_similar_words(self):
		hide = 'COMMENT_HIDDEN_FIELDS = ("comment_email", "comment_by")\n'
		self.assertEqual(check_no_legacy_ticket_comment({READ_TOOL_FILE: hide}), [])
		self.assertCaught(check_no_legacy_ticket_comment({"agent/authority.py": hide}))
		self.assertCaught(check_no_legacy_ticket_comment({READ_TOOL_FILE: "x = 'comment_by'\n" + hide}))
		similar = "owner = 'x'\ncomment_type = 'Comment'\nfields = ['commenter', 'comment_by_x', 'ticket_comment']\n"
		self.assertEqual(check_no_legacy_ticket_comment({"agent/authority.py": similar}), [])

	# CI ----------------------------------------------------------------------------------------

	GOOD_CI = (
		"          bench init --skip-assets --frappe-branch version-15 --python py ~/frappe-bench\n"
		"          bench get-app telephony\n"
		"          bench get-app helpdesk --branch v15.1.0\n"
		"          bench get-app erpnext --branch version-15\n"
		"          bench get-app erp_ai $GITHUB_WORKSPACE\n"
		"          bench --site test_site install-app telephony\n"
		"          bench --site test_site install-app helpdesk\n"
		"          bench --site test_site install-app erpnext\n"
		"          bench --site test_site install-app erp_ai\n"
	)

	def test_ci_check_accepts_complete_workflow(self):
		self.assertEqual(check_ci_workflow(self.GOOD_CI), [])

	def test_ci_check_catches_each_missing_or_wrong_piece(self):
		cases = {
			"bench init": self.GOOD_CI.replace("--frappe-branch version-15 ", ""),
			"bench init ": self.GOOD_CI.replace("--frappe-branch version-15", "--frappe-branch develop"),
			"get-app helpdesk": self.GOOD_CI.replace("--branch v15.1.0", "--branch v15.0.0"),
			"get-app erpnext": self.GOOD_CI.replace("bench get-app erpnext --branch version-15\n", ""),
			"get-app telephony": self.GOOD_CI.replace("bench get-app telephony\n", ""),
			"install-app helpdesk": self.GOOD_CI.replace(
				"          bench --site test_site install-app helpdesk\n", ""
			),
			"install-app erp_ai": self.GOOD_CI.replace("install-app erp_ai", "migrate"),
			"comes after install-app erp_ai": self.GOOD_CI.replace(
				"          bench --site test_site install-app telephony\n", ""
			)
			+ "          bench --site test_site install-app telephony\n",
		}
		for fragment, text in cases.items():
			with self.subTest(fragment=fragment):
				self.assertCaught(check_ci_workflow(text), fragment)

	def test_ci_check_ignores_commented_commands(self):
		commented = self.GOOD_CI.replace("bench get-app erpnext", "# bench get-app erpnext")
		self.assertCaught(check_ci_workflow(commented), "get-app erpnext")

	# Frappe-skipped test file names ------------------------------------------------------------

	def test_frappe_skipped_test_name_check_catches_any_depth(self):
		violating = [
			"agent/test_runner.py",
			"tests/test_runner.py",
			"erp_ai_agent/doctype/x/test_runner.py",
			"test_runner.py",
		]
		clean = [
			"agent/test_agent_runner.py",
			"tests/test_runner_utils.py",
			"agent/runner.py",
			"agent/my_test_runner.py",
		]
		violations = check_no_frappe_skipped_test_files(violating)
		self.assertEqual(len(violations), len(violating))
		for rel in violating:
			self.assertCaught(violations, rel)
		self.assertEqual(check_no_frappe_skipped_test_files(clean), [])

	# status signals and form script (ADR-007, ADR-008) -----------------------------------------

	GOOD_PUBLISH = (
		"import frappe\nfrom frappe.realtime import get_doc_room\n"
		"frappe.publish_realtime('e', message={}, room=get_doc_room('HD Ticket', 'T'), after_commit=False)\n"
	)

	def test_publish_realtime_scanner_catches_violations(self):
		# publish_realtime / frappe.realtime only in run_status.py, with room= and after_commit=False
		self.assertEqual(check_publish_realtime_only_in_run_status({RUN_STATUS_FILE: self.GOOD_PUBLISH}), [])
		for source in (
			"import frappe\nfrappe.publish_realtime('e', room='r', after_commit=False)\n",
			"from frappe import publish_realtime\n",
			"import frappe\nfrappe.publish_progress(1)\n",
			"from frappe.realtime import emit_via_redis\n",
			"import frappe\nfrappe.realtime.get_doc_room('HD Ticket', 'T')\n",
			"from frappe.realtime import get_doc_room\n",
			"import frappe\ngetattr(frappe, 'publish_realtime')('e')\n",
			"import frappe\nfrappe.get_attr('frappe.publish_realtime')('e')\n",
			"import importlib\nimportlib.import_module('frappe.realtime')\n",
			"import frappe as f\nf.realtime.get_doc_room('HD Ticket', 'T')\n",
			"from frappe import realtime as rt\nrt.get_doc_room('HD Ticket', 'T')\n",
		):
			with self.subTest(source=source):
				self.assertCaught(check_publish_realtime_only_in_run_status({"agent/runner.py": source}))
		for fragment, source in {
			"room=": "import frappe\nfrappe.publish_realtime('e', after_commit=False)\n",
			"after_commit=False": "import frappe\nfrappe.publish_realtime('e', room='r')\n",
		}.items():
			with self.subTest(fragment=fragment):
				self.assertCaught(
					check_publish_realtime_only_in_run_status({RUN_STATUS_FILE: source}), fragment
				)
		self.assertCaught(
			check_publish_realtime_only_in_run_status(
				{
					RUN_STATUS_FILE: "import frappe\nfrappe.publish_realtime('e', room='r', after_commit=True)\n"
				}
			),
			"after_commit=False",
		)
		# aliased or rebound publish_realtime inside run_status is still pinned to room= and after_commit=False
		for fragment, source in {
			"room=": "from frappe import publish_realtime as publish\npublish('e', after_commit=False)\n",
			"binds publish_realtime": "from frappe import publish_realtime as publish\n",
		}.items():
			with self.subTest(fragment=fragment, source=source):
				self.assertCaught(
					check_publish_realtime_only_in_run_status({RUN_STATUS_FILE: source}), fragment
				)
		self.assertCaught(
			check_publish_realtime_only_in_run_status(
				{
					RUN_STATUS_FILE: "import frappe\npublish = frappe.publish_realtime\n"
					"publish('e', room='r', after_commit=False)\n"
				}
			),
			"binds publish_realtime",
		)
		self.assertCaught(
			check_publish_realtime_only_in_run_status(
				{RUN_STATUS_FILE: "import frappe as f\nf.publish_realtime('e', room='r')\n"}
			),
			"after_commit=False",
		)

	def test_run_status_import_scanner_catches_violations(self):
		# the status module is imported only by the runner
		for rel, source in {
			"agent/tools/read.py": "from erp_ai.agent import run_status\n",
			"handlers.py": "from erp_ai.agent.run_status import RunStatus\n",
			"tasks.py": "import erp_ai.agent.run_status\n",
			"agent/queue.py": "from . import run_status\n",
			"eval/run_eval.py": "import importlib\nimportlib.import_module('erp_ai.agent.run_status')\n",
		}.items():
			with self.subTest(rel=rel):
				self.assertCaught(check_run_status_imported_only_by_runner({rel: source}), rel)
		self.assertEqual(
			check_run_status_imported_only_by_runner(
				{RUNNER_FILE: "from erp_ai.agent.run_status import RunStatus\n"}
			),
			[],
		)

	def test_run_status_writes_nothing_scanner_catches_violations(self):
		# the status module writes nothing
		for source in (
			"import frappe\nfrappe.db.set_value('X', 'y', 'z', 1)\n",
			"import frappe\nfrappe.delete_doc('X', 'y')\n",
			"import frappe\nfrappe.cache.set_value('k', 1)\n",
			"import frappe\nfrappe.get_doc({}).insert()\n",
			"def f(doc):\n\tdoc.save()\n",
			"def f():\n\twith open('x', 'w') as handle:\n\t\thandle.write('1')\n",
			"from erp_ai.gateway import call_model\n",
			"import frappe\nfrappe.db.commit()\n",
		):
			with self.subTest(source=source):
				self.assertCaught(check_run_status_writes_nothing({RUN_STATUS_FILE: source}))
		# no banned write name is called here: only the frappe.cache / frappe.db attribute rule catches these
		for fragment, source in (
			("uses frappe.cache", "import frappe\nfrappe.cache.hset('k', 'f', 1)\n"),
			("uses frappe.cache", "import frappe\nfrappe.cache.get_value('k')\n"),
			("uses frappe.db", "import frappe\nfrappe.db.set_single_value('X', 'f', 1)\n"),
			("uses frappe.cache", "import frappe as f\nf.cache.hset('k', 'f', 1)\n"),
			("uses frappe.db", "from frappe import db\ndb.set_single_value('X', 'f', 1)\n"),
			("uses frappe.cache", "from frappe import cache\ncache().hset('k', 'f', 1)\n"),
		):
			with self.subTest(fragment=fragment, source=source):
				self.assertCaught(check_run_status_writes_nothing({RUN_STATUS_FILE: source}), fragment)
		clean = self.GOOD_PUBLISH + "def f(errors):\n\terrors.append('x')\n"
		self.assertEqual(check_run_status_writes_nothing({RUN_STATUS_FILE: clean}), [])
		self.assertEqual(check_run_status_writes_nothing({"agent/runner.py": "def f(d):\n\td.save()\n"}), [])

	def test_document_room_scanner_catches_violations(self):
		# no open_doc: room, no room "all", no publish without a document room
		for rel, source in {
			"agent/runner.py": "room = 'open_doc:HD Ticket/T'\n",
			"x/y.js": "socket.emit('open_doc:HD Ticket')",
			RUN_STATUS_FILE: "import frappe\nfrappe.publish_realtime('e', room='all', after_commit=False)\n",
			"tasks.py": "import frappe\nfrappe.publish_realtime('e', after_commit=False)\n",
			"handlers.py": "import frappe\nfrappe.publish_realtime('e', room=None)\n",
			"agent/queue.py": "from frappe import publish_realtime as publish\npublish('e', after_commit=False)\n",
			"agent/policy.py": "import frappe as f\nf.publish_realtime('e', after_commit=False)\n",
			"agent/tools/read.py": "import frappe\nROOM = 'all'\n"
			"frappe.publish_realtime('e', room=ROOM, after_commit=False)\n",
		}.items():
			with self.subTest(rel=rel):
				self.assertCaught(check_no_open_doc_or_all_room({rel: source}), rel)
		self.assertEqual(check_no_open_doc_or_all_room({RUN_STATUS_FILE: self.GOOD_PUBLISH}), [])

	def test_form_script_scanner_catches_violations(self):
		# HD Form Script only in install.py
		for rel, source in {
			"agent/runner.py": "import frappe\nfrappe.get_doc('HD Form Script', 'x')\n",
			"tasks.py": "DT = 'HD Form Script'\n",
			"x/y.json": '{"doctype": "HD Form Script"}',
			"x/y.html": "<p>HD Form Script</p>",
			"handlers.py": "from helpdesk.helpdesk.doctype.hd_form_script import hd_form_script\n",
		}.items():
			with self.subTest(rel=rel):
				self.assertCaught(check_form_script_only_in_install({rel: source}), rel)
		self.assertEqual(check_form_script_only_in_install({INSTALL_FILE: "DT = 'HD Form Script'\n"}), [])

	def test_hooks_scanner_catches_violations(self):
		# hooks.py injects nothing into the page
		for fragment, source in {
			"app_include_js": "app_include_js = '/assets/erp_ai/js/agent_status_indicator.js'\n",
			"web_include_js": "web_include_js = ['x.js']\n",
			"app_include_css": "app_include_css = 'x.css'\n",
			"after_request": "after_request = ['erp_ai.x.inject']\n",
			"website_route_rules": "website_route_rules = [{'from_route': '/helpdesk/<path:app_path>', 'to_route': 'x'}]\n",
			"fixtures": "fixtures = [{'dt': 'HD Form Script'}]\n",
			"status script": "doc_events = {'x': 'agent_status_indicator'}\n",
		}.items():
			with self.subTest(fragment=fragment):
				self.assertCaught(check_hooks_have_no_page_injection({HOOKS_FILE: source}), fragment)
		self.assertCaught(
			check_hooks_have_no_page_injection({HOOKS_FILE: f"x = '{AGENT_STATUS_SCRIPT_NAME}'\n"}),
			"references the status script",
		)
		hooks_ok = (
			"fixtures = [{'dt': 'Custom Field'}]\n"
			"website_route_rules = [{'from_route': '/a', 'to_route': 'b'}]\n"
			"# app_include_js = '/assets/erp_ai/js/x.js'\n"
			"before_uninstall = 'erp_ai.install.before_uninstall'\n"
		)
		self.assertEqual(check_hooks_have_no_page_injection({HOOKS_FILE: hooks_ok}), [])

	def test_install_scanner_catches_violations(self):
		# install.py has exactly one delete: delete_doc of the status script in before_uninstall
		good_install = (
			"import frappe\n"
			"FORM_SCRIPT_DOCTYPE = 'HD Form Script'\n"
			"AGENT_STATUS_SCRIPT = 'ERP AI Agent Status'\n"
			"def before_uninstall():\n"
			"\tfrappe.delete_doc(FORM_SCRIPT_DOCTYPE, AGENT_STATUS_SCRIPT, ignore_permissions=True)\n"
		)
		self.assertEqual(check_install_deletes_only_status_script({INSTALL_FILE: good_install}), [])
		moved_outside = (
			"import frappe\n"
			"FORM_SCRIPT_DOCTYPE = 'HD Form Script'\n"
			"AGENT_STATUS_SCRIPT = 'ERP AI Agent Status'\n"
			"def before_uninstall():\n"
			"\tpass\n"
			"def ensure_setup():\n"
			"\tfrappe.delete_doc(FORM_SCRIPT_DOCTYPE, AGENT_STATUS_SCRIPT, ignore_permissions=True)\n"
		)
		for fragment, source in (
			("found 0", good_install.replace("frappe.delete_doc(", "print(")),
			("found 2", good_install + "\tfrappe.delete_doc('ToDo', 'x')\n"),
			("outside before_uninstall", moved_outside),
			("outside before_uninstall", good_install + "def ensure_setup():\n\tfrappe.db.delete('X', {})\n"),
			("SQL delete", good_install + "def f():\n\tfrappe.db.sql('DELETE FROM `tabX`')\n"),
			("delete must be", good_install.replace("AGENT_STATUS_SCRIPT,", "'Other',")),
			("delete must be", good_install.replace("frappe.delete_doc(", "frappe.db.delete(")),
			("delete must be", good_install.replace("FORM_SCRIPT_DOCTYPE,", "'HD Ticket',")),
		):
			with self.subTest(fragment=fragment, source=source):
				self.assertCaught(check_install_deletes_only_status_script({INSTALL_FILE: source}), fragment)

	# ticket panel (ADR-009, ADR-010 Amendment 1) -------------------------------------------------

	# ADR-044 QĐ 1 (CHG-008): the clean panel has the third method, decide_proposal, like the product.
	PANEL_SOURCES: ClassVar[dict] = {
		"ticket_panel.py": (
			"import frappe\n"
			"from erp_ai.agent import messages\n"
			"@frappe.whitelist(methods=['POST'])\n"
			"def get_panel_data(ticket):\n\treturn 1\n"
			"@frappe.whitelist(methods=['POST'])\n"
			"def send_message(ticket, text):\n\treturn messages.add_message(ticket, text)\n"
			"@frappe.whitelist(methods=['POST'])\n"
			"def decide_proposal(name, action):\n\treturn PANEL_DECISIONS[action](name)\n"
			"@frappe.whitelist(methods=['POST'])\n"
			"def decide_result(ticket, action):\n\treturn 1\n"
		)
	}

	def test_call_allow_list_scanner_catches_unlisted_method(self):
		allowed = tuple(PANEL_METHODS)
		# ADR-044 QĐ 1 (CHG-008): a clean script calls each of the three panel methods
		good = (
			'state.call("erp_ai.ticket_panel.get_panel_data", {});\n'
			'state.call("erp_ai.ticket_panel.decide_proposal", {});\n'
			'state.call("erp_ai.ticket_panel.decide_result", {});\n'
			'state.call("erp_ai.ticket_panel.send_message", {});'
		)
		self.assertEqual(check_call_allow_list(good, allowed, self.PANEL_SOURCES), [])
		self.assertCaught(
			check_call_allow_list(
				good + 'state.call("erp_ai.handlers.other", {});', allowed, self.PANEL_SOURCES
			),
			"erp_ai.handlers.other is not in PANEL_METHODS",
			"does not point to a @frappe.whitelist function",
		)
		self.assertCaught(
			check_call_allow_list(good.split("\n")[0], allowed, self.PANEL_SOURCES),
			"erp_ai.ticket_panel.send_message is in PANEL_METHODS but the script never calls it",
		)
		self.assertCaught(
			check_call_allow_list(good + "state.call(METHOD, {});", allowed, self.PANEL_SOURCES),
			"not a string literal",
		)
		undecorated = {
			"ticket_panel.py": self.PANEL_SOURCES["ticket_panel.py"].replace(
				"@frappe.whitelist(methods=['POST'])\ndef send", "def send"
			)
		}
		self.assertCaught(
			check_call_allow_list(good, allowed, undecorated),
			"erp_ai.ticket_panel.send_message does not point to a @frappe.whitelist function",
		)

	def test_socket_on_scanner_catches_outside_once_block(self):
		block = 'if (state.socket !== socket) {\n\tsocket.on(EVENT, a);\n\tsocket.on("connect", () => { b(); });\n}\n'
		head = 'const EVENT = "erp_ai:agent_status";\n'
		self.assertEqual(check_socket_on_only_in_once_block(head + block, "erp_ai:agent_status"), [])
		self.assertCaught(
			check_socket_on_only_in_once_block(
				head + block + 'socket.on("doc_update", c);\n', "erp_ai:agent_status"
			),
			"outside the once-per-socket block",
		)
		self.assertCaught(
			check_socket_on_only_in_once_block(
				head + block.replace("EVENT, a", '"typing", a'), "erp_ai:agent_status"
			),
			"event 'typing' is not one of",
		)
		self.assertCaught(
			check_socket_on_only_in_once_block(head + "socket.on(EVENT, a);\n", "erp_ai:agent_status"),
			"block if (state.socket !== socket) { is missing",
		)
		self.assertCaught(
			check_socket_on_only_in_once_block(
				head + block.replace("EVENT, a", "OTHER, a"), "erp_ai:agent_status"
			),
			"event None is not one of",
		)
		# an `.on(` in a comment or string is not a registration
		self.assertEqual(
			check_socket_on_only_in_once_block(
				head + block + '// socket.on("x", y)\nconst s = "socket.on(";\n', "erp_ai:agent_status"
			),
			[],
		)

	def test_status_script_query_scanner_catches_other_selectors(self):
		self.assertEqual(check_status_script_queries('document.querySelector("#app")'), [])
		self.assertEqual(check_status_script_queries('document.getElementById("app")'), [])
		for source in (
			'document.querySelector(".ticket")',
			'document.querySelector("#app .x")',
			'document.querySelectorAll("#app")',
			'document.getElementById("other")',
			'document.getElementsByClassName("x")',
			"document.querySelector(selector)",
		):
			with self.subTest(source=source):
				self.assertCaught(check_status_script_queries(source), "only allowed with the Vue root")

	def test_status_script_window_scanner_catches_second_state(self):
		good = "window.__erpAiAgentStatus = window.__erpAiAgentStatus || {};\nwindow.addEventListener(1, 2);"
		self.assertEqual(check_status_script_window_state(good), [])
		self.assertCaught(
			check_status_script_window_state(good + "window.__erpAiPanel = {};"), "window state names are"
		)
		self.assertCaught(
			check_status_script_window_state(good + "window.other = 1;"), "window.other is written"
		)
		self.assertCaught(check_status_script_window_state(good + 'window["x"] = 1;'), "window[...]")
		self.assertCaught(check_status_script_window_state("var a = 1;"), "window state names are")

	def test_status_indicator_scanner_catches_hidden_without_display(self):
		good = (
			'const INDICATOR_FLOATING_STYLE = { position: "fixed" };\n'
			'const INDICATOR_DOCKED_STYLE = { position: "static" };\n'
			"const setIndicatorVisible = (el, visible) => {\n"
			"\tel.hidden = !visible;\n"
			'\tel.style.display = visible ? "flex" : "none";\n'
			"};\n"
			"const ensureElement = () => {\n"
			"\tObject.assign(el.style, INDICATOR_FLOATING_STYLE);\n"
			"\tsetIndicatorVisible(el, false);\n"
			"};\n"
			"const render = () => {\n"
			"\tif (state.runs.size === 0) {\n"
			"\t\tsetIndicatorVisible(el, false);\n"
			"\t\treturn;\n"
			"\t}\n"
			"\tsetIndicatorVisible(el, true);\n"
			"};\n"
			"const dockIndicator = (docked) => {\n"
			"\tObject.assign(el.style, INDICATOR_DOCKED_STYLE);\n"
			"};\n"
			"const reset = () => {\n"
			"\tif (state.el) { setIndicatorVisible(state.el, false); }\n"
			"};\n"
		)
		self.assertEqual(check_status_indicator_hides(good), [])
		for old, new, fragment in (
			("setIndicatorVisible(state.el, false);", "state.el.hidden = true;", "reset sets hidden without"),
			("setIndicatorVisible(el, true);", "el.hidden = false;", "render sets hidden without"),
			(
				"\tsetIndicatorVisible(el, false);\n};\nconst render",
				"\tel.hidden = true;\n};\nconst render",
				"ensureElement does not hide",
			),
			(
				"\tObject.assign(el.style, INDICATOR_FLOATING_STYLE);\n\tsetIndicatorVisible(el, false);",
				"\tsetIndicatorVisible(el, false);\n\tObject.assign(el.style, INDICATOR_FLOATING_STYLE);",
				"ensureElement does not hide",
			),
			(
				'{ position: "static" }',
				'{ position: "static", display: "flex" }',
				"INDICATOR_DOCKED_STYLE sets",
			),
			('\tel.style.display = visible ? "flex" : "none";\n', "", "setIndicatorVisible does not write"),
			("const dockIndicator = (docked)", "const dock = (docked)", "function dockIndicator is missing"),
			(
				"\t\tsetIndicatorVisible(el, false);\n\t\treturn;\n\t}\n\tsetIndicatorVisible(el, true);\n",
				"\t\tsetIndicatorVisible(el, true);\n\t\treturn;\n\t}\n\tsetIndicatorVisible(el, false);\n",
				"render does not hide the indicator when no run is active",
			),
			(
				"\t\tsetIndicatorVisible(el, false);\n\t\treturn;\n\t}\n\tsetIndicatorVisible(el, true);\n",
				"\t\tsetIndicatorVisible(el, true);\n\t\treturn;\n\t}\n\tsetIndicatorVisible(el, false);\n",
				"render does not end with setIndicatorVisible(el, true)",
			),
			(
				"\tsetIndicatorVisible(el, true);\n};",
				"\tsetIndicatorVisible(el, true);\n\tel.title = name;\n};",
				"render does not end with setIndicatorVisible(el, true)",
			),
			(
				"if (state.el) { setIndicatorVisible(state.el, false); }",
				"if (state.el) { state.el.remove(); }",
				"reset does not call setIndicatorVisible(state.el, false)",
			),
			(
				"\tsetIndicatorVisible(el, true);\n};",
				'\tsetIndicatorVisible(el, true);\n\tel.style.display = "flex";\n};',
				"render writes display outside setIndicatorVisible",
			),
			(
				"Object.assign(el.style, INDICATOR_DOCKED_STYLE);",
				'Object.assign(el.style, INDICATOR_DOCKED_STYLE, { display: "flex" });',
				"dockIndicator writes display outside setIndicatorVisible",
			),
		):
			with self.subTest(fragment=fragment):
				self.assertIn(old, good)
				self.assertCaught(check_status_indicator_hides(good.replace(old, new)), fragment)

	def test_whitelist_scanner_catches_guest_bare_and_missing_methods(self):
		for decorator, fragment in (
			("@frappe.whitelist()", "methods= must list"),
			("@frappe.whitelist", "bare @frappe.whitelist"),
			("@frappe.whitelist(allow_guest=True, methods=['POST'])", "allow_guest"),
			("@frappe.whitelist(allow_guest=False, methods=['POST'])", "allow_guest"),
			("@frappe.whitelist(methods=[])", "methods= must list"),
			("@whitelist(methods=METHODS)", "methods= must list"),
		):
			with self.subTest(decorator=decorator):
				source = f"import frappe\nfrom frappe import whitelist\n{decorator}\ndef f():\n\tpass\n"
				self.assertCaught(check_whitelisted_methods_declare_http_methods({"x.py": source}), fragment)
		ok = "import frappe\n@frappe.whitelist(methods=['POST'])\ndef f():\n\tpass\n"
		self.assertEqual(check_whitelisted_methods_declare_http_methods({"x.py": ok}), [])

	def test_ticket_panel_whitelist_scanner_catches_fourth_method_and_get(self):
		# ADR-044 QĐ 1 (CHG-008): three methods are the clean panel, so the extra one is now the fourth
		self.assertEqual(check_ticket_panel_whitelist(self.PANEL_SOURCES), [])
		source = self.PANEL_SOURCES["ticket_panel.py"]
		extra = source + "@frappe.whitelist(methods=['POST'])\ndef fourth():\n\tpass\n"
		self.assertCaught(check_ticket_panel_whitelist({PANEL_FILE: extra}), "whitelisted functions are")
		self.assertCaught(
			check_ticket_panel_whitelist({PANEL_FILE: source.replace("'POST'", "'GET'", 1)}),
			'exactly ["POST"]',
		)
		self.assertCaught(
			check_ticket_panel_whitelist({PANEL_FILE: source.replace("['POST']", "['POST', 'GET']", 1)}),
			'exactly ["POST"]',
		)
		self.assertCaught(
			check_ticket_panel_whitelist({PANEL_FILE: source.replace("def get_panel_data", "def get_data")}),
			"whitelisted functions are",
		)
		decide_by_get = source.replace(
			"@frappe.whitelist(methods=['POST'])\ndef decide_proposal",
			"@frappe.whitelist(methods=['GET'])\ndef decide_proposal",
		)
		self.assertNotEqual(decide_by_get, source)
		self.assertCaught(
			check_ticket_panel_whitelist({PANEL_FILE: decide_by_get}),
			'decide_proposal: methods must be exactly ["POST"]',
		)

	def test_ticket_panel_forbidden_scanner_catches_each_name(self):
		for snippet in (
			"frappe.get_doc('X', 1, ignore_permissions=True)",
			"frappe.set_user('a')",
			"frappe.get_all('X')",
			"frappe.db.get_values('X')",
			"frappe.db.sql('select 1')",
			"frappe.db.set_value('X', 1, 'a', 2)",
			"doc.db_set('a', 1)",
			"doc.insert()",
			"doc.save()",
			"frappe.delete_doc('X', 1)",
			"frappe.db.delete('X')",
			"frappe.db.commit()",
			"frappe.db.rollback()",
			"frappe.cache.get('k')",
			"frappe.publish_realtime('e')",
			"frappe.get_doc('HD Ticket', 1).new_comment('a')",
		):
			with self.subTest(snippet=snippet):
				source = self.PANEL_SOURCES["ticket_panel.py"] + f"def extra():\n\t{snippet}\n"
				self.assertCaught(
					check_ticket_panel_forbidden_calls({PANEL_FILE: source}), "not allowed in the panel"
				)
		source = self.PANEL_SOURCES["ticket_panel.py"]
		self.assertCaught(
			check_ticket_panel_forbidden_calls(
				{PANEL_FILE: source + "def x(d):\n\tmessages.add_message(d, 'a')\n"}
			),
			"found 2",
		)
		self.assertCaught(
			check_ticket_panel_forbidden_calls({PANEL_FILE: source.replace("add_message", "other")}),
			"found 0",
		)
		moved = source.replace("return messages.add_message(ticket, text)", "return 1")
		moved += "def helper(d):\n\tmessages.add_message(d, 'a')\n"
		self.assertCaught(
			check_ticket_panel_forbidden_calls({PANEL_FILE: moved}), "must be inside send_message"
		)
		self.assertEqual(check_ticket_panel_forbidden_calls({PANEL_FILE: source}), [])

	def test_ticket_panel_gate_scanner_catches_each_gate(self):
		for gate in PANEL_GATE_NAMES:
			for snippet in (f"policy.{gate}()", f"{gate} = 1", f"d.get('{gate}')"):
				with self.subTest(snippet=snippet):
					source = self.PANEL_SOURCES["ticket_panel.py"] + f"def extra(d, policy):\n\t{snippet}\n"
					self.assertCaught(
						check_ticket_panel_does_not_evaluate_agent_gates({PANEL_FILE: source}), gate
					)
		self.assertCaught(
			check_ticket_panel_does_not_evaluate_agent_gates(
				{PANEL_FILE: "from erp_ai.agent.queue import enqueue_agent_run\n"}
			),
			"enqueue",
		)
		self.assertEqual(check_ticket_panel_does_not_evaluate_agent_gates(self.PANEL_SOURCES), [])

	# FEAT-006: routing rules --------------------------------------------------------------------

	ROUTE_SOURCES: ClassVar[dict] = {
		REGISTRY_FILE: 'TOOL_MODULES = (\n\t"erp_ai.agent.tools.read",\n\t"erp_ai.agent.tools.write_ticket",\n)\n',
		ROUTE_FILE: (
			"import frappe\n"
			"from frappe.desk.form import assign_to\n\n"
			"def apply_route(decision, classification, ctx):\n"
			"\tdoc = frappe.get_doc('HD Ticket', ctx.ticket_name)\n"
			"\tdoc.save()\n\n"
			"def assign_owner(user, ctx):\n"
			"\tassign_to.add({'assign_to': [user], 'doctype': 'HD Ticket', 'name': ctx.ticket_name})\n"
		),
	}

	def test_route_module_scanner_catches_registry_listing_and_tool_names(self):
		self.assertEqual(check_route_module_is_not_a_tool(self.ROUTE_SOURCES), [])
		listed = {
			**self.ROUTE_SOURCES,
			REGISTRY_FILE: 'TOOL_MODULES = ("erp_ai.agent.tools.route_ticket",)\n',
		}
		self.assertCaught(check_route_module_is_not_a_tool(listed), "lists route_ticket")
		for extra in (
			"TOOLS = []\n",
			"from erp_ai.agent.tools.registry import ToolSpec\n",
			"spec = ToolSpec\n",
		):
			with self.subTest(extra=extra):
				routed = {**self.ROUTE_SOURCES, ROUTE_FILE: self.ROUTE_SOURCES[ROUTE_FILE] + extra}
				self.assertCaught(check_route_module_is_not_a_tool(routed), "routing module")
		self.assertCaught(check_route_module_is_not_a_tool({ROUTE_FILE: ""}), REGISTRY_FILE)
		wrapper = "TOOLS = [ToolSpec(name='n', group='g', schema={}, handler=%s)]\n"
		for handler in (
			"apply_route",
			"route_ticket.assign_owner",
			"post_routing_comment",
			"create_routed_task",
		):
			with self.subTest(handler=handler):
				others = {**self.ROUTE_SOURCES, "agent/tools/write_ticket.py": wrapper % handler}
				self.assertCaught(
					check_route_module_is_not_a_tool(others), "write_ticket.py", handler.split(".")[-1]
				)
		positional = {
			**self.ROUTE_SOURCES,
			"agent/tools/write_ticket.py": "TOOLS = [ToolSpec('n', 'g', {}, apply_route)]\n",
		}
		self.assertCaught(check_route_module_is_not_a_tool(positional), "write_ticket.py", "apply_route")
		harmless = {**self.ROUTE_SOURCES, "agent/tools/write_ticket.py": wrapper % "set_classification"}
		self.assertEqual(check_route_module_is_not_a_tool(harmless), [])

	def test_route_single_save_scanner_catches_second_and_misplaced_saves(self):
		self.assertEqual(check_route_module_single_ticket_save(self.ROUTE_SOURCES), [])
		route = self.ROUTE_SOURCES[ROUTE_FILE]
		second = route + "\ndef other(doc):\n\tdoc.save()\n"
		self.assertCaught(
			check_route_module_single_ticket_save({ROUTE_FILE: second}), "outside apply_route", "found 2"
		)
		twice = route.replace("\tdoc.save()\n", "\tdoc.save()\n\tdoc.save()\n")
		self.assertCaught(check_route_module_single_ticket_save({ROUTE_FILE: twice}), "found 2")
		moved = route.replace("def apply_route", "def other_name")
		self.assertCaught(check_route_module_single_ticket_save({ROUTE_FILE: moved}), "outside apply_route")
		none = route.replace("\tdoc.save()\n", "\tpass\n")
		self.assertCaught(check_route_module_single_ticket_save({ROUTE_FILE: none}), "found 0")
		for extra in (
			"\ndef assign_owner_again(doc):\n\tdoc.db_update()\n",
			"\ndef retry(doc):\n\tdoc.db_update(x=1)\n",
		):
			with self.subTest(extra=extra):
				self.assertCaught(
					check_route_module_single_ticket_save({ROUTE_FILE: route + extra}), "db_update"
				)
		inside = route.replace("\tdoc.save()\n", "\tdoc.save()\n\tdoc.db_update()\n")
		self.assertCaught(check_route_module_single_ticket_save({ROUTE_FILE: inside}), "db_update")

	def test_assign_to_scanner_catches_every_way_to_call_it_outside_route_module(self):
		for source in (
			"from frappe.desk.form import assign_to\nassign_to.add({})\n",
			"from frappe.desk.form.assign_to import add\nadd({})\n",
			"from frappe.desk.form.assign_to import add as put\nput({})\n",
			"import frappe\nfrappe.desk.form.assign_to.add({})\n",
			"from frappe.desk.form import assign_to as a\na.add_multiple({})\n",
			"from frappe.desk.form import assign_to\n",
			# no import of the module at all: only the call suffix can catch these
			"def f(a):\n\ta.assign_to.add_multiple({})\n",
			"def f(a):\n\ta.assign_to.add({})\n",
			"def f(doc):\n\tdoc.assign_agent('u')\n",
			"import frappe\nfrappe.get_doc('HD Ticket', t).assign_agent(u)\n",
			"f = getattr(doc, 'assign_agent')\n",
			# ADR-021: no ToDo created by hand either
			"import frappe\nfrappe.get_doc('ToDo').insert()\n",
			"import frappe\nfrappe.get_doc({'doctype': 'ToDo', 'allocated_to': u}).insert()\n",
			"import frappe\nfrappe.new_doc('ToDo')\n",
		):
			with self.subTest(source=source):
				self.assertCaught(
					check_assign_to_only_in_route_module({"agent/runner.py": source}), "agent/runner.py"
				)
		self.assertEqual(check_assign_to_only_in_route_module(self.ROUTE_SOURCES), [])
		clean = (
			"import frappe\nitems = [].add\nfrappe.get_all('ToDo', filters={})\n"
			"frappe.get_doc('HD Ticket', t).save()\nfrappe.get_doc({'doctype': 'Task'}).insert()\n"
		)
		self.assertEqual(check_assign_to_only_in_route_module({"agent/runner.py": clean}), [])

	def test_share_bypass_scanner_catches_each_forbidden_name(self):
		for source in (
			"assign_to.add({}, ignore_share_permission=True)\n",
			"d = {'ignore_share_permission': 1}\n",
			"from frappe.desk.form import assign_to\nassign_to._add({})\n",
			"from frappe.desk.form.assign_to import _add\n_add({})\n",
			"from frappe.share import add_docshare\nadd_docshare('T', 'x', 'u')\n",
			"import frappe\nfrappe.share.add('T', 'x', 'u')\n",
			"from frappe import share\nshare.add('T', 'x', 'u')\n",
			"from frappe.share import add\nadd('T', 'x', 'u')\n",
		):
			with self.subTest(source=source):
				self.assertCaught(check_no_share_bypass({"agent/tools/route_ticket.py": source}), "sharing")
		self.assertEqual(check_no_share_bypass(self.ROUTE_SOURCES), [])
		self.assertEqual(check_no_share_bypass({"x.py": "s = set()\ns.add(1)\nshare = 1\n"}), [])

	def test_policy_scanner_catches_auto_assign_switch_read_outside_policy(self):
		for source in (
			"def f(settings):\n\treturn settings.auto_assign_enabled\n",
			"def f(settings):\n\treturn getattr(settings, 'auto_assign_enabled', 0)\n",
			"def f(settings):\n\treturn settings.get('auto_assign_enabled')\n",
			"import frappe\nfrappe.db.get_single_value('ERP AI Setting', 'auto_assign_enabled')\n",
			"auto_assign_enabled = 1\n",
		):
			with self.subTest(source=source):
				self.assertCaught(
					check_policy_fields_only_in_policy({"agent/runner.py": source}), "auto_assign_enabled"
				)
		through_policy = "from erp_ai.agent import policy\n\ndef f(settings):\n\treturn policy.auto_assign_enabled(settings)\n"
		self.assertEqual(check_policy_fields_only_in_policy({"agent/runner.py": through_policy}), [])
		self.assertEqual(
			check_policy_fields_only_in_policy({POLICY_FILE: "def x(s):\n\treturn s.auto_assign_enabled\n"}),
			[],
		)

	def test_entry_types_scanner_catches_new_type_in_code_or_doctype(self):
		# CHG-009 (ADR-048 QĐ 1): the compliant sample carries run_event; the five types before it are now caught.
		run_log = 'ENTRY_TYPES = ("classify", "reason", "skip", "change", "bot_action", "run_event")\n'
		doctype = json.dumps(
			{
				"fields": [
					{
						"fieldname": "entry_type",
						"options": "classify\nreason\nskip\nchange\nbot_action\nrun_event",
					}
				]
			}
		)
		good = {RUN_LOG_FILE: run_log, LOG_DOCTYPE_FILE: doctype}
		self.assertEqual(check_entry_types_unchanged(good), [])
		extra = {
			**good,
			RUN_LOG_FILE: 'ENTRY_TYPES = ("classify", "reason", "skip", "change", "bot_action", "run_event", "route")\n',
		}
		self.assertCaught(check_entry_types_unchanged(extra), "ENTRY_TYPES")
		without_change = {**good, RUN_LOG_FILE: 'ENTRY_TYPES = ("classify", "reason", "skip", "change")\n'}
		self.assertCaught(check_entry_types_unchanged(without_change), "ENTRY_TYPES")
		without_run_event = {
			**good,
			RUN_LOG_FILE: 'ENTRY_TYPES = ("classify", "reason", "skip", "change", "bot_action")\n',
		}
		self.assertCaught(check_entry_types_unchanged(without_run_event), "ENTRY_TYPES")
		options = json.dumps(
			{
				"fields": [
					{
						"fieldname": "entry_type",
						"options": "classify\nreason\nskip\nchange\nbot_action\nrun_event\nroute",
					}
				]
			}
		)
		self.assertCaught(check_entry_types_unchanged({**good, LOG_DOCTYPE_FILE: options}), "options")
		old_options = json.dumps(
			{"fields": [{"fieldname": "entry_type", "options": "classify\nreason\nskip\nchange\nbot_action"}]}
		)
		self.assertCaught(check_entry_types_unchanged({**good, LOG_DOCTYPE_FILE: old_options}), "options")
		computed = {**good, RUN_LOG_FILE: "ENTRY_TYPES = tuple(x)\n"}
		self.assertCaught(check_entry_types_unchanged(computed), "ENTRY_TYPES")
		self.assertCaught(check_entry_types_unchanged({RUN_LOG_FILE: run_log}), LOG_DOCTYPE_FILE)

	def test_assign_column_scanner_catches_reads_and_allows_authority(self):
		for source in (
			"import frappe\nfrappe.db.get_value('HD Ticket', t, '_assign')\n",
			"def f(doc):\n\treturn doc._assign\n",
			"def f(doc):\n\treturn doc.get('_assign')\n",
			"import frappe\nfrappe.db.sql('select _assign from `tabHD Ticket`')\n",
			"_assign = 1\n",
		):
			with self.subTest(source=source):
				self.assertCaught(
					check_no_assign_column_for_decisions({"agent/routing.py": source}), "_assign"
				)
		source = "import frappe\nfrappe.db.get_value('HD Ticket', t, '_assign')\n"
		allowed = f"def {ASSIGN_FIELD_ALLOWED_FUNCTION}(a, t):\n\treturn frappe.db.get_value('HD Ticket', t, '_assign')\n"
		self.assertEqual(check_no_assign_column_for_decisions({AUTHORITY_FILE: allowed}), [])
		self.assertEqual(check_no_assign_column_for_decisions({"handlers.py": source}), [])
		# authority.py is exempt only inside its one function
		self.assertCaught(check_no_assign_column_for_decisions({AUTHORITY_FILE: source}), "_assign")
		other = allowed.replace(ASSIGN_FIELD_ALLOWED_FUNCTION, "is_instruction")
		self.assertCaught(check_no_assign_column_for_decisions({AUTHORITY_FILE: other}), "_assign")
		both = allowed + "\ndef other(t):\n\treturn frappe.db.get_value('HD Ticket', t, '_assign')\n"
		self.assertCaught(check_no_assign_column_for_decisions({AUTHORITY_FILE: both}), "_assign")
		self.assertEqual(
			check_no_assign_column_for_decisions(
				{"agent/site_facts.py": "x = 'assigned_by'\ny = 'reassign'\n"}
			),
			[],
		)
		# the pattern's own edges: a letter or digit before, a letter, digit or `_` after, is another word
		for text in ("ai_assign", "9_assign", "_assigned", "_assign_to", "_assign9", "x_assign_y"):
			with self.subTest(text=text):
				self.assertEqual(check_no_assign_column_for_decisions({"agent/a.py": f"x = {text!r}\n"}), [])
		for text in ("(_assign)", " _assign ", "`_assign`", "select _assign,x", "_assign"):
			with self.subTest(text=text):
				self.assertCaught(
					check_no_assign_column_for_decisions({"agent/a.py": f"x = {text!r}\n"}), "_assign"
				)

	def test_route_module_bypass_rules_catch_violations_in_route_module(self):
		route = self.ROUTE_SOURCES[ROUTE_FILE]
		self.assertEqual(check_tools_never_bypass_permissions({ROUTE_FILE: route}), [])
		for extra in (
			"def x(doc):\n\tdoc.save(ignore_permissions=True)\n",
			"def x():\n\tfrappe.db.set_value('HD Ticket', 'T', 'a', 1)\n",
			"def x():\n\tfrappe.set_user('Administrator')\n",
			"def x():\n\tfrappe.db.sql('update `tabHD Ticket` set a = 1')\n",
			"def x():\n\tfrappe.get_all('ToDo')\n",
		):
			with self.subTest(extra=extra):
				self.assertCaught(check_tools_never_bypass_permissions({ROUTE_FILE: route + extra}))

	def test_sla_dates_scanner_catches_each_way_to_write_them(self):
		for source in (
			"def f(doc):\n\tdoc.response_by = 1\n",
			"def f(doc):\n\tdoc.resolution_by += 1\n",
			"def f(doc):\n\tdoc['response_by'] = 1\n",
			"def f(doc):\n\tdoc.update({'resolution_by': 1})\n",
			"def f(doc):\n\tdoc.update(response_by=1)\n",
			"def f(doc):\n\tsetattr(doc, 'response_by', 1)\n",
			"import frappe\nfrappe.db.set_value('HD Ticket', t, 'resolution_by', 1)\n",
			"def f(doc):\n\tdoc.db_set('response_by', 1)\n",
			"response_by: int = 1\n",
			"def f(doc):\n\tdoc.set('response_by', 1)\n",
			"def f(doc):\n\tdoc.set('resolution_by', 1)\n",
			# the field name held in a constant, then used by a generic writer
			"F = 'resolution_by'\n",
			"F: str = 'response_by'\n",
			"FIELDS = ('response_by', 'x')\n",
			"FIELDS = ['x', 'resolution_by']\n",
			"FIELDS = {'response_by'}\n",
			"def f(doc, v):\n\tF = 'response_by'\n\tdoc.set(F, v)\n",
		):
			with self.subTest(source=source):
				self.assertCaught(
					check_feature_never_assigns_sla_dates({"agent/routing.py": source}), "SLA date"
				)
		reads = (
			"def f(doc):\n\tx = doc.get('resolution_by')\n\ty = doc.response_by\n"
			"\treturn doc.response_by, doc.get('resolution_by'), x, y, s.set('other', 1)\n"
		)
		self.assertEqual(check_feature_never_assigns_sla_dates({"agent/site_facts.py": reads}), [])
		self.assertEqual(check_feature_never_assigns_sla_dates({"tasks.py": "x.response_by = 1\n"}), [])

	def test_default_people_scanner_matches_whole_words_only(self):
		for text in (
			"Việt",
			"Tiến",
			"Hiếu",
			"Lan",
			"Hà",
			"Thư",
			"Chi",
			"gán cho Hiếu",
			"A: Lan, Hà",
			"ai.agent",
		):
			with self.subTest(text=text):
				source = f"DEFAULT = {text!r}\n"
				self.assertCaught(
					check_no_default_people_in_agent_python({"agent/routing.py": source}), "AC-14"
				)
		self.assertCaught(
			check_no_default_people_in_agent_python(
				{"agent/run_status.py": "U = 'ai.agent@miyano.com.vn'\n"}
			),
			"ai.agent",
		)
		self.assertCaught(
			check_no_default_people_in_agent_python({"agent/prompts.py": 'P = f"Giao cho {x} là Hiếu"\n'}),
			"Hiếu",
		)
		self.assertCaught(
			check_no_default_people_in_agent_python({"agent/prompts.py": '"""Việt Nam, nhờ Việt xử lý"""\n'}),
			"Việt",
		)
		clean = (
			"A = 'Công ty Miyano Việt Nam'\nB = 'Tiếng Việt, ngắn'\nC = 'Thư mục nằm ngoài mã nguồn'\n"
			"D = 'erp_ai.agent.runner.run_for_ticket'\nE = 'Chiều', 'Hàng', 'Lanh', 'Thưa', 'Chính', 'Hiếm'\n"
			"F = 'chi tiết', 'lan can', 'ai.agents'\n"
			"G = 'ThanhLan', 'ThiHà', 'AnhChi', '2Thư', 'ai_Việt', 'xHiếu', 'NhàTiến'\n"
		)
		self.assertEqual(check_no_default_people_in_agent_python({"agent/prompts.py": clean}), [])
		outside = "DEFAULT = 'Hiếu'\n"
		self.assertEqual(check_no_default_people_in_agent_python({"constants.py": outside}), [])

	# FEAT-004 group 1 (ADR-011, ADR-012) -------------------------------------------------------

	def test_transitions_import_caught_outside_controller_and_changes(self):
		cases = {
			"agent/runner.py": "from erp_ai.agent.changes import transitions\n",
			"handlers.py": "import erp_ai.agent.changes.transitions\n",
			"agent/tools/propose_change.py": "from erp_ai.agent.changes.transitions import approve\n",
			"tasks.py": "from erp_ai.agent.changes import transitions as t\n",
			"gateway/client.py": "from erp_ai.agent import changes\nX = changes.transitions.approve\n",
			"change_decision.py": "M = 'erp_ai.agent.changes.transitions.approve'\n",
			"agent/changes_old.py": "from erp_ai.agent.changes import transitions\n",
			"erp_ai_agent/doctype/erp_ai_log/erp_ai_log.py": "from erp_ai.agent.changes import transitions\n",
		}
		for rel, source in cases.items():
			with self.subTest(rel=rel):
				self.assertCaught(
					check_transitions_imported_only_by_controller_and_changes({rel: source}), rel, "ADR-012"
				)

	def test_transitions_import_clean_in_controller_and_changes(self):
		allowed = "from erp_ai.agent.changes import transitions\n"
		clean = {
			PROPOSAL_CONTROLLER_FILE: allowed,
			"agent/changes/apply_job.py": allowed,
			"agent/changes/transitions.py": "from erp_ai.agent.run_log import write_entry\n",
			"agent/runner.py": "from erp_ai.agent.changes import apply_job\nM = 'erp_ai.agent.changes.apply_job.run_change'\n",
			"agent/queue.py": "from erp_ai.agent.changes import transitions_note\n",
		}
		self.assertEqual(check_transitions_imported_only_by_controller_and_changes(clean), [])

	def test_state_field_writes_caught_outside_changes(self):
		for field in STATE_FIELDS:
			with self.subTest(field=field):
				self.assertCaught(
					check_change_state_fields_written_only_in_changes(
						{"agent/tools/propose_change.py": f"doc.{field} = 1\n"}
					),
					field,
				)
		shapes = {
			"attribute": "proposal.change_status = 'Đã duyệt'\n",
			"augmented": "proposal.exit_code += 1\n",
			"annotated": "proposal.decided_by: str = user\n",
			"subscript": "proposal['decided_at'] = now\n",
			"dict key": "frappe.get_doc({'doctype': D, 'approved_digest': x}).insert()\n",
			"doc.set": "doc.set('undo_by', user)\n",
			"db_set": "doc.db_set('undo_at', now)\n",
			"set_value": "frappe.db.set_value(D, name, 'finished_at', now)\n",
			"setattr": "setattr(doc, 'failure_reason', text)\n",
			"keyword": "frappe.new_doc(D, applied_branch='main')\n",
			"qb set attribute": "frappe.qb.update(T).set(T.change_status, v).run()\n",
			"dict() keyword": "doc.update(dict(change_status=v))\n",
			"return dict": "def f(n, v):\n\treturn {'name': n, 'restart_status': v}\n",
			"helper dict to a write": "def f(v):\n\treturn {'change_status': v}\n\nfrappe.db.set_value(D, n, f(v))\n",
		}
		for shape, source in shapes.items():
			with self.subTest(shape=shape):
				self.assertCaught(
					check_change_state_fields_written_only_in_changes({"change_decision.py": source}),
					"change_decision.py",
					"ADR-012",
				)

	def test_state_field_reads_and_changes_writes_are_clean(self):
		clean = {
			# Writes inside agent/changes/ are the state machine's own job.
			"agent/changes/transitions.py": "doc.set('change_status', S)\nfrappe.db.set_value(D, n, {'decided_by': u})\n",
			"agent/changes/apply_job.py": "proposal.apply_commit_sha = sha\n",
			# Reads elsewhere, and a content field (not in STATE_FIELDS) written elsewhere.
			"agent/change_text.py": "s = fields.get('change_status')\nc = proposal.undo_commit_sha\n",
			"agent/tools/propose_change.py": (
				"x = {'ok': True, 'status': proposal.change_status}\n"
				"frappe.get_doc({'doctype': D, 'change_kind': k}).insert()\n"
			),
			"agent/tools/source.py": "run = GitRun(exit_code=None, stdout=b'')\n",
			"change_decision.py": "s = frappe.db.get_value(D, name, 'change_status')\n",
		}
		self.assertEqual(check_change_state_fields_written_only_in_changes(clean), [])

	def test_change_guard_without_resolve_safe_path_caught(self):
		good = (
			"from erp_ai.agent.tools import source\n\ndef check_write_path(rel):\n"
			"\tfull = source.resolve_safe_path(rel)\n\tif full is None:\n\t\treturn _refused(PATH_INVALID)\n"
			"\treturn full\n"
		)
		cases = {
			"refusal of the resolver not kept": (
				{
					CHANGE_GUARD_FILE: "import os\nfrom erp_ai.agent.tools import source\n\n"
					"def check_write_path(rel):\n\tfull = source.resolve_safe_path(rel)\n"
					"\ttarget = full or os.path.realpath(rel)\n\treturn _refused(None) if not target else target\n"
				},
				"None",
			),
			"None check without a refusal": (
				{
					CHANGE_GUARD_FILE: "from erp_ai.agent.tools import source\n\ndef check_write_path(rel):\n"
					"\tfull = source.resolve_safe_path(rel)\n\tif full is None:\n\t\tpass\n\treturn full\n"
				},
				"None",
			),
			"realpath root check in a helper": (
				{
					CHANGE_GUARD_FILE: good,
					"agent/changes/file_writer.py": "import os\n\ndef _real(p):\n\tr = os.path.realpath(p)\n"
					"\treturn os.path.commonpath([ROOT, r]) == ROOT\n",
				},
				"agent/changes/file_writer.py",
				"_real",
			),
			"root check in another guard function": (
				{
					CHANGE_GUARD_FILE: good
					+ "\ndef _inside(p):\n\treturn os.path.commonpath([R, os.path.realpath(p)]) == R\n",
				},
				"_inside",
			),
			# source.py's own shape: the root check in a helper, the realpath calls in its caller.
			"root check split from realpath": (
				{
					CHANGE_GUARD_FILE: good,
					"agent/changes/file_writer.py": "import os\n\ndef _inside(root, full):\n"
					"\treturn os.path.commonpath([root, full]) == root\n\ndef resolve(rel):\n"
					"\troot, full = os.path.realpath(ROOT), os.path.realpath(rel)\n"
					"\treturn full if _inside(root, full) else None\n",
				},
				"agent/changes/file_writer.py",
				"_inside",
			),
			"root check at module level": (
				{
					CHANGE_GUARD_FILE: good,
					"agent/changes/file_writer.py": "import pathlib\n\nOK = pathlib.Path(P).is_relative_to(R)\n",
				},
				"agent/changes/file_writer.py",
				"is_relative_to",
			),
			"missing file": (
				{SOURCE_TOOL_FILE: "def resolve_safe_path(rel):\n\treturn rel\n"},
				CHANGE_GUARD_FILE,
			),
			"no guard function": (
				{CHANGE_GUARD_FILE: "def other(rel):\n\treturn rel\n"},
				CHANGE_GUARD_FUNCTION,
			),
			"guard resolves itself": (
				{
					CHANGE_GUARD_FILE: "import os\n\ndef check_write_path(rel):\n\treturn os.path.realpath(rel)\n"
				},
				"ADR-011",
			),
			"call in another function": (
				{
					CHANGE_GUARD_FILE: "from erp_ai.agent.tools import source\n\ndef check_write_path(rel):\n\treturn rel\n"
					"\ndef helper(rel):\n\treturn source.resolve_safe_path(rel)\n"
				},
				"ADR-011",
			),
			"second resolver": (
				{
					CHANGE_GUARD_FILE: good,
					"agent/changes/file_writer.py": "def _resolve_safe_path(p):\n\treturn p\n",
				},
				"agent/changes/file_writer.py",
			),
		}
		for name, (sources, *fragments) in cases.items():
			with self.subTest(case=name):
				self.assertCaught(check_change_guard_uses_resolve_safe_path(sources), *fragments)

	def test_change_guard_with_resolve_safe_path_clean(self):
		clean = {
			SOURCE_TOOL_FILE: "def resolve_safe_path(rel):\n\treturn rel\n",
			# The guard's own realpath/commonpath only classifies a refused path (allowlisted, ADR-011).
			CHANGE_GUARD_FILE: "import os\nfrom erp_ai.agent.tools import source\n\ndef check_write_path(rel):\n"
			"\tif not rel:\n\t\treturn _refused(PATH_INVALID)\n\tfull = source.resolve_safe_path(rel)\n"
			"\ttarget = full or os.path.realpath(rel)\n\tif os.path.commonpath([R, target]) != R:\n"
			"\t\treturn _refused(PATH_INVALID)\n\tif full is None:\n\t\treturn _refused(PATH_INVALID)\n"
			"\treturn full\n",
			# realpath alone (no root check) is not a resolver.
			"agent/changes/apply_job.py": "import os\n\ndef _top(p):\n\treturn os.path.realpath(p)\n",
		}
		self.assertEqual(check_change_guard_uses_resolve_safe_path(clean), [])
		direct = {
			CHANGE_GUARD_FILE: "from erp_ai.agent.tools.source import resolve_safe_path\n\n"
			"def check_write_path(rel):\n\tif (full := resolve_safe_path(rel)) is None:\n"
			"\t\traise ValueError(rel)\n\treturn full\n"
		}
		self.assertEqual(check_change_guard_uses_resolve_safe_path(direct), [])

	def test_root_check_allowlist_is_closed(self):
		# Hand-written and closed: exactly these (file, function) pairs; anything else is a second resolver.
		self.assertEqual(
			ROOT_CHECK_ALLOWLIST,
			frozenset(
				{(CHANGE_GUARD_FILE, CHANGE_GUARD_FUNCTION), ("eval/export_tickets.py", "_inside_repo")}
			),
		)
		good = (
			"from erp_ai.agent.tools import source\n\ndef check_write_path(rel):\n"
			"\tfull = source.resolve_safe_path(rel)\n\tif full is None:\n\t\treturn _refused(PATH_INVALID)\n"
			"\treturn full\n"
		)
		root_check = (
			"import os\n\ndef {name}(p):\n\treturn os.path.commonpath([R, os.path.realpath(p)]) == R\n"
		)
		allowed = {CHANGE_GUARD_FILE: good, "eval/export_tickets.py": root_check.format(name="_inside_repo")}
		self.assertEqual(check_change_guard_uses_resolve_safe_path(allowed), [])
		outside = {
			"same function, another file": ("eval/compute_metrics.py", "_inside_repo"),
			"same file, another function": ("eval/export_tickets.py", "_inside_app"),
		}
		for name, (rel, function) in outside.items():
			with self.subTest(case=name):
				sources = {CHANGE_GUARD_FILE: good, rel: root_check.format(name=function)}
				self.assertCaught(check_change_guard_uses_resolve_safe_path(sources), rel, function)

	def _proposal_json(self, permissions):
		return {
			PROPOSAL_DOCTYPE_FILE: json.dumps({"name": PROPOSAL_DOCTYPE_NAME, "permissions": permissions})
		}

	def _proposal_rows(self):
		return [
			{"role": "ERP AI Agent", "create": 1, "read": 1},
			{"role": "ERP AI Instructor", "read": 1},
			{"role": "System Manager", "read": 1},
		]

	def test_proposal_permissions_caught(self):
		self.assertCaught(check_proposal_doctype_permissions({}), PROPOSAL_DOCTYPE_FILE)
		for role in PROPOSAL_PERMISSIONS:
			for flag in PROPOSAL_FORBIDDEN_PERMISSIONS:
				with self.subTest(role=role, flag=flag):
					rows = self._proposal_rows()
					next(row for row in rows if row["role"] == role)[flag] = 1
					self.assertCaught(
						check_proposal_doctype_permissions(self._proposal_json(rows)), role, flag
					)
		cases = {
			"agent without create": [{"role": "ERP AI Agent", "read": 1}, *self._proposal_rows()[1:]],
			"agent without read": [{"role": "ERP AI Agent", "create": 1}, *self._proposal_rows()[1:]],
			"instructor may create": [
				*self._proposal_rows()[:1],
				{"role": "ERP AI Instructor", "read": 1, "create": 1},
				*self._proposal_rows()[2:],
			],
			"outside flag share": [
				{"role": "ERP AI Agent", "create": 1, "read": 1, "share": 1},
				*self._proposal_rows()[1:],
			],
			"outside role": [*self._proposal_rows(), {"role": "Guest", "read": 1}],
			"missing role": self._proposal_rows()[:2],
			"split rows add write": [*self._proposal_rows(), {"role": "ERP AI Agent", "write": 1}],
		}
		for name, rows in cases.items():
			with self.subTest(case=name):
				self.assertCaught(check_proposal_doctype_permissions(self._proposal_json(rows)), "ADR-012")

	def test_proposal_permissions_clean(self):
		self.assertEqual(check_proposal_doctype_permissions(self._proposal_json(self._proposal_rows())), [])
		zeros = [
			{**row, **{flag: 0 for flag in PROPOSAL_FORBIDDEN_PERMISSIONS}, "permlevel": 0, "if_owner": 0}
			for row in self._proposal_rows()
		]
		self.assertEqual(check_proposal_doctype_permissions(self._proposal_json(zeros)), [])

	def test_tool_saving_a_proposal_caught(self):
		builds = "from erp_ai.constants import PROPOSAL_DOCTYPE\nd = frappe.get_doc({'doctype': PROPOSAL_DOCTYPE})\n"
		for call in ("d.save()", "d.db_set('reason', 'x')", "frappe.db.set_value('ToDo', n, 'x', 1)"):
			with self.subTest(call=call):
				self.assertCaught(
					check_tool_never_saves_proposal({PROPOSE_TOOL_FILE: builds + call + "\n"}),
					PROPOSE_TOOL_FILE,
					"ADR-011",
				)
		elsewhere = {
			"get_doc constant": "frappe.get_doc(PROPOSAL_DOCTYPE, name).save()\n",
			"get_doc literal": "frappe.get_doc('ERP AI Change Proposal', name).save()\n",
			"new_doc": "d = frappe.new_doc(PROPOSAL_DOCTYPE)\nd.save()\n",
			"set_value": "frappe.db.set_value(PROPOSAL_DOCTYPE, name, 'reason', 'x')\n",
			"set_value literal": "frappe.db.set_value('ERP AI Change Proposal', name, 'reason', 'x')\n",
			"db_set": "frappe.get_doc(PROPOSAL_DOCTYPE, name).db_set('reason', 'x')\n",
		}
		for name, source in elsewhere.items():
			with self.subTest(case=name):
				self.assertCaught(
					check_tool_never_saves_proposal({"agent/tools/site_api.py": source}),
					"agent/tools/site_api.py",
				)
		saves = "def save(doctype, name):\n\tdoc = frappe.get_doc(doctype, name)\n\tdoc.save()\n"
		generic = {
			"no deny set": ("agent/tools/site_api.py", saves),
			"denied set lacks it": ("agent/tools/cleanup.py", "DENIED_DOCTYPES = {'User'}\n" + saves),
			"subtracted from the set": (
				"agent/tools/cleanup.py",
				"DENIED_DOCTYPES = (read.DENIED_DOCTYPES | {'X'}) - {PROPOSAL_DOCTYPE}\n" + saves,
			),
			"delete_doc in another tool": (
				"agent/tools/cleanup.py",
				"DENIED_DOCTYPES = {LOG_DOCTYPE}\ndef drop(doctype, name):\n\tfrappe.delete_doc(doctype, name)\n",
			),
			"get_doc with keywords only": (
				"agent/tools/cleanup.py",
				"def save(d, n):\n\tdoc = frappe.get_doc(doctype=d, name=n)\n\tdoc.save()\n",
			),
			"delete_doc with keywords only": (
				"agent/tools/cleanup.py",
				"def drop(d, n):\n\tfrappe.delete_doc(doctype=d, name=n)\n",
			),
		}
		for name, (rel, source) in generic.items():
			with self.subTest(case=name):
				self.assertCaught(check_tool_never_saves_proposal({rel: source}), rel, "deny")

	def test_tool_inserting_a_proposal_clean(self):
		clean = {
			PROPOSE_TOOL_FILE: "d = frappe.get_doc({'doctype': PROPOSAL_DOCTYPE, 'reason': r})\nd.insert()\n",
			# Other DocTypes in tools keep their own rules.
			"agent/tools/write_ticket.py": "doc = frappe.get_doc('HD Ticket', n)\ndoc.save()\n",
			"agent/tools/route_ticket.py": "doc = frappe.get_doc(TICKET_DOCTYPE, ctx.ticket_name)\ndoc.save()\n",
			# A tool saving or deleting any DocType keeps the proposal in every deny set (ADR-011).
			"agent/tools/write_any.py": (
				"DENIED_DOCTYPES = (read.DENIED_DOCTYPES - {'User'}) | {PROPOSAL_DOCTYPE, 'Custom Role'}\n"
				"doc = frappe.get_doc(doctype, name)\ndoc.save()\nfrappe.delete_doc(doctype, name)\n"
			),
			# site_api refuses through the derived deny gate (ADR-023).
			SITE_API_FILE: SITE_API_GATED,
			# A generic loader that never saves or deletes needs no deny set.
			"agent/tools/read.py": "doc = frappe.get_doc(doctype, name)\nreturn doc.as_dict()\n",
			"agent/tools/cleanup.py": "DENIED_DOCTYPES = {'ERP AI Change Proposal'}\nfrappe.delete_doc(doctype, name)\n",
			# Outside agent/tools/ the state machine writes the proposal (ADR-012).
			"agent/changes/transitions.py": "frappe.db.set_value(PROPOSAL_DOCTYPE, name, values)\n",
		}
		self.assertEqual(check_tool_never_saves_proposal(clean), [])

	def test_site_api_hand_written_app_doctype_set_caught(self):
		cases = {
			"frozenset of a constant": "ALWAYS_DENIED_DOCTYPES = frozenset({PROPOSAL_DOCTYPE})\n",
			"set literal of a string": "DENIED = {'ERP AI Change Proposal', 'User'}\n",
			"tuple of constants": "APP_DOCTYPES = (SETTING_DOCTYPE, constants.CREDENTIAL_DOCTYPE)\n",
			"annotated list": "APP: list = ['ERP AI Log']\n",
			"union with a derived set": "DENIED = read.DENIED_DOCTYPES | {LOG_DOCTYPE}\n",
		}
		for name, line in cases.items():
			with self.subTest(case=name):
				self.assertCaught(
					check_tool_never_saves_proposal({SITE_API_FILE: line + SITE_API_GATED}),
					f"{SITE_API_FILE}:1:",
					"ADR-023",
				)

	def test_site_api_hand_written_app_doctype_set_clean(self):
		# Sets of other DocTypes and a single constant stay allowed; only a set naming the app's DocTypes is caught.
		source = (
			"PERMISSION_DOCTYPES = frozenset({'Custom Role', DOCTYPE_DOCTYPE, ROLE_DOCTYPE})\n"
			"FORCED_VALUES = {'Server Script': {'disabled': 1}}\n"
			"OWN = PROPOSAL_DOCTYPE\n" + SITE_API_GATED
		)
		self.assertEqual(check_tool_never_saves_proposal({SITE_API_FILE: source}), [])

	def test_site_api_always_denied_not_derived_caught(self):
		derived = 'return frozenset(frappe.get_all("DocType", {"module": read.AI_MODULE}, pluck="name"))'
		cases = {
			"missing": (
				SITE_API_GATED.replace("def always_denied_doctypes", "def other_doctypes"),
				"no always_",
			),
			"hand-written inside": (
				SITE_API_GATED.replace(derived, "return frozenset({SETTING_DOCTYPE, PROPOSAL_DOCTYPE})"),
				"not derived",
			),
			"not from the app module": (
				SITE_API_GATED.replace("read.AI_MODULE", "'Core'"),
				"not derived",
			),
		}
		for name, (source, fragment) in cases.items():
			with self.subTest(case=name):
				self.assertNotEqual(source, SITE_API_GATED)
				self.assertCaught(
					check_tool_never_saves_proposal({SITE_API_FILE: source}), fragment, "ADR-023"
				)

	def test_site_api_handler_without_deny_gate_caught(self):
		gate = "\tif refusal := _refusal(doctype, ctx):\n\t\treturn refusal\n"
		read_tool = (
			"def get_record(args, ctx):\n\treturn frappe.get_doc(args['doctype'], args['name']).as_dict()\n"
			"TOOLS.append(ToolSpec(name='api_get_record', handler=get_record))\n"
		)
		cases = {
			"save before the gate": SITE_API_GATED.replace(
				gate, "\tfrappe.get_doc(doctype, 'x').save()\n" + gate
			),
			"no gate": SITE_API_GATED.replace(gate, ""),
			# review-31: calling the deny set without refusing on it proves nothing.
			"deny set called, not gated": SITE_API_GATED.replace(gate, "\t_refusal(doctype, ctx)\n"),
			"refusal never returns": SITE_API_GATED.replace(
				"\t\treturn {'ok': False, 'reason': 'không được phép'}\n\treturn None\n",
				"\t\tlogger.info(doctype)\n\treturn None\n",
			),
			"proposal taken out of the set": SITE_API_GATED.replace(
				"read.denied_doctypes() - {'User'}", "read.denied_doctypes() - {PROPOSAL_DOCTYPE}"
			),
			"read handler returns before the gate": SITE_API_GATED + read_tool,
		}
		for name, source in cases.items():
			with self.subTest(case=name):
				self.assertNotEqual(source, SITE_API_GATED)
				self.assertCaught(
					check_tool_never_saves_proposal({SITE_API_FILE: source}), "before the derived deny gate"
				)
		no_tools = SITE_API_GATED.split("TOOLS = ")[0]
		self.assertCaught(check_tool_never_saves_proposal({SITE_API_FILE: no_tools}), "deny gate")
		elsewhere = SITE_API_GATED.replace("handler=call_method", "handler=other.call_method")
		self.assertCaught(check_tool_never_saves_proposal({SITE_API_FILE: elsewhere}), "deny gate unproven")

	def test_site_api_handlers_behind_deny_gate_clean(self):
		# The real module is held to the same rule by TestArchitecture.test_tool_never_saves_proposal.
		self.assertEqual(check_tool_never_saves_proposal({SITE_API_FILE: SITE_API_GATED}), [])

	# FEAT-004 T32: file-system writes, session and publish in the change path (ADR-013) --------------

	def test_fs_writes_caught_outside_file_writer(self):
		cases = {
			"open positional w": "open(p, 'w')\n",
			"open positional a": "with open(p, 'ab') as f:\n\tf.write(b)\n",
			"open positional x": "open(p, 'x')\n",
			"open r+": "open(p, 'r+')\n",
			"open mode= w": "open(p, mode='w', encoding='utf-8')\n",
			"open mode= a": "open(file=p, mode='a')\n",
			"open non-literal mode": "MODE = 'w'\nopen(p, MODE)\n",
			"open mode through a helper": "def _mode():\n\treturn 'w'\n\ndef save(p):\n\treturn open(p, _mode())\n",
			"open mode through **kwargs": "open(p, **options)\n",
			"io.open": "import io\nio.open(p, 'w')\n",
			"io aliased": "import io as i\ni.open(p, mode='wb')\n",
			"codecs.open": "import codecs\ncodecs.open(p, 'w', 'utf-8')\n",
			"os.fdopen": "import os\nos.fdopen(fd, 'wb')\n",
			"Path.open": "from pathlib import Path\nPath(p).open('w')\n",
			"Path.open mode=": "from pathlib import Path\nPath(p).open(mode='a')\n",
			"os.open write flags": "import os\nos.open(p, os.O_WRONLY | os.O_CREAT)\n",
			"os.open int flags": "import os\nos.open(p, 577)\n",
			"os.replace": "import os\nos.replace(a, b)\n",
			"os.rename": "import os\nos.rename(a, b)\n",
			"os.remove": "import os\nos.remove(p)\n",
			"os.unlink": "import os\nos.unlink(p)\n",
			"from os import replace": "from os import replace\nreplace(a, b)\n",
			"from os import remove as rm": "from os import remove as rm\nrm(p)\n",
			"import os as o": "import os as o\no.unlink(p)\n",
			"os function as a value": "import os\ncleanup = os.remove\ncleanup(p)\n",
			"os.makedirs": "import os\nos.makedirs(d, exist_ok=True)\n",
			"shutil": "import shutil\nshutil.copyfile(a, b)\n",
			"shutil aliased": "import shutil as s\ns.move(a, b)\n",
			"from shutil import": "from shutil import rmtree\nrmtree(d)\n",
			"tempfile": "import tempfile\ntempfile.NamedTemporaryFile(dir=d)\n",
			"from tempfile import mkstemp as m": "from tempfile import mkstemp as m\nm(dir=d)\n",
			"Path.write_text": "from pathlib import Path\nPath(p).write_text(s)\n",
			"Path.write_bytes chain": "self.root.joinpath(rel).write_bytes(b)\n",
			"Path.unlink": "target.unlink(missing_ok=True)\n",
			"Path.touch": "target.touch()\n",
		}
		for rel in (
			"agent/changes/apply_job.py",
			"agent/changes/process_runner.py",
			PROPOSE_TOOL_FILE,
			CHANGE_GUARD_FILE,
			PROPOSAL_CONTROLLER_FILE,
			"agent/run_log.py",
		):
			for case, source in cases.items():
				with self.subTest(rel=rel, case=case):
					self.assertCaught(check_fs_writes_only_in_file_writer({rel: source}), rel)

	def test_fs_reads_and_file_writer_writes_are_clean(self):
		writer = (
			"import os\nimport tempfile\n"
			"fd, temp = tempfile.mkstemp(dir=d)\n"
			"with os.fdopen(fd, 'wb') as handle:\n\thandle.write(b)\n"
			"os.replace(temp, full)\nos.remove(full)\n"
		)
		clean = {
			FILE_WRITER_FILE: writer,
			PROPOSE_TOOL_FILE: "with open(full, 'rb') as handle:\n\tdata = handle.read()\n",
			CHANGE_GUARD_FILE: "import os\nwith open(p, encoding='utf-8') as h:\n\tos.path.join(a, b)\n",
			"agent/tools/source.py": "open(full, 'r', encoding='utf-8', errors='replace')\nopen(p, mode='rt')\n",
			"agent/changes/apply_job.py": (
				"import os\nfrom pathlib import Path\n"
				"text = Path(p).read_text()\nPath(p).open()\nos.open(p, os.O_RDONLY | os.O_CLOEXEC)\n"
				"name = name.replace('a', 'b')\nos.path.exists(p)\nfile_writer.remove_created(full)\n"
			),
			PROPOSAL_CONTROLLER_FILE: "doc.rename(new)\n",
			# Outside agent/** and the controller the rule does not apply (ADR-013: eval/ untouched).
			"eval/run_eval.py": "import shutil\nopen(p, 'w')\nshutil.rmtree(d)\n",
			"install.py": "import os\nos.remove(p)\n",
		}
		self.assertEqual(check_fs_writes_only_in_file_writer(clean), [])

	def test_file_writer_recheck_rule_catches_bypass(self):
		canonical = (
			"def _refuse_unless_canonical(full_path):\n"
			"\tfull = os.path.abspath(full_path)\n"
			"\tif source.resolve_safe_path(os.path.relpath(full, source.get_source_root())) != full:\n"
			"\t\traise ValueError(full)\n"
		)
		writer = (
			"import os\nimport tempfile\nfrom erp_ai.agent.tools import source\n\n{canonical}\n"
			"def make_parents(full_path, app_dir):\n\t{make}\n\tos.mkdir(full_path)\n\n"
			"def remove_empty_dirs(dirs):\n\tfor d in dirs:\n\t\t_refuse_unless_canonical(d)\n\t\t{remove}\n\n"
			"def write_atomic(full_path, content):\n\t_refuse_unless_canonical(full_path)\n"
			"\tfd, temp = tempfile.mkstemp(dir=os.path.dirname(full_path))\n\tos.replace(temp, full_path)\n\n"
			"def remove_file(full_path):\n\t_refuse_unless_canonical(full_path)\n\tos.remove(full_path)\n"
		)
		recheck = "_refuse_unless_canonical(full_path)"
		good = {"canonical": canonical, "make": recheck, "remove": "os.rmdir(d)"}
		self.assertEqual(
			check_file_writer_rechecks_through_resolver({FILE_WRITER_FILE: writer.format(**good)}), []
		)
		direct = (
			"from erp_ai.agent.tools.source import resolve_safe_path as resolve\n\n"
			"def _refuse_unless_canonical(full_path):\n\tif resolve(full_path) != full_path:\n"
			"\t\traise ValueError(full_path)\n"
		)
		self.assertEqual(
			check_file_writer_rechecks_through_resolver(
				{
					FILE_WRITER_FILE: writer.format(**{**good, "canonical": direct}).replace(
						"from erp_ai.agent.tools import source\n", ""
					)
				}
			),
			[],
		)
		cases = {
			"resolver not called": (
				{"canonical": "def _refuse_unless_canonical(full_path):\n\tpass\n"},
				"_refuse_unless_canonical",
			),
			"resolver not called, decoy source call": (
				{"canonical": "def _refuse_unless_canonical(full_path):\n\tsource.get_source_root()\n"},
				"_refuse_unless_canonical",
			),
			"no canonical function": (
				{"canonical": "def _refuse_other(full_path):\n\tsource.resolve_safe_path(full_path)\n"},
				"_refuse_unless_canonical",
			),
			"realpath in remove_empty_dirs": (
				{"remove": "os.path.realpath(d)"},
				"realpath",
			),
			"aliased realpath": (
				{"remove": "rp(d)", "canonical": "from os.path import realpath as rp\n" + canonical},
				"realpath",
			),
			"commonpath": ({"remove": "os.path.commonpath([d, d])"}, "commonpath"),
			"is_relative_to": ({"remove": "PurePath(d).is_relative_to(d)"}, "is_relative_to"),
			"readlink": ({"remove": "os.readlink(d)"}, "readlink"),
			"make_parents skips the recheck": ({"make": "pass"}, "make_parents"),
		}
		for name, (overrides, fragment) in cases.items():
			with self.subTest(case=name):
				source = writer.format(**{**good, **overrides})
				self.assertCaught(
					check_file_writer_rechecks_through_resolver({FILE_WRITER_FILE: source}), fragment
				)
		no_remover = (
			"import os\nfrom erp_ai.agent.tools import source\n\n"
			+ canonical
			+ ("\ndef make_parents(full_path, app_dir):\n\t_refuse_unless_canonical(full_path)\n")
		)
		self.assertCaught(
			check_file_writer_rechecks_through_resolver({FILE_WRITER_FILE: no_remover}), "remove_empty_dirs"
		)
		remover_skips_recheck = (
			no_remover + "\ndef remove_empty_dirs(dirs):\n\tfor d in dirs:\n\t\tos.rmdir(d)\n"
		)
		self.assertCaught(
			check_file_writer_rechecks_through_resolver({FILE_WRITER_FILE: remover_skips_recheck}),
			"remove_empty_dirs",
		)
		self.assertCaught(check_file_writer_rechecks_through_resolver({}), FILE_WRITER_FILE)
		# Condition 4 (on from T6): a file-system function outside FILE_WRITER_RECHECKERS is caught.
		renamer = writer.format(**good) + "\ndef rename_file(a, b):\n\tos.replace(a, b)\n"
		self.assertCaught(
			check_file_writer_rechecks_through_resolver({FILE_WRITER_FILE: renamer}), "rename_file"
		)
		# The ADR-011 name rule still catches the old name in this file: the new rule does not loosen it.
		old_name = {
			CHANGE_GUARD_FILE: "from erp_ai.agent.tools import source\n\ndef check_write_path(rel):\n"
			"\tfull = source.resolve_safe_path(rel)\n\tif full is None:\n\t\treturn _refused(PATH_INVALID)\n"
			"\treturn full\n",
			FILE_WRITER_FILE: "def _refuse_unsafe_path(full_path):\n\treturn None\n",
		}
		self.assertCaught(
			check_change_guard_uses_resolve_safe_path(old_name), FILE_WRITER_FILE, "second path resolver"
		)
		self.assertTrue(FILE_WRITER_RECHECKS_ALL)
		self.assertEqual(
			FILE_WRITER_RECHECKERS, ("make_parents", "remove_empty_dirs", "write_atomic", "remove_file")
		)

	def test_changes_set_user_or_publish_caught(self):
		cases = {
			"set_user": "import frappe\nfrappe.set_user('Administrator')\n",
			"set_user aliased import": "from frappe import set_user as su\nsu(owner)\n",
			"set_user aliased module": "import frappe as f\nf.set_user(owner)\n",
			"set_user as a value": "import frappe\nbecome = frappe.set_user\nbecome(owner)\n",
			"set_user by string": "import frappe\ngetattr(frappe, 'set_user')(owner)\n",
			"publish_realtime": "import frappe\nfrappe.publish_realtime('e', {}, user=u)\n",
			"publish_realtime from realtime": "from frappe.realtime import publish_realtime as p\np('e')\n",
			"publish by dotted string": "import frappe\nfrappe.get_attr('frappe.publish_realtime')('e')\n",
		}
		for rel in (
			"agent/changes/apply_job.py",
			"agent/changes/transitions.py",
			"agent/changes/new_step.py",
		):
			for case, source in cases.items():
				with self.subTest(rel=rel, case=case):
					self.assertCaught(check_changes_never_set_user_or_publish({rel: source}), rel, "ADR-013")

	def test_changes_session_reads_and_other_modules_are_clean(self):
		clean = {
			"agent/changes/apply_job.py": (
				"import frappe\nif frappe.session.user != runner:\n\tpass\n"
				"user = frappe.session.user\nnote = 'never calls set_user or publish_realtime'\n"
				"doc.user = frappe.session.user\nrow['user'] = user\n"
			),
			"agent/changes/transitions.py": "import frappe\nfrappe.db.set_value(D, n, {'decided_by': frappe.session.user})\n",
			# Outside agent/changes/ this rule does not apply (run_status.py publishes, by ADR-008).
			RUN_STATUS_FILE: "import frappe\nfrappe.publish_realtime('e', {}, room=r, after_commit=False)\n",
			"agent/runner.py": "import frappe\nfrappe.set_user(u)\n",
		}
		self.assertEqual(check_changes_never_set_user_or_publish(clean), [])

	# FEAT-004 T32: the enqueue and subprocess rules also catch the change path ------------------------

	def test_single_enqueue_catches_change_path_files(self):
		for rel in ("agent/changes/apply_job.py", PROPOSE_TOOL_FILE, PROPOSAL_CONTROLLER_FILE):
			for source in (
				"import frappe as f\nf.enqueue('erp_ai.agent.changes.apply_job.run_change')\n",
				"from frappe.utils.background_jobs import enqueue as later\nlater('x')\n",
				"import frappe\nfrappe.enqueue_doc(D, n, 'run')\n",
			):
				with self.subTest(rel=rel, source=source):
					self.assertCaught(check_single_enqueue_site({rel: source}), rel, QUEUE_FILE)

	def test_subprocess_caught_in_change_path_files(self):
		for rel in (
			"agent/changes/apply_job.py",
			FILE_WRITER_FILE,
			PROPOSE_TOOL_FILE,
			CHANGE_GUARD_FILE,
			PROPOSAL_CONTROLLER_FILE,
		):
			for source in (
				"import subprocess as sp\nsp.run(['bench', 'migrate'], timeout=3)\n",
				"from subprocess import check_output as co\nco(['git', 'status'], timeout=3)\n",
				"from os import system\nsystem('bench migrate')\n",
				"import os as o\no.execvp('bench', ['bench'])\n",
			):
				with self.subTest(rel=rel, source=source):
					self.assertCaught(check_subprocess_only_in_source_tool({rel: source}), rel, "outside")

	# FEAT-004 T44: ADR-022 git rules ---------------------------------------------------------------

	def git_product(self, rel: str, extra: str = "", replace: tuple = ()) -> dict:
		"""GIT_CLEAN with `extra` appended to `rel` (a new file when absent) and `replace=(old, new)` applied."""
		text = GIT_CLEAN.get(rel, "")
		if replace:
			self.assertIn(replace[0], text)
			text = text.replace(*replace)
		return {**GIT_CLEAN, rel: text + extra}

	def test_git_rules_pass_on_the_clean_product(self):
		for check in (
			check_git_subcommands_only_allowed_sets_per_file,
			check_no_forbidden_git_operations_in_product,
			check_git_commit_add_rm_argv_shape,
			check_git_env_single_definition,
			check_bot_identity_constants,
			check_no_git_in_web_and_runner,
			check_bench_allowlist_has_no_git_running_subcommands,
			check_apps_root_single_function,
		):
			with self.subTest(check=check.__name__):
				self.assertEqual(check(GIT_CLEAN), [])
		# ADR-044 (CHG-008): the panel layer rule now forbids erp_ai.agent.tools, which the fixture's panel imports on
		# purpose to show the git rules; the layer rules are checked on the rest of the fixture.
		self.assertEqual(
			check_layer_imports({rel: text for rel, text in GIT_CLEAN.items() if rel != "ticket_panel.py"}),
			[],
		)
		scan = GitScan(GIT_CLEAN)
		self.assertEqual(
			{sub for argv in scan.argvs if argv.root_rel == SOURCE_TOOL_FILE for sub in argv.subcommands},
			{"log", "blame", "rev-parse", "status", "cat-file"},
		)

	def test_change_text_layer_rule_catches_non_stdlib_imports(self):
		for source in (
			"import frappe\n",
			"from frappe.utils import cstr\n",
			"import helpdesk\n",
			"from erp_ai.agent.tools import source\n",
			"from erp_ai.agent import policy\n",
			"from . import queue\n",
			"from erp_ai import gateway\n",
			"import erp_ai.erp_ai_agent\n",
		):
			with self.subTest(source=source):
				self.assertCaught(
					check_layer_imports({CHANGE_TEXT_FILE: source}), CHANGE_TEXT_FILE, "change_text"
				)

	def test_change_text_layer_rule_allows_stdlib_and_constants(self):
		clean = "import re\nimport unicodedata\nfrom erp_ai.constants import BOT_GIT_NAME\nfrom erp_ai import constants\n"
		self.assertEqual(check_layer_imports({CHANGE_TEXT_FILE: clean}), [])

	def test_git_subcommands_rule_catches_each_way_of_reaching_git(self):
		run_read = "\n\ndef extra(r):\n\treturn run_git_read(r, {sub})\n"
		cases = {
			# outside the read set, as a literal, a module constant and an f-string
			"source push": self.git_product(SOURCE_TOOL_FILE, run_read.format(sub='"push"')),
			"source add": self.git_product(SOURCE_TOOL_FILE, run_read.format(sub='"add"')),
			"source constant": self.git_product(
				SOURCE_TOOL_FILE, "\nPUSH = 'pu' + 'sh'" + run_read.format(sub="PUSH")
			),
			"source f-string": self.git_product(SOURCE_TOOL_FILE, run_read.format(sub="f\"{'fetch'}\"")),
			# a log/blame gate whose set is wider than log/blame
			"source gate": self.git_product(
				SOURCE_TOOL_FILE,
				replace=('GIT_SUBCOMMANDS = {"log", "blame"}', 'GIT_SUBCOMMANDS = {"log", "push"}'),
			),
			# a read subcommand, and log, in the write file (both outside {add, commit, rm})
			"runner status": self.git_product(
				PROCESS_RUNNER_FILE, "\nX = _run_git_write(r, rel, 1, ['status'])\n"
			),
			"runner literal log": self.git_product(
				PROCESS_RUNNER_FILE,
				"\nX = _run_wrapped(['git', *source.git_global_options(read=False), 'log'], cwd=r, env=e, limit_s=1)\n",
			),
			# the subcommand passed through a variable / a parameter of another function
			"variable": self.git_product(
				PROCESS_RUNNER_FILE, "\n\ndef f(r, sub):\n\treturn _run_git_write(r, 'x', 1, [sub])\n"
			),
			"forwarded": self.git_product(
				SOURCE_TOOL_FILE, "\n\ndef f(r, sub):\n\treturn run_git_read(r, sub)\n"
			),
			"local": self.git_product(
				SOURCE_TOOL_FILE, "\n\ndef f(r):\n\tsub = pick()\n\treturn run_git_read(r, sub)\n"
			),
			# aliased import of the wrapper, the wrapper used as a value
			"alias": self.git_product(
				"agent/changes/apply_job.py",
				"\nfrom erp_ai.agent.tools.source import run_git_read as rg\nrg(r, 'fetch')\n",
			),
			"as value": self.git_product("agent/changes/apply_job.py", "\nreader = source.run_git_read\n"),
			# git in another file: literal, path, constant list + concatenation, f-string, tuple
			"other literal": self.git_product("agent/changes/apply_job.py", "\nC = ['git', 'status']\n"),
			"other path": self.git_product("agent/tools/read.py", "C = ('/usr/bin/git', 'log')\n"),
			"other concat": self.git_product(
				"agent/changes/apply_job.py", "\nGIT = ['git']\nC = GIT + ['status']\n"
			),
			"other spread": self.git_product(
				"agent/changes/apply_job.py", "\nC = [*source.GIT_PREFIX, 'rev-parse']\n"
			)
			| {SOURCE_TOOL_FILE: GIT_CLEAN[SOURCE_TOOL_FILE] + "\nGIT_PREFIX = ('git', '--no-pager')\n"},
			"other f-string": self.git_product("handlers.py", "\nC = [f\"{'git'}\", 'log']\n"),
			# no constant subcommand: built and then changed
			"mutated": self.git_product(
				PROCESS_RUNNER_FILE, "\n\ndef f(r):\n\tcmd = ['git']\n\tcmd += ['push']\n\treturn cmd\n"
			),
		}
		for case, sources in cases.items():
			with self.subTest(case=case):
				self.assertCaught(check_git_subcommands_only_allowed_sets_per_file(sources), "git")

	def test_git_subcommands_rule_names_the_file_and_the_reason(self):
		found = check_git_subcommands_only_allowed_sets_per_file(
			self.git_product(PROCESS_RUNNER_FILE, "\nX = _run_git_write(r, rel, 1, ['status'])\n")
		)
		self.assertCaught(found, PROCESS_RUNNER_FILE, "status", "ADR-022")
		found = check_git_subcommands_only_allowed_sets_per_file(
			self.git_product("agent/tools/read.py", "C = ['git', 'log']\n")
		)
		self.assertCaught(found, "agent/tools/read.py", "outside")

	def test_forbidden_git_operations_caught(self):
		for sub in GIT_FORBIDDEN_SUBCOMMANDS:
			for case, sources in (
				(
					"read arg",
					self.git_product(
						SOURCE_TOOL_FILE, f"\n\ndef f(r):\n\treturn run_git_read(r, 'rev-parse', '{sub}')\n"
					),
				),
				(
					"write list",
					self.git_product(PROCESS_RUNNER_FILE, f"\nX = _run_git_write(r, rel, 1, ['{sub}'])\n"),
				),
				(
					"constant",
					self.git_product(
						PROCESS_RUNNER_FILE,
						f"\nSUB = '{sub}'\nX = _run_git_write(r, rel, 1, ['commit', SUB])\n",
					),
				),
				("shlex", self.git_product(PROCESS_RUNNER_FILE, f"\nX = shlex.split('git {sub} origin')\n")),
			):
				with self.subTest(sub=sub, case=case):
					self.assertCaught(check_no_forbidden_git_operations_in_product(sources), repr(sub))
		for fragment in GIT_FORBIDDEN_FRAGMENTS:
			for rel in ("agent/changes/apply_job.py", "eval/run_eval.py", SOURCE_TOOL_FILE):
				with self.subTest(fragment=fragment, rel=rel):
					sources = self.git_product(rel, f"\nX = f'-c {{key}}{fragment}x'\n")
					self.assertCaught(check_no_forbidden_git_operations_in_product(sources), rel, fragment)
		for config_read in (
			"open(os.path.join(repo, '.git', 'config'))",
			"(Path(repo) / '.git' / 'config').read_text()",
			"open(f'{repo}/.git/config')",
			"open(repo + '/.git' + '/config')",
		):
			with self.subTest(config_read=config_read):
				sources = self.git_product(CHANGE_GUARD_FILE, f"\nX = {config_read}\n")
				self.assertCaught(
					check_no_forbidden_git_operations_in_product(sources), CHANGE_GUARD_FILE, "config"
				)
		# a git dir found at runtime, no literal .git: only the subprocess-file config branch sees it
		for rel in SUBPROCESS_FILES:
			for config_read in (
				"open(f'{git_dir}/config')",
				"open(os.path.join(git_dir, 'config'))",
			):
				with self.subTest(rel=rel, config_read=config_read):
					sources = self.git_product(
						rel, f"\n\ndef f(r):\n\tgit_dir = locate(r)\n\treturn {config_read}\n"
					)
					self.assertCaught(
						check_no_forbidden_git_operations_in_product(sources), rel, "git config file"
					)

	def test_forbidden_git_operations_clean_cases(self):
		clean = self.git_product(
			"agent/changes/apply_job.py",
			"\nMESSAGE = 'remote không tên; nhánh theo dõi upstream'\nGIT_DIR = '.git'\nSETTINGS = os.path.join(root, 'config')\n",
		)
		self.assertEqual(check_no_forbidden_git_operations_in_product(clean), [])
		for rel in SUBPROCESS_FILES:
			with self.subTest(rel=rel):
				clean = self.git_product(rel, "\nSTEP = 'configure'\nPATH = 'etc/configure'\n")
				self.assertEqual(check_no_forbidden_git_operations_in_product(clean), [])

	def test_git_write_argv_shape_caught(self):
		write = "\nX = _run_git_write(r, rel, 1, {args})\n"
		cases = {
			"commit without --only": write.format(args="['commit', '--no-gpg-sign', '-m', s]"),
			"commit without --no-gpg-sign": write.format(args="['commit', '--only', '-m', s]"),
			"rm without --cached": write.format(args="['rm', '-q']"),
			"commit spread": write.format(args="['commit', '--only', '--no-gpg-sign', *extra]"),
			"commit from a constant": "\nAMEND = ['commit', '--only', '--no-gpg-sign', '--amend']"
			+ write.format(args="AMEND"),
			"commit non-constant option": write.format(args="['commit', '--only', '--no-gpg-sign', flag]"),
			"add without --": "\nX = _run_wrapped(['git', *source.git_global_options(read=False), 'add', rel], cwd=r, env=e)\n",
			"add two paths": "\nX = _run_wrapped(['git', *source.git_global_options(read=False), 'add', '--', a, b], cwd=r, env=e)\n",
			"add magic path": "\nX = _run_wrapped(['git', *source.git_global_options(read=False), 'add', '--', f':(literal){rel}'], cwd=r, env=e)\n",
			"add magic constant": "\nX = _run_wrapped(['git', *source.git_global_options(read=False), 'add', '--', ':' + rel], cwd=r, env=e)\n",
			"rm two separators": "\nX = _run_wrapped(['git', *source.git_global_options(read=False), 'rm', '--cached', '--', '--', rel], cwd=r, env=e)\n",
			"commit no path": "\nX = _run_wrapped(['git', *source.git_global_options(read=False), 'commit', '--only', '--no-gpg-sign', '--'], cwd=r, env=e)\n",
			"commit without --": "\nX = _run_wrapped(['git', *source.git_global_options(read=False), 'commit', '--only', '--no-gpg-sign', *rels], cwd=r, env=e)\n",
			"commit magic among paths": "\nX = _run_git_write(r, ('a.py', f':(literal){rel}', 'b.py'), 1, ['commit', '--only', '--no-gpg-sign'])\n",
			"add spread path": "\nX = _run_git_write(r, rels, 1, ['add'])\n",
			"add two paths through the helper": "\nX = _run_git_write(r, (a, b), 1, ['add'])\n",
			"rm spread path": "\nX = _run_git_write(r, sorted(rels), 1, ['rm', '--cached'])\n",
			"rm no path through the helper": "\nX = _run_git_write(r, (), 1, ['rm', '--cached'])\n",
		}
		for flag in (*COMMIT_FORBIDDEN_FLAGS, "--amen", "-am", "--fixup=HEAD", "--squash=HEAD"):
			cases[f"commit {flag}"] = write.format(
				args=f"['commit', '--only', '--no-gpg-sign', '{flag}', '-m', s]"
			)
		for case, extra in cases.items():
			with self.subTest(case=case):
				found = check_git_commit_add_rm_argv_shape(self.git_product(PROCESS_RUNNER_FILE, extra))
				self.assertCaught(found, PROCESS_RUNNER_FILE, "ADR-022")

	def test_git_write_argv_shape_allows_commit_with_one_to_n_paths(self):
		cases = {
			"one constant": "\nX = _run_git_write(r, ('a.py',), 1, ['commit', '--only', '--no-gpg-sign'])\n",
			"three names": "\nX = _run_git_write(r, (a, b, c), 1, ['commit', '--only', '--no-gpg-sign'])\n",
			"spread of a sorted tuple": "\nX = _run_git_write(r, sorted(rels), 1, ['commit', '--only', '--no-gpg-sign'])\n",
			"literal argv with paths": "\nX = _run_wrapped(['git', *source.git_global_options(read=False), 'commit', '--only', '--no-gpg-sign', '--', a, *rest], cwd=r, env=e)\n",
		}
		for case, extra in cases.items():
			with self.subTest(case=case):
				self.assertEqual(
					check_git_commit_add_rm_argv_shape(self.git_product(PROCESS_RUNNER_FILE, extra)), []
				)

	def test_git_write_argv_shape_allows_a_message_that_looks_like_a_flag(self):
		extra = "\nX = _run_git_write(r, rel, 1, ['commit', '--only', '--no-gpg-sign', '-m', '-a', '-m', '--amend'])\n"
		self.assertEqual(check_git_commit_add_rm_argv_shape(self.git_product(PROCESS_RUNNER_FILE, extra)), [])

	def test_git_env_single_definition_caught(self):
		new_add = "\nX = _run_wrapped(['git', *source.git_global_options(read=False), 'add', '--', rel], cwd=r, env={env})\n"
		cases = {
			"marker in runner": self.git_product(
				PROCESS_RUNNER_FILE, "\nENV = {'GIT_CONFIG_GLOBAL': '/dev/null'}\n"
			),
			"marker keyword": self.git_product(
				"agent/changes/apply_job.py", "\nENV = dict(GIT_CONFIG_NOSYSTEM='1')\n"
			),
			"hooks f-string": self.git_product(
				PROCESS_RUNNER_FILE, "\nOPTS = ['-c', f'core.hooksPath={d}']\n"
			),
			"marker elsewhere in source": self.git_product(
				SOURCE_TOOL_FILE, "\n\ndef other_env():\n\treturn {'GIT_TERMINAL_PROMPT': '0'}\n"
			),
			"identity elsewhere": self.git_product(
				PROCESS_RUNNER_FILE, "\nENV = {'GIT_AUTHOR_' + 'NAME': n}\n"
			),
			"second git_env": self.git_product(
				PROCESS_RUNNER_FILE, "\n\ndef git_env(*, identity):\n\treturn {}\n"
			),
			"second options": self.git_product(
				"agent/changes/apply_job.py", "\n\ndef git_global_options(*, read):\n\treturn []\n"
			),
			"os.environ env": self.git_product(PROCESS_RUNNER_FILE, new_add.format(env="{**os.environ}")),
			"env mixed": self.git_product(
				PROCESS_RUNNER_FILE, new_add.format(env="source.git_env(identity=True) | dict(os.environ)")
			),
			"own env": self.git_product(PROCESS_RUNNER_FILE, new_add.format(env="_minimal_env()")),
			"no env": self.git_product(
				PROCESS_RUNNER_FILE,
				"\nX = _run_wrapped(['git', *source.git_global_options(read=False), 'add', '--', rel], cwd=r)\n",
			),
			"no options": self.git_product(
				PROCESS_RUNNER_FILE,
				"\nX = _run_wrapped(['git', 'add', '--', rel], cwd=r, env=source.git_env(identity=True))\n",
			),
			"read without options": self.git_product(
				SOURCE_TOOL_FILE, replace=("*git_global_options(read=True), subcommand", "subcommand")
			),
			"runner own env": self.git_product(
				PROCESS_RUNNER_FILE, replace=("env=source.git_env(identity=True)", "env={'PATH': '/usr/bin'}")
			),
		}
		for case, sources in cases.items():
			with self.subTest(case=case):
				self.assertCaught(check_git_env_single_definition(sources), "ADR-022")

	def test_git_env_single_definition_sees_aliases(self):
		aliased = self.git_product(
			PROCESS_RUNNER_FILE,
			replace=(
				"from erp_ai.agent.tools import source\n",
				"from erp_ai.agent.tools import source\nfrom erp_ai.agent.tools.source import git_env as ge\n",
			),
		)
		aliased[PROCESS_RUNNER_FILE] = aliased[PROCESS_RUNNER_FILE].replace("env=source.git_env(", "env=ge(")
		self.assertEqual(check_git_env_single_definition(aliased), [])

	def test_bot_identity_caught(self):
		cases = {
			"real address": self.git_product(
				CONSTANTS_FILE, replace=('"erp-ai-agent@bot.invalid"', '"erp-ai-agent@miyano.com.vn"')
			),
			"no domain": self.git_product(
				CONSTANTS_FILE, replace=('"erp-ai-agent@bot.invalid"', '"bot.invalid"')
			),
			"other name": self.git_product(CONSTANTS_FILE, replace=('"ERP AI Agent"', '"Bot"')),
			"literal email": self.git_product(
				SOURCE_TOOL_FILE,
				replace=('"GIT_AUTHOR_EMAIL": BOT_GIT_EMAIL', '"GIT_AUTHOR_EMAIL": "a@b.invalid"'),
			),
			"agent user": self.git_product(
				SOURCE_TOOL_FILE,
				replace=(
					'"GIT_COMMITTER_EMAIL": BOT_GIT_EMAIL',
					'"GIT_COMMITTER_EMAIL": constants.AGENT_USER',
				),
			),
			"missing variable": self.git_product(
				SOURCE_TOOL_FILE, replace=('"GIT_COMMITTER_NAME": BOT_GIT_NAME,', "")
			),
			"user.email option": self.git_product(
				PROCESS_RUNNER_FILE, "\nOPTS = ['-c', 'user.email=x@y.z']\n"
			),
			"user.name option": self.git_product(SOURCE_TOOL_FILE, "\nOPTS = ['-c', f'user.name={n}']\n"),
			"agent user alias": self.git_product(
				PROCESS_RUNNER_FILE, "\nfrom erp_ai.constants import AGENT_USER as who\nX = who\n"
			),
		}
		for case, sources in cases.items():
			with self.subTest(case=case):
				self.assertCaught(check_bot_identity_constants(sources), "ADR-022")

	def test_no_git_in_web_and_runner_caught(self):
		cases = {
			"controller subprocess": (PROPOSAL_CONTROLLER_FILE, "\nimport subprocess as sp\n"),
			"controller alias": (
				PROPOSAL_CONTROLLER_FILE,
				"\nfrom erp_ai.agent.tools.source import read_git_state as rgs\nX = rgs(p, new_file=False)\n",
			),
			"controller module": (
				PROPOSAL_CONTROLLER_FILE,
				"\nfrom erp_ai.agent.tools import source\nX = source.git_head(r)\n",
			),
			"handlers runner module": (HANDLERS_FILE, "\nfrom erp_ai.agent.changes import process_runner\n"),
			"runner getattr": (RUNNER_FILE, "\nX = getattr(source, 'read_git_state')\n"),
			"runner git argv": (RUNNER_FILE, "\nX = ['git', 'status']\n"),
			"whitelist through helper": (
				"ticket_panel.py",
				"",
			),
			"whitelist local import": (
				"change_decision.py",
				"import frappe\n\n\n@frappe.whitelist()\ndef decide(name):\n\timport subprocess\n\treturn subprocess.run(['ls'], timeout=1)\n",
			),
		}
		for case, (rel, extra) in cases.items():
			with self.subTest(case=case):
				sources = self.git_product(rel, extra)
				if case == "whitelist through helper":
					sources = self.git_product(
						rel, replace=('return {"name": name}', "return source.run_git_read(name, 'status')")
					)
				self.assertCaught(check_no_git_in_web_and_runner(sources), rel, "ADR-022")

	def test_bench_allowlist_caught(self):
		for command in GIT_RUNNING_BENCH_SUBCOMMANDS:
			for case, replace in (
				(
					"site list",
					(
						'SITE_COMMANDS = ("migrate", "clear-cache")',
						f'SITE_COMMANDS = ("migrate", "{command}")',
					),
				),
				(
					"table",
					(
						'BENCH_COMMANDS = (*SITE_COMMANDS, BUILD_COMMAND, "version", RESTART_COMMAND)',
						f'BENCH_COMMANDS = (*SITE_COMMANDS, "{command}", RESTART_COMMAND)',
					),
				),
				("shape", ('["--site", site, command]', f'["--site", site, "{command}"]')),
			):
				with self.subTest(command=command, case=case):
					found = check_bench_allowlist_has_no_git_running_subcommands(
						self.git_product(CHANGE_GUARD_FILE, replace=replace)
					)
					self.assertCaught(found, CHANGE_GUARD_FILE, command)
		unreadable = self.git_product(
			CHANGE_GUARD_FILE,
			replace=(
				'BENCH_COMMANDS = (*SITE_COMMANDS, BUILD_COMMAND, "version", RESTART_COMMAND)',
				"BENCH_COMMANDS = tuple(load())",
			),
		)
		self.assertCaught(
			check_bench_allowlist_has_no_git_running_subcommands(unreadable), BENCH_COMMANDS_NAME
		)

	def test_apps_root_caught(self):
		cases = {
			"join": (
				"agent/changes/apply_job.py",
				"\nROOT = os.path.join(frappe.utils.get_bench_path(), 'apps')\n",
			),
			"f-string": (
				"agent/changes/apply_job.py",
				"\n\ndef root(bench, app):\n\treturn f'{bench}/apps/{app}'\n",
			),
			"path": (CHANGE_GUARD_FILE, "\nROOT = Path(get_bench_path()) / 'apps'\n"),
			"app path": (
				CHANGE_GUARD_FILE,
				"\nROOT = os.path.dirname(os.path.dirname(frappe.get_app_path('frappe')))\n",
			),
			"second root": (CHANGE_GUARD_FILE, "\n\ndef get_source_root():\n\treturn '/srv'\n"),
		}
		for case, (rel, extra) in cases.items():
			with self.subTest(case=case):
				self.assertCaught(
					check_apps_root_single_function(self.git_product(rel, extra)), rel, "ADR-022"
				)
		no_root = self.git_product(SOURCE_TOOL_FILE, replace=("def get_source_root():", "def find_root():"))
		self.assertCaught(check_apps_root_single_function(no_root), APPS_ROOT_FUNCTION)

	# ADR-023 Ràng buộc (FEAT-004 T68) ------------------------------------------------------------------

	@staticmethod
	def changed(clean: dict, rel: str, extra: str = "", replace=None) -> dict:
		"""A copy of `clean` with `extra` appended to `rel` (a new file when absent) and `replace` applied."""
		sources = dict(clean)
		source = sources.get(rel, "")
		if replace is not None:
			assert replace[0] in source, replace[0]
			source = source.replace(*replace)
		sources[rel] = source + extra
		return sources

	def test_get_whitelist_reaching_change_state_clean(self):
		self.assertEqual(check_no_get_whitelist_reaches_change_state(WHITELIST_CLEAN), [])
		# The clean product is not clean because nothing is seen: the POST methods do reach the state machine.
		self.assertEqual(
			sorted((rel, node.name) for rel, node, _methods in change_state_whitelists(WHITELIST_CLEAN)),
			[("change_decision.py", "decide"), (PROPOSAL_CONTROLLER_FILE, "approve")],
		)

	def test_get_whitelist_reaching_change_state_caught(self):
		get_api = (
			'import frappe\n{imports}\n\n@frappe.whitelist(methods=("GET",))\ndef go(name=None):\n{body}\n'
		)
		cases = {
			"transitions call": (
				PROPOSAL_CONTROLLER_FILE,
				"",
				('methods=["POST"])\ndef approve', 'methods=["GET", "POST"])\ndef approve'),
			),
			"through a module dict": (
				"change_decision.py",
				"",
				('methods=["POST"])\ndef decide', 'methods=["POST", "GET"])\ndef decide'),
			),
			"through a module function": (
				"change_decision.py",
				'\n\n@frappe.whitelist(methods=["GET"])\ndef go(name=None):\n\treturn helper(name)\n',
				None,
			),
			"aliased import": (
				"api.py",
				get_api.format(
					imports=f"from erp_ai.{PROPOSAL_CONTROLLER_FILE[:-3].replace('/', '.')} import undo as back",
					body="\treturn back(name)",
				),
				None,
			),
			"transitions module alias": (
				"api.py",
				get_api.format(
					imports="import erp_ai.agent.changes.transitions as t",
					body="\treturn t.request_undo(name, 'u')",
				),
				None,
			),
			"relative transitions import": (
				"api.py",
				get_api.format(
					imports="from .agent.changes import transitions",
					body="\treturn transitions.request_undo(name, 'u')",
				),
				None,
			),
			"transitions imported in the body": (
				"api.py",
				get_api.format(
					imports="",
					body="\timport erp_ai.agent.changes.transitions\n\treturn frappe.get_attr(name)(name)",
				),
				None,
			),
			"transitions path as text": (
				"api.py",
				get_api.format(
					imports="",
					body="\treturn frappe.get_attr('erp_ai.agent.changes.transitions.request_undo')(name)",
				),
				None,
			),
		}
		for case, (rel, extra, replace) in cases.items():
			with self.subTest(case=case):
				sources = self.changed(WHITELIST_CLEAN, rel, extra, replace)
				self.assertCaught(check_no_get_whitelist_reaches_change_state(sources), rel, "ADR-023")

	def test_change_link_api_method_path_clean(self):
		self.assertEqual(check_change_link_builds_no_api_method_path(CHANGE_LINK_CLEAN), [])
		self.assertIn("/app/erp-ai-change-proposal/\0?\0", change_link_string_shapes(CHANGE_LINK_CLEAN))

	def test_change_link_api_method_path_caught(self):
		cases = {
			"literal": '\nURL = "/api/method/erp_ai.change_decision.decide"\n',
			"f-string": '\n\ndef path(method, query):\n\treturn f"/api/method/{method}?{query}"\n',
			"concatenation": '\nURL = "/api/" + "method/" + DECIDE_METHOD\n',
			"constant prefix": '\nAPI = "/api/method"\n\n\ndef path(method):\n\treturn f"{API}/{method}"\n',
			"imported prefix": "\nfrom erp_ai.constants import API_ROOT\n\n\ndef path(m):\n\treturn API_ROOT + m\n",
			"full url": '\n\ndef url(host, method):\n\treturn host + "/api/method/" + method\n',
		}
		with_constant = self.changed(CHANGE_LINK_CLEAN, CONSTANTS_FILE, 'API_ROOT = "/api/method/"\n')
		for case, extra in cases.items():
			with self.subTest(case=case):
				sources = self.changed(with_constant, CHANGE_LINK_FILE, extra)
				self.assertCaught(
					check_change_link_builds_no_api_method_path(sources), CHANGE_LINK_FILE, "ADR-023"
				)
		missing = {rel: src for rel, src in CHANGE_LINK_CLEAN.items() if rel != CHANGE_LINK_FILE}
		self.assertCaught(check_change_link_builds_no_api_method_path(missing), CHANGE_LINK_FILE, "missing")

	def test_registry_one_grant_function_clean(self):
		self.assertEqual(check_registry_has_one_grant_function(GRANT_CLEAN), [])
		aliased = self.changed(
			GRANT_CLEAN,
			RUNNER_FILE,
			replace=("import grant\n", "import grant as issue\n"),
		)
		aliased[RUNNER_FILE] = aliased[RUNNER_FILE].replace("granted = grant(", "granted = issue(")
		self.assertEqual(check_registry_has_one_grant_function(aliased), [])
		chained = self.changed(
			GRANT_CLEAN,
			RUNNER_FILE,
			replace=("\tgranted = grant(inputs)\n\treturn granted.", "\treturn grant(inputs)."),
		)
		self.assertEqual(check_registry_has_one_grant_function(chained), [])
		documented = self.changed(
			GRANT_CLEAN,
			QUEUE_FILE,
			f'\n\ndef f():\n\t"""Replaces _unrestricted_specs; never call {SPEC_SOURCE} here."""\n',
		)
		self.assertEqual(check_registry_has_one_grant_function(documented), [])

	def test_registry_one_grant_function_caught(self):
		cases = {
			"removed function back": (REGISTRY_FILE, "\n\ndef _unrestricted_specs():\n\treturn []\n", None),
			"removed name read": (QUEUE_FILE, "\nX = _unrestricted_specs\n", None),
			"removed name as attribute": (
				QUEUE_FILE,
				"\nX = registry.get_unrestricted_tool_schemas('L3')\n",
				None,
			),
			"removed name imported": (
				QUEUE_FILE,
				"\nfrom erp_ai.agent.tools.registry import get_unrestricted_tool_schemas as g\n",
				None,
			),
			"removed name as text": (QUEUE_FILE, "\nX = getattr(registry, '_unrestricted_specs')\n", None),
			"second grant function": (
				REGISTRY_FILE,
				f"\n\ndef _other(level):\n\treturn [g for g, c in {GRANT_TABLE_NAME}]\n",
				None,
			),
			"no grant function": (
				REGISTRY_FILE,
				"",
				(f"for g, c in {GRANT_TABLE_NAME} if", "for g, c in () if"),
			),
			"second table": (REGISTRY_FILE, f"\n{GRANT_TABLE_NAME} = ()\n", None),
			"second schema call": (
				RUNNER_FILE,
				"\n\ndef again(granted):\n\treturn granted.schemas()\n",
				None,
			),
			"other schema function": (
				RUNNER_FILE,
				"",
				("return granted.schemas()", "return registry.schemas_for(inputs)"),
			),
			"no schema call": (RUNNER_FILE, "", ("return granted.schemas()", "return []")),
			"runner back on the legacy schema function": (
				RUNNER_FILE,
				"",
				("return granted.schemas()", f"return {SCHEMA_FUNCTION}(inputs)"),
			),
			"removed name as dotted path": (
				QUEUE_FILE,
				"\nX = frappe.get_attr('erp_ai.agent.tools.registry.get_unrestricted_tool_schemas')\n",
				None,
			),
			"6d90e79 _unrestricted_specs body under a new name": (
				REGISTRY_FILE,
				"\n\ndef _full_specs(effective_level, has_instructor, unrestricted):\n"
				"\tif not (unrestricted and has_instructor):\n\t\treturn []\n"
				"\tif effective_level not in LEVELS or effective_level == LEVELS[0]:\n\t\treturn []\n"
				f"\treturn [spec for spec in {SPEC_SOURCE}() if spec.group in UNRESTRICTED_GROUPS]\n",
				None,
			),
			"spec source listed outside the grant function": (
				REGISTRY_FILE,
				"",
				("return _granted_specs(level)\n", f"return {SPEC_SOURCE}()\n"),
			),
			"tool modules read outside the spec source": (
				REGISTRY_FILE,
				f"\n\ndef _extra():\n\treturn [importlib.import_module(n).TOOLS for n in {TOOL_MODULES_NAME}]\n",
				None,
			),
			"execute_tool skips the grant function": (
				REGISTRY_FILE,
				"",
				("granted = _granted_specs(context.effective_level)", "granted = context.specs"),
			),
			"execute_tool missing": (REGISTRY_FILE, "", ("def execute_tool(", "def run_tool(")),
			"spec source reached from the runner": (
				RUNNER_FILE,
				f"\n\ndef tools():\n\treturn registry.{SPEC_SOURCE}()\n",
				None,
			),
			"spec source imported elsewhere": (
				QUEUE_FILE,
				f"\nfrom erp_ai.agent.tools.registry import {SPEC_SOURCE}\n",
				None,
			),
		}
		for case, (rel, extra, replace) in cases.items():
			with self.subTest(case=case):
				sources = self.changed(GRANT_CLEAN, rel, extra, replace)
				self.assertCaught(check_registry_has_one_grant_function(sources), rel, "ADR-023")
		for rel in (REGISTRY_FILE, RUNNER_FILE):
			with self.subTest(missing=rel):
				missing = {other: src for other, src in GRANT_CLEAN.items() if other != rel}
				self.assertCaught(check_registry_has_one_grant_function(missing), rel, "missing")

	def test_agent_write_flag_clean(self):
		self.assertEqual(check_agent_write_flag_only_in_run_log_and_propose_tool(AGENT_WRITE_CLEAN), [])
		documented = self.changed(
			AGENT_WRITE_CLEAN,
			"erp_ai_agent/doctype/erp_ai_log/erp_ai_log.py",
			f'\n\ndef g():\n\t"""Never opens erp_ai.agent.agent_write_guard.{AGENT_WRITE_OPENER}."""\n',
		)
		self.assertEqual(check_agent_write_flag_only_in_run_log_and_propose_tool(documented), [])
		self.assertEqual(
			sorted({(rel, kind) for rel, _node, kind in agent_write_references(AGENT_WRITE_CLEAN)}),
			sorted(
				[
					(AGENT_WRITE_GUARD_FILE, AGENT_WRITE_FLAG_NAME),
					(AGENT_WRITE_GUARD_FILE, AGENT_WRITE_OPENER),  # its __all__ string: exempt in the guard
					(PROPOSE_TOOL_FILE, AGENT_WRITE_OPENER),
					(RUN_LOG_FILE, AGENT_WRITE_OPENER),
				]
			),
		)

	def test_agent_write_flag_caught(self):
		elsewhere = "erp_ai_agent/doctype/erp_ai_log/erp_ai_log.py"
		with_block = "\n\ndef f():\n\twith {opener}():\n\t\tpass\n"
		cases = {
			"opener called elsewhere": (
				elsewhere,
				f"\nfrom erp_ai.agent.agent_write_guard import {AGENT_WRITE_OPENER}\n"
				+ with_block.format(opener=AGENT_WRITE_OPENER),
			),
			"opener aliased": (
				elsewhere,
				f"\nfrom erp_ai.agent.agent_write_guard import {AGENT_WRITE_OPENER} as opened\n"
				+ with_block.format(opener="opened"),
			),
			"opener as attribute": (
				elsewhere,
				with_block.format(opener=f"guard.{AGENT_WRITE_OPENER}"),
			),
			"opener as text": (elsewhere, f"\nX = getattr(guard, '{AGENT_WRITE_OPENER}')\n"),
			"opener called in the guard": (
				AGENT_WRITE_GUARD_FILE,
				with_block.format(opener=AGENT_WRITE_OPENER),
			),
			"opener aliased in the guard": (
				AGENT_WRITE_GUARD_FILE,
				f"\nfrom erp_ai.agent.agent_write_guard import {AGENT_WRITE_OPENER} as again\n"
				+ with_block.format(opener="again"),
			),
			"other run_log.py": ("eval/run_log.py", with_block.format(opener=f"guard.{AGENT_WRITE_OPENER}")),
			"flag constant imported": (
				elsewhere,
				f"\nfrom erp_ai.agent.agent_write_guard import {AGENT_WRITE_FLAG_NAME}\n",
			),
			"flag constant as attribute": (RUN_LOG_FILE, f"\nX = guard.{AGENT_WRITE_FLAG_NAME}\n"),
			"flag value as key": (PROPOSE_TOOL_FILE, '\nfrappe.flags["erp_ai_agent_write_allowed"] = True\n'),
			"flag value as attribute": (elsewhere, "\nfrappe.flags.erp_ai_agent_write_allowed = True\n"),
			"flag value as keyword": (elsewhere, "\nfrappe.flags.update(erp_ai_agent_write_allowed=True)\n"),
			"opener as dotted path": (
				elsewhere,
				f"\nX = frappe.get_attr('erp_ai.agent.agent_write_guard.{AGENT_WRITE_OPENER}')\n",
			),
			"opener as hooks.py entry": (
				"hooks.py",
				f'\ndoc_events = {{"*": {{"validate": "erp_ai.agent.agent_write_guard.{AGENT_WRITE_OPENER}"}}}}\n',
			),
		}
		for case, (rel, extra) in cases.items():
			with self.subTest(case=case):
				sources = self.changed(AGENT_WRITE_CLEAN, rel, extra)
				self.assertCaught(
					check_agent_write_flag_only_in_run_log_and_propose_tool(sources), rel, "ADR-023"
				)
		missing = {rel: src for rel, src in AGENT_WRITE_CLEAN.items() if rel != AGENT_WRITE_GUARD_FILE}
		self.assertCaught(
			check_agent_write_flag_only_in_run_log_and_propose_tool(missing),
			AGENT_WRITE_GUARD_FILE,
			"missing",
		)
		unknown = self.changed(
			AGENT_WRITE_CLEAN,
			AGENT_WRITE_GUARD_FILE,
			replace=('= "erp_ai_agent_write_allowed"', '= "erp_ai_" + SUFFIX'),
		)
		self.assertCaught(
			check_agent_write_flag_only_in_run_log_and_propose_tool(unknown),
			AGENT_WRITE_GUARD_FILE,
			"ADR-023",
		)

	def test_set_user_agent_scanner_catches_each_switch_outside_enter_agent_session(self):
		self.assertEqual(check_set_user_agent_only_in_enter_agent_session(SESSION_SWITCH_CLEAN), [])
		runner_switch = "\n\ndef _switch():\n\t{}\n"
		for call in (
			# the runner keeping its own switch (the pre-T74 shape)
			"frappe.set_user(AGENT_USER)",
			"frappe.set_user(user=AGENT_USER)",
			"frappe.set_user(constants.AGENT_USER)",
			f"frappe.set_user({AGENT_USER!r})",
		):
			with self.subTest(call=call):
				sources = self.changed(SESSION_SWITCH_CLEAN, RUNNER_FILE, runner_switch.format(call))
				self.assertCaught(
					check_set_user_agent_only_in_enter_agent_session(sources), RUNNER_FILE, "ADR-033 QĐ 1"
				)
		aliased = (
			"from frappe import set_user as switch\nfrom erp_ai.constants import AGENT_USER as BOT\n\n"
			"switch(BOT)\n"
		)
		self.assertCaught(
			check_set_user_agent_only_in_enter_agent_session(
				self.changed(SESSION_SWITCH_CLEAN, "agent/tasks_like.py", aliased)
			),
			"agent/tasks_like.py",
		)
		# inside authority.py but in another function
		other_function = self.changed(
			SESSION_SWITCH_CLEAN, AUTHORITY_FILE, "\n\ndef helper():\n\tfrappe.set_user(AGENT_USER)\n"
		)
		self.assertCaught(
			check_set_user_agent_only_in_enter_agent_session(other_function), f"{AUTHORITY_FILE}:"
		)
		# enter_agent_session without the switch, or with two of them
		for replacement in (
			"frappe.session.user",
			"frappe.set_user(AGENT_USER)\n\tfrappe.set_user(AGENT_USER)",
		):
			with self.subTest(replacement=replacement):
				sources = self.changed(
					SESSION_SWITCH_CLEAN,
					AUTHORITY_FILE,
					replace=("frappe.set_user(AGENT_USER)", replacement),
				)
				self.assertCaught(check_set_user_agent_only_in_enter_agent_session(sources), "exactly once")
		missing = {rel: src for rel, src in SESSION_SWITCH_CLEAN.items() if rel != AUTHORITY_FILE}
		self.assertCaught(
			check_set_user_agent_only_in_enter_agent_session(missing), AUTHORITY_FILE, "missing"
		)
		clean = "\n\ndef _back(previous):\n\tfrappe.set_user(previous)\n\tfrappe.set_user('Guest')\n"
		self.assertEqual(
			check_set_user_agent_only_in_enter_agent_session(
				self.changed(SESSION_SWITCH_CLEAN, RUNNER_FILE, clean)
			),
			[],
		)

	def test_instructor_scan_scanner_catches_each_comment_scan(self):
		self.assertEqual(check_authority_has_no_comment_scan_for_instructor(INSTRUCTOR_SCAN_CLEAN), [])
		scan = (
			"\n\ndef {}(ticket_name):\n\tfor comment in fetch_ticket_comments(ticket_name):\n"
			"\t\tif is_instruction(comment['author'], ticket_name):\n\t\t\treturn comment['author']\n"
		)
		# the removed function back (the pre-T80 shape), and the same loop under another name
		for name, fragment in (
			(REMOVED_INSTRUCTOR_SCAN, REMOVED_INSTRUCTOR_SCAN),
			("newest_boss", "newest_boss"),
		):
			with self.subTest(name=name):
				sources = self.changed(INSTRUCTOR_SCAN_CLEAN, AUTHORITY_FILE, scan.format(name))
				self.assertCaught(
					check_authority_has_no_comment_scan_for_instructor(sources),
					f"{AUTHORITY_FILE}:",
					fragment,
					"ADR-030 QĐ 6",
				)
		# the runner calling it, by attribute, by alias or by name in a string
		for caller in (
			"authority.latest_instructor(ticket_name)",
			"from erp_ai.agent.authority import latest_instructor as pick",
			"patch_target = 'latest_instructor'",
		):
			with self.subTest(caller=caller):
				sources = self.changed(INSTRUCTOR_SCAN_CLEAN, RUNNER_FILE, f"\n{caller}\n")
				self.assertCaught(
					check_authority_has_no_comment_scan_for_instructor(sources),
					f"{RUNNER_FILE}:",
					"ADR-030 QĐ 6",
				)
		# a runner function doing the scan itself
		runner_scan = (
			"\n\ndef _boss(ticket_name):\n\tfor comment in authority.fetch_ticket_comments(ticket_name):\n"
			"\t\tif authority.is_instruction(comment['author'], ticket_name):\n\t\t\treturn comment['author']\n"
		)
		self.assertCaught(
			check_authority_has_no_comment_scan_for_instructor(
				self.changed(INSTRUCTOR_SCAN_CLEAN, RUNNER_FILE, runner_scan)
			),
			"_boss",
		)
		missing = {rel: src for rel, src in INSTRUCTOR_SCAN_CLEAN.items() if rel != AUTHORITY_FILE}
		self.assertCaught(
			check_authority_has_no_comment_scan_for_instructor(missing), AUTHORITY_FILE, "missing"
		)


# A minimal site_api: derived always-denied set, a refusal gating on it, two handlers gated before writing.
SITE_API_GATED = """def always_denied_doctypes():
	return frozenset(frappe.get_all("DocType", {"module": read.AI_MODULE}, pluck="name"))

def _denied(ctx):
	if ctx.unrestricted:
		return always_denied_doctypes()
	return frozenset(read.denied_doctypes() - {'User'}) | PERMISSION_DOCTYPES

def _refusal(doctype, ctx):
	if doctype in _denied(ctx):
		return {'ok': False, 'reason': 'không được phép'}
	return None

def update_record(args, ctx):
	doctype = args['doctype']
	if refusal := _refusal(doctype, ctx):
		return refusal
	doc = frappe.get_doc(doctype, args['name'])
	doc.save()

def call_method(args, ctx):
	if any(name in str(args) for name in always_denied_doctypes()):
		return {'ok': False}
	return frappe.call(args['method'])

TOOLS = [
	ToolSpec(name='api_update_record', handler=update_record),
	ToolSpec(name='api_call_method', handler=call_method),
]
"""

# ADR-023 Ràng buộc (T68): small products that keep each rule; each caught case changes one file.
WHITELIST_CLEAN = {
	PROPOSAL_CONTROLLER_FILE: """import frappe
from erp_ai.agent.changes import transitions

LIMIT = 5


@frappe.whitelist(methods=["POST"])
def approve(name=None):
	return transitions.approve(name, frappe.session.user)


@frappe.whitelist(methods=["GET", "POST"])
def form_data(name=None):
	return frappe.get_doc("ERP AI Change Proposal", name).as_dict(), LIMIT, _again(name)


def _again(name):
	return _again(name) if name else None
""",
	"change_decision.py": """import frappe
from erp_ai.erp_ai_agent.doctype.erp_ai_change_proposal import erp_ai_change_proposal as proposal_form

DECIDERS = {"approve": proposal_form.approve}


@frappe.whitelist(methods=["POST"])
def decide(name=None, action=None):
	return DECIDERS[action](name)


def helper(name):
	return proposal_form.reject(name)
""",
}

CHANGE_LINK_CLEAN = {
	CHANGE_LINK_FILE: '''"""Links open the form; the old /api/method/ link is gone."""

FORM_ROUTE = "/app/erp-ai-change-proposal"


def decision_path(name, query):
	return f"{FORM_ROUTE}/{name}?{query}"
''',
	"ticket_panel.py": 'PANEL_URL = "/api/method/erp_ai.ticket_panel.get_panel_data"\n',
}

GRANT_CLEAN = {
	REGISTRY_FILE: f"""import importlib

{TOOL_MODULES_NAME} = ("erp_ai.agent.tools.read",)
{GRANT_TABLE_NAME} = (("read", lambda level: True),)


def {SPEC_SOURCE}():
	return [spec for name in {TOOL_MODULES_NAME} for spec in importlib.import_module(name).TOOLS]


def _granted_specs(level):
	groups = [g for g, c in {GRANT_TABLE_NAME} if c(level)]
	return [spec for spec in {SPEC_SOURCE}() if spec.group in groups]


def {SCHEMA_FUNCTION}(level):
	return _granted_specs(level)


def execute_tool(name, arguments, context):
	granted = _granted_specs(context.effective_level)
	return next(spec for spec in granted if spec.name == name)
""",
	RUNNER_FILE: f"""from erp_ai.agent.tools.registry import grant


def run(inputs):
	granted = grant(inputs)
	return granted.{RUNNER_SCHEMA_CALL}()
""",
	QUEUE_FILE: "from erp_ai.agent.tools import registry\n",
}

AGENT_WRITE_CLEAN = {
	AGENT_WRITE_GUARD_FILE: f'''"""`{AGENT_WRITE_FLAG_NAME}` is set by `{AGENT_WRITE_OPENER}()` only."""

import frappe

__all__ = ["{AGENT_WRITE_OPENER}", "refuse_agent_write"]
{AGENT_WRITE_FLAG_NAME} = "erp_ai_agent_write_allowed"


def {AGENT_WRITE_OPENER}():
	frappe.flags[{AGENT_WRITE_FLAG_NAME}] = True


def refuse_agent_write(doc):
	return frappe.flags.get({AGENT_WRITE_FLAG_NAME})
''',
	RUN_LOG_FILE: f"""from erp_ai.agent.agent_write_guard import {AGENT_WRITE_OPENER}


def write_entry():
	with {AGENT_WRITE_OPENER}():
		pass
""",
	PROPOSE_TOOL_FILE: f"""from erp_ai.agent import agent_write_guard as guard


def propose():
	with guard.{AGENT_WRITE_OPENER}():
		pass
""",
	"erp_ai_agent/doctype/erp_ai_log/erp_ai_log.py": """from erp_ai.agent.agent_write_guard import refuse_agent_write


def validate(doc):
	refuse_agent_write(doc)
""",
}


# ---------------------------------------------------------------------------------------------------
# CHG-002 change-block rules (design §8.2; addendum-3 RQ-8: own block, own class, self-checks inside)
# ---------------------------------------------------------------------------------------------------

SETSID_TEXT = "setsid"
SETSID_EXECUTABLE_NAME = "SETSID_EXECUTABLE"
RESTART_ARGV_NAME = "RESTART_ARGV"
RESTART_STREAMS = ("stdin", "stdout", "stderr")
RESTART_REQUIRED_KEYWORDS = ("timeout", "cwd")
PRIVILEGE_COMMANDS = ("sudo", "supervisorctl")


def _command_tokens(text: str) -> list:
	"""Words of a string as a command sees them: `"/usr/bin/sudo -n"` -> ["usr", "bin", "sudo", "-n"];
	shell quotes and metacharacters split too: `"x||'sudo' $(y)"` -> ["x", "sudo", "y"]."""
	return [token for token in re.split(r"[^\w.-]+", text) if token]


def _code_strings(tree: ast.AST):
	"""`(node, text)` for every str or bytes constant of the code (bytes decoded), f-string pieces
	included, docstrings excluded."""
	docstrings = _docstring_ids(tree)
	for node in ast.walk(tree):
		if not isinstance(node, ast.Constant) or id(node) in docstrings:
			continue
		if isinstance(node.value, str):
			yield node, node.value
		elif isinstance(node.value, bytes):
			yield node, node.value.decode("utf-8", "replace")


def _is_named(node, name: str) -> bool:
	"""`name` or `<anything>.name`."""
	return (isinstance(node, ast.Name) and node.id == name) or (
		isinstance(node, ast.Attribute) and node.attr == name
	)


def _module_value(tree: ast.AST, name: str):
	for node in tree.body:
		if isinstance(node, ast.Assign) and any(_is_named(target, name) for target in node.targets):
			return node.value
	return None


def _is_none(node) -> bool:
	return isinstance(node, ast.Constant) and node.value is None


ARGV_COPIERS = ("list", "tuple")


def _is_restart_argv(node) -> bool:
	"""`RESTART_ARGV`, `list(RESTART_ARGV)`, `tuple(RESTART_ARGV)` or `[*RESTART_ARGV, ...]`."""
	if _is_named(node, RESTART_ARGV_NAME):
		return True
	if isinstance(node, ast.Call) and dotted_name(node.func) in ARGV_COPIERS and node.args:
		return _is_restart_argv(node.args[0])
	if isinstance(node, ast.List | ast.Tuple):
		return any(isinstance(elt, ast.Starred) and _is_restart_argv(elt.value) for elt in node.elts)
	return False


def restart_launch_calls(tree: ast.AST) -> list:
	"""Calls whose argv (first argument or `args=`) is `RESTART_ARGV` (or `<module>.RESTART_ARGV`),
	a `list()`/`tuple()` copy of it or a literal unpacking it; the copy calls themselves are not launches."""
	calls = []
	for node in ast.walk(tree):
		if not isinstance(node, ast.Call) or dotted_name(node.func) in ARGV_COPIERS:
			continue
		argv = node.args[0] if node.args else next((k.value for k in node.keywords if k.arg == "args"), None)
		if argv is not None and _is_restart_argv(argv):
			calls.append(node)
	return calls


def _restart_launch_violations(rel: str, call: ast.Call) -> list:
	keywords = {keyword.arg: keyword.value for keyword in call.keywords if keyword.arg}
	found = [
		violation(rel, call, f"restart launch lacks {stream}=DEVNULL (ADR-040 QĐ 7)")
		for stream in RESTART_STREAMS
		if (dotted_name(keywords.get(stream)) or "").rsplit(".", 1)[-1] != "DEVNULL"
	]
	found.extend(
		violation(rel, call, f"restart launch lacks {name}= (ADR-040 QĐ 7)")
		for name in RESTART_REQUIRED_KEYWORDS
		if name not in keywords or _is_none(keywords[name])
	)
	env = keywords.get("env")
	if env is None or _is_none(env):
		found.append(
			violation(rel, call, "restart launch lacks env= and would inherit os.environ (ADR-040 QĐ 7)")
		)
	elif any(
		dotted_name(node) == "os.environ" or (isinstance(node, ast.Name) and node.id == "environ")
		for node in ast.walk(env)
	):
		found.append(
			violation(rel, call, "restart launch passes os.environ as env= (ADR-040 QĐ 7: minimal env)")
		)
	return found


def check_change_block_restart_launch_shape(sources: dict) -> list:
	"""A-5, ADR-040 QĐ 7: `"setsid"` is written once, as `source.SETSID_EXECUTABLE`; that name is used once,
	as element 0 of `process_runner.RESTART_ARGV`; every launch of `RESTART_ARGV` has stdin, stdout and
	stderr DEVNULL, `timeout=`, `cwd=` and an `env=` that is not `os.environ`."""
	trees = {rel: parse(rel, src) for rel, src in only_python(sources).items()}
	missing = [rel for rel in (SOURCE_TOOL_FILE, PROCESS_RUNNER_FILE) if rel not in trees]
	if missing:
		return [f"{rel}: file missing" for rel in missing]
	violations = []
	setsid_value = _module_value(trees[SOURCE_TOOL_FILE], SETSID_EXECUTABLE_NAME)
	if not (isinstance(setsid_value, ast.Constant) and setsid_value.value == SETSID_TEXT):
		violations.append(
			f"{SOURCE_TOOL_FILE}: {SETSID_EXECUTABLE_NAME} is not the constant {SETSID_TEXT!r} (A-5)"
		)
	argv = _module_value(trees[PROCESS_RUNNER_FILE], RESTART_ARGV_NAME)
	first = argv.elts[0] if isinstance(argv, ast.Tuple | ast.List) and argv.elts else None
	if not _is_named(first, SETSID_EXECUTABLE_NAME):
		violations.append(
			f"{PROCESS_RUNNER_FILE}: element 0 of {RESTART_ARGV_NAME} is not {SETSID_EXECUTABLE_NAME} (A-5)"
		)
	launches = 0
	for rel, tree in trees.items():
		for node, text in _code_strings(tree):
			if SETSID_TEXT in _command_tokens(text) and node is not setsid_value:
				text = f"{SETSID_TEXT!r} written outside {SOURCE_TOOL_FILE} {SETSID_EXECUTABLE_NAME} (A-5)"
				violations.append(violation(rel, node, text))
		for node in ast.walk(tree):
			if (
				_is_named(node, SETSID_EXECUTABLE_NAME)
				and not isinstance(node.ctx, ast.Store)
				and node is not first
			):
				text = f"{SETSID_EXECUTABLE_NAME} used outside element 0 of {RESTART_ARGV_NAME} (A-5: one argv use)"
				violations.append(violation(rel, node, text))
		for call in restart_launch_calls(tree):
			launches += 1
			violations.extend(_restart_launch_violations(rel, call))
	if not launches:
		violations.append(f"{PROCESS_RUNNER_FILE}: {RESTART_ARGV_NAME} is never launched (ADR-040 QĐ 7)")
	return violations


def check_change_block_no_sudo_or_supervisorctl_argv(sources: dict) -> list:
	"""Design §8.2, AC-45: no string of the product code holds the command `sudo` or `supervisorctl`."""
	violations = []
	for rel, src in only_python(sources).items():
		for node, text in _code_strings(parse(rel, src)):
			tokens = _command_tokens(text)
			violations.extend(
				violation(
					rel, node, f"{command!r} in product code (design §8.2, AC-45: no sudo, no supervisorctl)"
				)
				for command in PRIVILEGE_COMMANDS
				if command in tokens
			)
	return violations


RESTART_LAUNCH_CLEAN = {
	SOURCE_TOOL_FILE: '''"""Server-fixed executables; `setsid` detaches `bench restart` (A-5)."""
TIMEOUT_EXECUTABLE = "timeout"
BENCH_EXECUTABLE = "bench"
SETSID_EXECUTABLE = "setsid"
''',
	PROCESS_RUNNER_FILE: '''"""Starts bench and git; never through sudo or supervisorctl."""
import os
import subprocess

import frappe

from erp_ai.agent.tools import source

RESTART_ARGV = (source.SETSID_EXECUTABLE, "-f", source.TIMEOUT_EXECUTABLE, "-s", "KILL", "1500", source.BENCH_EXECUTABLE, "restart")


def _minimal_env():
	return {name: os.environ[name] for name in ("PATH", "HOME") if name in os.environ}


def launch_restart():
	return subprocess.run(
		RESTART_ARGV,
		cwd=frappe.utils.get_bench_path(),
		env=_minimal_env(),
		stdin=subprocess.DEVNULL,
		stdout=subprocess.DEVNULL,
		stderr=subprocess.DEVNULL,
		timeout=30,
		start_new_session=True,
	)
''',
	"agent/changes/apply_job.py": '''"""Runs the approved block; asks process_runner to restart."""
from erp_ai.agent.changes import process_runner


def restart_after_apply():
	return process_runner.launch_restart()
''',
}
RESTART_JOB_FILE = "agent/changes/apply_job.py"
FS_WRITE_OS_FUNCTIONS = (
	"os.mkdir",
	"os.makedirs",
	"os.rmdir",
	"os.rename",
	"os.replace",
	"os.remove",
	"os.unlink",
)


class TestChangeBlockRules(unittest.TestCase):
	"""CHG-002 rules on the product, then each rule's self-checks on samples (addendum-3 RQ-8)."""

	@classmethod
	def setUpClass(cls):
		cls.sources = load_product_sources()

	def assertCaught(self, violations, *fragments):
		self.assertGreater(len(violations), 0, "scanner missed the violation")
		for fragment in fragments:
			self.assertTrue(any(fragment in text for text in violations), f"{fragment!r} not in {violations}")

	def restart_product(self, rel: str, extra: str = "", replace: tuple = ()) -> dict:
		"""RESTART_LAUNCH_CLEAN with `replace=(old, new)` applied to `rel` and `extra` appended."""
		text = RESTART_LAUNCH_CLEAN.get(rel, "")
		if replace:
			self.assertIn(replace[0], text)
			text = text.replace(*replace)
		return {**RESTART_LAUNCH_CLEAN, rel: text + extra}

	# T47: restart launch shape, no sudo (AC-57, AC-45; A-5; ADR-040 QĐ 7) ------------------------

	def test_restart_launch_shape(self):
		for rel in (SOURCE_TOOL_FILE, PROCESS_RUNNER_FILE):
			self.assertIn(rel, self.sources)
		# Not a blind scan: the real `"setsid"` and the real launch call are seen.
		setsid_texts = [
			(rel, text)
			for rel, src in only_python(self.sources).items()
			for _node, text in _code_strings(parse(rel, src))
			if SETSID_TEXT in _command_tokens(text)
		]
		self.assertEqual(setsid_texts, [(SOURCE_TOOL_FILE, SETSID_TEXT)])
		runner = parse(PROCESS_RUNNER_FILE, self.sources[PROCESS_RUNNER_FILE])
		self.assertEqual(len(restart_launch_calls(runner)), 1)
		self.assertEqual(check_change_block_restart_launch_shape(self.sources), [])

	def test_no_sudo_or_supervisorctl_argv(self):
		self.assertIn(PROCESS_RUNNER_FILE, self.sources)
		self.assertEqual(check_change_block_no_sudo_or_supervisorctl_argv(self.sources), [])

	def test_restart_rules_pass_on_the_clean_sample(self):
		self.assertEqual(check_change_block_restart_launch_shape(RESTART_LAUNCH_CLEAN), [])
		# A docstring may name sudo; a word holding the letters is not the command.
		clean = self.restart_product(RESTART_JOB_FILE, extra='\nLABEL = "pseudo-restart"\n')
		self.assertEqual(check_change_block_no_sudo_or_supervisorctl_argv(clean), [])

	def test_restart_launch_shape_caught(self):
		run = PROCESS_RUNNER_FILE
		cases = {
			"stdin not DEVNULL": (run, "", ("\t\tstdin=subprocess.DEVNULL,\n", ""), "stdin=DEVNULL"),
			"stdout not DEVNULL": (run, "", ("\t\tstdout=subprocess.DEVNULL,\n", ""), "stdout=DEVNULL"),
			"stderr not DEVNULL": (run, "", ("\t\tstderr=subprocess.DEVNULL,\n", ""), "stderr=DEVNULL"),
			"stdout PIPE": (
				run,
				"",
				("stdout=subprocess.DEVNULL", "stdout=subprocess.PIPE"),
				"stdout=DEVNULL",
			),
			"no timeout=": (run, "", ("\t\ttimeout=30,\n", ""), "timeout="),
			"timeout=None": (run, "", ("timeout=30", "timeout=None"), "timeout="),
			"no cwd=": (run, "", ("\t\tcwd=frappe.utils.get_bench_path(),\n", ""), "cwd="),
			"no env=": (run, "", ("\t\tenv=_minimal_env(),\n", ""), "lacks env="),
			"env=None": (run, "", ("env=_minimal_env()", "env=None"), "lacks env="),
			"env=os.environ": (run, "", ("env=_minimal_env()", "env=os.environ"), "os.environ"),
			"env copies os.environ": (run, "", ("env=_minimal_env()", "env={**os.environ}"), "os.environ"),
			"env=dict(os.environ)": (run, "", ("env=_minimal_env()", "env=dict(os.environ)"), "os.environ"),
			"setsid rewritten in another file": (
				RESTART_JOB_FILE,
				'\nARGV = ["setsid", "-f", "bench", "restart"]\n',
				(),
				f"{RESTART_JOB_FILE}:8: 'setsid' written outside",
			),
			"setsid inside a command string": (
				RESTART_JOB_FILE,
				'\nCOMMAND = "setsid -f bench restart"\n',
				(),
				"'setsid' written outside",
			),
			"setsid glued to ||": (
				RESTART_JOB_FILE,
				'\nCOMMAND = "bench restart||setsid -f bench restart"\n',
				(),
				"'setsid' written outside",
			),
			"setsid glued to ;": (
				RESTART_JOB_FILE,
				'\nCOMMAND = "x;setsid -f y"\n',
				(),
				"'setsid' written outside",
			),
			"setsid inside $(": (
				RESTART_JOB_FILE,
				'\nCOMMAND = "$(setsid -f y)"\n',
				(),
				"'setsid' written outside",
			),
			"setsid quoted": (
				RESTART_JOB_FILE,
				"\nCOMMAND = \"'setsid' -f bench restart\"\n",
				(),
				"'setsid' written outside",
			),
			"setsid bytes argv": (
				RESTART_JOB_FILE,
				'\nARGV = [b"setsid", b"-f", b"bench", b"restart"]\n',
				(),
				f"{RESTART_JOB_FILE}:8: 'setsid' written outside",
			),
			"setsid literal in RESTART_ARGV": (
				run,
				"",
				("(source.SETSID_EXECUTABLE, ", '("setsid", '),
				f"{run}:9: 'setsid' written outside",
			),
			"SETSID_EXECUTABLE not 'setsid'": (
				SOURCE_TOOL_FILE,
				"",
				('SETSID_EXECUTABLE = "setsid"', 'SETSID_EXECUTABLE = "/usr/bin/setsid"'),
				"is not the constant 'setsid'",
			),
			"SETSID_EXECUTABLE missing from source.py": (
				SOURCE_TOOL_FILE,
				"",
				('SETSID_EXECUTABLE = "setsid"\n', ""),
				"is not the constant 'setsid'",
			),
			"SETSID_EXECUTABLE defined outside source.py": (
				RESTART_JOB_FILE,
				'\nSETSID_EXECUTABLE = "setsid"\n',
				(),
				f"{RESTART_JOB_FILE}:8: 'setsid' written outside",
			),
			"SETSID_EXECUTABLE not element 0": (
				run,
				"",
				(
					'(source.SETSID_EXECUTABLE, "-f", source.TIMEOUT_EXECUTABLE,',
					'(source.TIMEOUT_EXECUTABLE, "-f", source.SETSID_EXECUTABLE,',
				),
				"element 0 of RESTART_ARGV is not SETSID_EXECUTABLE",
			),
			"SETSID_EXECUTABLE used twice": (
				run,
				'\nOTHER_ARGV = (source.SETSID_EXECUTABLE, "bench")\n',
				(),
				"SETSID_EXECUTABLE used outside element 0",
			),
			"SETSID_EXECUTABLE used in another file": (
				RESTART_JOB_FILE,
				'\nfrom erp_ai.agent.tools.source import SETSID_EXECUTABLE\nARGV = [SETSID_EXECUTABLE, "bench"]\n',
				(),
				f"{RESTART_JOB_FILE}:9: SETSID_EXECUTABLE used outside element 0",
			),
			"RESTART_ARGV never launched": (
				run,
				"",
				("\t\tRESTART_ARGV,\n", "\t\tlist(source.BENCH_EXECUTABLE),\n"),
				"RESTART_ARGV is never launched",
			),
			"second launch without DEVNULL": (
				RESTART_JOB_FILE,
				"\nimport subprocess\nsubprocess.run(process_runner.RESTART_ARGV, timeout=5)\n",
				(),
				f"{RESTART_JOB_FILE}:9: restart launch lacks stdin=DEVNULL",
			),
			"second launch via args=": (
				RESTART_JOB_FILE,
				"\nimport subprocess\nsubprocess.run(args=process_runner.RESTART_ARGV, timeout=5)\n",
				(),
				f"{RESTART_JOB_FILE}:9: restart launch lacks stdin=DEVNULL",
			),
			"second launch via list()": (
				RESTART_JOB_FILE,
				"\nimport subprocess\nsubprocess.run(list(process_runner.RESTART_ARGV), timeout=5)\n",
				(),
				f"{RESTART_JOB_FILE}:9: restart launch lacks stdin=DEVNULL",
			),
			"second launch via [*]": (
				RESTART_JOB_FILE,
				"\nimport subprocess\nsubprocess.run([*process_runner.RESTART_ARGV, '-v'], timeout=5)\n",
				(),
				f"{RESTART_JOB_FILE}:9: restart launch lacks stdin=DEVNULL",
			),
		}
		for case, (rel, extra, replace, fragment) in cases.items():
			with self.subTest(case=case):
				found = check_change_block_restart_launch_shape(self.restart_product(rel, extra, replace))
				self.assertCaught(found, fragment)
		missing = {SOURCE_TOOL_FILE: RESTART_LAUNCH_CLEAN[SOURCE_TOOL_FILE]}
		self.assertCaught(
			check_change_block_restart_launch_shape(missing), PROCESS_RUNNER_FILE, "file missing"
		)

	def test_sudo_or_supervisorctl_caught(self):
		cases = {
			"sudo argv": (PROCESS_RUNNER_FILE, '\nARGV = ["sudo", "bench", "restart"]\n', "'sudo'"),
			"supervisorctl argv": (
				PROCESS_RUNNER_FILE,
				'\nARGV = ("supervisorctl", "restart", "all")\n',
				"'supervisorctl'",
			),
			"sudo path in another file": (RESTART_JOB_FILE, '\nSUDO = "/usr/bin/sudo"\n', "'sudo'"),
			"command string": (
				RESTART_JOB_FILE,
				'\nCOMMAND = "sudo supervisorctl restart all"\n',
				"'supervisorctl'",
			),
			"f-string": (RESTART_JOB_FILE, '\nCOMMAND = f"sudo {name}"\n', "'sudo'"),
			"glued to ||": (RESTART_JOB_FILE, '\nCOMMAND = "bench restart||sudo bench restart"\n', "'sudo'"),
			"glued to ;": (
				RESTART_JOB_FILE,
				'\nCOMMAND = "x;supervisorctl restart all"\n',
				"'supervisorctl'",
			),
			"inside $(": (RESTART_JOB_FILE, '\nCOMMAND = "$(sudo x)"\n', "'sudo'"),
			"quoted": (RESTART_JOB_FILE, "\nCOMMAND = \"'sudo' bench restart\"\n", "'sudo'"),
			"bytes argv": (
				PROCESS_RUNNER_FILE,
				'\nARGV = [b"sudo", b"supervisorctl", b"restart", b"all"]\n',
				"'supervisorctl'",
			),
		}
		for case, (rel, extra, fragment) in cases.items():
			with self.subTest(case=case):
				found = check_change_block_no_sudo_or_supervisorctl_argv(self.restart_product(rel, extra))
				self.assertCaught(found, rel, fragment)

	# T48: file system writes only in file_writer; the bench table (AC-47, AC-52; ADR-040 QĐ 6) -------

	def test_fs_write_os_functions_caught_outside_file_writer(self):
		for function in FS_WRITE_OS_FUNCTIONS:
			for rel in (RESTART_JOB_FILE, PROCESS_RUNNER_FILE, PROPOSE_TOOL_FILE, CHANGE_GUARD_FILE):
				with self.subTest(function=function, rel=rel):
					source = f"import os\n{function}(path)\n"
					self.assertCaught(check_fs_writes_only_in_file_writer({rel: source}), rel, function)
			with self.subTest(function=function, rel=FILE_WRITER_FILE):
				writer = {FILE_WRITER_FILE: f"import os\n{function}(path)\n"}
				self.assertEqual(check_fs_writes_only_in_file_writer(writer), [])

	def bench_table(self, table: str, site_commands: str = "") -> dict:
		"""GIT_CLEAN with change_guard's `BENCH_COMMANDS = ...` line (and `SITE_COMMANDS`, if given) replaced."""
		text, count = re.subn(
			r"^BENCH_COMMANDS = .*$", f"BENCH_COMMANDS = {table}", GIT_CLEAN[CHANGE_GUARD_FILE], flags=re.M
		)
		self.assertEqual(count, 1)
		if site_commands:
			text, count = re.subn(
				r"^SITE_COMMANDS = .*$", f"SITE_COMMANDS = {site_commands}", text, flags=re.M
			)
			self.assertEqual(count, 1)
		return {**GIT_CLEAN, CHANGE_GUARD_FILE: text}

	def test_bench_table_with_restart_is_clean(self):
		clean = self.bench_table('(*SITE_COMMANDS, BUILD_COMMAND, "version", "restart")')
		self.assertEqual(check_bench_allowlist_has_no_git_running_subcommands(clean), [])

	def test_bench_table_without_restart_caught(self):
		found = check_bench_allowlist_has_no_git_running_subcommands(
			self.bench_table('(*SITE_COMMANDS, BUILD_COMMAND, "version")')
		)
		self.assertCaught(found, CHANGE_GUARD_FILE, "lacks 'restart'", "ADR-040 QĐ 6")

	def test_bench_table_with_forbidden_command_caught(self):
		for command in FORBIDDEN_BENCH_COMMANDS:
			for case, table, site_commands in (
				("table", f'(*SITE_COMMANDS, BUILD_COMMAND, "version", "restart", "{command}")', ""),
				("site list", '(*SITE_COMMANDS, "restart")', f'("migrate", "{command}")'),
			):
				with self.subTest(command=command, case=case):
					found = check_bench_allowlist_has_no_git_running_subcommands(
						self.bench_table(table, site_commands)
					)
					self.assertCaught(found, CHANGE_GUARD_FILE, f"holds {command!r}", "ADR-040 QĐ 6")
					self.assertFalse(any("lacks 'restart'" in text for text in found), found)

	def test_bench_table_without_restart_and_with_forbidden_command_reports_both(self):
		found = check_bench_allowlist_has_no_git_running_subcommands(
			self.bench_table('(*SITE_COMMANDS, "execute")')
		)
		self.assertCaught(found, "lacks 'restart'", "holds 'execute'")


LOCK_HELPER_FILE = "agent/tools/write_ticket.py"
LOCK_HELPER = "locked_rows"
LOCK_HELPER_READS = ("get_value", "get_values")


def _locks(keyword: ast.keyword) -> bool:
	"""`for_update=<anything but the constant False>`."""
	return keyword.arg == "for_update" and not (
		isinstance(keyword.value, ast.Constant) and keyword.value.value is False
	)


def check_locked_count_queries_use_for_update(sources: dict) -> list:
	"""ADR-036 QĐ 4, AD3-6 (T99): `locked_rows` of write_ticket.py first locks the ticket with
	`get_value(..., for_update=True)`, then reads with `get_values(..., for_update=True)`; no other code of the
	file has `for_update`, so every locked read of the module goes through it."""
	if LOCK_HELPER_FILE not in sources:
		return [f"{LOCK_HELPER_FILE}: file missing"]
	tree = parse(LOCK_HELPER_FILE, sources[LOCK_HELPER_FILE])
	helpers = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == LOCK_HELPER]
	if len(helpers) != 1:
		return [f"{LOCK_HELPER_FILE}: no single top-level {LOCK_HELPER} (AD3-6)"]
	(helper,) = helpers
	locked_calls = sorted(
		(
			node
			for node in ast.walk(helper)
			if isinstance(node, ast.Call)
			and isinstance(node.func, ast.Attribute)
			and any(_locks(keyword) for keyword in node.keywords)
		),
		key=lambda node: (node.lineno, node.col_offset),
	)
	violations = []
	if [call.func.attr for call in locked_calls] != list(LOCK_HELPER_READS):
		text = (
			f"{LOCK_HELPER} must lock the ticket with get_value(..., for_update=True), then read with "
			"get_values(..., for_update=True) (ADR-036 QĐ 4)"
		)
		violations.append(violation(LOCK_HELPER_FILE, helper, text))
	inside = {id(node) for node in ast.walk(helper)}
	violations.extend(
		violation(LOCK_HELPER_FILE, node, f"for_update outside {LOCK_HELPER} (AD3-6: the one locking place)")
		for node in ast.walk(tree)
		if isinstance(node, ast.keyword) and _locks(node) and id(node) not in inside
	)
	return violations


LOCK_HELPER_CLEAN = """def locked_rows(ticket_name, doctype, filters, fields=("name",)):
	if not frappe.db.get_value("HD Ticket", ticket_name, "name", for_update=True):
		raise ValueError("phiếu không có")
	return frappe.db.get_values(doctype, filters, list(fields), as_dict=True, for_update=True)


def locked_count(ticket_name, doctype, filters):
	return len(locked_rows(ticket_name, doctype, filters))
"""


class TestTicketLockRules(unittest.TestCase):
	"""T99 rule on the product, then its self-checks on samples."""

	@classmethod
	def setUpClass(cls):
		cls.sources = load_product_sources()

	def assertCaught(self, violations, *fragments):
		self.assertGreater(len(violations), 0, "scanner missed the violation")
		for fragment in fragments:
			self.assertTrue(any(fragment in text for text in violations), f"{fragment!r} not in {violations}")

	def lock_sample(self, replace: tuple = (), extra: str = "") -> dict:
		"""LOCK_HELPER_CLEAN with `replace=(old, new)` applied and `extra` appended, as write_ticket.py."""
		text = LOCK_HELPER_CLEAN
		if replace:
			self.assertIn(replace[0], text)
			text = text.replace(*replace)
		return {LOCK_HELPER_FILE: text + extra}

	def test_locked_count_queries_use_for_update(self):
		self.assertEqual(check_locked_count_queries_use_for_update(self.sources), [])

	def test_locked_count_rule_passes_on_the_clean_sample(self):
		self.assertEqual(check_locked_count_queries_use_for_update(self.lock_sample()), [])
		unlocked_elsewhere = self.lock_sample(
			extra="\n\ndef peek(name):\n\treturn frappe.db.get_value('HD Ticket', name, 'name', for_update=False)\n"
		)
		self.assertEqual(check_locked_count_queries_use_for_update(unlocked_elsewhere), [])

	def test_locked_count_rule_catches_each_violation(self):
		must_lock = "must lock the ticket"
		cases = {
			"file missing": ({}, "file missing"),
			"no helper": (
				self.lock_sample(("def locked_rows(", "def rows(")),
				"no single top-level locked_rows",
			),
			"read without lock": (
				self.lock_sample((", as_dict=True, for_update=True)", ", as_dict=True)")),
				must_lock,
			),
			"read with for_update=False": (
				self.lock_sample((", as_dict=True, for_update=True)", ", as_dict=True, for_update=False)")),
				must_lock,
			),
			"no ticket lock": (self.lock_sample(('"name", for_update=True)', '"name")')), must_lock),
			"read before the ticket lock": (
				self.lock_sample(
					(
						'	if not frappe.db.get_value("HD Ticket", ticket_name, "name", for_update=True):\n',
						"	frappe.db.get_values(doctype, filters, for_update=True)\n"
						'	if not frappe.db.get_value("HD Ticket", ticket_name, "name", for_update=True):\n',
					)
				),
				must_lock,
			),
			"lock in another function": (
				self.lock_sample(
					extra="\n\ndef post_notice(name):\n\treturn frappe.db.get_values('Comment', {}, for_update=True)\n"
				),
				"for_update outside locked_rows",
			),
		}
		for case, (sources, fragment) in cases.items():
			with self.subTest(case=case):
				self.assertCaught(check_locked_count_queries_use_for_update(sources), fragment)


PENDING_SECTION_NAME = "SECTION_PENDING"
# AD3-5 (T105): the guidance writer defines it, the one proposal insert function adds its lines.
PENDING_SECTION_FILES = ("agent/tools/write_ticket.py", "agent/tools/propose_change.py")


def check_section_pending_only_in_writer_and_proposal_module(sources: dict) -> list:
	"""AD3-5 (T105): the name SECTION_PENDING (a name, an attribute or an imported name) occurs only in
	write_ticket.py and propose_change.py, so no other module (the runner included) adds a "Chờ duyệt" line."""
	violations = []
	for rel, source in sources.items():
		if rel in PENDING_SECTION_FILES or not rel.endswith(".py"):
			continue
		for node in ast.walk(parse(rel, source)):
			used = (
				(isinstance(node, ast.Name) and node.id == PENDING_SECTION_NAME)
				or (isinstance(node, ast.Attribute) and node.attr == PENDING_SECTION_NAME)
				or (isinstance(node, ast.alias) and PENDING_SECTION_NAME in (node.name, node.asname))
			)
			if used:
				text = f"{PENDING_SECTION_NAME} outside write_ticket.py and propose_change.py (AD3-5)"
				violations.append(violation(rel, node, text))
	return violations


class TestGuidanceSectionRules(unittest.TestCase):
	"""T105 rule on the product, then its self-checks on samples."""

	@classmethod
	def setUpClass(cls):
		cls.sources = load_product_sources()

	def test_section_pending_only_in_writer_and_proposal_module(self):
		self.assertEqual(check_section_pending_only_in_writer_and_proposal_module(self.sources), [])

	def test_section_pending_rule_passes_on_the_clean_sample(self):
		clean = {
			"agent/tools/write_ticket.py": 'SECTION_PENDING = "Chờ duyệt"\n',
			"agent/tools/propose_change.py": (
				"from erp_ai.agent.tools.write_ticket import SECTION_PENDING, collect\n"
				"collect(run_id, SECTION_PENDING, line)\n"
			),
			# a mention in a comment or a string is no use of the name
			"agent/runner.py": '# SECTION_PENDING is the writer\'s\nNOTE = "SECTION_PENDING"\n',
		}
		self.assertEqual(check_section_pending_only_in_writer_and_proposal_module(clean), [])

	def test_section_pending_rule_catches_each_use_elsewhere(self):
		cases = {
			"attribute": "write_ticket.collect(run_id, write_ticket.SECTION_PENDING, line)\n",
			"imported": "from erp_ai.agent.tools.write_ticket import SECTION_PENDING\n",
			"imported under another name": "from erp_ai.agent.tools.write_ticket import SECTION_PENDING as P\n",
			"bare name": "collect(run_id, SECTION_PENDING, line)\n",
		}
		for case, source in cases.items():
			for rel in ("agent/runner.py", "agent/tools/catalog_tools.py"):
				with self.subTest(case=case, rel=rel):
					found = check_section_pending_only_in_writer_and_proposal_module({rel: source})
					self.assertEqual(len(found), 1, found)
					self.assertIn(f"{rel}:", found[0])
					self.assertIn("outside write_ticket.py and propose_change.py", found[0])


# ---------------------------------------------------------------------------------------------------
# ADR-036 and ADR-037 (T119, w1.md:203, AD3-3, design-w1-fixes-13 Điểm 3)
# ---------------------------------------------------------------------------------------------------

GUIDANCE_WRITER_FILE = "agent/tools/write_ticket.py"
RUNNER_FILE = "agent/runner.py"
HANDLERS_FILE = "handlers.py"
# The marker's names and its text (the key inside the HTML comment): the writer module's alone.
GUIDANCE_MARKER_NAMES = ("GUIDANCE_MARKER", "_GUIDANCE_KEY")
GUIDANCE_MARKER_TEXT = "erp_ai:huong-xu-ly"
GUIDANCE_WRITER = "post_guidance"
GUIDANCE_WRITER_CALLER = "_finish_guidance"
WRITE_TICKET_MODULE = "erp_ai.agent.tools.write_ticket"
# AD3-3: the writer module never depends on the proposal, catalog or runner modules (by their last name).
WRITE_TICKET_FORBIDDEN_MODULES = ("propose_change", "catalog", "catalog_tools", "runner")
# ADR-036 QĐ 6: no stored "already has guidance" field; the comment is the truth.
GUIDANCE_FLAG_WORDS = ("guidance", "huong")
GUIDANCE_FLAG_DOCTYPE_FILES = (
	"erp_ai_agent/doctype/erp_ai_log/erp_ai_log.json",
	"erp_ai_agent/doctype/erp_ai_setting/erp_ai_setting.json",
)
# The HD Ticket fields of the app are created from this file (install._ai_field_specs).
TICKET_FIELDS_FILE = "install.py"
_FIELDNAME = re.compile(r"[a-z][a-z0-9_]*")
# Rule A (design-w1-fixes-13 Điểm 3): every writer here counts its dedup reads through locked_count
# (T168 added "create_task", T169 "post_comment_tool").
DEDUP_WRITERS = ("post_notice", "post_guidance", "create_task", "post_comment_tool")
DEDUP_UNLOCKED_READS = (
	"frappe.db.count",
	"frappe.db.exists",
	"frappe.db.get_values",
	"frappe.db.get_all",
	"frappe.get_all",
	"frappe.get_list",
	"frappe.db.sql",
)
# Rule B (design-w1-fixes-13 Điểm 3).
ROUTE_FUNCTION = "_route"
ROUTE_LOCK_CALLS = ("locked_count", "locked_rows")
ROUTE_WRITE_CALLS = ("_record_route", "execute_tool", "set_value", "save", "insert", "db_set", "sql")
FOR_UPDATE_ALLOWED = {
	("agent/tools/write_ticket.py", "locked_rows"),
	("agent/changes/transitions.py", "_lock"),
	# these two lock the ticket row by design: U6b design step (4) for lifecycle, controller ruling R17e for kb_draft
	("agent/lifecycle.py", "_locked_status_category"),
	("agent/tools/kb_draft.py", "create_kb_draft"),
	# locks the ticket row by design: U5b design step 6.1 for the reminder job, controller ruling R30
	("agent/due_checks.py", "_lock_ticket"),
}


def _names_used(tree: ast.AST, names) -> list:
	"""Name, Attribute and import-alias nodes whose name is one of `names`."""
	return [
		node
		for node in ast.walk(tree)
		if (isinstance(node, ast.Name) and node.id in names)
		or (isinstance(node, ast.Attribute) and node.attr in names)
		or (isinstance(node, ast.alias) and ({node.name.rpartition(".")[2], node.asname} & set(names)))
	]


def _top_level_function(tree: ast.AST, name: str):
	return next(
		(
			node
			for node in tree.body
			if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and node.name == name
		),
		None,
	)


def _enclosing_functions(tree: ast.AST) -> dict:
	"""`{id(node): name of the nearest enclosing function}` for every node inside a function."""
	owner = {}

	def visit(node, function):
		for child in ast.iter_child_nodes(node):
			name = child.name if isinstance(child, ast.FunctionDef | ast.AsyncFunctionDef) else function
			if name is not None:
				owner[id(child)] = name
			visit(child, name)

	visit(tree, None)
	return owner


def check_guidance_marker_defined_once_used_only_by_writer_module(sources: dict) -> list:
	"""ADR-036 Ràng buộc: the marker is assigned exactly once, in the writer module, and spelled out only there; no
	other product module names it or writes its text."""
	violations = []
	if GUIDANCE_WRITER_FILE not in sources:
		return [f"{GUIDANCE_WRITER_FILE}: file missing"]
	writer = parse(GUIDANCE_WRITER_FILE, sources[GUIDANCE_WRITER_FILE])
	for name in GUIDANCE_MARKER_NAMES:
		assigned = [
			node
			for node in ast.walk(writer)
			if isinstance(node, ast.Assign | ast.AnnAssign)
			and any(
				isinstance(target, ast.Name) and target.id == name
				for written in (node.targets if isinstance(node, ast.Assign) else [node.target])
				for target in ast.walk(written)
			)
		]
		if len(assigned) != 1:
			violations.append(
				f"{GUIDANCE_WRITER_FILE}: {name} assigned {len(assigned)} times, not once (ADR-036)"
			)
	texts = [node for node in constant_strings(writer) if GUIDANCE_MARKER_TEXT in node.value]
	if len(texts) != 1:
		violations.append(f"{GUIDANCE_WRITER_FILE}: the marker text is written {len(texts)} times, not once")
	for rel, source in sources.items():
		if rel == GUIDANCE_WRITER_FILE or not rel.endswith(".py"):
			continue
		tree = parse(rel, source)
		for node in _names_used(tree, GUIDANCE_MARKER_NAMES):
			violations.append(violation(rel, node, "the guidance marker outside write_ticket.py (ADR-036)"))
		for node in constant_strings(tree):
			if GUIDANCE_MARKER_TEXT in node.value:
				violations.append(
					violation(rel, node, "the guidance marker text outside write_ticket.py (ADR-036)")
				)
	return violations


def check_runner_calls_post_guidance_in_one_place(sources: dict) -> list:
	"""ADR-036 QĐ 1, w1.md:105: outside its own module, the guidance writer is called exactly once, by the runner's
	`_finish_guidance`; no tool, handler, job or route step calls it."""
	calls = []
	for rel, source in sources.items():
		if rel == GUIDANCE_WRITER_FILE or not rel.endswith(".py"):
			continue
		tree = parse(rel, source)
		owners = _enclosing_functions(tree)
		calls.extend(
			(rel, node, owners.get(id(node)))
			for node in ast.walk(tree)
			if isinstance(node, ast.Call) and referenced_name(node.func) == GUIDANCE_WRITER
		)
	violations = [
		violation(
			rel, node, f"{GUIDANCE_WRITER} called outside runner.{GUIDANCE_WRITER_CALLER} (ADR-036 QĐ 1)"
		)
		for rel, node, owner in calls
		if (rel, owner) != (RUNNER_FILE, GUIDANCE_WRITER_CALLER)
	]
	if len(calls) != 1:
		violations.append(
			f"{RUNNER_FILE}: {GUIDANCE_WRITER} called {len(calls)} times, not once (ADR-036 QĐ 1)"
		)
	return violations


def check_dedup_reads_go_through_locked_count(sources: dict) -> list:
	"""Rule A (ADR-036 QĐ 4, design-w1-fixes-13 Điểm 3): each DEDUP_WRITERS function of write_ticket.py reads through
	`locked_count` or `count_guidance(..., lock=True)`, never with its own read or lock."""
	if GUIDANCE_WRITER_FILE not in sources:
		return []
	tree = parse(GUIDANCE_WRITER_FILE, sources[GUIDANCE_WRITER_FILE])
	violations = []
	for name in DEDUP_WRITERS:
		function = _top_level_function(tree, name)
		if function is None:
			violations.append(f"{GUIDANCE_WRITER_FILE}: {name}: không thấy hàm")
			continue
		calls = [node for node in ast.walk(function) if isinstance(node, ast.Call)]
		locked = any(
			referenced_name(call.func) == "locked_count"
			or (
				referenced_name(call.func) == "count_guidance"
				and any(
					keyword.arg == "lock"
					and isinstance(keyword.value, ast.Constant)
					and keyword.value.value is True
					for keyword in call.keywords
				)
			)
			for call in calls
		)
		if not locked:
			text = f"{name}: no locked_count(...) or count_guidance(..., lock=True) (ADR-036 QĐ 4)"
			violations.append(violation(GUIDANCE_WRITER_FILE, function, text))
		for call in calls:
			if dotted_name(call.func) in DEDUP_UNLOCKED_READS:
				text = f"{name}: own read {dotted_name(call.func)} instead of locked_count (ADR-036 QĐ 4)"
				violations.append(violation(GUIDANCE_WRITER_FILE, call, text))
		violations.extend(
			violation(
				GUIDANCE_WRITER_FILE, node, f"{name}: own for_update instead of locked_count (ADR-036 QĐ 4)"
			)
			for node in ast.walk(function)
			if isinstance(node, ast.keyword) and node.arg == "for_update"
		)
	return violations


def check_handlers_do_not_import_write_ticket(sources: dict) -> list:
	"""ADR-036 Ràng buộc, ADR-033 QĐ 2: the handlers only queue runs; they never import the guidance writer module."""
	if HANDLERS_FILE not in sources:
		return []
	tree = parse(HANDLERS_FILE, sources[HANDLERS_FILE])
	return [
		f"{HANDLERS_FILE}:{line}: imports {module} (ADR-036: the handlers do not read the guidance)"
		for line, module in imported_modules(tree, module_name(HANDLERS_FILE), False)
		if module_in(module, WRITE_TICKET_MODULE)
	]


def check_write_ticket_imports_no_proposal_or_catalog_module(sources: dict) -> list:
	"""AD3-3: write_ticket.py imports no proposal, catalog or runner module; they call it, never the other way."""
	if GUIDANCE_WRITER_FILE not in sources:
		return []
	tree = parse(GUIDANCE_WRITER_FILE, sources[GUIDANCE_WRITER_FILE])
	return [
		f"{GUIDANCE_WRITER_FILE}:{line}: imports {module} (AD3-3)"
		for line, module in imported_modules(tree, module_name(GUIDANCE_WRITER_FILE), False)
		if module.rpartition(".")[2] in WRITE_TICKET_FORBIDDEN_MODULES
	]


def check_no_guidance_flag_field(sources: dict) -> list:
	"""ADR-036 QĐ 6: no field named for the guidance on ERP AI Log or ERP AI Setting (their DocType JSON) or on HD
	Ticket (the field names install.py creates). `sources` holds the JSON files too."""
	violations = []
	for rel in GUIDANCE_FLAG_DOCTYPE_FILES:
		if rel not in sources:
			violations.append(f"{rel}: file missing")
			continue
		for field in json.loads(sources[rel]).get("fields", []):
			name = field.get("fieldname") or ""
			if any(word in name for word in GUIDANCE_FLAG_WORDS):
				violations.append(f"{rel}: field {name} (ADR-036 QĐ 6: no guidance flag)")
	if TICKET_FIELDS_FILE in sources:
		for node in constant_strings(parse(TICKET_FIELDS_FILE, sources[TICKET_FIELDS_FILE])):
			if _FIELDNAME.fullmatch(node.value) and any(word in node.value for word in GUIDANCE_FLAG_WORDS):
				text = f"HD Ticket field {node.value} (ADR-036 QĐ 6: no guidance flag)"
				violations.append(violation(TICKET_FIELDS_FILE, node, text))
	return violations


def check_route_locks_ticket_before_first_write_unit(sources: dict) -> list:
	"""Rule B (ADR-037 Ràng buộc, design-w1-fixes-13 Điểm 3). (B1) `_route` of runner.py calls locked_count or
	locked_rows before its first write unit, and has one. (B2) no `for_update` other than False in a product module,
	but in the two places FOR_UPDATE_ALLOWED names."""
	violations = []
	if RUNNER_FILE in sources:
		function = _top_level_function(parse(RUNNER_FILE, sources[RUNNER_FILE]), ROUTE_FUNCTION)
		calls = [node for node in ast.walk(function) if isinstance(node, ast.Call)] if function else []
		where = lambda node: (node.lineno, node.col_offset)  # noqa: E731
		locks = sorted((call for call in calls if referenced_name(call.func) in ROUTE_LOCK_CALLS), key=where)
		writes = sorted(
			(
				call
				for call in calls
				if (referenced_name(call.func) or "").endswith("_unit")
				or referenced_name(call.func) in ROUTE_WRITE_CALLS
			),
			key=where,
		)
		if function is None or not writes:
			violations.append(
				f"{RUNNER_FILE}: {ROUTE_FUNCTION} has no write unit (the rule must not hold empty)"
			)
		elif not locks:
			violations.append(
				violation(RUNNER_FILE, function, f"{ROUTE_FUNCTION} never locks the ticket (ADR-037 QĐ 4)")
			)
		elif where(locks[0]) >= where(writes[0]):
			text = f"{ROUTE_FUNCTION} writes before it locks the ticket (ADR-037 QĐ 4)"
			violations.append(violation(RUNNER_FILE, writes[0], text))
	for rel, source in sources.items():
		if not rel.endswith(".py") or Path(rel).name.startswith("test_"):
			continue
		tree = parse(rel, source)
		owners = _enclosing_functions(tree)
		violations.extend(
			violation(rel, node, "for_update outside locked_rows and transitions._lock (ADR-037 Ràng buộc)")
			for node in ast.walk(tree)
			if isinstance(node, ast.keyword)
			and _locks(node)
			and (rel, owners.get(id(node))) not in FOR_UPDATE_ALLOWED
		)
	return violations


class TestGuidanceArchitectureRules(unittest.TestCase):
	"""T119: the rules of ADR-036 and ADR-037 on the product, then each one's red and green samples."""

	@classmethod
	def setUpClass(cls):
		cls.sources = load_product_sources()
		cls.with_json = load_product_sources(suffixes=(".py", ".json"))

	def assertCaught(self, violations, *fragments):
		self.assertGreater(len(violations), 0, "scanner missed the violation")
		for fragment in fragments:
			self.assertTrue(any(fragment in text for text in violations), f"{fragment!r} not in {violations}")

	# on the product

	def test_guidance_marker_defined_once_used_only_by_writer_module(self):
		self.assertEqual(check_guidance_marker_defined_once_used_only_by_writer_module(self.sources), [])

	def test_runner_calls_post_guidance_in_one_place(self):
		self.assertEqual(check_runner_calls_post_guidance_in_one_place(self.sources), [])

	def test_dedup_reads_go_through_locked_count(self):
		self.assertEqual(check_dedup_reads_go_through_locked_count(self.sources), [])

	def test_handlers_do_not_import_write_ticket(self):
		self.assertEqual(check_handlers_do_not_import_write_ticket(self.sources), [])

	def test_no_guidance_flag_field(self):
		self.assertEqual(check_no_guidance_flag_field(self.with_json), [])

	def test_write_ticket_imports_no_proposal_or_catalog_module(self):
		self.assertEqual(check_write_ticket_imports_no_proposal_or_catalog_module(self.sources), [])

	# samples

	W = GUIDANCE_WRITER_FILE
	R = RUNNER_FILE
	WRITER_CLEAN = (
		'_GUIDANCE_KEY = "erp_ai:huong-xu-ly"\n'
		'GUIDANCE_MARKER = f"<!-- {_GUIDANCE_KEY} -->"\n'
		"def guidance_filters(t):\n\treturn {'content': ['like', GUIDANCE_MARKER + '%']}\n"
	)

	def test_marker_rule_samples(self):
		clean = {
			self.W: self.WRITER_CLEAN,
			self.R: "from erp_ai.agent.tools.write_ticket import post_guidance\n",
		}
		self.assertEqual(check_guidance_marker_defined_once_used_only_by_writer_module(clean), [])
		cases = {
			"named in the runner": (
				{
					self.W: self.WRITER_CLEAN,
					self.R: "from erp_ai.agent.tools.write_ticket import GUIDANCE_MARKER\n",
				},
				"marker outside write_ticket.py",
			),
			"attribute in a tool": (
				{
					self.W: self.WRITER_CLEAN,
					"agent/tools/catalog_tools.py": "x = write_ticket.GUIDANCE_MARKER\n",
				},
				"marker outside write_ticket.py",
			),
			"text spelled out elsewhere": (
				{self.W: self.WRITER_CLEAN, "handlers.py": 'MARK = "<!-- erp_ai:huong-xu-ly -->"\n'},
				"marker text outside write_ticket.py",
			),
			"assigned twice": (
				{self.W: self.WRITER_CLEAN + "GUIDANCE_MARKER = '<!-- x -->'\n"},
				"GUIDANCE_MARKER assigned 2 times",
			),
			"text written twice in the writer": (
				{self.W: self.WRITER_CLEAN + "OTHER = 'erp_ai:huong-xu-ly'\n"},
				"marker text is written 2 times",
			),
		}
		for case, (sources, fragment) in cases.items():
			with self.subTest(case=case):
				self.assertCaught(
					check_guidance_marker_defined_once_used_only_by_writer_module(sources), fragment
				)

	FINISH = "def _finish_guidance(context, actions):\n\treturn post_guidance(context.ticket_name, context.run_id)\n"

	def test_post_guidance_rule_samples(self):
		self.assertEqual(check_runner_calls_post_guidance_in_one_place({self.R: self.FINISH}), [])
		cases = {
			"called twice in the runner": (
				{self.R: self.FINISH + "def _reason():\n\twrite_ticket.post_guidance(t, r)\n"},
				"outside runner._finish_guidance",
			),
			"called by a handler": (
				{
					self.R: self.FINISH,
					"handlers.py": "def on_comment(doc):\n\tpost_guidance(doc.name, 'x')\n",
				},
				"called 2 times",
			),
			"never called": ({self.R: "def _reason():\n\treturn True\n"}, "called 0 times"),
		}
		for case, (sources, fragment) in cases.items():
			with self.subTest(case=case):
				self.assertCaught(check_runner_calls_post_guidance_in_one_place(sources), fragment)

	# the samples define only the original pair, so the rule is run for that pair
	@patch(f"{__name__}.DEDUP_WRITERS", ("post_notice", "post_guidance"))
	def test_dedup_rule_samples(self):
		# design-w1-fixes-13 Điểm 3, verbatim: A0 green; A1, A2, A3 red, one violation each
		a0 = {
			self.W: "def post_notice(args, ctx):\n    if locked_count(ctx.ticket_name, 'Comment', {}):\n        return {}\n\ndef post_guidance(ctx, text):\n    if count_guidance(ctx.ticket_name, lock=True):\n        return {}\n"
		}
		a1 = {
			self.W: "def post_notice(args, ctx):\n    if frappe.db.count('Comment', {'reference_name': ctx.ticket_name}):\n        return {}\n\ndef post_guidance(ctx, text):\n    if count_guidance(ctx.ticket_name, lock=True):\n        return {}\n"
		}
		a2 = {
			self.W: "def post_notice(args, ctx):\n    if locked_count(ctx.ticket_name, 'Comment', {}):\n        return {}\n\ndef post_guidance(ctx, text):\n    if count_guidance(ctx.ticket_name):\n        return {}\n"
		}
		a3 = {
			self.W: "def post_notice(args, ctx):\n    if locked_count(ctx.ticket_name, 'Comment', {}):\n        return {}\n"
		}
		self.assertEqual(check_dedup_reads_go_through_locked_count(a0), [])
		for case, sources, name in (("A1", a1, "post_notice"), ("A2", a2, "post_guidance")):
			with self.subTest(case=case):
				found = check_dedup_reads_go_through_locked_count(sources)
				self.assertCaught(found, f"{name}:")
				# only the function at fault
				self.assertTrue(all(f"{name}:" in text for text in found), found)
		with self.subTest(case="A3"):
			self.assertEqual(
				check_dedup_reads_go_through_locked_count(a3),
				[f"{GUIDANCE_WRITER_FILE}: post_guidance: không thấy hàm"],
			)

	def test_handlers_import_rule_samples(self):
		clean = {
			"handlers.py": "from erp_ai.agent import policy\nfrom erp_ai.agent.queue import enqueue_agent_run\n"
		}
		self.assertEqual(check_handlers_do_not_import_write_ticket(clean), [])
		for source in (
			"from erp_ai.agent.tools import write_ticket\n",
			"from erp_ai.agent.tools.write_ticket import count_guidance\n",
			"import erp_ai.agent.tools.write_ticket as wt\n",
			"from .agent.tools.write_ticket import GUIDANCE_MARKER\n",
		):
			with self.subTest(source=source):
				self.assertCaught(
					check_handlers_do_not_import_write_ticket({"handlers.py": source}), "imports"
				)

	def test_write_ticket_import_rule_samples(self):
		clean = {
			self.W: "from erp_ai.agent import policy\nfrom erp_ai.agent.tools.registry import ToolContext\n"
		}
		self.assertEqual(check_write_ticket_imports_no_proposal_or_catalog_module(clean), [])
		for source in (
			"from erp_ai.agent.tools import propose_change\n",
			"from erp_ai.agent.tools.catalog_tools import record_summary\n",
			"import erp_ai.agent.catalog\n",
			"from erp_ai.agent import runner\n",
			"from . import propose_change\n",
		):
			with self.subTest(source=source):
				self.assertCaught(
					check_write_ticket_imports_no_proposal_or_catalog_module({self.W: source}), "AD3-3"
				)

	def test_guidance_flag_field_rule_samples(self):
		log, setting = GUIDANCE_FLAG_DOCTYPE_FILES

		def doctype(*names):
			return json.dumps({"fields": [{"fieldname": name} for name in names]})

		clean = {
			log: doctype("ticket", "run_id"),
			setting: doctype("enabled", "confidence_threshold"),
			"install.py": "def _ai_field_specs():\n\treturn [{'fieldname': 'ai_confidence', 'label': 'Hướng giải quyết'}]\n",
		}
		self.assertEqual(check_no_guidance_flag_field(clean), [])
		cases = {
			"log field": ({**clean, log: doctype("ticket", "guidance_posted")}, "field guidance_posted"),
			"setting field": (
				{**clean, setting: doctype("huong_xu_ly_da_dang")},
				"field huong_xu_ly_da_dang",
			),
			"ticket field": (
				{
					**clean,
					"install.py": "def _ai_field_specs():\n\treturn [{'fieldname': 'ai_guidance_posted'}]\n",
				},
				"HD Ticket field ai_guidance_posted",
			),
			"doctype file gone": ({setting: clean[setting]}, "file missing"),
		}
		for case, (sources, fragment) in cases.items():
			with self.subTest(case=case):
				self.assertCaught(check_no_guidance_flag_field(sources), fragment)

	def test_route_lock_rule_samples(self):
		# design-w1-fixes-13 Điểm 3, verbatim: B0, B2c, B2d green; B1a, B1b, B2a, B2b red, one violation each
		b0 = {
			self.R: "def _route(log_name, c, d, context, a, s):\n    frappe.db.savepoint('r')\n    if locked_count(context.ticket_name, LOG_DOCTYPE, {'applied': 1}):\n        return []\n    _apply_route_unit(d, c, context, [], [])\n"
		}
		b1a = {
			self.R: "def _route(log_name, c, d, context, a, s):\n    _apply_route_unit(d, c, context, [], [])\n    locked_count(context.ticket_name, LOG_DOCTYPE, {'applied': 1})\n"
		}
		b1b = {
			self.R: "def _route(log_name, c, d, context, a, s):\n    _apply_route_unit(d, c, context, [], [])\n"
		}
		b2a = {
			"agent/tools/read.py": "def peek(name):\n    return frappe.db.get_value('HD Ticket', name, 'name', for_update=True)\n"
		}
		b2b = {
			"agent/changes/apply_job.py": "def claim(name):\n    return frappe.db.get_value('ERP AI Change Proposal', name, 'name', for_update=True)\n"
		}
		b2c = {
			self.W: "def locked_rows(t, d, f, fields=('name',)):\n    frappe.db.get_value('HD Ticket', t, 'name', for_update=True)\n    return frappe.db.get_values(d, f, fields, as_dict=True, for_update=True)\n",
			"agent/changes/transitions.py": "def _lock(name, *extra):\n    return frappe.db.get_value('ERP AI Change Proposal', name, ['change_status'], as_dict=True, for_update=True)\n",
		}
		b2d = {
			"agent/tools/test_write_ticket.py": "def helper(name):\n    return frappe.db.get_value('HD Ticket', name, 'name', for_update=True)\n"
		}
		for case, sources in (("B0", b0), ("B2c", b2c), ("B2d", b2d)):
			with self.subTest(case=case):
				self.assertEqual(check_route_locks_ticket_before_first_write_unit(sources), [])
		for case, sources, fragment in (
			("B1a", b1a, "writes before it locks"),
			("B1b", b1b, "never locks"),
			("B2a", b2a, "agent/tools/read.py:2: for_update"),
			("B2b", b2b, "agent/changes/apply_job.py:2: for_update"),
		):
			with self.subTest(case=case):
				found = check_route_locks_ticket_before_first_write_unit(sources)
				self.assertEqual(len(found), 1, found)
				self.assertCaught(found, fragment)


# ---------------------------------------------------------------------------------------------------
# ADR-034 Ràng buộc 1-2 (FEAT-007 U2, T139, U2.md:260, :291-293): the ticket send policy is read only in policy.py,
# the record tool's read paths ask it inside the query, TICKET_LINK_FIELDS covers TICKET_CONTENT_DOCTYPES
# ---------------------------------------------------------------------------------------------------

TICKET_POLICY_FIELDS = ("excluded_teams", "ai_opt_out", "excluded_title_prefixes")
# policy.py's constants holding those names: naming one outside policy.py is a read of the field too
TICKET_POLICY_CONSTANTS = ("EXCLUDED_TEAMS_FIELD", "OPT_OUT_FIELD", "EXCLUDED_TITLE_PREFIXES_FIELD")
# the policy function that carries a field's name (`policy.excluded_title_prefixes()`): a call, not a field read
TICKET_POLICY_FUNCTIONS = ("excluded_title_prefixes",)
TICKET_POLICY_NAME = re.compile(
	r"(?<![A-Za-z0-9_])(?:excluded_teams|ai_opt_out|excluded_title_prefixes)(?![A-Za-z0-9_])"
)
# ADR-034 Ràng buộc 1: "chỉ được đọc trong policy.py (và JSON, cài đặt, test)"; JSON and tests are never scanned.
TICKET_POLICY_FILES = {
	POLICY_FILE: "the one reader: send_refusal, is_excluded_team, excluded_title_prefixes (ADR-034 QĐ 1)",
	SETTING_CONTROLLER_FILE: "the ERP AI Setting controller owns its fields",
	INSTALL_FILE: "sets up the Setting defaults and the ticket's custom fields at install",
}
TICKET_RECORD_CHECK = "is_ticket_record_excluded"
TICKET_LIST_FILTERS = "ticket_content_filters"
TICKET_LINK_FIELDS_NAME = "TICKET_LINK_FIELDS"
TICKET_CONTENT_DOCTYPES_NAME = "TICKET_CONTENT_DOCTYPES"
TICKET_DOCTYPE_NAME = "HD Ticket"
# C3b (R10b, R10g, R11a): log DocTypes that name a ticket only by a (DocType, name) pair, declared in
# TICKET_LINK_FIELDS beyond TICKET_CONTENT_DOCTYPES so the record tool filters them too. The narrowest allowance that
# keeps the U2.md:293 rule: these names may be declared; no other DocType outside TICKET_CONTENT_DOCTYPES may.
TICKET_LINK_ONLY_DOCTYPES = frozenset(
	{
		"ToDo",
		"Notification Log",
		"Activity Log",
		"Email Queue",
		"Tag Link",
		"Document Follow",
		"Workflow Action",
		"Reminder",
	}
)


def check_ticket_policy_fields_read_only_in_policy(sources: dict) -> list:
	"""ADR-034 Ràng buộc 1: outside TICKET_POLICY_FILES no Python file names a field of TICKET_POLICY_FIELDS (a name, an
	attribute, a keyword, a string, a built string) or a constant of TICKET_POLICY_CONSTANTS; the one exception is a
	policy function of TICKET_POLICY_FUNCTIONS (`policy.excluded_title_prefixes()`, or imported from policy)."""
	policy_module = module_name(POLICY_FILE)
	functions = {f"{policy_module}.{name}" for name in TICKET_POLICY_FUNCTIONS}
	flagged = {*TICKET_POLICY_FIELDS, *TICKET_POLICY_CONSTANTS}
	violations = []
	for rel, source in only_python(sources).items():
		if rel in TICKET_POLICY_FILES:
			continue
		tree = parse(rel, source)
		aliases = import_aliases(tree)
		function_imports = {
			id(alias)
			for node in ast.walk(tree)
			if isinstance(node, ast.ImportFrom) and not node.level and node.module == policy_module
			for alias in node.names
			if alias.name in TICKET_POLICY_FUNCTIONS
		}
		lines = set()
		for node in ast.walk(tree):
			if id(node) in function_imports or isinstance(node, ast.Constant):
				continue  # strings are checked below, built ones included
			if not flagged.intersection(_node_names(node)):
				continue
			if resolved_name(node, aliases) in functions:
				continue  # the policy's function, not a field read
			lines.add(node.lineno)
		lines |= {
			node.lineno
			for node, text in _string_texts(tree, _docstring_ids(tree))
			if TICKET_POLICY_NAME.search(text)
		}
		violations.extend(
			f"{rel}:{line}: names a ticket policy field outside {POLICY_FILE}; ask policy.py (ADR-034 Ràng buộc 1)"
			for line in sorted(lines)
		)
	return violations


def _policy_calls(function, name: str, aliases: dict) -> list:
	"""The calls of `policy.<name>(...)` inside `function`."""
	target = f"{module_name(POLICY_FILE)}.{name}"
	return [
		node
		for node in ast.walk(function)
		if isinstance(node, ast.Call) and resolved_name(node.func, aliases) == target
	]


def _bound_names(function, call) -> set:
	"""The names an assignment inside `function` binds to the result of `call`; empty when it binds none."""
	return {
		name.id
		for node in ast.walk(function)
		if isinstance(node, ast.Assign) and node.value is call
		for target in node.targets
		for name in ast.walk(target)
		if isinstance(name, ast.Name)
	}


def check_site_api_read_paths_call_ticket_policy(sources: dict) -> list:
	"""ADR-034 Ràng buộc 1-2, U2.md:291-292: in site_api.py `get_record` calls policy.is_ticket_record_excluded, and
	`list_records` calls policy.ticket_content_filters, binds its result and hands every bound name to one
	frappe.get_list call (the exclusion is part of the query, never a filter after it)."""
	source = sources.get(SITE_API_FILE)
	if source is None:
		return [f"{SITE_API_FILE}: file missing"]
	tree = parse(SITE_API_FILE, source)
	aliases = import_aliases(tree)
	functions = {node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)}
	violations = [
		f"{SITE_API_FILE}: {name} missing" for name in ("get_record", "list_records") if name not in functions
	]
	get_record, list_records = functions.get("get_record"), functions.get("list_records")
	if get_record is not None and not _policy_calls(get_record, TICKET_RECORD_CHECK, aliases):
		violations.append(
			f"{SITE_API_FILE}:{get_record.lineno}: get_record does not call policy.{TICKET_RECORD_CHECK}"
		)
	if list_records is None:
		return violations
	calls = _policy_calls(list_records, TICKET_LIST_FILTERS, aliases)
	if not calls:
		violations.append(
			f"{SITE_API_FILE}:{list_records.lineno}: list_records does not call policy.{TICKET_LIST_FILTERS}"
		)
	passed = [
		{name.id for name in ast.walk(node) if isinstance(name, ast.Name)}
		for node in ast.walk(list_records)
		if isinstance(node, ast.Call) and resolved_name(node.func, aliases) == "frappe.get_list"
	]
	for call in calls:
		bound = _bound_names(list_records, call)
		if not bound or not any(bound <= names for names in passed):
			violations.append(
				f"{SITE_API_FILE}:{call.lineno}: list_records does not pass the result of "
				f"policy.{TICKET_LIST_FILTERS} into frappe.get_list (ADR-034 Ràng buộc 2)"
			)
	return violations


def _module_assignment(rel: str, source: str, name: str):
	"""The value node of the module-level `name = ...` of `rel`, or None."""
	return next(
		(
			node.value
			for node in parse(rel, source).body
			if isinstance(node, ast.Assign)
			and any(isinstance(target, ast.Name) and target.id == name for target in node.targets)
		),
		None,
	)


def check_ticket_link_fields_cover_ticket_content_doctypes(sources: dict) -> list:
	"""U2.md:293: `set(TICKET_LINK_FIELDS) | {"HD Ticket"} == set(TICKET_CONTENT_DOCTYPES)`, TICKET_LINK_ONLY_DOCTYPES
	aside: every content DocType but the ticket says how it names its ticket, and no other DocType is declared."""
	link_fields = _module_assignment(POLICY_FILE, sources.get(POLICY_FILE, ""), TICKET_LINK_FIELDS_NAME)
	content = _module_assignment(
		CONSTANTS_FILE, sources.get(CONSTANTS_FILE, ""), TICKET_CONTENT_DOCTYPES_NAME
	)
	if not isinstance(link_fields, ast.Dict) or content is None:
		return [
			f"{TICKET_LINK_FIELDS_NAME} ({POLICY_FILE}) or {TICKET_CONTENT_DOCTYPES_NAME} ({CONSTANTS_FILE}) "
			"missing or not a literal"
		]
	literal = [isinstance(key, ast.Constant) and isinstance(key.value, str) for key in link_fields.keys]
	violations = [
		f"{POLICY_FILE}:{link_fields.lineno}: a {TICKET_LINK_FIELDS_NAME} key that is not a string literal"
		for ok in literal
		if not ok
	]
	declared = {key.value for key, ok in zip(link_fields.keys, literal, strict=True) if ok}
	expected = set(ast.literal_eval(content))
	violations.extend(
		f"{POLICY_FILE}: {TICKET_LINK_FIELDS_NAME} has no entry for {doctype}"
		for doctype in sorted(expected - declared - {TICKET_DOCTYPE_NAME})
	)
	violations.extend(
		f"{POLICY_FILE}: {TICKET_LINK_FIELDS_NAME} declares {doctype}, not in {TICKET_CONTENT_DOCTYPES_NAME}"
		for doctype in sorted(declared - expected - TICKET_LINK_ONLY_DOCTYPES)
	)
	return violations


# Clean samples of the three rules: each allowed file names what it may, the policy's function is called.
TICKET_POLICY_SAMPLE = {
	POLICY_FILE: (
		'import frappe\n\nEXCLUDED_TEAMS_FIELD = "excluded_teams"\n\n\n'
		"def excluded_title_prefixes():\n"
		"\treturn frappe.db.get_single_value('ERP AI Setting', 'excluded_title_prefixes')\n"
	),
	SETTING_CONTROLLER_FILE: "def validate(self):\n\tself.excluded_teams = (self.excluded_teams or '').strip()\n",
	INSTALL_FILE: "TICKET_FIELDS = [{'fieldname': 'ai_opt_out', 'fieldtype': 'Check'}]\n",
	HANDLERS_FILE: (
		"from erp_ai.agent import policy\n\n\n"
		"def hook(doc):\n"
		'\t"""Not sent when send_refusal says so (excluded_teams, ai_opt_out, excluded_title_prefixes)."""\n'
		"\treturn policy.send_refusal(doc) or policy.excluded_title_prefixes()\n"
	),
	READ_TOOL_FILE: (
		"from erp_ai.agent.policy import excluded_title_prefixes\n"
		"from erp_ai.agent.policy import excluded_title_prefixes as prefixes\n\n\n"
		"def shown():\n\treturn excluded_title_prefixes() + prefixes()\n"
	),
}

SITE_API_READ_SAMPLE = {
	SITE_API_FILE: (
		"import frappe\n\nfrom erp_ai.agent import policy\n\n\n"
		"def get_record(args, ctx):\n"
		"\tif policy.is_ticket_record_excluded(args['doctype'], args['name']):\n"
		"\t\treturn {'ok': False}\n"
		"\treturn frappe.get_doc(args['doctype'], args['name']).as_dict()\n\n\n"
		"def list_records(args, ctx):\n"
		"\textra, or_filters = policy.ticket_content_filters(args['doctype'])\n"
		"\treturn frappe.get_list(args['doctype'], filters=[*args['filters'], *extra], or_filters=or_filters)\n"
	)
}

TICKET_LINK_SAMPLE = {
	POLICY_FILE: (
		"TICKET_LINK_FIELDS = {\n"
		'\t"Comment": (("reference_doctype", "reference_name"),),\n'
		'\t"Communication": (("reference_doctype", "reference_name"),),\n'
		'\t"File": (("attached_to_doctype", "attached_to_name"),),\n'
		'\t"ToDo": (("reference_type", "reference_name"),),\n'
		"}\n"
	),
	CONSTANTS_FILE: 'TICKET_CONTENT_DOCTYPES = ("HD Ticket", "Comment", "Communication", "File")\n',
}


class TestTicketPolicyRules(unittest.TestCase):
	"""T139: the rules of ADR-034 Ràng buộc 1-2 on the product, then each one's green and red samples."""

	@classmethod
	def setUpClass(cls):
		cls.sources = load_product_sources()

	def assertCaught(self, violations, *fragments):
		self.assertGreater(len(violations), 0, "scanner missed the violation")
		for fragment in fragments:
			self.assertTrue(any(fragment in text for text in violations), f"{fragment!r} not in {violations}")

	def assertSamples(self, check, clean: dict, cases: dict):
		"""`check` lets `clean` through and catches each case: `{case: (sources, fragment)}`."""
		self.assertEqual(check(clean), [], "the clean sample is flagged")
		for case, (sources, fragment) in cases.items():
			with self.subTest(case=case):
				self.assertCaught(check(sources), fragment)

	def test_ticket_policy_fields_read_only_in_policy(self):
		self.assertIn("excluded_title_prefixes", POLICY_FIELDS)
		for rel in TICKET_POLICY_FILES:
			self.assertIn(rel, self.sources)
		self.assertEqual(check_policy_fields_only_in_policy(self.sources), [])
		self.assertEqual(check_ticket_policy_fields_read_only_in_policy(self.sources), [])

		changed = TestScannersCatchViolations.changed
		clean = TICKET_POLICY_SAMPLE

		def in_job(body: str) -> dict:
			return changed(clean, TASKS_FILE, f"import frappe\n\n\ndef job(settings, doc):\n\t{body}\n")

		outside = f"{TASKS_FILE}:5: names a ticket policy field outside {POLICY_FILE}"
		self.assertSamples(
			check_ticket_policy_fields_read_only_in_policy,
			clean,
			{
				"Setting field read by its name": (
					in_job('return frappe.db.get_single_value("ERP AI Setting", "excluded_teams")'),
					outside,
				),
				"ticket flag read as an attribute": (in_job("return doc.ai_opt_out"), outside),
				"ticket flag as a filter keyword": (
					in_job('return frappe.get_all("HD Ticket", filters=dict(ai_opt_out=0))'),
					outside,
				),
				"a built string": (in_job('return settings.get("excluded_" + "title_prefixes")'), outside),
				"an f-string": (
					in_job('return frappe.db.sql(f"select ai_opt_out from t where name={doc}")'),
					outside,
				),
				"policy's constant outside policy": (
					in_job("return getattr(settings, policy.EXCLUDED_TEAMS_FIELD)"),
					outside,
				),
				"the Setting field named like the policy function": (
					in_job("return settings.excluded_title_prefixes"),
					outside,
				),
				"a field name imported from policy": (
					changed(clean, TASKS_FILE, "from erp_ai.agent.policy import excluded_teams\n"),
					f"{TASKS_FILE}:1:",
				),
				"the handler reads the flag itself": (
					changed(clean, HANDLERS_FILE, "\n\ndef flag(doc):\n\treturn doc.ai_opt_out\n"),
					f"{HANDLERS_FILE}:10:",
				),
			},
		)

	def test_site_api_read_paths_call_ticket_policy(self):
		self.assertEqual(check_site_api_read_paths_call_ticket_policy(self.sources), [])

		changed = TestScannersCatchViolations.changed
		clean = SITE_API_READ_SAMPLE
		bind = "\textra, or_filters = policy.ticket_content_filters(args['doctype'])\n"
		query = "\treturn frappe.get_list(args['doctype'], filters=[*args['filters'], *extra], or_filters=or_filters)\n"
		not_passed = (
			f"{SITE_API_FILE}:13: list_records does not pass the result of policy.{TICKET_LIST_FILTERS}"
		)
		self.assertSamples(
			check_site_api_read_paths_call_ticket_policy,
			clean,
			{
				"get_record reads without asking": (
					changed(
						clean, SITE_API_FILE, replace=("policy.is_ticket_record_excluded(", "is_hidden(")
					),
					f"{SITE_API_FILE}:6: get_record does not call policy.{TICKET_RECORD_CHECK}",
				),
				"list_records filters after the query": (
					changed(
						clean,
						SITE_API_FILE,
						replace=(
							query,
							"\trows = frappe.get_list(args['doctype'], filters=args['filters'])\n"
							"\treturn [row for row in rows if [row] not in (extra, or_filters)]\n",
						),
					),
					not_passed,
				),
				"the OR group left out of the query": (
					changed(clean, SITE_API_FILE, replace=(", or_filters=or_filters)", ")")),
					not_passed,
				),
				"the result not bound": (
					changed(
						clean,
						SITE_API_FILE,
						replace=(
							bind,
							"\tpolicy.ticket_content_filters(args['doctype'])\n\textra = or_filters = []\n",
						),
					),
					not_passed,
				),
				"list_records never asks": (
					changed(clean, SITE_API_FILE, replace=(bind, "\textra, or_filters = [], []\n")),
					f"{SITE_API_FILE}:12: list_records does not call policy.{TICKET_LIST_FILTERS}",
				),
			},
		)

	def test_ticket_link_fields_cover_ticket_content_doctypes(self):
		self.assertEqual(check_ticket_link_fields_cover_ticket_content_doctypes(self.sources), [])
		# the allowance names only DocTypes the product declares (C3b); a name gone from policy.py leaves it
		for doctype in TICKET_LINK_ONLY_DOCTYPES:
			self.assertIn(f'"{doctype}": (', self.sources[POLICY_FILE])

		changed = TestScannersCatchViolations.changed
		clean = TICKET_LINK_SAMPLE
		self.assertSamples(
			check_ticket_link_fields_cover_ticket_content_doctypes,
			clean,
			{
				"a content DocType without an entry": (
					changed(clean, CONSTANTS_FILE, replace=('"File")', '"File", "Note")')),
					f"{TICKET_LINK_FIELDS_NAME} has no entry for Note",
				),
				"an entry outside the content DocTypes": (
					changed(clean, POLICY_FILE, replace=('\t"ToDo"', '\t"Event"')),
					f"{TICKET_LINK_FIELDS_NAME} declares Event, not in {TICKET_CONTENT_DOCTYPES_NAME}",
				),
				"a key that is not a string literal": (
					changed(clean, POLICY_FILE, replace=('\t"File":', "\tFILE_DOCTYPE:")),
					"not a string literal",
				),
				"the declaration gone": ({CONSTANTS_FILE: clean[CONSTANTS_FILE]}, "missing or not a literal"),
			},
		)


# ---------------------------------------------------------------------------------------------------
# FEAT-008 lesson store and its reader (ADR-045 Ràng buộc, ADR-046 Ràng buộc, Task 10)
# ---------------------------------------------------------------------------------------------------

LESSONS_FILE = "agent/lessons.py"
LESSON_READ_FILE = "agent/lesson_read.py"
LESSONS_MODULE = module_name(LESSONS_FILE)
LESSON_READ_MODULE = module_name(LESSON_READ_FILE)
# The only places that name the lesson DocTypes: the store, the reader, their controllers, constants and hooks.
LESSON_DOCTYPE_FILES = (CONSTANTS_FILE, LESSONS_FILE, LESSON_READ_FILE, HOOKS_FILE)
LESSON_DOCTYPE_DIRS = ("erp_ai_agent/doctype/erp_ai_lesson/", "erp_ai_agent/doctype/erp_ai_lesson_event/")
LESSON_DOCTYPE_CONSTANTS = ("LESSON_DOCTYPE", "LESSON_EVENT_DOCTYPE")
LESSON_DOCTYPE_TEXT = "ERP AI Lesson"  # both DocType names start with it
LESSON_DOCTYPE_JSONS = tuple(f"{folder}{Path(folder).name}.json" for folder in LESSON_DOCTYPE_DIRS)
LESSON_WRITE_RIGHTS = ("create", "write", "delete", "submit", "cancel", "amend")
LESSON_READ_FUNCTION = "relevant_lessons"
LESSON_ACTIVE_CONSTANT = "LESSON_STATUS_ACTIVE"
LESSON_STATUS_FIELD = "lesson_status"
# Modules that get lessons only as values from the runner: they never import the store or the reader.
LESSON_FREE_MODULES = ("erp_ai.agent.prompts", "erp_ai.agent.tools", "erp_ai.gateway", "erp_ai.eval")
# Global Constraints of FEAT-008 batch 1: (scope module, forbidden modules, reason), read by check_layer_imports.
LESSON_IMPORT_RULES = (
	(
		"erp_ai.agent",
		("erp_ai.handlers", "erp_ai.tasks", "erp_ai.install", "erp_ai.eval", "erp_ai.erp_ai_agent"),
		"ADR-045: agent core never imports handlers, the scheduler, install, eval or doctype controllers",
	),
	(
		LESSONS_MODULE,
		("erp_ai.agent.runner", "erp_ai.gateway", "erp_ai.agent.changes"),
		"ADR-045: the lesson store never runs the agent, calls the model or reaches the change job",
	),
	(
		LESSON_READ_MODULE,
		(LESSONS_MODULE, "erp_ai.gateway"),
		"ADR-046: the lesson reader never imports the store or calls the model",
	),
	*(
		(
			scope,
			(LESSONS_MODULE, LESSON_READ_MODULE),
			"ADR-046: prompts, tools, gateway and eval get lessons as values from the runner, never from the store or reader",
		)
		for scope in LESSON_FREE_MODULES
	),
)


def _is_text(node, docstrings: set) -> bool:
	return isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in docstrings


def check_lesson_doctype_named_only_in_store(sources: dict) -> list:
	"""ADR-045/046: a lesson DocType is named (its constant, imported or read, or a string holding its name, docstrings
	aside) only in constants.py, the store, the reader, the two DocType folders and hooks.py."""
	violations = []
	for rel, source in only_python(sources).items():
		if rel in LESSON_DOCTYPE_FILES or rel.startswith(LESSON_DOCTYPE_DIRS):
			continue
		tree = parse(rel, source)
		docstrings = _docstring_ids(tree)
		for node in ast.walk(tree):
			if (
				referenced_name(node) in LESSON_DOCTYPE_CONSTANTS
				or (isinstance(node, ast.alias) and node.name in LESSON_DOCTYPE_CONSTANTS)
				or (_is_text(node, docstrings) and LESSON_DOCTYPE_TEXT in node.value)
			):
				violations.append(
					violation(
						rel,
						node,
						"names a lesson DocType; only the store and its reader may (ADR-045, ADR-046)",
					)
				)
	return violations


def check_lesson_import_direction(sources: dict) -> list:
	return check_layer_imports(sources, LESSON_IMPORT_RULES)


def check_relevant_lessons_called_only_by_runner(sources: dict) -> list:
	"""ADR-046: only the runner names `lesson_read.relevant_lessons` (a call, an import, a string path) besides the
	reader that defines it, and the runner does call it."""
	violations, runner_calls = [], 0
	for rel, source in only_python(sources).items():
		if rel == LESSON_READ_FILE:
			continue
		tree = parse(rel, source)
		docstrings = _docstring_ids(tree)
		for node in ast.walk(tree):
			if rel == RUNNER_FILE:
				runner_calls += (
					isinstance(node, ast.Call) and referenced_name(node.func) == LESSON_READ_FUNCTION
				)
				continue
			if (
				referenced_name(node) == LESSON_READ_FUNCTION
				or (isinstance(node, ast.alias) and node.name == LESSON_READ_FUNCTION)
				or (_is_text(node, docstrings) and re.search(rf"\b{LESSON_READ_FUNCTION}\b", node.value))
			):
				violations.append(
					violation(
						rel, node, f"names {LESSON_READ_FUNCTION}; only {RUNNER_FILE} reads lessons (ADR-046)"
					)
				)
	if RUNNER_FILE in sources and not runner_calls:
		violations.append(f"{RUNNER_FILE}: never calls lesson_read.{LESSON_READ_FUNCTION} (ADR-046 QĐ 1)")
	return violations


def check_lesson_doctypes_grant_no_write(sources: dict) -> list:
	"""ADR-045: the store is the only writer, so no permission row of a lesson DocType grants a write right."""
	violations = []
	for rel in LESSON_DOCTYPE_JSONS:
		if rel not in sources:
			violations.append(f"{rel}: file missing")
			continue
		for row in json.loads(sources[rel]).get("permissions") or []:
			granted = [right for right in LESSON_WRITE_RIGHTS if row.get(right)]
			if granted:
				violations.append(
					f"{rel}: role {row.get('role')} is granted {', '.join(granted)}; only the store writes (ADR-045)"
				)
	return violations


def _filter_values(tree: ast.AST) -> set:
	"""ids of the nodes given as the `lesson_status` value of a filter: `{"lesson_status": X}`, `["lesson_status", X]`
	or `["lesson_status", "=", X]`."""
	values = set()
	for node in ast.walk(tree):
		if isinstance(node, ast.Dict):
			values |= {
				id(value)
				for key, value in zip(node.keys, node.values, strict=True)
				if _is_constant(key, LESSON_STATUS_FIELD)
			}
		elif isinstance(node, ast.List | ast.Tuple) and len(node.elts) in (2, 3):
			if _is_constant(node.elts[0], LESSON_STATUS_FIELD):
				values.add(id(node.elts[-1]))
	return values


def check_active_status_condition_written_once(sources: dict) -> list:
	"""ADR-046 Ràng buộc: the "đang dùng" condition is written once in the reader, as the value of its one
	`lesson_status` filter; never twice, never outside a filter, never as the literal text."""
	source = sources.get(LESSON_READ_FILE)
	if source is None:
		return [f"{LESSON_READ_FILE}: file missing"]
	tree = parse(LESSON_READ_FILE, source)
	docstrings = _docstring_ids(tree)
	uses = [
		node
		for node in ast.walk(tree)
		if isinstance(node, ast.Name | ast.Attribute) and referenced_name(node) == LESSON_ACTIVE_CONSTANT
	]
	filters = _filter_values(tree)
	violations = [
		violation(LESSON_READ_FILE, node, f"{LESSON_ACTIVE_CONSTANT} outside a {LESSON_STATUS_FIELD} filter")
		for node in uses
		if id(node) not in filters
	]
	if len(uses) != 1:
		violations.append(
			f"{LESSON_READ_FILE}: {LESSON_ACTIVE_CONSTANT} used {len(uses)} times; the condition is written once (ADR-046)"
		)
	violations.extend(
		violation(LESSON_READ_FILE, node, f"the text of {LESSON_ACTIVE_CONSTANT}; filter on the constant")
		for node in ast.walk(tree)
		if _is_text(node, docstrings) and node.value == LESSON_STATUS_ACTIVE
	)
	return violations


# Clean samples of the lesson rules: each file does what it may.
LESSON_RULES_SAMPLE = {
	CONSTANTS_FILE: 'LESSON_DOCTYPE = "ERP AI Lesson"\nLESSON_EVENT_DOCTYPE = "ERP AI Lesson Event"\n',
	HOOKS_FILE: 'ignore_links_on_delete = ["ERP AI Log", "ERP AI Lesson"]\n',
	LESSONS_FILE: (
		"import frappe\n\nfrom erp_ai.agent import policy\nfrom erp_ai.constants import LESSON_DOCTYPE\n\n\n"
		"def store(values):\n\treturn frappe.get_doc({'doctype': LESSON_DOCTYPE, **values}).insert()\n"
	),
	LESSON_READ_FILE: (
		"import frappe\n\nfrom erp_ai.agent import knowledge, policy\n"
		"from erp_ai.constants import LESSON_DOCTYPE, LESSON_STATUS_ACTIVE\n\n\n"
		"def relevant_lessons(subject, description):\n"
		"\treturn frappe.get_all(LESSON_DOCTYPE, filters={'lesson_status': LESSON_STATUS_ACTIVE})\n"
	),
	"erp_ai_agent/doctype/erp_ai_lesson/erp_ai_lesson.py": (
		"from frappe.model.document import Document\n\nfrom erp_ai.agent import lessons\n\n\n"
		"class ERPAILesson(Document):\n\tpass\n"
	),
	RUNNER_FILE: (
		'"""The runner; relevant_lessons gives the ERP AI Lesson rows of a step."""\n\n'
		"from erp_ai.agent import lesson_read, policy\nfrom erp_ai.agent.prompts import build_classify_request\n\n\n"
		"def _lessons(settings, subject, description):\n"
		"\treturn lesson_read.relevant_lessons(subject, description)\n"
	),
	"agent/prompts.py": "from erp_ai.constants import LESSON_STATUS_ACTIVE\n",
	HANDLERS_FILE: "from erp_ai.agent import lessons\n",
	"agent/changes/transitions.py": "from erp_ai.agent import lessons\n",
	"erp_ai_agent/doctype/erp_ai_lesson/erp_ai_lesson.json": json.dumps(
		{
			"permissions": [
				{"role": "System Manager", "read": 1, "write": 0},
				{"role": "ERP AI Instructor", "read": 1},
			]
		}
	),
	"erp_ai_agent/doctype/erp_ai_lesson_event/erp_ai_lesson_event.json": json.dumps(
		{"istable": 1, "permissions": []}
	),
}


class TestLessonArchitecture(unittest.TestCase):
	"""FEAT-008 Task 10: the rules of ADR-045 and ADR-046 on the product, then each one's green and red samples."""

	@classmethod
	def setUpClass(cls):
		cls.sources = load_product_sources()
		cls.with_json = load_product_sources(suffixes=(".py", ".json"))

	def assertCaught(self, violations, *fragments):
		self.assertGreater(len(violations), 0, "scanner missed the violation")
		for fragment in fragments:
			self.assertTrue(any(fragment in text for text in violations), f"{fragment!r} not in {violations}")

	def assertSamples(self, check, clean: dict, cases: dict):
		"""`check` lets `clean` through and catches each case: `{case: (sources, fragment)}`."""
		self.assertEqual(check(clean), [], "the clean sample is flagged")
		for case, (sources, fragment) in cases.items():
			with self.subTest(case=case):
				self.assertCaught(check(sources), fragment)

	def test_lesson_doctype_named_only_in_store_reader_controller(self):
		# the allowance names files and folders the product has
		for rel in LESSON_DOCTYPE_FILES:
			self.assertIn(rel, self.sources)
		for folder in LESSON_DOCTYPE_DIRS:
			self.assertTrue(any(rel.startswith(folder) for rel in self.sources), folder)
		self.assertEqual(check_lesson_doctype_named_only_in_store(self.sources), [])

		changed = TestScannersCatchViolations.changed
		clean = LESSON_RULES_SAMPLE
		self.assertSamples(
			check_lesson_doctype_named_only_in_store,
			clean,
			{
				"the constant imported by the runner": (
					changed(clean, RUNNER_FILE, "from erp_ai.constants import LESSON_DOCTYPE\n"),
					f"{RUNNER_FILE}:9: names a lesson DocType",
				),
				"the constant read off the module": (
					changed(
						clean,
						TASKS_FILE,
						"from erp_ai import constants\n\nX = constants.LESSON_EVENT_DOCTYPE\n",
					),
					f"{TASKS_FILE}:3:",
				),
				"the name as a string": (
					changed(
						clean, HANDLERS_FILE, "\n\ndef f(frappe):\n\treturn frappe.get_all('ERP AI Lesson')\n"
					),
					f"{HANDLERS_FILE}:5:",
				),
				"the table in raw SQL": (
					changed(clean, "agent/policy.py", "Q = 'select name from `tabERP AI Lesson Event`'\n"),
					"agent/policy.py:1:",
				),
			},
		)

	def test_lesson_modules_import_direction(self):
		self.assertEqual(check_lesson_import_direction(self.sources), [])

		changed = TestScannersCatchViolations.changed
		clean = LESSON_RULES_SAMPLE
		cases = {
			"agent core imports handlers": (
				"agent/policy.py",
				"from erp_ai import handlers\n",
				"erp_ai.handlers",
			),
			"agent core imports tasks": ("agent/queue.py", "import erp_ai.tasks\n", "erp_ai.tasks"),
			"agent core imports install": (
				"agent/policy.py",
				"from erp_ai.install import x\n",
				"erp_ai.install",
			),
			"agent core imports eval": (
				"agent/policy.py",
				"from erp_ai.eval import run_eval\n",
				"erp_ai.eval",
			),
			"agent core imports a controller": (
				"agent/policy.py",
				"from erp_ai.erp_ai_agent.doctype.erp_ai_lesson import erp_ai_lesson\n",
				"erp_ai.erp_ai_agent",
			),
			"the store imports the runner": (
				LESSONS_FILE,
				"from erp_ai.agent import runner\n",
				"erp_ai.agent.runner",
			),
			"the store imports the gateway": (LESSONS_FILE, "from erp_ai import gateway\n", "erp_ai.gateway"),
			"the store imports the change job": (
				LESSONS_FILE,
				"from erp_ai.agent.changes import transitions\n",
				"erp_ai.agent.changes",
			),
			"the reader imports the store": (
				LESSON_READ_FILE,
				"from erp_ai.agent import lessons\n",
				LESSONS_MODULE,
			),
			"the reader imports the gateway": (LESSON_READ_FILE, "import erp_ai.gateway\n", "erp_ai.gateway"),
			"prompts import the reader": (
				"agent/prompts.py",
				"from erp_ai.agent import lesson_read\n",
				LESSON_READ_MODULE,
			),
			"a tool imports the store": (
				"agent/tools/read.py",
				"from erp_ai.agent.lessons import _store\n",
				LESSONS_MODULE,
			),
			"the gateway imports the reader": (
				"gateway/client.py",
				"from erp_ai.agent.lesson_read import relevant_lessons\n",
				LESSON_READ_MODULE,
			),
			"eval imports the store": ("eval/run_eval.py", "from ..agent import lessons\n", LESSONS_MODULE),
		}

		def extra_line(sources, rel):
			"""The line `changed` appends to `rel` on."""
			return sources.get(rel, "").count("\n") + 1

		self.assertSamples(
			check_lesson_import_direction,
			clean,
			{
				case: (changed(clean, rel, extra), f"{rel}:{extra_line(clean, rel)}: imports {target}")
				for case, (rel, extra, target) in cases.items()
			},
		)

	def test_relevant_lessons_called_only_by_runner(self):
		self.assertEqual(check_relevant_lessons_called_only_by_runner(self.sources), [])

		changed = TestScannersCatchViolations.changed
		clean = LESSON_RULES_SAMPLE
		self.assertSamples(
			check_relevant_lessons_called_only_by_runner,
			clean,
			{
				"a tool calls the reader": (
					changed(
						clean,
						"agent/tools/read.py",
						"from erp_ai.agent import lesson_read\n\n\ndef f(s):\n\treturn lesson_read.relevant_lessons(s, '')\n",
					),
					"agent/tools/read.py:5: names relevant_lessons",
				),
				"the handlers import it": (
					changed(
						clean,
						HANDLERS_FILE,
						"from erp_ai.agent.lesson_read import relevant_lessons as pick\n",
					),
					f"{HANDLERS_FILE}:2:",
				),
				"a string path to it": (
					changed(
						clean, "hooks.py", "doc_events = {'x': 'erp_ai.agent.lesson_read.relevant_lessons'}\n"
					),
					"hooks.py:2:",
				),
				"the runner never calls it": (
					changed(clean, RUNNER_FILE, replace=("lesson_read.relevant_lessons(", "list(")),
					f"{RUNNER_FILE}: never calls lesson_read.relevant_lessons",
				),
			},
		)

	def test_lesson_doctypes_grant_no_write(self):
		self.assertEqual(check_lesson_doctypes_grant_no_write(self.with_json), [])

		changed = TestScannersCatchViolations.changed
		clean = LESSON_RULES_SAMPLE
		lesson_json, event_json = LESSON_DOCTYPE_JSONS
		cases = {
			right: (
				changed(clean, lesson_json, replace=('"write": 0', f'"write": 0, "{right}": 1')),
				f"{lesson_json}: role System Manager is granted {right}",
			)
			for right in LESSON_WRITE_RIGHTS
		}
		cases["a row of the event table"] = (
			changed(
				clean,
				event_json,
				replace=('"permissions": []', '"permissions": [{"role": "All", "create": 1}]'),
			),
			f"{event_json}: role All is granted create",
		)
		cases["a DocType file gone"] = ({lesson_json: clean[lesson_json]}, f"{event_json}: file missing")
		self.assertSamples(check_lesson_doctypes_grant_no_write, clean, cases)

	def test_active_status_condition_written_once(self):
		self.assertEqual(check_active_status_condition_written_once(self.sources), [])

		changed = TestScannersCatchViolations.changed
		clean = LESSON_RULES_SAMPLE
		self.assertSamples(
			check_active_status_condition_written_once,
			clean,
			{
				"a second filter": (
					changed(
						clean,
						LESSON_READ_FILE,
						"\n\ndef more():\n\treturn frappe.get_all(LESSON_DOCTYPE, filters=[['lesson_status', '=', LESSON_STATUS_ACTIVE]])\n",
					),
					"used 2 times",
				),
				"a check after the query": (
					changed(
						clean,
						LESSON_READ_FILE,
						"\n\ndef keep(row):\n\treturn row.lesson_status == LESSON_STATUS_ACTIVE\n",
					),
					f"{LESSON_READ_FILE}:12: {LESSON_ACTIVE_CONSTANT} outside a {LESSON_STATUS_FIELD} filter",
				),
				"the literal text": (
					changed(
						clean,
						LESSON_READ_FILE,
						replace=(
							"'lesson_status': LESSON_STATUS_ACTIVE",
							f"'lesson_status': '{LESSON_STATUS_ACTIVE}'",
						),
					),
					f"the text of {LESSON_ACTIVE_CONSTANT}",
				),
				"no condition at all": (
					changed(
						clean,
						LESSON_READ_FILE,
						replace=("filters={'lesson_status': LESSON_STATUS_ACTIVE}", "limit=5"),
					),
					"used 0 times",
				),
				"the reader gone": (
					{CONSTANTS_FILE: clean[CONSTANTS_FILE]},
					f"{LESSON_READ_FILE}: file missing",
				),
			},
		)


# ---------------------------------------------------------------------------------------------------
# ADR-048 Ràng buộc (CHG-009 design 8.2): the RQ job-state reads live only in agent/queue.py; handlers.py and
# agent/queue.py never commit (an event row rides the person's transaction); comment_after_insert still starts
# with step 0
# ---------------------------------------------------------------------------------------------------

RQ_JOB_READS = ("get_job", "get_job_status", "is_job_enqueued")
RQ_JOB_CLASS = "Job"
RQ_JOB_FETCH = "fetch"
RQ_JOB_READ_FILE = QUEUE_FILE
EVENT_NO_COMMIT_FILES = (HANDLERS_FILE, QUEUE_FILE)
COMMENT_HOOK = "comment_after_insert"
# Step 0 tests the comment's own fields, never the database: the hook fires for every Comment of the site.
COMMENT_STEP_ZERO_FIELD = "reference_doctype"


def _rq_job_read(node, aliases: dict) -> str | None:
	"""The RQ job-state read `node` names (a name, an attribute, an imported name or `Job.fetch`), else None."""
	if isinstance(node, ast.alias):
		name = node.name.rpartition(".")[2]
	elif isinstance(node, ast.Attribute) and node.attr == RQ_JOB_FETCH:
		job = resolved_name(node.value, aliases).rpartition(".")[2]
		return f"{RQ_JOB_CLASS}.{RQ_JOB_FETCH}" if job == RQ_JOB_CLASS else None
	else:
		name = referenced_name(node)
	return name if name in RQ_JOB_READS else None


def check_rq_job_reads_only_in_queue(sources: dict) -> list:
	"""ADR-048 Ràng buộc: `get_job`, `get_job_status`, `is_job_enqueued` and `Job.fetch` only in agent/queue.py."""
	violations = []
	for rel, source in only_python(sources).items():
		if rel == RQ_JOB_READ_FILE:
			continue
		tree = parse(rel, source)
		aliases = import_aliases(tree)
		for node in ast.walk(tree):
			read = _rq_job_read(node, aliases)
			if read:
				violations.append(
					violation(
						rel, node, f"reads the RQ job state ({read}) outside {RQ_JOB_READ_FILE} (ADR-048)"
					)
				)
	return violations


def check_no_commit_in_event_request_files(sources: dict) -> list:
	"""ADR-048 Ràng buộc: handlers.py and agent/queue.py never call `frappe.db.commit()`."""
	violations = []
	for rel in EVENT_NO_COMMIT_FILES:
		if rel not in sources:
			violations.extend(_missing(rel))
			continue
		tree = parse(rel, sources[rel])
		aliases = import_aliases(tree)
		violations.extend(
			violation(rel, node, f"calls {COMMIT_CALL}() (ADR-048)")
			for node in ast.walk(tree)
			if isinstance(node, ast.Call) and resolved_name(node.func, aliases) == COMMIT_CALL
		)
	return violations


def check_comment_hook_starts_with_step_zero(sources: dict) -> list:
	"""ADR-048 Ràng buộc: the first statement of `comment_after_insert` (after a docstring) is still step 0: an
	`if` on the comment's own `reference_doctype`, with no call in its test and no `else`, that only returns."""
	if HANDLERS_FILE not in sources:
		return _missing(HANDLERS_FILE)
	function = _module_functions(parse(HANDLERS_FILE, sources[HANDLERS_FILE])).get(COMMENT_HOOK)
	if function is None:
		return [f"{HANDLERS_FILE}: no function {COMMENT_HOOK} (ADR-048)"]
	body = function.body[1:] if ast.get_docstring(function) is not None else function.body
	first = body[0] if body else function
	is_step_zero = (
		isinstance(first, ast.If)
		and COMMENT_STEP_ZERO_FIELD in {referenced_name(node) for node in ast.walk(first.test)}
		and not any(isinstance(node, ast.Call) for node in ast.walk(first.test))
		and not first.orelse
		and len(first.body) == 1
		and isinstance(first.body[0], ast.Return)
		and first.body[0].value is None
	)
	if is_step_zero:
		return []
	return [violation(HANDLERS_FILE, first, f"the first statement of {COMMENT_HOOK} is not step 0 (ADR-048)")]


# Clean samples of the three rules: queue.py reads the RQ job state, the comment hook writes its event row after
# step 0 and nothing commits.
EVENT_WRITE_SAMPLE = {
	QUEUE_FILE: (
		"from frappe.utils.background_jobs import get_job, get_job_status, is_job_enqueued\n"
		"from rq.job import Job\n\n\n"
		"def enqueue_agent_run(job_id):\n"
		"\tjob = get_job(job_id) or Job.fetch(job_id)\n"
		"\treturn is_job_enqueued(job_id) or get_job_status(job_id) or job\n"
	),
	HANDLERS_FILE: (
		"import frappe\n\n"
		"from erp_ai.agent import run_log\n\n\n"
		"def comment_after_insert(doc, method=None):\n"
		'\t"""Step 0 first: every Comment of the site reaches this hook."""\n'
		'\tif doc.reference_doctype != "HD Ticket" or doc.comment_type != "Comment":\n'
		"\t\treturn\n"
		'\trun_log.record_event(ticket=doc.reference_name, trigger="comment_mention", code="agent_disabled")\n'
	),
	"agent/runner.py": "from rq.job import Job\n\n\ndef job_class():\n\treturn Job\n",
}


class TestEventWriteRules(unittest.TestCase):
	"""CHG-009 T1: the ADR-048 rules on writing event rows, on the product, then each one's clean and violating samples."""

	assertRuleSamples = TestArchitecture.assertRuleSamples

	@classmethod
	def setUpClass(cls):
		cls.sources = load_product_sources()

	def test_event_write_rules_follow_adr_048(self):
		for rel in (QUEUE_FILE, HANDLERS_FILE):
			self.assertIn(rel, self.sources)
		self.assertEqual(check_rq_job_reads_only_in_queue(self.sources), [])
		self.assertEqual(check_no_commit_in_event_request_files(self.sources), [])
		self.assertEqual(check_comment_hook_starts_with_step_zero(self.sources), [])

		changed = TestScannersCatchViolations.changed
		clean = EVENT_WRITE_SAMPLE
		event_call = '\trun_log.record_event(ticket=doc.reference_name, trigger="comment_mention", code="agent_disabled")\n'
		self.assertRuleSamples(
			check_rq_job_reads_only_in_queue,
			clean,
			{
				"get_job in a handler": (
					changed(
						clean,
						HANDLERS_FILE,
						"\n\ndef busy(job_id):\n\treturn frappe.utils.background_jobs.get_job(job_id)\n",
					),
					f"{HANDLERS_FILE}:14: reads the RQ job state (get_job)",
				),
				"is_job_enqueued imported under another name": (
					changed(
						clean,
						"agent/runner.py",
						"from frappe.utils.background_jobs import is_job_enqueued as queued\n",
					),
					"agent/runner.py:6: reads the RQ job state (is_job_enqueued)",
				),
				"get_job_status through its module": (
					changed(
						clean,
						"ticket_panel.py",
						"from frappe.utils import background_jobs\n\n\n"
						"def running(job_id):\n\treturn background_jobs.get_job_status(job_id)\n",
					),
					"ticket_panel.py:5: reads the RQ job state (get_job_status)",
				),
				"Job.fetch under another name": (
					changed(
						clean,
						"agent/bot_status.py",
						"from rq.job import Job as RQJob\n\n\ndef state(job_id):\n\treturn RQJob.fetch(job_id)\n",
					),
					"agent/bot_status.py:5: reads the RQ job state (Job.fetch)",
				),
			},
		)
		self.assertRuleSamples(
			check_no_commit_in_event_request_files,
			clean,
			{
				"commit in the comment hook": (
					changed(clean, HANDLERS_FILE, "\tfrappe.db.commit()\n"),
					f"{HANDLERS_FILE}:11: calls {COMMIT_CALL}()",
				),
				"commit through `from frappe import db` in the queue": (
					changed(
						clean, QUEUE_FILE, "\n\ndef flush():\n\tfrom frappe import db\n\n\tdb.commit()\n"
					),
					f"{QUEUE_FILE}:13: calls {COMMIT_CALL}()",
				),
				"handlers.py missing": ({QUEUE_FILE: clean[QUEUE_FILE]}, f"{HANDLERS_FILE}: file missing"),
			},
		)
		step_zero = '\tif doc.reference_doctype != "HD Ticket" or doc.comment_type != "Comment":\n'
		not_first = f"{HANDLERS_FILE}:8: the first statement of {COMMENT_HOOK} is not step 0"
		self.assertRuleSamples(
			check_comment_hook_starts_with_step_zero,
			clean,
			{
				"event written before step 0": (
					changed(clean, HANDLERS_FILE, replace=(step_zero, event_call + step_zero)),
					not_first,
				),
				"step 0 reads the database": (
					changed(
						clean,
						HANDLERS_FILE,
						replace=(
							'doc.comment_type != "Comment"',
							'not frappe.db.exists("HD Ticket", doc.reference_name)',
						),
					),
					not_first,
				),
				"step 0 writes before returning": (
					changed(
						clean, HANDLERS_FILE, replace=("\t\treturn\n", "\t" + event_call + "\t\treturn\n")
					),
					not_first,
				),
				"step 0 no longer tests the DocType": (
					changed(clean, HANDLERS_FILE, replace=('doc.reference_doctype != "HD Ticket" or ', "")),
					not_first,
				),
				"the hook renamed": (
					changed(clean, HANDLERS_FILE, replace=("def comment_after_insert(", "def comment_hook(")),
					f"{HANDLERS_FILE}: no function {COMMENT_HOOK}",
				),
			},
		)


# ---------------------------------------------------------------------------------------------------
# ADR-048 Ràng buộc "module đọc ở QĐ 6" (CHG-009 design 3.2, 8.2): the panel's status reader writes nothing and
# reads no cache or job state; outside tests only ticket_panel.py imports it; ticket_panel.py still never names
# "ERP AI Log" (its import rule is the `erp_ai.agent.bot_status` entry of LAYER_RULES)
# ---------------------------------------------------------------------------------------------------

BOT_STATUS_FILE = "agent/bot_status.py"
BOT_STATUS_MODULE = "erp_ai.agent.bot_status"
BOT_STATUS_FORBIDDEN_NAMES = (
	"insert",
	"save",
	"set_value",
	"db_set",
	"commit",
	"write_entry",
	"cache",
	"publish_realtime",
	"get_job",
)
PANEL_FORBIDDEN_LOG_TEXT = "ERP AI Log"


def check_bot_status_reader_follows_adr_048(sources: dict) -> list:
	"""ADR-048 Ràng buộc: the reader names no write, commit, cache, realtime publish or job read; no product file
	but ticket_panel.py imports or names the reader; ticket_panel.py holds no "ERP AI Log" string."""
	for rel in (BOT_STATUS_FILE, PANEL_FILE):
		if rel not in sources:
			return _missing(rel)
	violations = [
		violation(
			BOT_STATUS_FILE, node, f"names {name}: the reader writes nothing, reads no cache or job (ADR-048)"
		)
		for node in ast.walk(parse(BOT_STATUS_FILE, sources[BOT_STATUS_FILE]))
		for name in _node_names(node)
		if name in BOT_STATUS_FORBIDDEN_NAMES
	]
	for rel, source in only_python(sources).items():
		if rel in (BOT_STATUS_FILE, PANEL_FILE):
			continue
		tree = parse(rel, source)
		for lineno, target in imported_modules(tree, module_name(rel), rel.endswith("__init__.py")):
			if module_in(target, BOT_STATUS_MODULE):
				violations.append(f"{rel}:{lineno}: imports {target}; only {PANEL_FILE} may (ADR-048)")
		violations.extend(
			violation(rel, node, f"names {BOT_STATUS_MODULE}; only {PANEL_FILE} may (ADR-048)")
			for node in constant_strings(tree)
			if BOT_STATUS_MODULE in node.value
		)
	violations.extend(
		violation(
			PANEL_FILE, node, f'names "{PANEL_FORBIDDEN_LOG_TEXT}": only the reader reads the log (ADR-048)'
		)
		for node in constant_strings(parse(PANEL_FILE, sources[PANEL_FILE]))
		if PANEL_FORBIDDEN_LOG_TEXT in node.value
	)
	return violations


# Clean sample: the reader reads the log through the allowed imports, the panel imports it, another module does not.
BOT_STATUS_SAMPLE = {
	BOT_STATUS_FILE: (
		"import frappe\n"
		"from frappe.utils import now_datetime\n\n"
		"from erp_ai.constants import LOG_DOCTYPE\n\n\n"
		"def panel_status(ticket, message_names, now=None):\n"
		'\trows = frappe.get_all(LOG_DOCTYPE, filters={"ticket": ticket}, fields=["name"], limit=500)\n'
		'\treturn {"lines": rows, "now": now or now_datetime()}\n'
	),
	PANEL_FILE: (
		"from erp_ai.agent import bot_status\n\n\n"
		"def get_panel_data(ticket):\n"
		'\treturn {"bot_status": bot_status.panel_status(ticket, [])}\n'
	),
	"agent/messages.py": "import frappe\n\nfrom erp_ai.constants import MESSAGE_DOCTYPE\n",
}
# design 8.2: what the LAYER_RULES entry of the reader forbids.
BOT_STATUS_FORBIDDEN_IMPORTS = (
	"erp_ai.gateway",
	"erp_ai.agent.runner",
	"erp_ai.agent.queue",
	"erp_ai.agent.run_status",
	"erp_ai.agent.tools",
	"erp_ai.agent.policy",
	"erp_ai.agent.run_log",
)


class TestBotStatusReaderRules(unittest.TestCase):
	"""CHG-009 T4: the ADR-048 rules on the panel's status reader, on the product, then the clean and violating samples."""

	assertRuleSamples = TestArchitecture.assertRuleSamples

	@classmethod
	def setUpClass(cls):
		cls.sources = load_product_sources()

	def test_bot_status_reader_follows_adr_048(self):
		self.assertIn(BOT_STATUS_FILE, self.sources)
		self.assertEqual(check_bot_status_reader_follows_adr_048(self.sources), [])

		changed = TestScannersCatchViolations.changed
		clean = BOT_STATUS_SAMPLE
		in_reader = {
			"insert": 'frappe.get_doc({"doctype": LOG_DOCTYPE}).insert()',
			"save": "doc.save()",
			"set_value": 'frappe.db.set_value(LOG_DOCTYPE, doc, "seen", 1)',
			"db_set": 'doc.db_set("seen", 1)',
			"commit": "frappe.db.commit()",
			"cache": "frappe.cache().get_value(doc)",
			"publish_realtime": 'frappe.publish_realtime("erp_ai:agent_status", doc)',
		}
		cases = {
			f"{name} in the reader": (
				changed(clean, BOT_STATUS_FILE, f"\n\ndef touch(doc):\n\treturn {expression}\n"),
				f"{BOT_STATUS_FILE}:13: names {name}",
			)
			for name, expression in in_reader.items()
		}
		cases |= {
			f"{name} imported by the reader": (
				changed(clean, BOT_STATUS_FILE, f"from {module} import {name}\n"),
				f"{BOT_STATUS_FILE}:10: names {name}",
			)
			for module, name in (
				("erp_ai.agent.run_log", "write_entry"),
				("frappe.utils.background_jobs", "get_job"),
			)
		}
		panel_only = f"imports {BOT_STATUS_MODULE}; only {PANEL_FILE} may"
		cases |= {
			"another module imports the reader": (
				changed(clean, "agent/messages.py", "from erp_ai.agent import bot_status\n"),
				f"agent/messages.py:4: {panel_only}",
			),
			"the runner imports it lazily and relatively": (
				changed(clean, RUNNER_FILE, "def status(ticket):\n\tfrom . import bot_status\n"),
				f"{RUNNER_FILE}:2: {panel_only}",
			),
			"a module names it by its path": (
				changed(
					clean,
					"tasks.py",
					'import frappe\n\nSTATUS = frappe.get_attr("erp_ai.agent.bot_status.panel_status")\n',
				),
				f"tasks.py:3: names {BOT_STATUS_MODULE}; only {PANEL_FILE} may",
			),
			"the panel names the log": (
				changed(
					clean,
					PANEL_FILE,
					'\n\ndef rows(ticket):\n\treturn frappe.get_all("ERP AI Log", filters={"ticket": ticket})\n',
				),
				f'{PANEL_FILE}:9: names "{PANEL_FORBIDDEN_LOG_TEXT}"',
			),
			"the panel queries the log's table": (
				changed(clean, PANEL_FILE, 'SQL = "select name from `tabERP AI Log` where ticket=%s"\n'),
				f'{PANEL_FILE}:6: names "{PANEL_FORBIDDEN_LOG_TEXT}"',
			),
			"the reader missing": ({PANEL_FILE: clean[PANEL_FILE]}, f"{BOT_STATUS_FILE}: file missing"),
			"the panel missing": ({BOT_STATUS_FILE: clean[BOT_STATUS_FILE]}, f"{PANEL_FILE}: file missing"),
		}
		self.assertRuleSamples(check_bot_status_reader_follows_adr_048, clean, cases)

		self.assertRuleSamples(
			check_layer_imports,
			clean,
			{
				target: (
					changed(clean, BOT_STATUS_FILE, "from {} import {}\n".format(*target.rsplit(".", 1))),
					f"{BOT_STATUS_FILE}:10: imports {target} (ADR-048 QĐ 6",
				)
				for target in BOT_STATUS_FORBIDDEN_IMPORTS
			},
		)


if __name__ == "__main__":
	unittest.main()
