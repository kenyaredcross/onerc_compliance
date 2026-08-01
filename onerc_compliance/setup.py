# Copyright (c) 2026, Kelvin Njenga and contributors
# For license information, please see license.txt

"""Custom fields the compliance dashboard reports on.

`Compliance Submission` already denormalizes `employee_name`, `department` and
`designation` from the Employee at creation time (see
`onerc_compliance.utils.ensure_submission`). These two columns extend that same
snapshot so the dashboard and the completion extract can group and filter
without joining back to Employee on every read:

* `hr_departments` — the raw Business Central HRDepartments code, stored
  verbatim. This is the value the dashboard groups by; `department` remains a
  Link to the ERPNext Department tree and is left untouched.
* `staff_type` — "Staff" / "Other", so the dashboard can default to staff-only.

Both are populated by the roster sync in `krcs_onesource`. When that app is not
installed the columns simply stay empty and everything still works.
"""

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

CUSTOM_FIELDS = {
	"Compliance Submission": [
		{
			"fieldname": "hr_departments",
			"label": "HRDepartments",
			"fieldtype": "Data",
			"insert_after": "department",
			"read_only": 1,
			"in_standard_filter": 1,
			"description": (
				"Raw HRDepartments code snapshotted from the Employee when the "
				"submission was created."
			),
		},
		{
			"fieldname": "staff_type",
			"label": "Staff Type",
			"fieldtype": "Select",
			"options": "\nStaff\nOther",
			"insert_after": "hr_departments",
			"read_only": 1,
			"description": "Snapshotted from the Employee: 'Staff' or 'Other'.",
		},
	]
}


def ensure_compliance_custom_fields():
	"""Install/refresh the reporting custom fields. Idempotent."""
	create_custom_fields(CUSTOM_FIELDS, update=True)
	frappe.db.commit()
