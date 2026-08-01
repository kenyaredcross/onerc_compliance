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

	def _make_employee(self, suffix="sub-test", staff_type="Staff", hr_departments=None):
		"""Create a test Employee. Defaults to staff, matching the roster sync's
		rule that an EMP-prefixed employee number means a permanent staff member."""
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
			"employee_number": ("EMP-" if staff_type == "Staff" else "VOL-") + suffix,
			"staff_type": staff_type,
			"hr_departments": hr_departments or "",
		})
		emp.insert(ignore_permissions=True)
		return emp.name

	def _make_submission(
		self,
		requirement_name,
		employee_name,
		status="Pending",
		display_name=None,
		hr_departments=None,
		staff_type="Staff",
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
		# These two are normally snapshotted from the Employee by
		# ensure_submission; set them directly since this builds the doc by hand.
		if hr_departments is not None:
			doc.hr_departments = hr_departments
		doc.staff_type = staff_type
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
		self._make_submission(req.name, emp_a, display_name="A", hr_departments="Accounts")
		self._make_submission(req.name, emp_b, display_name="B", hr_departments="Marketing")
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
			req.name, emp_a, status="Overdue", display_name="Kamau One", hr_departments="Accounts"
		)
		self._make_submission(
			req.name, emp_b, status="Pending", display_name="Kamau Two", hr_departments="Accounts"
		)
		self._make_submission(
			req.name, emp_c, status="Overdue", display_name="Wanjiru Three", hr_departments="Marketing"
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
		self._make_submission(req.name, emp_a, display_name="A", hr_departments="Marketing")
		self._make_submission(req.name, emp_b, display_name="B", hr_departments="Accounts")
		self._make_submission(req.name, emp_c, display_name="C")  # Unassigned

		from onerc_compliance.api.v1.compliance import get_dashboard

		result = get_dashboard(requirement=req.name)
		departments = result["data"]["departments"]
		# Real departments sorted, "Unassigned" appended last.
		self.assertEqual(departments, ["Accounts", "Marketing", "Unassigned"])

	# ------------------------------------------------------------------
	# Duplicate (requirement, employee) pairs
	# ------------------------------------------------------------------

	def _plant_duplicate(self, source_name, status="Overdue"):
		src = frappe.db.get_value(
			"Compliance Submission", source_name,
			["requirement", "employee", "employee_name"], as_dict=True,
		)
		dup = source_name + "-DUP"
		frappe.db.sql(
			"""INSERT INTO `tabCompliance Submission`
			   (name, creation, modified, modified_by, owner, docstatus, idx,
			    requirement, employee, employee_name, status, staff_type)
			   VALUES (%s, NOW(), NOW(), 'Administrator', 'Administrator', 0, 0,
			           %s, %s, %s, %s, 'Staff')""",
			(dup, src.requirement, src.employee, src.employee_name or "", status),
		)
		return dup

	def test_reopen_succeeds_despite_preexisting_duplicate(self):
		"""A legacy duplicate must not block extending and reactivating.

		The uniqueness check used to fire on every save of either row, so
		_reset_overdue_submissions could not flip Overdue -> Pending and the whole
		requirement save was rolled back.
		"""
		dept = self._make_empty_department()
		emp = self._make_employee(suffix="dup-reopen")
		req = self._make_scoped_requirement("_test-sub-req-dup-reopen", dept)
		sub = self._make_submission(req.name, emp, status="Overdue")

		dup = self._plant_duplicate(sub.name, status="Overdue")
		self.assertEqual(
			frappe.db.count("Compliance Submission",
							{"requirement": req.name, "employee": emp}), 2
		)

		frappe.db.set_value("Compliance Requirement", req.name, "status", "Closed")
		doc = frappe.get_doc("Compliance Requirement", req.name)
		doc.deadline = "2099-12-31 23:59:00"
		doc.status = "Active"
		doc.save(ignore_permissions=True)  # must not raise

		self.assertEqual(
			frappe.db.get_value("Compliance Submission", sub.name, "status"), "Pending"
		)
		# Both rows survive — nothing here removes data.
		self.assertEqual(
			frappe.db.count("Compliance Submission",
							{"requirement": req.name, "employee": emp}), 2
		)
		frappe.db.delete("Compliance Submission", {"name": dup})

	def test_cleanup_never_deletes_a_row_holding_data(self):
		"""The duplicate tool must not destroy submitted work.

		Guards the specific trap: the surviving row is chosen by what it holds,
		not by how far along its status is. A Reviewed-but-empty row must never
		win over a Pending row carrying the employee's answers.
		"""
		dept = self._make_empty_department()
		emp = self._make_employee(suffix="dup-safe")
		req = self._make_scoped_requirement("_test-sub-req-dup-safe", dept)

		# Empty but Reviewed — the status the old scoring would have preferred.
		empty = self._make_submission(req.name, emp, status="Reviewed")
		# Pending, but holds the actual answer.
		full = self._plant_duplicate(empty.name, status="Pending")
		frappe.get_doc({
			"doctype": "Compliance Submission Value",
			"parenttype": "Compliance Submission",
			"parentfield": "values",
			"parent": full,
			"field_name": "declaration",
			"field_label": "Declaration",
			"field_type": "Data",
			"value": "I agree",
		}).insert(ignore_permissions=True)
		frappe.db.commit()

		from onerc_compliance.duplicate_submissions import cleanup_duplicate_submissions

		# Dry run must change nothing at all.
		cleanup_duplicate_submissions(dry_run=True)
		self.assertTrue(frappe.db.exists("Compliance Submission", full))
		self.assertTrue(frappe.db.exists("Compliance Submission", empty.name))

		# Applied: the row holding the answer survives; the empty one may go.
		cleanup_duplicate_submissions(dry_run=False)
		self.assertTrue(
			frappe.db.exists("Compliance Submission", full),
			"The row holding the employee's answer must never be deleted",
		)

		frappe.db.delete("Compliance Submission Value", {"parent": full})
		frappe.db.delete("Compliance Submission", {"name": full})

	def test_cleanup_skips_groups_where_two_rows_hold_data(self):
		"""When both duplicates carry work, the tool refuses and reports."""
		dept = self._make_empty_department()
		emp = self._make_employee(suffix="dup-both")
		req = self._make_scoped_requirement("_test-sub-req-dup-both", dept)

		first = self._make_submission(req.name, emp, status="Submitted")
		frappe.db.set_value("Compliance Submission", first.name, "submitted_on",
							"2026-01-01 00:00:00", update_modified=False)
		second = self._plant_duplicate(first.name, status="Submitted")
		frappe.db.sql(
			"UPDATE `tabCompliance Submission` SET submitted_on = %s WHERE name = %s",
			("2026-02-01 00:00:00", second),
		)
		frappe.db.commit()

		from onerc_compliance.duplicate_submissions import cleanup_duplicate_submissions

		summary = cleanup_duplicate_submissions(dry_run=False)

		self.assertEqual(summary["removed"], 0)
		self.assertTrue(frappe.db.exists("Compliance Submission", first.name))
		self.assertTrue(frappe.db.exists("Compliance Submission", second))
		self.assertTrue(
			any(s["employee"] == emp for s in summary["skipped_groups"]),
			"Group with two data-holding rows must be reported for manual review",
		)

		frappe.db.delete("Compliance Submission", {"name": second})

	def test_duplicate_insert_still_blocked(self):
		dept = self._make_empty_department()
		emp = self._make_employee(suffix="dup-insert")
		req = self._make_scoped_requirement("_test-sub-req-dup-insert", dept)
		self._make_submission(req.name, emp)

		with self.assertRaises(frappe.ValidationError):
			self._make_submission(req.name, emp)

	def test_repointing_onto_a_taken_pair_is_blocked(self):
		"""Editing a submission to target a pair that already exists still throws."""
		dept = self._make_empty_department()
		emp_a = self._make_employee(suffix="dup-point-a")
		emp_b = self._make_employee(suffix="dup-point-b")
		req = self._make_scoped_requirement("_test-sub-req-dup-point", dept)
		self._make_submission(req.name, emp_a)
		sub_b = self._make_submission(req.name, emp_b)

		sub_b.reload()
		sub_b.employee = emp_a
		with self.assertRaises(frappe.ValidationError):
			sub_b.save(ignore_permissions=True)

	def test_ensure_submission_returns_existing_instead_of_raising(self):
		dept = self._make_empty_department()
		emp = self._make_employee(suffix="dup-ensure")
		req = self._make_scoped_requirement("_test-sub-req-dup-ensure", dept)

		from onerc_compliance.utils import ensure_submission

		first = ensure_submission(req.name, emp)
		second = ensure_submission(req.name, emp)
		self.assertEqual(first, second)
		self.assertEqual(
			frappe.db.count("Compliance Submission", {"requirement": req.name, "employee": emp}), 1
		)

	# ------------------------------------------------------------------
	# staff_scope — the dashboard defaults to staff only
	# ------------------------------------------------------------------

	def _make_mixed_population(self, title):
		"""One staff submission and one non-staff submission on a scoped requirement."""
		dept = self._make_empty_department()
		req = self._make_scoped_requirement(title, dept)
		staff_emp = self._make_employee(suffix="scope-staff", staff_type="Staff")
		other_emp = self._make_employee(suffix="scope-other", staff_type="Other")
		self._make_submission(
			req.name, staff_emp, status="Reviewed", display_name="Staff Person",
			hr_departments="ICT", staff_type="Staff",
		)
		self._make_submission(
			req.name, other_emp, status="Pending", display_name="Volunteer Person",
			hr_departments="SCLAM", staff_type="Other",
		)
		return req

	def test_get_submissions_defaults_to_staff_only(self):
		req = self._make_mixed_population("_test-sub-req-scope-list")

		from onerc_compliance.api.v1.compliance import get_submissions

		default = get_submissions(requirement=req.name)
		self.assertEqual(default["meta"]["total_count"], 1)
		self.assertEqual(default["data"][0]["employee_name"], "Staff Person")
		self.assertEqual(default["meta"]["staff_scope"], "Staff")

	def test_get_submissions_staff_scope_all_includes_everyone(self):
		req = self._make_mixed_population("_test-sub-req-scope-all")

		from onerc_compliance.api.v1.compliance import get_submissions

		everyone = get_submissions(requirement=req.name, staff_scope="All")
		self.assertEqual(everyone["meta"]["total_count"], 2)
		self.assertEqual(everyone["meta"]["staff_scope"], "All")
		self.assertEqual(
			sorted(s["employee_name"] for s in everyone["data"]),
			["Staff Person", "Volunteer Person"],
		)

	def test_get_submissions_unknown_staff_scope_falls_back_to_staff(self):
		req = self._make_mixed_population("_test-sub-req-scope-bad")

		from onerc_compliance.api.v1.compliance import get_submissions

		result = get_submissions(requirement=req.name, staff_scope="Nonsense")
		self.assertEqual(result["meta"]["staff_scope"], "Staff")
		self.assertEqual(result["meta"]["total_count"], 1)

	def test_get_dashboard_respects_staff_scope(self):
		req = self._make_mixed_population("_test-sub-req-scope-dash")

		from onerc_compliance.api.v1.compliance import get_dashboard

		# Default: staff only — headline totals AND the department breakdown.
		staff_only = get_dashboard(requirement=req.name)["data"]
		self.assertEqual(staff_only["staff_scope"], "Staff")
		self.assertEqual(staff_only["known_total"], 1)
		self.assertEqual(staff_only["reviewed_count"], 1)
		self.assertEqual(staff_only["departments"], ["ICT"])
		self.assertEqual(staff_only["completion_percent"], 100.0)

		# All: the non-staff submission and its department reappear.
		everyone = get_dashboard(requirement=req.name, staff_scope="All")["data"]
		self.assertEqual(everyone["staff_scope"], "All")
		self.assertEqual(everyone["known_total"], 2)
		self.assertEqual(everyone["reviewed_count"], 1)
		self.assertEqual(sorted(everyone["departments"]), ["ICT", "SCLAM"])
		self.assertEqual(everyone["completion_percent"], 50.0)

	def test_get_submissions_department_filter_uses_hr_departments(self):
		"""The department dimension is the raw HRDepartments code, not the
		ERPNext Department link."""
		req = self._make_mixed_population("_test-sub-req-scope-dept")

		from onerc_compliance.api.v1.compliance import get_submissions

		ict = get_submissions(requirement=req.name, department="ICT")
		self.assertEqual(ict["meta"]["total_count"], 1)
		self.assertEqual(ict["data"][0]["department"], "ICT")

		# SCLAM belongs to the non-staff employee, so it is empty under the
		# default staff-only scope but visible under "All".
		self.assertEqual(
			get_submissions(requirement=req.name, department="SCLAM")["meta"]["total_count"], 0
		)
		self.assertEqual(
			get_submissions(
				requirement=req.name, department="SCLAM", staff_scope="All"
			)["meta"]["total_count"],
			1,
		)

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
