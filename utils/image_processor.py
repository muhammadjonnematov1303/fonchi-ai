import io
from PIL import Image, ImageFilter, ImageEnhance
from rembg import remove, new_session

_SESSION = None
MAX_SIZE = 1024  # Qayta ishlash uchun maksimal o'lcham (tezlik)


def get_session():
    global _SESSION
    if _SESSION is None:
        _SESSION = new_session("u2net")
    return _SESSION


def _prep(input_path: str):
    """Rasmni o'q va kerak bo'lsa kichraytir."""
    img = Image.open(input_path).convert("RGB")
    w, h = img.size
    if max(w, h) > MAX_SIZE:
        scale = MAX_SIZE / max(w, h)
        img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue(), img.size


def remove_background(input_path: str) -> Image.Image:
    data, _ = _prep(input_path)
    result = remove(data, session=get_session())
    img = Image.open(io.BytesIO(result)).convert("RGBA")
    r, g, b, a = img.split()
    a = a.point(lambda p: 0 if p < 128 else 255)
    return Image.merge("RGBA", (r, g, b, a))


def apply_background(foreground: Image.Image, bg_path: str) -> Image.Image:
    background = Image.open(bg_path).convert("RGBA")
    bg_w, bg_h = background.size

    usable_h = int(bg_h * 0.78)
    padding_x = int(bg_w * 0.05)
    padding_top = int(bg_h * 0.04)
    max_w = bg_w - padding_x * 2
    max_h = usable_h - padding_top

    fg_w, fg_h = foreground.size
    scale = min(max_w / fg_w, max_h / fg_h)
    foreground = foreground.resize((int(fg_w * scale), int(fg_h * scale)), Image.LANCZOS)

    offset_x = (bg_w - int(fg_w * scale)) // 2
    offset_y = padding_top + (max_h - int(fg_h * scale)) // 2

    canvas = Image.new("RGBA", (bg_w, bg_h))
    canvas.paste(background, (0, 0))
    canvas.paste(foreground, (offset_x, offset_y), foreground)
    rgb = canvas.convert("RGB")
    return _enhance(rgb)


def _enhance(img: Image.Image) -> Image.Image:
    img = img.filter(ImageFilter.UnsharpMask(radius=1.2, percent=150, threshold=2))
    img = ImageEnhance.Sharpness(img).enhance(1.4)
    img = ImageEnhance.Contrast(img).enhance(1.08)
    return img


def process_images(person_path: str, bg_path: str, output_path: str):
    foreground = remove_background(person_path)
    result = apply_background(foreground, bg_path)
    result.save(output_path, "JPEG", quality=95, subsampling=0)


def remove_bg_only(input_path: str) -> io.BytesIO:
    data, _ = _prep(input_path)
    result = remove(data, session=get_session())
    img = Image.open(io.BytesIO(result)).convert("RGBA")
    r, g, b, a = img.split()
    a = a.point(lambda p: 0 if p < 128 else 255)
    img = Image.merge("RGBA", (r, g, b, a))
    r2, g2, b2, _ = img.split()
    rgb = _enhance(Image.merge("RGB", (r2, g2, b2)))
    r3, g3, b3 = rgb.split()
    out = io.BytesIO()
    Image.merge("RGBA", (r3, g3, b3, a)).save(out, "PNG")
    out.seek(0)
    return out


def preload_model():
    get_session()