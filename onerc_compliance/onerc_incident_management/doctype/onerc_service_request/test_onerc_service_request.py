# Copyright (c) 2026, Kelvin Njenga and contributors
# For license information, please see license.txt
"""Tests for Onerc Service Request: catalogue pre-fill, the HOD->ICT approval chain
with the AUP-10.3 ICT gate, the deferred access-grant spawn flag, and fulfilment.

Status changes step through the active Onerc Service Request Workflow, so these
exercise the controller gate and the workflow together.
"""
import frappe
from frappe.tests import IntegrationTestCase

CAL = "_Test SR Calendar"
IMP_HIGH, URG_HIGH, PRI_CRIT = "_Test SR Impact", "_Test SR Urgency", "_Test SR Priority"
SR_TEAM = "_Test SR Team"
POLICY = "_Test SR Policy"
CAT_SIMPLE = "_Test Catalogue Simple"
CAT_SOFTWARE = "_Test Catalogue Software"

IGNORE_TEST_RECORD_DEPENDENCIES = [
	"Geo Node",
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
	"Onerc Request Catalogue Item",
]


def _ensure(doctype, name, payload):
	if frappe.db.exists(doctype, name):
		return name
	return frappe.get_doc({"doctype": doctype, **payload}).insert(ignore_permissions=True).name


class IntegrationTestOnercServiceRequest(IntegrationTestCase):
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
		_ensure("Onerc Impact", IMP_HIGH, {"impact_name": IMP_HIGH})
		_ensure("Onerc Urgency", URG_HIGH, {"urgency_name": URG_HIGH})
		_ensure("Onerc Priority", PRI_CRIT, {"priority_name": PRI_CRIT})
		_ensure(
			"Onerc Priority Matrix",
			f"{IMP_HIGH}-{URG_HIGH}",
			{"impact": IMP_HIGH, "urgency": URG_HIGH, "priority": PRI_CRIT},
		)
		_ensure(
			"Onerc Support Team",
			SR_TEAM,
			{"team_name": SR_TEAM, "members": [{"user": "Administrator", "team_role": "Lead"}]},
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
		_ensure(
			"Onerc Request Catalogue Item",
			CAT_SIMPLE,
			{
				"item_name": CAT_SIMPLE,
				"default_impact": IMP_HIGH,
				"default_urgency": URG_HIGH,
				"default_support_team": SR_TEAM,
				"requires_ict_approval": 0,
				"spawns_access_request": 0,
			},
		)
		_ensure(
			"Onerc Request Catalogue Item",
			CAT_SOFTWARE,
			{
				"item_name": CAT_SOFTWARE,
				"default_impact": IMP_HIGH,
				"default_urgency": URG_HIGH,
				"requires_ict_approval": 1,
				"spawns_access_request": 1,
			},
		)

	def _make_sr(self, catalogue, **overrides):
		data = {"doctype": "Onerc Service Request", "catalogue_item": catalogue, "subject": "_Test SR"}
		data.update(overrides)
		return frappe.get_doc(data).insert(ignore_permissions=True)

	def _advance(self, doc, status, **fields):
		"""Move through one valid workflow transition (run as Administrator)."""
		doc.status = status
		for key, value in fields.items():
			setattr(doc, key, value)
		doc.save(ignore_permissions=True)
		return doc

	def _approve(self, doc, stage):
		doc.append("approvals", {"approval_stage": stage, "status": "Approved"})

	def test_valid_creation(self):
		sr = self._make_sr(CAT_SIMPLE)
		self.assertTrue(frappe.db.exists("Onerc Service Request", sr.name))
		self.assertEqual(sr.status, "Draft")
		self.assertTrue(sr.name.startswith("SR-"), f"unexpected name {sr.name}")

	def test_catalogue_prefill_and_priority(self):
		sr = self._make_sr(CAT_SIMPLE)
		self.assertEqual(sr.impact, IMP_HIGH)
		self.assertEqual(sr.urgency, URG_HIGH)
		self.assertEqual(sr.support_team, SR_TEAM)
		self.assertEqual(sr.priority, PRI_CRIT)
		self.assertTrue(sr.requires_ict_approval == 0)

	def test_ict_gate_blocks_software_without_ict(self):
		sr = self._make_sr(CAT_SOFTWARE)
		self._advance(sr, "Pending HOD")
		self._approve(sr, "HOD")
		self._advance(sr, "Pending ICT")
		sr.status = "Approved"  # no ICT approval row yet
		with self.assertRaises(frappe.ValidationError):
			sr.save(ignore_permissions=True)

	def test_ict_gate_allows_software_with_ict(self):
		sr = self._make_sr(CAT_SOFTWARE)
		self._advance(sr, "Pending HOD")
		self._approve(sr, "HOD")
		self._advance(sr, "Pending ICT")
		self._approve(sr, "ICT")
		self._advance(sr, "Approved")
		self.assertEqual(sr.status, "Approved")

	def test_simple_item_needs_only_hod(self):
		sr = self._make_sr(CAT_SIMPLE)
		self._advance(sr, "Pending HOD")
		self._approve(sr, "HOD")
		self._advance(sr, "Approved")
		self.assertEqual(sr.status, "Approved")

	def test_approval_requires_hod(self):
		# Jumping straight to Approved is rejected (no workflow transition from Draft).
		sr = self._make_sr(CAT_SIMPLE)
		sr.status = "Approved"
		with self.assertRaises(frappe.ValidationError):
			sr.save(ignore_permissions=True)

	def test_spawn_sets_access_flag(self):
		sr = self._make_sr(CAT_SOFTWARE)
		self._advance(sr, "Pending HOD")
		self._approve(sr, "HOD")
		self._advance(sr, "Pending ICT")
		self._approve(sr, "ICT")
		self._advance(sr, "Approved")
		sr.reload()
		self.assertTrue(sr.access_provisioning_pending)

	def test_no_spawn_for_simple_item(self):
		sr = self._make_sr(CAT_SIMPLE)
		self._advance(sr, "Pending HOD")
		self._approve(sr, "HOD")
		self._advance(sr, "Approved")
		sr.reload()
		self.assertFalse(sr.access_provisioning_pending)

	def test_fulfilment_stamps_sla(self):
		sr = self._make_sr(CAT_SIMPLE)
		self._advance(sr, "Pending HOD")
		self._approve(sr, "HOD")
		self._advance(sr, "Approved")
		self._advance(sr, "In Fulfilment")
		self._advance(sr, "Fulfilled", fulfilment_notes="Done")
		sr.reload()
		self.assertTrue(sr.resolved_on)
		self.assertTrue(sr.fulfilled_on)
		self.assertEqual(sr.sla_status, "Fulfilled")
