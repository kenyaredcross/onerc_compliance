# Copyright (c) 2026, Kelvin Njenga and contributors
# For license information, please see license.txt

import json

import frappe
from frappe import _
from frappe.utils import now_datetime

from onerc_compliance.scheme_utils import ACTIVE_STATUSES, is_minor
from onerc_compliance.utils import get_employee_for_user


def _ok(data, message="", meta=None):
	return {"status": "success", "data": data, "message": message, "meta": meta or {}}


def _err(message, data=None):
	return {"status": "error", "data": data if data is not None else [], "message": message, "meta": {}}


FORM_DOCTYPES = {
	"scheme": "Occupational Scheme Form",
	"nomination": "Beneficiary Nomination",
}

EDITABLE_STATUSES = ("Draft", "Needs More Info")

# Fields staff may write per form type — lifecycle/review/trustee fields are
# deliberately excluded so a crafted payload cannot self-approve.
STAFF_FIELDS = {
	"scheme": [
		"member_full_name", "occupation", "date_of_birth", "member_number",
		"date_of_admission", "date_of_appointment", "mobile_number", "email",
		"kra_pin", "id_number", "details_confirmed",
		"avc_amount", "avc_percent",
		"bank_account_name", "bank_name", "bank_branch", "bank_account_number",
		"bank_town_city", "bank_code", "branch_code", "swift_code", "sort_or_iban_code",
		"declaration_accepted",
	],
	"nomination": [
		"member_full_name", "email", "telephone", "marital_status",
		"id_number", "kra_pin",
		"declaration_accepted", "signed_at",
	],
}

BENEFICIARY_FIELDS = [
	"full_name", "email", "mobile", "date_of_birth", "id_number",
	"birth_certificate_no", "relationship", "share_percent",
	"source", "bc_relative_no", "bc_line_no", "bc_category",
]

GUARDIAN_FIELDS = [
	"guardian_name", "email", "mobile", "id_number",
	"beneficiary_name", "relationship_to_beneficiary",
]

_NO_EMPLOYEE_MSG = (
	"Your account isn't linked to an employee record. "
	"Scheme forms are tied to staff records — "
	"if you're a member of staff, contact HR or your Compliance Officer."
)


# ---------------------------------------------------------------------------
# Business Central prefill
# ---------------------------------------------------------------------------

def _split_name(rec):
	parts = [rec.get("FirstName") or "", rec.get("MiddleName") or "", rec.get("LastName") or ""]
	return " ".join(p.strip() for p in parts if p.strip())


def _map_relative(rec):
	category = (rec.get("Category") or "").strip()
	full_name = _split_name(rec)
	# Legacy BC rows cram the whole description into FirstName with a blank
	# Category — surface them, but flag for the member to clean up.
	needs_review = not category

	birth_date = (rec.get("BirthDate") or "").strip()
	if birth_date.startswith("0001"):
		birth_date = ""

	relationship = (rec.get("RelativeCode") or "").strip().title()

	return {
		"full_name": full_name,
		"date_of_birth": birth_date or None,
		"id_number": (rec.get("IDNo") or "").strip(),
		"mobile": (rec.get("PhoneNo") or "").strip(),
		"relationship": relationship,
		"source": "Business Central",
		"bc_relative_no": (rec.get("RelativeNo") or "").strip(),
		"bc_line_no": rec.get("LineNo") or 0,
		"bc_category": category,
		"needs_review": needs_review,
	}


