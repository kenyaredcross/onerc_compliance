# onerc_compliance Backend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the full backend for the onerc_compliance Frappe app — doctypes, controllers, utils, permissions, scheduled tasks, API, and tests for a staff compliance attestation tracker.

**Architecture:** Six doctypes (four child tables, two parents) with controllers enforcing schema freeze and status-transition rules; shared utils for employee-scope resolution and submission creation; permission hooks restricting submission visibility per role; daily scheduled tasks for expiry and reminders; four whitelisted API endpoints returning a `{status, data, message, meta}` envelope.

**Tech Stack:** Python 3.14, Frappe 17 (bench at `~/frappe/redHive`), MariaDB, site `onerc.localhost`. No frontend. No git operations.

**Hard constraints:**
- NO git commands. No `git add`, `git commit`, `git push`, or any variant.
- Run only `bench --site onerc.localhost migrate` and `bench --site onerc.localhost run-tests --app onerc_compliance` for verification.
- `onerc_storage` is NOT installed — use `Attach` fieldtype (not `Link → OneRC Storage File`).
- ERPNext IS installed: `Employee`, `Department`, `Designation` doctypes exist.

---

## File Map

**Already correct — do not touch:**
- `onerc_compliance/onerc_compliance/doctype/compliance_requirement_field/compliance_requirement_field.json` — fully defined with `istable: 1`
- `onerc_compliance/onerc_compliance/doctype/compliance_requirement_field/compliance_requirement_field.py` — bare stub, no logic needed

**Create (new files):**
- `onerc_compliance/fixtures/role.json`
- `onerc_compliance/onerc_compliance/doctype/compliance_target_department/__init__.py`
- `onerc_compliance/onerc_compliance/doctype/compliance_target_department/compliance_target_department.json`
- `onerc_compliance/onerc_compliance/doctype/compliance_target_department/compliance_target_department.py`
- `onerc_compliance/onerc_compliance/doctype/compliance_submission_value/__init__.py`
- `onerc_compliance/onerc_compliance/doctype/compliance_submission_value/compliance_submission_value.json`
- `onerc_compliance/onerc_compliance/doctype/compliance_submission_value/compliance_submission_value.py`
- `onerc_compliance/onerc_compliance/doctype/compliance_review_action/__init__.py`
- `onerc_compliance/onerc_compliance/doctype/compliance_review_action/compliance_review_action.json`
- `onerc_compliance/onerc_compliance/doctype/compliance_review_action/compliance_review_action.py`
- `onerc_compliance/onerc_compliance/doctype/compliance_submission/__init__.py`
- `onerc_compliance/onerc_compliance/doctype/compliance_submission/compliance_submission.json`
- `onerc_compliance/onerc_compliance/doctype/compliance_submission/compliance_submission.py`
- `onerc_compliance/onerc_compliance/doctype/compliance_submission/test_compliance_submission.py`
- `onerc_compliance/onerc_compliance/utils.py`
- `onerc_compliance/onerc_compliance/permissions.py`
- `onerc_compliance/onerc_compliance/tasks.py`
- `onerc_compliance/onerc_compliance/api/__init__.py`
- `onerc_compliance/onerc_compliance/api/v1/__init__.py`
- `onerc_compliance/onerc_compliance/api/v1/compliance.py`

**Modify (existing files):**
- `onerc_compliance/onerc_compliance/hooks.py` — add scheduler_events, permission_query_conditions, has_permission, fixtures
- `onerc_compliance/onerc_compliance/doctype/compliance_requirement/compliance_requirement.json` — replace stub with full field definition
- `onerc_compliance/onerc_compliance/doctype/compliance_requirement/compliance_requirement.py` — implement `validate()` + `on_update()`
- `onerc_compliance/onerc_compliance/doctype/compliance_requirement/test_compliance_requirement.py` — add two tests

All paths are relative to `/home/chetri/frappe/redHive/apps/onerc_compliance/`.

---

## Task 1: Role fixture + hooks fixture registration

**Files:**
- Create: `onerc_compliance/fixtures/role.json`
- Modify: `onerc_compliance/onerc_compliance/hooks.py`

- [ ] **Step 1: Create the fixtures directory and role.json**

```bash
mkdir -p /home/chetri/frappe/redHive/apps/onerc_compliance/onerc_compliance/fixtures
```

Write `/home/chetri/frappe/redHive/apps/onerc_compliance/onerc_compliance/fixtures/role.json`:

```json
[
    {
        "doctype": "Role",
        "role_name": "Compliance Officer",
        "desk_access": 1
    }
]
```

- [ ] **Step 2: Add fixtures declaration to hooks.py**

Open `onerc_compliance/onerc_compliance/hooks.py`. At the end of the file, append:

```python
fixtures = [
    {
        "dt": "Role",
        "filters": [["role_name", "in", ["Compliance Officer"]]],
    }
]
```

---

## Task 2: Child doctype — Compliance Target Department

**Files:**
- Create: `onerc_compliance/onerc_compliance/doctype/compliance_target_department/__init__.py` (empty)
- Create: `onerc_compliance/onerc_compliance/doctype/compliance_target_department/compliance_target_department.json`
- Create: `onerc_compliance/onerc_compliance/doctype/compliance_target_department/compliance_target_department.py`

- [ ] **Step 1: Create directory and __init__.py**

```bash
mkdir -p /home/chetri/frappe/redHive/apps/onerc_compliance/onerc_compliance/onerc_compliance/doctype/compliance_target_department
touch /home/chetri/frappe/redHive/apps/onerc_compliance/onerc_compliance/onerc_compliance/doctype/compliance_target_department/__init__.py
```

- [ ] **Step 2: Write compliance_target_department.json**

