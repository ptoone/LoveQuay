"""Trace the approved LoveQuay logo raster into clean vector geometry.

    python tools/trace_logo.py <source.png>

Separates the artwork into its colour layers, follows each boundary, smooths the
result into cubic beziers, and prints SVG path data on a 512-unit grid ready to
paste into build_brand.py. Run once; the geometry then lives in build_brand.py.
"""
import sys
from collections import deque

import numpy as np
from PIL import Image

TOL = 90


# --- mask helpers ----------------------------------------------------------

def mask_for(rgb, colour, tol=TOL):
    return np.abs(rgb - np.array(colour)).sum(2) < tol


def fill_holes(m):
    """Flood the background in from the border; whatever it can't reach is a hole."""
    h, w = m.shape
    outside = np.zeros_like(m)
    q = deque()
    for x in range(w):
        for y in (0, h - 1):
            if not m[y, x] and not outside[y, x]:
                outside[y, x] = True
                q.append((y, x))
    for y in range(h):
        for x in (0, w - 1):
            if not m[y, x] and not outside[y, x]:
                outside[y, x] = True
                q.append((y, x))
    while q:
        y, x = q.popleft()
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ny, nx = y + dy, x + dx
            if 0 <= ny < h and 0 <= nx < w and not m[ny, nx] and not outside[ny, nx]:
                outside[ny, nx] = True
                q.append((ny, nx))
    return ~outside


def largest_component(m):
    h, w = m.shape
    seen = np.zeros_like(m)
    best, best_n = None, 0
    for sy in range(h):
        for sx in range(w):
            if not m[sy, sx] or seen[sy, sx]:
                continue
            q = deque([(sy, sx)])
            seen[sy, sx] = True
            comp = []
            while q:
                y, x = q.popleft()
                comp.append((y, x))
                for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    ny, nx = y + dy, x + dx
                    if 0 <= ny < h and 0 <= nx < w and m[ny, nx] and not seen[ny, nx]:
                        seen[ny, nx] = True
                        q.append((ny, nx))
            if len(comp) > best_n:
                best_n, best = len(comp), comp
    out = np.zeros_like(m)
    for y, x in best:
        out[y, x] = True
    return out


# --- boundary following ----------------------------------------------------

NEIGHBOURS = [(0, 1), (1, 1), (1, 0), (1, -1), (0, -1), (-1, -1), (-1, 0), (-1, 1)]


def trace_boundary(m):
    """Moore-neighbour boundary trace of the outer contour, clockwise."""
    h, w = m.shape
    start = None
    for y in range(h):
        xs = np.nonzero(m[y])[0]
        if xs.size:
            start = (y, int(xs[0]))
            break
    contour = [start]
    cur, b = start, 4          # entered from the west
    while True:
        found = False
        for k in range(8):
            i = (b + 1 + k) % 8
            dy, dx = NEIGHBOURS[i]
            ny, nx = cur[0] + dy, cur[1] + dx
            if 0 <= ny < h and 0 <= nx < w and m[ny, nx]:
                b = (i + 4 + 1) % 8      # back-track direction for the next step
                cur = (ny, nx)
                found = True
                break
        if not found:
            break
        if cur == start and len(contour) > 2:
            break
        contour.append(cur)
        if len(contour) > 400000:
            break
    return [(x, y) for y, x in contour]


def rdp(pts, eps):
    if len(pts) < 3:
        return pts
    a, b = np.array(pts[0]), np.array(pts[-1])
    ab = b - a
    n = np.hypot(*ab)
    p = np.array(pts)
    if n == 0:
        d = np.hypot(*(p - a).T)
    else:
        d = np.abs(ab[0] * (p - a)[:, 1] - ab[1] * (p - a)[:, 0]) / n
    i = int(np.argmax(d))
    if d[i] > eps:
        return rdp(pts[:i + 1], eps)[:-1] + rdp(pts[i:], eps)
    return [pts[0], pts[-1]]


def smooth_path(pts, alpha=0.5, corner_deg=92, prec=1):
    """Closed centripetal Catmull-Rom through the points, as cubic beziers.

    Centripetal (alpha=0.5) parameterisation is what keeps long straight runs
    next to tight curves from overshooting — uniform Catmull-Rom bulges badly on
    the uneven spacing that Douglas-Peucker leaves behind. Handles collapse to
    zero at genuine corners so they stay crisp.
    """
    n = len(pts)
    f = f"%.{prec}f"
    P = [np.array(q, float) for q in pts]
    cos_lim = np.cos(np.radians(180 - corner_deg))

    def straightness(i):
        a, b, c = P[(i - 1) % n], P[i], P[(i + 1) % n]
        u, v = b - a, c - b
        nu, nv = np.hypot(*u), np.hypot(*v)
        if nu == 0 or nv == 0:
            return 0.0
        cosang = float(np.dot(u, v) / (nu * nv))
        if cosang < cos_lim:
            return 0.0
        return min(1.0, max(0.0, (cosang - cos_lim) / (1 - cos_lim)))

    def clamp(anchor, handle, limit):
        v = handle - anchor
        L = np.hypot(*v)
        return anchor + v * (limit / L) if L > limit else handle

    w = [straightness(i) for i in range(n)]
    d = [f"M{f % pts[0][0]},{f % pts[0][1]}"]
    for i in range(n):
        p0, p1 = P[(i - 1) % n], P[i]
        p2, p3 = P[(i + 1) % n], P[(i + 2) % n]
        d1 = max(np.hypot(*(p1 - p0)) ** alpha, 1e-6)
        d2 = max(np.hypot(*(p2 - p1)) ** alpha, 1e-6)
        d3 = max(np.hypot(*(p3 - p2)) ** alpha, 1e-6)
        b1 = (d1 * d1 * p2 - d2 * d2 * p0
              + (2 * d1 * d1 + 3 * d1 * d2 + d2 * d2) * p1) / (3 * d1 * (d1 + d2))
        b2 = (d3 * d3 * p1 - d2 * d2 * p3
              + (2 * d3 * d3 + 3 * d3 * d2 + d2 * d2) * p2) / (3 * d3 * (d3 + d2))
        # Clamp each handle to a third of the span. Douglas-Peucker leaves long
        # straight runs as single segments, and an unclamped handle bows them.
        seg = np.hypot(*(p2 - p1))
        c1 = clamp(p1, p1 + (b1 - p1) * w[i], seg / 3)
        c2 = clamp(p2, p2 + (b2 - p2) * w[(i + 1) % n], seg / 3)
        d.append(f"C{f % c1[0]},{f % c1[1]} {f % c2[0]},{f % c2[1]} "
                 f"{f % p2[0]},{f % p2[1]}")
    return "".join(d) + "Z"


