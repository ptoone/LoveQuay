"""Generate every LoveQuay brand file from one set of geometry.

The mark is the old heart-shaped pool composition — coping, basin wall, water,
ladder — rebuilt on the heart/hull silhouette traced from the artwork, and the
wordmark is traced from the LOVE sign's own lettering. Nothing here depends on
a font being installed: all type is outlined.

    python tools/build_brand.py            # SVG only
    python tools/build_brand.py --png      # SVG + PNG (needs Inkscape)
"""
import io
import math
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "assets", "brand")
sys.path.insert(0, HERE)
from textpath import Typesetter  # noqa: E402

FONT = os.path.join(HERE, "Poppins-SemiBold.ttf")
INKSCAPE = os.environ.get("INKSCAPE", r"C:/Program Files/Inkscape/bin/inkscape.exe")

# ---------------------------------------------------------------- palette ---
NAVY = "#082A65"      # Quay Navy  — the coping the pool sits on
BASIN = "#0056B8"     # Basin Blue — the pool wall behind the water
WATER = "#007FFF"     # Water Blue — the water surface
SIGN = "#FE010F"      # Sign Red   — the LOVE sign's own red; the wordmark
WHITE = "#FFFFFF"
NAVY_LT = "#1E63C8"   # basin, reversed on navy
WATER_LT = "#2E9BFF"  # water, reversed on navy
COPE_DK = "#0A3F8F"   # coping, reversed on navy

# --------------------------------------------------------------- geometry ---
HULL = re.search(
    r'HULL_0 = "([^"]+)"',
    io.open(os.path.join(HERE, "traced-hull-path.txt"), encoding="utf-8").read()).group(1)
HW, HH = 436.4, 1000.9                       # the traced hull's own box

GLYPH = [m.group(1) for m in re.finditer(
    r'LTR_\d+ = "([^"]+)"',
    io.open(os.path.join(HERE, "traced-lettering-paths.txt"), encoding="utf-8").read())]
LBOX = eval(io.open(os.path.join(HERE, "letter_boxes.txt"), encoding="utf-8").read())
B = [LBOX[f"g{i}"] for i in range(8)]        # x, y, w, h per letter
BASELINE = 172.0                             # Q's tail hangs below this

# The pool, as fractions of the heart's box. Changing any of these re-cuts every
# file on the page, which is the point of keeping them in one place.
STRETCH = 1.55        # the traced heart is 0.44:1; the pool needs width for the ladder
WATER_S = 0.70        # water heart, scaled — small enough to clear the basin's taper
WATER_SINK = 0.26     # how far down the leftover space the water sits
WATER_SHIFT = 0.12    # and how far right, so the wall shows along the back edge
COPE = 0.075          # coping offset, down
COPE_DX = 0.020       # coping offset, right
RIM = 0.42            # the white sliver between coping and basin, as a share of the offset
LAD_CX, LAD_W = 0.635, 0.24
LAD_TOP, LAD_BOT = -0.05, 0.42
LAD_STROKE = 0.055
# Rung positions along the rails. The first one has to clear the heart's crown:
# the right lobe peaks at y/h = 0.000 between the rails, and a rung whose white
# band started just below that sliced a hairline crescent off the top and left
# it stranded above the rung. At 0.30 the band starts near 0.07, so the rung
# sits at the waterline with the rails rising out of it.
RUNGS = (0.30, 0.60, 0.90)


def heart(x, y, w, h, fill):
    return (f'<g transform="translate({x:.2f},{y:.2f}) scale({w / HW:.5f},{h / HH:.5f})">'
            f'<path fill="{fill}" fill-rule="evenodd" d="{HULL}"/></g>')


def heart_path_only(x, y, w, h):
    """The same silhouette with no fill, for use inside a mask."""
    return (f'<g transform="translate({x:.2f},{y:.2f}) scale({w / HW:.5f},{h / HH:.5f})">'
            f'<path fill-rule="evenodd" d="{HULL}"/></g>')


def ladder_strokes(x, y, w, h):
    lx = x + w * LAD_CX
    half = w * LAD_W / 2
    top, bot = y + h * LAD_TOP, y + h * LAD_BOT
    rails = "".join(f'<path d="M{v:.1f},{top:.1f} V{bot:.1f}"/>' for v in (lx - half, lx + half))
    rungs = "".join(f'<path d="M{lx - half:.1f},{top + (bot - top) * f:.1f} '
                    f'H{lx + half:.1f}"/>' for f in RUNGS)
    return rails + rungs, max(w * LAD_STROKE, 2)


