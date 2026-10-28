"""Analytics API — her yanıt veri dönemi, birim, kaynak, son güncelleme ve hesaplama yöntemini taşır. Eksik veri 0 olarak dönmez."""
from __future__ import annotations

from datetime import date

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.calc.engine import compute_derived, spread, maturity_shares
from app.db import SessionLocal
from app.db import models as m
from app.dictionary import load as load_dictionary, metric_index
from app.verification_findings import COLUMNS, FINDINGS, QUESTIONS

router = APIRouter(prefix="/api")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _scope(s: str) -> m.ReportingScope:
    try:
        return m.ReportingScope(s)
    except ValueError:
        raise HTTPException(400, f"geçersiz kapsam: {s}")


def _fin_scope(s: str):
    """Finansal gözlem kapsam filtresi: istenen kapsam + kapsamdan bağımsız sayımlar (şube/çalışan: reporting_scope='na')."""
    return m.FinancialObservation.reporting_scope.in_([_scope(s), m.ReportingScope.na])


# ------------------------------------------------------------------ referans
@router.get("/sectors")
def sectors(db: Session = Depends(get_db)):
    return [{"code": s.code, "name": s.name_tr, "enabled": s.module_enabled} for s in db.scalars(select(m.Sector))]


@router.get("/banks")
def banks(db: Session = Depends(get_db)):
    rows = db.scalars(select(m.Institution).where(m.Institution.active == True).order_by(m.Institution.name)).all()  # noqa: E712
    counts = dict(db.execute(select(m.FinancialObservation.institution_id, func.count()).group_by(m.FinancialObservation.institution_id)).all())
    # en güncel solo toplam aktif (Toplam sütunu, son revizyon) — sıralama/varsayılan seçim için; eksikse None (0 yazılmaz)
    ta = {}
    q = (select(m.FinancialObservation).where(m.FinancialObservation.metric_code == "total_assets", m.FinancialObservation.reporting_scope == m.ReportingScope.solo,
                                              m.FinancialObservation.currency == "ALL", m.FinancialObservation.value.is_not(None))
         .order_by(m.FinancialObservation.period_end.desc(), m.FinancialObservation.revision_no.desc()))
    for o in db.scalars(q):
        ta.setdefault(o.institution_id, (o.period_end.isoformat(), o.value))
    return [{"code": b.code, "name": b.name, "short_name": b.short_name, "type": b.institution_type, "ownership": b.ownership_type,
             "observations": counts.get(b.id, 0), "latest_total_assets": ta.get(b.id, (None, None))[1], "latest_total_assets_period": ta.get(b.id, (None, None))[0]}
            for b in rows]


@router.get("/dictionary")
def dictionary():
    return load_dictionary()


@router.get("/periods")
def periods(db: Session = Depends(get_db)):
    rows = db.execute(select(m.FinancialObservation.period_end, m.FinancialObservation.reporting_scope, func.count())
                      .group_by(m.FinancialObservation.period_end, m.FinancialObservation.reporting_scope)
                      .order_by(m.FinancialObservation.period_end.desc())).all()
    return [{"period_end": pe.isoformat(), "scope": sc.value, "observations": n} for pe, sc, n in rows]


# ------------------------------------------------------------------ gözlemler
def _obs_payload(o, inst_code: str, doc_url: str | None, src_code: str) -> dict:
    return {"bank": inst_code, "metric": o.metric_code if hasattr(o, "metric_code") else None, "period_end": o.period_end.isoformat(),
            "period_start": o.period_start.isoformat() if o.period_start else None, "value": o.value, "unit": o.unit, "currency": o.currency,
            "scope": o.reporting_scope.value, "frequency": o.frequency.value, "status": o.verification_status.value, "revision": o.revision_no,
            "source": src_code, "source_url": doc_url, "source_field": o.source_field, "source_sheet": o.source_sheet,
            "retrieved_at": o.retrieved_at.isoformat() if o.retrieved_at else None, "flags": o.quality_flags,
            "cumulative_ytd": getattr(o, "cumulative_ytd", None)}


