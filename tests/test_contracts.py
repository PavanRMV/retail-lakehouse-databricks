"""Regression contracts for every independent-review blocker."""
from pathlib import Path
import ast, io, zipfile
import pytest

ROOT = Path(__file__).parents[1]


def text(rel):
    return (ROOT / rel).read_text(encoding="utf-8")


def test_source_identity_is_file_plus_physical_row_and_collision_safe():
    from src.contracts import source_identity
    duplicate = ("536365", "85123A", "6", "2.55")
    assert source_identity("landing/a.csv", 1) != source_identity("landing/a.csv", 2)
    assert source_identity("landing/a.csv", 1) == source_identity("landing/a.csv", 1)
    assert len({source_identity("landing/a.csv", i) for i, _ in enumerate([duplicate, duplicate], 1)}) == 2


def test_bronze_uses_whole_file_positioned_lines_and_validates_before_sql():
    s = text("src/databricks/bronze.py")
    assert "binaryFile" in s and "posexplode" in s and "source_row_number" in s
    assert "source_line_hash" in s and "availableNow" in s and "_rescued_data" in s
    tree = ast.parse(s)
    assert not any(isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "sql" and isinstance(n.args[0], ast.JoinedStr) for n in ast.walk(tree))


def test_silver_materializes_parity_columns_and_unique_merge_source():
    s = text("src/databricks/silver.py")
    for name in ("item_type", "gross_merchandise_sales", "cancellation_value", "adjustment_value", "net_merchandise_value"):
        assert name in s
    assert "source_row_number" in s and "dropDuplicates(['transaction_key'])" in s
    assert "sha2(F.concat_ws('||', F.col('_source_file'), F.col('source_row_number')" in s


def test_gold_has_all_eight_marts_and_no_unchecked_replace_or_cwd_path():
    sql = text("sql/gold_marts.sql")
    for mart in ("gold_daily_sales", "gold_monthly_sales", "gold_product_performance", "gold_country_performance", "gold_customer_rfm", "gold_cohort_retention", "gold_cancellation_exposure", "gold_data_quality_metrics"):
        assert mart in sql
    g = text("src/databricks/gold.py")
    assert ".replace(" not in g and "../sql" not in g and "Path(__file__)" in g


def test_quality_gate_uses_shared_decision_and_audits_only_after_checks():
    s = text("src/databricks/quality_gate.py")
    for token in ("evaluate_quality_metrics", "source_max_epoch_seconds", "dq_metrics", "run_control", 'decision["status"]'):
        assert token in s
    assert s.index("evaluate_quality_metrics(metrics") < s.index('if decision["status"] == "FAILED"')


def test_bundle_provisions_environment_scoped_volumes_and_robust_paths():
    uc = text("sql/unity_catalog.sql")
    for volume in ("landing", "schema_state", "checkpoints"):
        assert f"VOLUME IF NOT EXISTS" in uc and volume in uc
    bundle = text("databricks.yml")
    assert "/landing/" in bundle and "/schema_state" in bundle and "/checkpoints" in bundle and "schema_root" in bundle
    assert "a.schema_root" in text("src/databricks/bronze.py")
    workflow = text("resources/workflow.yml")
    assert "${workspace.file_path}/src/databricks" in workflow


def test_ci_runs_generated_fixture_not_silent_full_data_skip():
    ci = text(".github/workflows/ci.yml")
    assert "generate_fixture" in ci and "test_fixture_pipeline" in ci