def _fetch_bc_relatives(employee_number):
	"""Fetch the employee's relatives from Business Central. Never raises.

	Returns (relatives, status, error) where status is "ok" or "unavailable".

	Production: in-process call into krcs_onesource, which reads the
	ApiUsername/ApiKey from Staff Portal Settings and calls BC directly.
	Local dev: the internal BC host is unreachable, so site_config's
	`scheme_bc_remote_proxy` (e.g. "https://one.redcross.or.ke") routes the
	same request through the deployed proxy over HTTPS.
	"""
	if not employee_number:
		return [], "unavailable", _("No employee number on your staff record.")

	path = "EmployeeRelatives?query=$filter=EmployeeNo eq '{0}'".format(employee_number)
	friendly = _("HR records are unreachable right now; you can still fill the form manually.")

	remote_proxy = frappe.conf.get("scheme_bc_remote_proxy")
	try:
		if remote_proxy:
			import requests

			resp = requests.post(
				"{0}/api/method/krcs_onesource.api.proxy.staff_portal".format(remote_proxy.rstrip("/")),
				json={"path": path, "method": "GET"},
				timeout=30,
			)
			resp.raise_for_status()
			result = resp.json().get("message") or {}
		else:
			from krcs_onesource.api.proxy import staff_portal

			result = staff_portal(path=path, method="GET")

		if not result.get("ok"):
			frappe.log_error(
				title="Scheme BC prefill - backend error",
				message="EmployeeNo: {0}\nStatus: {1}\nData: {2}".format(
					employee_number, result.get("status_code"), result.get("data")
				),
			)
			return [], "unavailable", friendly

		rows = result.get("data") or []
		if not isinstance(rows, list):
			rows = []
		return [_map_relative(r) for r in rows], "ok", ""

	except Exception:
		frappe.log_error(frappe.get_traceback(), "Scheme BC prefill failed")
		return [], "unavailable", friendly


# ---------------------------------------------------------------------------
# Serialization
# ---------------------------------------------------------------------------

def _serialize_doc(doc):
	data = {
		"name": doc.name,
		"status": doc.status,
		"employee": doc.employee,
		"employee_name": doc.employee_name or "",
		"employee_number": doc.employee_number or "",
		"department": doc.department or "",
		"designation": doc.designation or "",
		"scheme_name": doc.get("scheme_name") or "",
		"submitted_on": str(doc.submitted_on) if doc.submitted_on else None,
		"declaration_date": str(doc.declaration_date) if doc.declaration_date else None,
		"amends": doc.get("amends"),
		"bc_prefill_used": bool(doc.get("bc_prefill_used")),
	}

	form_type = "scheme" if doc.doctype == "Occupational Scheme Form" else "nomination"
	for fieldname in STAFF_FIELDS[form_type]:
		value = doc.get(fieldname)
		if hasattr(value, "isoformat"):
			value = str(value)
		data[fieldname] = value

	if form_type == "scheme":
		for fieldname in ("documents_checked", "trustee_1_name", "trustee_1_certified_on",
			"trustee_2_name", "trustee_2_certified_on"):
			value = doc.get(fieldname)
			data[fieldname] = str(value) if value else None
	else:
		data["witness_name"] = doc.get("witness_name") or ""
		data["trustee_name"] = doc.get("trustee_name") or ""
		data["date_received_by_trustee"] = (
			str(doc.date_received_by_trustee) if doc.get("date_received_by_trustee") else None
		)

	data["beneficiaries"] = [
		{f: (str(row.get(f)) if f == "date_of_birth" and row.get(f) else row.get(f)) for f in BENEFICIARY_FIELDS}
		for row in doc.beneficiaries
	]
	data["guardians"] = [
		{f: row.get(f) for f in GUARDIAN_FIELDS} for row in doc.guardians
	]
	data["review_actions"] = [
		{
			"action": act.action,
			"reviewer": act.reviewer,
			"action_on": str(act.action_on) if act.action_on else None,
			"remarks": act.remarks or "",
		}
		for act in doc.review_actions
	]
	return data


def _get_settings():
	settings = frappe.get_cached_doc("Occupational Scheme Settings")
	return {
		"scheme_name": settings.scheme_name or "",
		"administrator_name": settings.administrator_name or "",
		"enrolment_open": bool(settings.enrolment_open),
		"staff_instructions": settings.staff_instructions or "",
		"nomination_statement": settings.nomination_statement or "",
		"declaration_text": settings.declaration_text or "",
	}


def _latest_doc_name(doctype, employee):
	rows = frappe.get_all(
		doctype,
		filters={"employee": employee},
		fields=["name", "status"],
		order_by="creation desc",
		limit=1,
	)
	return rows[0] if rows else None