@router.get("/observations")
def observations(bank: str = Query(...), metric: str = Query(...), scope: str = "solo", db: Session = Depends(get_db)):
    inst = db.scalar(select(m.Institution).where(m.Institution.code == bank))
    if not inst:
        raise HTTPException(404, "banka bulunamadı")
    q = (select(m.FinancialObservation, m.SourceDocument.url, m.DataSource.code)
         .join(m.DataSource, m.DataSource.id == m.FinancialObservation.source_id)
         .outerjoin(m.SourceDocument, m.SourceDocument.id == m.FinancialObservation.source_document_id)
         .where(m.FinancialObservation.institution_id == inst.id, m.FinancialObservation.metric_code == metric,
                _fin_scope(scope))
         .order_by(m.FinancialObservation.period_end, m.FinancialObservation.period_start, m.FinancialObservation.currency, m.FinancialObservation.revision_no.desc()))
    seen, out = set(), []
    for o, url, src in db.execute(q):
        k = (o.period_end, o.period_start, o.currency)      # aynı dönem: TP/YP/Toplam ve YTD/çeyrek ayrı seriler; her biri için en güncel revizyon
        if k in seen:
            continue
        seen.add(k)
        out.append(_obs_payload(o, inst.code, url, src))
    meta = metric_index().get(metric, {})
    return {"bank": inst.code, "metric": metric, "metric_name": meta.get("name_tr"), "kind": meta.get("kind"), "scope": scope, "series": out}


@router.get("/compare")
def compare(banks: str = Query(..., description="virgülle ayrılmış banka kodları"), metric: str = Query(...), period_end: date = Query(...),
            scope: str = "solo", db: Session = Depends(get_db)):
    codes = [c.strip() for c in banks.split(",") if c.strip()]
    insts = {i.code: i for i in db.scalars(select(m.Institution).where(m.Institution.code.in_(codes)))}
    out = []
    for c in codes:
        inst = insts.get(c)
        if not inst:
            out.append({"bank": c, "value": None, "status": "UNAVAILABLE", "note": "banka kaydı yok"})
            continue
        # Toplam sütunu (currency ALL); akış kalemlerinde yıl başından kümülatif satır (en erken period_start); en güncel revizyon
        o = db.scalar(select(m.FinancialObservation).where(m.FinancialObservation.institution_id == inst.id, m.FinancialObservation.metric_code == metric,
                                                            m.FinancialObservation.period_end == period_end, _fin_scope(scope),
                                                            (m.FinancialObservation.currency == "ALL") | (m.FinancialObservation.currency.is_(None)))
                      .order_by(m.FinancialObservation.period_start, m.FinancialObservation.revision_no.desc()))
        out.append({"bank": c, "name": inst.name, "value": o.value if o else None, "unit": o.unit if o else None,
                    "status": o.verification_status.value if o else "UNAVAILABLE", "revision": o.revision_no if o else None})
    ranked = sorted([r for r in out if r["value"] is not None], key=lambda r: r["value"], reverse=True)
    for i, r in enumerate(ranked, 1):
        r["rank"] = i
    return {"metric": metric, "period_end": period_end.isoformat(), "scope": scope, "rows": out}


