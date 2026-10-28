from datetime import date

from app.acquisition.downloader import DownloadResult
from app.acquisition.sources.tbb import LIST_URL, TBBAdapter, quarter_end
from tests.fixtures import CATEGORY_HTML, LIST_HTML, REPORT_HTML


def test_parse_period_options_reads_year_ids_not_guesses():
    forms = TBBAdapter.parse_period_options(CATEGORY_HTML)
    fs = next(v for k, v in forms.items() if "Excel" in (k or ""))
    assert fs["years"]["2026"] == "11411" and fs["years"]["2024"] == "11279" and fs["list_id"] == 11241
    assert fs["latest_year"] == "2026" and fs["latest_pages"]["Haziran"].endswith("2026-haziran-finansal-tablolar-konsolide-olmayan-solo-banka-excel-formatinda")


def test_parse_report_links_and_attachments():
    links = TBBAdapter.parse_report_links(LIST_HTML)
    assert links[0]["type"] == "report_page" and links[0]["url"].endswith("2026-haziran-finansal-tablolar-konsolide-olmayan-solo-banka-excel-formatinda")
    atts = TBBAdapter.parse_attachments(REPORT_HTML)
    assert atts[0]["url"] == "https://www.tbb.org.tr/download/node/55001/field_raporlar_ekler/310500" and atts[0]["format_hint"] == "xlsx"
    assert all("/docs/" not in a["url"] for a in atts)       # takvim PDF'i (site geneli) rapor eki sayılmaz


class FakeDownloader:
    """Canlı ağ yok: sayfalar sabit; indirme kayıtları loglanır."""

    def __init__(self):
        self.calls = []

    def fetch(self, url, dataset_code="misc", expected=None, allow_browser=False):
        self.calls.append(url)
        pages = {
            "https://www.tbb.org.tr/istatistiki-raporlar/11232": CATEGORY_HTML,
            LIST_URL.format(list_id=11241, period_id="11411", month=6): LIST_HTML,
            "https://www.tbb.org.tr/istatistiki-raporlar/2026-haziran-finansal-tablolar-konsolide-olmayan-solo-banka-excel-formatinda": REPORT_HTML,
        }
        if url in pages:
            data = pages[url].encode()
            return DownloadResult(url, url, True, data, "html", "text/html", None, "x", len(data), None)
        return DownloadResult(url, None, False, None, None, None, None, None, None, None, error="not found (fake)")


def test_discover_chain_offline():
    ad = TBBAdapter(FakeDownloader())
    files = ad.discover("tbb_fs_solo_excel", 2026, 6)
    assert [f.url for f in files] == ["https://www.tbb.org.tr/download/node/55001/field_raporlar_ekler/310500"]
    assert files[0].period_end == date(2026, 6, 30) and files[0].format_hint == "xlsx"
    # Aralık 2025 için period id yok → bağlantı bulunamaz, hata fırlatmaz
    assert ad.discover("tbb_fs_solo_excel", 2019, 12) == []


def test_known_static_files_included():
    ad = TBBAdapter(FakeDownloader())
    files = ad.discover("tbb_dt13_bank_branch_employee", 2026, 6)
    assert any("54910" in f.url for f in files)
    assert quarter_end(2026, 6) == date(2026, 6, 30)


SELECTOR_HTML = """<html><body><h1>2026 Haziran - Finansal Tablolar - Konsolide Olmayan (Solo Banka, Excel formatında ortak veri seti)</h1>
<form action="/istatistiki-raporlar/2026-haziran-finansal-tablolar-konsolide-olmayan-solo-banka-excel-formatinda" method="get">
<select name="banka"><option value="">Banka Seçiniz</option><option value="55101">Akbank T.A.Ş.</option><option value="55102">Aktif Yatırım Bankası A.Ş.</option>
<option value="55103">Alternatifbank A.Ş.</option><option value="55104">Anadolubank A.Ş.</option><option value="55105">Bank Mellat</option>
<option value="55106">Türkiye Cumhuriyeti Ziraat Bankası A.Ş.</option></select></form></body></html>"""


def test_bank_selector_parse_and_form_get_resolution():
    info = TBBAdapter.parse_bank_selector(SELECTOR_HTML)
    assert len(info["options"]) == 6 and info["select_name"] == "banka" and info["form_method"] == "get"
    ad = TBBAdapter(FakeDownloader())
    files = ad.resolve_bank_files(SELECTOR_HTML, "https://www.tbb.org.tr/x", "tbb_fs_solo_excel", date(2026, 6, 30))
    zi = next(f for f in files if f.bank_raw.startswith("Türkiye Cumhuriyeti Ziraat"))
    assert zi.strategy == "form_get" and zi.url.endswith("?banka=55106")
