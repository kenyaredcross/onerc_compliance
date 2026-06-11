# Copyright (c) 2026, Kelvin Njenga and contributors
# For license information, please see license.txt
"""Helpdesk sync — the Onerc Incident is the source of truth.

On insert an Incident pushes a linked Frappe Helpdesk ``HD Ticket``; on resolution
the ticket is closed. Controlled by the ``sync_to_helpdesk`` flag in Onerc Incidents
Settings and guarded so a missing/misconfigured Helpdesk never breaks the Incident.

PDF closure documents are deferred (onerc_storage not available in this bench).
"""
import frappe


def _enabled():
	if not frappe.db.get_single_value("Onerc Incidents Settings", "sync_to_helpdesk"):
		return False
	return "helpdesk" in frappe.get_installed_apps()


def create_helpdesk_ticket(doc, method=None):
	if not _enabled() or doc.helpdesk_ticket:
		return
	try:
		ticket = frappe.new_doc("HD Ticket")
		ticket.subject = f"{doc.name}: {doc.title}"
		ticket.description = doc.description or doc.title
		if doc.reported_by:
			ticket.raised_by = frappe.db.get_value("User", doc.reported_by, "email") or doc.reported_by
		priority = _map_priority(doc.priority)
		if priority:
			ticket.priority = priority
		if frappe.db.has_column("HD Ticket", "onerc_incident"):
			ticket.onerc_incident = doc.name
		ticket.insert(ignore_permissions=True)
		# update_modified=False so we don't bump the incident's timestamp under the user
		# (or a subsequent save), which would trigger a TimestampMismatchError.
		doc.db_set("helpdesk_ticket", ticket.name, update_modified=False)
	except Exception:
		frappe.log_error(title="Onerc → Helpdesk ticket creation failed")


def sync_helpdesk_on_resolve(doc, method=None):
	if not _enabled() or not doc.helpdesk_ticket:
		return
	if doc.status not in ("Resolved", "Closed"):
		return
	try:
		closed = _closed_status()
		if closed:
			frappe.db.set_value("HD Ticket", doc.helpdesk_ticket, "status", closed)
		# TODO(onerc_storage): generate and attach a PDF closure document here.
	except Exception:
		frappe.log_error(title="Onerc → Helpdesk close failed")


def _map_priority(priority):
	if priority and frappe.db.exists("HD Ticket Priority", priority):
		return priority
	return None


def _closed_status():
	if frappe.db.exists("DocType", "HD Ticket Status"):
		for status in ("Closed", "Resolved"):
			if frappe.db.exists("HD Ticket Status", status):
				return status
	return "Closed"
