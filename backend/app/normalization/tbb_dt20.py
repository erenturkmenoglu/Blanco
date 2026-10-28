"""TBB "Banka Bilgileri (Seçilmiş Tablolar, Konsolide Olmayan)" (DT20) Excel seti — GERÇEK düzen (Haziran 2026 dosyaları açılarak doğrulandı).

Dosyalar: 1.Mali bünye.xls, 2.Aktifler.xls, 3.Pasifler.xls, 4.Gelir-Gider.xls, 5.Nazım.xls, Açıklamalar.xls
Her sayfa: satırlar = Sektör Toplamı / gruplar / tek tek bankalar (72 satır), sütunlar = kalemler; başlık 2–4 seviyeli (grup / alt grup / kalem).
Birim: Milyon TL (sayfa başlığında), oranlar %.

Eşleme bu modülde AÇIK ve DEKLARATİF olarak tutulur: her kolon, başlık yolunun ("Grup / Alt grup / Kalem") normalize edilmiş
hâliyle tanınır; tanınmayan kolonlar `unmapped` listesinde raporlanır, tahmin edilmez.
"""
from __future__ import annotations

import re
from datetime import date
from contextvars import ContextVar
from dataclasses import dataclass, field

import pandas as pd

from app.acquisition.parsers import to_number
from .scale import detect_scale
from .bank_names import BankRegistry, normalize_name

SCALE_MTL = 1e6                                   # DT20 sayfalarının başlığı 'Milyon TL' der; yine de her sayfada okunur (DQ01)
_SCALE: ContextVar[tuple[float | None, str | None]] = ContextVar("dt20_scale", default=(None, None))


def _scale() -> float:
    sc, _ = _SCALE.get()
    return sc if sc is not None else SCALE_MTL

# ---------------------------------------------------------------- yardımcılar
def header_segments(df: pd.DataFrame, header_rows: int) -> dict[int, list[str]]:
    """Her sütun için başlık yolu (segment listesi). Üst seviyelerde (grup başlıkları) soldan sağa ileri doldurma (ffill) uygulanır;
    bir üst seviyede yeni etiket geldiğinde alt seviyelerin doldurması sıfırlanır (alt grup, ait olduğu grubun dışına taşmaz).
    Yaprak (en alt) seviye doldurulmaz."""
    nrows = min(header_rows, df.shape[0])
    raw = [[(re.sub(r"\s+", " ", df.iat[r, c].strip()) if isinstance(df.iat[r, c], str) and df.iat[r, c].strip() else None)
            for c in range(df.shape[1])] for r in range(nrows)]
    leaf_row = {}
    for c in range(df.shape[1]):
        rows_with = [r for r in range(nrows) if raw[r][c]]
        leaf_row[c] = max(rows_with) if rows_with else None
    carried: list[str | None] = [None] * nrows          # satır başına taşınan (ffill) etiket
    out: dict[int, list[str]] = {}
    for c in range(1, df.shape[1]) if df.shape[1] > 1 else []:
        for r in range(nrows):
            if raw[r][c]:
                carried[r] = raw[r][c]
                for rr in range(r + 1, nrows):        # yeni üst etiket → alt seviyeler sıfırlanır
                    carried[rr] = None
        segs: list[str] = []
        if leaf_row[c] is not None:
            for r in range(nrows):
                if r < leaf_row[c] and carried[r]:
                    segs.extend(x.strip() for x in carried[r].split(" / "))
                elif r == leaf_row[c]:
                    segs.extend(x.strip() for x in raw[r][c].split(" / "))
        dedup: list[str] = []
        for x in segs:
            if not dedup or dedup[-1] != x:
                dedup.append(x)
        out[c] = dedup
    out[0] = [x for r in range(nrows) if raw[r][0] for x in raw[r][0].split(" / ")] if df.shape[1] else []
    return out


def header_paths(df: pd.DataFrame, header_rows: int) -> dict[int, str]:
    return {c: " / ".join(segs) for c, segs in header_segments(df, header_rows).items()}


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", normalize_name(s)).strip()


