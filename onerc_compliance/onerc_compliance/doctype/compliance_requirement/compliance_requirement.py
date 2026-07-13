# Copyright (c) 2026, Kelvin Njenga and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_datetime, now_datetime


class ComplianceRequirement(Document):
	def validate(self):
		# Capture the current DB status before any changes land
		if not self.is_new():
			self._prev_status = (
				frappe.db.get_value("Compliance Requirement", self.name, "status") or "Draft"
			)
		else:
			self._prev_status = "Draft"

		self._validate_fields()
		self._validate_targeting()
		self._validate_deadline_not_past()
		self._validate_schema_freeze()

	def on_update(self):
		became_active = self.status == "Active" and self._prev_status != "Active"
		if became_active:
			self._generate_submissions()

		# Reopen path: when an expired (Closed) requirement is set back to Active
		# — typically after its deadline was extended — the daily job has already
		# flipped non-submitters to Overdue and those submissions can no longer be
		# edited by staff. Reset them to Pending so people can fill them in again.
		# Submitted / Reviewed / Rejected submissions are intentionally left alone.
		if self.status == "Active" and self._prev_status == "Closed":
			self._reset_overdue_submissions()

	# ------------------------------------------------------------------
	# Helpers
	# ------------------------------------------------------------------

	def _validate_fields(self):
		seen_names = {}
		for row in self.fields:
			if not row.label:
				frappe.throw(_("Every field row must have a label."))

			if not row.fieldname:
				row.fieldname = frappe.scrub(row.label)

			base = row.fieldname
			count = seen_names.get(base, 0) + 1
			seen_names[base] = count
			if count > 1:
				row.fieldname = f"{base}_{count}"
			else:
				seen_names[base] = 1

			if row.fieldtype == "Select" and not (row.options or "").strip():
				frappe.throw(
					_("Field '{0}' is of type Select and must have Options.").format(row.label)
				)

	def _validate_deadline_not_past(self):
		# Guardrail against reactivating with a stale date: an Active requirement
		# whose deadline is already in the past would just be Closed again by the
		# next run of close_expired_requirements. Force a future deadline first.
		if self.status != "Active":
			return
		if not self.deadline:
			return
		if get_datetime(self.deadline) < now_datetime():
			frappe.throw(
				_("The deadline has passed. Set a future deadline before activating this requirement.")
			)

	def _reset_overdue_submissions(self):
		overdue = frappe.get_all(
			"Compliance Submission",
			filters={"requirement": self.name, "status": "Overdue"},
			pluck="name",
		)
		for sub_name in overdue:
			sub = frappe.get_doc("Compliance Submission", sub_name)
			sub.status = "Pending"
			sub.save(ignore_permissions=True)

	def _validate_targeting(self):
		if self.target_type == "By Department":
			if not self.target_departments:
				frappe.throw(
					_("At least one target department is required for 'By Department' targeting.")
				)

	def _make_fields_signature(self, fields):
		result = []
		for row in fields:
			result.append((
				row.fieldname or "",
				row.fieldtype or "",
				row.label or "",
				row.options or "",
				int(row.mandatory or 0),
			))
		return result

	def _validate_schema_freeze(self):
		if self.is_new():
			return
		if self._prev_status not in ("Active", "Closed"):
			return

		old_doc = frappe.get_doc("Compliance Requirement", self.name)
		old_sig = self._make_fields_signature(old_doc.fields)
		new_sig = self._make_fields_signature(self.fields)

		if old_sig != new_sig:
			frappe.throw(
				_("The field schema cannot be changed once the requirement is Active or Closed.")
			)

	def _generate_submissions(self):
		from onerc_compliance.utils import bulk_ensure_submissions, ensure_submission, get_in_scope_employees

		employees = get_in_scope_employees(self)

		if len(employees) > 200:
			frappe.enqueue(
				"onerc_compliance.utils.bulk_ensure_submissions",
				queue="long",
				requirement_name=self.name,
				employee_names=employees,
			)
		else:
			for emp in employees:
				ensure_submission(self.name, emp)


def reopen_requirement(name):
	"""Set a requirement back to Active and reopen its Overdue submissions.

	Operational one-shot for a requirement that the daily job already closed:
	flips the requirement to Active (which throws if the deadline is still in
	the past — extend it first) and resets every Overdue submission back to
	Pending so staff can fill them in again. Safe to run from
	`bench --site <site> execute
	onerc_compliance.onerc_compliance.doctype.compliance_requirement.compliance_requirement.reopen_requirement
	--kwargs '{"name": "COMPLIANCE-2026-0001"}'`.
	"""
	doc = frappe.get_doc("Compliance Requirement", name)
	doc.status = "Active"
	doc.save(ignore_permissions=True)

	# on_update already resets Overdue -> Pending when reopening from Closed;
	# repeat it here so the helper is self-contained regardless of prior status.
	overdue = frappe.get_all(
		"Compliance Submission",
		filters={"requirement": name, "status": "Overdue"},
		pluck="name",
	)
	for sub_name in overdue:
		sub = frappe.get_doc("Compliance Submission", sub_name)
		sub.status = "Pending"
		sub.save(ignore_permissions=True)

	frappe.db.commit()
	return {"requirement": name, "reopened_submissions": len(overdue)}
