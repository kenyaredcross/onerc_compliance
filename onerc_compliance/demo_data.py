"""
Demo data loader for onerc_compliance.

All records are clearly namespaced — emails end in @demo.local,
requirement titles start with "DEMO: " — so teardown is reliable.

Usage:
    bench --site onerc.localhost execute onerc_compliance.demo_data.load
    bench --site onerc.localhost execute onerc_compliance.demo_data.teardown
"""

import frappe
from frappe.utils import add_days, now_datetime, today

DEMO_PASSWORD = "Demo@1234"
DEMO_COMPANY = "United Nations"

DEMO_STAFF = [
    {"email": "demo.alice@demo.local", "first": "Alice", "last": "Demo", "dept": "Operations"},
    {"email": "demo.bob@demo.local",   "first": "Bob",   "last": "Demo", "dept": "Operations"},
    {"email": "demo.carol@demo.local", "first": "Carol", "last": "Demo", "dept": "Human Resources"},
    {"email": "demo.dave@demo.local",  "first": "Dave",  "last": "Demo", "dept": "Human Resources"},
]

DEMO_OFFICER_EMAIL = "demo.officer@demo.local"

_REQ1_TITLE = "DEMO: Annual Policy Acknowledgement"
_REQ2_TITLE = "DEMO: Operations Safety Compliance"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_or_create_user(email, first, last, roles):
    if frappe.db.exists("User", email):
        return frappe.get_doc("User", email)
    user = frappe.get_doc({
        "doctype": "User",
        "email": email,
        "first_name": first,
        "last_name": last,
        "enabled": 1,
        "user_type": "System User",
        "new_password": DEMO_PASSWORD,
        "roles": [{"role": r} for r in roles],
    })
    user.insert(ignore_permissions=True)
    return user


def _get_or_create_employee(email, first, last, dept):
    existing = frappe.db.get_value("Employee", {"company_email": email}, "name")
    if existing:
        return existing
    emp = frappe.get_doc({
        "doctype": "Employee",
        "first_name": first,
        "last_name": last,
        "employee_name": f"{first} {last}",
        "status": "Active",
        "gender": "Male",
        "date_of_birth": "1990-01-01",
        "date_of_joining": "2020-01-01",
        "company": DEMO_COMPANY,
        "department": dept,
        "company_email": email,
        "user_id": email,
    })
    emp.insert(ignore_permissions=True)
    return emp.name


def _get_or_create_requirement(title, target_type, fields_def,
                                requires_review=1, target_departments=None):
    existing = frappe.db.get_value("Compliance Requirement", {"title": title}, "name")
    if existing:
        return existing

    deadline = f"{add_days(today(), 90)} 23:59:00"

    fields = [
        {
            "label": f["label"],
            "fieldtype": f["fieldtype"],
            "options": f.get("options", ""),
            "mandatory": f.get("mandatory", 0),
        }
        for f in fields_def
    ]

    dept_rows = [{"department": d} for d in (target_departments or [])]

    doc = frappe.get_doc({
        "doctype": "Compliance Requirement",
        "title": title,
        "target_type": target_type,
        "target_departments": dept_rows,
        "deadline": deadline,
        "requires_review": requires_review,
        "status": "Active",
        "fields": fields,
    })
    doc.insert(ignore_permissions=True)
    return doc.name


def _get_submission(requirement, employee):
    return frappe.db.get_value(
        "Compliance Submission",
        {"requirement": requirement, "employee": employee},
        "name",
    )


def _submit(sub_name, req_doc, answers):
    """Fill answers and move the submission to Submitted status."""
    sub = frappe.get_doc("Compliance Submission", sub_name)
    if sub.status not in ("Pending", "Needs More Info"):
        return
    sub.values = []
    for sf in req_doc.fields:
        raw = answers.get(sf.fieldname)
        row = {
            "field_name": sf.fieldname,
            "field_label": sf.label or sf.fieldname,
            "field_type": sf.fieldtype,
        }
        if sf.fieldtype == "Check":
            row["value_check"] = 1 if raw else 0
        elif sf.fieldtype == "Date":
            row["value_date"] = raw or None
        elif sf.fieldtype == "Attach":
            row["attachment"] = raw or None
        else:
            row["value"] = str(raw) if raw is not None else ""
        sub.append("values", row)
    sub.status = "Submitted"
    sub.submitted_on = now_datetime()
    sub.save(ignore_permissions=True)
    frappe.db.commit()


