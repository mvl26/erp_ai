import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime

from erp_ai.agent import lessons
from erp_ai.agent.agent_write_guard import refuse_agent_write

LOCKED_MESSAGE = "Không được đổi danh sách phiếu của kỳ rà soát"


class ERPAIReviewMonth(Document):
	# The name is the cycle key of ADR-033 QĐ 6: a second row for the same month is a DuplicateEntryError.
	def autoname(self):
		self.name = f"REV-{self.month}"

	# Reviewers write the verdicts; the agent account never writes this row (ADR-023 QĐ 5).
	def before_insert(self):
		refuse_agent_write(self)

	def validate(self):
		refuse_agent_write(self)
		self.check_ticket_list_locked()
		self.stamp_reviewer()

	def on_update(self):
		"""A verdict newly set to `Sai` teaches the bot one "don't do this" lesson; a `Sai` taken back retires it
		(a failure never blocks the save)."""
		before = self.get_doc_before_save()
		previous = {row.name: row.verdict for row in before.items} if before else {}
		for row in self.items:
			was_sai = previous.get(row.name) == "Sai"
			if row.verdict == "Sai" and not was_sai:
				lessons.safely(lessons.record_review_verdict, self.name, row.ticket, row.note or "")
			elif was_sai and row.verdict != "Sai":
				lessons.safely(lessons.retire_review_verdict, self.name, row.ticket)

	def on_trash(self):
		refuse_agent_write(self)

	def before_rename(self, old, new, merge=False):
		refuse_agent_write(self)

	def check_ticket_list_locked(self):
		"""The set and order of `ticket` in `items` is fixed once the job has created the row (AC-59)."""
		if self.is_new():
			return
		stored = frappe.get_all(
			"ERP AI Review Item",
			filters={"parent": self.name, "parenttype": self.doctype, "parentfield": "items"},
			order_by="idx",
			pluck="ticket",
		)
		if stored != [row.ticket for row in self.items]:
			frappe.throw(LOCKED_MESSAGE)

	def stamp_reviewer(self):
		"""A row whose verdict or note changed records who changed it and when."""
		before = self.get_doc_before_save()
		previous = {row.name: (row.verdict, row.note) for row in before.items} if before else {}
		for row in self.items:
			if (row.verdict or row.note) and previous.get(row.name) != (row.verdict, row.note):
				row.reviewed_by = frappe.session.user
				row.reviewed_at = now_datetime()
