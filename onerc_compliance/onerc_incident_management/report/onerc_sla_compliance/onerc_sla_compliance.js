// Copyright (c) 2026, Kelvin Njenga and contributors
// For license information, please see license.txt

frappe.query_reports["Onerc SLA Compliance"] = {
	filters: [
		{
			fieldname: "group_by",
			label: __("Group By"),
			fieldtype: "Select",
			options: "priority\nsupport_team\naffected_service\nbranch_region",
			default: "priority",
		},
	],
};
