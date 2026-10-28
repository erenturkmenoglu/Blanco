"""TBB DT13 'Banka, Çalışan ve Şube Bilgileri' — xlsx (ve aynı tabloyu içeren docx) çıkarıcısı.

GERÇEK düzen (Haziran 2026, 'Banka Çalışan ve Şube Sayıları-Haziran 2026.xlsx', sayfa 'şube ve çalışan'; doğrulandı):
  satır 0: 'Tablo 4 Şube ve Çalışan Sayıları …'
  satır 2: '' | 'Şube Sayısı' | '' | '' | 'Çalışan Sayısı' | '' | ''
  satır 3: '' | '2025 Haziran' | '2025 Aralık' | '2026 Haziran' | '2025 Haziran' | '2025 Aralık' | '2026 Haziran'
  satır 4: 'Sektör Toplamı' | 9324 | 9158 | 9148 | 188912 | 189636 | 188406
  sonra grup başlıkları (Mevduat Bankaları, Kamu Sermayeli…, Özel…, Yabancı…, Kalkınma ve Yatırım…) ve banka satırları; '-' = veri yok.
Genel eşleyici bu sayfada satırları kaydırıp yanlış değer (Bank Mellat 3.856 şube) üretmişti → yalnızca bu çıkarıcı kullanılır.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date

import pandas as pd

from app.acquisition.parsers import to_number
from .bank_names import BankRegistry
from .periods import MONTHS, _month_end


@dataclass
class Extracted:
    observations: list[dict] = field(default_factory=list)
    unmatched_banks: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


def _period_from_label(s) -> date | None:
    """'2025 Haziran' / 'Haziran 2025' → ay sonu tarihi."""
    if not isinstance(s, str):
        return None
    t = s.strip().lower()
    m = re.search(r"(\d{4})", t)
    if not m:
        return None
    y = int(m.group(1))
    for name, mo in MONTHS.items():
        if re.search(rf"\b{name}\b", t):
            return _month_end(y, mo)
    return None


def _find_sheet(tables: dict[str, pd.DataFrame]):
    for k, df in tables.items():
        name = k.split("::")[-1].strip().lower()
        if "şube" in name and "çalışan" in name:
            return k, df
    # docx: tablo adları table1.. → başlıkta 'Şube Sayısı' ve 'Çalışan Sayısı' olan ilk tablo
    for k, df in tables.items():
        txt = " ".join(str(v) for v in df.head(6).values.ravel() if isinstance(v, str))
        if "Şube Sayısı" in txt and "Çalışan Sayısı" in txt:
            return k, df
    return None, None


def extract_dt13(tables: dict[str, pd.DataFrame], registry: BankRegistry, scope: str = "solo", source_code: str = "TBB") -> Extracted:
    ex = Extracted()
    name, df = _find_sheet(tables)
    if df is None:
        ex.notes.append("DT13: 'şube ve çalışan' tablosu bulunamadı")
        return ex
    hdr = None
    for r in range(min(8, df.shape[0])):
        cells = [str(v).strip() if isinstance(v, str) else "" for v in df.iloc[r].tolist()]
        if any(c.startswith("Şube Sayısı") for c in cells) and any(c.startswith("Çalışan Sayısı") for c in cells):
            hdr = r
            break
    if hdr is None or hdr + 1 >= df.shape[0]:
        ex.notes.append("DT13: 'Şube Sayısı / Çalışan Sayısı' başlığı bulunamadı")
        return ex
    # metrik bloğu: başlık hücresi dolu olan sütundan sonraki boş hücreler aynı bloğa aittir (birleştirilmiş hücre)
    cols: dict[int, tuple[str, date]] = {}
    current = None
    for c in range(1, df.shape[1]):
        h = df.iat[hdr, c]
        if isinstance(h, str) and h.strip():
            current = "branch_count" if h.strip().startswith("Şube") else "employee_count" if h.strip().startswith("Çalışan") else None
        pe = _period_from_label(df.iat[hdr + 1, c])
        if current and pe:
            cols[c] = (current, pe)
    if not cols:
        ex.notes.append("DT13: dönem sütunları çözümlenemedi")
        return ex
    for r in range(hdr + 2, df.shape[0]):
        raw = df.iat[r, 0]
        if not isinstance(raw, str) or not raw.strip() or raw.strip().startswith("*"):
            continue
        raw = raw.strip()
        if registry.is_aggregate(raw):
            continue
        code, conf, _how = registry.match(raw.rstrip("*").strip())
        if conf < 0.92:
            ex.unmatched_banks.append(raw)
            continue
        for c, (metric, pe) in cols.items():
            v = to_number(df.iat[r, c])
            ex.observations.append(dict(bank_raw=raw, bank_code=code, bank_match="alias", metric_code=metric, period_end=pe, period_start=pe,
                                        value=v, value_raw=v, unit="count", scale=1.0, scale_detected=True, currency=None, reporting_scope=scope,
                                        frequency="quarterly", source_code=source_code, cumulative_ytd=False, sheet=name.split("::")[-1], row=r, col=c,
                                        label_raw=f"{'Şube Sayısı' if metric == 'branch_count' else 'Çalışan Sayısı'} / {df.iat[hdr + 1, c]}", kind="financial"))
    return ex
