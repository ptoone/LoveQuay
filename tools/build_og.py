"""Compose the 1200x630 social sharing card.

    python tools/build_og.py

Run after build_brand.py and build_images.py — it uses output from both.
"""
import os
import subprocess

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
IMG = os.path.join(ROOT, "assets", "img")
BRAND = os.path.join(ROOT, "assets", "brand")
INKSCAPE = os.environ.get("INKSCAPE", r"C:/Program Files/Inkscape/bin/inkscape.exe")

W, H = 1200, 630
NAVY = (10, 39, 92)


def main():
    photo = Image.open(os.path.join(IMG, "pier-length-1920.jpg")).convert("RGB")

    # Cover-crop to 1200x630.
    s = max(W / photo.width, H / photo.height)
    photo = photo.resize((round(photo.width * s), round(photo.height * s)), Image.LANCZOS)
    left = (photo.width - W) // 2
    top = int((photo.height - H) * 0.55)
    card = photo.crop((left, top, left + W, top + H))

    # Navy scrim, heavier on the left where the logo sits.
    scrim = Image.new("RGBA", (W, H))
    d = ImageDraw.Draw(scrim)
    for x in range(W):
        a = int(238 - 168 * min(1.0, x / (W * 0.78)))
        d.line([(x, 0), (x, H)], fill=NAVY + (max(a, 58),))
    card = Image.alpha_composite(card.convert("RGBA"), scrim).convert("RGB")

    # White stacked lockup, rendered fresh from the SVG.
    logo_png = os.path.join(HERE, "_og-logo.png")
    subprocess.run([INKSCAPE, "--export-type=png", f"--export-filename={logo_png}",
                    "-w", "760", os.path.join(BRAND, "logo-stacked-white.svg")],
                   capture_output=True, check=False)
    if os.path.exists(logo_png):
        logo = Image.open(logo_png).convert("RGBA")
        logo.thumbnail((360, 360), Image.LANCZOS)
        card.paste(logo, (76, (H - logo.height) // 2 - 16), logo)
        os.remove(logo_png)

    out = os.path.join(IMG, "og-default.jpg")
    card.save(out, quality=86, progressive=True, optimize=True)
    print(f"{out}  {os.path.getsize(out) / 1000:.0f} kB")


if __name__ == "__main__":
    main()
