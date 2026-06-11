# Copyright (c) 2026, Kelvin Njenga and contributors
# For license information, please see license.txt
"""SLA policy resolution, target stamping and pause/resume.

These helpers operate on any document that carries the SLA field block
(sla_policy, first_response_due, resolution_due, first_responded_on,
resolved_on, on_hold_since, total_hold_minutes, response_breached,
resolution_breached, sla_status) together with the common fields priority,
affected_service and support_team. Onerc Incident and Onerc Service Request
both call into these from their controllers, so the logic lives here once.
"""
import frappe
from frappe.utils import flt, get_datetime, now_datetime

from onerc_compliance.onerc_incident_management.sla.working_time import (
	add_working_minutes,
	get_working_calendar,
	working_minutes_between,
)

_MATCH_FIELDS = ("priority", "service", "service_category", "support_team")


def _service_category_of(doc):
	if doc.get("service_category"):
		return doc.get("service_category")
	if doc.get("affected_service"):
		return frappe.db.get_value("Onerc Service", doc.get("affected_service"), "service_category")
	return None


def _doc_criteria(doc):
	return {
		"priority": doc.get("priority"),
		"service": doc.get("affected_service"),
		"service_category": _service_category_of(doc),
		"support_team": doc.get("support_team"),
	}


def resolve_policy(doc):
	"""Return the name of the most specific enabled SLA Policy for ``doc``.

	Every non-blank criterion on a policy must match the document; among the
	matching policies the one constraining the most criteria wins. Falls back to
	the flagged default policy, then to the default in Onerc Incidents Settings.
	"""
	policies = frappe.get_all(
		"Onerc SLA Policy",
		filters={"enabled": 1},
		fields=["name", "is_default", *_MATCH_FIELDS],
	)
	criteria = _doc_criteria(doc)
	best, best_score = None, -1
	for policy in policies:
		score, matches = 0, True
		for field in _MATCH_FIELDS:
			constraint = policy.get(field)
			if constraint:
				if constraint == criteria.get(field):
					score += 1
				else:
					matches = False
					break
		if matches and score > best_score:
			best, best_score = policy.name, score
	if best:
		return best
	default = next((p.name for p in policies if p.is_default), None)
	return default or frappe.db.get_single_value("Onerc Incidents Settings", "default_sla_policy")


def _calendar_for(policy_name):
	calendar_name = None
	if policy_name:
		calendar_name = frappe.db.get_value("Onerc SLA Policy", policy_name, "business_calendar")
	return get_working_calendar(calendar_name)


def stamp_targets(doc, start=None):
	"""Resolve the SLA policy and stamp first_response_due / resolution_due."""
	policy_name = resolve_policy(doc)
	if not policy_name:
		return
	policy = frappe.get_cached_doc("Onerc SLA Policy", policy_name)
	calendar = _calendar_for(policy_name)
	start = get_datetime(start or doc.get("creation") or now_datetime())
	doc.sla_policy = policy_name
	if policy.first_response_minutes:
		doc.first_response_due = add_working_minutes(start, policy.first_response_minutes, calendar)
	if policy.resolution_minutes:
		doc.resolution_due = add_working_minutes(start, policy.resolution_minutes, calendar)
	if not doc.get("sla_status"):
		doc.sla_status = "Ongoing"


def get_pause_statuses():
	settings = frappe.get_cached_doc("Onerc Incidents Settings")
	return {row.status for row in settings.pause_statuses if row.status}


def apply_pause(doc):
	doc.on_hold_since = now_datetime()
	doc.sla_status = "Paused"


def apply_resume(doc):
	"""Add the working minutes spent on hold back onto both due dates."""
	if doc.get("on_hold_since"):
		calendar = _calendar_for(doc.get("sla_policy"))
		held = working_minutes_between(get_datetime(doc.on_hold_since), now_datetime(), calendar)
		doc.total_hold_minutes = flt(doc.get("total_hold_minutes")) + held
		if doc.get("first_response_due") and not doc.get("first_responded_on"):
			doc.first_response_due = add_working_minutes(
				get_datetime(doc.first_response_due), held, calendar
			)
		if doc.get("resolution_due") and not doc.get("resolved_on"):
			doc.resolution_due = add_working_minutes(get_datetime(doc.resolution_due), held, calendar)
	doc.on_hold_since = None
	doc.sla_status = "Ongoing"


def handle_status_change(doc):
	"""Pause or resume SLA timers when a record enters/leaves a pause status.

	Called from the controller's validate() on existing records.
	"""
	if doc.is_new() or not doc.has_value_changed("status"):
		return
	pause_statuses = get_pause_statuses()
	if not pause_statuses:
		return
	before = doc.get_doc_before_save()
	was_paused = bool(before) and before.get("status") in pause_statuses
	is_paused = doc.get("status") in pause_statuses
	if is_paused and not was_paused:
		apply_pause(doc)
	elif was_paused and not is_paused:
		apply_resume(doc)