def water_box(x, y, w, h):
    ww, wh = w * WATER_S, h * WATER_S
    return x + (w - ww) * (0.5 + WATER_SHIFT), y + (h - wh) * WATER_SINK, ww, wh


def mark_full(x, y, w, h, basin=BASIN, water=WATER, cope=NAVY, rim=WHITE, rail=WHITE):
    """Coping, white sliver, basin wall, water, ladder — the full-colour mark."""
    body = heart(x + w * COPE_DX, y + h * COPE, w, h, cope)
    body += heart(x + w * COPE_DX * RIM, y + h * COPE * RIM, w, h, rim)
    body += heart(x, y, w, h, basin)
    body += heart(*water_box(x, y, w, h), water)
    d, sw = ladder_strokes(x, y, w, h)
    body += (f'<g fill="none" stroke="{rail}" stroke-width="{sw:.1f}" '
             f'stroke-linecap="round">{d}</g>')
    return body


def mark_flat(x, y, w, h, dark=NAVY, light=BASIN):
    """Two flat colours and the paper: for embroidery, stamps and screen print."""
    body = heart(x, y, w, h, dark)
    body += heart(*water_box(x, y, w, h), light)
    d, sw = ladder_strokes(x, y, w, h)
    body += (f'<g fill="none" stroke="{WHITE}" stroke-width="{sw:.1f}" '
             f'stroke-linecap="round">{d}</g>')
    return body


_mask_n = [0]


def mark_mono(x, y, w, h, fill):
    """One colour. The water and the ladder are knocked clean through, so the
    mark works on any ground without carrying a second colour."""
    _mask_n[0] += 1
    mid = f"lqm{_mask_n[0]}"
    d, sw = ladder_strokes(x, y, w, h)
    wx, wy, ww, wh = water_box(x, y, w, h)
    mask = (f'<mask id="{mid}" maskUnits="userSpaceOnUse" '
            f'x="{x - w:.1f}" y="{y - h:.1f}" width="{w * 3:.1f}" height="{h * 3:.1f}">'
            f'<rect x="{x - w:.1f}" y="{y - h:.1f}" width="{w * 3:.1f}" height="{h * 3:.1f}" '
            f'fill="#fff"/>'
            f'<g fill="#000">{heart_path_only(wx, wy, ww, wh)}</g>'
            f'<g fill="none" stroke="#fff" stroke-width="{sw:.1f}" '
            f'stroke-linecap="round">{d}</g></mask>')
    return (f'<defs>{mask}</defs><g mask="url(#{mid})">'
            f'{heart(x, y, w, h, fill)}</g>')


def mark_box(h):
    """The mark's true extents at height `h`: the coping pushes right and down,
    the ladder pokes up. Everything that places the mark measures from this."""
    w = h * HW / HH * STRETCH
    _, sw = ladder_strokes(0, 0, w, h)
    x0, y0 = 0.0, h * LAD_TOP - sw / 2
    x1, y1 = w * (1 + COPE_DX), h * (1 + COPE)
    return w, x0, y0, x1 - x0, y1 - y0


# --------------------------------------------------------------- wordmark ---
SUMW = sum(b[2] for b in B)          # the eight letters, side by side, untracked
TRACK = 0.035                        # letter gap as a share of cap height


def word_width(cap, track=TRACK):
    return cap * (SUMW / BASELINE + 7 * track)


def cap_for(target_w, track=TRACK):
    """Cap height that sets LOVEQUAY to `target_w`.

    An earlier version held the cap at 100 and solved for tracking instead,
    which meant a wide lockup got small letters flung apart rather than big
    ones — invert the relation instead, it has a closed form."""
    return target_w / (SUMW / BASELINE + 7 * track)


def wordmark(x, baseline, cap, fill=SIGN, track=TRACK):
    """LOVEQUAY traced from the sign. Returns the body and its drawn width."""
    s = cap / BASELINE
    gap = cap * track
    out, cx = "", x
    for i in range(8):
        bx, _, bw, _ = B[i]
        out += (f'<g transform="translate({cx:.2f},{baseline:.2f}) scale({s:.5f}) '
                f'translate({-bx:.2f},{-BASELINE:.2f})"><path d="{GLYPH[i]}"/></g>')
        cx += bw * s + gap
    return f'<g fill="{fill}" fill-rule="evenodd">{out}</g>', cx - gap - x


