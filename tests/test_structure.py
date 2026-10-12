from pathlib import Path
import re,yaml
ROOT=Path(__file__).parents[1]
def test_bundle_targets_and_workflow_graph():
 b=yaml.safe_load((ROOT/'databricks.yml').read_text());w=yaml.safe_load((ROOT/'resources/workflow.yml').read_text())
 assert set(b['targets'])=={'dev','prod'};assert set(b['variables'])>={'catalog','schema','source_path','checkpoint_root'}
 tasks=w['resources']['jobs']['retail_lakehouse_job']['tasks'];assert [x['task_key'] for x in tasks]==['bronze_ingest','silver_transform','quality_gate','gold_marts']
 assert tasks[1]['depends_on'][0]['task_key']=='bronze_ingest' and tasks[-1]['depends_on'][0]['task_key']=='quality_gate'
def test_databricks_assets_have_incremental_and_fail_closed_contracts():
 bronze=(ROOT/'src/databricks/bronze.py').read_text();silver=(ROOT/'src/databricks/silver.py').read_text();quality=(ROOT/'src/databricks/quality_gate.py').read_text()
 for token in ('cloudFiles','checkpointLocation','availableNow','_rescued_data'):assert token in bronze
 for token in ('DeltaTable','merge(','silver_quarantine','transaction_key'):assert token in silver
 for token in ('evaluate_quality_metrics','source_max_epoch_seconds','dq_metrics','run_control','FAILED'):assert token in quality
def test_no_personal_path_secret_or_unsafe_python_in_publishable_text():
 bad=[]
 for p in ROOT.rglob('*'):
  if p.name=='test_structure.py' or not p.is_file() or any(x in p.parts for x in ('.venv','.git','data','.pytest_cache','__pycache__')):continue
  try:s=p.read_text(encoding='utf-8')
  except UnicodeDecodeError:continue
  if re.search(r'C:[\\/]Users[\\/]|Sai Pavan|AKIA[0-9A-Z]{16}|shell\s*=\s*True|\beval\(|\bexec\(|pickle\.',s,re.I):bad.append(str(p.relative_to(ROOT)))
 assert bad==[]
def test_readme_claims_execution_boundary_and_evidence():
 s=(ROOT/'README.md').read_text();assert '541,909' in s and 'Local DuckDB' in s and 'not been deployed' in s and 'Databricks Asset Bundle' in s
