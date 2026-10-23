import os
import json
import time
import re
import html
import requests
from typing import Optional
from concurrent.futures import ThreadPoolExecutor
from importers.base import BaseDomainImporter

CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".cache")
DEFAULT_CACHE_FILE = os.path.join(CACHE_DIR, "import_cache_mgeko_cc.json")
CACHE_TTL = 7 * 86400  # 1 week in seconds

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "X-Requested-With": "XMLHttpRequest"
}


class MgekoImporter(BaseDomainImporter):
    domain = "mgeko.cc"
    name = "MGeko"

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

    def _fetch_manga_detail(self, card_info: tuple[str, str]) -> dict:
        rel_url, title = card_info
        clean_rel = rel_url.strip()
        try:
            url = f"https://www.mgeko.cc{clean_rel}"
            r = requests.get(url, headers=DEFAULT_HEADERS, timeout=12)
            if r.status_code == 200:
                # First check inside chapter-list-item
                ch_m = re.search(
                    r"""class=["\'][^"\']*chapter-list-item[^"\']*["\'].*?href=["\'](/reader/[^"\']+)["\']""",
                    r.text,
                    re.DOTALL
                )
                if not ch_m:
                    ch_m = re.search(r"""href=["\'](/reader/[^"\']+)["\']""", r.text)

                if ch_m:
                    ch_url = ch_m.group(1).strip()
                    num_m = re.search(r"""chapter-(\d+)""", ch_url)
                    last_ch = int(num_m.group(1)) if num_m else None
                    tmpl = re.sub(r"""chapter-\d+""", "chapter-{chapter}", ch_url)
                    return {
                        "title": title,
                        "urlTemplate": f"https://www.mgeko.cc{tmpl}",
                        "lastChapter": last_ch
                    }

            return {
                "title": title,
                "urlTemplate": f"https://www.mgeko.cc{clean_rel}",
                "lastChapter": None
            }
        except Exception:
            return {
                "title": title,
                "urlTemplate": f"https://www.mgeko.cc{clean_rel}",
                "lastChapter": None
            }

    def _parse_results_html(self, raw_html: str) -> tuple[list[dict], int]:
        cards = re.findall(r"""<article class="comic-card">.*?</article>""", raw_html, re.DOTALL)
        parsed_cards = []
        for c in cards:
            title_m = re.search(r"""<h3 class="comic-card__title">\s*<a href="(/manga/[^"]+)">\s*(.*?)\s*</a>""", c, re.DOTALL)
            if title_m:
                rel_url = title_m.group(1).strip()
                title = html.unescape(title_m.group(2).strip())
                parsed_cards.append((rel_url, title))

        if not parsed_cards:
            return []

        # Fetch manga detail pages concurrently
        with ThreadPoolExecutor(max_workers=12) as executor:
            items = list(executor.map(self._fetch_manga_detail, parsed_cards))

        return items

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

        url = "https://www.mgeko.cc/browse-comics/data/"
        params = {}
        if q_key:
            params["q"] = q_key
            params["page"] = page
        else:
            params["page"] = page
            params["sort"] = "az"

        try:
            resp = requests.get(url, params=params, headers=DEFAULT_HEADERS, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            total_pages = data.get("num_pages", 294)
            raw_html = data.get("results_html", "")
            items = self._parse_results_html(raw_html)
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
