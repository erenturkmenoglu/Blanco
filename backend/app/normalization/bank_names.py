"""Banka adı standardizasyonu.

- `normalize_name` Türkçe'ye duyarlı (İ/ı) küçük harf + hukuki sonek temizliği + noktalama temizliği.
- Eşleme sırası: (1) alias tablosu / tohum listesi tam eşleşme, (2) yüksek benzerlik (difflib ≥ 0.92) + UYARI,
  (3) eşleşme yoksa yeni kuruluş kaydı + DQ01 uyarısı (sessizce yanlış bankaya yazılmaz).
- Tohum listesi TBB üyesi bankaları (mevduat + kalkınma/yatırım) kapsar. KATILIM bankaları TBB değil TKBB üyesidir;
  TBB tablolarında yer almazlar → katılım bankaları için ayrı kaynak (TKBB) gerekir.
"""
from __future__ import annotations

import difflib
import re
import unicodedata

LEGAL_SUFFIXES = [
    r"\bt\.?a\.?ş\.?\b", r"\ba\.?ş\.?\b", r"\bt\.?a\.?o\.?\b", r"\ba\.?o\.?\b", r"\bn\.?a\.?\b", r"\bs\.?p\.?a\.?\b",
    r"\bs\.?a\.?\b", r"\blimited\b", r"\bltd\.?\b", r"\binc\.?\b",
]

TR_LOWER = str.maketrans({"I": "ı", "İ": "i"})