def word_desc(cap):
    """How far the Q's tail drops below the baseline."""
    return (B[4][3] - BASELINE) * cap / BASELINE


# -------------------------------------------------------------- tag line ----
_ts = Typesetter(FONT) if os.path.exists(FONT) else None


def tagline(text, cap_h, target_w, fill, x, baseline):
    """SWIM PIER, outlined from Poppins SemiBold and tracked to `target_w`."""
    if _ts is None:
        return "", 0.0
    size = cap_h / 0.70
    lo, hi = 0.0, 2.0
    for _ in range(60):
        mid = (lo + hi) / 2
        b = _ts.bbox(text, size, mid)
        if b[2] - b[0] < target_w:
            lo = mid
        else:
            hi = mid
    tr = (lo + hi) / 2
    b = _ts.bbox(text, size, tr)
    d, _ = _ts.path(text, size, tr, x=x - b[0], y=baseline)
    return f'<path fill="{fill}" d="{d}"/>', b[2] - b[0]


# ------------------------------------------------------------------ files ---
def svg(body, x, y, w, h, label, bg=None):
    rect = (f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" fill="{bg}"/>'
            if bg else "")
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{x:.1f} {y:.1f} {w:.1f} {h:.1f}" '
            f'width="{math.ceil(w)}" height="{math.ceil(h)}" role="img" '
            f'aria-label="{label}">{rect}{body}</svg>')


def write(name, content):
    path = os.path.join(OUT, name)
    io.open(path, "w", encoding="utf-8").write(content)
    print(f"  {name}")


def png(src, dst, px, by_width=True):
    if not os.path.exists(INKSCAPE):
        return False
    subprocess.run([INKSCAPE, "--export-type=png",
                    f"--export-filename={os.path.join(OUT, dst)}",
                    "-w" if by_width else "-h", str(px), os.path.join(OUT, src)],
                   capture_output=True)
    print(f"  {dst}")
    return True


# ---------------------------------------------------------------- lockups ---
TAG_RATIO = 0.26      # tagline cap, as a share of the wordmark cap


def stacked(mark_fn, word_fill, tag_fill, label, bg=None, tag=True):
    """Mark over the wordmark. The primary lockup."""
    H = 1000.0
    w, mx, my, mw, mh = mark_box(H)
    word_w = mw * 1.12
    cap = cap_for(word_w)
    body = mark_fn(0, 0, w, H)
    base = my + mh + H * 0.115 + cap
    wd, drawn = wordmark(mx + (mw - word_w) / 2, base, cap, word_fill)
    body += wd
    bottom = base + word_desc(cap)
    if tag:
        tcap = cap * TAG_RATIO
        tw = word_w * 0.74
        t, _ = tagline("SWIM PIER", tcap, tw, tag_fill,
                       mx + (mw - tw) / 2, bottom + H * 0.055 + tcap)
        body += t
        bottom += H * 0.055 + tcap
    # The wordmark is wider than the mark, so the box has to span both.
    left = min(mx, mx + (mw - word_w) / 2)
    right = max(mx + mw, mx + (mw + word_w) / 2)
    pad = H * 0.02
    return svg(body, left - pad, my - pad, right - left + pad * 2,
               bottom - my + pad * 2, label, bg)


def horizontal(mark_fn, word_fill, tag_fill, label, bg=None, tag=True):
    """Mark left, type right. For wide spaces and the footer."""
    H = 1000.0
    w, mx, my, mw, mh = mark_box(H)
    sep = mw * 0.30
    cap = mh * 0.235
    word_w = word_width(cap)
    tx = mx + mw + sep
    tcap = cap * TAG_RATIO
    block = cap + (mh * 0.075 + tcap if tag else 0.0)
    top = my + (mh - block) / 2
    body = mark_fn(0, 0, w, H)
    wd, _ = wordmark(tx, top + cap, cap, word_fill)
    body += wd
    if tag:
        t, _ = tagline("SWIM PIER", tcap, word_w * 0.66, tag_fill,
                       tx, top + cap + mh * 0.075 + tcap)
        body += t
    pad = H * 0.02
    return svg(body, mx - pad, my - pad, (tx + word_w) - mx + pad * 2, mh + pad * 2, label, bg)


