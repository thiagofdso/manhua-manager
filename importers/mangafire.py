import os
import json
import time
import re
import html
import requests
from typing import Optional
from importers.base import BaseDomainImporter
import mangafire_provider

CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".cache")
DEFAULT_CACHE_FILE = os.path.join(CACHE_DIR, "import_cache_mangafire_to.json")
CACHE_TTL = 7 * 86400  # 1 week in seconds

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "X-Requested-With": "XMLHttpRequest",
    "Referer": "https://mangafire.to/"
}


class MangafireImporter(BaseDomainImporter):
    domain = "mangafire.to"
    name = "MangaFire"

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

    def _parse_items(self, data: dict) -> tuple[list[dict], int]:
        raw_items = data.get("items", [])
        meta = data.get("meta", {})
        total_pages = meta.get("lastPage", 1)

        items = []
        for it in raw_items:
            raw_title = it.get("title") or it.get("name") or ""
            title = html.unescape(raw_title).strip()
            slug = it.get("slug") or ""
            url_path = it.get("url") or (f"/title/{slug}" if slug else "")
            if not title or not url_path:
                continue

            url_path = url_path.rstrip("/")
            url_template = f"https://mangafire.to{url_path}/chapter/{{chapter}}"

            raw_ch = it.get("latestChapter") if it.get("latestChapter") is not None else it.get("latest_chapter")
            last_chapter = None
            if raw_ch is not None:
                try:
                    val = float(raw_ch)
                    last_chapter = int(val) if val.is_integer() else val
                except (ValueError, TypeError):
                    if isinstance(raw_ch, str):
                        num_m = (
                            re.search(r"(?:chapter|ch\.?)\s*(\d+(?:\.\d+)?)", raw_ch, re.IGNORECASE)
                            or re.search(r"(\d+(?:\.\d+)?)", raw_ch)
                        )
                        if num_m:
                            val = float(num_m.group(1))
                            last_chapter = int(val) if val.is_integer() else val

            items.append({
                "title": title,
                "urlTemplate": url_template,
                "lastChapter": last_chapter
            })

        return items, total_pages

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

        endpoint_url = "/titles"
        if q_key:
            cfg_params = {"keyword": q_key, "page": page, "limit": 40}
            http_params = {"keyword": q_key, "page": page, "limit": 40}
        else:
            cfg_params = {"order": {"chapter_updated_at": "desc"}, "hot": 1, "page": page, "limit": 40}
            http_params = {"order[chapter_updated_at]": "desc", "hot": 1, "page": page, "limit": 40}

        try:
            vrf = mangafire_provider.generate_vrf_for_config(endpoint_url, cfg_params)
            http_params["vrf"] = vrf

            resp = requests.get(
                "https://mangafire.to/api/titles",
                params=http_params,
                headers=DEFAULT_HEADERS,
                timeout=15
            )

            # Retry once on 403 in case site build refreshed
            if resp.status_code == 403:
                mangafire_provider.refresh_assets()
                vrf = mangafire_provider.generate_vrf_for_config(endpoint_url, cfg_params)
                http_params["vrf"] = vrf
                resp = requests.get(
                    "https://mangafire.to/api/titles",
                    params=http_params,
                    headers=DEFAULT_HEADERS,
                    timeout=15
                )

            resp.raise_for_status()
            data = resp.json()
            items, total_pages = self._parse_items(data)
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
