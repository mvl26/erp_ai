import os
import re
import time

import frappe

DUOI_CHO_PHEP = {".py", ".js", ".vue", ".json", ".md", ".html", ".css", ".txt"}
TEN_CAM = re.compile(
	r"(site_config\.json|common_site_config\.json|\.env|\.pem|\.key|" r"id_rsa|credential|secret|password)",
	re.I,
)

READ_MAX_LINES = 400
READ_DEFAULT_LINES = 200
SEARCH_MAX_HITS = 40
SEARCH_TIME_BUDGET_S = 30
SEARCH_FILE_MAX_BYTES = 1024 * 1024
SEARCH_TEXT_MAX_CHARS = 300
PATTERN_MIN_CHARS = 2
PATTERN_MAX_CHARS = 200
SKIPPED_DIRS = {"node_modules"}


def get_source_root():
	return os.path.realpath(os.path.dirname(os.path.dirname(frappe.get_app_path("frappe"))))


def _inside(root, full):
	return os.path.commonpath([root, full]) == root and full != root


def resolve_safe_path(rel):
	"""Return the real path of an allowed source file under the root, else None."""
	if not isinstance(rel, str) or not rel.strip() or "\0" in rel:
		return None
	root = os.path.realpath(get_source_root())
	full = os.path.realpath(os.path.join(root, rel))
	if not _inside(root, full):
		return None
	if TEN_CAM.search(os.path.relpath(full, root)):
		return None
	if os.path.isfile(full) and os.path.splitext(full)[1].lower() not in DUOI_CHO_PHEP:
		return None
	return full


def _refuse(reason):
	return {"ok": False, "reason": reason}


def _to_int(value, default):
	try:
		return int(value)
	except (TypeError, ValueError):
		return default


def read_source(args, ctx):
	try:
		args = args or {}
		full = resolve_safe_path(args.get("path"))
		if full is None or not os.path.isfile(full):
			return _refuse("Đường dẫn không hợp lệ hoặc không được phép đọc")
		if os.path.splitext(full)[1].lower() not in DUOI_CHO_PHEP:
			return _refuse("Đuôi file không được phép đọc")
		offset = max(_to_int(args.get("offset"), 1), 1)
		limit = min(max(_to_int(args.get("limit"), READ_DEFAULT_LINES), 1), READ_MAX_LINES)
		with open(full, encoding="utf-8", errors="replace") as handle:
			lines = handle.read().splitlines()
		chunk = lines[offset - 1 : offset - 1 + limit]
		return {
			"ok": True,
			"path": os.path.relpath(full, os.path.realpath(get_source_root())),
			"from_line": offset,
			"total_lines": len(lines),
			"content": "\n".join(chunk),
		}
	except Exception:
		return _refuse("Không đọc được file")


def _search_base(root, app):
	if not app:
		return root
	if not isinstance(app, str):
		return None
	base = os.path.realpath(os.path.join(root, app))
	if base == root or (_inside(root, base) and os.path.isdir(base)):
		return base
	return None


def _scan_file(full, rel, needle, hits):
	try:
		with open(full, encoding="utf-8", errors="replace") as handle:
			for number, line in enumerate(handle, 1):
				if needle in line.lower():
					text = line.strip()[:SEARCH_TEXT_MAX_CHARS]
					hits.append({"path": rel, "line": number, "text": text})
					if len(hits) >= SEARCH_MAX_HITS:
						return
	except OSError:
		return


def search_source(args, ctx):
	try:
		args = args or {}
		pattern = args.get("pattern")
		if not isinstance(pattern, str) or not PATTERN_MIN_CHARS <= len(pattern) <= PATTERN_MAX_CHARS:
			return _refuse("Mẫu tìm phải dài từ 2 đến 200 ký tự")
		extension = args.get("extension")
		if extension is not None and extension not in DUOI_CHO_PHEP:
			return _refuse("Đuôi file không được phép tìm")
		root = os.path.realpath(get_source_root())
		base = _search_base(root, args.get("app"))
		if base is None:
			return _refuse("Thư mục nằm ngoài mã nguồn cho phép")

		needle = pattern.lower()
		started = time.monotonic()
		hits = []
		for folder, dirnames, filenames in os.walk(base, followlinks=False):
			dirnames[:] = [d for d in dirnames if not d.startswith(".") and d not in SKIPPED_DIRS]
			for name in sorted(filenames):
				if time.monotonic() - started > SEARCH_TIME_BUDGET_S or len(hits) >= SEARCH_MAX_HITS:
					return {"ok": True, "hits": hits}
				if extension and os.path.splitext(name)[1].lower() != extension:
					continue
				full = resolve_safe_path(os.path.relpath(os.path.join(folder, name), root))
				if full is None or not os.path.isfile(full):
					continue
				if os.path.getsize(full) > SEARCH_FILE_MAX_BYTES:
					continue
				_scan_file(full, os.path.relpath(full, root), needle, hits)
		return {"ok": True, "hits": hits}
	except Exception:
		return _refuse("Không tìm được trong mã nguồn")