```json
{
    "actions": [],
    "creation": "2026-06-08 00:00:00.000000",
    "doctype": "DocType",
    "editable_grid": 1,
    "engine": "InnoDB",
    "field_order": [
        "department"
    ],
    "fields": [
        {
            "fieldname": "department",
            "fieldtype": "Link",
            "in_list_view": 1,
            "label": "Department",
            "options": "Department",
            "reqd": 1
        }
    ],
    "grid_page_length": 50,
    "index_web_pages_for_search": 0,
    "istable": 1,
    "links": [],
    "modified": "2026-06-08 00:00:00.000000",
    "modified_by": "Administrator",
    "module": "Onerc Compliance",
    "name": "Compliance Target Department",
    "owner": "Administrator",
    "permissions": [],
    "row_format": "Dynamic",
    "sort_field": "creation",
    "sort_order": "DESC",
    "states": []
}
```

- [ ] **Step 3: Write compliance_target_department.py**

```python
# Copyright (c) 2026, Kelvin Njenga and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class ComplianceTargetDepartment(Document):
    pass
```

---

## Task 3: Child doctype — Compliance Submission Value

**Files:**
- Create: `onerc_compliance/onerc_compliance/doctype/compliance_submission_value/__init__.py` (empty)
- Create: `onerc_compliance/onerc_compliance/doctype/compliance_submission_value/compliance_submission_value.json`
- Create: `onerc_compliance/onerc_compliance/doctype/compliance_submission_value/compliance_submission_value.py`

- [ ] **Step 1: Create directory and __init__.py**

```bash
mkdir -p /home/chetri/frappe/redHive/apps/onerc_compliance/onerc_compliance/onerc_compliance/doctype/compliance_submission_value
touch /home/chetri/frappe/redHive/apps/onerc_compliance/onerc_compliance/onerc_compliance/doctype/compliance_submission_value/__init__.py
```

- [ ] **Step 2: Write compliance_submission_value.json**

Note: `onerc_storage` is NOT installed; using `Attach` for the `attachment` field.

```json
{
    "actions": [],
    "creation": "2026-06-08 00:00:00.000000",
    "doctype": "DocType",
    "editable_grid": 1,
    "engine": "InnoDB",
    "field_order": [
        "field_name",
        "field_label",
        "field_type",
        "value",
        "value_date",
        "value_check",
        "attachment"
    ],
    "fields": [
        {
            "fieldname": "field_name",
            "fieldtype": "Data",
            "label": "Field Name"
        },
        {
            "fieldname": "field_label",
            "fieldtype": "Data",
            "label": "Field Label"
        },
        {
            "fieldname": "field_type",
            "fieldtype": "Data",
            "label": "Field Type"
        },
        {
            "fieldname": "value",
            "fieldtype": "Small Text",
            "label": "Value"
        },
        {
            "fieldname": "value_date",
            "fieldtype": "Date",
            "label": "Value Date"
        },
        {
            "default": "0",
            "fieldname": "value_check",
            "fieldtype": "Check",
            "label": "Value Check"
        },
        {
            "fieldname": "attachment",
            "fieldtype": "Attach",
            "label": "Attachment"
        }
    ],
    "grid_page_length": 50,
    "index_web_pages_for_search": 0,
    "istable": 1,
    "links": [],
    "modified": "2026-06-08 00:00:00.000000",
    "modified_by": "Administrator",
    "module": "Onerc Compliance",
    "name": "Compliance Submission Value",
    "owner": "Administrator",
    "permissions": [],
    "row_format": "Dynamic",
    "sort_field": "creation",
    "sort_order": "DESC",
    "states": []
}
```

- [ ] **Step 3: Write compliance_submission_value.py**

```python
# Copyright (c) 2026, Kelvin Njenga and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class ComplianceSubmissionValue(Document):
    pass
```

---

## Task 4: Child doctype — Compliance Review Action

**Files:**
- Create: `onerc_compliance/onerc_compliance/doctype/compliance_review_action/__init__.py` (empty)
- Create: `onerc_compliance/onerc_compliance/doctype/compliance_review_action/compliance_review_action.json`
- Create: `onerc_compliance/onerc_compliance/doctype/compliance_review_action/compliance_review_action.py`

- [ ] **Step 1: Create directory and __init__.py**

```bash
mkdir -p /home/chetri/frappe/redHive/apps/onerc_compliance/onerc_compliance/onerc_compliance/doctype/compliance_review_action
touch /home/chetri/frappe/redHive/apps/onerc_compliance/onerc_compliance/onerc_compliance/doctype/compliance_review_action/__init__.py
```

- [ ] **Step 2: Write compliance_review_action.json**

```json
{
    "actions": [],
    "creation": "2026-06-08 00:00:00.000000",
    "doctype": "DocType",
    "editable_grid": 1,
    "engine": "InnoDB",
    "field_order": [
        "action",
        "reviewer",
        "action_on",
        "remarks"
    ],
    "fields": [
        {
            "fieldname": "action",
            "fieldtype": "Select",
            "in_list_view": 1,
            "label": "Action",
            "options": "Reviewed\nNeeds More Info\nRejected"
        },
        {
            "fieldname": "reviewer",
            "fieldtype": "Link",
            "in_list_view": 1,
            "label": "Reviewer",
            "options": "User",
            "read_only": 1
        },
        {
            "fieldname": "action_on",
            "fieldtype": "Datetime",
            "in_list_view": 1,
            "label": "Action On",
            "read_only": 1
        },
        {
            "fieldname": "remarks",
            "fieldtype": "Small Text",
            "label": "Remarks"
        }
    ],
    "grid_page_length": 50,
    "index_web_pages_for_search": 0,
    "istable": 1,
    "links": [],
    "modified": "2026-06-08 00:00:00.000000",
    "modified_by": "Administrator",
    "module": "Onerc Compliance",
    "name": "Compliance Review Action",
    "owner": "Administrator",
    "permissions": [],
    "row_format": "Dynamic",
    "sort_field": "creation",
    "sort_order": "DESC",
    "states": []
}
```

- [ ] **Step 3: Write compliance_review_action.py**

```python
# Copyright (c) 2026, Kelvin Njenga and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class ComplianceReviewAction(Document):
    pass
```

---

## Task 5: Update Compliance Requirement doctype JSON

**Files:**
- Modify: `onerc_compliance/onerc_compliance/doctype/compliance_requirement/compliance_requirement.json`

