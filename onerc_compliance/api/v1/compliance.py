# Copyright (c) 2026, Kelvin Njenga and contributors
# For license information, please see license.txt

import json

import frappe
from frappe import _
from frappe.utils import now_datetime

from onerc_compliance.utils import employee_in_scope, ensure_submission, get_employee_for_user


def _ok(data, message="", meta=None):
	return {"status": "success", "data": data, "message": message, "meta": meta or {}}


def _err(message, data=None):
	return {"status": "error", "data": data if data is not None else [], "message": message, "meta": {}}


@frappe.whitelist()
def get_my_requirements():
	employee_name = get_employee_for_user()
	if not employee_name:
		return _err(_(
			"Your account isn't linked to an employee record. "
			"Compliance requirements are assigned to staff records — "
			"if you're a member of staff, contact HR or your Compliance Officer."
		))

	requirements = frappe.get_all(
		"Compliance Requirement",
		filters={"status": "Active"},
		fields=["name", "title", "description", "external_link", "deadline", "target_type"],
	)

	result = []
	for req in requirements:
		req_doc = frappe.get_doc("Compliance Requirement", req.name)

		if not employee_in_scope(req_doc, employee_name):
			continue

		submission_name = ensure_submission(req.name, employee_name)

		field_schema = []
		for f in req_doc.fields:
			options_list = []
			if f.fieldtype == "Select" and f.options:
				options_list = [o.strip() for o in f.options.split("\n") if o.strip()]
			field_schema.append({
				"fieldname": f.fieldname,
				"label": f.label,
				"fieldtype": f.fieldtype,
				"options": options_list,
				"mandatory": bool(f.mandatory),
				"description": f.description or "",
			})

		sub_doc = frappe.get_doc("Compliance Submission", submission_name)
		answers = {}
		for val in sub_doc.values:
			answers[val.field_name] = {
				"value": val.value,
				"value_date": str(val.value_date) if val.value_date else None,
				"value_check": bool(val.value_check),
				"attachment": val.attachment,
			}

		review_actions = []
		for act in sub_doc.review_actions:
			review_actions.append({
				"action": act.action,
				"reviewer": act.reviewer,
				"action_on": str(act.action_on) if act.action_on else None,
				"remarks": act.remarks or "",
			})

		result.append({
			"requirement": req.name,
			"title": req.title,
			"description": req.description,
			"external_link": req.external_link,
			"deadline": str(req.deadline) if req.deadline else None,
			"field_schema": field_schema,
			"submission_status": sub_doc.status,
			"answers": answers,
			"review_actions": review_actions,
		})

	return _ok(result)


@frappe.whitelist()
def submit_requirement(requirement, answers):
	if isinstance(answers, str):
		answers = json.loads(answers)

	req_doc = frappe.get_doc("Compliance Requirement", requirement)
	if req_doc.status != "Active":
		return _err(_("This requirement is no longer active."))

	employee_name = get_employee_for_user()
	if not employee_name:
		return _err(_(
			"Your account isn't linked to an employee record. "
			"Compliance requirements are assigned to staff records — "
			"if you're a member of staff, contact HR or your Compliance Officer."
		))

	submission_name = ensure_submission(requirement, employee_name)
	sub = frappe.get_doc("Compliance Submission", submission_name)

	if sub.status not in ("Pending", "Needs More Info"):
		return _err(
			_("Submission is in status '{0}' and cannot be re-submitted.").format(sub.status)
		)

	# Rebuild values child table from schema
	sub.values = []
	for schema_field in req_doc.fields:
		fname = schema_field.fieldname
		raw = answers.get(fname)
		row = {
			"field_name": fname,
			"field_label": schema_field.label or fname,
			"field_type": schema_field.fieldtype,
		}
		if schema_field.fieldtype == "Check":
			row["value_check"] = 1 if raw else 0
		elif schema_field.fieldtype == "Date":
			row["value_date"] = raw or None
		elif schema_field.fieldtype == "Attach":
			row["attachment"] = raw or None
		else:
			row["value"] = str(raw) if raw is not None else ""
		sub.append("values", row)

	sub.status = "Submitted" if req_doc.requires_review else "Reviewed"
	sub.save(ignore_permissions=True)

	return _ok({"submission": sub.name, "status": sub.status})


