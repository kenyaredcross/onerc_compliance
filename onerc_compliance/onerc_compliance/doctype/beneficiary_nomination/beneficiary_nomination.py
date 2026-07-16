# Copyright (c) 2026, Kelvin Njenga and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import today

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

DOCTYPE = "Beneficiary Nomination"

SUBMIT_REQUIRED_FIELDS = [
	("member_full_name", "Member's Full Name"),
	("id_number", "Member's ID No."),
]


class BeneficiaryNomination(Document):
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
			validate_beneficiaries(self)
			validate_guardians(self)
			apply_submit_timestamps(self)

	def on_update(self):
		if self.status == "Reviewed" and getattr(self, "_prev_status", None) != "Reviewed":
			if not self.date_received_by_trustee:
				self.db_set("date_received_by_trustee", today(), update_modified=False)
			supersede_previous(self, DOCTYPE)
