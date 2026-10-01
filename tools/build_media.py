"""Build the Media page and its preview assets.

    python tools/build_media.py [path-to-source-folder]

The originals are far too large for GitHub Pages — 4.7 GB across 41 files, seven
of them over GitHub's 100 MB per-file ceiling — so they live in an R2 bucket and
this page links out to them. What *is* committed here is a poster frame per item
plus one small looping preview of the splat, which together come to a few MB.

Writes media/ and regenerates media.html from the inventory below, so the
page can never drift out of step with the files it advertises. Nav and footer are
lifted from gallery.html at build time, so they stay identical to the other pages.
"""
import json
import os
import re
import subprocess
import sys

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
# Previews live at /media/ rather than under assets/, matching how they
# were uploaded to the repo.
OUT = os.path.join(ROOT, "media")
DEFAULT_SRC = r"C:/Users/p/Downloads/PeterStreetBasin2026sep06-1-001"

# Where each original is hosted. These files are too big and too varied to sit
# on one host — an image CDN will take the 17 MB GIF and refuse the 780 MB one —
# so every file carries its own URL.
#
# Paste a URL here as you upload each file. Anything still set to None is left
# off the page rather than published as a link that goes nowhere.
URLS = {
    # Event posters, in the repo.
    "LoveQuay-Saturdays-2pm-1080x1920-story.png": "download/LoveQuay-Saturdays-2pm-1080x1920-story.png",
    "LoveQuay-Saturdays-2pm-1080x1350.png": "download/LoveQuay-Saturdays-2pm-1080x1350.png",
    "LoveQuay-Saturdays-2pm-1080x1080.png": "download/LoveQuay-Saturdays-2pm-1080x1080.png",
    "LoveQuay-Saturdays-2pm-1920x1005-event.png": "download/LoveQuay-Saturdays-2pm-1920x1005-event.png",
    "LoveQuay-Saturdays-2pm-1920x1080.png": "download/LoveQuay-Saturdays-2pm-1920x1080.png",
    "LoveQuay-Saturdays-2pm-1200x500-banner.png": "download/LoveQuay-Saturdays-2pm-1200x500-banner.png",
    "LoveQuay-Saturdays-2pm-1500x500-banner.png": "download/LoveQuay-Saturdays-2pm-1500x500-banner.png",

    # In the repo, served from the site itself.
    "LoveQuay-splat-transparent-1280.webp": "download/LoveQuay-splat-transparent-1280.webp",

    # Too large for GitHub's 25 MB web upload, so not on the server yet. Both
    # files sit ready in download/; paste their paths back when they are up.
    "LoveQuay-splat-transparent-1920.webm": None,
    "LoveQuay_2026-09-17_rc0011b_merge001_20MCompColor_dbros.mp4": None,

    # On Blogger's image CDN.
    "LoveQuay-splat-transparent-640.gif": "https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEiYgQpZzKYpO7Bij6rXosVoZs-S1a1UpKDrXnoevR1affzvwijjW1gmxXJB3-NyxyvfTEfdF8QcUFsA4_wnwEfcQoA1jHpTieWX4TTgqXysumbn6SH1472Vro-ThsHKIwvLQWf8Rsdwnd1plU9N1LxD-rVUvvaOQoesP5fk3jUczg_9LvgS-U3ZmCzJcx4/s1600/LoveQuay-splat-transparent-640.gif",

    # Too big for the repo — paste the Box links here once they are up.
    "LoveQuay-splat-transparent-1920.gif": None,
    "LoveQuay-splat-transparent-3840.gif": None,
}

NAVY_RGB = (8, 42, 101)

# Which groups the page publishes. The rest stay defined below so they can be
# switched back on in one edit — add "mixes", "reels" or "basin" to this set.
ENABLED = {"splat", "posters"}