The existing file is a bare stub. Replace its entire contents.

- [ ] **Step 1: Overwrite compliance_requirement.json**

Write the following to `/home/chetri/frappe/redHive/apps/onerc_compliance/onerc_compliance/onerc_compliance/doctype/compliance_requirement/compliance_requirement.json`:

```json
{
    "actions": [],
    "allow_rename": 0,
    "autoname": "COMPLIANCE-.YYYY.-.####",
    "creation": "2026-06-08 00:00:00.000000",
    "doctype": "DocType",
    "engine": "InnoDB",
    "field_order": [
        "title",
        "description",
        "external_link",
        "section_targeting",
        "target_type",
        "target_departments",
        "section_schedule",
        "deadline",
        "requires_review",
        "reminder_lead_days",
        "reminder_repeat_days",
        "expected_headcount",
        "status",
        "section_fields",
        "fields"
    ],
    "fields": [
        {
            "fieldname": "title",
            "fieldtype": "Data",
            "in_list_view": 1,
            "label": "Title",
            "reqd": 1
        },
        {
            "fieldname": "description",
            "fieldtype": "Text Editor",
            "label": "Description"
        },
        {
            "fieldname": "external_link",
            "fieldtype": "Data",
            "label": "External Link"
        },
        {
            "fieldname": "section_targeting",
            "fieldtype": "Section Break",
            "label": "Targeting"
        },
        {
            "default": "All Staff",
            "fieldname": "target_type",
            "fieldtype": "Select",
            "in_list_view": 1,
            "label": "Target Type",
            "options": "All Staff\nBy Department",
            "reqd": 1
        },
        {
            "depends_on": "eval:doc.target_type==\"By Department\"",
            "fieldname": "target_departments",
            "fieldtype": "Table MultiSelect",
            "label": "Target Departments",
            "options": "Compliance Target Department"
        },
        {
            "fieldname": "section_schedule",
            "fieldtype": "Section Break",
            "label": "Schedule"
        },
        {
            "fieldname": "deadline",
            "fieldtype": "Datetime",
            "in_list_view": 1,
            "label": "Deadline",
            "reqd": 1
        },
        {
            "default": "1",
            "fieldname": "requires_review",
            "fieldtype": "Check",
            "label": "Requires Review"
        },
        {
            "default": "7",
            "fieldname": "reminder_lead_days",
            "fieldtype": "Int",
            "label": "Reminder Lead Days"
        },
        {
            "default": "2",
            "fieldname": "reminder_repeat_days",
            "fieldtype": "Int",
            "label": "Reminder Repeat Days"
        },
        {
            "fieldname": "expected_headcount",
            "fieldtype": "Int",
            "label": "Expected Headcount"
        },
        {
            "default": "Draft",
            "fieldname": "status",
            "fieldtype": "Select",
            "in_list_view": 1,
            "label": "Status",
            "options": "Draft\nActive\nClosed"
        },
        {
            "fieldname": "section_fields",
            "fieldtype": "Section Break",
            "label": "Form Fields"
        },
        {
            "fieldname": "fields",
            "fieldtype": "Table",
            "label": "Fields",
            "options": "Compliance Requirement Field"
        }
    ],
    "grid_page_length": 50,
    "index_web_pages_for_search": 1,
    "links": [],
    "modified": "2026-06-08 00:00:00.000000",
    "modified_by": "Administrator",
    "module": "Onerc Compliance",
    "name": "Compliance Requirement",
    "owner": "Administrator",
    "permissions": [
        {
            "create": 1,
            "delete": 1,
            "email": 1,
            "export": 1,
            "print": 1,
            "read": 1,
            "report": 1,
            "role": "Compliance Officer",
            "share": 1,
            "write": 1
        },
        {
            "read": 1,
            "role": "Employee"
        },
        {
            "create": 1,
            "delete": 1,
            "email": 1,
            "export": 1,
            "print": 1,
            "read": 1,
            "report": 1,
            "role": "System Manager",
            "share": 1,
            "write": 1
        }
    ],
    "row_format": "Dynamic",
    "rows_threshold_for_grid_search": 20,
    "sort_field": "creation",
    "sort_order": "DESC",
    "states": []
}
```

---

## Task 6: Compliance Submission doctype

**Files:**
- Create: `onerc_compliance/onerc_compliance/doctype/compliance_submission/__init__.py` (empty)
- Create: `onerc_compliance/onerc_compliance/doctype/compliance_submission/compliance_submission.json`
- Create: `onerc_compliance/onerc_compliance/doctype/compliance_submission/compliance_submission.py` (stub — controller logic comes in Task 10)

- [ ] **Step 1: Create directory and __init__.py**

```bash
mkdir -p /home/chetri/frappe/redHive/apps/onerc_compliance/onerc_compliance/onerc_compliance/doctype/compliance_submission
touch /home/chetri/frappe/redHive/apps/onerc_compliance/onerc_compliance/onerc_compliance/doctype/compliance_submission/__init__.py
```

- [ ] **Step 2: Write compliance_submission.json**

