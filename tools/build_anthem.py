"""Build the assets for the anthem page from the score and the demo track.

The words were finalised on 2026-11-20; the music did not change. This still
exists to be run again: drop a newer PDF or MP3 in the source folder, re-run,
and the page picks the new files up.

    python tools/build_anthem.py                 # uses the default sources
    python tools/build_anthem.py <pdf> <mp3> [mxl]

The MusicXML is the score as data rather than as a picture. It is published so
anyone can open the song in their own notation software, it drives the
interactive score on the page, and it is read here at build time to check that
what the page claims about the music is still true.
"""
import os
import shutil
import sys
import xml.etree.ElementTree as ET
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "assets", "anthem")

DEFAULT_PDF = os.path.join(os.path.expanduser("~"), "Downloads",
                           "01 - Full score - COME SWIM WITH ME AT LOVEQUAY.pdf")
DEFAULT_MP3 = os.path.join(os.path.expanduser("~"), "Downloads",
                           "lovekey-chart-4-Electric_Piano.mp3")
DEFAULT_MXL = os.path.join(os.path.expanduser("~"), "Downloads",
                           "COME SWIM WITH ME AT LOVEQUAY - Full score - 01 Flow 1.mxl")

SHEET = "score"
PDF_NAME = "come-swim-with-me-at-lovequay-score.pdf"
MP3_NAME = "come-swim-with-me-at-lovequay-electric-piano.mp3"
MXL_NAME = "come-swim-with-me-at-lovequay-score.mxl"
WIDTHS = [960, 1440, 1920]

TITLE = "Come Swim With Me at LoveQuay"
ARTIST = "Steve Mann, Perry Toone, Rhyzome Adkisson"


def render(pdf):
    """The score as WebP and JPEG.

    PyMuPDF rasterises the PDF, not Inkscape. Inkscape 1.1 does not carry the
    engraver's SMuFL music font and silently substitutes, which turned every
    note head, clef and time signature into a box or a stray CJK glyph. MuPDF
    uses the fonts embedded in the PDF, so the page comes out as engraved.

    The trailing white space is trimmed as well. The score is four systems on a
    portrait page, so nearly half of it is empty, and an image that is half
    blank reads as a loading error."""
    import pymupdf
    from PIL import Image, ImageChops

    page = pymupdf.open(pdf)[0]
    pix = page.get_pixmap(dpi=400)          # once, large; everything else is a resize
    im = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)

    blank = Image.new("RGB", im.size, (255, 255, 255))
    mask = ImageChops.difference(im, blank).convert("L").point(
        lambda v: 255 if v > 12 else 0)     # ignore anti-aliasing against the paper
    box = mask.getbbox()
    if box:
        # Trimming to the ink bounding box is not enough on its own: the page
        # carries a credit line at the very foot, so the box still spans the
        # empty middle. Find the tallest run of blank rows and, if all that
        # survives below it is a thin footer, cut there instead. The PDF
        # download still has the whole page.
        rows = [mask.crop((0, y, im.width, y + 1)).getbbox() is None
                for y in range(box[1], box[3])]
        best = run = 0
        best_at = run_at = 0
        for y, blank in enumerate(rows + [False]):
            if blank:
                if run == 0:
                    run_at = y
                run += 1
            else:
                if run > best:
                    best, best_at = run, run_at
                run = 0
        tail = len(rows) - (best_at + best)
        if best > im.height * 0.06 and tail < im.height * 0.12:
            box = (box[0], box[1], box[2], box[1] + best_at)
            print(f"   dropped a {tail}px footer below a {best}px gap")

        m = round(im.width * 0.035)         # put a page margin back
        im = im.crop((max(0, box[0] - m), max(0, box[1] - m),
                      min(im.width, box[2] + m), min(im.height, box[3] + m)))
        print(f"   trimmed to {im.size[0]}x{im.size[1]}")

    made = []
    for w in WIDTHS:
        r = im.resize((w, round(im.height * w / im.width)), Image.LANCZOS)
        r.save(os.path.join(OUT, f"{SHEET}-{w}.webp"), quality=86, method=6)
        r.save(os.path.join(OUT, f"{SHEET}-{w}.jpg"), quality=86,
               progressive=True, optimize=True)
        made.append((w, r.size))
        print(f"   {SHEET}-{w}  {r.size[0]}x{r.size[1]}")
    return made


# Spelled in ASCII on purpose: this goes to a Windows console, which is cp1252
# and cannot print a flat sign.
FIFTHS = {-3: "Eb major", -2: "Bb major", -1: "F major", 0: "C major",
          1: "G major", 2: "D major", 3: "A major"}


def inspect(mxl):
    """Read the MusicXML and report what the music actually says.

    The page makes claims — the key, the tempo, the metre, the changes, the
    words — and claims drift from sources. This prints them from the file so a
    rebuild shows up any disagreement rather than hiding it.

    The lyrics are reassembled from their syllables, so a word that has lost a
    syllable in the notation comes out visibly misspelled instead of looking
    fine strung under the notes."""
    with zipfile.ZipFile(mxl) as z:
        name = next(n for n in z.namelist()
                    if n.endswith(".xml") and not n.startswith("META-INF"))
        root = ET.fromstring(z.read(name))

    part = root.find("part")
    measures = part.findall("measure")
    key = tempo = None
    times, repeats = [], []
    for m in measures:
        a = m.find("attributes")
        if a is not None:
            f = a.find("key/fifths")
            if f is not None:
                key = int(f.text)
            t = a.find("time")
            if t is not None:
                times.append(f"{t.find('beats').text}/{t.find('beat-type').text}")
        for pm in m.findall("direction//per-minute"):
            tempo = pm.text
        for b in m.findall("barline"):
            rp = b.find("repeat")
            if rp is not None:
                repeats.append(rp.get("direction"))

    print(f"   {len(measures)} bars, {FIFTHS.get(key, '?')}, "
          f"{' then '.join(times)}, {tempo} to the quarter")
    print(f"   repeats: {repeats.count('forward')} forward, "
          f"{repeats.count('backward')} backward"
          + ("" if repeats else " — none, so the form is written out"))

    # Reassemble each lyric line, word by word, out of its syllables.
    lines = {}
    for m in measures:
        for n in m.findall("note"):
            for ly in n.findall("lyric"):
                txt = ly.find("text")
                if txt is None or txt.text is None:
                    continue
                syl = ly.find("syllabic")
                syl = syl.text if syl is not None else "single"
                buf = lines.setdefault(ly.get("number") or "1", [])
                if syl in ("begin", "single") or not buf:
                    buf.append(txt.text)
                else:
                    buf[-1] += txt.text
    for num in sorted(lines):
        words = " ".join(lines[num])
        print(f"   verse {num}: {words}")
    return lines


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
    mxl = sys.argv[3] if len(sys.argv) > 3 else DEFAULT_MXL
    for p in (pdf, mp3, mxl):
        if not os.path.exists(p):
            sys.exit(f"source not found: {p}")
    os.makedirs(OUT, exist_ok=True)

    print("score")
    sizes = render(pdf)
    shutil.copy2(pdf, os.path.join(OUT, PDF_NAME))
    print(f"   {PDF_NAME}")

    print("musicxml")
    shutil.copy2(mxl, os.path.join(OUT, MXL_NAME))
    print(f"   {MXL_NAME}")
    inspect(mxl)

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
