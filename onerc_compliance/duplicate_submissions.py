# Copyright (c) 2026, Kelvin Njenga and contributors
# For license information, please see license.txt

"""Inspect (and optionally tidy) duplicate Compliance Submissions.

Duplicates arose because `ensure_submission` checked for an existing row and
then inserted, with nothing making the two atomic. That race is now closed at
source, so no new duplicates should appear; this module is for dealing with rows
created before the fix.

Nothing here runs automatically. There is no patch and no scheduler entry — a
duplicate holds real submitted work, so deciding what happens to it is a human's
call, not a side effect of `bench migrate`.

Inspect what exists:

    bench --site <site> execute \
        onerc_compliance.duplicate_submissions.find_duplicate_submissions

`cleanup_duplicate_submissions` defaults to a dry run and will only ever remove
a row that is provably empty — no answers, no attachments, no review actions and
never submitted. If any duplicate in a group carries data, the whole group is
left untouched and reported for manual review.
"""

import frappe

#: Used only to break ties between rows that are equally empty or equally full.
STATUS_RANK = {
	"Pending": 0,
	"Overdue": 1,
	"Rejected": 2,
	"Needs More Info": 3,
	"Submitted": 4,
	"Exempted": 5,
	"Reviewed": 6,
}


def _row_detail(name):
	"""Everything needed to judge whether a row is safe to remove."""
	values = frappe.get_all(
		"Compliance Submission Value",
		filters={"parent": name},
		fields=["field_name", "value", "value_date", "value_check", "attachment"],
	)
	answered = 0
	attachments = 0
	for value in values:
		if value.attachment:
			attachments += 1
			answered += 1
		elif (value.value or "").strip() or value.value_date or value.value_check:
			answered += 1

	doc = frappe.db.get_value(
		"Compliance Submission", name, ["status", "submitted_on", "creation"], as_dict=True
	)
	actions = frappe.db.count("Compliance Review Action", {"parent": name})

	return {
		"name": name,
		"status": doc.status,
		"submitted_on": str(doc.submitted_on) if doc.submitted_on else None,
		"creation": str(doc.creation),
		"value_rows": len(values),
		"answered": answered,
		"attachments": attachments,
		"review_actions": actions,
		# The single question that governs removal.
		"holds_data": bool(answered or attachments or actions or doc.submitted_on),
	}


def find_duplicate_submissions():
	"""Report every (requirement, employee) pair with more than one submission.

	Read-only. Returns a list of groups, each listing what every row holds so a
	human can see exactly what is at stake before anything is touched.
	"""
	pairs = frappe.db.sql(
		"""
		SELECT requirement, employee, COUNT(*) AS total
		FROM `tabCompliance Submission`
		GROUP BY requirement, employee
		HAVING COUNT(*) > 1
		""",
		as_dict=True,
	)

	groups = []
	for pair in pairs:
		names = frappe.get_all(
			"Compliance Submission",
			filters={"requirement": pair.requirement, "employee": pair.employee},
			pluck="name",
			order_by="creation asc",
		)
		rows = [_row_detail(name) for name in names]
		groups.append({
			"requirement": pair.requirement,
			"employee": pair.employee,
			"count": pair.total,
			"rows": rows,
			"rows_holding_data": sum(1 for row in rows if row["holds_data"]),
		})

	print("Duplicate (requirement, employee) pairs: {0}".format(len(groups)))
	for group in groups:
		print("\n{0} / {1}  — {2} rows, {3} hold data".format(
			group["requirement"], group["employee"], group["count"], group["rows_holding_data"]
		))
		for row in group["rows"]:
			print("   {0}  {1:<16} answered={2} attachments={3} actions={4} submitted_on={5}{6}".format(
				row["name"], row["status"], row["answered"], row["attachments"],
				row["review_actions"], row["submitted_on"],
				"  <-- HOLDS DATA" if row["holds_data"] else "",
			))

	return groups


def cleanup_duplicate_submissions(dry_run=True):
	"""Remove only provably empty duplicate rows. Dry run unless told otherwise.

	A group is skipped entirely — and reported — unless exactly one row holds
	data, or none do. Nothing that carries an answer, an attachment, a review
	action or a submission timestamp is ever deleted.
	"""
	dry_run = not (dry_run is False or str(dry_run).lower() in ("0", "false", "no"))

	groups = find_duplicate_submissions()
	summary = {"groups": len(groups), "removable": 0, "removed": 0, "skipped_groups": []}

	for group in groups:
		with_data = [row for row in group["rows"] if row["holds_data"]]

		if len(with_data) > 1:
			# Two rows both carry real work; merging them is a judgement call.
			summary["skipped_groups"].append({
				"requirement": group["requirement"],
				"employee": group["employee"],
				"reason": "more than one row holds submitted data",
				"rows": [row["name"] for row in with_data],
			})
			continue

		if with_data:
			keep = with_data[0]
		else:
			# All empty — keep the furthest along, oldest as tie-break.
			keep = max(group["rows"], key=lambda r: (STATUS_RANK.get(r["status"], 0), -len(r["creation"])))

		for row in group["rows"]:
			if row["name"] == keep["name"] or row["holds_data"]:
				continue
			summary["removable"] += 1
			if dry_run:
				print("   would remove empty duplicate {0} (keeping {1})".format(
					row["name"], keep["name"]))
				continue
			frappe.db.delete("Compliance Submission Value", {"parent": row["name"]})
			frappe.db.delete("Compliance Review Action", {"parent": row["name"]})
			frappe.db.delete("Compliance Submission", {"name": row["name"]})
			summary["removed"] += 1
			print("   removed empty duplicate {0} (kept {1})".format(row["name"], keep["name"]))

	if not dry_run and summary["removed"]:
		frappe.db.commit()

	print("\n{0}: {1} empty duplicate rows {2}, {3} groups need manual review.".format(
		"DRY RUN" if dry_run else "APPLIED",
		summary["removable"] if dry_run else summary["removed"],
		"would be removed" if dry_run else "removed",
		len(summary["skipped_groups"]),
	))
	for skipped in summary["skipped_groups"]:
		print("   MANUAL: {0} / {1} — {2}: {3}".format(
			skipped["requirement"], skipped["employee"], skipped["reason"], skipped["rows"]))

	return summary
