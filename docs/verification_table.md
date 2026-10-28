# Doğrulama Tablosu — TBB / BDDK banka bazında veri keşfi (28.10.2026)

Durumlar: VERIFIED (dosya açıldı, alan+dönem görüldü) · UNVERIFIED (kaynak bulundu, içerik açılamadı) · UNAVAILABLE (o kaynak/dönemde alan yok) · ERROR (teknik hata). Birbirinin yerine kullanılmaz.

| VERİ ALANI | KAYNAK | DOSYA | DÖNEM | BANKA BAZINDA MI? | GERÇEK SÜTUN/SATIR | DOĞRULAMA DURUMU | AÇIKLAMA |
|---|---|---|---|---|---|---|---|
| loans_gross, total_deposits, total_assets, total_equity (bilanço kalemleri) | TBB | Finansal Tablolar – Konsolide Olmayan (Solo Banka, Excel ortak veri seti) — kategori 11232, rapor listesi 11241 (https://www.tbb.org.tr/istatistiki-raporlar-liste/11241?rapor_donemi=11411&ay=6 kalıbı) | 2026-06 | Evet (bölüm adı 'Solo Banka'; dosyadan doğrulanmadı) | — (Excel eki açılamadı) | UNVERIFIED | Kategori sayfasında yıl listesi 2002–2026 ve ay listesi Mart/Haziran/Eylül/Aralık doğrulandı; rapor sayfaları (2025 Haziran/Eylül, 2024 Eylül) sunucu hatası verdi veya ek bağlantısı sayfa metninde görünmedi. 'K1 Mali Bünye / K2 Aktifler / K3 Pasifler / K4 Gelir-Gider / K5 Nazım' adlandırması hiçbir resmî sayfada GÖRÜLMEDİ — dosya içi sayfa adları olabilir; doğrulanana kadar varsayım. |
| total_assets, loans, deposits, equity, net profit (sıralama tablosu) | TBB | Aktif Büyüklüğüne Göre Banka Sıralaması.xls → https://www.tbb.org.tr/download/node/54929/field_raporlar_ekler/310010 | 2026-06 | Evet (rapor adı banka sıralaması) | — (xls açılamadı) | UNVERIFIED | 2026 Haziran rapor sayfası ve .xls ek bağlantısı okundu; dosyanın kendisi sunucu hatası + sandbox ağ engeli nedeniyle açılamadı. Sütunlar (Toplam Aktifler/Krediler/Mevduat/Özkaynaklar/Net Kâr) BEKLENTİ, doğrulanmadı. |
| employee_count, branch_count | TBB | Banka, Çalışan ve Şube Sayıları Haziran 2026 (Rapor Kodu DT13, Ağustos 2026) → https://www.tbb.org.tr/download/node/54910/field_raporlar_ekler/309903 | 2026-06 | Evet | Tablo 1 'Banka, Şube ve Çalışan Sayıları': Banka \| Şube Sayısı \| Çalışan Sayısı (kamu/özel/yabancı/KYB grupları altında banka satırları); Tablo 4: Şube ve Çalışan Sayısı Haz 2025 \| Ara 2025 \| Haz 2026 | VERIFIED | Dosya resmî adresten okundu. Biçim PDF; Excel sürümü olup olmadığı rapor sayfasından kontrol edilecek. |
| loan_interest_tl, deposit_interest_tl | TBB | Banka Bazında Seçilmiş Tablolar, Konsolide Olmayan (DT20) Haziran 2023 → https://www.tbb.org.tr/sites/default/files/raporlar/51298/ekler/Banka_Bazinda_Secilmis_Tablolar-Haziran_2023_0.pdf | 2023-06 | Evet (sektör, gruplar ve tek tek bankalar) | Tablo 'Verilen Kredilere ve Diğer Mevduata Uygulanan Ortalama Faiz Oranları*, %' → başlık TL → alt başlık 'Verilen Krediler' \| 'Mevduat'; örnek satırlar: Ziraat 12.07 \| 21.40; Halk 14.53 \| 22.07; Vakıflar 15.90 \| 29.96; Akbank 20.98 \| 22.24; Anadolubank 13.59 \| 23.75 | VERIFIED | Dipnot (*): faiz oranı riski amaçlı hazırlanan parasal finansal araçlara uygulanan ORTALAMA faiz oranlarından derlenmiştir; (**) mevduat: bankalararası hariç. Yani dönem sonu STOK ortalama uygulanan oran — yeni açılış faizi DEĞİL, muhasebesel getiri/maliyet DEĞİL. |
| loan_interest_usd, deposit_interest_usd | TBB | DT20 Haziran 2023 (aynı dosya) | 2023-06 | Evet | Aynı tablo → başlık USD → 'Verilen Krediler' \| 'Mevduat'; Ziraat 8.64 \| 3.26; Halk 8.50 \| 2.78; Vakıflar 9.51 \| 1.83; Akbank 10.25 \| 1.46 | VERIFIED | Tanım TL ile aynı (stok ortalama uygulanan oran). |
| loan_interest_eur, deposit_interest_eur | TBB | DT20 Haziran 2023 (aynı dosya) | 2023-06 | Evet | Aynı tablo → başlık EURO → 'Verilen Krediler' \| 'Mevduat'; Ziraat 7.22 \| 0.77; Halk 5.56 \| 1.87; Vakıflar 7.24 \| 1.77; Akbank 7.10 \| 0.26 | VERIFIED | Tanım TL ile aynı. |
| loan/deposit_interest_{tl,usd,eur} | TBB | DT20 Mart 2023 | 2023-03 | Evet (beklenti) | — (dosya açılmadı) | UNVERIFIED | Mart 2023 dosyası bu oturumda açılamadı; Haziran 2023 ile aynı tablo yapısı BEKLENİR ama doğrulanmadı. Konsolide sürüm (DT21) için Aralık 2019, Mart 2021, Haziran 2022 dosyalarında aynı tablo doğrulandı. |
| loan/deposit_interest_{tl,usd,eur} | TBB | DT20 Haziran 2026 (bölüm: 'Banka Bilgileri (Seçilmiş Tablolar, Konsolide Olmayan)', kategori 11236) | 2026-06 | Evet (beklenti) | — (dosya açılmadı) | UNVERIFIED | Kategori sayfası (11236) bu oturumda sunucu hatası verdi; EN kategori sayfasında bölüm için yıl 2026 görüldü ancak ay listesi 'March' olarak göründü → Haziran 2026 DT20'nin yayımlandığı DOĞRULANMADI (yayın takvimine göre dönem sonu +45 gün ≈ Ağustos 2026). 2026'da aynı sütunların yayımlandığı varsayılmıyor. |
| loan_maturity_0_1m / 1_3m / 3_6m / 6_12m (kredi kalan vade) | TBB | DT20 Haziran 2023 → tablo 'Aktif ve Pasif Kalemlerin Kalan Vadelerine Göre Gösterimi, Milyon TL' | 2023-06 | Evet, ancak kalem TOPLAM AKTİF | Kovalar: Vadesiz \| 1 Ay \| 1-3 Ay \| 3-12 Ay \| 1-5 Yıl \| 5 Yıl ve Üzeri \| Dağıtılamayan \| Toplam; bloklar: toplam aktifler, toplam pasifler, likidite açığı | UNAVAILABLE | Bu tablo kredileri AYRI vermiyor; toplam aktif vade dağılımı kredi vade dağılımı olarak KABUL EDİLMEDİ (proje kuralı). 3-12 ay tek kovadır; 3-6 / 6-12 ayrımı kaynakta yok. Alternatif: finansal tablo dipnotlarında kredilerin kalan vade kovası standart değildir (yalnızca kısa / orta-uzun orijinal vade) → banka bazında ≤12 ay kredi kalan vadesi için bilinen kamuya açık yapılandırılmış kaynak bulunamadı. |
| deposit_demand, deposit_maturity_0_1m / 1_3m / 3_6m / 6_12m (mevduat kalan vade) | TBB | DT20 Haziran 2023 → aynı tablo | 2023-06 | Evet, ancak kalem TOPLAM PASİF | Kovalar yukarıdaki gibi; mevduat satırı yok | UNAVAILABLE | Toplam pasif vade dağılımı mevduat vade dağılımı olarak KABUL EDİLMEDİ. Alternatif kaynak: 17 Sayılı Tebliğ formatı dipnotu 'Mevduatın vade yapısı' (Vadesiz \| 7 Gün İhbarlı \| 1 Aya Kadar \| 1-3 Ay \| 3-6 Ay \| 6 Ay-1 Yıl \| 1 Yıl ve Üstü \| Birikimli; TP/YP) — TBB Veri Sorgulama Sistemi 'Dipnotlar' ve/veya Excel ortak veri seti üzerinden banka bazında olması beklenir; bu oturumda DOĞRULANMADI (aşağıya bakınız). |
| deposit_maturity_* (dipnot: Mevduatın vade yapısı) | TBB | Finansal Tablolar Excel ortak veri seti (dipnot tabloları içeriyorsa) / TBB Veri Sorgulama Sistemi → Dipnotlar | 2026-06 | Evet (beklenti) | — (açılmadı) | UNVERIFIED | Veri Sorgulama Sistemi kullanım kılavuzu: 'Dipnotlar — 17 Sayılı Tebliğ kapsamındaki dipnot tipi tablolar (Konsolide Olmayan / Konsolide)', bankalar tek tek seçilebilir, dönemler 1988→. Ancak verisistemi.tbb.org.tr robots.txt otomatik erişimi yasaklıyor → bu adaptör onu kullanmaz; Excel ortak veri setinin dipnot içerip içermediği dosya açılarak doğrulanacak. |
| total_assets/total_liabilities kalan vade dağılımı | TBB | Seçilmiş İstatistikler → 'Aktif ve Pasiflerin Kalan Vadelerine Göre Gösterimi' (kategori 11237) | 2026-06 | Evet (beklenti; DT20'deki aynı adlı tablo banka bazında) | — (dosya açılmadı) | UNVERIFIED | Kategori sayfasında yıl 2026 ve ay Mart/Haziran seçenekleri doğrulandı (seri 2002→). Yayın takvimi: Mar/Haz/Eyl +45 gün, Aralık Nisan sonu. |
| banka bazında herhangi bir alan | BDDK | Aylık Bankacılık Sektörü Verileri (Temel/Gelişmiş Gösterim) https://www.bddk.org.tr/BultenAylik/ | 2026-06 (aylık) | HAYIR | Bilanço \| Kar/Zarar \| Likidite \| Sermaye Yeterliliği \| YP Pozisyonu \| Diğer (sektör ve gruplar) | UNAVAILABLE | BDDK açıklama sayfası: banka bazında toplanan veriler, hangi bankaya ait olduğu anlaşılmayacak şekilde toplulaştırılarak yayımlanır. Yalnızca Excel dışa aktarımı (JS arayüzü). Sektör/grup karşılaştırma katmanı için kullanılabilir; banka verisi yerine KULLANILMAZ. |
| sektör/grup temel göstergeler | BDDK | TBS Temel Göstergeleri Haziran 2026 → https://www.bddk.org.tr/Veri/EkGetir/8?ekId=676 | 2026-06 | HAYIR (sahiplik/fonksiyon grupları) | — (dosya açılmadı) | UNVERIFIED | Veri/Detay/162 sayfasından ekId listesi (659→676, 2022-06→2026-06) okundu; dosya biçimi (PDF/xlsx) ve içeriği açılmadı. |
| Excel ortak veri seti — dosya yapısı (banka bazlı seçici) | TBB | https://www.tbb.org.tr/istatistiki-raporlar/2025-eylul-finansal-tablolar-konsolide-olmayan-solo-banka-excel-formatinda (liste 11241, 2025→rapor_donemi=11405) | 2025-09 | EVET — sayfa 'Banka Seçiniz' seçicisiyle 57 bankayı tek tek listeliyor | Seçici seçenekleri (resmî adlar): Akbank T.A.Ş. … Ziraat Dinamik Banka A.Ş. (dijital banka); dosya bağlantısı seçime bağlı (değer/JS yapısı görülemedi) | VERIFIED | Veri seti banka bazında ayrı Excel dosyaları olarak sunuluyor (tek toplu dosya değil). Dosyanın kendisi ve sayfa adları açılmadı → K1–K5 adlandırması hâlâ doğrulanmadı. Seçici listesi tohum banka kaydını güncelledi (Colendi, Enpara, Hedef, Misyon, Türk Ticaret, Ziraat Dinamik, BofA Yatırım). |
| robots.txt (TBB) | TBB | https://www.tbb.org.tr/robots.txt | — | — | — (içerik okunamadı) | UNVERIFIED | Web okuyucu aracı 28.10.2026 öğleden sonra /download/node/... ve /istatistiki-raporlar/... adresleri için 'robots_disallowed' döndürdü (aynı adresler sabah okunabilmişti). Genel '*' kuralı mı, yapay zekâ botlarına özel kural mı bilinmiyor; probe robots.txt'yi kaydedecek. Downloader varsayılanı strict; lenient kararı kullanıcıya ait. |
| İndirme otomasyonu (TBB statik dosyalar) | TBB | /download/node/<nid>/field_raporlar_ekler/<fid> ve /sites/default/files/raporlar/<nid>/ekler/<dosya> | — | — | — | VERIFIED | Bağlantılar düz HTTP GET; oturum/CAPTCHA gözlenmedi (DT13 Haziran 2026 ve DT20/DT21 PDF'leri doğrudan okundu). Dönem→rapor_donemi id eşlemesi opak (2026→11411, 2024→11279) → kategori sayfasındaki <select>'ten okunur, tahmin edilmez. |
| İndirme denemesi (bu çalışma ortamı) | TBB/BDDK/TCMB | curl/httpx/requests → www.tbb.org.tr, verisistemi.tbb.org.tr, www.bddk.org.tr, evds3.tcmb.gov.tr | — | — | — | ERROR | Sandbox DNS düzeyinde dış siteleri çözmüyor (yalnızca PyPI/npm/GitHub izinli): curl exit 56, 'Name or service not known'. Dosyalar bu ortamdan İNDİRİLEMEDİ; keşif resmî sayfaların/dosyaların web-okuyucu ile okunmasıyla yapıldı. Motor gerçek ortamda çalıştırılmalıdır. |
| TBB Veri Sorgulama Sistemi (Mali Tablolar + Dipnotlar, banka bazında, 1988→) | TBB | https://verisistemi.tbb.org.tr/ (kılavuz: /sites/default/files/docs/bbtsyardim.pdf) | tüm çeyrekler | Evet (kılavuz) | Mali Tablolar: bilanço, gelir-gider, bilanço dışı; Dipnotlar (17 Sayılı Tebliğ) solo/konsolide; birim TL/Bin/Milyon/Milyar | UNVERIFIED | robots.txt otomatik erişimi yasaklıyor (web-okuyucu 'robots_disallowed'). Proje kuralı gereği izinsiz aşılmaz; resmî Excel yayınları birincil yol olarak kalır. TBB'den API/izin alınması değerlendirilebilir. |
| Katılım bankaları | TBB | — | — | — | — | UNAVAILABLE | TBB üyeleri mevduat + kalkınma/yatırım bankalarıdır; katılım bankaları TKBB üyesidir ve TBB tablolarında yer almaz → ayrı kaynak gerekir. |
| usd_try, eur_try, policy_rate, cpi, deposit_rate_tl, loan_rate_tl, ... (makro) | TCMB EVDS | https://evds3.tcmb.gov.tr/service/evds/... | günlük/haftalık/aylık | Hayır (sektör/piyasa) | — (seri kodu doğrulanmadı) | UNVERIFIED | API anahtarı sağlanmadı; seri kodları tahmin edilmeyecek, serieList uç noktasından doğrulanıp kaydedilecek. |

## Öncelikli araştırma sorularının cevapları

**1. Haziran 2026 banka bazında kredi tutarları mevcut mu?**

Kaynak ve dönem bulundu (TBB solo Excel veri seti + Aktif Büyüklük sıralaması .xls); dosya içeriği açılamadığı için UNVERIFIED. Yok DEĞİL.

**2. Haziran 2026 banka bazında mevduat tutarları mevcut mu?**

Aynı kaynaklar; UNVERIFIED.

**3. Kredi ve mevduatın ≤12 ay kalan vade dağılımları ayrı ayrı mevcut mu?**

TBB 'Kalan Vade' tablosu TOPLAM aktif/pasif verir → bu tabloda UNAVAILABLE. Mevduat için dipnot 'Mevduatın vade yapısı' (3-6, 6-12 dahil) adaydır (UNVERIFIED); krediler için ≤12 ay kalan vade kovası bilinen kamuya açık yapılandırılmış kaynakta bulunamadı.

**4. TL kredi ortalama faizi banka bazında mevcut mu?**

Evet — DT20/DT21 tablosu; Haziran 2023 VERIFIED, Haziran 2026 UNVERIFIED.

**5. TL mevduat ortalama faizi banka bazında mevcut mu?**

Evet — aynı tablo (bankalararası mevduat hariç); Haziran 2023 VERIFIED.

**6. USD ve EUR faizleri banka bazında mevcut mu?**

Evet — aynı tabloda USD ve EURO sütunları; Haziran 2023 VERIFIED.

**7. Faiz verilerinin gerçek tanımı nedir?**

Faiz oranı riski dipnotundaki 'parasal finansal araçlara uygulanan ortalama faiz oranları' → dönem sonu STOK ortalama uygulanan oran; yeni açılış faizi değil, muhasebesel faiz geliri/gideri bazlı getiri/maliyet değil. Makas yalnızca aynı tanım içinde hesaplanır.

**8. Tarihsel veri hangi dönemlere kadar uzanıyor?**

Seçilmiş Tablolar (DT20/DT21): 2005→ (EN kategori sayfası yıl listesi); Finansal Tablolar Excel veri seti: 2002→; Kalan vade tablosu: 2002→; Veri Sorgulama Sistemi: 1988→ (2002 Aralık sonrası 17 Sayılı Tebliğ formatı).

**9. Dosyalar kullanıcı müdahalesi olmadan indirilebiliyor mu?**

TBB statik ekler: evet (düz GET, oturum/CAPTCHA yok). Veri Sorgulama Sistemi: robots.txt yasak → hayır (izinsiz aşılmaz). BDDK bültenleri: JS arayüzü, tarayıcı otomasyonu gerekir; BDDK TBS dosyaları: düz GET.

**10. Aynı işlem sonraki dönemlerde otomatik tekrarlanabiliyor mu?**

Evet — kategori sayfası <select> (yıl→rapor_donemi id) + /istatistiki-raporlar-liste/<list_id>?rapor_donemi=&ay= + rapor sayfası ekleri kalıbı; zamanlayıcı yayın takvimi gecikmelerine göre (dönem sonu +45/+75 gün) kontrol eder. Canlı doğrulama gerçek ağ ortamında yapılacak.
