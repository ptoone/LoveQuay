#!/usr/bin/env python3
"""The Citizen of LoveQuay certificate.

    python tools/build_certificate.py

Writes assets/brand/certificate-citizen.svg and drafts/certificate.html.

US Letter, landscape, 11 x 8.5in. There is deliberately no bleed: this is meant
to come out of whatever printer is to hand, so the border sits inside the page
and nothing needs trimming. A print shop that wants bleed can be given the same
file on a larger sheet.

It is built to match the citizen card — the same guilloche, the same navy and
sign red, the same Article One printed where it can be read — so that a card
and a certificate look like they came from the same office.

All type is outlined, so the file carries no font dependency.

Signatures
----------
The two rules at the foot are left empty on purpose. They get signed by hand.
A signature set in a script typeface is a picture of a signature, and the only
thing a signature line is for is evidence that a particular person put a pen
on it.
"""

import base64
import io
import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from textpath import Typesetter  # noqa: E402
from build_idcard_draft import rosette_family  # noqa: E402  (same guilloche as the card)

BRAND = os.path.join(ROOT, "assets", "brand")
OUT = os.path.join(BRAND, "certificate-citizen.svg")

# The faint photograph behind everything. Swap this file to change the picture;
# it is pre-desaturated and pre-lightened by tools so the SVG needs no filter,
# which print RIPs handle unevenly.
BACKDROP = os.path.join(BRAND, "certificate-backdrop.jpg")
BACKDROP_OPACITY = 0.075
PREVIEW = os.path.join(ROOT, "drafts", "certificate.html")

W, H = 792.0, 612.0            # US Letter landscape, points
MID = W / 2.0

NAVY = "#082A65"
NAVY_DEEP = "#051B44"
BASIN = "#0056B8"
SIGN = "#FE010F"
SAND = "#FBF9F2"
INK = "#101B2D"
MUTED = "#5A6A80"
RULE = "#8FA6C4"

ts_semi = Typesetter(os.path.join(HERE, "Poppins-SemiBold.ttf"))
ts_med = Typesetter(os.path.join(HERE, "Poppins-Medium.ttf"))
ts_bold = Typesetter(os.path.join(HERE, "Poppins-ExtraBold.ttf"))

SIGNATORIES = ["Steve Mann", "Perry Toone"]

WARNINGS = []


# ------------------------------------------------------------------ type ----

def fit(ts, text, target_w, tracking=0.0):
    _, adv = ts.path(text, size=100.0, tracking=tracking)
    return 100.0 * target_w / adv


def centred(ts, text, size, baseline, fill, tracking=0.0, cx=MID, opacity=None):
    _, adv = ts.path(text, size=size, tracking=tracking)
    d, _ = ts.path(text, size=size, tracking=tracking, x=cx - adv / 2.0, y=baseline)
    op = f' opacity="{opacity}"' if opacity is not None else ""
    return f'<path d="{d}" fill="{fill}"{op}/>'


def centred_fit(ts, text, target_w, baseline, fill, tracking=0.0, cx=MID):
    return centred(ts, text, fit(ts, text, target_w, tracking), baseline, fill, tracking, cx)


# --------------------------------------------------------------- artwork ----

def brand_art(name, cx, top, width=None, height=None):
    """Place a brand SVG, centred on cx, top edge at `top`."""
    s = io.open(os.path.join(BRAND, name), encoding="utf-8").read()
    vx, vy, vw, vh = (float(v) for v in
                      re.search(r'viewBox="([-\d. ]+)"', s).group(1).split())
    inner = s[s.index(">", s.index("<svg")) + 1: s.rindex("</svg>")]
    tag = re.sub(r"[^a-z0-9]", "", name.lower())
    for m in set(re.findall(r'id="([^"]+)"', inner)):
        inner = inner.replace(f'id="{m}"', f'id="{m}-{tag}"').replace(f"url(#{m})", f"url(#{m}-{tag})")
    k = (width / vw) if width is not None else (height / vh)
    x = cx - (vw * k) / 2.0
    g = (f'<g transform="translate({x:.3f},{top:.3f}) scale({k:.5f}) '
         f'translate({-vx:.3f},{-vy:.3f})">{inner}</g>')
    return g, vh * k, vw * k