def _review(sub_name, action, remarks=""):
    """Add a review action and update status (Reviewed / Needs More Info)."""
    sub = frappe.get_doc("Compliance Submission", sub_name)
    if sub.status != "Submitted":
        return
    sub.append("review_actions", {
        "action": action,
        "reviewer": DEMO_OFFICER_EMAIL,
        "action_on": now_datetime(),
        "remarks": remarks,
    })
    sub.status = action
    sub.save(ignore_permissions=True)
    frappe.db.commit()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def load():
    """Create all demo records idempotently and print login credentials."""
    frappe.set_user("Administrator")

    # ── Users ────────────────────────────────────────────────────────────
    for s in DEMO_STAFF:
        _get_or_create_user(s["email"], s["first"], s["last"], ["Employee"])

    _get_or_create_user(DEMO_OFFICER_EMAIL, "Demo", "Officer",
                        ["Compliance Officer", "Employee"])
    frappe.db.commit()

    # ── Employees ────────────────────────────────────────────────────────
    emp_ids = {}
    for s in DEMO_STAFF:
        emp_ids[s["email"]] = _get_or_create_employee(
            s["email"], s["first"], s["last"], s["dept"]
        )
    frappe.db.commit()

    # ── Requirement 1: All Staff (Check, Date, Select, Data, Attach) ─────
    req1 = _get_or_create_requirement(
        title=_REQ1_TITLE,
        target_type="All Staff",
        requires_review=1,
        fields_def=[
            {"label": "I have read the policy",      "fieldtype": "Check",  "mandatory": 1},
            {"label": "Training Completion Date",     "fieldtype": "Date",   "mandatory": 1},
            {"label": "Training Mode",                "fieldtype": "Select", "mandatory": 1,
             "options": "Online\nIn-Person\nSelf-Study"},
            {"label": "Declaration Statement",        "fieldtype": "Data",   "mandatory": 0},
            {"label": "Certificate / Evidence",       "fieldtype": "Attach", "mandatory": 0},
        ],
    )

    # ── Requirement 2: By Department — Operations ─────────────────────────
    req2 = _get_or_create_requirement(
        title=_REQ2_TITLE,
        target_type="By Department",
        target_departments=["Operations"],
        requires_review=1,
        fields_def=[
            {"label": "Safety Checklist Complete",    "fieldtype": "Check",  "mandatory": 1},
            {"label": "Incident Notes (if any)",      "fieldtype": "Data",   "mandatory": 0},
        ],
    )
    frappe.db.commit()

    # ── Ensure all in-scope submissions exist ────────────────────────────
    # _generate_submissions fires on Active status, but guard here in case
    # the requirement already existed when load() was re-run.
    from onerc_compliance.utils import ensure_submission, get_in_scope_employees

    for req_name in (req1, req2):
        req_doc = frappe.get_doc("Compliance Requirement", req_name)
        for emp in get_in_scope_employees(req_doc):
            ensure_submission(req_name, emp)
    frappe.db.commit()

    # ── Build answer maps from live fieldnames (set by validator) ────────
    req1_doc = frappe.get_doc("Compliance Requirement", req1)
    fn1 = {f.label: f.fieldname for f in req1_doc.fields}
    req1_answers = {
        fn1["I have read the policy"]:   True,
        fn1["Training Completion Date"]: today(),
        fn1["Training Mode"]:            "Online",
        fn1["Declaration Statement"]:    "I confirm all information is accurate.",
        fn1["Certificate / Evidence"]:   None,
    }

    req2_doc = frappe.get_doc("Compliance Requirement", req2)
    fn2 = {f.label: f.fieldname for f in req2_doc.fields}
    req2_answers = {
        fn2["Safety Checklist Complete"]: True,
        fn2["Incident Notes (if any)"]:   "",
    }

    alice = emp_ids["demo.alice@demo.local"]
    bob   = emp_ids["demo.bob@demo.local"]
    carol = emp_ids["demo.carol@demo.local"]
    # dave  → Pending (no action)

    # ── Req 1 submission states ───────────────────────────────────────────
    # Alice  → Submitted
    s = _get_submission(req1, alice)
    if s:
        _submit(s, req1_doc, req1_answers)

    # Bob    → Reviewed
    s = _get_submission(req1, bob)
    if s:
        _submit(s, req1_doc, req1_answers)
        _review(s, "Reviewed")

    # Carol  → Needs More Info
    s = _get_submission(req1, carol)
    if s:
        _submit(s, req1_doc, req1_answers)
        _review(s, "Needs More Info", "Please attach your training certificate.")

    # ── Req 2 submission states ───────────────────────────────────────────
    # Alice  → Submitted
    s = _get_submission(req2, alice)
    if s:
        _submit(s, req2_doc, req2_answers)
    # Bob    → Pending (no action)

    frappe.db.commit()

    # ── Print credentials ─────────────────────────────────────────────────
    print("\n" + "=" * 62)
    print("  OneRC Compliance — Demo Data Loaded")
    print("=" * 62)
    print(f"\n  Password (all demo accounts): {DEMO_PASSWORD}")
    print("\n  STAFF LOGINS  →  /compliance")
    for s in DEMO_STAFF:
        print(f"    {s['email']:30s}  ({s['dept']})")
    print("\n  OFFICER LOGIN  →  /compliance/dashboard")
    print(f"    {DEMO_OFFICER_EMAIL}")
    print("\n  Req 1 — Annual Policy Acknowledgement (All Staff):")
    print(f"    Alice  {emp_ids['demo.alice@demo.local']}  → Submitted")
    print(f"    Bob    {emp_ids['demo.bob@demo.local']}  → Reviewed")
    print(f"    Carol  {emp_ids['demo.carol@demo.local']}  → Needs More Info")
    print(f"    Dave   {emp_ids['demo.dave@demo.local']}  → Pending")
    print("\n  Req 2 — Operations Safety Compliance (Operations dept):")
    print(f"    Alice  → Submitted")
    print(f"    Bob    → Pending")
    print("=" * 62 + "\n")