@router.get("/derived")
def derived(bank: str, period_end: date, scope: str = "solo", db: Session = Depends(get_db)):
    inst = db.scalar(select(m.Institution).where(m.Institution.code == bank))
    if not inst:
        raise HTTPException(404, "banka bulunamadı")
    # Türetilmiş göstergeler yalnızca Toplam sütunundan (currency ALL) ve akışlarda yıl başından kümülatif satırdan (en erken period_start) hesaplanır;
    # TP/YP sütunları ve bağımsız çeyrek satırları karıştırılmaz. Şube/çalışan sayıları (kapsam 'na') istenen kapsama dahil edilir.
    rows = db.execute(select(m.FinancialObservation).where(m.FinancialObservation.institution_id == inst.id, _fin_scope(scope),
                                                           (m.FinancialObservation.currency == "ALL") | (m.FinancialObservation.currency.is_(None)))
                      .order_by(m.FinancialObservation.period_end, m.FinancialObservation.period_start, m.FinancialObservation.revision_no.desc())).scalars().all()
    latest: dict[tuple, m.FinancialObservation] = {}
    for o in rows:
        latest.setdefault((o.metric_code, o.period_end), o)
    df = pd.DataFrame([{"bank_code": inst.code, "metric_code": o.metric_code, "period_end": o.period_end, "value": o.value,
                        "reporting_scope": scope, "cumulative_ytd": o.cumulative_ytd} for o in latest.values()],
                      columns=["bank_code", "metric_code", "period_end", "value", "reporting_scope", "cumulative_ytd"])
    res = compute_derived(df, inst.code, period_end, scope) if len(df) else []
    return {"bank": inst.code, "period_end": period_end.isoformat(), "scope": scope, "status": "DERIVED",
            "metrics": [{"metric": d.metric_code, "value": d.value, "unit": d.unit, "method": d.method, "inputs": d.inputs,
                         "limitations": d.limitations} for d in res]}


@router.get("/rates")
def rates(bank: str, scope: str = "solo", db: Session = Depends(get_db)):
    inst = db.scalar(select(m.Institution).where(m.Institution.code == bank))
    if not inst:
        raise HTTPException(404, "banka bulunamadı")
    q = (select(m.InterestRateObservation, m.SourceDocument.url, m.DataSource.code)
         .join(m.DataSource, m.DataSource.id == m.InterestRateObservation.source_id)
         .outerjoin(m.SourceDocument, m.SourceDocument.id == m.InterestRateObservation.source_document_id)
         .where(m.InterestRateObservation.institution_id == inst.id, m.InterestRateObservation.reporting_scope == _scope(scope))
         .order_by(m.InterestRateObservation.period_end))
    series = []
    by_pe: dict[tuple, dict] = {}
    for o, url, src in db.execute(q):
        p = _obs_payload(o, inst.code, url, src)
        p.update({"instrument": o.instrument, "rate_definition": o.rate_definition})
        series.append(p)
        by_pe[(o.period_end, o.currency, o.instrument)] = {"value": o.value, "rate_definition": o.rate_definition, "currency": o.currency,
                                                           "period_end": o.period_end, "reporting_scope": o.reporting_scope.value}
    spreads = []
    for (pe, cur, ins) in list(by_pe):
        if ins == "loan":
            s = spread(by_pe.get((pe, cur, "loan")), by_pe.get((pe, cur, "deposit")))
            spreads.append({"period_end": pe.isoformat(), "currency": cur, "spread": s.value, "method": s.method, "limitations": s.limitations})
    return {"bank": inst.code, "scope": scope, "series": series, "spreads": spreads,
            "definition_note": "Oranlar kaynaktaki tanımıyla saklanır; farklı tanımlar (stok ort. / yeni açılış / muhasebesel) birbirinin yerine kullanılmaz."}


BASIS_LABELS = {"remaining": "kalan vade (Likidite Riski / malibünye1)", "contractual": "sözleşme vadesi — dipnot 2.a.1.i (9 kova)",
                "contractual_coarse": "sözleşme vadesi — DT20 Mevd.Vade (4 kova: Vadesiz+7g | ≤1 ay | 1-3 ay | 3 ay+)"}
BASIS_PREFERENCE = ["remaining", "contractual", "contractual_coarse"]


