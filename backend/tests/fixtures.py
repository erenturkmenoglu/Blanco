"""Sentetik test dosyaları — gerçek TBB dosyalarının DOĞRULANMIŞ başlık/düzenine göre kurgulanmıştır (dosyanın kendisi değildir)."""
from __future__ import annotations

import io

from openpyxl import Workbook


def interest_table_rows():
    # DT20 Haziran 2023'te okunan gerçek değerler (ilk beş banka)
    return [
        ["Verilen Kredilere ve Diğer Mevduata Uygulanan Ortalama Faiz Oranları*, %", None, None, None, None, None, None],
        ["Haziran 2023", None, None, None, None, None, None],
        [None, "TL", None, "USD", None, "EURO", None],
        ["Banka", "Verilen Krediler", "Mevduat**", "Verilen Krediler", "Mevduat**", "Verilen Krediler", "Mevduat**"],
        ["Sektör", 17.5, 24.0, 9.1, 2.2, 6.9, 1.0],
        ["Kamusal Sermayeli Mevduat Bankaları", 14.1, 24.3, 8.9, 2.6, 6.7, 1.5],
        ["T.C. Ziraat Bankası A.Ş.", 12.07, 21.40, 8.64, 3.26, 7.22, 0.77],
        ["Türkiye Halk Bankası A.Ş.", 14.53, 22.07, 8.50, 2.78, 5.56, 1.87],
        ["Türkiye Vakıflar Bankası T.A.O.", 15.90, 29.96, 9.51, 1.83, 7.24, 1.77],
        ["Akbank T.A.Ş.", 20.98, 22.24, 10.25, 1.46, 7.10, 0.26],
        ["Anadolubank A.Ş.", 13.59, 23.75, 8.34, 3.05, 8.86, 2.65],
        ["(*) Faiz oranı riski amaçlı hazırlanan parasal finansal araçlara uygulanan ortalama faiz oranlarından derlenmiştir.", None, None, None, None, None, None],
    ]


def maturity_table_rows():
    return [
        ["Aktif ve Pasif Kalemlerin Kalan Vadelerine Göre Gösterimi, Milyon TL", None, None, None, None, None, None, None, None],
        ["Toplam Aktifler", None, None, None, None, None, None, None, None],
        ["Banka", "Vadesiz", "1 Ay", "1-3 Ay", "3-12 Ay", "1-5 Yıl", "5 Yıl ve Üzeri", "Dağıtılamayan", "Toplam"],
        ["Sektör", 1000, 2000, 1500, 2500, 3000, 1000, 500, 11500],
        ["T.C. Ziraat Bankası A.Ş.", 100, 200, 150, 250, 300, 100, 50, 1150],
        ["Akbank T.A.Ş.", 50, 120, 80, 150, 200, 60, 20, 680],
        [None, None, None, None, None, None, None, None, None],
        ["Toplam Pasifler", None, None, None, None, None, None, None, None],
        ["Banka", "Vadesiz", "1 Ay", "1-3 Ay", "3-12 Ay", "1-5 Yıl", "5 Yıl ve Üzeri", "Dağıtılamayan", "Toplam"],
        ["T.C. Ziraat Bankası A.Ş.", 300, 400, 150, 100, 100, 20, 80, 1150],
        ["Akbank T.A.Ş.", 200, 250, 90, 60, 50, 10, 20, 680],
    ]


def balance_sheet_rows():
    # (A) düzeni: satırlar kalemler, sütunlar bankalar — "Bin TL" ölçeği başlıkta
    return [
        ["Bilanço (Solo), Eylül 2025, Bin TL", None, None, None],
        ["Kalemler", "T.C. Ziraat Bankası A.Ş.", "Akbank T.A.Ş.", "Türkiye İş Bankası A.Ş."],
        ["Nakit Değerler ve Merkez Bankası", "100.000", "60.000", "70.000"],
        ["Krediler", "700.000", "400.000", "500.000"],
        ["Toplam Aktifler", "1.000.000", "600.000", "750.000"],
        ["Mevduat", "650.000", "380.000", "470.000"],
        ["Özkaynaklar", "100.000", "70.000", "80.000"],
        ["Toplam Pasifler", "1.000.000", "600.000", "750.000"],
        ["Şüpheli Bir Kalem", "1", "2", "3"],
    ]


