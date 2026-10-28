"""Veritabanı modelleri (PostgreSQL hedef; SQLite uyumlu).

İlkeler:
- Ham gözlem (value_raw, source_scale) ve normalize değer (value, unit) ayrı saklanır.
- Her gözlem kaynağa (source_document) ve alana (source_field/sheet/row/col) geri izlenebilir.
- Aynı dönem/metrik için birden fazla kaynak veya revizyon desteklenir (revision_id, uniq kısıtı revizyon içerir).
- verification_status: VERIFIED | DERIVED | UNVERIFIED | UNAVAILABLE | ERROR — birbirinin yerine kullanılmaz.
"""
from __future__ import annotations

import enum
from datetime import date, datetime

from sqlalchemy import (JSON, Boolean, Date, DateTime, Enum, Float, ForeignKey, Index, Integer, String, Text,
                        UniqueConstraint, func)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class VerificationStatus(str, enum.Enum):
    VERIFIED = "VERIFIED"
    DERIVED = "DERIVED"
    UNVERIFIED = "UNVERIFIED"
    UNAVAILABLE = "UNAVAILABLE"
    ERROR = "ERROR"


class Frequency(str, enum.Enum):
    daily = "daily"
    weekly = "weekly"
    monthly = "monthly"
    quarterly = "quarterly"
    annual = "annual"


class ReportingScope(str, enum.Enum):
    solo = "solo"
    consolidated = "consolidated"
    sector = "sector"       # sektör / grup toplamı — banka verisi yerine KULLANILMAZ
    na = "na"


class JobStatus(str, enum.Enum):
    running = "running"
    success = "success"
    partial = "partial"
    failed = "failed"
    skipped = "skipped"


def _ts():
    return mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


# ---------------------------------------------------------------- kuruluşlar / sektörler
class Sector(Base):
    __tablename__ = "sectors"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True)      # banks, retail, energy ...
    name_tr: Mapped[str] = mapped_column(String(128))
    module_enabled: Mapped[bool] = mapped_column(Boolean, default=False)


class Institution(Base):
    __tablename__ = "institutions"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(64), unique=True)      # standart kısa kod: ziraat, isbank ...
    name: Mapped[str] = mapped_column(String(256))                  # resmî ad
    short_name: Mapped[str | None] = mapped_column(String(64))
    official_code: Mapped[str | None] = mapped_column(String(32))   # bank_code (BDDK/TBB kodu, mevcutsa)
    institution_type: Mapped[str | None] = mapped_column(String(32))  # bank_type: deposit | participation | development_investment
    ownership_type: Mapped[str | None] = mapped_column(String(32))    # public | private | foreign | sdif
    country: Mapped[str] = mapped_column(String(2), default="TR")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = _ts()
    aliases: Mapped[list["InstitutionAlias"]] = relationship(back_populates="institution", cascade="all, delete-orphan")


class InstitutionAlias(Base):
    """Kaynaklarda görülen ham banka adları → standart kuruluş eşlemesi."""
    __tablename__ = "institution_aliases"
    id: Mapped[int] = mapped_column(primary_key=True)
    institution_id: Mapped[int] = mapped_column(ForeignKey("institutions.id", ondelete="CASCADE"))
    alias_normalized: Mapped[str] = mapped_column(String(256), index=True)
    alias_raw: Mapped[str] = mapped_column(String(256))
    source_code: Mapped[str | None] = mapped_column(String(32))
    institution: Mapped[Institution] = relationship(back_populates="aliases")
    __table_args__ = (UniqueConstraint("alias_normalized", "source_code", name="uq_alias_source"),)


class InstitutionSectorMembership(Base):
    __tablename__ = "institution_sector_memberships"
    id: Mapped[int] = mapped_column(primary_key=True)
    institution_id: Mapped[int] = mapped_column(ForeignKey("institutions.id", ondelete="CASCADE"))
    sector_id: Mapped[int] = mapped_column(ForeignKey("sectors.id", ondelete="CASCADE"))
    valid_from: Mapped[date | None] = mapped_column(Date)
    valid_to: Mapped[date | None] = mapped_column(Date)
    __table_args__ = (UniqueConstraint("institution_id", "sector_id", "valid_from", name="uq_membership"),)


# ---------------------------------------------------------------- kaynaklar / veri setleri
class DataSource(Base):
    __tablename__ = "data_sources"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True)      # TBB, BDDK, TCMB, EVDS
    name: Mapped[str] = mapped_column(String(256))
    base_url: Mapped[str] = mapped_column(String(512))
    access_method: Mapped[str] = mapped_column(String(64), default="http_get")  # http_get | html_form | api_key | browser
    robots_note: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)


