# ADR-002: Assignment Model — Eager Activation + Lazy First-Visit

**Status:** Accepted  
**Date:** 2026-06-08  
**Deciders:** Kelvin Njenga

---

## Context

Every Compliance Requirement must produce a Compliance Submission record for each employee in scope. These submissions are what officers track for completion — without them, the dashboard has nothing to count.

The challenge: at the time this app ships, Kenya Red Cross does not have a complete, authoritative staff roster in any system that `onerc_compliance` can pull from. ERPNext's Employee records exist but are incomplete — not every active staff member has an Employee record, and newly-onboarded staff may not appear for days after joining.

Three assignment strategies were considered:

1. **Fully eager** — generate submissions for all known employees the moment a requirement is activated; never create on-demand.
2. **Fully lazy** — generate a submission only when an employee first visits the `/compliance` page.
3. **Hybrid: eager activation + lazy first-visit** — generate submissions for all known employees at activation, and also create on first page visit if an employee was missed.

## Decision

Use the hybrid model: **eager on activation + lazy on first visit**.

- `Compliance Requirement.on_update`: when status transitions to Active, call `_generate_submissions` which creates a Pending submission for every in-scope employee in ERPNext (inline for ≤200 employees, enqueued for larger populations).
- `ensure_submission(requirement_name, employee_name)` in `utils.py`: called by `get_my_requirements`; idempotent — creates the submission if absent, returns existing name if present.

The `expected_headcount` field on `Compliance Requirement` gives officers an override for the denominator in completion-percentage calculations, independent of how many submissions exist.

## Rationale

**Why eager at activation?**  
Officers want an accurate picture immediately after activating a requirement. If the dashboard only showed employees who had visited, early-activating a requirement would show 0 completions until staff trickle in — creating false urgency or confusion about whether the requirement published successfully.

**Why lazy on first visit?**  
Staff who join after activation, or whose Employee records are created after the requirement goes live, should not be invisible to the compliance cycle. The lazy path in `ensure_submission` ensures they are captured the moment they log in.

**Why `expected_headcount`?**  
Because the number of ERPNext Employee records is not the same as the number of staff who need to comply. HR sets `expected_headcount` to the real denominator (e.g., 340 staff) even if only 280 have Employee records today. The dashboard's completion percentage uses `expected_headcount` when set, so officers see an honest metric rather than an inflated "100% of records we know about" figure.

## Tradeoffs

| Concern | Accepted consequence |
|---|---|
| Submissions created at activation may be stale if an employee is deactivated later | Out of scope for MVP; a separate "sync roster" task is the right fix, not blocking activation |
| Large activations (>200 employees) run in a background queue | Officers see a "generating…" gap in the dashboard; acceptable given the population size |
| `ensure_submission` creates submissions mid-API-call, in-process | The creation is a single DB insert per new employee — negligible latency; no async complexity needed |
| `expected_headcount` is manually maintained | Deliberate: automated headcount sync belongs in a `krcs_onesource` roster task, not this app |

## Future Path

When the `krcs_onesource` integration ships a staff roster sync, replace the lazy-creation path with a scheduled task that runs after each roster sync and creates any missing submissions for Active requirements. The `ensure_submission` utility function remains the correct insertion point — the scheduled task simply calls it in a loop rather than on page load.

At that point `expected_headcount` can be auto-populated from the roster sync result and the manual override can be deprecated.
