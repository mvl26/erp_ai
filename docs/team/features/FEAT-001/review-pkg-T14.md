# Review package FEAT-001 T14 (BASE 7415abd..8fb14a8, branch team/FEAT-001-task-14)

Diff command: `git diff 7415abd..team/FEAT-001-task-14`

Commits:
- 8fb14a8 feat(alerts): send_alarm and send_notice with email recipients (FEAT-001)

Stat: erp_ai/alerts.py (+26, new), erp_ai/tests/test_alerts.py (+78, new)

## Diff: erp_ai/alerts.py (new)

```python
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
```

## Diff: erp_ai/tests/test_alerts.py (new)

```python
from unittest.mock import MagicMock, patch

import frappe
from frappe.tests.utils import FrappeTestCase

from erp_ai import alerts
from erp_ai.constants import LOGGER_NAME, SETTING_DOCTYPE, TITLE_ALARM
from erp_ai.test_utils import set_agent_settings

SENDMAIL = "erp_ai.alerts.frappe.sendmail"
LOG_ERROR = "erp_ai.alerts.frappe.log_error"
LOGGER = "erp_ai.alerts.frappe.logger"
FAKE_KEY = "sk-ant-SECRET-1234567890"
RECIPIENTS = ["a@example.com", "b@example.com"]


class TestAlerts(FrappeTestCase):
	def setUp(self):
		self.addCleanup(frappe.db.rollback)
		set_agent_settings(alert_recipients="a@example.com\nb@example.com")

	def test_send_alarm_logs_error_and_sends_one_mail(self):
		with patch(SENDMAIL) as sendmail, patch(LOG_ERROR) as log_error:
			alerts.send_alarm("Hết khóa", "Mọi khóa API đã hết")

		log_error.assert_called_once_with(TITLE_ALARM, "Mọi khóa API đã hết")
		self.assertEqual(sendmail.call_count, 1)
		mail = sendmail.call_args.kwargs
		self.assertEqual(mail["recipients"], RECIPIENTS)
		self.assertEqual(mail["subject"], "[erp_ai] Hết khóa")
		self.assertEqual(mail["message"], "Mọi khóa API đã hết")
		self.assertTrue(mail["delayed"])

	def test_send_notice_logs_info_without_error_log(self):
		logger = MagicMock()
		with (
			patch(SENDMAIL) as sendmail,
			patch(LOG_ERROR) as log_error,
			patch(LOGGER, return_value=logger) as get_logger,
		):
			alerts.send_notice("Khóa dự phòng", "Đã chuyển sang khóa 2")

		log_error.assert_not_called()
		get_logger.assert_called_with(LOGGER_NAME)
		logger.info.assert_called()
		self.assertEqual(sendmail.call_count, 1)
		mail = sendmail.call_args.kwargs
		self.assertEqual(mail["recipients"], RECIPIENTS)
		self.assertEqual(mail["subject"], "[erp_ai] Khóa dự phòng")
		self.assertTrue(mail["delayed"])

	def test_no_recipients_sends_no_mail_and_no_error(self):
		set_agent_settings(alert_recipients="")
		with patch(SENDMAIL) as sendmail, patch(LOG_ERROR) as log_error:
			alerts.send_alarm("x", "y")
			alerts.send_notice("x", "y")
		sendmail.assert_not_called()
		self.assertEqual(log_error.call_count, 1)

	def test_recipients_are_stripped_and_blank_lines_ignored(self):
		set_agent_settings(alert_recipients=" a@example.com \n\n  \nb@example.com\n")
		with patch(SENDMAIL) as sendmail:
			alerts.send_notice("x", "y")
		self.assertEqual(sendmail.call_args.kwargs["recipients"], RECIPIENTS)

	def test_content_never_contains_configured_api_keys(self):
		settings = frappe.get_single(SETTING_DOCTYPE)
		settings.append("credentials", {"label": "k1", "api_key": FAKE_KEY})
		settings.flags.ignore_validate = True
		settings.save(ignore_permissions=True)

		with patch(SENDMAIL) as sendmail, patch(LOG_ERROR) as log_error:
			alerts.send_alarm("Hết khóa", "Khóa 'k1' bị từ chối (401)")

		mail = sendmail.call_args.kwargs
		logged = " ".join(str(arg) for arg in log_error.call_args.args)
		for text in (mail["message"], mail["subject"], logged):
			self.assertNotIn(FAKE_KEY, text)
```
