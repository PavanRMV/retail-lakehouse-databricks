# Repair acceptance report

**Status:** PASS for full local DuckDB execution, generated-fixture behavior, parsed workflow/SQL contracts, and static Databricks validation. **Not deployed to or executed on Databricks.**

## Executed evidence
- Full ignored CSV run twice: 541,909 rows; source SHA-256 `414e528b64e9a6220b0e4322896fd182b64338a8b25b2e0d421a171471839c59`; reruns produced one idempotent local audit record.
- Row accounting: Bronze 541,909 = Silver accepted 541,909 + quarantine 0.
- Classification: merchandise 537,378; non-merchandise 3,045; unknown-review 1,486; cancellation lines 9,288.
- Merchandise: gross £10,269,646.28; cancellation £478,694.18; adjustments £0.00; net £9,790,952.10.
- Eight local Gold marts materialized. Grains: daily 305; monthly 13; product 3,819; country 38; purchase-only RFM 4,334; cohort 91; cancellation exposure is exactly `StockCode`; DQ freshness is `source_max_epoch_seconds=1323435000`. The explicit `cancellation_mart_rows=1936` result is verified local DuckDB/CSV evidence, not live Databricks evidence.
- Focused final blockers: cohort semantics, exact workflow policy/chain, evidence reconciliation, and exemption-free path/security scan → **4 passed in 3.30s**.
- Clean locked sync followed by full suite: `uv sync --dev --locked && uv run pytest -q` → **40 passed in 42.43s**. The full-data test executes the 541,909-row pipeline twice; the fixture tests execute acquisition-independent end-to-end behavior.
- Python compilation, YAML parse, workflow graph/policy, metric cross-file comparison, publishable security scan, and source/Gold CSV/DuckDB reconciliation passed.
- Parsed SQL tests use locked `sqlglot==30.22.0` with the Databricks dialect to validate cancellation grain, purchase-only RFM and cohorts, distinct customer-month cohort behavior, cohort/month output grain, the exact segment CASE, and the persisted freshness metric.
- Pure production-helper tests cover safe/unsafe identifiers, success, row imbalance, rescued content, quarantine threshold, duplicate identity, unknown-review threshold, and terminal run status without Spark mocks.

## Workflow policy
The parsed dependency graph is `bronze_ingest -> silver_transform -> quality_gate -> gold_marts`. Every task has positive `timeout_seconds` and explicit non-negative `max_retries`. The deterministic quality gate has `max_retries: 0`; Bronze has 2 retries, and Silver/Gold have 1.

## Bundle boundary
Native `databricks bundle validate` was unavailable (`databricks: command not found`). No CLI was installed because live authentication/runtime validation was outside scope. No deployment, grants, workspace run, Delta runtime, or Auto Loader runtime behavior is claimed.

## Intended publication inventory
This Databricks folder is not represented as a Git repository and no tracking-status claim is made. `.gitignore` excludes `data/raw/`, `.venv/`, `.pytest_cache/`, `__pycache__/`, `data/local/`, and `*.duckdb`; those raw/environment/cache/local-state paths are omitted from the intended publication inventory. Deterministic files under `evidence/` are the publication evidence.

## Exact Snowflake protection verification
Commands were run from the exact Snowflake repository root, `retail-revenue-intelligence-snowflake`:
- `git rev-parse --show-toplevel` → the `retail-revenue-intelligence-snowflake` repository root
- `git rev-parse HEAD` → `9490bad73b81ba095d5ccecf70df12ed59efafe9`
- `git status --porcelain=v1` → empty

The separate Snowflake repository was not modified.
