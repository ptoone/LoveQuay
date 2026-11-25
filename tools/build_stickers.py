#!/usr/bin/env python3
"""One-inch square stickers for the LoveQuay Republic.

    python tools/build_stickers.py

Writes print-ready SVG into assets/brand/, a PNG of each at 600 dpi for
printers that want raster, and drafts/stickers.html to look at them — at actual
size, enlarged, and with the bleed and trim marked.

An inch is not much room, so the whole thing is built to a print spec rather
than eyeballed:

    artboard   1.25 x 1.25 in   90 x 90 pt   (the file)
    bleed      0.125 in          9 pt        (trimmed off)
    trim       1.00 x 1.00 in   72 x 72 pt   (the sticker)
    safe       0.75 x 0.75 in   54 x 54 pt   (keep type inside this)

All type is outlined from Poppins by tools/textpath.py, so the files carry no
font dependency and a printer cannot substitute something else. Every line is
*solved* to a target width rather than set at a guessed point size: at this
scale a line that overshoots by a millimetre is the difference between legible
and not. Nothing is allowed below MIN_CAP, because vinyl and a 1 mm cutting
tolerance will not hold finer than that.
"""

import base64
import io
import math
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from textpath import Typesetter  # noqa: E402
import build_brand as bb  # noqa: E402  (the traced sign alphabet)

OUT = os.path.join(ROOT, "assets", "brand")
PREVIEW = os.path.join(ROOT, "drafts", "stickers.html")

PT = 72.0                      # points per inch
ART = 90.0                     # artboard, points (1.25 in)
BLEED = 9.0                    # per side
TRIM0, TRIM1 = BLEED, ART - BLEED              # 9 .. 81
SAFE0, SAFE1 = BLEED * 2, ART - BLEED * 2      # 18 .. 72
MID = ART / 2
CORNER = 9.0                   # 0.125 in radius, the usual square-sticker cut

# Nothing smaller than this gets printed. 4 pt is about the floor for cut vinyl;
# below it the counters in a, e and o fill in and the whole line goes grey.
MIN_CAP = 3.6

NAVY = "#082A65"
NAVY_DEEP = "#051B44"      # the scrim over photographs
WHITE = "#FFFFFF"
SIGN = "#FE010F"
SKY = "#9ED2FF"

SEMI = os.path.join(HERE, "Poppins-SemiBold.ttf")
XBOLD = os.path.join(HERE, "Poppins-ExtraBold.ttf")

ts_semi = Typesetter(SEMI)
ts_bold = Typesetter(XBOLD)


# ----------------------------------------------------------------- type ----

def fit(ts, text, target_w, tracking=0.0):
    """The point size at which `text` is exactly `target_w` wide.

    Width is linear in size — tracking is expressed in em, so it scales too —
    which makes this an exact solve rather than a search."""
    _, adv = ts.path(text, size=100.0, tracking=tracking)
    return 100.0 * target_w / adv


def line(ts, text, target_w, baseline, fill, tracking=0.0, name=""):
    """One centred line, solved to width, returned as an SVG path.

    Reports anything that lands under MIN_CAP instead of quietly shipping type
    nobody can read."""
    size = fit(ts, text, target_w, tracking)
    x0, y0, x1, y1 = ts.bbox(text, size=size, tracking=tracking)
    cap = y1 - y0
    if cap < MIN_CAP:
        WARNINGS.append(f"{name or text!r}: cap {cap:.2f}pt is under the {MIN_CAP}pt floor")
    d, adv = ts.path(text, size=size, tracking=tracking, x=MID - target_w / 2.0, y=baseline)
    left = MID - target_w / 2.0
    # ts.bbox() is already in SVG orientation — the typesetter flips Y when it
    # records — so the ink runs from baseline+y0 (above) to baseline+y1. Negating
    # here instead put the ink below the baseline and under-reported every
    # clearance by about a line's height.
    note_extent(left + x0, baseline + y0, left + x1, baseline + y1)
    return f'<path d="{d}" fill="{fill}"/>', cap


