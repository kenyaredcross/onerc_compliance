# Copyright (c) 2026, Kelvin Njenga and contributors
# For license information, please see license.txt
"""Tests for remote support: starting a session and the provider end webhook."""
import frappe
from frappe.tests import IntegrationTestCase

from onerc_compliance.onerc_incident_management import remote_support

CAL = "_Test RS Calendar"
IMP, URG, PRI = "_Test RS Impact", "_Test RS Urgency", "_Test RS Priority"
POLICY = "_Test RS Policy"

IGNORE_TEST_RECORD_DEPENDENCIES = [
	"User",
	"Geo Node",
	"Onerc Incident",
	"Onerc Remote Support Session",
	"Onerc Impact",
	"Onerc Urgency",
	"Onerc Priority",
	"Onerc Priority Matrix",
	"Onerc SLA Policy",
	"Onerc Business Calendar",
]


def _ensure(doctype, name, payload):
	if frappe.db.exists(doctype, name):
		return name
	return frappe.get_doc({"doctype": doctype, **payload}).insert(ignore_permissions=True).name


class IntegrationTestRemoteSupport(IntegrationTestCase):
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

	def _make_incident(self):
		return frappe.get_doc(
			{
				"doctype": "Onerc Incident",
				"title": "_Test RS Incident",
				"description": "x",
				"impact": IMP,
				"urgency": URG,
			}
		).insert(ignore_permissions=True)

	def test_start_session_creates_record(self):
		inc = self._make_incident()
		name = remote_support.start_session("Onerc Incident", inc.name)
		session = frappe.get_doc("Onerc Remote Support Session", name)
		self.assertEqual(session.reference_type, "Onerc Incident")
		self.assertEqual(session.reference_name, inc.name)
		self.assertEqual(session.status, "Requested")
		self.assertEqual(session.agent, frappe.session.user)
		self.assertTrue(session.session_token)
		self.assertTrue(session.started_on)

	def test_webhook_ends_session_and_posts_note(self):
		inc = self._make_incident()
		name = remote_support.start_session("Onerc Incident", inc.name)
		result = remote_support.session_webhook(session=name, duration=180, ended_on="2026-06-11 10:00:00")
		self.assertTrue(result["ok"])
		session = frappe.get_doc("Onerc Remote Support Session", name)
		self.assertEqual(session.status, "Ended")
		self.assertTrue(session.ended_on)
		self.assertEqual(int(session.duration), 180)
		notes = frappe.get_all(
			"Comment",
			filters={"reference_doctype": "Onerc Incident", "reference_name": inc.name, "comment_type": "Comment"},
			pluck="content",
		)
		self.assertTrue(any("Remote support session" in (c or "") for c in notes))

	def test_webhook_rejects_bad_secret(self):
		inc = self._make_incident()
		name = remote_support.start_session("Onerc Incident", inc.name)
		settings = frappe.get_single("Onerc Remote Support Settings")
		settings.webhook_secret = "s3cret"
		settings.save(ignore_permissions=True)
		with self.assertRaises(frappe.PermissionError):
			remote_support.session_webhook(session=name, secret="wrong", duration=10)
