# Copyright (c) 2026, Kelvin Njenga and contributors
# For license information, please see license.txt

# NOTE: Email reminders are disabled by design. `send_compliance_reminders`
# (and its inline reminder logic) is intentionally left in place but is no
# longer wired into scheduler_events in hooks.py, so it does not run. Staff
# are now nudged via in-app notifications in the frontend instead of email.
# The function is kept so its lead/repeat-day logic can be repurposed for
# those notifications later.

import frappe
from frappe import _
from frappe.utils import add_days, getdate, now_datetime, today


def close_expired_requirements():
	now = now_datetime()
	requirements = frappe.get_all(
		"Compliance Requirement",
		filters={"status": "Active", "deadline": ["<", now]},
		fields=["name"],
	)
	for req in requirements:
		frappe.db.set_value("Compliance Requirement", req.name, "status", "Closed")

		for status in ("Pending", "Needs More Info"):
			submissions = frappe.get_all(
				"Compliance Submission",
				filters={"requirement": req.name, "status": status},
				fields=["name"],
			)
			for sub in submissions:
				frappe.db.set_value("Compliance Submission", sub.name, "status", "Overdue")

	frappe.db.commit()


def send_compliance_reminders():
	today_date = getdate(today())
	requirements = frappe.get_all(
		"Compliance Requirement",
		filters={"status": "Active"},
		fields=["name", "deadline", "reminder_lead_days", "reminder_repeat_days"],
	)

	for req in requirements:
		lead_days = req.reminder_lead_days or 7
		repeat_days = req.reminder_repeat_days or 2
		deadline_date = getdate(req.deadline)
		lead_date = getdate(add_days(deadline_date, -lead_days))

		if today_date < lead_date:
			continue

		req_doc = frappe.get_doc("Compliance Requirement", req.name)
		from onerc_compliance.utils import ensure_submission, get_in_scope_employees

		employees = get_in_scope_employees(req_doc)
		for emp in employees:
			ensure_submission(req.name, emp)

		submissions = frappe.get_all(
			"Compliance Submission",
			filters={
				"requirement": req.name,
				"status": ["in", ["Pending", "Needs More Info"]],
			},
			fields=["name", "employee", "last_reminded_on"],
		)

		cutoff = getdate(add_days(today_date, -repeat_days))

		for sub in submissions:
			if sub.last_reminded_on:
				if getdate(sub.last_reminded_on) >= cutoff:
					continue

			emp_data = frappe.db.get_value(
				"Employee",
				sub.employee,
				["company_email", "user_id"],
				as_dict=True,
			)
			if not emp_data:
				continue

			email = emp_data.company_email or emp_data.user_id
			if not email:
				continue

			req_title = frappe.db.get_value("Compliance Requirement", req.name, "title")
			frappe.sendmail(
				recipients=[email],
				subject=_("Compliance Reminder: {0}").format(req_title or req.name),
				message=_("Please complete your compliance submission for: {0}").format(
					req_title or req.name
				),
				now=True,
			)
			frappe.db.set_value(
				"Compliance Submission", sub.name, "last_reminded_on", today_date
			)

	frappe.db.commit()