# ---------------------------------------------------------------------------
# Staff endpoints
# ---------------------------------------------------------------------------

@frappe.whitelist()
def get_my_forms():
	employee = get_employee_for_user()
	if not employee:
		return _err(_(_NO_EMPLOYEE_MSG))

	emp = frappe.db.get_value(
		"Employee",
		employee,
		["name", "employee_name", "employee_number", "department", "designation",
		 "date_of_birth", "date_of_joining", "cell_number", "company_email",
		 "personal_email", "user_id"],
		as_dict=True,
	)

	settings = _get_settings()

	forms = {}
	any_editable = False
	local_bc_keys = set()
	local_id_numbers = set()

	for form_type, doctype in FORM_DOCTYPES.items():
		latest = _latest_doc_name(doctype, employee)
		doc_data = None
		editable = True
		history = []

		if latest:
			doc = frappe.get_doc(doctype, latest.name)
			doc_data = _serialize_doc(doc)
			editable = doc.status in EDITABLE_STATUSES
			for row in doc.beneficiaries:
				if row.bc_relative_no:
					local_bc_keys.add(row.bc_relative_no)
				if (row.id_number or "").strip():
					local_id_numbers.add(row.id_number.strip())

		history_rows = frappe.get_all(
			doctype,
			filters={"employee": employee},
			fields=["name", "status", "submitted_on"],
			order_by="creation desc",
		)
		history = [
			{
				"name": row.name,
				"status": row.status,
				"submitted_on": str(row.submitted_on) if row.submitted_on else None,
			}
			for row in history_rows
		]

		# A new form may be started once the latest one is closed out.
		can_start_new = not latest or latest.status not in ACTIVE_STATUSES
		if editable or can_start_new:
			any_editable = True

		forms[form_type] = {
			"doc": doc_data,
			"editable": editable if latest else True,
			"can_start_new": can_start_new,
			"history": history,
		}

	bc = {"status": "skipped", "error": "", "suggestions": []}
	if any_editable:
		relatives, bc_status, bc_error = _fetch_bc_relatives(emp.employee_number)
		suggestions = [
			r for r in relatives
			if not (
				(r["bc_relative_no"] and r["bc_relative_no"] in local_bc_keys)
				or (r["id_number"] and r["id_number"] in local_id_numbers)
			)
		]
		bc = {"status": bc_status, "error": bc_error, "suggestions": suggestions}

	return _ok({
		"settings": settings,
		"employee_prefill": {
			"employee": emp.name,
			"employee_name": emp.employee_name or "",
			"employee_number": emp.employee_number or "",
			"department": emp.department or "",
			"designation": emp.designation or "",
			"date_of_birth": str(emp.date_of_birth) if emp.date_of_birth else None,
			"date_of_joining": str(emp.date_of_joining) if emp.date_of_joining else None,
			"cell_number": emp.cell_number or "",
			"email": emp.company_email or emp.user_id or "",
		},
		"forms": forms,
		"bc": bc,
	})


def _rebuild_children(doc, payload):
	doc.beneficiaries = []
	for raw in payload.get("beneficiaries") or []:
		row = {f: raw.get(f) for f in BENEFICIARY_FIELDS}
		if not (row.get("source") or "").strip():
			row["source"] = "Manual"
		doc.append("beneficiaries", row)

	doc.guardians = []
	for raw in payload.get("guardians") or []:
		doc.append("guardians", {f: raw.get(f) for f in GUARDIAN_FIELDS})