# --- inventory -------------------------------------------------------------
# (id, heading, aspect, blurb, [(filename, title, note), ...])
GROUPS = [
    ("splat", "The splat", "16x9",
     "The LoveQuay splat, rendered against transparency so it drops onto any "
     "footage. The same 19-second loop in both formats below — the GIF plays "
     "anywhere, the WebP is smaller and sharper. Larger sizes, and a WebM with "
     "VP9 alpha, are on the way.",
     [
         ("LoveQuay-splat-transparent-3840.gif", "GIF · 3840 wide", "Transparent. For 4K and print work."),
         ("LoveQuay-splat-transparent-1920.gif", "GIF · 1920 wide", "Transparent."),
         ("LoveQuay-splat-transparent-640.gif", "GIF · 640 wide", "Transparent. Small enough for chat and email."),
         ("LoveQuay-splat-transparent-1920.webm", "WebM · 1920 wide", "Transparent, VP9 alpha. Best quality per byte."),
         ("LoveQuay-splat-transparent-1280.webp", "WebP · 1280 wide", "Transparent, animated."),
         ("LoveQuay_2026-09-17_rc0011b_merge001_20MCompColor_dbros.mp4", "Master comp · 3840", "The 4K render this was cut from. No alpha. Re-encoded a little tighter so it fits the site — SSIM 0.99 against the original."),
     ]),
    ("posters", "Saturdays", "poster",
     "Come swim with us, Saturdays at 2 PM. Print it, post it, put it on a "
     "story — seven crops of the same artwork so it fits wherever you are "
     "sharing it.",
     [
         ("LoveQuay-Saturdays-2pm-1080x1920-story.png", "Story · 1080 × 1920",
          "Instagram and Facebook stories, TikTok."),
         ("LoveQuay-Saturdays-2pm-1080x1350.png", "Portrait · 1080 × 1350",
          "The tallest an Instagram feed post will run."),
         ("LoveQuay-Saturdays-2pm-1080x1080.png", "Square · 1080 × 1080",
          "Feed posts, and anywhere that crops to a square."),
         ("LoveQuay-Saturdays-2pm-1920x1005-event.png", "Event cover · 1920 × 1005",
          "The size Facebook wants for an event header."),
         ("LoveQuay-Saturdays-2pm-1920x1080.png", "Landscape · 1920 × 1080",
          "Plain 16:9, for slides, screens and video."),
         ("LoveQuay-Saturdays-2pm-1200x500-banner.png", "Banner · 1200 × 500",
          "Wide. Page headers, newsletters, the top of a listing."),
         ("LoveQuay-Saturdays-2pm-1500x500-banner.png", "Banner · 1500 × 500",
          "The same banner at the size X wants for a profile header."),
     ]),
    ("mixes", "Long-form mixes", "16x9",
     "Two-hour continuous mixes over a looping visual. Each full mix is well "
     "over a gigabyte, so there is a 60-second sample beside it. Try that first.",
     [
         ("NightMode-2hr-SAMPLE-60s.mp4", "Night Mode · 60-second sample", "Start here."),
         ("NightMode-2hr-mix-1080p.mp4", "Night Mode · full mix", "The whole two hours, 1080p."),
         ("404DreamsFound-2hr-SAMPLE-60s.mp4", "404 Dreams Found · 60-second sample", "Start here."),
         ("404DreamsFound-2hr-mix-1080p.mp4", "404 Dreams Found · full mix", "The whole two hours, 1080p."),
     ]),
    ("reels", "Reels", "9x16",
     "Vertical cuts from around the quay and the harbour.",
     [
         ("LoveQuay-swim-pier-9x16.mp4", "LoveQuay Swim Pier", ""),
         ("LoveQuay-SwimWithUs-Saturdays-9x16.mp4", "Swim with us · Saturdays", ""),
         ("LoveQuayLabs-SteveMann-9x16.mp4", "LoveQuay Labs · Steve Mann", ""),
         ("PeterStreetBasin-cleanup-reel-9x16.mp4", "Peter Street Basin cleanup", ""),
         ("BeachHead-Sept19-promo-9x16.mp4", "Beachhead · promo", ""),
         ("BeachheadSymposium-2026sep19-9x16.mp4", "Beachhead Symposium", "19 September 2026."),
         ("BoomerBuggy-WaterAccess-9x16.mp4", "Boomer Buggy · water access", ""),
         ("BoomerBuggy-fullclip-SAMPLE-25s.mp4", "Boomer Buggy · 25-second sample", ""),
         ("BoomerBuggy-fullclip-720p-preview.mp4", "Boomer Buggy · full clip, 720p", "Same cut, an eighth of the size."),
         ("BoomerBuggy-fullclip-9x16.mp4", "Boomer Buggy · full clip, 1080p", ""),
         ("PaddleboardingToBillyBishop-9x16.mp4", "Paddleboarding to Billy Bishop", ""),
         ("SharkQuiz-promo-9x16.mp4", "Shark Quiz · promo", ""),
         ("Toronto-Aquarium-CuriousPenguins-9x16.mp4", "Curious penguins", "Ripley's Aquarium."),
     ]),
    ("basin", "Peter Street Basin · 6 September 2026", "16x9",
     "Raw clips and stills from the basin, straight off the camera and untouched.",
     [(f, "", "") for f in [
         "20260906_142806.jpg", "20260906_142931.jpg", "20260906_142948.jpg",
         "20260906_142949.jpg", "20260906_161908.jpg",
         "20260906_143210.mp4", "20260906_143225.mp4", "20260906_143435.mp4",
         "20260906_152733.mp4", "20260906_152751.mp4", "20260906_155121.mp4",
         "20260906_155636.mp4", "20260906_155650.mp4", "20260906_155715.mp4",
         "20260906_161913.mp4", "20260906_161924.mp4", "20260906_161944.mp4",
     ]]),
]