WARNINGS = []
EXTENT = []          # [x0, y0, x1, y1] of every piece of ink on the current sticker


RADIAL = []          # outer radii of ring artwork on the current sticker


def note_extent(x0, y0, x1, y1):
    EXTENT.append((x0, y0, x1, y1))


def note_radial(r):
    """Ring text is measured by its radius. Taking the bounding square of a
    ring and then checking its corners would overstate the reach by a factor
    of root two and condemn a layout that is nowhere near the blade."""
    RADIAL.append(r)


RADIUS = (TRIM1 - TRIM0) / 2.0      # 36pt: a 1in circle die


def chord(dy, r=None):
    """How wide a line can be at `dy` from the centre of a circular die.

    This is the whole difference between designing for a square and for a
    circle. In a square every line gets the same width; in a circle the
    available width is a chord, 2*sqrt(r^2 - dy^2), so it closes fast as a line
    moves away from the middle. A layout that fits a 1in square will run off a
    1in circle at the top and bottom."""
    r = RADIUS if r is None else r
    if abs(dy) >= r:
        return 0.0
    return 2.0 * math.sqrt(r * r - dy * dy)


def clearance(die="square"):
    """Smallest gap between the ink and the cut line, in points.

    The type-size floor keeps lines readable; this keeps them on the sticker.
    Between the two, the layout numbers cannot be nudged into something that
    prints badly without the build saying so.

    For a circular die the test is per corner, not per edge: the worst case is
    whichever corner of whichever piece of ink sits furthest from the centre."""
    if not EXTENT:
        return None
    if die == "circle":
        worst = max(RADIAL) if RADIAL else 0.0
        for x0, y0, x1, y1 in EXTENT:
            for cx, cy in ((x0, y0), (x1, y0), (x0, y1), (x1, y1)):
                worst = max(worst, math.hypot(cx - MID, cy - MID))
        return RADIUS - worst
    x0 = min(e[0] for e in EXTENT); y0 = min(e[1] for e in EXTENT)
    x1 = max(e[2] for e in EXTENT); y1 = max(e[3] for e in EXTENT)
    return min(x0 - TRIM0, TRIM1 - x1, y0 - TRIM0, TRIM1 - y1)


# ---------------------------------------------------------------- marks ----

def art(name, top, width=None, height=None):
    """Place a brand SVG, centred, scaled to `width` or `height`, with its top
    edge at `top`. Returns the group and the height it occupies.

    The brand files are used whole and never redrawn here, so a sticker cannot
    drift from the logo the rest of the site uses. That matters most for the
    wordmark: LOVEQUAY is traced from the lettering on the LOVE sign itself and
    is not any typeface, so setting those letters in a font would be a
    different thing wearing the same name."""
    s = io.open(os.path.join(OUT, name), encoding="utf-8").read()
    vx, vy, vw, vh = (float(v) for v in
                      re.search(r'viewBox="([-\d. ]+)"', s).group(1).split())
    inner = s[s.index(">", s.index("<svg")) + 1: s.rindex("</svg>")]
    # namespace the ids so two pieces of brand art on one page cannot fight
    # over the same mask
    tag = re.sub(r"[^a-z0-9]", "", name.lower())
    for m in set(re.findall(r'id="([^"]+)"', inner)):
        inner = inner.replace(f'id="{m}"', f'id="{m}-{tag}"').replace(f"url(#{m})", f"url(#{m}-{tag})")

    k = (width / vw) if width is not None else (height / vh)
    w, h = vw * k, vh * k
    x = MID - w / 2.0
    note_extent(x, top, x + w, top + h)
    g = (f'<g transform="translate({x:.3f},{top:.3f}) scale({k:.5f}) '
         f'translate({-vx:.3f},{-vy:.3f})">{inner}</g>')
    return g, h


def mark(colour, height, cy):
    """The mark alone, centred on (MID, cy)."""
    g, _ = art("mark-white.svg" if colour == "white" else "mark-navy.svg",
               cy - height / 2.0, height=height)
    return g


