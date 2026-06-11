app_name = "onerc_compliance"
app_title = "Onerc Compliance"
app_publisher = "Kelvin Njenga"
app_description = "OneRC Compliance"
app_email = "njengasheba@gmail.com"
app_license = "mit"

# SPA routing — redirect all /compliance/* sub-paths back to the index page
website_route_rules = [
	{"from_route": "/compliance/<path:app_path>", "to_route": "compliance"},
	{"from_route": "/ict-help/<path:app_path>", "to_route": "ict_help"},
	{"from_route": "/ict-help", "to_route": "ict_help"},
]

scheduler_events = {
	"daily": [
		"onerc_compliance.tasks.close_expired_requirements",
		"onerc_compliance.tasks.send_compliance_reminders",
	],
	"cron": {
		# ITSM SLA breach + escalation scan (every 10 minutes)
		"*/10 * * * *": [
			"onerc_compliance.onerc_incident_management.sla.escalation.scan_sla",
		],
	},
}

permission_query_conditions = {
	"Compliance Submission": "onerc_compliance.permissions.submission_query_conditions",
}

has_permission = {
	"Compliance Submission": "onerc_compliance.permissions.has_submission_permission",
}

doc_events = {
	"Onerc Incident": {
		"after_insert": "onerc_compliance.onerc_incident_management.helpdesk_sync.create_helpdesk_ticket",
		"on_update": "onerc_compliance.onerc_incident_management.helpdesk_sync.sync_helpdesk_on_resolve",
	},
}

after_install = "onerc_compliance.onerc_incident_management.install.setup_itsm"

after_migrate = [
	"onerc_compliance.onerc_incident_management.setup.ensure_helpdesk_link_field",
]

fixtures = [
	{
		"doctype": "Role",
		"filters": {"name": "Compliance Officer"},
	}
]
