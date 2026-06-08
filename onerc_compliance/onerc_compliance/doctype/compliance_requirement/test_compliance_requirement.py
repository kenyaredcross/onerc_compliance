# Copyright (c) 2026, Kelvin Njenga and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase

EXTRA_TEST_RECORD_DEPENDENCIES = []
# Prevent Frappe's test-record generator from creating Fiscal Year 2025 records
# that conflict with the pre-existing 2025-2026 FY on onerc.localhost.
# All test data is created manually; this list has no effect on test correctness.
IGNORE_TEST_RECORD_DEPENDENCIES = ["Department", "Company", "Fiscal Year", "Employee", "Designation"]

_TEST_EMP_FIRST_NAME = "_test-emp-req-active"


class IntegrationTestComplianceRequirement(IntegrationTestCase):
	def _cleanup_test_data(self):
		# Delete submissions before requirements to avoid dangling links
		test_reqs = frappe.get_all(
			"Compliance Requirement",
			filters={"title": ["like", "_test-%"]},
			fields=["name"],
		)
		for req in test_reqs:
			frappe.db.delete("Compliance Submission", {"requirement": req.name})
		frappe.db.delete("Compliance Requirement", {"title": ["like", "_test-%"]})
		frappe.db.delete("Employee", {"first_name": _TEST_EMP_FIRST_NAME})

	def setUp(self):
		self._cleanup_test_data()

	def tearDown(self):
		self._cleanup_test_data()

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

	def _make_test_employee(self):
		emp = frappe.get_doc({
			"doctype": "Employee",
			"first_name": _TEST_EMP_FIRST_NAME,
			"employee_name": _TEST_EMP_FIRST_NAME,
			"status": "Active",
			"gender": "Male",
			"date_of_birth": "1990-01-01",
			"date_of_joining": "2020-01-01",
			"company": "United Nations",
		})
		emp.insert(ignore_permissions=True)
		return emp.name

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

	def test_active_requirement_creates_pending_submissions(self):
		emp_name = self._make_test_employee()

		# Creating directly in Active state must trigger _generate_submissions via on_update
		req = self._make_requirement(title="_test-req-auto-sub", status="Active")

		sub_name = frappe.db.get_value(
			"Compliance Submission",
			{"requirement": req.name, "employee": emp_name},
			"name",
		)
		self.assertIsNotNone(sub_name, "Expected a Pending submission auto-created on activation")
		self.assertEqual(
			frappe.db.get_value("Compliance Submission", sub_name, "status"),
			"Pending",
		)

		# Idempotency: re-saving an already-Active requirement must not create duplicates
		req.reload()
		req.save(ignore_permissions=True)

		count = frappe.db.count(
			"Compliance Submission",
			{"requirement": req.name, "employee": emp_name},
		)
		self.assertEqual(count, 1, "Re-saving an Active requirement must not duplicate submissions")
