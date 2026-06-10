// Copyright (c) 2026, Kelvin Njenga and contributors
// For license information, please see license.txt

frappe.ui.form.on("ICT Incident Report", {
	refresh(frm) {
		if (!frm.is_new()) {
			frm.add_custom_button(__("View Staff Dashboard"), () => {
				window.open("/ict_status", "_blank");
			});
		}
	},
});