STILL_EXT = (".jpg", ".jpeg", ".png", ".webp")


# --- helpers ---------------------------------------------------------------

def probe(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
         "stream=width,height:format=duration", "-of", "json", path],
        capture_output=True, text=True)
    try:
        d = json.loads(out.stdout)
        s = (d.get("streams") or [{}])[0]
        w, h = int(s.get("width") or 0), int(s.get("height") or 0)
        if w and h:
            return w, h, float(d.get("format", {}).get("duration") or 0)
    except Exception:
        pass
    try:                       # ffprobe cannot size an animated WebP; PIL can
        with Image.open(path) as im:
            n = getattr(im, "n_frames", 1)
            dur = (im.info.get("duration", 0) or 0) * n / 1000.0
            return im.width, im.height, dur
    except Exception:
        return 0, 0, 0.0


def human_size(n):
    if n >= 1e9:
        return f"{n / 1e9:.2f} GB"
    if n >= 1e6:
        return f"{n / 1e6:.0f} MB"
    return f"{n / 1e3:.0f} kB"


def human_time(s):
    if not s:
        return ""
    s = int(round(s))
    h, m, sec = s // 3600, (s % 3600) // 60, s % 60
    return f"{h}:{m:02d}:{sec:02d}" if h else f"{m}:{sec:02d}"


def slug(name):
    return re.sub(r"[^a-z0-9]+", "-", os.path.splitext(name)[0].lower()).strip("-")


