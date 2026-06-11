# Copyright (c) 2026, Kelvin Njenga and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class OnercRemoteSupportSession(Document):
	def validate(self):
		if not self.status:
			self.status = "Requested"
