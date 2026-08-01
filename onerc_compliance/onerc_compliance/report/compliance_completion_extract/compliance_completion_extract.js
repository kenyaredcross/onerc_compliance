// Copyright (c) 2026, Kelvin Njenga and contributors
// For license information, please see license.txt

frappe.query_reports["Compliance Completion Extract"] = {
	filters: [
		{
			fieldname: "requirement",
			label: __("Requirement"),
			fieldtype: "Link",
			options: "Compliance Requirement",
		},
		{
			// Matches the dashboard's "Staff only / All" toggle and its default.
			fieldname: "staff_scope",
			label: __("Staff Scope"),
			fieldtype: "Select",
			options: "Staff\nAll",
			default: "Staff",
			reqd: 1,
		},
	],
};