def find_header_rows(df: pd.DataFrame) -> int:
    """'Banka' etiketli hücrenin bulunduğu satıra kadar (dahil) başlık sayılır; ardından ilk veri satırı 'Sektör' ile başlar."""
    for r in range(min(12, df.shape[0])):
        v = df.iat[r, 0]
        if isinstance(v, str) and _norm(v) in ("banka", "bankalar"):
            # bazı sayfalarda Banka hücresinden sonra bir alt başlık satırı daha vardır
            for rr in range(r + 1, min(r + 9, df.shape[0])):
                w = df.iat[rr, 0]
                if isinstance(w, str) and w.strip():
                    return rr            # ilk veri satırı (Sektör Toplamı) → başlık satırı sayısı
            return r + 1
    return 7


def bank_rows(df: pd.DataFrame, start: int, registry: BankRegistry):
    """(row, raw_name, bank_code|None, is_aggregate) — grup/sektör satırları aggregate, dipnot satırları atlanır."""
    for r in range(start, df.shape[0]):
        v = df.iat[r, 0]
        if not isinstance(v, str) or not v.strip():
            continue
        raw = v.strip()
        if raw.startswith(("*", "(", "Not", "Kaynak")) or len(raw) > 70:
            continue
        code, conf, how = registry.match(raw)
        if conf >= 0.92:
            yield r, raw, code, False
        elif registry.is_aggregate(raw) or raw.lower().startswith(("kalkınma ve yatırım", "tas. mevd", "sektör")):
            yield r, raw, None, True
        else:
            yield r, raw, None, False     # eşleşmeyen banka → DQ01


@dataclass
class Extracted:
    observations: list[dict] = field(default_factory=list)      # pipeline._write biçimi (kind: financial|rate|maturity)
    unmapped_columns: list[str] = field(default_factory=list)
    unmatched_banks: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


def _segs(path: str) -> list[str]:
    return [_norm(x) for x in path.split(" / ") if _norm(x)]


def _match_col(paths: dict[int, str], needle: str) -> int | None:
    """Anahtarın segmentleri, kolonun başlık yolunun SONEKİ ise eşleşir (tam yol veya son k segment). Tek eşleşme şartı."""
    ns = _segs(needle)
    if not ns:
        return None
    exact = [c for c, p in paths.items() if _segs(p) == ns]
    if len(exact) == 1:
        return exact[0]
    hits = [c for c, p in paths.items() if _segs(p)[-len(ns):] == ns]
    return hits[0] if len(hits) == 1 else None


# ---------------------------------------------------------------- deklaratif kolon haritaları (başlık yolu → metrik)
# Varlıklar (2.Aktifler.xls)
VARLIKLAR_MAP = {
    "Finansal Varlıklar (net) / Likit Aktifler / Nakit Değerler ve TCMB": "cash_and_central_bank",
    "Bankalar": "due_from_banks",
    "Para Piyasalarından Alacaklar": "money_market_receivables",
    "Beklenen Zarar Karşılıkları (-) (TFRS 9 uygulayan b.)": "ecl_allowance_liquid_assets",
    "Gerçeğe Uygun Değer Farkı K/Z Yansıtulan FV": "securities_fvtpl",
    "Gerçeğe Uygun Değer Farkı Diğer Kaps. Gelire Yansı. FV": "securities_fvoci",
    "Türev Finansal Varlıklar": "derivative_assets",
    "İtfa Edilmiş Maliyeti ile Ölçülen FV (Net) / Krediler": "loans_gross",
    "Kiralama İşlemleri. Alacaklar": "lease_receivables",
    "Faktoring Alacakları": "factoring_receivables",
    "İtfa Edilmiş Maliyeti ile Ölçülen Diğer FV / Devlet Borçlanma Senetleri": "securities_amortized_government",
    "Diğer Finansal Varlıklar": "securities_amortized_other",
    "Beklenen Zarar Karşılık. ( - ) (TFRS 9 uygulayan b.)": "ecl_allowance_loans",
    "Donuk Alacaklar (TFRS 9 uygulamayan b.)": "npl_non_tfrs9",
    "Özel Karşılıklar ( - ) (TFRS 9 uygulamayan b.)": "specific_provisions_non_tfrs9",
    "Maddi Duran Varlıklar": "fixed_assets",
    "Maddi Olmayan Duran Varlıklar (net)": "intangible_assets",
    "Yatırım Amaçlı Gayri- menkuller (net)": "investment_property",
    "Diğer Aktifler": "other_assets_dt20",          # bilanço 'X. Diğer Aktifler (Net)' ile aynı tanım DEĞİL → ayrı kod
    "Toplam Aktifler": "total_assets",
}
# 'Toplam' sütunları konuma göre (aynı etiket birden çok kez geçer): sırayla Likit Aktifler Toplam, Finansal Varlıklar Toplam, İtfa Diğer FV Toplam,
# İtfa FV Toplam, Ortaklık Toplam, Duran Varlık Toplam
VARLIKLAR_TOPLAM_SEQ = ["financial_assets", "securities_amortized_total", "amortized_cost_assets_total", "equity_investments", "non_current_assets_total"]

