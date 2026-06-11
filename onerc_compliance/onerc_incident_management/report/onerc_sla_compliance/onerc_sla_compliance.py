# Copyright (c) 2026, Kelvin Njenga and contributors
# For license information, please see license.txt
"""SLA compliance: % first-response and resolution targets met, grouped by
priority, support team, service or branch."""
import frappe

GROUPABLE = {"priority", "support_team", "affected_service", "branch_region"}


def execute(filters=None):
	filters = filters or {}
	group_field = filters.get("group_by") or "priority"
	if group_field not in GROUPABLE:
		group_field = "priority"

	rows = frappe.get_all(
		"Onerc Incident",
		filters={"sla_policy": ["is", "set"]},
		fields=[
			group_field,
			"first_response_due",
			"first_responded_on",
			"response_breached",
			"resolution_due",
			"resolved_on",
			"resolution_breached",
		],
	)

	buckets = {}
	for r in rows:
		bucket = buckets.setdefault(
			r.get(group_field) or "(none)",
			{"total": 0, "resp_total": 0, "resp_met": 0, "res_total": 0, "res_met": 0},
		)
		bucket["total"] += 1
		if r.first_response_due:
			bucket["resp_total"] += 1
			if r.first_responded_on and not r.response_breached:
				bucket["resp_met"] += 1
		if r.resolution_due:
			bucket["res_total"] += 1
			if r.resolved_on and not r.resolution_breached:
				bucket["res_met"] += 1

	columns = [
		{
			"label": group_field.replace("_", " ").title(),
			"fieldname": group_field,
			"fieldtype": "Data",
			"width": 200,
		},
		{"label": "Total", "fieldname": "total", "fieldtype": "Int", "width": 90},
		{"label": "Response Met %", "fieldname": "response_pct", "fieldtype": "Percent", "width": 140},
		{"label": "Resolution Met %", "fieldname": "resolution_pct", "fieldtype": "Percent", "width": 150},
	]
	data = [
		{
			group_field: key,
			"total": b["total"],
			"response_pct": (b["resp_met"] / b["resp_total"] * 100) if b["resp_total"] else 0,
			"resolution_pct": (b["res_met"] / b["res_total"] * 100) if b["res_total"] else 0,
		}
		for key, b in sorted(buckets.items())
	]
	return columns, data
