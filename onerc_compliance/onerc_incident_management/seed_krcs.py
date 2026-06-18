# Copyright (c) 2026, Kelvin Njenga and contributors
# For license information, please see license.txt
"""KRCS / Kenya configuration pack for the ITSM engine.

Everything here is **config data**, not engine code — impact/urgency/priority values,
the priority matrix, Kenyan holidays and working hours, services, teams, SLA targets,
and catalogue items. Run on demand:

    bench --site <site> execute onerc_compliance.onerc_incident_management.seed_krcs.seed

Idempotent: safe to re-run. (Branch regions are intentionally omitted — they live in
onerc_core's Geo Node, which is seeded separately once that app is installed.)
"""
import frappe

IMPACTS = [("High", 3), ("Medium", 2), ("Low", 1)]
URGENCIES = [("High", 3), ("Medium", 2), ("Low", 1)]
PRIORITIES = [("Critical", 4, "#e03131"), ("High", 3, "#f76707"), ("Medium", 2, "#f59f00"), ("Low", 1, "#37b24d")]

# (impact, urgency) -> priority  (standard ITIL 3x3)
MATRIX = {
	("High", "High"): "Critical",
	("High", "Medium"): "High",
	("High", "Low"): "Medium",
	("Medium", "High"): "High",
	("Medium", "Medium"): "Medium",
	("Medium", "Low"): "Low",
	("Low", "High"): "Medium",
	("Low", "Medium"): "Low",
	("Low", "Low"): "Low",
}

DATA_CLASSES = [("Public", 1), ("Internal", 2), ("Confidential", 3), ("Restricted", 4)]

CALENDAR = "KRCS Standard"
KENYA_HOLIDAYS_2026 = [
	("2026-01-01", "New Year's Day"),
	("2026-04-03", "Good Friday"),
	("2026-04-06", "Easter Monday"),
	("2026-05-01", "Labour Day"),
	("2026-06-01", "Madaraka Day"),
	("2026-10-10", "Utamaduni Day"),
	("2026-10-20", "Mashujaa Day"),
	("2026-12-12", "Jamhuri Day"),
	("2026-12-25", "Christmas Day"),
	("2026-12-26", "Boxing Day"),
]

CATEGORIES = ["Connectivity", "End-User Computing", "Applications", "Access Management"]
SERVICES = [
	("Email", "Applications"),
	("Internet / VPN", "Connectivity"),
	("Laptop / Desktop", "End-User Computing"),
	("Finance System", "Applications"),
	("Active Directory Account", "Access Management"),
]

TEAM = "ICT Helpdesk"
SLA_DEFAULT = "KRCS Default SLA"
SLA_CRITICAL = "KRCS Critical SLA"


def _ensure(doctype, name, payload):
	if frappe.db.exists(doctype, name):
		return name
	return frappe.get_doc({"doctype": doctype, **payload}).insert(ignore_permissions=True).name


def _seed_dimensions():
	for nm, w in IMPACTS:
		_ensure("Onerc Impact", nm, {"impact_name": nm, "weight": w})
	for nm, w in URGENCIES:
		_ensure("Onerc Urgency", nm, {"urgency_name": nm, "weight": w})
	for nm, w, color in PRIORITIES:
		_ensure("Onerc Priority", nm, {"priority_name": nm, "weight": w, "color": color})


def _seed_matrix():
	for (impact, urgency), priority in MATRIX.items():
		_ensure(
			"Onerc Priority Matrix",
			f"{impact}-{urgency}",
			{"impact": impact, "urgency": urgency, "priority": priority},
		)


def _seed_classifications():
	for nm, w in DATA_CLASSES:
		_ensure("Onerc Data Classification", nm, {"classification_name": nm, "weight": w})


def _seed_calendar():
	_ensure(
		"Onerc Business Calendar",
		CALENDAR,
		{
			"calendar_name": CALENDAR,
			"time_zone": "Africa/Nairobi",
			"work_monday": 1,
			"work_tuesday": 1,
			"work_wednesday": 1,
			"work_thursday": 1,
			"work_friday": 1,
			"work_saturday": 0,
			"work_sunday": 0,
			"business_start_time": "08:00:00",
			"business_end_time": "17:00:00",
			"holidays": [{"holiday_date": d, "holiday_name": n} for d, n in KENYA_HOLIDAYS_2026],
		},
	)


