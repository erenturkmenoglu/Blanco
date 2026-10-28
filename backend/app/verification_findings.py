"""Doğrulama tablosu — veri keşfi bulgularının tek kaynağı (28.10.2026, güncel: GitHub Actions runner ile gerçek dosyalar indirilip açıldı).

  VERIFIED    = dosya/sayfa okundu, alan ve dönem görüldü (gerçek sütun/satır adları aşağıda)
  UNVERIFIED  = kaynak/bölüm/bağlantı bulundu ama dosya içeriği açılamadı
  UNAVAILABLE = o kaynak ve dönem için alan YOK
  ERROR       = teknik toplama hatası
Bu liste hem veritabanına (dataset_fields) tohumlanır hem docs/verification_table.md olarak üretilir.
"""
from __future__ import annotations

COLUMNS = ["VERİ ALANI", "KAYNAK", "DOSYA", "DÖNEM", "BANKA BAZINDA MI?", "GERÇEK SÜTUN/SATIR", "DOĞRULAMA DURUMU", "AÇIKLAMA"]

TBB = "https://www.tbb.org.tr"
DT20 = ("TBB 'Banka Bilgileri (Seçilmiş Tablolar, Konsolide Olmayan)' 2026 Haziran (rapor sayfası /istatistiki-raporlar/2026-haziran-banka-bilgileri-secilmis-tablolar-konsolide-olmayansolo-banka; "
        "ekler /download/node/54932/field_raporlar_ekler/310643 1.Mali bünye.xls, 310157 2.Aktifler.xls, 310158 3.Pasifler.xls, 310159 4.Gelir-Gider.xls, 310160 5.Nazım.xls, 310161 Açıklamalar.xls)")
WB = ("TBB 'Finansal Tablolar – Konsolide Olmayan (Solo Banka, Excel ortak veri seti)' 2026 Haziran — banka bazında zip: "
      "/sites/default/files/raporlar/54947/bankalar/<Banka Adı>.zip (içinde <Banka>.xls 42 sayfa + <Banka>-Ek Tablolar.xlsx); Akbank ve Ziraat açıldı")

