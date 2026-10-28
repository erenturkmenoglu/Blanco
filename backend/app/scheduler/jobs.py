"""Zamanlanmış veri kontrolleri (APScheduler).

Sistem her gün çalışır ama kaynakları GERÇEK yayın takvimine göre kontrol eder (TBB İstatistiki Rapor Yayınlama Takvimi):
- Üç aylık banka bazlı yayınlar: Mar/Haz/Eyl dönem sonundan itibaren 45 gün (solo) / 75 gün (konsolide); Aralık → Nisan sonu / Haziran.
- Dönem yayımlanmamışsa (bağlantı yok) mevcut doğrulanmış veri korunur; deneme ve nedeni loglanır.
- Aynı dosya (sha256) tekrar görülürse yeni revizyon açılmaz.
"""
from __future__ import annotations

import logging
from datetime import date, timedelta

from app.config import settings
from app.db import get_session, init_db
from app.pipeline import ingest, seed

log = logging.getLogger("bilanco.scheduler")

QUARTERLY_DATASETS = [   # (source, dataset, yayın gecikmesi gün)
    ("TBB", "tbb_fs_solo_excel", 45), ("TBB", "tbb_dt20_selected_solo", 45), ("TBB", "tbb_maturity_remaining", 45),
    ("TBB", "tbb_asset_ranking", 45), ("TBB", "tbb_dt13_bank_branch_employee", 15),
    ("TBB", "tbb_fs_cons_excel", 75), ("TBB", "tbb_dt21_selected_cons", 75), ("TBB", "tbb_bank_group_quarterly", 75),
    ("BDDK", "bddk_tbs_temel_gostergeler", 60),
]


def quarters_due(today: date, lag_days: int, lookback_quarters: int = 2) -> list[tuple[int, int]]:
    """Yayın gecikmesi dolmuş son `lookback_quarters` çeyrek (dönem sonu + gecikme <= bugün)."""
    out = []
    y, m = today.year, ((today.month - 1) // 3) * 3
    if m == 0:
        y, m = y - 1, 12
    for _ in range(lookback_quarters + 2):
        pe = date(y, m, {3: 31, 6: 30, 9: 30, 12: 31}[m])
        lag = lag_days if m != 12 else max(lag_days, 120)   # Aralık dönemi Nisan sonu
        if pe + timedelta(days=lag) <= today:
            out.append((y, m))
        m -= 3
        if m <= 0:
            m, y = 12, y - 1
    return out[:lookback_quarters]


def run_quarterly_checks(today: date | None = None) -> None:
    today = today or date.today()
    with get_session() as db:
        for source, dataset, lag in QUARTERLY_DATASETS:
            for (y, mo) in quarters_due(today, lag):
                job = ingest(db, source, dataset, y, mo, trigger="scheduler")
                log.info("%s %s %d-%02d → %s (%s)", source, dataset, y, mo, job.status.value, job.message)


def main():
    init_db()
    with get_session() as db:
        seed(db)
    if not settings.scheduler_enabled:
        log.warning("SCHEDULER_ENABLED=false; tek seferlik kontrol çalıştırılıyor")
        run_quarterly_checks()
        return
    from apscheduler.schedulers.blocking import BlockingScheduler
    sch = BlockingScheduler(timezone=settings.scheduler_timezone)
    sch.add_job(run_quarterly_checks, "cron", hour=6, minute=30, id="quarterly_checks")   # her gün 06:30 (yerel)
    log.info("zamanlayıcı başladı (%s)", settings.scheduler_timezone)
    sch.start()


if __name__ == "__main__":
    main()