def income_rows():
    return [
        ["Gelir Tablosu (Solo), Eylül 2025 (1 Ocak - 30 Eylül), Bin TL", None, None],
        ["Kalemler", "T.C. Ziraat Bankası A.Ş.", "Akbank T.A.Ş."],
        ["Faiz Gelirleri", "120.000", "80.000"],
        ["Faiz Giderleri", "90.000", "50.000"],
        ["Net Faiz Geliri", "30.000", "30.000"],
        ["Net Ücret ve Komisyon Gelirleri", "8.000", "9.000"],
        ["Diğer Faaliyet Giderleri", "15.000", "12.000"],
        ["Dönem Net Kârı", "12.000", "15.000"],
    ]


def build_xlsx(sheets: dict[str, list[list]]) -> bytes:
    wb = Workbook()
    wb.remove(wb.active)
    for name, rows in sheets.items():
        ws = wb.create_sheet(name)
        for r in rows:
            ws.append(r)
    bio = io.BytesIO()
    wb.save(bio)
    return bio.getvalue()


CATEGORY_HTML = """<html><body>
<h2>Finansal Tablolar - Konsolide Olmayan (Solo Banka, Excel formatında ortak veri seti)</h2>
<select class="lh-30 rapor-donemi-secimi" data-cat="11241"><option value="">Rapor Dönemi Seçiniz</option>
<option value="/istatistiki-raporlar-liste/11241?rapor_donemi=11411">2026</option><option value="/istatistiki-raporlar-liste/11241?rapor_donemi=11405">2025</option>
<option value="/istatistiki-raporlar-liste/11241?rapor_donemi=11279">2024</option></select>
<select class="rapor-donemi-ay-yil ay-yil-11241"><option value="/istatistiki-raporlar/2026-mart-finansal-tablolar-konsolide-olmayan-solo-banka-excel-formatinda">Mart</option>
<option value="/istatistiki-raporlar/2026-haziran-finansal-tablolar-konsolide-olmayan-solo-banka-excel-formatinda">Haziran</option></select>
<h2>Aktif Büyüklüklerine Göre Banka Sıralaması</h2>
<select class="rapor-donemi-secimi" data-cat="11254"><option value="/istatistiki-raporlar-liste/11254?rapor_donemi=11411">2026</option><option value="/istatistiki-raporlar-liste/11254?rapor_donemi=11405">2025</option></select>
<select class="rapor-donemi-ay-yil ay-yil-11254"><option value="/istatistiki-raporlar/2026-mart-aktif-buyukluklerine-gore-banka-siralamasi">Mart</option><option value="/istatistiki-raporlar/2026-haziran-aktif-buyukluklerine-gore-banka-siralamasi">Haziran</option></select>
</body></html>"""

LIST_HTML = """<html><body><ul>
<li><a href="/istatistiki-raporlar/2025-eylul-finansal-tablolar-konsolide-olmayan-solo-banka-excel-formatinda">2025 Eylül - Finansal Tablolar - Konsolide Olmayan (Solo Banka, Excel formatında ortak veri seti)</a></li>
<li><a href="/istatistiki-raporlar/2025-haziran-finansal-tablolar-konsolide-olmayan-solo-banka-excel-formatinda">2025 Haziran - ...</a></li>
</ul></body></html>"""

REPORT_HTML = """<html><body>
<a href="/download/node/55001/field_raporlar_ekler/310500" title="Finansal Tablolar Solo Haziran 2026.xlsx">Finansal Tablolar Solo Haziran 2026</a>
<a href="/sites/default/files/docs/tbb_istatistikleri_yayinlama_takvimi.pdf">İstatistiki Rapor Yayınlama Takvimi</a>
</body></html>"""
