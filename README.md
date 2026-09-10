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
as geometry, at the top of the script — heart path, water transform, ladder rails
and rungs, quay bracket — so all the lockups, colourways and icons stay in exact
agreement. Text is converted to outlines via `fontTools`, so no file depends on a
font being installed.

Requires `fonttools` and [Inkscape](https://inkscape.org) (for the PNG exports).
Poppins ExtraBold is downloaded on first run. Set `INKSCAPE=/path/to/inkscape` if
it isn't at the default Windows location.

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

## Notes

- Colours are defined once, as custom properties at the top of
  `assets/css/style.css`, and mirror the constants in `tools/build_brand.py`.
- `assets/js/site.js` is progressive enhancement only — the sticky nav, scroll
  reveals, and the gallery lightbox. Nothing on the site depends on it to be
  readable.
- Motion respects `prefers-reduced-motion` throughout.
