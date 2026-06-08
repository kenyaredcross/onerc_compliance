# ADR-001: Dynamic Form Builder in onerc_compliance

**Status:** Accepted  
**Date:** 2026-06-08  
**Deciders:** Kelvin Njenga

---

## Context

OneRC has at least two modules that require staff to fill in structured, officer-defined forms: compliance attestations (this app) and pre-qualification questionnaires (`onerc_prequalification`). Both require the same fundamental capability — a form schema defined at runtime by officers, stored as child-table rows, rendered dynamically in a Vue SPA, and answered per-employee with per-field typed storage.

The question was where to build this capability first and how to name it.

## Decision

Build the dynamic form engine inside `onerc_compliance` under neutral names (`Compliance Requirement Field`, `Compliance Submission Value`) rather than compliance-specific names. The schema stores enough fieldtype metadata (label, fieldtype, options, mandatory) that the renderer and the value storage pattern can be extracted into a shared `onerc_core` library later without a breaking change on the DB side.

## Rationale

1. **Ship the immediate need** — compliance attestation is the concrete, funded requirement. Building a generic engine in `onerc_core` first delays the deliverable with no current second consumer.
2. **Neutral naming reduces rework** — if the child-table names had "Compliance" in them they would need to be duplicated or migrated when reused. Naming them descriptively (`Requirement Field`, `Submission Value`) keeps them promotable.
3. **Schema freeze pattern is shareable** — the `_validate_schema_freeze()` logic (compare field-list signatures, block edits once Active) is implemented as a pure Frappe model method with no compliance-specific coupling. Promoting it to `onerc_core` later is a copy-paste lift.
4. **Value storage is generic** — `Compliance Submission Value` stores answers as `value` (Text), `value_date` (Date), `value_check` (Check), and `attachment` (Attach). This covers all fieldtypes both compliance and prequalification need without schema changes.

## Schema Freeze Decision

Once a Compliance Requirement reaches Active status its field schema is frozen. Any attempt to add, remove, or reorder fields raises a validation error.

**Why:** Submissions already created against the requirement reference field names from the snapshot at activation time. Mutating the schema retroactively would produce answers whose field names no longer match the schema, breaking the dashboard renderer and the review UI.

**Tradeoff accepted:** Officers cannot fix typos in labels or descriptions once a requirement is Active. The workaround is to Close the requirement and create a new one. This is intentional — it forces officers to treat field definitions as a deliberate act and avoids silent data inconsistencies.

## Consequences

- `onerc_prequalification` will duplicate the child-table structure until the engine is promoted to `onerc_core`.
- When the engine is promoted, a Frappe migration will rename the child doctypes and patch existing rows — acceptable one-time cost.
- Any new fieldtype support (e.g., Table, Link) must be added to the value storage schema before use; the current four columns cover the agreed MVP field set.

## Future Path

When `onerc_prequalification` ships and shares the form-engine concept, create an `onerc_core` module that:
- Owns the field-definition and value-storage doctypes
- Exports the renderer composable (`useDynamicForm.js`)
- Both apps install `onerc_core` and declare link fields to the shared doctypes

This ADR does not block that path — it defers it until there is a concrete second consumer.