def wordmark(colour, top, width):
    """LOVEQUAY, traced from the sign. Returns the group and its height."""
    return art("wordmark-white.svg" if colour == "white" else "wordmark-navy.svg",
               top, width=width)


def rule(y, w, colour, thick=0.7):
    note_extent(MID - w / 2, y, MID + w / 2, y + thick)
    return (f'<rect x="{MID - w/2:.2f}" y="{y:.2f}" width="{w:.2f}" '
            f'height="{thick}" fill="{colour}"/>')


def dot(x, y, r, colour):
    return f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{r:.2f}" fill="{colour}"/>'


# -------------------------------------------------------------- sticker ----

def wrap(body, bg, guides=False, die="square"):
    """An artboard with bleed. The background runs the full 1.25in so the
    colour survives the trim wherever the blade actually lands; the rounded
    rect is the cut line, drawn only on the proof."""
    g = ""
    if guides:
        edge = (f'<rect x="0" y="0" width="{ART}" height="{ART}" fill="none" '
                f'stroke="#FF00FF" stroke-width="0.4" stroke-dasharray="2 2"/>')
        if die == "circle":
            cut = (f'<circle cx="{MID}" cy="{MID}" r="{RADIUS}" fill="none" '
                   f'stroke="#00C2FF" stroke-width="0.5"/>')
            safe = (f'<circle cx="{MID}" cy="{MID}" r="{RADIUS-5}" fill="none" '
                    f'stroke="#00FF88" stroke-width="0.4" stroke-dasharray="1.5 1.5"/>')
        else:
            cut = (f'<rect x="{TRIM0}" y="{TRIM0}" width="{TRIM1-TRIM0}" height="{TRIM1-TRIM0}" '
                   f'rx="{CORNER}" fill="none" stroke="#00C2FF" stroke-width="0.5"/>')
            safe = (f'<rect x="{SAFE0}" y="{SAFE0}" width="{SAFE1-SAFE0}" height="{SAFE1-SAFE0}" '
                    f'rx="{CORNER/2}" fill="none" stroke="#00FF88" stroke-width="0.4" '
                    f'stroke-dasharray="1.5 1.5"/>')
        g = edge + cut + safe
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'xmlns:xlink="http://www.w3.org/1999/xlink" width="1.25in" height="1.25in" '
        f'viewBox="0 0 {ART:g} {ART:g}">'
        f'<rect x="0" y="0" width="{ART}" height="{ART}" fill="{bg}"/>'
        f'{body}{g}</svg>'
    )


def sticker_republic(reverse=True, guides=False):
    """The identity sticker: mark, name, and what the Republic is for."""
    EXTENT.clear()
    bg = NAVY if reverse else WHITE
    ink = WHITE if reverse else NAVY
    quiet = SKY if reverse else "#5A6A80"
    accent = SIGN

    white = reverse
    body = [mark("white" if white else "navy", 16.0, 25.5)]

    # The real wordmark, not LOVEQUAY set in a font.
    wm, wh = wordmark("white" if white else "navy", 36.5, 54.0)
    body.append(wm)

    d, _ = line(ts_semi, "REPUBLIC", 40.0, 56.0, accent, tracking=0.22, name="REPUBLIC")
    body.append(d)

    body.append(rule(59.5, 34.0, quiet, 0.6))

    d, _ = line(ts_semi, "SMALL TECH", 44.0, 65.5, quiet, tracking=0.07, name="SMALL TECH")
    body.append(d)
    d, _ = line(ts_semi, "OPEN STANDARDS", 60.0, 71.5, quiet, tracking=0.03, name="OPEN STANDARDS")
    body.append(d)

    return wrap("".join(body), bg, guides)


