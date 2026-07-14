# Copyright (c) 2026, Kelvin Njenga and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase

EXTRA_TEST_RECORD_DEPENDENCIES = []
IGNORE_TEST_RECORD_DEPENDENCIES = ["Employee", "Fiscal Year", "Company", "Department", "Designation", "User"]

_STAFF_USER_EMAIL = "_test-compliance-employee@example.com"


class IntegrationTestComplianceSubmission(IntegrationTestCase):
	def setUp(self):
		# Delete ALL submissions for test requirements — catches auto-generated ones for any
		# active employee (including demo employees) that _generate_submissions() created.
		test_req_names = frappe.get_all(
			"Compliance Requirement",
			filters={"title": ["like", "_test-sub-%"]},
			pluck="name",
		)
		for req_name in test_req_names:
			for sub_name in frappe.get_all(
				"Compliance Submission",
				filters={"requirement": req_name},
				pluck="name",
			):
				frappe.delete_doc("Compliance Submission", sub_name, force=True, ignore_permissions=True)
		# Belt-and-suspenders: clear any remaining test-employee submissions
		for s in frappe.get_all(
			"Compliance Submission",
			filters={"employee": ["like", "_test-emp-%"]},
			fields=["name"],
		):
			frappe.delete_doc("Compliance Submission", s.name, force=True, ignore_permissions=True)
		frappe.db.delete("Compliance Requirement", {"title": ["like", "_test-sub-%"]})

	def tearDown(self):
		frappe.set_user("Administrator")  # always restore before cleanup
		test_req_names = frappe.get_all(
			"Compliance Requirement",
			filters={"title": ["like", "_test-sub-%"]},
			pluck="name",
		)
		for req_name in test_req_names:
			for sub_name in frappe.get_all(
				"Compliance Submission",
				filters={"requirement": req_name},
				pluck="name",
			):
				frappe.delete_doc("Compliance Submission", sub_name, force=True, ignore_permissions=True)
		for s in frappe.get_all(
			"Compliance Submission",
			filters={"employee": ["like", "_test-emp-%"]},
			fields=["name"],
		):
			frappe.delete_doc("Compliance Submission", s.name, force=True, ignore_permissions=True)
		frappe.db.delete("Compliance Requirement", {"title": ["like", "_test-sub-%"]})
		frappe.db.delete("Employee", {"first_name": ["like", "_test-emp-%"]})
		if frappe.db.exists("User", _STAFF_USER_EMAIL):
			frappe.delete_doc("User", _STAFF_USER_EMAIL, force=True, ignore_permissions=True)
		empty_dept = frappe.db.get_value(
			"Department", {"department_name": "_Test Compliance Empty Dept"}, "name"
		)
		if empty_dept:
			frappe.delete_doc("Department", empty_dept, force=True, ignore_permissions=True)

	def _make_staff_user(self):
		"""Create (or reuse) a user that has the Employee role only — no Compliance Officer."""
		if not frappe.db.exists("User", _STAFF_USER_EMAIL):
			user = frappe.get_doc({
				"doctype": "User",
				"email": _STAFF_USER_EMAIL,
				"first_name": "_Test",
				"last_name": "Employee",
				"enabled": 1,
				"user_type": "System User",
				"roles": [{"role": "Employee"}],
			})
			user.insert(ignore_permissions=True)
		return _STAFF_USER_EMAIL

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

	def _make_submission(
		self, requirement_name, employee_name, status="Pending", display_name=None, department=None
	):
		doc = frappe.get_doc({
			"doctype": "Compliance Submission",
			"requirement": requirement_name,
			"employee": employee_name,
			"status": status,
		})
		# employee_name is read-only (normally fetched from Employee); set it directly so
		# search tests have a deterministic display name to match against.
		if display_name is not None:
			doc.employee_name = display_name
		if department is not None:
			doc.department = department
		doc.insert(ignore_permissions=True)
		return doc

	def _make_empty_department(self):
		"""A department with no employees, used to scope a requirement so that
		_generate_submissions() creates ZERO auto-submissions. Every submission on
		the requirement is then one the test created — making counts deterministic."""
		name = "_Test Compliance Empty Dept"
		existing = frappe.db.get_value("Department", {"department_name": name}, "name")
		if existing:
			return existing
		dept = frappe.get_doc({
			"doctype": "Department",
			"department_name": name,
			"company": "United Nations",
		})
		dept.insert(ignore_permissions=True)
		return dept.name

	def _make_scoped_requirement(self, title, dept):
		"""Requirement targeting a single department, so auto-generation is confined
		to that department's employees."""
		doc = frappe.get_doc({
			"doctype": "Compliance Requirement",
			"title": title,
			"target_type": "By Department",
			"target_departments": [{"department": dept}],
			"deadline": "2099-12-31 23:59:00",
			"status": "Active",
			"requires_review": 1,
			"fields": [],
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
		# Other active employees (e.g. demo data) may also have auto-generated submissions;
		# locate the test employee's submission by name instead of asserting total count.
		our_sub = next((s for s in subs if s["name"] == sub.name), None)
		self.assertIsNotNone(our_sub, "Test employee submission not found in get_submissions result")
		self.assertEqual(our_sub["status"], "Pending")
		self.assertIn("field_schema", our_sub)
		self.assertEqual(len(our_sub["field_schema"]), 1)
		self.assertEqual(our_sub["field_schema"][0]["label"], "Full Name")
		self.assertIn("answers", our_sub)
		self.assertIn("review_actions", our_sub)

	def test_get_submissions_status_filter(self):
		req = self._make_requirement(title="_test-sub-req-filter")
		emp_a = self._make_employee(suffix="filter-a")
		emp_b = self._make_employee(suffix="filter-b")
		self._make_submission(req.name, emp_a, status="Pending")
		sub_b = self._make_submission(req.name, emp_b, status="Overdue")

		from onerc_compliance.api.v1.compliance import get_submissions
		all_result = get_submissions(requirement=req.name)
		# Other active employees may have auto-generated Pending submissions; count >= 2.
		self.assertGreaterEqual(len(all_result["data"]), 2)

		# Verify status filter returns only the requested status.
		pending_result = get_submissions(requirement=req.name, status="Pending")
		self.assertTrue(
			all(s["status"] == "Pending" for s in pending_result["data"]),
			"Pending filter returned non-Pending submissions",
		)

		# Only emp_b was explicitly set to Overdue, so Overdue filter returns exactly 1.
		overdue_result = get_submissions(requirement=req.name, status="Overdue")
		self.assertEqual(len(overdue_result["data"]), 1)
		self.assertEqual(overdue_result["data"][0]["name"], sub_b.name)

	def test_get_submissions_search_by_partial_name(self):
		dept = self._make_empty_department()
		req = self._make_scoped_requirement("_test-sub-req-search", dept)
		emp_a = self._make_employee(suffix="search-a")
		emp_b = self._make_employee(suffix="search-b")
		self._make_submission(req.name, emp_a, display_name="Wanjiru Kamau")
		self._make_submission(req.name, emp_b, display_name="Otieno Odhiambo")

		from onerc_compliance.api.v1.compliance import get_submissions

		# Partial, case-insensitive match on employee_name.
		result = get_submissions(requirement=req.name, search="wanj")
		names = [s["employee_name"] for s in result["data"]]
		self.assertEqual(names, ["Wanjiru Kamau"])
		self.assertEqual(result["meta"]["total_count"], 1)

		# A term matching neither name returns nothing.
		empty = get_submissions(requirement=req.name, search="zzznomatch")
		self.assertEqual(empty["data"], [])
		self.assertEqual(empty["meta"]["total_count"], 0)

	def test_get_submissions_search_by_employee_id(self):
		dept = self._make_empty_department()
		req = self._make_scoped_requirement("_test-sub-req-search-id", dept)
		emp_a = self._make_employee(suffix="search-id-a")
		self._make_submission(req.name, emp_a, display_name="No Name Match")

		from onerc_compliance.api.v1.compliance import get_submissions

		# Search matches the employee ID even when the display name doesn't.
		result = get_submissions(requirement=req.name, search=emp_a.lower())
		matched = [s["name"] for s in result["data"]]
		self.assertEqual(len(matched), 1)

	def test_get_submissions_department_filter(self):
		dept = self._make_empty_department()
		req = self._make_scoped_requirement("_test-sub-req-dept", dept)
		emp_a = self._make_employee(suffix="dept-a")
		emp_b = self._make_employee(suffix="dept-b")
		emp_c = self._make_employee(suffix="dept-c")
		self._make_submission(req.name, emp_a, display_name="A", department="Accounts")
		self._make_submission(req.name, emp_b, display_name="B", department="Marketing")
		# emp_c: no department -> Unassigned
		self._make_submission(req.name, emp_c, display_name="C")

		from onerc_compliance.api.v1.compliance import get_submissions

		acc = get_submissions(requirement=req.name, department="Accounts")
		self.assertEqual([s["department"] for s in acc["data"]], ["Accounts"])
		self.assertEqual(acc["meta"]["total_count"], 1)

		# "Unassigned" matches the submission with no department.
		un = get_submissions(requirement=req.name, department="Unassigned")
		self.assertEqual(un["meta"]["total_count"], 1)
		self.assertEqual(un["data"][0]["employee_name"], "C")
		self.assertEqual(un["data"][0]["department"], "")

		# No filter returns all three.
		allr = get_submissions(requirement=req.name)
		self.assertEqual(allr["meta"]["total_count"], 3)

	def test_get_submissions_filters_combine(self):
		dept = self._make_empty_department()
		req = self._make_scoped_requirement("_test-sub-req-combine", dept)
		emp_a = self._make_employee(suffix="combine-a")
		emp_b = self._make_employee(suffix="combine-b")
		emp_c = self._make_employee(suffix="combine-c")
		# Same department, differing status + name.
		self._make_submission(
			req.name, emp_a, status="Overdue", display_name="Kamau One", department="Accounts"
		)
		self._make_submission(
			req.name, emp_b, status="Pending", display_name="Kamau Two", department="Accounts"
		)
		self._make_submission(
			req.name, emp_c, status="Overdue", display_name="Wanjiru Three", department="Marketing"
		)

		from onerc_compliance.api.v1.compliance import get_submissions

		# status + department + search all AND together.
		res = get_submissions(
			requirement=req.name, status="Overdue", department="Accounts", search="kamau"
		)
		self.assertEqual(res["meta"]["total_count"], 1)
		self.assertEqual(res["data"][0]["employee_name"], "Kamau One")

		# search alone spans both Accounts "Kamau" rows.
		res2 = get_submissions(requirement=req.name, search="kamau")
		self.assertEqual(res2["meta"]["total_count"], 2)

	def test_get_submissions_pagination(self):
		dept = self._make_empty_department()
		req = self._make_scoped_requirement("_test-sub-req-page", dept)
		for i in range(5):
			emp = self._make_employee(suffix=f"page-{i}")
			self._make_submission(req.name, emp, display_name=f"Person {i}")

		from onerc_compliance.api.v1.compliance import get_submissions

		page1 = get_submissions(requirement=req.name, page=1, page_length=2)
		self.assertEqual(page1["meta"]["total_count"], 5)
		self.assertEqual(page1["meta"]["page"], 1)
		self.assertEqual(len(page1["data"]), 2)

		page3 = get_submissions(requirement=req.name, page=3, page_length=2)
		self.assertEqual(page3["meta"]["total_count"], 5)
		self.assertEqual(len(page3["data"]), 1)

		# Pages don't overlap.
		page2 = get_submissions(requirement=req.name, page=2, page_length=2)
		seen = {s["name"] for s in page1["data"]} | {s["name"] for s in page2["data"]} | {
			s["name"] for s in page3["data"]
		}
		self.assertEqual(len(seen), 5)

	def test_get_dashboard_returns_departments_present(self):
		dept = self._make_empty_department()
		req = self._make_scoped_requirement("_test-sub-req-dash-depts", dept)
		emp_a = self._make_employee(suffix="dash-a")
		emp_b = self._make_employee(suffix="dash-b")
		emp_c = self._make_employee(suffix="dash-c")
		self._make_submission(req.name, emp_a, display_name="A", department="Marketing")
		self._make_submission(req.name, emp_b, display_name="B", department="Accounts")
		self._make_submission(req.name, emp_c, display_name="C")  # Unassigned

		from onerc_compliance.api.v1.compliance import get_dashboard

		result = get_dashboard(requirement=req.name)
		departments = result["data"]["departments"]
		# Real departments sorted, "Unassigned" appended last.
		self.assertEqual(departments, ["Accounts", "Marketing", "Unassigned"])

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

	# ---- Permission tests ----

	def test_get_submissions_denies_employee(self):
		"""A user with only the Employee role must be denied by get_submissions."""
		req = self._make_requirement(title="_test-sub-req-deny")
		self._make_staff_user()

		from onerc_compliance.api.v1.compliance import get_submissions

		try:
			frappe.set_user(_STAFF_USER_EMAIL)
			with self.assertRaises(frappe.PermissionError):
				get_submissions(requirement=req.name)
		finally:
			frappe.set_user("Administrator")

	def test_get_dashboard_denies_employee(self):
		"""A user with only the Employee role must be denied by get_dashboard."""
		req = self._make_requirement(title="_test-sub-req-deny-dash")
		self._make_staff_user()

		from onerc_compliance.api.v1.compliance import get_dashboard

		try:
			frappe.set_user(_STAFF_USER_EMAIL)
			with self.assertRaises(frappe.PermissionError):
				get_dashboard(requirement=req.name)
		finally:
			frappe.set_user("Administrator")

	def test_get_submissions_permits_officer(self):
		"""Administrator (System Manager) must be able to call get_submissions."""
		req = self._make_requirement(title="_test-sub-req-permit")
		emp = self._make_employee(suffix="permit")
		self._make_submission(req.name, emp)

		# We're already running as Administrator in the test suite.
		from onerc_compliance.api.v1.compliance import get_submissions

		result = get_submissions(requirement=req.name)
		self.assertEqual(result["status"], "success")
		self.assertIsInstance(result["data"], list)
