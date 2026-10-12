# Architecture decisions
## ADR-001 — Bounded file ingestion
Use Auto Loader with `availableNow`, not fabricated CDC/real-time claims. The source is a batch workbook; incremental value comes from newly landed immutable files.
## ADR-002 — Managed tables, external landing
Raw landing remains an external UC Volume for lifecycle control; Bronze/Silver/Gold are managed Delta for governance and maintenance.
## ADR-003 — Fail-closed classification
Only documented code patterns become merchandise. Explicit exceptions are non-merchandise; unresolved codes stay visible as unknown-review.
## ADR-004 — Source identity and MERGE
Hash immutable file identity plus row identity and MERGE to make retries idempotent without collapsing legitimate duplicate business lines.
## ADR-005 — Local reference scope, not runtime parity
DuckDB mirrors classification rules, measures, and eight mart grains for deterministic evidence when workspace access is absent. It does not prove PySpark/Delta/Auto Loader semantics and is never represented as Databricks execution or full engine parity.

## ADR-006 — Fail-closed publication
Gold runs only after accounting, rescue, quarantine, duplicate identity, and unknown-review checks write metrics and pass. Failed runs receive a terminal failure record; success is never pre-written.

## ADR-007 — Workflow retry policy
Every task has an explicit timeout and retry count. Bronze may retry twice for transient ingestion failures; Silver and Gold retry once; the deterministic quality gate never retries bad data (`max_retries: 0`).
