"""Dosya ayrıştırıcıları: xls / xlsx / csv / html / zip / json / xml → pandas tabloları + envanter.

Her ayrıştırıcı ham hücreleri başlık varsaymadan (header=None) okur; başlık satırı ve banka satırları
normalization katmanında bulunur. Böylece kaynak düzeni değişse bile ham veri korunur ve envanter raporlanır.
"""
from __future__ import annotations

import io
import json
import zipfile
from dataclasses import dataclass, field

import pandas as pd

from .downloader import sniff_format


@dataclass
class ParsedDocument:
    format: str
    tables: dict[str, pd.DataFrame] = field(default_factory=dict)   # sheet/tablo adı → ham hücre tablosu
    inventory: dict[str, dict] = field(default_factory=dict)        # ad → {rows, cols, first_cells}
    notes: list[str] = field(default_factory=list)

    def add(self, name: str, df: pd.DataFrame):
        name = name or f"table_{len(self.tables) + 1}"
        base, i = name, 1
        while name in self.tables:
            i += 1
            name = f"{base}_{i}"
        self.tables[name] = df
        head = []
        for r in range(min(6, len(df))):
            row = [str(x) for x in df.iloc[r].tolist()[:8] if pd.notna(x) and str(x).strip()]
            if row:
                head.append(row)
        self.inventory[name] = {"rows": int(df.shape[0]), "cols": int(df.shape[1]), "first_cells": head}


def parse_bytes(data: bytes, file_name: str | None = None, fmt: str | None = None) -> ParsedDocument:
    fmt = fmt or sniff_format(data, file_name)
    if fmt == "xls":
        return _parse_xls(data)
    if fmt == "xlsx":
        return _parse_xlsx(data)
    if fmt == "zip":
        return _parse_zip(data)
    if fmt == "csv":
        return _parse_csv(data)
    if fmt == "html":
        return _parse_html(data)
    if fmt == "json":
        return _parse_json(data)
    if fmt == "xml":
        return _parse_xml(data)
    if fmt == "docx":
        return _parse_docx(data)
    doc = ParsedDocument(format=fmt)
    doc.notes.append(f"desteklenmeyen/anlaşılamayan biçim: {fmt} (pdf için yapılandırılmış kaynak yoksa pdf-tablo çıkarımı ayrı aşamadır)")
    return doc


def _parse_docx(data: bytes) -> ParsedDocument:
    """Word belgesindeki tabloları (w:tbl) okur — TBB 'Banka, Çalışan ve Şube Bilgileri' bazı dönemlerde docx olarak yayımlanır."""
    import io
    import zipfile
    from xml.etree import ElementTree as ET
    doc = ParsedDocument(format="docx")
    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    try:
        xml = zipfile.ZipFile(io.BytesIO(data)).read("word/document.xml")
    except Exception as exc:
        doc.notes.append(f"docx okunamadı: {exc}")
        return doc
    root = ET.fromstring(xml)
    for i, tbl in enumerate(root.iter(f"{{{ns['w']}}}tbl")):
        rows = []
        for tr in tbl.iter(f"{{{ns['w']}}}tr"):
            cells = []
            for tc in tr.findall("w:tc", ns):
                cells.append(" ".join(t.text or "" for t in tc.iter(f"{{{ns['w']}}}t")).strip())
            rows.append(cells)
        if rows:
            width = max(len(r) for r in rows)
            doc.add(f"table{i + 1}", pd.DataFrame([r + [""] * (width - len(r)) for r in rows]))
    if not doc.tables:
        doc.notes.append("docx: tablo bulunamadı")
    return doc


def _excel_default_decrypt(data: bytes) -> bytes | None:
    """Bazı TBB kitapları (ör. Fibabanka Mart 2026 konsolide) Excel'in VARSAYILAN parolasıyla ('VelvetSweatshop') şifrelidir; Excel bunları
    parola sormadan açar. Yalnızca bu varsayılan denenir — başka parola denemesi yapılmaz (erişim kısıtı aşılmaz)."""
    try:
        import msoffcrypto
        f = msoffcrypto.OfficeFile(io.BytesIO(data))
        if not f.is_encrypted():
            return None
        out = io.BytesIO()
        f.load_key(password="VelvetSweatshop")
        f.decrypt(out)
        return out.getvalue()
    except Exception:
        return None


def _parse_xls(data: bytes) -> ParsedDocument:
    import xlrd
    doc = ParsedDocument(format="xls")
    try:
        book = xlrd.open_workbook(file_contents=data, on_demand=True, formatting_info=False)
    except xlrd.biffh.XLRDError as exc:
        if "encrypted" not in str(exc).lower():
            raise
        dec = _excel_default_decrypt(data)
        if dec is None:
            raise ValueError("xls şifreli (Excel varsayılan parolası değil) — kaynaktan şifresiz sürüm beklenir") from exc
        doc.notes.append("xls Excel varsayılan parolasıyla şifreliydi; Excel'in yaptığı gibi saydam açıldı")
        book = xlrd.open_workbook(file_contents=dec, on_demand=True, formatting_info=False)
    for sh in book.sheets():
        rows = [[sh.cell_value(r, c) for c in range(sh.ncols)] for r in range(sh.nrows)]
        doc.add(sh.name, pd.DataFrame(rows))
    return doc


