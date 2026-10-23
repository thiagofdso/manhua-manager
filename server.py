import os
import json
import time
import re
import urllib.request
import urllib.parse
import threading
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from flask import Flask, request, jsonify, send_from_directory, Response
from flask_cors import CORS
import mangafire_provider
import comix_provider
import manhuaus_provider
from importers.registry import get_registered_domains, get_importer

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, "database.json")
NOTIFICATIONS_FILE = os.path.join(BASE_DIR, "notifications.json")

app = Flask(__name__, static_folder=BASE_DIR)
CORS(app)

def load_data():
    if not os.path.exists(DB_FILE):
        return []
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def save_data(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_notifications():
    if not os.path.exists(NOTIFICATIONS_FILE):
        return []
    try:
        with open(NOTIFICATIONS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def save_notifications(data):
    with open(NOTIFICATIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def add_notification(manhua_id: int, title: str, chapter: int) -> dict:
    notifs = load_notifications()
    item = {
        "id": int(time.time() * 1000),
        "manhuaId": manhua_id,
        "title": title,
        "chapter": chapter,
        "message": f"Novo episódio {chapter} de {title} disponível!",
        "createdAt": int(time.time())
    }
    notifs.insert(0, item)
    save_notifications(notifs)
    return item

@app.route("/api/notifications", methods=["GET"])
def get_notifications():
    return jsonify(load_notifications())

@app.route("/api/notifications/<int:notification_id>", methods=["DELETE"])
def delete_notification(notification_id):
    notifs = [n for n in load_notifications() if n["id"] != notification_id]
    save_notifications(notifs)
    return jsonify({"status": "ok"})

@app.route("/api/notifications", methods=["DELETE"])
def clear_all_notifications():
    save_notifications([])
    return jsonify({"status": "ok"})

@app.route("/")
def index():
    return send_from_directory(BASE_DIR, "index.html")

@app.route("/<path:filename>")
def static_files(filename):
    return send_from_directory(BASE_DIR, filename)

def sort_manhuas(data):
    return sorted(
        data,
        key=lambda x: (
            not bool(x.get("isFavorite", False)),
            int(x.get("customOrder", 0)),
            -int(x.get("updatedAt", 0))
        )
    )

@app.route("/api/manhuas", methods=["GET"])
def get_manhuas():
    data = load_data()
    return jsonify(sort_manhuas(data))

@app.route("/api/import/domains", methods=["GET"])
def get_import_domains():
    return jsonify(get_registered_domains())

@app.route("/api/import/browse", methods=["GET"])
def browse_import():
    domain = request.args.get("domain", "").strip()
    query = request.args.get("q", "").strip() or None
    try:
        page = int(request.args.get("page", 1))
    except (ValueError, TypeError):
        page = 1

    importer = get_importer(domain)
    if not importer:
        return jsonify({"error": f"Domínio '{domain}' não suportado para importação"}), 400

    try:
        data = importer.search_or_browse(query=query, page=page)
        db_data = load_data()

        # Build duplicate lookup sets
        existing_urls = {
            m.get("urlTemplate", "").lower().strip()
            for m in db_data if m.get("urlTemplate")
        }
        existing_titles = {
            m.get("title", "").lower().strip()
            for m in db_data if m.get("title")
        }

        # Annotate items with alreadyExists
        annotated_items = []
        for item in data.get("items", []):
            url_tmpl = item.get("urlTemplate", "").lower().strip()
            title = item.get("title", "").lower().strip()
            already_exists = (url_tmpl in existing_urls) or (title in existing_titles)

            annotated_items.append({
                "title": item["title"],
                "urlTemplate": item["urlTemplate"],
                "lastChapter": item.get("lastChapter"),
                "alreadyExists": already_exists
            })

        return jsonify({
            "status": "ok",
            "domain": domain,
            "page": data.get("page", page),
            "totalPages": data.get("totalPages", 1),
            "items": annotated_items
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/import", methods=["POST"])
def import_works():
    payload = request.get_json() or {}
    items = payload.get("items", [])
    if not isinstance(items, list) or not items:
        return jsonify({"error": "Nenhum item fornecido para importação"}), 400

    data = load_data()
    existing_urls = {
        m.get("urlTemplate", "").lower().strip()
        for m in data if m.get("urlTemplate")
    }
    existing_titles = {
        m.get("title", "").lower().strip()
        for m in data if m.get("title")
    }

    group_orders = [m.get("customOrder", 0) for m in data if not bool(m.get("isFavorite", False))]
    min_order = min(group_orders) if group_orders else 0

    imported_count = 0
    skipped_count = 0

    for item in items:
        title = item.get("title", "").strip()
        url_template = item.get("urlTemplate", "").strip()
        last_chapter = item.get("lastChapter")

        if not title or not url_template:
            continue

        norm_url = url_template.lower().strip()
        norm_title = title.lower().strip()

        if norm_url in existing_urls or norm_title in existing_titles:
            skipped_count += 1
            continue

        min_order -= 1
        new_manhua = {
            "id": int(time.time() * 1000) + imported_count,
            "title": title,
            "urlTemplate": url_template,
            "currentChapter": 1,
            "updatedAt": int(time.time()),
            "isFavorite": False,
            "customOrder": min_order,
            "isHiatus": False,
            "updateDay": 6  # Domingo
        }
        if last_chapter is not None:
            try:
                new_manhua["lastChapter"] = int(last_chapter)
            except (ValueError, TypeError):
                pass

        data.append(new_manhua)
        existing_urls.add(norm_url)
        existing_titles.add(norm_title)
        imported_count += 1

    if imported_count > 0:
        save_data(data)

    return jsonify({
        "status": "ok",
        "imported": imported_count,
        "skipped": skipped_count
    })

@app.route("/api/manhuas", methods=["POST"])
def add_manhua():
    payload = request.get_json() or {}
    if not payload.get("title") or not payload.get("urlTemplate") or payload.get("currentChapter") is None:
        return jsonify({"error": "Dados inválidos"}), 400

    url_template = payload["urlTemplate"].strip()
    current_chapter = max(1, int(payload["currentChapter"]))
    chapter_id = None
    next_chapter = None
    prev_chapter = None

    if "mangafire.to" in url_template.lower():
        try:
            hid, ch_param = mangafire_provider.parse_mangafire_url(url_template)
            test_id = mangafire_provider.resolve_chapter_id(hid, ch_param) if ch_param else None
            if test_id:
                ch_meta = mangafire_provider.fetch_chapter_by_id(test_id)
                current_chapter = ch_meta.get("number", current_chapter)
                chapter_id = ch_meta.get("id")
                next_chapter = ch_meta.get("next")
                prev_chapter = ch_meta.get("prev")
            url_template = re.sub(r'/chapter/\d+', '/chapter/{chapter}', url_template)
        except Exception:
            pass
    elif "comix.to" in url_template.lower():
        try:
            ch_meta = comix_provider.get_comix_chapter_data(url_template)
            current_chapter = ch_meta.get("chapter", current_chapter)
            chapter_id = ch_meta.get("chapterId")
            next_chapter = ch_meta.get("next")
            prev_chapter = ch_meta.get("prev")
            url_template = re.sub(r'/\d+-chapter-\d+', '/{chapter}', url_template)
        except Exception:
            pass
    elif "manhuaus.com" in url_template.lower():
        try:
            ch_meta = manhuaus_provider.get_manhuaus_chapter_data(url_template)
            current_chapter = ch_meta.get("chapter", current_chapter)
            next_chapter = ch_meta.get("next")
            prev_chapter = ch_meta.get("prev")
            url_template = re.sub(r'chapter-\d+', 'chapter-{chapter}', url_template, flags=re.IGNORECASE)
        except Exception:
            pass
    elif "{chapter}" not in url_template:
        if re.search(r'chapter-\d+', url_template, re.IGNORECASE):
            url_template = re.sub(r'chapter-\d+', 'chapter-{chapter}', url_template, flags=re.IGNORECASE)
        elif re.search(r'/chapter/\d+', url_template, re.IGNORECASE):
            url_template = re.sub(r'/chapter/\d+', '/chapter/{chapter}', url_template, flags=re.IGNORECASE)

    data = load_data()
    fav = bool(payload.get("isFavorite", False))
    group_orders = [m.get("customOrder", 0) for m in data if bool(m.get("isFavorite", False)) == fav]
    min_order = min(group_orders) if group_orders else 0
    last_chapter = int(payload["lastChapter"]) if payload.get("lastChapter") is not None and str(payload.get("lastChapter")).strip() != "" else None
    update_day = int(payload["updateDay"]) if payload.get("updateDay") is not None and str(payload.get("updateDay")).strip() != "" else None
    is_hiatus = bool(payload.get("isHiatus", False))

    new_item = {
        "id": int(time.time() * 1000),
        "title": payload["title"].strip(),
        "urlTemplate": url_template,
        "currentChapter": current_chapter,
        "updatedAt": int(time.time()),
        "isFavorite": fav,
        "customOrder": min_order - 1,
        "isHiatus": is_hiatus
    }
    if last_chapter is not None:
        new_item["lastChapter"] = last_chapter
    if update_day is not None:
        new_item["updateDay"] = update_day
    if chapter_id:
        new_item["chapterId"] = chapter_id
    if next_chapter:
        new_item["nextChapter"] = next_chapter
    if prev_chapter:
        new_item["prevChapter"] = prev_chapter

    data.append(new_item)
    save_data(data)
    return jsonify({"status": "ok", "item": new_item})

@app.route("/api/manhuas/<int:item_id>", methods=["PATCH"])
def update_chapter(item_id):
    payload = request.get_json() or {}
    data = load_data()
    for m in data:
        if m["id"] == item_id:
            if "isFavorite" in payload:
                new_fav = bool(payload["isFavorite"])
                m["isFavorite"] = new_fav
                same_group_orders = [
                    other.get("customOrder", 0)
                    for other in data
                    if other["id"] != m["id"] and bool(other.get("isFavorite", False)) == new_fav
                ]
                min_order = min(same_group_orders) if same_group_orders else 0
                m["customOrder"] = min_order - 1

            if "title" in payload and str(payload["title"]).strip():
                m["title"] = str(payload["title"]).strip()
            if "urlTemplate" in payload and str(payload["urlTemplate"]).strip():
                m["urlTemplate"] = str(payload["urlTemplate"]).strip()
                if "mangafire.to" in m["urlTemplate"].lower():
                    m["urlTemplate"] = re.sub(r'/chapter/\d+', '/chapter/{chapter}', m["urlTemplate"])
                elif "comix.to" in m["urlTemplate"].lower():
                    m["urlTemplate"] = re.sub(r'/\d+-chapter-\d+', '/{chapter}', m["urlTemplate"])
                elif "manhuaus.com" in m["urlTemplate"].lower():
                    m["urlTemplate"] = re.sub(r'chapter-\d+', 'chapter-{chapter}', m["urlTemplate"], flags=re.IGNORECASE)
                elif "{chapter}" not in m["urlTemplate"]:
                    if re.search(r'chapter-\d+', m["urlTemplate"], re.IGNORECASE):
                        m["urlTemplate"] = re.sub(r'chapter-\d+', 'chapter-{chapter}', m["urlTemplate"], flags=re.IGNORECASE)
                    elif re.search(r'/chapter/\d+', m["urlTemplate"], re.IGNORECASE):
                        m["urlTemplate"] = re.sub(r'/chapter/\d+', '/chapter/{chapter}', m["urlTemplate"], flags=re.IGNORECASE)

            is_mf = "mangafire.to" in m.get("urlTemplate", "").lower()
            is_comix = "comix.to" in m.get("urlTemplate", "").lower()
            is_manhuaus = "manhuaus.com" in m.get("urlTemplate", "").lower()

            if "chapter" in payload:
                m["currentChapter"] = max(1, int(payload["chapter"]))
                if is_mf or is_comix:
                    m.pop("chapterId", None)
                cur_fav = bool(m.get("isFavorite", False))
                same_group_orders = [
                    other.get("customOrder", 0)
                    for other in data
                    if other["id"] != m["id"] and bool(other.get("isFavorite", False)) == cur_fav
                ]
                min_order = min(same_group_orders) if same_group_orders else 0
                m["customOrder"] = min_order - 1
            elif "delta" in payload:
                delta = int(payload["delta"])
                if is_comix:
                    if (delta > 0 and not m.get("nextChapter")) or (delta < 0 and not m.get("prevChapter")):
                        try:
                            t_url = m.get("urlTemplate", "")
                            if m.get("chapterId"):
                                t_url = re.sub(r'/\{chapter\}|\/\d+-chapter-\d+', f'/{m["chapterId"]}-chapter-{m["currentChapter"]}', t_url)
                            ch_info = comix_provider.get_comix_chapter_data(t_url)
                            m["currentChapter"] = ch_info.get("chapter", m["currentChapter"])
                            m["chapterId"] = ch_info.get("chapterId")
                            m["nextChapter"] = ch_info.get("next")
                            m["prevChapter"] = ch_info.get("prev")
                        except Exception:
                            pass

                    if delta > 0 and m.get("nextChapter"):
                        next_info = m["nextChapter"]
                        m["currentChapter"] = next_info.get("number", m["currentChapter"] + delta)
                        m["chapterId"] = next_info.get("id")
                    elif delta < 0 and m.get("prevChapter"):
                        prev_info = m["prevChapter"]
                        m["currentChapter"] = prev_info.get("number", max(1, m["currentChapter"] + delta))
                        m["chapterId"] = prev_info.get("id")
                    else:
                        m["currentChapter"] = max(1, m["currentChapter"] + delta)
                        m.pop("chapterId", None)
                elif is_mf:
                    if (delta > 0 and not m.get("nextChapter")) or (delta < 0 and not m.get("prevChapter")):
                        try:
                            hid, ch_param = mangafire_provider.parse_mangafire_url(m.get("urlTemplate", ""))
                            target_val = m.get("chapterId") or ch_param or m.get("currentChapter")
                            ch_id = mangafire_provider.resolve_chapter_id(hid, str(target_val))
                            if ch_id:
                                ch_info = mangafire_provider.fetch_chapter_by_id(ch_id)
                                m["currentChapter"] = ch_info.get("number", m["currentChapter"])
                                m["chapterId"] = ch_info.get("id")
                                m["nextChapter"] = ch_info.get("next")
                                m["prevChapter"] = ch_info.get("prev")
                        except Exception:
                            pass

                    if delta > 0 and m.get("nextChapter"):
                        next_info = m["nextChapter"]
                        m["currentChapter"] = next_info.get("number", m["currentChapter"] + delta)
                        m["chapterId"] = next_info.get("id")
                    elif delta < 0 and m.get("prevChapter"):
                        prev_info = m["prevChapter"]
                        m["currentChapter"] = prev_info.get("number", max(1, m["currentChapter"] + delta))
                        m["chapterId"] = prev_info.get("id")
                    else:
                        m["currentChapter"] = max(1, m["currentChapter"] + delta)
                        m.pop("chapterId", None)
                elif is_manhuaus:
                    if (delta > 0 and not m.get("nextChapter")) or (delta < 0 and not m.get("prevChapter")):
                        try:
                            t_url = m.get("urlTemplate", "").replace("{chapter}", str(m.get("currentChapter", 1)))
                            ch_info = manhuaus_provider.get_manhuaus_chapter_data(t_url)
                            m["currentChapter"] = ch_info.get("chapter", m["currentChapter"])
                            m["nextChapter"] = ch_info.get("next")
                            m["prevChapter"] = ch_info.get("prev")
                        except Exception:
                            pass

                    if delta > 0 and m.get("nextChapter"):
                        next_info = m["nextChapter"]
                        m["currentChapter"] = next_info.get("number", m["currentChapter"] + delta)
                    elif delta < 0 and m.get("prevChapter"):
                        prev_info = m["prevChapter"]
                        m["currentChapter"] = prev_info.get("number", max(1, m["currentChapter"] + delta))
                    else:
                        m["currentChapter"] = max(1, m["currentChapter"] + delta)
                else:
                    m["currentChapter"] = max(1, m["currentChapter"] + delta)

                cur_fav = bool(m.get("isFavorite", False))
                same_group_orders = [
                    other.get("customOrder", 0)
                    for other in data
                    if other["id"] != m["id"] and bool(other.get("isFavorite", False)) == cur_fav
                ]
                min_order = min(same_group_orders) if same_group_orders else 0
                m["customOrder"] = min_order - 1


            if "lastChapter" in payload:
                raw_lc = payload["lastChapter"]
                m["lastChapter"] = int(raw_lc) if raw_lc is not None and str(raw_lc).strip() != "" else None
            if "updateDay" in payload:
                raw_ud = payload["updateDay"]
                m["updateDay"] = int(raw_ud) if raw_ud is not None and str(raw_ud).strip() != "" else None
            if "isHiatus" in payload:
                m["isHiatus"] = bool(payload["isHiatus"])

            m["updatedAt"] = int(time.time())
            save_data(data)
            return jsonify({"status": "ok", "item": m})
    return jsonify({"error": "Item não encontrado"}), 404

@app.route("/api/manhuas/<int:item_id>", methods=["DELETE"])
def delete_manhua(item_id):
    data = [m for m in load_data() if m["id"] != item_id]
    save_data(data)
    return jsonify({"status": "ok"})

@app.route("/api/manhuas/reorder", methods=["PUT"])
def reorder_manhuas():
    payload = request.get_json() or {}
    order_ids = payload.get("order")
    if not isinstance(order_ids, list):
        return jsonify({"error": "Campo 'order' deve ser uma lista de IDs"}), 400

    data = load_data()
    id_map = {m["id"]: m for m in data}

    fav_items = []
    non_fav_items = []

    for item_id in order_ids:
        if item_id in id_map:
            item = id_map.pop(item_id)
            if item.get("isFavorite", False):
                fav_items.append(item)
            else:
                non_fav_items.append(item)

    for rem in id_map.values():
        if rem.get("isFavorite", False):
            fav_items.append(rem)
        else:
            non_fav_items.append(rem)

    final_ordered = fav_items + non_fav_items

    for idx, item in enumerate(final_ordered):
        item["customOrder"] = idx

    save_data(data)
    return jsonify({"status": "ok", "items": sort_manhuas(data)})

def extract_manhuatop_images(html: str) -> list[str]:
    raw_imgs = re.findall(r'<img[^>]+src=[\"\']([^\"\']+)[\"\'][^>]*class=[\"\'][^\"\']*wp-manga-chapter-img[^\"\']*[\"\']', html, re.IGNORECASE)
    raw_imgs += re.findall(r'<img[^>]+class=[\"\'][^\"\']*wp-manga-chapter-img[^\"\']*[\"\'][^>]+src=[\"\']([^\"\']+)[\"\']', html, re.IGNORECASE)

    seen = set()
    chapter_imgs = []
    for img in raw_imgs:
        clean = img.strip()
        if clean and clean not in seen and "about_manhuatop" not in clean:
            seen.add(clean)
            chapter_imgs.append(clean)
    return chapter_imgs

def extract_asurascans_images(html: str) -> list[str]:
    pattern = r'https://cdn\.asurascans\.com/asura-images/chapters(?:-merged)?/[^\s"\'<>&]+(?:\?[^\s"\'<>&]*)?'
    raw_matches = re.findall(pattern, html)
    return list(dict.fromkeys(raw_matches))

def extract_ravenscans_images(html: str) -> list[str]:
    match = re.search(r'ts_reader\.run\(\s*({.*?})\s*\);', html, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group(1).replace(r'\/', '/'))
            sources = data.get("sources", [])
            if sources and "images" in sources[0]:
                return [img.strip() for img in sources[0]["images"] if img.strip()]
        except Exception:
            pass

    reader_match = re.search(r'<div[^>]*id=["\']readerarea["\'][^>]*>(.*?)</div>', html, re.DOTALL)
    if reader_match:
        reader_html = reader_match.group(1)
        img_tags = re.findall(r'<img[^>]+>', reader_html)
        images = []
        for tag in img_tags:
            src_match = re.search(r'data-src=["\']([^"\']+)["\']', tag) or re.search(r'src=["\']([^"\']+)["\']', tag)
            if src_match:
                src = src_match.group(1).strip()
                if src and "readerarea.svg" not in src and not src.startswith("data:"):
                    images.append(src)
        if images:
            return list(dict.fromkeys(images))

    pattern = r'https?://[^\s"\'<>]*(?:ravenscans\.org)[^\s"\'<>]*\.(?:webp|jpg|jpeg|png)(?:\?[^\s"\'<>]*)?'
    raw_matches = re.findall(pattern, html)
    filtered = [
        m for m in raw_matches
        if not any(x in m for x in ["/wp-content/", "/themes/", "logo", "favicon"])
    ]
    return list(dict.fromkeys(filtered))

def extract_mangak_images(html: str) -> list[str]:
    m = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html, re.DOTALL)
    if m:
        try:
            data = json.loads(m.group(1))
            images = data.get("props", {}).get("pageProps", {}).get("initialChapter", {}).get("images", [])
            if images:
                return [img.strip() for img in images if img and img.strip()]
        except Exception:
            pass
    raw = re.findall(r'https?://[^\s"\'<>]*qvzr[^\s"\'<>]*\.(?:webp|jpg|jpeg|png)', html)
    return list(dict.fromkeys(raw))

def extract_mgeko_images(html: str) -> list[str]:
    imgs = re.findall(r'<img[^>]+id=["\']image-\d+["\'][^>]*src=["\']([^"\']+)["\']', html, re.IGNORECASE)
    if not imgs:
        imgs = re.findall(r'<img[^>]+src=["\']([^"\']+)["\'][^>]*id=["\']image-\d+["\']', html, re.IGNORECASE)
    if not imgs:
        reader_match = re.search(r'<div[^>]*id=["\']chapter-reader["\'][^>]*>(.*?)</div>', html, re.DOTALL | re.IGNORECASE)
        if reader_match:
            imgs = re.findall(r'<img[^>]+src=["\']([^"\']+)["\']', reader_match.group(1), re.IGNORECASE)
    filtered = []
    for u in imgs:
        u = u.strip()
        if u and not u.startswith("data:") and not any(x in u.lower() for x in ["banner", "credit", "logo", "loading"]):
            if u not in filtered:
                filtered.append(u)
    return filtered

def extract_levelingwithgods_images(html: str) -> list[str]:
    content_match = re.search(r'<div[^>]*class=["\'][^"\']*entry-content[^"\']*["\'][^>]*>(.*?)</div>\s*(?:<!--|\z)', html, re.DOTALL | re.IGNORECASE)
    search_scope = content_match.group(1) if content_match else html
    raw = re.findall(r'<img[^>]+(?:data-src|src)=["\'](https?://[^"\']+)["\']', search_scope, re.IGNORECASE)
    images = []
    for u in raw:
        u = u.strip()
        if any(x in u.lower() for x in ["lazy_placeholder", "logo", "avatar", "icon", "about_"]) or u.startswith("data:"):
            continue
        if u not in images:
            images.append(u)
    return images

def extract_pickmeupgacha_images(html: str) -> list[str]:
    raw = re.findall(r'<img[^>]+(?:data-src|src)=["\'](https?://[^"\']+)["\']', html, re.IGNORECASE)
    images = []
    for u in raw:
        u = u.strip()
        if "abyssrift.com" in u or ("/Gacha/" in u and u.lower().endswith((".webp", ".jpg", ".png", ".jpeg"))):
            if u not in images:
                images.append(u)
    if not images:
        for u in raw:
            u = u.strip()
            if any(ext in u.lower() for ext in [".webp", ".jpg", ".png", ".jpeg"]) and not any(x in u.lower() for x in ["lazy", "logo", "avatar", "icon"]):
                if u not in images:
                    images.append(u)
    return images

def extract_magicemperor_images(html: str) -> list[str]:
    content_match = re.search(r'<div[^>]*class=["\'][^"\']*entry-content[^"\']*["\'][^>]*>(.*?)</div>\s*<!-- \.entry-content -->', html, re.DOTALL | re.IGNORECASE)
    search_scope = content_match.group(1) if content_match else html
    raw = re.findall(r'<img[^>]+src=["\']([^"\']+)["\']', search_scope, re.IGNORECASE)
    images = []
    for u in raw:
        u = u.strip()
        if u and not u.startswith("data:") and not any(x in u.lower() for x in ["logo", "avatar", "icon", "banner"]):
            if u not in images:
                images.append(u)
    return images

def extract_arenascan_images(html: str) -> list[str]:
    raw = re.findall(r'<img[^>]+(?:data-src|src)=["\'](https?://[^"\']+)["\']', html, re.IGNORECASE)
    images = []
    for u in raw:
        u = u.strip()
        if "arena-bucket" in u or "arenascan.com/wp-content/uploads" in u:
            if not any(x in u.lower() for x in ["logo", "icon", "avatar", "banner"]):
                if u not in images:
                    images.append(u)
    return images

def extract_html_navigation(html: str, target_url: str):
    parsed = urllib.parse.urlparse(target_url)
    domain = parsed.netloc.lower()
    base_url = f"{parsed.scheme}://{parsed.netloc}"

    next_url, prev_url = None, None
    if "mangak.io" in domain:
        m = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html, re.DOTALL)
        if m:
            try:
                data = json.loads(m.group(1))
                page_props = data.get("props", {}).get("pageProps", {})
                nxt = page_props.get("nextChapter")
                prv = page_props.get("previousChapter")
                if nxt and nxt.get("url"):
                    next_url = urllib.parse.urljoin(base_url, nxt["url"])
                if prv and prv.get("url"):
                    prev_url = urllib.parse.urljoin(base_url, prv["url"])
            except Exception:
                pass
    elif "mgeko.cc" in domain:
        nxt = re.search(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*class=["\'][^"\']*(?:nextchap|next)[^"\']*["\']', html, re.I) or \
              re.search(r'<a[^>]+class=["\'][^"\']*(?:nextchap|next)[^"\']*["\'][^>]+href=["\']([^"\']+)["\']', html, re.I)
        prv = re.search(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*class=["\'][^"\']*(?:prevchap|prev)[^"\']*["\']', html, re.I) or \
              re.search(r'<a[^>]+class=["\'][^"\']*(?:prevchap|prev)[^"\']*["\'][^>]+href=["\']([^"\']+)["\']', html, re.I)
        if nxt:
            next_url = urllib.parse.urljoin(base_url, nxt.group(1))
        if prv:
            prev_url = urllib.parse.urljoin(base_url, prv.group(1))
    else:
        nxt = re.search(r'<a[^>]+rel=["\']next["\'][^>]*href=["\']([^"\']+)["\']', html, re.I) or \
              re.search(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*rel=["\']next["\']', html, re.I) or \
              re.search(r'<div[^>]*class=["\'][^"\']*next-post[^"\']*["\'][^>]*>\s*<a[^>]+href=["\']([^"\']+)["\']', html, re.I) or \
              re.search(r'<a[^>]+class=["\'][^"\']*(?:next_page|btn-next)[^"\']*["\'][^>]+href=["\']([^"\']+)["\']', html, re.I)
        prv = re.search(r'<a[^>]+rel=["\']prev(?:ious)?["\'][^>]*href=["\']([^"\']+)["\']', html, re.I) or \
              re.search(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*rel=["\']prev(?:ious)?["\']', html, re.I) or \
              re.search(r'<div[^>]*class=["\'][^"\']*prev-post[^"\']*["\'][^>]*>\s*<a[^>]+href=["\']([^"\']+)["\']', html, re.I) or \
              re.search(r'<a[^>]+class=["\'][^"\']*(?:prev_page|btn-prev)[^"\']*["\'][^>]+href=["\']([^"\']+)["\']', html, re.I)
        if nxt:
            next_url = urllib.parse.urljoin(base_url, nxt.group(1))
        if prv:
            prev_url = urllib.parse.urljoin(base_url, prv.group(1))

    next_info = None
    if next_url:
        m = re.search(r'chapter[/-](\d+)', next_url, re.I)
        next_info = {"url": next_url, "number": int(m.group(1)) if m else None}

    prev_info = None
    if prev_url:
        m = re.search(r'chapter[/-](\d+)', prev_url, re.I)
        prev_info = {"url": prev_url, "number": int(m.group(1)) if m else None}

    return next_info, prev_info

def extract_generic_images(html: str) -> list[str]:
    for extractor in [
        extract_manhuatop_images,
        extract_asurascans_images,
        extract_ravenscans_images,
        extract_mangak_images,
        extract_mgeko_images,
        extract_levelingwithgods_images,
        extract_pickmeupgacha_images,
        extract_magicemperor_images,
        extract_arenascan_images,
    ]:
        imgs = extractor(html)
        if imgs:
            return imgs
    return []

def extract_chapter_images_by_domain(html: str, target_url: str) -> list[str]:
    parsed = urllib.parse.urlparse(target_url)
    domain = parsed.netloc.lower()
    if domain.startswith("www."):
        domain = domain[4:]

    if domain.endswith("mangafire.to"):
        data = mangafire_provider.get_mangafire_chapter_data(target_url)
        return data.get("images", [])

    if domain.endswith("comix.to"):
        data = comix_provider.get_comix_chapter_data(target_url)
        return data.get("images", [])

    if domain.endswith("manhuaus.com"):
        data = manhuaus_provider.get_manhuaus_chapter_data(target_url)
        return data.get("images", [])

    if domain.endswith("mangak.io"):
        return extract_mangak_images(html)

    if domain.endswith("mgeko.cc"):
        return extract_mgeko_images(html)

    if domain.endswith("levelingwithgods.com"):
        return extract_levelingwithgods_images(html)

    if domain.endswith("pickmeupgacha.com"):
        return extract_pickmeupgacha_images(html)

    if domain.endswith("magicemperor.online"):
        return extract_magicemperor_images(html)

    if domain.endswith("arenascan.com"):
        return extract_arenascan_images(html)

    extractors = {
        "asurascans.com": extract_asurascans_images,
        "manhuatop.org": extract_manhuatop_images,
        "ravenscans.org": extract_ravenscans_images,
    }
    extractor = extractors.get(domain, extract_generic_images)
    return extractor(html)

@app.route("/api/chapter-images", methods=["GET"])
def get_chapter_images():
    target_url = request.args.get("url")
    if not target_url:
        return jsonify({"error": "Parâmetro url é obrigatório"}), 400

    parsed = urllib.parse.urlparse(target_url)
    domain = parsed.netloc.lower()
    if domain.startswith("www."):
        domain = domain[4:]

    if domain == "mangafire.to":
        try:
            data = mangafire_provider.get_mangafire_chapter_data(target_url)

            # Sync database if there is a matching MangaFire manhua
            db_data = load_data()
            updated = False
            for m in db_data:
                if "mangafire.to" in m.get("urlTemplate", "").lower():
                    m_hid, _ = mangafire_provider.parse_mangafire_url(m.get("urlTemplate", ""))
                    t_hid, _ = mangafire_provider.parse_mangafire_url(target_url)
                    if m_hid and m_hid == t_hid:
                        if data.get("chapter") is not None:
                            m["currentChapter"] = data["chapter"]
                        if data.get("chapterId") is not None:
                            m["chapterId"] = data["chapterId"]
                        if data.get("next") is not None:
                            m["nextChapter"] = data["next"]
                        if data.get("prev") is not None:
                            m["prevChapter"] = data["prev"]
                        m["updatedAt"] = int(time.time())
                        updated = True
                        break
            if updated:
                save_data(db_data)

            return jsonify(data)
        except Exception as e:
            return jsonify({"error": str(e), "images": []}), 500

    if domain == "comix.to":
        try:
            data = comix_provider.get_comix_chapter_data(target_url)
            if "status" not in data:
                data["status"] = "ok"

            # Sync database if there is a matching Comix manhua
            db_data = load_data()
            updated = False
            for m in db_data:
                if "comix.to" in m.get("urlTemplate", "").lower():
                    m_slug, _, _ = comix_provider.parse_comix_url(m.get("urlTemplate", ""))
                    t_slug, _, _ = comix_provider.parse_comix_url(target_url)
                    if m_slug and m_slug == t_slug:
                        if data.get("chapter") is not None:
                            m["currentChapter"] = data["chapter"]
                        if data.get("chapterId") is not None:
                            m["chapterId"] = data["chapterId"]
                        if data.get("next") is not None:
                            m["nextChapter"] = data["next"]
                        if data.get("prev") is not None:
                            m["prevChapter"] = data["prev"]
                        m["updatedAt"] = int(time.time())
                        updated = True
                        break
            if updated:
                save_data(db_data)

            return jsonify(data)
        except Exception as e:
            return jsonify({"error": str(e), "images": []}), 500

    if domain == "manhuaus.com":
        try:
            data = manhuaus_provider.get_manhuaus_chapter_data(target_url)
            if "status" not in data:
                data["status"] = "ok"

            # Sync database if there is a matching Manhuaus manhua
            db_data = load_data()
            updated = False
            for m in db_data:
                if "manhuaus.com" in m.get("urlTemplate", "").lower():
                    m_slug, _ = manhuaus_provider.parse_manhuaus_url(m.get("urlTemplate", ""))
                    t_slug, _ = manhuaus_provider.parse_manhuaus_url(target_url)
                    if m_slug and m_slug == t_slug:
                        if data.get("chapter") is not None:
                            m["currentChapter"] = data["chapter"]
                        if data.get("next") is not None:
                            m["nextChapter"] = data["next"]
                        if data.get("prev") is not None:
                            m["prevChapter"] = data["prev"]
                        m["updatedAt"] = int(time.time())
                        updated = True
                        break
            if updated:
                save_data(db_data)

            return jsonify(data)
        except Exception as e:
            return jsonify({"error": str(e), "images": []}), 500

    try:
        req = urllib.request.Request(
            target_url,
            headers={
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
            }
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode("utf-8", errors="ignore")

        chapter_imgs = extract_chapter_images_by_domain(html, target_url)
        next_info, prev_info = extract_html_navigation(html, target_url)

        res_payload = {
            "status": "ok",
            "count": len(chapter_imgs),
            "images": chapter_imgs
        }
        if next_info:
            res_payload["next"] = next_info
        if prev_info:
            res_payload["prev"] = prev_info

        # Sync database if there is a matching manhua
        db_data = load_data()
        updated = False
        for m in db_data:
            tmpl = m.get("urlTemplate", "")
            if tmpl:
                tmpl_domain = urllib.parse.urlparse(tmpl).netloc.lower()
                if tmpl_domain.startswith("www."):
                    tmpl_domain = tmpl_domain[4:]
                if tmpl_domain and (tmpl_domain in domain or domain in tmpl_domain):
                    if next_info:
                        m["nextChapter"] = next_info
                    if prev_info:
                        m["prevChapter"] = prev_info
                    m["updatedAt"] = int(time.time())
                    updated = True
                    break
        if updated:
            save_data(db_data)

        return jsonify(res_payload)
    except Exception as e:
        return jsonify({"error": str(e), "images": []}), 500

def extract_images_from_url(target_url):
    parsed = urllib.parse.urlparse(target_url)
    domain = parsed.netloc.lower()
    if domain.startswith("www."):
        domain = domain[4:]

    if domain == "mangafire.to":
        data = mangafire_provider.get_mangafire_chapter_data(target_url)
        return data.get("images", [])

    if domain == "comix.to":
        data = comix_provider.get_comix_chapter_data(target_url)
        return data.get("images", [])

    if domain == "manhuaus.com":
        data = manhuaus_provider.get_manhuaus_chapter_data(target_url)
        return data.get("images", [])

    req = urllib.request.Request(
        target_url,
        headers={
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        }
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        html = resp.read().decode("utf-8", errors="ignore")
    return extract_chapter_images_by_domain(html, target_url)

@app.route("/api/manhuas/<int:item_id>/batch-chapter-images", methods=["GET"])
def get_batch_chapter_images(item_id):
    db_data = load_data()
    manhua = next((m for m in db_data if m["id"] == item_id), None)
    if not manhua:
        return jsonify({"error": "Obra não encontrada"}), 404

    try:
        start = int(request.args.get("start", ""))
        end = int(request.args.get("end", ""))
    except (ValueError, TypeError):
        return jsonify({"error": "Parâmetros 'start' e 'end' são obrigatórios e devem ser inteiros válidos"}), 400

    if start < 1 or end < start:
        return jsonify({"error": "Intervalo de capítulos inválido"}), 400

    if (end - start + 1) > 50:
        return jsonify({"error": "Limite máximo de 50 capítulos por lote excedido"}), 400

    last_chap = manhua.get("lastChapter")
    if last_chap is not None and (start > last_chap or end > last_chap):
        return jsonify({"error": f"Capítulo excede o último episódio disponível ({last_chap})"}), 400

    url_template = manhua.get("urlTemplate", "")

    def process_chapter(chap_num):
        chap_url = url_template.replace("{chapter}", str(chap_num))
        try:
            images = extract_images_from_url(chap_url)
            return {"chapter": chap_num, "targetUrl": chap_url, "images": images}
        except Exception as e:
            return {"chapter": chap_num, "targetUrl": chap_url, "images": [], "error": str(e)}

    chapters_to_fetch = list(range(start, end + 1))
    with ThreadPoolExecutor(max_workers=5) as executor:
        results = list(executor.map(process_chapter, chapters_to_fetch))

    results.sort(key=lambda x: x["chapter"])

    return jsonify({
        "manhuaId": manhua["id"],
        "title": manhua.get("title", ""),
        "range": {"start": start, "end": end},
        "totalChapters": len(results),
        "chapters": results
    })

@app.route("/api/proxy-image", methods=["GET"])
def proxy_image():
    img_url = request.args.get("url")
    if not img_url:
        return jsonify({"error": "Parâmetro url é obrigatório"}), 400

    parsed = urllib.parse.urlparse(img_url)
    netloc = parsed.netloc.lower()
    custom_cookie = None
    user_agent = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

    if "asurascans.com" in netloc:
        referer = "https://asurascans.com/"
    elif "ravenscans.org" in netloc:
        referer = "https://ravenscans.org/"
    elif "mangafire.to" in netloc or "mfcdn" in netloc:
        referer = "https://mangafire.to/"
    elif ".site" in netloc or "comix.to" in netloc:
        referer = None
    elif "qvzr" in netloc or "mangak.io" in netloc:
        referer = "https://mangak.io/"
    elif "manhuaus.com" in netloc:
        referer = "https://manhuaus.com/"
        user_agent = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        clearance = manhuaus_provider.get_cached_clearance()
        if clearance:
            custom_cookie = f"cf_clearance={clearance}"
    else:
        referer = f"{parsed.scheme}://{parsed.netloc}/"

    try:
        headers = {
            "User-Agent": user_agent
        }
        if referer:
            headers["Referer"] = referer
        if custom_cookie:
            headers["Cookie"] = custom_cookie

        req = urllib.request.Request(img_url, headers=headers)
        with urllib.request.urlopen(req, timeout=20) as resp:
            content = resp.read()
            content_type = resp.headers.get("Content-Type", "image/jpeg")
            return Response(content, mimetype=content_type, headers={"Cache-Control": "public, max-age=86400"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def run_daily_update_check(check_all: bool = False, target_weekday: int = None) -> dict:
    if target_weekday is None:
        target_weekday = datetime.now().weekday()

    db_data = load_data()
    eligible = []
    for m in db_data:
        if m.get("isHiatus", False):
            continue
        if m.get("lastChapter") is None:
            continue
        if check_all or m.get("updateDay") == target_weekday:
            eligible.append(m)

    results = []
    new_found = 0

    for m in eligible:
        try:
            current_last = int(m["lastChapter"])
            next_candidate = current_last + 1
            url_template = m.get("urlTemplate", "")
            if not url_template:
                continue
            target_url = url_template.replace("{chapter}", str(next_candidate))
            images = extract_images_from_url(target_url)
            if images and len(images) > 0:
                m["lastChapter"] = next_candidate
                m["updatedAt"] = int(time.time())
                add_notification(m["id"], m.get("title", ""), next_candidate)
                new_found += 1
                results.append({
                    "id": m["id"],
                    "title": m.get("title", ""),
                    "newChapter": next_candidate,
                    "status": "updated"
                })
            else:
                results.append({
                    "id": m["id"],
                    "title": m.get("title", ""),
                    "attemptedChapter": next_candidate,
                    "status": "no_new_chapter"
                })
        except Exception as e:
            results.append({
                "id": m["id"],
                "title": m.get("title", ""),
                "attemptedChapter": m.get("lastChapter", 0) + 1,
                "status": "error",
                "error": str(e)
            })

    if new_found > 0:
        save_data(db_data)

    return {
        "status": "ok",
        "checkedCount": len(eligible),
        "newChaptersFound": new_found,
        "results": results
    }

@app.route("/api/routine/run-check", methods=["POST"])
def trigger_update_check():
    payload = request.get_json(silent=True) or {}
    check_all = bool(payload.get("checkAll", False))
    result = run_daily_update_check(check_all=check_all)
    return jsonify(result)

_last_run_date = None
_scheduler_started = False
_scheduler_lock = threading.Lock()

def _routine_scheduler_loop():
    global _last_run_date
    while True:
        try:
            now = datetime.now()
            today_str = now.strftime("%Y-%m-%d")
            if now.hour == 23 and now.minute == 50 and _last_run_date != today_str:
                _last_run_date = today_str
                run_daily_update_check(check_all=False, target_weekday=now.weekday())
        except Exception:
            pass
        time.sleep(30)

def start_routine_scheduler():
    global _scheduler_started
    with _scheduler_lock:
        if not _scheduler_started:
            _scheduler_started = True
            t = threading.Thread(target=_routine_scheduler_loop, daemon=True)
            t.start()

start_routine_scheduler()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
