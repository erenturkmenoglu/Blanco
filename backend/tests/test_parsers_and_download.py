import io
import zipfile

from app.acquisition.downloader import sniff_format
from app.acquisition.parsers import parse_bytes, to_number
from tests.fixtures import balance_sheet_rows, build_xlsx


def test_sniff_formats():
    assert sniff_format(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"\x00" * 32) == "xls"
    assert sniff_format(build_xlsx({"S": [["a"]]})) == "xlsx"
    assert sniff_format(b"%PDF-1.7 ...") == "pdf"
    assert sniff_format(b"<!DOCTYPE html><html><body></body></html>") == "html"
    assert sniff_format(b'{"a": 1}') == "json"
    assert sniff_format("a;b;c\n1;2;3\n".encode()) == "csv"
    bio = io.BytesIO()
    with zipfile.ZipFile(bio, "w") as z:
        z.writestr("x.csv", "a;b\n1;2\n")
    assert sniff_format(bio.getvalue()) == "zip"


def test_parse_xlsx_inventory_and_zip():
    data = build_xlsx({"K2 Aktifler": balance_sheet_rows()})
    doc = parse_bytes(data)
    assert doc.format == "xlsx" and "K2 Aktifler" in doc.tables
    assert doc.inventory["K2 Aktifler"]["rows"] == 9
    bio = io.BytesIO()
    with zipfile.ZipFile(bio, "w") as z:
        z.writestr("veri.xlsx", data)
        z.writestr("not.csv", "Banka;Deger\nAkbank;1.234,5\n")
    zdoc = parse_bytes(bio.getvalue())
    assert any(n.endswith("K2 Aktifler") for n in zdoc.tables) and any(n.endswith("csv") for n in zdoc.tables)


def test_parse_html_table():
    html = b"<html><body><table><tr><th>Banka</th><th>Toplam Aktifler</th></tr><tr><td>Akbank</td><td>1.000</td></tr></table></body></html>"
    doc = parse_bytes(html)
    assert doc.format == "html" and len(doc.tables) == 1


def test_to_number_tr_and_en():
    assert to_number("1.234.567,89") == 1234567.89
    assert to_number("1,234,567.89") == 1234567.89
    assert to_number("12,07") == 12.07
    assert to_number("(1.500)") == -1500
    assert to_number("-") is None and to_number("") is None and to_number(None) is None
    assert to_number(42) == 42.0
