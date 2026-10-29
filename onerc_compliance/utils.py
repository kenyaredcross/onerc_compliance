# Copyright (c) 2026, Kelvin Njenga and contributors
# For license information, please see license.txt

import re

import frappe
from frappe import _

# Frappe rejects an attached_to_field containing any non-word character
# (see frappe.database.schema.SPECIAL_CHAR_PATTERN). Compliance schema
# fieldnames are user-defined and may contain "/", spaces, etc., so we only
# record the field when it is safe — file access does not depend on it.
_VALID_FIELDNAME = re.compile(r"^\w+$")


def get_employee_for_user(user=None):
	if not user:
		user = frappe.session.user
	return frappe.db.get_value("Employee", {"user_id": user}, "name")


def employee_in_scope(requirement, employee):
	if requirement.target_type == "All Staff":
		return True
	dept_names = [row.department for row in requirement.target_departments]
	emp_dept = frappe.db.get_value("Employee", employee, "department")
	return emp_dept in dept_names


def get_in_scope_employees(requirement):
	if requirement.target_type == "All Staff":
		rows = frappe.get_all("Employee", filters={"status": "Active"}, fields=["name"])
		result = []
		for row in rows:
			result.append(row.name)
		return result

	dept_names = []
	for row in requirement.target_departments:
		dept_names.append(row.department)

	seen = set()
	result = []
	for dept in dept_names:
		rows = frappe.get_all(
			"Employee",
			filters={"status": "Active", "department": dept},
			fields=["name"],
		)
		for row in rows:
			if row.name not in seen:
				seen.add(row.name)
				result.append(row.name)
	return result


def ensure_submission(requirement_name, employee_name):
	existing = frappe.db.get_value(
		"Compliance Submission",
		{"requirement": requirement_name, "employee": employee_name},
		"name",
	)
	if existing:
		return existing

	emp_data = frappe.db.get_value(
		"Employee",
		employee_name,
		["employee_name", "department", "designation"],
		as_dict=True,
	)
	doc = frappe.get_doc(
		{
			"doctype": "Compliance Submission",
			"requirement": requirement_name,
			"employee": employee_name,
			"employee_name": (emp_data.get("employee_name") or "") if emp_data else "",
			"department": (emp_data.get("department") or "") if emp_data else "",
			"designation": (emp_data.get("designation") or "") if emp_data else "",
			"status": "Pending",
		}
	)
	doc.insert(ignore_permissions=True)
	return doc.name


def bulk_ensure_submissions(requirement_name, employee_names):
	for emp in employee_names:
		ensure_submission(requirement_name, emp)
		frappe.db.commit()


def link_file_to_submission(file_url, submission_name, fieldname=None):
	"""Attach a private File (by its file_url) to a Compliance Submission.

	Reviewers (e.g. the Compliance Officer) get read access to a private file
	through attachment inheritance: a File whose attached_to_doctype/name points
	at a document they can read becomes readable to them too. Staff certificates
	are uploaded as standalone private files, so without this link only the
	uploader and System Manager can open them.

	The file stays private (is_private = 1). Returns True if a File row was
	found and linked, False otherwise. Idempotent: re-linking an already-linked
	file is a no-op save.
	"""
	if not file_url:
		return False

	file_name = frappe.db.get_value("File", {"file_url": file_url}, "name")
	if not file_name:
		return False

	file_doc = frappe.get_doc("File", file_name)
	file_doc.attached_to_doctype = "Compliance Submission"
	file_doc.attached_to_name = submission_name
	# Reviewer read access is inherited purely from attached_to_doctype +
	# attached_to_name; attached_to_field is optional metadata that Frappe
	# only accepts when it has no special characters.
	if fieldname and _VALID_FIELDNAME.match(fieldname):
		file_doc.attached_to_field = fieldname
	file_doc.is_private = 1
	file_doc.save(ignore_permissions=True)
	return True


def sync_submission_employee_fields(doc, method=None):
	"""Employee on_update hook: keep the department/designation snapshot on that
	employee's Compliance Submissions in sync with the HR master.

	Compliance Submission snapshots these fields at creation time and never
	refreshes them, so changing an Employee's department later would otherwise
	leave their submissions (and the dashboard grouping) showing the old /
	blank value. We only write when the value has actually changed, and we use
	frappe.db.set_value to avoid re-triggering submission validations.
	"""
	submissions = frappe.get_all(
		"Compliance Submission",
		filters={"employee": doc.name},
		fields=["name", "department", "designation"],
	)
	if not submissions:
		return

	new_department = doc.department or ""
	new_designation = doc.designation or ""

	for sub in submissions:
		updates = {}
		if (sub.department or "") != new_department:
			updates["department"] = new_department
		if (sub.designation or "") != new_designation:
			updates["designation"] = new_designation
		if updates:
			frappe.db.set_value(
				"Compliance Submission", sub.name, updates, update_modified=False
			)


def backfill_submission_departments():
	"""Re-copy department/designation onto every Compliance Submission from its
	current Employee record. One-off repair for submissions whose snapshot was
	captured while the Employee had no department (shown as "Unassigned" on the
	dashboard). Safe to run repeatedly — only changed rows are written.

	Returns a summary dict: {total, updated, skipped_no_employee}.
	"""
	submissions = frappe.get_all(
		"Compliance Submission",
		fields=["name", "employee", "department", "designation"],
	)

	# Batch-load every linked Employee's current department/designation.
	emp_ids = {s["employee"] for s in submissions if s.get("employee")}
	emp_data = {}
	if emp_ids:
		for emp in frappe.get_all(
			"Employee",
			filters={"name": ["in", list(emp_ids)]},
			fields=["name", "department", "designation"],
		):
			emp_data[emp["name"]] = emp

	updated = 0
	skipped_no_employee = 0
	for sub in submissions:
		emp = emp_data.get(sub.get("employee"))
		if not emp:
			skipped_no_employee += 1
			continue
		updates = {}
		new_department = emp.get("department") or ""
		new_designation = emp.get("designation") or ""
		if (sub.get("department") or "") != new_department:
			updates["department"] = new_department
		if (sub.get("designation") or "") != new_designation:
			updates["designation"] = new_designation
		if updates:
			frappe.db.set_value(
				"Compliance Submission", sub["name"], updates, update_modified=False
			)
			updated += 1

	frappe.db.commit()
	return {
		"total": len(submissions),
		"updated": updated,
		"skipped_no_employee": skipped_no_employee,
	}
