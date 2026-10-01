# lovequay.com

Static site for the **LoveQuay Swim Pier** — a 400 m quay running west out of
Toronto's Inner Harbour into clean, deep, open water.

Plain HTML + Bootstrap 5 (from a CDN), no build step required to deploy. The
`tools/` scripts exist only to regenerate the brand artwork and the responsive
image set; the committed output in `assets/` is what actually ships.

## Pages

| File | What it covers |
| --- | --- |
| `index.html` | The pier: what it is, swimming, safety summary, the LOVE installation |
| `swim.html` | Safety in full — the four essentials, known hazards, winter swimming, the ladders |
| `friends.html` | Friends of Love Quay: why the group exists, what it does, how to help |
| `gallery.html` | Photo grid with a keyboard-accessible lightbox |
| `videos.html` | YouTube films and shorts — generated, see below |
| `media.html` | Downloadable artwork — generated, see below |
| `brand.html` | The mark, lockups, colourways, clear space, palette, type, downloads |

Navigation and footer are repeated in each file. There is no templating layer —
if you change a nav link, change it in all five.

## Deploying to GitHub Pages

1. Create a repository and push the contents of this folder to its default branch.
2. **Settings → Pages → Source:** *Deploy from a branch*, branch `main`, folder `/ (root)`.
3. **Settings → Pages → Custom domain:** enter `lovequay.com`. The `CNAME` file
   here already contains that, so it will be picked up automatically.
4. At your DNS provider, point the apex domain at GitHub Pages:

   | Type | Name | Value |
   | --- | --- | --- |
   | A | `@` | `185.199.108.153` |
   | A | `@` | `185.199.109.153` |
   | A | `@` | `185.199.110.153` |
   | A | `@` | `185.199.111.153` |
   | CNAME | `www` | `<your-username>.github.io` |

5. Once DNS resolves, tick **Enforce HTTPS**.

`.nojekyll` is present so Pages serves the files as-is instead of running them
through Jekyll.

### Before it goes live

- `friends.html` has a placeholder block under **Cleanup dates and contact** —
  add a real email address, group chat link or social account.
- The footer copyright reads *© 2026 Friends of Love Quay*. Update as needed.

## Regenerating the brand artwork

```bash
python tools/build_brand.py
```

Writes every file in `assets/brand/` plus `favicon.ico`. The mark is defined once,
as geometry, at the top of the script — the pool, water and quay silhouettes plus
the ladder's rails and rungs — so all the lockups, colourways and icons stay in
exact agreement. Text is converted to outlines via `fontTools`, so no file
depends on a font being installed.

Requires `fonttools` and [Inkscape](https://inkscape.org) (for the PNG exports).
Poppins ExtraBold is downloaded on first run. Set `INKSCAPE=/path/to/inkscape` if
it isn't at the default Windows location.

### Where the mark's curves came from

`tools/logo-source.png` is the approved artwork. `tools/trace_logo.py` separated
it into colour layers, followed each boundary, and fitted smooth cubic beziers,
printing the path data that now lives at the top of `build_brand.py`:

```bash
python tools/trace_logo.py tools/logo-source.png
```

You only need this if the artwork itself changes. The ladder is *not* traced — it
is drawn as strokes, so it stays crisp and can be knocked out for the one-colour
versions. That also fixed a misregistration in the source, where the ladder's
blue backing and its white rails were offset from each other by about 25 px.

## Regenerating the photographs

```bash
python tools/build_images.py ["../LoveQuay swim pier"]
```

Reads the camera originals, applies EXIF rotation, and writes WebP + JPEG at the
widths each image's role needs, with metadata stripped. Animated GIFs become muted
MP4 loops. Edit the `PHOTOS` table in the script to add, remove or re-caption an
image — the alt text lives there too.

Requires `Pillow`, and `ffmpeg` for the video loops.

```bash
python tools/build_og.py
```

Composes `assets/img/og-default.jpg`, the 1200×630 social card. Run it after the
other two.

## The Videos page

```bash
python tools/build_youtube.py
```

Add a YouTube URL to `tools/youtube.txt`, one per line, and run that. Title,
uploader, orientation and thumbnail come from YouTube's public oEmbed endpoint —
no API key, no quota — and are baked into `videos.html`. `watch?v=`, `youtu.be/`
and `/shorts/` forms all work; shorts are detected from the oEmbed dimensions
and laid out 9:16, everything else 16:9.

Nothing is embedded up front. Five YouTube iframes would pull a megabyte of
player script and set cookies before anyone watched anything, so each video is a
cached still with a play button, and the iframe is created on click from
`youtube-nocookie.com`. Stills live in `media/yt/` and are pruned when a video
is removed from the list.

## The Media page

```bash
python tools/build_media.py
```

```powershell
.\tools\upload_media.ps1 -Setup      # once, to configure the rclone remote
.\tools\upload_media.ps1             # upload
```

`media.html` is the one generated page — it is a catalogue, so it is built from
an inventory rather than hand-written, and regenerating it keeps the listed
sizes and durations honest. Edit the `GROUPS` table in `build_media.py` to add,
remove or re-title an item.

Only the splat group is published. `ENABLED` at the top of the script decides
that — add `"mixes"`, `"reels"` or `"basin"` to bring the long mixes, the
vertical reels or the raw Peter Street Basin footage back. Rebuilding also
prunes preview files belonging to groups that are switched off, and both upload
scripts carry matching filters. Nav and footer are lifted from
`gallery.html` at build time so they cannot drift from the other pages.

**The originals are not in this repo.** Even the six splat files come to
1.27 GB and two are over GitHub's 100 MB per-file limit, so they live in a
Cloudflare R2 bucket served from `media.lovequay.com`; `R2_BASE` at the top of `build_media.py` is
the only place that URL appears. What *is* committed is one poster frame per
item plus a small looping preview of the splat — about 3.3 MB in `media/`.

`upload_media.ps1` (PowerShell, native on Windows) and `upload_media.sh` (bash)
push the originals to R2 and carry the one-time setup notes. Run
`.\tools\upload_media.ps1 -Setup` once to configure the rclone remote, then
without the flag to upload; `-WhatIf` is a dry run. Both pass `--max-depth 1`,
because the source folder has subdirectories the page does not list. They also
mark the largest files `Content-Disposition: attachment`,
because the HTML `download` attribute is ignored on cross-origin links and
without it a click would try to render an 819 MB GIF in the browser.

## Notes

- Colours are defined once, as custom properties at the top of
  `assets/css/style.css`, and mirror the constants in `tools/build_brand.py`.
- `assets/js/site.js` is progressive enhancement only — the sticky nav, scroll
  reveals, and the gallery lightbox. Nothing on the site depends on it to be
  readable.
- Motion respects `prefers-reduced-motion` throughout.