def inline(mark_fn, word_fill, label, bg=None):
    """Short and wide, for navigation bars under 40 px tall. No tagline — it
    turns to mud at that size."""
    H = 1000.0
    w, mx, my, mw, mh = mark_box(H)
    sep = mw * 0.26
    # A taller cap than the other lockups: at 44 px the mark eats the height and
    # the letters have to hold their own.
    cap = mh * 0.34
    word_w = word_width(cap)
    tx = mx + mw + sep
    body = mark_fn(0, 0, w, H)
    wd, _ = wordmark(tx, my + (mh + cap) / 2, cap, word_fill)
    body += wd
    pad = H * 0.02
    return svg(body, mx - pad, my - pad, (tx + word_w) - mx + pad * 2, mh + pad * 2, label, bg)


def tile(bg, basin, water, cope, rim, radius=0.1875, frac=0.74):
    """Square app icon. The mark alone is too narrow to hold a square, and at
    16 px a shape with no edge has nothing to grip — the tile supplies one."""
    N = 512.0
    H = N * frac
    w, mx, my, mw, mh = mark_box(H)
    body = mark_full(0, 0, w, H, basin, water, cope, rim)
    dx, dy = (N - mw) / 2 - mx, (N - mh) / 2 - my
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" '
            f'width="512" height="512" role="img" aria-label="LoveQuay">'
            f'<rect width="512" height="512" rx="{N * radius:.0f}" fill="{bg}"/>'
            f'<g transform="translate({dx:.2f},{dy:.2f})">{body}</g></svg>')


LOVE, QUAY = (0, 1, 2, 3), (4, 5, 6, 7)


def line(idx, x, baseline, cap, gap):
    """One word of the sign alphabet, set on a baseline."""
    s = cap / BASELINE
    out, cx = "", x
    for i in idx:
        bx, _, bw, _ = B[i]
        out += (f'<g transform="translate({cx:.2f},{baseline:.2f}) scale({s:.5f}) '
                f'translate({-bx:.2f},{-BASELINE:.2f})"><path d="{GLYPH[i]}"/></g>')
        cx += bw * s + gap
    return out


def line_w(idx, cap, gap):
    return sum(B[i][2] for i in idx) * cap / BASELINE + gap * (len(idx) - 1)


def justify(idx, target_w, cap):
    """The letter gap that sets this word to exactly target_w. QUAY is naturally
    wider than LOVE, so the two lines need different tracking to square up."""
    n = len(idx) - 1
    return (target_w - sum(B[i][2] for i in idx) * cap / BASELINE) / n


def word_tile(bg, fill, radius=0.1875, inner=0.78, lead=0.20):
    """LOVE over QUAY, both justified to the same width, in a square.

    The wordmark on one line is far too wide for an icon. Stacked and justified
    it fills a square properly, and it is the only lettering we have — the sign
    alphabet stops at these eight characters."""
    N = 512.0
    w = N * inner
    cap = w * 0.405
    g1, g2 = justify(LOVE, w, cap), justify(QUAY, w, cap)
    desc = (B[4][3] - BASELINE) * cap / BASELINE      # the Q's tail
    block = cap + cap * lead + cap + desc             # total ink, top to tail
    x = (N - w) / 2
    top = (N - block) / 2
    body = (line(LOVE, x, top + cap, cap, g1)
            + line(QUAY, x, top + cap + cap * lead + cap, cap, g2))
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" '
            f'width="512" height="512" role="img" aria-label="LoveQuay">'
            f'<rect width="512" height="512" rx="{N * radius:.0f}" fill="{bg}"/>'
            f'<g fill="{fill}" fill-rule="evenodd">{body}</g></svg>')


def ico():
    """favicon.ico, for the browsers and crawlers that still ask for it."""
    try:
        from PIL import Image
    except ImportError:
        print("  (favicon.ico skipped — Pillow not installed)")
        return
    sizes = (16, 32, 48, 64)
    for s in sizes:
        png("favicon.svg", f"_ico{s}.png", s)
    imgs = [Image.open(os.path.join(OUT, f"_ico{s}.png")).convert("RGBA") for s in sizes]
    imgs[0].save(os.path.join(ROOT, "favicon.ico"), format="ICO",
                 sizes=[(s, s) for s in sizes], append_images=imgs[1:])
    for s in sizes:
        os.remove(os.path.join(OUT, f"_ico{s}.png"))
    print("  favicon.ico")


