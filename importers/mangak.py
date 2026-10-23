import os
import json
import time
import re
import html
import requests
from typing import Optional
from importers.base import BaseDomainImporter

CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".cache")
DEFAULT_CACHE_FILE = os.path.join(CACHE_DIR, "import_cache_mangak_io.json")
CACHE_TTL = 7 * 86400  # 1 week in seconds

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
}


class MangakImporter(BaseDomainImporter):
    domain = "mangak.io"
    name = "MangaK"

    def __init__(self, cache_file: Optional[str] = None):
        self.cache_file = cache_file or DEFAULT_CACHE_FILE

    def _is_cache_valid(self) -> bool:
        if not os.path.exists(self.cache_file):
            return False
        try:
            with open(self.cache_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            ts = data.get("timestamp", 0)
            return (time.time() - ts) < CACHE_TTL
        except Exception:
            return False

    def _load_cache(self) -> dict:
        if not os.path.exists(self.cache_file):
            return {"timestamp": 0, "catalog": {}, "totalPages": {}}
        try:
            with open(self.cache_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {"timestamp": 0, "catalog": {}, "totalPages": {}}

    def _save_cache(self, data: dict):
        os.makedirs(os.path.dirname(self.cache_file), exist_ok=True)
        try:
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _parse_next_data(self, html_text: str) -> tuple[list[dict], int]:
        m = re.search(r"""<script id="__NEXT_DATA__" type="application/json">(.*?)</script>""", html_text, re.DOTALL)
        if not m:
            return [], 1

        try:
            data = json.loads(m.group(1))
            pp = data.get("props", {}).get("pageProps", {})
            raw_items = pp.get("ssrItems") or pp.get("items") or []
            pag = pp.get("ssrPagination") or pp.get("pagination") or {}
            total_pages = pag.get("total_pages") or 1

            items = []
            for it in raw_items:
                title = html.unescape((it.get("name") or "").strip())
                slug = (it.get("slug") or it.get("url") or "").strip().strip("/")
                if not title or not slug:
                    continue

                url_template = f"https://mangak.io/{slug}/chapter-{{chapter}}"

                last_chapter = None
                latest_chapters = it.get("latestChapters") or []
                if latest_chapters:
                    ch_info = latest_chapters[0]
                    ch_text = ch_info.get("name", "") or ch_info.get("slug", "") or ch_info.get("url", "")
                    num_m = (
                        re.search(r"(?:chapter|ch\.?)\s*(\d+)", ch_text, re.IGNORECASE)
                        or re.search(r"chapter-(\d+)", ch_text, re.IGNORECASE)
                        or re.search(r"(\d+)", ch_text)
                    )
                    if num_m:
                        last_chapter = int(num_m.group(1))

                if last_chapter is None:
                    ch_count = it.get("stats", {}).get("chaptersCount")
                    if isinstance(ch_count, int) and ch_count > 0:
                        last_chapter = ch_count

                items.append({
                    "title": title,
                    "urlTemplate": url_template,
                    "lastChapter": last_chapter
                })

            return items, total_pages
        except Exception:
            return [], 1

    def search_or_browse(self, query: Optional[str] = None, page: int = 1, force_refresh: bool = False) -> dict:
        q_key = (query or "").strip().lower()
        p_key = str(page)

        cache = self._load_cache()
        if not force_refresh and self._is_cache_valid():
            catalog = cache.get("catalog", {})
            total_pages_dict = cache.get("totalPages", {})
            if q_key in catalog and p_key in catalog[q_key]:
                return {
                    "items": catalog[q_key][p_key],
                    "page": page,
                    "totalPages": total_pages_dict.get(q_key, {}).get(p_key, 1)
                }

        if q_key:
            url = "https://mangak.io/search"
            params = {"q": q_key}
            if page > 1:
                params["page"] = page
        else:
            url = "https://mangak.io/latest"
            params = {}
            if page > 1:
                params["page"] = page
                params["sort"] = "latest"

        try:
            resp = requests.get(url, params=params, headers=DEFAULT_HEADERS, timeout=15)
            resp.raise_for_status()
            html_text = resp.content.decode("utf-8", errors="replace")
            items, total_pages = self._parse_next_data(html_text)
        except Exception as e:
            catalog = cache.get("catalog", {})
            if q_key in catalog and p_key in catalog[q_key]:
                return {
                    "items": catalog[q_key][p_key],
                    "page": page,
                    "totalPages": cache.get("totalPages", {}).get(q_key, {}).get(p_key, 1),
                    "warning": f"Erro de rede: {str(e)}. Usando dados locais em cache."
                }
            raise

        if not self._is_cache_valid():
            cache["timestamp"] = time.time()
        if "catalog" not in cache:
            cache["catalog"] = {}
        if "totalPages" not in cache:
            cache["totalPages"] = {}

        if q_key not in cache["catalog"]:
            cache["catalog"][q_key] = {}
        if q_key not in cache["totalPages"]:
            cache["totalPages"][q_key] = {}

        cache["catalog"][q_key][p_key] = items
        cache["totalPages"][q_key][p_key] = total_pages
        self._save_cache(cache)

        return {
            "items": items,
            "page": page,
            "totalPages": total_pages
        }
