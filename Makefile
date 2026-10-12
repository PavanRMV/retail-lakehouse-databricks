install:
	uv sync --dev
test:
	uv run pytest -q
run-local:
	uv run python -m src.local_pipeline --source data/input/online_retail.csv
validate:
	uv run pytest -q tests/test_structure.py
