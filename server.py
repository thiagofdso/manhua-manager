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

        raw_imgs = re.findall(r'<img[^>]+src=[\"\']([^\"\']+)[\"\'][^>]*class=[\"\'][^\"\']*wp-manga-chapter-img[^\"\']*[\"\']', html, re.IGNORECASE)
        raw_imgs += re.findall(r'<img[^>]+class=[\"\'][^\"\']*wp-manga-chapter-img[^\"\']*[\"\'][^>]+src=[\"\']([^\"\']+)[\"\']', html, re.IGNORECASE)

        seen = set()
        chapter_imgs = []
        for img in raw_imgs:
            clean = img.strip()
            if clean and clean not in seen and "about_manhuatop" not in clean:
                seen.add(clean)
                chapter_imgs.append(clean)

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
