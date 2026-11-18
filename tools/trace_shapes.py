"""Trace flat artwork into clean SVG paths, counters and all.

    python tools/trace_shapes.py <image.png> [--name NAME] [--eps 1.2]

Written for the two LoveQuay sources: the heart/hull shape, and the lettering
off the LOVE sign. Unlike trace_logo.py this follows holes as well as outlines,
so the counters in O, Q and A survive, and it keeps each letter as its own path
so they can be re-spaced later.

Prints SVG path data normalised to a 1000-unit em box.
"""
import argparse
import os
import sys
from collections import deque

import numpy as np
from PIL import Image

# --- contour following ------------------------------------------------------

NB = [(0, 1), (1, 1), (1, 0), (1, -1), (0, -1), (-1, -1), (-1, 0), (-1, 1)]


def trace(mask, start, backtrack=4):
    """Moore-neighbour boundary walk from `start`."""
    h, w = mask.shape
    contour = [start]
    cur, b = start, backtrack
    while True:
        found = False
        for k in range(8):
            i = (b + 1 + k) % 8
            dy, dx = NB[i]
            ny, nx = cur[0] + dy, cur[1] + dx
            if 0 <= ny < h and 0 <= nx < w and mask[ny, nx]:
                b = (i + 5) % 8
                cur = (ny, nx)
                found = True
                break
        if not found or (cur == start and len(contour) > 2):
            break
        contour.append(cur)
        if len(contour) > 200000:
            break
    return [(x, y) for y, x in contour]


def components(mask):
    """Each connected run of ink, as its own mask."""
    h, w = mask.shape
    seen = np.zeros_like(mask)
    out = []
    for sy in range(h):
        for sx in range(w):
            if not mask[sy, sx] or seen[sy, sx]:
                continue
            q = deque([(sy, sx)])
            seen[sy, sx] = True
            px = []
            while q:
                y, x = q.popleft()
                px.append((y, x))
                for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    ny, nx = y + dy, x + dx
                    if 0 <= ny < h and 0 <= nx < w and mask[ny, nx] and not seen[ny, nx]:
                        seen[ny, nx] = True
                        q.append((ny, nx))
            if len(px) < 60:          # specks, not letters
                continue
            m = np.zeros_like(mask)
            for y, x in px:
                m[y, x] = True
            out.append(m)
    out.sort(key=lambda m: np.nonzero(m)[1].min())     # left to right
    return out


def holes(comp):
    """Background pockets fully enclosed by this component."""
    h, w = comp.shape
    bg = ~comp
    outside = np.zeros_like(bg)
    q = deque()
    for x in range(w):
        for y in (0, h - 1):
            if bg[y, x] and not outside[y, x]:
                outside[y, x] = True
                q.append((y, x))
    for y in range(h):
        for x in (0, w - 1):
            if bg[y, x] and not outside[y, x]:
                outside[y, x] = True
                q.append((y, x))
    while q:
        y, x = q.popleft()
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ny, nx = y + dy, x + dx
            if 0 <= ny < h and 0 <= nx < w and bg[ny, nx] and not outside[ny, nx]:
                outside[ny, nx] = True
                q.append((ny, nx))
    pocket = bg & ~outside
    return [m for m in components(pocket)]


# --- simplify and smooth ----------------------------------------------------

def rdp(pts, eps):
    if len(pts) < 3:
        return pts
    a, b = np.array(pts[0], float), np.array(pts[-1], float)
    ab = b - a
    n = float(np.hypot(*ab))
    p = np.array(pts, float)
    d = (np.hypot(*(p - a).T) if n == 0
         else np.abs(ab[0] * (p - a)[:, 1] - ab[1] * (p - a)[:, 0]) / n)
    i = int(np.argmax(d))
    if d[i] > eps:
        return rdp(pts[:i + 1], eps)[:-1] + rdp(pts[i:], eps)
    return [pts[0], pts[-1]]


