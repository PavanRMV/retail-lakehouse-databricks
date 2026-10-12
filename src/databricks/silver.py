"""Canonical typed Silver transformation with collision-safe identity."""
from pyspark.sql import functions as F
from delta.tables import DeltaTable
from common import args, fq

a = args()
b = spark.table(fq(a, "bronze_invoice_lines"))
special = ["POST","DOT","C2","AMAZONFEE","BANK CHARGES","M","D","CRUK","B","S","23444","23574","22016","GIFT_0001_10","GIFT_0001_20","GIFT_0001_30","GIFT_0001_40","GIFT_0001_50"]
typed = (b.withColumn("invoice_no", F.trim("InvoiceNo"))
 .withColumn("stock_code", F.upper(F.trim("StockCode")))
 .withColumn("description", F.trim("Description"))
 .withColumn("quantity", F.col("Quantity").cast("long"))
 .withColumn("unit_price", F.col("UnitPrice").cast("decimal(18,4)"))
 .withColumn("invoice_timestamp", F.to_timestamp("InvoiceDate"))
 .withColumn("customer_id", F.trim("CustomerID")).withColumn("country", F.trim("Country"))
 .withColumn("transaction_key", F.sha2(F.concat_ws('||', F.col('_source_file'), F.col('source_row_number')), 256)))
invalid = "invoice_no is null or stock_code is null or quantity is null or unit_price is null or invoice_timestamp is null or _rescued_data is not null"
bad = typed.filter(invalid).withColumn("quarantine_reason", F.lit("TYPE_OR_SCHEMA_CONTRACT_FAILED"))
bad.write.format("delta").mode("overwrite").option("overwriteSchema", "true").saveAsTable(fq(a, "silver_quarantine"))
good = typed.filter("NOT (" + invalid + ")")
sale = (~F.col("invoice_no").startswith("C")) & (F.col("quantity") > 0) & (F.col("unit_price") > 0)
cancel = F.col("invoice_no").startswith("C") & (F.col("quantity") < 0) & (F.col("unit_price") > 0)
merch = F.col("stock_code").rlike(r"^[0-9]{5}[A-Z]{0,2}$") & F.col("description").isNotNull() & (~F.col("stock_code").isin(special))
value = F.col("quantity") * F.col("unit_price")
good = (good.withColumn("line_class", F.when(cancel,"CANCELLATION").when(sale,"SALE").otherwise("ADJUSTMENT"))
 .withColumn("item_type", F.when(F.col("stock_code").isin(special),"NON_MERCHANDISE_SERVICE_ACCOUNTING").when(merch,"MERCHANDISE").otherwise("UNKNOWN_REVIEW"))
 .withColumn("gross_merchandise_sales", F.when(merch & sale,value).otherwise(F.lit(0)))
 .withColumn("cancellation_value", F.when(merch & cancel,-value).otherwise(F.lit(0)))
 .withColumn("adjustment_value", F.when(merch & (~sale) & (~cancel),value).otherwise(F.lit(0)))
 .withColumn("net_merchandise_value", F.col("gross_merchandise_sales")-F.col("cancellation_value")+F.col("adjustment_value"))
 .dropDuplicates(['transaction_key']))
if not spark.catalog.tableExists(fq(a, "silver_transactions")):
    good.limit(0).write.format("delta").saveAsTable(fq(a, "silver_transactions"))
(DeltaTable.forName(spark, fq(a, "silver_transactions")).alias("t")
 .merge(good.alias("s"), "t.transaction_key = s.transaction_key")
 .whenMatchedUpdateAll().whenNotMatchedInsertAll().execute())