```json
{
    "actions": [],
    "allow_rename": 0,
    "autoname": "COMP-SUB-.####",
    "creation": "2026-06-08 00:00:00.000000",
    "doctype": "DocType",
    "engine": "InnoDB",
    "field_order": [
        "requirement",
        "employee",
        "employee_name",
        "department",
        "designation",
        "status",
        "submitted_on",
        "last_reminded_on",
        "section_values",
        "values",
        "section_review",
        "review_actions"
    ],
    "fields": [
        {
            "fieldname": "requirement",
            "fieldtype": "Link",
            "in_list_view": 1,
            "label": "Requirement",
            "options": "Compliance Requirement",
            "reqd": 1
        },
        {
            "fieldname": "employee",
            "fieldtype": "Link",
            "in_list_view": 1,
            "label": "Employee",
            "options": "Employee",
            "reqd": 1
        },
        {
            "fieldname": "employee_name",
            "fieldtype": "Data",
            "label": "Employee Name",
            "read_only": 1
        },
        {
            "fieldname": "department",
            "fieldtype": "Link",
            "label": "Department",
            "options": "Department"
        },
        {
            "fieldname": "designation",
            "fieldtype": "Link",
            "label": "Designation",
            "options": "Designation"
        },
        {
            "default": "Pending",
            "fieldname": "status",
            "fieldtype": "Select",
            "in_list_view": 1,
            "label": "Status",
            "options": "Pending\nSubmitted\nNeeds More Info\nReviewed\nRejected\nOverdue\nExempted"
        },
        {
            "fieldname": "submitted_on",
            "fieldtype": "Datetime",
            "label": "Submitted On",
            "read_only": 1
        },
        {
            "fieldname": "last_reminded_on",
            "fieldtype": "Date",
            "label": "Last Reminded On",
            "read_only": 1
        },
        {
            "fieldname": "section_values",
            "fieldtype": "Section Break",
            "label": "Answers"
        },
        {
            "fieldname": "values",
            "fieldtype": "Table",
            "label": "Values",
            "options": "Compliance Submission Value"
        },
        {
            "fieldname": "section_review",
            "fieldtype": "Section Break",
            "label": "Review"
        },
        {
            "fieldname": "review_actions",
            "fieldtype": "Table",
            "label": "Review Actions",
            "options": "Compliance Review Action"
        }
    ],
    "grid_page_length": 50,
    "index_web_pages_for_search": 1,
    "links": [],
    "modified": "2026-06-08 00:00:00.000000",
    "modified_by": "Administrator",
    "module": "Onerc Compliance",
    "name": "Compliance Submission",
    "owner": "Administrator",
    "permissions": [
        {
            "email": 1,
            "export": 1,
            "print": 1,
            "read": 1,
            "report": 1,
            "role": "Compliance Officer",
            "share": 1,
            "write": 1
        },
        {
            "read": 1,
            "role": "Employee"
        },
        {
            "create": 1,
            "delete": 1,
            "email": 1,
            "export": 1,
            "print": 1,
            "read": 1,
            "report": 1,
            "role": "System Manager",
            "share": 1,
            "write": 1
        }
    ],
    "row_format": "Dynamic",
    "rows_threshold_for_grid_search": 20,
    "sort_field": "creation",
    "sort_order": "DESC",
    "states": []
}
```

- [ ] **Step 3: Write compliance_submission.py (stub)**

```python
# Copyright (c) 2026, Kelvin Njenga and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class ComplianceSubmission(Document):
    pass
```

---

## Task 7: utils.py — shared utility functions

**Files:**
- Create: `onerc_compliance/onerc_compliance/utils.py`

- [ ] **Step 1: Write utils.py**

```python
# Copyright (c) 2026, Kelvin Njenga and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def get_employee_for_user(user=None):
    if not user:
        user = frappe.session.user
    return frappe.db.get_value("Employee", {"user_id": user}, "name")


def employee_in_scope(requirement, employee):
    if requirement.target_type == "All Staff":
        return True
    dept_names = [row.department for row in requirement.target_departments]
    emp_dept = frappe.db.get_value("Employee", employee, "department")
    return emp_dept in dept_names


def get_in_scope_employees(requirement):
    if requirement.target_type == "All Staff":
        rows = frappe.get_all("Employee", filters={"status": "Active"}, fields=["name"])
        result = []
        for row in rows:
            result.append(row.name)
        return result

    dept_names = []
    for row in requirement.target_departments:
        dept_names.append(row.department)

    seen = set()
    result = []
    for dept in dept_names:
        rows = frappe.get_all(
            "Employee",
            filters={"status": "Active", "department": dept},
            fields=["name"],
        )
        for row in rows:
            if row.name not in seen:
                seen.add(row.name)
                result.append(row.name)
    return result


def ensure_submission(requirement_name, employee_name):
    existing = frappe.db.get_value(
        "Compliance Submission",
        {"requirement": requirement_name, "employee": employee_name},
        "name",
    )
    if existing:
        return existing

    emp_data = frappe.db.get_value(
        "Employee",
        employee_name,
        ["employee_name", "department", "designation"],
        as_dict=True,
    )
    doc = frappe.get_doc(
        {
            "doctype": "Compliance Submission",
            "requirement": requirement_name,
            "employee": employee_name,
            "employee_name": (emp_data.get("employee_name") or "") if emp_data else "",
            "department": (emp_data.get("department") or "") if emp_data else "",
            "designation": (emp_data.get("designation") or "") if emp_data else "",
            "status": "Pending",
        }
    )
    doc.insert(ignore_permissions=True)
    return doc.name


def bulk_ensure_submissions(requirement_name, employee_names):
    for emp in employee_names:
        ensure_submission(requirement_name, emp)
        frappe.db.commit()
```

---

## Task 8: permissions.py — row-level permission functions

**Files:**
- Create: `onerc_compliance/onerc_compliance/permissions.py`

- [ ] **Step 1: Write permissions.py**

```python
# Copyright (c) 2026, Kelvin Njenga and contributors
# For license information, please see license.txt

import frappe


def submission_query_conditions(user=None):
    if not user:
        user = frappe.session.user

    if frappe.has_role("Compliance Officer", user) or frappe.has_role("System Manager", user):
        return ""

    employee = frappe.db.get_value("Employee", {"user_id": user}, "name")
    if not employee:
        return "1=0"

    return f"`tabCompliance Submission`.`employee` = {frappe.db.escape(employee)}"


def has_submission_permission(doc, user=None, permission_type=None):
    if not user:
        user = frappe.session.user

    if frappe.has_role("Compliance Officer", user) or frappe.has_role("System Manager", user):
        return True

    employee = frappe.db.get_value("Employee", {"user_id": user}, "name")
    if not employee:
        return False

    return doc.employee == employee
```

---

## Task 9: Compliance Requirement controller

**Files:**
- Modify: `onerc_compliance/onerc_compliance/doctype/compliance_requirement/compliance_requirement.py`

- [ ] **Step 1: Write the full controller**