class Dataset(Base):
    __tablename__ = "datasets"
    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("data_sources.id"))
    code: Mapped[str] = mapped_column(String(64), unique=True)      # tbb_fs_solo_excel, tbb_dt20 ...
    name: Mapped[str] = mapped_column(String(256))
    frequency: Mapped[Frequency] = mapped_column(Enum(Frequency, native_enum=False, length=16))
    reporting_scope: Mapped[ReportingScope] = mapped_column(Enum(ReportingScope, native_enum=False, length=16), default=ReportingScope.na)
    per_institution: Mapped[bool] = mapped_column(Boolean, default=False)   # banka bazında mı?
    discovery_url: Mapped[str | None] = mapped_column(String(1024))         # keşif (liste) sayfası / API
    url_pattern: Mapped[str | None] = mapped_column(String(1024))           # yeniden üretilebilir kalıp
    expected_formats: Mapped[str | None] = mapped_column(String(64))        # xls,xlsx,pdf,csv,html,json
    publication_lag_days: Mapped[int | None] = mapped_column(Integer)       # yayın takviminden
    status: Mapped[VerificationStatus] = mapped_column(Enum(VerificationStatus, native_enum=False, length=16), default=VerificationStatus.UNVERIFIED)
    status_note: Mapped[str | None] = mapped_column(Text)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    fields: Mapped[list["DatasetField"]] = relationship(back_populates="dataset", cascade="all, delete-orphan")


class DatasetField(Base):
    """Kaynak alan → veri sözlüğü metrik eşlemesi ve doğrulama durumu (doğrulama tablosunun kalıcı hâli)."""
    __tablename__ = "dataset_fields"
    id: Mapped[int] = mapped_column(primary_key=True)
    dataset_id: Mapped[int] = mapped_column(ForeignKey("datasets.id", ondelete="CASCADE"))
    metric_code: Mapped[str] = mapped_column(String(64), index=True)
    source_field: Mapped[str | None] = mapped_column(String(512))   # gerçek sütun/satır başlığı
    source_sheet: Mapped[str | None] = mapped_column(String(128))
    per_institution: Mapped[bool] = mapped_column(Boolean, default=False)
    verified_period: Mapped[str | None] = mapped_column(String(16))  # "2023-06"
    status: Mapped[VerificationStatus] = mapped_column(Enum(VerificationStatus, native_enum=False, length=16), default=VerificationStatus.UNVERIFIED)
    note: Mapped[str | None] = mapped_column(Text)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    dataset: Mapped[Dataset] = relationship(back_populates="fields")
    __table_args__ = (UniqueConstraint("dataset_id", "metric_code", "source_field", "verified_period", name="uq_dataset_field"),)


class FinancialPeriod(Base):
    __tablename__ = "financial_periods"
    id: Mapped[int] = mapped_column(primary_key=True)
    period_start: Mapped[date] = mapped_column(Date)
    period_end: Mapped[date] = mapped_column(Date, index=True)
    frequency: Mapped[Frequency] = mapped_column(Enum(Frequency, native_enum=False, length=16))
    label: Mapped[str] = mapped_column(String(16))                  # 2026Q2, 2026-06, 2026
    __table_args__ = (UniqueConstraint("period_end", "frequency", name="uq_period"),)


class SourceDocument(Base):
    """İndirilen her dosya: değiştirilmeden saklanır, sha256 ile bütünlük/revizyon takibi."""
    __tablename__ = "source_documents"
    id: Mapped[int] = mapped_column(primary_key=True)
    dataset_id: Mapped[int] = mapped_column(ForeignKey("datasets.id"))
    period_id: Mapped[int | None] = mapped_column(ForeignKey("financial_periods.id"))
    url: Mapped[str] = mapped_column(String(2048))
    file_name: Mapped[str | None] = mapped_column(String(512))
    content_type_declared: Mapped[str | None] = mapped_column(String(128))
    format_detected: Mapped[str | None] = mapped_column(String(16))   # içerik imzasından: xls, xlsx, zip, pdf, html, csv, json, xml
    sha256: Mapped[str | None] = mapped_column(String(64), index=True)
    size_bytes: Mapped[int | None] = mapped_column(Integer)
    local_path: Mapped[str | None] = mapped_column(String(1024))
    publication_date: Mapped[date | None] = mapped_column(Date)
    retrieved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(16), default="pending")   # pending | downloaded | parsed | failed
    error: Mapped[str | None] = mapped_column(Text)
    sheets: Mapped[dict | None] = mapped_column(JSON)               # {sheet: {rows: n, cols: n, header: [...]}}
    revisions: Mapped[list["SourceRevision"]] = relationship(back_populates="document", cascade="all, delete-orphan")


