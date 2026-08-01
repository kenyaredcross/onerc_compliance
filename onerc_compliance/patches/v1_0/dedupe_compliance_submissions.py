"""Remove duplicate Compliance Submissions and stop them coming back.

`ensure_submission` used to check-then-insert with no atomicity, and activating a
requirement with more than 200 employees runs that loop in a background job while
staff can hit `get_my_requirements` at the same time. Two writers could both pass
the existence check and both insert, leaving two rows for one
(requirement, employee) pair.

The uniqueness check in `ComplianceSubmission.validate` then throws on *any* save
of either row — "A submission already exists for employee X on requirement Y" —
which blocks the Overdue -> Pending reset that reopening a requirement performs,
so the requirement can no longer be extended and reactivated.

This collapses each duplicate group down to the row worth keeping and adds a
unique index so the database refuses to create another pair.
"""

import frappe

#: Higher wins. A reviewed submission carries more history than a pending one,
#: so it is the row to keep when a pair has several.
STATUS_RANK = {
	"Pending": 0,
	"Overdue": 1,
	"Rejected": 2,
	"Needs More Info": 3,
	"Submitted": 4,
	"Exempted": 5,
	"Reviewed": 6,
}


def _score(row):
	"""Rank a candidate: furthest through the workflow, then most data, then oldest."""
	values = frappe.db.count("Compliance Submission Value", {"parent": row.name})
	actions = frappe.db.count("Compliance Review Action", {"parent": row.name})
	return (
		STATUS_RANK.get(row.status, 0),
		values + actions,
		1 if row.submitted_on else 0,
		-(row.creation.timestamp() if row.creation else 0),
	)


def execute():
	duplicate_pairs = frappe.db.sql(
		"""
		SELECT requirement, employee
		FROM `tabCompliance Submission`
		GROUP BY requirement, employee
		HAVING COUNT(*) > 1
		""",
		as_dict=True,
	)

	if not duplicate_pairs:
		frappe.logger().info("No duplicate Compliance Submissions found.")
	else:
		removed = 0
		for pair in duplicate_pairs:
			rows = frappe.get_all(
				"Compliance Submission",
				filters={"requirement": pair.requirement, "employee": pair.employee},
				fields=["name", "status", "submitted_on", "creation"],
			)
			keep = max(rows, key=_score)

			for row in rows:
				if row.name == keep.name:
					continue
				# Child rows are not cascaded by a raw delete.
				frappe.db.delete("Compliance Submission Value", {"parent": row.name})
				frappe.db.delete("Compliance Review Action", {"parent": row.name})
				frappe.db.delete("Compliance Submission", {"name": row.name})
				removed += 1

			frappe.logger().info(
				"Deduped {0}/{1}: kept {2} ({3}), removed {4}".format(
					pair.requirement, pair.employee, keep.name, keep.status, len(rows) - 1
				)
			)

		frappe.db.commit()
		frappe.logger().info(
			"Removed {0} duplicate Compliance Submissions across {1} pairs.".format(
				removed, len(duplicate_pairs)
			)
		)

	# Belt and braces: even with the race closed in ensure_submission, let the
	# database be the final arbiter. Tolerated if it fails so a migrate is never
	# blocked by residual data.
	try:
		frappe.db.add_unique(
			"Compliance Submission",
			["requirement", "employee"],
			constraint_name="unique_requirement_employee",
		)
		frappe.db.commit()
	except Exception:
		frappe.db.rollback()
		frappe.log_error(
			frappe.get_traceback(),
			"Could not add unique index on Compliance Submission (requirement, employee)",
		)
