"""Backfill the HRDepartments / staff type snapshot onto existing rows.

`ensure_submission` only stamps these columns at creation time, so submissions
that predate the roster sync would report as blank ("Unassigned") forever and
would vanish from the dashboard's default staff-only view. This patch fills them
in once from the Employee record.

Employee.staff_type is derived here too, using the same rule as the sync — an
employee number starting with EMP is staff, anything else is not — so sites can
adopt the staff-only default before the first Business Central pull lands.

Idempotent: only blank values are written.
"""

import frappe

STAFF_PREFIX = "EMP"


def _derive_staff_type(employee):
	number = (employee.get("staff_portal_id") or employee.get("employee_number") or "").strip()
	if not number:
		return "Other"
	return "Staff" if number.upper().startswith(STAFF_PREFIX) else "Other"


def execute():
	from onerc_compliance.setup import ensure_compliance_custom_fields

	ensure_compliance_custom_fields()

	employee_meta = frappe.get_meta("Employee")
	has_staff_type = bool(employee_meta.get_field("staff_type"))
	has_hr_departments = bool(employee_meta.get_field("hr_departments"))

	# 1. Derive Employee.staff_type where the roster sync has not set it yet.
	if has_staff_type:
		fields = ["name", "employee_number", "staff_type"]
		if employee_meta.get_field("staff_portal_id"):
			fields.append("staff_portal_id")

		for employee in frappe.get_all("Employee", fields=fields):
			if employee.get("staff_type"):
				continue
			frappe.db.set_value(
				"Employee",
				employee.name,
				"staff_type",
				_derive_staff_type(employee),
				update_modified=False,
			)

	# 2. Copy the snapshot onto submissions that are missing it.
	employee_fields = ["name"]
	if has_hr_departments:
		employee_fields.append("hr_departments")
	if has_staff_type:
		employee_fields.append("staff_type")

	employees = {
		row.name: row for row in frappe.get_all("Employee", fields=employee_fields)
	}

	for submission in frappe.get_all(
		"Compliance Submission",
		fields=["name", "employee", "hr_departments", "staff_type"],
	):
		employee = employees.get(submission.employee)
		if not employee:
			continue

		updates = {}
		if has_hr_departments and not submission.hr_departments and employee.get("hr_departments"):
			updates["hr_departments"] = employee.get("hr_departments")
		if has_staff_type and not submission.staff_type and employee.get("staff_type"):
			updates["staff_type"] = employee.get("staff_type")

		if updates:
			frappe.db.set_value(
				"Compliance Submission", submission.name, updates, update_modified=False
			)

	frappe.db.commit()
