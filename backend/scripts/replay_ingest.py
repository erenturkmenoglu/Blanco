"""Çevrimdışı yeniden işleme: 'data' dalındaki ham dosyalar (raw/…) + eski DB'deki URL kayıtlarıyla, ağa çıkmadan TÜM pipeline'ı yeniden çalıştırır.

Ne zaman: ayrıştırma/normalizasyon kodu düzeltildiğinde (ör. DQ01 ölçek hatası) veriyi kaynaktan tekrar indirmeden, aynı ham dosyalardan
temiz bir DB üretmek için. Ham dosyalar değişmez (sha256 aynı); yalnızca türetilmiş gözlemler yeniden yazılır.

Kullanım:
  cd backend && DATABASE_URL=sqlite:///./bilanco_new.db RAW_STORE_DIR=./data/raw \
    python scripts/replay_ingest.py --old-db /path/to/old/bilanco.db --raw /path/to/data-branch/raw --periods 2026-06,2026-03
"""
from __future__ import annotations

import argparse
import hashlib
import logging
import re
import sqlite3
import sys
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.acquisition.downloader import DownloadResult, sniff_format  # noqa: E402

log = logging.getLogger("replay")


class LocalReplayDownloader:
    """URL → yerel ham dosya. Harita: (1) eski DB source_documents(url, local_path); (2) sayfa dosyaları slug ile (raw/tbb_pages/<sha>__<slug>.html)."""

    def __init__(self, old_db: Path, raw_dir: Path):
        self.raw = raw_dir
        self.map: dict[str, Path] = {}
        con = sqlite3.connect(str(old_db))
        for url, lp in con.execute("select url, local_path from source_documents where local_path is not null"):
            p = raw_dir / Path(lp).relative_to("data/raw") if lp.startswith("data/raw/") else raw_dir / Path(lp).name
            if p.exists():
                self.map[url] = p
        self.pages: dict[str, Path] = {}
        for p in (raw_dir / "tbb_pages").glob("*"):
            slug = p.name.split("__", 1)[-1]
            self.pages[slug] = p
        self.calls: list[str] = []
        self.misses: list[str] = []

    def _page(self, url: str) -> Path | None:
        path = urlparse(url).path.rstrip("/")
        slug = path.split("/")[-1]
        for cand in (slug + ".html", slug):
            if cand in self.pages:
                return self.pages[cand]
        # liste sayfaları: /istatistiki-raporlar-liste/<id>?rapor_donemi=.. → kayıtlı değil (keşif kategori sayfasından yürür)
        return None

    def fetch(self, url, dataset_code="misc", expected=None, allow_browser=False):
        self.calls.append(url)
        p = self.map.get(url) or self._page(url)
        if not p:
            self.misses.append(url)
            return DownloadResult(url, None, False, None, None, None, None, None, None, None, error="replay: yerel kopya yok (çevrimdışı)")
        data = p.read_bytes()
        fn = re.sub(r"^[0-9a-f]{12}__", "", p.name)
        return DownloadResult(url, url, True, data, sniff_format(data, fn), None, fn, hashlib.sha256(data).hexdigest(), len(data), str(p))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--old-db", required=True)
    ap.add_argument("--raw", required=True)
    ap.add_argument("--periods", default="2026-06,2026-03")
    ap.add_argument("--datasets", default="")
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    from app.db import get_session, init_db
    from app.pipeline import ingest, seed
    from app.scheduler.jobs import QUARTERLY_DATASETS

    init_db()
    with get_session() as db:
        seed(db)
    dl = LocalReplayDownloader(Path(a.old_db), Path(a.raw))
    log.info("replay haritası: %d dosya, %d sayfa", len(dl.map), len(dl.pages))
    only = {d for d in a.datasets.split(",") if d}
    with get_session() as db:
        for source, dataset, _lag in QUARTERLY_DATASETS:
            if only and dataset not in only:
                continue
            for per in a.periods.split(","):
                y, mo = (int(x) for x in per.split("-"))
                job = ingest(db, source, dataset, y, mo, downloader=dl, trigger="replay")
                print(f"{source} {dataset} {y}-{mo:02d} → {job.status.value} | {job.message}")
    print(f"istekler: {len(dl.calls)}, yerel kopyası olmayan: {len(set(dl.misses))}")
    for u in sorted(set(dl.misses))[:15]:
        print("  eksik:", u)


if __name__ == "__main__":
    main()
