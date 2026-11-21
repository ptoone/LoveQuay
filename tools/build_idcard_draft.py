#!/usr/bin/env python3
"""Draft of the LoveQuay citizen card — front and back, at real ID-1 size.

This writes drafts/idcard.html, which is a *preview*, not a print pipeline. It
exists so the card can be looked at and argued about before anything is sent to
a printer. The eventual tools/build_idcard.py will share the number scheme and
the artwork, but will emit press-ready PDF with bleed.

The front is pitched at an Ontario driver's licence: pale blue field, dark navy
type, photo at the left, a ghost portrait at the right. Everything that reads as
official is doing real work:

  - the guilloche is a family of hypotrochoids, the curve engravers have used on
    banknotes since the 1810s, because a lathe-drawn line is hard to redraw by
    hand and dies in a photocopier. Ours is also a water ripple, which is the
    only reason it belongs on this particular card;
  - the MRZ strip is the ICAO 9303 TD-1 layout, padded with the same filler
    character. It encodes nothing a reader could not already see on the front;
  - the backdrop is the pier itself, shot back east along the bollards toward
    the LOVE sign, with the sign's own traced lettering ghosted over it;
  - there is no expiry date. The card is valid exactly as long as the
    subscription behind it is paid, and the QR is the only honest way to ask.
    A printed expiry would be a second source of truth, and the wrong one;
  - the back carries Article One, because a card that bought special access
    would contradict it, and the contradiction should be printed on the card.

ID-1 is 85.6 x 54 mm. At PX_PER_MM = 8 that is 684.8 x 432 px, which is big
enough to judge type sizes on screen and small enough to put both faces side by
side on a laptop.
"""

import base64
import pathlib
import re

import segno

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
BRAND = ROOT / "assets" / "brand"
IMG = ROOT / "assets" / "img"
OUT = ROOT / "drafts" / "idcard.html"

PX_PER_MM = 8.0
CARD_W = 85.6 * PX_PER_MM          # 684.8
CARD_H = 54.0 * PX_PER_MM          # 432.0
RADIUS = 3.18 * PX_PER_MM          # ID-1 corner radius, 3.18 mm

# The long lens back east along the deck: bollards receding toward the LOVE
# sign, so one frame carries both the pier and the sign. Swap the slug to try
# another; love-wall is the sign on its own, pier-length is the dusk hero.
BACKDROP = "pier-telephoto-640.webp"

NAVY = "#082A65"
NAVY_DEEP = "#051B44"
BASIN = "#0056B8"
WATER = "#007FFF"
SIGN = "#FE010F"
INK = "#101B2D"

# The light-blue field. Ontario's licence is mostly white with blue weather in
# it, not a block of blue, so these stay pale and the type carries the contrast.
SKY = "#EAF4FF"
SKY_MID = "#D3E6FA"
SKY_DEEP = "#BFD9F4"
EDGE = "#A9C9EC"
LABEL = "#4D6B96"

# --------------------------------------------------------------------- number

ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXY"   # 31 symbols: no I L O U Z


def check_char(body: str) -> str:
    """Mirror of assets/js/lqid.js and the Worker. Weighted sum mod 31."""
    total = sum(ALPHABET.index(c) * (i + 1) for i, c in enumerate(body))
    return ALPHABET[total % 31]


def make_number(body: str) -> str:
    assert len(body) == 7 and all(c in ALPHABET for c in body), body
    d = body + check_char(body)
    return f"LQ-{d[:4]}-{d[4:]}"


# -------------------------------------------------------------------- artwork

def rosette(cx, cy, R, r, d, rot=0.0, steps=200):
    """One hypotrochoid, rotated bodily by `rot`.

    A hypotrochoid closes after r / gcd(R, r) turns and draws R / gcd(R, r)
    petals, so the petal count is chosen by picking r as a divisor of R. Keeping
    it low and then rotating many copies of the same curve is what gives the
    woven, evenly-spaced look; raising the petal count instead just fills the
    middle in solid, which is a blob rather than an engraving.
    """
    import math
    g = math.gcd(int(R), int(r))
    turns = r // g
    k = (R - r) / r
    ca, sa = math.cos(rot), math.sin(rot)
    pts = []
    for i in range(steps + 1):
        t = 2 * math.pi * turns * i / steps
        x = (R - r) * math.cos(t) + d * math.cos(k * t)
        y = (R - r) * math.sin(t) - d * math.sin(k * t)
        pts.append(f"{cx + x * ca - y * sa:.1f},{cy + x * sa + y * ca:.1f}")
    return "M" + "L".join(pts) + "Z"


