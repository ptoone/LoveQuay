"""Build the Videos page from a list of YouTube URLs.

    python tools/build_youtube.py

Reads tools/youtube.txt — one URL per line — and asks YouTube's public oEmbed
endpoint for each video's title, uploader and thumbnail. No API key, no quota.
Thumbnails are cached locally so the page makes no third-party request until a
reader actually presses play.

Nothing is embedded up front either. Five YouTube iframes would pull well over a
megabyte of player script and set cookies before anyone had watched anything, so
each video is a still with a play button; the iframe is only created on click,
and from youtube-nocookie.com.
"""
import html
import json
import os
import re
import sys
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
LIST = os.path.join(HERE, "youtube.txt")
THUMBS = os.path.join(ROOT, "media", "yt")
PAGE = os.path.join(ROOT, "videos.html")

UA = {"User-Agent": "Mozilla/5.0 (compatible; LoveQuay site build)"}


def video_id(url):
    m = re.search(r"(?:v=|/shorts/|youtu\.be/|/embed/)([A-Za-z0-9_-]{11})", url)
    return m.group(1) if m else None


def oembed(url):
    q = "https://www.youtube.com/oembed?" + urllib.parse.urlencode(
        {"url": url, "format": "json"})
    with urllib.request.urlopen(urllib.request.Request(q, headers=UA), timeout=30) as r:
        return json.load(r)


def grab(url, dest):
    if os.path.exists(dest):
        return True
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
            data = r.read()
        if len(data) < 2000:          # YouTube serves a grey placeholder for missing sizes
            return False
        with open(dest, "wb") as f:
            f.write(data)
        return True
    except Exception:
        return False


def thumbnail(vid, is_short):
    """Best available still. Shorts have no 16:9 master, so fall back in order."""
    os.makedirs(THUMBS, exist_ok=True)
    dest = os.path.join(THUMBS, vid + ".jpg")
    order = (["oar2.jpg", "hq2.jpg", "hqdefault.jpg"] if is_short
             else ["maxresdefault.jpg", "sddefault.jpg", "hqdefault.jpg"])
    for name in order:
        if grab(f"https://i.ytimg.com/vi/{vid}/{name}", dest):
            return os.path.relpath(dest, ROOT).replace(os.sep, "/")
    return None


def read_list():
    out = []
    for line in open(LIST, encoding="utf-8"):
        line = line.strip()
        if line and not line.startswith("#"):
            out.append(line)
    return out


def chrome():
    """Nav and footer, lifted from gallery.html so every page stays identical."""
    src = open(os.path.join(ROOT, "gallery.html"), encoding="utf-8").read()
    nav = re.search(r'<nav class="lq-nav.*?</nav>', src, re.S).group(0)
    nav = nav.replace(' aria-current="page"', "")
    nav = nav.replace('<a class="nav-link" href="videos.html">',
                      '<a class="nav-link" aria-current="page" href="videos.html">')
    foot = re.search(r'<footer class="lq-footer">.*?</footer>', src, re.S).group(0)
    return nav, foot


def card(v):
    e = html.escape
    kind = "short" if v["short"] else "wide"
    thumb = (f'<img src="{v["thumb"]}" alt="" loading="lazy" decoding="async">'
             if v["thumb"] else "")
    return f'''      <li class="yt-item yt-item--{kind}">
        <button class="yt-item__play" type="button" data-yt="{v['id']}"
                aria-label="Play: {e(v['title'])}">
          <span class="yt-item__shot">
            {thumb}
            <span class="yt-item__badge" aria-hidden="true">
              <svg viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg>
            </span>
          </span>
        </button>
        <div class="yt-item__body">
          <h3><a href="https://www.youtube.com/watch?v={v['id']}" target="_blank"
                 rel="noopener noreferrer">{e(v['title'])}</a></h3>
          <p class="yt-item__by">
            <a href="{e(v['author_url'])}" target="_blank" rel="noopener noreferrer">{e(v['author'])}</a>
          </p>
        </div>
      </li>
'''


