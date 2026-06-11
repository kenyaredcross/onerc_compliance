# Copyright (c) 2026, Kelvin Njenga and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class OnercConfigurationItem(Document):
	def validate(self):
		if not self.status:
			self.status = "Active"
		if self.parent_ci and self.parent_ci == self.name:
			frappe.throw("A Configuration Item cannot depend on itself.")
