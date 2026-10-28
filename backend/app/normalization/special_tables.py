"""TBB DT20/DT21 'Seçilmiş Tablolar' içindeki iki öncelikli tablo için özel eşleyiciler.

Doğrulanmış yapı (Haziran 2023 DT20 PDF; Aralık 2019 / Mart 2021 / Haziran 2022 DT21 PDF'leri):
1) "Verilen Kredilere ve Diğer Mevduata Uygulanan Ortalama Faiz Oranları*, %"
   başlık: TL | USD | EURO  → alt başlık her biri için: Verilen Krediler | Mevduat ; satırlar = sektör/grup/banka
   dipnot: oranlar faiz oranı riski amaçlı hazırlanan parasal finansal araçlara uygulanan ortalama faiz oranlarıdır;
           mevduat bankalararası hariç.  → rate_definition = stock_avg_applied_rate
2) "Aktif ve Pasif Kalemlerin Kalan Vadelerine Göre Gösterimi, Milyon TL"
   kovalar: Vadesiz | 1 Ay | 1-3 Ay | 3-12 Ay | 1-5 Yıl | 5 Yıl ve Üzeri | Dağıtılamayan | Toplam
   bloklar: Toplam Aktifler | Toplam Pasifler | Likidite Açığı ; satırlar = sektör/grup/banka
   → item ∈ {total_assets, total_liabilities, liquidity_gap}; kredi/mevduat AYRI DEĞİLDİR.
Excel/HTML sürümünde hücre düzeni aynı mantıkla taranır; eşleşmeyen hücreler raporlanır, varsayılmaz.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

import pandas as pd

from app.acquisition.parsers import to_number
from .bank_names import BankRegistry, normalize_name

BUCKET_LABELS = [   # boşluk ve noktalama atılmış (compact) etiketler
    (r"^vadesiz$", "demand"), (r"^7günihbarlı$", "notice_7d"),
    (r"^(1ay|1ayakadar|01ay|biraya?kadar)$", "0_1m"), (r"^13ay$", "1_3m"), (r"^36ay$", "3_6m"),
    (r"^(612ay|6ay1yıl)$", "6_12m"), (r"^312ay$", "3_12m"), (r"^15yıl$", "1_5y"),
    (r"^5yıl(ve)?(üzeri|üstü)$", "over_5y"), (r"^1yıl(ve)?(üzeri|üstü)$", "over_1y"),
    (r"^dağıtılamayan$", "unallocated"), (r"^birikimli(mevduat)?$", "accumulating"), (r"^toplam$", "total"),
]
ITEM_LABELS = [
    (r"toplam (aktif|varlık)", "total_assets"), (r"^(aktif|varlık)(ler)?$", "total_assets"),
    (r"toplam (pasif|yükümlülük)", "total_liabilities"), (r"^(pasif|yükümlülük)(ler)?$", "total_liabilities"),
    (r"likidite açığı", "liquidity_gap"), (r"^krediler$", "loans"), (r"^mevduat$", "deposits"),
]
CURRENCY_LABELS = {"tl": "TRY", "tp": "TRY", "usd": "USD", "abd doları": "USD", "euro": "EUR", "eur": "EUR"}


def _is_note_row(label: str) -> bool:
    t = label.strip()
    return t.startswith(("(", "*", "Not", "Kaynak", "Dipnot")) or normalize_name(t) in ("banka", "bankalar", "")


def _bucket(label: str) -> str | None:
    n = normalize_name(label).replace(" ", "")
    for pat, code in BUCKET_LABELS:
        if re.search(pat, n):
            return code
    return None


def _item(label: str) -> str | None:
    n = normalize_name(label)
    for pat, code in ITEM_LABELS:
        if re.search(pat, n):
            return code
    return None


@dataclass
class SpecialRow:
    bank_raw: str
    bank_code: str | None
    bank_match: str
    key: dict
    value: float | None
    row: int
    col: int
    flags: list[str] = field(default_factory=list)


def map_interest_table(df: pd.DataFrame, registry: BankRegistry) -> list[SpecialRow]:
    """→ key = {instrument, currency, metric_code, rate_definition}"""
    cur_row = ins_row = None
    for r in range(min(15, len(df))):
        cells = [normalize_name(str(x)) for x in df.iloc[r].tolist() if isinstance(x, str)]
        if sum(1 for c in cells if c in CURRENCY_LABELS) >= 2 and cur_row is None:
            cur_row = r
        if sum(1 for c in cells if c.startswith("verilen kredi") or c == "mevduat" or c == "krediler") >= 2:
            ins_row = r
    if cur_row is None or ins_row is None:
        return []
    cols: dict[int, tuple[str, str]] = {}
    current_cur = None
    for c in range(df.shape[1]):
        v = df.iat[cur_row, c]
        if isinstance(v, str) and normalize_name(v) in CURRENCY_LABELS:
            current_cur = CURRENCY_LABELS[normalize_name(v)]
        w = df.iat[ins_row, c]
        if isinstance(w, str) and current_cur:
            n = normalize_name(w)
            if n.startswith("verilen kredi") or n == "krediler":
                cols[c] = ("loan", current_cur)
            elif n.startswith("mevduat"):
                cols[c] = ("deposit", current_cur)
    out = []
    for r in range(ins_row + 1, df.shape[0]):
        braw = next((x for x in df.iloc[r].tolist() if isinstance(x, str) and x.strip()), None)
        if not braw or _is_note_row(braw) or not any(to_number(df.iat[r, c]) is not None for c in cols):
            continue   # dipnot / başlık / boş satır — banka satırı değil
        code, conf, how = registry.match(braw)
        if conf < 0.92:
            code, how = None, ("aggregate" if registry.is_aggregate(braw) else "none")
        for c, (ins, cur) in cols.items():
            metric = f"{ins}_interest_{cur.lower().replace('try', 'tl')}"
            out.append(SpecialRow(braw.strip(), code, how, {"instrument": ins, "currency": cur, "metric_code": metric,
                                                           "rate_definition": "stock_avg_applied_rate"}, to_number(df.iat[r, c]), r, c))
    return out


def map_maturity_table(df: pd.DataFrame, registry: BankRegistry) -> list[SpecialRow]:
    """→ key = {item, basis='remaining', bucket, bucket_label_raw}; aynı kova başlığı birden çok blokta tekrarlanabilir."""
    out = []
    r = 0
    current_item = None
    while r < df.shape[0]:
        cells = [(c, df.iat[r, c]) for c in range(df.shape[1]) if isinstance(df.iat[r, c], str) and df.iat[r, c].strip()]
        for _, v in cells:
            it = _item(v)
            if it:
                current_item = it
        bucket_cols = {c: (_bucket(v), v.strip()) for c, v in cells if _bucket(v)}
        if len(bucket_cols) >= 3:
            rr = r + 1
            while rr < df.shape[0]:
                row = df.iloc[rr].tolist()
                braw = next((x for x in row if isinstance(x, str) and x.strip()), None)
                if braw is None:
                    rr += 1
                    if rr < df.shape[0] and all(not isinstance(x, str) or not x.strip() for x in df.iloc[rr].tolist()):
                        break
                    continue
                if _item(braw) or _bucket(braw) and len([x for x in row if isinstance(x, str)]) >= 3:
                    break   # yeni blok başlığı
                if _is_note_row(braw) or not any(to_number(df.iat[rr, c]) is not None for c in bucket_cols):
                    rr += 1
                    continue
                code, conf, how = registry.match(braw)
                if conf < 0.92:
                    code, how = None, ("aggregate" if registry.is_aggregate(braw) else "none")
                for c, (bk, raw_lab) in bucket_cols.items():
                    out.append(SpecialRow(braw.strip(), code, how, {"item": current_item or "unknown", "basis": "remaining", "bucket": bk,
                                                                   "bucket_label_raw": raw_lab}, to_number(df.iat[rr, c]), rr, c,
                                          [] if current_item else ["item_unknown"]))
                rr += 1
            r = rr
            continue
        r += 1
    return out
