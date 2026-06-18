# Copyright (c) 2026, Kelvin Njenga and contributors
# For license information, please see license.txt
"""Exhaustive tests for the SLA working-time helper.

Runs both standalone (``python3 test_working_time.py``) and under Frappe's test
runner. The arithmetic is pure Python, so no site/DB is required.

Reference week (Mon-Fri 09:00-17:00 = 480 working minutes/day):
    Mon 2026-06-08, Tue -09, Wed -10, Thu -11, Fri -12, Sat -13, Sun -14, Mon -15.
"""
import unittest
from datetime import date, datetime, time

try:  # under Frappe's test runner
    from onerc_compliance.onerc_incident_management.sla.working_time import (
        WorkingCalendar,
        add_working_minutes,
        working_minutes_between,
    )
except ImportError:  # standalone: python3 test_working_time.py
    from working_time import (
        WorkingCalendar,
        add_working_minutes,
        working_minutes_between,
    )

MON_FRI = frozenset({0, 1, 2, 3, 4})
WED_HOLIDAY = frozenset({date(2026, 6, 10)})


def cal(holidays=frozenset()):
    return WorkingCalendar(MON_FRI, time(9, 0), time(17, 0), holidays)


class AddWorkingMinutes(unittest.TestCase):
    def test_within_day(self):
        self.assertEqual(
            add_working_minutes(datetime(2026, 6, 8, 10, 0), 60, cal()),
            datetime(2026, 6, 8, 11, 0),
        )

    def test_overnight_rollover(self):
        self.assertEqual(
            add_working_minutes(datetime(2026, 6, 8, 16, 30), 60, cal()),
            datetime(2026, 6, 9, 9, 30),
        )

    def test_exact_close_boundary(self):
        self.assertEqual(
            add_working_minutes(datetime(2026, 6, 8, 16, 0), 60, cal()),
            datetime(2026, 6, 8, 17, 0),
        )

    def test_before_hours_start(self):
        self.assertEqual(
            add_working_minutes(datetime(2026, 6, 8, 7, 0), 60, cal()),
            datetime(2026, 6, 8, 10, 0),
        )

    def test_after_hours_start(self):
        self.assertEqual(
            add_working_minutes(datetime(2026, 6, 8, 18, 0), 60, cal()),
            datetime(2026, 6, 9, 10, 0),
        )

    def test_weekend_skip(self):
        self.assertEqual(
            add_working_minutes(datetime(2026, 6, 12, 16, 30), 60, cal()),
            datetime(2026, 6, 15, 9, 30),
        )

    def test_holiday_spanning(self):
        self.assertEqual(
            add_working_minutes(datetime(2026, 6, 9, 16, 30), 60, cal(WED_HOLIDAY)),
            datetime(2026, 6, 11, 9, 30),
        )

    def test_two_full_days(self):
        self.assertEqual(
            add_working_minutes(datetime(2026, 6, 8, 9, 0), 960, cal()),
            datetime(2026, 6, 9, 17, 0),
        )

    def test_weekend_start(self):
        self.assertEqual(
            add_working_minutes(datetime(2026, 6, 13, 12, 0), 60, cal()),
            datetime(2026, 6, 15, 10, 0),
        )

    def test_zero_minutes_normalizes(self):
        self.assertEqual(
            add_working_minutes(datetime(2026, 6, 8, 7, 0), 0, cal()),
            datetime(2026, 6, 8, 9, 0),
        )

    def test_multi_day_weekend_and_holiday(self):
        self.assertEqual(
            add_working_minutes(datetime(2026, 6, 9, 9, 0), 960, cal(WED_HOLIDAY)),
            datetime(2026, 6, 11, 17, 0),
        )


class WorkingMinutesBetween(unittest.TestCase):
    def test_full_day(self):
        self.assertEqual(
            working_minutes_between(datetime(2026, 6, 8, 9, 0), datetime(2026, 6, 8, 17, 0), cal()),
            480.0,
        )

    def test_overnight(self):
        self.assertEqual(
            working_minutes_between(datetime(2026, 6, 8, 16, 0), datetime(2026, 6, 9, 10, 0), cal()),
            120.0,
        )

    def test_weekend(self):
        self.assertEqual(
            working_minutes_between(datetime(2026, 6, 12, 16, 0), datetime(2026, 6, 15, 10, 0), cal()),
            120.0,
        )

    def test_holiday(self):
        self.assertEqual(
            working_minutes_between(
                datetime(2026, 6, 9, 16, 0), datetime(2026, 6, 11, 10, 0), cal(WED_HOLIDAY)
            ),
            120.0,
        )

    def test_fully_outside(self):
        self.assertEqual(
            working_minutes_between(datetime(2026, 6, 13, 10, 0), datetime(2026, 6, 14, 10, 0), cal()),
            0.0,
        )


if __name__ == "__main__":
    unittest.main()
