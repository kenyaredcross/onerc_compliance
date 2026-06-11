# ADR 0001 — ITSM practices as a single module within onerc_compliance

**Status:** Accepted · 2026-06-11

## Context
The ITSM build covers several ITIL practices (a shared foundation/SLA engine, Incident
Management, Service Request Management, Remote Support). The original guidance was that
**each practice be its own Module Def** in `modules.txt`, to ease a future extraction into a
standalone `onerc_itsm` app.

During planning the team chose instead to keep **all ITSM doctypes in one module**,
`Onerc Incident Management`, for Phase 1.

## Decision
Ship every ITSM doctype (foundation, Incident, Service Request, Remote Support,
Configuration Item) under the single module **`Onerc Incident Management`**.

## Consequences
- **Simpler now:** one module folder, one workspace, less ceremony during rapid build-out.
- **Naming caveat:** the module name reads narrower than its contents (it also holds the SLA
  engine, service catalogue and remote support). Accepted for Phase 1.
- **Extractability is preserved by coupling rules, not by module count.** The real guard is:
  ITSM doctypes never import from, or Link into, the compliance attestation doctypes (and
  vice-versa); anything shared goes through `onerc_core`. This is upheld regardless of how
  many modules exist.
- **Future split path:** to extract to `onerc_itsm`, move the doctype folders, re-point each
  doctype's `module`, and split `modules.txt` — no data migration of relationships required,
  because there are no cross-domain links to untangle.

## Alternatives considered
- *One Module Def per practice* — most faithful to the original guidance, but more overhead
  than Phase 1 warranted. Deferred.
