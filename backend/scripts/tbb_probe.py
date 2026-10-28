"""TBB keşif/indirme probu — ağı olan bir ortamda (GitHub Actions runner) çalışır.

Amaç: gerçek dosyaları indirip AÇMAK ve envanterini (sayfa adları, başlık satırları, satır etiketleri) kaydetmek.
Çıktı: --out dizini altında robots.txt, alınan HTML sayfaları, indirilen dosyalar ve summary.json / summary.md.
Hiçbir şey tahmin edilmez: açılamayan dosya 'ERROR' nedeniyle, bulunamayan bağlantı nedeniyle raporlanır.

Kullanım: cd backend && python scripts/tbb_probe.py --year 2026 --month 6 --out ../probe_output [--banks "Akbank T.A.Ş.;Türkiye Cumhuriyeti Ziraat Bankası A.Ş."]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.acquisition.downloader import Downloader  # noqa: E402
from app.acquisition.parsers import parse_bytes  # noqa: E402
from app.acquisition.sources.tbb import (BASE, CATEGORY_ANALYSIS, CATEGORY_FS, CATEGORY_SELECTED, LIST_URL, MONTH_TR, SECTIONS,  # noqa: E402
                                         TBBAdapter, quarter_end)
from app.normalization.bank_names import BankRegistry  # noqa: E402
from app.normalization.mapping import map_label  # noqa: E402

PROBE_DATASETS = ["tbb_fs_solo_excel", "tbb_asset_ranking", "tbb_dt20_selected_solo", "tbb_maturity_remaining", "tbb_dt13_bank_branch_employee"]


def inventory(data: bytes, file_name: str | None, fmt: str | None) -> dict:
    doc = parse_bytes(data, file_name, fmt)
    out = {"format": doc.format, "notes": doc.notes, "sheets": {}}
    for name, df in doc.tables.items():
        head = []
        for r in range(min(14, len(df))):
            head.append([("" if (x is None or (isinstance(x, float) and x != x)) else str(x))[:60] for x in df.iloc[r].tolist()[:14]])
        # etiket sütunu: en çok metin içeren sütun
        best_c, best_n = 0, -1
        for c in range(df.shape[1]):
            n = sum(1 for r in range(df.shape[0]) if isinstance(df.iat[r, c], str) and df.iat[r, c].strip())
            if n > best_n:
                best_c, best_n = c, n
        labels = [df.iat[r, best_c].strip() for r in range(df.shape[0]) if isinstance(df.iat[r, best_c], str) and df.iat[r, best_c].strip()][:120]
        mapped = {lab: map_label(lab) for lab in labels}
        out["sheets"][name] = {"rows": int(df.shape[0]), "cols": int(df.shape[1]), "head": head, "label_col": best_c, "labels": labels,
                               "mapped_labels": {k: v for k, v in mapped.items() if v}, "unmapped_count": sum(1 for v in mapped.values() if not v)}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", type=int, default=2026)
    ap.add_argument("--month", type=int, default=6)
    ap.add_argument("--out", default="../probe_output")
    ap.add_argument("--banks", default="Akbank T.A.Ş.;Türkiye Cumhuriyeti Ziraat Bankası A.Ş.")
    ap.add_argument("--max-files", type=int, default=12)
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    (out / "pages").mkdir(exist_ok=True); (out / "files").mkdir(exist_ok=True)
    dl = Downloader(raw_dir=out / "files")
    ad = TBBAdapter(dl)
    summary: dict = {"run_at": datetime.now(timezone.utc).isoformat(), "year": a.year, "month": a.month,
                     "robots_policy": os.getenv("ROBOTS_POLICY", "strict"), "steps": [], "files": [], "selector": None}
    pe = quarter_end(a.year, a.month)

    def step(name: str, **kw):
        kw["step"] = name
        summary["steps"].append(kw)
        print(f"[{name}] " + json.dumps({k: v for k, v in kw.items() if k != 'step'}, ensure_ascii=False, default=str)[:600], flush=True)

    # 0) robots.txt (politikadan bağımsız düz okuma)
    try:
        import httpx
        r = httpx.get(f"{BASE}/robots.txt", timeout=30, headers=dl.headers, follow_redirects=True)
        (out / "robots.txt").write_text(r.text, encoding="utf-8")
        step("robots", status=r.status_code, first_lines=r.text.splitlines()[:40])
    except Exception as exc:
        step("robots", error=f"{type(exc).__name__}: {exc}")

    # 1) kategori sayfaları → dönem id'leri
    period_ids: dict[str, dict] = {}
    for cat in (CATEGORY_FS, CATEGORY_ANALYSIS, CATEGORY_SELECTED):
        res = dl.fetch(cat, dataset_code="tbb_pages", expected="html")
        if res.ok:
            html = res.data.decode("utf-8", errors="replace")
            (out / "pages" / (cat.rsplit("/", 1)[-1] + ".html")).write_text(html, encoding="utf-8")
            forms = TBBAdapter.parse_period_options(html)
            period_ids[cat] = forms
            step("category", url=cat, sections={k: {"list_id": v["list_id"], "years": dict(list(v["years"].items())[:4]), "months": v["months"]} for k, v in forms.items()})
        else:
            step("category", url=cat, error=res.error, attempts=res.as_log())

    # 2) her veri seti için keşif + indirme
    n_files = 0
    for ds in PROBE_DATASETS:
        files = ad.discover(ds, a.year, a.month)
        step("discover", dataset=ds, found=[{"url": f.url, "title": f.title, "strategy": f.strategy, "bank": f.bank_raw} for f in files][:60])
        # rapor sayfasını da sakla (seçici incelemesi için)
        for f in files:
            if f.report_page and not (out / "pages" / (re.sub(r"[^\w-]", "_", f.report_page.rsplit('/', 1)[-1]) + ".html")).exists():
                pr = dl.fetch(f.report_page, dataset_code="tbb_pages", expected="html")
                if pr.ok:
                    html = pr.data.decode("utf-8", errors="replace")
                    (out / "pages" / (re.sub(r"[^\w-]", "_", f.report_page.rsplit('/', 1)[-1]) + ".html")).write_text(html, encoding="utf-8")
                    if ds.endswith("_excel"):
                        summary["selector"] = TBBAdapter.parse_bank_selector(html)
                        step("selector", options=len(summary["selector"]["options"]), first=summary["selector"]["options"][:3],
                             select_name=summary["selector"]["select_name"], form_action=summary["selector"]["form_action"], js_hints=summary["selector"]["js_hints"][:3])
        # banka bazlı excel: yalnızca istenen bankalar
        wanted = [b.strip() for b in a.banks.split(";") if b.strip()]
        if ds.endswith("_excel"):
            files = [f for f in files if (f.bank_raw in wanted) or f.strategy == "attachment"]
        for f in files:
            if n_files >= a.max_files:
                step("limit", note=f"max-files={a.max_files} aşıldı; kalanlar atlandı")
                break
            res = ad.fetch(f)
            rec = {"dataset": ds, "url": f.url, "bank": f.bank_raw, "strategy": f.strategy, "ok": res.ok, "format": res.format_detected,
                   "content_type": res.content_type, "file_name": res.file_name, "sha256": res.sha256, "size": res.size_bytes,
                   "local_path": res.local_path, "error": res.error, "attempts": res.as_log()}
            n_files += 1
            if res.ok and res.format_detected in ("xls", "xlsx", "zip", "csv", "html"):
                try:
                    rec["inventory"] = inventory(res.data, res.file_name, res.format_detected)
                except Exception as exc:
                    rec["inventory_error"] = f"{type(exc).__name__}: {exc}"
            elif res.ok and res.format_detected == "pdf":
                rec["inventory"] = {"format": "pdf", "note": "PDF — tablo çıkarımı ayrı aşama; xls sürümü aranmalı"}
            summary["files"].append(rec)
            step("download", dataset=ds, url=f.url, ok=res.ok, format=res.format_detected, size=res.size_bytes, error=res.error,
                 sheets=list(rec.get("inventory", {}).get("sheets", {}).keys())[:20] if rec.get("inventory") else None)
            time.sleep(1.0)

    (out / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    # kısa markdown özet
    lines = [f"# TBB probe {a.year}-{a.month:02d} ({summary['run_at']}, robots_policy={summary['robots_policy']})", ""]
    for rec in summary["files"]:
        lines.append(f"## {rec['dataset']} — {rec.get('bank') or ''} {rec['url']}")
        lines.append(f"- ok={rec['ok']} format={rec['format']} size={rec['size']} error={rec['error']}")
        inv = rec.get("inventory") or {}
        for sh, info in (inv.get("sheets") or {}).items():
            lines.append(f"- sheet `{sh}` {info['rows']}x{info['cols']} — etiket sütunu {info['label_col']}, eşlenen {len(info['mapped_labels'])}, eşlenmeyen {info['unmapped_count']}")
            for row in info["head"][:8]:
                lines.append("  - " + " | ".join(row[:10]))
    (out / "summary.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines)[:12000])


if __name__ == "__main__":
    main()
