# Copyright (c) 2026, Kelvin Njenga and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


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
		self._validate_schema_freeze()

	def on_update(self):
		if self.status == "Active" and self._prev_status != "Active":
			self._generate_submissions()

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
