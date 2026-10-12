"""Shared, deterministic retail transformation contracts."""
from __future__ import annotations
import hashlib
import re
import pandas as pd

NON_MERCHANDISE_CODES = {
    "POST", "DOT", "C2", "AMAZONFEE", "BANK CHARGES", "M", "D", "CRUK",
    "B", "S", "23444", "23574", "22016", "GIFT_0001_10", "GIFT_0001_20",
    "GIFT_0001_30", "GIFT_0001_40", "GIFT_0001_50",
}
MERCHANDISE_CODE_RE = re.compile(r"^\d{5}[A-Z]{0,2}$")
REQUIRED_COLUMNS = ["InvoiceNo", "StockCode", "Description", "Quantity", "InvoiceDate", "UnitPrice", "CustomerID", "Country"]


def source_identity(source_file: str, source_row_number: int) -> str:
    """Immutable identity: exact source object path plus physical 1-based CSV line."""
    if not source_file or not isinstance(source_row_number, int) or source_row_number < 1:
        raise ValueError("source identity requires a file and positive physical line number")
    return hashlib.sha256(f"{source_file}\x1f{source_row_number}".encode("utf-8")).hexdigest()


def transaction_key(values: tuple[object, ...]) -> str:
    payload = "\x1f".join("<NULL>" if pd.isna(v) else str(v).strip() for v in values)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def classify_lines(df: pd.DataFrame) -> pd.DataFrame:
    x = df.copy()
    desc = x["Description"].astype("string").str.strip()
    inv = x["InvoiceNo"].astype("string").str.strip()
    code = x["StockCode"].astype("string").str.strip().str.upper()
    qty = pd.to_numeric(x["Quantity"], errors="coerce")
    price = pd.to_numeric(x["UnitPrice"], errors="coerce")
    sale = ~inv.str.startswith("C", na=False) & qty.gt(0) & price.gt(0)
    cancel = inv.str.startswith("C", na=False) & qty.lt(0) & price.gt(0)
    explicit = code.isin(NON_MERCHANDISE_CODES)
    merchandise = code.str.match(MERCHANDISE_CODE_RE, na=False) & desc.notna() & ~explicit
    x["line_class"] = "ADJUSTMENT"
    x.loc[sale, "line_class"] = "SALE"
    x.loc[cancel, "line_class"] = "CANCELLATION"
    x["item_type"] = "UNKNOWN_REVIEW"
    x.loc[merchandise, "item_type"] = "MERCHANDISE"
    x.loc[explicit, "item_type"] = "NON_MERCHANDISE_SERVICE_ACCOUNTING"
    value = qty * price
    x["gross_merchandise_sales"] = value.where(merchandise & sale, 0.0)
    x["cancellation_value"] = (-value).where(merchandise & cancel, 0.0)
    x["adjustment_value"] = value.where(merchandise & ~(sale | cancel), 0.0)
    x["net_merchandise_value"] = x.gross_merchandise_sales - x.cancellation_value + x.adjustment_value
    invoice_date = x["InvoiceDate"] if "InvoiceDate" in x else pd.Series("", index=x.index)
    customer = x["CustomerID"] if "CustomerID" in x else pd.Series("", index=x.index)
    country = x["Country"] if "Country" in x else pd.Series("", index=x.index)
    x["transaction_key"] = [transaction_key(row) for row in zip(inv, code, desc, qty, invoice_date, price, customer, country)]
    return x
