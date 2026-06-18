# ADR 0002 — HRMS-free identity and a native Business Calendar

**Status:** Accepted · 2026-06-11

## Context
HRMS is not installed on the target deployment and will not be. Two things normally lean on
HRMS: (1) person references typically Link to **Employee**, and (2) SLA/working-time logic
typically counts against an HRMS **Holiday List**.

## Decision
1. **People are Frappe `User`s.** Every person field — `reported_by`, `requested_by`,
   `agent`, `target_user`, `assigned_to`, team members, approvers — Links to **`User`**.
   The Employee doctype is never referenced anywhere in the ITSM code.
2. **A native `Onerc Business Calendar`** (working days, business start/end time, and a
   holiday child table) replaces the HRMS Holiday List. The working-time engine
   (`sla/working_time.py`) counts against this calendar, not against HRMS.
3. **`branch_region` Links to onerc_core `Geo Node`** (not an HRMS department) for branch
   scoping; `department` is omitted entirely.

## Consequences
- The ITSM suite runs on a lean site with **no HRMS dependency**.
- The SLA engine is fully self-contained and unit-testable: `add_working_minutes()` takes a
  plain calendar object, so business-hours maths is verified without a database.
- KRCS/Kenya specifics (working hours, public holidays) are **config records** in the
  Business Calendar, not code — consistent with the engine-vs-config separation.

## Alternatives considered
- *Link to Employee / use HRMS Holiday List* — rejected outright per the deployment constraint.
- *Hardcode Kenyan holidays in the engine* — rejected; they live in the seeded calendar so the
  engine stays national-society-neutral.
