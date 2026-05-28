import io
from PIL import Image, ImageFilter, ImageEnhance
from rembg import remove, new_session
from config import IMAGES_DIR
import os

_SESSION = None


def get_session():
    global _SESSION
    if _SESSION is None:
        _SESSION = new_session("birefnet-general")
    return _SESSION


def remove_background(input_path: str) -> Image.Image:
    with open(input_path, "rb") as f:
        data = f.read()
    result = remove(data, session=get_session())
    img = Image.open(io.BytesIO(result)).convert("RGBA")
    r, g, b, a = img.split()
    a = a.point(lambda p: 0 if p < 128 else 255)
    return Image.merge("RGBA", (r, g, b, a))


def apply_background(foreground: Image.Image, bg_path: str) -> Image.Image:
    background = Image.open(bg_path).convert("RGBA")
    bg_w, bg_h = background.size

    # Pastki 22% text/logolar uchun, yuqori qismga joylash
    usable_h = int(bg_h * 0.78)
    padding_x = int(bg_w * 0.05)
    padding_top = int(bg_h * 0.04)
    max_w = bg_w - padding_x * 2
    max_h = usable_h - padding_top

    fg_w, fg_h = foreground.size
    scale = min(max_w / fg_w, max_h / fg_h)
    new_fg_w = int(fg_w * scale)
    new_fg_h = int(fg_h * scale)
    foreground = foreground.resize((new_fg_w, new_fg_h), Image.LANCZOS)

    offset_x = (bg_w - new_fg_w) // 2
    offset_y = padding_top + (max_h - new_fg_h) // 2

    canvas = Image.new("RGBA", (bg_w, bg_h))
    canvas.paste(background, (0, 0))
    canvas.paste(foreground, (offset_x, offset_y), foreground)
    rgb = canvas.convert("RGB")
    return _enhance(rgb)


def _enhance(img: Image.Image) -> Image.Image:
    img = img.filter(ImageFilter.UnsharpMask(radius=1.2, percent=150, threshold=2))
    img = ImageEnhance.Sharpness(img).enhance(1.5)
    img = ImageEnhance.Contrast(img).enhance(1.1)
    return img


def process_images(person_path: str, bg_path: str, output_path: str):
    foreground = remove_background(person_path)
    result = apply_background(foreground, bg_path)
    result.save(output_path, "JPEG", quality=95, subsampling=0)


def remove_bg_only(input_path: str) -> io.BytesIO:
    with open(input_path, "rb") as f:
        data = f.read()
    result = remove(data, session=get_session())
    img = Image.open(io.BytesIO(result)).convert("RGBA")
    r, g, b, a = img.split()
    a = a.point(lambda p: 0 if p < 128 else 255)
    img = Image.merge("RGBA", (r, g, b, a))
    rgb = Image.merge("RGB", img.split()[:3])
    rgb = _enhance(rgb)
    r2, g2, b2 = rgb.split()
    img = Image.merge("RGBA", (r2, g2, b2, a))
    output = io.BytesIO()
    img.save(output, "PNG")
    output.seek(0)
    return output


def preload_model():
    get_session()