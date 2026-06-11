# Onerc Incident Management (ITSM)

IT Service Management for KRCS, built inside the `onerc_compliance` app. Runs **Incidents**,
**Service Requests**, and **Remote Support** on a **business-hours SLA engine**, and syncs with
**Frappe Helpdesk**. All ITSM doctypes live in the single `Onerc Incident Management` module
(see `docs/adr/0001`). People are Frappe **Users** — no HRMS (see `docs/adr/0002`).

## Headlines
- **Priority is never typed** — it is derived from **Impact × Urgency** via `Onerc Priority Matrix`.
- **SLA timers respect business hours** — they skip nights, weekends and Kenyan holidays, and
  **pause** while a record waits on someone.
- **Engine vs. config** — the engine is national-society-neutral; every KRCS/Kenya value is a
  seeded record (`seed_krcs.py`), never hardcoded.

## Quick setup
```bash
bench --site <site> migrate
# engine: roles, role profiles, notifications, workflows, ITSM workspace
bench --site <site> execute onerc_compliance.onerc_incident_management.install.setup_itsm
# KRCS config: priorities, matrix, Kenya calendar, services, teams, SLA, catalogue
bench --site <site> execute onerc_compliance.onerc_incident_management.seed_krcs.seed
```
Then open the **ITSM** workspace in Desk.

## The doctypes
**Foundation:** Onerc Incidents Settings (single), Onerc Business Calendar (+ Holiday),
Onerc SLA Policy (+ Escalation Step), Onerc Service / Service Category, Onerc Support Team
(+ Member), Onerc Impact / Urgency / Priority, Onerc Priority Matrix, Onerc Data
Classification, Onerc SLA Escalation Event (log).
**Incident:** Onerc Incident (`INC-.YYYY.-.#####`) + Onerc Incident Activity.
**Service Request:** Onerc Request Catalogue Item, Onerc Service Request
(`SR-.YYYY.-.#####`) + Onerc Service Request Approval.
**Configuration Item:** Onerc Configuration Item.
**Remote Support:** Onerc Remote Support Session (`RS-.YYYY.-.#####`), Onerc Remote Support
Settings (single).

## The SLA engine (`sla/`)
- `working_time.py` — `add_working_minutes(start, n, calendar)`: the single helper every
  deadline routes through (skips closed hours / weekends / holidays). Unit-tested without a DB.
- `policy.py` — resolve the most-specific SLA policy, stamp due dates, pause/resume.
- `escalation.py` — scheduled scan (every 10 min): flag breaches, fire escalations, email.

## Integrations
- **Helpdesk** (`helpdesk_sync.py`) — Incident `after_insert` creates an `HD Ticket`; on Resolved
  it is closed. Toggle: `sync_to_helpdesk`. The Incident is the source of truth. (PDF closure
  deferred to `onerc_storage`.)
- **Remote Support** (`remote_support.py`) — `start_session()` mints a provider token (provider
  swappable via settings) and emails the link; the provider `session_webhook()` closes the
  session and posts a work note. (SMS delivery deferred to `onerc_sms`.)

## Tests
```bash
bench --site <site> run-tests --module onerc_compliance.onerc_incident_management.sla.test_working_time
# plus: sla.test_policy, doctype.onerc_incident.test_onerc_incident,
#   doctype.onerc_service_request.test_onerc_service_request,
#   doctype.onerc_configuration_item.test_onerc_configuration_item,
#   doctype.onerc_remote_support_session.test_onerc_remote_support_session,
#   test_helpdesk_sync
```

## Deferred (Phase 2)
Branch-scoping permissions (needs `onerc_core`/Geo Node installed), PDF closure docs &
SMS delivery, the full Access Grant registry, full CMDB, and the ERPNext Asset link.
