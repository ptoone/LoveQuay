"""Compose the Saturdays poster at landscape sizes.

    python tools/build_posters.py

The three portrait crops were made elsewhere; these are the landscape ones, which
cannot be cropped out of a 1080-wide portrait without either upscaling or losing
most of the frame. So they are recomposed from the same ingredients: a frame from
the 12 September swim, the white lockup, and the same type and colours sampled
out of the original artwork.

Writes into download/ alongside the portrait versions.
"""
import os
import subprocess

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "download")
PHOTO = os.path.join(HERE, "poster-src", "dive-group-4k.jpg")
INKSCAPE = os.environ.get("INKSCAPE", r"C:/Program Files/Inkscape/bin/inkscape.exe")

# Sampled from LoveQuay-Saturdays-2pm-1080x1920-story.png.
NAVY = (5, 27, 68)
YELLOW = "#DBE02E"
SKY = "#12AAF0"
WHITE = "#F8F8F8"
MUTED = (150, 165, 190)

SIZES = [
    (1920, 1005, "LoveQuay-Saturdays-2pm-1920x1005-event.png"),   # Facebook event
    (1920, 1080, "LoveQuay-Saturdays-2pm-1920x1080.png"),         # plain 16:9
]


def font(weight, size):
    return ImageFont.truetype(os.path.join(HERE, f"Poppins-{weight}.ttf"), size)


def text_width(d, s, f, tracking=0):
    if not tracking:
        return d.textlength(s, font=f)
    return sum(d.textlength(c, font=f) for c in s) + tracking * (len(s) - 1)


def draw_tracked(d, xy, s, f, fill, tracking):
    """Pillow has no letter-spacing, so step the glyphs by hand."""
    x, y = xy
    for c in s:
        d.text((x, y), c, font=f, fill=fill)
        x += d.textlength(c, font=f) + tracking


def logo(width):
    png = os.path.join(HERE, "_poster-logo.png")
    subprocess.run([INKSCAPE, "--export-type=png", f"--export-filename={png}",
                    "-w", str(width),
                    os.path.join(ROOT, "assets", "brand", "logo-horizontal-white.svg")],
                   capture_output=True)
    return Image.open(png).convert("RGBA") if os.path.exists(png) else None


def compose(W, H, name):
    # --- photo, cover-cropped, biased right so the divers clear the type ----
    src = Image.open(PHOTO).convert("RGB")
    s = max(W / src.width, H / src.height)
    img = src.resize((round(src.width * s), round(src.height * s)), Image.LANCZOS)
    left = int((img.width - W) * 0.62)
    img = img.crop((left, int((img.height - H) * 0.42), left + W,
                    int((img.height - H) * 0.42) + H))

    # --- navy wash: heavy at the left, so the type always has ground --------
    wash = Image.new("RGBA", (W, H))
    wd = ImageDraw.Draw(wash)
    for x in range(W):
        t = x / W
        a = int(246 - 210 * min(1.0, (t / 0.80) ** 1.25))
        wd.line([(x, 0), (x, H)], fill=NAVY + (max(a, 30),))
    img = Image.alpha_composite(img.convert("RGBA"), wash)

    foot = Image.new("RGBA", (W, H))
    fd = ImageDraw.Draw(foot)
    for y in range(int(H * 0.72), H):
        t = (y - H * 0.72) / (H * 0.28)
        fd.line([(0, y), (W, y)], fill=NAVY + (int(165 * t * t),))
    img = Image.alpha_composite(img, foot).convert("RGB")

    d = ImageDraw.Draw(img)
    M = int(W * 0.062)                       # left margin
    scale = H / 1005.0                       # everything keys off the 1920x1005 design

    # --- logo ---------------------------------------------------------------
    lg = logo(int(W * 0.21))
    y = int(H * 0.085)
    if lg:
        img.paste(lg, (M, y), lg)
        y += lg.height + int(66 * scale)
    else:
        y += int(96 * scale)

    # --- the shout ----------------------------------------------------------
    f_eyebrow = font("SemiBold", int(27 * scale))
    draw_tracked(d, (M, y), "COME SWIM WITH US", f_eyebrow, SKY, 7 * scale)
    y += int(58 * scale)

    f_big = font("ExtraBold", int(132 * scale))
    d.text((M, y), "SATURDAYS", font=f_big, fill=WHITE)
    y += int(132 * scale)

    d.text((M, y), "2 PM", font=f_big, fill=YELLOW)
    y += int(150 * scale)

    f_url = font("SemiBold", int(40 * scale))
    d.text((M, y), "lovequay.com", font=f_url, fill=SKY)
    y += int(74 * scale)

    # --- rule, then the cleanup line ---------------------------------------
    d.line([(M, y), (M + int(190 * scale), y)], fill=(120, 140, 175), width=max(1, int(2 * scale)))
    y += int(34 * scale)

    f_body = font("Medium", int(29 * scale))
    f_bold = font("SemiBold", int(29 * scale))
    d.text((M, y), "Volunteer cleanup with ", font=f_body, fill=(206, 218, 236))
    d.text((M + d.textlength("Volunteer cleanup with ", font=f_body), y),
           "Friends of LoveQuay", font=f_bold, fill=WHITE)

    # --- the disclaimer, bottom-left ---------------------------------------
    f_fine = font("Medium", int(21 * scale))
    draw_tracked(d, (M, H - int(62 * scale)),
                 "OPEN WATER  ·  NO LIFEGUARD  ·  SWIM AT YOUR OWN RISK",
                 f_fine, MUTED, 2.2 * scale)

    img.save(os.path.join(OUT, name), optimize=True)
    return os.path.getsize(os.path.join(OUT, name))


def main():
    if not os.path.exists(PHOTO):
        raise SystemExit("hero frame missing: " + PHOTO)
    os.makedirs(OUT, exist_ok=True)
    for W, H, name in SIZES:
        n = compose(W, H, name)
        print(f"   {name:46s} {W}x{H}  {n/1e6:.1f} MB")
    tmp = os.path.join(HERE, "_poster-logo.png")
    if os.path.exists(tmp):
        os.remove(tmp)


if __name__ == "__main__":
    main()
