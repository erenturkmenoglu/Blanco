"""Statik web verisi dışa aktarımı — API yanıtlarını JSON dosyalarına yazar (Vercel'de backend olmadan çalışan arayüz için).

Çıktı düzeni (frontend/public/data/ altına açılır):
  banks.json, periods.json, sources.json, verification.json, jobs.json, quality.json, documents.json, dictionary.json, meta.json
  bank/<code>_<scope>.json  → {series: {metric: [...]}, derived: {period_end: [...]}, rates: {...}, maturity: {period_end: {item: {...}}}}
Aynı API fonksiyonları (TestClient) kullanılır → şekiller birebir API ile aynıdır; eksik veri 0 yazılmaz.
Kullanım: cd backend && DATABASE_URL=sqlite:///./bilanco.db python scripts/export_static.py --out ../frontend/public/data [--tar ../web-data.tar.gz]
"""
from __future__ import annotations

import argparse
import json
import sys
import tarfile
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="../frontend/public/data")
    ap.add_argument("--tar", default=None)
    a = ap.parse_args()
    out = Path(a.out)
    (out / "bank").mkdir(parents=True, exist_ok=True)

    from fastapi.testclient import TestClient
    from sqlalchemy import select
    from app.db import get_session
    from app.db import models as m
    from app.main import app

    c = TestClient(app)

    def dump(name: str, obj):
        (out / name).write_text(json.dumps(obj, ensure_ascii=False, separators=(",", ":"), default=str), encoding="utf-8")

    def get(path, **params):
        r = c.get(path, params=params)
        r.raise_for_status()
        return r.json()

    for name, path in [("banks.json", "/api/banks"), ("periods.json", "/api/periods"), ("sources.json", "/api/sources"), ("verification.json", "/api/verification"),
                       ("jobs.json", "/api/jobs?limit=100"), ("quality.json", "/api/quality?limit=500"), ("documents.json", "/api/documents?limit=300"),
                       ("dictionary.json", "/api/dictionary")]:
        dump(name, get(path))

    banks = get("/api/banks")
    periods = get("/api/periods")
    n_files = 0
    with get_session() as db:
        insts = {i.code: i.id for i in db.scalars(select(m.Institution))}
        for b in banks:
            iid = insts[b["code"]]
            for scope in ("solo", "consolidated"):
                sc = m.ReportingScope(scope)
                metrics = sorted({r[0] for r in db.execute(select(m.FinancialObservation.metric_code).where(m.FinancialObservation.institution_id == iid,
                                                                                                           m.FinancialObservation.reporting_scope == sc).distinct())})
                pes = sorted({r[0] for r in db.execute(select(m.FinancialObservation.period_end).where(m.FinancialObservation.institution_id == iid,
                                                                                                      m.FinancialObservation.reporting_scope == sc).distinct())})
                items = sorted({r[0] for r in db.execute(select(m.MaturityObservation.item).where(m.MaturityObservation.institution_id == iid,
                                                                                                 m.MaturityObservation.reporting_scope == sc).distinct())})
                mpes = sorted({r[0] for r in db.execute(select(m.MaturityObservation.period_end).where(m.MaturityObservation.institution_id == iid,
                                                                                                      m.MaturityObservation.reporting_scope == sc).distinct())})
                if not metrics and not items:
                    continue
                bf = {"bank": b["code"], "scope": scope, "series": {}, "derived": {}, "rates": None, "maturity": {}}
                for met in metrics:
                    bf["series"][met] = get("/api/observations", bank=b["code"], metric=met, scope=scope)["series"]
                for pe in pes:
                    bf["derived"][pe.isoformat()] = get("/api/derived", bank=b["code"], period_end=pe.isoformat(), scope=scope)["metrics"]
                bf["rates"] = get("/api/rates", bank=b["code"], scope=scope)
                for pe in mpes:
                    bf["maturity"][pe.isoformat()] = {it: get("/api/maturity", bank=b["code"], period_end=pe.isoformat(), item=it, scope=scope) for it in items}
                dump(f"bank/{b['code']}_{scope}.json", bf)
                n_files += 1
    dump("meta.json", {"exported_at": datetime.now(timezone.utc).isoformat(), "banks": len(banks), "bank_files": n_files, "periods": periods[:12], "mode": "static-snapshot"})
    total = sum(p.stat().st_size for p in out.rglob("*.json"))
    print(f"export: {n_files} banka dosyası, toplam {total / 1e6:.1f} MB → {out}")
    if a.tar:
        with tarfile.open(a.tar, "w:gz") as t:
            t.add(out, arcname="data")
        print(f"tar: {a.tar} ({Path(a.tar).stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
