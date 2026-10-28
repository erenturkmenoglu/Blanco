"""Uçtan uca veri toplama hattı: keşif → indirme → ayrıştırma → eşleme → doğrulama → kayıt.

İlkeler: ham dosya değiştirilmez; başarısızlık nedeniyle loglanır; bloklanan gözlem yazılmaz; önceki doğrulanmış veri bozulmaz;
aynı sha256 tekrar indirildiğinde yeni revizyon AÇILMAZ, farklı sha256 → yeni revizyon.
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.acquisition.parsers import parse_bytes
from app.acquisition.sources import SourceAdapter
from app.acquisition.sources.bddk import BDDKAdapter
from app.acquisition.sources.evds import EVDSAdapter
from app.acquisition.sources.tbb import TBBAdapter
from app.config import settings
from app.db import models as m
from app.dictionary import metric_index
from app.normalization.bank_names import SEED_BANKS, BankRegistry
from app.normalization.mapping import map_table
from app.normalization.periods import quarter_period, ytd_period
from app.normalization.special_tables import map_interest_table, map_maturity_table
from app.normalization.tbb_bank_workbook import extract_workbook
from app.normalization.tbb_dt20 import extract_dt20_tables
from app.validation.checks import apply_checks, run_checks
from app.verification_findings import FINDINGS

log = logging.getLogger("bilanco.pipeline")

ADAPTERS: dict[str, type[SourceAdapter]] = {"TBB": TBBAdapter, "BDDK": BDDKAdapter, "EVDS": EVDSAdapter}
SOURCES = [
    ("TBB", "Türkiye Bankalar Birliği", "https://www.tbb.org.tr", "http_get", "verisistemi.tbb.org.tr robots.txt otomatik erişimi yasaklıyor; www.tbb.org.tr ekleri düz GET."),
    ("BDDK", "Bankacılık Düzenleme ve Denetleme Kurumu", "https://www.bddk.org.tr", "http_get", "Bültenler banka bazında değil (grup/sektör)."),
    ("TCMB", "Türkiye Cumhuriyet Merkez Bankası", "https://www.tcmb.gov.tr", "http_get", None),
    ("EVDS", "TCMB Elektronik Veri Dağıtım Sistemi", "https://evds3.tcmb.gov.tr", "api_key", "Anahtar ortam değişkeninden."),
]


def now() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------- tohum
def seed(db: Session) -> None:
    if not db.scalar(select(m.Sector).where(m.Sector.code == "banks")):
        db.add(m.Sector(code="banks", name_tr="Bankalar", module_enabled=True))
        for code, name in (("retail", "Perakende"), ("energy", "Enerji"), ("technology", "Teknoloji"), ("industry", "Sanayi"), ("supermarkets", "Süpermarket zincirleri")):
            db.add(m.Sector(code=code, name_tr=name, module_enabled=False))
        db.flush()
    banks = db.scalar(select(m.Sector).where(m.Sector.code == "banks"))
    for code, (name, btype, own, aliases) in SEED_BANKS.items():
        inst = db.scalar(select(m.Institution).where(m.Institution.code == code))
        if not inst:
            inst = m.Institution(code=code, name=name, short_name=aliases[0], institution_type=btype, ownership_type=own)
            db.add(inst)
            db.flush()
            db.add(m.InstitutionSectorMembership(institution_id=inst.id, sector_id=banks.id))
            from app.normalization.bank_names import normalize_name
            for a in [name, *aliases]:
                db.add(m.InstitutionAlias(institution_id=inst.id, alias_normalized=normalize_name(a), alias_raw=a, source_code=None))
    for code, name, url, method, note in SOURCES:
        if not db.scalar(select(m.DataSource).where(m.DataSource.code == code)):
            db.add(m.DataSource(code=code, name=name, base_url=url, access_method=method, robots_note=note))
    db.flush()
    src_ids = {s.code: s.id for s in db.scalars(select(m.DataSource))}
    for AdapterCls in ADAPTERS.values():
        for spec in AdapterCls().datasets():
            ds = db.scalar(select(m.Dataset).where(m.Dataset.code == spec.code))
            if not ds:
                ds = m.Dataset(source_id=src_ids[spec.source_code], code=spec.code, name=spec.name, frequency=m.Frequency(spec.frequency),
                               reporting_scope=m.ReportingScope(spec.reporting_scope), per_institution=spec.per_institution,
                               discovery_url=spec.discovery_url, url_pattern=spec.url_pattern, expected_formats=spec.expected_formats,
                               publication_lag_days=spec.publication_lag_days, status=m.VerificationStatus(spec.status), status_note=spec.status_note)
                db.add(ds)
    db.flush()
    ds_ids = {d.code: d.id for d in db.scalars(select(m.Dataset))}
    for f in FINDINGS:
        ds_id = ds_ids.get(f["dataset"])
        if not ds_id:
            continue
        exists = db.scalar(select(m.DatasetField).where(m.DatasetField.dataset_id == ds_id, m.DatasetField.metric_code == f["field"][:64],
                                                        m.DatasetField.source_field == f["cells"][:512],
                                                        m.DatasetField.verified_period == f["period"][:16]))
        if not exists:
            db.add(m.DatasetField(dataset_id=ds_id, metric_code=f["field"][:64], source_field=f["cells"][:512],
                                  per_institution=f["per_bank"].lower().startswith("evet"), verified_period=f["period"][:16],
                                  status=m.VerificationStatus(f["status"]), note=f["note"], verified_at=now() if f["status"] == "VERIFIED" else None))
    db.commit()


# ---------------------------------------------------------------------------- yardımcılar
def _registry(db: Session) -> BankRegistry:
    reg = BankRegistry()
    for a in db.scalars(select(m.InstitutionAlias)):
        inst = db.get(m.Institution, a.institution_id)
        if inst:
            reg.add_alias(a.alias_raw, inst.code)
    return reg


def _institution_id(db: Session, code: str) -> int | None:
    inst = db.scalar(select(m.Institution).where(m.Institution.code == code))
    return inst.id if inst else None


def _period_id(db: Session, pe: date, freq: str, label: str, ps: date) -> int:
    p = db.scalar(select(m.FinancialPeriod).where(m.FinancialPeriod.period_end == pe, m.FinancialPeriod.frequency == m.Frequency(freq)))
    if not p:
        p = m.FinancialPeriod(period_start=ps, period_end=pe, frequency=m.Frequency(freq), label=label)
        db.add(p)
        db.flush()
    return p.id


# ---------------------------------------------------------------------------- hat
def ingest(db: Session, source_code: str, dataset_code: str, year: int, month: int, trigger: str = "manual",
           downloader=None, force: bool = False) -> m.DataIngestionJob:
    """Bir veri seti + dönem için tam döngü: keşif → indirme → ayrıştırma → eşleme → doğrulama → yazım. force=True yakın zamanda kontrol edilmiş dosyaları da yeniden indirir."""
    ds = db.scalar(select(m.Dataset).where(m.Dataset.code == dataset_code))
    job = m.DataIngestionJob(dataset_id=ds.id if ds else None, period_label=f"{year}-{month:02d}", trigger=trigger, log=[])
    db.add(job)
    db.flush()
    adapter = ADAPTERS[source_code](downloader) if downloader else ADAPTERS[source_code]()
    src = db.scalar(select(m.DataSource).where(m.DataSource.code == source_code))
    reg = _registry(db)
    mi = metric_index()
    logs: list[dict] = []
    n_docs = n_obs = n_parse_errors = n_confirmed = n_skipped = 0
    try:
        files = adapter.discover(dataset_code, year, month)
        logs.append({"step": "discover", "found": len(files), "urls": [f.url for f in files]})
        if not files:
            logs.append({"step": "discover", "result": "bağlantı bulunamadı", "reason": "liste/kategori sayfası alınamadı veya dönem yayımlanmamış"})
        for f in files:
            doc = db.scalar(select(m.SourceDocument).where(m.SourceDocument.url == f.url))
            pe = f.period_end or date(year, month, 28)
            per = quarter_period(year, month) if month in (3, 6, 9, 12) else None
            pid = _period_id(db, per.end, "quarterly", per.label, per.start) if per else None
            if (doc and doc.status == "parsed" and doc.sha256 and doc.last_checked_at and not force
                    and (now() - doc.last_checked_at.replace(tzinfo=doc.last_checked_at.tzinfo or timezone.utc)) < timedelta(days=settings.recheck_days)):
                n_skipped += 1          # yakın zamanda doğrulanmış dosya: yeniden indirilmez (revizyon kontrolü recheck_days'de bir)
                logs.append({"step": "skip", "url": f.url, "reason": f"{settings.recheck_days} gün içinde kontrol edildi; sha {doc.sha256[:12]}"})
                continue
            res = adapter.fetch(f)
            logs.append({"step": "download", "url": f.url, "ok": res.ok, "format": res.format_detected, "attempts": res.as_log(), "error": res.error})
            if not doc:
                doc = m.SourceDocument(dataset_id=ds.id, period_id=pid, url=f.url, file_name=f.file_name or f.title)
                db.add(doc)
                db.flush()
            doc.last_checked_at = now()
            if not res.ok:
                doc.status, doc.error = "failed", res.error
                db.add(m.DataQualityCheck(job_id=job.id, check_code="DQ14_file_integrity", severity="error", passed=False,
                                          message=f"indirilemedi: {res.error}", period_end=pe))
                continue
            if doc.sha256 and doc.sha256 != res.sha256:
                rev_no = (max((r.revision_no for r in doc.revisions), default=0) + 1)
                db.add(m.SourceRevision(source_document_id=doc.id, revision_no=rev_no, sha256=res.sha256, note="kaynak dosya değişti"))
                logs.append({"step": "revision", "url": f.url, "revision_no": rev_no})
            elif not doc.sha256:
                db.add(m.SourceRevision(source_document_id=doc.id, revision_no=1, sha256=res.sha256, note="ilk indirme"))
            doc.sha256, doc.size_bytes, doc.local_path = res.sha256, res.size_bytes, res.local_path
            doc.format_detected, doc.content_type_declared, doc.retrieved_at = res.format_detected, res.content_type, now()
            doc.file_name = res.file_name or doc.file_name
            doc.status = "downloaded"
            n_docs += 1
            try:
                parsed = parse_bytes(res.data, res.file_name, res.format_detected)
            except Exception as exc:          # tek dosya (şifreli xls, bozuk zip, desteklenmeyen docx…) işi düşürmez: ERROR olarak kaydedilir, devam edilir
                doc.status, doc.error = "failed", f"{type(exc).__name__}: {exc}"
                n_parse_errors += 1
                logs.append({"step": "parse", "url": f.url, "result": "ERROR", "error": doc.error})
                db.add(m.DataQualityCheck(job_id=job.id, check_code="DQ14_file_integrity", severity="error", passed=False,
                                          institution_id=_institution_id(db, reg.match(f.bank_raw)[0]) if f.bank_raw and reg.match(f.bank_raw)[1] >= 0.92 else None,
                                          message=f"ayrıştırılamadı ({f.file_name or f.url}): {doc.error}", period_end=pe))
                continue
            doc.sheets = parsed.inventory
            logs.append({"step": "parse", "url": f.url, "format": parsed.format, "tables": list(parsed.inventory), "notes": parsed.notes})
            if parsed.format in ("docx", "unsupported") or not parsed.tables:
                logs.append({"step": "parse", "url": f.url, "result": f"{parsed.format}: tablo çıkarılamadı (yapılandırılmış sürüm aranmalı)", "notes": parsed.notes})
                doc.status = "parsed"
                continue
            if parsed.format == "pdf":
                logs.append({"step": "parse", "url": f.url, "result": "PDF: yapılandırılmış sürüm (xls) aranmalı; PDF tablo çıkarımı ayrı aşama"})
                doc.status = "parsed"
                continue
            cands = _candidates(parsed, reg, mi, dataset_code, ds.reporting_scope.value, per, source_code, bank_hint=f.bank_raw)
            logs.append({"step": "map", "url": f.url, "candidates": len(cands["obs"]), "unmapped_labels": cands["unmapped"][:50],
                         "unmatched_banks": cands["unmatched"][:50], "orientation": cands["orientation"], "scale": cands["scale"]})
            checks = run_checks(cands["obs"], raw_bytes=res.data, reporting_scope=ds.reporting_scope.value, frequency=ds.frequency.value)
            for c in checks:
                if not c.passed or c.severity != "info":
                    db.add(m.DataQualityCheck(job_id=job.id, check_code=c.code, severity=c.severity, passed=c.passed,
                                              institution_id=_institution_id(db, c.bank) if c.bank else None, metric_code=c.metric,
                                              period_end=c.period_end, message=c.message))
            kept, dropped = apply_checks(cands["obs"], checks)
            logs.append({"step": "validate", "url": f.url, "kept": len(kept), "dropped": dropped,
                         "errors": sorted({c.message for c in checks if not c.passed and c.severity == "error"})[:20]})
            if not kept:
                doc.status = "parsed"
                continue
            c0 = db.info.get("confirmed", 0)
            n_obs += _write(db, kept, src.id, doc.id, pid)
            n_confirmed += db.info.get("confirmed", 0) - c0
            doc.status = "parsed"
        if n_docs:
            job.status = m.JobStatus.success if (n_obs or n_confirmed) and not n_parse_errors else m.JobStatus.partial
        else:
            job.status = m.JobStatus.success if n_skipped else m.JobStatus.failed     # tüm dosyalar yakın zamanda doğrulanmış → değişiklik yok, başarılı
    except Exception as exc:   # hat kırılmaz; hata kaydedilir
        log.exception("ingest hatası")
        job.status = m.JobStatus.failed
        logs.append({"step": "exception", "error": f"{type(exc).__name__}: {exc}"})
    job.documents_count, job.observations_count, job.log, job.finished_at = n_docs, n_obs, logs, now()
    job.message = f"{n_docs} dosya, {n_obs} gözlem" + (f" (+{n_confirmed} mevcut gözlemle aynı değer; teyit)" if n_confirmed else "") + \
        (f", {n_parse_errors} dosya ayrıştırılamadı" if n_parse_errors else "") + (f", {n_skipped} dosya yakın zamanda doğrulanmış (atlandı)" if n_skipped else "")
    logs.append({"step": "summary", "documents": n_docs, "new_observations": n_obs, "confirmed_existing": n_confirmed, "parse_errors": n_parse_errors, "skipped_recent": n_skipped})
    db.commit()
    return job


def _candidates(parsed, reg, mi, dataset_code, scope, per, source_code, bank_hint: str | None = None) -> dict:
    out = {"obs": [], "unmapped": [], "unmatched": [], "orientation": None, "scale": None}
    # Gerçek düzeni doğrulanmış TBB setleri için özel çıkarıcılar
    if dataset_code in ("tbb_dt20_selected_solo", "tbb_dt21_selected_cons") and per:
        ex = extract_dt20_tables(parsed.tables, reg, per.end, scope, source_code)
        out["obs"] = ex.observations
        out["unmapped"], out["unmatched"], out["orientation"] = ex.unmapped_columns, ex.unmatched_banks, "dt20_wide"
        out["scale"] = next((o.get("scale") for o in ex.observations if o.get("scale_detected") and o.get("unit") == "TRY"), None)
        out["notes"] = ex.notes
        return out
    if dataset_code in ("tbb_fs_solo_excel", "tbb_fs_cons_excel") and bank_hint:
        ex = extract_workbook(parsed.tables, bank_hint, reg, scope, source_code)
        out["obs"] = ex.observations
        out["unmapped"], out["orientation"], out["scale"] = ex.unmapped_labels, "bank_workbook", ex.scale
        out["notes"] = ex.notes
        out["unmatched"] = [n for n in ex.notes if n.startswith("banka eşlenemedi")]
        return out
    for name, df in parsed.tables.items():
        pe, ps = (per.end, per.start) if per else (None, None)
        # özel tablolar (bulunursa genel eşleyici bu sayfaya uygulanmaz)
        special_found = False
        for sr in map_interest_table(df, reg):
            special_found = True
            if sr.bank_match == "aggregate":
                continue
            out["obs"].append(dict(bank_raw=sr.bank_raw, bank_code=sr.bank_code, bank_match=sr.bank_match, metric_code=sr.key["metric_code"],
                                   period_end=pe, period_start=pe, value=sr.value, unit="pct", scale=1.0, currency=sr.key["currency"],
                                   reporting_scope=scope, frequency="quarterly", source_code=source_code, rate_definition=sr.key["rate_definition"],
                                   instrument=sr.key["instrument"], sheet=name, row=sr.row, col=sr.col, kind="rate"))
        for sr in map_maturity_table(df, reg):
            special_found = True
            if sr.bank_match == "aggregate":
                continue
            out["obs"].append(dict(bank_raw=sr.bank_raw, bank_code=sr.bank_code, bank_match=sr.bank_match, metric_code=f"maturity:{sr.key['item']}",
                                   period_end=pe, period_start=pe, value=(sr.value * 1e6) if sr.value is not None else None, unit="TRY",
                                   scale=1e6, currency="ALL", reporting_scope=scope, frequency="quarterly", source_code=source_code,
                                   bucket=sr.key["bucket"], bucket_label_raw=sr.key["bucket_label_raw"], item=sr.key["item"], basis="remaining",
                                   sheet=name, row=sr.row, col=sr.col, kind="maturity"))
        if special_found:
            continue
        # genel tablo
        mr = map_table(df, reg, bank_hint=bank_hint, period_hint=per)
        out["orientation"] = out["orientation"] or mr.orientation
        out["scale"] = out["scale"] or mr.scale
        out["unmapped"].extend(mr.unmapped_labels)
        out["unmatched"].extend(mr.unmatched_banks)
        for o in mr.observations:
            if o.bank_match == "aggregate":
                continue
            meta = mi.get(o.metric_code, {})
            unit = meta.get("unit", "TRY")
            cum = bool(meta.get("cumulative_ytd")) if meta.get("kind") == "flow" else None
            if getattr(o, "period", None):            # tek banka düzeni: sütundan gelen dönem
                pe, ps = o.period.end, o.period.start
            # akış: kümülatifse yıl başı, değilse çeyrek başı; STOK (bilanço) kalemi nokta-zaman → period_start = period_end
            p_start = ytd_period(pe.year, pe.month).start if (cum and pe) else (ps if meta.get("kind") == "flow" else pe)
            val = None
            if o.value_raw is not None:
                val = o.value_raw * (o.scale or 1.0) if unit == "TRY" else o.value_raw
            out["obs"].append(dict(bank_raw=o.bank_raw, bank_code=o.bank_code, bank_match=o.bank_match, metric_code=o.metric_code,
                                   period_end=pe, period_start=p_start, value=val, value_raw=o.value_raw, unit=unit, scale=o.scale,
                                   currency=(getattr(o, "currency", None) or meta.get("currency", "ALL")), reporting_scope=scope, frequency="quarterly", source_code=source_code,
                                   cumulative_ytd=cum if meta.get("kind") == "flow" else False, sheet=name, row=o.row, col=o.col, kind="financial",
                                   label_raw=o.label_raw))
    return out


def _write(db: Session, obs: list[dict], source_id: int, doc_id: int, pid: int | None) -> int:
    """Yazılan YENİ satır sayısını döner; aynı değerle teyit edilen (atlanan) satırlar db.info['confirmed'] sayacına eklenir."""
    n = 0
    before = db.info.get("confirmed", 0)
    for o in obs:
        if not o.get("bank_code"):
            continue
        iid = _institution_id(db, o["bank_code"])
        if not iid:
            continue
        status = m.VerificationStatus.VERIFIED if o.get("value") is not None else m.VerificationStatus.UNAVAILABLE
        flags: list[str] = []
        if o.get("value") is not None and o.get("unit") == "TRY" and o.get("scale_detected") is False:
            status = m.VerificationStatus.UNVERIFIED              # DQ01: ölçek başlıktan okunamadı → doğrulanmış sayılmaz
            flags.append("DQ01_scale_not_found")
        common = dict(institution_id=iid, period_start=o.get("period_start"), period_end=o["period_end"], value_raw=o.get("value_raw", o.get("value")),
                      source_scale=o.get("scale") or 1.0, value=o.get("value"), unit=o["unit"], currency=o.get("currency"),
                      frequency=m.Frequency(o["frequency"]), reporting_scope=m.ReportingScope(o["reporting_scope"]), source_field=o.get("label_raw") or o.get("metric_code"),
                      source_sheet=o.get("sheet"), source_row=o.get("row"), source_col=o.get("col"), retrieved_at=now(), verification_status=status,
                      source_id=source_id, source_document_id=doc_id, quality_flags=flags or None)
        if o["kind"] == "rate":
            key = dict(institution_id=iid, metric_code=o["metric_code"], period_end=o["period_end"], reporting_scope=common["reporting_scope"],
                       rate_definition=o["rate_definition"], source_id=source_id)
            n += _upsert(db, m.InterestRateObservation, key, dict(**common, instrument=o["instrument"], rate_definition=o["rate_definition"], metric_code=o["metric_code"]))
        elif o["kind"] == "maturity":
            key = dict(institution_id=iid, item=o["item"], basis=o["basis"], bucket=o["bucket"], currency=o.get("currency"), period_end=o["period_end"],
                       reporting_scope=common["reporting_scope"], source_id=source_id)
            n += _upsert(db, m.MaturityObservation, key, dict(**common, item=o["item"], basis=o["basis"], bucket=o["bucket"], bucket_label_raw=o.get("bucket_label_raw")))
        else:
            key = dict(institution_id=iid, metric_code=o["metric_code"], period_start=o.get("period_start"), period_end=o["period_end"],
                       reporting_scope=common["reporting_scope"], currency=o.get("currency"), source_id=source_id)
            n += _upsert(db, m.FinancialObservation, key, dict(**common, metric_code=o["metric_code"], period_id=pid, cumulative_ytd=bool(o.get("cumulative_ytd"))))
    db.flush()
    db.info.get("pending_obs", {}).clear()
    return n


REVISION_REL_TOL = 1e-4      # %0,01: Bin TL ↔ Milyon TL yuvarlama farkı revizyon sayılmaz


def _same_value(a, b) -> bool:
    if a is None or b is None:
        return a is b
    return abs(a - b) <= max(1e-9, REVISION_REL_TOL * max(abs(a), abs(b)))


def _doc_meta(db: Session, doc_id: int | None) -> tuple[date | None, str | None]:
    """(veri seti dönemi, veri seti kodu). Dönem yayın sırası içindir: Haziran 2026 kitabındaki 31/12/2025 sütunu Mart 2026 kitabındakinden yeni yayındır.
    Önbellek oturuma bağlıdır (db.info): belge kimlikleri geri alınan işlemlerden sonra yeniden kullanılabilir."""
    if doc_id is None:
        return None, None
    cache: dict = db.info.setdefault("doc_meta", {})
    if doc_id not in cache:
        d = db.get(m.SourceDocument, doc_id)
        per = db.get(m.FinancialPeriod, d.period_id) if d and d.period_id else None
        ds = db.get(m.Dataset, d.dataset_id) if d else None
        cache[doc_id] = (per.period_end if per else None, ds.code if ds else None)
    return cache[doc_id]


def _doc_period_end(db: Session, doc_id: int | None):
    return _doc_meta(db, doc_id)[0]


def _upsert(db: Session, Model, key: dict, values: dict) -> int:
    """Aynı doğal anahtar:
    - aynı değer (tolerans içinde) → atla;
    - daha ESKİ bir yayından gelen farklı değer → atla (yeni yayındaki yeniden ifade edilmiş değer geçerli kalır);
    - daha yeni/aynı yayından farklı değer → yeni revizyon satırı (eski satır KORUNUR; ~1000× fark DQ01 kuşkusu olarak işaretlenir)."""
    pending: dict = db.info.setdefault("pending_obs", {})       # oturum autoflush=False: aynı toplu yazımda eklenen satırlar da görülsün
    pkey = (Model.__tablename__, tuple(sorted((k, str(v)) for k, v in key.items())))
    latest = pending.get(pkey)
    if latest is None:
        stmt = select(Model)
        for k, v in key.items():
            stmt = stmt.where(getattr(Model, k) == v)
        latest = db.scalars(stmt.order_by(Model.revision_no.desc()).limit(1)).first()
    if latest is not None:
        if _same_value(latest.value, values.get("value")):
            db.info["confirmed"] = db.info.get("confirmed", 0) + 1      # başka kaynak/dosya aynı değeri teyit etti; satır yinelenmez
            return 0
        (old_pub, old_ds), (new_pub, new_ds) = _doc_meta(db, latest.source_document_id), _doc_meta(db, values.get("source_document_id"))
        if old_pub and new_pub and new_pub < old_pub:
            return 0
        flags = list(values.get("quality_flags") or [])
        # Aynı tanım, aynı dönem, FARKLI veri seti (ör. DT20 'Likidite Riski' ↔ banka kitabı dipnotu) → revizyon değil kaynak çelişkisi;
        # iki satır da korunur, sonuncu (birincil kaynak en son işlenir) öne çıkar, bayrak UI'da gösterilir
        flags.append(f"source_conflict:{old_ds}->{new_ds}" if (old_ds and new_ds and old_ds != new_ds) else "revised")
        a, b = latest.value, values.get("value")
        if a and b and (900 <= abs(b / a) <= 1100 or 900 <= abs(a / b) <= 1100):
            flags.append("DQ01_scale_conflict_x1000")
        values = {**values, "revision_no": latest.revision_no + 1, "quality_flags": flags}
    obj = Model(**{"revision_no": 1, **values})
    db.add(obj)
    pending[pkey] = obj
    return 1
