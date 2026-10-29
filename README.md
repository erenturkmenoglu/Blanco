# DBTR — Deutsche Bank A.Ş. (solo) finansal veri tabanı ve analiz paneli

Eski "Bilanço/Blanco" çok-banka platformu iptal edildi; aynı repo tek bankaya (Deutsche Bank A.Ş., konsolide olmayan)
odaklanan, kamuya açık bildirimlerden kurulan bir veri tabanı + statik web paneline dönüştürüldü.

## Veri kaynakları
- `data/kap/` — KAP "Banka Finansal Rapor" bildirimleri (2021Ç3–2026Ç2, 20 PDF): bilanço, nazım, K/Z, kapsamlı gelir, nakit akış, özkaynak değişim. Her bildirimin "Önceki Dönem" kolonu da alınır → seri 3Ç2020'ye uzanır.
- `data/tbb/` — TBB Ortak Veri Gönderim Seti banka kitapları (31.03.2026 Bin TL, 30.06.2026 Milyon TL): SYR, LKO, NSFR, ortalama faizler, kalan vade, yeniden fiyatlama, mevduat vade yapısı, donuk alacak; DT13 şube/çalışan.
- Kurlar: TCMB döviz alış, dönem sonunda geçerli bülten (`pipeline/export_json.py` içinde kaynaklı tablo).

## Pipeline (`pipeline/`)
```
python parse_kap.py data/kap kap_long.pkl   # PDF tablo ayrıştırma (pdfplumber, çizgi tabanlı), hiyerarşi girintiden
python build_db.py                          # normalizasyon (mn TL), tercih edilen gözlem, tutarlılık ve restatement kontrolleri
python build_xlsx.py && python build_analysis.py   # DBTR_KAP_DB.xlsx: DB + SUMIFS geniş tablolar + Blanco kalemleri/oranlar/grafikler
python parse_tbb.py                         # TBB kitapları → dipnot.pkl
python export_json.py                       # → frontend/public/data/dbtr.json (Excel'in hesaplanmış değerlerinden)
```
Excel'deki formüller LibreOffice ile yeniden hesaplanır; JSON hesaplanmış değerlerden üretilir, böylece Excel ve web aynı sayıları gösterir.

## Web (`frontend/`, Next.js 14, statik export)
Sekmeler: Genel Bakış · Bilanço · Gelir Tablosu · Nazım & Türev · Oranlar · Dipnotlar · Tablolar · Veri & Kalite. Sağ üstte TL/USD/EUR seçimi
(stok: dönem sonu kuru; çeyrek akım: dönem ortalama kuru). Vercel: Root Directory `frontend`, ortam değişkeni gerekmez.

## İlkeler
Eksik veri uydurulmaz (boş hücre / UNAVAILABLE); her kalemde VERIFIED / DERIVED / UNAVAILABLE durumu ve kaynak; tüm tutarlar nominal (TMS 29 uygulanmamış).