def poster(src, stem, width=640):
    """One representative frame as WebP + JPEG. Alpha lands on navy."""
    tmp = os.path.join(OUT, "_frame.png")
    if src.lower().endswith(STILL_EXT):
        im = Image.open(src)
    else:
        _, _, dur = probe(src)
        subprocess.run(["ffmpeg", "-y", "-ss", str(max(0.2, dur * 0.25)), "-i", src,
                        "-frames:v", "1", "-vf", f"scale={width}:-2", tmp],
                       capture_output=True)
        if not os.path.exists(tmp):
            return False
        im = Image.open(tmp)
    if im.mode in ("RGBA", "LA", "P"):
        im = im.convert("RGBA")
        im = Image.alpha_composite(Image.new("RGBA", im.size, NAVY_RGB + (255,)), im)
    im = im.convert("RGB")
    im.thumbnail((width, width * 3), Image.LANCZOS)
    im.save(os.path.join(OUT, stem + ".webp"), quality=78, method=6)
    im.save(os.path.join(OUT, stem + ".jpg"), quality=78, progressive=True, optimize=True)
    if os.path.exists(tmp):
        os.remove(tmp)
    return True


def splat_preview(src):
    """Small looping MP4 of the splat on navy — MP4 carries no alpha."""
    dest = os.path.join(OUT, "splat-preview.mp4")
    subprocess.run(
        ["ffmpeg", "-y", "-f", "lavfi", "-i", f"color=c=0x082A65:s=960x540:d=20",
         "-i", src, "-filter_complex",
         "[1:v]scale=960:-2[v];[0:v][v]overlay=(W-w)/2:(H-h)/2:shortest=1,fps=24,format=yuv420p",
         "-c:v", "libx264", "-crf", "30", "-preset", "slow",
         "-movflags", "+faststart", "-an", dest],
        capture_output=True)
    return os.path.exists(dest)


def esc(s):
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
             .replace('"', "&quot;"))


# --- page ------------------------------------------------------------------

def chrome():
    """Nav and footer, taken from gallery.html so every page stays identical."""
    src = open(os.path.join(ROOT, "gallery.html"), encoding="utf-8").read()
    nav = re.search(r'<nav class="lq-nav.*?</nav>', src, re.S).group(0)
    nav = nav.replace(' aria-current="page"', "")
    nav = nav.replace('<a class="nav-link" href="media.html">',
                      '<a class="nav-link" aria-current="page" href="media.html">')
    foot = re.search(r'<footer class="lq-footer">.*?</footer>', src, re.S).group(0)
    return nav, foot


def card(item, aspect):
    name, title, note = item["file"], item["title"], item["note"]
    meta = " · ".join(x for x in [
        f"{item['w']} × {item['h']}" if item["w"] else "",
        human_time(item["dur"]),
        human_size(item["size"]),
    ] if x)
    badge = human_time(item["dur"]) or ("Photo" if name.lower().endswith(STILL_EXT) else "")
    stem = item["stem"]
    return f'''      <article class="media-item">
        <figure class="media-item__shot media-item__shot--{aspect}">
          <picture>
            <source type="image/webp" srcset="media/{stem}.webp">
            <img src="media/{stem}.jpg" alt="{esc(title or name)}" loading="lazy" decoding="async">
          </picture>
          {f'<span class="media-item__badge">{badge}</span>' if badge else ''}
        </figure>
        <div class="media-item__body">
          <h3>{esc(title or name)}</h3>
          <p class="media-item__meta">{meta}</p>
          {f'<p class="media-item__note">{esc(note)}</p>' if note else ''}
          <a class="media-item__dl" href="{item["url"]}" download>
            <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M12 3v11m0 0 4-4m-4 4-4-4M4 19h16"/></svg>
            Download <span>{human_size(item['size'])}</span>
          </a>
        </div>
      </article>
'''


