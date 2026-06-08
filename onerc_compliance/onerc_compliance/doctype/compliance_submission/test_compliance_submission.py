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

	def _make_requirement(self, title="_test-sub-req", fields=None, requires_review=1):
		doc = frappe.get_doc({
			"doctype": "Compliance Requirement",
			"title": title,
			"target_type": "All Staff",
			"deadline": "2099-12-31 23:59:00",
			"status": "Active",
			"requires_review": requires_review,
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

	def test_get_submissions_returns_submission_data(self):
		req = self._make_requirement(
			title="_test-sub-req-api",
			fields=[{"label": "Full Name", "fieldtype": "Data", "mandatory": 1}],
		)
		emp = self._make_employee(suffix="api-get")
		sub = self._make_submission(req.name, emp)

		from onerc_compliance.api.v1.compliance import get_submissions
		result = get_submissions(requirement=req.name)

		self.assertEqual(result["status"], "success")
		subs = result["data"]
		self.assertEqual(len(subs), 1)
		self.assertEqual(subs[0]["name"], sub.name)
		self.assertEqual(subs[0]["status"], "Pending")
		self.assertIn("field_schema", subs[0])
		self.assertEqual(len(subs[0]["field_schema"]), 1)
		self.assertEqual(subs[0]["field_schema"][0]["label"], "Full Name")
		self.assertIn("answers", subs[0])
		self.assertIn("review_actions", subs[0])

	def test_get_submissions_status_filter(self):
		req = self._make_requirement(title="_test-sub-req-filter")
		emp_a = self._make_employee(suffix="filter-a")
		emp_b = self._make_employee(suffix="filter-b")
		self._make_submission(req.name, emp_a, status="Pending")
		self._make_submission(req.name, emp_b, status="Overdue")

		from onerc_compliance.api.v1.compliance import get_submissions
		all_result = get_submissions(requirement=req.name)
		self.assertEqual(len(all_result["data"]), 2)

		pending_result = get_submissions(requirement=req.name, status="Pending")
		self.assertEqual(len(pending_result["data"]), 1)
		self.assertEqual(pending_result["data"][0]["status"], "Pending")

	def test_no_review_blank_mandatory_raises(self):
		# requires_review=0: submit_requirement sets status straight to Reviewed.
		# Mandatory-field validation must still fire on that path.
		req = self._make_requirement(
			title="_test-sub-req-no-review",
			requires_review=0,
			fields=[{
				"label": "Declaration",
				"fieldtype": "Data",
				"mandatory": 1,
			}],
		)
		emp = self._make_employee(suffix="no-review")
		sub = self._make_submission(req.name, emp)

		sub.reload()
		# Mimic what submit_requirement does when requires_review is falsy
		sub.status = "Reviewed"
		# values table is empty — Declaration field has no answer

		with self.assertRaises(frappe.ValidationError):
			sub.save(ignore_permissions=True)

		# Must not have landed in Reviewed
		self.assertEqual(
			frappe.db.get_value("Compliance Submission", sub.name, "status"),
			"Pending",
		)
