# Copyright (c) 2026, Kelvin Njenga and contributors
# For license information, please see license.txt
"""ITSM setup hooks run after migrate."""
import frappe


def ensure_helpdesk_link_field():
	"""Add the reverse link (HD Ticket -> Onerc Incident) for bidirectional navigation.

	Created as a Custom Field so we don't fork the Helpdesk app. No-op when Helpdesk
	is absent or the field already exists.
	"""
	if "helpdesk" not in frappe.get_installed_apps():
		return
	if frappe.db.exists("Custom Field", "HD Ticket-onerc_incident"):
		return
	frappe.get_doc(
		{
			"doctype": "Custom Field",
			"dt": "HD Ticket",
			"fieldname": "onerc_incident",
			"label": "Onerc Incident",
			"fieldtype": "Link",
			"options": "Onerc Incident",
			"read_only": 1,
			"insert_after": "subject",
		}
	).insert(ignore_permissions=True)