def build_page(groups, total_bytes, total_files):
    nav, foot = chrome()
    ids = {g[0] for g in groups}
    big = total_bytes > 5e8
    notice_head = "Some of these are large" if big else "Everything here is free"
    size = (f"{total_bytes / 1e9:.2f}&nbsp;GB" if total_bytes >= 1e9
            else f"{total_bytes / 1e6:.0f}&nbsp;MB")
    notice_body = (
        f"{total_files} files, {size} in total. Every button shows its size before "
        "you commit to it." if big else
        f"{total_files} files, {size} in total. No sign-up, no attribution required — "
        "though a link back is always welcome.")
    lead = ("Artwork from LoveQuay, free to download and reuse — the Saturdays "
            "poster in five crops, and the splat with its transparency intact."
            if ids == {"splat", "posters"} else
            "The LoveQuay splat, free to download and reuse, with its transparency "
            "intact. Six formats of the same loop — take whichever one your editor wants."
            if ids == {"splat"} else
            "Everything here is free to download and reuse — the splat with its "
            "transparency intact, the long mixes, the reels, and the raw footage "
            "they came from.")
    secs = []
    for gid, heading, aspect, blurb, items in groups:
        if gid == "splat":
            rows = "".join(
                f'''          <li>
            <div>
              <strong>{esc(i["title"])}</strong>
              <span>{" · ".join(x for x in [f"{i['w']} × {i['h']}" if i["w"] else "", human_size(i["size"])] if x)}</span>
              {f'<em>{esc(i["note"])}</em>' if i["note"] else ''}
            </div>
            <a class="media-item__dl" href="{i["url"]}" download>
              <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M12 3v11m0 0 4-4m-4 4-4-4M4 19h16"/></svg>
              Download
            </a>
          </li>
''' for i in items)
            secs.append(f'''<section class="section section--tight" id="{gid}">
  <div class="container">
    <p class="eyebrow">{esc(heading)}</p>
    <div class="rule"></div>
    <div class="row g-5 align-items-start">
      <div class="col-lg-6">
        <div class="clip">
          <video autoplay muted loop playsinline preload="metadata"
                 poster="media/splat-preview.jpg"
                 aria-label="The LoveQuay splat animation, looping">
            <source src="media/splat-preview.mp4" type="video/mp4">
          </video>
        </div>
        <p class="media-note mt-3">Preview only, flattened onto navy. Every download below keeps its
          transparency.</p>
      </div>
      <div class="col-lg-6">
        <p class="lead-lg">{esc(blurb)}</p>
        <ul class="media-formats">
{rows}        </ul>
      </div>
    </div>
  </div>
</section>

''')
        else:
            cards = "".join(card(i, aspect) for i in items)
            secs.append(f'''<section class="section section--tight{' section--sand' if gid == 'reels' else ''}" id="{gid}">
  <div class="container">
    <p class="eyebrow">{esc(heading)}</p>
    <div class="rule"></div>
    <p class="lead-lg mb-5" style="max-width:62ch">{esc(blurb)}</p>
    <div class="media-grid media-grid--{aspect}">
{cards}    </div>
  </div>
</section>

''')

    return f'''<!doctype html>
<html lang="en" class="no-js">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Media — LoveQuay Swim Pier</title>
<meta name="description" content="Video, animation and stills from LoveQuay: the transparent splat in every format, two-hour mixes, vertical reels, and raw footage from Peter Street Basin. All free to download.">
<link rel="canonical" href="https://lovequay.com/media.html">

<meta property="og:type" content="website">
<meta property="og:site_name" content="LoveQuay Swim Pier">
<meta property="og:title" content="Media — LoveQuay Swim Pier">
<meta property="og:description" content="The transparent splat in every format, two-hour mixes, reels and raw footage. All free to download.">
<meta property="og:url" content="https://lovequay.com/media.html">
<meta property="og:image" content="https://lovequay.com/assets/img/og-default.jpg">
<meta name="twitter:card" content="summary_large_image">
<meta name="theme-color" content="#082A65">

<link rel="icon" href="favicon.ico" sizes="any">
<link rel="icon" href="assets/brand/favicon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="assets/brand/apple-touch-icon.png">
<link rel="manifest" href="site.webmanifest">

<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Poppins:wght@600;700;800&display=swap" rel="stylesheet">
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet" integrity="sha384-QWTKZyjpPEjISv5WaRU9OFeRpok6YctnYmDr5pNlyT2bRjXh0JMhjY6hW+ALEwIH" crossorigin="anonymous">
<link href="assets/css/style.css" rel="stylesheet">
</head>
<body>
<a class="skip-link" href="#main">Skip to content</a>

{nav}

<main id="main">

<section class="section section--tight">
  <div class="container">
    <div class="row g-5 align-items-end">
      <div class="col-lg-7">
        <p class="eyebrow">Media</p>
        <div class="rule"></div>
        <h1>Take any of it.</h1>
        <p class="lead-lg mt-4">{lead}</p>
      </div>
      <div class="col-lg-5">
        <div class="notice">
          <h3>{notice_head}</h3>
          <p>{notice_body}</p>
        </div>
      </div>
    </div>
  </div>
</section>

{''.join(secs)}</main>

{foot}

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js" integrity="sha384-YvpcrYf0tY3lHB60NNkmXc5s9fDVZLESaAA55NDzOxhy9GkcIdslK1eN7N6jIeHz" crossorigin="anonymous"></script>
<script src="assets/js/site.js"></script>
</body>
</html>
'''


