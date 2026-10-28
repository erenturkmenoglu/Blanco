"""Financial Calculation Engine.

Tüm fonksiyonlar saf (pure) ve yeniden üretilebilir; her hesap `method` metnini ve `limitations` notunu döndürür.
Dönem uyumu kuralları (§7.5):
- Gelir tablosu kalemleri yıl başından KÜMÜLATİF gelir → bağımsız çeyrek = YTD[q] - YTD[q-1]; yıllıklandırma = YTD × 4/q
  (yöntem adı 'ytd_x4q') veya son 4 çeyrek toplamı ('trailing_4q') — kullanılan yöntem çıktıda belirtilir.
- Ortalama bakiye = (dönem sonu + bir önceki yıl sonu) / 2 ('avg_2pt') ya da mevcut çeyrek sonlarının ortalaması ('avg_npt').
- Faiz makası yalnızca aynı tanım/para birimi/dönem/kapsamdaki oranlar için hesaplanır; aksi hâlde None + sınırlama.
- Aralık orta noktasıyla hesaplanan ortalama vade yalnızca 'illustrative_midpoint_wam' etiketiyle verilir, kesin değer değildir.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import pandas as pd

BUCKET_MIDPOINT_MONTHS = {"demand": 0.0, "notice_7d": 0.25, "0_1m": 0.5, "1_3m": 2.0, "3_6m": 4.5, "6_12m": 9.0, "6m_1y": 9.0,
                          "3_12m": 7.5, "1_5y": 36.0, "over_5y": 84.0, "over_1y": 36.0}


@dataclass
class Derived:
    metric_code: str
    value: float | None
    unit: str
    method: str
    inputs: dict
    limitations: str | None = None


def _q_of(pe: date) -> int:
    return (pe.month - 1) // 3 + 1


def prev_quarter_end(pe: date) -> date:
    y, m = pe.year, pe.month
    m -= 3
    if m <= 0:
        m, y = m + 12, y - 1
    return date(y, m, {3: 31, 6: 30, 9: 30, 12: 31}[m])


def prev_year_end(pe: date) -> date:
    return date(pe.year - 1, 12, 31)


def quarterly_from_cumulative(ytd: dict[date, float]) -> dict[date, float | None]:
    """YTD kümülatif → bağımsız çeyrek. Önceki çeyrek yoksa (Q1 hariç) None (uydurulmaz)."""
    out = {}
    for pe, v in sorted(ytd.items()):
        q = _q_of(pe)
        if q == 1:
            out[pe] = v
        else:
            p = ytd.get(prev_quarter_end(pe))
            out[pe] = None if (v is None or p is None) else v - p
    return out


def annualize_ytd(value_ytd: float | None, pe: date, method: str = "ytd_x4q") -> tuple[float | None, str]:
    if value_ytd is None:
        return None, method
    q = _q_of(pe)
    if method == "ytd_x4q":
        return value_ytd * 4.0 / q, f"ytd_x4q (YTD×4/{q})"
    raise ValueError(method)


def average_balance(series: dict[date, float], pe: date) -> tuple[float | None, str]:
    cur = series.get(pe)
    if cur is None:
        return None, "none"
    prior = series.get(prev_year_end(pe))
    if prior is not None:
        return (cur + prior) / 2.0, "avg_2pt (dönem sonu + önceki yıl sonu)/2"
    return cur, "period_end_only (ortalama için önceki yıl sonu yok — SINIRLAMA)"


def growth(series: dict[date, float], pe: date, lag_quarters: int) -> tuple[float | None, str]:
    cur = series.get(pe)
    back = pe
    for _ in range(lag_quarters):
        back = prev_quarter_end(back)
    base = series.get(back)
    if cur is None or base in (None, 0):
        return None, f"lag_{lag_quarters}q (taban {back} yok)"
    return cur / base - 1.0, f"lag_{lag_quarters}q: value[{pe}]/value[{back}]-1"


def spread(loan_rate: dict | None, deposit_rate: dict | None) -> Derived:
    """loan_rate/deposit_rate: {'value', 'rate_definition', 'currency', 'period_end', 'reporting_scope'}"""
    if not loan_rate or not deposit_rate or loan_rate.get("value") is None or deposit_rate.get("value") is None:
        return Derived("loan_deposit_spread", None, "pct", "loan_rate - deposit_rate", {}, "faiz oranlarından biri yok")
    mism = [k for k in ("rate_definition", "currency", "period_end", "reporting_scope") if loan_rate.get(k) != deposit_rate.get(k)]
    if mism:
        return Derived("loan_deposit_spread", None, "pct", "loan_rate - deposit_rate", {"loan": loan_rate, "deposit": deposit_rate},
                       f"karşılaştırılamaz tanımlar/dönem/para birimi: {mism} — makas hesaplanmadı")
    lim = None
    if loan_rate["rate_definition"] == "stock_avg_applied_rate":
        lim = ("Oranlar faiz oranı riski dipnotundaki parasal finansal araçlara uygulanan STOK ortalama oranlarıdır; "
               "yeni açılış faizleri ve muhasebesel getiri/maliyetle karşılaştırılamaz.")
    return Derived("loan_deposit_spread", loan_rate["value"] - deposit_rate["value"], "pct", "loan_rate - deposit_rate",
                   {"loan": loan_rate, "deposit": deposit_rate}, lim)


def maturity_shares(buckets: dict[str, float | None], total: float | None = None, bucket_labels: dict[str, str] | None = None) -> Derived:
    present = {k: v for k, v in buckets.items() if v is not None and k != "total"}
    tot = total if total is not None else (sum(present.values()) if present else None)
    if not present or not tot or sum(present.values()) == 0:
        return Derived("maturity_shares", None, "ratio", "bucket/total", {"shares": {}, "labels": bucket_labels or {}}, "vade verisi yok veya tümü sıfır")
    if tot < 0 or any(v < 0 for v in present.values()):
        # likidite açığı / net nazım gibi işaretli kalemlerde pay ve ortalama vade anlamsızdır
        return Derived("maturity_shares", None, "ratio", "bucket/total", {"shares": {}, "labels": bucket_labels or {}},
                       "işaretli (negatif) kalem: pay ve ortalama vade hesaplanmaz")
    shares = {k: v / tot for k, v in present.items()}
    lim = None
    if "3_12m" in present:
        lim = "kaynak 3-12 ayı tek kova verir; 3-6 / 6-12 ayrımı yapılmadı"
    wam = sum(BUCKET_MIDPOINT_MONTHS.get(k, 0.0) * v for k, v in present.items()) / sum(present.values())
    return Derived("maturity_shares", None, "ratio", "bucket/total; illustrative_midpoint_wam=orta nokta ağırlıklı (kesin değil)",
                   {"shares": shares, "illustrative_midpoint_wam_months": wam, "labels": bucket_labels or {}}, lim)


def compute_derived(obs: pd.DataFrame, bank_code: str, pe: date, scope: str = "solo") -> list[Derived]:
    """obs: long tablo [bank_code, metric_code, period_end, value, reporting_scope, cumulative_ytd].
    Yalnızca mevcut gözlemlerden hesaplar; eksikse None + sınırlama döner (uydurma yok)."""
    d = obs[(obs.bank_code == bank_code) & (obs.reporting_scope == scope)]

    def series(code: str) -> dict[date, float]:
        s = d[d.metric_code == code].dropna(subset=["value"])
        return {r.period_end: float(r.value) for r in s.itertuples()}

    out: list[Derived] = []
    ta, te, lg, dep, ni, nii, nfc, trd, oth, opx, prov, npl, llp = (series(c) for c in (
        "total_assets", "total_equity", "loans_gross", "total_deposits", "net_profit", "net_interest_income",
        "net_fee_commission_income", "trading_income", "other_operating_income", "operating_expenses", "provision_expenses",
        "npl_amount", "loan_loss_provisions"))
    emp, br = series("employee_count"), series("branch_count")

    # kârlılık (gelir tablosu kümülatif → yıllıklandır)
    ni_a, m1 = annualize_ytd(ni.get(pe), pe)
    avg_ta, m2 = average_balance(ta, pe)
    out.append(Derived("roa", (ni_a / avg_ta * 100) if (ni_a is not None and avg_ta) else None, "pct",
                       f"net_profit[{m1}] / avg_total_assets[{m2}]", {"net_profit_ytd": ni.get(pe), "avg_total_assets": avg_ta},
                       None if avg_ta and "SINIRLAMA" not in m2 else m2))
    avg_te, m3 = average_balance(te, pe)
    out.append(Derived("roe", (ni_a / avg_te * 100) if (ni_a is not None and avg_te) else None, "pct",
                       f"net_profit[{m1}] / avg_equity[{m3}]", {"net_profit_ytd": ni.get(pe), "avg_equity": avg_te}))
    nii_a, m4 = annualize_ytd(nii.get(pe), pe)
    out.append(Derived("nim", (nii_a / avg_ta * 100) if (nii_a is not None and avg_ta) else None, "pct",
                       f"net_interest_income[{m4}] / avg_total_assets[{m2}]", {"nii_ytd": nii.get(pe), "avg_total_assets": avg_ta},
                       "Payda faiz getirili aktif değil TOPLAM aktif (proxy) — kaynakta faiz getirili aktif ayrımı doğrulanana kadar"))
    rev = [x.get(pe) for x in (nii, nfc, trd, oth)]
    tot_rev = sum(v for v in rev if v is not None) if any(v is not None for v in rev) else None
    out.append(Derived("cost_to_income", (opx[pe] / tot_rev * 100) if (opx.get(pe) is not None and tot_rev) else None, "pct",
                       "operating_expenses_ytd / (nii + nfc + trading + other)_ytd", {"opex": opx.get(pe), "revenue": tot_rev},
                       None if all(v is not None for v in rev) else "gelir bileşenlerinden bazıları eksik; payda eksik bileşenlerle hesaplandı" if tot_rev else "gelir yok"))
    # kredi kalitesi
    out.append(Derived("npl_ratio", (npl[pe] / lg[pe] * 100) if (npl.get(pe) is not None and lg.get(pe)) else None, "pct",
                       "npl_amount / loans_gross", {"npl": npl.get(pe), "loans_gross": lg.get(pe)}))
    out.append(Derived("npl_coverage_ratio", (llp[pe] / npl[pe] * 100) if (llp.get(pe) is not None and npl.get(pe)) else None, "pct",
                       "loan_loss_provisions / npl_amount", {"llp": llp.get(pe), "npl": npl.get(pe)}))
    prov_a, m5 = annualize_ytd(prov.get(pe), pe)
    avg_lg, m6 = average_balance(lg, pe)
    out.append(Derived("cost_of_risk", (prov_a / avg_lg * 100) if (prov_a is not None and avg_lg) else None, "pct",
                       f"provision_expenses[{m5}] / avg_loans_gross[{m6}]", {"prov_ytd": prov.get(pe), "avg_loans": avg_lg}))
    # sermaye / likidite
    out.append(Derived("equity_to_assets", (te[pe] / ta[pe] * 100) if (te.get(pe) is not None and ta.get(pe)) else None, "pct",
                       "total_equity / total_assets", {"equity": te.get(pe), "assets": ta.get(pe)}))
    out.append(Derived("loan_to_deposit_ratio", (lg[pe] / dep[pe] * 100) if (lg.get(pe) is not None and dep.get(pe)) else None, "pct",
                       "loans_gross / total_deposits", {"loans": lg.get(pe), "deposits": dep.get(pe)}))
    # operasyonel
    out.append(Derived("assets_per_employee", (ta[pe] / emp[pe]) if (ta.get(pe) is not None and emp.get(pe)) else None, "TRY",
                       "total_assets / employee_count", {"assets": ta.get(pe), "employees": emp.get(pe)}))
    out.append(Derived("deposits_per_branch", (dep[pe] / br[pe]) if (dep.get(pe) is not None and br.get(pe)) else None, "TRY",
                       "total_deposits / branch_count", {"deposits": dep.get(pe), "branches": br.get(pe)}))
    # büyüme (stok: QoQ/YoY; kâr: aynı YTD penceresi)
    for code, s in (("assets", ta), ("loans", lg), ("deposits", dep)):
        g, m = growth(s, pe, 1)
        out.append(Derived(f"{code}_growth_qoq", g * 100 if g is not None else None, "pct", m, {}))
        g, m = growth(s, pe, 4)
        out.append(Derived(f"{code}_growth_yoy", g * 100 if g is not None else None, "pct", m, {}))
    g, m = growth(te, pe, 4)
    out.append(Derived("equity_growth_yoy", g * 100 if g is not None else None, "pct", m, {}))
    g, m = growth(ni, pe, 4)
    out.append(Derived("profit_growth_yoy", g * 100 if g is not None else None, "pct", m + " (aynı YTD penceresi)", {}))
    return out
