# Copyright (c) 2026, Kelvin Njenga and contributors
# For license information, please see license.txt
"""Tests for Onerc Incident: valid creation, Impact×Urgency priority derivation,
SLA stamping, the resolution guard, and pause/resume wiring.

Status changes step through valid workflow transitions (the Onerc Incident Workflow
is active), so these exercise the controller and the workflow together.
"""
import frappe
from frappe.tests import IntegrationTestCase

CAL = "_Test Inc Calendar"
IMP_HIGH, IMP_LOW = "_Test Impact High", "_Test Impact Low"
URG_HIGH, URG_LOW = "_Test Urgency High", "_Test Urgency Low"
PRI_CRIT, PRI_LOW = "_Test Priority Critical", "_Test Priority Low"
POLICY = "_Test Inc Default Policy"

IGNORE_TEST_RECORD_DEPENDENCIES = [
	"Geo Node",
	"Geo Level",
	"HD Ticket",
	"User",
	"Onerc Service",
	"Onerc Support Team",
	"Onerc Data Classification",
	"Onerc SLA Policy",
	"Onerc Priority",
	"Onerc Impact",
	"Onerc Urgency",
	"Onerc Priority Matrix",
	"Onerc Business Calendar",
]


def _ensure(doctype, name, payload):
	if frappe.db.exists(doctype, name):
		return name
	return frappe.get_doc({"doctype": doctype, **payload}).insert(ignore_permissions=True).name


class IntegrationTestOnercIncident(IntegrationTestCase):
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
				"business_start_time": "09:00:00",
				"business_end_time": "17:00:00",
			},
		)
		for imp in (IMP_HIGH, IMP_LOW):
			_ensure("Onerc Impact", imp, {"impact_name": imp})
		for urg in (URG_HIGH, URG_LOW):
			_ensure("Onerc Urgency", urg, {"urgency_name": urg})
		for pri in (PRI_CRIT, PRI_LOW):
			_ensure("Onerc Priority", pri, {"priority_name": pri})
		_ensure(
			"Onerc Priority Matrix",
			f"{IMP_HIGH}-{URG_HIGH}",
			{"impact": IMP_HIGH, "urgency": URG_HIGH, "priority": PRI_CRIT},
		)
		_ensure(
			"Onerc Priority Matrix",
			f"{IMP_LOW}-{URG_LOW}",
			{"impact": IMP_LOW, "urgency": URG_LOW, "priority": PRI_LOW},
		)
		_ensure(
			"Onerc SLA Policy",
			POLICY,
			{
				"policy_name": POLICY,
				"is_default": 1,
				"enabled": 1,
				"first_response_minutes": 60,
				"resolution_minutes": 480,
				"business_calendar": CAL,
			},
		)
		settings = frappe.get_single("Onerc Incidents Settings")
		if not any(row.status == "Pending" for row in settings.pause_statuses):
			settings.append("pause_statuses", {"status": "Pending"})
			settings.save(ignore_permissions=True)

	def _make_incident(self, **overrides):
		data = {
			"doctype": "Onerc Incident",
			"title": "_Test Incident",
			"description": "Something is broken",
			"impact": IMP_HIGH,
			"urgency": URG_HIGH,
		}
		data.update(overrides)
		return frappe.get_doc(data).insert(ignore_permissions=True)

	def _advance(self, doc, status, **fields):
		"""Move through one valid workflow transition (run as Administrator).

		Reloads first so background writes (Assignment Rule's _assign, Helpdesk link)
		that bumped `modified` don't trigger a TimestampMismatchError.
		"""
		doc.reload()
		doc.status = status
		for key, value in fields.items():
			setattr(doc, key, value)
		doc.save(ignore_permissions=True)
		return doc

	def test_valid_creation(self):
		inc = self._make_incident()
		self.assertTrue(frappe.db.exists("Onerc Incident", inc.name))
		self.assertEqual(inc.status, "New")
		self.assertTrue(inc.name.startswith("INC-"), f"unexpected name {inc.name}")

	def test_priority_auto_derived(self):
		inc = self._make_incident()
		self.assertEqual(inc.priority, PRI_CRIT)

	def test_priority_ignores_typed_value(self):
		inc = self._make_incident(priority=PRI_LOW)
		self.assertEqual(inc.priority, PRI_CRIT)

	def test_sla_targets_stamped_on_create(self):
		inc = self._make_incident()
		self.assertTrue(inc.sla_policy)
		self.assertTrue(inc.first_response_due)
		self.assertTrue(inc.resolution_due)

	def test_resolution_guard_blocks_without_fields(self):
		inc = self._make_incident()
		self._advance(inc, "Assigned")
		self._advance(inc, "In Progress")
		inc.status = "Resolved"
		with self.assertRaises(frappe.ValidationError):
			inc.save(ignore_permissions=True)

	def test_resolution_succeeds_with_fields(self):
		inc = self._make_incident()
		self._advance(inc, "Assigned")
		self._advance(inc, "In Progress")
		self._advance(inc, "Resolved", resolution_category="Fixed", resolution_summary="Restarted service")
		inc.reload()
		self.assertTrue(inc.resolved_on)
		self.assertTrue(inc.first_responded_on)
		self.assertEqual(inc.sla_status, "Fulfilled")

	def test_pause_then_resume(self):
		inc = self._make_incident()
		self._advance(inc, "Assigned")
		self._advance(inc, "In Progress")
		self._advance(inc, "Pending")
		inc.reload()
		self.assertTrue(inc.on_hold_since)
		self.assertEqual(inc.sla_status, "Paused")

		self._advance(inc, "In Progress")
		inc.reload()
		self.assertFalse(inc.on_hold_since)
		self.assertEqual(inc.sla_status, "Ongoing")
		self.assertGreaterEqual(inc.total_hold_minutes or 0, 0)