def main():
    os.makedirs(OUT, exist_ok=True)
    want_png = "--png" in sys.argv
    print("marks")

    H = 1000.0
    w, mx, my, mw, mh = mark_box(H)
    pad = H * 0.02
    box = (mx - pad, my - pad, mw + pad * 2, mh + pad * 2)

    write("mark.svg", svg(mark_full(0, 0, w, H), *box,
                          "The LoveQuay mark: a heart-shaped pool with a swim ladder"))
    write("mark-reversed.svg", svg(
        mark_full(0, 0, w, H, NAVY_LT, WATER_LT, COPE_DK, NAVY), *box,
        "The LoveQuay mark, reversed"))
    write("mark-flat.svg", svg(mark_flat(0, 0, w, H), *box,
                               "The LoveQuay mark in two flat colours"))
    write("mark-navy.svg", svg(mark_mono(0, 0, w, H, NAVY), *box,
                               "The LoveQuay mark in navy"))
    write("mark-white.svg", svg(mark_mono(0, 0, w, H, WHITE), *box,
                                "The LoveQuay mark reversed in white"))
    write("mark-red.svg", svg(mark_mono(0, 0, w, H, SIGN), *box,
                              "The LoveQuay mark in sign red"))

    print("wordmark")
    cap = 200.0
    ww = word_width(cap)
    wbox = (-4, -4, ww + 8, cap + word_desc(cap) + 8)
    write("wordmark.svg", svg(wordmark(0, cap, cap, SIGN)[0], *wbox, "LOVEQUAY"))
    write("wordmark-navy.svg", svg(wordmark(0, cap, cap, NAVY)[0], *wbox, "LOVEQUAY"))
    write("wordmark-white.svg", svg(wordmark(0, cap, cap, WHITE)[0], *wbox, "LOVEQUAY"))

    print("lockups")
    colour = lambda x, y, a, b: mark_full(x, y, a, b)                      # noqa: E731
    rev = lambda x, y, a, b: mark_full(x, y, a, b, NAVY_LT, WATER_LT,      # noqa: E731
                                       COPE_DK, NAVY)
    L = "LoveQuay Swim Pier"
    write("logo-stacked.svg", stacked(colour, SIGN, NAVY, L))
    write("logo-stacked-white.svg", stacked(rev, WHITE, "#8FD0FF", L))
    write("logo-horizontal.svg", horizontal(colour, SIGN, NAVY, L))
    write("logo-horizontal-white.svg", horizontal(rev, WHITE, "#8FD0FF", L))
    write("logo-inline.svg", inline(colour, SIGN, L))
    write("logo-inline-white.svg", inline(rev, WHITE, L))

    print("icons")
    write("favicon.svg", tile(NAVY, NAVY_LT, WATER_LT, "#061E4A", NAVY))
    write("tile-white.svg", tile(WHITE, BASIN, WATER, NAVY, WHITE))
    write("tile-word-navy.svg", word_tile(NAVY, WHITE))
    write("tile-word-red.svg", word_tile(SIGN, WHITE))
    write("tile-word-white.svg", word_tile(WHITE, SIGN))
    write("tile-word-blue.svg", word_tile(BASIN, WHITE))

    if want_png:
        print("png")
        png("mark.svg", "mark-512.png", 512)
        png("mark.svg", "mark-1024.png", 1024)
        png("logo-stacked.svg", "logo-stacked-1000.png", 1000)
        png("logo-horizontal.svg", "logo-horizontal-1200.png", 1200)
        png("logo-horizontal-white.svg", "logo-horizontal-white-1200.png", 1200)
        png("logo-inline.svg", "logo-inline-800.png", 800)
        png("favicon.svg", "favicon-16.png", 16)
        png("favicon.svg", "favicon-32.png", 32)
        png("favicon.svg", "apple-touch-icon.png", 180)
        png("favicon.svg", "icon-192.png", 192)
        png("favicon.svg", "icon-512.png", 512)
        png("tile-white.svg", "tile-white-512.png", 512)
        for n in ("tile-word-navy", "tile-word-red", "tile-word-white", "tile-word-blue"):
            png(f"{n}.svg", f"{n}-512.png", 512)
        for s in (180, 64, 32, 16):
            png("tile-word-navy.svg", f"tile-word-navy-{s}.png", s)
        png("wordmark.svg", "wordmark-1200.png", 1200)
        ico()
    else:
        print("  (skipped — pass --png to render)")

    print("done")


if __name__ == "__main__":
    main()
