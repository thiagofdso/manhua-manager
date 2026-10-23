import os
import json
import math
from typing import Optional
from importers.base import BaseDomainImporter

CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".cache")

DOMAIN_FILENAME_MAP = {
    "import_cache_asurascans_com.json": ("asurascans.com", "Asura Scans"),
    "import_cache_ravenscans_org.json": ("ravenscans.org", "RavenScans"),
    "import_cache_comix_to.json": ("comix.to", "Comix"),
    "import_cache_manhuaus_com.json": ("manhuaus.com", "ManhuaUS"),
    "import_cache_arenascan_com.json": ("arenascan.com", "ArenaScan"),
    "import_cache_manhuatop_org.json": ("manhuatop.org", "ManhuaTop"),
    "import_cache_mgeko_cc.json": ("mgeko.cc", "MGeko"),
    "import_cache_mangak_io.json": ("mangak.io", "MangaK"),
    "import_cache_mangafire_to.json": ("mangafire.to", "MangaFire"),
}


class AllCacheImporter(BaseDomainImporter):
    domain = "all"
    name = "Todos"

    def __init__(self, cache_dir: Optional[str] = None):
        self.cache_dir = cache_dir or CACHE_DIR

    def _infer_domain_info(self, filename: str) -> tuple[str, str]:
        if filename in DOMAIN_FILENAME_MAP:
            return DOMAIN_FILENAME_MAP[filename]
        # Fallback based on filename pattern import_cache_<key>.json
        base = filename.replace("import_cache_", "").replace(".json", "")
        domain_name = base.replace("_", ".")
        return domain_name, domain_name

    def search_or_browse(self, query: Optional[str] = None, page: int = 1, force_refresh: bool = False) -> dict:
        if not os.path.exists(self.cache_dir):
            return {"items": [], "page": 1, "totalPages": 1, "domain": "all"}

        q_clean = (query or "").strip().lower()
        unique_works: dict[str, dict] = {}

        # Scan all cache files in cache_dir
        for fname in sorted(os.listdir(self.cache_dir)):
            if not fname.startswith("import_cache_") or not fname.endswith(".json") or fname == "import_cache_all.json":
                continue

            filepath = os.path.join(self.cache_dir, fname)
            domain_id, domain_name = self._infer_domain_info(fname)

            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                catalog = data.get("catalog", {})
            except Exception:
                continue

            # Iterate all queries and pages in the cache
            for q_key, pages in catalog.items():
                if not isinstance(pages, dict):
                    continue
                for p_key, items in pages.items():
                    if not isinstance(items, list):
                        continue
                    for it in items:
                        if not isinstance(it, dict):
                            continue
                        tmpl = it.get("urlTemplate", "").strip()
                        title = it.get("title", "").strip()
                        if not tmpl or not title:
                            continue

                        # Deduplicate by urlTemplate
                        if tmpl not in unique_works:
                            unique_works[tmpl] = {
                                "title": title,
                                "urlTemplate": tmpl,
                                "lastChapter": it.get("lastChapter"),
                                "domain": domain_id,
                                "domainName": domain_name
                            }

        # Filter by search term if provided
        all_items = list(unique_works.values())
        if q_clean:
            all_items = [it for it in all_items if q_clean in it["title"].lower()]

        # Sort alphabetically by title
        all_items.sort(key=lambda x: x["title"].lower())

        # Pagination (40 items per page)
        limit = 40
        total_items = len(all_items)
        total_pages = max(1, math.ceil(total_items / limit))
        page = max(1, min(page, total_pages)) if total_items > 0 else 1

        start = (page - 1) * limit
        end = start + limit
        paged_items = all_items[start:end]

        return {
            "items": paged_items,
            "page": page,
            "totalPages": total_pages,
            "domain": "all"
        }
