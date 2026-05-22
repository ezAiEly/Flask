from PIL import Image, ImageDraw, ImageFont
import os


def add_watermark(image_path, watermark_text="Video Community", output_path=None):
    img = Image.open(image_path).convert("RGBA")
    width, height = img.size

    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    try:
        font_size = max(14, min(width, height) // 30)
        font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", size=font_size)
    except OSError:
        font = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), watermark_text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    x = width - tw - 20
    y = height - th - 20

    draw.text((x, y), watermark_text, font=font, fill=(255, 255, 255, 128))

    watermarked = Image.alpha_composite(img, overlay).convert("RGB")

    if output_path is None:
        name, ext = os.path.splitext(image_path)
        output_path = f"{name}_wm{ext}"
    watermarked.save(output_path, quality=85, optimize=True)
    return output_path


def compress_image(image_path, output_path=None, max_size=(600, 600), quality=80):
    img = Image.open(image_path)
    img.thumbnail(max_size, Image.LANCZOS)

    if output_path is None:
        name, ext = os.path.splitext(image_path)
        output_path = f"{name}_thumb{ext}"
    img.save(output_path, quality=quality, optimize=True)
    return output_path