def guilloche():
    """The same engraving as the citizen card: a rosette in each corner and a
    wave field across the sheet, pale enough to read as paper rather than as
    pattern."""
    parts = []
    # r must divide R or the petal count explodes: gcd(62,10)=2 gives 31 petals,
    # which fills in solid and reads as a smudge. gcd(48,8)=8 gives six.
    for cx, cy in ((104, 106), (W - 104, 106), (104, H - 106), (W - 104, H - 106)):
        parts.append(rosette_family(cx, cy, 48, 8, 22, 14, 0.3))
    waves = []
    for i in range(30):
        ph = i * 0.42
        amp = 9 + 4 * math.sin(i * 0.5)
        y0 = H * 0.08 + i * (H * 0.030)
        pts = []
        x = -20.0
        while x <= W + 20:
            y = y0 + amp * math.sin(x / 120.0 + ph) + 4 * math.sin(x / 47.0 - ph)
            pts.append(f"{x:.0f},{y:.1f}")
            x += 14
        waves.append(f'<path d="M{"L".join(pts)}" fill="none" stroke="currentColor" stroke-width="0.3"/>')
    return (f'<g color="{BASIN}" opacity="0.13">{"".join(parts)}</g>'
            f'<g color="{BASIN}" opacity="0.08">{"".join(waves)}</g>')


def backdrop():
    """A photograph of the pier, faint enough to be paper rather than picture."""
    if not os.path.exists(BACKDROP):
        WARNINGS.append(f"no backdrop at {os.path.relpath(BACKDROP, ROOT)} - printing plain")
        return ""
    b64 = base64.b64encode(io.open(BACKDROP, "rb").read()).decode("ascii")
    return (f'<image x="0" y="0" width="{W}" height="{H}" preserveAspectRatio="xMidYMid slice" '
            f'opacity="{BACKDROP_OPACITY}" '
            f'href="data:image/jpeg;base64,{b64}" xlink:href="data:image/jpeg;base64,{b64}"/>')


def border():
    o = 26.0        # outer rule
    i = 34.0        # inner hairline
    return (
        f'<rect x="{o}" y="{o}" width="{W-2*o}" height="{H-2*o}" rx="4" fill="none" '
        f'stroke="{NAVY}" stroke-width="3"/>'
        f'<rect x="{i}" y="{i}" width="{W-2*i}" height="{H-2*i}" rx="2" fill="none" '
        f'stroke="{SIGN}" stroke-width="0.8" opacity="0.85"/>'
    )


def seal(cx, cy, r):
    """A struck seal: the mark inside a legend ring. Same idea as the sticker,
    drawn here at the size the sheet wants."""
    text = "REPUBLIC OF LOVEQUAY \u00b7 CITIZEN \u00b7 "
    tracking = 0.02

    # size the legend so its outer ink lands on the ring
    size = 6.0
    for _ in range(50):
        _, adv100 = ts_semi.path(text, size=100.0, tracking=tracking)
        y0, y1 = ts_semi.bbox(text, size=100.0, tracking=tracking)[1::2]
        cap = (y1 - y0) * size / 100.0
        radius = (r - 5.0) - cap
        size = 100.0 * (2 * math.pi * radius) / adv100

    advs = []
    for ch in text:
        _, a = ts_semi.path(ch, size=size)
        advs.append(a + tracking * size)
    lead = text.split(" \u00b7 ")[0]
    _, lead_adv = ts_semi.path(lead, size=size, tracking=tracking)
    ang = -math.degrees((lead_adv + tracking * size) / radius) / 2.0

    glyphs = []
    for ch, a in zip(text, advs):
        step = math.degrees(a / radius)
        if ch.strip():
            d, _ = ts_semi.path(ch, size=size, x=-(a - tracking * size) / 2.0, y=0.0)
            glyphs.append(f'<g transform="translate({cx},{cy}) rotate({ang+step/2:.4f}) '
                          f'translate(0,{-radius:.3f})"><path d="{d}"/></g>')
        ang += step

    mk, mh, mw = brand_art("mark-navy.svg", cx, cy - r * 0.40, height=r * 0.78)
    return (
        f'<g opacity="0.92">'
        f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{NAVY}" stroke-width="1.6"/>'
        f'<circle cx="{cx}" cy="{cy}" r="{radius - cap*1.1:.2f}" fill="none" stroke="{NAVY}" stroke-width="0.7"/>'
        f'<g fill="{NAVY}">{"".join(glyphs)}</g>'
        f'{mk}</g>'
    )


def writeline(cx, y, width, caption, cap_size=7.5):
    """A rule to write on, with its caption underneath."""
    out = (f'<rect x="{cx-width/2:.1f}" y="{y:.1f}" width="{width:.1f}" height="0.9" '
           f'fill="{RULE}"/>')
    out += centred(ts_semi, caption, cap_size, y + 13.5, MUTED, tracking=0.20, cx=cx)
    return out


