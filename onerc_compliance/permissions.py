# Copyright (c) 2026, Kelvin Njenga and contributors
# For license information, please see license.txt

import frappe


def submission_query_conditions(user=None):
	if not user:
		user = frappe.session.user

	if frappe.has_role("Compliance Officer", user) or frappe.has_role("System Manager", user):
		return ""

	employee = frappe.db.get_value("Employee", {"user_id": user}, "name")
	if not employee:
		return "1=0"

	return f"`tabCompliance Submission`.`employee` = {frappe.db.escape(employee)}"


def has_submission_permission(doc, user=None, permission_type=None):
	if not user:
		user = frappe.session.user

	if frappe.has_role("Compliance Officer", user) or frappe.has_role("System Manager", user):
		return True

	employee = frappe.db.get_value("Employee", {"user_id": user}, "name")
	if not employee:
		return False

	return doc.employee == employee
