"""TBB "Finansal Tablolar – Konsolide Olmayan (Solo Banka, Excel ortak veri seti)" — banka bazında zip içindeki <Banka>.xls çalışma kitabı.
GERÇEK düzen (Akbank / Ziraat Haziran 2026 dosyaları açılarak doğrulandı; 17 Sayılı Tebliğ "Ortak Veri Gönderim Seti"):

- 'varlıklar' / 'yüküm.' : Roma rakamlı kalemler; sütunlar Dipnot | TP | YP | Toplam (Cari dönem, ör. 30/06/2026) | TP | YP | Toplam (Önceki dönem, 31/12/2025)
- ÖLÇEK: satır 3 'MİLYON TÜRK LİRASI' (Haziran 2026) veya 'BİN TÜRK LİRASI' (Mart 2026) — dönemden döneme değişir, başlıktan okunur (DQ01)
- 'gelir'                : kalemler; sütunlar Dipnot | Cari YTD (01/01–30/06) | Önceki yıl YTD | Cari ÇEYREK (01/04–30/06) | Önceki yıl çeyrek
- 'pasif1'  blok "2.a.1.i) Mevduatın vade yapısına ilişkin bilgiler": mevduat türü × (Vadesiz | 7 Gün İhbarlı | 1 Aya Kadar | 1-3 Ay | 3-6 Ay | 6 Ay-1 Yıl | 1 Yıl ve Üstü | Birikimli | Toplam) — Cari ve Önceki dönem
- 'malibünye1' blok "Parasal Finansal Araçlara Uygulanan Ortalama Faiz Oranları: % (3 Aylık)": EURO | USD | Yen | TL × kalemler (Verilen Krediler, Diğer Mevduat, ...) — cari ve önceki dönem sonu
- 'malibünye1' blok "Aktif ve Pasif Kalemlerin Kalan Vadelerine Göre Gösterimi: (3 Aylık)": kalemler (Verilen Krediler, Diğer Mevduat, ...) × (Vadesiz | 1 Aya Kadar | 1-3 Ay | 3-12 Ay | 1-5 Yıl | 5 Yıl ve Üzeri | Dağıtılamayan | Toplam)
- 'gelir1' blok "2.b.4.i) Mevduata ödenen faizin vade yapısına göre gösterimi (3 Aylık)": TP/YP mevduat türü × (Vadesiz | 1 Aya Kadar | 3 Aya Kadar | 6 Aya Kadar | 1 Yıla Kadar | 1 Yıldan Uzun | Birikimli | Toplam)
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date

import pandas as pd

from contextvars import ContextVar

from app.acquisition.parsers import to_number
from .bank_names import BankRegistry, normalize_name
from .scale import detect_scale

SCALE_MTL = 1e6                                   # yalnızca geriye dönük sabit; gerçek ölçek başlıktan okunur (DQ01)
_SCALE: ContextVar[tuple[float | None, str | None]] = ContextVar("workbook_scale", default=(None, None))


def detect_workbook_scale(tables: dict[str, pd.DataFrame]) -> tuple[float | None, str | None]:
    """Çalışma kitabının para ölçeği: 'varlıklar' (yoksa 'yüküm.' / 'gelir') sayfasının başlık satırlarından okunur.
    Haziran 2026 kitapları 'MİLYON TÜRK LİRASI', Mart 2026 kitapları 'BİN TÜRK LİRASI' — aynı veri setinde dönemden döneme değişir."""
    for suffix in ("varlıklar", "yüküm.", "gelir"):
        _, df = _find_sheet(tables, suffix)
        if df is not None:
            hit = detect_scale(df, rows=8)
            if hit:
                return hit
    return None, None


def _lab(s) -> str:
    """Kalem etiketi: numaralandırma (I., 1.1., 2.4.1.) ve parantezli notlar atılır, Türkçe küçük harf."""
    if not isinstance(s, str):
        return ""
    t = re.sub(r"^\s*(?:[IVX]+\.|\d+(?:\.\d+)*\.?)\s*", "", s.strip())
    t = re.sub(r"\(.*?\)", " ", t)
    return re.sub(r"\s+", " ", normalize_name(t)).strip()


def _dates_in(df: pd.DataFrame, rows=(0, 8)) -> list[date]:
    out = []
    for r in range(rows[0], min(rows[1], df.shape[0])):
        for c in range(df.shape[1]):
            v = df.iat[r, c]
            if isinstance(v, str):
                for m in re.finditer(r"(\d{2})/(\d{2})/(\d{4})", v):
                    d = date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
                    if d not in out:
                        out.append(d)
    return out


@dataclass
class Extracted:
    observations: list[dict] = field(default_factory=list)
    unmapped_labels: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    scale: float | None = None
    scale_label: str | None = None


def _o(bank_raw, code, pe, ps, scope, source_code, sheet, r, c, label, metric, value, unit="TRY", currency="ALL", cum=False, kind="financial", **extra):
    scale, scale_label = _SCALE.get()
    detected = scale is not None
    eff = scale if detected else SCALE_MTL      # tespit edilemediyse değer yine de yazılır ama UNVERIFIED (DQ01) işaretlenir
    o = dict(bank_raw=bank_raw, bank_code=code, bank_match="alias" if code else "none", period_end=pe, period_start=ps, reporting_scope=scope,
             frequency="quarterly", source_code=source_code, sheet=sheet, row=r, col=c, label_raw=label, metric_code=metric, unit=unit,
             scale=eff if unit == "TRY" else 1.0, scale_label=scale_label, scale_detected=detected if unit == "TRY" else True, currency=currency, value_raw=value,
             value=(value * eff) if (value is not None and unit == "TRY") else value, cumulative_ytd=cum, kind=kind)
    o.update(extra)
    return o


# ---------------------------------------------------------------- ana tablolar
ASSET_MAP = {
    "finansal varlıklar": "financial_assets", "nakit ve nakit benzerleri": "cash_and_cash_equivalents",
    "nakit değerler ve merkez bankası": "cash_and_central_bank", "bankalar": "due_from_banks", "para piyasalarından alacaklar": "money_market_receivables",
    "gerçeğe uygun değer farkı kar zarara yansıtılan finansal varlıklar": "securities_fvtpl",
    "gerçeğe uygun değer farkı diğer kapsamlı gelire yansıtılan finansal varlıklar": "securities_fvoci",
    "türev finansal varlıklar": "derivative_assets", "itfa edilmiş maliyeti ile ölçülen finansal varlıklar": "amortized_cost_assets_total",
    "krediler": "loans_gross", "kiralama işlemlerinden alacaklar": "lease_receivables", "faktoring alacakları": "factoring_receivables",
    "itfa edilmiş maliyeti ile ölçülen diğer finansal varlıklar": "securities_amortized_total", "beklenen zarar karşılıkları": "ecl_allowance_loans",
    "ortaklık yatırımları": "equity_investments", "maddi duran varlıklar": "fixed_assets", "maddi olmayan duran varlıklar": "intangible_assets",
    "yatırım amaçlı gayrimenkuller": "investment_property", "diğer aktifler": "other_assets", "varlıklar toplamı": "total_assets",
}
LIAB_MAP = {
    "mevduat": "total_deposits", "alınan krediler": "funds_borrowed", "para piyasalarına borçlar": "money_market_funds",
    "ihraç edilen menkul kıymetler": "securities_issued", "fonlar": "funds", "türev finansal yükümlülükler": "derivative_liabilities",
    "karşılıklar": "provisions", "cari vergi borcu": "current_tax_liability", "ertelenmiş vergi borcu": "deferred_tax_liability",
    "sermaye benzeri borçlanma araçları": "subordinated_debt", "diğer yükümlülükler": "other_liabilities", "özkaynaklar": "total_equity",
    "ödenmiş sermaye": "paid_in_capital", "sermaye yedekleri": "capital_reserves", "kâr yedekleri": "profit_reserves", "kar yedekleri": "profit_reserves",
    "geçmiş yıllar kâr veya zararı": "retained_earnings", "geçmiş yıllar kar veya zararı": "retained_earnings",
    "dönem net kâr veya zararı": "net_profit_bs", "dönem net kar veya zararı": "net_profit_bs", "yükümlülükler toplamı": "total_liabilities",
    "azınlık payları": "minority_interests",
}
INCOME_MAP = {
    "faiz gelirleri": "interest_income", "kredilerden alınan faizler": "interest_on_loans", "zorunlu karşılıklardan alınan faizler": "interest_on_reserves",
    "bankalardan alınan faizler": "interest_from_banks", "para piyasası işlemlerinden alınan faizler": "interest_from_money_market",
    "menkul değerlerden alınan faizler": "interest_on_securities", "diğer faiz gelirleri": "other_interest_income",
    "faiz giderleri": "interest_expense", "mevduata verilen faizler": "interest_on_deposits", "kullanılan kredilere verilen faizler": "interest_on_funds_borrowed",
    "para piyasası işlemlerine verilen faizler": "interest_on_money_market", "ihraç edilen menkul kıymetlere verilen faizler": "interest_on_securities_issued",
    "diğer faiz giderleri": "other_interest_expense", "net faiz geliri/gideri": "net_interest_income", "net faiz geliri gideri": "net_interest_income",
    "net ücret ve komisyon gelirleri/giderleri": "net_fee_commission_income", "net ücret ve komisyon gelirleri giderleri": "net_fee_commission_income",
    "alınan ücret ve komisyonlar": "fee_commission_income", "verilen ücret ve komisyonlar": "fee_commission_expense", "temettü gelirleri": "dividend_income",
    "ticari kâr/zarar": "trading_income", "ticari kar/zarar": "trading_income", "ticari kâr zarar": "trading_income", "ticari kar zarar": "trading_income",
    "diğer faaliyet gelirleri": "other_operating_income", "faaliyet brüt karı": "gross_operating_profit",
    "beklenen zarar karşılıkları giderleri": "expected_credit_loss_expense", "diğer karşılık giderleri": "other_provision_expense",
    "personel giderleri": "personnel_expenses", "diğer faaliyet giderleri": "other_operating_expenses", "net faaliyet kârı/zararı": "net_operating_profit",
    "net faaliyet karı/zararı": "net_operating_profit", "sürdürülen faaliyetler vergi öncesi k/z": "profit_before_tax",
    "sürdürülen faaliyetler vergi karşılığı": "tax_provision", "sürdürülen faaliyetler dönem net k/z": "net_profit_continuing",
    "dönem net karı/zararı": "net_profit", "dönem net kârı/zararı": "net_profit",
}


def _normkeys(m: dict) -> dict:
    return {re.sub(r"\s+", " ", normalize_name(k)).strip(): v for k, v in m.items()}


ASSET_MAP, LIAB_MAP, INCOME_MAP = _normkeys(ASSET_MAP), _normkeys(LIAB_MAP), _normkeys(INCOME_MAP)


def _find_sheet(tables: dict[str, pd.DataFrame], suffix: str):
    """Solo kitapta 'varlıklar', konsolide kitapta 'Kvarlıklar' (K öneki)."""
    for k, df in tables.items():
        name = k.split("::")[-1].strip().lower()
        if name == suffix or name == "k" + suffix:
            return k, df
    return None, None


def extract_balance_sheet(tables, bank_raw, code, scope, source_code) -> Extracted:
    ex = Extracted()
    for suffix, cmap in (("varlıklar", ASSET_MAP), ("yüküm.", LIAB_MAP)):
        name, df = _find_sheet(tables, suffix)
        if df is None:
            ex.notes.append(f"{suffix}: sayfa yok")
            continue
        dates = _dates_in(df)
        if len(dates) < 1:
            ex.notes.append(f"{suffix}: dönem tarihi bulunamadı")
            continue
        cur, prev = dates[0], (dates[1] if len(dates) > 1 else None)
        # sütunlar: TP | YP | Toplam blokları — başlıkta 'TP' olan satırı bul
        hdr = next((r for r in range(0, 10) if any(isinstance(df.iat[r, c], str) and df.iat[r, c].strip() == "TP" for c in range(df.shape[1]))), None)
        if hdr is None:
            ex.notes.append(f"{suffix}: TP/YP başlığı yok")
            continue
        blocks = []   # (col, currency, period_end, period_start)
        seen_tp = 0
        for c in range(df.shape[1]):
            v = df.iat[hdr, c]
            if not isinstance(v, str):
                continue
            t = v.strip()
            pe = cur if seen_tp < (1 if t == "TP" else 1) and seen_tp < 1 else None
            if t == "TP":
                seen_tp += 1
                blocks.append((c, "TRY", seen_tp))
            elif t == "YP":
                blocks.append((c, "FX", seen_tp))
            elif t.lower().startswith("toplam"):
                blocks.append((c, "ALL", seen_tp))
        for r in range(hdr + 1, df.shape[0]):
            raw = df.iat[r, 0]
            lab = _lab(raw)
            if not lab:
                continue
            metric = cmap.get(lab)
            if lab == "beklenen zarar karşılıkları":          # aynı etiket iki kez: 1.1.4 likit aktif ECL, 2.5 kredi ECL
                metric = "ecl_allowance_liquid_assets" if raw.strip().startswith("1.1.4") else "ecl_allowance_loans"
            if not metric:
                ex.unmapped_labels.append(f"{suffix}: {raw.strip()[:80]}")
                continue
            for c, ccy, blk in blocks:
                pe = cur if blk == 1 else prev
                if pe is None:
                    continue
                v = to_number(df.iat[r, c])
                ex.observations.append(_o(bank_raw, code, pe, pe, scope, source_code, suffix, r, c, raw.strip(), metric, v, currency=ccy))
    return ex


def extract_income(tables, bank_raw, code, scope, source_code, cur: date | None = None) -> Extracted:
    ex = Extracted()
    name, df = _find_sheet(tables, "gelir")
    if df is None:
        ex.notes.append("gelir: sayfa yok")
        return ex
    # başlıktaki dönem aralıkları: (01/01/2026-30/06/2026) ...
    spans = []
    for r in range(0, 10):
        for c in range(df.shape[1]):
            v = df.iat[r, c]
            if isinstance(v, str):
                m = re.search(r"(\d{2})/(\d{2})/(\d{4})\s*-\s*(\d{2})/(\d{2})/(\d{4})", v)
                if m:
                    spans.append((c, date(int(m.group(3)), int(m.group(2)), int(m.group(1))), date(int(m.group(6)), int(m.group(5)), int(m.group(4)))))
    if cur:   # başlık tarihleri bilanço dönemiyle tutarlı olmalı (cari yıl veya önceki yıl karşılaştırması); bazı bankalar şablon tarihini güncellemiyor
        ok = [sp for sp in spans if sp[2] == cur or (sp[2].month == cur.month and sp[2].year == cur.year - 1)]
        if len(ok) < len(spans):
            ex.notes.append(f"gelir: {len(spans) - len(ok)} sütunun dönem başlığı bilanço tarihiyle ({cur}) tutarsız → atlandı: " +
                            ", ".join(f"{a}-{b}" for _, a, b in spans if (_, a, b) not in ok))
        spans = ok
    if not spans:
        ex.notes.append("gelir: dönem aralıkları bulunamadı")
        return ex
    hdr = max(r for r in range(0, 10) if any(isinstance(df.iat[r, c], str) and "/" in df.iat[r, c] and "-" in df.iat[r, c] for c in range(df.shape[1])))
    for r in range(hdr + 1, df.shape[0]):
        raw = df.iat[r, 0]
        lab = _lab(raw)
        if not lab:
            continue
        metric = INCOME_MAP.get(lab)
        if not metric:
            ex.unmapped_labels.append(f"gelir: {raw.strip()[:80]}")
            continue
        for c, ps, pe in spans:
            v = to_number(df.iat[r, c])
            cum = ps.month == 1 and ps.day == 1
            ex.observations.append(_o(bank_raw, code, pe, ps, scope, source_code, "gelir", r, c, raw.strip(), metric, v, cum=cum))
    return ex


# ---------------------------------------------------------------- dipnotlar
DEP_BUCKETS = [("vadesiz", "demand"), ("7 gün ihbarlı", "notice_7d"), ("1 aya kadar", "0_1m"), ("1 3 ay", "1_3m"), ("3 6 ay", "3_6m"), ("6 ay 1 yıl", "6_12m"),
               ("1 yıl ve üstü", "over_1y"), ("birikimli", "accumulating"), ("toplam", "total")]
DEP_TYPES = [("tasarruf mevduatı", "deposits_savings", "TRY"), ("döviz tevdiat hesabı", "deposits_fx", "FX"), ("yurtiçinde yerleşik", "deposits_fx_resident", "FX"),
             ("yurtdışında yerleşik", "deposits_fx_nonresident", "FX"), ("resmi kur", "deposits_official", "TRY"), ("tic kur", "deposits_commercial", "TRY"),
             ("ticari kur", "deposits_commercial", "TRY"), ("diğ kur", "deposits_other_institutions", "TRY"), ("diğer kur", "deposits_other_institutions", "TRY"),
             ("kıymetli maden", "deposits_precious_metal", "FX"), ("bankalar mevduatı", "deposits_banks", "ALL"), ("tc merkez b", "deposits_banks_cbrt", "ALL"),
             ("yurtiçi bankalar", "deposits_banks_domestic", "ALL"), ("yurtdışı bankalar", "deposits_banks_foreign", "ALL"), ("katılım bankaları", "deposits_banks_participation", "ALL"),
             ("diğer", "deposits_banks_other", "ALL"), ("toplam", "deposits_total", "ALL")]


def extract_deposit_maturity(tables, bank_raw, code, scope, source_code, cur: date, prev: date | None) -> Extracted:
    ex = Extracted()
    name, df = _find_sheet(tables, "pasif1")
    if df is None:
        ex.notes.append("pasif1: sayfa yok")
        return ex
    start = next((r for r in range(df.shape[0]) if isinstance(df.iat[r, 0], str) and "mevduatın vade yapısına" in df.iat[r, 0].lower()), None)
    if start is None:
        ex.notes.append("pasif1: 'Mevduatın vade yapısına ilişkin bilgiler' bloğu yok")
        return ex
    r = start + 1
    period = None
    cols: dict[int, tuple[str, str]] = {}
    while r < min(start + 60, df.shape[0]):
        first = df.iat[r, 0]
        lab = normalize_name(first) if isinstance(first, str) else ""
        if lab.startswith("cari dönem") or lab.startswith("önceki dönem"):
            period = cur if lab.startswith("cari") else prev
            cols = {}
            for c in range(1, df.shape[1]):
                v = df.iat[r, c]
                if isinstance(v, str):
                    n = re.sub(r"\s+", " ", normalize_name(v)).strip()
                    b = next((bk for lab_, bk in DEP_BUCKETS if n.startswith(lab_)), None)
                    if b:
                        cols[c] = (b, v.strip())
            r += 1
            continue
        if period and cols and lab:
            typ = next(((item, ccy) for lab_, item, ccy in DEP_TYPES if lab.startswith(lab_)), None)
            if typ:
                for c, (bucket, blab) in cols.items():
                    v = to_number(df.iat[r, c])
                    ex.observations.append(_o(bank_raw, code, period, period, scope, source_code, "pasif1", r, c, blab, f"maturity:{typ[0]}", v, currency=typ[1],
                                              kind="maturity", item=typ[0], basis="contractual", bucket=bucket, bucket_label_raw=blab))
                if lab.startswith("toplam") and period == prev:
                    break
            else:
                ex.unmapped_labels.append(f"pasif1: {first.strip()[:60]}")
        if isinstance(first, str) and re.match(r"^\s*\d+\.[a-z]", first) and r > start + 2:
            break     # sonraki dipnot başladı
        r += 1
    return ex


RATE_ITEMS = {"verilen krediler": ("loan", "loan_interest"), "diğer mevduat": ("deposit", "deposit_interest"), "bankalar mevduatı": ("interbank_deposit", "interbank_deposit_interest"),
              "bankalar": ("due_from_banks", "due_from_banks_interest"), "para piyasalarından alacaklar": ("money_market_asset", "money_market_asset_interest"),
              "para piyasalarına borçlar": ("money_market_funding", "money_market_funding_interest"), "ihraç edilen menkul değerler": ("securities_issued", "securities_issued_interest"),
              "diğer mali kuruluşlardan sağlanan fonlar": ("funds_from_fi", "funds_from_fi_interest"), "muhtelif borçlar": ("sundry_payables", "sundry_payables_interest"),
              "nakit değerler": ("cash", "cash_interest"), "gerçeğe uygun değer farkı kar zarara yansıtılan finansal varlıklar": ("securities_fvtpl", "securities_fvtpl_interest"),
              "gerçeğe uygun değer farkı diğer kapsamlı gelire yansıtılan finansal varlıklar": ("securities_fvoci", "securities_fvoci_interest"),
              "itfa edilmiş maliyeti üzerinden değerlenen": ("securities_amortized", "securities_amortized_interest")}
CCY = {"euro": "EUR", "usd": "USD", "yen": "JPY", "tl": "TRY"}
MAT_BUCKETS = [("vadesiz", "demand"), ("1 aya kadar", "0_1m"), ("1 3 ay", "1_3m"), ("3 12 ay", "3_12m"), ("1 5 yıl", "1_5y"), ("5 yıl ve üzeri", "over_5y"),
               ("dağıtılama", "unallocated"), ("dağıtılamayan", "unallocated"), ("toplam", "total")]
MAT_ITEMS = {"verilen krediler": "loans", "diğer mevduat": "deposits_other", "bankalar mevduatı": "deposits_banks", "toplam varlıklar": "total_assets",
             "toplam yükümlülükler": "total_liabilities", "likidite açığı": "liquidity_gap", "toplam aktifler": "total_assets", "nakit değerler": "cash",
             "bankalar": "due_from_banks", "para piyasalarından alacaklar": "money_market_receivables", "para piyasalarına borçlar": "money_market_funds",
             "ihraç edilen menkul değerler": "securities_issued", "fonlar": "funds", "muhtelif borçlar": "sundry_payables", "diğer yükümlülükler": "other_liabilities",
             "diğer varlıklar": "other_assets", "net bilanço dışı pozisyon": "net_off_balance_sheet", "gayrinakdi krediler": "non_cash_loans",
             "diğer mali kuruluşlardan sağlanan fonlar": "funds_from_fi", "itfa edilmiş maliyeti": "securities_amortized",
             "gerçeğe uygun değer farkı kar zarara": "securities_fvtpl", "gerçeğe uygun değer farkı diğer kapsamlı": "securities_fvoci",
             "türev finansal varlıklar": "derivative_assets", "türev finansal yükümlülükler": "derivative_liabilities"}


def extract_malibunye1(tables, bank_raw, code, scope, source_code, cur: date, prev: date | None) -> Extracted:
    ex = Extracted()
    name, df = _find_sheet(tables, "malibünye1")
    if df is None:
        ex.notes.append("malibünye1: sayfa yok")
        return ex
    col0 = [(r, df.iat[r, 0].strip()) for r in range(df.shape[0]) if isinstance(df.iat[r, 0], str) and df.iat[r, 0].strip()]
    # --- ortalama faiz oranları blokları
    rate_blocks = [r for r, t in col0 if "ortalama faiz oranları" in t.lower()]
    for bi, start in enumerate(rate_blocks):
        hdr = next((r for r in range(start + 1, start + 5) if sum(1 for c in range(df.shape[1]) if isinstance(df.iat[r, c], str) and normalize_name(df.iat[r, c]) in CCY) >= 3), None)
        if hdr is None:
            ex.notes.append("malibünye1: faiz başlığı (EURO/USD/Yen/TL) bulunamadı")
            continue
        ccols = {c: CCY[normalize_name(df.iat[hdr, c])] for c in range(df.shape[1]) if isinstance(df.iat[hdr, c], str) and normalize_name(df.iat[hdr, c]) in CCY}
        period = None
        for r in range(hdr + 1, min(hdr + 30, df.shape[0])):
            first = df.iat[r, 0]
            if not isinstance(first, str) or not first.strip():
                continue
            lab = _lab(first)
            if lab.startswith("cari dönem"):
                period = cur
                continue
            if lab.startswith("önceki dönem"):
                period = prev
                continue
            if lab in ("varlıklar", "yükümlülükler"):
                continue
            if "ortalama faiz" in lab or "kalan vade" in lab:
                break
            item = next((v for k, v in RATE_ITEMS.items() if lab.startswith(k)), None)
            if not item or period is None:
                if period is not None:
                    ex.unmapped_labels.append(f"malibünye1 faiz: {first.strip()[:60]}")
                continue
            ins, prefix = item
            for c, ccy in ccols.items():
                v = to_number(df.iat[r, c])
                metric = f"{prefix}_{ccy.lower().replace('try', 'tl')}"
                ex.observations.append(_o(bank_raw, code, period, period, scope, source_code, "malibünye1", r, c, first.strip(), metric, v, unit="pct", currency=ccy,
                                          kind="rate", instrument=ins, rate_definition="stock_avg_applied_rate"))
    # --- kalan vade bloğu
    mstart = next((r for r, t in col0 if "kalan vadelerine göre gösterimi" in t.lower()), None)
    if mstart is None:
        ex.notes.append("malibünye1: kalan vade bloğu yok")
        return ex
    hdr = next((r for r in range(mstart + 1, mstart + 5) if sum(1 for c in range(df.shape[1]) if isinstance(df.iat[r, c], str) and normalize_name(df.iat[r, c]).startswith("vadesiz")) >= 1), None)
    if hdr is None:
        ex.notes.append("malibünye1: kalan vade başlığı yok")
        return ex
    bcols = {}
    for c in range(1, df.shape[1]):
        v = df.iat[hdr, c]
        if isinstance(v, str):
            n = re.sub(r"\s+", " ", normalize_name(v)).strip()
            b = next((bk for lab_, bk in MAT_BUCKETS if n.startswith(lab_)), None)
            if b:
                bcols[c] = (b, v.strip())
    period = None
    for r in range(hdr + 1, min(hdr + 60, df.shape[0])):
        first = df.iat[r, 0]
        if not isinstance(first, str) or not first.strip():
            continue
        lab = _lab(first)
        if lab.startswith("cari dönem"):
            period = cur
            continue
        if lab.startswith("önceki dönem"):
            period = prev
            continue
        if lab in ("varlıklar", "yükümlülükler") or first.strip().startswith("*"):
            continue
        if "madde" in lab or re.search(r"\((3 aylık|yıllık)\)\s*$", first.strip().lower()) or ":" in first:
            break                              # sonraki dipnot tablosu başladı
        if period is None:
            continue
        item = next((v for k, v in MAT_ITEMS.items() if lab.startswith(k)), None)
        if not item:
            ex.unmapped_labels.append(f"malibünye1 vade: {first.strip()[:60]}")
            continue
        for c, (bucket, blab) in bcols.items():
            v = to_number(df.iat[r, c])
            ex.observations.append(_o(bank_raw, code, period, period, scope, source_code, "malibünye1", r, c, blab, f"maturity:{item}", v, currency="ALL",
                                      kind="maturity", item=item, basis="remaining", bucket=bucket, bucket_label_raw=blab))
    return ex


def extract_workbook(tables: dict[str, pd.DataFrame], bank_raw: str, registry: BankRegistry, scope: str = "solo", source_code: str = "TBB") -> Extracted:
    code, conf, how = registry.match(bank_raw)
    if conf < 0.92:
        code = None
    name, dfv = _find_sheet(tables, "varlıklar")
    dates = _dates_in(dfv) if dfv is not None else []
    cur = dates[0] if dates else None
    prev = dates[1] if len(dates) > 1 else None
    total = Extracted()
    if cur is None:
        total.notes.append("varlıklar sayfasında dönem tarihi yok — çalışma kitabı atlandı")
        return total
    scale, scale_label = detect_workbook_scale(tables)
    total.scale, total.scale_label = scale, scale_label
    if scale is None:
        total.notes.append("DQ01: ölçek (Bin/Milyon TL) başlıkta bulunamadı — tutar gözlemleri UNVERIFIED")
    token = _SCALE.set((scale, scale_label))
    try:
        for ex in (extract_balance_sheet(tables, bank_raw, code, scope, source_code), extract_income(tables, bank_raw, code, scope, source_code, cur),
                   extract_deposit_maturity(tables, bank_raw, code, scope, source_code, cur, prev), extract_malibunye1(tables, bank_raw, code, scope, source_code, cur, prev)):
            total.observations.extend(ex.observations)
            total.unmapped_labels.extend(ex.unmapped_labels)
            total.notes.extend(ex.notes)
    finally:
        _SCALE.reset(token)
    if not code:
        total.notes.append(f"banka eşlenemedi: {bank_raw}")
    return total
