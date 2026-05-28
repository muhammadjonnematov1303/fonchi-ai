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
    img = Image.open(io.BytesIO(result)).convert("RGBA")
    return img


def apply_background(foreground: Image.Image, bg_path: str) -> Image.Image:
    background = Image.open(bg_path).convert("RGBA")
    fg_w, fg_h = foreground.size

    # Background ni foreground o'lchamiga cover qilish (proporsiya saqlanib, crop markazdan)
    bg_ratio = background.width / background.height
    fg_ratio = fg_w / fg_h
    if bg_ratio > fg_ratio:
        new_h = fg_h
        new_w = int(new_h * bg_ratio)
    else:
        new_w = fg_w
        new_h = int(new_w / bg_ratio)
    background = background.resize((new_w, new_h), Image.LANCZOS)
    left = (new_w - fg_w) // 2
    top  = (new_h - fg_h) // 2
    background = background.crop((left, top, left + fg_w, top + fg_h))

    result = Image.new("RGBA", (fg_w, fg_h))
    result.paste(background, (0, 0))
    result.paste(foreground, (0, 0), foreground)
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
    # Kiruvchi rasmni 2x ga kattalashtirish — sifat oshadi
    src = Image.open(input_path).convert("RGB")
    orig_w, orig_h = src.size
    upscaled = src.resize((orig_w * 2, orig_h * 2), Image.LANCZOS)
    upscaled_bytes = io.BytesIO()
    upscaled.save(upscaled_bytes, "PNG")
    upscaled_bytes.seek(0)

    result = remove(
        upscaled_bytes.read(),
        session=get_session(),
        alpha_matting=True,
        alpha_matting_foreground_threshold=245,
        alpha_matting_background_threshold=15,
        alpha_matting_erode_size=5,
    )

    img = Image.open(io.BytesIO(result)).convert("RGBA")

    # Alpha kanalini tozalash: qirralarni yumshatish
    r, g, b, a = img.split()
    a = a.filter(ImageFilter.GaussianBlur(0.8))
    a = a.point(lambda p: 0 if p < 20 else (255 if p > 235 else p))
    img = Image.merge("RGBA", (r, g, b, a))

    # Asl o'lchamga qaytarish
    img = img.resize((orig_w, orig_h), Image.LANCZOS)

    output = io.BytesIO()
    img.save(output, "PNG", optimize=True)
    output.seek(0)
    return output


def preload_model():
    get_session()