def sticker_email(reverse=True, guides=False):
    """The call-to-action sticker: the address is the hero, everything else
    sits under it."""
    EXTENT.clear()
    bg = NAVY if reverse else WHITE
    ink = WHITE if reverse else NAVY
    quiet = SKY if reverse else "#5A6A80"

    white = reverse

    # Identity at the top in the real wordmark, the address as the hero, what
    # the Republic stands for underneath. No separate mark: at this size the
    # wordmark alone identifies it and the room is better spent on the address.
    wm, wh = wordmark("white" if white else "navy", 19.0, 52.0)
    body = [wm]

    d, _ = line(ts_semi, "REPUBLIC", 38.0, 37.5, SIGN, tracking=0.22, name="REPUBLIC (b)")
    body.append(d)

    d, _ = line(ts_bold, "@lovequay.com", 58.0, 54.0, ink, name="@lovequay.com")
    body.append(d)

    body.append(rule(58.0, 34.0, quiet, 0.6))

    d, _ = line(ts_semi, "SMALL TECH", 40.0, 65.0, quiet, tracking=0.07, name="SMALL TECH (b)")
    body.append(d)
    d, _ = line(ts_semi, "OPEN STANDARDS", 56.0, 71.5, quiet, tracking=0.03, name="OPEN STANDARDS (b)")
    body.append(d)

    return wrap("".join(body), bg, guides)


def sticker_republic_round(reverse=True, guides=False):
    """The identity sticker on a 1in circle die.

    Less fits here than on the square of the same nominal size: the die loses
    the corners, and every line is limited by its chord rather than by the full
    width. The layout is pulled in towards the middle to pay for it."""
    EXTENT.clear()
    bg = NAVY if reverse else WHITE
    ink = WHITE if reverse else NAVY
    quiet = SKY if reverse else "#5A6A80"
    white = reverse

    body = [mark("white" if white else "navy", 12.0, 25.0)]

    wm, wh = wordmark("white" if white else "navy", 34.0, 44.0)
    body.append(wm)

    d, _ = line(ts_semi, "REPUBLIC", 34.0, 50.0, SIGN, tracking=0.22, name="REPUBLIC (r)")
    body.append(d)

    body.append(rule(53.0, 28.0, quiet, 0.6))

    d, _ = line(ts_semi, "SMALL TECH", 40.0, 58.5, quiet, tracking=0.07, name="SMALL TECH (r)")
    body.append(d)
    d, _ = line(ts_semi, "OPEN STANDARDS", 47.0, 64.5, quiet, tracking=0.02, name="OPEN STANDARDS (r)")
    body.append(d)

    return wrap("".join(body), bg, guides, die="circle")


def sticker_email_round(reverse=True, guides=False):
    """The address sticker on a 1in circle die."""
    EXTENT.clear()
    bg = NAVY if reverse else WHITE
    ink = WHITE if reverse else NAVY
    quiet = SKY if reverse else "#5A6A80"
    white = reverse

    # REPUBLIC comes off this one. On a 1in circle there is room for the
    # wordmark, the address and the two values, and not for a fifth line at a
    # size anyone could read — the wordmark already says whose address it is.
    wm, wh = wordmark("white" if white else "navy", 27.0, 40.0)
    body = [wm]

    d, _ = line(ts_bold, "@lovequay.com", 48.0, 49.0, ink, name="@lovequay.com (re)")
    body.append(d)

    body.append(rule(53.0, 28.0, quiet, 0.6))

    d, _ = line(ts_semi, "SMALL TECH", 39.0, 58.5, quiet, tracking=0.07, name="SMALL TECH (re)")
    body.append(d)
    d, _ = line(ts_semi, "OPEN STANDARDS", 47.5, 64.5, quiet, tracking=0.02, name="OPEN STANDARDS (re)")
    body.append(d)

    return wrap("".join(body), bg, guides, die="circle")


