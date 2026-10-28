"""TBB (Türkiye Bankalar Birliği) adaptörü.

Keşif ile DOĞRULANMIŞ site yapısı (28.10.2026, resmî sayfalar/ dosyalar okunarak):
- Kategori sayfası:   https://www.tbb.org.tr/istatistiki-raporlar/<category_id>
      11232 Kamuya Açıklanan Finansal Tablolar   (Finansal Tablolar – Konsolide / Konsolide Olmayan, Excel ortak veri seti; 2002..2026, Mart/Haziran/Eylül/Aralık)
      11236 Bilanço Verilerine Dayalı Analiz ve Raporlar (Banka ve Grup Bilgileri; Banka Bilgileri – Seçilmiş Tablolar DT20/DT21; Grup Bilgileri)
      11237 Seçilmiş İstatistikler (Aktif Büyüklüklerine Göre Banka Sıralaması; Aktif ve Pasiflerin Kalan Vadelerine Göre Gösterimi; Banka, Çalışan ve Şube Bilgileri; ...)
  Her bölümde <select> ile yıl (rapor_donemi = opak taksonomi id'si) ve ay (ay=3/6/9/12) seçilir.
- Rapor listesi:      https://www.tbb.org.tr/istatistiki-raporlar-liste/<list_id>?rapor_donemi=<period_id>&ay=<month>
      örn. 11241 → Finansal Tablolar – Konsolide Olmayan (Solo Banka, Excel ortak veri seti) [2024 Eylül: rapor_donemi=11279&ay=9; 2025 Eylül: 11405&ay=9]
      Excel veri seti rapor sayfası (ör. 2025 Eylül) ek bağlantısı yerine 'Banka Seçiniz' seçicisi (57 banka) sunar → dosya banka bazında,
      bağlantı seçimle oluşur (parse_bank_selector / resolve_bank_files). Seçeneklerin değer/JS yapısı gerçek HTML'den (probe) doğrulanacak.
           11254 → Aktif Büyüklüklerine Göre Banka Sıralaması                                [2026 Haziran: rapor_donemi=11411&ay=6]
- Rapor sayfası:      https://www.tbb.org.tr/istatistiki-raporlar/<yil>-<ay>-<slug>
      ekler:  <a href="/download/node/<nid>/field_raporlar_ekler/<fid>" title="<dosya adı>.xls">
      örn. 2026 Haziran Aktif Büyüklüğüne Göre Banka Sıralaması.xls → /download/node/54929/field_raporlar_ekler/310010
- Statik dosya yolu:  https://www.tbb.org.tr/sites/default/files/raporlar/<nid>/ekler/<dosya>   (örn. DT20 Haziran 2023 PDF)
- İndirme bağlantıları düz HTTP GET'tir; oturum/CAPTCHA gözlenmemiştir (DT13 Haziran 2026 PDF doğrudan okundu).
- robots.txt: web okuyucu aracı 28.10.2026'da /download/... ve /istatistiki-raporlar/... için 'robots_disallowed' döndürdü (muhtemelen
  yapay zekâ botlarına özel kural; genel '*' kuralı bilinmiyor). Downloader politikası ROBOTS_POLICY=strict|lenient ile ayarlanır; probe robots.txt'yi kaydeder.
- Veri Sorgulama Sistemi (verisistemi.tbb.org.tr): robots.txt otomatik erişimi yasaklıyor → bu adaptör onu KULLANMAZ.

period_id (rapor_donemi) tahmin edilmez: kategori sayfasındaki <select> seçeneklerinden yıl→id eşlemesi okunur.
"""
from __future__ import annotations

import logging
import re
from datetime import date
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .base import DatasetSpec, DiscoveredFile, SourceAdapter

log = logging.getLogger("bilanco.tbb")

BASE = "https://www.tbb.org.tr"
CATEGORY_FS = f"{BASE}/istatistiki-raporlar/11232"
CATEGORY_ANALYSIS = f"{BASE}/istatistiki-raporlar/11236"
CATEGORY_SELECTED = f"{BASE}/istatistiki-raporlar/11237"
LIST_URL = BASE + "/istatistiki-raporlar-liste/{list_id}?rapor_donemi={period_id}&ay={month}"

