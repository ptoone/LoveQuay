"""Convert font glyphs to SVG path data, so brand lockups carry no font dependency."""
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.recordingPen import RecordingPen
from fontTools.pens.boundsPen import BoundsPen
from fontTools.misc.transform import Transform


class Typesetter:
    def __init__(self, path):
        self.font = TTFont(path)
        self.upem = self.font["head"].unitsPerEm
        self.gs = self.font.getGlyphSet()
        self.cmap = self.font.getBestCmap()
        self.hmtx = self.font["hmtx"]
        try:
            self.kern = self.font["kern"].kernTables[0].kernTable
        except Exception:
            self.kern = {}

    def _record(self, text, tracking):
        rec = RecordingPen()
        cx = 0.0
        names = [self.cmap[ord(c)] for c in text]
        for i, gn in enumerate(names):
            r = RecordingPen()
            self.gs[gn].draw(TransformPen(r, Transform(1, 0, 0, -1, cx, 0)))
            rec.value.extend(r.value)
            cx += self.hmtx[gn][0] + tracking * self.upem
            if i + 1 < len(names):
                cx += self.kern.get((gn, names[i + 1]), 0)
        return rec, cx - tracking * self.upem

    def path(self, text, size=100, tracking=0.0, x=0.0, y=0.0):
        """SVG path data for `text` set at `size`, baseline at `y`, left edge at `x`."""
        scale = size / self.upem
        rec, adv = self._record(text, tracking)
        out = RecordingPen()
        rec.replay(TransformPen(out, Transform(scale, 0, 0, scale, x, y)))
        sp = SVGPathPen(None, ntos=lambda v: f"{v:.2f}")
        out.replay(sp)
        return sp.getCommands(), adv * scale

    def bbox(self, text, size=100, tracking=0.0):
        rec, _ = self._record(text, tracking)
        bp = BoundsPen(None)
        rec.replay(bp)
        s = size / self.upem
        x0, y0, x1, y1 = bp.bounds
        return (x0 * s, y0 * s, x1 * s, y1 * s)
