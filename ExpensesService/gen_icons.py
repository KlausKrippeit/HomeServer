from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parent / "static"
BLUE = "#0a60ff"
WHITE = "#ffffff"
FONTS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
]


def make_icon(size):
    image = Image.new("RGB", (size, size), BLUE)
    draw = ImageDraw.Draw(image)
    font = None
    for path in FONTS:
        if Path(path).exists():
            try:
                font = ImageFont.truetype(path, int(size * 0.60))
                font.getmask("€")
                break
            except (OSError, UnicodeError):
                font = None
    if font is None:
        font = ImageFont.load_default()
    try:
        draw.text((size / 2, size / 2), "€", fill=WHITE, font=font, anchor="mm")
    except (UnicodeError, OSError):
        # Draw a legible fallback euro mark if the selected bitmap font lacks the glyph.
        width = max(4, int(size * 0.075))
        x = int(size * 0.54)
        y = int(size * 0.22)
        r = int(size * 0.27)
        draw.arc((x - r, y, x + r, y + 2 * r), 70, 290, fill=WHITE, width=width)
        draw.line((int(size * 0.25), int(size * 0.46), int(size * 0.72), int(size * 0.46)), fill=WHITE, width=width)
        draw.line((int(size * 0.22), int(size * 0.57), int(size * 0.68), int(size * 0.57)), fill=WHITE, width=width)
    image.save(OUT / f"icon-{size}.png", format="PNG")


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    for dimension in (180, 192, 512):
        make_icon(dimension)
