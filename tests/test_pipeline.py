import json
from pathlib import Path
import duckdb,pandas as pd,pytest
from src.contracts import classify_lines,transaction_key

def test_key_is_deterministic_and_null_explicit():
 assert transaction_key(('1',None))==transaction_key(('1',None));assert transaction_key(('1',None))!=transaction_key(('1',''))
def test_classification_edges_and_merchandise_kpi_scope():
 d=pd.DataFrame({'InvoiceNo':['1','2','3','C4'],'StockCode':['POST','ARBITRARY','85123A','85123A'],'Description':['post','thing','product','product'],'Quantity':[1,1,2,-1],'UnitPrice':[3,9,5,5]})
 g=classify_lines(d);assert g.item_type.tolist()==['NON_MERCHANDISE_SERVICE_ACCOUNTING','UNKNOWN_REVIEW','MERCHANDISE','MERCHANDISE'];assert g.gross_merchandise_sales.sum()==10;assert g.cancellation_value.sum()==5

def test_fixture_pipeline(tmp_path):
 root=tmp_path
 source=root/'fixture.csv';source.write_text('InvoiceNo,StockCode,Description,Quantity,InvoiceDate,UnitPrice,CustomerID,Country\n001,85123A,Product,2,2010-01-01 00:00:00,3.50,0007,UK\nC002,85123A,Product,-1,2010-01-02 00:00:00,3.50,0007,UK\n',encoding='utf-8')
 from src.local_pipeline import run
 m=run(source,root)
 assert m['source_rows']==2 and str(m['gross_merchandise_sales'])=='7.00' and str(m['cancellation_value'])=='3.50'
 assert len(list((root/'evidence').glob('gold_*.csv')))==8


def test_cancellation_mart_excludes_stockcodes_without_cancellations(tmp_path):
 root=tmp_path;source=root/'fixture.csv'
 source.write_text('InvoiceNo,StockCode,Description,Quantity,InvoiceDate,UnitPrice,CustomerID,Country\n001,85123A,Product,2,2010-01-01 00:00:00,3.50,0007,UK\n002,84029G,Other,1,2010-01-01 00:00:00,2.00,0008,UK\nC003,85123A,Product,-1,2010-01-02 00:00:00,3.50,0007,UK\n',encoding='utf-8')
 from src.local_pipeline import run
 run(source,root)
 con=duckdb.connect(str(root/'data/local/retail_lakehouse.duckdb'),read_only=True)
 assert con.execute('select stock_code from gold_cancellation_exposure').fetchall()==[('85123A',)]
 con.close()


def test_full_run_reconciliation_and_rerun_idempotency():
 root=Path(__file__).parents[1];source=root/'data/input/online_retail.csv'
 if not source.exists():pytest.skip('ignored full local input not present')
 from src.local_pipeline import run
 a=run(source,root);b=run(source,root)
 assert a==b;assert a['source_rows']==541909;assert a['source_rows']==a['silver_accepted_rows']+a['quarantine_rows']
 assert [a[k] for k in ('merchandise_rows','non_merchandise_rows','unknown_review_rows')]==[537378,3045,1486]
 assert str(a['gross_merchandise_sales'])=='10269646.28';assert str(a['net_merchandise_value'])=='9790952.10'
 con=duckdb.connect(str(root/'data/local/retail_lakehouse.duckdb'),read_only=True)
 assert con.execute('select count(*) from audit_runs').fetchone()[0]==1
 assert con.execute("select count(*) from gold_customer_rfm where purchase_frequency<1").fetchone()[0]==0
 assert con.execute("select count(*) from gold_monthly_sales where is_partial_month").fetchone()[0]==1
 con.close()


def test_published_evidence_completeness_matches_duckdb_and_csv():
 root=Path(__file__).parents[1];db=root/'data/local/retail_lakehouse.duckdb'
 if not db.exists():pytest.skip('ignored full local database not present')
 local=json.loads((root/'evidence/local_run_metrics.json').read_text())
 sample=json.loads((root/'evidence/sample_job_run.json').read_text())
 con=duckdb.connect(str(db),read_only=True)
 expected_epoch=con.execute("select epoch(max(invoice_timestamp))::bigint from silver_transactions").fetchone()[0]
 expected_cancellations=con.execute("select count(*) from gold_cancellation_exposure").fetchone()[0]
 con.close()
 csv_rows=len(pd.read_csv(root/'evidence/gold_cancellation_exposure.csv'))
 assert expected_cancellations==csv_rows==1936
 assert expected_epoch==1323435000
 readme=(root/'README.md').read_text(encoding='utf-8')
 acceptance=(root/'evidence/acceptance_report.md').read_text(encoding='utf-8')
 for document in (readme,acceptance):
  assert 'cancellation_mart_rows=1936' in document
  assert 'verified local DuckDB/CSV evidence' in document
 for evidence in (local,sample):
  assert evidence['cancellation_mart_rows']==expected_cancellations
  assert evidence['source_max_epoch_seconds']==expected_epoch
