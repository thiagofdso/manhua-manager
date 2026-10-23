import os
import json
import time
import re
import html
import requests
from importers.base import BaseDomainImporter

CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".cache")
DEFAULT_CACHE_FILE = os.path.join(CACHE_DIR, "import_cache_asurascans_com.json")
CACHE_TTL = 7 * 86400  # 1 week in seconds

class AsurascansImporter(BaseDomainImporter):
    domain = "asurascans.com"
    name = "Asura Scans"

    def __init__(self, cache_file: str = None):
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

    def _parse_html(self, html_text: str) -> tuple[list[dict], int]:
        cards = re.findall(r'<div class="series-card [^>]+>.*?</div>\s*</div>\s*</div>', html_text, re.DOTALL)
        if not cards:
            cards = re.findall(r'<div class="series-card .*?(?=(?:<div class="series-card |<nav id="pagination-nav"|$))', html_text, re.DOTALL)

        items = []
        for c in cards:
            href_m = re.search(r'href=["\'](/comics/[^"\']+)["\']', c)
            title_m = re.search(r'<h3[^>]*>(.*?)</h3>', c)
            chs_m = re.search(r'(\d+)\s*(?:<!-- -->)?\s*<span[^>]*>(?:Chs\.|Chapters)', c)

            if href_m and title_m:
                href = href_m.group(1).strip().rstrip("/")
                title = html.unescape(title_m.group(1).strip())
                url_template = f"https://asurascans.com{href}/chapter/{{chapter}}"
                last_chapter = int(chs_m.group(1)) if chs_m else None

                items.append({
                    "title": title,
                    "urlTemplate": url_template,
                    "lastChapter": last_chapter
                })

        pages = [int(p) for p in re.findall(r'page=(\d+)', html_text)]
        aria_pages = [int(p) for p in re.findall(r'aria-label="Page (\d+)"', html_text)]
        all_pages = pages + aria_pages
        total_pages = max(all_pages) if all_pages else 1

        return items, total_pages

    def search_or_browse(self, query: str = None, page: int = 1, force_refresh: bool = False) -> dict:
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

        # Request to asurascans
        url = "https://asurascans.com/browse/comics"
        params = {}
        if q_key:
            params["q"] = q_key
        if page > 1:
            params["page"] = page

        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        }

        try:
            resp = requests.get(url, params=params, headers=headers, timeout=15)
            resp.raise_for_status()
            html_text = resp.content.decode("utf-8", errors="replace")
            items, total_pages = self._parse_html(html_text)
        except Exception as e:
            # Fallback to cache if available
            catalog = cache.get("catalog", {})
            if q_key in catalog and p_key in catalog[q_key]:
                return {
                    "items": catalog[q_key][p_key],
                    "page": page,
                    "totalPages": cache.get("totalPages", {}).get(q_key, {}).get(p_key, 1),
                    "warning": f"Erro de rede: {str(e)}. Usando dados locais em cache."
                }
            raise

        # Update cache
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