def main():
    src_dir = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_SRC
    if not os.path.isdir(src_dir):
        sys.exit(f"source folder not found: {src_dir}")
    os.makedirs(OUT, exist_ok=True)

    built, total, count = [], 0, 0
    for gid, heading, aspect, blurb, entries in GROUPS:
        if gid not in ENABLED:
            continue
        items = []
        for fname, title, note in entries:
            path = os.path.join(src_dir, fname)
            if not os.path.exists(path):
                print("  missing:", fname)
                continue
            w, h, dur = probe(path)
            # Where a re-encoded copy is what we serve, size the page from that.
            served = os.path.join(ROOT, URLS[fname]) if URLS.get(fname) and not \
                URLS[fname].startswith("http") else None
            if fname.lower().endswith(STILL_EXT):
                dur = 0.0          # ffprobe reports a nominal frame time for stills
            size = os.path.getsize(served if served and os.path.exists(served)
                                   else path)
            stem = slug(fname)
            if not URLS.get(fname):
                print(f"  not hosted yet, leaving off the page: {fname}")
                continue
            ok = poster(path, stem)
            if not ok:
                print("  no poster:", fname)
            items.append(dict(file=fname, title=title or fname, note=note, stem=stem,
                              w=w, h=h, dur=dur, size=size, url=URLS[fname]))
            total += size
            count += 1
            print(f"   {fname[:52]:54s} {w}x{h} {human_time(dur):>8s} {human_size(size):>8s}")
        built.append((gid, heading, aspect, blurb, items))

    splat_src = os.path.join(src_dir, "LoveQuay-splat-transparent-1920.webm")
    if os.path.exists(splat_src) and splat_preview(splat_src):
        poster(os.path.join(OUT, "splat-preview.mp4"), "splat-preview", 960)
        print("   splat-preview.mp4")

    # Drop previews belonging to groups that are switched off, so assets/media
    # never accumulates posters for things the page no longer shows.
    keep = {"splat-preview.mp4", "splat-preview.webp", "splat-preview.jpg"}
    for gid, _, _, _, items in built:
        if gid == "splat":
            continue        # that group renders a format list, not poster cards
        for i in items:
            keep.update({i["stem"] + ".webp", i["stem"] + ".jpg"})
    for f in os.listdir(OUT):
        if f not in keep:
            os.remove(os.path.join(OUT, f))
            print("   pruned:", f)

    with open(os.path.join(ROOT, "media.html"), "w", encoding="utf-8") as f:
        f.write(build_page(built, total, count))

    local = sum(os.path.getsize(os.path.join(OUT, f)) for f in os.listdir(OUT))
    print(f"\nmedia.html written — {count} files, {total/1e9:.2f} GB hosted elsewhere, "
          f"{local/1e6:.1f} MB of previews committed here")


if __name__ == "__main__":
    main()
