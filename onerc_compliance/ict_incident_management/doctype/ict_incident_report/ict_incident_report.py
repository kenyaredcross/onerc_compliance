# Copyright (c) 2026, Kelvin Njenga and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime


class ICTIncidentReport(Document):
	def validate(self):
		if not self.logged_by:
			self.logged_by = frappe.session.user
		if not self.date_reported:
			self.date_reported = now_datetime()

		for row in self.progress_updates:
			if not row.update_datetime:
				row.update_datetime = now_datetime()
			if not row.updated_by:
				row.updated_by = frappe.session.user

	def after_insert(self):
		if not self.incident_id:
			self.db_set("incident_id", self.name)