YUKUMLULUKLER_MAP = {
    "Mevduat": "total_deposits",
    "Mevduat Dışı Kaynaklar / Alınan Krediler": "funds_borrowed",
    "Para Piyasalarına Borçlar": "money_market_funds",
    "İhraç Edilen Menkul Kıymetler (net)": "securities_issued",
    "Fonlar": "funds",
    "Diğer Pasifler / Gerçeğe Uygun Değer Farkı K/Z Yansıtılan FY": "fvtpl_liabilities",
    "Türev Finansal Yükümlü-lükler": "derivative_liabilities",
    "Karşılıklar": "provisions",
    "Cari ve Ertelenmiş Vergi Borcu": "tax_liabilities",
    "Sermaye Benzeri Borçlanma Araçları": "subordinated_debt",
    "Sınıflandırıl- mayan Pasifler": "other_unclassified_liabilities",
    "Özkaynaklar / Ödenmiş Sermaye": "paid_in_capital",
    "Sermaye Yedekleri": "capital_reserves",
    "Kar Yedekleri": "profit_reserves",
    "Kar (Zarar) / Geçmiş Yıl Karı (Zararı)": "retained_earnings",
    "Dönem Net Karı (Zararı)": "net_profit_bs",
    "Toplam Yükümlülükler": "total_liabilities",
}
YUKUMLULUKLER_TOPLAM_SEQ = ["non_deposit_funding", "other_liabilities_group_dt20", "profit_loss_total", "total_equity"]
# Konsolide (DT21) 'Özkaynaklar / Toplam' azınlık paylarını İÇERMEZ (İş Bankası Haz-2026: 454.045 vs XVI. Özkaynaklar 540.585) → total_equity_parent
YUKUMLULUKLER_TOPLAM_SEQ_CONS = ["non_deposit_funding", "other_liabilities_group_dt20", "profit_loss_total", "total_equity_parent"]

GELIR_GIDER_MAP = {
    "Faaliyet Gelir-Giderleri / Faiz Gelirleri / Kredilerden Alınan Faiz": "interest_on_loans",
    "Bankalardan Alınan Faiz": "interest_from_banks",
    "Menkul Değerlerden Alınan Faiz": "interest_on_securities",
    "Diğer Faiz Gelirleri": "other_interest_income_residual_dt20",     # DT20: Toplam − (krediler + bankalar + menkul) KALANI; bilanço 1.7 satırı DEĞİL
    "Faiz Giderleri / Mevduata Verilen Faiz": "interest_on_deposits",
    "Kullanılan Kredilere Verilen Faiz": "interest_on_funds_borrowed",
    "Diğer Faiz Gider.": "other_interest_expense_residual_dt20",      # DT20: Toplam − (mevduat + kullanılan krediler) KALANI; bilanço 2.6 satırı DEĞİL
    "Net Faiz Geliri / Gideri": "net_interest_income",
    "Net Ücret ve Komisyon Gel. / Gid. / Alınan Ücret ve Komisyon": "fee_commission_income",
    "Verilen Ücret ve Komisyon": "fee_commission_expense",
    "Net": "net_fee_commission_income",
    "Temettü Geliri": "dividend_income",
    "Ticari Kar -Zarar (net)": "trading_income",
    "Diğer Faaliyet Gelirleri": "other_operating_income",
    "Faaliyet Brüt Karı": "gross_operating_profit",
    "(TFRS 9 Uygulayan Bankalar) Beklenen Zarar Karş. (-)": "expected_credit_loss_expense",
    "(TFRS Uygulayan Bankalar) Diğer Karşılık Giderleri (-)": "other_provision_expense",
    "(TFRS 9 Uygulama- yan Bankalar) Kredi Karş. (-)": "loan_provision_expense_non_tfrs9",
    "Personel Giderleri": "personnel_expenses",
    "Diğer Faaliyet Giderleri (-)": "other_operating_expenses",
    "Net Faaliyet Karı / Zararı": "net_operating_profit",
    "Sürdürülen Faaliyetler Vergi Öncesi K/Z": "profit_before_tax",
    "Sürdürülen Faaliyetler Vergi Karşılığı (+/-)": "tax_provision",
    "Net Dönem Karı (Zararı)": "net_profit",
}
GELIR_TOPLAM_SEQ = ["interest_income", "interest_expense"]

