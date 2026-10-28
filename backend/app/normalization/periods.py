"""Dönem çözümleme: 'Haziran 2026', '2026 Haziran', '30.06.2026', '2026-06', '2026Q2', 'Jun-26' → (period_start, period_end, label)."""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date

MONTHS = {
    "ocak": 1, "şubat": 2, "subat": 2, "mart": 3, "nisan": 4, "mayıs": 5, "mayis": 5, "haziran": 6, "temmuz": 7,
    "ağustos": 8, "agustos": 8, "eylül": 9, "eylul": 9, "ekim": 10, "kasım": 11, "kasim": 11, "aralık": 12, "aralik": 12,
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6, "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}


@dataclass(frozen=True)
class Period:
    start: date
    end: date
    frequency: str
    label: str


def _month_end(y: int, m: int) -> date:
    if m == 12:
        return date(y, 12, 31)
    return date(y, m + 1, 1).fromordinal(date(y, m + 1, 1).toordinal() - 1)


def quarter_period(y: int, m: int) -> Period:
    assert m in (3, 6, 9, 12)
    q = m // 3
    return Period(date(y, m - 2, 1), _month_end(y, m), "quarterly", f"{y}Q{q}")


def ytd_period(y: int, m: int) -> Period:
    """Kümülatif gelir tablosu penceresi: yıl başı → ay sonu."""
    return Period(date(y, 1, 1), _month_end(y, m), "quarterly", f"{y}YTD{m:02d}")


def parse_period(text: str, default_freq: str = "quarterly") -> Period | None:
    t = (text or "").strip().lower().replace("i̇", "i")
    m = re.search(r"(\d{4})\s*q([1-4])", t)
    if m:
        return quarter_period(int(m.group(1)), int(m.group(2)) * 3)
    m = re.search(r"(\d{1,2})[./-](\d{1,2})[./-](\d{4})", t)            # 30.06.2026
    if m:
        d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        return _from_ym(y, mo, default_freq)
    m = re.search(r"(\d{4})-(\d{2})(?:-(\d{2}))?", t)                     # 2026-06(-30)
    if m:
        return _from_ym(int(m.group(1)), int(m.group(2)), default_freq)
    for name, mo in MONTHS.items():
        if re.search(rf"\b{name}\w*\b", t):
            y = re.search(r"((?:19|20)\d{2})", t)
            if y:
                return _from_ym(int(y.group(1)), mo, default_freq)
            y2 = re.search(rf"{name}\w*[-\s']?(\d{{2}})\b", t)              # Jun-26
            if y2:
                return _from_ym(2000 + int(y2.group(1)), mo, default_freq)
    m = re.fullmatch(r"((?:19|20)\d{2})", t)
    if m:
        y = int(m.group(1))
        return Period(date(y, 1, 1), date(y, 12, 31), "annual", str(y))
    return None


def _from_ym(y: int, mo: int, freq: str) -> Period:
    if freq == "quarterly" and mo in (3, 6, 9, 12):
        return quarter_period(y, mo)
    if freq == "annual":
        return Period(date(y, 1, 1), date(y, 12, 31), "annual", str(y))
    return Period(date(y, mo, 1), _month_end(y, mo), "monthly", f"{y}-{mo:02d}")
