# Copyright (c) 2026, Kelvin Njenga and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import getdate, now_datetime, today

ACTIVE_STATUSES = ("Draft", "Submitted", "Needs More Info")
LOCKED_STATUSES = ("Submitted", "Reviewed", "Rejected", "Superseded")
OFFICER_ROLES = {"Compliance Officer", "HR Manager", "System Manager"}

ALLOWED_TRANSITIONS = {
	"Draft": {"Submitted"},
	"Submitted": {"Reviewed", "Needs More Info", "Rejected"},
	"Needs More Info": {"Submitted"},
	"Reviewed": {"Superseded"},
	"Rejected": set(),
	"Superseded": set(),
}


def user_is_officer(user=None):
	return bool(OFFICER_ROLES & set(frappe.get_roles(user or frappe.session.user)))


def capture_prev_status(doc, doctype):
	if doc.is_new():
		doc._prev_status = "Draft"
	else:
		doc._prev_status = frappe.db.get_value(doctype, doc.name, "status") or "Draft"


def enforce_lock(doc):
	"""Non-officers may only write while the doc is in an editable status."""
	if doc._prev_status in LOCKED_STATUSES and not user_is_officer():
		frappe.throw(
			_("This form cannot be edited because its status is '{0}'.").format(doc._prev_status)
		)


def enforce_transition(doc):
	if doc.is_new():
		if doc.status not in ("Draft", "Submitted"):
			frappe.throw(_("A new form must start as Draft or Submitted."))
		return
	if doc.status == doc._prev_status:
		return
	allowed = ALLOWED_TRANSITIONS.get(doc._prev_status, set())
	if doc.status not in allowed:
		frappe.throw(
			_("Cannot transition from '{0}' to '{1}'.").format(doc._prev_status, doc.status)
		)


def enforce_one_active(doc, doctype):
	"""At most one active (Draft/Submitted/Needs More Info) form per employee."""
	filters = {
		"employee": doc.employee,
		"status": ["in", list(ACTIVE_STATUSES)],
	}
	if not doc.is_new():
		filters["name"] = ["!=", doc.name]
	existing = frappe.db.get_value(doctype, filters, "name")
	if existing and doc.status in ACTIVE_STATUSES:
		frappe.throw(
			_("An active {0} ({1}) already exists for this employee. "
			  "Complete or withdraw it before starting a new one.").format(doctype, existing)
		)


def validate_review_remarks(doc):
	for row in doc.review_actions:
		if row.action in ("Needs More Info", "Rejected") and not (row.remarks or "").strip():
			frappe.throw(_("Remarks are required when action is '{0}'.").format(row.action))


def is_minor(date_of_birth):
	if not date_of_birth:
		return False
	dob = getdate(date_of_birth)
	ref = getdate(today())
	age = ref.year - dob.year - ((ref.month, ref.day) < (dob.month, dob.day))
	return age < 18


def validate_beneficiaries(doc):
	if not doc.beneficiaries:
		frappe.throw(_("At least one beneficiary is required."))

	total = 0.0
	names = set()
	guardian_targets = {(g.beneficiary_name or "").strip() for g in (doc.guardians or [])}

	for row in doc.beneficiaries:
		if not (row.full_name or "").strip():
			frappe.throw(_("Beneficiary row {0}: name is required.").format(row.idx))
		if not (row.relationship or "").strip():
			frappe.throw(
				_("Beneficiary '{0}': relationship to member is required.").format(row.full_name)
			)
		share = float(row.share_percent or 0)
		if share <= 0:
			frappe.throw(
				_("Beneficiary '{0}': % share must be greater than zero.").format(row.full_name)
			)
		total += share
		names.add(row.full_name.strip())

		if is_minor(row.date_of_birth):
			if not (row.birth_certificate_no or "").strip():
				frappe.throw(
					_("Beneficiary '{0}' is under 18 — a Birth Certificate No. is required.").format(
						row.full_name
					)
				)
			if row.full_name.strip() not in guardian_targets:
				frappe.throw(
					_("Beneficiary '{0}' is under 18 — a guardian entry is required.").format(
						row.full_name
					)
				)

	if abs(total - 100.0) > 0.01:
		frappe.throw(
			_("Beneficiary % shares must total exactly 100 (currently {0}).").format(round(total, 2))
		)


def validate_guardians(doc):
	names = {(b.full_name or "").strip() for b in (doc.beneficiaries or [])}
	for g in doc.guardians or []:
		if not (g.guardian_name or "").strip():
			frappe.throw(_("Guardian row {0}: name is required.").format(g.idx))
		target = (g.beneficiary_name or "").strip()
		if target not in names:
			frappe.throw(
				_("Guardian '{0}': beneficiary '{1}' does not match any beneficiary row.").format(
					g.guardian_name, target
				)
			)


def is_submit_action(doc):
	return doc.status == "Submitted" and doc._prev_status in ("Draft", "Needs More Info")


def apply_submit_timestamps(doc):
	doc.submitted_on = now_datetime()
	if not doc.declaration_date:
		doc.declaration_date = today()


def require_fields(doc, fieldname_labels):
	for fieldname, label in fieldname_labels:
		value = doc.get(fieldname)
		if isinstance(value, str):
			value = value.strip()
		if not value:
			frappe.throw(_("'{0}' is required before submitting.").format(label))


def supersede_previous(doc, doctype):
	"""When a form becomes Reviewed, archive any prior Reviewed form for the employee."""
	prior = frappe.get_all(
		doctype,
		filters={
			"employee": doc.employee,
			"status": "Reviewed",
			"name": ["!=", doc.name],
		},
		pluck="name",
	)
	for name in prior:
		frappe.db.set_value(doctype, name, "status", "Superseded")