def arc_text(ts, text, size, radius, fill, tracking=0.0, start_deg=None):
    """Set `text` around a circle, letters upright with their tops outward.

    Each glyph gets its own angular slot sized by its advance, so the spacing
    stays even whatever the letters are. The run reads clockwise from the top;
    on a ring that closes, the bottom of the sticker is upside down to the
    reader, which is how a seal is meant to work — you turn it to read it."""
    advances = []
    for ch in text:
        _, adv = ts.path(ch, size=size)
        advances.append(adv + tracking * size)
    total = sum(advances)
    span = math.degrees(total / radius)
    ang = start_deg if start_deg is not None else -span / 2.0

    parts = []
    for ch, adv in zip(text, advances):
        step = math.degrees(adv / radius)
        if ch.strip():
            d, _ = ts.path(ch, size=size, x=-(adv - tracking * size) / 2.0, y=0.0)
            parts.append(f'<g transform="translate({MID},{MID}) rotate({ang + step/2:.4f}) '
                         f'translate(0,{-radius:.3f})"><path d="{d}"/></g>')
        ang += step
    cap = ts.bbox("H", size=size)[3] - ts.bbox("H", size=size)[1]
    note_radial(radius + cap)
    return f'<g fill="{fill}">{"".join(parts)}</g>'


def fit_ring(ts, text, outer_r, tracking):
    """Size the ring so its outermost ink lands exactly on `outer_r`.

    Cap height and radius chase each other — bigger type sits on a smaller
    circle, which leaves less room for type — so this iterates to the fixed
    point rather than guessing."""
    size = 5.0
    for _ in range(60):
        _, adv100 = ts.path(text, size=100.0, tracking=tracking)
        y0, y1 = ts.bbox(text, size=100.0, tracking=tracking)[1], ts.bbox(text, size=100.0, tracking=tracking)[3]
        cap = (y1 - y0) * size / 100.0
        radius = outer_r - cap
        size = 100.0 * (2 * math.pi * radius) / adv100
    return size, cap, radius


def stacked_words(cap, width, top, fill):
    """LOVE over QUAY in the sign alphabet, both justified to the same width.

    This is the same lettering as the wordmark, stacked — the eight traced
    characters are the only alphabet the brand has, so the words are set from
    them rather than from a typeface."""
    lead = cap * 0.22
    g1 = bb.justify(bb.LOVE, width, cap)
    g2 = bb.justify(bb.QUAY, width, cap)
    x = MID - width / 2.0
    b1 = top + cap
    b2 = b1 + cap + lead
    body = bb.line(bb.LOVE, x, b1, cap, g1) + bb.line(bb.QUAY, x, b2, cap, g2)
    desc = (bb.B[4][3] - bb.BASELINE) * cap / bb.BASELINE      # the Q tail
    note_extent(x, top, x + width, b2 + desc)
    # evenodd, not the default nonzero. The traced sign letters carry their
    # counters as contours wound the same way as the outside, so under nonzero
    # the holes in O, A and Q fill solid. build_brand sets the same rule
    # wherever it draws this alphabet.
    return f'<g fill="{fill}" fill-rule="evenodd">{body}</g>', (b2 + desc) - top


def sticker_seal(reverse=True, guides=False, full_ring=True):
    """A seal: stacked LOVE / QUAY in the middle, text right round the edge.

    Red field, white art. With `full_ring` the ring carries everything,
    including LOVEQUAY REPUBLIC, which costs tighter letter-spacing to fit.
    Without it, REPUBLIC moves to the middle under the words — where a seal
    usually puts the name anyway — and the ring gets room to breathe."""
    EXTENT.clear(); RADIAL.clear()
    bg = SIGN if reverse else WHITE
    ink = WHITE if reverse else SIGN

    dot = " · "
    if full_ring:
        ring = ("LOVEQUAY REPUBLIC" + dot + "SMALL TECH" + dot + "OPEN STANDARDS"
                + dot + "SWIM AT OWN RISK" + dot + "@LOVEQUAY.COM" + dot)
        track, outer = -0.04, 32.0
    else:
        ring = ("SMALL TECH" + dot + "OPEN STANDARDS" + dot + "SWIM AT OWN RISK"
                + dot + "@LOVEQUAY.COM" + dot)
        track, outer = 0.02, 31.0

    size, cap, radius = fit_ring(ts_semi, ring, outer, track)

    # Start the ring so its leading phrase sits centred at twelve o'clock.
    # Centring the whole string instead puts the middle of the legend at the
    # top, which on a closed ring buries the name at the bottom.
    lead = ring.split(dot)[0]
    _, lead_adv = ts_semi.path(lead, size=size, tracking=track)
    start = -math.degrees((lead_adv + track * size) / radius) / 2.0
    body = [arc_text(ts_semi, ring, size, radius, ink, tracking=track, start_deg=start)]

    # A hairline inside the ring, the way a stamp separates its legend from its
    # device. It also stops the ring and the words reading as one block.
    inner = radius - cap * 0.9
    body.append(f'<circle cx="{MID}" cy="{MID}" r="{inner:.2f}" fill="none" '
                f'stroke="{ink}" stroke-width="0.55" opacity="0.55"/>')
    note_radial(inner + 0.3)

    if full_ring:
        w, top, c = 30.0, 31.5, 11.0
        g, h = stacked_words(c, w, top, ink)
        body.append(g)
    else:
        w, top, c = 29.0, 28.5, 10.5
        g, h = stacked_words(c, w, top, ink)
        body.append(g)
        d, _ = line(ts_semi, "REPUBLIC", 33.0, top + h + 7.0, ink,
                    tracking=0.20, name="REPUBLIC (seal)")
        body.append(d)

    return wrap("".join(body), bg, guides, die="circle")


