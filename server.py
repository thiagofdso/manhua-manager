import os
import json
import time
import re
import urllib.request
import urllib.parse
from flask import Flask, request, jsonify, send_from_directory, Response
from flask_cors import CORS

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, "database.json")

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

@app.route("/")
def index():
    return send_from_directory(BASE_DIR, "index.html")

@app.route("/<path:filename>")
def static_files(filename):
    return send_from_directory(BASE_DIR, filename)

@app.route("/api/manhuas", methods=["GET"])
def get_manhuas():
    data = load_data()
    data.sort(key=lambda x: x.get("updatedAt", 0), reverse=True)
    return jsonify(data)

@app.route("/api/manhuas", methods=["POST"])
def add_manhua():
    payload = request.get_json() or {}
    if not payload.get("title") or not payload.get("urlTemplate") or payload.get("currentChapter") is None:
        return jsonify({"error": "Dados inválidos"}), 400
    
    data = load_data()
    new_item = {
        "id": int(time.time() * 1000),
        "title": payload["title"].strip(),
        "urlTemplate": payload["urlTemplate"].strip(),
        "currentChapter": max(1, int(payload["currentChapter"])),
        "updatedAt": int(time.time())
    }
    data.append(new_item)
    save_data(data)
    return jsonify({"status": "ok", "item": new_item})

@app.route("/api/manhuas/<int:item_id>", methods=["PATCH"])
def update_chapter(item_id):
    payload = request.get_json() or {}
    data = load_data()
    for m in data:
        if m["id"] == item_id:
            if "title" in payload and str(payload["title"]).strip():
                m["title"] = str(payload["title"]).strip()
            if "urlTemplate" in payload and str(payload["urlTemplate"]).strip():
                m["urlTemplate"] = str(payload["urlTemplate"]).strip()
            if "chapter" in payload:
                m["currentChapter"] = max(1, int(payload["chapter"]))
            elif "delta" in payload:
                m["currentChapter"] = max(1, m["currentChapter"] + int(payload["delta"]))
            m["updatedAt"] = int(time.time())
            save_data(data)
            return jsonify({"status": "ok", "item": m})
    return jsonify({"error": "Item não encontrado"}), 404

@app.route("/api/manhuas/<int:item_id>", methods=["DELETE"])
def delete_manhua(item_id):
    data = [m for m in load_data() if m["id"] != item_id]
    save_data(data)
    return jsonify({"status": "ok"})

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

def extract_generic_images(html: str) -> list[str]:
    for extractor in [extract_manhuatop_images, extract_asurascans_images, extract_ravenscans_images]:
        imgs = extractor(html)
        if imgs:
            return imgs
    return []

def extract_chapter_images_by_domain(html: str, target_url: str) -> list[str]:
    parsed = urllib.parse.urlparse(target_url)
    domain = parsed.netloc.lower()
    if domain.startswith("www."):
        domain = domain[4:]

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

        return jsonify({
            "status": "ok",
            "count": len(chapter_imgs),
            "images": chapter_imgs
        })
    except Exception as e:
        return jsonify({"error": str(e), "images": []}), 500

@app.route("/api/proxy-image", methods=["GET"])
def proxy_image():
    img_url = request.args.get("url")
    if not img_url:
        return jsonify({"error": "Parâmetro url é obrigatório"}), 400

    parsed = urllib.parse.urlparse(img_url)
    if "asurascans.com" in parsed.netloc.lower():
        referer = "https://asurascans.com/"
    elif "ravenscans.org" in parsed.netloc.lower():
        referer = "https://ravenscans.org/"
    else:
        referer = f"{parsed.scheme}://{parsed.netloc}/"

    try:
        req = urllib.request.Request(
            img_url,
            headers={
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Referer": referer
            }
        )
        with urllib.request.urlopen(req, timeout=20) as resp:
            content = resp.read()
            content_type = resp.headers.get("Content-Type", "image/jpeg")
            return Response(content, mimetype=content_type, headers={"Cache-Control": "public, max-age=86400"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