SERMAYE_MAP = {"Toplam Risk Ağırlıklı Tutarlar / (Milyon TL)": ("risk_weighted_assets", "TRY"),
               "Özkaynak / (Milyon TL)": ("regulatory_equity", "TRY"),
               "Sermaye Yeterliliği Oranı / (%)": ("capital_adequacy_ratio", "pct")}
NSFR_MAP = {"Mevcut İstikrarlı Fon / (Milyon TL)": ("available_stable_funding", "TRY"),
            "Gerekli İstikrarlı Fon / (Milyon TL)": ("required_stable_funding", "TRY"),
            "Net İstikrarlı Fonlama Oranı / (%)": ("nsfr", "pct")}
DONUK_MAP = {"Toplam donuk alacak hareketleri / Dönem Sonu Bakiyesi": "npl_amount",
             "Toplam donuk alacak hareketleri / Önceki Dönem Sonu Bakiyesi": "npl_amount_prior_year_end"}
DONUK_AFTER = {"Karşılık (-)": "npl_provisions", "Bilançodaki Net Bakiyesi": "npl_net"}   # npl_amount kolonundan sonraki iki kolon
STD_YAKIN_MAP = {"Standart Nitelikli Krediler / İhtisas Dışı Krediler / İşletme Kredileri": None}   # yalnızca Toplam kolonları kullanılır
KARSILIK_MAP = {"12 Aylık Beklenen Zarar Karşılığı (Birinci Aşama)": "ecl_stage1", "Kredi Riskinde Önemli Artış (İkinci Aşama)": "ecl_stage2",
                "Temerrüt (Üçüncü Aşama)": "ecl_stage3"}

RATE_CURRENCIES = {"tl": "TRY", "usd": "USD", "euro": "EUR", "eur": "EUR"}
MATURITY_BUCKETS = [("vadesiz", "demand"), ("1 ay", "0_1m"), ("1 3 ay", "1_3m"), ("3 12 ay", "3_12m"), ("1 5 yıl", "1_5y"),
                    ("5 yıl ve üzeri", "over_5y"), ("dağıtıla mayan", "unallocated"), ("dağıtılamayan", "unallocated"),
                    ("toplam varlıklar", "total"), ("toplam yükümlü lükler", "total"), ("toplam yükümlülükler", "total"), ("toplam", "total")]
DEPOSIT_TYPES = [("tasarruf mevduatı", "deposits_savings", "TRY"), ("döviz tevdiat hesabı / yurtiçinde yerleşik kişiler", "deposits_fx_resident", "FX"),
                 ("yurtdışında yerleşik kişiler", "deposits_fx_nonresident", "FX"), ("resmi kuruluşlar mevduatı", "deposits_official", "TRY"),
                 ("ticari kuruluşlar mevduatı", "deposits_commercial", "TRY"), ("diğer kuruluşlar mevduatı", "deposits_other_institutions", "TRY"),
                 ("kıymetli maden depo hesabı", "deposits_precious_metal", "FX"), ("döviz tevdiat hesabı", "deposits_fx", "FX"),
                 ("bankalar mevduatı", "deposits_banks", "ALL"), ("bankalar mevduatı / tc merkez bankası", "deposits_banks_cbrt", "ALL"),
                 ("yurtiçi bankalar", "deposits_banks_domestic", "ALL"), ("yurtdışı bankalar", "deposits_banks_foreign", "ALL"),
                 ("katılım bankaları", "deposits_banks_participation", "ALL"), ("diğer", "deposits_banks_other", "ALL"), ("toplam", "deposits_total", "ALL")]
