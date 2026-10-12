"""Pinned, exact-member, idempotent UCI acquisition and XLSX→CSV CLI."""
import argparse, hashlib, io, urllib.request, zipfile
from pathlib import Path, PurePosixPath
import pandas as pd

URL="https://archive.ics.uci.edu/static/public/352/online+retail.zip"
ZIP_SHA256="f5385cbb54bbebf7196389109c6b0621faab0c304e3702548165e71c84aede8b"
XLSX_SHA256="43465a06f2ccf7c8b5bd2892bc7defb52f97487934fe93b16ae4c3936424676d"
MEMBER="Online Retail.xlsx"
EXPECTED_COLUMNS=["InvoiceNo","StockCode","Description","Quantity","InvoiceDate","UnitPrice","CustomerID","Country"]


def acquire(root: Path, downloader=None) -> Path:
    target=Path(root)/"data/raw"/MEMBER
    if target.exists() and hashlib.sha256(target.read_bytes()).hexdigest()==XLSX_SHA256:
        return target
    payload=(downloader or (lambda u: urllib.request.urlopen(u,timeout=90).read()))(URL)
    if hashlib.sha256(payload).hexdigest()!=ZIP_SHA256:
        raise ValueError("ZIP SHA-256 mismatch")
    with zipfile.ZipFile(io.BytesIO(payload)) as z:
        names=z.namelist()
        if any(PurePosixPath(n).is_absolute() or ".." in PurePosixPath(n).parts for n in names):
            raise ValueError("archive traversal rejected")
        if names != [MEMBER]:
            raise ValueError("archive must contain the exact member only")
        data=z.read(MEMBER)
    if hashlib.sha256(data).hexdigest()!=XLSX_SHA256:
        raise ValueError("XLSX SHA-256 mismatch")
    target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
    return target


def convert_xlsx(source: Path, target: Path) -> Path:
    frame=pd.read_excel(source,dtype={"InvoiceNo":"string","StockCode":"string","CustomerID":"string"},engine="openpyxl")
    if frame.columns.tolist()!=EXPECTED_COLUMNS:
        raise ValueError(f"exact schema mismatch: {frame.columns.tolist()}")
    target=Path(target);target.parent.mkdir(parents=True,exist_ok=True)
    frame.to_csv(target,index=False,encoding="utf-8",date_format="%Y-%m-%d %H:%M:%S")
    return target


def main(argv=None) -> int:
    p=argparse.ArgumentParser(description="Acquire pinned UCI Online Retail and produce pipeline-ready CSV")
    p.add_argument("--root",type=Path,default=Path(__file__).resolve().parents[1])
    p.add_argument("--xlsx",type=Path,help="convert this local workbook without downloading")
    p.add_argument("--csv",type=Path)
    a=p.parse_args(argv)
    xlsx=a.xlsx or acquire(a.root)
    output=a.csv or a.root/"data/input/online_retail.csv"
    print(convert_xlsx(xlsx,output))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
