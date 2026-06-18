# Copyright (c) 2026, Kelvin Njenga and contributors
# For license information, please see license.txt
"""Frappe-level tests for the SLA engine: policy resolution, business-hours target
stamping and pause/resume. The pure working-time arithmetic is covered separately
in test_working_time.py.
"""
from datetime import date, datetime
from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase

from onerc_compliance.onerc_incident_management.sla import policy as sla
from onerc_compliance.onerc_incident_management.sla.working_time import get_working_calendar

CAL = "_Test ITSM Calendar"
PRIORITY = "_Test Critical"
DEFAULT_POLICY = "_Test Default Policy"
CRITICAL_POLICY = "_Test Critical Policy"


def _ensure(doctype, name, payload):
	if frappe.db.exists(doctype, name):
		return name
	return frappe.get_doc({"doctype": doctype, **payload}).insert(ignore_permissions=True).name


class IntegrationTestOnercSLAEngine(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		_ensure(
			"Onerc Business Calendar",
			CAL,
			{
				"calendar_name": CAL,
				"work_monday": 1,
				"work_tuesday": 1,
				"work_wednesday": 1,
				"work_thursday": 1,
				"work_friday": 1,
				"work_saturday": 0,
				"work_sunday": 0,
				"business_start_time": "09:00:00",
				"business_end_time": "17:00:00",
				"holidays": [{"holiday_date": "2026-06-10", "holiday_name": "Test Holiday"}],
			},
		)
		_ensure("Onerc Priority", PRIORITY, {"priority_name": PRIORITY})
		_ensure(
			"Onerc SLA Policy",
			DEFAULT_POLICY,
			{
				"policy_name": DEFAULT_POLICY,
				"is_default": 1,
				"enabled": 1,
				"first_response_minutes": 60,
				"resolution_minutes": 480,
				"business_calendar": CAL,
			},
		)
		_ensure(
			"Onerc SLA Policy",
			CRITICAL_POLICY,
			{
				"policy_name": CRITICAL_POLICY,
				"enabled": 1,
				"priority": PRIORITY,
				"first_response_minutes": 30,
				"resolution_minutes": 240,
				"business_calendar": CAL,
			},
		)

	def test_calendar_loads_holiday_and_weekdays(self):
		cal = get_working_calendar(CAL)
		self.assertIn(date(2026, 6, 10), cal.holidays)
		self.assertEqual(cal.working_weekdays, frozenset({0, 1, 2, 3, 4}))

	def test_resolve_specific_policy_wins(self):
		self.assertEqual(sla.resolve_policy(frappe._dict(priority=PRIORITY)), CRITICAL_POLICY)

	def test_resolve_falls_back_to_default(self):
		self.assertEqual(sla.resolve_policy(frappe._dict(priority=None)), DEFAULT_POLICY)

	def test_stamp_targets_respects_business_hours(self):
		# Mon 2026-06-08 16:00 + 30 min response, + 240 min resolution.
		doc = frappe._dict(priority=PRIORITY, creation=datetime(2026, 6, 8, 16, 0, 0))
		sla.stamp_targets(doc)
		self.assertEqual(doc.sla_policy, CRITICAL_POLICY)
		self.assertEqual(doc.first_response_due, datetime(2026, 6, 8, 16, 30, 0))
		# 240: Mon 16:00->17:00 = 60, remaining 180 -> Tue 09:00 + 180 = Tue 12:00
		self.assertEqual(doc.resolution_due, datetime(2026, 6, 9, 12, 0, 0))

	def test_pause_resume_pushes_due_dates(self):
		doc = frappe._dict(
			sla_policy=DEFAULT_POLICY,
			first_response_due=datetime(2026, 6, 8, 16, 0, 0),
			resolution_due=datetime(2026, 6, 9, 12, 0, 0),
			first_responded_on=None,
			resolved_on=None,
			on_hold_since=datetime(2026, 6, 8, 10, 0, 0),
			total_hold_minutes=0,
		)
		# Held Mon 10:00 -> Mon 12:00 = 120 working minutes.
		with patch.object(sla, "now_datetime", return_value=datetime(2026, 6, 8, 12, 0, 0)):
			sla.apply_resume(doc)
		self.assertEqual(doc.total_hold_minutes, 120)
		# first_response_due Mon 16:00 + 120 -> Tue 10:00
		self.assertEqual(doc.first_response_due, datetime(2026, 6, 9, 10, 0, 0))
		# resolution_due Tue 12:00 + 120 -> Tue 14:00
		self.assertEqual(doc.resolution_due, datetime(2026, 6, 9, 14, 0, 0))
		self.assertIsNone(doc.on_hold_since)
		self.assertEqual(doc.sla_status, "Ongoing")
