# Copyright (c) 2026, Kelvin Njenga and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase

EXTRA_TEST_RECORD_DEPENDENCIES = []
IGNORE_TEST_RECORD_DEPENDENCIES = ["Employee", "Fiscal Year", "Company", "Department", "Designation", "User"]


class IntegrationTestComplianceSubmission(IntegrationTestCase):
	def setUp(self):
		# Clean up in correct order: submissions first, then requirements, then employees
		frappe.db.delete("Compliance Submission Value", {})
		frappe.db.delete("Compliance Review Action", {})
		subs = frappe.get_all(
			"Compliance Submission",
			filters={"employee": ["like", "_test-emp-%"]},
			fields=["name"],
		)
		for s in subs:
			frappe.delete_doc("Compliance Submission", s.name, force=True, ignore_permissions=True)
		frappe.db.delete("Compliance Requirement", {"title": ["like", "_test-sub-%"]})

	def tearDown(self):
		subs = frappe.get_all(
			"Compliance Submission",
			filters={"employee": ["like", "_test-emp-%"]},
			fields=["name"],
		)
		for s in subs:
			frappe.delete_doc("Compliance Submission", s.name, force=True, ignore_permissions=True)
		frappe.db.delete("Compliance Requirement", {"title": ["like", "_test-sub-%"]})
		frappe.db.delete("Employee", {"first_name": ["like", "_test-emp-%"]})

	def _make_requirement(self, title="_test-sub-req", fields=None):
		doc = frappe.get_doc({
			"doctype": "Compliance Requirement",
			"title": title,
			"target_type": "All Staff",
			"deadline": "2099-12-31 23:59:00",
			"status": "Active",
			"fields": fields or [],
		})
		doc.insert(ignore_permissions=True)
		return doc

	def _make_employee(self, suffix="sub-test"):
		first_name = f"_test-emp-{suffix}"
		existing = frappe.db.get_value("Employee", {"first_name": first_name}, "name")
		if existing:
			return existing
		emp = frappe.get_doc({
			"doctype": "Employee",
			"first_name": first_name,
			"employee_name": first_name,
			"status": "Active",
			"gender": "Male",
			"date_of_birth": "1990-01-01",
			"date_of_joining": "2020-01-01",
			"company": "United Nations",
		})
		emp.insert(ignore_permissions=True)
		return emp.name

	def _make_submission(self, requirement_name, employee_name, status="Pending"):
		doc = frappe.get_doc({
			"doctype": "Compliance Submission",
			"requirement": requirement_name,
			"employee": employee_name,
			"status": status,
		})
		doc.insert(ignore_permissions=True)
		return doc

	def test_valid_creation(self):
		req = self._make_requirement(title="_test-sub-req-create")
		emp = self._make_employee(suffix="create")
		sub = self._make_submission(req.name, emp)
		self.assertTrue(frappe.db.exists("Compliance Submission", sub.name))
		self.assertEqual(sub.status, "Pending")

	def test_submit_with_blank_mandatory_field_raises(self):
		req = self._make_requirement(
			title="_test-sub-req-mandatory",
			fields=[{
				"label": "Full Name",
				"fieldtype": "Data",
				"mandatory": 1,
			}],
		)
		emp = self._make_employee(suffix="mandatory")
		sub = self._make_submission(req.name, emp)

		sub.reload()
		sub.status = "Submitted"
		# values table is empty — the mandatory Data field has no answer

		with self.assertRaises(frappe.ValidationError):
			sub.save(ignore_permissions=True)