def rosette_family(cx, cy, R, r, d, copies, stroke):
    """One curve rotated through a single petal's worth of arc. The copies
    interleave, which is the whole trick."""
    import math
    petals = R // math.gcd(int(R), int(r))
    span = 2 * math.pi / petals
    return "".join(
        f'<path d="{rosette(cx, cy, R, r, d, rot=i * span / copies)}" '
        f'fill="none" stroke="currentColor" stroke-width="{stroke}"/>'
        for i in range(copies)
    )


GUILLOCHE_STROKE = 0.42


def guilloche_defs(w, h):
    """The artwork, emitted once. Both faces reference it with <use>, which is
    the difference between a 100 KB page and a 1 MB one — the curve families run
    to thousands of points, and the browser pane will not open the big version."""
    import math
    parts = []

    cx, cy = w * 0.785, h * 0.54
    parts.append(rosette_family(cx, cy, 160, 20, 78, 16, GUILLOCHE_STROKE))  # 8 petals
    parts.append(rosette_family(cx, cy, 96, 16, 44, 12, GUILLOCHE_STROKE))   # 6 petals

    # A band of phase-shifted sines across the whole face. Guilloche on a
    # banknote; a wave set here.
    for i in range(26):
        ph = i * 0.42
        amp = 11 + 5 * math.sin(i * 0.5)
        y0 = h * 0.10 + i * (h * 0.034)
        pts = []
        x = -20.0
        while x <= w + 20:
            y = y0 + amp * math.sin(x / 46.0 + ph) + 5 * math.sin(x / 17.0 - ph)
            pts.append(f"{x:.0f},{y:.1f}")
            x += 7
        parts.append(
            f'<path d="M{"L".join(pts)}" fill="none" stroke="currentColor" '
            f'stroke-width="{GUILLOCHE_STROKE}"/>'
        )

    return (f'<svg width="0" height="0" aria-hidden="true" '
            f'style="position:absolute">'
            f'<defs><g id="guil">{"".join(parts)}</g></defs></svg>')


def guilloche(w, h, opacity):
    return (f'<svg class="guilloche" viewBox="0 0 {w:.1f} {h:.1f}" '
            f'preserveAspectRatio="none" aria-hidden="true" '
            f'style="opacity:{opacity}"><use href="#guil"/></svg>')


def inline_svg(name, cls):
    """Pull a brand SVG in whole so the card carries no external art."""
    s = (BRAND / name).read_text(encoding="utf-8")
    s = re.sub(r'\s(width|height)="[^"]*"', "", s, count=2)
    s = s.replace("<svg ", f'<svg class="{cls}" ', 1)
    # The ids inside each mark are shared between files; namespace them so two
    # marks on one page do not fight over the same mask.
    tag = re.sub(r"[^a-z0-9]", "", name.lower())
    for m in set(re.findall(r'id="([^"]+)"', s)):
        s = s.replace(f'id="{m}"', f'id="{m}-{tag}"')
        s = s.replace(f"url(#{m})", f"url(#{m}-{tag})")
    return s


def data_uri(path):
    """Embed rather than link. The draft has to survive being opened from
    anywhere, including the preview pane's sandboxed origin where a relative
    path resolves to nothing."""
    mime = "image/webp" if path.suffix == ".webp" else "image/jpeg"
    return f"data:{mime};base64," + base64.b64encode(path.read_bytes()).decode("ascii")


# ------------------------------------------------------------------------- qr

