"""MangaFire Provider for Manhua Manager.

Handles dynamic VRF generation, chapter parsing, chapter navigation,
and CDN proxying for mangafire.to.
"""

import os
import json
import re
import time
import subprocess
import urllib.request
import urllib.parse
from typing import Optional, Dict, Any, Tuple

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR = os.path.join(BASE_DIR, ".cache")
POLYFILL_FILE = os.path.join(CACHE_DIR, "mangafire_polyfill.js")
META_FILE = os.path.join(CACHE_DIR, "mangafire_meta.json")

USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# In-memory chapter mapping cache: (hid, chapter_number) -> chapter_id
_CHAPTER_MAP: Dict[Tuple[str, int], int] = {}


def ensure_cache_dir() -> None:
    os.makedirs(CACHE_DIR, exist_ok=True)


def get_meta() -> Dict[str, Any]:
    ensure_cache_dir()
    if os.path.exists(META_FILE):
        try:
            with open(META_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_meta(data: Dict[str, Any]) -> None:
    ensure_cache_dir()
    with open(META_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def refresh_assets() -> Dict[str, Any]:
    """Fetches mangafire.to homepage to extract window.__config, window.__build,

    and downloads the polyfill script to local cache.
    """
    ensure_cache_dir()
    req = urllib.request.Request(
        "https://mangafire.to/",
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        },
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        html = resp.read().decode("utf-8", errors="ignore")

    config_match = re.search(r'window\.__config\s*=\s*["\']([^"\']+)["\']', html)
    build_match = re.search(r'window\.__build\s*=\s*["\']([^"\']+)["\']', html)
    polyfill_match = re.search(
        r'https://[^"\'\s<>]*polyfill[^"\'\s<>]*\.js', html
    )

    if not config_match or not build_match or not polyfill_match:
        raise ValueError("Failed to extract MangaFire config/build/polyfill")

    config = config_match.group(1)
    build = build_match.group(1)
    polyfill_url = polyfill_match.group(0)

    # Download polyfill script
    poly_req = urllib.request.Request(
        polyfill_url, headers={"User-Agent": USER_AGENT, "Accept": "*/*"}
    )
    with urllib.request.urlopen(poly_req, timeout=20) as resp:
        poly_code = resp.read().decode("utf-8", errors="ignore")

    with open(POLYFILL_FILE, "w", encoding="utf-8") as f:
        f.write(poly_code)

    meta = {
        "config": config,
        "build": build,
        "polyfill_url": polyfill_url,
        "updatedAt": int(time.time()),
    }
    save_meta(meta)
    return meta


def ensure_assets() -> Dict[str, Any]:
    meta = get_meta()
    if (
        not meta.get("config")
        or not meta.get("build")
        or not os.path.exists(POLYFILL_FILE)
    ):
        return refresh_assets()
    return meta


def generate_vrf(path: str) -> str:
    """Generates the VRF token for the specified path using Node.js and the polyfill."""
    meta = ensure_assets()

    node_script = f"""
Object.defineProperty(navigator, "appCodeName", {{ value: "Mozilla", configurable: true }});
globalThis.window = globalThis;
globalThis.document = {{ querySelector: () => null, createElement: () => ({{ setAttribute: () => {{}}, style: {{}} }}), body: {{ appendChild: () => {{}} }} }};
globalThis.location = {{ href: "https://mangafire.to/", origin: "https://mangafire.to" }};
globalThis.__config = {json.dumps(meta['config'])};
globalThis.__build = {json.dumps(meta['build'])};
window.__config = globalThis.__config;
window.__build = globalThis.__build;

import({json.dumps(POLYFILL_FILE)}).then(() => {{
    const vrf = globalThis.dynamicEncrypt({json.dumps(path)});
    console.log(vrf);
    process.exit(0);
}}).catch(err => {{
    console.error("ERROR:" + err.message);
    process.exit(1);
}});
"""
    try:
        out = subprocess.check_output(
            ["node", "--input-type=module", "-e", node_script],
            stderr=subprocess.STDOUT,
            timeout=10,
        ).decode("utf-8")
        clean_lines = [
            l.strip()
            for l in out.split("\n")
            if l.strip() and not l.strip().startswith("(")
        ]
        if not clean_lines:
            raise ValueError(f"No VRF returned: {out}")
        return clean_lines[-1]
    except subprocess.CalledProcessError as e:
        # If execution fails, try refreshing assets once
        refresh_assets()
        meta = get_meta()
        node_script_retry = node_script.replace(
            json.dumps(meta["config"]), json.dumps(meta["config"])
        )
        out = subprocess.check_output(
            ["node", "--input-type=module", "-e", node_script_retry],
            stderr=subprocess.STDOUT,
            timeout=10,
        ).decode("utf-8")
        clean_lines = [
            l.strip()
            for l in out.split("\n")
            if l.strip() and not l.strip().startswith("(")
        ]
        return clean_lines[-1]


def generate_vrf_for_config(
    url: str, params: Optional[Dict[str, Any]] = None
) -> str:
    """Generates the VRF token for the specified URL and params using Node.js and the polyfill interceptor."""
    meta = ensure_assets()
    cfg = {"url": url, "params": params or {}}

    node_script = f"""
Object.defineProperty(navigator, "appCodeName", {{ value: "Mozilla", configurable: true }});
globalThis.window = globalThis;
globalThis.document = {{ querySelector: () => null, createElement: () => ({{ setAttribute: () => {{}}, style: {{}} }}), body: {{ appendChild: () => {{}} }} }};
globalThis.location = {{ href: "https://mangafire.to/", origin: "https://mangafire.to" }};
globalThis.__config = {json.dumps(meta['config'])};
globalThis.__build = {json.dumps(meta['build'])};
window.__config = globalThis.__config;
window.__build = globalThis.__build;

const requestInterceptors = [];
const fakeAxios = {{
    interceptors: {{
        request: {{
            use: (fn) => {{ requestInterceptors.push(fn); }}
        }},
        response: {{ use: () => {{}} }}
    }}
}};

import({json.dumps(POLYFILL_FILE)}).then(async (mod) => {{
    mod.a(fakeAxios);
    const interceptor = requestInterceptors[0];
    const cfg = {json.dumps(cfg)};
    const res = await interceptor(cfg);
    const vrf = res.params?.vrf || (typeof globalThis.dynamicEncrypt === "function" ? globalThis.dynamicEncrypt({json.dumps(url)}) : "");
    console.log(vrf);
    process.exit(0);
}}).catch(err => {{
    console.error("ERROR:" + err.message);
    process.exit(1);
}});
"""
    try:
        out = subprocess.check_output(
            ["node", "--input-type=module", "-e", node_script],
            stderr=subprocess.STDOUT,
            timeout=10,
        ).decode("utf-8")
        clean_lines = [
            l.strip()
            for l in out.split("\n")
            if l.strip() and not l.strip().startswith("(")
        ]
        if not clean_lines:
            raise ValueError(f"No VRF returned: {out}")
        return clean_lines[-1]
    except subprocess.CalledProcessError:
        refresh_assets()
        meta = get_meta()
        node_script_retry = node_script.replace(
            json.dumps(meta["config"]), json.dumps(meta["config"])
        )
        out = subprocess.check_output(
            ["node", "--input-type=module", "-e", node_script_retry],
            stderr=subprocess.STDOUT,
            timeout=10,
        ).decode("utf-8")
        clean_lines = [
            l.strip()
            for l in out.split("\n")
            if l.strip() and not l.strip().startswith("(")
        ]
        return clean_lines[-1]


def api_request(path: str, retry_on_403: bool = True) -> Dict[str, Any]:
    """Performs a GET request to MangaFire's internal API with the generated VRF token."""
    vrf = generate_vrf(path)
    separator = "&" if "?" in path else "?"
    url = f"https://mangafire.to/api{path}{separator}vrf={vrf}"

    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": "https://mangafire.to/",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code == 403 and retry_on_403:
            # Token might be invalidated by new site build, refresh and retry once
            refresh_assets()
            return api_request(path, retry_on_403=False)
        raise


def fetch_chapter_by_id(chapter_id: int | str) -> Dict[str, Any]:
    """Fetches chapter metadata and image list by chapter ID."""
    res = api_request(f"/chapters/{chapter_id}")
    data = res.get("data", {})

    # Cache relationships
    ch_num = data.get("number")
    title_hid = extract_hid_from_slug(data.get("title", {}).get("slug", ""))
    if title_hid and ch_num is not None:
        _CHAPTER_MAP[(title_hid, int(ch_num))] = int(data["id"])

    prev_ch = data.get("prev")
    if prev_ch and title_hid and prev_ch.get("number") is not None:
        _CHAPTER_MAP[(title_hid, int(prev_ch["number"]))] = int(prev_ch["id"])

    next_ch = data.get("next")
    if next_ch and title_hid and next_ch.get("number") is not None:
        _CHAPTER_MAP[(title_hid, int(next_ch["number"]))] = int(next_ch["id"])

    return data


def fetch_title_chapters(hid: str, page: int = 1) -> Dict[str, Any]:
    """Fetches chapter listing for a title HID."""
    path = f"/titles/{hid}/chapters"
    if page > 1:
        path += f"?page={page}"
    res = api_request(path)
    for item in res.get("items", []):
        ch_num = item.get("number")
        ch_id = item.get("id")
        if ch_num is not None and ch_id is not None:
            _CHAPTER_MAP[(hid, int(ch_num))] = int(ch_id)
    return res


def extract_hid_from_slug(slug: str) -> Optional[str]:
    """Extracts HID from a slug like 'nk6zl-necromancer-the-ultimate-scourge' -> 'nk6zl'."""
    if not slug:
        return None
    parts = slug.split("-")
    return parts[0] if parts else None


def parse_mangafire_url(url: str) -> Tuple[Optional[str], Optional[str]]:
    """Parses a MangaFire chapter or title URL.

    Returns (hid, chapter_id_or_number).
    Example:
    'https://mangafire.to/title/nk6zl-necromancer-the-ultimate-scourge/chapter/9427010'
    -> ('nk6zl', '9427010')
    """
    clean_url = url.split("?")[0].rstrip("/")
    m = re.search(r"/title/([^/]+)/chapter/([^/]+)", clean_url)
    if m:
        slug = m.group(1)
        hid = extract_hid_from_slug(slug)
        chapter_param = m.group(2)
        return hid, chapter_param

    m_title = re.search(r"/title/([^/]+)", clean_url)
    if m_title:
        return extract_hid_from_slug(m_title.group(1)), None

    return None, None


def resolve_chapter_id(
    hid: Optional[str], chapter_param: str
) -> Optional[int]:
    """Resolves a chapter parameter (which could be an ID or a chapter number) to a chapter ID."""
    if not chapter_param or chapter_param == "{chapter}":
        return None

    try:
        val = int(chapter_param)
    except ValueError:
        return None

    # MangaFire chapter IDs are large numbers (typically >= 100,000, usually 7 digits like 9427010)
    # Chapter numbers are small (typically 1 to 2000).
    if val >= 100000:
        return val

    # val is a chapter number, look up in cache
    if hid and (hid, val) in _CHAPTER_MAP:
        return _CHAPTER_MAP[(hid, val)]

    # Fetch title chapters to find ID for this chapter number
    if hid:
        try:
            page = 1
            while page <= 5:  # Search up to first 5 pages (300 chapters)
                res = fetch_title_chapters(hid, page=page)
                if (hid, val) in _CHAPTER_MAP:
                    return _CHAPTER_MAP[(hid, val)]
                meta = res.get("meta", {})
                if not meta.get("hasNext"):
                    break
                page += 1
        except Exception:
            pass

    return None


def get_mangafire_chapter_data(target_url: str) -> Dict[str, Any]:
    """Main entry point to fetch chapter pages and navigation for MangaFire URLs.

    Returns dict with images, chapter number, chapterId, prev, next.
    """
    hid, chapter_param = parse_mangafire_url(target_url)
    if not chapter_param:
        raise ValueError(
            f"Could not extract chapter parameter from URL: {target_url}"
        )

    chapter_id = resolve_chapter_id(hid, chapter_param)
    if not chapter_id:
        raise ValueError(
            f"Could not resolve chapter ID for {chapter_param} in {target_url}"
        )

    ch_data = fetch_chapter_by_id(chapter_id)

    raw_pages = ch_data.get("pages", [])
    images = []
    for page in raw_pages:
        img_url = page.get("url") if isinstance(page, dict) else str(page)
        if img_url:
            images.append(img_url)

    return {
        "status": "ok",
        "count": len(images),
        "images": images,
        "chapter": ch_data.get("number"),
        "chapterId": ch_data.get("id"),
        "title": ch_data.get("title", {}).get("name", ""),
        "prev": ch_data.get("prev"),
        "next": ch_data.get("next"),
    }