DEPOSIT_BUCKETS = [("vadesiz 7 gün ihbarlı mevduat", "demand_7d"), ("1 aya kadar", "0_1m"), ("1 3 ay", "1_3m"), ("3 ay ve üstü", "over_3m"), ("3 ay", "over_3m"), ("toplam", "total")]


def _base(bank_raw, code, pe, scope, source_code, sheet, r, c, label):
    sc, lab = _SCALE.get()
    return dict(scale_label=lab, scale_detected=sc is not None, bank_raw=bank_raw, bank_code=code, bank_match="alias" if code else "none", period_end=pe, period_start=pe, reporting_scope=scope,
                frequency="quarterly", source_code=source_code, sheet=sheet, row=r, col=c, label_raw=label)


# ---------------------------------------------------------------- sayfa çıkarıcıları
def extract_wide_sheet(df: pd.DataFrame, sheet: str, colmap: dict[str, str], toplam_seq: list[str], registry: BankRegistry, pe, scope: str,
                       source_code: str, unit: str = "TRY", scale: float | None = None, cumulative: bool = False) -> Extracted:
    """Satır=banka, sütun=kalem düzeni. 'Toplam' başlıklı sütunlar konuma göre `toplam_seq` ile adlandırılır."""
    scale = scale if scale is not None else _scale()
    ex = Extracted()
    hr = find_header_rows(df)
    paths = header_paths(df, hr)
    col_to_metric: dict[int, str] = {}
    toplam_cols = [c for c, p in paths.items() if _norm(p).endswith("toplam") and not _norm(p).startswith("toplam ") and c != 0]
    for i, c in enumerate(toplam_cols):
        if i < len(toplam_seq):
            col_to_metric[c] = toplam_seq[i]
    for path, metric in colmap.items():
        c = _match_col(paths, path)
        if c is None:
            ex.unmapped_columns.append(f"{sheet}: başlık bulunamadı → {path}")
        else:
            col_to_metric[c] = metric
    for c, p in paths.items():
        if c != 0 and p and c not in col_to_metric:
            ex.unmapped_columns.append(f"{sheet}: c{c} {p}")
    for r, raw, code, agg in bank_rows(df, hr, registry):
        if agg:
            continue
        if not code:
            ex.unmatched_banks.append(raw)
            continue
        for c, metric in col_to_metric.items():
            v = to_number(df.iat[r, c])
            o = _base(raw, code, pe, scope, source_code, sheet, r, c, paths[c])
            o.update(metric_code=metric, unit=unit, scale=scale if unit == "TRY" else 1.0, currency="ALL", value_raw=v,
                     value=(v * scale) if (v is not None and unit == "TRY") else v, cumulative_ytd=cumulative, kind="financial",
                     period_start=date(pe.year, 1, 1) if cumulative else pe)      # Gelir-Gider yıl başından kümülatif → period_start = 1 Ocak
            ex.observations.append(o)
    return ex


def extract_ratio_sheet(df, sheet, colmap: dict[str, tuple[str, str]], registry, pe, scope, source_code) -> Extracted:
    ex = Extracted()
    hr = find_header_rows(df)
    paths = header_paths(df, hr)
    for r, raw, code, agg in bank_rows(df, hr, registry):
        if agg or not code:
            if not agg:
                ex.unmatched_banks.append(raw)
            continue
        for path, (metric, unit) in colmap.items():
            c = _match_col(paths, path)
            if c is None:
                ex.unmapped_columns.append(f"{sheet}: {path}")
                continue
            v = to_number(df.iat[r, c])
            o = _base(raw, code, pe, scope, source_code, sheet, r, c, paths[c])
            o.update(metric_code=metric, unit=unit, scale=_scale() if unit == "TRY" else 1.0, currency="ALL", value_raw=v,
                     value=(v * _scale()) if (v is not None and unit == "TRY") else v, cumulative_ytd=False, kind="financial")
            ex.observations.append(o)
    return ex


