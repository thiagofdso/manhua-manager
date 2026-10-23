import os
import json
import time
import shutil
import subprocess
from typing import Optional
from importers.base import BaseDomainImporter

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE_DIR = os.path.join(BASE_DIR, ".cache")
DEFAULT_CACHE_FILE = os.path.join(CACHE_DIR, "import_cache_comix_to.json")
SCRAPER_SCRIPT = os.path.join(BASE_DIR, "comix_catalog_extractor.mjs")
CACHE_TTL = 7 * 86400  # 1 week in seconds


class ComixImporter(BaseDomainImporter):
    domain = "comix.to"
    name = "Comix"

    def __init__(self, cache_file: Optional[str] = None, scraper_script: Optional[str] = None):
        self.cache_file = cache_file or DEFAULT_CACHE_FILE
        self.scraper_script = scraper_script or SCRAPER_SCRIPT

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

        if not os.path.exists(self.scraper_script):
            raise FileNotFoundError(f"Catalog extractor script not found: {self.scraper_script}")

        has_xvfb = shutil.which("xvfb-run") is not None
        cmd = ["xvfb-run", "-a", "node", self.scraper_script, str(page)] if has_xvfb else ["node", self.scraper_script, str(page)]
        if q_key:
            cmd.append(q_key)

        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=45)
            if res.returncode != 0:
                err_msg = res.stderr.strip() or res.stdout.strip() or f"Process returned code {res.returncode}"
                raise RuntimeError(f"Comix extractor failed: {err_msg}")

            parsed = None
            stdout = res.stdout.strip()
            for line in stdout.splitlines()[::-1]:
                line = line.strip()
                if line.startswith("{") and line.endswith("}"):
                    try:
                        data = json.loads(line)
                        if data.get("status") == "ok":
                            parsed = data
                            break
                    except json.JSONDecodeError:
                        continue

            if not parsed:
                raise ValueError(f"Could not parse valid JSON from comix extractor: {stdout[:300]}")

            items = parsed.get("items", [])
            total_pages = parsed.get("totalPages", 1)

        except Exception as e:
            # Fallback to cache if available
            catalog = cache.get("catalog", {})
            if q_key in catalog and p_key in catalog[q_key]:
                return {
                    "items": catalog[q_key][p_key],
                    "page": page,
                    "totalPages": cache.get("totalPages", {}).get(q_key, {}).get(p_key, 1),
                    "warning": f"Erro ao consultar comix.to: {str(e)}. Usando dados locais em cache."
                }
            raise

        # Save to cache
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
