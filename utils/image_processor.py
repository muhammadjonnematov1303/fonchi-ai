import io
from PIL import Image, ImageFilter, ImageEnhance
from rembg import remove, new_session

_SESSION = None
MAX_SIZE = 1800  # Yuqori sifat uchun


def get_session():
    global _SESSION
    if _SESSION is None:
        _SESSION = new_session("u2net")
    return _SESSION


def _prep(input_path: str):
    img = Image.open(input_path).convert("RGB")
    w, h = img.size
    if max(w, h) > MAX_SIZE:
        scale = MAX_SIZE / max(w, h)
        img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue(), img.size


def _sharpen_product(img: Image.Image) -> Image.Image:
    img = img.filter(ImageFilter.UnsharpMask(radius=0.5, percent=220, threshold=1))
    img = img.filter(ImageFilter.UnsharpMask(radius=1.8, percent=140, threshold=3))
    img = ImageEnhance.Sharpness(img).enhance(2.0)
    img = ImageEnhance.Contrast(img).enhance(1.18)
    img = ImageEnhance.Color(img).enhance(1.12)
    return img


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
    scale = min(max_w / fg_w, max_h / fg_h) * 1.35
    new_w, new_h = int(fg_w * scale), int(fg_h * scale)
    foreground = foreground.resize((new_w, new_h), Image.LANCZOS)

    # Foreground tiniqlash (alpha saqlanib)
    r, g, b, a = foreground.split()
    rgb = _sharpen_product(Image.merge("RGB", (r, g, b)))
    r2, g2, b2 = rgb.split()
    foreground = Image.merge("RGBA", (r2, g2, b2, a))

    offset_x = (bg_w - new_w) // 2
    offset_y = padding_top + (max_h - new_h) // 2

    canvas = Image.new("RGBA", (bg_w, bg_h))
    canvas.paste(background, (0, 0))
    canvas.paste(foreground, (offset_x, offset_y), foreground)
    return canvas.convert("RGB")


def process_images(person_path: str, bg_path: str, output_path: str):
    foreground = remove_background(person_path)
    result = apply_background(foreground, bg_path)
    result.save(output_path, "JPEG", quality=97, subsampling=0)


def remove_bg_only(input_path: str) -> io.BytesIO:
    data, _ = _prep(input_path)
    result = remove(data, session=get_session())
    fg = Image.open(io.BytesIO(result)).convert("RGBA")

    r, g, b, a = fg.split()
    a = a.point(lambda p: 0 if p < 128 else 255)
    fg = Image.merge("RGBA", (r, g, b, a))

    # Oq fonga joylash
    white = Image.new("RGB", fg.size, (255, 255, 255))
    white.paste(fg, mask=fg.split()[3])

    # Tiniqlash
    white = _sharpen_product(white)

    out = io.BytesIO()
    white.save(out, "JPEG", quality=97, subsampling=0)
    out.seek(0)
    return out


def preload_model():
    get_session()