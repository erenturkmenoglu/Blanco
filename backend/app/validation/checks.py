"""Data Validation Layer — proje belgesi §13'teki 14 zorunlu kontrol.

Girdi: normalize edilmiş gözlem adayları (dict listesi) + bağlam. Çıktı: CheckResult listesi.
Kural: bir kontrol başarısız olduğunda ÖNCEKİ doğrulanmış veri bozulmaz; aday gözlem `blocked` olarak işaretlenir
(severity=error) veya bayraklanır (severity=warn). Hiçbir eksik değer 0'a çevrilmez.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import date

from app.dictionary import metric_index

STATUSES = {"VERIFIED", "DERIVED", "UNVERIFIED", "UNAVAILABLE", "ERROR"}
RATE_DEFINITIONS = {"stock_avg_applied_rate", "new_business_flow_rate", "accounting_yield", "accounting_cost"}
MATURITY_BUCKETS = {"demand", "demand_7d", "notice_7d", "0_1m", "1_3m", "3_6m", "6m_1y", "6_12m", "3_12m", "over_3m", "1_5y", "over_5y", "over_1y", "unallocated", "accumulating", "total"}
FREQS = {"daily", "weekly", "monthly", "quarterly", "annual"}


@dataclass
class CheckResult:
    code: str
    passed: bool
    severity: str = "error"
    message: str | None = None
    bank: str | None = None
    metric: str | None = None
    period_end: date | None = None

    def as_dict(self) -> dict:
        return self.__dict__.copy()


def run_checks(observations: list[dict], *, raw_bytes: bytes | None = None, expected_sha256: str | None = None,
               existing_keys: set[tuple] | None = None, prior_values: dict[tuple, float] | None = None,
               reporting_scope: str | None = None, frequency: str | None = None) -> list[CheckResult]:
    res: list[CheckResult] = []
    mi = metric_index()
    existing_keys = existing_keys or set()
    prior_values = prior_values or {}

    # DQ14 kaynak dosya bütünlüğü
    if raw_bytes is not None:
        if not raw_bytes:
            res.append(CheckResult("DQ14_file_integrity", False, "error", "boş dosya"))
        elif expected_sha256 and hashlib.sha256(raw_bytes).hexdigest() != expected_sha256:
            res.append(CheckResult("DQ14_file_integrity", False, "error", "sha256 beklenenle uyuşmuyor"))
        else:
            res.append(CheckResult("DQ14_file_integrity", True, "info"))

    seen = set()
    by_bank_period: dict[tuple, dict[str, float]] = {}
    for o in observations:
        bank, metric, pe = o.get("bank_code"), o.get("metric_code"), o.get("period_end")
        # DQ01 banka adı
        if not bank:
            res.append(CheckResult("DQ01_bank_name", False, "error", f"banka eşlenemedi: {o.get('bank_raw')!r}", o.get("bank_raw"), metric, pe))
            continue
        if o.get("bank_match") == "fuzzy":
            res.append(CheckResult("DQ01_bank_name", True, "warn", f"benzerlikle eşlendi: {o.get('bank_raw')!r}→{bank}", bank, metric, pe))
        # DQ02 dönem
        if not isinstance(pe, date) or pe > date.today():
            res.append(CheckResult("DQ02_period", False, "error", f"geçersiz dönem: {pe}", bank, metric, pe if isinstance(pe, date) else None))
            continue
        # DQ03 para birimi
        cur = o.get("currency")
        if cur not in (None, "TRY", "USD", "EUR", "JPY", "GBP", "CHF", "FX", "ALL", "OTHER"):
            res.append(CheckResult("DQ03_currency", False, "error", f"tanımsız para birimi {cur}", bank, metric, pe))
        # DQ04 birim/ölçek
        unit = o.get("unit")
        if o.get("value") is not None and unit == "TRY" and not o.get("scale"):
            res.append(CheckResult("DQ04_unit_scale", False, "error", "ölçek (TL/Bin TL/Milyon TL) kaynaktan okunamadı — gözlem bloklandı", bank, metric, pe))
        if unit == "pct" and o.get("value") is not None and abs(o["value"]) > 500:
            res.append(CheckResult("DQ04_unit_scale", False, "error", f"yüzde alanı için olağan dışı değer {o['value']} (ondalık/yüzde karışıklığı?)", bank, metric, pe))
        if unit == "ratio" and o.get("value") is not None and abs(o["value"]) > 5:
            res.append(CheckResult("DQ04_unit_scale", False, "warn", f"oran alanı için olağan dışı değer {o['value']}", bank, metric, pe))
        # DQ05 solo/konsolide
        sc = o.get("reporting_scope") or reporting_scope
        if sc not in ("solo", "consolidated", "sector", "na"):
            res.append(CheckResult("DQ05_scope", False, "error", f"raporlama kapsamı belirsiz: {sc}", bank, metric, pe))
        # DQ07 yinelenen
        key = (bank, metric, o.get("period_start"), pe, sc, cur, o.get("source_code"), o.get("rate_definition"), o.get("bucket"), o.get("item"))
        if key in seen:
            res.append(CheckResult("DQ07_duplicate", False, "error", "aynı dosyada yinelenen gözlem", bank, metric, pe))
        seen.add(key)
        if key in existing_keys:
            res.append(CheckResult("DQ10_revision", True, "info", "mevcut gözlem; değer farklıysa yeni revizyon açılır", bank, metric, pe))
        # DQ08 eksik veri
        if o.get("value") is None:
            res.append(CheckResult("DQ08_missing", True, "warn", "değer yok — UNAVAILABLE olarak işaretlenir, 0 yazılmaz", bank, metric, pe))
        # DQ09 aykırı değer: önceki döneme göre >10x / <0.1x
        prev = prior_values.get((bank, metric, sc))
        if prev and o.get("value") not in (None, 0) and prev not in (0, None):
            ratio = abs(o["value"] / prev)
            if ratio > 10 or ratio < 0.1:
                res.append(CheckResult("DQ09_outlier", True, "warn", f"önceki döneme göre {ratio:.1f}x (ölçek hatası olabilir)", bank, metric, pe))
        # DQ11 faiz tanımı
        if metric in mi and mi[metric].get("kind") == "rate":
            if o.get("rate_definition") not in RATE_DEFINITIONS:
                res.append(CheckResult("DQ11_rate_definition", False, "error", "faiz oranı tanımı belirtilmemiş (stok ort. / yeni açılış / muhasebesel)", bank, metric, pe))
        # DQ12 vade sınıflandırması
        if o.get("bucket") is not None and o["bucket"] not in MATURITY_BUCKETS:
            res.append(CheckResult("DQ12_maturity_bucket", False, "error", f"tanımsız vade kovası {o['bucket']}", bank, metric, pe))
        if o.get("bucket") in ("3_6m", "6_12m") and o.get("bucket_label_raw") and "3-12" in o["bucket_label_raw"]:
            res.append(CheckResult("DQ12_maturity_bucket", False, "error", "3-12 ay kovası yapay olarak bölünmüş", bank, metric, pe))
        # DQ13 frekans
        fq = o.get("frequency") or frequency
        if fq not in FREQS:
            res.append(CheckResult("DQ13_frequency", False, "error", f"frekans belirsiz: {fq}", bank, metric, pe))
        if metric in mi and mi[metric].get("cumulative_ytd") and o.get("cumulative_ytd") is None:
            res.append(CheckResult("DQ13_frequency", False, "error", "gelir tablosu kaleminde kümülatif/çeyrek bilgisi yok", bank, metric, pe))
        # bilanço tutarlılığı için biriktir
        if o.get("value") is not None and sc in ("solo", "consolidated") and cur in (None, "ALL") and o.get("period_start") in (None, pe):
            by_bank_period.setdefault((bank, pe, sc), {})[metric] = o["value"]

    # DQ06 bilanço tutarlılığı: aktif ≈ pasif(+özkaynak) ; TL+YP ≈ toplam
    for (bank, pe, sc), vals in by_bank_period.items():
        ta, tl, te = vals.get("total_assets"), vals.get("total_liabilities"), vals.get("total_equity")
        if ta and tl:
            rhs = tl if (te is None or abs(tl - ta) < abs(tl + te - ta)) else tl + te
            if abs(ta - rhs) / abs(ta) > 0.005:
                res.append(CheckResult("DQ06_balance", False, "error", f"aktif {ta:.0f} ≠ pasif {rhs:.0f} (fark {abs(ta - rhs) / abs(ta):.2%})", bank, "total_assets", pe))
            else:
                res.append(CheckResult("DQ06_balance", True, "info", None, bank, "total_assets", pe))
        for tot, parts in (("loans_gross", ("loans_tl", "loans_fx")), ("total_deposits", ("deposits_tl", "deposits_fx"))):
            if vals.get(tot) and all(vals.get(p) is not None for p in parts):
                s = sum(vals[p] for p in parts)
                if abs(s - vals[tot]) / abs(vals[tot]) > 0.01:
                    res.append(CheckResult("DQ06_balance", False, "warn", f"{tot}: TP+YP={s:.0f} ≠ toplam {vals[tot]:.0f}", bank, tot, pe))
    return res


def blocked(results: list[CheckResult]) -> bool:
    return any((not r.passed) and r.severity == "error" for r in results)


FILE_LEVEL = {"DQ14_file_integrity"}


def apply_checks(observations: list[dict], results: list[CheckResult]) -> tuple[list[dict], int]:
    """Satır düzeyinde filtre: dosya düzeyi hata → hiçbir şey yazılmaz; banka/dönem düzeyi hata (DQ01/DQ06/DQ04-ölçek vb.) →
    yalnızca ilgili gözlemler düşer; uyarılar düşürmez. Yinelenenlerden ilki tutulur."""
    if any((not r.passed) and r.severity == "error" and r.code in FILE_LEVEL for r in results):
        return [], len(observations)
    bad_banks_raw = {r.bank for r in results if (not r.passed) and r.severity == "error" and r.code == "DQ01_bank_name"}
    bad_bank_period = {(r.bank, r.period_end) for r in results if (not r.passed) and r.severity == "error" and r.code in ("DQ06_balance", "DQ02_period")}
    bad_triplet = {(r.bank, r.metric, r.period_end) for r in results if (not r.passed) and r.severity == "error"
                   and r.code in ("DQ04_unit_scale", "DQ03_currency", "DQ05_scope", "DQ11_rate_definition", "DQ12_maturity_bucket", "DQ13_frequency")}
    kept, seen = [], set()
    for o in observations:
        if o.get("bank_raw") in bad_banks_raw or not o.get("bank_code"):
            continue
        if (o["bank_code"], o.get("period_end")) in bad_bank_period:
            continue
        if (o["bank_code"], o.get("metric_code"), o.get("period_end")) in bad_triplet:
            continue
        key = (o["bank_code"], o.get("metric_code"), o.get("period_start"), o.get("period_end"), o.get("reporting_scope"), o.get("currency"),
               o.get("source_code"), o.get("rate_definition"), o.get("bucket"), o.get("item"))
        if key in seen:
            continue
        seen.add(key)
        kept.append(o)
    return kept, len(observations) - len(kept)
