from PIL import Image, ImageDraw
import os

def create_icon(size, filename):
    img = Image.new("RGBA", (size, size), color=(18, 18, 20, 255))
    draw = ImageDraw.Draw(img)
    
    # Outer circle with accent color (#8257e6)
    pad = int(size * 0.08)
    draw.rounded_rectangle([pad, pad, size - pad, size - pad], radius=int(size * 0.2), fill=(130, 87, 230, 255))
    
    # Book / Bookmark shape
    cx, cy = size // 2, size // 2
    w = int(size * 0.45)
    h = int(size * 0.5)
    left = cx - w // 2
    top = cy - h // 2
    draw.rectangle([left, top, cx - int(size * 0.02), top + h], fill=(255, 255, 255, 240))
    draw.rectangle([cx + int(size * 0.02), top, left + w, top + h], fill=(235, 235, 245, 240))
    
    # Bookmark ribbon
    ribbon_w = int(size * 0.1)
    ribbon_h = int(size * 0.25)
    rx = cx - ribbon_w // 2
    draw.rectangle([rx, top, rx + ribbon_w, top + ribbon_h], fill=(255, 180, 50, 255))
    
    img.save(filename, "PNG")

if __name__ == "__main__":
    base = os.path.dirname(os.path.abspath(__file__))
    create_icon(192, os.path.join(base, "icon-192.png"))
    create_icon(512, os.path.join(base, "icon-512.png"))
    print("Icons generated successfully.")
