# Copyright (c) 2026, Kelvin Njenga and contributors
# For license information, please see license.txt
"""Idempotent ITSM engine setup: roles, role profiles, workflows and notifications.

Org-neutral (no KRCS/Kenya values). Runs on install (hooks.after_install) or on demand:
``bench execute onerc_compliance.onerc_incident_management.install.setup_itsm``.
KRCS-specific config is seeded separately — see seed_krcs.py.
"""
import json

import frappe

ITSM_ROLES = ("ITSM Agent", "ITSM Manager", "HOD", "ICT Approver", "Branch User")

ROLE_PROFILES = {
	"ITSM Agent Profile": ["ITSM Agent", "Branch User"],
	"ITSM Manager Profile": ["ITSM Manager", "ITSM Agent"],
	"ITSM Approver Profile": ["HOD", "ICT Approver"],
}

NOTIFICATIONS = [
	{
		"document_type": "Onerc Incident",
		"event": "Value Change",
		"value_changed": "assigned_to",
		"condition": "doc.assigned_to",
		"subject": "Incident {{ doc.name }} assigned to you",
		"message": "Incident {{ doc.name }} — {{ doc.title }} — has been assigned to you.",
		"field": "assigned_to",
	},
	{
		"document_type": "Onerc Incident",
		"event": "Value Change",
		"value_changed": "status",
		"condition": "doc.status == 'Resolved'",
		"subject": "Your incident {{ doc.name }} has been resolved",
		"message": "Incident {{ doc.name }} has been resolved.<br>Summary: {{ doc.resolution_summary }}",
		"field": "reported_by",
	},
]

# (state, style, allow_edit role)
INCIDENT_WORKFLOW = "Onerc Incident Workflow"
INCIDENT_STATES = [
	("New", "Primary", "ITSM Agent"),
	("Assigned", "Info", "ITSM Agent"),
	("In Progress", "Info", "ITSM Agent"),
	("Pending", "Warning", "ITSM Agent"),
	("Resolved", "Success", "ITSM Agent"),
	("Closed", "Success", "ITSM Manager"),
	("Cancelled", "Danger", "ITSM Manager"),
]
# (state, action, next_state, allowed role, condition)
INCIDENT_TRANSITIONS = [
	("New", "Assign", "Assigned", "ITSM Agent", None),
	("Assigned", "Start Work", "In Progress", "ITSM Agent", None),
	("In Progress", "Put On Hold", "Pending", "ITSM Agent", None),
	("Pending", "Resume", "In Progress", "ITSM Agent", None),
	("In Progress", "Resolve", "Resolved", "ITSM Agent", None),
	("Resolved", "Close", "Closed", "ITSM Manager", None),
	("Resolved", "Reopen", "In Progress", "ITSM Agent", None),
	("New", "Cancel", "Cancelled", "ITSM Manager", None),
	("Assigned", "Cancel", "Cancelled", "ITSM Manager", None),
	("In Progress", "Cancel", "Cancelled", "ITSM Manager", None),
	("Pending", "Cancel", "Cancelled", "ITSM Manager", None),
]

SR_WORKFLOW = "Onerc Service Request Workflow"
SR_STATES = [
	("Draft", "Primary", "ITSM Agent"),
	("Pending HOD", "Warning", "HOD"),
	("Pending ICT", "Warning", "ICT Approver"),
	("Approved", "Info", "ITSM Manager"),
	("In Fulfilment", "Info", "ITSM Agent"),
	("Fulfilled", "Success", "ITSM Agent"),
	("Closed", "Success", "ITSM Manager"),
	("Rejected", "Danger", "ITSM Manager"),
	("Cancelled", "Danger", "ITSM Manager"),
]
SR_TRANSITIONS = [
	("Draft", "Submit for Approval", "Pending HOD", "ITSM Agent", None),
	("Pending HOD", "HOD Approve", "Pending ICT", "HOD", "doc.requires_ict_approval"),
	("Pending HOD", "HOD Approve and Finalise", "Approved", "HOD", "not doc.requires_ict_approval"),
	("Pending HOD", "Reject", "Rejected", "HOD", None),
	("Pending ICT", "ICT Approve", "Approved", "ICT Approver", None),
	("Pending ICT", "Reject", "Rejected", "ICT Approver", None),
	("Approved", "Start Fulfilment", "In Fulfilment", "ITSM Agent", None),
	("In Fulfilment", "Fulfil", "Fulfilled", "ITSM Agent", None),
	("Fulfilled", "Close", "Closed", "ITSM Manager", None),
	("Draft", "Cancel", "Cancelled", "ITSM Agent", None),
	("Pending HOD", "Cancel", "Cancelled", "ITSM Manager", None),
	("Pending ICT", "Cancel", "Cancelled", "ITSM Manager", None),
]


def ensure_roles():
	for role in ITSM_ROLES:
		if not frappe.db.exists("Role", role):
			frappe.get_doc({"doctype": "Role", "role_name": role, "desk_access": 1}).insert(
				ignore_permissions=True
			)


