// Copyright (c) 2026, Kelvin Njenga and contributors
// For license information, please see license.txt

function startRemoteSession(frm) {
	frappe.call({
		method: "onerc_compliance.onerc_incident_management.remote_support.start_session",
		args: { reference_doctype: frm.doctype, reference_name: frm.doc.name },
		freeze: true,
		freeze_message: __("Starting remote session…"),
		callback(r) {
			if (r.message) {
				frappe.show_alert({
					message: __("Remote session started: {0}", [r.message]),
					indicator: "green",
				});
			}
		},
	});
}

frappe.ui.form.on("Onerc Incident", {
	refresh(frm) {
		// Priority is derived from Impact × Urgency via the Priority Matrix.
		frm.set_df_property("priority", "read_only", 1);
		if (!frm.is_new()) {
			frm.add_custom_button(__("Start Remote Session"), () => startRemoteSession(frm), __("Actions"));
		}
	},
});
