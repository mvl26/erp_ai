import frappe

from erp_ai import gateway


def run_for_ticket(ticket_name: str, trigger: str) -> None:
	subject, description = frappe.db.get_value("HD Ticket", ticket_name, ["subject", "description"])
	gateway.call_model(
		"classify",
		system=[{"type": "text", "text": "Phân loại phiếu hỗ trợ."}],
		messages=[{"role": "user", "content": f"Tiêu đề: {subject}\n\nNội dung:\n{description or ''}"}],
		max_tokens=400,
	)