```python
# Copyright (c) 2026, Kelvin Njenga and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class ComplianceRequirement(Document):
    def validate(self):
        # Capture previous status before any changes are written
        if not self.is_new():
            self._prev_status = frappe.db.get_value(
                "Compliance Requirement", self.name, "status"
            ) or "Draft"
        else:
            self._prev_status = "Draft"

        self._validate_fields()
        self._validate_targeting()
        self._validate_schema_freeze()

    def on_update(self):
        if self.status == "Active" and self._prev_status != "Active":
            self._generate_submissions()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _validate_fields(self):
        seen_names = {}
        for row in self.fields:
            if not row.label:
                frappe.throw(_("Every field row must have a label."))

            if not row.fieldname:
                row.fieldname = frappe.scrub(row.label)

            # Make fieldnames unique within the form
            base = row.fieldname
            count = seen_names.get(base, 0) + 1
            seen_names[base] = count
            if count > 1:
                row.fieldname = f"{base}_{count}"
            else:
                seen_names[base] = 1

            if row.fieldtype == "Select" and not (row.options or "").strip():
                frappe.throw(
                    _("Field '{0}' is of type Select and must have Options.").format(row.label)
                )

    def _validate_targeting(self):
        if self.target_type == "By Department":
            if not self.target_departments:
                frappe.throw(_("At least one target department is required for 'By Department' targeting."))

    def _make_fields_signature(self, fields):
        result = []
        for row in fields:
            result.append((
                row.fieldname or "",
                row.fieldtype or "",
                row.label or "",
                row.options or "",
                int(row.mandatory or 0),
            ))
        return result

    def _validate_schema_freeze(self):
        if self.is_new():
            return
        if self._prev_status not in ("Active", "Closed"):
            return

        old_doc = frappe.get_doc("Compliance Requirement", self.name)
        old_sig = self._make_fields_signature(old_doc.fields)
        new_sig = self._make_fields_signature(self.fields)

        if old_sig != new_sig:
            frappe.throw(
                _("The field schema cannot be changed once the requirement is Active or Closed.")
            )

    def _generate_submissions(self):
        from onerc_compliance.utils import bulk_ensure_submissions, get_in_scope_employees

        employees = get_in_scope_employees(self)

        if len(employees) > 200:
            frappe.enqueue(
                "onerc_compliance.utils.bulk_ensure_submissions",
                queue="long",
                requirement_name=self.name,
                employee_names=employees,
            )
        else:
            for emp in employees:
                from onerc_compliance.utils import ensure_submission
                ensure_submission(self.name, emp)
```

---

## Task 10: Compliance Submission controller

**Files:**
- Modify: `onerc_compliance/onerc_compliance/doctype/compliance_submission/compliance_submission.py`

- [ ] **Step 1: Write the full controller**

```python
# Copyright (c) 2026, Kelvin Njenga and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import now_datetime
from frappe.model.document import Document


ALLOWED_TRANSITIONS = {
    "Pending": {"Submitted", "Exempted", "Overdue"},
    "Submitted": {"Reviewed", "Needs More Info", "Rejected"},
    "Needs More Info": {"Submitted", "Overdue"},
    "Rejected": {"Submitted"},
    "Overdue": {"Submitted"},
    "Reviewed": set(),
    "Exempted": set(),
}


class ComplianceSubmission(Document):
    def validate(self):
        # Capture previous status before DB is updated
        if not self.is_new():
            self._prev_status = frappe.db.get_value(
                "Compliance Submission", self.name, "status"
            ) or "Pending"
        else:
            self._prev_status = "Pending"

        self._enforce_unique_per_pair()
        self._enforce_transition()
        self._validate_review_remarks()
        self._validate_submitted_values()

    def on_update(self):
        notify_statuses = {"Reviewed", "Needs More Info", "Rejected"}
        if self.status in notify_statuses and self._prev_status != self.status:
            self._email_employee()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _enforce_unique_per_pair(self):
        if self.is_new():
            existing = frappe.db.get_value(
                "Compliance Submission",
                {"requirement": self.requirement, "employee": self.employee},
                "name",
            )
            if existing:
                frappe.throw(
                    _("A submission already exists for employee {0} on requirement {1}.").format(
                        self.employee, self.requirement
                    )
                )
        else:
            existing = frappe.db.get_value(
                "Compliance Submission",
                {
                    "requirement": self.requirement,
                    "employee": self.employee,
                    "name": ["!=", self.name],
                },
                "name",
            )
            if existing:
                frappe.throw(
                    _("A submission already exists for employee {0} on requirement {1}.").format(
                        self.employee, self.requirement
                    )
                )

    def _enforce_transition(self):
        if self.is_new():
            return
        allowed = ALLOWED_TRANSITIONS.get(self._prev_status, set())
        if self.status != self._prev_status and self.status not in allowed:
            frappe.throw(
                _("Cannot transition from '{0}' to '{1}'.").format(
                    self._prev_status, self.status
                )
            )

    def _validate_review_remarks(self):
        for row in self.review_actions:
            if row.action in ("Needs More Info", "Rejected") and not (row.remarks or "").strip():
                frappe.throw(
                    _("Remarks are required when action is '{0}'.").format(row.action)
                )

    def _validate_submitted_values(self):
        if self.status != "Submitted":
            return

        req = frappe.get_doc("Compliance Requirement", self.requirement)
        mandatory_fieldnames = set()
        for schema_field in req.fields:
            if schema_field.mandatory:
                mandatory_fieldnames.add(schema_field.fieldname)

        if not mandatory_fieldnames:
            if not self.submitted_on:
                self.submitted_on = now_datetime()
            return

        # Build a lookup of answers
        answers = {}
        for val_row in self.values:
            answers[val_row.field_name] = val_row

        for fname in mandatory_fieldnames:
            row = answers.get(fname)
            schema_field = next(
                (f for f in req.fields if f.fieldname == fname), None
            )
            if not schema_field:
                continue

            blank = True
            if row:
                if schema_field.fieldtype == "Check":
                    blank = not int(row.value_check or 0)
                elif schema_field.fieldtype == "Date":
                    blank = not row.value_date
                elif schema_field.fieldtype == "Attach":
                    blank = not row.attachment
                else:
                    blank = not (row.value or "").strip()

            if blank:
                frappe.throw(
                    _("Mandatory field '{0}' has no answer.").format(
                        schema_field.label or fname
                    )
                )

        if not self.submitted_on:
            self.submitted_on = now_datetime()

    def _email_employee(self):
        emp = frappe.db.get_value(
            "Employee",
            self.employee,
            ["company_email", "user_id"],
            as_dict=True,
        )
        if not emp:
            return

        email = emp.company_email or emp.user_id
        if not email:
            return

        latest_remark = ""
        for row in reversed(self.review_actions):
            if row.remarks:
                latest_remark = row.remarks
                break

        subject = _("Compliance submission status updated: {0}").format(self.status)
        message_parts = [
            _("Your compliance submission {0} has been updated to: {1}.").format(
                self.name, self.status
            )
        ]
        if latest_remark:
            message_parts.append(_("Reviewer note: {0}").format(latest_remark))

        frappe.sendmail(
            recipients=[email],
            subject=subject,
            message="<br>".join(message_parts),
            now=True,
        )
```

