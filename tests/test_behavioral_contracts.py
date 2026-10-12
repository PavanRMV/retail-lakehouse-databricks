"""Executable behavioral contracts for shared helpers, Gold SQL, and workflow policy."""
from pathlib import Path

import pytest
import sqlglot
from sqlglot import exp
import yaml

from src.databricks.common import evaluate_quality_metrics, identifier

ROOT = Path(__file__).parents[1]


def test_identifier_accepts_safe_names_and_quotes_them():
    assert identifier("retail_dev") == "`retail_dev`"
    assert identifier("_schema2") == "`_schema2`"


@pytest.mark.parametrize("unsafe", ["retail-dev", "x.y", "x; DROP TABLE sales", "name`", "with space", ""])
def test_identifier_rejects_punctuation_and_sql_injection(unsafe):
    with pytest.raises(ValueError, match="unsafe identifier"):
        identifier(unsafe)


def good_metrics(**overrides):
    metrics = {
        "source_rows": 10,
        "accepted_rows": 10,
        "quarantine_rows": 0,
        "rescued_rows": 0,
        "duplicate_source_identity": 0,
        "unknown_review_rows": 1,
        "source_max_epoch_seconds": 1_323_443_580,
    }
    metrics.update(overrides)
    return metrics


def test_quality_metrics_success_has_terminal_succeeded_status():
    decision = evaluate_quality_metrics(good_metrics(), {"quarantine_rows": 0, "unknown_review_rows": 1})
    assert decision == {"status": "SUCCEEDED", "failures": []}


@pytest.mark.parametrize(
    ("overrides", "expected"),
    [
        ({"accepted_rows": 9}, "row_imbalance"),
        ({"rescued_rows": 1}, "rescued_content"),
        ({"quarantine_rows": 1, "accepted_rows": 9}, "quarantine_threshold"),
        ({"duplicate_source_identity": 1}, "duplicate_source_identity"),
        ({"unknown_review_rows": 2}, "unknown_review_threshold"),
    ],
)
def test_quality_metrics_fail_closed_with_terminal_failed_status(overrides, expected):
    decision = evaluate_quality_metrics(good_metrics(**overrides), {"quarantine_rows": 0, "unknown_review_rows": 1})
    assert decision["status"] == "FAILED"
    assert expected in decision["failures"]


def parsed_gold_statements():
    sql = (ROOT / "sql/gold_marts.sql").read_text(encoding="utf-8")
    sql = sql.replace("`${catalog}`", "catalog").replace("`${schema}`", "schema")
    statements = sqlglot.parse(sql, read="databricks")
    return {statement.this.this.name: statement.expression for statement in statements if isinstance(statement, exp.Create)}


def test_gold_cancellation_exposure_has_exact_stockcode_grain():
    query = parsed_gold_statements()["gold_cancellation_exposure"]
    grouped = [column.name for column in query.args["group"].expressions]
    assert grouped == ["stock_code"]


def test_gold_rfm_is_purchase_only_and_has_exact_segment_rule():
    query = parsed_gold_statements()["gold_customer_rfm"]
    normalized = query.sql(dialect="databricks")
    where = next(query.find_all(exp.Where)).sql(dialect="databricks")
    assert "item_type = 'MERCHANDISE'" in where and "line_class = 'SALE'" in where
    case = next(query.find_all(exp.Case)).sql(dialect="databricks")
    assert case == "CASE WHEN monetary >= 2000 AND purchase_frequency >= 5 THEN 'CHAMPION' WHEN purchase_frequency >= 3 THEN 'LOYAL' ELSE 'DEVELOPING' END"
    assert "segment" in normalized


def test_gold_cohort_retention_has_purchase_only_customer_month_semantics():
    query = parsed_gold_statements()["gold_cohort_retention"]
    ctes = {cte.alias: cte.this for cte in query.args["with_"].expressions}
    activity = ctes["a"]
    deduplicated = ctes["d"]
    aggregated = ctes["z"]

    where = activity.args["where"]
    assert any(isinstance(node, exp.Not) and isinstance(node.this, exp.Is) and node.this.this.name == "customer_id" for node in where.walk())
    equalities = {(node.this.name, node.expression.this) for node in where.find_all(exp.EQ)}
    assert {("item_type", "MERCHANDISE"), ("line_class", "SALE")} <= equalities

    month_projections = {projection.alias: projection.this for projection in activity.expressions if isinstance(projection, exp.Alias)}
    activity_month = month_projections["activity_month"]
    cohort_month = month_projections["cohort_month"]
    assert isinstance(activity_month, exp.TimestampTrunc)
    assert activity_month.this.name == "invoice_timestamp" and activity_month.text("unit").upper() == "MONTH"
    cohort_date_trunc = next(cohort_month.find_all(exp.TimestampTrunc))
    assert cohort_date_trunc.this.name == "invoice_timestamp" and cohort_date_trunc.text("unit").upper() == "MONTH"

    assert deduplicated.args.get("distinct")
    assert [projection.name for projection in deduplicated.expressions] == ["customer_id", "cohort_month", "activity_month"]
    assert [projection.name for projection in aggregated.expressions[:2]] == ["cohort_month", "activity_month"]
    assert [column.name for column in aggregated.args["group"].expressions] == ["cohort_month", "activity_month"]
    assert [projection.name for projection in query.expressions[:2]] == ["cohort_month", "activity_month"]
    assert query.args["from_"].this.name == "z"


def test_gold_dq_exposes_persisted_freshness_metric():
    query = parsed_gold_statements()["gold_data_quality_metrics"]
    metric_names = {literal.this for literal in query.find_all(exp.Literal) if literal.is_string}
    assert "source_max_epoch_seconds" in metric_names


def test_workflow_tasks_have_exact_policy_and_required_chain():
    workflow = yaml.safe_load((ROOT / "resources/workflow.yml").read_text(encoding="utf-8"))
    tasks = workflow["resources"]["jobs"]["retail_lakehouse_job"]["tasks"]
    assert {task["task_key"]: (task["timeout_seconds"], task["max_retries"]) for task in tasks} == {
        "bronze_ingest": (1800, 2),
        "silver_transform": (1800, 1),
        "quality_gate": (900, 0),
        "gold_marts": (1800, 1),
    }
    assert {task["task_key"]: [d["task_key"] for d in task.get("depends_on", [])] for task in tasks} == {
        "bronze_ingest": [],
        "silver_transform": ["bronze_ingest"],
        "quality_gate": ["silver_transform"],
        "gold_marts": ["quality_gate"],
    }