def extract_rates(df, sheet, registry, pe, scope, source_code) -> Extracted:
    """'Ort.Faiz Oranı': başlık satırı 1: Banka | TL | | USD | | EURO ; satır 2: Verilen Krediler | Mevduat** ..."""
    ex = Extracted()
    hr = find_header_rows(df)
    cur_row = ins_row = None
    for r in range(hr):
        cells = [_norm(str(x)) for x in df.iloc[r].tolist() if isinstance(x, str)]
        if sum(1 for c in cells if c in RATE_CURRENCIES) >= 2:
            cur_row = r
        if sum(1 for c in cells if c.startswith("verilen kredi") or c.startswith("mevduat")) >= 2:
            ins_row = r
    if cur_row is None or ins_row is None:
        ex.notes.append(f"{sheet}: faiz başlıkları bulunamadı")
        return ex
    cols, cur = {}, None
    for c in range(df.shape[1]):
        v = df.iat[cur_row, c]
        if isinstance(v, str) and _norm(v) in RATE_CURRENCIES:
            cur = RATE_CURRENCIES[_norm(v)]
        w = df.iat[ins_row, c]
        if isinstance(w, str) and cur:
            n = _norm(w)
            if n.startswith("verilen kredi"):
                cols[c] = ("loan", cur)
            elif n.startswith("mevduat"):
                cols[c] = ("deposit", cur)
    for r, raw, code, agg in bank_rows(df, hr, registry):
        if agg or not code:
            if not agg:
                ex.unmatched_banks.append(raw)
            continue
        for c, (ins, cur) in cols.items():
            v = to_number(df.iat[r, c])
            o = _base(raw, code, pe, scope, source_code, sheet, r, c, f"{cur} {ins}")
            o.update(metric_code=f"{ins}_interest_{cur.lower().replace('try', 'tl')}", unit="pct", scale=1.0, currency=cur, value_raw=v, value=v,
                     instrument=ins, rate_definition="stock_avg_applied_rate", kind="rate")
            ex.observations.append(o)
    return ex


def extract_liquidity_maturity(df, sheet, registry, pe, scope, source_code) -> Extracted:
    """'Likidite Riski': Varlıklar / Yükümlülükler / Likidite Açığı × kovalar → maturity (item total_assets|total_liabilities|liquidity_gap)."""
    ex = Extracted()
    hr = find_header_rows(df)
    paths = header_paths(df, hr)
    cols = {}
    group = None
    for c in range(1, df.shape[1]):
        segs = _segs(paths.get(c, ""))
        if not segs:
            continue
        if segs[0].startswith("varlıklar"):
            group = "total_assets"
        elif segs[0].startswith("yükümlülükler"):
            group = "total_liabilities"
        elif segs[0].startswith("likitide açığı") or segs[0].startswith("likidite açığı"):
            group = "liquidity_gap"
        last = segs[-1]
        bucket = next((b for lab, b in MATURITY_BUCKETS if last.startswith(lab)), None)
        if group and bucket:
            cols[c] = (group, bucket, paths[c].split(" / ")[-1])
        else:
            ex.unmapped_columns.append(f"{sheet}: c{c} {paths[c]}")
    for r, raw, code, agg in bank_rows(df, hr, registry):
        if agg or not code:
            if not agg:
                ex.unmatched_banks.append(raw)
            continue
        for c, (item, bucket, lab) in cols.items():
            v = to_number(df.iat[r, c])
            o = _base(raw, code, pe, scope, source_code, sheet, r, c, lab)
            o.update(metric_code=f"maturity:{item}", unit="TRY", scale=_scale(), currency="ALL", value_raw=v,
                     value=(v * _scale()) if v is not None else None, item=item, basis="remaining", bucket=bucket, bucket_label_raw=lab, kind="maturity")
            ex.observations.append(o)
    return ex