---

## Task 11: tasks.py — scheduled jobs

**Files:**
- Create: `onerc_compliance/onerc_compliance/tasks.py`

- [ ] **Step 1: Write tasks.py**

```python
# Copyright (c) 2026, Kelvin Njenga and contributors
# For license information, please see license.txt

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
        lead_date = add_days(deadline_date, -lead_days)

        if today_date < getdate(lead_date):
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

        cutoff = add_days(today_date, -repeat_days)

        for sub in submissions:
            if sub.last_reminded_on:
                last = getdate(sub.last_reminded_on)
                if last >= getdate(cutoff):
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
```

---

## Task 12: API — api/v1/compliance.py

**Files:**
- Create: `onerc_compliance/onerc_compliance/api/__init__.py` (empty)
- Create: `onerc_compliance/onerc_compliance/api/v1/__init__.py` (empty)
- Create: `onerc_compliance/onerc_compliance/api/v1/compliance.py`

- [ ] **Step 1: Create directories and empty __init__.py files**

```bash
mkdir -p /home/chetri/frappe/redHive/apps/onerc_compliance/onerc_compliance/api/v1
touch /home/chetri/frappe/redHive/apps/onerc_compliance/onerc_compliance/api/__init__.py
touch /home/chetri/frappe/redHive/apps/onerc_compliance/onerc_compliance/api/v1/__init__.py
```

- [ ] **Step 2: Write api/v1/compliance.py**

```python
# Copyright (c) 2026, Kelvin Njenga and contributors
# For license information, please see license.txt

import json

import frappe
from frappe import _
from frappe.utils import now_datetime

from onerc_compliance.utils import employee_in_scope, ensure_submission, get_employee_for_user


def _ok(data, message="", meta=None):
    return {"status": "success", "data": data, "message": message, "meta": meta or {}}


def _err(message, data=None):
    return {"status": "error", "data": data or {}, "message": message, "meta": {}}


@frappe.whitelist()
def get_my_requirements():
    employee_name = get_employee_for_user()
    if not employee_name:
        return _err(_("No employee record linked to your account."))

    requirements = frappe.get_all(
        "Compliance Requirement",
        filters={"status": "Active"},
        fields=["name", "title", "description", "external_link", "deadline", "target_type"],
    )

    result = []
    for req in requirements:
        req_doc = frappe.get_doc("Compliance Requirement", req.name)

        if not employee_in_scope(req_doc, employee_name):
            continue

        submission_name = ensure_submission(req.name, employee_name)
        sub = frappe.db.get_value(
            "Compliance Submission", submission_name, ["status", "name"], as_dict=True
        )

        field_schema = []
        for f in req_doc.fields:
            options_list = []
            if f.fieldtype == "Select" and f.options:
                options_list = [o.strip() for o in f.options.split("\n") if o.strip()]
            field_schema.append({
                "fieldname": f.fieldname,
                "label": f.label,
                "fieldtype": f.fieldtype,
                "options": options_list,
                "mandatory": bool(f.mandatory),
                "description": f.description or "",
            })

        # Existing answers keyed by field_name
        answers = {}
        sub_doc = frappe.get_doc("Compliance Submission", submission_name)
        for val in sub_doc.values:
            answers[val.field_name] = {
                "value": val.value,
                "value_date": str(val.value_date) if val.value_date else None,
                "value_check": bool(val.value_check),
                "attachment": val.attachment,
            }

        result.append({
            "requirement": req.name,
            "title": req.title,
            "description": req.description,
            "external_link": req.external_link,
            "deadline": str(req.deadline) if req.deadline else None,
            "field_schema": field_schema,
            "submission_status": sub.status if sub else "Pending",
            "answers": answers,
        })

    return _ok(result)


@frappe.whitelist()
def submit_requirement(requirement, answers):
    if isinstance(answers, str):
        answers = json.loads(answers)

    req_doc = frappe.get_doc("Compliance Requirement", requirement)
    if req_doc.status != "Active":
        return _err(_("This requirement is no longer active."))

    employee_name = get_employee_for_user()
    if not employee_name:
        return _err(_("No employee record linked to your account."))

    submission_name = ensure_submission(requirement, employee_name)
    sub = frappe.get_doc("Compliance Submission", submission_name)

    if sub.status not in ("Pending", "Needs More Info"):
        return _err(
            _("Submission is in status '{0}' and cannot be re-submitted.").format(sub.status)
        )

    # Rebuild values child table from the schema
    sub.values = []
    for schema_field in req_doc.fields:
        fname = schema_field.fieldname
        raw = answers.get(fname)
        row = {
            "field_name": fname,
            "field_label": schema_field.label or fname,
            "field_type": schema_field.fieldtype,
        }
        if schema_field.fieldtype == "Check":
            row["value_check"] = 1 if raw else 0
        elif schema_field.fieldtype == "Date":
            row["value_date"] = raw or None
        elif schema_field.fieldtype == "Attach":
            row["attachment"] = raw or None
        else:
            row["value"] = str(raw) if raw is not None else ""
        sub.append("values", row)

    sub.status = "Submitted"
    sub.save(ignore_permissions=True)

    return _ok({"submission": sub.name, "status": sub.status})


@frappe.whitelist()
def review_submission(submission, action, remarks=None):
    frappe.has_permission("Compliance Submission", doc=submission, ptype="write", throw=True)

    allowed_actions = {"Reviewed", "Needs More Info", "Rejected"}
    if action not in allowed_actions:
        return _err(_("Invalid action. Must be one of: Reviewed, Needs More Info, Rejected."))

    if action in ("Needs More Info", "Rejected") and not (remarks or "").strip():
        return _err(_("Remarks are required for action '{0}'.").format(action))

    sub = frappe.get_doc("Compliance Submission", submission)
    if sub.status != "Submitted":
        return _err(
            _("Only submissions in 'Submitted' status can be reviewed. Current status: {0}.").format(
                sub.status
            )
        )

    sub.append(
        "review_actions",
        {
            "action": action,
            "reviewer": frappe.session.user,
            "action_on": now_datetime(),
            "remarks": remarks or "",
        },
    )
    sub.status = action
    sub.save(ignore_permissions=True)

    return _ok({"submission": sub.name, "status": sub.status})


@frappe.whitelist()
def get_dashboard(requirement):
    frappe.has_permission("Compliance Requirement", doc=requirement, ptype="read", throw=True)

    req_doc = frappe.get_doc("Compliance Requirement", requirement)

    submissions = frappe.get_all(
        "Compliance Submission",
        filters={"requirement": requirement},
        fields=["name", "status", "department"],
    )

    status_counts = {}
    dept_map = {}

    for sub in submissions:
        # Status counts
        status_counts[sub.status] = status_counts.get(sub.status, 0) + 1

        # Per-department breakdown
        dept = sub.department or "Unassigned"
        if dept not in dept_map:
            dept_map[dept] = {"department": dept, "reviewed": 0, "total": 0}
        dept_map[dept]["total"] += 1
        if sub.status == "Reviewed":
            dept_map[dept]["reviewed"] += 1

    reviewed_count = status_counts.get("Reviewed", 0)
    known_total = len(submissions)
    expected = req_doc.expected_headcount or 0
    denominator = expected if expected else known_total
    completion_percent = round((reviewed_count / denominator) * 100, 2) if denominator else 0.0

    return _ok({
        "requirement": requirement,
        "status_counts": status_counts,
        "by_department": list(dept_map.values()),
        "reviewed_count": reviewed_count,
        "known_total": known_total,
        "expected_headcount": expected,
        "completion_percent": completion_percent,
    })
```