def _seed_services():
	for cat in CATEGORIES:
		_ensure("Onerc Service Category", cat, {"category_name": cat})
	for name, cat in SERVICES:
		_ensure("Onerc Service", name, {"service_name": name, "service_category": cat, "owner_team": TEAM})


def _seed_teams():
	_ensure(
		"Onerc Support Team",
		TEAM,
		{
			"team_name": TEAM,
			"team_email": "ict-helpdesk@redcross.or.ke",
			"members": [{"user": "Administrator", "team_role": "Lead"}],
		},
	)


def _seed_sla():
	_ensure(
		"Onerc SLA Policy",
		SLA_DEFAULT,
		{
			"policy_name": SLA_DEFAULT,
			"is_default": 1,
			"enabled": 1,
			"first_response_minutes": 60,
			"resolution_minutes": 480,
			"business_calendar": CALENDAR,
			"escalation_steps": [
				{"step_label": "Overdue reminder", "applies_to": "Resolution", "after_minutes": 360, "escalate_to_role": "ITSM Manager"},
			],
		},
	)
	_ensure(
		"Onerc SLA Policy",
		SLA_CRITICAL,
		{
			"policy_name": SLA_CRITICAL,
			"is_default": 0,
			"enabled": 1,
			"priority": "Critical",
			"first_response_minutes": 15,
			"resolution_minutes": 120,
			"business_calendar": CALENDAR,
			"escalation_steps": [
				{"step_label": "Manager escalation", "applies_to": "Both", "after_minutes": 60, "escalate_to_role": "ITSM Manager"},
			],
		},
	)


def _seed_catalogue():
	_ensure(
		"Onerc Request Catalogue Item",
		"New Laptop",
		{"item_name": "New Laptop", "service": "Laptop / Desktop", "default_impact": "Medium", "default_urgency": "Medium", "default_support_team": TEAM},
	)
	_ensure(
		"Onerc Request Catalogue Item",
		"Install Software",
		{"item_name": "Install Software", "service": "Laptop / Desktop", "default_impact": "Low", "default_urgency": "Medium", "default_support_team": TEAM, "requires_ict_approval": 1},
	)
	_ensure(
		"Onerc Request Catalogue Item",
		"Grant System Access",
		{"item_name": "Grant System Access", "service": "Active Directory Account", "default_impact": "Medium", "default_urgency": "High", "default_support_team": TEAM, "requires_ict_approval": 1, "spawns_access_request": 1},
	)


def _seed_settings():
	settings = frappe.get_single("Onerc Incidents Settings")
	settings.default_support_team = TEAM
	settings.default_sla_policy = SLA_DEFAULT
	settings.default_business_calendar = CALENDAR
	settings.sync_to_helpdesk = 1
	existing = {row.status for row in settings.pause_statuses}
	for status in ("Pending", "Pending HOD", "Pending ICT"):
		if status not in existing:
			settings.append("pause_statuses", {"status": status})
	settings.save(ignore_permissions=True)

	rss = frappe.get_single("Onerc Remote Support Settings")
	rss.consent_required = 1
	rss.default_timeout = 120
	rss.save(ignore_permissions=True)


def _seed_assignment_rule():
	name = "KRCS Incident Routing"
	if frappe.db.exists("Assignment Rule", name):
		return
	members = frappe.get_all("Onerc Support Team Member", filters={"parent": TEAM}, pluck="user")
	frappe.get_doc(
		{
			"doctype": "Assignment Rule",
			"name": name,
			"document_type": "Onerc Incident",
			"priority": 0,
			"disabled": 0,
			"description": "Route open incidents to ICT Helpdesk members (round robin).",
			"assign_condition": "status in ('New', 'Assigned')",
			"unassign_condition": "status in ('Resolved', 'Closed', 'Cancelled')",
			"rule": "Round Robin",
			"users": [{"user": u} for u in members] or [{"user": "Administrator"}],
			"assignment_days": [{"day": d} for d in ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday")],
		}
	).insert(ignore_permissions=True)


def seed():
	_seed_dimensions()
	_seed_matrix()
	_seed_classifications()
	_seed_calendar()
	_seed_teams()
	_seed_services()
	_seed_sla()
	_seed_catalogue()
	_seed_settings()
	_seed_assignment_rule()
	frappe.db.commit()
	return "KRCS ITSM configuration seeded."