FINDINGS: list[dict] = [
    # ---- Haziran 2026: kredi / mevduat tutarları (banka bazında)
    dict(field="loans_gross (Krediler), total_deposits (Mevduat), total_assets, total_equity, net_profit …", source="TBB", dataset="tbb_dt20_selected_solo",
         file=DT20, period="2026-06", per_bank="EVET — 58 banka + sektör/grup satırları (72 satır)",
         cells="2.Aktifler.xls / sayfa 'Varlıklar': başlık yolu 'İtfa Edilmiş Maliyeti ile Ölçülen FV (Net) / Krediler', 'Toplam Aktifler', 'Finansal Varlıklar (net) / Likit Aktifler / Nakit Değerler ve TCMB' …; "
               "3.Pasifler.xls / 'Yükümlülükler': 'Mevduat', 'Mevduat Dışı Kaynaklar / Alınan Krediler', 'Özkaynaklar / Ödenmiş Sermaye', 'Toplam Yükümlülükler'; birim Milyon TL. "
               "Örnek: Ziraat Toplam Aktifler 9.076.507, Krediler 4.929.033, Mevduat 5.780.816; Akbank 3.727.680 / 2.061.098 / 2.382.280",
         status="VERIFIED", note="Aktif = Pasif özdeşliği ve Mevduat+Mevduat dışı+Diğer+Özkaynak = Toplam özdeşliği tüm bankalarda sağlandı. Aynı değerler 'Aktif Büyüklüğüne Göre Banka Sıralaması.xls' "
                                "(/download/node/54929/field_raporlar_ekler/310010; sütunlar Banka | Kuruluş Yılı | Toplam Aktifler | Toplam Krediler* | Toplam Mevduat | Toplam Özkaynaklar | Ödenmiş Sermaye | Net Dönem Kar/Zararı | Bilanço Dışı Hesaplar, Milyon TL) ile birebir."),
    dict(field="loans_tl / loans_fx, deposits_tl / deposits_fx (TP/YP ayrımı)", source="TBB", dataset="tbb_fs_solo_excel", file=WB, period="2026-06 (ve önceki dönem 2025-12)",
         per_bank="EVET — her banka kendi dosyasında", cells="<Banka>.xls / sayfa 'varlıklar': satır '2.1.Krediler' × sütunlar TP | YP | Toplam (30/06/2026) | TP | YP | Toplam (31/12/2025); "
                                                            "sayfa 'yüküm.': 'I. MEVDUAT' aynı sütun düzeni; Milyon TL. Akbank: krediler TP 1.517.781 / YP 543.317; mevduat TP 1.574.270 / YP 808.010",
         status="VERIFIED", note="Standart BDDK/TFRS formatı (17 Sayılı Tebliğ ortak veri gönderim seti). Önceki dönem sütunları Aralık 2025 verisini de verir."),
    dict(field="Gelir tablosu (faiz gelir/gider, NII, komisyon, karşılık, personel, VÖK, net kâr) — YTD ve BAĞIMSIZ ÇEYREK", source="TBB", dataset="tbb_fs_solo_excel", file=WB, period="2026-06",
         per_bank="EVET", cells="<Banka>.xls / 'gelir': satırlar I. FAİZ GELİRLERİ … XXV. DÖNEM NET KARI/ZARARI; sütunlar CARİ DÖNEM (01/01/2026-30/06/2026) | ÖNCEKİ DÖNEM (01/01/2025-30/06/2025) | "
                                "CARİ DÖNEM (01/04/2026-30/06/2026) | ÖNCEKİ DÖNEM (01/04/2025-30/06/2025). Akbank NII YTD 83.173, 2Ç 42.576; DT20 4.Gelir-Gider.xls aynı YTD değerleri tüm bankalar için",
         status="VERIFIED", note="Çeyrek değerleri kaynakta hazır → fark alma gerekmez; DT20 Gelir-Gider yalnızca YTD (kümülatif) verir."),
    # ---- faiz oranları
    dict(field="loan_interest_tl, deposit_interest_tl, loan/deposit_interest_usd, loan/deposit_interest_eur", source="TBB", dataset="tbb_dt20_selected_solo",
         file=DT20 + " → 1.Mali bünye.xls", period="2026-06", per_bank="EVET — 58 banka",
         cells="sayfa 'Ort.Faiz Oranı': başlık 'Verilen Kredilere ve Diğer Mevduata Uygulanan Ortalama Faiz Oranları*, %' (Haziran 2026); satır 4: Banka | TL | | USD | | EURO; satır 5: Verilen Krediler | Mevduat** …; "
               "örnek: Sektör Toplamı 43,12 | 37,62 | 7,44 | 1,46 | 6,42 | 0,81; Ziraat 42,04 | 38,85 | 7,45 | 2,07 | 6,86 | 0,68; Akbank 42,13 | 41,10 | 6,94 | 2,22 | 5,96 | 1,67",
         status="VERIFIED", note="Dipnot (*): faiz oranı riskine ilişkin olarak hazırlanan parasal finansal araçlara uygulanan ortalama faiz oranlarından derlenir; (**) bankalararası mevduat hariç. "
                                "→ rate_definition = stock_avg_applied_rate (dönem sonu stok ortalama uygulanan oran); yeni açılış faizi DEĞİL, muhasebesel getiri DEĞİL."),
    dict(field="Ortalama faiz oranları — JPY dahil, araç bazında (krediler, diğer mevduat, bankalar mevduatı, ihraç edilen MK, para piyasası, …)", source="TBB", dataset="tbb_fs_solo_excel",
         file=WB, period="2026-06 ve 2025-12", per_bank="EVET", cells="<Banka>.xls / 'malibünye1' blok 'Parasal Finansal Araçlara Uygulanan Ortalama Faiz Oranları: % (3 Aylık)': sütunlar EURO | USD | Yen | TL; "
                                                                        "satırlar Varlıklar: Nakit Değerler, Bankalar, GUD FK, Para Piyasalarından Alacaklar, GUD DKG, Verilen Krediler, İtfa; Yükümlülükler: Bankalar Mevduatı, Diğer Mevduat, "
                                                                        "Para Piyasalarına Borçlar, Muhtelif Borçlar, İhraç Edilen Menkul Değerler, Diğer Mali Kuruluşlardan Sağlanan Fonlar; 'Cari Dönem Sonu' ve 'Önceki Dönem Sonu' blokları",
         status="VERIFIED", note="DT20 tablosunun kaynağı; Akbank Verilen Krediler TL 42,13 / Diğer Mevduat TL 41,10 — DT20 ile birebir."),
    dict(field="loan/deposit_interest_{tl,usd,eur}", source="TBB", dataset="tbb_dt20_selected_solo", file="DT20 Haziran 2023 (…/raporlar/51298/ekler/Banka_Bazinda_Secilmis_Tablolar-Haziran_2023_0.pdf)",
         period="2023-06", per_bank="EVET", cells="Aynı tablo; Ziraat TL 12,07 | 21,40; USD 8,64 | 3,26; EUR 7,22 | 0,77", status="VERIFIED",
         note="Tarihsel seri DT20/DT21 ile 2005'e kadar geri gider (kategori sayfası yıl listesi 2005–2026). Mart 2023 dosyası açılmadı (aynı yapı beklenir)."),
    # ---- vade
    dict(field="loan_maturity_0_1m, loan_maturity_1_3m, loan_maturity_3_12m (kredi KALAN vade)", source="TBB", dataset="tbb_fs_solo_excel", file=WB, period="2026-06",
         per_bank="EVET", cells="<Banka>.xls / 'malibünye1' blok 'Aktif ve Pasif Kalemlerin Kalan Vadelerine Göre Gösterimi: (3 Aylık)': sütunlar Vadesiz | 1 Aya Kadar | 1-3 Ay | 3-12 Ay | 1-5 Yıl | 5 Yıl ve Üzeri | Dağıtılamayan | Toplam; "
                                "satır 'Verilen Krediler' (Akbank: - | 727.559 | 244.230 | 476.967 | 388.527 | 144.650 | 79.165 | 2.061.098; Ziraat: 0 | 615.359 | 440.583 | 1.698.797 | 1.602.947 | 405.755 | 36.520 | 4.799.961)",
         status="VERIFIED", note="Krediler için 3-12 ay TEK kovadır → 3-6 / 6-12 ayrımı kaynakta YOK (yapay bölünmez). Aynı blokta 'Diğer Mevduat' ve 'Bankalar Mevduatı' satırları (mevduatın kalan vadesi) ve Toplam Varlıklar/Yükümlülükler/Likidite Açığı var."),
    dict(field="deposit_demand, deposit_maturity_0_1m / 1_3m / 3_6m / 6_12m (mevduat SÖZLEŞMESEL vade, mevduat türü bazında)", source="TBB", dataset="tbb_fs_solo_excel", file=WB, period="2026-06 ve 2025-12",
         per_bank="EVET", cells="<Banka>.xls / 'pasif1' blok '2.a.1.i) Mevduatın vade yapısına ilişkin bilgiler: (3 Aylık)': sütunlar Vadesiz | 7 Gün İhbarlı | 1 Aya Kadar | 1-3 Ay | 3-6 Ay | 6 Ay-1 Yıl | 1 Yıl ve Üstü | Birikimli Mevduat | Toplam; "
                                "satırlar Tasarruf Mevduatı, Döviz Tevdiat Hesabı (Yurtiçinde/Yurtdışında Yerleşik), Resmi Kur., Tic. Kur., Diğ. Kur., Kıymetli Maden, Bankalar Mevduatı (TCMB, Yurtiçi, Yurtdışı, Katılım), Toplam. "
                                "Akbank Toplam: 760.881 | 0 | 469.708 | 881.168 | 91.970 | 71.832 | 106.716 | 5 | 2.382.280",
         status="VERIFIED", note="Hedef kovaların tamamı (3-6 ve 6-12 dahil) mevduat için mevcut. DT20 3.Pasifler.xls 'Mevd.Vade' sayfası ise tüm bankalar için ama kovalar Vadesiz+7 Gün | 1 Aya Kadar | 1-3 Ay | 3 Ay ve Üstü | Toplam (3 ay+ tek kova)."),
    dict(field="total_assets / total_liabilities / liquidity_gap kalan vade dağılımı (tüm bankalar)", source="TBB", dataset="tbb_dt20_selected_solo", file=DT20 + " → 1.Mali bünye.xls", period="2026-06",
         per_bank="EVET — 58 banka", cells="sayfa 'Likidite Riski' ('Aktif ve Pasif Kalemlerin Kalan Vadelerine Göre Gösterimi, Milyon TL'): Varlıklar / Yükümlülükler / Likitide Açığı × Vadesiz | 1 ay | 1-3 ay | 3-12 ay | 1-5 yıl | 5 yıl ve üzeri | Dağıtılamayan | Toplam",
         status="VERIFIED", note="Toplam düzeyinde; kredi/mevduat ayrımı için banka kitabı kullanılır. Ayrıca 'Aktif ve Pasiflerin Kalan Vadelerine Göre Gösterimi.xls' (/download/node/54933/field_raporlar_ekler/310162) SEKTÖR toplamını kalem bazında (Verilen Krediler, Diğer Mevduat …) verir."),
    # ---- kredi kalitesi, sermaye, likidite
    dict(field="npl_amount, npl_provisions, stage_1/2 loans, restructured, ECL stage 1-3, capital_adequacy_ratio, risk_weighted_assets, nsfr", source="TBB", dataset="tbb_dt20_selected_solo",
         file=DT20, period="2026-06", per_bank="EVET", cells="2.Aktifler.xls 'Donuk Alacak' ('Toplam donuk alacak hareketleri / Dönem Sonu Bakiyesi', 'Karşılık (-)', 'Bilançodaki Net Bakiyesi'), 'Std.Nit.-Yakın İzl.Kred.' (Standart / Yakın İzleme / Yeniden Yapılandırılan Toplam sütunları); "
                                                              "4.Gelir-Gider.xls 'Karşılıklar' (1./2./3. Aşama); 1.Mali bünye.xls 'Sermaye Std. Oranı' (Toplam Risk Ağırlıklı Tutarlar | Özkaynak | SYR %), 'Net İstik.Fon.Oranı'. Akbank: NPL 79.165, karşılık 53.261, SYR 17,48%, NİFO 119,2%",
         status="VERIFIED", note="npl_ratio = npl_amount / loans_gross; coverage = npl_provisions / npl_amount (DERIVED)."),
    dict(field="employee_count, branch_count", source="TBB", dataset="tbb_dt13_bank_branch_employee",
         file=f"Banka, Çalışan ve Şube Sayıları Haziran 2026 (DT13) → {TBB}/download/node/54910/field_raporlar_ekler/309903 (PDF) ve …/309904 (docx)", period="2026-06", per_bank="EVET",
         cells="Tablo 1 'Banka, Şube ve Çalışan Sayıları'", status="VERIFIED", note="Yalnızca PDF/docx; xls sürümü yok → PDF tablo çıkarımı ayrı aşama (ilk sürümde DB'ye yazılmadı)."),
    # ---- kaynak yapısı / otomasyon
    dict(field="Dosya yapısı: K1–K5", source="TBB", dataset="tbb_dt20_selected_solo", file=DT20, period="2026-06", per_bank="—",
         cells="1.Mali bünye.xls (Sermaye Std. Oranı, Kur Riski, Faiz Riski, Ort.Faiz Oranı, Likidite Riski, Net İstik.Fon.Oranı) · 2.Aktifler.xls (Varlıklar, Std.Nit.-Yakın İzl.Kred., Tüketici, Ticari, Kredi, Donuk Alacak, Donuk Brüt-Net) · "
               "3.Pasifler.xls (Yükümlülükler, Mevd.Vade, Sig. Kaps., Alın.Kred., Ödenecek Vergi) · 4.Gelir-Gider.xls (Gelir-Gider, Karşılıklar, Diğer Faal.Gid., Ticari Kar-Zarar) · 5.Nazım.xls (Nazım) · Açıklamalar.xls",
         status="VERIFIED", note="Proje belgesindeki 'K1 Mali Bünye … K5 Nazım' adlandırması bu dosya setine karşılık gelir (dosya adları 1.–5. ile numaralı)."),
    dict(field="Keşif/indirme otomasyonu (kategori → rapor sayfası → ekler / banka zip'leri)", source="TBB", dataset="tbb_*",
         file=f"{TBB}/istatistiki-raporlar/11232 | 11236 | 11237", period="—", per_bank="—",
         cells="select.rapor-donemi-secimi[data-cat=<list_id>] option value='/istatistiki-raporlar-liste/<list_id>?rapor_donemi=<id>' (2026→11411, 2025→11405, 2024→11279); select.ay-yil-<list_id> option value = en güncel yılın rapor sayfası URL'si; "
               "rapor sayfasında <a href='/download/node/<nid>/field_raporlar_ekler/<fid>' title='…xls'>; Excel veri seti sayfasında <select> 'Banka Seçiniz' option value = '/sites/default/files/raporlar/54947/bankalar/<Banka>.zip'. "
               "list_id'ler: 11240 FS solo, 11241 FS solo Excel, 11242 FS konsolide, 11243 FS konsolide Excel, 11244 DT20, 11245 DT21, 11246 Banka ve Grup 3 Aylık, 11254 Sıralama, 11276 Kalan Vade, 11256 DT13",
         status="VERIFIED", note="GitHub Actions runner'da iki probe koşusu: tüm hedef dosyalar düz HTTP GET ile indirildi (oturum/CAPTCHA yok). robots.txt Drupal varsayılanı (User-agent: * → /admin/, /user/… yasak; /download/ ve /istatistiki-raporlar/ SERBEST) "
                                "→ web okuyucu aracının 'robots_disallowed' yanıtı o aracın kendi kuralıydı; strict politika da çalışır."),
    dict(field="İndirme denemesi (geliştirme sandbox'ı)", source="TBB/BDDK/TCMB", dataset="—", file="curl/httpx/requests → www.tbb.org.tr …", period="—", per_bank="—", cells="—", status="ERROR",
         note="Sandbox dış siteleri DNS/proxy düzeyinde engelliyor (ProxyError 403) → çözüm: GitHub Actions runner (tbb-probe.yml, ingest.yml) + sonuçların results/* dalına yayımlanması."),
    # ---- BDDK / diğer
    dict(field="banka bazında herhangi bir alan", source="BDDK", dataset="bddk_monthly_bulletin", file="Aylık Bankacılık Sektörü Verileri https://www.bddk.org.tr/BultenAylik/", period="aylık",
         per_bank="HAYIR", cells="Bilanço | Kar/Zarar | Likidite | Sermaye Yeterliliği | YP Pozisyonu | Diğer (sektör ve gruplar)", status="UNAVAILABLE",
         note="BDDK: banka bazında toplanan veriler, hangi bankaya ait olduğu anlaşılmayacak şekilde toplulaştırılarak yayımlanır. Sektör/grup karşılaştırma katmanı; banka verisi yerine KULLANILMAZ."),
    dict(field="sektör/grup temel göstergeler", source="BDDK", dataset="bddk_tbs_temel_gostergeler", file="TBS Temel Göstergeleri Haziran 2026 → https://www.bddk.org.tr/Veri/EkGetir/8?ekId=676", period="2026-06",
         per_bank="HAYIR", cells="— (dosya açılmadı)", status="UNVERIFIED", note="ekId listesi 659 (2022-06) → 676 (2026-06) sayfadan okundu; biçim/içerik açılmadı."),
    dict(field="TBB Veri Sorgulama Sistemi", source="TBB", dataset="—", file="https://verisistemi.tbb.org.tr/", period="1988→", per_bank="EVET (kılavuz)", cells="Mali Tablolar + Dipnotlar (17 Sayılı Tebliğ)",
         status="UNVERIFIED", note="Gerek kalmadı: aynı dipnotlar Excel ortak veri setinde banka bazında dosya olarak mevcut."),
    dict(field="Katılım bankaları", source="TBB", dataset="—", file="—", period="—", per_bank="—", cells="—", status="UNAVAILABLE", note="TBB üyesi değil (TKBB); DT20/Excel setinde yer almaz → ayrı kaynak gerekir."),
    dict(field="usd_try, eur_try, policy_rate, cpi, deposit_rate_tl, loan_rate_tl … (makro)", source="TCMB EVDS", dataset="evds_macro", file="https://evds3.tcmb.gov.tr/service/evds/…", period="günlük/haftalık/aylık",
         per_bank="HAYIR", cells="— (seri kodu doğrulanmadı)", status="UNVERIFIED", note="API anahtarı sağlanmadı; seri kodları serieList uç noktasından doğrulanıp kaydedilecek."),
    # ---- Tüm dosyalar işlendikten sonra bulunan veri kalitesi farkları (DQ01 vb.) — 28.10.2026, tam yeniden işleme
    dict(field="ÖLÇEK (DQ01): banka kitapları Bin TL / Milyon TL", source="TBB", dataset="tbb_fs_solo_excel, tbb_fs_cons_excel",
         file="/sites/default/files/raporlar/54947/… (Haziran 2026) ve /raporlar/54871/… (Mart 2026) <Banka>.zip", period="2026-03 vs 2026-06",
         per_bank="EVET", cells="'varlıklar' satır 3: Haziran 2026 'MİLYON TÜRK LİRASI'; Mart 2026 'BİN TÜRK LİRASI' (Akbank: Varlıklar Toplamı ham 3.727.680 vs 3.419.802.978)",
         status="VERIFIED", note="Aynı veri setinde ölçek dönemden döneme DEĞİŞİYOR. Ölçek artık her kitabın başlığından okunur; bulunamazsa gözlem UNVERIFIED (DQ01_scale_not_found). "
                                "Mart 2026 ve 31/12/2025 değerleri ilk çalıştırmada 1000× büyük yazılmıştı; DB ham dosyalardan yeniden üretildi ve DT20 ile birebir doğrulandı (Akbank 3.419.802.978 Bin TL = 3.419.802,978 Mn TL)."),
    dict(field="DT20/DT21 'Diğer' sütunları ≠ bilanço 'Diğer' satırları", source="TBB", dataset="tbb_dt20_selected_solo, tbb_dt21_selected_cons", file=DT20, period="2026-03, 2026-06", per_bank="EVET",
         cells="2.Aktifler 'Diğer Aktifler' (Akbank 101.251) vs kitap 'X. DİĞER AKTİFLER (Net)' 100.606; 3.Pasifler 'Diğer Pasifler / Toplam' 365.531 vs kitap 'XV. DİĞER YÜKÜMLÜLÜKLER' 153.923; "
               "4.Gelir-Gider 'Diğer Faiz Gelirleri' 34.443 (= Toplam − krediler − bankalar − menkul) vs kitap '1.7 Diğer Faiz Gelirleri' 1.004; 'Diğer Faiz Gider.' 34.835 vs '2.6' 82",
         status="VERIFIED", note="Farklı tanımlar ayrı kodlarda tutulur: other_assets_dt20, other_liabilities_group_dt20, other_interest_income_residual_dt20, other_interest_expense_residual_dt20. Birleştirilmez."),
    dict(field="Konsolide özkaynak: DT21 'Özkaynaklar / Toplam' azınlık paylarını içermez", source="TBB", dataset="tbb_dt21_selected_cons", file="DT21 3.Pasifler.xls 'Yükümlülükler' vs konsolide kitap 'Kyüküm.'",
         period="2026-06", per_bank="EVET", cells="İş Bankası: DT21 454.045; kitap XVI. ÖZKAYNAKLAR 540.585 = 453.… + 16.7 Azınlık Payları 86.540",
         status="VERIFIED", note="DT21 değeri total_equity_parent (ana ortaklığa ait), kitap XVI satırı total_equity, 16.7 satırı minority_interests olarak ayrı saklanır."),
    dict(field="Mevduat vade kümeleri (basis)", source="TBB", dataset="tbb_dt20_selected_solo + tbb_fs_solo_excel", file="DT20 3.Pasifler 'Mevd.Vade' vs kitap 'pasif1' 2.a.1.i", period="2026-06", per_bank="EVET",
         cells="DT20: Vadesiz+7 Gün | 1 Aya Kadar | 1-3 Ay | 3 Ay+ | Toplam (basis=contractual_coarse); kitap: Vadesiz | 7 Gün İhbarlı | 1 Aya Kadar | 1-3 Ay | 3-6 Ay | 6 Ay-1 Yıl | 1 Yıl ve Üstü | Birikimli | Toplam (basis=contractual). "
               "DT20 'Döviz Tevdiat Hesabı / Toplam' (Akbank 408.323) tür toplamıdır, alt grup (yurtdışı yerleşik) değil",
         status="VERIFIED", note="İki kova kümesi aynı kalem için AYRI temel olarak saklanır ve UI'da seçilerek gösterilir; birleştirilmez, 3 ay+ bölünmez. Yurtiçi 379.183 + yurtdışı 29.140 = 408.323 doğrulandı."),
    dict(field="Kaynaklar arası fark (source_conflict bayrağı)", source="TBB", dataset="DT20/DT21 ↔ banka kitapları", file="—", period="2026-03, 2026-06", per_bank="EVET",
         cells="Aynı tanım/dönem için farklı değer: 'Likidite Riski' Toplam Yükümlülükler vade kovaları (14 banka, ör. Aktif Yatırım vadesiz 29.516 vs kitap dipnotu 47.852); "
               "gelir tablosu bazı kalemler (mevduata verilen faiz 15 banka, temettü 15, diğer karşılık 22, BZK gideri 13)",
         status="VERIFIED", note="İki değer de saklanır; bankanın kendi tablosu (birincil) en son işlendiği için öne çıkar, önceki değer revizyon geçmişinde kalır; UI'da ⚑ ile işaretlenir. %0,01 içindeki farklar (Bin/Milyon yuvarlaması) fark sayılmaz."),
    dict(field="Şifreli Excel (Excel varsayılan parolası)", source="TBB", dataset="tbb_fs_cons_excel", file="/raporlar/54883/bankalar/Fibabanka A.Ş..zip (Mart 2026 konsolide)", period="2026-03", per_bank="EVET",
         cells="Fibabanka A.Ş..xls: BIFF FILEPASS kaydı; Excel'in varsayılan parolası ('VelvetSweatshop') ile saydam açılır (Excel de parola sormaz)",
         status="VERIFIED", note="Yalnızca varsayılan parola denenir; başka parola denemesi yapılmaz. Dosya başına hata işi düşürmez: ayrıştırılamayan dosya ERROR olarak kaydedilir, diğerleri devam eder."),
]