---

## Task 13: Update hooks.py — wire everything together

**Files:**
- Modify: `onerc_compliance/onerc_compliance/hooks.py`

- [ ] **Step 1: Replace hooks.py with the complete version**

Open `/home/chetri/frappe/redHive/apps/onerc_compliance/onerc_compliance/hooks.py` and replace its entire contents with:

```python
app_name = "onerc_compliance"
app_title = "Onerc Compliance"
app_publisher = "Kelvin Njenga"
app_description = "OneRC Compliance"
app_email = "njengasheba@gmail.com"
app_license = "mit"

scheduler_events = {
    "daily": [
        "onerc_compliance.tasks.close_expired_requirements",
        "onerc_compliance.tasks.send_compliance_reminders",
    ]
}

permission_query_conditions = {
    "Compliance Submission": "onerc_compliance.permissions.submission_query_conditions",
}

has_permission = {
    "Compliance Submission": "onerc_compliance.permissions.has_submission_permission",
}

fixtures = [
    {
        "dt": "Role",
        "filters": [["role_name", "in", ["Compliance Officer"]]],
    }
]
```

---

## Task 14: Tests

**Files:**
- Modify: `onerc_compliance/onerc_compliance/doctype/compliance_requirement/test_compliance_requirement.py`
- Create: `onerc_compliance/onerc_compliance/doctype/compliance_submission/test_compliance_submission.py`

- [ ] **Step 1: Write test_compliance_requirement.py**

```python
# Copyright (c) 2026, Kelvin Njenga and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase

EXTRA_TEST_RECORD_DEPENDENCIES = []
IGNORE_TEST_RECORD_DEPENDENCIES = []


class IntegrationTestComplianceRequirement(IntegrationTestCase):
    def setUp(self):
        frappe.db.delete(
            "Compliance Requirement", {"title": ["like", "_test-%"]}
        )

    def tearDown(self):
        frappe.db.delete(
            "Compliance Requirement", {"title": ["like", "_test-%"]}
        )

    def _make_requirement(self, title="_test-req", status="Draft", target_type="All Staff", fields=None):
        doc = frappe.get_doc({
            "doctype": "Compliance Requirement",
            "title": title,
            "target_type": target_type,
            "deadline": "2099-12-31 23:59:00",
            "status": status,
            "fields": fields or [],
        })
        doc.insert(ignore_permissions=True)
        return doc

    def test_valid_creation(self):
        doc = self._make_requirement(title="_test-req-valid")
        self.assertTrue(frappe.db.exists("Compliance Requirement", doc.name))

    def test_schema_freeze_raises_when_active(self):
        doc = self._make_requirement(
            title="_test-req-freeze",
            fields=[{
                "label": "Agree",
                "fieldtype": "Check",
                "mandatory": 0,
            }],
        )
        doc.status = "Active"
        doc.save(ignore_permissions=True)

        # Reload and try to change the field schema
        doc.reload()
        original_label = doc.fields[0].label
        doc.fields[0].label = "Agree Updated"
        doc.fields[0].fieldname = frappe.scrub("Agree Updated")

        with self.assertRaises(frappe.ValidationError):
            doc.save(ignore_permissions=True)

        # Restore
        doc.reload()
        self.assertEqual(doc.fields[0].label, original_label)
```

