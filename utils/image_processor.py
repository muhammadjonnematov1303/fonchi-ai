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
    result = remove(
        data,
        session=get_session(),
        alpha_matting=True,
        alpha_matting_foreground_threshold=240,
        alpha_matting_background_threshold=20,
        alpha_matting_erode_size=3,
    )
    return Image.open(io.BytesIO(result)).convert("RGBA")


def apply_background(foreground: Image.Image, bg_path: str) -> Image.Image:
    background = Image.open(bg_path).convert("RGBA")
    bg_w, bg_h = background.size

    # Foreground ni fon o'lchamiga to'liq sig'dirish (proporsiya saqlanib, markazga)
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
    src = Image.open(input_path).convert("RGB")
    orig_w, orig_h = src.size
    upscaled = src.resize((orig_w * 2, orig_h * 2), Image.LANCZOS)
    buf = io.BytesIO()
    upscaled.save(buf, "PNG")
    buf.seek(0)

    result = remove(
        buf.read(),
        session=get_session(),
        alpha_matting=True,
        alpha_matting_foreground_threshold=245,
        alpha_matting_background_threshold=15,
        alpha_matting_erode_size=5,
    )

    img = Image.open(io.BytesIO(result)).convert("RGBA")
    r, g, b, a = img.split()
    a = a.filter(ImageFilter.GaussianBlur(0.8))
    a = a.point(lambda p: 0 if p < 20 else (255 if p > 235 else p))
    img = Image.merge("RGBA", (r, g, b, a))
    img = img.resize((orig_w, orig_h), Image.LANCZOS)

    output = io.BytesIO()
    img.save(output, "PNG", optimize=True)
    output.seek(0)
    return output


def preload_model():
    get_session()