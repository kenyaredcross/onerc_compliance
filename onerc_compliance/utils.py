# Copyright (c) 2026, Kelvin Njenga and contributors
# For license information, please see license.txt

import frappe
from frappe import _


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
