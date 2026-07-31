# Copyright (c) 2026, Kelvin Njenga and contributors
# For license information, please see license.txt

import json

import frappe
from frappe import _
from frappe.utils import now_datetime

from onerc_compliance.scheme_utils import ACTIVE_STATUSES
from onerc_compliance.utils import get_employee_for_user


def _ok(data, message="", meta=None):
	return {"status": "success", "data": data, "message": message, "meta": meta or {}}


def _err(message, data=None):
	return {"status": "error", "data": data if data is not None else [], "message": message, "meta": {}}


DOCTYPE = "Pension Compliance Form"

EDITABLE_STATUSES = ("Draft", "Needs More Info")

# Fields staff may write — lifecycle/review/trustee fields are deliberately
# excluded so a crafted payload cannot self-approve.
STAFF_FIELDS = [
	"member_full_name", "occupation", "date_of_birth", "marital_status",
	"member_number", "date_of_admission", "date_of_appointment",
	"mobile_number", "email", "personal_email", "kra_pin", "id_number", "details_confirmed",
	"avc_amount", "avc_percent",
	"bank_account_name", "bank_name", "bank_branch", "bank_account_number",
	"bank_town_city", "bank_code", "branch_code", "swift_code", "sort_or_iban_code",
	"declaration_accepted", "signed_at",
	"data_consent", "marketing_consent",
]

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
	"""
	if not employee_number:
		return [], "unavailable", _("No employee number on your staff record.")

	path = "EmployeeRelatives?query=$filter=EmployeeNo eq '{0}'".format(employee_number)
	friendly = _("HR records are unreachable right now; you can still fill the form manually.")

	try:
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
		"scheme_name": doc.scheme_name or "",
		"submitted_on": str(doc.submitted_on) if doc.submitted_on else None,
		"declaration_date": str(doc.declaration_date) if doc.declaration_date else None,
		"amends": doc.amends,
		"bc_prefill_used": bool(doc.bc_prefill_used),
		"witness_name": doc.witness_name or "",
		"documents_checked": doc.documents_checked or "",
		"date_received_by_trustee": (
			str(doc.date_received_by_trustee) if doc.date_received_by_trustee else None
		),
	}

	for fieldname in STAFF_FIELDS:
		value = doc.get(fieldname)
		if hasattr(value, "isoformat"):
			value = str(value)
		data[fieldname] = value

	for fieldname in ("trustee_1_name", "trustee_1_certified_on",
		"trustee_2_name", "trustee_2_certified_on"):
		value = doc.get(fieldname)
		data[fieldname] = str(value) if value else None

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


def _latest_doc(employee):
	rows = frappe.get_all(
		DOCTYPE,
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
def get_my_form():
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

	latest = _latest_doc(employee)
	doc_data = None
	editable = True
	local_bc_keys = set()
	local_id_numbers = set()

	if latest:
		doc = frappe.get_doc(DOCTYPE, latest.name)
		doc_data = _serialize_doc(doc)
		editable = doc.status in EDITABLE_STATUSES
		for row in doc.beneficiaries:
			if row.bc_relative_no:
				local_bc_keys.add(row.bc_relative_no)
			if (row.id_number or "").strip():
				local_id_numbers.add(row.id_number.strip())

	history = [
		{
			"name": row.name,
			"status": row.status,
			"submitted_on": str(row.submitted_on) if row.submitted_on else None,
		}
		for row in frappe.get_all(
			DOCTYPE,
			filters={"employee": employee},
			fields=["name", "status", "submitted_on"],
			order_by="creation desc",
		)
	]

	can_start_new = not latest or latest.status not in ACTIVE_STATUSES

	bc = {"status": "skipped", "error": "", "suggestions": []}
	if editable or can_start_new:
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
		"settings": _get_settings(),
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
			"personal_email": emp.personal_email or "",
		},
		"form": {
			"doc": doc_data,
			"editable": editable if latest else True,
			"can_start_new": can_start_new,
			"history": history,
		},
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
def save_form(payload, submit=0):
	if isinstance(payload, str):
		payload = json.loads(payload)
	submit = int(submit or 0)

	employee = get_employee_for_user()
	if not employee:
		return _err(_(_NO_EMPLOYEE_MSG))

	settings = frappe.get_cached_doc("Occupational Scheme Settings")
	if submit and not settings.enrolment_open:
		return _err(_("Enrolment is currently closed. Contact HR or your Compliance Officer."))

	latest = _latest_doc(employee)

	if latest and latest.status in ACTIVE_STATUSES:
		if latest.status not in EDITABLE_STATUSES:
			return _err(
				_("Your form is in status '{0}' and cannot be edited.").format(latest.status)
			)
		doc = frappe.get_doc(DOCTYPE, latest.name)
	else:
		emp = frappe.db.get_value(
			"Employee",
			employee,
			["employee_name", "employee_number", "department", "designation"],
			as_dict=True,
		)
		doc = frappe.new_doc(DOCTYPE)
		doc.employee = employee
		doc.employee_name = emp.employee_name or ""
		doc.employee_number = emp.employee_number or ""
		doc.department = emp.department or ""
		doc.designation = emp.designation or ""
		doc.scheme_name = settings.scheme_name or ""
		if latest:
			doc.amends = latest.name

	for fieldname in STAFF_FIELDS:
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

@frappe.whitelist()
def get_forms(status=None, search=None, department=None, page=1, page_length=50):
	frappe.has_permission(DOCTYPE, ptype="write", throw=True)

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
		frappe.get_all(DOCTYPE, filters=filters, or_filters=or_filters, fields=["name"])
	)

	rows = frappe.get_all(
		DOCTYPE,
		filters=filters,
		or_filters=or_filters,
		fields=["name", "employee_name", "employee_number", "department", "status", "submitted_on"],
		order_by="employee_name asc, name asc",
		limit=page_length,
		offset=(page - 1) * page_length,
	)

	result = [
		{
			"name": row.name,
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
def get_form_detail(name):
	frappe.has_permission(DOCTYPE, ptype="write", throw=True)
	doc = frappe.get_doc(DOCTYPE, name)
	return _ok(_serialize_doc(doc))


@frappe.whitelist()
def officer_update_form(name, payload):
	"""Let a reviewer correct a member's details on any form, regardless of
	status. Lifecycle/review/trustee fields stay untouched; beneficiary
	rules are re-validated so an edit cannot break a submitted form."""
	frappe.has_permission(DOCTYPE, doc=name, ptype="write", throw=True)

	if isinstance(payload, str):
		payload = json.loads(payload)

	doc = frappe.get_doc(DOCTYPE, name)

	for fieldname in STAFF_FIELDS:
		if fieldname in payload:
			doc.set(fieldname, payload.get(fieldname))

	if "beneficiaries" in payload or "guardians" in payload:
		_rebuild_children(doc, payload)

	if doc.beneficiaries:
		from onerc_compliance.scheme_utils import validate_beneficiaries, validate_guardians

		validate_beneficiaries(doc)
		validate_guardians(doc)

	doc.save(ignore_permissions=True)
	return _ok(_serialize_doc(doc))


@frappe.whitelist()
def review_form(name, action, remarks=None):
	frappe.has_permission(DOCTYPE, doc=name, ptype="write", throw=True)

	allowed_actions = {"Reviewed", "Approved", "Needs More Info", "Rejected"}
	if action not in allowed_actions:
		return _err(_("Invalid action. Must be one of: Reviewed, Approved, Needs More Info, Rejected."))

	if action in ("Needs More Info", "Rejected") and not (remarks or "").strip():
		return _err(_("Remarks are required for action '{0}'.").format(action))

	doc = frappe.get_doc(DOCTYPE, name)

	if action == "Approved":
		from onerc_compliance.scheme_utils import user_is_trustee

		if not user_is_trustee():
			return _err(_("Only a Pension Trustee can approve forms."))
		if doc.status != "Reviewed":
			return _err(
				_("Only forms in 'Reviewed' status can be approved. Current status: {0}.").format(doc.status)
			)
	elif doc.status != "Submitted":
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
	doc.save(ignore_permissions=True)

	return _ok({"name": doc.name, "status": doc.status})


@frappe.whitelist()
def certify_form(name, trustee_name=None, documents_checked=None):
	frappe.has_permission(DOCTYPE, doc=name, ptype="write", throw=True)

	doc = frappe.get_doc(DOCTYPE, name)
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
def export_forms(status=None, search=None, department=None):
	"""Download all pension compliance forms as an Excel file.

	One row per beneficiary (a form without beneficiaries still gets one
	row), so HR can process nominations straight into Business Central.
	Respects the same filters as the review list.
	"""
	frappe.has_permission(DOCTYPE, ptype="write", throw=True)

	filters = []
	if status:
		filters.append(["status", "=", status])
	if department:
		if department == "Unassigned":
			filters.append(["department", "is", "not set"])
		else:
			filters.append(["department", "=", department])

	or_filters = None
	if search and (search or "").strip():
		term = "%{0}%".format(search.strip())
		or_filters = [
			["employee_name", "like", term],
			["employee", "like", term],
			["employee_number", "like", term],
		]

	names = frappe.get_all(
		DOCTYPE,
		filters=filters,
		or_filters=or_filters,
		order_by="employee_name asc, name asc",
		pluck="name",
	)

	header = [
		"Form ID", "Status", "Employee No", "Employee Name", "Department", "Position",
		"Member's Full Name", "Date of Birth", "Marital Status", "ID No.", "KRA PIN",
		"Work Email", "Personal Email", "Mobile", "Member Number",
		"Date of Admission", "Date of Appointment", "Scheme Name",
		"AVC Amount (Kshs)", "AVC Percent",
		"Bank Account Name", "Bank", "Bank Branch", "Account Number",
		"Town/City", "Bank Code", "Branch Code", "SWIFT", "SORT/IBAN",
		"Beneficiary Name", "Relationship", "Beneficiary DOB",
		"Beneficiary ID No.", "Birth Certificate No.", "Beneficiary Mobile",
		"% Share", "Beneficiary Source", "Guardian Name", "Guardian ID No.",
		"Guardian Relationship",
		"Signed At", "Declaration Date", "Submitted On",
		"Trustee 1", "Trustee 2", "Date Received by Trustee",
	]
	data = [header]

	for name in names:
		doc = frappe.get_doc(DOCTYPE, name)

		guardians_by_beneficiary = {}
		for g in doc.guardians:
			guardians_by_beneficiary.setdefault((g.beneficiary_name or "").strip(), g)

		base = [
			doc.name, doc.status, doc.employee_number, doc.employee_name,
			doc.department, doc.occupation,
			doc.member_full_name, doc.date_of_birth, doc.marital_status,
			doc.id_number, doc.kra_pin, doc.email, doc.personal_email,
			doc.mobile_number, doc.member_number,
			doc.date_of_admission, doc.date_of_appointment, doc.scheme_name,
			doc.avc_amount, doc.avc_percent,
			doc.bank_account_name, doc.bank_name, doc.bank_branch,
			doc.bank_account_number, doc.bank_town_city, doc.bank_code,
			doc.branch_code, doc.swift_code, doc.sort_or_iban_code,
		]
		tail = [
			doc.signed_at, doc.declaration_date, doc.submitted_on,
			doc.trustee_1_name, doc.trustee_2_name, doc.date_received_by_trustee,
		]

		if doc.beneficiaries:
			for b in doc.beneficiaries:
				g = guardians_by_beneficiary.get((b.full_name or "").strip())
				data.append(base + [
					b.full_name, b.relationship, b.date_of_birth,
					b.id_number, b.birth_certificate_no, b.mobile,
					b.share_percent,
					"HR records" if b.source == "Business Central" else "Member",
					g.guardian_name if g else "",
					g.id_number if g else "",
					g.relationship_to_beneficiary if g else "",
				] + tail)
		else:
			data.append(base + [""] * 11 + tail)

	from frappe.utils.xlsxutils import make_xlsx

	xlsx = make_xlsx(data, "Pension Compliance")
	frappe.response["filename"] = "pension_compliance_forms.xlsx"
	frappe.response["filecontent"] = xlsx.getvalue()
	frappe.response["type"] = "binary"


def _render_membership_html(doc):
	"""Render the pixel-accurate Jubilee Membership Application Form replica
	(4 pages incl. the data-subject consent) filled with the member's data.
	Signature and stamp boxes stay blank for wet signing."""
	from frappe.utils import escape_html, formatdate

	def esc(value):
		return escape_html(str(value)) if value not in (None, "") else ""

	def fmt_date(value):
		return formatdate(value, "dd/MM/yyyy") if value else ""

	def fmt_share(value):
		if not value:
			return ""
		value = float(value)
		return str(int(value)) if value == int(value) else str(round(value, 2))

	beneficiaries = [
		{
			"name": esc(b.full_name),
			"email": esc(b.email),
			"mobile": esc(b.mobile),
			"dob": fmt_date(b.date_of_birth),
			"id_no": esc(b.id_number or b.birth_certificate_no),
			"relationship": esc(b.relationship),
			"share": fmt_share(b.share_percent),
		}
		for b in doc.beneficiaries
	]
	while len(beneficiaries) < 6:
		beneficiaries.append({k: "" for k in ("name", "email", "mobile", "dob", "id_no", "relationship", "share")})

	guardians = [
		{
			"name": esc(g.guardian_name),
			"email": esc(g.email),
			"mobile": esc(g.mobile),
			"id_no": esc(g.id_number),
			"beneficiary": esc(g.beneficiary_name),
			"relationship": esc(g.relationship_to_beneficiary),
		}
		for g in doc.guardians
	]
	while len(guardians) < 4:
		guardians.append({k: "" for k in ("name", "email", "mobile", "id_no", "beneficiary", "relationship")})

	context = {
		"form_id": esc(doc.name),
		"scheme_name": esc(doc.scheme_name),
		"member_name": esc(doc.member_full_name),
		"occupation": esc(doc.occupation),
		"dob": fmt_date(doc.date_of_birth),
		"member_no": esc(doc.member_number),
		"admission_date": fmt_date(doc.date_of_admission),
		"appointment_date": fmt_date(doc.date_of_appointment),
		"mobile": esc(doc.mobile_number),
		"email": esc(doc.email or doc.personal_email),
		"kra_pin": esc(doc.kra_pin),
		"id_no": esc(doc.id_number),
		"avc_amount": esc(doc.avc_amount or ""),
		"avc_percent": fmt_share(doc.avc_percent),
		"account_name": esc(doc.bank_account_name),
		"bank": esc(doc.bank_name),
		"bank_branch": esc(doc.bank_branch),
		"account_number": esc(doc.bank_account_number),
		"town_city": esc(doc.bank_town_city),
		"bank_code": esc(doc.bank_code),
		"branch_code": esc(doc.branch_code),
		"swift_code": esc(doc.swift_code),
		"sort_iban_code": esc(doc.sort_or_iban_code),
		"nominator_name": esc(doc.member_full_name),
		"member_date": fmt_date(doc.declaration_date),
		"trustee1_name": esc(doc.trustee_1_name),
		"trustee1_date": fmt_date(doc.trustee_1_certified_on),
		"trustee2_name": esc(doc.trustee_2_name),
		"trustee2_date": fmt_date(doc.trustee_2_certified_on),
		"consent_name": esc(doc.member_full_name),
		"consent_date": fmt_date(doc.declaration_date),
		"dp_consent_checked": "checked" if doc.data_consent == "I Consent" else "",
		"dp_do_not_consent_checked": "checked" if doc.data_consent == "I Do Not Consent" else "",
		"mkt_consent_checked": "checked" if doc.marketing_consent == "I Consent" else "",
		"mkt_do_not_consent_checked": "checked" if doc.marketing_consent == "I Do Not Consent" else "",
		"beneficiaries": beneficiaries,
		"guardians": guardians,
	}

	template = open(
		frappe.get_app_path("onerc_compliance", "templates", "pension", "jubilee_membership_form.html"),
		encoding="utf-8",
	).read()
	return frappe.render_template(template, context)


def _build_membership_pdf(doc):
	"""The filled Jubilee form as PDF bytes (wkhtmltopdf-compatible)."""
	from frappe.utils.pdf import get_pdf

	html = _render_membership_html(doc)

	# wkhtmltopdf's WebKit predates CSS custom properties — inline them,
	# or every var()-based position/colour/border silently collapses.
	css_vars = {
		"--red": "#CD143D", "--maroon": "#A91E47", "--grey": "#DADFE3",
		"--ink": "#231F20", "--fill": "#00337a",
		"--cl": "17.9mm", "--cw": "174.4mm", "--rc": "96.2mm", "--rw": "96.1mm",
	}
	for var, value in css_vars.items():
		html = html.replace("var({0})".format(var), value)

	# No flexbox in wkhtmltopdf either: filled-in <input>s don't stretch
	# and clip their values, so render them as plain text spans. Empty
	# inputs stay as-is (they draw the blank boxes/underlines).
	import re as _re

	html = _re.sub(
		r'<input(?![^>]*type="checkbox")[^>]*?value="([^"]*)"[^>]*>',
		r'<span class="pdfv">\1</span>',
		html,
	)
	# The consent checkboxes use appearance:none + a CSS-drawn tick,
	# neither of which wkhtmltopdf supports — draw them as bordered
	# boxes with a real tick character instead.
	html = _re.sub(
		r'<input type="checkbox"[^>]*\bchecked\b[^>]*>',
		'<span class="pdfcb">&#10004;</span>',
		html,
	)
	html = _re.sub(
		r'<input type="checkbox"[^>]*>',
		'<span class="pdfcb"></span>',
		html,
	)
	html = html.replace(
		"</head>",
		"<style>"
		"table.f td, table.f th{border:0.35mm solid #231F20 !important;}"
		".pdfv{color:#00337a;font-size:8.5pt;padding:0 1.4mm;white-space:nowrap;}"
		"td.v .pdfv{display:block;}"
		".pdfcb{display:inline-block;width:3.2mm;height:3.2mm;border:0.35mm solid #231F20;"
		"font-size:8pt;line-height:3.2mm;text-align:center;vertical-align:middle;color:#231F20;}"
		# A full 297mm page overflows wkhtmltopdf's printable area by a
		# hair and spills a blank page before each page break — shave the
		# page height slightly so each sheet fits exactly.
		"html{background:#fff;}body{padding:0;margin:0;}"
		".page{height:295mm !important;margin:0 auto !important;box-shadow:none !important;"
		"page-break-after:always;}"
		".page:last-of-type{page-break-after:auto;}"
		# frappe's get_pdf force-resets page margins to 15mm unless a
		# .print-format rule declares them — 15mm shrinks the printable
		# area below our page height and spills a blank page per sheet.
		".print-format{margin-top:0mm;margin-bottom:0mm;margin-left:0mm;margin-right:0mm;}"
		"</style></head>",
	)

	return get_pdf(
		html, options={"page-size": "A4", "margin-top": "0mm", "margin-bottom": "0mm",
			"margin-left": "0mm", "margin-right": "0mm"}
	)


@frappe.whitelist()
def export_membership_form(name, as_pdf=0):
	"""Download one form as the official Jubilee Membership Application Form."""
	frappe.has_permission(DOCTYPE, doc=name, ptype="print", throw=True)

	doc = frappe.get_doc(DOCTYPE, name)

	if int(as_pdf or 0):
		frappe.response["filename"] = "{0}_membership_application.pdf".format(doc.name)
		frappe.response["filecontent"] = _build_membership_pdf(doc)
		frappe.response["type"] = "pdf"
	else:
		frappe.response["filename"] = "{0}_membership_application.html".format(doc.name)
		frappe.response["filecontent"] = _render_membership_html(doc)
		frappe.response["type"] = "binary"


def send_approval_notification(doc):
	"""Email the configured recipients that a form was approved, attaching
	the filled Jubilee membership PDF. Called from the doctype controller
	when a form transitions to Approved."""
	settings = frappe.get_cached_doc("Occupational Scheme Settings")
	raw = settings.get("notification_emails") or ""
	recipients = [e.strip() for e in raw.replace(",", "\n").splitlines() if e.strip()]
	if not recipients:
		return

	beneficiary_lines = "".join(
		"<li>{0} ({1}) - {2}%</li>".format(
			frappe.utils.escape_html(b.full_name or ""),
			frappe.utils.escape_html(b.relationship or ""),
			b.share_percent,
		)
		for b in doc.beneficiaries
	)

	def row(label, value):
		return "<tr><td style='padding:2px 12px 2px 0;color:#666'>{0}</td><td style='padding:2px 0'><b>{1}</b></td></tr>".format(
			label, frappe.utils.escape_html(str(value)) if value else "-"
		)

	message = """
		<p>The following pension compliance form has been <b>approved</b> by the scheme trustees.
		The filled Jubilee Membership Application Form is attached as PDF.</p>
		<table style='font-size:13px'>
			{rows}
		</table>
		<p><b>Beneficiaries</b></p>
		<ul style='font-size:13px'>{beneficiaries}</ul>
	""".format(
		rows="".join([
			row("Form", doc.name),
			row("Member", doc.member_full_name),
			row("Employee No", doc.employee_number),
			row("Department", doc.department),
			row("Position", doc.occupation),
			row("Member No", doc.member_number),
			row("ID No", doc.id_number),
			row("Work Email", doc.email),
			row("Personal Email", doc.personal_email),
			row("Mobile", doc.mobile_number),
			row("Scheme", doc.scheme_name),
			row("Approved By", frappe.utils.get_fullname(frappe.session.user)),
			row("Approved On", frappe.utils.formatdate(frappe.utils.today(), "dd/MM/yyyy")),
		]),
		beneficiaries=beneficiary_lines or "<li>-</li>",
	)

	frappe.sendmail(
		recipients=recipients,
		subject=_("Pension Compliance Approved: {0} ({1})").format(
			doc.member_full_name or doc.employee_name, doc.name
		),
		message=message,
		attachments=[{
			"fname": "{0}_membership_application.pdf".format(doc.name),
			"fcontent": _build_membership_pdf(doc),
		}],
	)


@frappe.whitelist()
def get_scheme_dashboard():
	frappe.has_permission(DOCTYPE, ptype="write", throw=True)

	active_employees = frappe.db.count("Employee", {"status": "Active"})
	rows = frappe.get_all(DOCTYPE, fields=["name", "status", "department", "employee"])

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

	return _ok({
		"active_employees": active_employees,
		"status_counts": status_counts,
		"by_department": list(dept_map.values()),
		"departments": departments,
		"reviewed_employees": len(reviewed_employees),
		"completion_percent": completion_percent,
	})
