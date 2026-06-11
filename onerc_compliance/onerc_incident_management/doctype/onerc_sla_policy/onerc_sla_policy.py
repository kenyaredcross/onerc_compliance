# Copyright (c) 2026, Kelvin Njenga and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class OnercSLAPolicy(Document):
	def validate(self):
		if (
			self.first_response_minutes
			and self.resolution_minutes
			and self.resolution_minutes < self.first_response_minutes
		):
			frappe.throw("Resolution target cannot be sooner than the first-response target.")
