# Copyright (c) 2026, Kelvin Njenga and contributors
# For license information, please see license.txt
"""Tests for Incident -> Helpdesk HD Ticket sync (Incident is the source of truth).

The toggle/guard behaviour is always validated; live HD Ticket creation runs only
when the `helpdesk` app is installed on the site.
"""
import frappe
from frappe.tests import IntegrationTestCase

CAL = "_Test HD Calendar"
IMP, URG, PRI = "_Test HD Impact", "_Test HD Urgency", "_Test HD Priority"
POLICY = "_Test HD Policy"


def _ensure(doctype, name, payload):
	if frappe.db.exists(doctype, name):
		return name
	return frappe.get_doc({"doctype": doctype, **payload}).insert(ignore_permissions=True).name


class IntegrationTestHelpdeskSync(IntegrationTestCase):
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
		_ensure("Onerc Impact", IMP, {"impact_name": IMP})
		_ensure("Onerc Urgency", URG, {"urgency_name": URG})
		_ensure("Onerc Priority", PRI, {"priority_name": PRI})
		_ensure("Onerc Priority Matrix", f"{IMP}-{URG}", {"impact": IMP, "urgency": URG, "priority": PRI})
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

	def _set_sync(self, enabled):
		settings = frappe.get_single("Onerc Incidents Settings")
		settings.sync_to_helpdesk = 1 if enabled else 0
		settings.save(ignore_permissions=True)

	def _make_incident(self):
		return frappe.get_doc(
			{
				"doctype": "Onerc Incident",
				"title": "_Test HD Incident",
				"description": "x",
				"impact": IMP,
				"urgency": URG,
			}
		).insert(ignore_permissions=True)

	def test_no_ticket_when_sync_disabled(self):
		self._set_sync(False)
		inc = self._make_incident()
		inc.reload()
		self.assertFalse(inc.helpdesk_ticket)

	def test_incident_creates_and_closes_hd_ticket(self):
		if "helpdesk" not in frappe.get_installed_apps():
			self.skipTest("Frappe Helpdesk app not installed on this site")
		self._set_sync(True)
		inc = self._make_incident()
		inc.reload()
		self.assertTrue(inc.helpdesk_ticket)
		self.assertTrue(frappe.db.exists("HD Ticket", inc.helpdesk_ticket))

		# Step through the active workflow to Resolved (reloading to absorb the
		# Assignment Rule's background _assign write).
		for status, fields in (
			("Assigned", {}),
			("In Progress", {}),
			("Resolved", {"resolution_category": "Fixed", "resolution_summary": "done"}),
		):
			inc.reload()
			inc.status = status
			for key, value in fields.items():
				setattr(inc, key, value)
			inc.save(ignore_permissions=True)
		ticket_status = frappe.db.get_value("HD Ticket", inc.helpdesk_ticket, "status")
		self.assertIn(ticket_status, ("Closed", "Resolved"))
