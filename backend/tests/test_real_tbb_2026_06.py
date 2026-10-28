"""Gerçek Haziran 2026 TBB dosyalarıyla uçtan uca: keşif → indirme (replay) → ayrıştırma → eşleme → doğrulama → DB → API."""
from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db import get_session
from app.db import models as m
from app.main import app
from app.pipeline import ingest
from tests.replay import ReplayDownloader


def _ingest(code):
    with get_session() as db:
        return ingest(db, "TBB", code, 2026, 6, downloader=ReplayDownloader(), trigger="test-real")


def test_dt20_real_files_all_banks():
    job = _ingest("tbb_dt20_selected_solo")
    assert job.status.value == "success" and job.documents_count == 6, job.log
    with get_session() as db:
        zi = db.scalar(select(m.Institution).where(m.Institution.code == "ziraat"))
        ta = db.scalar(select(m.FinancialObservation).where(m.FinancialObservation.institution_id == zi.id, m.FinancialObservation.metric_code == "total_assets",
                                                            m.FinancialObservation.period_end == date(2026, 6, 30), m.FinancialObservation.currency == "ALL"))
        assert ta.value == 9_076_507 * 1e6 and ta.source_scale == 1e6          # Aktif Büyüklük sıralaması ile aynı
        n_banks = db.scalar(select(m.FinancialObservation.institution_id).where(m.FinancialObservation.metric_code == "total_assets").distinct().count()) if False else None
        rates = db.scalars(select(m.InterestRateObservation).where(m.InterestRateObservation.institution_id == zi.id)).all()
        r = {x.metric_code: x.value for x in rates}
        assert r["loan_interest_tl"] == 42.04 and r["deposit_interest_tl"] == 38.85 and r["loan_interest_usd"] == 7.45 and r["deposit_interest_eur"] == 0.68
        assert all(x.rate_definition == "stock_avg_applied_rate" for x in rates)
        mats = db.scalars(select(m.MaturityObservation).where(m.MaturityObservation.institution_id == zi.id, m.MaturityObservation.item == "total_assets")).all()
        assert {x.bucket for x in mats} == {"demand", "0_1m", "1_3m", "3_12m", "1_5y", "over_5y", "unallocated", "total"}
        dep = {x.bucket: x.value for x in db.scalars(select(m.MaturityObservation).where(m.MaturityObservation.institution_id == zi.id, m.MaturityObservation.item == "deposits_savings"))}
        assert dep["total"] == 1_825_216 * 1e6 and "over_3m" in dep and "3_6m" not in dep     # DT20 Mevd.Vade: 3 ay+ tek kova
        ak = db.scalar(select(m.Institution).where(m.Institution.code == "akbank"))
        car = db.scalar(select(m.FinancialObservation).where(m.FinancialObservation.institution_id == ak.id, m.FinancialObservation.metric_code == "capital_adequacy_ratio"))
        assert abs(car.value - 17.475) < 0.01 and car.unit == "pct"


def test_bank_workbook_real_files_maturity_detail():
    job = _ingest("tbb_fs_solo_excel")
    assert job.documents_count == 2, job.log      # yalnızca Akbank + Ziraat zip'leri çevrimdışı mevcut; diğer 55 banka 'adres kayıtlı değil' ile loglanır
    with get_session() as db:
        ak = db.scalar(select(m.Institution).where(m.Institution.code == "akbank"))
        loans = {x.bucket: x.value for x in db.scalars(select(m.MaturityObservation).where(m.MaturityObservation.institution_id == ak.id, m.MaturityObservation.item == "loans",
                                                                                           m.MaturityObservation.period_end == date(2026, 6, 30)))}
        assert loans["0_1m"] == 727_559 * 1e6 and loans["3_12m"] == 476_967 * 1e6 and loans["total"] == 2_061_098 * 1e6
        dep = {x.bucket: x.value for x in db.scalars(select(m.MaturityObservation).where(m.MaturityObservation.institution_id == ak.id, m.MaturityObservation.item == "deposits_total",
                                                                                         m.MaturityObservation.basis == "contractual", m.MaturityObservation.period_end == date(2026, 6, 30)))}
        assert dep["3_6m"] == 91_970 * 1e6 and dep["6_12m"] == 71_832 * 1e6 and dep["total"] == 2_382_280 * 1e6
        tl = db.scalar(select(m.FinancialObservation).where(m.FinancialObservation.institution_id == ak.id, m.FinancialObservation.metric_code == "loans_gross",
                                                            m.FinancialObservation.currency == "TRY", m.FinancialObservation.period_end == date(2026, 6, 30)))
        assert tl.value == 1_517_781 * 1e6
        q2 = db.scalar(select(m.FinancialObservation).where(m.FinancialObservation.institution_id == ak.id, m.FinancialObservation.metric_code == "net_interest_income",
                                                            m.FinancialObservation.period_start == date(2026, 4, 1)))
        ytd = db.scalar(select(m.FinancialObservation).where(m.FinancialObservation.institution_id == ak.id, m.FinancialObservation.metric_code == "net_interest_income",
                                                             m.FinancialObservation.period_start == date(2026, 1, 1), m.FinancialObservation.currency == "ALL"))
        assert q2.value == 42_576 * 1e6 and ytd.value == 83_173 * 1e6 and ytd.cumulative_ytd and not q2.cumulative_ytd
        jpy = db.scalar(select(m.InterestRateObservation).where(m.InterestRateObservation.institution_id == ak.id, m.InterestRateObservation.metric_code == "deposit_interest_jpy"))
        assert jpy.value == 0.04


