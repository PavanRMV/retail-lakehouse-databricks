import hashlib, io, subprocess, sys, zipfile
from pathlib import Path
import pytest
import scripts.acquire_data as acq


def archive(member="Online Retail.xlsx", payload=b"xlsx"):
    b=io.BytesIO()
    with zipfile.ZipFile(b,"w") as z:z.writestr(member,payload)
    return b.getvalue()


def test_acquisition_rejects_wrong_zip_hash(tmp_path):
    with pytest.raises(ValueError,match="ZIP SHA-256"):
        acq.acquire(tmp_path,lambda _:b"not authoritative")


def test_acquisition_reaches_and_rejects_wrong_member(tmp_path,monkeypatch):
    payload=archive("wrong.xlsx")
    monkeypatch.setattr(acq,"ZIP_SHA256",hashlib.sha256(payload).hexdigest())
    with pytest.raises(ValueError,match="exact member"):
        acq.acquire(tmp_path,lambda _:payload)


def test_acquisition_rejects_traversal_member(tmp_path,monkeypatch):
    payload=archive("../Online Retail.xlsx")
    monkeypatch.setattr(acq,"ZIP_SHA256",hashlib.sha256(payload).hexdigest())
    with pytest.raises(ValueError,match="traversal"):
        acq.acquire(tmp_path,lambda _:payload)
    assert not (tmp_path/"Online Retail.xlsx").exists()


def test_acquisition_is_idempotent_for_verified_xlsx(tmp_path,monkeypatch):
    target=tmp_path/"data/raw/Online Retail.xlsx";target.parent.mkdir(parents=True);target.write_bytes(b"known")
    monkeypatch.setattr(acq,"XLSX_SHA256",hashlib.sha256(b"known").hexdigest())
    assert acq.acquire(tmp_path,lambda _:pytest.fail("downloaded"))==target


def test_xlsx_to_csv_preserves_schema_and_text_and_cli_needs_no_download(tmp_path):
    import openpyxl
    xlsx=tmp_path/"fixture.xlsx";csv=tmp_path/"out.csv"
    wb=openpyxl.Workbook();ws=wb.active
    ws.append(acq.EXPECTED_COLUMNS);ws.append(["00123","00001A","x",1,"2010-01-01 00:00:00",2.5,"00007","UK"]);wb.save(xlsx)
    subprocess.run([sys.executable,str(Path(acq.__file__)),"--root",str(tmp_path),"--xlsx",str(xlsx),"--csv",str(csv)],check=True)
    lines=csv.read_text(encoding="utf-8").splitlines()
    assert lines[0].split(",")==acq.EXPECTED_COLUMNS
    assert lines[1].startswith("00123,00001A,") and ",00007," in lines[1]
