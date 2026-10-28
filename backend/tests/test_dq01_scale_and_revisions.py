"""DQ01 (Bin TL / Milyon TL) ve revizyon kuralları — gerçek Akbank Mart 2026 (BİN TÜRK LİRASI) ve Haziran 2026 (MİLYON TÜRK LİRASI) kitaplarıyla.

Bulgu: aynı TBB veri setinde ("Finansal Tablolar – Excel") ölçek dönemden döneme değişir; başlıktan okunmazsa Mart değerleri 1000× büyük yazılır.
"""
from datetime import date
from pathlib import Path

from sqlalchemy import select

from app.acquisition.parsers import parse_bytes
from app.db import get_session
from app.db import models as m
from app.normalization.bank_names import BankRegistry
from app.normalization.scale import detect_scale_in_text
from app.normalization.tbb_bank_workbook import extract_workbook
from app.normalization.tbb_dt20 import extract_dt20_tables
from app.pipeline import _same_value, _upsert, _institution_id, seed

DATA = Path(__file__).resolve().parent / "data" / "tbb_2026_06"


def test_scale_text_rules():
    assert detect_scale_in_text("MİLYON TÜRK LİRASI") == (1e6, "Milyon TL")
    assert detect_scale_in_text("BİN TÜRK LİRASI") == (1e3, "Bin TL")
    assert detect_scale_in_text("Varlıklar, Milyon TL") == (1e6, "Milyon TL")
    assert detect_scale_in_text("(Bin TL)") == (1e3, "Bin TL")
    assert detect_scale_in_text("Tutar (TL)") == (1.0, "TL")
    assert detect_scale_in_text("Milyon Adet") is None            # TL bağlamı yoksa ölçek değildir
    assert detect_scale_in_text("Banka") is None


def _wb(fn: str, bank="Akbank T.A.Ş."):
    parsed = parse_bytes((DATA / fn).read_bytes(), fn)
    return extract_workbook(parsed.tables, bank, BankRegistry(), "solo", "TBB")


def test_workbook_scale_read_from_header_march_bin_tl_vs_june_milyon_tl():
    mar, jun = _wb("fs_solo_akbank_2026_03.zip"), _wb("fs_solo_akbank.zip")
    assert (mar.scale, mar.scale_label) == (1e3, "Bin TL") and (jun.scale, jun.scale_label) == (1e6, "Milyon TL")

    def val(ex, metric, pe, ccy="ALL"):
        return next(o for o in ex.observations if o["metric_code"] == metric and o["period_end"] == pe and o["currency"] == ccy)

    a = val(mar, "total_assets", date(2026, 3, 31))
    assert a["value_raw"] == 3_419_802_978 and a["value"] == 3_419_802_978 * 1e3 and a["scale_detected"] and a["scale"] == 1e3
    # Her iki kitabın 31/12/2025 sütunu aynı tutarı farklı ölçekle verir → normalize değerler %0,01 içinde eşit
    d_mar, d_jun = val(mar, "total_assets", date(2025, 12, 31)), val(jun, "total_assets", date(2025, 12, 31))
    assert abs(d_mar["value"] - d_jun["value"]) / d_jun["value"] < 1e-4
    assert _same_value(d_mar["value"], d_jun["value"])
    # vade kovaları da kitabın ölçeğiyle normalize edilir
    loans = {o["bucket"]: o["value"] for o in mar.observations if o["kind"] == "maturity" and o.get("item") == "loans" and o["period_end"] == date(2026, 3, 31)}
    assert loans["total"] == 1_884_653_992 * 1e3 and loans["3_12m"] == 379_823_593 * 1e3 or abs(loans["3_12m"] - 379.8e9) < 0.2e9
    assert not any("DQ01" in n for n in mar.notes + jun.notes)