def signature(cx, name, y_rule, width=180.0, role="Founding Citizen"):
    """A rule to sign on, with the name and role printed under it.

    No facsimile sits above the rule. A signature that was set in a typeface
    would be a picture of a signature, and the whole value of the line is that
    somebody actually put a pen on it."""
    out = (f'<rect x="{cx-width/2:.1f}" y="{y_rule:.1f}" width="{width:.1f}" height="0.9" '
           f'fill="{NAVY}" opacity="0.55"/>')
    out += centred_fit(ts_semi, name.upper(), width * 0.52, y_rule + 15.0, NAVY, tracking=0.12, cx=cx)
    out += centred(ts_med, role, 8.5, y_rule + 27.0, MUTED, tracking=0.06, cx=cx)
    return out


# ----------------------------------------------------------- certificate ----

def certificate():
    body = [f'<rect x="0" y="0" width="{W}" height="{H}" fill="{SAND}"/>',
            backdrop(), guilloche(), border()]

    # The full lockup, not just the heart: the mark on its own reads as a blue
    # heart to anyone who does not already know it, and a certificate is
    # exactly the wrong place to be coy about whose it is.
    mk, mh, mw = brand_art("mark-navy.svg", MID, 46.0, height=42.0)
    body.append(mk)
    wm, wh, ww = brand_art("wordmark-navy.svg", MID, 96.0, width=186.0)
    body.append(wm)
    body.append(centred_fit(ts_semi, "REPUBLIC", 120.0, 156.0, SIGN, tracking=0.26))

    body.append(f'<rect x="{MID-110:.0f}" y="168" width="220" height="0.8" fill="{SIGN}" opacity="0.6"/>')

    body.append(centred_fit(ts_bold, "CERTIFICATE OF CITIZENSHIP", 420.0, 212.0, NAVY))

    body.append(centred(ts_med, "This is to certify that", 15.0, 252.0, MUTED, tracking=0.04))

    body.append(writeline(MID, 298.0, 460.0, "FULL NAME OF CITIZEN"))

    body.append(centred(ts_med, "has this day been admitted a Citizen of the Republic of LoveQuay,",
                        13.0, 346.0, INK, tracking=0.02))
    body.append(centred(ts_med, "with all the rights of any other person at the water's edge, and no others.",
                        13.0, 364.0, INK, tracking=0.02))

    body.append(writeline(MID - 150, 404.0, 230.0, "DATE ADMITTED"))
    body.append(writeline(MID + 150, 404.0, 230.0, "CITIZEN No."))

    body.append(centred(ts_semi, "“It is prohibited to prohibit swimming.”",
                        12.0, 452.0, SIGN, tracking=0.03))

    body.append(seal(MID, 514.0, 42.0))

    body.append(signature(MID - 252, SIGNATORIES[0], 526.0))
    body.append(signature(MID + 252, SIGNATORIES[1], 526.0))

    return (f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
            f'width="11in" height="8.5in" viewBox="0 0 {W:g} {H:g}">{"".join(body)}</svg>')


def main():
    os.makedirs(os.path.dirname(PREVIEW), exist_ok=True)
    svg = certificate()
    io.open(OUT, "w", encoding="utf-8", newline="\n").write(svg)
    print(f"   {os.path.relpath(OUT, ROOT)}  ({len(svg)/1024:.0f} KB)")

    b64 = base64.b64encode(svg.encode("utf-8")).decode("ascii")
    html = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<title>Citizen certificate &mdash; draft</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap" rel="stylesheet">
<style>
  body {{ margin:0; padding:30px 16px 60px; background:#e8ecf2;
         font-family:Inter,system-ui,sans-serif; color:#101B2D; }}
  .wrap {{ max-width:1180px; margin:0 auto; }}
  h1 {{ font-size:20px; margin:0 0 4px; }}
  p.sub {{ margin:0 0 22px; color:#5A6A80; font-size:13.5px; }}
  img {{ width:100%; height:auto; display:block; background:#fff;
         box-shadow:0 18px 50px -24px rgba(8,42,101,.5); border-radius:3px; }}
  .note {{ margin-top:20px; background:#fff8e1; border-left:4px solid #e9b949;
           padding:12px 16px; border-radius:0 8px 8px 0; font-size:13px; line-height:1.55; }}
</style></head>
<body><div class="wrap">
  <h1>Citizen of LoveQuay &mdash; certificate</h1>
  <p class="sub">US Letter landscape, 11 &times; 8.5&Prime;. No bleed &mdash; it prints on any printer.</p>
  <img src="data:image/svg+xml;base64,{b64}" alt="">
  <p class="note">The signature rules are left blank to be signed by hand. The backdrop is
    <code>assets/brand/certificate-backdrop.jpg</code> &mdash; replace that file to change the
    picture.</p>
</div></body></html>
"""
    io.open(PREVIEW, "w", encoding="utf-8", newline="\n").write(html)
    print(f"   {os.path.relpath(PREVIEW, ROOT)}")

    if WARNINGS:
        print()
        for w in WARNINGS:
            print("   note:", w)


if __name__ == "__main__":
    main()
