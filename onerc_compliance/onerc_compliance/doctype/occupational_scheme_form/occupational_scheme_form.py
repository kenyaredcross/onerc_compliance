# Copyright (c) 2026, Kelvin Njenga and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

from onerc_compliance.scheme_utils import (
	apply_submit_timestamps,
	capture_prev_status,
	enforce_lock,
	enforce_one_active,
	enforce_transition,
	is_submit_action,
	require_fields,
	supersede_previous,
	validate_beneficiaries,
	validate_guardians,
	validate_review_remarks,
)

DOCTYPE = "Occupational Scheme Form"

SUBMIT_REQUIRED_FIELDS = [
	("member_full_name", "Member's Full Name"),
	("date_of_birth", "Date of Birth"),
	("member_number", "Member Number"),
	("id_number", "ID No."),
	("bank_account_name", "Account Name"),
	("bank_name", "Bank"),
	("bank_account_number", "Account Number"),
]


class OccupationalSchemeForm(Document):
	def validate(self):
		capture_prev_status(self, DOCTYPE)
		enforce_lock(self)
		enforce_one_active(self, DOCTYPE)
		enforce_transition(self)
		validate_review_remarks(self)

		if is_submit_action(self):
			require_fields(self, SUBMIT_REQUIRED_FIELDS)
			if not self.declaration_accepted:
				frappe.throw(_("You must accept the declaration before submitting."))
			if self.avc_amount and self.avc_percent:
				frappe.throw(
					_("Additional Voluntary Contributions: fill either an amount or a percentage, not both.")
				)
			# Beneficiaries are nominated on the Beneficiary Nomination form;
			# this form only validates them if rows were provided anyway.
			if self.beneficiaries:
				validate_beneficiaries(self)
				validate_guardians(self)
			apply_submit_timestamps(self)

	def on_update(self):
		if self.status == "Reviewed" and getattr(self, "_prev_status", None) != "Reviewed":
			supersede_previous(self, DOCTYPE)