def extract_deposit_maturity(df, sheet, registry, pe, scope, source_code) -> Extracted:
    """'Mevd.Vade': mevduat türü × (Vadesiz+7 Gün | 1 Aya Kadar | 1-3 Ay | 3 Ay ve Üstü | Toplam). Kovalar kaynağın kendisidir (3 ay+ bölünmez).
    basis='contractual_coarse' (4 kova) — banka çalışma kitabı dipnotu 2.a.1.i ise 'contractual' (9 kova); iki küme BİRLEŞTİRİLMEZ."""
    ex = Extracted()
    hr = find_header_rows(df)
    paths = header_paths(df, hr)
    # Gerçek düzen: satır A = mevduat türü (birleştirilmiş hücre), satır B = alt grup (yalnızca DTH: Yurtiçi/Yurtdışı; Bankalar Mevduatı:
    # TCMB/Yurtiçi/Yurtdışı/Katılım/Diğer), satır C = kova. Türün 'Toplam' sütunu alt grup satırında BOŞTUR → alt grup etiketi oraya taşınmaz.
    segs_by_col = header_segments(df, hr)
    leaf_row = {}
    for c in range(df.shape[1]):
        rws = [r for r in range(min(hr, df.shape[0])) if isinstance(df.iat[r, c], str) and df.iat[r, c].strip()]
        leaf_row[c] = max(rws) if rws else None
    cols = {}
    current = None
    for c in range(1, df.shape[1]):
        segs = _segs(paths.get(c, ""))
        if not segs:
            continue
        head, last = " / ".join(segs[:-1]), segs[-1]
        if last.startswith("toplam") and len(segs) >= 3 and leaf_row[c] is not None:
            # 'Toplam' yaprağı: alt grup satırı bu sütunda boşsa yol = tür / Toplam (alt grup düşer)
            sub_row = leaf_row[c] - 1
            sub_cell = df.iat[sub_row, c] if sub_row >= 0 else None
            if not (isinstance(sub_cell, str) and sub_cell.strip()):
                head = segs[0]
        if head:
            for lab, item, cur in DEPOSIT_TYPES:
                if head.endswith(lab):
                    current = (item, cur)
                    break
        elif segs == ["toplam"]:                  # tablonun en sağındaki genel 'Toplam / Toplam' bloğu (ardışık tekrar tekilleşti)
            current = ("deposits_total", "ALL")
        bucket = next((b for lab, b in DEPOSIT_BUCKETS if last.startswith(lab)), None)
        if current and bucket:
            cols[c] = (current[0], current[1], bucket, paths[c].split(" / ")[-1])
        else:
            ex.unmapped_columns.append(f"{sheet}: c{c} {paths[c]}")
    for r, raw, code, agg in bank_rows(df, hr, registry):
        if agg or not code:
            if not agg:
                ex.unmatched_banks.append(raw)
            continue
        for c, (item, cur, bucket, lab) in cols.items():
            v = to_number(df.iat[r, c])
            o = _base(raw, code, pe, scope, source_code, sheet, r, c, lab)
            o.update(metric_code=f"maturity:{item}", unit="TRY", scale=_scale(), currency=cur, value_raw=v,
                     value=(v * _scale()) if v is not None else None, item=item, basis="contractual_coarse", bucket=bucket, bucket_label_raw=lab, kind="maturity")
            ex.observations.append(o)
    return ex


def extract_npl(df, sheet, registry, pe, scope, source_code) -> Extracted:
    ex = Extracted()
    hr = find_header_rows(df)
    paths = header_paths(df, hr)
    c_npl = _match_col(paths, "Toplam donuk alacak hareketleri / Dönem Sonu Bakiyesi")
    if c_npl is None:
        ex.notes.append(f"{sheet}: 'Toplam donuk alacak hareketleri / Dönem Sonu Bakiyesi' bulunamadı")
        return ex
    cols = {c_npl: "npl_amount", c_npl + 1: "npl_provisions", c_npl + 2: "npl_net"}
    for r, raw, code, agg in bank_rows(df, hr, registry):
        if agg or not code:
            if not agg:
                ex.unmatched_banks.append(raw)
            continue
        for c, metric in cols.items():
            v = to_number(df.iat[r, c])
            o = _base(raw, code, pe, scope, source_code, sheet, r, c, paths.get(c, ""))
            o.update(metric_code=metric, unit="TRY", scale=_scale(), currency="ALL", value_raw=v, value=(v * _scale()) if v is not None else None,
                     cumulative_ytd=False, kind="financial")
            ex.observations.append(o)
    return ex