def test_dt20_deposit_maturity_total_column_belongs_to_parent_type():
    parsed = parse_bytes((DATA / "dt20_3_pasifler.xls").read_bytes(), "3.Pasifler.xls")
    ex = extract_dt20_tables(parsed.tables, BankRegistry(), date(2026, 6, 30), "solo", "TBB")
    ak = {}
    for o in ex.observations:
        if o["bank_code"] == "akbank" and o["kind"] == "maturity":
            ak.setdefault(o["item"], {})[o["bucket"]] = o["value_raw"]
    assert ak["deposits_fx"] == {"total": 408_323}                     # DTH 'Toplam' alt gruba (Yurtdışı yerleşik) değil türe aittir
    assert "total" not in ak["deposits_fx_nonresident"] and "total" not in ak["deposits_fx_resident"]
    assert sum(ak["deposits_fx_resident"].values()) + sum(ak["deposits_fx_nonresident"].values()) == 408_323
    assert ak["deposits_banks"] == {"total": 107_752} and "total" not in ak["deposits_banks_other"]
    assert all(o["basis"] == "contractual_coarse" for o in ex.observations if o["kind"] == "maturity")
    assert all(o["scale_detected"] and o["scale"] == 1e6 for o in ex.observations if o["unit"] == "TRY")


def test_upsert_tolerance_publication_order_and_scale_conflict_flag():
    with get_session() as db:
        seed(db)
        iid = _institution_id(db, "akbank")
        src = db.scalar(select(m.DataSource).where(m.DataSource.code == "TBB"))
        ds = db.scalar(select(m.Dataset).where(m.Dataset.code == "tbb_fs_solo_excel"))

        def period(pe):
            p = db.scalar(select(m.FinancialPeriod).where(m.FinancialPeriod.period_end == pe, m.FinancialPeriod.frequency == m.Frequency.quarterly))
            if not p:
                p = m.FinancialPeriod(period_start=date(pe.year, pe.month - 2, 1), period_end=pe, frequency=m.Frequency.quarterly, label=f"{pe.year}-{pe.month:02d}")
                db.add(p)
                db.flush()
            return p

        def doc(pe, tag):
            d = m.SourceDocument(dataset_id=ds.id, period_id=period(pe).id, url=f"https://example.test/{tag}", file_name=tag, sha256=tag * 8, status="ok")
            db.add(d)
            db.flush()
            return d

        d_mar, d_jun = doc(date(2026, 3, 31), "mar"), doc(date(2026, 6, 30), "jun")
        key = dict(institution_id=iid, metric_code="zz_test_metric", period_start=date(2025, 12, 31), period_end=date(2025, 12, 31),
                   reporting_scope=m.ReportingScope.solo, currency="ALL", source_id=src.id)
        base = dict(**key, unit="TRY", frequency=m.Frequency.quarterly, period_id=period(date(2025, 12, 31)).id)
        # 1) Haziran kitabından gelen değer (Milyon TL → yuvarlanmış)
        assert _upsert(db, m.FinancialObservation, key, dict(**base, value=2_236_918e6, source_document_id=d_jun.id)) == 1
        # 2) Mart kitabından aynı tutar (Bin TL, daha hassas) → tolerans içinde: revizyon YOK
        assert _upsert(db, m.FinancialObservation, key, dict(**base, value=2_236_916_963e3, source_document_id=d_mar.id)) == 0
        # 3) Daha ESKİ yayından farklı değer → atlanır (yeni yayındaki değer geçerli kalır)
        assert _upsert(db, m.FinancialObservation, key, dict(**base, value=2_100_000e6, source_document_id=d_mar.id)) == 0
        # 4) Aynı/yeni yayından 1000× farklı değer → revizyon + DQ01 kuşku bayrağı
        assert _upsert(db, m.FinancialObservation, key, dict(**base, value=2_236_918e9, source_document_id=d_jun.id)) == 1
        db.flush()
        rows = db.scalars(select(m.FinancialObservation).where(m.FinancialObservation.metric_code == "zz_test_metric").order_by(m.FinancialObservation.revision_no)).all()
        assert [r.revision_no for r in rows] == [1, 2] and "DQ01_scale_conflict_x1000" in rows[1].quality_flags and "revised" in rows[1].quality_flags
        db.rollback()
