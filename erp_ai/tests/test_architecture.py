"""Architecture tests (ADR-001..005, NFR-1, NFR-5, D-23): static scans of the source tree.

Nothing here imports product code or touches the database: files are read as text and parsed with `ast`.

Scanned files ("product code"): every `.py` file under `erp_ai/` except `test_*.py` (this also drops
`test_utils.py`), anything under a `tests/` directory and `__pycache__`. `eval/` is product code (it is an
entry layer, ADR-001), so it is scanned. The legacy-comment rule also scans `.json`, `.js` and `.html`
files of the same tree. `docs/` lives outside `erp_ai/` and is never scanned.

Every rule is a pure function over `{relative path: source}`, so the second class below can feed it
synthetic violating code (must be caught) and clean code (must not be flagged).
"""

import ast
import re
import shlex
import sys
import unittest
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = PACKAGE_ROOT.parent
CI_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "ci.yml"
PACKAGE = "erp_ai"

CLIENT_FILE = "gateway/client.py"
CREDENTIALS_FILE = "gateway/credentials.py"
QUEUE_FILE = "agent/queue.py"
POLICY_FILE = "agent/policy.py"
SOURCE_TOOL_FILE = "agent/tools/source.py"
READ_TOOL_FILE = "agent/tools/read.py"
HANDLERS_FILE = "handlers.py"
TOOLS_PREFIX = "agent/tools/"

# ADR-001 (layers), ADR-003 (handlers), ADR-005 (tools): (scope module, forbidden modules, reason).
LAYER_RULES = (
	(
		"erp_ai.gateway",
		(
			"erp_ai.agent",
			"erp_ai.eval",
			"erp_ai.handlers",
			"erp_ai.tasks",
			"erp_ai.install",
			"erp_ai.erp_ai_agent",
		),
		"ADR-001: gateway must not import agent, eval, handlers, scheduler, install or doctype controllers",
	),
	(
		"erp_ai.agent",
		("erp_ai.eval", "erp_ai.handlers", "erp_ai.tasks", "erp_ai.install", "erp_ai.erp_ai_agent"),
		"ADR-001: agent core must not import eval, handlers, scheduler, install or doctype controllers",
	),
	(
		"erp_ai.agent.tools",
		("erp_ai.gateway", "erp_ai.agent.runner", "erp_ai.agent.queue"),
		"ADR-001/ADR-005: tools never call the model, run the agent or enqueue jobs",
	),
	(
		"erp_ai.handlers",
		("erp_ai.gateway", "erp_ai.agent.runner"),
		"ADR-001/ADR-003: handlers enqueue by path string, never import gateway or runner",
	),
)
# NOT forbidden on purpose: erp_ai.eval -> erp_ai.agent.runner (entry layer -> agent core, ADR-001).

ENQUEUE_NAMES = ("enqueue", "enqueue_doc")
ENQUEUE_REQUIRED_KEYWORDS = ("queue", "timeout", "enqueue_after_commit", "job_id", "deduplicate")
ENQUEUE_TARGET = "erp_ai.agent.runner.run_for_ticket"

CONFIG_DOCTYPES = ("ERP AI Setting", "ERP AI Credential")
CONFIG_DOCTYPE_CONSTANTS = ("SETTING_DOCTYPE", "CREDENTIAL_DOCTYPE")
CONFIG_CONTROLLER_FILES = (
	"erp_ai_agent/doctype/erp_ai_setting/erp_ai_setting.py",
	"erp_ai_agent/doctype/erp_ai_credential/erp_ai_credential.py",
)
CONFIG_VARIABLE_NAMES = ("settings", "setting", "credential", "credentials")
DOC_GETTERS = ("get_doc", "get_single", "get_cached_doc", "new_doc")

TOOL_FORBIDDEN_CALL_SUFFIXES = ("db.set_value", "set_user", "db.multisql")
SQL_READ_ONLY = re.compile(r"^\s*(select|show|describe)\b", re.IGNORECASE)

# ADR-001: product code imports only the standard library, frappe, helpdesk and itself; `anthropic` (declared
# in pyproject.toml `dependencies`) only in gateway/client.py (NFR-5). Anything else, any other app, is a violation.
ALLOWED_TOP_LEVEL_MODULES = frozenset({PACKAGE, "frappe", "helpdesk", *sys.stdlib_module_names})
ANTHROPIC_MODULE = "anthropic"

POLICY_FIELDS = ("permission_level", "excluded_teams", "ai_opt_out")

SECRET_READERS = ("get_decrypted_password", "get_password")
SECRET_NAMES = ("api_key", "apikey", "secret", "password", "token")
LOG_SINK_CALLS = ("print", "frappe.log_error", "frappe.msgprint", "frappe.throw")
LOG_SINK_METHODS = ("debug", "info", "warning", "error", "exception", "critical")

