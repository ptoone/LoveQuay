"""Turn the camera originals into responsive web images.

    python tools/build_images.py [path-to-source-folder]

Every photo is EXIF-rotated, resized to the widths its role needs, and written as
both WebP and JPEG with metadata stripped. Animated GIFs become muted MP4 loops.
"""
import json
import os
import subprocess
import sys

from PIL import Image, ImageOps

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "assets", "img")
DEFAULT_SRC = os.path.join(os.path.dirname(ROOT), "LoveQuay swim pier")

# Widths exported per role.
WIDTHS = {
    "hero": [960, 1440, 1920, 2560],
    "wide": [640, 960, 1440, 1920],
    "card": [400, 640, 960, 1440],
}

# slug -> (source file, role, object-position, alt text)
PHOTOS = {
    "pier-length": ("20260908_191358.jpg", "hero", "50% 55%",
                    "The LoveQuay pier stretching west into Lake Ontario at dusk, "
                    "mooring bollards lining the deck"),
    "dive-westmouth": ("cap_20260908_172253_00.00.06_05.jpg", "hero", "60% 50%",
                       "A swimmer diving from the west end of the pier into open "
                       "water, the Toronto skyline behind"),
    "dive-steve": ("SteveMann_jumping_into_LakeOntario_at_Westmouth_cap_20210720_142205.jpg",
                   "wide", "50% 50%",
                   "A swimmer mid-dive off the westernmost end of LoveQuay into "
                   "Lake Ontario"),
    "dive-arc": ("cap_20260908_172053_00.00.07_01.jpg", "wide", "50% 50%",
                 "A swimmer arcing into the lake beside the pier's safety ladder"),
    "love-wall": ("20260907_194617.jpg", "wide", "50% 45%",
                  "The LOVE public art installation at the east end of the quay, "
                  "painted white concrete with tall red letters"),
    "love-wall-evening": ("20260908_171003.jpg", "card", "50% 45%",
                          "The LOVE installation seen from the roadway with the "
                          "Toronto skyline and lake beyond"),
    "love-bollard": ("20260908_191058-EDIT.jpg", "card", "50% 50%",
                     "A red and white bollard painted with the word LOVE on the "
                     "pier, CN Tower in the distance"),
    "love-bollard-summer": ("20210729_144657-EDIT.jpg", "wide", "50% 50%",
                            "A LOVE-painted planter at the pier's edge on a clear "
                            "summer afternoon"),
    "sunset-swimmers": ("20260907_192112.jpg", "hero", "50% 50%",
                        "People gathered on the quay deck watching the sun set "
                        "over the lake"),
    "sunset-water": ("20260907_190225.jpg", "wide", "50% 50%",
                     "Low sun over open water at the west end of the pier"),
    "pier-people": ("20260907_194144.jpg", "wide", "50% 45%",
                    "Neighbours walking and talking along the wide concrete deck "
                    "of the quay"),
    "pier-picnic": ("20260907_194147.jpg", "card", "50% 50%",
                    "A group sitting on the pier at golden hour with a picnic "
                    "blanket spread out"),
    "danger-sign": ("20260907_163717.jpg", "wide", "50% 40%",
                    "A City of Toronto sign reading Danger, Use at Own Risk, "
                    "Walkway Not Owned or Maintained by The City of Toronto"),
    "danger-post": ("20260907_163712.jpg", "card", "50% 50%",
                    "A Danger, Use at Own Risk sign on a post at the very edge of "
                    "the pier, open water behind it"),
    "broken-edge": ("20260907_164135.jpg", "card", "50% 60%",
                    "A broken section of the concrete deck exposing a dark void "
                    "below, next to a walker's feet"),
    "debris": ("20260907_164150.jpg", "card", "50% 55%",
               "Broken concrete and washed-up litter along the rubble edge of "
               "the quay"),
    "litter-bag": ("20260908_190618.jpg", "card", "50% 55%",
                   "A bag of collected litter and scattered rubbish gathered at "
                   "the shoreline during a cleanup"),
    "chalk-lovequay": ("20260908_175428.jpg", "wide", "50% 45%",
                       "The words LOVE Quay written in chalk on the concrete deck "
                       "beside a picnic laid out on the pier"),
    "chalk-swimpier": ("20260908_190052.jpg", "card", "45% 45%",
                       "LOVE Quay Swim Pier written in chalk on the pier deck "
                       "alongside a drawing of a ladder"),
    "shoreline": ("20260907_170846.jpg", "wide", "50% 50%",
                  "The rubble and armour-stone shoreline running alongside the "
                  "quay toward the city"),
    "warning-sign": ("20260907_194552.jpg", "card", "50% 45%",
                     "A weathered wooden warning sign about the cross-channel "
                     "ferry standing at the head of the pier"),
    "skyline-walk": ("20260908_171722.jpg", "wide", "50% 55%",
                     "Looking back along the quay toward the marina and the "
                     "downtown skyline"),
    "evening-walk": ("20260907_190251.jpg", "wide", "50% 50%",
                     "Walkers heading out along the pier as the sun drops toward "
                     "the horizon"),
    "pier-bollard": ("20210729_155341.jpg", "card", "50% 50%",
                     "A rusted mooring bollard set into the pier deck, with the "
                     "LOVE installation and a ferry in the distance"),
}

