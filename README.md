# Bilanço — otomatik finansal analiz platformu (Bankalar modülü, v0.1)

Kamuya açık resmî kaynaklardan (TBB, BDDK, TCMB/EVDS) banka bazında finansal veriyi **otomatik toplayan, içerik imzasından
biçimini tespit edip ayrıştıran, veri sözlüğüne eşleyen, 14 kalite kontrolünden geçiren, ham+normalize+revizyonlu saklayan ve
analiz üreten** platformun ilk çalışan sürümü. Diğer sektörler için ortak altyapı (sectors / institutions / memberships) hazırdır;
yalnızca `banks` modülü etkindir.

## Durum — neyin gerçekten çalıştığı, neyin çalışmadığı (28.10.2026)

| Bileşen | Durum |
|---|---|
| Veri keşfi (TBB/BDDK/EVDS kaynak yapısı, gerçek URL kalıpları, dönem id'leri, yayın takvimi) | **Yapıldı** — resmî sayfalar/dosyalar okunarak; bulgular `docs/verification_table.md` |
| TBB DT20 Haziran 2023: banka bazında TL/USD/EUR kredi & mevduat ortalama faizleri ve kalan vade tablosu | **VERIFIED** (dosya açıldı, sütunlar görüldü) |
| TBB DT13 Haziran 2026: banka bazında şube ve çalışan sayıları | **VERIFIED** |
| Haziran 2026 banka bazında bilanço/kredi/mevduat Excel dosyaları | **UNVERIFIED** — kaynak ve dönem bulundu; Excel veri seti **banka bazında ayrı dosyalar** halinde ('Banka Seçiniz', 57 banka); dosya **bu ortamdan indirilemedi** (sandbox ağ engeli) → GitHub Actions probe ile açılacak |
| Veri toplama motoru (fallback zincirli indirme, robots.txt saygısı, içerik imzası, xls/xlsx/csv/html/zip/json/xml ayrıştırma, banka adı standardizasyonu, etiket→metrik eşleme, DT20 faiz & vade tablosu eşleyicileri, 14 DQ kontrolü, revizyon yönetimi) | **Yazıldı ve test edildi** (21 pytest; gerçek TBB dosyası yerine *doğrulanmış düzenin sentetik replikası*) |
| PostgreSQL şeması (16 tablo) + SQLAlchemy modelleri | **Yazıldı**; SQLite ile çalıştırıldı, PostgreSQL docker-compose ile |
| Hesaplama motoru (ROA/ROE/NIM/CIR, NPL, büyüme, YTD→çeyrek, yıllıklandırma, vade payları, faiz makası tanım kontrolü) | **Yazıldı ve test edildi** |
| Analytics API (FastAPI, 14 uç nokta) | **Çalıştırıldı** (uvicorn smoke test + TestClient) |
| Bankalar arayüzü (Next.js: Genel Bakış, Bankalar, Karşılaştırmalar, Veri Kaynakları, Veri Güncelleme Durumu) | **Derlendi** (`next build` başarılı); canlı veriyle görsel test yapılmadı |
| Zamanlayıcı (APScheduler; yayın takvimine göre +45/+75 gün kontrol) | **Yazıldı**, üretimde **kurulmadı/çalışmıyor** |
| EVDS makro katmanı | Adaptör yazıldı; **API anahtarı yok → seri kodları doğrulanmadı** |

Gerçekleştirilmeyen hiçbir şey yapılmış gibi gösterilmemiştir: indirilemeyen dosya `ERROR`, açılmayan dosyanın alanları `UNVERIFIED`,
kaynakta olmayan alan `UNAVAILABLE` olarak kayıtlıdır (`backend/app/verification_findings.py`).

## Hızlı başlangıç

```bash
cp .env.example .env                      # EVDS_API_KEY'i buraya (git'e girmez)
docker compose up --build                 # db + api (8000) + scheduler + web (3000)
# veya yerel:
cd backend && pip install -r requirements.txt && python -m app.cli init-db
uvicorn app.main:app --reload             # http://localhost:8000/docs
python -m app.cli discover --dataset tbb_fs_solo_excel --year 2026 --month 6   # gerçek bağlantıları bul
python -m app.cli ingest   --dataset tbb_fs_solo_excel --year 2026 --month 6   # indir → ayrıştır → doğrula → kaydet
python -m app.cli verification-table --out ../docs/verification_table.md
pytest -q                                 # 21 test
cd ../frontend && npm install && npm run dev                                   # http://localhost:3000
```

İlk gerçek çalıştırmada (ağı olan bir makinede) sırasıyla: `tbb_dt13_bank_branch_employee`, `tbb_asset_ranking`, `tbb_fs_solo_excel`,
`tbb_dt20_selected_solo`, `tbb_maturity_remaining` için `ingest` çalıştırın; `Veri Güncelleme Durumu` ekranı her denemenin yöntem/adres/neden
kaydını gösterir. Gerçek Excel düzeni sentetik replikadan farklıysa eşleyici `unmapped_labels` listesini loglar — eşleme yalnızca tek metrikle
örtüşen etiketlerde yapılır, tahmin edilmez.

## Yapı

```
backend/app
  acquisition/   downloader.py (httpx→requests→[playwright], robots, içerik imzası, ham saklama)  parsers.py  sources/{tbb,bddk,evds}.py
  normalization/ bank_names.py (TBB üyesi tohum listesi + alias/fuzzy)  periods.py  mapping.py (etiket→metrik)  special_tables.py (DT20 faiz & vade)
  validation/    checks.py (DQ01–DQ14 + satır düzeyi filtre)
  calc/          engine.py (saf fonksiyonlar; yöntem + sınırlama metni)
  db/            models.py (institutions, sectors, datasets, dataset_fields, *_observations, derived_metrics, jobs, quality, documents, revisions)
  api/routes.py  main.py  scheduler/jobs.py  pipeline.py  cli.py  verification_findings.py  dictionary.py
docs/            data_dictionary.yaml (tek kaynak)  verification_table.md  sources.md  domain.md
frontend/        Next.js 14 (app router) — API'yi tüketir; her grafik altında dönem/birim/kaynak/güncelleme/yöntem
```

## Kritik kaynak bulguları (özet)

* **Banka bazında faiz**: TBB "Banka Bazında Seçilmiş Tablolar" (DT20 solo / DT21 konsolide, üç aylık) → *Verilen Kredilere ve Diğer Mevduata
  Uygulanan Ortalama Faiz Oranları, %* : TL/USD/EURO × (Verilen Krediler | Mevduat). Tanım: faiz oranı riski dipnotundaki **stok ortalama uygulanan
  oran** (yeni açılış değil, muhasebesel getiri değil); mevduat bankalararası hariç. Makas yalnızca bu tanım içinde hesaplanır.
* **Vade**: aynı raporun *Aktif ve Pasif Kalemlerin Kalan Vadelerine Göre Gösterimi* tablosu **toplam aktif/pasif** verir (Vadesiz / 1 Ay / 1-3 / 3-12 /
  1-5 Yıl / 5+ / Dağıtılamayan). Kredi ve mevduat **ayrı değil**; 3-12 ay **tek kova**. Mevduat ≤12 ay dağılımı için aday: finansal tablo dipnotu
  *Mevduatın vade yapısı* (Veri Sorgulama Sistemi / Excel veri seti) — doğrulanmadı.
* **BDDK**: banka bazında yayın yok (tasarım gereği toplulaştırılmış) → yalnızca sektör/grup karşılaştırma katmanı.
* **TBB Veri Sorgulama Sistemi**: robots.txt otomatik erişimi yasaklıyor → adaptör kullanmaz (izinsiz aşılmaz).
* **Katılım bankaları** TBB kapsamı dışında (TKBB).

## Excel dosyalarını açma yolu — GitHub Actions runner (bu ortamın ağ engeli için)

Geliştirme ortamı dış siteleri DNS/proxy düzeyinde engellediği için gerçek TBB dosyaları **GitHub Actions** üzerinde indirilip envanteri
çıkarılır (`.github/workflows/tbb-probe.yml` → `backend/scripts/tbb_probe.py`): robots.txt, kategori sayfaları (dönem id'leri), rapor sayfaları
('Banka Seçiniz' seçicisi dahil), seçilen bankaların Excel dosyaları, Aktif Büyüklük sıralaması .xls, DT20/kalan vade/DT13 ekleri → `summary.json`
(sayfa adları, başlık satırları, satır etiketleri, hangi etiketlerin veri sözlüğüne eşlendiği) artifact olarak saklanır. Aynı runner
`.github/workflows/ingest.yml` ile her gün 06:30 (İstanbul) yayın takvimine göre vadesi gelen çeyrekleri **otomatik** toplar.

Çalıştırma: `gh workflow run tbb-probe.yml -f year=2026 -f month=6 -f robots_policy=strict` → `gh run download` → `probe_output/summary.md`.

**Karar noktası (robots.txt):** 28.10.2026'da web okuyucu `/download/...` ve rapor sayfaları için `robots_disallowed` döndürdü. Downloader varsayılanı
`ROBOTS_POLICY=strict` (yasaklı yol indirilmez). Yalnızca açıkça yapılandırılmış resmî istatistik dosyalarının 2 sn aralıkla alınması için `lenient`
seçilebilir; bu kullanıcı kararıdır. Probe robots.txt'nin gerçek içeriğini kaydeder.

## Alan adı

Hedef ana makine **bilanco.vercel.app** (ASCII; onaylandı). Ürün adı "Bilanço". IDN not: `bilanço` → Punycode `xn--bilano-0ua`. Ayrıntı: `docs/domain.md`.
