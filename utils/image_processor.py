import io
import os
from PIL import Image, ImageFilter, ImageEnhance
from rembg import remove, new_session

_SESSION = None


def get_session():
    global _SESSION
    if _SESSION is None:
        _SESSION = new_session("u2net")
    return _SESSION


def remove_background(input_path: str) -> Image.Image:
    with open(input_path, "rb") as f:
        data = f.read()
    result = remove(data, session=get_session())
    img = Image.open(io.BytesIO(result)).convert("RGBA")
    return _clean_alpha(img)


def _clean_alpha(img: Image.Image) -> Image.Image:
    r, g, b, a = img.split()
    a = a.filter(ImageFilter.MedianFilter(3))
    a = a.point(lambda p: 0 if p < 100 else (255 if p > 180 else p))
    a = a.filter(ImageFilter.GaussianBlur(0.5))
    return Image.merge("RGBA", (r, g, b, a))


def _enhance(img: Image.Image) -> Image.Image:
    """Rasmni avtomatik tiniqlash va yaxshilash."""
    # 1. Unsharp mask — qirralarni aniqlashtirish
    img = img.filter(ImageFilter.UnsharpMask(radius=1.5, percent=160, threshold=2))
    img = img.filter(ImageFilter.UnsharpMask(radius=0.5, percent=80,  threshold=1))
    # 2. Keskinlik (sharpness)
    img = ImageEnhance.Sharpness(img).enhance(1.6)
    # 3. Kontrast
    img = ImageEnhance.Contrast(img).enhance(1.12)
    # 4. Yorqinlik (brightness) — biroz ko'tarish
    img = ImageEnhance.Brightness(img).enhance(1.04)
    # 5. Rang to'yinganlik
    img = ImageEnhance.Color(img).enhance(1.10)
    return img


def apply_background(foreground: Image.Image, bg_path: str) -> Image.Image:
    background = Image.open(bg_path).convert("RGBA")
    bg_w, bg_h = background.size

    # Pastki 22% — logolar va text uchun saqlanadi
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

    # Gorizontal: markazda; vertikal: yuqori qismda
    offset_x = (bg_w - new_fg_w) // 2
    offset_y = padding_top + (max_h - new_fg_h) // 2

    result = Image.new("RGBA", (bg_w, bg_h))
    result.paste(background, (0, 0))
    result.paste(foreground, (offset_x, offset_y), foreground)
    return result.convert("RGB")


def process_images(person_path: str, bg_path: str, output_path: str):
    foreground = remove_background(person_path)
    result = apply_background(foreground, bg_path)
    result = _enhance(result)
    result.save(output_path, "JPEG", quality=97, subsampling=0)


def remove_bg_only(input_path: str) -> io.BytesIO:
    with open(input_path, "rb") as f:
        data = f.read()
    result = remove(data, session=get_session())
    img = Image.open(io.BytesIO(result)).convert("RGBA")
    img = _clean_alpha(img)

    # RGB qismini ham yaxshilaymiz (alpha saqlanib)
    r, g, b, a = img.split()
    rgb = Image.merge("RGB", (r, g, b))
    rgb = _enhance(rgb)
    r2, g2, b2 = rgb.split()
    img = Image.merge("RGBA", (r2, g2, b2, a))

    output = io.BytesIO()
    img.save(output, "PNG", optimize=True)
    output.seek(0)
    return output


def preload_model():
    get_session()