QUESTIONS: list[tuple[str, str]] = [
    ("1. Haziran 2026'da banka bazında kredi tutarları mevcut mu?", "EVET — DT20 2.Aktifler.xls 'Varlıklar / Krediler' (58 banka) ve her bankanın kendi kitabında TP/YP ayrımıyla (varlıklar 2.1.Krediler). VERIFIED."),
    ("2. Haziran 2026'da banka bazında mevduat tutarları mevcut mu?", "EVET — DT20 3.Pasifler.xls 'Yükümlülükler / Mevduat' (58 banka) ve banka kitabında TP/YP ile (yüküm. I. MEVDUAT). VERIFIED."),
    ("3. Kredi ve mevduatın ≤12 ay kalan vade dağılımları ayrı ayrı mevcut mu?",
     "EVET — banka kitabı 'malibünye1' kalan vade bloğunda 'Verilen Krediler' ve 'Diğer Mevduat' satırları (Vadesiz | 1 Aya Kadar | 1-3 Ay | 3-12 Ay | …). Krediler için 3-12 ay tek kova (3-6 / 6-12 yok). "
     "Mevduat için ayrıca 'pasif1' sözleşmesel vade yapısı 3-6 Ay ve 6 Ay-1 Yıl kovalarını mevduat türü bazında verir. DT20 'Mevd.Vade' tüm bankalar için 3 ay+ tek kova."),
    ("4. TL kredi ortalama faizi banka bazında mevcut mu?", "EVET — DT20 'Ort.Faiz Oranı' TL / Verilen Krediler (58 banka; Ziraat 42,04; Akbank 42,13; sektör 43,12). VERIFIED."),
    ("5. TL mevduat ortalama faizi banka bazında mevcut mu?", "EVET — aynı tablo TL / Mevduat** (bankalararası hariç; Ziraat 38,85; Akbank 41,10; sektör 37,62). VERIFIED."),
    ("6. USD ve EUR faizleri banka bazında mevcut mu?", "EVET — aynı tabloda USD ve EURO sütunları; banka kitabında ayrıca Yen. VERIFIED."),
    ("7. Faiz verilerinin gerçek tanımı nedir?",
     "'Parasal Finansal Araçlara Uygulanan Ortalama Faiz Oranları' (faiz oranı riski dipnotu): dönem sonu STOK ortalama uygulanan oran; mevduat bankalararası hariç. Yeni açılış faizi ve muhasebesel getiri/maliyet değildir; makas yalnızca bu tanım içinde."),
    ("8. Tarihsel veri hangi dönemlere kadar uzanıyor?", "DT20/DT21 (Seçilmiş Tablolar): 2005→; Finansal Tablolar Excel veri seti: 2002→ (Mart/Haziran/Eylül/Aralık); Kalan vade: 2002→; sıralama: 1995→ (kategori sayfası yıl listeleri)."),
    ("9. Dosyalar kullanıcı müdahalesi olmadan indirilebiliyor mu?", "EVET — düz HTTP GET; oturum/CAPTCHA yok; robots.txt Drupal varsayılanı bu yolları yasaklamıyor. GitHub Actions runner'da iki koşuda doğrulandı."),
    ("11. Dönemler arası ölçek tutarlı mı (DQ01)?",
     "HAYIR — aynı TBB Excel veri setinde Mart 2026 kitapları Bin TL, Haziran 2026 kitapları Milyon TL. Ölçek her kitabın başlık satırından okunur; DT20 sayfaları 'Milyon TL' yazar. "
     "Dönemler arası karşılaştırma yalnızca normalize (TL) değerlerle yapılır; ham değerler kaynaktaki ölçekle birlikte saklanır (value_raw + source_scale)."),
    ("10. Aynı işlem sonraki dönemlerde otomatik tekrarlanabiliyor mu?",
     "EVET — kategori sayfası select'lerinden (rapor_donemi id + ay-yil rapor URL'si) → rapor sayfası → ekler / banka zip'leri; TBBAdapter.discover() bunu uygular, ingest.yml her gün vadesi gelen çeyrekleri kontrol eder."),
]


def render_markdown() -> str:
    lines = ["# Doğrulama Tablosu — TBB / BDDK banka bazında veri keşfi (28.10.2026, gerçek dosyalar açıldı)", "",
             "Durumlar: VERIFIED (dosya açıldı, alan+dönem görüldü) · UNVERIFIED (kaynak bulundu, içerik açılamadı) · "
             "UNAVAILABLE (o kaynak/dönemde alan yok) · ERROR (teknik hata). Birbirinin yerine kullanılmaz.", "",
             "| " + " | ".join(COLUMNS) + " |", "|" + "---|" * len(COLUMNS)]
    for f in FINDINGS:
        row = [f["field"], f["source"], f["file"], f["period"], f["per_bank"], f["cells"], f["status"], f["note"]]
        lines.append("| " + " | ".join(str(x).replace("|", "\\|") for x in row) + " |")
    lines += ["", "## Öncelikli araştırma sorularının cevapları", ""]
    for q, a in QUESTIONS:
        lines += [f"**{q}**", "", a, ""]
    return "\n".join(lines)
