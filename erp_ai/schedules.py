"""Scheduler entry points (ADR-033 QĐ 6, F-2): one line each, calling `agent.queue`; nothing is queued here."""

from erp_ai.agent import queue


def enqueue_daily_report() -> None:
	queue.enqueue_daily_report_job()


def enqueue_weekly_kpi() -> None:
	queue.enqueue_weekly_kpi_job()


def enqueue_monthly_review() -> None:
	queue.enqueue_monthly_review_job()
