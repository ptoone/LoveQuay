"""Generate every LoveQuay brand asset from one source of truth.

    python tools/build_brand.py

Outputs SVG lockups (font-free — all text is converted to outlines) plus the
raster sizes the site and social cards need. PNG export requires Inkscape.
"""
import math
import os
import subprocess
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "assets", "brand")
FONT = os.path.join(HERE, "Poppins-ExtraBold.ttf")
FONT_URL = "https://github.com/google/fonts/raw/main/ofl/poppins/Poppins-ExtraBold.ttf"
INKSCAPE = os.environ.get("INKSCAPE", r"C:/Program Files/Inkscape/bin/inkscape.exe")

sys.path.insert(0, HERE)
from textpath import Typesetter  # noqa: E402

# --- Brand constants -------------------------------------------------------
NAVY = "#082A65"      # Quay Navy   - the coping around the pool
BASIN = "#1766D7"     # Basin Blue  - the pool wall behind the water
WATER = "#13B3F6"     # Water Blue  - the water surface
BLUE = BASIN          # primary accent used across the site
BLUE_LT = "#4FB6F8"   # Shallow     - light accent
BLUE_DK = "#0F4FA8"   # Deep        - dark accent
SAND = "#F4F1E6"      # Quay Sand   - warm neutral ground

CAP = 0.716           # Poppins ExtraBold cap height, in em

# ---------------------------------------------------------------------------
# The mark is a heart-shaped pool seen from slightly above: the basin wall
# behind, the water surface inside it, a swim ladder standing at the back edge,
# and the navy quay coping wrapping the near side and the right-hand end.
#
# The three silhouettes were traced from the approved artwork by
# tools/trace_logo.py and smoothed onto this 512-unit grid. The ladder is drawn
# as strokes instead, so it stays crisp and can be knocked out for one-colour
# versions.
# ---------------------------------------------------------------------------
BOX = (47, 70, 464, 341)

POOL_PATH = (
             "M293.5,104.0C296.5,102.8 374.7,101.6 393.8,105.0"
             "C400.5,106.2 407.0,109.3 413.2,112.0C419.4,114.7 425.8,118.1 431.2,121.5"
             "C435.9,124.4 440.5,127.7 444.6,131.4C449.5,135.8 455.2,141.5 459.1,146.9"
             "C462.9,152.1 466.4,158.7 468.6,164.4C470.6,169.6 471.9,175.2 472.6,180.8"
             "C475.7,207.1 472.6,353.0 472.6,353.0C472.6,353.0 200.4,354.3 166.2,353.0"
             "C162.1,352.8 157.9,352.5 153.8,352.0C146.3,350.9 134.5,348.9 125.8,346.5"
             "C118.0,344.3 109.7,341.1 102.9,338.0C97.2,335.4 91.2,332.0 86.4,329.0"
             "C82.8,326.7 79.2,324.3 75.9,321.5C71.3,317.5 64.4,310.4 61.0,306.1"
             "C59.1,303.7 57.4,301.2 56.0,298.6C53.9,294.8 51.3,288.9 50.0,284.6"
             "C48.9,281.0 48.3,277.3 48.0,273.6C47.7,269.6 47.9,264.7 48.5,260.7"
             "C49.1,256.9 50.1,253.2 51.5,249.7C52.9,246.0 55.0,242.1 57.0,238.7"
             "C58.9,235.5 61.1,232.5 63.5,229.7C66.7,225.9 71.2,221.4 75.4,217.8"
             "C79.6,214.1 84.2,210.8 88.9,207.8C93.6,204.7 98.9,201.7 103.9,199.3"
             "C108.4,197.0 113.1,195.1 117.8,193.3C123.6,191.2 130.4,188.9 136.8,187.3"
             "C146.1,185.1 159.2,182.8 169.7,181.8C179.3,181.0 191.3,181.1 198.7,181.3"
             "C202.5,181.5 209.8,182.6 210.1,182.3C210.5,182.1 212.1,173.2 213.6,168.9"
             "C215.2,164.5 217.3,160.0 219.6,155.9C222.2,151.4 225.7,146.5 229.1,142.4"
             "C232.4,138.5 236.5,134.6 240.1,131.4C242.9,128.9 245.9,126.6 249.1,124.5"
             "C252.9,121.8 257.6,118.9 262.0,116.5C266.7,113.9 271.9,111.5 277.0,109.5"
             "C282.1,107.5 291.6,105.3 293.0,104.5C293.2,104.4 293.3,104.1 293.5,104.0Z")

