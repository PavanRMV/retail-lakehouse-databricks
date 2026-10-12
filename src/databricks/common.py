import argparse
import re

IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def identifier(value: str) -> str:
    """Validate before interpolation and return a quoted UC identifier."""
    if not isinstance(value, str) or not IDENTIFIER_RE.fullmatch(value):
        raise ValueError(f"unsafe identifier: {value!r}")
    return f"`{value}`"


def evaluate_quality_metrics(metrics: dict, thresholds: dict) -> dict:
    """Evaluate portable DQ metrics and choose the terminal run status."""
    failures = []
    if metrics["source_rows"] != metrics["accepted_rows"] + metrics["quarantine_rows"]:
        failures.append("row_imbalance")
    if metrics["rescued_rows"]:
        failures.append("rescued_content")
    if metrics["quarantine_rows"] > thresholds["quarantine_rows"]:
        failures.append("quarantine_threshold")
    if metrics["duplicate_source_identity"]:
        failures.append("duplicate_source_identity")
    if metrics["unknown_review_rows"] > thresholds["unknown_review_rows"]:
        failures.append("unknown_review_threshold")
    return {"status": "FAILED" if failures else "SUCCEEDED", "failures": failures}


def args(extra=()):
    p = argparse.ArgumentParser()
    p.add_argument("--catalog", required=True)
    p.add_argument("--schema", required=True)
    for name in extra:
        default = "0" if name == "quarantine-threshold" else "1486" if name == "unknown-review-threshold" else None
        p.add_argument("--" + name, required=default is None, default=default)
    parsed = p.parse_args()
    identifier(parsed.catalog)
    identifier(parsed.schema)
    return parsed


def namespace(a) -> str:
    return f"{identifier(a.catalog)}.{identifier(a.schema)}"


def fq(a, table: str) -> str:
    return f"{namespace(a)}.{identifier(table)}"
