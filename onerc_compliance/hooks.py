app_name = "onerc_compliance"
app_title = "Onerc Compliance"
app_publisher = "Kelvin Njenga"
app_description = "OneRC Compliance"
app_email = "njengasheba@gmail.com"
app_license = "mit"

# SPA routing — redirect all /compliance/* sub-paths back to the index page
website_route_rules = [
	{"from_route": "/compliance/<path:app_path>", "to_route": "compliance"},
]

scheduler_events = {
	"daily": [
		"onerc_compliance.tasks.close_expired_requirements",
		"onerc_compliance.tasks.send_compliance_reminders",
	]
}

permission_query_conditions = {
	"Compliance Submission": "onerc_compliance.permissions.submission_query_conditions",
}

has_permission = {
	"Compliance Submission": "onerc_compliance.permissions.has_submission_permission",
}

fixtures = [
	{
		"doctype": "Role",
		"filters": {"name": "Compliance Officer"},
	}
]