def test_ranking_real_file_generic_mapper_and_api():
    job = _ingest("tbb_asset_ranking")
    summary = next(l for l in job.log if l.get("step") == "summary")
    # DT20 ve banka kitapları önce işlendiği için sıralama dosyasındaki Toplam Aktifler çoğunlukla MEVCUT değerle aynıdır → teyit, yeni satır değil
    assert job.status.value == "success" and summary["new_observations"] + summary["confirmed_existing"] > 50, job.log
    c = TestClient(app)
    cmp_ = c.get("/api/compare", params={"banks": "ziraat,vakifbank,isbank,akbank", "metric": "total_assets", "period_end": "2026-06-30"}).json()
    rows = {r["bank"]: r for r in cmp_["rows"]}
    assert rows["ziraat"]["rank"] == 1 and rows["vakifbank"]["rank"] == 2 and rows["isbank"]["rank"] == 3
    rates = c.get("/api/rates", params={"bank": "ziraat"}).json()
    assert any(s["currency"] == "TRY" and abs(s["spread"] - (42.04 - 38.85)) < 1e-9 for s in rates["spreads"])
    mat = c.get("/api/maturity", params={"bank": "akbank", "period_end": "2026-06-30", "item": "loans"}).json()
    assert mat["buckets"]["3_12m"] == 476_967 * 1e6 and mat["shares"]["0_1m"] > 0.3
    der = c.get("/api/derived", params={"bank": "akbank", "period_end": "2026-06-30"}).json()
    met = {d["metric"]: d for d in der["metrics"]}
    assert met["npl_ratio"]["value"] is not None and met["loan_to_deposit_ratio"]["value"] is not None


def test_second_run_skips_recently_verified_files_and_force_rechecks():
    """Günlük zamanlayıcı: 7 gün içinde doğrulanmış dosya yeniden indirilmez (kaynağa nazik); force=True ile yeniden kontrol edilir ve aynı sha → revizyon yok."""
    with get_session() as db:
        dl = ReplayDownloader()
        job = ingest(db, "TBB", "tbb_asset_ranking", 2026, 6, downloader=dl, trigger="test-rerun")
        summary = next(l for l in job.log if l.get("step") == "summary")
        assert job.status.value == "success" and summary["skipped_recent"] == 1 and summary["documents"] == 0, job.log
        assert not any(u.endswith("/310010") for u in dl.calls)          # dosya indirilmedi
        dl2 = ReplayDownloader()
        job2 = ingest(db, "TBB", "tbb_asset_ranking", 2026, 6, downloader=dl2, trigger="test-force", force=True)
        s2 = next(l for l in job2.log if l.get("step") == "summary")
        assert job2.status.value == "success" and s2["documents"] == 1 and s2["new_observations"] == 0 and s2["confirmed_existing"] > 50, job2.log
        assert any(u.endswith("/310010") for u in dl2.calls)
        assert not any(l.get("step") == "revision" for l in job2.log)      # aynı sha256 → kaynak revizyonu açılmaz
