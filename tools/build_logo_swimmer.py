"""Raster the swimmer logo out of its own SVG at the sizes the site needs.

The vector is supplied artwork, not generated geometry, so this script only
rasters - it never redraws. assets/brand/logo-swimmer.svg is the master; edit
that and re-run, and every PNG below follows.

Two sets come out:

  logo-swimmer-NNN.png        the logo at its own proportions, transparent.
                              NNN is the WIDTH; height follows the artwork,
                              which is 1145.04 x 1138.98 - a whisker wider
                              than tall, so a 512 file is 512 x 509.

  logo-swimmer-square-NNN.png the same logo centred in a true square with a
                              little air around it, for favicons, app icons
                              and anywhere a non-square logo would be letter-
                              boxed by something else's layout.

    python tools/build_logo_swimmer.py
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "assets", "brand")
INKSCAPE = os.environ.get("INKSCAPE", r"C:/Program Files/Inkscape/bin/inkscape.exe")

SRC = "logo-swimmer.svg"
VB_W, VB_H = 1145.0358, 1138.9783

NATURAL = (2048, 1024, 512, 256, 128, 64)
SQUARE = (1024, 512, 256, 192, 180, 128, 64, 48, 32, 16)

# How much of the square each side is artwork. 0.92 leaves a thin margin so the
# green ring does not sit hard against the edge of an app icon, where every
# platform crops a little differently.
FIT = 0.92


def run(args):
    subprocess.run([INKSCAPE] + args, check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def natural(px):
    dst = "logo-swimmer-%d.png" % px
    run(["--export-type=png", "--export-filename=" + os.path.join(OUT, dst),
         "--export-width=%d" % px, os.path.join(OUT, SRC)])
    print("  %-32s %dpx wide" % (dst, px))


def square(px):
    """Export, then paste onto a transparent square. Inkscape can letterbox via
    --export-area, but doing it here keeps the margin exact at every size."""
    from PIL import Image
    inner = max(1, int(round(px * FIT)))
    tmp = os.path.join(OUT, "_sq.png")
    run(["--export-type=png", "--export-filename=" + tmp,
         "--export-width=%d" % inner, os.path.join(OUT, SRC)])
    im = Image.open(tmp).convert("RGBA")
    if im.height > inner:                      # taller than wide: fit by height
        im = im.resize((max(1, round(inner * im.width / im.height)), inner),
                       Image.LANCZOS)
    canvas = Image.new("RGBA", (px, px), (0, 0, 0, 0))
    canvas.alpha_composite(im, ((px - im.width) // 2, (px - im.height) // 2))
    dst = "logo-swimmer-square-%d.png" % px
    canvas.save(os.path.join(OUT, dst))
    im.close()
    os.remove(tmp)
    print("  %-32s %dx%d" % (dst, px, px))


def main():
    if not os.path.exists(os.path.join(OUT, SRC)):
        sys.exit("missing %s" % os.path.join(OUT, SRC))
    print("natural")
    for px in NATURAL:
        natural(px)
    print("square")
    for px in SQUARE:
        square(px)


if __name__ == "__main__":
    main()
