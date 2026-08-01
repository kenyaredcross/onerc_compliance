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

		self._load_stored_fields()
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

	def _load_stored_fields(self):
		"""Snapshot the field rows as they currently stand in the DB.

		Read once, before `_validate_fields` mutates `self.fields`, so both the
		schema-freeze check and the per-row content checks can tell an untouched
		row apart from one the officer actually edited. Without this, editing a
		non-schema field (typically the deadline) on an Active requirement could
		be rejected because validation had rewritten a row a moment earlier.
		"""
		self._stored_field_rows = []
		self._stored_fields_by_name = {}
		if self.is_new():
			return

		old_doc = frappe.get_doc("Compliance Requirement", self.name)
		self._stored_field_rows = list(old_doc.fields)
		for row in old_doc.fields:
			self._stored_fields_by_name[row.name] = row

	def _row_is_untouched(self, row):
		"""True when this row is byte-for-byte the schema already stored."""
		stored = self._stored_fields_by_name.get(row.name)
		if stored is None:
			return False
		return self._row_signature(stored) == self._row_signature(row)

	def _validate_fields(self):
		seen_names = {}
		for row in self.fields:
			# A pre-existing row the officer did not touch is left alone. Legacy
			# rows can carry a blank fieldname or a Select with no Options; those
			# must not block an unrelated edit such as extending the deadline.
			# Any row that is new or genuinely changed is still fully validated.
			untouched = self._row_is_untouched(row)

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

			if untouched:
				continue

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

	@staticmethod
	def _resolved_fieldname(row):
		"""The fieldname this row settles on once `_validate_fields` has run.

		A stored row may have a blank fieldname (legacy or imported data).
		Validation fills it in from the label, so comparing the raw column would
		report a schema change on a save that touched nothing. Resolving both
		sides the same way makes the comparison invariant to that rewrite.
		"""
		fieldname = (row.fieldname or "").strip()
		if fieldname:
			return fieldname
		return frappe.scrub(row.label or "")

	@staticmethod
	def _normalize_options(options):
		"""Collapse Select options to their meaningful lines.

		The Desk textarea round-trips trailing newlines and stray indentation, so
		"A\nB\n" and "A\nB" describe the same choice list and must compare equal.
		"""
		lines = []
		for line in (options or "").splitlines():
			line = line.strip()
			if line:
				lines.append(line)
		return "\n".join(lines)

	def _row_signature(self, row):
		"""The parts of a field row that actually constitute the schema.

		`description` is deliberately excluded (it is presentational), as are
		bookkeeping columns like name/idx/modified. Label whitespace and Select
		option whitespace are normalized so cosmetic round-tripping is not
		mistaken for a schema edit.
		"""
		return (
			self._resolved_fieldname(row),
			(row.fieldtype or "").strip(),
			" ".join((row.label or "").split()),
			self._normalize_options(row.options),
			int(row.mandatory or 0),
		)

	def _validate_schema_freeze(self):
		if self.is_new():
			return
		if self._prev_status not in ("Active", "Closed"):
			return

		# Ordered comparison: adding, removing, editing *or reordering* a field is
		# a schema change and stays blocked (ADR-001). Only cosmetic differences
		# that do not alter the schema are tolerated, so that editing the deadline
		# or any other non-schema field always saves cleanly.
		old_sig = [self._row_signature(row) for row in self._stored_field_rows]
		new_sig = [self._row_signature(row) for row in self.fields]

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
