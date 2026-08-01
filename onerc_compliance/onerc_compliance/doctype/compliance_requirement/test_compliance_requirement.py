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

	def test_reopen_closed_requirement_resets_overdue_and_allows_submit(self):
		emp_name = self._make_test_employee()

		# Active requirement auto-generates a Pending submission for the employee.
		req = self._make_requirement(title="_test-req-reopen", status="Active")
		sub_name = frappe.db.get_value(
			"Compliance Submission",
			{"requirement": req.name, "employee": emp_name},
			"name",
		)
		self.assertIsNotNone(sub_name)

		# Simulate the daily job after the deadline passes: the requirement is
		# Closed and the non-submitter's submission is flipped to Overdue.
		frappe.db.set_value("Compliance Requirement", req.name, "status", "Closed")
		frappe.db.set_value("Compliance Submission", sub_name, "status", "Overdue")

		# HR extends the deadline into the future and reopens the requirement.
		req.reload()
		req.deadline = "2099-12-31 23:59:00"
		req.status = "Active"
		req.save(ignore_permissions=True)

		# The Overdue submission is reset to Pending on reopen.
		self.assertEqual(
			frappe.db.get_value("Compliance Submission", sub_name, "status"),
			"Pending",
			"Reopening a Closed requirement must reset Overdue submissions to Pending",
		)

		# And it can now be submitted by staff (Pending -> Submitted is valid again).
		sub = frappe.get_doc("Compliance Submission", sub_name)
		sub.status = "Submitted"
		sub.save(ignore_permissions=True)
		self.assertEqual(
			frappe.db.get_value("Compliance Submission", sub_name, "status"),
			"Submitted",
		)

	def test_activating_with_past_deadline_raises(self):
		doc = self._make_requirement(title="_test-req-stale")
		doc.reload()
		doc.deadline = "2000-01-01 00:00:00"
		doc.status = "Active"
		with self.assertRaises(frappe.ValidationError):
			doc.save(ignore_permissions=True)

	# ------------------------------------------------------------------
	# Deadline edits — must never be blocked while the schema is unchanged
	# ------------------------------------------------------------------

	def _submission_snapshot(self, requirement_name):
		"""(name, status, modified) for every submission, to prove none were touched."""
		rows = frappe.get_all(
			"Compliance Submission",
			filters={"requirement": requirement_name},
			fields=["name", "status", "modified"],
			order_by="name",
		)
		return [(r.name, r.status, str(r.modified)) for r in rows]

	def test_active_requirement_deadline_can_be_extended(self):
		"""Extending an Active requirement's deadline saves cleanly and leaves
		its submissions completely untouched."""
		self._make_test_employee()
		req = self._make_requirement(
			title="_test-req-extend",
			status="Active",
			fields=[{"label": "Agree", "fieldtype": "Check", "mandatory": 0}],
		)

		before = self._submission_snapshot(req.name)
		self.assertTrue(before, "Expected at least one auto-generated submission")

		req.reload()
		req.deadline = "2098-06-30 23:59:00"
		req.save(ignore_permissions=True)

		self.assertEqual(
			frappe.db.get_value("Compliance Requirement", req.name, "deadline").strftime(
				"%Y-%m-%d %H:%M:%S"
			),
			"2098-06-30 23:59:00",
		)
		self.assertEqual(
			self._submission_snapshot(req.name),
			before,
			"Extending the deadline must not create, delete or modify any submission",
		)

	def test_closed_requirement_deadline_can_be_extended(self):
		"""The same holds while the requirement is Closed."""
		self._make_test_employee()
		req = self._make_requirement(
			title="_test-req-extend-closed",
			status="Active",
			fields=[{"label": "Agree", "fieldtype": "Check", "mandatory": 0}],
		)
		frappe.db.set_value("Compliance Requirement", req.name, "status", "Closed")
		before = self._submission_snapshot(req.name)

		req.reload()
		req.deadline = "2098-06-30 23:59:00"
		req.save(ignore_permissions=True)

		self.assertEqual(self._submission_snapshot(req.name), before)

	def test_deadline_edit_survives_blank_stored_fieldname(self):
		"""A legacy row with no fieldname must not be mistaken for a schema edit.

		`_validate_fields` fills the fieldname in from the label on every save, so
		comparing the raw column would flag a save that changed only the deadline.
		"""
		req = self._make_requirement(
			title="_test-req-blank-fieldname",
			status="Active",
			fields=[{"label": "Agree Here", "fieldtype": "Check", "mandatory": 0}],
		)
		frappe.db.set_value(
			"Compliance Requirement Field", req.fields[0].name, "fieldname", ""
		)

		req.reload()
		req.deadline = "2098-06-30 23:59:00"
		req.save(ignore_permissions=True)  # must not raise

	def test_deadline_edit_survives_select_options_whitespace(self):
		"""A trailing newline round-tripped by the Desk textarea is not a schema edit."""
		req = self._make_requirement(
			title="_test-req-opts-ws",
			status="Active",
			fields=[{
				"label": "Pick",
				"fieldtype": "Select",
				"options": "A\nB",
				"mandatory": 0,
			}],
		)
		frappe.db.set_value(
			"Compliance Requirement Field", req.fields[0].name, "options", "A\nB\n"
		)

		req.reload()
		req.fields[0].options = "A\nB"
		req.deadline = "2098-06-30 23:59:00"
		req.save(ignore_permissions=True)  # must not raise

	def test_deadline_edit_survives_stored_select_without_options(self):
		"""Pre-existing invalid data must not block an unrelated deadline edit."""
		req = self._make_requirement(
			title="_test-req-opts-blank",
			status="Active",
			fields=[{
				"label": "Pick",
				"fieldtype": "Select",
				"options": "A\nB",
				"mandatory": 0,
			}],
		)
		frappe.db.set_value(
			"Compliance Requirement Field", req.fields[0].name, "options", ""
		)

		req.reload()
		req.deadline = "2098-06-30 23:59:00"
		req.save(ignore_permissions=True)  # must not raise

	def test_schema_freeze_still_blocks_reorder_when_active(self):
		"""The freeze is not weakened: reordering fields remains a schema change."""
		req = self._make_requirement(
			title="_test-req-reorder",
			status="Active",
			fields=[
				{"label": "Alpha", "fieldtype": "Data", "mandatory": 0},
				{"label": "Beta", "fieldtype": "Data", "mandatory": 0},
			],
		)

		req.reload()
		req.fields.reverse()
		for idx, row in enumerate(req.fields):
			row.idx = idx + 1
		req.deadline = "2098-06-30 23:59:00"

		with self.assertRaises(frappe.ValidationError):
			req.save(ignore_permissions=True)