@frappe.whitelist()
def save_form(form_type, payload, submit=0):
	if form_type not in FORM_DOCTYPES:
		return _err(_("Unknown form type '{0}'.").format(form_type))
	doctype = FORM_DOCTYPES[form_type]

	if isinstance(payload, str):
		payload = json.loads(payload)
	submit = int(submit or 0)

	employee = get_employee_for_user()
	if not employee:
		return _err(_(_NO_EMPLOYEE_MSG))

	settings = frappe.get_cached_doc("Occupational Scheme Settings")
	if submit and not settings.enrolment_open:
		return _err(_("Enrolment is currently closed. Contact HR or your Compliance Officer."))

	latest = _latest_doc_name(doctype, employee)

	if latest and latest.status in ACTIVE_STATUSES:
		if latest.status not in EDITABLE_STATUSES:
			return _err(
				_("Your form is in status '{0}' and cannot be edited.").format(latest.status)
			)
		doc = frappe.get_doc(doctype, latest.name)
	else:
		emp = frappe.db.get_value(
			"Employee",
			employee,
			["employee_name", "employee_number", "department", "designation"],
			as_dict=True,
		)
		doc = frappe.new_doc(doctype)
		doc.employee = employee
		doc.employee_name = emp.employee_name or ""
		doc.employee_number = emp.employee_number or ""
		doc.department = emp.department or ""
		doc.designation = emp.designation or ""
		doc.scheme_name = settings.scheme_name or ""
		if latest:
			doc.amends = latest.name

	for fieldname in STAFF_FIELDS[form_type]:
		if fieldname in payload:
			doc.set(fieldname, payload.get(fieldname))

	_rebuild_children(doc, payload)

	if any((row.source or "") == "Business Central" for row in doc.beneficiaries):
		doc.bc_prefill_used = 1
		if not doc.bc_prefill_fetched_on:
			doc.bc_prefill_fetched_on = now_datetime()

	if submit:
		doc.status = "Submitted"

	doc.save(ignore_permissions=True)
	return _ok({"name": doc.name, "status": doc.status})


# ---------------------------------------------------------------------------
# Officer endpoints
# ---------------------------------------------------------------------------

def _require_officer(doctype):
	frappe.has_permission(doctype, ptype="write", throw=True)


@frappe.whitelist()
def get_forms(form_type, status=None, search=None, department=None, page=1, page_length=50):
	if form_type not in FORM_DOCTYPES:
		return _err(_("Unknown form type '{0}'.").format(form_type))
	doctype = FORM_DOCTYPES[form_type]
	_require_officer(doctype)

	page = max(1, int(page or 1))
	page_length = int(page_length or 50)
	if page_length <= 0:
		page_length = 50

	filters = []
	if status:
		filters.append(["status", "=", status])
	if department:
		if department == "Unassigned":
			filters.append(["department", "is", "not set"])
		else:
			filters.append(["department", "=", department])

	or_filters = None
	if search and search.strip():
		term = "%{0}%".format(search.strip())
		or_filters = [
			["employee_name", "like", term],
			["employee", "like", term],
			["employee_number", "like", term],
		]

	total_count = len(
		frappe.get_all(doctype, filters=filters, or_filters=or_filters, fields=["name"])
	)

	rows = frappe.get_all(
		doctype,
		filters=filters,
		or_filters=or_filters,
		fields=["name", "employee", "employee_name", "employee_number", "department", "status", "submitted_on"],
		order_by="employee_name asc, name asc",
		limit=page_length,
		offset=(page - 1) * page_length,
	)

	result = [
		{
			"name": row.name,
			"employee": row.employee or "",
			"employee_name": row.employee_name or "",
			"employee_number": row.employee_number or "",
			"department": row.department or "",
			"status": row.status,
			"submitted_on": str(row.submitted_on) if row.submitted_on else None,
		}
		for row in rows
	]

	meta = {
		"total_count": total_count,
		"page": page,
		"page_length": page_length,
		"returned": len(result),
	}
	return _ok(result, meta=meta)


@frappe.whitelist()
def get_form_detail(form_type, name):
	if form_type not in FORM_DOCTYPES:
		return _err(_("Unknown form type '{0}'.").format(form_type))
	doctype = FORM_DOCTYPES[form_type]
	_require_officer(doctype)

	doc = frappe.get_doc(doctype, name)
	return _ok(_serialize_doc(doc))