# GIF clips converted to video, which is an order of magnitude smaller.
CLIPS = {
    "dive-loop": "cap_20260908_172253_00.00.06_01-ANIMATION.gif",
    "dive-loop-wide": "LoveQuay2026sep08.gif",
}


def export(src_path, slug, role):
    im = ImageOps.exif_transpose(Image.open(src_path)).convert("RGB")
    w0, h0 = im.size
    out = []
    for w in WIDTHS[role]:
        if w > w0:
            w = w0
        h = round(h0 * w / w0)
        r = im.resize((w, h), Image.LANCZOS)
        for ext, kw in (("webp", dict(quality=80, method=6)),
                        ("jpg", dict(quality=80, progressive=True, optimize=True,
                                     subsampling=1))):
            p = os.path.join(OUT, f"{slug}-{w}.{ext}")
            r.save(p, **kw)
        out.append(w)
        if w == w0:
            break
    return sorted(set(out)), (w0, h0)


def export_clip(src_path, slug):
    """GIF -> a muted, looping MP4 plus a poster frame."""
    mp4 = os.path.join(OUT, f"{slug}.mp4")
    poster = os.path.join(OUT, f"{slug}-poster.jpg")
    subprocess.run(["ffmpeg", "-y", "-i", src_path, "-vf",
                    "scale='min(1280,iw)':-2:flags=lanczos,fps=24,format=yuv420p",
                    "-c:v", "libx264", "-crf", "26", "-preset", "slow",
                    "-movflags", "+faststart", "-an", mp4],
                   capture_output=True, check=False)
    im = Image.open(src_path)
    im.seek(0)
    im.convert("RGB").save(poster, quality=80, progressive=True)
    return [p for p in (mp4, poster) if os.path.exists(p)]


def main():
    src_dir = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_SRC
    if not os.path.isdir(src_dir):
        sys.exit(f"source folder not found: {src_dir}")
    os.makedirs(OUT, exist_ok=True)

    manifest = {}
    for slug, (fname, role, pos, alt) in PHOTOS.items():
        p = os.path.join(src_dir, fname)
        if not os.path.exists(p):
            print("  missing:", fname)
            continue
        widths, size = export(p, slug, role)
        manifest[slug] = dict(role=role, widths=widths, w=size[0], h=size[1],
                              pos=pos, alt=alt, src=fname)
        print(f"   {slug:22s} {size[0]}x{size[1]} -> {widths}")

    for slug, fname in CLIPS.items():
        p = os.path.join(src_dir, fname)
        if os.path.exists(p):
            made = export_clip(p, slug)
            print(f"   {slug:22s} -> {[os.path.basename(m) for m in made]}")

    with open(os.path.join(OUT, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=1)
    total = sum(os.path.getsize(os.path.join(OUT, f)) for f in os.listdir(OUT))
    print(f"\n{len(manifest)} photos, {total / 1e6:.1f} MB in assets/img/")


if __name__ == "__main__":
    main()