STATUS_SCRIPT_FILE = "public/js/agent_status_indicator.js"
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
	r"\bcall\b",
	r"600",
	r"HD Form Script",
	r"^\s*(import|export)\b",
)
STATUS_SCRIPT_REQUIRED = ("textContent", "doc_subscribe", '"connect"', "setTimeout", "try", "expires_in_s")

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
	"""ADR-001 allowlist: stdlib, frappe, helpdesk, erp_ai; NFR-5/ADR-002: `anthropic` only in gateway/client.py."""
	violations = []
	for rel, source in only_python(sources).items():
		imports = imported_modules(parse(rel, source), module_name(rel), rel.endswith("__init__.py"))
		for lineno, target in imports:
			if module_in(target, ANTHROPIC_MODULE):
				if rel != CLIENT_FILE:
					violations.append(f"{rel}:{lineno}: imports {target} outside {CLIENT_FILE} (NFR-5)")
			elif target.split(".")[0] not in ALLOWED_TOP_LEVEL_MODULES:
				violations.append(
					f"{rel}:{lineno}: imports {target}, not stdlib/frappe/helpdesk/erp_ai (ADR-001: no other app or library)"
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
	"""ADR-003: the one call has the runner path and all five parameters."""
	source = sources.get(QUEUE_FILE)
	if source is None:
		return [f"{QUEUE_FILE}: file missing"]
	calls = [
		node
		for node in ast.walk(parse(QUEUE_FILE, source))
		if isinstance(node, ast.Call) and referenced_name(node.func) in ENQUEUE_NAMES
	]
	if len(calls) != 1:
		return [f"{QUEUE_FILE}: expected exactly one enqueue call, found {len(calls)}"]
	call = calls[0]
	violations = []
	first = call.args[0] if call.args else None
	if not (isinstance(first, ast.Constant) and first.value == ENQUEUE_TARGET):
		violations.append(
			violation(QUEUE_FILE, call, f"first argument must be the string {ENQUEUE_TARGET!r}")
		)
	given = {keyword.arg for keyword in call.keywords}
	for name in ENQUEUE_REQUIRED_KEYWORDS:
		if name not in given:
			violations.append(violation(QUEUE_FILE, call, f"missing keyword {name}="))
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
	"""
	violations = []
	for rel, source in only_python(scoped(sources, TOOLS_PREFIX)).items():
		for node in ast.walk(parse(rel, source)):
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


def check_subprocess_only_in_source_tool(sources: dict) -> list:
	violations = []
	for rel, source in only_python(sources).items():
		if rel == SOURCE_TOOL_FILE:
			continue
		tree = parse(rel, source)
		aliases = import_aliases(tree)
		for lineno, target in imported_modules(tree, module_name(rel), False):
			if module_in(target, "subprocess"):
				violations.append(f"{rel}:{lineno}: imports {target} outside {SOURCE_TOOL_FILE}")
		for node in ast.walk(tree):
			if isinstance(node, ast.Call):
				name = resolved_name(node.func, aliases)
				function = name.split(".")[-1]
				if name.startswith("subprocess.") or (
					name.startswith("os.")
					and (function in OS_SHELL_FUNCTIONS or function.startswith(OS_SHELL_PREFIXES))
				):
					violations.append(violation(rel, node, f"{name} outside {SOURCE_TOOL_FILE}"))
	return violations


def check_subprocess_call_shape(sources: dict) -> list:
	"""ADR-005: every subprocess call in the source tool has timeout=, a list command, no shell."""
	source = sources.get(SOURCE_TOOL_FILE)
	if source is None:
		return [f"{SOURCE_TOOL_FILE}: file missing"]
	violations = []
	tree = parse(SOURCE_TOOL_FILE, source)
	aliases = import_aliases(tree)
	for node in ast.walk(tree):
		if not isinstance(node, ast.Call):
			continue
		name = resolved_name(node.func, aliases)
		if not name.startswith("subprocess.") or name.split(".")[-1] not in (
			*SUBPROCESS_RUN_FUNCTIONS,
			"Popen",
		):
			continue
		keywords = {keyword.arg: keyword.value for keyword in node.keywords}
		if name.split(".")[-1] not in SUBPROCESS_RUN_FUNCTIONS:
			violations.append(
				violation(SOURCE_TOOL_FILE, node, f"{name}: only run()-style calls with timeout")
			)
		if "timeout" not in keywords:
			violations.append(violation(SOURCE_TOOL_FILE, node, f"{name} without timeout="))
		shell = keywords.get("shell")
		if shell is not None and not (isinstance(shell, ast.Constant) and shell.value is False):
			violations.append(violation(SOURCE_TOOL_FILE, node, f"{name} with shell="))
		command = node.args[0] if node.args else keywords.get("args")
		if isinstance(command, ast.Constant | ast.JoinedStr):
			violations.append(violation(SOURCE_TOOL_FILE, node, f"{name} with a string command, not a list"))
	return violations


def check_policy_fields_only_in_policy(sources: dict) -> list:
	"""ADR-003/ADR-005: level and send-policy fields are read only by agent/policy.py."""
	violations = []
	for rel, source in only_python(sources).items():
		if rel == POLICY_FILE:
			continue
		for node in ast.walk(parse(rel, source)):
			name = referenced_name(node)
			if name in POLICY_FIELDS:
				violations.append(violation(rel, node, f"reads {name} outside {POLICY_FILE}"))
			elif isinstance(node, ast.Constant) and node.value in POLICY_FIELDS:
				violations.append(violation(rel, node, f"reads {node.value!r} outside {POLICY_FILE}"))
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


def _allowed_legacy_nodes(rel: str, tree: ast.AST) -> set:
	target = LEGACY_ALLOWED_ASSIGNMENTS.get(rel)
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

	def test_subprocess_only_in_source_tool(self):
		scanned = only_python(self.sources)
		self.assertGreater(len(scanned), 0)
		self.assertIn("subprocess", self.sources[SOURCE_TOOL_FILE])
		self.assertEqual(check_subprocess_only_in_source_tool(self.sources), [])
		self.assertEqual(check_subprocess_call_shape(self.sources), [])

	def test_level_and_send_policy_fields_only_in_policy(self):
		scanned = only_python(self.sources)
		self.assertGreater(len(scanned), 0)
		self.assertIn("permission_level", self.sources[POLICY_FILE])
		self.assertEqual(check_policy_fields_only_in_policy(self.sources), [])

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
		self.assertIn("function setupForm({ doc, router })", script)
		for pattern in STATUS_SCRIPT_FORBIDDEN:
			self.assertIsNone(re.search(pattern, script, re.MULTILINE), f"forbidden in script: {pattern}")
		for token in STATUS_SCRIPT_REQUIRED:
			self.assertIn(token, script)

	def test_status_event_name_matches_script(self):
		match = re.search(r'^AGENT_STATUS_EVENT = "([^"]+)"', self.sources[CONSTANTS_FILE], re.MULTILINE)
		self.assertIsNotNone(match, "AGENT_STATUS_EVENT not found in constants.py")
		script = load_product_sources(suffixes=(".js",)).get(STATUS_SCRIPT_FILE)
		self.assertIsNotNone(script, f"{STATUS_SCRIPT_FILE} is missing")
		self.assertIn(f'"{match.group(1)}"', script)


# ---------------------------------------------------------------------------------------------------
# Tests of the scanners themselves (STD-TEST-8): violating code is caught, clean code is not flagged
# ---------------------------------------------------------------------------------------------------


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
		}
		for rel, source in cases.items():
			with self.subTest(rel=rel):
				self.assertCaught(check_layer_imports({rel: source}), rel)

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

	def test_enqueue_call_shape_requires_five_parameters(self):
		good = (
			"import frappe\n"
			f"frappe.enqueue({ENQUEUE_TARGET!r}, queue='long', timeout=1, enqueue_after_commit=True,"
			" job_id='j', deduplicate=True)\n"
		)
		self.assertEqual(check_enqueue_call_shape({QUEUE_FILE: good}), [])
		missing = good.replace(", deduplicate=True", "")
		self.assertCaught(check_enqueue_call_shape({QUEUE_FILE: missing}), "deduplicate")
		wrong_target = good.replace(ENQUEUE_TARGET, "erp_ai.other.fn")
		self.assertCaught(check_enqueue_call_shape({QUEUE_FILE: wrong_target}), "first argument")
		twice = good + good
		self.assertCaught(check_enqueue_call_shape({QUEUE_FILE: twice}), "exactly one")

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

	def test_tools_bypass_ignores_code_outside_tools(self):
		source = "import frappe\nfrappe.db.set_value('X', 'y', 'z', 1)\nfrappe.get_all('X')\n"
		self.assertEqual(check_tools_never_bypass_permissions({"agent/runner.py": source}), [])

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

	# policy fields -----------------------------------------------------------------------------

	def test_policy_fields_caught_outside_policy_and_allowed_inside(self):
		cases = (
			"def f(settings):\n\treturn settings.permission_level\n",
			"import frappe\nfrappe.db.get_single_value('ERP AI Setting', 'permission_level')\n",
			"import frappe\nfrappe.db.get_single_value('ERP AI Setting', 'excluded_teams')\n",
			"def f(ticket):\n\treturn ticket.ai_opt_out\n",
			"def f(ticket):\n\treturn ticket.get('ai_opt_out')\n",
		)
		for source in cases:
			with self.subTest(source=source):
				self.assertCaught(check_policy_fields_only_in_policy({"agent/tools/read.py": source}))
		inside = "def f(settings):\n\treturn settings.permission_level\n"
		self.assertEqual(check_policy_fields_only_in_policy({POLICY_FILE: inside}), [])
		prose = "def f():\n\t'''The only reader of permission_level.'''\n"
		self.assertEqual(check_policy_fields_only_in_policy({"handlers.py": prose}), [])

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


if __name__ == "__main__":
	unittest.main()
