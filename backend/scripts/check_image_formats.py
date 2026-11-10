"""核实作文素材图片的真实格式，并检查是否存在 Pillow 依赖。"""
import glob
import importlib.util
from pathlib import Path

print("Pillow 可用:", importlib.util.find_spec("pillow") is not None)

for path_text in sorted(glob.glob(str(Path("../作文/*.jpg"))))[:5]:
    path = Path(path_text)
    head = path.read_bytes()[:12]
    if head.startswith(b"\xff\xd8\xff"):
        detected = "JPEG"
    elif head.startswith(b"\x89PNG\r\n\x1a\n"):
        detected = "PNG"
    elif head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        detected = "WEBP"
    else:
        detected = "OTHER"
    print(path.name, "声明扩展名=", path.suffix, "真实格式=", detected)