# Copyright (c) 2026, Kelvin Njenga and contributors
# For license information, please see license.txt
"""Scheduled SLA breach + escalation scan.

Runs every few minutes (see hooks.scheduler_events). For every open ITSM record
it flags response/resolution breaches and fires any escalation step whose
working-minute threshold has elapsed. Firing is idempotent: each (record, step)
pair is logged once in Onerc SLA Escalation Event.

The scan is guarded by ``table_exists`` so it is safe to schedule before the
transactional doctypes (Onerc Incident / Onerc Service Request) are migrated.
"""
import frappe
from frappe.utils import get_datetime, now_datetime

from onerc_compliance.onerc_incident_management.sla.working_time import (
	add_working_minutes,
	get_working_calendar,
)

SLA_DOCTYPES = ("Onerc Incident", "Onerc Service Request")

# Statuses that take a record out of scope for SLA scanning.
CLOSED_STATUSES = ("Resolved", "Closed", "Cancelled", "Rejected", "Fulfilled")

_SCAN_FIELDS = (
	"name",
	"creation",
	"status",
	"sla_policy",
	"first_response_due",
	"resolution_due",
	"first_responded_on",
	"resolved_on",
	"on_hold_since",
	"response_breached",
	"resolution_breached",
)


def scan_sla():
	for doctype in SLA_DOCTYPES:
		if frappe.db.table_exists(doctype):
			_scan_doctype(doctype)


def _scan_doctype(doctype):
	records = frappe.get_all(
		doctype,
		filters={"status": ["not in", CLOSED_STATUSES]},
		fields=list(_SCAN_FIELDS),
	)
	now = now_datetime()
	for record in records:
		_flag_breaches(doctype, record, now)
		if not record.on_hold_since:
			_fire_escalations(doctype, record, now)


def _flag_breaches(doctype, record, now):
	updates = {}
	breached = []
	if (
		record.first_response_due
		and not record.first_responded_on
		and not record.response_breached
		and get_datetime(record.first_response_due) < now
	):
		updates["response_breached"] = 1
		breached.append("first response")
	if (
		record.resolution_due
		and not record.resolved_on
		and not record.resolution_breached
		and get_datetime(record.resolution_due) < now
	):
		updates["resolution_breached"] = 1
		updates["sla_status"] = "Breached"
		breached.append("resolution")
	if updates:
		frappe.db.set_value(doctype, record.name, updates, update_modified=False)
		for kind in breached:
			_notify_breach(doctype, record.name, kind)


def _notify_breach(doctype, name, kind):
	recipient = None
	if frappe.db.has_column(doctype, "assigned_to"):
		recipient = frappe.db.get_value(doctype, name, "assigned_to")
	recipient = recipient or frappe.db.get_value(doctype, name, "owner")
	if not recipient:
		return
	try:
		frappe.sendmail(
			recipients=[recipient],
			subject=f"SLA {kind} breached: {name}",
			message=f"The {kind} SLA target for {doctype} {name} has been breached.",
		)
	except Exception:
		frappe.log_error(title="Onerc SLA breach notification failed")


def _already_fired(doctype, name):
	return set(
		frappe.get_all(
			"Onerc SLA Escalation Event",
			filters={"reference_doctype": doctype, "reference_name": name},
			pluck="escalation_step",
		)
	)


def _fire_escalations(doctype, record, now):
	if not record.sla_policy:
		return
	policy = frappe.get_cached_doc("Onerc SLA Policy", record.sla_policy)
	if not policy.escalation_steps:
		return
	calendar = get_working_calendar(policy.business_calendar)
	fired = _already_fired(doctype, record.name)
	created = get_datetime(record.creation)
	for step in policy.escalation_steps:
		if step.name in fired:
			continue
		if step.applies_to == "Response" and record.first_responded_on:
			continue
		if step.applies_to == "Resolution" and record.resolved_on:
			continue
		if add_working_minutes(created, step.after_minutes, calendar) < now:
			_fire_step(doctype, record, policy, step)


def _fire_step(doctype, record, policy, step):
	frappe.get_doc(
		{
			"doctype": "Onerc SLA Escalation Event",
			"reference_doctype": doctype,
			"reference_name": record.name,
			"policy": policy.name,
			"escalation_step": step.name,
			"step_label": step.step_label,
			"applies_to": step.applies_to,
			"fired_on": now_datetime(),
		}
	).insert(ignore_permissions=True)

	if step.notification:
		_send_step_notification(doctype, record.name, step.notification)


def _send_step_notification(doctype, name, notification):
	try:
		frappe.get_doc("Notification", notification).send(frappe.get_doc(doctype, name))
	except Exception:
		frappe.log_error(title="Onerc SLA escalation notification failed")