def teardown():
    """Remove all demo records created by load()."""
    frappe.set_user("Administrator")

    # 1. Collect demo requirement names
    demo_reqs = frappe.get_all(
        "Compliance Requirement",
        filters={"title": ["like", "DEMO: %"]},
        pluck="name",
    )

    # 2. Delete submissions that reference demo requirements
    for req_name in demo_reqs:
        subs = frappe.get_all(
            "Compliance Submission",
            filters={"requirement": req_name},
            pluck="name",
        )
        for sub_name in subs:
            frappe.delete_doc(
                "Compliance Submission", sub_name,
                force=True, ignore_permissions=True,
            )
    frappe.db.commit()

    # 3. Delete demo requirements
    for req_name in demo_reqs:
        frappe.delete_doc(
            "Compliance Requirement", req_name,
            force=True, ignore_permissions=True,
        )
    frappe.db.commit()

    # 4. Delete demo employees (matched by @demo.local company_email)
    demo_emps = frappe.get_all(
        "Employee",
        filters={"company_email": ["like", "%@demo.local"]},
        pluck="name",
    )
    for emp_name in demo_emps:
        frappe.delete_doc(
            "Employee", emp_name,
            force=True, ignore_permissions=True,
        )
    frappe.db.commit()

    # 5. Delete demo users
    demo_users = frappe.get_all(
        "User",
        filters={"email": ["like", "%@demo.local"]},
        pluck="name",
    )
    for email in demo_users:
        frappe.delete_doc(
            "User", email,
            force=True, ignore_permissions=True,
        )
    frappe.db.commit()

    print("\nOneRC Compliance — demo data removed.\n")


def verify():
    """Quick smoke-check of all demo API paths."""
    from onerc_compliance.api.v1.compliance import (
        get_my_requirements, get_submissions, get_dashboard,
    )

    original_user = frappe.session.user

    # Alice — Operations dept, should see 2 requirements
    frappe.set_user("demo.alice@demo.local")
    r = get_my_requirements()
    assert r["status"] == "success", f"Alice: {r}"
    assert len(r["data"]) == 2, f"Alice req count: {len(r['data'])}"
    for item in r["data"]:
        assert "review_actions" in item, f"review_actions missing for {item['title']}"
    print(f"Alice  ✔  {len(r['data'])} requirements")

    # Carol — Human Resources, should see Req 1 in Needs More Info with a remark
    frappe.set_user("demo.carol@demo.local")
    r = get_my_requirements()
    assert r["status"] == "success", f"Carol: {r}"
    assert len(r["data"]) == 1, f"Carol req count: {len(r['data'])}"
    req = r["data"][0]
    assert req["submission_status"] == "Needs More Info", f"Carol status: {req['submission_status']}"
    assert len(req.get("review_actions", [])) == 1, "Carol should have 1 review action"
    assert req["review_actions"][0]["remarks"], "Carol review action must have remarks"
    print(f"Carol  ✔  status={req['submission_status']}, remark present")

    # Dave — Human Resources, Req 1 only, Pending
    frappe.set_user("demo.dave@demo.local")
    r = get_my_requirements()
    assert r["status"] == "success", f"Dave: {r}"
    assert len(r["data"]) == 1 and r["data"][0]["submission_status"] == "Pending"
    print(f"Dave   ✔  status=Pending")

    # Officer — get_dashboard and get_submissions
    frappe.set_user("demo.officer@demo.local")
    req1 = frappe.db.get_value("Compliance Requirement",
                               {"title": _REQ1_TITLE}, "name")
    d = get_dashboard(requirement=req1)
    assert d["status"] == "success", f"Dashboard: {d}"
    sc = d["data"]["status_counts"]
    print(f"Officer dashboard ✔  status_counts={sc}, completion={d['data']['completion_percent']}%")
    subs = get_submissions(requirement=req1)
    assert subs["status"] == "success"
    print(f"Officer submissions ✔  {len(subs['data'])} records")

    frappe.set_user(original_user)
    print("\nAll demo API paths verified ✔")