def normalize_name(raw: str) -> str:
    s = (raw or "").strip().translate(TR_LOWER).lower()
    s = unicodedata.normalize("NFKC", s)
    s = re.sub(r"\(\s*\d+\s*\)", " ", s)              # dipnot numaraları: "Ziraat (1)"
    s = re.sub(r"[\*†‡]+", " ", s)
    for pat in LEGAL_SUFFIXES:
        s = re.sub(pat, " ", s)
    s = re.sub(r"[^\w\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


# code → (resmî ad, tür, sahiplik, [alias'lar])   — tohum; kaynak dosyalarından genişletilir
SEED_BANKS: dict[str, tuple[str, str, str, list[str]]] = {
    "ziraat": ("Türkiye Cumhuriyeti Ziraat Bankası A.Ş.", "deposit", "public", ["Ziraat", "Ziraat Bankası", "T.C. Ziraat Bankası", "T.C. Ziraat Bankası A.Ş."]),
    "halkbank": ("Türkiye Halk Bankası A.Ş.", "deposit", "public", ["Halk", "Halkbank", "Türkiye Halk Bankası"]),
    "vakifbank": ("Türkiye Vakıflar Bankası T.A.O.", "deposit", "public", ["Vakıflar", "VakıfBank", "Türkiye Vakıflar Bankası"]),
    "akbank": ("Akbank T.A.Ş.", "deposit", "private", ["Akbank"]),
    "anadolubank": ("Anadolubank A.Ş.", "deposit", "private", ["Anadolubank"]),
    "fibabanka": ("Fibabanka A.Ş.", "deposit", "private", ["Fibabanka"]),
    "sekerbank": ("Şekerbank T.A.Ş.", "deposit", "private", ["Şekerbank"]),
    "turkishbank": ("Turkish Bank A.Ş.", "deposit", "private", ["Turkish Bank"]),
    "teb": ("Türk Ekonomi Bankası A.Ş.", "deposit", "private", ["TEB", "Türk Ekonomi Bankası"]),
    "isbank": ("Türkiye İş Bankası A.Ş.", "deposit", "private", ["İş Bankası", "İşbank", "Türkiye İş Bankası"]),
    "yapikredi": ("Yapı ve Kredi Bankası A.Ş.", "deposit", "private", ["Yapı Kredi", "Yapı ve Kredi Bankası"]),
    "alternatifbank": ("Alternatifbank A.Ş.", "deposit", "foreign", ["Alternatifbank", "Alternatif Bank", "Alternatif Bank A.Ş."]),
    "arapturk": ("Arap Türk Bankası A.Ş.", "deposit", "foreign", ["Arap Türk Bankası", "Arap Türk"]),
    "bankofchina": ("Bank of China Turkey A.Ş.", "deposit", "foreign", ["Bank of China Turkey", "Bank of China"]),
    "burgan": ("Burgan Bank A.Ş.", "deposit", "foreign", ["Burgan Bank", "Burgan"]),
    "citibank": ("Citibank A.Ş.", "deposit", "foreign", ["Citibank"]),
    "denizbank": ("Denizbank A.Ş.", "deposit", "foreign", ["Denizbank", "DenizBank"]),
    "deutsche": ("Deutsche Bank A.Ş.", "deposit", "foreign", ["Deutsche Bank"]),
    "garanti": ("Türkiye Garanti Bankası A.Ş.", "deposit", "foreign", ["Garanti", "Garanti BBVA", "Türkiye Garanti Bankası"]),
    "hsbc": ("HSBC Bank A.Ş.", "deposit", "foreign", ["HSBC", "HSBC Bank"]),
    "icbc": ("ICBC Turkey Bank A.Ş.", "deposit", "foreign", ["ICBC Turkey Bank", "ICBC Turkey"]),
    "ing": ("ING Bank A.Ş.", "deposit", "foreign", ["ING Bank", "ING"]),
    "mufg": ("MUFG Bank Turkey A.Ş.", "deposit", "foreign", ["MUFG Bank Turkey", "MUFG"]),
    "odea": ("Odea Bank A.Ş.", "deposit", "foreign", ["Odea Bank", "Odeabank"]),
    "qnb": ("QNB Bank A.Ş.", "deposit", "foreign", ["QNB Bank", "QNB Finansbank", "QNB"]),
    "rabobank": ("Rabobank A.Ş.", "deposit", "foreign", ["Rabobank"]),
    "turkland": ("Turkland Bank A.Ş.", "deposit", "foreign", ["Turkland Bank", "T-Bank"]),
    "bankmellat": ("Bank Mellat", "deposit", "foreign", ["Bank Mellat"]),
    "habib": ("Habib Bank Limited", "deposit", "foreign", ["Habib Bank"]),
    "intesa": ("Intesa Sanpaolo S.p.A.", "deposit", "foreign", ["Intesa Sanpaolo"]),
    "jpmorgan": ("JPMorgan Chase Bank N.A.", "deposit", "foreign", ["JPMorgan Chase Bank", "JPMorgan"]),
    "socgen": ("Société Générale (SA)", "deposit", "foreign", ["Société Générale", "Societe Generale"]),
    "birlesikfon": ("Birleşik Fon Bankası A.Ş.", "deposit", "sdif", ["Birleşik Fon Bankası", "Birleşik Fon"]),
    "aktifyatirim": ("Aktif Yatırım Bankası A.Ş.", "development_investment", "private", ["Aktif Yatırım Bankası", "Aktifbank"]),
    "bankpozitif": ("BankPozitif Kredi ve Kalkınma Bankası A.Ş.", "development_investment", "foreign", ["BankPozitif"]),
    "diler": ("Diler Yatırım Bankası A.Ş.", "development_investment", "private", ["Diler Yatırım Bankası"]),
    "gsd": ("GSD Yatırım Bankası A.Ş.", "development_investment", "private", ["GSD Yatırım Bankası"]),
    "illerbank": ("İller Bankası A.Ş.", "development_investment", "public", ["İller Bankası", "İlbank"]),
    "takasbank": ("İstanbul Takas ve Saklama Bankası A.Ş.", "development_investment", "private", ["Takasbank", "İstanbul Takas ve Saklama Bankası"]),
    "bofa": ("Bank of America Yatırım Bank A.Ş.", "development_investment", "foreign", ["Bank of America Yatırım Bank", "Merrill Lynch Yatırım Bank A.Ş.", "Merrill Lynch Yatırım Bank"]),
    "nurol": ("Nurol Yatırım Bankası A.Ş.", "development_investment", "private", ["Nurol Yatırım Bankası"]),
    "pasha": ("Pasha Yatırım Bankası A.Ş.", "development_investment", "foreign", ["Pasha Yatırım Bankası", "PASHA Bank"]),
    "stanchart": ("Standard Chartered Yatırım Bankası Türk A.Ş.", "development_investment", "foreign", ["Standard Chartered Yatırım Bankası"]),
    "eximbank": ("Türkiye İhracat Kredi Bankası A.Ş.", "development_investment", "public", ["Türk Eximbank", "Eximbank", "Türkiye İhracat Kredi Bankası"]),
    "tkyb": ("Türkiye Kalkınma ve Yatırım Bankası A.Ş.", "development_investment", "public", ["Türkiye Kalkınma ve Yatırım Bankası", "TKYB"]),
    "tskb": ("Türkiye Sınai Kalkınma Bankası A.Ş.", "development_investment", "private", ["TSKB", "Türkiye Sınai Kalkınma Bankası"]),
    "goldenglobal": ("Golden Global Yatırım Bankası A.Ş.", "development_investment", "private", ["Golden Global Yatırım Bankası"]),
    "dyatirim": ("D Yatırım Bankası A.Ş.", "development_investment", "private", ["D Yatırım Bankası"]),
    "terayatirim": ("Tera Yatırım Bankası A.Ş.", "development_investment", "private", ["Tera Yatırım Bankası", "Tera Yatirim Bankası A.Ş."]),
    "destekyatirim": ("Destek Yatırım Bankası A.Ş.", "development_investment", "private", ["Destek Yatırım Bankası"]),
    "qyatirim": ("Q Yatırım Bankası A.Ş.", "development_investment", "private", ["Q Yatırım Bankası", "Q Yatirim Bankası A.Ş."]),
    # TBB 2025 Eylül Excel veri seti 'Banka Seçiniz' listesinden (28.10.2026) eklenenler:
    "colendi": ("Colendi Bank A.Ş.", "deposit", "private", ["Colendi Bank A.Ş. (dijital banka)", "Colendi Bank", "Colendi"]),
    "enpara": ("Enpara Bank A.Ş.", "deposit", "private", ["Enpara Bank", "Enpara"]),
    "hedefyatirim": ("Hedef Yatırım Bankası A.Ş.", "development_investment", "private", ["Hedef Yatırım Bankası"]),
    "misyonyatirim": ("Misyon Yatırım Bankası A.Ş.", "development_investment", "private", ["Misyon Yatırım Bankası"]),
    "turkticaret": ("Türk Ticaret Bankası A.Ş.", "deposit", "private", ["Türk Ticaret Bankası"]),
    "ziraatdinamik": ("Ziraat Dinamik Banka A.Ş.", "deposit", "public", ["Ziraat Dinamik Banka A.Ş. (dijital banka)", "Ziraat Dinamik Banka", "Ziraat Dinamik"]),
    # DT20 Haziran 2026 dosyasında görülen (28.10.2026):
    "fups": ("FUPS Bank A.Ş.", "deposit", "private", ["FUPS Bank A.Ş. (dijital banka)", "FUPS Bank", "FUPS"]),
    "aytemizyatirim": ("Aytemiz Yatırım Bankası A.Ş.", "development_investment", "private", ["Aytemiz Yatırım Bankası"]),
}

# TBB'nin 2025 Eylül solo Excel veri seti sayfasındaki resmî 'Banka Seçiniz' listesi (57 banka) — tohum listesini doğrulamak için.
TBB_SELECTOR_BANKS_2025_09 = [
    "Akbank T.A.Ş.", "Aktif Yatırım Bankası A.Ş.", "Alternatifbank A.Ş.", "Anadolubank A.Ş.", "Arap Türk Bankası A.Ş.", "Bank Mellat",
    "Bank of America Yatırım Bank A.Ş.", "Bank of China Turkey A.Ş.", "BankPozitif Kredi ve Kalkınma Bankası A.Ş.", "Birleşik Fon Bankası A.Ş.",
    "Burgan Bank A.Ş.", "Citibank A.Ş.", "Colendi Bank A.Ş. (dijital banka)", "D Yatırım Bankası A.Ş.", "Denizbank A.Ş.", "Destek Yatırım Bankası A.Ş.",
    "Deutsche Bank A.Ş.", "Diler Yatırım Bankası A.Ş.", "Enpara Bank A.Ş.", "Fibabanka A.Ş.", "Golden Global Yatırım Bankası A.Ş.",
    "GSD Yatırım Bankası A.Ş.", "Habib Bank Limited", "Hedef Yatırım Bankası A.Ş.", "HSBC Bank A.Ş.", "ICBC Turkey Bank A.Ş.", "ING Bank A.Ş.",
    "Intesa Sanpaolo S.p.A.", "İller Bankası A.Ş.", "İstanbul Takas ve Saklama Bankası A.Ş.", "JPMorgan Chase Bank N.A.", "Misyon Yatırım Bankası A.Ş.",
    "MUFG Bank Turkey A.Ş.", "Nurol Yatırım Bankası A.Ş.", "Odea Bank A.Ş.", "Pasha Yatırım Bankası A.Ş.", "Q Yatırım Bankası A.Ş.", "QNB Bank A.Ş.",
    "Rabobank A.Ş.", "Société Générale (SA)", "Standard Chartered Yatırım Bankası Türk A.Ş.", "Şekerbank T.A.Ş.", "Tera Yatırım Bankası A.Ş.",
    "Turkish Bank A.Ş.", "Turkland Bank A.Ş.", "Türk Ekonomi Bankası A.Ş.", "Türk Eximbank", "Türk Ticaret Bankası A.Ş.",
    "Türkiye Cumhuriyeti Ziraat Bankası A.Ş.", "Türkiye Garanti Bankası A.Ş.", "Türkiye Halk Bankası A.Ş.", "Türkiye İş Bankası A.Ş.",
    "Türkiye Kalkınma ve Yatırım Bankası A.Ş.", "Türkiye Sınai Kalkınma Bankası A.Ş.", "Türkiye Vakıflar Bankası T.A.O.", "Yapı ve Kredi Bankası A.Ş.",
    "Ziraat Dinamik Banka A.Ş. (dijital banka)",
]

# Sektör / grup satırları — banka DEĞİL; gözlem olarak banka tablosuna yazılmaz (reporting_scope=sector katmanı)
AGGREGATE_ROW_PATTERNS = [
    r"^sektör", r"^toplam", r"^mevduat bankaları", r"^kamusal sermayeli", r"^kamu sermayeli", r"^özel sermayeli",
    r"^yabancı sermayeli", r"^yabancı bankalar", r"^tmsf", r"^tasarruf mevduatı sigorta", r"^tasarruf mevduatı sig", r"^tas mevd", r"^kalkınma ve yatırım",
    r"^türkiye'de kurulmuş", r"^türkiye de kurulmuş", r"^türkiye'de şube açan", r"^türkiye de şube açan",
]


class BankRegistry:
    def __init__(self, extra_aliases: dict[str, str] | None = None):
        self._alias: dict[str, str] = {}
        for code, (name, _t, _o, aliases) in SEED_BANKS.items():
            self._alias[normalize_name(name)] = code
            for a in aliases:
                self._alias[normalize_name(a)] = code
        for raw, code in (extra_aliases or {}).items():
            self._alias[normalize_name(raw)] = code

    @staticmethod
    def is_aggregate(raw: str) -> bool:
        n = normalize_name(raw)
        return any(re.search(p, n) for p in AGGREGATE_ROW_PATTERNS)

    def match(self, raw: str) -> tuple[str | None, float, str]:
        """→ (code | None, güven, yöntem). Güven 1.0 = tam alias; <1 = benzerlik; None = eşleşme yok."""
        n = normalize_name(raw)
        if not n:
            return None, 0.0, "empty"
        if n in self._alias:
            return self._alias[n], 1.0, "alias"
        best, score = None, 0.0
        for cand, code in self._alias.items():
            r = difflib.SequenceMatcher(None, n, cand).ratio()
            if r > score:
                best, score = code, r
        if score >= 0.92:
            return best, score, "fuzzy"
        return None, score, "none"

    def add_alias(self, raw: str, code: str):
        self._alias[normalize_name(raw)] = code