def qr_svg(url, size, dark=NAVY):
    """Drawn at build time, not fetched. A card generator that needed a CDN at
    print time would be a bad card generator, and error level M survives a
    scuffed card without making the modules too fine for a 300 dpi print."""
    qr = segno.make(url, error="m")
    n = qr.symbol_size(border=0)[0]        # modules per side, border stripped
    svg = qr.svg_inline(dark=dark, light=None, border=0)
    # segno sizes the symbol in modules and omits a viewBox, so scaling it means
    # adding one rather than overwriting the width.
    svg = re.sub(r'\s(width|height)="[^"]*"', "", svg, count=2)
    return svg.replace(
        "<svg ",
        f'<svg width="{size}" height="{size}" viewBox="0 0 {n} {n}" '
        f'shape-rendering="crispEdges" ',
        1,
    )


# ------------------------------------------------------------------------ mrz

def mrz(number, surname, given, dob, since):
    """ICAO 9303 TD-1, three lines of 30. Filler is '<'. The document code for
    anything that is not a passport or a visa is a free choice; 'IR' reads as
    identity card, Republic. The issuing state is three letters, and ours is not
    on the ISO list, so LQY is a courtesy to the eye rather than a claim.

    Line two opens with the date of birth in YYMMDD, which is where TD-1 really
    puts it. The expiry field that would follow it is left as filler, because
    this card does not have one."""
    digits = number.replace("LQ-", "").replace("-", "")

    def pad(s, n):
        return (s + "<" * n)[:n]

    def ymd(iso):
        return iso.replace("-", "")[2:]

    l1 = "IR" + "LQY" + pad(digits, 9) + "<" * 15
    l2 = ymd(dob) + "<<" + "<" * 6 + "<LQY" + ymd(since) + "<" * 6
    l3 = pad(surname.upper() + "<<" + given.upper().replace(" ", "<"), 30)
    # The filler is a literal '<', so an unescaped MRZ opens tags: "<<PERRY"
    # parses as an element named "perry" and quietly eats the rest of the card.
    return [ln[:30].replace("<", "&lt;") for ln in (l1, l2, l3)]


# ----------------------------------------------------------------------- card

def front(d):
    verify = f"https://lovequay.com/verify.html?id={d['number']}"
    return f"""
<div class="card card--front">
  <div class="backdrop" aria-hidden="true"></div>
  {guilloche(CARD_W, CARD_H, 0.26)}
  <div class="signmark" aria-hidden="true">{inline_svg("wordmark-navy.svg", "wm")}</div>
  <div class="sheen" aria-hidden="true"></div>

  <header class="hdr">
    <div class="hdr-mark">{inline_svg("mark-navy.svg", "mk")}</div>
    <div class="hdr-txt">
      <div class="state">The Republic of LoveQuay</div>
      <div class="doc">Citizen Card &middot; Carte de citoyen</div>
    </div>
    <div class="hdr-tab">Citizen</div>
  </header>

  <div class="body">
    <div class="col-l">
      <div class="portrait">
        <div class="portrait-ghost">{inline_svg("mark-navy.svg", "mk")}</div>
        <span class="portrait-cap">PHOTO</span>
      </div>
      <div class="holo" aria-hidden="true">
        <div class="holo-mark">{inline_svg("mark-white.svg", "mk")}</div>
      </div>
    </div>

    <dl class="fields">
      <div class="f f--wide"><dt>Surname / Nom</dt><dd>{d['surname']}</dd></div>
      <div class="f f--wide"><dt>Given names / Pr&eacute;noms</dt><dd>{d['given']}</dd></div>
      <div class="f f--wide"><dt>Citizen No. / N&ordm; de citoyen</dt><dd class="mono num">{d['number']}</dd></div>
      <div class="f"><dt>Date of birth</dt><dd class="mono">{d['dob']}</dd></div>
      <div class="f"><dt>Active since</dt><dd class="mono">{d['since']}</dd></div>
      <div class="f"><dt>Home water</dt><dd>{d['water']}</dd></div>
    </dl>

    <div class="col-r">
      <div class="qr">{qr_svg(verify, 112)}</div>
      <div class="qr-cap">Scan to verify</div>
      <div class="ghost">
        <div class="ghost-img">{inline_svg("mark-navy.svg", "mk")}</div>
      </div>
    </div>
  </div>

  <div class="mrz mono">{"<br>".join(mrz(d['number'], d['surname'], d['given'], d['dob'], d['since']))}</div>
</div>
"""