def ensure_role_profiles():
	for name, roles in ROLE_PROFILES.items():
		if frappe.db.exists("Role Profile", name):
			continue
		frappe.get_doc(
			{"doctype": "Role Profile", "role_profile": name, "roles": [{"role": r} for r in roles]}
		).insert(ignore_permissions=True)


def ensure_notifications():
	for spec in NOTIFICATIONS:
		if frappe.db.exists("Notification", {"subject": spec["subject"]}):
			continue
		frappe.get_doc(
			{
				"doctype": "Notification",
				"subject": spec["subject"],
				"document_type": spec["document_type"],
				"event": spec["event"],
				"value_changed": spec["value_changed"],
				"condition": spec["condition"],
				"channel": "Email",
				"enabled": 1,
				"is_standard": 0,
				"message": spec["message"],
				"recipients": [{"receiver_by_document_field": spec["field"]}],
			}
		).insert(ignore_permissions=True)


def _ensure_workflow_states(states):
	for name, style, _role in states:
		if not frappe.db.exists("Workflow State", name):
			frappe.get_doc(
				{"doctype": "Workflow State", "workflow_state_name": name, "style": style}
			).insert(ignore_permissions=True)


def _ensure_workflow_actions(transitions):
	for action in {t[1] for t in transitions}:
		if not frappe.db.exists("Workflow Action Master", action):
			frappe.get_doc(
				{"doctype": "Workflow Action Master", "workflow_action_name": action}
			).insert(ignore_permissions=True)


def _ensure_workflow(name, document_type, states, transitions):
	_ensure_workflow_states(states)
	_ensure_workflow_actions(transitions)
	if frappe.db.exists("Workflow", name):
		return
	frappe.get_doc(
		{
			"doctype": "Workflow",
			"workflow_name": name,
			"document_type": document_type,
			"workflow_state_field": "status",
			"is_active": 1,
			"send_email_alert": 0,
			"states": [
				{"state": s, "doc_status": "0", "allow_edit": role} for s, _style, role in states
			],
			"transitions": [
				{
					"state": s,
					"action": a,
					"next_state": n,
					"allowed": allowed,
					"allow_self_approval": 1,
					**({"condition": cond} if cond else {}),
				}
				for s, a, n, allowed, cond in transitions
			],
		}
	).insert(ignore_permissions=True)


def ensure_workflows():
	_ensure_workflow(INCIDENT_WORKFLOW, "Onerc Incident", INCIDENT_STATES, INCIDENT_TRANSITIONS)
	_ensure_workflow(SR_WORKFLOW, "Onerc Service Request", SR_STATES, SR_TRANSITIONS)


WORKSPACE = "ITSM"
WS_SHORTCUTS = [
	("Incidents", "DocType", "Onerc Incident", "Red"),
	("Service Requests", "DocType", "Onerc Service Request", "Blue"),
	("Remote Sessions", "DocType", "Onerc Remote Support Session", "Green"),
	("SLA Compliance", "Report", "Onerc SLA Compliance", "Orange"),
]
WS_CARDS = [
	("Operations", ["Onerc Incident", "Onerc Service Request", "Onerc Remote Support Session", "Onerc Configuration Item"]),
	("Catalogue & Services", ["Onerc Request Catalogue Item", "Onerc Service", "Onerc Service Category"]),
	("SLA & Priority", ["Onerc SLA Policy", "Onerc Priority Matrix", "Onerc Business Calendar", "Onerc Impact", "Onerc Urgency", "Onerc Priority"]),
	("Configuration", ["Onerc Incidents Settings", "Onerc Support Team", "Onerc Data Classification", "Onerc Remote Support Settings"]),
]


def ensure_workspace():
	if frappe.db.exists("Workspace", WORKSPACE):
		return
	content = [{"type": "header", "data": {"text": "Onerc ITSM", "col": 12}}]
	for label, *_rest in WS_SHORTCUTS:
		content.append({"type": "shortcut", "data": {"shortcut_name": label, "col": 3}})
	content.append({"type": "spacer", "data": {"col": 12}})
	for card_name, _items in WS_CARDS:
		content.append({"type": "card", "data": {"card_name": card_name, "col": 4}})
	shortcuts = [
		{
			"type": typ,
			"link_to": link,
			"label": label,
			"color": color,
			"doc_view": "List" if typ == "DocType" else "",
		}
		for label, typ, link, color in WS_SHORTCUTS
	]
	links = []
	for card_name, items in WS_CARDS:
		links.append({"type": "Card Break", "label": card_name})
		for dt in items:
			links.append({"type": "Link", "link_type": "DocType", "link_to": dt, "label": dt.replace("Onerc ", "")})
	frappe.get_doc(
		{
			"doctype": "Workspace",
			"title": WORKSPACE,
			"label": WORKSPACE,
			"module": "Onerc Incident Management",
			"public": 1,
			"icon": "tool",
			"content": json.dumps(content),
			"shortcuts": shortcuts,
			"links": links,
		}
	).insert(ignore_permissions=True)


def setup_itsm():
	"""Idempotent engine setup: roles, role profiles, notifications, workflows, workspace."""
	ensure_roles()
	ensure_role_profiles()
	ensure_notifications()
	ensure_workflows()
	ensure_workspace()
	frappe.db.commit()
