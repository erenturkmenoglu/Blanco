"""Uçtan uca: sahte indirici → gerçek ayrıştırma/eşleme/doğrulama/kayıt → API (SQLite)."""
from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.acquisition.downloader import DownloadResult
from app.db import get_session
from app.db import models as m
from app.main import app
from app.pipeline import ingest
from tests.fixtures import (CATEGORY_HTML, LIST_HTML, REPORT_HTML, balance_sheet_rows, build_xlsx, income_rows, interest_table_rows,
                            maturity_table_rows)
from app.acquisition.sources.tbb import LIST_URL

XLSX = build_xlsx({"K2 Aktifler": balance_sheet_rows(), "K4 Gelir-Gider": income_rows(), "Faiz": interest_table_rows(), "Vade": maturity_table_rows()})


class FakeDownloader:
    def __init__(self, payload=XLSX):
        self.payload = payload

    def fetch(self, url, dataset_code="misc", expected=None, allow_browser=False):
        pages = {"https://www.tbb.org.tr/istatistiki-raporlar/11232": CATEGORY_HTML,
                 LIST_URL.format(list_id=11241, period_id="11411", month=6): LIST_HTML,
                 "https://www.tbb.org.tr/istatistiki-raporlar/2026-haziran-finansal-tablolar-konsolide-olmayan-solo-banka-excel-formatinda": REPORT_HTML}
        if url in pages:
            d = pages[url].encode()
            return DownloadResult(url, url, True, d, "html", "text/html", None, "h", len(d), None)
        if url.endswith("/310500"):
            import hashlib
            return DownloadResult(url, url, True, self.payload, "xlsx", "application/octet-stream", "fs_solo_2026_06.xlsx",
                                  hashlib.sha256(self.payload).hexdigest(), len(self.payload), None)
        return DownloadResult(url, None, False, None, None, None, None, None, None, None, error="unreachable (fake)")


def test_ingest_end_to_end_and_api():
    with get_session() as db:
        job = ingest(db, "TBB", "tbb_fs_solo_excel", 2026, 6, downloader=FakeDownloader())
        assert job.status.value == "success" and job.observations_count > 0
        doc = db.scalar(select(m.SourceDocument).where(m.SourceDocument.url.endswith("/310500")))
        assert doc.status == "parsed" and doc.format_detected == "xlsx" and doc.sha256
        ziraat = db.scalar(select(m.Institution).where(m.Institution.code == "ziraat"))
        ta = db.scalar(select(m.FinancialObservation).where(m.FinancialObservation.institution_id == ziraat.id, m.FinancialObservation.metric_code == "total_assets"))
        assert ta.value == 1_000_000 * 1e3 and ta.source_scale == 1e3 and ta.verification_status.value == "VERIFIED"
        ni = db.scalar(select(m.FinancialObservation).where(m.FinancialObservation.institution_id == ziraat.id, m.FinancialObservation.metric_code == "net_profit"))
        assert ni.cumulative_ytd is True and ni.period_start == date(2026, 1, 1)
        r = db.scalar(select(m.InterestRateObservation).where(m.InterestRateObservation.institution_id == ziraat.id, m.InterestRateObservation.metric_code == "loan_interest_tl"))
        assert r.value == 12.07 and r.rate_definition == "stock_avg_applied_rate"
        mat = db.scalars(select(m.MaturityObservation).where(m.MaturityObservation.institution_id == ziraat.id)).all()
        assert {x.bucket for x in mat} >= {"demand", "0_1m", "1_3m", "3_12m"} and not {x.bucket for x in mat} & {"3_6m", "6_12m"}
        # aynı dosya tekrar → yeni revizyon yok
        job2 = ingest(db, "TBB", "tbb_fs_solo_excel", 2026, 6, downloader=FakeDownloader())
        assert job2.observations_count == 0
        assert len(doc.revisions) == 1

    c = TestClient(app)
    assert c.get("/health").json()["status"] == "ok"
    banks = c.get("/api/banks").json()
    assert any(b["code"] == "ziraat" and b["observations"] > 0 for b in banks)
    obs = c.get("/api/observations", params={"bank": "ziraat", "metric": "total_assets"}).json()
    assert obs["series"][0]["value"] == 1e9 and obs["series"][0]["source"] == "TBB" and obs["series"][0]["source_url"].endswith("/310500")
    cmp_ = c.get("/api/compare", params={"banks": "ziraat,akbank,isbank,halkbank", "metric": "total_deposits", "period_end": "2026-06-30"}).json()
    rows = {r["bank"]: r for r in cmp_["rows"]}
    assert rows["ziraat"]["rank"] == 1 and rows["halkbank"]["value"] is None and rows["halkbank"]["status"] == "UNAVAILABLE"
    der = c.get("/api/derived", params={"bank": "ziraat", "period_end": "2026-06-30"}).json()
    met = {d["metric"]: d for d in der["metrics"]}
    assert met["loan_to_deposit_ratio"]["value"] is not None and met["assets_growth_yoy"]["value"] is None
    rates = c.get("/api/rates", params={"bank": "ziraat"}).json()
    assert any(s["currency"] == "TRY" and abs(s["spread"] - (12.07 - 21.40)) < 1e-9 for s in rates["spreads"])
    mat = c.get("/api/maturity", params={"bank": "ziraat", "period_end": "2026-06-30", "item": "total_assets"}).json()
    assert "3_12m" in mat["buckets"] and mat["limitations"]
    ver = c.get("/api/verification").json()
    assert ver["columns"][0] == "VERİ ALANI" and len(ver["rows"]) >= 15
    assert c.get("/api/sources").json() and c.get("/api/jobs").json()[0]["status"] in ("success", "partial", "failed")