def sticker_logo_round(reverse=False, guides=False):
    """Just the mark and the name, on a 1in circle. White field by default.

    With only three elements there is room to set them properly, so this is the
    one round sticker where nothing is fighting for space and the wordmark can
    be read across a room rather than squinted at."""
    EXTENT.clear(); RADIAL.clear()
    bg = NAVY if reverse else WHITE
    ink = WHITE if reverse else NAVY

    body = [mark("white" if reverse else "navy", 21.0, 31.5)]

    wm, _ = wordmark("white" if reverse else "navy", 46.0, 48.0)
    body.append(wm)

    d, _ = line(ts_semi, "REPUBLIC", 42.0, 65.0, SIGN, tracking=0.22, name="REPUBLIC (logo)")
    body.append(d)

    return wrap("".join(body), bg, guides, die="circle")


PHOTO = os.path.join(OUT, "sticker-dive-source.jpg")


def sticker_photo(round_die=True, guides=False):
    """The dive, with the wordmark over it.

    The photograph is embedded rather than linked, so the file a printer
    receives is the whole artwork and cannot arrive with a missing image.

    A scrim does the work of making the wordmark readable. White type straight
    onto a photograph is a gamble — it depends on whatever happens to be behind
    each letter — so the lower half is graded into navy and the type sits on
    that. The gradient starts above the waterline and is weakest where the
    picture is already dark, which keeps the dive and the reflection intact."""
    EXTENT.clear(); RADIAL.clear()

    b64 = base64.b64encode(io.open(PHOTO, "rb").read()).decode("ascii")
    grad_id = "scrim"
    parts = [
        f'<defs><linearGradient id="{grad_id}" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0.34" stop-color="{NAVY_DEEP}" stop-opacity="0"/>'
        f'<stop offset="0.62" stop-color="{NAVY_DEEP}" stop-opacity="0.55"/>'
        f'<stop offset="1" stop-color="{NAVY_DEEP}" stop-opacity="0.93"/>'
        f'</linearGradient></defs>',
        f'<image x="0" y="0" width="{ART}" height="{ART}" '
        f'preserveAspectRatio="xMidYMid slice" '
        f'href="data:image/jpeg;base64,{b64}" '
        f'xlink:href="data:image/jpeg;base64,{b64}"/>',
        f'<rect x="0" y="0" width="{ART}" height="{ART}" fill="url(#{grad_id})"/>',
    ]

    if round_die:
        wm, _ = wordmark("white", 57.5, 42.0)
        parts.append(wm)
        return wrap("".join(parts), NAVY_DEEP, guides, die="circle")

    wm, _ = wordmark("white", 59.0, 52.0)
    parts.append(wm)
    return wrap("".join(parts), NAVY_DEEP, guides)


# ---------------------------------------------------------------- output ----

