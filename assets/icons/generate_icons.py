"""Generate app icons for DnD World Builder.

Creates a d20-inspired icon with a shield shape in dark purple/gold theme.
Outputs app.ico (Windows multi-size) and app.png (256x256 for Linux).
"""

import math
from PIL import Image, ImageDraw, ImageFont

SIZE = 256


def draw_icon(size: int) -> Image.Image:
    """Draw a d20-themed icon at the given size."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    cx, cy = size / 2, size / 2
    r = size * 0.45  # radius

    # Background circle — dark indigo
    draw.ellipse(
        [cx - r, cy - r, cx + r, cy + r],
        fill=(30, 27, 75, 255),
        outline=(180, 160, 90, 255),
        width=max(1, size // 40),
    )

    # D20 triangle shape (equilateral, pointing up)
    tri_r = r * 0.62
    pts = []
    for i in range(3):
        angle = math.radians(-90 + i * 120)
        pts.append((cx + tri_r * math.cos(angle), cy + tri_r * math.sin(angle)))

    draw.polygon(pts, fill=(55, 48, 120, 255), outline=(212, 175, 55, 255),
                 width=max(1, size // 50))

    # Inner lines of the d20 face
    mid01 = ((pts[0][0] + pts[1][0]) / 2, (pts[0][1] + pts[1][1]) / 2)
    mid12 = ((pts[1][0] + pts[2][0]) / 2, (pts[1][1] + pts[2][1]) / 2)
    mid20 = ((pts[2][0] + pts[0][0]) / 2, (pts[2][1] + pts[0][1]) / 2)
    lw = max(1, size // 80)
    gold = (212, 175, 55, 180)
    draw.line([mid01, mid12], fill=gold, width=lw)
    draw.line([mid12, mid20], fill=gold, width=lw)
    draw.line([mid20, mid01], fill=gold, width=lw)

    # "20" text in center
    font_size = int(size * 0.22)
    try:
        font = ImageFont.truetype("arialbd.ttf", font_size)
    except OSError:
        try:
            font = ImageFont.truetype("DejaVuSans-Bold.ttf", font_size)
        except OSError:
            font = ImageFont.load_default()

    text = "20"
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    tx = cx - tw / 2 - bbox[0]
    ty = cy - th / 2 - bbox[1] + size * 0.02
    draw.text((tx, ty), text, fill=(255, 235, 160, 255), font=font)

    return img


def main():
    icon = draw_icon(SIZE)

    # Save PNG (256x256)
    icon.save("app.png", "PNG")
    print("Created app.png (256x256)")

    # Save ICO with multiple sizes
    ico_sizes = [16, 32, 48, 64, 128, 256]
    images = [draw_icon(s) for s in ico_sizes]
    # Convert RGBA to RGB with white background for ICO compatibility
    ico_images = []
    for img_rgba in images:
        bg = Image.new("RGBA", img_rgba.size, (0, 0, 0, 255))
        bg.paste(img_rgba, mask=img_rgba)
        ico_images.append(bg)
    ico_images[-1].save(
        "app.ico",
        format="ICO",
        append_images=ico_images[:-1],
    )
    print(f"Created app.ico (sizes: {ico_sizes})")


if __name__ == "__main__":
    main()
