import os
import json
import time
from flask import Flask, request, jsonify, send_from_directory
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

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