def main():
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(os.path.dirname(PREVIEW), exist_ok=True)

    files = {
        "sticker-republic.svg": sticker_republic(reverse=True),
        "sticker-republic-light.svg": sticker_republic(reverse=False),
        "sticker-email.svg": sticker_email(reverse=True),
        "sticker-email-light.svg": sticker_email(reverse=False),
        "sticker-republic-round.svg": sticker_republic_round(reverse=True),
        "sticker-republic-round-light.svg": sticker_republic_round(reverse=False),
        "sticker-email-round.svg": sticker_email_round(reverse=True),
        "sticker-email-round-light.svg": sticker_email_round(reverse=False),
        "sticker-seal.svg": sticker_seal(reverse=True, full_ring=True),
        "sticker-seal-light.svg": sticker_seal(reverse=False, full_ring=True),
        "sticker-seal-roomy.svg": sticker_seal(reverse=True, full_ring=False),
        "sticker-logo-round-light.svg": sticker_logo_round(reverse=False),
        "sticker-logo-round.svg": sticker_logo_round(reverse=True),
        "sticker-dive-round.svg": sticker_photo(round_die=True),
        "sticker-dive.svg": sticker_photo(round_die=False),
    }
    for name, svg in files.items():
        io.open(os.path.join(OUT, name), "w", encoding="utf-8", newline="\n").write(svg)
        print(f"   {name}")

    guided = {
        "sticker-republic.svg": sticker_republic(True, guides=True),
        "sticker-republic-light.svg": sticker_republic(False, guides=True),
        "sticker-email.svg": sticker_email(True, guides=True),
        "sticker-email-light.svg": sticker_email(False, guides=True),
        "sticker-republic-round.svg": sticker_republic_round(True, guides=True),
        "sticker-republic-round-light.svg": sticker_republic_round(False, guides=True),
        "sticker-email-round.svg": sticker_email_round(True, guides=True),
        "sticker-email-round-light.svg": sticker_email_round(False, guides=True),
        "sticker-seal.svg": sticker_seal(True, guides=True, full_ring=True),
        "sticker-seal-light.svg": sticker_seal(False, guides=True, full_ring=True),
        "sticker-seal-roomy.svg": sticker_seal(True, guides=True, full_ring=False),
        "sticker-logo-round-light.svg": sticker_logo_round(False, guides=True),
        "sticker-logo-round.svg": sticker_logo_round(True, guides=True),
        "sticker-dive-round.svg": sticker_photo(True, guides=True),
        "sticker-dive.svg": sticker_photo(False, guides=True),
    }
    io.open(PREVIEW, "w", encoding="utf-8", newline="\n").write(preview(files, guided))
    print("   drafts/stickers.html")

    # Clearance is measured on a fresh build of each face, because EXTENT only
    # holds whichever sticker was drawn last.
    print()
    for name, fn, die in (("sticker-republic.svg", sticker_republic, "square"),
                          ("sticker-email.svg", sticker_email, "square"),
                          ("sticker-republic-round.svg", sticker_republic_round, "circle"),
                          ("sticker-email-round.svg", sticker_email_round, "circle"),
                          ("sticker-seal.svg", lambda r: sticker_seal(r, full_ring=True), "circle"),
                          ("sticker-seal-roomy.svg", lambda r: sticker_seal(r, full_ring=False), "circle"),
                          ("sticker-logo-round-light.svg", lambda r: sticker_logo_round(False), "circle"),
                          ("sticker-dive-round.svg", lambda r: sticker_photo(True), "circle"),
                          ("sticker-dive.svg", lambda r: sticker_photo(False), "square")):
        fn(True)
        c = clearance(die)
        mm = c / PT * 25.4
        flag = "" if mm >= 1.0 else "   *** TOO CLOSE TO THE CUT ***"
        print(f"   {name:32s} ink clears the cut by {c:5.2f}pt / {mm:4.2f}mm{flag}")

    # The warnings list is appended to on every call, and the guided twins run
    # the same lines again, so report each distinct complaint once.
    if WARNINGS:
        print("\n  TYPE UNDER THE FLOOR:")
        for w in sorted(set(WARNINGS)):
            print("   -", w)
    else:
        print(f"\n  all type at or above the {MIN_CAP}pt floor")


