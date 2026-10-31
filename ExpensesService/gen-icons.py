from pathlib import Path

from PIL import Image, ImageDraw

OUTPUT_DIR = Path(__file__).parent / 'static'
ICON_SIZES = (180, 192, 512)
FAVICON_SIZES = (16, 32, 48)
BACKGROUND = '#193b36'
PAPER = '#f2e9d8'
ACCENT = '#cf7048'


def create_icon(size):
    """Erzeugt ein reduziertes, geometrisches App-Zeichen."""
    image = Image.new('RGB', (size, size), BACKGROUND)
    draw = ImageDraw.Draw(image)
    margin = int(size * 0.20)
    sheet = (margin, margin, size - margin, size - margin)
    draw.rounded_rectangle(sheet, radius=int(size * 0.055), fill=PAPER)
    line_width = max(2, size // 42)
    left = int(size * 0.34)
    right = int(size * 0.66)
    for y_ratio in (0.41, 0.50, 0.59):
        y = int(size * y_ratio)
        draw.line((left, y, right, y), fill=BACKGROUND, width=line_width)
    mark_box = (int(size * 0.37), int(size * 0.68), int(size * 0.63), int(size * 0.76))
    draw.rounded_rectangle(mark_box, radius=max(2, size // 40), fill=ACCENT)
    return image


def main():
    """Erstellt PWA-Bilddateien und Favicons."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for size in ICON_SIZES:
        image = create_icon(size)
        image.save(OUTPUT_DIR / f'icon-{size}.png', format='PNG', optimize=True)

    favicon_images = [create_icon(size) for size in FAVICON_SIZES]
    favicon_images[-1].save(
        OUTPUT_DIR / 'favicon.ico',
        format='ICO',
        sizes=[(size, size) for size in FAVICON_SIZES],
    )
    favicon_images[1].save(OUTPUT_DIR / 'favicon-32.png', format='PNG', optimize=True)


if __name__ == '__main__':
    main()
