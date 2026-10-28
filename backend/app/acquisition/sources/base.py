"""Kaynak adaptörü arayüzü. Her kaynak (TBB, BDDK, EVDS) aynı sözleşmeyi uygular:
discover → list periods → find real download URL → fetch → parse → normalize (ayrı katman)."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date

from ..downloader import Downloader, DownloadResult


@dataclass
class DatasetSpec:
    code: str
    name: str
    source_code: str
    frequency: str                      # daily|weekly|monthly|quarterly|annual
    reporting_scope: str                # solo|consolidated|sector|na
    per_institution: bool
    discovery_url: str | None = None
    url_pattern: str | None = None
    expected_formats: str | None = None
    publication_lag_days: int | None = None
    status: str = "UNVERIFIED"
    status_note: str | None = None
    extra: dict = field(default_factory=dict)


@dataclass
class DiscoveredFile:
    dataset_code: str
    period_end: date | None
    url: str
    title: str | None = None
    file_name: str | None = None
    format_hint: str | None = None
    report_page: str | None = None
    bank_raw: str | None = None          # banka bazlı tek dosya (Excel ortak veri seti) ise kaynak sayfadaki banka adı
    strategy: str | None = None          # attachment | option_url | form_get | js_pattern | known


class SourceAdapter(ABC):
    code: str = "BASE"

    def __init__(self, downloader: Downloader | None = None):
        self.downloader = downloader or Downloader()

    @abstractmethod
    def datasets(self) -> list[DatasetSpec]: ...

    @abstractmethod
    def discover(self, dataset_code: str, year: int, month: int) -> list[DiscoveredFile]:
        """Verilen dönem için gerçek indirme bağlantılarını bulur (bulamazsa boş liste + nedeni loga)."""

    def fetch(self, f: DiscoveredFile, expected: str | None = None) -> DownloadResult:
        return self.downloader.fetch(f.url, dataset_code=f.dataset_code, expected=expected or f.format_hint)
