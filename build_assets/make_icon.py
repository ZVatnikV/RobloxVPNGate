"""Generate app.ico from a simple branded mark."""

from pathlib import Path

from PIL import Image, ImageDraw

OUT = Path(__file__).resolve().parent / "app.ico"
SIZES = [16, 24, 32, 48, 64, 128, 256]


def make(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    pad = max(1, size // 16)
    # Rounded square background
    d.rounded_rectangle(
        (pad, pad, size - pad - 1, size - pad - 1),
        radius=max(2, size // 5),
        fill=(226, 35, 26, 255),
    )
    # Inner darker plate
    inset = size // 5
    d.rounded_rectangle(
        (inset, inset, size - inset - 1, size - inset - 1),
        radius=max(2, size // 8),
        fill=(11, 13, 18, 255),
    )
    # Three signal bars
    bar_w = max(2, size // 10)
    gap = max(1, size // 16)
    total = bar_w * 3 + gap * 2
    x0 = (size - total) // 2
    heights = [0.35, 0.55, 0.78]
    base = size - inset - max(2, size // 14)
    for i, h in enumerate(heights):
        x = x0 + i * (bar_w + gap)
        y = int(base - h * (size - 2 * inset))
        d.rounded_rectangle((x, y, x + bar_w, base), radius=max(1, bar_w // 3), fill=(255, 106, 61, 255))
    return img


def main() -> None:
    images = [make(s) for s in SIZES]
    images[0].save(OUT, format="ICO", sizes=[(s, s) for s in SIZES], append_images=images[1:])
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()