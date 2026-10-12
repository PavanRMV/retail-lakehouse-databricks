"""Fail-closed quality gate with auditable metrics and terminal run state."""
from datetime import datetime, timezone
import uuid
from common import args, evaluate_quality_metrics, fq

a = args(("quarantine-threshold", "unknown-review-threshold"))
quarantine_threshold = int(a.quarantine_threshold)
unknown_review_threshold = int(a.unknown_review_threshold)
run_id = str(uuid.uuid4()); started_at = datetime.now(timezone.utc)
b = spark.table(fq(a,"bronze_invoice_lines")); s = spark.table(fq(a,"silver_transactions")); q = spark.table(fq(a,"silver_quarantine"))
source_rows=b.count(); accepted_rows=s.count(); quarantine_rows=q.count()
rescued_rows=b.filter("_rescued_data is not null").count()
duplicate_source_identity=b.groupBy("_source_file","source_row_number").count().filter("count > 1").count()
unknown_review_rows=s.filter("item_type = 'UNKNOWN_REVIEW'").count()
source_max_epoch_seconds=s.selectExpr("CAST(MAX(invoice_timestamp) AS BIGINT) source_max_epoch_seconds").first()[0]
metrics={"source_rows":source_rows,"accepted_rows":accepted_rows,"quarantine_rows":quarantine_rows,"rescued_rows":rescued_rows,"duplicate_source_identity":duplicate_source_identity,"unknown_review_rows":unknown_review_rows,"source_max_epoch_seconds":source_max_epoch_seconds}
decision=evaluate_quality_metrics(metrics,{"quarantine_rows":quarantine_threshold,"unknown_review_rows":unknown_review_threshold})
failures=decision["failures"]
spark.sql("CREATE TABLE IF NOT EXISTS " + fq(a,"dq_metrics") + " (run_id STRING, metric STRING, value BIGINT, measured_at TIMESTAMP) USING DELTA")
spark.sql("CREATE TABLE IF NOT EXISTS " + fq(a,"run_control") + " (run_id STRING, status STRING, source_rows BIGINT, accepted_rows BIGINT, quarantine_rows BIGINT, rescued_rows BIGINT, duplicate_source_identity BIGINT, unknown_review_rows BIGINT, started_at TIMESTAMP, completed_at TIMESTAMP, failures STRING) USING DELTA")
rows=[(run_id,k,int(v),started_at) for k,v in metrics.items()]
spark.createDataFrame(rows,"run_id string, metric string, value long, measured_at timestamp").write.mode("append").saveAsTable(fq(a,"dq_metrics"))
if decision["status"] == "FAILED":
    spark.createDataFrame([(run_id,"FAILED",source_rows,accepted_rows,quarantine_rows,rescued_rows,duplicate_source_identity,unknown_review_rows,started_at,datetime.now(timezone.utc),",".join(failures))],spark.table(fq(a,"run_control")).schema).write.mode("append").saveAsTable(fq(a,"run_control"))
    raise RuntimeError("quality gate failed: " + ",".join(failures))
spark.createDataFrame([(run_id,decision["status"],source_rows,accepted_rows,quarantine_rows,rescued_rows,duplicate_source_identity,unknown_review_rows,started_at,datetime.now(timezone.utc),"")],spark.table(fq(a,"run_control")).schema).write.mode("append").saveAsTable(fq(a,"run_control"))
