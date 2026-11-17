"""同一张作文图片的识别耗时对比：原图 vs 前端同参数压缩图。"""
import io
import time
from pathlib import Path

import httpx
from PIL import Image

CFG = {}
for line in io.open(".env", encoding="utf-8"):
    stripped = line.strip()
    if stripped and not stripped.startswith("#") and "=" in stripped:
        key, _, value = stripped.partition("=")
        CFG[key] = value

BASE = "http://127.0.0.1:8000/api/v1"
PASSWORD = CFG.get("DEMO_PASSWORD", "") or "Demo@2026"
client = httpx.Client(timeout=30)
login = client.post(f"{BASE}/auth/login", json={"username": "demo_student", "password": PASSWORD})
headers = {"Authorization": f"Bearer {login.json()['data']['access_token']}"}
tokens = []


def upload(data: bytes, name: str, mime: str) -> str:
    response = client.post(
        f"{BASE}/essays/upload-image",
        headers=headers,
        files={"image": (name, data, mime)},
    )
    token = response.json()["data"]["image_token"]
    tokens.append(token)
    return token


def recognize(token: str) -> tuple[int, float, int]:
    started = time.perf_counter()
    response = client.post(
        f"{BASE}/essays/ocr",
        headers=headers,
        json={"image_token": token},
        timeout=300,
    )
    elapsed = time.perf_counter() - started
    data = response.json().get("data", {})
    return response.status_code, round(elapsed, 1), len(data.get("text") or "")


source = max(Path("../作文").glob("*.jpg"), key=lambda item: item.stat().st_size)
original_bytes = source.read_bytes()
image = Image.open(io.BytesIO(original_bytes)).convert("RGB")
width, height = image.size
scale = min(1, 1600 / max(width, height))
resized = image.resize((max(1, round(width * scale)), max(1, round(height * scale))), Image.LANCZOS)
buffer = io.BytesIO()
resized.save(buffer, "JPEG", quality=82)
compressed_bytes = buffer.getvalue()

print(f"FILE {source.name} original={width}x{height} {round(len(original_bytes)/1024)}KB")
print(f"COMPRESSED {resized.size[0]}x{resized.size[1]} {round(len(compressed_bytes)/1024)}KB")

original_mime = "image/png" if original_bytes[:8] == b"\x89PNG\r\n\x1a\n" else "image/jpeg"
t1 = upload(original_bytes, source.name, original_mime)
status1, seconds1, length1 = recognize(t1)
print(f"ORIGINAL_OCR http={status1} seconds={seconds1} chars={length1}")

t2 = upload(compressed_bytes, "compressed.jpg", "image/jpeg")
status2, seconds2, length2 = recognize(t2)
print(f"COMPRESSED_OCR http={status2} seconds={seconds2} chars={length2}")
print(f"DELTA_SECONDS {round(seconds1 - seconds2, 1)}")

for token in tokens:
    path = Path(token)
    if not path.is_absolute():
        path = Path("..") / token if not Path(token).exists() else Path(token)
    if path.exists() and path.is_file():
        path.unlink(missing_ok=True)