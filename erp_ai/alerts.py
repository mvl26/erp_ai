import frappe

from erp_ai.constants import LOGGER_NAME, SETTING_DOCTYPE, TITLE_ALARM


def _recipients() -> list[str]:
	raw = frappe.get_single(SETTING_DOCTYPE).get("alert_recipients") or ""
	return [line.strip() for line in raw.splitlines() if line.strip()]


def _send_mail(subject: str, message: str) -> None:
	recipients = _recipients()
	if recipients:
		frappe.sendmail(recipients=recipients, subject=f"[erp_ai] {subject}", message=message, delayed=True)


def send_alarm(subject: str, message: str) -> None:
	"""Error Log + email to the alert recipients. Callers must keep keys out of `message`."""
	frappe.log_error(TITLE_ALARM, message)
	_send_mail(subject, message)


def send_notice(subject: str, message: str) -> None:
	"""Info log + email to the alert recipients; no Error Log."""
	frappe.logger(LOGGER_NAME).info("%s: %s", subject, message)
	_send_mail(subject, message)