def _parse_xlsx(data: bytes) -> ParsedDocument:
    doc = ParsedDocument(format="xlsx")
    sheets = pd.read_excel(io.BytesIO(data), sheet_name=None, header=None, engine="openpyxl")
    for name, df in sheets.items():
        doc.add(str(name), df)
    return doc


def _parse_csv(data: bytes) -> ParsedDocument:
    doc = ParsedDocument(format="csv")
    text = data.decode("utf-8-sig", errors="replace")
    sep = ";" if text[:2000].count(";") > text[:2000].count(",") else ","
    df = pd.read_csv(io.StringIO(text), sep=sep, header=None, dtype=str, engine="python")
    doc.add("csv", df)
    return doc


def _parse_html(data: bytes) -> ParsedDocument:
    doc = ParsedDocument(format="html")
    try:
        tables = pd.read_html(io.BytesIO(data), header=None, flavor="lxml")
    except ValueError:
        tables = []
    for i, t in enumerate(tables, 1):
        doc.add(f"html_table_{i}", t)
    if not tables:
        doc.notes.append("HTML içinde <table> bulunamadı")
    return doc


def _parse_zip(data: bytes) -> ParsedDocument:
    doc = ParsedDocument(format="zip")
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        for info in z.infolist():
            if info.is_dir():
                continue
            member = z.read(info)
            try:
                inner = parse_bytes(member, info.filename)
            except Exception as exc:             # şifreli/bozuk üye diğer üyeleri engellemez; not düşülür
                doc.notes.append(f"{info.filename}: HATA {type(exc).__name__}: {exc}")
                continue
            for name, df in inner.tables.items():
                doc.add(f"{info.filename}::{name}", df)
            doc.notes.extend(f"{info.filename}: {n}" for n in inner.notes)
    return doc


def _parse_json(data: bytes) -> ParsedDocument:
    doc = ParsedDocument(format="json")
    obj = json.loads(data.decode("utf-8", errors="replace"))
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(v, list) and v and isinstance(v[0], dict):
                doc.add(k, pd.DataFrame(v))
        if not doc.tables:
            doc.add("json", pd.json_normalize(obj))
    elif isinstance(obj, list):
        doc.add("json", pd.DataFrame(obj))
    return doc


def _parse_xml(data: bytes) -> ParsedDocument:
    doc = ParsedDocument(format="xml")
    try:
        doc.add("xml", pd.read_xml(io.BytesIO(data)))
    except Exception as exc:
        doc.notes.append(f"xml okunamadı: {exc}")
    return doc


# --------------------------------------------------------------------------- tablo tarama yardımcıları
def find_cells(df: pd.DataFrame, needle: str, casefold: bool = True) -> list[tuple[int, int]]:
    """Metin içeren hücreleri (satır, sütun) olarak döndürür — başlık/etiket bulmak için."""
    hits = []
    n = needle.casefold() if casefold else needle
    for r in range(df.shape[0]):
        for c in range(df.shape[1]):
            v = df.iat[r, c]
            if isinstance(v, str):
                s = v.casefold() if casefold else v
                if n in s:
                    hits.append((r, c))
    return hits


def to_number(v) -> float | None:
    """'1.234.567,89' / '1,234.5' / '(12)' / '-' gibi kaynak gösterimlerini sayıya çevirir; çevrilemezse None."""
    if v is None:
        return None
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return None if pd.isna(v) else float(v)
    s = str(v).strip()
    if s in ("", "-", "—", "–", "n.a.", "na", "NaN", "nan"):
        return None
    neg = s.startswith("(") and s.endswith(")")
    s = s.strip("()").replace(" ", "").replace("%", "")
    # Kural (TR kaynaklar): nokta binlik, virgül ondalık. Tek ayraç varsa: ayraçtan sonraki tüm gruplar 3 haneliyse binlik,
    # değilse ondalık ("700.000"→700000, "12.07"→12.07, "12,07"→12.07, "1.234.567,89"→1234567.89, "1,234,567.89"→1234567.89).
    if "," in s and "." in s:
        if s.rfind(",") > s.rfind("."):   # 1.234.567,89 (TR)
            s = s.replace(".", "").replace(",", ".")
        else:                              # 1,234,567.89 (EN)
            s = s.replace(",", "")
    elif "," in s:
        parts = s.split(",")
        s = s.replace(",", "") if len(parts) > 2 and all(len(p) == 3 for p in parts[1:]) else s.replace(",", ".")
    elif "." in s:
        parts = s.split(".")
        if all(len(p) == 3 for p in parts[1:]) and parts[0].lstrip("-").isdigit():
            s = s.replace(".", "")
    try:
        x = float(s)
    except ValueError:
        return None
    return -x if neg else x