def back(d):
    return f"""
<div class="card card--back">
  <div class="backdrop backdrop--back" aria-hidden="true"></div>
  {guilloche(CARD_W, CARD_H, 0.16)}
  <div class="signmark signmark--back" aria-hidden="true">{inline_svg("wordmark-navy.svg", "wm")}</div>

  <!-- A microtext band rather than a magnetic stripe. A stripe that encoded
       nothing would be a prop, and this card already promises on its own face
       not to claim more than it is. Microtext is a real anti-copy feature:
       it survives a press and dies in a photocopier. -->
  <div class="microband" aria-hidden="true">
    <span>{"REPUBLIC OF LOVEQUAY &middot; " * 14}</span>
  </div>

  <div class="back-body">
    <h3>Anyone may check this card.</h3>
    <p>Scan the code on the front, or type the number at
       <strong>lovequay.com/verify.html</strong>. It reads as valid for exactly
       as long as the subscription behind it is paid &mdash; which is why there
       is no expiry date printed anywhere on it. The check answers valid or not
       valid and nothing else: no name, no address, no holder.</p>

    <div class="article">
      <span class="article-no">Article One</span>
      <p>It is prohibited to prohibit swimming. This card buys no right to the
         water that its holder did not already have, and gives its holder no
         priority over anyone else on the deck.</p>
    </div>
  </div>

  <div class="notes">
    <div class="note">
      <span class="note-h">What this is</span>
      <p>A receipt for an annual subscription and a name on a mailbox. It is not
         a licence, a permit, or a ticket.</p>
    </div>
    <div class="note">
      <span class="note-h">If it stops working</span>
      <p>The card reads as not valid once the subscription lapses. There is
         nothing else to cancel and nothing to return.</p>
    </div>
  </div>

  <div class="sig">
    <div class="sig-line"><span class="mono">{d['number']}</span></div>
    <div class="sig-cap">Signature of holder</div>
  </div>

  <footer class="back-foot">
    <span>Issued by the Republic of LoveQuay &middot; Toronto</span>
    <span>If found, hand to any Friend of Love Quay</span>
    <span>Not a government document &middot; no legal status</span>
  </footer>
</div>
"""


