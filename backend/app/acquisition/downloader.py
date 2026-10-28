"""Otomatik indirme motoru.

Kurallar (proje belgesi §4):
- httpx → requests fallback; yönlendirme ve çerezleri izle; makul istek aralığı; robots.txt'ye saygı.
- Dosya türü uzantıdan değil İÇERİK İMZASINDAN belirlenir.
- Her deneme (yöntem, url, sonuç, neden) loglanır; başarısızlık UNAVAILABLE değil ERROR olarak kaydedilir.
- CAPTCHA / yetkilendirme engeli izinsiz aşılmaz; tarayıcı otomasyonu yalnızca HTML-form/JS zorunluysa (playwright isteğe bağlı).
"""
from __future__ import annotations

import hashlib
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

from app.config import settings

log = logging.getLogger("bilanco.download")

MAGIC = [
    (b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1", "xls"),   # OLE2 (eski Excel)
    (b"PK\x03\x04", "zip"),                          # zip | xlsx (içerikte [Content_Types].xml varsa xlsx)
    (b"%PDF", "pdf"),
]


def sniff_format(data: bytes, declared_name: str | None = None) -> str:
    head = data[:16]
    for sig, fmt in MAGIC:
        if head.startswith(sig):
            if fmt == "zip":
                try:
                    import io as _io, zipfile as _zf
                    names = _zf.ZipFile(_io.BytesIO(data)).namelist()
                    if "[Content_Types].xml" in names and any(n.startswith("xl/") for n in names):
                        return "xlsx"
                    if "[Content_Types].xml" in names and any(n.startswith("word/") for n in names):
                        return "docx"
                    if "[Content_Types].xml" in names and any(n.startswith("ppt/") for n in names):
                        return "pptx"
                except Exception:
                    pass
                if declared_name and declared_name.lower().endswith(".xlsx"):
                    return "xlsx"
                if declared_name and declared_name.lower().endswith(".docx"):
                    return "docx"
            return fmt
    text = data[:4096].lstrip().lower()
    if text.startswith(b"<?xml"):
        return "xml"
    if text.startswith(b"<!doctype html") or b"<html" in text or b"<table" in text:
        return "html"
    if text.startswith(b"{") or text.startswith(b"["):
        return "json"
    sample = data[:4096].decode("utf-8", errors="ignore")
    if sample.count(";") + sample.count(",") >= 3 and "\n" in sample:
        return "csv"
    return "unknown"


@dataclass
class DownloadAttempt:
    method: str
    url: str
    ok: bool
    status: int | None = None
    reason: str | None = None
    elapsed_ms: int | None = None


@dataclass
class DownloadResult:
    url: str
    final_url: str | None
    ok: bool
    data: bytes | None
    format_detected: str | None
    content_type: str | None
    file_name: str | None
    sha256: str | None
    size_bytes: int | None
    local_path: str | None
    attempts: list[DownloadAttempt] = field(default_factory=list)
    error: str | None = None

    def as_log(self) -> list[dict]:
        return [a.__dict__ for a in self.attempts]


class RobotsCache:
    """Her host için robots.txt bir kez okunur; disallow ise istek yapılmaz ve nedeni kaydedilir."""

    def __init__(self):
        self._cache: dict[str, RobotFileParser | None] = {}

    def allowed(self, url: str, ua: str) -> tuple[bool, str | None]:
        host = urlparse(url).netloc
        if host not in self._cache:
            rp = RobotFileParser()
            rp.set_url(f"{urlparse(url).scheme}://{host}/robots.txt")
            try:
                rp.read()
                self._cache[host] = rp
            except Exception as exc:  # robots okunamazsa izinli varsay, ama not düş
                log.info("robots.txt okunamadı (%s): %s", host, exc)
                self._cache[host] = None
        rp = self._cache[host]
        if rp is None:
            return True, "robots.txt okunamadı; izinli varsayıldı"
        ok = rp.can_fetch(ua, url)
        return ok, None if ok else "robots.txt bu yolu yasaklıyor"


class Downloader:
    def __init__(self, raw_dir: Path | None = None, min_gap: float | None = None):
        self.raw_dir = Path(raw_dir or settings.raw_store_dir)
        self.min_gap = settings.min_seconds_between_requests if min_gap is None else min_gap
        self._last_request = 0.0
        self.robots = RobotsCache()
        self.headers = {"User-Agent": settings.user_agent, "Accept": "*/*", "Accept-Language": "tr,en;q=0.8"}

    # ------------------------------------------------------------------ yardımcılar
    def _throttle(self):
        wait = self.min_gap - (time.monotonic() - self._last_request)
        if wait > 0:
            time.sleep(wait)
        self._last_request = time.monotonic()

    @staticmethod
    def _file_name_from(resp_headers: dict, url: str) -> str | None:
        cd = resp_headers.get("content-disposition") or resp_headers.get("Content-Disposition")
        if cd and "filename" in cd:
            part = cd.split("filename")[-1]
            part = part.split("=", 1)[-1].strip().strip('"').strip("'")
            if part.startswith("*=UTF-8''"):
                from urllib.parse import unquote
                part = unquote(part[len("*=UTF-8''"):])
            return part or None
        tail = urlparse(url).path.rsplit("/", 1)[-1]
        return tail or None

    def _store(self, data: bytes, dataset_code: str, file_name: str | None, fmt: str, sha: str) -> str:
        d = self.raw_dir / dataset_code
        d.mkdir(parents=True, exist_ok=True)
        base = (file_name or "download").replace("/", "_")
        if "." not in base:
            base = f"{base}.{fmt}"
        path = d / f"{sha[:12]}__{base}"
        if not path.exists():
            path.write_bytes(data)    # ham dosya değiştirilmeden saklanır
        return str(path)

    # ------------------------------------------------------------------ istemciler
    def _try_httpx(self, url: str, timeout: float) -> tuple[bytes | None, dict, int | None, str | None, str | None]:
        import httpx
        with httpx.Client(follow_redirects=True, timeout=timeout, headers=self.headers) as c:
            r = c.get(url)
            return r.content, dict(r.headers), r.status_code, str(r.url), None

    def _try_requests(self, url: str, timeout: float):
        import requests
        s = requests.Session()
        s.headers.update(self.headers)
        r = s.get(url, timeout=timeout, allow_redirects=True)
        return r.content, dict(r.headers), r.status_code, r.url, None

    def _try_playwright(self, url: str, timeout: float):
        """Yalnızca HTML/JS engeli varsa; playwright kurulu değilse atlanır. CAPTCHA aşmaz."""
        try:
            from playwright.sync_api import sync_playwright  # type: ignore
        except Exception:
            return None, {}, None, None, "playwright kurulu değil"
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(user_agent=self.headers["User-Agent"])
            with page.expect_download(timeout=timeout * 1000) as dl:
                page.goto(url)
            path = dl.value.path()
            data = Path(path).read_bytes()
            browser.close()
            return data, {}, 200, url, None

    # ------------------------------------------------------------------ ana giriş
    def fetch(self, url: str, dataset_code: str = "misc", expected: str | None = None,
              allow_browser: bool = False) -> DownloadResult:
        res = DownloadResult(url=url, final_url=None, ok=False, data=None, format_detected=None, content_type=None,
                             file_name=None, sha256=None, size_bytes=None, local_path=None)
        allowed, why = self.robots.allowed(url, self.headers["User-Agent"])
        if not allowed:
            if settings.robots_policy == "lenient":
                log.warning("robots.txt yasaklıyor (%s) — ROBOTS_POLICY=lenient: açıkça yapılandırılmış resmî dosya, düşük hızda devam", url)
                res.attempts.append(DownloadAttempt("robots", url, True, None, "disallowed; lenient politika ile devam edildi"))
            else:
                res.error = f"robots.txt: {why}"
                res.attempts.append(DownloadAttempt("robots", url, False, None, why))
                return res

        methods = [("httpx", self._try_httpx), ("requests", self._try_requests)]
        if allow_browser:
            methods.append(("playwright", self._try_playwright))

        for name, fn in methods:
            for attempt in range(1, settings.http_max_retries + 1):
                self._throttle()
                t0 = time.monotonic()
                try:
                    data, headers, status, final, err = fn(url, settings.http_timeout)
                    ms = int((time.monotonic() - t0) * 1000)
                    if err:
                        res.attempts.append(DownloadAttempt(name, url, False, status, err, ms))
                        break
                    if status and status >= 400:
                        res.attempts.append(DownloadAttempt(name, url, False, status, f"HTTP {status}", ms))
                        if status in (401, 403, 407, 429):
                            break   # yetkilendirme/hız sınırı: aynı yöntemle ısrar etme
                        continue
                    if not data:
                        res.attempts.append(DownloadAttempt(name, url, False, status, "boş yanıt", ms))
                        continue
                    fname = self._file_name_from(headers, final or url)
                    fmt = sniff_format(data, fname)
                    ctype = headers.get("content-type") or headers.get("Content-Type")
                    if expected and fmt != expected and not (expected == "xls" and fmt in ("xls", "xlsx")):
                        # Beklenen dosya yerine HTML (giriş sayfası / hata) geldiyse başarısızlık say
                        res.attempts.append(DownloadAttempt(name, url, False, status, f"beklenen {expected}, gelen {fmt}", ms))
                        if fmt == "html":
                            continue
                    sha = hashlib.sha256(data).hexdigest()
                    res.ok, res.data, res.format_detected, res.content_type = True, data, fmt, ctype
                    res.file_name, res.sha256, res.size_bytes, res.final_url = fname, sha, len(data), final
                    res.local_path = self._store(data, dataset_code, fname, fmt, sha)
                    res.attempts.append(DownloadAttempt(name, url, True, status, None, ms))
                    return res
                except Exception as exc:  # ağ hatası → bir sonraki deneme / yöntem
                    ms = int((time.monotonic() - t0) * 1000)
                    res.attempts.append(DownloadAttempt(name, url, False, None, f"{type(exc).__name__}: {exc}", ms))
        res.error = "; ".join(f"{a.method}: {a.reason}" for a in res.attempts if not a.ok)[:2000]
        return res
