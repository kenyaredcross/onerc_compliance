# Copyright (c) 2026, Kelvin Njenga and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime


ALLOWED_TRANSITIONS = {
	"Pending": {"Submitted", "Reviewed", "Exempted", "Overdue"},
	"Submitted": {"Reviewed", "Needs More Info", "Rejected"},
	"Needs More Info": {"Submitted", "Reviewed", "Overdue"},
	"Rejected": {"Submitted"},
	"Overdue": {"Submitted"},
	"Reviewed": set(),
	"Exempted": set(),
}


class ComplianceSubmission(Document):
	def validate(self):
		if not self.is_new():
			self._prev_status = (
				frappe.db.get_value("Compliance Submission", self.name, "status") or "Pending"
			)
		else:
			self._prev_status = "Pending"

		self._enforce_unique_per_pair()
		self._enforce_transition()
		self._validate_review_remarks()
		self._validate_submitted_values()

	def on_update(self):
		notify_statuses = {"Reviewed", "Needs More Info", "Rejected"}
		if self.status in notify_statuses and self._prev_status != self.status:
			# Auto-complete (requires_review=False) sets Reviewed with no review_actions rows.
			# There is no human reviewer, so nothing to notify the employee about.
			if self.status == "Reviewed" and not self.review_actions:
				return
			self._email_employee()

	# ------------------------------------------------------------------
	# Helpers
	# ------------------------------------------------------------------

	def _enforce_unique_per_pair(self):
		if self.is_new():
			existing = frappe.db.get_value(
				"Compliance Submission",
				{"requirement": self.requirement, "employee": self.employee},
				"name",
			)
			if existing:
				frappe.throw(
					_("A submission already exists for employee {0} on requirement {1}.").format(
						self.employee, self.requirement
					)
				)
		else:
			existing = frappe.db.get_value(
				"Compliance Submission",
				{
					"requirement": self.requirement,
					"employee": self.employee,
					"name": ["!=", self.name],
				},
				"name",
			)
			if existing:
				frappe.throw(
					_("A submission already exists for employee {0} on requirement {1}.").format(
						self.employee, self.requirement
					)
				)

	def _enforce_transition(self):
		if self.is_new():
			return
		allowed = ALLOWED_TRANSITIONS.get(self._prev_status, set())
		if self.status != self._prev_status and self.status not in allowed:
			frappe.throw(
				_("Cannot transition from '{0}' to '{1}'.").format(self._prev_status, self.status)
			)

	def _validate_review_remarks(self):
		for row in self.review_actions:
			if row.action in ("Needs More Info", "Rejected") and not (row.remarks or "").strip():
				frappe.throw(
					_("Remarks are required when action is '{0}'.").format(row.action)
				)

	def _validate_submitted_values(self):
		if self.status != "Submitted":
			return

		req = frappe.get_doc("Compliance Requirement", self.requirement)
		mandatory_fieldnames = set()
		for schema_field in req.fields:
			if schema_field.mandatory:
				mandatory_fieldnames.add(schema_field.fieldname)

		if not mandatory_fieldnames:
			if not self.submitted_on:
				self.submitted_on = now_datetime()
			return

		answers = {}
		for val_row in self.values:
			answers[val_row.field_name] = val_row

		for fname in mandatory_fieldnames:
			row = answers.get(fname)
			schema_field = next(
				(f for f in req.fields if f.fieldname == fname), None
			)
			if not schema_field:
				continue

			blank = True
			if row:
				if schema_field.fieldtype == "Check":
					blank = not int(row.value_check or 0)
				elif schema_field.fieldtype == "Date":
					blank = not row.value_date
				elif schema_field.fieldtype == "Attach":
					blank = not row.attachment
				else:
					blank = not (row.value or "").strip()

			if blank:
				frappe.throw(
					_("Mandatory field '{0}' has no answer.").format(schema_field.label or fname)
				)

		if not self.submitted_on:
			self.submitted_on = now_datetime()

	def _email_employee(self):
		emp = frappe.db.get_value(
			"Employee",
			self.employee,
			["company_email", "user_id"],
			as_dict=True,
		)
		if not emp:
			return

		email = emp.company_email or emp.user_id
		if not email:
			return

		latest_remark = ""
		for row in reversed(self.review_actions):
			if row.remarks:
				latest_remark = row.remarks
				break

		subject = _("Compliance submission status updated: {0}").format(self.status)
		message_parts = [
			_("Your compliance submission {0} has been updated to: {1}.").format(
				self.name, self.status
			)
		]
		if latest_remark:
			message_parts.append(_("Reviewer note: {0}").format(latest_remark))

		frappe.sendmail(
			recipients=[email],
			subject=subject,
			message="<br>".join(message_parts),
			now=True,
		)