MONTH_TR = {3: "mart", 6: "haziran", 9: "eylul", 12: "aralik"}
MONTH_TR_DISPLAY = {3: "Mart", 6: "Haziran", 9: "Eylül", 12: "Aralık"}

# Bölüm başlığı (kategori sayfasında görülen metin) → list_id; bilinmeyenler None (sayfadan keşfedilir)
SECTIONS: dict[str, dict] = {
    "tbb_fs_solo_excel": {
        "category": CATEGORY_FS, "list_id": 11241,
        "title_match": r"Finansal Tablolar\s*-\s*Konsolide Olmayan.*Excel",
        "slug_match": r"finansal-tablolar-konsolide-olmayan-solo-banka-excel",
    },
    "tbb_fs_cons_excel": {
        "category": CATEGORY_FS, "list_id": None,
        "title_match": r"Finansal Tablolar\s*-\s*Konsolide\s*\(.*Excel",
        "slug_match": r"finansal-tablolar-konsolide-?\(?.*excel",
    },
    "tbb_dt20_selected_solo": {
        "category": CATEGORY_ANALYSIS, "list_id": None,
        "title_match": r"Banka Bilgileri\s*\(Seçilmiş Tablolar, Konsolide Olmayan",
        "slug_match": r"banka-bilgileri-secilmis-tablolar-konsolide-olmayan",
    },
    "tbb_dt21_selected_cons": {
        "category": CATEGORY_ANALYSIS, "list_id": None,
        "title_match": r"Banka Bilgileri\s*\(Seçilmiş Tablolar, Konsolide\(",
        "slug_match": r"banka-bilgileri-secilmis-tablolar-konsolide(?!-olmayan)",
    },
    "tbb_bank_group_quarterly": {
        "category": CATEGORY_ANALYSIS, "list_id": None,
        "title_match": r"Banka ve Grup Bilgileri\s*\(3 Aylık",
        "slug_match": r"banka-ve-grup-bilgileri-3-aylik",
    },
    "tbb_maturity_remaining": {
        "category": CATEGORY_SELECTED, "list_id": None,
        "title_match": r"Aktif ve Pasiflerin Kalan Vadelerine Göre Gösterimi",
        "slug_match": r"aktif-ve-pasiflerin-kalan-vadelerine",
    },
    "tbb_dt13_bank_branch_employee": {
        "category": CATEGORY_SELECTED, "list_id": None,
        "title_match": r"Banka, Çalışan ve Şube Bilgileri",
        "slug_match": r"banka-calisan-ve-sube",
    },
    "tbb_asset_ranking": {
        "category": CATEGORY_SELECTED, "list_id": 11254,
        "title_match": r"Aktif Büyüklüklerine Göre Banka Sıralaması",
        "slug_match": r"aktif-buyukluklerine-gore-banka-siralamasi",
    },
}

