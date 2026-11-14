import json
import re
from dataclasses import dataclass, field

import frappe

from erp_ai.constants import CATEGORIES, CLASSIFICATION_FIELDS, CONFIDENCE_VALUES

PRIORITIES = ("Low", "Medium", "High", "Urgent")
PRIORITY_URGENT = "Urgent"
SCORE_VALUES = (1, 2, 3)
SCORE_REASON_MAX_WORDS = 25
# The guide spells the tag "[GẬP]"; "[GẤP]" is the standard spelling. Accept both.
URGENT_TAGS = ("[GẤP]", "[GẬP]")
# AC-28 (design.md:409): the split question lists at most 10 requests, each cut to 200 characters.
SPLIT_MAX_REQUESTS = 10
SPLIT_REQUEST_MAX_CHARS = 200

# D-8: ticket_type = category name; agent_group and priority per guide 16.1-16.2.
DEFAULT_CATEGORY_MAPPING = {
	"A": {"ticket_type": "Sự cố & lỗi hệ thống", "agent_group": "IT", "priority": "High"},
	"B": {"ticket_type": "Quản trị & cấu hình hệ thống", "agent_group": "IT", "priority": "Medium"},
	"C": {"ticket_type": "Phát triển tính năng & tự động hóa", "agent_group": "IT", "priority": "Medium"},
	"D": {"ticket_type": "Chuẩn hóa dữ liệu & quy trình trên ERP", "agent_group": "", "priority": "Medium"},
	"E": {"ticket_type": "Công việc nghiệp vụ ngoài IT", "agent_group": "", "priority": ""},
	"F": {"ticket_type": "Câu hỏi, phiếu nhiễu", "agent_group": "IT", "priority": "Low"},
}

_FENCE = re.compile(r"^```(?:json)?[ \t]*\n?(.*?)\n?```$", re.DOTALL)


@dataclass(frozen=True)
class Classification:
	category: str
	confidence: str
	reason: str = ""
	team: str | None = None
	priority: str | None = None
	needs_split: bool = False
	requests: list = field(default_factory=list)
	complexity: int = 0
	importance: int = 0
	score_reason: str = ""
	department: str | None = None


def _load_json_object(text):
	"""Parse a JSON object from plain text or from one ```json fence; None when it is not one."""
	if not isinstance(text, str):
		return None
	body = text.strip()
	fenced = _FENCE.match(body)
	if fenced:
		body = fenced.group(1).strip()
	try:
		data = json.loads(body)
	except (ValueError, RecursionError):
		return None
	return data if isinstance(data, dict) else None


def _read_scores(data):
	"""(complexity, importance, reason): a bad score in the pair means no score at all (D-4)."""
	complexity = data.get("do_phuc_tap")
	importance = data.get("do_quan_trong")
	for score in (complexity, importance):
		if type(score) is not int or score not in SCORE_VALUES:
			return 0, 0, ""
	reason = data.get("ly_do_diem")
	if not isinstance(reason, str):
		reason = ""
	return complexity, importance, " ".join(reason.split()[:SCORE_REASON_MAX_WORDS])


def parse_classification(text: str) -> Classification | None:
	"""Read the model's classification reply. Never raises; None when it cannot be trusted."""
	data = _load_json_object(text)
	if data is None:
		return None
	category = data.get("dau_muc")
	confidence = data.get("do_tin_cay")
	if not isinstance(category, str) or category not in CATEGORIES:
		return None
	if not isinstance(confidence, str) or confidence not in CONFIDENCE_VALUES:
		return None
	reason = data.get("ly_do")
	team = data.get("nhom")
	priority = data.get("uu_tien")
	requests = data.get("cac_yeu_cau")
	complexity, importance, score_reason = _read_scores(data)
	department = data.get("bo_phan")
	return Classification(
		category=category,
		confidence=confidence,
		reason=reason if isinstance(reason, str) else "",
		team=team if isinstance(team, str) else None,
		priority=priority if isinstance(priority, str) and priority in PRIORITIES else None,
		needs_split=data.get("can_tach") is True,
		requests=[r for r in requests if isinstance(r, str)] if isinstance(requests, list) else [],
		complexity=complexity,
		importance=importance,
		score_reason=score_reason,
		department=department if isinstance(department, str) else None,
	)


def split_request_comment(classification) -> str | None:
	"""AC-28: the comment asking the creator whether to split a merged ticket; None when there is nothing to ask.

	Blank requests are dropped and do not count towards the two needed.
	"""
	if classification is None or not classification.needs_split:
		return None
	requests = [r.strip() for r in classification.requests if r.strip()]
	if len(requests) < 2:
		return None
	listed = [r[:SPLIT_REQUEST_MAX_CHARS] for r in requests[:SPLIT_MAX_REQUESTS]]
	lines = [f"Phiếu này có vẻ gồm {len(listed)} yêu cầu:"]
	lines += [f"{number}. {request}" for number, request in enumerate(listed, start=1)]
	lines.append("Anh/chị xác nhận có muốn tách thành các phiếu riêng không? Bot không tự tách phiếu.")
	return "\n".join(lines)


def _mapping_error(raw):
	"""Return a specific message when raw is not a valid category_mapping, else None."""
	if not isinstance(raw, str) or not raw.strip():
		return "Ánh xạ đầu mục rỗng hoặc không phải văn bản JSON"
	try:
		data = json.loads(raw)
	except ValueError:
		return "Ánh xạ đầu mục không phải JSON hợp lệ"
	if not isinstance(data, dict):
		return "Ánh xạ đầu mục phải là một object JSON"
	for category, entry in data.items():
		if category not in CATEGORIES:
			return f"Đầu mục '{category}' không hợp lệ, chỉ nhận {', '.join(CATEGORIES)}"
		if not isinstance(entry, dict):
			return f"Đầu mục '{category}' phải là object có các khóa {', '.join(CLASSIFICATION_FIELDS)}"
		for key, value in entry.items():
			if key not in CLASSIFICATION_FIELDS:
				return f"Đầu mục '{category}' có khóa lạ '{key}', chỉ nhận {', '.join(CLASSIFICATION_FIELDS)}"
			if not isinstance(value, str):
				return f"Đầu mục '{category}', khóa '{key}' phải là chuỗi"
	return None


def validate_mapping(raw) -> None:
	"""Raise frappe.ValidationError with a specific message when raw is a bad category_mapping."""
	error = _mapping_error(raw)
	if error:
		frappe.throw(error)


def load_mapping(raw) -> dict:
	"""Parse category_mapping; a bad schema gives {} (validate_mapping already blocks it on save)."""
	if _mapping_error(raw):
		return {}
	return json.loads(raw)