def preview(files, guided):
    def embed(svg):
        return "data:image/svg+xml;base64," + base64.b64encode(svg.encode("utf-8")).decode("ascii")

    cards = []
    for name, svg in files.items():
        proof = guided[name]
        # The print file is a square either way — the die is chosen at the
        # printer, not baked into the artwork — so this crops the central inch
        # to show what actually comes back after it is cut.
        round_die = "round" in name
        cut_shape = "50%" if round_die else f"{CORNER / ART * 125:.1f}px"
        cut = f"""
          <div class="cell">
            <div class="cut" style="border-radius:{cut_shape}">
              <img src="{embed(svg)}" alt="">
            </div>
            <span class="cap">as cut{' &mdash; round die' if round_die else ''}</span>
          </div>"""
        cards.append(f"""
      <figure class="card">
        <figcaption class="name">{name}</figcaption>
        <div class="row">
          <div class="cell">
            <img class="actual" src="{embed(svg)}" alt="">
            <span class="cap">file, actual size</span>
          </div>{cut}
          <div class="cell">
            <img class="big" src="{embed(svg)}" alt="">
            <span class="cap">6&times;</span>
          </div>
          <div class="cell">
            <img class="big" src="{embed(proof)}" alt="">
            <span class="cap">bleed / cut / safe</span>
          </div>
        </div>
      </figure>""")

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<title>Stickers &mdash; draft</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Poppins:wght@600;700&display=swap" rel="stylesheet">
<style>
  * {{ box-sizing: border-box; }}
  body {{ margin:0; padding:40px 20px 70px; background:#eef1f6;
         font-family:Inter,system-ui,sans-serif; color:#101B2D; }}
  .wrap {{ max-width:1000px; margin:0 auto; }}
  h1 {{ font-family:Poppins,sans-serif; font-size:24px; margin:0 0 4px; color:{NAVY}; }}
  .sub {{ margin:0 0 32px; color:#5A6A80; font-size:14px; }}
  .card {{ margin:0 0 26px; background:#fff; border-radius:14px; padding:20px 22px;
           box-shadow:0 10px 30px -18px rgba(8,42,101,.5); }}
  .name {{ font-family:"Roboto Mono",ui-monospace,Consolas,monospace; font-size:12px;
           color:#5A6A80; margin-bottom:14px; }}
  .row {{ display:flex; gap:30px; align-items:flex-end; flex-wrap:wrap; }}
  .cell {{ display:flex; flex-direction:column; align-items:center; gap:7px; }}
  .cap {{ font-size:10px; letter-spacing:.14em; text-transform:uppercase; color:#8A94A6; }}
  /* 1.25in at 96 css px per inch = 120px; the sticker inside it is 1in = 96px */
  .actual {{ width:120px; height:120px; }}
  /* The file is 1.25in; the sticker is the middle 1in. Crop to that and round
     the corners the way the die will, to show what comes back from the cutter. */
  .cut {{ width:96px; height:96px; overflow:hidden; position:relative; }}
  .cut img {{ width:120px; height:120px; position:absolute; left:-12px; top:-12px; }}
  .big {{ width:360px; height:360px; image-rendering:auto; }}
  .note {{ background:#fff8e1; border-left:4px solid #e9b949; padding:14px 18px;
           border-radius:0 10px 10px 0; font-size:13.5px; line-height:1.55; }}
</style>
</head>
<body>
<div class="wrap">
  <h1>Stickers &mdash; draft</h1>
  <p class="sub">1&Prime; square, 0.125&Prime; bleed, 0.125&Prime; corner radius. Actual size assumes a
    96&nbsp;dpi screen.</p>
  {''.join(cards)}
  <p class="note"><strong>Magenta</strong> is the artboard edge &mdash; colour must run to it.
    <strong>Blue</strong> is where it gets cut. <strong>Green</strong> is the safe area; type
    inside it survives a cutting tolerance. Nothing important should cross the blue line.</p>
</div>
</body>
</html>
"""


if __name__ == "__main__":
    main()