def extract_stage_loans(df, sheet, registry, pe, scope, source_code) -> Extracted:
    """'Std.Nit.-Yakın İzl.Kred.': Toplam sütunları konuma göre: stage1, stage2 (yapılandırılmamış), stage2 restructured (sözleşme değişikliği),
    stage2 refinansman, Genel Toplam."""
    ex = Extracted()
    hr = find_header_rows(df)
    paths = header_paths(df, hr)
    toplam = [c for c, p in paths.items() if _norm(p).endswith("toplam") and c != 0]
    seq = ["stage_1_loans", "stage_2_loans_not_restructured", "stage_2_restructured_modified", "stage_2_restructured_refinanced", "loans_stage1_stage2_total"]
    cols = {c: seq[i] for i, c in enumerate(toplam) if i < len(seq)}
    for r, raw, code, agg in bank_rows(df, hr, registry):
        if agg or not code:
            if not agg:
                ex.unmatched_banks.append(raw)
            continue
        for c, metric in cols.items():
            v = to_number(df.iat[r, c])
            o = _base(raw, code, pe, scope, source_code, sheet, r, c, paths.get(c, ""))
            o.update(metric_code=metric, unit="TRY", scale=_scale(), currency="ALL", value_raw=v, value=(v * _scale()) if v is not None else None,
                     cumulative_ytd=False, kind="financial")
            ex.observations.append(o)
    return ex


def extract_dt20_tables(tables: dict[str, pd.DataFrame], registry: BankRegistry, pe, scope: str = "solo", source_code: str = "TBB") -> Extracted:
    """parse_bytes çıktısındaki sayfa adlarına göre uygun çıkarıcıyı çağırır (dosya adından bağımsız)."""
    total = Extracted()
    for name, df in tables.items():
        sheet = name.split("::")[-1].strip()
        hit = detect_scale(df, rows=8)
        token = _SCALE.set(hit if hit else (None, None))
        if not hit:
            total.notes.append(f"DQ01: {sheet}: ölçek (Milyon/Bin TL) başlıkta bulunamadı — tutar gözlemleri UNVERIFIED")
        try:
            if sheet == "Varlıklar":
                ex = extract_wide_sheet(df, sheet, VARLIKLAR_MAP, VARLIKLAR_TOPLAM_SEQ, registry, pe, scope, source_code)
            elif sheet == "Yükümlülükler":
                ex = extract_wide_sheet(df, sheet, YUKUMLULUKLER_MAP, YUKUMLULUKLER_TOPLAM_SEQ_CONS if scope == "consolidated" else YUKUMLULUKLER_TOPLAM_SEQ,
                                        registry, pe, scope, source_code)
            elif sheet == "Gelir-Gider":
                ex = extract_wide_sheet(df, sheet, GELIR_GIDER_MAP, GELIR_TOPLAM_SEQ, registry, pe, scope, source_code, cumulative=True)
            elif sheet == "Sermaye Std. Oranı":
                ex = extract_ratio_sheet(df, sheet, SERMAYE_MAP, registry, pe, scope, source_code)
            elif sheet == "Net İstik.Fon.Oranı":
                ex = extract_ratio_sheet(df, sheet, NSFR_MAP, registry, pe, scope, source_code)
            elif sheet == "Ort.Faiz Oranı":
                ex = extract_rates(df, sheet, registry, pe, scope, source_code)
            elif sheet == "Likidite Riski":
                ex = extract_liquidity_maturity(df, sheet, registry, pe, scope, source_code)
            elif sheet == "Mevd.Vade":
                ex = extract_deposit_maturity(df, sheet, registry, pe, scope, source_code)
            elif sheet == "Donuk Alacak":
                ex = extract_npl(df, sheet, registry, pe, scope, source_code)
            elif sheet == "Std.Nit.-Yakın İzl.Kred.":
                ex = extract_stage_loans(df, sheet, registry, pe, scope, source_code)
            elif sheet == "Karşılıklar":
                ex = extract_wide_sheet(df, sheet, KARSILIK_MAP, ["ecl_total_tfrs9"], registry, pe, scope, source_code)
            else:
                total.notes.append(f"atlandı: {sheet}")
                continue
        except Exception as exc:   # bir sayfa bozuksa diğerleri etkilenmez
            total.notes.append(f"{sheet}: HATA {type(exc).__name__}: {exc}")
            continue
        finally:
            _SCALE.reset(token)
        total.observations.extend(ex.observations)
        total.unmapped_columns.extend(ex.unmapped_columns)
        total.unmatched_banks.extend(ex.unmatched_banks)
        total.notes.extend(ex.notes)
    total.unmatched_banks = sorted(set(total.unmatched_banks))
    return total
