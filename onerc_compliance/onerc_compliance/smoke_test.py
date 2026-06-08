# Copyright (c) 2026, Kelvin Njenga and contributors
# For license information, please see license.txt
#
# Run via:
#   bench --site onerc.localhost execute onerc_compliance.onerc_compliance.smoke_test.run

import json
import frappe


_SMOKE_USER = "_smoke-compliance-staff@example.com"
_SMOKE_EMP_SUFFIX = "smoke-test-001"
_SMOKE_REQ_TITLE = "_smoke Compliance Requirement"


def _cleanup():
	frappe.set_user("Administrator")

	# --- submissions (child tables first, then parent) ---
	sub_names = frappe.db.sql_list(
		"SELECT name FROM `tabCompliance Submission` WHERE requirement IN "
		"(SELECT name FROM `tabCompliance Requirement` WHERE title = %s)",
		_SMOKE_REQ_TITLE,
	)
	# Also catch any orphaned submissions linked to the smoke employee
	emp_names = frappe.db.sql_list(
		"SELECT name FROM `tabEmployee` WHERE employee_name LIKE %s",
		f"%{_SMOKE_EMP_SUFFIX}%",
	)
	if emp_names:
		extra = frappe.db.sql_list(
			"SELECT name FROM `tabCompliance Submission` WHERE employee IN ({})".format(
				",".join(["%s"] * len(emp_names))
			),
			emp_names,
		)
		sub_names = list(set(sub_names + extra))

	if sub_names:
		placeholders = ",".join(["%s"] * len(sub_names))
		frappe.db.sql(f"DELETE FROM `tabCompliance Submission Value` WHERE parent IN ({placeholders})", sub_names)
		frappe.db.sql(f"DELETE FROM `tabCompliance Review Action` WHERE parent IN ({placeholders})", sub_names)
		frappe.db.sql(f"DELETE FROM `tabCompliance Submission` WHERE name IN ({placeholders})", sub_names)

	# --- requirement ---
	frappe.db.sql(
		"DELETE FROM `tabCompliance Requirement Field` WHERE parent IN "
		"(SELECT name FROM `tabCompliance Requirement` WHERE title = %s)",
		_SMOKE_REQ_TITLE,
	)
	frappe.db.sql(
		"DELETE FROM `tabCompliance Target Department` WHERE parent IN "
		"(SELECT name FROM `tabCompliance Requirement` WHERE title = %s)",
		_SMOKE_REQ_TITLE,
	)
	frappe.db.sql("DELETE FROM `tabCompliance Requirement` WHERE title = %s", _SMOKE_REQ_TITLE)

	# --- employee ---
	if emp_names:
		placeholders = ",".join(["%s"] * len(emp_names))
		frappe.db.sql(f"DELETE FROM `tabEmployee` WHERE name IN ({placeholders})", emp_names)

	# --- user ---
	frappe.db.sql("DELETE FROM `tabHas Role` WHERE parent = %s", _SMOKE_USER)
	frappe.db.sql("DELETE FROM `tabUser` WHERE name = %s", _SMOKE_USER)

	frappe.db.commit()


def run():
	print("=" * 60)
	print("onerc_compliance smoke test")
	print("=" * 60)

	_cleanup()

	try:
		_run_all()
		print("\n✓  All smoke test steps passed.")
	except Exception as exc:
		print(f"\n✗  Smoke test FAILED: {exc}")
		import traceback
		traceback.print_exc()
		raise
	finally:
		_cleanup()
		print("Cleanup complete.")


