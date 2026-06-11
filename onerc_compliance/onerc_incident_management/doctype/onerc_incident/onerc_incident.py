# Copyright (c) 2026, Kelvin Njenga and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime

from onerc_compliance.onerc_incident_management.sla import policy as sla


class OnercIncident(Document):
	def validate(self):
		self._set_defaults()
		self._derive_priority()
		self._guard_resolution()
		if self.is_new():
			sla.stamp_targets(self)
		else:
			sla.handle_status_change(self)
		self._sync_response_and_resolution()

	def _set_defaults(self):
		if not self.status:
			self.status = "New"
		if not self.reported_by:
			self.reported_by = frappe.session.user
		if not self.date_reported:
			self.date_reported = now_datetime()
		for row in self.progress_updates:
			if not row.update_datetime:
				row.update_datetime = now_datetime()
			if not row.updated_by:
				row.updated_by = frappe.session.user

	def _derive_priority(self):
		"""Priority is NEVER typed: it is the Impact × Urgency cell of the matrix."""
		if self.impact and self.urgency:
			self.priority = frappe.db.get_value(
				"Onerc Priority Matrix",
				{"impact": self.impact, "urgency": self.urgency},
				"priority",
			)
		else:
			self.priority = None

	def _guard_resolution(self):
		if self.status == "Resolved" and not (self.resolution_category and self.resolution_summary):
			frappe.throw("Provide a resolution category and summary before resolving this incident.")

	def _sync_response_and_resolution(self):
		# First response is stamped the first time the incident leaves the New state.
		if self.status and self.status != "New" and not self.first_responded_on:
			self.first_responded_on = now_datetime()
		if self.status == "Resolved":
			if not self.resolved_on:
				self.resolved_on = now_datetime()
			if not self.resolution_datetime:
				self.resolution_datetime = now_datetime()
			if not self.resolved_by:
				self.resolved_by = frappe.session.user
			if self.sla_status != "Breached":
				self.sla_status = "Fulfilled"
