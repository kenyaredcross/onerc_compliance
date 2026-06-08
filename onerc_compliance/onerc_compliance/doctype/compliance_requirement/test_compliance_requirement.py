# Copyright (c) 2026, Kelvin Njenga and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase

EXTRA_TEST_RECORD_DEPENDENCIES = []
IGNORE_TEST_RECORD_DEPENDENCIES = ["Department", "Company", "Fiscal Year", "Employee", "Designation"]


class IntegrationTestComplianceRequirement(IntegrationTestCase):
	def setUp(self):
		frappe.db.delete("Compliance Requirement", {"title": ["like", "_test-%"]})

	def tearDown(self):
		frappe.db.delete("Compliance Requirement", {"title": ["like", "_test-%"]})

	def _make_requirement(self, title="_test-req", status="Draft", fields=None):
		doc = frappe.get_doc({
			"doctype": "Compliance Requirement",
			"title": title,
			"target_type": "All Staff",
			"deadline": "2099-12-31 23:59:00",
			"status": status,
			"fields": fields or [],
		})
		doc.insert(ignore_permissions=True)
		return doc

	def test_valid_creation(self):
		doc = self._make_requirement(title="_test-req-valid")
		self.assertTrue(frappe.db.exists("Compliance Requirement", doc.name))
		self.assertEqual(doc.status, "Draft")

	def test_schema_freeze_raises_when_active(self):
		doc = self._make_requirement(
			title="_test-req-freeze",
			fields=[{
				"label": "Agree",
				"fieldtype": "Check",
				"mandatory": 0,
			}],
		)
		doc.status = "Active"
		doc.save(ignore_permissions=True)

		# Reload and attempt to mutate the field schema
		doc.reload()
		original_label = doc.fields[0].label
		doc.fields[0].label = "Agree Updated"
		doc.fields[0].fieldname = frappe.scrub("Agree Updated")

		with self.assertRaises(frappe.ValidationError):
			doc.save(ignore_permissions=True)

		# Confirm the DB was not changed
		doc.reload()
		self.assertEqual(doc.fields[0].label, original_label)