def _maturity_block(db: Session, rows: list) -> dict:
    buckets, labels, src = {}, {}, None
    for r in rows:                       # revizyon sırası azalan → ilk görülen en güncel
        if r.bucket in buckets:
            continue
        buckets[r.bucket] = r.value
        labels[r.bucket] = r.bucket_label_raw
        src = src or r
    sh = maturity_shares(buckets, buckets.get("total"), labels)
    doc = db.get(m.SourceDocument, src.source_document_id) if src and src.source_document_id else None
    statuses = {r.verification_status.value for r in rows}
    status = "VERIFIED" if statuses == {"VERIFIED"} else ("UNAVAILABLE" if not rows else "UNVERIFIED" if "UNVERIFIED" in statuses else sorted(statuses)[0])
    return {"basis": rows[0].basis if rows else None, "basis_label": BASIS_LABELS.get(rows[0].basis, rows[0].basis) if rows else None, "buckets": buckets,
            "bucket_labels": labels, "shares": sh.inputs.get("shares"), "illustrative_midpoint_wam_months": sh.inputs.get("illustrative_midpoint_wam_months"),
            "limitations": sh.limitations, "status": status, "source_url": doc.url if doc else None, "source_sheet": src.source_sheet if src else None,
            "retrieved_at": src.retrieved_at.isoformat() if src and src.retrieved_at else None, "revision": max(r.revision_no for r in rows) if rows else None}


@router.get("/maturity")
def maturity(bank: str, period_end: date, item: str = "total_assets", scope: str = "solo", basis: str | None = None, db: Session = Depends(get_db)):
    """Bir kalemin vade dağılımı. Aynı kalem için farklı KOVA KÜMELERİ (kalan vade / dipnot sözleşme vadesi / DT20 kaba sözleşme vadesi)
    ayrı 'bases' altında döner; birleştirilmez. Üst düzey alanlar tercih edilen (veya istenen) temelin kopyasıdır."""
    inst = db.scalar(select(m.Institution).where(m.Institution.code == bank))
    if not inst:
        raise HTTPException(404, "banka bulunamadı")
    rows = db.scalars(select(m.MaturityObservation).where(m.MaturityObservation.institution_id == inst.id, m.MaturityObservation.period_end == period_end,
                                                          m.MaturityObservation.item == item, m.MaturityObservation.reporting_scope == _scope(scope))
                      .order_by(m.MaturityObservation.revision_no.desc())).all()
    by_basis: dict[str, list] = {}
    for r in rows:
        by_basis.setdefault(r.basis, []).append(r)
    bases = {b: _maturity_block(db, rs) for b, rs in by_basis.items()}
    pref = basis if basis in bases else next((b for b in BASIS_PREFERENCE if b in bases), None)
    top = bases.get(pref) or {"basis": None, "basis_label": None, "buckets": {}, "bucket_labels": {}, "shares": None, "illustrative_midpoint_wam_months": None,
                              "limitations": None, "status": "UNAVAILABLE", "source_url": None, "source_sheet": None, "retrieved_at": None, "revision": None}
    return {"bank": inst.code, "period_end": period_end.isoformat(), "item": item, **top, "bases": bases,
            "note": "Kaynağın kendi vade kovaları korunur; 3-12 ay yapay bölünmez; farklı kova kümeleri birleştirilmez. Toplam aktif/pasif dağılımı kredi/mevduat dağılımı DEĞİLDİR."}


@router.get("/maturity/items")
def maturity_items(bank: str, period_end: date, scope: str = "solo", db: Session = Depends(get_db)):
    """Bu banka/dönem için vade gözlemi olan kalemler ve temelleri (UI seçici için)."""
    inst = db.scalar(select(m.Institution).where(m.Institution.code == bank))
    if not inst:
        raise HTTPException(404, "banka bulunamadı")
    rows = db.execute(select(m.MaturityObservation.item, m.MaturityObservation.basis, func.count()).where(
        m.MaturityObservation.institution_id == inst.id, m.MaturityObservation.period_end == period_end, m.MaturityObservation.reporting_scope == _scope(scope),
        m.MaturityObservation.value.is_not(None)).group_by(m.MaturityObservation.item, m.MaturityObservation.basis)).all()
    out: dict[str, list] = {}
    for item, basis, n in rows:
        out.setdefault(item, []).append({"basis": basis, "basis_label": BASIS_LABELS.get(basis, basis), "observations": n})
    return {"bank": inst.code, "period_end": period_end.isoformat(), "items": out}


