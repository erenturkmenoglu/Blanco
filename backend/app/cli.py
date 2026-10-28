"""Komut satırı: init-db | seed | discover | ingest | verification-table | derived"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

from app.db import get_session, init_db


def main(argv=None):
    p = argparse.ArgumentParser(prog="bilanco")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init-db")
    sub.add_parser("seed")
    d = sub.add_parser("discover"); d.add_argument("--source", default="TBB"); d.add_argument("--dataset", required=True); d.add_argument("--year", type=int, required=True); d.add_argument("--month", type=int, required=True)
    i = sub.add_parser("ingest"); i.add_argument("--source", default="TBB"); i.add_argument("--dataset", required=True); i.add_argument("--year", type=int, required=True); i.add_argument("--month", type=int, required=True)
    v = sub.add_parser("verification-table"); v.add_argument("--out", default="docs/verification_table.md")
    dv = sub.add_parser("derived"); dv.add_argument("--bank", required=True); dv.add_argument("--period", required=True); dv.add_argument("--scope", default="solo")
    a = p.parse_args(argv)

    if a.cmd in ("init-db", "seed"):
        init_db()
        from app.pipeline import seed
        with get_session() as db:
            seed(db)
        print("ok: şema oluşturuldu ve tohum veriler yüklendi")
    elif a.cmd == "discover":
        from app.pipeline import ADAPTERS
        files = ADAPTERS[a.source]().discover(a.dataset, a.year, a.month)
        print(json.dumps([f.__dict__ for f in files], default=str, ensure_ascii=False, indent=2))
    elif a.cmd == "ingest":
        init_db()
        from app.pipeline import ingest, seed
        with get_session() as db:
            seed(db)
            job = ingest(db, a.source, a.dataset, a.year, a.month)
            print(json.dumps({"job": job.id, "status": job.status.value, "message": job.message, "log": job.log}, default=str, ensure_ascii=False, indent=2))
    elif a.cmd == "verification-table":
        from app.verification_findings import render_markdown
        out = Path(a.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(render_markdown(), encoding="utf-8")
        print(f"yazıldı: {out}")
    elif a.cmd == "derived":
        from app.api.routes import derived
        from app.db import SessionLocal
        db = SessionLocal()
        print(json.dumps(derived(a.bank, date.fromisoformat(a.period), a.scope, db), default=str, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