class SourceRevision(Base):
    __tablename__ = "source_revisions"
    id: Mapped[int] = mapped_column(primary_key=True)
    source_document_id: Mapped[int] = mapped_column(ForeignKey("source_documents.id", ondelete="CASCADE"))
    revision_no: Mapped[int] = mapped_column(Integer, default=1)
    sha256: Mapped[str | None] = mapped_column(String(64))
    detected_at: Mapped[datetime] = _ts()
    note: Mapped[str | None] = mapped_column(Text)
    document: Mapped[SourceDocument] = relationship(back_populates="revisions")


class DataIngestionJob(Base):
    __tablename__ = "data_ingestion_jobs"
    id: Mapped[int] = mapped_column(primary_key=True)
    dataset_id: Mapped[int | None] = mapped_column(ForeignKey("datasets.id"))
    period_label: Mapped[str | None] = mapped_column(String(16))
    started_at: Mapped[datetime] = _ts()
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[JobStatus] = mapped_column(Enum(JobStatus, native_enum=False, length=16), default=JobStatus.running)
    trigger: Mapped[str] = mapped_column(String(32), default="manual")   # manual | scheduler
    documents_count: Mapped[int] = mapped_column(Integer, default=0)
    observations_count: Mapped[int] = mapped_column(Integer, default=0)
    message: Mapped[str | None] = mapped_column(Text)
    log: Mapped[list | None] = mapped_column(JSON)                  # adım adım kayıt (url, yöntem, sonuç, neden)


