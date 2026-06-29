# Copyright (c) 2026, Kelvin Njenga and contributors
# For license information, please see license.txt
"""Backfill: link certificates uploaded before the attachment-inheritance fix.

Staff certificates are uploaded as standalone private Files and were never
linked to their Compliance Submission, so only the uploader and System Manager
could open them — reviewers (e.g. the Compliance Officer) got a permission
error. This walks every existing Compliance Submission and links each Attach
value's File to its submission, restoring reviewer read access through
attachment inheritance.

Idempotent: re-linking an already-linked file is a no-op, and submissions with
no attachments are skipped.
"""
import frappe

from onerc_compliance.utils import link_file_to_submission


def execute():
	submissions = frappe.get_all("Compliance Submission", pluck="name")
	for sub_name in submissions:
		rows = frappe.get_all(
			"Compliance Submission Value",
			filters={
				"parent": sub_name,
				"parenttype": "Compliance Submission",
				"field_type": "Attach",
			},
			fields=["attachment", "field_name"],
		)
		for row in rows:
			if row.attachment:
				link_file_to_submission(row.attachment, sub_name, row.field_name)
		frappe.db.commit()
