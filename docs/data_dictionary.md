# Data dictionary
| Table | Grain / key | Purpose |
|---|---|---|
| bronze_invoice_lines | source file + row | Raw strings, rescued data, source identity, ingestion timestamp |
| silver_transactions | one accepted source line / transaction_key | Typed transaction, line/item classes, merchandise measures |
| silver_quarantine | rejected source line / source identity | Reason-coded type/schema failures; never silent coercion |
| dq_metrics | run_id × metric | Auditable accounting, rescued, duplicate-identity, quarantine, unknown-review, and `source_max_epoch_seconds` freshness observations |
| run_control | run_id | Terminal `FAILED`/`SUCCEEDED` state, thresholds/counts, timestamps, and failure reasons; success only after every gate passes |
| gold_daily_sales | date | Gross, cancellation exposure, net merchandise sales |
| gold_monthly_sales | month | Same KPIs plus explicit partial-month flag |
| gold_product_performance | merchandise StockCode | Product revenue and cancellation exposure |
| gold_country_performance | country | Merchandise KPIs by country |
| gold_customer_rfm | known purchasing customer | Purchase-only recency/frequency/monetary; `CHAMPION` when monetary ≥ 2000 and frequency ≥ 5, `LOYAL` when frequency ≥ 3, otherwise `DEVELOPING` |
| gold_cohort_retention | cohort month × month number | Active purchasing customers |
| gold_cancellation_exposure | merchandise StockCode | Cancellation lines and value |
| gold_data_quality_metrics | run_id × metric | Selected persisted DQ metrics including `source_max_epoch_seconds` (maximum Silver invoice timestamp as Unix epoch seconds) |

Identifiers remain text. Merchandise requires `^[0-9]{5}[A-Z]{0,2}$` plus description; explicit service/accounting codes are non-merchandise; everything else is `UNKNOWN_REVIEW`. A cancellation requires C-prefixed invoice, negative quantity, and positive price.
