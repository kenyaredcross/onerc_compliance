# Copyright (c) 2026, Kelvin Njenga and contributors
# For license information, please see license.txt
"""Whitelisted API for the /ict-help self-service portal.

These run as the logged-in user. Records are created/read on the user's behalf with
ignore_permissions, always scoped to ``frappe.session.user`` (reported_by /
requested_by), so a portal user never needs desk permissions on the ITSM doctypes.
"""
import frappe
from frappe import _


def _require_login():
	if frappe.session.user == "Guest":
		frappe.throw(_("Please sign in to use the ICT Help portal."), frappe.PermissionError)


@frappe.whitelist()
def get_context():
	_require_login()
	user = frappe.session.user
	return {"user": user, "full_name": frappe.utils.get_fullname(user)}


@frappe.whitelist()
def get_catalogue():
	"""Active catalogue items grouped by service category."""
	_require_login()
	items = frappe.get_all(
		"Onerc Request Catalogue Item",
		filters={"is_active": 1},
		fields=[
			"name",
			"item_name",
			"description",
			"service",
			"service_category",
			"requires_ict_approval",
			"spawns_access_request",
		],
		order_by="item_name asc",
		ignore_permissions=True,
	)
	groups = {}
	for item in items:
		category = item.get("service_category")
		if not category and item.get("service"):
			category = frappe.db.get_value("Onerc Service", item["service"], "service_category")
		groups.setdefault(category or "General", []).append(item)
	return [{"category": cat, "items": its} for cat, its in sorted(groups.items())]


@frappe.whitelist()
def get_urgency_options():
	_require_login()
	return frappe.get_all(
		"Onerc Urgency", fields=["name", "urgency_name"], order_by="weight desc", ignore_permissions=True
	)


@frappe.whitelist(methods=["POST"])
def submit_service_request(catalogue_item, subject=None, description=None):
	_require_login()
	if not frappe.db.exists("Onerc Request Catalogue Item", catalogue_item):
		frappe.throw(_("Unknown catalogue item."))
	item = frappe.get_cached_doc("Onerc Request Catalogue Item", catalogue_item)
	doc = frappe.get_doc(
		{
			"doctype": "Onerc Service Request",
			"catalogue_item": catalogue_item,
			"subject": (subject or "").strip() or item.item_name,
			"description": description,
			"requested_by": frappe.session.user,
			"requested_for": frappe.session.user,
		}
	).insert(ignore_permissions=True)
	return {"name": doc.name, "subject": doc.subject, "status": doc.status, "type": "Service Request"}


@frappe.whitelist(methods=["POST"])
def submit_incident(title, description=None, urgency="Medium"):
	_require_login()
	impact = "Medium" if frappe.db.exists("Onerc Impact", "Medium") else _first("Onerc Impact")
	if not frappe.db.exists("Onerc Urgency", urgency):
		urgency = _first("Onerc Urgency")
	doc = frappe.get_doc(
		{
			"doctype": "Onerc Incident",
			"title": title,
			"description": description,
			"impact": impact,
			"urgency": urgency,
			"channel": "Portal",
			"reported_by": frappe.session.user,
		}
	).insert(ignore_permissions=True)
	return {"name": doc.name, "subject": doc.title, "status": doc.status, "priority": doc.priority, "type": "Incident"}


@frappe.whitelist()
def get_my_tickets():
	"""The user's incidents and service requests, newest first."""
	_require_login()
	user = frappe.session.user
	tickets = []
	for inc in frappe.get_all(
		"Onerc Incident",
		filters={"reported_by": user},
		fields=["name", "title", "status", "priority", "creation", "sla_status"],
		order_by="creation desc",
		limit=50,
		ignore_permissions=True,
	):
		tickets.append({**inc, "subject": inc.pop("title"), "type": "Incident"})
	for req in frappe.get_all(
		"Onerc Service Request",
		filters={"requested_by": user},
		fields=["name", "subject", "status", "priority", "creation", "sla_status"],
		order_by="creation desc",
		limit=50,
		ignore_permissions=True,
	):
		tickets.append({**req, "type": "Service Request"})
	tickets.sort(key=lambda t: t["creation"], reverse=True)
	return tickets


def _first(doctype):
	names = frappe.get_all(doctype, pluck="name", limit=1, ignore_permissions=True)
	return names[0] if names else None
