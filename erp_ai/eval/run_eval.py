from collections import Counter

from erp_ai.constants import CATEGORIES

VERDICT_HIGH = "≥ 85%"
VERDICT_MID = "70\u201385%"
VERDICT_LOW = "< 70%"
THRESHOLD_HIGH = 0.85
THRESHOLD_MID = 0.70


def _ratio(correct, count):
	return correct / count if count else 0.0


def _verdict(accuracy):
	if accuracy >= THRESHOLD_HIGH:
		return VERDICT_HIGH
	if accuracy >= THRESHOLD_MID:
		return VERDICT_MID
	return VERDICT_LOW


def _expected_category(ticket_type, mapping):
	if not ticket_type:
		return None
	for category in CATEGORIES:
		if (mapping.get(category) or {}).get("ticket_type") == ticket_type:
			return category
	return None


def compute_metrics(rows, mapping):
	"""Offline accuracy metrics for labeled tickets (design 3.7). Pure: no I/O.

	The label of a row is the category whose mapped ticket_type equals row["ticket_type"];
	rows without such a category are counted in skipped_unlabeled. A row whose
	predicted_category is empty or outside A-F is unclassified and counts as wrong.
	"""
	labeled_rows = []
	skipped_unlabeled = 0
	for row in rows:
		expected = _expected_category(row.get("ticket_type"), mapping)
		if expected is None:
			skipped_unlabeled += 1
			continue
		predicted = row.get("predicted_category")
		if predicted not in CATEGORIES:
			predicted = None
		labeled_rows.append((expected, predicted, row.get("owner")))

	per_category = {c: {"count": 0, "correct": 0, "accuracy": 0.0} for c in CATEGORIES}
	confusion = {e: dict.fromkeys(CATEGORIES, 0) for e in CATEGORIES}
	unclassified = 0
	for expected, predicted, _owner in labeled_rows:
		per_category[expected]["count"] += 1
		if predicted is None:
			unclassified += 1
			continue
		confusion[expected][predicted] += 1
		if predicted == expected:
			per_category[expected]["correct"] += 1
	for cell in per_category.values():
		cell["accuracy"] = _ratio(cell["correct"], cell["count"])

	owner_counts = Counter(owner for _e, _p, owner in labeled_rows)
	top_owner = min(owner_counts, key=lambda o: (-owner_counts[o], str(o))) if owner_counts else None
	non_top = [(e, p) for e, p, owner in labeled_rows if owner != top_owner]
	non_top_correct = sum(1 for e, p in non_top if p == e)

	labeled = len(labeled_rows)
	correct = sum(1 for e, p, _o in labeled_rows if p == e)
	accuracy = _ratio(correct, labeled)
	return {
		"labeled": labeled,
		"correct": correct,
		"accuracy": accuracy,
		"per_category": per_category,
		"confusion": confusion,
		"unclassified": unclassified,
		"top_owner": top_owner,
		"non_top_owner": {
			"count": len(non_top),
			"correct": non_top_correct,
			"accuracy": _ratio(non_top_correct, len(non_top)),
		},
		"verdict": _verdict(accuracy),
		"skipped_unlabeled": skipped_unlabeled,
	}


def _pct(value):
	return f"{value * 100:.1f}%"


def format_report(metrics):
	lines = [
		f"Overall accuracy: {_pct(metrics['accuracy'])} ({metrics['correct']}/{metrics['labeled']})",
		f"Unclassified (counted wrong): {metrics['unclassified']}",
		f"Skipped (no label): {metrics['skipped_unlabeled']}",
		"",
		"Per category:",
	]
	for category, cell in metrics["per_category"].items():
		lines.append(f"  {category}: {_pct(cell['accuracy'])} ({cell['correct']}/{cell['count']})")
	lines += ["", "Confusion matrix (rows = expected, columns = predicted):"]
	lines.append("     " + " ".join(f"{c:>3}" for c in CATEGORIES))
	for expected, row in metrics["confusion"].items():
		lines.append(f"  {expected}  " + " ".join(f"{row[c]:>3}" for c in CATEGORIES))
	non_top = metrics["non_top_owner"]
	lines += [
		"",
		f"Top author: {metrics['top_owner']}",
		f"Tickets by other authors: {_pct(non_top['accuracy'])} ({non_top['correct']}/{non_top['count']})",
		"",
		f"Verdict: {metrics['verdict']}",
	]
	return "\n".join(lines)