# ------------------------------------------------------------------ kaynaklar / durum
@router.get("/sources")
def sources(db: Session = Depends(get_db)):
    out = []
    for s in db.scalars(select(m.DataSource)):
        ds = db.scalars(select(m.Dataset).where(m.Dataset.source_id == s.id)).all()
        out.append({"code": s.code, "name": s.name, "base_url": s.base_url, "access_method": s.access_method, "robots_note": s.robots_note,
                    "datasets": [{"code": d.code, "name": d.name, "frequency": d.frequency.value, "scope": d.reporting_scope.value,
                                  "per_institution": d.per_institution, "discovery_url": d.discovery_url, "url_pattern": d.url_pattern,
                                  "formats": d.expected_formats, "publication_lag_days": d.publication_lag_days, "status": d.status.value,
                                  "status_note": d.status_note, "last_checked_at": d.last_checked_at.isoformat() if d.last_checked_at else None} for d in ds]})
    return out


@router.get("/verification")
def verification():
    return {"columns": COLUMNS, "rows": FINDINGS, "questions": [{"q": q, "a": a} for q, a in QUESTIONS]}


@router.get("/jobs")
def jobs(limit: int = 50, db: Session = Depends(get_db)):
    rows = db.scalars(select(m.DataIngestionJob).order_by(m.DataIngestionJob.started_at.desc()).limit(limit)).all()
    ds = {d.id: d.code for d in db.scalars(select(m.Dataset))}
    return [{"id": j.id, "dataset": ds.get(j.dataset_id), "period": j.period_label, "status": j.status.value, "trigger": j.trigger,
             "started_at": j.started_at.isoformat() if j.started_at else None, "finished_at": j.finished_at.isoformat() if j.finished_at else None,
             "documents": j.documents_count, "observations": j.observations_count, "message": j.message, "log": j.log} for j in rows]


@router.get("/quality")
def quality(limit: int = 200, db: Session = Depends(get_db)):
    rows = db.scalars(select(m.DataQualityCheck).order_by(m.DataQualityCheck.created_at.desc()).limit(limit)).all()
    return [{"job_id": c.job_id, "check": c.check_code, "severity": c.severity, "passed": c.passed, "metric": c.metric_code,
             "period_end": c.period_end.isoformat() if c.period_end else None, "message": c.message, "at": c.created_at.isoformat()} for c in rows]


@router.get("/documents")
def documents(limit: int = 100, db: Session = Depends(get_db)):
    rows = db.scalars(select(m.SourceDocument).order_by(m.SourceDocument.last_checked_at.desc().nullslast()).limit(limit)).all()
    ds = {d.id: d.code for d in db.scalars(select(m.Dataset))}
    return [{"id": d.id, "dataset": ds.get(d.dataset_id), "url": d.url, "file_name": d.file_name, "format": d.format_detected, "sha256": d.sha256,
             "size": d.size_bytes, "status": d.status, "error": d.error, "retrieved_at": d.retrieved_at.isoformat() if d.retrieved_at else None,
             "sheets": d.sheets} for d in rows]


class RunJob(BaseModel):
    source: str = "TBB"
    dataset: str
    year: int
    month: int


@router.post("/jobs/run")
def run_job(body: RunJob, db: Session = Depends(get_db)):
    from app.pipeline import ingest
    job = ingest(db, body.source, body.dataset, body.year, body.month, trigger="api")
    return {"id": job.id, "status": job.status.value, "message": job.message, "log": job.log}
