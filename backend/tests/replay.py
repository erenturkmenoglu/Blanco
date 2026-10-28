"""Gerçek TBB sayfalarını/dosyalarını (tests/data/tbb_2026_06) adreslerine göre çevrimdışı servis eden indirici — uçtan uca gerçek veri testi."""
from __future__ import annotations

import hashlib
from pathlib import Path

from app.acquisition.downloader import DownloadResult, sniff_format

DATA = Path(__file__).resolve().parent / "data" / "tbb_2026_06"
B = "https://www.tbb.org.tr"
URL_MAP = {
    f"{B}/istatistiki-raporlar/11232": "11232.html", f"{B}/istatistiki-raporlar/11236": "11236.html", f"{B}/istatistiki-raporlar/11237": "11237.html",
    f"{B}/istatistiki-raporlar/2026-haziran-finansal-tablolar-konsolide-olmayan-solo-banka-excel-formatinda": "2026-haziran-finansal-tablolar-konsolide-olmayan-solo-banka-excel-formatinda.html",
    f"{B}/istatistiki-raporlar/2026-haziran-banka-bilgileri-secilmis-tablolar-konsolide-olmayansolo-banka": "2026-haziran-banka-bilgileri-secilmis-tablolar-konsolide-olmayansolo-banka.html",
    f"{B}/istatistiki-raporlar/2026-haziran-aktif-ve-pasiflerin-kalan-vadelerine-gore-gosterimi": "2026-haziran-aktif-ve-pasiflerin-kalan-vadelerine-gore-gosterimi.html",
    f"{B}/istatistiki-raporlar/2026-haziran-aktif-buyukluklerine-gore-banka-siralamasi": "2026-haziran-aktif-buyukluklerine-gore-banka-siralamasi.html",
    f"{B}/istatistiki-raporlar/2026-haziran-banka-calisan-ve-sube-bilgileri": "2026-haziran-banka-calisan-ve-sube-bilgileri.html",
    f"{B}/download/node/54932/field_raporlar_ekler/310643": "dt20_1_mali_bunye.xls", f"{B}/download/node/54932/field_raporlar_ekler/310157": "dt20_2_aktifler.xls",
    f"{B}/download/node/54932/field_raporlar_ekler/310158": "dt20_3_pasifler.xls", f"{B}/download/node/54932/field_raporlar_ekler/310159": "dt20_4_gelir_gider.xls",
    f"{B}/download/node/54932/field_raporlar_ekler/310160": "dt20_5_nazim.xls", f"{B}/download/node/54932/field_raporlar_ekler/310161": "dt20_aciklamalar.xls",
    f"{B}/download/node/54933/field_raporlar_ekler/310162": "kalan_vade_sektor.xls", f"{B}/download/node/54929/field_raporlar_ekler/310010": "aktif_buyukluk_siralamasi.xls",
    f"{B}/download/node/54910/field_raporlar_ekler/309903": "dt13_banka_calisan_sube.pdf",
    f"{B}/download/node/54910/field_raporlar_ekler/309905": "dt13_banka_calisan_sube.xlsx",
    f"{B}/sites/default/files/raporlar/54947/bankalar/Akbank%20T.A.%C5%9E..zip": "fs_solo_akbank.zip",
    f"{B}/sites/default/files/raporlar/54947/bankalar/T%C3%BCrkiye%20Cumhuriyeti%20Ziraat%20Bankas%C4%B1%20A.%C5%9E..zip": "fs_solo_ziraat.zip",
}


class ReplayDownloader:
    def __init__(self):
        self.calls: list[str] = []

    def fetch(self, url, dataset_code="misc", expected=None, allow_browser=False):
        self.calls.append(url)
        fn = URL_MAP.get(url)
        if not fn:
            return DownloadResult(url, None, False, None, None, None, None, None, None, None, error="replay: adres kayıtlı değil (çevrimdışı)")
        data = (DATA / fn).read_bytes()
        fmt = sniff_format(data, fn)
        return DownloadResult(url, url, True, data, fmt, None, fn, hashlib.sha256(data).hexdigest(), len(data), str(DATA / fn))
