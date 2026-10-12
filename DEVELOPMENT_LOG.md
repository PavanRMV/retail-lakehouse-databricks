# Development log

## 2026-10-11 — final contract repair (strict TDD)
- RED: `.venv/Scripts/python.exe -m pytest tests/test_behavioral_contracts.py -q` stopped during collection with exactly **1 error**: `evaluate_quality_metrics` did not yet exist in production shared code.
- GREEN focused: the same command most recently produced **17 passed in 1.62s** after extracting the pure quality evaluator and implementing Gold/workflow contracts.
- First full-suite check produced **2 failed, 35 passed in 44.33s**. Both failures were stale source-token assertions that expected quality rules to remain inline after the tested extraction; they were replaced with assertions for use of the shared evaluator.
- Reconciliation exposed that the local cancellation mart still emitted StockCodes having no cancellation. RED: `test_cancellation_mart_excludes_stockcodes_without_cancellations` returned both the sale-only and cancelled codes; GREEN: the focused test produced **1 passed in 1.62s** after applying the same cancellation filter as Databricks.
- Final GREEN: `.venv/Scripts/python.exe -m pytest -q` produced **38 passed in 44.86s**. This includes the generated fixture and the 541,909-row local pipeline executed twice by `test_full_run_reconciliation_and_rerun_idempotency`.
- Behavioral coverage now executes identifier acceptance/rejection, every quality failure branch and terminal status, parsed Databricks Gold SQL semantics, and parsed workflow timeout/retry/dependency policy. Databricks assets remain authored/static-tested only; no live workspace execution is claimed.

## 2026-10-11 — absolute final release-candidate blockers (strict TDD)
- RED: focused cohort/workflow/evidence tests produced **2 failed, 1 passed**: the initial cohort assertion exposed sqlglot's normalized `NOT customer_id IS NULL` AST, and both evidence JSON documents lacked `cancellation_mart_rows` / `source_max_epoch_seconds`.
- GREEN dependency proof: `uv lock` added `sqlglot==30.22.0`; `uv sync --dev --locked` resolved 19 and checked 17 packages without a manual install.
- GREEN focused: cohort AST semantics, exact per-task workflow policy and chain, direct DuckDB/CSV evidence reconciliation, and the exemption-free publishable path/security scan produced **4 passed in 3.30s**.
- Full local pipeline ran twice over **541,909** source rows; both runs returned `cancellation_mart_rows=1936`, `source_max_epoch_seconds=1323435000`, balanced accounting, and the unchanged source SHA-256.
- Final clean-sync GREEN: `uv sync --dev --locked` resolved 19 and checked 17 packages, then `uv run pytest -q` produced **40 passed in 42.43s**. `compileall` completed, workflow YAML parsed, cross-file metrics matched, and the exact Snowflake repository-root check returned HEAD `9490bad73b81ba095d5ccecf70df12ed59efafe9` with empty porcelain status.
- Boundary remains unchanged: local DuckDB execution and static Databricks validation only; no live Databricks deployment or execution is claimed.