def layer_path(m, transform, eps):
    m = largest_component(fill_holes(m))
    pts = trace_boundary(m)
    pts = rdp(pts, eps)
    if pts[0] == pts[-1]:
        pts = pts[:-1]
    return smooth_path([transform(p) for p in pts]), m


# --- main ------------------------------------------------------------------

def bridge(mask, x_lo, x_hi, pad=6):
    """Close the ladder's notch out of a silhouette.

    The ladder is white, so in the source raster it carves a slot into the pool
    and the waterline. Re-fill each affected column from an interpolated top
    edge, taken from clean columns either side, so the traced contour is the
    heart alone and the ladder can be rebuilt as its own layer.
    """
    out = mask.copy()

    def top_of(x):
        c = np.nonzero(mask[:, x])[0]
        return int(c.min()) if c.size else None

    def bottom_of(x):
        c = np.nonzero(mask[:, x])[0]
        return int(c.max()) if c.size else None

    lo_t, hi_t = top_of(x_lo - pad), top_of(x_hi + pad)
    if lo_t is None or hi_t is None:
        return out
    span = (x_hi + pad) - (x_lo - pad)
    for x in range(x_lo - pad, x_hi + pad + 1):
        b = bottom_of(x)
        if b is None:
            continue
        f = (x - (x_lo - pad)) / span
        t = int(round(lo_t + (hi_t - lo_t) * f))
        out[:t, x] = False          # drop the rails standing proud of the edge
        out[t:b + 1, x] = True      # and close the slot they cut into it
    return out


def main():
    src = sys.argv[1]
    rgb = np.asarray(Image.open(src).convert("RGB")).astype(int)

    navy = mask_for(rgb, (8, 42, 101))
    basin = mask_for(rgb, (23, 102, 215))
    water = mask_for(rgb, (19, 179, 246))
    white = rgb.sum(2) > 700

    # Bridge the ladder slot out of both silhouettes before tracing, so each
    # traced path is a clean heart and the ladder becomes a separate layer.
    pool = bridge(fill_holes(basin | water), 668, 852)
    water_solid = bridge(fill_holes(water), 690, 852)
    ink = pool | navy
    ys, xs = np.nonzero(ink)
    x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
    print(f"ink box: x {x0}..{x1}  y {y0}..{y1}  ({x1-x0}x{y1-y0})")

    # Map the ink box onto a 512-wide grid, origin at (48, 104) to match the
    # existing build_brand.py coordinate space.
    s = 462.0 / (x1 - x0)
    def T(p):
        return (48 + (p[0] - x0) * s, 104 + (p[1] - y0) * s)
    print(f"scale {s:.5f}  -> box 462 x {(y1-y0)*s:.1f}")

    for name, m, eps in (("POOL", pool, 1.3),
                         ("WATER", water_solid, 1.3),
                         ("QUAY", fill_holes(navy), 1.0)):
        d, _ = layer_path(m, T, eps)
        print(f"\n# --- {name} ({len(d)} chars)\n{name} = \"{d}\"")

    # --- white ladder: measure the strokes directly ------------------------
    inside = fill_holes(pool)
    lad = np.zeros_like(white)
    for y in range(inside.shape[0]):
        r = np.nonzero(inside[y])[0]
        if r.size > 1:
            lad[y, r.min():r.max()] = white[y, r.min():r.max()]
    ys, xs = np.nonzero(lad)
    print(f"\n# ladder ink: x {xs.min()}..{xs.max()}  y {ys.min()}..{ys.max()}")
    row = int(np.median(ys))
    runs, st = [], None
    for x in range(rgb.shape[1]):
        if lad[row, x] and st is None:
            st = x
        elif not lad[row, x] and st is not None:
            if x - st > 4:
                runs.append((st, x))
            st = None
    print(f"# rails at row {row}: {runs}")
    for a, b in runs:
        col = np.nonzero(lad[:, (a + b) // 2])[0]
        print(f"#   rail x {a}..{b} -> centre {T(((a+b)/2, 0))[0]:.1f} "
              f"width {(b-a)*s:.1f}; y {col.min()}..{col.max()} -> "
              f"{T((0, col.min()))[1]:.1f}..{T((0, col.max()))[1]:.1f}")
    if len(runs) >= 2:
        mid = (runs[0][1] + runs[1][0]) // 2
        col = lad[:, mid]
        rr, st = [], None
        for y in range(rgb.shape[0]):
            if col[y] and st is None:
                st = y
            elif not col[y] and st is not None:
                if y - st > 4:
                    rr.append((st, y))
                st = None
        print("# rungs (y ranges between rails):",
              [(f"{T((0,a))[1]:.1f}", f"{T((0,b))[1]:.1f}") for a, b in rr])


if __name__ == "__main__":
    main()