WATER_PATH = (
              "M382.8,151.9C383.6,151.6 389.6,151.5 392.8,151.9"
              "C396.0,152.3 399.4,153.4 402.7,154.4C407.3,155.8 413.2,157.7 418.2,159.9"
              "C424.0,162.3 430.6,165.5 436.2,168.9C441.7,172.2 447.6,176.5 452.1,180.3"
              "C455.7,183.4 459.1,186.7 462.1,190.3C465.7,194.7 470.8,199.8 472.6,205.8"
              "C478.5,225.1 472.6,353.0 472.6,353.0C472.6,353.0 201.9,355.9 158.3,352.5"
              "C150.7,351.9 143.2,350.7 135.8,349.0C127.9,347.1 116.8,344.8 111.4,341.5"
              "C107.0,338.8 103.1,333.7 99.9,329.5C96.8,325.4 93.8,320.4 91.9,316.0"
              "C90.2,312.0 88.9,307.0 88.4,303.1C88.0,299.6 88.1,295.8 88.4,292.6"
              "C88.7,289.5 89.4,286.5 90.4,283.6C91.5,280.4 93.1,276.8 94.9,273.6"
              "C96.9,270.2 99.7,266.3 102.4,263.2C105.0,260.1 107.8,257.2 110.9,254.7"
              "C115.6,250.7 122.8,245.4 129.3,241.7C136.6,237.6 145.8,233.6 153.8,230.7"
              "C161.1,228.1 168.6,226.2 176.2,224.7C184.2,223.2 192.8,222.2 201.2,221.7"
              "C209.8,221.3 226.6,223.0 227.6,222.2C228.3,221.8 229.4,215.0 230.6,211.8"
              "C231.7,208.8 233.0,206.0 234.6,203.3C236.6,199.8 239.6,195.4 242.1,192.3"
              "C244.1,189.8 246.3,187.5 248.6,185.3C251.6,182.5 255.6,179.0 259.0,176.3"
              "C262.1,174.0 265.2,171.8 268.5,169.9C274.4,166.4 285.4,161.0 292.0,158.4"
              "C296.0,156.8 300.1,155.1 304.4,154.4C318.6,152.0 379.5,153.6 382.3,152.4"
              "C382.5,152.3 382.6,152.0 382.8,151.9Z")

QUAY_PATH = (
             "M486.1,235.7C486.1,235.7 510.0,235.7 510.0,235.7"
             "C510.0,235.7 510.0,408.3 510.0,408.3C510.0,408.3 178.1,412.0 127.8,407.8"
             "C119.8,407.2 110.7,405.5 103.9,403.9C99.1,402.7 94.1,401.0 89.9,399.4"
             "C86.3,397.9 82.8,396.3 79.4,394.4C75.9,392.4 72.0,389.9 69.0,387.4"
             "C66.2,385.1 63.5,382.5 61.5,379.9C59.5,377.4 57.5,373.9 56.5,371.4"
             "C55.8,369.8 55.2,368.1 55.0,366.4C54.0,359.5 55.0,323.5 55.0,323.5"
             "C55.0,323.5 58.0,329.1 60.0,331.5C62.4,334.6 66.0,338.2 69.5,341.0"
             "C73.8,344.6 80.3,348.7 85.4,351.5C89.7,353.8 94.3,355.7 98.9,357.5"
             "C103.4,359.2 108.2,360.7 112.9,361.9C117.3,363.1 121.8,364.1 126.3,364.9"
             "C130.9,365.8 135.6,366.6 140.3,366.9C178.4,369.7 485.6,367.4 485.6,367.4"
             "C485.6,367.4 486.0,241.3 486.1,236.2C486.1,236.0 486.1,235.7 486.1,235.7Z")

# Ladder: two rails standing proud of the back edge, two rungs. Round caps, so
# each stroke endpoint sits half a stroke-width inside the visible extent.
RAIL_X = (319.0, 382.1)
RAIL_TOP, RAIL_BOTTOM = 80.1, 191.8
RUNG_Y = (128.7, 165.6)
RAIL_W = 12
HALO_W = 19           # basin-coloured backing, so the ladder reads above the water


def ladder(color, width=RAIL_W):
    rails = [f"M{x},{RAIL_TOP} V{RAIL_BOTTOM}" for x in RAIL_X]
    rungs = [f"M{RAIL_X[0]},{y} H{RAIL_X[1]}" for y in RUNG_Y]
    paths = "".join(f'<path d="{d}"/>' for d in rails + rungs)
    return (f'<g fill="none" stroke="{color}" stroke-width="{width}" '
            f'stroke-linecap="round">{paths}</g>')


def quay(color):
    return f'<path fill="{color}" d="{QUAY_PATH}"/>'


def mark_color(gid=None):
    """The full mark: basin, ladder backing, water, white ladder, navy quay."""
    return (f'<path fill="{BASIN}" d="{POOL_PATH}"/>{ladder(BASIN, HALO_W)}'
            f'<path fill="{WATER}" d="{WATER_PATH}"/>{ladder("#FFFFFF")}'
            f'{quay(NAVY)}')


