"""Build the assets for the anthem page from the lead sheet and the demo track.

The song is not finished, so this exists to be run again: drop a newer PDF or
MP3 in the source folder, re-run, and the page picks the new files up.

    python tools/build_anthem.py                 # uses the default sources
    python tools/build_anthem.py <pdf> <mp3>
"""
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "assets", "anthem")
INKSCAPE = os.environ.get("INKSCAPE", r"C:/Program Files/Inkscape/bin/inkscape.exe")

DEFAULT_PDF = os.path.join(os.path.expanduser("~"), "Downloads",
                           "SwimWithMeAtLoveQuay_NationalAnthem_LoveQuay_Republic.pdf")
DEFAULT_MP3 = os.path.join(os.path.expanduser("~"), "Downloads",
                           "lovekey-chart-4-Electric_Piano.mp3")

SHEET = "lead-sheet"
PDF_NAME = "swim-with-me-at-lovequay-lead-sheet.pdf"
MP3_NAME = "swim-with-me-at-lovequay-electric-piano.mp3"
WIDTHS = [960, 1440, 1920]

TITLE = "Swim With Me at LoveQuay"
ARTIST = "Perry Toone, Steve Mann, Rhyzome Adkisson"


def render(pdf):
    """The lead sheet as WebP and JPEG. Inkscape rasterises the PDF; poppler is
    not installed here and this is the one PDF the site has to show inline."""
    made = []
    for w in WIDTHS:
        png = os.path.join(OUT, f"_{SHEET}-{w}.png")
        subprocess.run([INKSCAPE, "--export-type=png", f"--export-filename={png}",
                        "-w", str(w), "--export-background=white",
                        "--export-background-opacity=1", pdf],
                       capture_output=True)
        if not os.path.exists(png):
            sys.exit(f"inkscape could not rasterise {pdf}")
        from PIL import Image
        im = Image.open(png).convert("RGB")
        im.save(os.path.join(OUT, f"{SHEET}-{w}.webp"), quality=86, method=6)
        im.save(os.path.join(OUT, f"{SHEET}-{w}.jpg"), quality=86,
                progressive=True, optimize=True)
        os.remove(png)
        made.append((w, im.size))
        print(f"   {SHEET}-{w}  {im.size[0]}x{im.size[1]}")
    return made


def tag(path):
    """Label the download, so a file saved out of the page says what it is."""
    try:
        from mutagen.id3 import ID3, ID3NoHeaderError, TIT2, TPE1, TALB, TCOM
    except ImportError:
        print("   (mutagen missing — mp3 left untagged)")
        return
    try:
        t = ID3(path)
    except ID3NoHeaderError:
        t = ID3()
    t.add(TIT2(encoding=3, text=f"{TITLE} (electric piano)"))
    t.add(TPE1(encoding=3, text=ARTIST))
    t.add(TCOM(encoding=3, text=ARTIST))
    t.add(TALB(encoding=3, text="LoveQuay"))
    t.save(path)
    print("   mp3 tagged")


def main():
    pdf = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_PDF
    mp3 = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_MP3
    for p in (pdf, mp3):
        if not os.path.exists(p):
            sys.exit(f"source not found: {p}")
    os.makedirs(OUT, exist_ok=True)

    print("lead sheet")
    sizes = render(pdf)
    shutil.copy2(pdf, os.path.join(OUT, PDF_NAME))
    print(f"   {PDF_NAME}")

    print("audio")
    dest = os.path.join(OUT, MP3_NAME)
    shutil.copy2(mp3, dest)
    tag(dest)

    total = sum(os.path.getsize(os.path.join(OUT, f)) for f in os.listdir(OUT))
    w, (iw, ih) = WIDTHS[-1], sizes[-1][1]
    print(f"\n{len(os.listdir(OUT))} files, {total / 1e6:.1f} MB in assets/anthem/")
    print(f"sheet is {iw}x{ih} at its largest")


if __name__ == "__main__":
    main()
