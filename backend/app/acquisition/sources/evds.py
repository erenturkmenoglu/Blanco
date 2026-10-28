"""TCMB EVDS (evds3) adaptörü — makro katman.

- Anahtar yalnızca EVDS_API_KEY ortam değişkeninden okunur; loglanmaz.
- Seri kodları TAHMİN EDİLMEZ: `verify_series()` katalog uç noktasından kodu doğrular; doğrulanmamış kod kullanılmaz.
- Uç noktalar (TCMB EVDS web servisi dokümantasyonu):
    https://evds3.tcmb.gov.tr/service/evds/categories/type=json
    https://evds3.tcmb.gov.tr/service/evds/datagroups/mode=2&code=<kategori>&type=json
    https://evds3.tcmb.gov.tr/service/evds/serieList/type=json&code=<veri_grubu>
    https://evds3.tcmb.gov.tr/service/evds/series=<SERI>&startDate=dd-mm-yyyy&endDate=dd-mm-yyyy&type=json
  Erişim yöntemi/adresler çalışma anında doğrulanır (hata → ERROR + neden).
"""
from __future__ import annotations

import logging
from datetime import date

from app.config import settings

from .base import DatasetSpec, DiscoveredFile, SourceAdapter

log = logging.getLogger("bilanco.evds")
BASE = "https://evds3.tcmb.gov.tr/service/evds"


class EVDSAdapter(SourceAdapter):
    code = "EVDS"

    def _headers(self) -> dict:
        key = settings.evds_api_key
        if not key:
            raise RuntimeError("EVDS_API_KEY tanımlı değil (ortam değişkeni)")
        return {"key": key, "User-Agent": settings.user_agent}

    def datasets(self) -> list[DatasetSpec]:
        return [DatasetSpec("evds_macro", "EVDS makro göstergeler (kur, politika faizi, TÜFE, sektör faizleri)", "EVDS",
                            "daily", "sector", False, BASE, f"{BASE}/series=<kod>&startDate=..&endDate=..&type=json",
                            "json", 0, "UNVERIFIED", "Seri kodları henüz API üzerinden doğrulanmadı (anahtar gerekli).")]

    def discover(self, dataset_code: str, year: int, month: int) -> list[DiscoveredFile]:
        return []   # EVDS dosya değil API; fetch_series kullanılır

    # ------------------------------------------------------------ API
    def _get_json(self, url: str) -> dict | list:
        import httpx
        with httpx.Client(timeout=settings.http_timeout, headers=self._headers()) as c:
            r = c.get(url)
            r.raise_for_status()
            return r.json()

    def list_series(self, datagroup_code: str) -> list[dict]:
        return self._get_json(f"{BASE}/serieList/type=json&code={datagroup_code}")

    def verify_series(self, series_code: str, datagroup_code: str) -> dict | None:
        """Kod katalogda varsa seri meta verisini döndürür; yoksa None (kullanılmaz)."""
        for s in self.list_series(datagroup_code):
            if s.get("SERIE_CODE") == series_code:
                return s
        return None

    def fetch_series(self, series_code: str, start: date, end: date, aggregation: str | None = None) -> list[dict]:
        url = f"{BASE}/series={series_code}&startDate={start:%d-%m-%Y}&endDate={end:%d-%m-%Y}&type=json"
        if aggregation:
            url += f"&aggregationTypes={aggregation}"
        payload = self._get_json(url)
        items = payload.get("items", []) if isinstance(payload, dict) else []
        key = series_code.replace(".", "_")
        out = []
        for it in items:
            val = it.get(key)
            if val in (None, ""):
                continue
            out.append({"date": it.get("Tarih"), "value": float(str(val).replace(",", ".")), "series_code": series_code})
        return out