def page(d):
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<title>Citizen card &mdash; draft</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Poppins:wght@600;700&family=Roboto+Mono:wght@400;500;700&display=swap" rel="stylesheet">
<style>
  :root {{
    --navy: {NAVY}; --navy-deep: {NAVY_DEEP}; --basin: {BASIN};
    --water: {WATER}; --sign: {SIGN}; --ink: {INK};
    --sky: {SKY}; --sky-mid: {SKY_MID}; --sky-deep: {SKY_DEEP};
    --edge: {EDGE}; --label: {LABEL};
    --card-w: {CARD_W:.1f}px; --card-h: {CARD_H:.1f}px; --r: {RADIUS:.1f}px;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0; padding: 48px 24px 72px;
    font-family: Inter, system-ui, sans-serif;
    background: #e8ecf2;
    background-image: radial-gradient(circle at 50% 0%, #fff 0%, #e2e8f0 70%);
    color: var(--ink);
  }}
  .wrap {{ max-width: 1520px; margin: 0 auto; }}
  .page-head {{ text-align: center; margin-bottom: 40px; }}
  .page-head h1 {{ font-family: Poppins, sans-serif; font-weight: 700; font-size: 26px;
                   margin: 0 0 6px; color: var(--navy); letter-spacing: -.01em; }}
  .page-head p {{ margin: 0; color: #5A6A80; font-size: 14px; }}
  .deck {{ display: flex; gap: 44px; justify-content: center; flex-wrap: wrap; }}
  .slot-cap {{ text-align: center; margin-top: 14px; font-size: 12px; letter-spacing: .14em;
               text-transform: uppercase; color: #7A8699; font-weight: 600; }}

  /* ------------------------------------------------------------- the card -- */
  .card {{
    position: relative; width: var(--card-w); height: var(--card-h);
    border-radius: var(--r); overflow: hidden; color: var(--navy);
    box-shadow: 0 2px 2px rgba(8,42,101,.10), 0 24px 48px -18px rgba(8,42,101,.40),
                0 0 0 1px rgba(8,42,101,.14);
    font-size: 16px;
    background: linear-gradient(118deg, #F3F9FF 0%, var(--sky) 26%,
                var(--sky-mid) 58%, var(--sky-deep) 84%, #E4F0FD 100%);
  }}
  .guilloche {{ position: absolute; inset: 0; width: 100%; height: 100%;
                pointer-events: none; color: var(--basin); }}
  .mono {{ font-family: "Roboto Mono", ui-monospace, Consolas, monospace; }}

  /* The pier itself, looking back east along the bollards to the LOVE sign.
     Masked so it is weather on the right and nothing behind the photo. */
  .backdrop {{
    position: absolute; inset: 0;
    background-image: url("{data_uri(IMG / BACKDROP)}");
    background-size: cover; background-position: 50% 52%;
    opacity: .16; filter: grayscale(.5) contrast(1.04);
    -webkit-mask-image: linear-gradient(97deg, transparent 12%,
      rgba(0,0,0,.35) 38%, rgba(0,0,0,.85) 68%, #000 100%);
            mask-image: linear-gradient(97deg, transparent 12%,
      rgba(0,0,0,.35) 38%, rgba(0,0,0,.85) 68%, #000 100%);
  }}
  .backdrop--back {{ opacity: .10;
    -webkit-mask-image: linear-gradient(255deg, transparent 20%, rgba(0,0,0,.6) 60%, #000 100%);
            mask-image: linear-gradient(255deg, transparent 20%, rgba(0,0,0,.6) 60%, #000 100%); }}

  /* LOVEQUAY, traced from the sign's own lettering, ghosted across the foot. */
  .signmark {{ position: absolute; left: -9%; right: -9%; bottom: 11%;
               opacity: .045; pointer-events: none; }}
  .signmark .wm {{ width: 100%; height: auto; display: block; }}
  .signmark--back {{ bottom: 20%; opacity: .04; }}

  .sheen {{
    position: absolute; inset: 0;
    background: linear-gradient(108deg, transparent 30%, rgba(255,255,255,.40) 46%,
                rgba(255,255,255,.08) 58%, transparent 70%);
  }}

  /* header */
  .hdr {{ position: relative; display: flex; align-items: center; gap: 11px;
          padding: 13px 20px 9px; }}
  .hdr::after {{ content: ""; position: absolute; left: 20px; right: 20px; bottom: 0;
                 height: 2px; background: linear-gradient(90deg,
                 var(--sign) 0 58px, rgba(8,42,101,.42) 58px, rgba(8,42,101,.06)); }}
  .hdr-mark {{ width: 25px; flex: none; }}
  .hdr-mark .mk {{ width: 100%; height: auto; display: block; }}
  .hdr-txt {{ flex: 1; min-width: 0; }}
  .state {{ font-family: Poppins, sans-serif; font-weight: 700; font-size: 15.5px;
            letter-spacing: .055em; text-transform: uppercase; line-height: 1.1;
            color: var(--navy); }}
  .doc {{ font-size: 9.5px; letter-spacing: .20em; text-transform: uppercase;
          color: var(--label); margin-top: 3px; font-weight: 600; }}
  .hdr-tab {{ flex: none; font-family: Poppins, sans-serif; font-weight: 700;
              font-size: 11px; letter-spacing: .13em; text-transform: uppercase;
              color: #fff; background: var(--sign); padding: 5px 10px;
              border-radius: 3px; box-shadow: 0 2px 7px rgba(254,1,15,.35); }}

  /* body */
  .body {{ position: relative; display: flex; gap: 16px; padding: 14px 20px 0; }}

  .col-l {{ flex: none; width: 132px; display: flex; flex-direction: column; gap: 10px; }}
  .portrait {{
    position: relative; height: 204px; border-radius: 4px;
    background: linear-gradient(165deg, #fff, #E8F2FD);
    border: 1px solid var(--edge);
    display: flex; align-items: center; justify-content: center; overflow: hidden;
  }}
  .portrait-ghost {{ position: absolute; width: 84px; opacity: .16; }}
  .portrait-ghost .mk {{ width: 100%; height: auto; display: block; }}
  .portrait-cap {{ position: relative; font-size: 9px; letter-spacing: .22em;
                   color: var(--label); font-weight: 700; }}

  /* The OVD patch. On a printed card this is a foil; here it is the same
     optical idea rendered in CSS so the layout reserves the right space. */
  .holo {{
    position: relative; height: 54px; border-radius: 4px; overflow: hidden;
    background: conic-gradient(from 210deg at 32% 44%,
      #7CE7D8 0deg, #9EC8FF 58deg, #C9A8FF 116deg, #FFC2D6 172deg,
      #FFE6A3 228deg, #A8F0C6 286deg, #7CE7D8 360deg);
    opacity: .55; display: flex; align-items: center; justify-content: center;
    border: 1px solid var(--edge);
  }}
  .holo::after {{
    content: ""; position: absolute; inset: 0;
    background: repeating-linear-gradient(72deg, rgba(255,255,255,.42) 0 1px,
                rgba(255,255,255,0) 1px 5px);
  }}
  .holo-mark {{ position: relative; width: 28px; opacity: .85;
                filter: drop-shadow(0 1px 1px rgba(8,42,101,.35)); }}
  .holo-mark .mk {{ width: 100%; height: auto; display: block; }}

  .fields {{ flex: 1; min-width: 0; margin: 0; height: 268px;
             display: grid; grid-template-columns: repeat(3, 1fr);
             gap: 12px 14px; align-content: start; }}
  .f--wide {{ grid-column: 1 / -1; }}
  .f dt {{ font-size: 7.5px; letter-spacing: .17em; text-transform: uppercase;
           color: var(--label); font-weight: 700; margin-bottom: 2px; }}
  .f dd {{ margin: 0; font-size: 15px; font-weight: 600; line-height: 1.15;
           color: var(--navy);
           white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
  .f--wide dd {{ font-size: 22px; letter-spacing: .005em; }}
  .f dd.mono {{ font-size: 14px; font-weight: 500; letter-spacing: .02em; }}
  .num {{ color: {BASIN} !important; font-weight: 700 !important;
          font-size: 23px !important; letter-spacing: .055em !important; }}

  .col-r {{ flex: none; width: 112px; }}
  .qr {{ width: 112px; height: 112px; background: #fff; padding: 6px;
         border-radius: 3px; border: 1px solid var(--edge); }}
  .qr svg {{ width: 100%; height: 100%; display: block; }}
  .qr-cap {{ margin: 5px 0 12px; text-align: center; font-size: 7.5px;
             letter-spacing: .16em; text-transform: uppercase;
             color: var(--label); font-weight: 700; }}
  /* The ghost portrait. Every modern licence carries a second, fainter copy of
     the photograph: it is hard to swap one picture without the other. */
  .ghost {{ height: 124px; border-radius: 4px; border: 1px dashed var(--edge);
            display: flex; align-items: center; justify-content: center;
            background: rgba(255,255,255,.30); }}
  .ghost-img {{ width: 58px; opacity: .22; }}
  .ghost-img .mk {{ width: 100%; height: auto; display: block; }}

  /* mrz */
  .mrz {{
    position: absolute; left: 0; right: 0; bottom: 0;
    background: rgba(255,255,255,.90); color: #0b1a33;
    border-top: 1px solid rgba(8,42,101,.22);
    padding: 8px 20px 7px; font-size: 12px; font-weight: 500;
    letter-spacing: .085em; line-height: 1.34;
  }}

  /* --------------------------------------------------------------- back --- */
  .card--back {{ background: linear-gradient(168deg, #FBFDFF 0%, #EDF5FE 48%, #E0EDFB 100%); }}

  .microband {{ position: absolute; left: 0; right: 0; top: 22px; height: 34px;
                background: linear-gradient(180deg, var(--navy), var(--navy-deep));
                overflow: hidden; display: flex; align-items: center; }}
  .microband span {{ white-space: nowrap; font-size: 4.6px; letter-spacing: .34em;
                     font-weight: 600; color: rgba(255,255,255,.55);
                     padding-left: 6px; }}

  .back-body {{ position: relative; padding: 70px 20px 0; }}
  .back-body h3 {{ font-family: Poppins, sans-serif; font-size: 15px; font-weight: 700;
                   margin: 0 0 6px; color: var(--navy); }}
  .back-body > p {{ margin: 0 0 12px; font-size: 11px; line-height: 1.5; color: #3C4A5F;
                    max-width: 92%; }}
  .article {{ border-left: 2.5px solid var(--sign); padding: 2px 0 2px 10px;
              max-width: 92%; }}
  .article-no {{ display: block; font-size: 8px; letter-spacing: .18em; text-transform: uppercase;
                 font-weight: 700; color: var(--sign); margin-bottom: 3px; }}
  .article p {{ margin: 0; font-size: 10.5px; line-height: 1.48; color: #3C4A5F;
                font-style: italic; }}

  .notes {{ position: relative; display: flex; gap: 20px; margin: 14px 20px 0;
            padding-top: 10px; border-top: 1px solid rgba(8,42,101,.14); }}
  .note {{ flex: 1; min-width: 0; }}
  .note-h {{ display: block; font-size: 7.5px; letter-spacing: .17em; font-weight: 700;
             text-transform: uppercase; color: var(--navy); margin-bottom: 2px; }}
  .note p {{ margin: 0; font-size: 9px; line-height: 1.45; color: #5A6A80; }}

  .sig {{ position: absolute; left: 20px; right: 20px; bottom: 36px; }}
  .sig-line {{ height: 34px; border-radius: 3px; background: repeating-linear-gradient(
                 -55deg, rgba(8,42,101,.05) 0 7px, rgba(8,42,101,.10) 7px 14px);
               border: 1px solid rgba(8,42,101,.18);
               display: flex; align-items: center; justify-content: flex-end;
               padding-right: 9px; }}
  .sig-line span {{ font-size: 10px; color: rgba(8,42,101,.52); letter-spacing: .05em; }}
  .sig-cap {{ font-size: 7.5px; letter-spacing: .17em; text-transform: uppercase;
              color: #7A8699; margin-top: 4px; font-weight: 700; }}

  .back-foot {{ position: absolute; left: 20px; right: 20px; bottom: 10px;
                display: flex; justify-content: space-between; gap: 10px;
                font-size: 7px; letter-spacing: .05em; color: #76829A;
                text-transform: uppercase; font-weight: 700; white-space: nowrap; }}

  @media (max-width: 860px) {{
    body {{ padding: 24px 12px 48px; }}
    .deck {{ gap: 28px; }}
    .card {{ transform: scale(.52); transform-origin: top center; }}
    .slot {{ height: calc(var(--card-h) * .52 + 8px); }}
  }}
</style>
</head>
<body>
{guilloche_defs(CARD_W, CARD_H)}
<div class="wrap">
  <div class="page-head">
    <h1>Citizen card &mdash; draft</h1>
    <p>ID-1, 85.6 &times; 54 mm, shown at actual size on a 96&nbsp;dpi screen. Not final.</p>
  </div>
  <div class="deck">
    <div class="slot">{front(d)}<div class="slot-cap">Front</div></div>
    <div class="slot">{back(d)}<div class="slot-cap">Back</div></div>
  </div>
</div>

</body>
</html>
"""


def main():
    d = {
        "surname": "TOONE",
        "given": "Perry",
        "number": make_number("4KQ7M2R"),
        "dob": "1979-11-02",
        "since": "2026-04-18",
        "water": "Lake Ontario",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(page(d), encoding="utf-8")
    kb = OUT.stat().st_size / 1024
    print(f"wrote {OUT.relative_to(ROOT)}  —  {d['number']}  —  {kb:.0f} KB")


if __name__ == "__main__":
    main()