def mark_flat(gid=None):
    """Two colours - for embroidery, stamps and single-pass printing."""
    return (f'<path fill="{BASIN}" d="{POOL_PATH}"/>{ladder(BASIN, HALO_W)}'
            f'{ladder("#FFFFFF")}{quay(NAVY)}')


def mark_mono(color, mid):
    """One colour. A single mask knocks the ladder out of everything behind it;
    the backing stroke becomes its outline where it stands clear of the water."""
    return (f'<mask id="{mid}" maskUnits="userSpaceOnUse" x="0" y="0" '
            f'width="560" height="460">'
            f'<rect width="560" height="460" fill="#fff"/>'
            f'{ladder("#000")}</mask>'
            f'<g mask="url(#{mid})">'
            f'<path fill="{color}" d="{POOL_PATH}"/>{ladder(color, HALO_W)}'
            f'{quay(color)}</g>')


def svg(defs, body, w, h, label):
    """Round the canvas up so sub-pixel overshoot never clips the artwork."""
    w, h = math.ceil(w), math.ceil(h)
    d = f"<defs>{defs}</defs>\n" if defs else ""
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" '
            f'width="{w}" height="{h}" role="img" aria-label="{label}">\n'
            f'{d}{body}\n</svg>\n')


def svg_box(body, label, pad=0):
    """Standalone mark file, trimmed to the ink box (plus optional padding)."""
    x, y, w, h = BOX
    x, y, w, h = x - pad, y - pad, w + 2 * pad, h + 2 * pad
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{x} {y} {w} {h}" '
            f'width="{w}" height="{h}" role="img" aria-label="{label}">\n'
            f'{body}\n</svg>\n')


def placed(mark_body, x, y, height):
    """Place the mark's ink box at (x, y) with the given height."""
    s = height / BOX[3]
    return (f'<g transform="translate({x:.2f},{y:.2f}) scale({s:.5f}) '
            f'translate({-BOX[0]},{-BOX[1]})">{mark_body}</g>', BOX[2] * s)


def write(name, content):
    with open(os.path.join(OUT, name), "w", encoding="utf-8") as f:
        f.write(content)
    print("  ", name)