# Keşifte doğrudan görülen, yeniden üretilebilir statik bağlantılar (doğrulama tablosunda ayrıca raporlanır)
KNOWN_FILES: list[dict] = [
    {"dataset": "tbb_dt13_bank_branch_employee", "period": "2026-06-30", "fmt": "pdf",
     "url": f"{BASE}/download/node/54910/field_raporlar_ekler/309903",
     "alt": f"{BASE}/sites/default/files/raporlar/54910/ekler/Banka%20%C3%87al%C4%B1%C5%9Fan%20ve%20%C5%9Eube%20Say%C4%B1lar%C4%B1-Haziran%202026.pdf",
     "title": "Banka, Çalışan ve Şube Sayıları Haziran 2026 (DT13)", "verified_content": True},
    {"dataset": "tbb_dt13_bank_branch_employee", "period": "2026-03-31", "fmt": "pdf",
     "url": f"{BASE}/sites/default/files/raporlar/54779/ekler/Banka%20%C3%87al%C4%B1%C5%9Fan%20ve%20%C5%9Eube%20Say%C4%B1lar%C4%B1-Mart%202026.pdf",
     "title": "Banka, Çalışan ve Şube Sayıları Mart 2026 (DT13)", "verified_content": False},
    {"dataset": "tbb_asset_ranking", "period": "2026-06-30", "fmt": "xls",
     "url": f"{BASE}/download/node/54929/field_raporlar_ekler/310010",
     "title": "Aktif Büyüklüğüne Göre Banka Sıralaması.xls (2026 Haziran)", "verified_content": False},
    {"dataset": "tbb_dt20_selected_solo", "period": "2023-06-30", "fmt": "pdf",
     "url": f"{BASE}/sites/default/files/raporlar/51298/ekler/Banka_Bazinda_Secilmis_Tablolar-Haziran_2023_0.pdf",
     "title": "Banka Bazında Seçilmiş Tablolar Haziran 2023 (DT20)", "verified_content": True},
    {"dataset": "tbb_dt21_selected_cons", "period": "2022-06-30", "fmt": "pdf",
     "url": f"{BASE}/download/node/51208/field_raporlar_ekler/278035",
     "title": "Banka Bazında Seçilmiş Konsolide Tablolar Haziran 2022 (DT21)", "verified_content": True},
    {"dataset": "tbb_dt21_selected_cons", "period": "2021-03-31", "fmt": "pdf",
     "url": f"{BASE}/download/node/51088/field_raporlar_ekler/276390",
     "title": "Banka Bazında Seçilmiş Konsolide Tablolar Mart 2021 (DT21)", "verified_content": True},
    {"dataset": "tbb_dt21_selected_cons", "period": "2019-12-31", "fmt": "pdf",
     "url": f"{BASE}/download/node/50926/field_raporlar_ekler/274879",
     "title": "Banka Bazında Seçilmiş Konsolide Tablolar Aralık 2019 (DT21)", "verified_content": True},
    {"dataset": "tbb_dt21_selected_cons", "period": "2022-12-31", "fmt": "pdf",
     "url": f"{BASE}/sites/default/files/raporlar/51259/ekler/Bankasecilmis_12-22-konsolide_0.pdf",
     "title": "Banka Bazında Seçilmiş Konsolide Tablolar Aralık 2022 (DT21)", "verified_content": False},
]


def quarter_end(year: int, month: int) -> date:
    last = {3: 31, 6: 30, 9: 30, 12: 31}[month]
    return date(year, month, last)