@frappe.whitelist()
def review_submission(submission, action, remarks=None):
	frappe.has_permission("Compliance Submission", doc=submission, ptype="write", throw=True)

	allowed_actions = {"Reviewed", "Needs More Info", "Rejected"}
	if action not in allowed_actions:
		return _err(_("Invalid action. Must be one of: Reviewed, Needs More Info, Rejected."))

	if action in ("Needs More Info", "Rejected") and not (remarks or "").strip():
		return _err(_("Remarks are required for action '{0}'.").format(action))

	sub = frappe.get_doc("Compliance Submission", submission)
	if sub.status != "Submitted":
		return _err(
			_("Only submissions in 'Submitted' status can be reviewed. Current status: {0}.").format(
				sub.status
			)
		)

	sub.append(
		"review_actions",
		{
			"action": action,
			"reviewer": frappe.session.user,
			"action_on": now_datetime(),
			"remarks": remarks or "",
		},
	)
	sub.status = action
	sub.save(ignore_permissions=True)

	return _ok({"submission": sub.name, "status": sub.status})


@frappe.whitelist()
def get_submissions(requirement, status=None):
	# Requires write on Compliance Submission — employees are read-only and must be denied.
	frappe.has_permission("Compliance Submission", ptype="write", throw=True)

	filters = {"requirement": requirement}
	if status:
		filters["status"] = status

	rows = frappe.get_all(
		"Compliance Submission",
		filters=filters,
		fields=["name", "employee_name", "department", "status", "submitted_on"],
		limit=500,
	)

	req_doc = frappe.get_doc("Compliance Requirement", requirement)
	field_schema = []
	for f in req_doc.fields:
		field_schema.append({
			"fieldname": f.fieldname,
			"label": f.label or f.fieldname,
			"fieldtype": f.fieldtype,
		})

	result = []
	for row in rows:
		sub_doc = frappe.get_doc("Compliance Submission", row.name)

		answers = {}
		for val in sub_doc.values:
			answers[val.field_name] = {
				"value": val.value,
				"value_date": str(val.value_date) if val.value_date else None,
				"value_check": bool(val.value_check),
				"attachment": val.attachment,
			}

		review_actions = []
		for act in sub_doc.review_actions:
			review_actions.append({
				"action": act.action,
				"reviewer": act.reviewer,
				"action_on": str(act.action_on) if act.action_on else None,
				"remarks": act.remarks or "",
			})

		result.append({
			"name": row.name,
			"employee_name": sub_doc.employee_name or "",
			"department": sub_doc.department or "",
			"status": row.status,
			"submitted_on": str(sub_doc.submitted_on) if sub_doc.submitted_on else None,
			"field_schema": field_schema,
			"answers": answers,
			"review_actions": review_actions,
		})

	return _ok(result)


@frappe.whitelist()
def get_dashboard(requirement):
	# Requires write on Compliance Submission — same gate as get_submissions and review_submission.
	frappe.has_permission("Compliance Submission", ptype="write", throw=True)

	req_doc = frappe.get_doc("Compliance Requirement", requirement)

	submissions = frappe.get_all(
		"Compliance Submission",
		filters={"requirement": requirement},
		fields=["name", "status", "department"],
	)

	status_counts = {}
	dept_map = {}

	for sub in submissions:
		status_counts[sub.status] = status_counts.get(sub.status, 0) + 1

		dept = sub.department or "Unassigned"
		if dept not in dept_map:
			dept_map[dept] = {"department": dept, "reviewed": 0, "total": 0}
		dept_map[dept]["total"] += 1
		if sub.status == "Reviewed":
			dept_map[dept]["reviewed"] += 1

	reviewed_count = status_counts.get("Reviewed", 0)
	known_total = len(submissions)
	expected = req_doc.expected_headcount or 0
	denominator = expected if expected else known_total
	completion_percent = round((reviewed_count / denominator) * 100, 2) if denominator else 0.0

	return _ok({
		"requirement": requirement,
		"status_counts": status_counts,
		"by_department": list(dept_map.values()),
		"reviewed_count": reviewed_count,
		"known_total": known_total,
		"expected_headcount": expected,
		"completion_percent": completion_percent,
	})
