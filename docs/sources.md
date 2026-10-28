# Kaynak keşfi — kanıt ve URL kalıpları (28.10.2026)

Okunan resmî sayfa/dosyalar (web okuyucu ile; sandbox'tan doğrudan indirme mümkün olmadı):

| Sayfa / dosya | Ne öğrenildi |
|---|---|
| https://www.tbb.org.tr/istatistiki-raporlar/11237 (Seçilmiş İstatistikler) | 16 bölüm; *Aktif ve Pasiflerin Kalan Vadelerine Göre Gösterimi* 2002–2026 (Mart/Haziran); *Aktif Büyüklüklerine Göre Banka Sıralaması* 1995–2026; *Banka, Çalışan ve Şube Bilgileri* 1986–2026; *Seçilmiş Rasyolar* yıllık 1996–2025 |
| https://www.tbb.org.tr/istatistiki-raporlar/11232 (Kamuya Açıklanan Finansal Tablolar) | 4 bölüm: Finansal Tablolar Konsolide / Konsolide Olmayan, her biri **Excel ortak veri seti** sürümüyle; yıllar 2002–2026, aylar Mart/Haziran(/Eylül/Aralık) |
| https://www.tbb.org.tr/en/istatistiki-raporlar/11372 (Reports and Analysis based on Financial Tables) | Quarterly Statistics by Banks (All Periods / Last vs Previous); Selected Tables by Banks – Consolidated / Non-consolidated: 2005–2026; Selected Tables by Groups: 2002–2026 |
| https://www.tbb.org.tr/istatistiki-raporlar/2026-haziran-aktif-buyukluklerine-gore-banka-siralamasi | Ek: `Aktif Büyüklüğüne Göre Banka Sıralaması.xls` → `/download/node/54929/field_raporlar_ekler/310010`; liste kalıbı `/istatistiki-raporlar-liste/11254?rapor_donemi=11411&ay=6` (2026 → 11411) |
| https://www.tbb.org.tr/istatistiki-raporlar/2024-eylul-finansal-tablolar-konsolide-olmayan-solo-banka-excel-formatinda | Liste kalıbı `/istatistiki-raporlar-liste/11241?rapor_donemi=11279&ay=9` (2024 → 11279); ay seçenekleri Mart/Haziran/Eylül/Aralık; Excel eki sayfa metninde görünmedi (sunucu hatası / dinamik) |
| https://www.tbb.org.tr/download/node/54910/field_raporlar_ekler/309903 (DT13 Haziran 2026) | Banka bazında Şube ve Çalışan Sayısı (Tablo 1, 4) — **okundu** |
| https://www.tbb.org.tr/sites/default/files/raporlar/51298/ekler/Banka_Bazinda_Secilmis_Tablolar-Haziran_2023_0.pdf (DT20) | Faiz tablosu (TL/USD/EURO × kredi/mevduat; dipnot tanımı) ve kalan vade tablosu (toplam aktif/pasif) — **okundu**, örnek değerler kaydedildi |
| https://www.tbb.org.tr/download/node/51088/field_raporlar_ekler/276390 (DT21 Mart 2021), .../50926/.../274879 (DT21 Aralık 2019), .../51208/.../278035 (DT21 Haziran 2022) | Aynı iki tablo konsolide sürümde de var; yapı sabit |
| https://www.tbb.org.tr/sites/default/files/docs/tbb_istatistikleri_yayinlama_takvimi.pdf | Yayın gecikmeleri: solo seçilmiş tablolar / finansal tablolar / kalan vade / sıralama: Mar-Haz-Eyl +45 gün, Aralık Nisan sonu; konsolide +75 gün; DT13 +15 gün; Seçilmiş Rasyolar Temmuz 1. hafta |
| https://www.tbb.org.tr/sites/default/files/docs/bbtsyardim.pdf (Veri Sorgulama Sistemi kılavuzu) | Mali Tablolar + Dipnotlar (17 Sayılı Tebliğ, solo/konsolide), banka tek tek, dönem 1988→, birim TL/Bin/Milyon/Milyar; çıktı HTML tablo |
| https://verisistemi.tbb.org.tr/ | robots.txt → otomatik erişim yasak (okuyucu `robots_disallowed`) |
| https://www.bddk.org.tr/BultenAylik/tr/Home/Aciklama | Banka bazında değil (toplulaştırılmış, tasarım gereği); Excel dışa aktarımı; aylık |
| https://www.bddk.org.tr/Veri/Detay/162 | TBS Temel Göstergeleri üç aylık; `Veri/EkGetir/8?ekId=` 659 (2022-06) … 676 (2026-06); grup düzeyi |

Başarısız (sunucu hatası, tekrar denenecek): `/istatistiki-raporlar/11236`, `/istatistiki-raporlar/2025-haziran-finansal-tablolar-...`,
`/istatistiki-raporlar/2025-eylul-finansal-tablolar-...`, `/istatistiki-raporlar-liste/11241?...`, `/download/node/54929/.../310010` (xls),
`/yakinda-yayinlanacak-raporlar`, `/istatistiki-raporlar/2024-eylul-banka-bilgileri-secilmis-tablolar-konsolide-olmayansolo-banka`.

## Yeniden üretilebilir keşif algoritması (TBBAdapter.discover)
1. Kategori sayfası (11232 / 11236 / 11237) → her bölümün `<form>` içindeki `<select name=rapor_donemi>` (yıl→id) ve `<select name=ay>`; `list_id` form action'ından.
2. `/istatistiki-raporlar-liste/<list_id>?rapor_donemi=<id>&ay=<ay>` → `<a href="/istatistiki-raporlar/<yıl>-<ay>-<slug>">`.
3. Rapor sayfası → `<a href="/download/node/<nid>/field_raporlar_ekler/<fid>" title="<dosya adı>">` (+ `/sites/default/files/raporlar/...`).
4. GET (httpx → requests → [playwright]); biçim içerik imzasından; sha256 ile revizyon; ham dosya `data/raw/<dataset>/` altında değiştirilmeden.