class TBBAdapter(SourceAdapter):
    code = "TBB"

    # ---------------------------------------------------------------- veri seti tanımları
    def datasets(self) -> list[DatasetSpec]:
        lag45 = "Mar/Haz/Eyl dönem sonundan itibaren 45 gün; Aralık Nisan sonu (TBB yayın takvimi)"
        return [
            DatasetSpec("tbb_fs_solo_excel", "Finansal Tablolar – Konsolide Olmayan (Solo Banka, Excel ortak veri seti)", "TBB",
                        "quarterly", "solo", True, CATEGORY_FS, LIST_URL.replace("{list_id}", "11241"), "xls,xlsx,zip", 45,
                        "UNVERIFIED", "Dönem listesi 2002–2026 Haziran doğrulandı; Excel eki açılamadı (sunucu hatası / sandbox ağ engeli). " + lag45),
            DatasetSpec("tbb_fs_cons_excel", "Finansal Tablolar – Konsolide (Excel ortak veri seti)", "TBB",
                        "quarterly", "consolidated", True, CATEGORY_FS, None, "xls,xlsx,zip", 75, "UNVERIFIED",
                        "Kategori sayfasında bölüm doğrulandı; list_id ve ek dosya açılmadı."),
            DatasetSpec("tbb_dt20_selected_solo", "Banka Bilgileri – Seçilmiş Tablolar, Konsolide Olmayan (DT20)", "TBB",
                        "quarterly", "solo", True, CATEGORY_ANALYSIS, None, "pdf,xls", 45, "VERIFIED",
                        "Haziran 2023 PDF açıldı: 'Verilen Kredilere ve Diğer Mevduata Uygulanan Ortalama Faiz Oranları' (TL/USD/EUR × kredi/mevduat) ve "
                        "'Aktif ve Pasif Kalemlerin Kalan Vadelerine Göre Gösterimi' (toplam aktif/pasif; kova: vadesiz,1 ay,1-3,3-12 ay,1-5 yıl,5+,dağıtılamayan). "
                        "2026 Haziran sürümü AÇILMADI."),
            DatasetSpec("tbb_dt21_selected_cons", "Banka Bilgileri – Seçilmiş Tablolar, Konsolide (DT21)", "TBB",
                        "quarterly", "consolidated", True, CATEGORY_ANALYSIS, None, "pdf,xls", 75, "VERIFIED",
                        "Aralık 2019, Mart 2021, Haziran 2022 PDF'leri açıldı; tablo yapısı DT20 ile aynı."),
            DatasetSpec("tbb_bank_group_quarterly", "Banka ve Grup Bilgileri (3 Aylık, Son Dönem Karşılaştırmalı Bilanço)", "TBB",
                        "quarterly", "solo", True, CATEGORY_ANALYSIS, None, "xls,pdf", 75, "UNVERIFIED",
                        "Bölüm ve 2025 Haziran sayfası var; ek açılamadı."),
            DatasetSpec("tbb_maturity_remaining", "Aktif ve Pasiflerin Kalan Vadelerine Göre Gösterimi", "TBB",
                        "quarterly", "solo", True, CATEGORY_SELECTED, None, "xls,pdf", 45, "UNVERIFIED",
                        "Seçilmiş İstatistikler sayfasında 2002–2026 (Mart/Haziran) dönem listesi doğrulandı; dosya açılmadı. "
                        "DT20'deki aynı adlı tablo TOPLAM aktif/pasif verir, kredi/mevduat ayrı DEĞİL."),
            DatasetSpec("tbb_dt13_bank_branch_employee", "Banka, Çalışan ve Şube Sayıları (DT13)", "TBB",
                        "quarterly", "na", True, CATEGORY_SELECTED, None, "pdf,xls", 15, "VERIFIED",
                        "Haziran 2026 dosyası açıldı: Tablo 1 banka bazında Şube ve Çalışan Sayısı."),
            DatasetSpec("tbb_asset_ranking", "Aktif Büyüklüklerine Göre Banka Sıralaması", "TBB",
                        "quarterly", "solo", True, CATEGORY_SELECTED, LIST_URL.replace("{list_id}", "11254"), "xls", 45, "UNVERIFIED",
                        "2026 Haziran rapor sayfası ve .xls eki bağlantısı doğrulandı; dosya içeriği açılamadı."),
        ]

    # ---------------------------------------------------------------- HTML çözümleme (saf fonksiyonlar → test edilebilir)
    @staticmethod
    def parse_period_options(html: str) -> dict[str, dict]:
        """Kategori sayfasındaki <select name=rapor_donemi> → {yıl: id}, <select name=ay> → {ay adı: değer}.
        Sayfada birden çok bölüm form'u olabilir; her form için bölüm başlığını da yakalar."""
        soup = BeautifulSoup(html, "lxml")
        out: dict[str, dict] = {}
        for form in soup.find_all("form"):
            years, months = {}, {}
            for sel in form.find_all("select"):
                name = (sel.get("name") or "").lower()
                for opt in sel.find_all("option"):
                    val, txt = opt.get("value"), opt.get_text(strip=True)
                    if not val or not txt:
                        continue
                    if "donem" in name or re.fullmatch(r"(19|20)\d\d", txt):
                        if re.fullmatch(r"(19|20)\d\d", txt):
                            years[txt] = val
                    elif "ay" == name or txt in MONTH_TR_DISPLAY.values() or txt == "Yıllık":
                        months[txt] = val
            title = None
            h = form.find_previous(["h2", "h3", "h4", "strong"])
            if h:
                title = h.get_text(" ", strip=True)
            list_id = None
            m = re.search(r"istatistiki-raporlar-liste/(\d+)", str(form))
            if m:
                list_id = int(m.group(1))
            if years:
                out[title or f"form_{len(out) + 1}"] = {"years": years, "months": months, "list_id": list_id}
        return out

    @staticmethod
    def parse_report_links(html: str, base: str = BASE) -> list[dict]:
        """Rapor liste sayfasındaki rapor sayfası bağlantıları (+ varsa doğrudan ekler)."""
        soup = BeautifulSoup(html, "lxml")
        items, seen = [], set()
        for a in soup.find_all("a", href=True):
            href = urljoin(base, a["href"])
            if "/istatistiki-raporlar/" in href and re.search(r"/istatistiki-raporlar/(19|20)\d\d-", href):
                if href not in seen:
                    seen.add(href)
                    items.append({"type": "report_page", "url": href, "title": a.get_text(" ", strip=True)})
            elif "/download/node/" in href or "/sites/default/files/" in href:
                if href not in seen:
                    seen.add(href)
                    items.append({"type": "attachment", "url": href, "title": a.get("title") or a.get_text(" ", strip=True)})
        return items

    @staticmethod
    def parse_attachments(html: str, base: str = BASE) -> list[dict]:
        soup = BeautifulSoup(html, "lxml")
        out, seen = [], set()
        for a in soup.find_all("a", href=True):
            href = urljoin(base, a["href"])
            if "/download/node/" in href or "/sites/default/files/raporlar/" in href:
                if href in seen:
                    continue
                seen.add(href)
                title = a.get("title") or a.get_text(" ", strip=True)
                fmt = None
                m = re.search(r"\.(xlsx|xls|pdf|zip|csv)\b", (title or "") + " " + href, re.I)
                if m:
                    fmt = m.group(1).lower()
                out.append({"url": href, "title": title, "format_hint": fmt})
        return out

    @staticmethod
    def parse_bank_selector(html: str, base: str = BASE) -> dict:
        """Excel ortak veri seti rapor sayfasındaki 'Banka Seçiniz' seçicisi (28.10.2026 keşfi: sayfa banka listesi veriyor,
        dosya bağlantısı seçime bağlı). Döndürür: {options: [{text, value}], select_name, form_action, form_method, js_hints: [...]}"""
        soup = BeautifulSoup(html, "lxml")
        out = {"options": [], "select_name": None, "form_action": None, "form_method": None, "js_hints": []}
        best = None
        for sel in soup.find_all("select"):
            opts = [(o.get("value"), o.get_text(" ", strip=True)) for o in sel.find_all("option")]
            bankish = sum(1 for v, t in opts if re.search(r"bank|a\.ş|t\.a\.o|limited|s\.p\.a", (t or "").lower()))
            if bankish >= 5 and (best is None or bankish > best[0]):
                best = (bankish, sel, opts)
        if best:
            _, sel, opts = best
            out["select_name"] = sel.get("name") or sel.get("id")
            out["options"] = [{"text": t, "value": v} for v, t in opts if t and v not in (None, "", "0") and not t.lower().startswith("banka seç")]
            form = sel.find_parent("form")
            if form:
                out["form_action"] = urljoin(base, form.get("action") or "")
                out["form_method"] = (form.get("method") or "get").lower()
        for sc in soup.find_all("script"):
            txt = sc.string or sc.get_text() or ""
            for m in re.finditer(r"[\"\'](/?(?:download/node|sites/default/files)[^\"\']*)[\"\']", txt):
                out["js_hints"].append(m.group(1))
            if re.search(r"location\.(href|assign)|window\.open", txt) and ("select" in txt or "option" in txt):
                out["js_hints"].append(txt.strip()[:400])
        return out

    def resolve_bank_files(self, page_html: str, page_url: str, dataset_code: str, pe) -> list[DiscoveredFile]:
        """Seçici seçeneklerinden gerçek dosya adreslerini türetir; strateji sırası: değer URL ise → form GET → JS kalıbı.
        Hiçbiri yoksa boş liste (loglanır); tahmin edilmez."""
        info = self.parse_bank_selector(page_html)
        files: list[DiscoveredFile] = []
        for o in info["options"]:
            v = o["value"] or ""
            if re.search(r"^(https?:)?/|\.(xls|xlsx|zip)$", v, re.I):
                files.append(DiscoveredFile(dataset_code, pe, urljoin(BASE, v), o["text"], None, None, page_url, o["text"], "option_url"))
            elif info["form_action"] and info["select_name"]:
                sep = "&" if "?" in info["form_action"] else "?"
                files.append(DiscoveredFile(dataset_code, pe, f"{info['form_action']}{sep}{info['select_name']}={v}", o["text"], None, None,
                                            page_url, o["text"], "form_get"))
        if not files and info["options"]:
            log.warning("banka seçicisi bulundu (%d seçenek) ama dosya adresi türetilemedi; js_hints=%s", len(info["options"]), info["js_hints"][:3])
        return files

    # ---------------------------------------------------------------- canlı keşif
    def _get_html(self, url: str) -> str | None:
        res = self.downloader.fetch(url, dataset_code="tbb_pages", expected="html")
        if not res.ok:
            log.warning("sayfa alınamadı %s: %s", url, res.error)
            return None
        return res.data.decode("utf-8", errors="replace")

    def resolve_list_id_and_period(self, dataset_code: str, year: int) -> tuple[int | None, str | None, dict | None]:
        spec = SECTIONS[dataset_code]
        html = self._get_html(spec["category"])
        if html is None:
            return spec.get("list_id"), None, None
        forms = self.parse_period_options(html)
        chosen = None
        for title, info in forms.items():
            if re.search(spec["title_match"], title or "", re.I):
                chosen = info
                break
        if chosen is None and spec.get("list_id"):
            for info in forms.values():
                if info.get("list_id") == spec["list_id"]:
                    chosen = info
                    break
        if chosen is None:
            return spec.get("list_id"), None, forms
        return chosen.get("list_id") or spec.get("list_id"), chosen["years"].get(str(year)), forms

    def discover(self, dataset_code: str, year: int, month: int) -> list[DiscoveredFile]:
        found: list[DiscoveredFile] = []
        pe = quarter_end(year, month) if month in (3, 6, 9, 12) else None
        # 1) bilinen statik bağlantılar
        for k in KNOWN_FILES:
            if k["dataset"] == dataset_code and pe and k["period"] == pe.isoformat():
                found.append(DiscoveredFile(dataset_code, pe, k["url"], k["title"], None, k["fmt"]))
        # 2) kategori → liste → rapor sayfası → ekler
        list_id, period_id, _ = self.resolve_list_id_and_period(dataset_code, year)
        if list_id and period_id:
            html = self._get_html(LIST_URL.format(list_id=list_id, period_id=period_id, month=month))
            if html:
                for item in self.parse_report_links(html):
                    if item["type"] == "attachment":
                        found.append(DiscoveredFile(dataset_code, pe, item["url"], item["title"], None, None))
                    else:
                        slug_ok = re.search(SECTIONS[dataset_code]["slug_match"], item["url"], re.I)
                        if not slug_ok or f"{year}-{MONTH_TR.get(month, '')}" not in item["url"]:
                            continue
                        page = self._get_html(item["url"])
                        if page:
                            atts = self.parse_attachments(page)
                            for att in atts:
                                found.append(DiscoveredFile(dataset_code, pe, att["url"], att["title"], None, att["format_hint"], item["url"], None, "attachment"))
                            if not atts and dataset_code.endswith("_excel"):
                                found.extend(self.resolve_bank_files(page, item["url"], dataset_code, pe))
        else:
            log.warning("%s %d-%02d: list_id/period_id çözülemedi (list_id=%s period_id=%s)", dataset_code, year, month, list_id, period_id)
        # tekilleştir
        uniq, seen = [], set()
        for f in found:
            if f.url not in seen:
                seen.add(f.url)
                uniq.append(f)
        return uniq
