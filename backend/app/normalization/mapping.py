"""Kaynak tablo → gözlem kayıtları.

İki yaygın düzen desteklenir:
  (A) satırlar = kalemler, sütunlar = bankalar   (TBB Veri Sistemi / Excel ortak veri seti tarzı)
  (B) satırlar = bankalar,  sütunlar = kalemler  (DT20/DT21 seçilmiş tablolar, Aktif Büyüklük sıralaması tarzı)
Yönelim, banka adı eşleşmelerinin satır/sütun dağılımından belirlenir. Etiket → metrik eşlemesi yalnızca TEK bir
metrikle eşleşen etiketlerde yapılır; belirsiz etiketler eşlenmeden `unmapped` listesinde raporlanır (UNVERIFIED).
Ölçek (TL / Bin TL / Milyon TL) tablodan okunur; okunamazsa gözlem `scale_unknown` bayrağıyla kaydedilir, varsayılmaz.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

import pandas as pd

from app.acquisition.parsers import to_number
from .bank_names import BankRegistry, normalize_name

# Etiket kalıpları (Türkçe küçük harf, noktalama temizlenmiş). Sıra önemli: özel → genel.
LABEL_PATTERNS: list[tuple[str, str]] = [
    (r"^(toplam )?(varlıklar|aktifler)( toplamı)?$|^aktif toplamı$|^toplam aktif", "total_assets"),
    (r"^(toplam )?(yükümlülükler|pasifler)( toplamı)?$|^pasif toplamı$|^toplam pasif", "total_liabilities"),
    (r"^nakit değerler ve merkez bankası$|^nakit ve nakit benzerleri$|^nakit değerler$", "cash_and_cash_equivalents"),
    (r"merkez bankası(ndan alacaklar)?$|^t c merkez bankası|^tcmb", "balances_with_central_bank"),
    (r"^brüt krediler$|^krediler brüt$|^toplam krediler brüt$", "loans_gross"),
    (r"^krediler net$|^net krediler$|^toplam krediler net$", "loans_net"),
    (r"^krediler$|^toplam krediler$|^toplam kredi$|^krediler ve alacaklar$", "loans_gross"),
    (r"^tp krediler$|^tl krediler$|^türk parası krediler$", "loans_tl"),
    (r"^yp krediler$|^yabancı para krediler$", "loans_fx"),
    (r"^menkul değerler( cüzdanı)?$|^menkul kıymetler$|^toplam menkul (değerler|kıymetler)$", "securities_portfolio"),
    (r"^finansal varlıklar( net)?$|^toplam finansal varlıklar$", "financial_assets"),
    (r"^maddi duran varlıklar( net)?$", "fixed_assets"),
    (r"^diğer aktifler$|^diğer varlıklar$", "other_assets"),
    (r"^(toplam )?mevduat$|^mevduat toplamı$", "total_deposits"),
    (r"^tp mevduat$|^tl mevduat$|^türk parası mevduat$", "deposits_tl"),
    (r"^yp mevduat$|^yabancı para mevduat$", "deposits_fx"),
    (r"^vadesiz( mevduat)?$", "demand_deposits"),
    (r"^vadeli( mevduat)?$", "time_deposits"),
    (r"^alınan krediler$|^alınan krediler net$", "funds_borrowed"),
    (r"^ihraç edilen menkul kıymetler( net)?$", "securities_issued"),
    (r"^diğer yükümlülükler$|^diğer pasifler$", "other_liabilities"),
    (r"^(toplam )?özkaynaklar$|^özkaynak(lar)? toplamı$|^özkaynak$", "total_equity"),
    (r"^ödenmiş sermaye$", "paid_in_capital"),
    (r"^geçmiş yıllar kâr(ı| veya zararı| zararı)?$|^geçmiş yıl kârları$", "retained_earnings"),
    (r"^faiz gelirleri$|^toplam faiz gelirleri$", "interest_income"),
    (r"^faiz giderleri$|^toplam faiz giderleri$", "interest_expense"),
    (r"^net faiz geliri( gideri)?$|^net faiz geliri veya gideri$|^net faiz gelirleri$", "net_interest_income"),
    (r"^alınan ücret ve komisyonlar$|^ücret ve komisyon gelirleri$", "fee_commission_income"),
    (r"^verilen ücret ve komisyonlar$|^ücret ve komisyon giderleri$", "fee_commission_expense"),
    (r"^net ücret ve komisyon gelirleri( giderleri)?$|^net ücret ve komisyon geliri$", "net_fee_commission_income"),
    (r"^ticari kâr( veya)? zarar( net)?$|^ticari işlemlerden net gelir$|^sermaye piyasası işlemleri kârı zararı", "trading_income"),
    (r"^diğer faaliyet gelirleri$", "other_operating_income"),
    (r"^faaliyet giderleri$|^diğer faaliyet giderleri$|^toplam faaliyet giderleri$", "operating_expenses"),
    (r"^personel giderleri$", "personnel_expenses"),
    (r"^karşılık giderleri$|^beklenen zarar karşılıkları giderleri$|^kredi ve diğer alacaklar (değer düşüş|karşılık)", "provision_expenses"),
    (r"^vergi öncesi kâr( zarar)?$|^sürdürülen faaliyetler vergi öncesi k z$|^vergi öncesi kar", "profit_before_tax"),
    (r"^(net )?dönem (net )?kâr(ı| zararı| veya zararı)?$|^net kâr( zarar)?$|^dönem net kârı zararı$|^net kar", "net_profit"),
    (r"^takipteki (krediler|alacaklar)( brüt)?$|^donuk alacaklar$|^takipteki krediler brüt$", "npl_amount"),
    (r"^(özel|beklenen zarar) karşılıklar(ı)?( )?$|^kredi zarar karşılıkları$|^takipteki krediler karşılığı$", "loan_loss_provisions"),
    (r"^sermaye yeterliliği (standart )?(oranı|rasyosu)$|^sermaye yeterlilik (standart )?(oranı|rasyosu)$", "capital_adequacy_ratio"),
    (r"^ana sermaye (yeterlilik )?oranı$|^tier 1", "tier_1_ratio"),
    (r"^çekirdek sermaye (yeterlilik )?oranı$|^cet ?1", "cet1_ratio"),
    (r"^risk ağırlıklı (varlıklar|tutarlar)$|^toplam risk ağırlıklı", "risk_weighted_assets"),
    (r"^şube sayısı$|^şube$|^toplam şube", "branch_count"),
    (r"^(çalışan|personel) sayısı$|^çalışan$|^personel$", "employee_count"),
]

SCALE_PATTERNS = [(r"milyar", 1e9), (r"milyon", 1e6), (r"\bbin\b", 1e3), (r"\(tl\)|^tl$|türk lirası", 1.0)]


def map_label(raw: str) -> str | None:
    n = normalize_name(raw)
    hits = []
    for pat, code in LABEL_PATTERNS:
        if re.search(pat, n):
            hits.append(code)
            break   # ilk (en özel) eşleşme
    return hits[0] if hits else None


def detect_scale(df: pd.DataFrame, max_rows: int = 8) -> tuple[float | None, str | None]:
    for r in range(min(max_rows, len(df))):
        for c in range(df.shape[1]):
            v = df.iat[r, c]
            if isinstance(v, str):
                s = v.lower()
                for pat, scale in SCALE_PATTERNS:
                    if re.search(pat, s) and ("tl" in s or "try" in s or "milyon" in s or "bin" in s or "milyar" in s):
                        return scale, v.strip()
    return None, None


@dataclass
class MappedObservation:
    bank_raw: str
    bank_code: str | None
    bank_match: str                 # alias | fuzzy | none | aggregate
    metric_code: str
    label_raw: str
    value_raw: float | None
    scale: float | None
    row: int
    col: int
    flags: list[str] = field(default_factory=list)
    currency: str | None = None     # tek banka düzeninde sütundan: TRY | FX | ALL
    period: object = None           # tek banka düzeninde sütundan çözülen dönem (Period) — None ise dosya dönemi


@dataclass
class MappingResult:
    orientation: str                # banks_in_columns | banks_in_rows | unknown
    scale: float | None
    scale_label: str | None
    observations: list[MappedObservation]
    unmapped_labels: list[str]
    unmatched_banks: list[str]


def _bank_hits(df: pd.DataFrame, registry: BankRegistry, limit: int = 60):
    row_hits: dict[int, int] = {}
    col_hits: dict[int, int] = {}
    for r in range(min(limit, df.shape[0])):
        for c in range(min(limit, df.shape[1])):
            v = df.iat[r, c]
            if isinstance(v, str) and v.strip():
                code, conf, how = registry.match(v)
                if code and conf >= 0.92:
                    row_hits[r] = row_hits.get(r, 0) + 1
                    col_hits[c] = col_hits.get(c, 0) + 1
    return row_hits, col_hits


CURRENCY_COLS = {"tp": "TRY", "tl": "TRY", "türk parası": "TRY", "yp": "FX", "yabancı para": "FX", "toplam": "ALL", "total": "ALL"}


def map_single_bank_table(df: pd.DataFrame, registry: BankRegistry, bank_hint: str, period_hint=None) -> MappingResult:
    """(C) düzeni: dosya tek bankaya ait (Excel ortak veri seti); satırlar = kalemler, sütunlar = TP/YP/Toplam veya dönemler.
    Banka adı tablodan değil dosyanın geldiği seçiciden (bank_hint) alınır. Başlık satırı bulunamazsa hiçbir şey eşlenmez."""
    from .periods import parse_period
    scale, scale_label = detect_scale(df)
    code, conf, how = registry.match(bank_hint)
    if conf < 0.92:
        code, how = None, "none"
    hdr = None
    for r in range(min(15, df.shape[0])):
        cells = [normalize_name(str(x)) for x in df.iloc[r].tolist() if isinstance(x, str) and str(x).strip()]
        if sum(1 for c in cells if c in CURRENCY_COLS) >= 2 or sum(1 for c in cells if parse_period(c)) >= 1:
            hdr = r
            break
    if hdr is None:
        return MappingResult("single_bank_no_header", scale, scale_label, [], [], [bank_hint] if not code else [])
    label_col = _label_column(df, hdr)
    cols: dict[int, dict] = {}
    for c in range(df.shape[1]):
        v = df.iat[hdr, c]
        if c == label_col or not isinstance(v, str) or not v.strip():
            continue
        n = normalize_name(v)
        if n in CURRENCY_COLS:
            cols[c] = {"currency": CURRENCY_COLS[n], "period": period_hint, "label": v.strip()}
        else:
            per = parse_period(v)
            if per:
                cols[c] = {"currency": "ALL", "period": per, "label": v.strip()}
    obs, unmapped = [], []
    for r in range(hdr + 1, df.shape[0]):
        lab = df.iat[r, label_col]
        if not isinstance(lab, str) or not lab.strip():
            continue
        mcode = map_label(lab)
        if not mcode:
            unmapped.append(lab.strip())
            continue
        for c, meta in cols.items():
            val = to_number(df.iat[r, c])
            o = MappedObservation(bank_hint, code, how, mcode, lab.strip(), val, scale, r, c, [] if scale else ["scale_unknown"])
            o.currency = meta["currency"]
            o.period = meta["period"]
            obs.append(o)
    return MappingResult("single_bank", scale, scale_label, obs, sorted(set(unmapped)), [] if code else [bank_hint])


def map_table(df: pd.DataFrame, registry: BankRegistry, metric_hint: str | None = None, bank_hint: str | None = None, period_hint=None) -> MappingResult:
    scale, scale_label = detect_scale(df)
    row_hits, col_hits = _bank_hits(df, registry)
    if bank_hint and max(list(row_hits.values()) + [0]) < 2 and max(list(col_hits.values()) + [0]) < 2:
        return map_single_bank_table(df, registry, bank_hint, period_hint)
    best_row = max(row_hits.items(), key=lambda kv: kv[1], default=(None, 0))
    best_col = max(col_hits.items(), key=lambda kv: kv[1], default=(None, 0))
    obs, unmapped, unmatched = [], [], []

    if best_row[1] >= 2 and best_row[1] >= best_col[1]:
        # (A) bankalar sütunlarda (başlık satırı = best_row); etiketler satır başlarında
        hdr = best_row[0]
        label_col = _label_column(df, hdr)
        bank_cols = {}
        for c in range(df.shape[1]):
            v = df.iat[hdr, c]
            if isinstance(v, str) and v.strip():
                code, conf, how = registry.match(v)
                bank_cols[c] = (v, code if conf >= 0.92 else None, how if conf >= 0.92 else ("aggregate" if registry.is_aggregate(v) else "none"))
        for r in range(hdr + 1, df.shape[0]):
            lab = df.iat[r, label_col]
            if not isinstance(lab, str) or not lab.strip():
                continue
            code = metric_hint or map_label(lab)
            if not code:
                unmapped.append(lab.strip())
                continue
            for c, (braw, bcode, how) in bank_cols.items():
                if c == label_col:
                    continue
                val = to_number(df.iat[r, c])
                if bcode is None and how != "aggregate":
                    unmatched.append(braw)
                obs.append(MappedObservation(braw, bcode, how, code, lab.strip(), val, scale, r, c,
                                             [] if scale else ["scale_unknown"]))
        return MappingResult("banks_in_columns", scale, scale_label, obs, sorted(set(unmapped)), sorted(set(unmatched)))

    if best_col[1] >= 2:
        # (B) bankalar satırlarda (sütun = best_col); başlık satırı = bankalardan önceki son metin satırı
        bc = best_col[0]
        first_bank_row = min(r for r in range(df.shape[0]) if isinstance(df.iat[r, bc], str) and registry.match(df.iat[r, bc])[1] >= 0.92)
        header_rows = [r for r in range(max(0, first_bank_row - 6), first_bank_row)]
        col_labels: dict[int, str] = {}
        for c in range(df.shape[1]):
            if c == bc:
                continue
            parts = [str(df.iat[r, c]).strip() for r in header_rows if isinstance(df.iat[r, c], str) and str(df.iat[r, c]).strip()]
            if parts:
                col_labels[c] = " ".join(parts)
        for r in range(first_bank_row, df.shape[0]):
            braw = df.iat[r, bc]
            if not isinstance(braw, str) or not braw.strip():
                continue
            bcode, conf, how = registry.match(braw)
            if conf < 0.92:
                bcode = None
                how = "aggregate" if registry.is_aggregate(braw) else "none"
                if how == "none":
                    unmatched.append(braw.strip())
            for c, lab in col_labels.items():
                code = metric_hint or map_label(lab)
                if not code:
                    unmapped.append(lab)
                    continue
                val = to_number(df.iat[r, c])
                obs.append(MappedObservation(braw.strip(), bcode, how, code, lab, val, scale, r, c, [] if scale else ["scale_unknown"]))
        return MappingResult("banks_in_rows", scale, scale_label, obs, sorted(set(unmapped)), sorted(set(unmatched)))

    return MappingResult("unknown", scale, scale_label, [], [], [])


def _label_column(df: pd.DataFrame, header_row: int) -> int:
    counts = {}
    for c in range(df.shape[1]):
        n = 0
        for r in range(header_row + 1, min(df.shape[0], header_row + 60)):
            if isinstance(df.iat[r, c], str) and df.iat[r, c].strip():
                n += 1
        counts[c] = n
    return max(counts.items(), key=lambda kv: kv[1])[0] if counts else 0
