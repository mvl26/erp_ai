import json
from collections import Counter

import frappe

from erp_ai import gateway
from erp_ai.agent import policy, site_facts
from erp_ai.agent.classification import DEFAULT_CATEGORY_MAPPING, load_mapping, parse_classification
from erp_ai.agent.prompts import build_classify_request
from erp_ai.agent.routing import decide_route, departments, load_routing_config
from erp_ai.agent.runner import CLASSIFY_MAX_TOKENS
from erp_ai.constants import CATEGORIES, SETTING_DOCTYPE

VERDICT_HIGH = "≥ 85%"
VERDICT_MID = "70\u201385%"
VERDICT_LOW = "< 70%"
THRESHOLD_HIGH = 0.85
THRESHOLD_MID = 0.70
SCORE_BINS = range(4)
MAX_TOKENS_STOP = "max_tokens"
PREDICTION_KEYS = ("category", "complexity", "importance", "priority", "agent_group")


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


def _match(rows, label_key, predicted_key):
	"""Accuracy over rows that carry a label and a prediction; the others are left out."""
	pairs = [
		(row[label_key], row[predicted_key])
		for row in rows
		if row.get(label_key) and row.get(predicted_key) is not None
	]
	correct = sum(1 for label, predicted in pairs if label == predicted)
	return {"count": len(pairs), "correct": correct, "accuracy": _ratio(correct, len(pairs))}


def _score_distribution(rows, key):
	counts = dict.fromkeys(SCORE_BINS, 0)
	for row in rows:
		value = row.get(key)
		if type(value) is int and value in counts:
			counts[value] += 1
	return counts


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
		"priority": _match(rows, "priority", "predicted_priority"),
		"team": _match(rows, "agent_group", "predicted_agent_group"),
		"score_distribution": {
			"complexity": _score_distribution(rows, "predicted_complexity"),
			"importance": _score_distribution(rows, "predicted_importance"),
		},
		"classify_output_tokens_max": max(
			(row["output_tokens"] for row in rows if isinstance(row.get("output_tokens"), int)), default=0
		),
		"classify_max_tokens_hits": sum(1 for row in rows if row.get("stop_reason") == MAX_TOKENS_STOP),
	}


def _pct(value):
	return f"{value * 100:.1f}%"


def _match_line(title, cell):
	return f"{title}: {_pct(cell['accuracy'])} ({cell['correct']}/{cell['count']})"


def _distribution_line(title, counts):
	return f"{title}: " + " ".join(f"{score}:{n}" for score, n in counts.items())


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
	distribution = metrics["score_distribution"]
	lines += [
		"",
		_match_line("Priority match", metrics["priority"]),
		_match_line("Team match", metrics["team"]),
		_distribution_line("Complexity distribution", distribution["complexity"]),
		_distribution_line("Importance distribution", distribution["importance"]),
		f"Classify output tokens max: {metrics['classify_output_tokens_max']}",
		f"Classify max_tokens hits: {metrics['classify_max_tokens_hits']}",
		"",
		f"Top author: {metrics['top_owner']}",
		f"Tickets by other authors: {_pct(non_top['accuracy'])} ({non_top['correct']}/{non_top['count']})",
		"",
		f"Verdict: {metrics['verdict']}",
	]
	return "\n".join(lines)


def _predict(row, routing, mapping):
	"""What the runner's classify and route steps would give this ticket; None values when it cannot classify."""
	prediction = dict.fromkeys((*PREDICTION_KEYS, "output_tokens", "stop_reason"))
	try:
		result = gateway.call_model(
			"classify",
			# CHG-018: the runner's request lets the model make a new tag; the eval sends the same
			**build_classify_request(
				row.get("subject"), row.get("description"), departments(routing), new_tags=True
			),
			max_tokens=CLASSIFY_MAX_TOKENS,
		)
	except gateway.GatewayError as exc:
		frappe.logger("erp_ai").warning(
			f"eval: classify failed line {row.get('_line')} kind={exc.kind} status={exc.status}"
		)
		return prediction
	# The call was made and paid for: its tokens and stop reason count even when the text is unreadable.
	prediction.update(output_tokens=(result.usage or {}).get("output_tokens"), stop_reason=result.stop_reason)
	classification = parse_classification(result.text)
	if classification is None:
		return prediction
	decision = decide_route(
		classification,
		row.get("subject"),
		mapping,
		routing,
		team_exists=site_facts.team_exists,
		is_excluded_team=policy.is_excluded_team,
		is_active_agent=site_facts.is_active_agent,
	)
	prediction.update(
		category=classification.category,
		complexity=classification.complexity,
		importance=classification.importance,
		priority=decision.priority,
		agent_group=decision.agent_group,
	)
	return prediction


def run(path):
	"""Classify a labeled JSONL with the runner's own prompt and print the accuracy report (design 3.7).

	Rows that already carry `predicted_category` are not sent. Nothing is written: no ERP AI Log, no ticket.
	"""
	rows = []
	with open(path, encoding="utf-8") as handle:
		for line_number, line in enumerate(handle, start=1):
			if not line.strip():
				continue
			try:
				row = json.loads(line)
			except json.JSONDecodeError as exc:
				raise ValueError(f"{path}: line {line_number}: invalid JSON ({exc.msg})") from exc
			row["_line"] = line_number
			rows.append(row)
	mapping = load_mapping(frappe.db.get_single_value(SETTING_DOCTYPE, "category_mapping")) or (
		DEFAULT_CATEGORY_MAPPING
	)
	routing = load_routing_config(frappe.db.get_single_value(SETTING_DOCTYPE, "routing_rules"))
	for row in rows:
		if not row.get("predicted_category"):
			prediction = _predict(row, routing, mapping)
			for key in PREDICTION_KEYS:
				row[f"predicted_{key}"] = prediction[key]
			row["output_tokens"] = prediction["output_tokens"]
			row["stop_reason"] = prediction["stop_reason"]
	metrics = compute_metrics(rows, mapping)
	print(format_report(metrics))
	return metrics
