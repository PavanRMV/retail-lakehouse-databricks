"""Bounded Auto Loader ingestion (file batch, not CDC).

Whole-file binary ingestion is intentional: splitting with posexplode gives each
CSV record a stable physical line number, including exact duplicate business rows.
"""
from pyspark.sql import functions as F, types as T
from common import args, fq, namespace

a = args(("source-path", "schema-root", "checkpoint-root"))  # validates names before SQL
spark.sql("CREATE SCHEMA IF NOT EXISTS " + namespace(a))
raw_schema = T.StructType([
    T.StructField("InvoiceNo", T.StringType()), T.StructField("StockCode", T.StringType()),
    T.StructField("Description", T.StringType()), T.StructField("Quantity", T.StringType()),
    T.StructField("InvoiceDate", T.StringType()), T.StructField("UnitPrice", T.StringType()),
    T.StructField("CustomerID", T.StringType()), T.StructField("Country", T.StringType()),
    T.StructField("_rescued_data", T.StringType()),
])
files = (spark.readStream.format("cloudFiles")
    .option("cloudFiles.format", "binaryFile")
    .option("cloudFiles.schemaLocation", a.schema_root)
    .load(a.source_path))
lines = (files.select(F.col("path").alias("_source_file"), F.col("modificationTime").alias("_source_modified_at"),
                      F.posexplode(F.split(F.decode("content", "UTF-8"), r"\r?\n")).alias("_position", "_source_line"))
    .filter((F.col("_position") > 0) & (F.length("_source_line") > 0))
    .withColumn("source_row_number", F.col("_position").cast("long"))
    .withColumn("source_line_hash", F.sha2("_source_line", 256))
    .withColumn("parsed", F.from_csv("_source_line", raw_schema, {"mode": "PERMISSIVE", "columnNameOfCorruptRecord": "_rescued_data"}))
    .select("parsed.*", "_source_file", "source_row_number", "source_line_hash", "_source_modified_at")
    .withColumn("_ingested_at", F.current_timestamp()))
query = (lines.writeStream.format("delta").option("checkpointLocation", a.checkpoint_root + "/bronze")
         .option("mergeSchema", "true").trigger(availableNow=True).toTable(fq(a, "bronze_invoice_lines")))
query.awaitTermination()