def smooth(pts, xf, alpha=0.5, corner_deg=72, prec=1):
    """corner_deg: turns sharper than (180 - this) collapse to a hard corner."""
    """Centripetal Catmull-Rom, handles collapsed at genuine corners."""
    P = [np.array(xf(q), float) for q in pts]
    n = len(P)
    if n < 3:
        return ""
    cos_lim = np.cos(np.radians(180 - corner_deg))
    f = f"%.{prec}f"

    def straight(i):
        a, b, c = P[(i - 1) % n], P[i], P[(i + 1) % n]
        u, v = b - a, c - b
        nu, nv = np.hypot(*u), np.hypot(*v)
        if nu == 0 or nv == 0:
            return 0.0
        cosang = float(np.dot(u, v) / (nu * nv))
        return 0.0 if cosang < cos_lim else min(1.0, max(0.0, (cosang - cos_lim) / (1 - cos_lim)))

    w = [straight(i) for i in range(n)]
    d = [f"M{f % P[0][0]},{f % P[0][1]}"]
    for i in range(n):
        p0, p1, p2, p3 = P[(i - 1) % n], P[i], P[(i + 1) % n], P[(i + 2) % n]
        d1 = max(float(np.hypot(*(p1 - p0))) ** alpha, 1e-6)
        d2 = max(float(np.hypot(*(p2 - p1))) ** alpha, 1e-6)
        d3 = max(float(np.hypot(*(p3 - p2))) ** alpha, 1e-6)
        b1 = (d1 * d1 * p2 - d2 * d2 * p0 + (2 * d1 * d1 + 3 * d1 * d2 + d2 * d2) * p1) / (3 * d1 * (d1 + d2))
        b2 = (d3 * d3 * p1 - d2 * d2 * p3 + (2 * d3 * d3 + 3 * d3 * d2 + d2 * d2) * p2) / (3 * d3 * (d3 + d2))
        seg = float(np.hypot(*(p2 - p1)))

        def clamp(anchor, handle):
            v = handle - anchor
            L = float(np.hypot(*v))
            return anchor + v * (seg / 3 / L) if L > seg / 3 else handle

        c1 = clamp(p1, p1 + (b1 - p1) * w[i])
        c2 = clamp(p2, p2 + (b2 - p2) * w[(i + 1) % n])
        d.append(f"C{f % c1[0]},{f % c1[1]} {f % c2[0]},{f % c2[1]} {f % p2[0]},{f % p2[1]}")
    return "".join(d) + "Z"


def first_ink(m):
    for y in range(m.shape[0]):
        xs = np.nonzero(m[y])[0]
        if xs.size:
            return (y, int(xs[0]))
    return None


def path_for(comp, xf, eps, corner=72):
    """Outline plus every counter, as one even-odd path."""
    parts = []
    s = first_ink(comp)
    if s:
        pts = rdp(trace(comp, s), eps)
        if pts[0] == pts[-1]:
            pts = pts[:-1]
        parts.append(smooth(pts, xf, corner_deg=corner))
    for hole in holes(comp):
        s = first_ink(hole)
        if not s:
            continue
        pts = rdp(trace(hole, s), eps)
        if pts[0] == pts[-1]:
            pts = pts[:-1]
        parts.append(smooth(pts, xf, corner_deg=corner))
    return "".join(parts)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("image")
    ap.add_argument("--name", default="SHAPE")
    ap.add_argument("--eps", type=float, default=1.2)
    ap.add_argument("--em", type=float, default=1000.0)
    ap.add_argument("--corner", type=float, default=72.0,
                    help="higher keeps right-angle corners crisp; 72 suits curves, 100 suits letterforms")
    a = ap.parse_args()

    rgb = np.asarray(Image.open(a.image).convert("RGB")).astype(int)
    ink = rgb.sum(2) < 600                      # anything clearly not white paper
    ys, xs = np.nonzero(ink)
    x0, y0, x1, y1 = xs.min(), ys.min(), xs.max(), ys.max()
    s = a.em / max(x1 - x0, y1 - y0)
    print(f"# {os.path.basename(a.image)}  ink {x1-x0+1}x{y1-y0+1}  scale {s:.5f}")

    def xf(p):
        return ((p[0] - x0) * s, (p[1] - y0) * s)

    comps = components(ink)
    print(f"# {len(comps)} component(s)\n")
    for i, c in enumerate(comps):
        cx = np.nonzero(c)[1]
        d = path_for(c, xf, a.eps, a.corner)
        print(f'{a.name}_{i} = "{d}"\n')
    print(f"# box: {(x1-x0+1)*s:.1f} x {(y1-y0+1)*s:.1f}")


if __name__ == "__main__":
    main()
