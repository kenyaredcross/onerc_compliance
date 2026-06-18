# Copyright (c) 2026, Kelvin Njenga and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime

from onerc_compliance.onerc_incident_management.sla import policy as sla


class OnercServiceRequest(Document):
	def validate(self):
		self._set_defaults()
		self._prefill_from_catalogue()
		self._derive_priority()
		self._enforce_approval_gate()
		if self.is_new():
			sla.stamp_targets(self)
		else:
			sla.handle_status_change(self)
		self._sync_lifecycle()

	def on_update(self):
		self._maybe_spawn_access_request()

	def _set_defaults(self):
		if not self.status:
			self.status = "Draft"
		if not self.requested_by:
			self.requested_by = frappe.session.user
		if not self.date_requested:
			self.date_requested = now_datetime()
		for row in self.approvals:
			if row.status in ("Approved", "Rejected"):
				if not row.decided_on:
					row.decided_on = now_datetime()
				if not row.approver:
					row.approver = frappe.session.user

	def _prefill_from_catalogue(self):
		if not self.catalogue_item:
			return
		item = frappe.get_cached_doc("Onerc Request Catalogue Item", self.catalogue_item)
		# requires_ict_approval is authoritative from the catalogue (read-only on the form).
		self.requires_ict_approval = item.requires_ict_approval
		if not self.affected_service:
			self.affected_service = item.service
		if not self.impact:
			self.impact = item.default_impact
		if not self.urgency:
			self.urgency = item.default_urgency
		if not self.support_team:
			self.support_team = item.default_support_team

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

	def _has_approved(self, stage):
		return any(row.approval_stage == stage and row.status == "Approved" for row in self.approvals)

	def _enforce_approval_gate(self):
		"""HOD approval is always required to reach Approved; ICT approval is additionally
		required when the catalogue item is governed by AUP 10.3."""
		if self.status != "Approved":
			return
		if not self._has_approved("HOD"):
			frappe.throw("HOD approval is required before this request can be Approved.")
		if self.requires_ict_approval and not self._has_approved("ICT"):
			frappe.throw("ICT approval is required (AUP 10.3) before this request can be Approved.")

	def _sync_lifecycle(self):
		if self.status and self.status != "Draft" and not self.first_responded_on:
			self.first_responded_on = now_datetime()
		if self.status in ("Fulfilled", "Closed"):
			if not self.resolved_on:
				self.resolved_on = now_datetime()
			if not self.fulfilled_on:
				self.fulfilled_on = now_datetime()
			if not self.fulfilled_by:
				self.fulfilled_by = frappe.session.user
			if self.sla_status != "Breached":
				self.sla_status = "Fulfilled"

	def _maybe_spawn_access_request(self):
		if self.status != "Approved" or self.access_provisioning_pending:
			return
		if not frappe.db.get_value(
			"Onerc Request Catalogue Item", self.catalogue_item, "spawns_access_request"
		):
			return
		# TODO(access-grant-registry): create an Onerc Access Grant record here once the
		# registry ships. For now, flag the request and raise a provisioning ToDo for ICT.
		self.db_set("access_provisioning_pending", 1)
		self.add_comment(
			"Comment",
			"Access provisioning required — an Access Grant will be created when the registry ships (deferred).",
		)
		assignee = self._ict_assignee()
		if assignee:
			frappe.get_doc(
				{
					"doctype": "ToDo",
					"allocated_to": assignee,
					"reference_type": self.doctype,
					"reference_name": self.name,
					"description": f"Provision access for Service Request {self.name}: {self.subject}",
				}
			).insert(ignore_permissions=True)

	def _ict_assignee(self):
		team = self.support_team or frappe.db.get_single_value(
			"Onerc Incidents Settings", "default_support_team"
		)
		if team:
			return frappe.db.get_value(
				"Onerc Support Team Member", {"parent": team, "team_role": "Lead"}, "user"
			)
		return None
