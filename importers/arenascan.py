import os
import json
import time
import re
import html
import requests
from importers.base import BaseDomainImporter

CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".cache")
DEFAULT_CACHE_FILE = os.path.join(CACHE_DIR, "import_cache_arenascan_com.json")
CACHE_TTL = 7 * 86400  # 1 week in seconds


class ArenascanImporter(BaseDomainImporter):
    domain = "arenascan.com"
    name = "ArenaScan"

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
        cards = re.findall(r'<div class="bsx">.*?</div>\s*</div>\s*</div>', html_text, re.DOTALL)
        if not cards:
            cards = re.findall(r'<div class="bsx">.*?(?=(?:<div class="bsx">|<div class="pagination"|$))', html_text, re.DOTALL)

        items = []
        for c in cards:
            slug_m = re.search(r'href=["\'](?:https://arenascan\.com)?/manga/([^/"\'?]+)/?["\']', c)
            tt_m = re.search(r'<div class=["\']tt["\']>\s*(.*?)\s*</div>', c, re.DOTALL)
            title_attr_m = re.search(r'title=["\']([^"\']+)["\']', c)
            chs_m = re.search(r'<div class=["\']epxs["\']>\s*(?:Chapter|Ch\.)?\s*(\d+)', c, re.IGNORECASE)

            if slug_m:
                slug = slug_m.group(1).strip()
                raw_title = tt_m.group(1).strip() if tt_m else (title_attr_m.group(1).strip() if title_attr_m else slug)
                title = html.unescape(raw_title)
                url_template = f"https://arenascan.com/{slug}-chapter-{{chapter}}/"
                last_chapter = int(chs_m.group(1)) if chs_m else None

                items.append({
                    "title": title,
                    "urlTemplate": url_template,
                    "lastChapter": last_chapter
                })

        pag_m = re.search(r'<div class=["\']pagination["\']>(.*?)</div>', html_text, re.DOTALL)
        total_pages = 1
        if pag_m:
            nums = [int(n) for n in re.findall(r'>(\d+)<', pag_m.group(1))]
            page_params = [int(p) for p in re.findall(r'page=(\d+)', pag_m.group(1))]
            all_nums = nums + page_params
            if all_nums:
                total_pages = max(all_nums)

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

        url = "https://arenascan.com/manga/"
        params = {}
        if q_key:
            params["s"] = q_key
        else:
            params["order"] = "update"

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
