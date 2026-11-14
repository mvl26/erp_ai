"""Lazy evidence that `bench restart` really happened (CHG-002 design 4.4 step 5, addendum A-6).

Read only: no subprocess, no filesystem writes, no enqueue. Every moment is turned into UTC epoch
seconds before comparing; `.timestamp()` is never called on a naive datetime here, because Python
would then read it in the process's own timezone.
"""

import datetime
import os
import zoneinfo

import psutil
import redis
from frappe.utils import background_jobs

from erp_ai.constants import RESTART_STATUS_CONFIRMED, RESTART_STATUS_UNCONFIRMED, RESTART_TIMEOUT_S

# Errors that mean "no evidence" rather than "not restarted".
NO_EVIDENCE_ERRORS = (redis.exceptions.RedisError, psutil.Error)


def epoch_of_naive_utc(dt: datetime.datetime) -> float:
	"""rq writes `birth_date` as a naive UTC datetime."""
	return dt.replace(tzinfo=datetime.timezone.utc).timestamp()


def epoch_of_system_time(dt: datetime.datetime, tz_name: str) -> float:
	"""Frappe Datetime fields (`restart_sent_at`) are naive, in the site's system timezone."""
	return dt.replace(tzinfo=zoneinfo.ZoneInfo(tz_name)).timestamp()


def web_started() -> float | None:
	"""Start of the gunicorn master serving this very request."""
	try:
		return psutil.Process(os.getppid()).create_time()
	except psutil.Error:
		return None


def workers_started() -> float | None:
	"""Birth of the oldest rq worker; no worker, a worker without birth date or an error → None."""
	try:
		workers = background_jobs.get_workers()
	except NO_EVIDENCE_ERRORS:
		return None
	births = [w.birth_date for w in workers]
	if not births or any(b is None for b in births):
		return None
	return min(epoch_of_naive_utc(b) for b in births)


def outcome(sent_epoch, now_epoch, web_epoch, workers_epoch):
	"""Both started after the send → confirmed; else past the deadline → unconfirmed; else None."""
	if web_epoch is not None and workers_epoch is not None and min(web_epoch, workers_epoch) > sent_epoch:
		return RESTART_STATUS_CONFIRMED
	if now_epoch > sent_epoch + RESTART_TIMEOUT_S:
		return RESTART_STATUS_UNCONFIRMED
	return None
