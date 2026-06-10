# OneRC Compliance

Staff compliance attestation tracker for Kenya Red Cross (OneRC ecosystem). Compliance Officers define requirements with dynamic forms; staff complete and submit them; officers review and sign off — all through a Vue 3 SPA served at `/compliance`.

---

## Prerequisites

| Dependency | Notes |
|---|---|
| Frappe v16+ | Tested on v17.x.x-develop |
| ERPNext | Required for Employee, Department, Designation doctypes |
| `onerc_core` | Role and site baseline for the OneRC ecosystem |
| `onerc_storage` | Optional — Attach fieldtype is used instead when absent |

## Installation

```bash
cd ~/frappe/<bench>
bench get-app https://github.com/<org>/onerc_compliance
bench --site <site> install-app onerc_compliance
bench --site <site> migrate
bench build --app onerc_compliance
```

## Configuration

**Outgoing email** — Status-change notifications (Reviewed, Needs More Info, Rejected) are queued via Frappe's Email Queue. Configure a default outgoing email account at *Tools > Email Account* and enable the scheduler (see Deployment Notes). If no account is configured the review still succeeds and a Frappe Error Log entry is written instead.

**Scheduler** — Two daily tasks depend on the scheduler being active:

```bash
bench --site <site> enable-scheduler
```

## Doctypes Introduced

| Doctype | Purpose |
|---|---|
| **Compliance Requirement** | Officer-defined attestation with a dynamic form schema and targeting rules (All Staff or By Department) |
| **Compliance Requirement Field** | Child table — one row per form field (Data, Check, Date, Select, Int, Float, Attach, Small Text) |
| **Compliance Target Department** | Child table — departments in scope when target_type = "By Department" |
| **Compliance Submission** | Per-employee instance of a requirement; tracks lifecycle from Pending → Submitted → Reviewed |
| **Compliance Submission Value** | Child table — one row per form-field answer |
| **Compliance Review Action** | Child table — audit trail of every review action (Reviewed / Needs More Info / Rejected) |

## API Reference

All endpoints live at `onerc_compliance.api.v1.compliance` and return `{"status": "success"|"error", "data": …, "message": …, "meta": {}}`.

| Endpoint | Auth | Description |
|---|---|---|
| `get_my_requirements` | Any Employee | Returns Active requirements in scope for the session user, with field schema, current answers, and submission status |
| `submit_requirement(requirement, answers)` | Any Employee | Creates or updates the employee's submission; moves status to Submitted (requires_review=1) or Reviewed (requires_review=0) |
| `review_submission(submission, action, remarks)` | Compliance Officer / System Manager | Records a review action and transitions status; remarks required for Needs More Info and Rejected |
| `get_submissions(requirement, status?)` | Compliance Officer / System Manager | Returns all submissions for a requirement, including answers and review history |
| `get_dashboard(requirement)` | Compliance Officer / System Manager | Aggregate stats — completion %, status counts, per-department breakdown |

## Demo Data

A self-contained demo dataset lets you explore both portals without manual data entry.

```bash
# Load (idempotent — safe to run multiple times)
bench --site <site> execute onerc_compliance.demo_data.load

# Remove everything the loader created
bench --site <site> execute onerc_compliance.demo_data.teardown
```

**Demo logins** (password for all: `Demo@1234`)

| Email | Role | Portal |
|---|---|---|
| `demo.alice@demo.local` | Employee — Operations | `/compliance` |
| `demo.bob@demo.local` | Employee — Operations | `/compliance` |
| `demo.carol@demo.local` | Employee — Human Resources | `/compliance` |
| `demo.dave@demo.local` | Employee — Human Resources | `/compliance` |
| `demo.officer@demo.local` | Compliance Officer | `/compliance/dashboard` |

**What gets created:**

* Two requirements with 90-day future deadlines and status Active (so submissions auto-generate for all in-scope employees):
  * *DEMO: Annual Policy Acknowledgement* — All Staff, `requires_review=1`, five field types: Check, Date, Select, Data, Attach
  * *DEMO: Operations Safety Compliance* — By Department (Operations), two fields: Check, Data
* Submission states spread across both requirements so the dashboard shows real data:
  * Alice → Submitted, Bob → Reviewed, Carol → Needs More Info (with reviewer note), Dave → Pending (Req 1)
  * Alice → Submitted, Bob → Pending (Req 2)

All records are namespaced (`@demo.local`, `DEMO: ` prefix) so `teardown()` is reliable and cannot accidentally remove real data.

## Running Tests

```bash
bench --site <site> run-tests --app onerc_compliance
```

Integration tests cover submission lifecycle, mandatory-field validation, no-review path, and permission gates (employee denied on officer-only endpoints, officer/SM permitted).

## Smoke Test

Runs a full functional round-trip in a live site context, then cleans up:

```bash
bench --site <site> execute onerc_compliance.onerc_compliance.smoke_test.run
```

Steps verified: employee creation, requirement activation, lazy submission creation, staff submit, permission denial check, officer get_submissions, get_dashboard, review_submission, DB state assertion, www page registration.

## Deployment Notes

- **Outgoing email account** — configure at least one default outgoing account for employee notifications to flow.
- **Scheduler** must be enabled for `close_expired_requirements` (marks requirements whose deadline has passed as Closed) and `send_compliance_reminders` (sends reminder emails to employees with Pending/Overdue submissions N days before deadline).
- **Frontend build** — the Vue 3 SPA is pre-built into `onerc_compliance/public/compliance/`. Running `bench build --app onerc_compliance` during installation is sufficient; no Node tooling needed in production.
- **SPA routing** — `website_route_rules` in `hooks.py` redirects all `/compliance/<path>` sub-paths to the index page so Vue Router handles client-side navigation.

## ADRs

- [ADR-001 — Dynamic Form Builder](docs/adr/ADR-001-dynamic-form-builder.md)
- [ADR-002 — Assignment Model](docs/adr/ADR-002-assignment-model.md)