def build(videos):
    nav, foot = chrome()
    channels = sorted({v["author"] for v in videos})
    by = (" and ".join(channels) if len(channels) < 3
          else ", ".join(channels[:-1]) + " and " + channels[-1])
    wide = [v for v in videos if not v["short"]]
    shorts = [v for v in videos if v["short"]]
    n_short = len(shorts)

    # Two grids rather than one. A 16:9 still beside a 9:16 one leaves a ragged
    # hole in the row, and that only gets worse as more are added.
    def block(items, heading, cls):
        if not items:
            return ""
        return (f'    <h2 class="yt-heading">{heading}</h2>\n'
                f'    <ul class="yt-grid yt-grid--{cls}">\n'
                + "".join(card(v) for v in items) + "    </ul>\n")

    cards = (block(wide, "Films", "wide")
             + block(shorts, "Shorts", "short"))

    return f'''<!doctype html>
<html lang="en" class="no-js">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Videos — LoveQuay Swim Pier</title>
<meta name="description" content="Film from the LoveQuay swim pier — swimming, safety drills, paddleboarding and lectures at the water's edge.">
<link rel="canonical" href="https://lovequay.com/videos.html">

<meta property="og:type" content="website">
<meta property="og:site_name" content="LoveQuay Swim Pier">
<meta property="og:title" content="Videos — LoveQuay Swim Pier">
<meta property="og:description" content="Film from the pier — swimming, safety drills, paddleboarding and lectures at the water's edge.">
<meta property="og:url" content="https://lovequay.com/videos.html">
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
        <p class="eyebrow">Videos</p>
        <div class="rule"></div>
        <h1>Film from the pier.</h1>
        <p class="lead-lg mt-4">{len(videos)} clips, {n_short} of them shorts, from {by}.
          Swimming, safety drills, paddleboarding, and the occasional lecture delivered
          waist-deep in the lake.</p>
      </div>
      <div class="col-lg-5">
        <div class="notice">
          <h3>Nothing loads until you press play</h3>
          <p>These are stills, not embeds. YouTube is only contacted — and only sets a
            cookie — once you choose to watch something.</p>
        </div>
      </div>
    </div>
  </div>
</section>

<section class="section section--tight pt-0">
  <div class="container">
{cards}
  </div>
</section>

</main>

{foot}

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js" integrity="sha384-YvpcrYf0tY3lHB60NNkmXc5s9fDVZLESaAA55NDzOxhy9GkcIdslK1eN7N6jIeHz" crossorigin="anonymous"></script>
<script src="assets/js/site.js"></script>
</body>
</html>
'''


def main():
    # Titles carry emoji; a Windows console is usually cp1252 and would abort the
    # whole build on the progress line alone. Never let reporting break the work.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    urls = read_list()
    videos = []
    for u in urls:
        vid = video_id(u)
        if not vid:
            print("  cannot read a video id from:", u)
            continue
        try:
            d = oembed(u)
        except Exception as e:
            print(f"  oEmbed failed for {u}: {e}")
            continue
        short = d["height"] > d["width"]
        v = dict(id=vid, title=d["title"], author=d["author_name"],
                 author_url=d.get("author_url", ""), short=short,
                 thumb=thumbnail(vid, short))
        videos.append(v)
        print(f"   {'short' if short else 'wide ':5s} {d['author_name']:18s} {d['title'][:52]}")

    if not videos:
        sys.exit("no videos resolved — nothing written")

    with open(PAGE, "w", encoding="utf-8") as f:
        f.write(build(videos))

    # Drop cached stills for videos no longer listed.
    keep = {v["id"] + ".jpg" for v in videos}
    if os.path.isdir(THUMBS):
        for f in os.listdir(THUMBS):
            if f not in keep:
                os.remove(os.path.join(THUMBS, f))
                print("   pruned:", f)

    size = sum(os.path.getsize(os.path.join(THUMBS, f))
               for f in os.listdir(THUMBS)) if os.path.isdir(THUMBS) else 0
    print(f"\nvideos.html written — {len(videos)} videos, {size/1e3:.0f} kB of stills")


if __name__ == "__main__":
    main()