# ---------------------------------------------------------------- gözlemler
class _ObservationMixin:
    id: Mapped[int] = mapped_column(primary_key=True)
    period_start: Mapped[date | None] = mapped_column(Date)
    period_end: Mapped[date] = mapped_column(Date, index=True)
    observation_date: Mapped[date | None] = mapped_column(Date)
    value_raw: Mapped[float | None] = mapped_column(Float)          # kaynaktaki sayı, olduğu gibi
    source_scale: Mapped[float] = mapped_column(Float, default=1.0)  # 1 = TL, 1e3 = Bin TL, 1e6 = Milyon TL
    value: Mapped[float | None] = mapped_column(Float)              # normalize (TL veya %)
    unit: Mapped[str] = mapped_column(String(16))                   # TRY | pct | count | ratio
    currency: Mapped[str | None] = mapped_column(String(8))         # TRY | USD | EUR | FX | ALL
    frequency: Mapped[Frequency] = mapped_column(Enum(Frequency, native_enum=False, length=16))
    reporting_scope: Mapped[ReportingScope] = mapped_column(Enum(ReportingScope, native_enum=False, length=16))
    source_field: Mapped[str | None] = mapped_column(String(512))
    source_sheet: Mapped[str | None] = mapped_column(String(128))
    source_row: Mapped[int | None] = mapped_column(Integer)
    source_col: Mapped[int | None] = mapped_column(Integer)
    publication_date: Mapped[date | None] = mapped_column(Date)
    retrieved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    verification_status: Mapped[VerificationStatus] = mapped_column(Enum(VerificationStatus, native_enum=False, length=16), default=VerificationStatus.UNVERIFIED)
    revision_no: Mapped[int] = mapped_column(Integer, default=1)
    quality_flags: Mapped[list | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = _ts()


class FinancialObservation(_ObservationMixin, Base):
    __tablename__ = "financial_observations"
    institution_id: Mapped[int] = mapped_column(ForeignKey("institutions.id"), index=True)
    metric_code: Mapped[str] = mapped_column(String(64), index=True)
    period_id: Mapped[int | None] = mapped_column(ForeignKey("financial_periods.id"))
    cumulative_ytd: Mapped[bool] = mapped_column(Boolean, default=False)   # gelir tablosu: yıl başından kümülatif
    source_id: Mapped[int] = mapped_column(ForeignKey("data_sources.id"))
    source_document_id: Mapped[int | None] = mapped_column(ForeignKey("source_documents.id"))
    __table_args__ = (
        UniqueConstraint("institution_id", "metric_code", "period_end", "reporting_scope", "currency", "source_id", "revision_no",
                         name="uq_fin_obs"),
        Index("ix_fin_obs_lookup", "metric_code", "period_end", "reporting_scope"),
    )


class InterestRateObservation(_ObservationMixin, Base):
    __tablename__ = "interest_rate_observations"
    institution_id: Mapped[int] = mapped_column(ForeignKey("institutions.id"), index=True)
    instrument: Mapped[str] = mapped_column(String(16))             # loan | deposit
    rate_definition: Mapped[str] = mapped_column(String(48))        # stock_avg_applied_rate | new_business_flow_rate | accounting_yield | accounting_cost
    metric_code: Mapped[str] = mapped_column(String(64), index=True)  # loan_interest_tl ...
    source_id: Mapped[int] = mapped_column(ForeignKey("data_sources.id"))
    source_document_id: Mapped[int | None] = mapped_column(ForeignKey("source_documents.id"))
    __table_args__ = (UniqueConstraint("institution_id", "metric_code", "period_end", "reporting_scope", "rate_definition", "source_id", "revision_no", name="uq_rate_obs"),)


class MaturityObservation(_ObservationMixin, Base):
    __tablename__ = "maturity_observations"
    institution_id: Mapped[int] = mapped_column(ForeignKey("institutions.id"), index=True)
    item: Mapped[str] = mapped_column(String(32))                   # total_assets | total_liabilities | loans | deposits | liquidity_gap
    basis: Mapped[str] = mapped_column(String(16))                  # remaining | original | behavioural
    bucket: Mapped[str] = mapped_column(String(16))                 # demand | 0_1m | 1_3m | 3_6m | 6_12m | 3_12m | 1_5y | over_5y | unallocated | total
    bucket_label_raw: Mapped[str | None] = mapped_column(String(64))  # kaynağın kendi etiketi (yapay bölme yok)
    source_id: Mapped[int] = mapped_column(ForeignKey("data_sources.id"))
    source_document_id: Mapped[int | None] = mapped_column(ForeignKey("source_documents.id"))
    __table_args__ = (UniqueConstraint("institution_id", "item", "basis", "bucket", "currency", "period_end", "reporting_scope", "source_id", "revision_no", name="uq_mat_obs"),)


class MacroObservation(Base):
    __tablename__ = "macro_observations"
    id: Mapped[int] = mapped_column(primary_key=True)
    metric_code: Mapped[str] = mapped_column(String(64), index=True)
    series_code: Mapped[str | None] = mapped_column(String(64))      # gerçek EVDS seri kodu (doğrulanmış)
    observation_date: Mapped[date] = mapped_column(Date, index=True)
    value: Mapped[float | None] = mapped_column(Float)
    unit: Mapped[str] = mapped_column(String(16))
    frequency: Mapped[Frequency] = mapped_column(Enum(Frequency, native_enum=False, length=16))
    source_id: Mapped[int] = mapped_column(ForeignKey("data_sources.id"))
    retrieved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    verification_status: Mapped[VerificationStatus] = mapped_column(Enum(VerificationStatus, native_enum=False, length=16), default=VerificationStatus.UNVERIFIED)
    __table_args__ = (UniqueConstraint("metric_code", "series_code", "observation_date", name="uq_macro_obs"),)


class DerivedMetric(Base):
    __tablename__ = "derived_metrics"
    id: Mapped[int] = mapped_column(primary_key=True)
    institution_id: Mapped[int] = mapped_column(ForeignKey("institutions.id"), index=True)
    metric_code: Mapped[str] = mapped_column(String(64), index=True)
    period_end: Mapped[date] = mapped_column(Date, index=True)
    reporting_scope: Mapped[ReportingScope] = mapped_column(Enum(ReportingScope, native_enum=False, length=16))
    value: Mapped[float | None] = mapped_column(Float)
    unit: Mapped[str] = mapped_column(String(16))
    method: Mapped[str] = mapped_column(String(256))                 # formül + yıllıklandırma yöntemi
    inputs: Mapped[dict | None] = mapped_column(JSON)               # {metric_code: observation_id,...}
    limitations: Mapped[str | None] = mapped_column(Text)            # tanım uyumsuzluğu vb.
    verification_status: Mapped[VerificationStatus] = mapped_column(Enum(VerificationStatus, native_enum=False, length=16), default=VerificationStatus.DERIVED)
    computed_at: Mapped[datetime] = _ts()
    __table_args__ = (UniqueConstraint("institution_id", "metric_code", "period_end", "reporting_scope", name="uq_derived"),)


class DataQualityCheck(Base):
    __tablename__ = "data_quality_checks"
    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int | None] = mapped_column(ForeignKey("data_ingestion_jobs.id"))
    check_code: Mapped[str] = mapped_column(String(48), index=True)   # DQ01_bank_name ... DQ14_file_integrity
    severity: Mapped[str] = mapped_column(String(8), default="error")  # error | warn | info
    passed: Mapped[bool] = mapped_column(Boolean)
    institution_id: Mapped[int | None] = mapped_column(ForeignKey("institutions.id"))
    metric_code: Mapped[str | None] = mapped_column(String(64))
    period_end: Mapped[date | None] = mapped_column(Date)
    message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = _ts()
