# Copyright (c) 2026, Kelvin Njenga and contributors
# For license information, please see license.txt
"""Rename the original ICT incident doctypes to the Onerc ITSM names.

Runs in pre_model_sync so the DocType records and their tables are renamed
(preserving existing rows) before the new onerc_incident / onerc_incident_activity
schema is synced from disk. Idempotent and safe on fresh sites.
"""
import frappe

RENAMES = (
	("ICT Incident Progress Update", "Onerc Incident Activity"),
	("ICT Incident Report", "Onerc Incident"),
)


def execute():
	for old, new in RENAMES:
		if frappe.db.exists("DocType", old) and not frappe.db.exists("DocType", new):
			frappe.rename_doc("DocType", old, new, force=True)