def _run_all():
	from onerc_compliance.api.v1.compliance import (
		get_my_requirements,
		submit_requirement,
		get_submissions,
		get_dashboard,
		review_submission,
	)

	# ── Step 1: Create Employee linked to smoke user ────────────────────────
	print("\n[1] Creating smoke employee…")
	emp = frappe.get_doc({
		"doctype": "Employee",
		"first_name": f"_smoke-{_SMOKE_EMP_SUFFIX}",
		"employee_name": f"_smoke-{_SMOKE_EMP_SUFFIX}",
		"status": "Active",
		"gender": "Male",
		"date_of_birth": "1990-01-01",
		"date_of_joining": "2020-01-01",
		"company": frappe.db.get_value("Company", {}, "name") or "United Nations",
	})
	emp.insert(ignore_permissions=True)
	frappe.db.commit()
	print(f"   Employee: {emp.name}")

	# ── Step 2: Create smoke user with Employee role ────────────────────────
	print("\n[2] Creating smoke user…")
	user = frappe.get_doc({
		"doctype": "User",
		"email": _SMOKE_USER,
		"first_name": "_Smoke",
		"last_name": "Staff",
		"enabled": 1,
		"user_type": "System User",
		"roles": [{"role": "Employee"}],
	})
	user.insert(ignore_permissions=True)

	# Link employee to user
	emp.reload()
	emp.user_id = _SMOKE_USER
	emp.save(ignore_permissions=True)
	frappe.db.commit()
	print(f"   User: {_SMOKE_USER} linked to {emp.name}")

	# ── Step 3: Create Active requirement targeting All Staff ───────────────
	print("\n[3] Creating Active compliance requirement…")
	req = frappe.get_doc({
		"doctype": "Compliance Requirement",
		"title": _SMOKE_REQ_TITLE,
		"target_type": "All Staff",
		"deadline": "2099-12-31 23:59:00",
		"status": "Active",
		"requires_review": 1,
		"fields": [
			{
				"label": "Full Name",
				"fieldtype": "Data",
				"mandatory": 1,
			},
			{
				"label": "Acknowledgement",
				"fieldtype": "Check",
				"mandatory": 0,
			},
		],
	})
	req.insert(ignore_permissions=True)
	frappe.db.commit()
	print(f"   Requirement: {req.name}")

	# ── Step 4: get_my_requirements as staff user ───────────────────────────
	print("\n[4] Calling get_my_requirements as staff user…")
	frappe.set_user(_SMOKE_USER)
	result = get_my_requirements()
	assert result["status"] == "success", f"Expected success, got: {result}"
	reqs_list = result["data"]
	matched = [r for r in reqs_list if r["requirement"] == req.name]
	assert matched, f"Smoke requirement not found in get_my_requirements: {[r['requirement'] for r in reqs_list]}"
	req_entry = matched[0]
	print(f"   Found requirement '{req_entry['title']}' with status '{req_entry['submission_status']}'")
	assert req_entry["submission_status"] == "Pending", f"Expected Pending, got {req_entry['submission_status']}"

	# ── Step 5: submit_requirement as staff user ────────────────────────────
	print("\n[5] Submitting requirement as staff user…")
	answers = {
		req_entry["field_schema"][0]["fieldname"]: "Jane Smoke",
		req_entry["field_schema"][1]["fieldname"]: True,
	}
	result = submit_requirement(requirement=req.name, answers=json.dumps(answers))
	assert result["status"] == "success", f"submit_requirement failed: {result}"
	submission_name = result["data"]["submission"]
	assert result["data"]["status"] == "Submitted", f"Expected Submitted, got {result['data']['status']}"
	print(f"   Submission: {submission_name} → Submitted")

	# ── Step 6: get_submissions as staff user should be denied ──────────────
	print("\n[6] Confirming get_submissions is denied for staff user…")
	try:
		get_submissions(requirement=req.name)
		raise AssertionError("get_submissions should have raised PermissionError for Employee role")
	except frappe.PermissionError:
		print("   PermissionError raised as expected — employee correctly denied.")

	# ── Step 7: get_submissions as Administrator ────────────────────────────
	print("\n[7] Calling get_submissions as Administrator…")
	frappe.set_user("Administrator")
	result = get_submissions(requirement=req.name)
	assert result["status"] == "success", f"get_submissions failed: {result}"
	subs = result["data"]
	assert len(subs) >= 1, f"Expected at least 1 submission, got {len(subs)}"
	smoke_sub = next((s for s in subs if s["name"] == submission_name), None)
	assert smoke_sub, f"Smoke submission {submission_name} not in get_submissions response"
	assert smoke_sub["status"] == "Submitted"
	print(f"   Got {len(subs)} submission(s); smoke submission present and Submitted.")

	# ── Step 8: get_dashboard as Administrator ──────────────────────────────
	print("\n[8] Calling get_dashboard as Administrator…")
	result = get_dashboard(requirement=req.name)
	assert result["status"] == "success", f"get_dashboard failed: {result}"
	dash = result["data"]
	assert dash["requirement"] == req.name
	assert dash["status_counts"].get("Submitted", 0) >= 1, f"No Submitted in status_counts: {dash['status_counts']}"
	print(f"   Dashboard: completion={dash['completion_percent']}%, status_counts={dash['status_counts']}")

	# ── Step 9: review_submission as Administrator ──────────────────────────
	print("\n[9] Reviewing submission as Administrator…")
	result = review_submission(submission=submission_name, action="Reviewed", remarks="")
	assert result["status"] == "success", f"review_submission failed: {result}"
	assert result["data"]["status"] == "Reviewed", f"Expected Reviewed, got {result['data']['status']}"
	print(f"   Submission → Reviewed")

	# ── Step 10: Verify final DB state ─────────────────────────────────────
	print("\n[10] Verifying final DB status…")
	db_status = frappe.db.get_value("Compliance Submission", submission_name, "status")
	assert db_status == "Reviewed", f"DB shows '{db_status}', expected 'Reviewed'"
	print(f"   DB confirms status = {db_status}")

	# ── Step 11: HTTP reachability check for /compliance ───────────────────
	print("\n[11] Checking /compliance page is registered…")
	from frappe.utils import get_url
	site_url = get_url()
	print(f"   Site URL: {site_url}")
	# Verify the www entry exists on disk (HTTP request would require a running server)
	import os
	www_path = frappe.get_app_path("onerc_compliance", "www", "compliance", "index.html")
	assert os.path.exists(www_path), f"www/compliance/index.html not found at {www_path}"
	print(f"   www/compliance/index.html exists at {www_path}")

	print("\n✓  Full round-trip complete.")
