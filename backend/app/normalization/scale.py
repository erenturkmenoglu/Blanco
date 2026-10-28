"""DQ01 — Ölçek (Bin TL / Milyon TL / TL) tespiti. Ölçek asla varsayılmaz; kaynak sayfanın başlığından okunur.

Gerçek örnekler (doğrulandı):
  TBB banka çalışma kitabı Haziran 2026 'varlıklar' sayfası, satır 3: 'MİLYON TÜRK LİRASI'
  TBB banka çalışma kitabı Mart 2026    'varlıklar' sayfası, satır 3: 'BİN TÜRK LİRASI'      ← aynı veri seti, farklı dönemde farklı ölçek!
  TBB DT20 sayfaları: 'Varlıklar, Milyon TL', '(Milyon TL)', 'Mevduatın Vade Yapısına İlişkin Bilgiler, Milyon TL'
"""
from __future__ import annotations

import re

import pandas as pd

_TR = str.maketrans({"İ": "i", "I": "ı", "Ş": "ş", "Ğ": "ğ", "Ü": "ü", "Ö": "ö", "Ç": "ç"})

SCALES = [
    (re.compile(r"\bmilyar\b"), 1e9, "Milyar TL"),
    (re.compile(r"\bmilyon\b"), 1e6, "Milyon TL"),
    (re.compile(r"\bbin\s*(tl|türk\s*liras)"), 1e3, "Bin TL"),
    (re.compile(r"\(\s*bin\s*\)"), 1e3, "Bin TL"),
]


def _fold(s: str) -> str:
    return re.sub(r"\s+", " ", s.translate(_TR).lower()).strip()


def detect_scale_in_text(text: str) -> tuple[float, str] | None:
    t = _fold(text)
    if not re.search(r"\btl\b|türk liras|lira", t):
        # 'Milyon' tek başına (ör. 'Milyon Adet') ölçek sayılmaz; TL/lira bağlamı şart
        return None
    for rx, scale, label in SCALES:
        if rx.search(t):
            return scale, label
    if re.search(r"\b(tl|türk liras[ıi])\b", t) and not re.search(r"bin|milyon|milyar", t):
        return 1.0, "TL"
    return None


def detect_scale(df: pd.DataFrame, rows: int = 8, cols: int | None = None) -> tuple[float, str] | None:
    """Sayfanın ilk `rows` satırındaki metin hücrelerinden ölçeği bulur. Bulunamazsa None (çağıran UNVERIFIED işaretler)."""
    nr = min(rows, df.shape[0])
    nc = df.shape[1] if cols is None else min(cols, df.shape[1])
    for r in range(nr):
        for c in range(nc):
            v = df.iat[r, c]
            if isinstance(v, str) and v.strip():
                hit = detect_scale_in_text(v)
                if hit:
                    return hit
    return None
