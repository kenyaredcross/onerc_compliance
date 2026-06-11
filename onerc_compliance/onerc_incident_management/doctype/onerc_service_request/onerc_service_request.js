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

frappe.ui.form.on("Onerc Service Request", {
	refresh(frm) {
		frm.set_df_property("priority", "read_only", 1);
		if (!frm.is_new()) {
			frm.add_custom_button(__("Start Remote Session"), () => startRemoteSession(frm), __("Actions"));
		}
	},

	catalogue_item(frm) {
		// Adaptive form: pre-fill defaults from the chosen catalogue item.
		if (!frm.doc.catalogue_item) return;
		frappe.db.get_doc("Onerc Request Catalogue Item", frm.doc.catalogue_item).then((item) => {
			frm.set_value("requires_ict_approval", item.requires_ict_approval);
			if (!frm.doc.affected_service && item.service) frm.set_value("affected_service", item.service);
			if (!frm.doc.impact && item.default_impact) frm.set_value("impact", item.default_impact);
			if (!frm.doc.urgency && item.default_urgency) frm.set_value("urgency", item.default_urgency);
			if (!frm.doc.support_team && item.default_support_team) {
				frm.set_value("support_team", item.default_support_team);
			}
		});
	},
});
