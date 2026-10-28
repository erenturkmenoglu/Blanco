"""BDDK adaptörü.

Keşif bulgusu (28.10.2026, https://www.bddk.org.tr/BultenAylik/tr/Home/Aciklama okundu):
- Aylık/haftalık/günlük bültenler banka BAZINDA DEĞİL; veriler hangi bankaya ait olduğu anlaşılmayacak şekilde
  sektör ve grup toplamı olarak yayımlanır (BDDK'nın açık ilkesi). Yalnızca Excel dışa aktarımı vardır (JS arayüzü).
- "TBS Temel Göstergeleri" üç aylık dosyaları statik GET ile indirilebilir: https://www.bddk.org.tr/Veri/EkGetir/8?ekId=<id>
  (Haziran 2026 → ekId=676, Mart 2026 → 675, Aralık 2025 → 674 ... Haziran 2022 → 659). Sahiplik/fonksiyon grubu düzeyindedir.
Bu nedenle BDDK verisi yalnızca "sektör ortalaması / grup karşılaştırma katmanı" olarak saklanır (reporting_scope=sector)
ve ASLA tekil banka verisi yerine kullanılmaz (proje ilkesi 9).
"""
from __future__ import annotations

from datetime import date

from .base import DatasetSpec, DiscoveredFile, SourceAdapter

BASE = "https://www.bddk.org.tr"
TBS_EKID: dict[str, int] = {   # Veri/Detay/162 sayfasından okunan gerçek ekId değerleri
    "2026-06-30": 676, "2026-03-31": 675, "2025-12-31": 674, "2025-09-30": 673, "2025-06-30": 672, "2025-03-31": 671,
    "2024-12-31": 670, "2024-09-30": 669, "2024-06-30": 668, "2024-03-31": 667, "2023-12-31": 666, "2023-09-30": 664,
    "2023-06-30": 663, "2023-03-31": 662, "2022-12-31": 661, "2022-09-30": 660, "2022-06-30": 659,
}


class BDDKAdapter(SourceAdapter):
    code = "BDDK"

    def datasets(self) -> list[DatasetSpec]:
        return [
            DatasetSpec("bddk_tbs_temel_gostergeler", "Türk Bankacılık Sektörü Temel Göstergeleri (üç aylık)", "BDDK", "quarterly",
                        "sector", False, f"{BASE}/Veri/Detay/162", f"{BASE}/Veri/EkGetir/8?ekId={{ekId}}", "pdf,xlsx", 60,
                        "UNVERIFIED", "Sayfa ve ekId listesi doğrulandı (Haziran 2026 = 676); dosya biçimi/içeriği açılmadı. Grup düzeyi."),
            DatasetSpec("bddk_monthly_bulletin", "Aylık Bankacılık Sektörü Verileri (Temel Gösterim)", "BDDK", "monthly", "sector",
                        False, f"{BASE}/BultenAylik/", None, "xlsx", 35, "UNVERIFIED",
                        "Banka bazında değil (BDDK ilkesi). Excel dışa aktarımı JS arayüzünden; otomasyon için tarayıcı gerekir."),
            DatasetSpec("bddk_weekly_bulletin", "Haftalık Bülten", "BDDK", "weekly", "sector", False, f"{BASE}/BultenHaftalik/",
                        None, "xlsx", 7, "UNVERIFIED", "Sektör/grup düzeyi; JS arayüzü."),
        ]

    def discover(self, dataset_code: str, year: int, month: int) -> list[DiscoveredFile]:
        if dataset_code == "bddk_tbs_temel_gostergeler":
            last = {3: 31, 6: 30, 9: 30, 12: 31}.get(month)
            if not last:
                return []
            pe = date(year, month, last)
            ek = TBS_EKID.get(pe.isoformat())
            if ek is None:
                return []
            return [DiscoveredFile(dataset_code, pe, f"{BASE}/Veri/EkGetir/8?ekId={ek}", f"TBS Temel Göstergeleri {pe}", None, None)]
        return []   # bültenler: tarayıcı otomasyonu gerektirir; ilk sürümde kapsam dışı (loglanır)