- [ ] **Step 2: Write test_compliance_submission.py**

```python
# Copyright (c) 2026, Kelvin Njenga and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import now_datetime

EXTRA_TEST_RECORD_DEPENDENCIES = []
IGNORE_TEST_RECORD_DEPENDENCIES = []


class IntegrationTestComplianceSubmission(IntegrationTestCase):
    def setUp(self):
        frappe.db.delete("Compliance Submission", {"requirement": ["like", "COMPLIANCE-%_test%"]})
        frappe.db.delete("Compliance Requirement", {"title": ["like", "_test-%"]})

    def tearDown(self):
        frappe.db.delete("Compliance Submission", {"requirement": ["like", "COMPLIANCE-%_test%"]})
        frappe.db.delete("Compliance Requirement", {"title": ["like", "_test-%"]})

    def _make_requirement(self, title="_test-sub-req", fields=None):
        doc = frappe.get_doc({
            "doctype": "Compliance Requirement",
            "title": title,
            "target_type": "All Staff",
            "deadline": "2099-12-31 23:59:00",
            "status": "Active",
            "fields": fields or [],
        })
        doc.insert(ignore_permissions=True)
        return doc

    def _make_employee(self, suffix="sub-test"):
        emp_name = f"_test-emp-{suffix}"
        if not frappe.db.exists("Employee", {"employee_name": emp_name}):
            emp = frappe.get_doc({
                "doctype": "Employee",
                "first_name": emp_name,
                "employee_name": emp_name,
                "status": "Active",
                "gender": "Male",
                "date_of_birth": "1990-01-01",
                "date_of_joining": "2020-01-01",
                "company": frappe.defaults.get_defaults().get("company") or "_Test Company",
            })
            emp.insert(ignore_permissions=True)
            return emp.name
        return frappe.db.get_value("Employee", {"employee_name": emp_name}, "name")

    def _make_submission(self, requirement_name, employee_name, status="Pending"):
        doc = frappe.get_doc({
            "doctype": "Compliance Submission",
            "requirement": requirement_name,
            "employee": employee_name,
            "status": status,
        })
        doc.insert(ignore_permissions=True)
        return doc

    def test_valid_creation(self):
        req = self._make_requirement()
        emp = self._make_employee()
        sub = self._make_submission(req.name, emp)
        self.assertTrue(frappe.db.exists("Compliance Submission", sub.name))
        self.assertEqual(sub.status, "Pending")

    def test_submit_with_blank_mandatory_field_raises(self):
        req = self._make_requirement(
            fields=[{
                "label": "Full Name",
                "fieldtype": "Data",
                "mandatory": 1,
            }]
        )
        emp = self._make_employee(suffix="mandatory-test")
        sub = self._make_submission(req.name, emp)

        sub.reload()
        sub.status = "Submitted"
        # values table is empty — mandatory field has no answer

        with self.assertRaises(frappe.ValidationError):
            sub.save(ignore_permissions=True)
```

---

## Task 15: bench migrate

- [ ] **Step 1: Run migrate**

```bash
cd /home/chetri/frappe/redHive && bench --site onerc.localhost migrate
```

Expected: migration completes without errors. All six new/updated doctypes should appear in the output.

- [ ] **Step 2: Verify doctypes exist on site**

```bash
cd /home/chetri/frappe/redHive && bench --site onerc.localhost execute frappe.db.exists --args "['DocType', 'Compliance Submission']"
```

Expected output: `Compliance Submission`

---

## Task 16: Run tests

- [ ] **Step 1: Run the test suite**

```bash
cd /home/chetri/frappe/redHive && bench --site onerc.localhost run-tests --app onerc_compliance
```

Expected: all tests pass. If any test fails due to a missing Employee test fixture (the company default), check available companies with:

```bash
cd /home/chetri/frappe/redHive && bench --site onerc.localhost execute frappe.db.sql --args "\"SELECT name FROM tabCompany LIMIT 3\""
```

Then update the `_make_employee` helper in `test_compliance_submission.py` to use that company name.

---

## Spec Coverage Checklist

| Spec Section | Covered In |
|---|---|
| Role: Compliance Officer | Task 1 |
| Child: Compliance Requirement Field | Pre-existing (correct) |
| Child: Compliance Target Department | Task 2 |
| Child: Compliance Submission Value | Task 3 |
| Child: Compliance Review Action | Task 4 |
| Compliance Requirement doctype + permissions | Task 5 |
| Compliance Submission doctype + permissions | Task 6 |
| utils: get_employee_for_user | Task 7 |
| utils: employee_in_scope | Task 7 |
| utils: get_in_scope_employees | Task 7 |
| utils: ensure_submission (snapshot employee data) | Task 7 |
| utils: bulk_ensure_submissions | Task 7 |
| permissions: submission_query_conditions | Task 8 |
| permissions: has_submission_permission | Task 8 |
| Requirement controller: fieldname auto-fill + uniqueness | Task 9 |
| Requirement controller: schema freeze Active/Closed | Task 9 |
| Requirement controller: on_update → generate submissions | Task 9 |
| Submission controller: unique per (req, emp) | Task 10 |
| Submission controller: status transitions | Task 10 |
| Submission controller: review remarks required | Task 10 |
| Submission controller: mandatory field check on Submit | Task 10 |
| Submission controller: email on review status change | Task 10 |
| tasks: close_expired_requirements | Task 11 |
| tasks: send_compliance_reminders | Task 11 |
| API: get_my_requirements | Task 12 |
| API: submit_requirement | Task 12 |
| API: review_submission | Task 12 |
| API: get_dashboard | Task 12 |
| hooks: scheduler_events daily | Task 13 |
| hooks: permission_query_conditions | Task 13 |
| hooks: has_permission | Task 13 |
| Tests: valid creation (Requirement) | Task 14 |
| Tests: schema freeze (Requirement) | Task 14 |
| Tests: valid creation (Submission) | Task 14 |
| Tests: blank mandatory field raises (Submission) | Task 14 |
| bench migrate | Task 15 |
| bench run-tests | Task 16 |
