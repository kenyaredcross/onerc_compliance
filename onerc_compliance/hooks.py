app_name = "onerc_compliance"
app_title = "Onerc Compliance"
app_publisher = "Kelvin Njenga"
app_description = "OneRC Compliance"
app_email = "njengasheba@gmail.com"
app_license = "mit"

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
