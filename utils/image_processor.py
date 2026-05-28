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
    """Alpha kanalini tozalash: shovqin va yarim shaffof piksellarni yo'qotish."""
    r, g, b, a = img.split()
    a = a.filter(ImageFilter.MedianFilter(3))
    a = a.point(lambda p: 0 if p < 100 else (255 if p > 180 else p))
    a = a.filter(ImageFilter.GaussianBlur(0.5))
    return Image.merge("RGBA", (r, g, b, a))


def apply_background(foreground: Image.Image, bg_path: str) -> Image.Image:
    background = Image.open(bg_path).convert("RGBA")
    bg_w, bg_h = background.size

    fg_w, fg_h = foreground.size
    scale = min(bg_w / fg_w, bg_h / fg_h)
    new_fg_w = int(fg_w * scale)
    new_fg_h = int(fg_h * scale)
    foreground = foreground.resize((new_fg_w, new_fg_h), Image.LANCZOS)

    offset_x = (bg_w - new_fg_w) // 2
    offset_y = (bg_h - new_fg_h) // 2

    result = Image.new("RGBA", (bg_w, bg_h))
    result.paste(background, (0, 0))
    result.paste(foreground, (offset_x, offset_y), foreground)
    return result.convert("RGB")


def _sharpen(img: Image.Image) -> Image.Image:
    img = img.filter(ImageFilter.UnsharpMask(radius=1.0, percent=130, threshold=2))
    img = ImageEnhance.Contrast(img).enhance(1.08)
    img = ImageEnhance.Color(img).enhance(1.05)
    return img


def process_images(person_path: str, bg_path: str, output_path: str):
    foreground = remove_background(person_path)
    result = apply_background(foreground, bg_path)
    result = _sharpen(result)
    result.save(output_path, "JPEG", quality=97, subsampling=0)


def remove_bg_only(input_path: str) -> io.BytesIO:
    with open(input_path, "rb") as f:
        data = f.read()
    result = remove(data, session=get_session())
    img = Image.open(io.BytesIO(result)).convert("RGBA")
    img = _clean_alpha(img)
    output = io.BytesIO()
    img.save(output, "PNG", optimize=True)
    output.seek(0)
    return output


def preload_model():
    get_session()