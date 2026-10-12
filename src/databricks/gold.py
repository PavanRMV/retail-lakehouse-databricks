"""Render packaged Gold SQL after strict identifier validation."""
import re
from pathlib import Path
from common import args, identifier

a = args()
resource = Path(__file__).resolve().parents[2] / "sql" / "gold_marts.sql"
text = resource.read_text(encoding="utf-8")
values = {"catalog": identifier(a.catalog), "schema": identifier(a.schema)}
# Template includes backticks around placeholders; substitute only validated bare names
values = {k: v[1:-1] for k, v in values.items()}
text = re.sub(r"\$\{(catalog|schema)\}", lambda m: values[m.group(1)], text)
for statement in text.split(";"):
    if statement.strip():
        spark.sql(statement)