def main():
    os.makedirs(OUT, exist_ok=True)
    if not os.path.exists(FONT):
        print("downloading Poppins ExtraBold ...")
        urllib.request.urlretrieve(FONT_URL, FONT)
    ts = Typesetter(FONT)

    def track_to(text, cap_h, target_w):
        """Letterspacing that sets `text` to `target_w` at cap height `cap_h`.
        Only widens — use cap_to() when the text must instead be scaled down."""
        size = cap_h / CAP
        lo, hi = 0.0, 2.0
        for _ in range(60):
            mid = (lo + hi) / 2
            if ts.bbox(text, size, mid)[2] - ts.bbox(text, size, mid)[0] < target_w:
                lo = mid
            else:
                hi = mid
        return (lo + hi) / 2

    def cap_to(text, target_w, tracking):
        """Cap height that makes `text` exactly `target_w` wide at `tracking`."""
        b = ts.bbox(text, 100, tracking)
        return target_w / ((b[2] - b[0]) / 100) * CAP

    def word(text, cap_h, tracking, fill, x, baseline):
        size = cap_h / CAP
        b = ts.bbox(text, size, tracking)
        d, _ = ts.path(text, size, tracking, x=x - b[0], y=baseline)
        return f'<path fill="{fill}" d="{d}"/>', b[2] - b[0], -b[1]

    print("SVG:")
    # --- Marks ------------------------------------------------------------
    write("mark.svg", svg_box(mark_color(), "LoveQuay"))
    write("mark-flat.svg", svg_box(mark_flat(), "LoveQuay"))
    write("mark-navy.svg", svg_box(mark_mono(NAVY, "mN"), "LoveQuay"))
    write("mark-white.svg", svg_box(mark_mono("#FFFFFF", "mW"), "LoveQuay"))

    # --- Wordmark ---------------------------------------------------------
    wd, ww, wasc = word("LOVEQUAY", 100, 0.012, NAVY, 0, 100)
    write("wordmark.svg", svg("", wd, ww, 100 + 0.118 * 100 / CAP * CAP, "LoveQuay"))

    # --- Stacked lockup (primary) ----------------------------------------
    W = 512
    mark_h = 268
    def build_stacked(word_fill, tag_fill, gid):
        mk, mw = placed(mark_color(gid), (W - mark_h * BOX[2] / BOX[3]) / 2, 0, mark_h)
        target = 424
        cap = cap_to("LOVEQUAY", target, 0.012)
        base = mark_h + 40 + cap
        w1, w1w, _ = word("LOVEQUAY", cap, 0.012, word_fill, (W - target) / 2, base)
        tcap = 17
        tbase = base + 30 + tcap
        w2, _, _ = word("SWIM PIER", tcap, track_to("SWIM PIER", tcap, w1w),
                        tag_fill, (W - target) / 2, tbase)
        return mk + w1 + w2, tbase + 6

    b, h = build_stacked(NAVY, BLUE, "lqS1")
    write("logo-stacked.svg", svg("", b, W, h, "LoveQuay Swim Pier"))
    b, h = build_stacked("#FFFFFF", BLUE_LT, "lqS2")
    write("logo-stacked-white.svg", svg("", b, W, h, "LoveQuay Swim Pier"))

    # --- Horizontal lockup ------------------------------------------------
    def build_horizontal(word_fill, tag_fill, gid):
        H = 128
        mk, mw = placed(mark_color(gid), 0, 8, 112)
        tx = mw + 24
        cap, base = 42, 73
        w1, tw, _ = word("LOVEQUAY", cap, 0.012, word_fill, tx, base)
        tcap = 13
        w2, _, _ = word("SWIM PIER", tcap, track_to("SWIM PIER", tcap, tw), tag_fill,
                        tx, base + 24 + tcap)
        return mk + w1 + w2, tx + tw, H

    b, w, h = build_horizontal(NAVY, BLUE, "lqH1")
    write("logo-horizontal.svg", svg("", b, w, h, "LoveQuay Swim Pier"))
    b, w, h = build_horizontal("#FFFFFF", BLUE_LT, "lqH2")
    write("logo-horizontal-white.svg", svg("", b, w, h, "LoveQuay Swim Pier"))

    # --- Inline lockup: no tagline, for navigation bars and small sizes ---
    def build_inline(word_fill, gid):
        H = 88
        mk, mw = placed(mark_color(gid), 0, 6, 76)
        tx = mw + 18
        cap = 38
        w1, tw, _ = word("LOVEQUAY", cap, 0.012, word_fill, tx, H / 2 + cap / 2 - 1)
        return mk + w1, tx + tw, H

    b, w, h = build_inline(NAVY, "lqI1")
    write("logo-inline.svg", svg("", b, w, h, "LoveQuay"))
    b, w, h = build_inline("#FFFFFF", "lqI2")
    write("logo-inline-white.svg", svg("", b, w, h, "LoveQuay"))

    # --- Favicon: square crop, ladder thickened for 16px legibility --------
    fav = (f'<path fill="{BASIN}" d="{POOL_PATH}"/>{ladder(BASIN, HALO_W + 5)}'
           f'<path fill="{WATER}" d="{WATER_PATH}"/>{ladder("#FFFFFF", RAIL_W + 4)}'
           f'{quay(NAVY)}')
    x, y, w, h = BOX
    side = w
    cy = y + h / 2
    write("favicon.svg",
          f'<svg xmlns="http://www.w3.org/2000/svg" '
          f'viewBox="{x} {cy - side / 2:.0f} {side} {side}" '
          f'width="{side}" height="{side}" role="img" aria-label="LoveQuay">' + chr(10)
          + fav + chr(10) + '</svg>' + chr(10))

    # --- Raster exports ---------------------------------------------------
    if not os.path.exists(INKSCAPE):
        print("Inkscape not found — skipping PNG export. Set $INKSCAPE to override.")
        return
    print("PNG:")
    for src, dest, w in [
        ("mark.svg", "mark-512.png", 512),
        ("mark.svg", "mark-1024.png", 1024),
        ("logo-stacked.svg", "logo-stacked-1000.png", 1000),
        ("logo-horizontal.svg", "logo-horizontal-1200.png", 1200),
        ("logo-inline.svg", "logo-inline-800.png", 800),
        ("logo-horizontal-white.svg", "logo-horizontal-white-1200.png", 1200),
        ("favicon.svg", "favicon-16.png", 16),
        ("favicon.svg", "favicon-32.png", 32),
        ("favicon.svg", "apple-touch-icon.png", 180),
        ("favicon.svg", "icon-192.png", 192),
        ("favicon.svg", "icon-512.png", 512),
    ]:
        subprocess.run([INKSCAPE, "--export-type=png",
                        f"--export-filename={os.path.join(OUT, dest)}",
                        "-w", str(w), os.path.join(OUT, src)],
                       capture_output=True, check=False)
        print("  ", dest)

    try:
        from PIL import Image
        Image.open(os.path.join(OUT, "icon-512.png")).save(
            os.path.join(ROOT, "favicon.ico"), sizes=[(16, 16), (32, 32), (48, 48)])
        print("   favicon.ico")
    except Exception as e:  # pragma: no cover
        print("   favicon.ico skipped:", e)


if __name__ == "__main__":
    main()