@frappe.whitelist()
def review_form(form_type, name, action, remarks=None):
	if form_type not in FORM_DOCTYPES:
		return _err(_("Unknown form type '{0}'.").format(form_type))
	doctype = FORM_DOCTYPES[form_type]
	frappe.has_permission(doctype, doc=name, ptype="write", throw=True)

	allowed_actions = {"Reviewed", "Needs More Info", "Rejected"}
	if action not in allowed_actions:
		return _err(_("Invalid action. Must be one of: Reviewed, Needs More Info, Rejected."))

	if action in ("Needs More Info", "Rejected") and not (remarks or "").strip():
		return _err(_("Remarks are required for action '{0}'.").format(action))

	doc = frappe.get_doc(doctype, name)
	if doc.status != "Submitted":
		return _err(
			_("Only forms in 'Submitted' status can be reviewed. Current status: {0}.").format(doc.status)
		)

	doc.append(
		"review_actions",
		{
			"action": action,
			"reviewer": frappe.session.user,
			"action_on": now_datetime(),
			"remarks": remarks or "",
		},
	)
	doc.status = action
	if doctype == "Beneficiary Nomination" and action == "Reviewed" and not doc.trustee_name:
		doc.trustee_name = frappe.utils.get_fullname(frappe.session.user)
		doc.trustee_user = frappe.session.user
	doc.save(ignore_permissions=True)

	return _ok({"name": doc.name, "status": doc.status})


@frappe.whitelist()
def certify_form(form_type, name, trustee_name=None, documents_checked=None):
	if form_type != "scheme":
		return _err(_("Trustee certification applies to the Occupational Scheme Form only."))
	doctype = FORM_DOCTYPES[form_type]
	frappe.has_permission(doctype, doc=name, ptype="write", throw=True)

	doc = frappe.get_doc(doctype, name)
	if doc.status not in ("Submitted", "Reviewed"):
		return _err(
			_("Only submitted or reviewed forms can be certified. Current status: {0}.").format(doc.status)
		)

	user = frappe.session.user
	if user in (doc.trustee_1_user, doc.trustee_2_user):
		return _err(_("You have already certified this form."))

	trustee_name = (trustee_name or "").strip() or frappe.utils.get_fullname(user)

	if not doc.trustee_1_user:
		doc.trustee_1_name = trustee_name
		doc.trustee_1_user = user
		doc.trustee_1_certified_on = now_datetime()
	elif not doc.trustee_2_user:
		doc.trustee_2_name = trustee_name
		doc.trustee_2_user = user
		doc.trustee_2_certified_on = now_datetime()
	else:
		return _err(_("Both trustee certification slots are already filled."))

	if documents_checked:
		doc.documents_checked = documents_checked

	doc.save(ignore_permissions=True)
	return _ok({
		"name": doc.name,
		"trustee_1_name": doc.trustee_1_name,
		"trustee_2_name": doc.trustee_2_name,
	})


@frappe.whitelist()
def get_scheme_dashboard():
	_require_officer("Occupational Scheme Form")

	active_employees = frappe.db.count("Employee", {"status": "Active"})
	data = {"active_employees": active_employees, "forms": {}}

	for form_type, doctype in FORM_DOCTYPES.items():
		rows = frappe.get_all(doctype, fields=["name", "status", "department", "employee"])

		status_counts = {}
		dept_map = {}
		reviewed_employees = set()

		for row in rows:
			status_counts[row.status] = status_counts.get(row.status, 0) + 1
			if row.status == "Superseded":
				continue
			dept = row.department or "Unassigned"
			if dept not in dept_map:
				dept_map[dept] = {"department": dept, "reviewed": 0, "total": 0}
			dept_map[dept]["total"] += 1
			if row.status == "Reviewed":
				dept_map[dept]["reviewed"] += 1
				reviewed_employees.add(row.employee)

		real_depts = sorted(d for d in dept_map if d != "Unassigned")
		departments = real_depts + (["Unassigned"] if "Unassigned" in dept_map else [])

		completion_percent = (
			round((len(reviewed_employees) / active_employees) * 100, 2) if active_employees else 0.0
		)

		data["forms"][form_type] = {
			"doctype": doctype,
			"status_counts": status_counts,
			"by_department": list(dept_map.values()),
			"departments": departments,
			"reviewed_employees": len(reviewed_employees),
			"completion_percent": completion_percent,
		}

	return _ok(data)
