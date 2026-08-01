# Copyright (c) 2026, Kelvin Njenga and contributors
# For license information, please see license.txt

"""Compliance completion grouped by HRDepartments.

Reports the same numbers as the dashboard's department breakdown, in an
exportable form: one row per Business Central HRDepartments code, with the
submission counts by status and the reviewed-completion percentage.

The grouping dimension is `Compliance Submission.hr_departments` — the raw BC
code snapshotted from the Employee — matching
`onerc_compliance.api.v1.compliance.get_dashboard`. Like the dashboard, it
defaults to staff only.
"""

import frappe
from frappe import _

from onerc_compliance.api.v1.compliance import (
	DEPARTMENT_FIELD,
	UNASSIGNED,
	normalize_staff_scope,
)

#: Statuses that get their own column, in the order the dashboard uses.
STATUS_COLUMNS = [
	"Reviewed",
	"Submitted",
	"Pending",
	"Needs More Info",
	"Overdue",
	"Rejected",
	"Exempted",
]


def execute(filters=None):
	filters = filters or {}

	requirement = filters.get("requirement")
	staff_scope = normalize_staff_scope(filters.get("staff_scope"))

	query_filters = []
	if requirement:
		query_filters.append(["requirement", "=", requirement])
	if staff_scope == "Staff":
		query_filters.append(["staff_type", "=", "Staff"])

	rows = frappe.get_all(
		"Compliance Submission",
		filters=query_filters,
		fields=["name", "status", DEPARTMENT_FIELD],
	)

	buckets = {}
	for row in rows:
		department = row.get(DEPARTMENT_FIELD) or UNASSIGNED
		bucket = buckets.get(department)
		if bucket is None:
			bucket = {"total": 0}
			for status in STATUS_COLUMNS:
				bucket[frappe.scrub(status)] = 0
			buckets[department] = bucket

		bucket["total"] += 1
		key = frappe.scrub(row.status or "")
		if key in bucket:
			bucket[key] += 1

	# Real departments sorted, "Unassigned" last — same ordering as the dashboard.
	ordered = sorted(key for key in buckets if key != UNASSIGNED)
	if UNASSIGNED in buckets:
		ordered.append(UNASSIGNED)

	data = []
	for department in ordered:
		bucket = buckets[department]
		total = bucket["total"]
		reviewed = bucket[frappe.scrub("Reviewed")]
		data.append({
			"hr_departments": department,
			"total": total,
			"completion_percent": (reviewed / total * 100) if total else 0,
			**{frappe.scrub(status): bucket[frappe.scrub(status)] for status in STATUS_COLUMNS},
		})

	return _columns(), data


def _columns():
	columns = [
		{
			"label": _("HRDepartments"),
			"fieldname": "hr_departments",
			"fieldtype": "Data",
			"width": 220,
		},
		{"label": _("Total"), "fieldname": "total", "fieldtype": "Int", "width": 90},
	]
	for status in STATUS_COLUMNS:
		columns.append({
			"label": _(status),
			"fieldname": frappe.scrub(status),
			"fieldtype": "Int",
			"width": 120,
		})
	columns.append({
		"label": _("Completion %"),
		"fieldname": "completion_percent",
		"fieldtype": "Percent",
		"width": 130,
	})
	return columns
