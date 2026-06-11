# Copyright (c) 2026, Kelvin Njenga and contributors
# For license information, please see license.txt
"""Business-hours working-time engine for the Onerc ITSM SLA.

This module is intentionally free of any Frappe import at load time so the core
arithmetic can be unit-tested as plain Python. The only Frappe-aware entry point,
:func:`get_working_calendar`, imports frappe lazily.

Every SLA due-date and elapsed-time calculation in the ITSM suite routes through
:func:`add_working_minutes` and :func:`working_minutes_between`.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

# Onerc Business Calendar check fields, ordered Monday..Sunday to line up with
# datetime.date.weekday() (Monday=0 .. Sunday=6).
_WEEKDAY_FIELDS = (
    "work_monday",
    "work_tuesday",
    "work_wednesday",
    "work_thursday",
    "work_friday",
    "work_saturday",
    "work_sunday",
)

_MAX_DAY_SCAN = 1000  # safety bound when hunting for the next working day


@dataclass(frozen=True)
class WorkingCalendar:
    """A lightweight, DB-free description of business working time."""

    working_weekdays: frozenset  # ints, Monday=0 .. Sunday=6
    start: time
    end: time
    holidays: frozenset = frozenset()  # set of datetime.date

    def __post_init__(self):
        if not self.working_weekdays:
            raise ValueError("WorkingCalendar needs at least one working weekday")
        if self.end <= self.start:
            raise ValueError("Business end time must be after start time")

    def is_working_day(self, d: date) -> bool:
        return d.weekday() in self.working_weekdays and d not in self.holidays

    def day_start(self, d: date) -> datetime:
        return datetime.combine(d, self.start)

    def day_end(self, d: date) -> datetime:
        return datetime.combine(d, self.end)

    def _next_working_day(self, d: date) -> date:
        """First working day on or after ``d``."""
        for _ in range(_MAX_DAY_SCAN):
            if self.is_working_day(d):
                return d
            d += timedelta(days=1)
        raise ValueError("No working day found within scan bound")

    def normalize(self, moment: datetime) -> datetime:
        """Return the first working instant at or after ``moment``."""
        d = moment.date()
        if self.is_working_day(d):
            ds, de = self.day_start(d), self.day_end(d)
            if moment < ds:
                return ds
            if moment < de:
                return moment
        # non-working day, or at/after close of business -> next working day's open
        nd = self._next_working_day(d + timedelta(days=1))
        return self.day_start(nd)


def add_working_minutes(start: datetime, minutes: float, calendar: WorkingCalendar) -> datetime:
    """Datetime by which ``minutes`` of working time elapse from ``start``.

    Skips non-working hours, non-working weekdays and holidays. A span that
    finishes exactly at close of business returns that closing instant.
    """
    if minutes < 0:
        raise ValueError("minutes must be non-negative")
    cursor = calendar.normalize(start)
    remaining = float(minutes)
    if remaining == 0:
        return cursor
    while True:
        avail = (calendar.day_end(cursor.date()) - cursor).total_seconds() / 60.0
        if remaining <= avail:
            return cursor + timedelta(minutes=remaining)
        remaining -= avail
        nd = calendar._next_working_day(cursor.date() + timedelta(days=1))
        cursor = calendar.day_start(nd)


def working_minutes_between(start: datetime, end: datetime, calendar: WorkingCalendar) -> float:
    """Working minutes contained in the span ``[start, end]``."""
    if end <= start:
        return 0.0
    total = 0.0
    d = start.date()
    last = end.date()
    for _ in range(_MAX_DAY_SCAN):
        if d > last:
            break
        if calendar.is_working_day(d):
            seg_start = max(start, calendar.day_start(d))
            seg_end = min(end, calendar.day_end(d))
            if seg_end > seg_start:
                total += (seg_end - seg_start).total_seconds() / 60.0
        d += timedelta(days=1)
    return total


def get_working_calendar(calendar_name: str | None = None) -> WorkingCalendar:
    """Build a :class:`WorkingCalendar` from an ``Onerc Business Calendar`` record.

    Falls back to the default calendar configured in ``Onerc Incidents Settings``.
    Imports frappe lazily so the arithmetic above stays unit-testable.
    """
    import frappe
    from frappe.utils import get_time, getdate

    if not calendar_name:
        calendar_name = frappe.db.get_single_value(
            "Onerc Incidents Settings", "default_business_calendar"
        )
    if not calendar_name:
        frappe.throw("No Business Calendar supplied and no default set in Onerc Incidents Settings")

    doc = frappe.get_cached_doc("Onerc Business Calendar", calendar_name)
    weekdays = frozenset(idx for idx, field in enumerate(_WEEKDAY_FIELDS) if doc.get(field))
    holidays = frozenset(getdate(row.holiday_date) for row in (doc.holidays or []))
    return WorkingCalendar(
        working_weekdays=weekdays,
        start=get_time(doc.business_start_time),
        end=get_time(doc.business_end_time),
        holidays=holidays,
    )
