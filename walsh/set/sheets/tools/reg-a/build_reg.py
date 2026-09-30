"""reg-a crew: measures the pocket model against the Lahontan Design Book and writes sheets/reg-a.js
   (F1.0 Regulatory report, A1.3 Design review compliance). Run from anywhere:
       python3 walsh/set/sheets/tools/reg-a/build_reg.py
   Inputs: walsh/index.html (model data), walsh/set/draw/calcs.json. Template: reg-a.src.js beside this file.
   Everything is FA grade and FA accuracy: about, confirm on survey."""
import json, math, re, collections
from pathlib import Path

HERE = Path(__file__).resolve().parent
SET = HERE.parents[2]                       # walsh/set
MODEL = SET.parent / 'index.html'
CALCS = json.loads((SET / 'draw' / 'calcs.json').read_text())
DATUM = 5990.0
INK, ACC = '#1b1a18', '#c07a2c'

for line in MODEL.read_text().splitlines():
    if 'id="model-data"' in line:
        D = json.loads(re.sub(r'^<script[^>]*>', '', line).rsplit('</script>', 1)[0]); break
P = D['plans']

# ------------------------------------------------------------------ terrain (same bilinear grid as draw/build_drawings.py)
TX0, TZ0, TS = -125.0, -44.0, 3.0
G = {}
T = D['site']['terrain']
for i in range(0, len(T), 3):
    G[(round((T[i] - TX0) / TS), round((T[i + 2] - TZ0) / TS))] = T[i + 1]
NX = max(k[0] for k in G); NZ = max(k[1] for k in G)
def ground(x, z):
    fx = min(max((x - TX0) / TS, 0), NX - 1e-6); fz = min(max((z - TZ0) / TS, 0), NZ - 1e-6)
    i, j = int(fx), int(fz); u, v = fx - i, fz - j
    g = lambda a, b: G.get((a, b), G.get((i, j)))
    return g(i, j) * (1 - u) * (1 - v) + g(i + 1, j) * u * (1 - v) + g(i, j + 1) * (1 - u) * v + g(i + 1, j + 1) * u * v

# ------------------------------------------------------------------ geometry helpers
def nums(s): return [float(v) for v in re.findall(r'-?\d+(?:\.\d+)?', s)]
def subpaths(d):
    out = []
    for sp in re.split(r'(?=M)', d):
        n = nums(sp)
        if len(n) >= 4: out.append(list(zip(n[0::2], n[1::2])))
    return out
def parea(p): return abs(sum(p[i][0] * p[(i + 1) % len(p)][1] - p[(i + 1) % len(p)][0] * p[i][1] for i in range(len(p)))) / 2
def pip(x, y, poly):
    c = False
    for i in range(len(poly)):
        x1, y1 = poly[i]; x2, y2 = poly[i - 1]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1: c = not c
    return c
def dseg(p, a, b):
    dx, dz = b[0] - a[0], b[1] - a[1]; L = dx * dx + dz * dz
    t = max(0, min(1, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dz) / L)) if L else 0
    return math.hypot(p[0] - a[0] - t * dx, p[1] - a[1] - t * dz)
def dpoly(p, poly): return min(dseg(p, poly[i], poly[(i + 1) % len(poly)]) for i in range(len(poly)))
def tris(a):
    for i in range(0, len(a) - 8, 9):
        yield (a[i], a[i + 1], a[i + 2]), (a[i + 3], a[i + 4], a[i + 5]), (a[i + 6], a[i + 7], a[i + 8])
def nrm(p, q, r):
    ux, uy, uz = q[0] - p[0], q[1] - p[1], q[2] - p[2]; vx, vy, vz = r[0] - p[0], r[1] - p[1], r[2] - p[2]
    n = (uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx); L = math.sqrt(sum(c * c for c in n)) or 1
    return tuple(c / L for c in n), L / 2
def hull(pts):
    pts = sorted(set(pts))
    cr = lambda o, a, b: (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lo, up = [], []
    for p in pts:
        while len(lo) >= 2 and cr(lo[-2], lo[-1], p) <= 0: lo.pop()
        lo.append(p)
    for p in reversed(pts):
        while len(up) >= 2 and cr(up[-2], up[-1], p) <= 0: up.pop()
        up.append(p)
    return lo[:-1] + up[:-1]
f2 = lambda v: f'{v:.2f}'.rstrip('0').rstrip('.')
poly_d = lambda pts: 'M' + ' L'.join(f'{f2(x)} {f2(y)}' for x, y in pts) + ' Z'
NS = 'vector-effect="non-scaling-stroke"'

# ------------------------------------------------------------------ 1. roof over natural grade, 1 ft cells, top surfaces only
top = {}
def raster(arr, cell=1.0):
    for t in tris(arr):
        n, a = nrm(*t)
        if a < 1e-5 or n[1] < 0.08: continue
        xs = [p[0] for p in t]; zs = [p[2] for p in t]
        (x1, _, z1), (x2, _, z2), (x3, _, z3) = t
        d = (z2 - z3) * (x1 - x3) + (x3 - x2) * (z1 - z3)
        if abs(d) < 1e-9: continue
        for gx in range(math.floor(min(xs)), math.ceil(max(xs)) + 1):
            for gz in range(math.floor(min(zs)), math.ceil(max(zs)) + 1):
                px, pz = gx + .5, gz + .5
                l1 = ((z2 - z3) * (px - x3) + (x3 - x2) * (pz - z3)) / d; l2 = ((z3 - z1) * (px - x3) + (x1 - x3) * (pz - z3)) / d
                if min(l1, l2, 1 - l1 - l2) < -1e-6: continue
                y = l1 * t[0][1] + l2 * t[1][1] + (1 - l1 - l2) * t[2][1]
                if (gx, gz) not in top or y > top[(gx, gz)][0]: top[(gx, gz)] = (y, n)
for arr in (D['rib']['roof'], D['wing']['roof'], D['rib']['deck'], D['wing']['deck']):
    raster(arr)
cells = {c: (y, y - ground(c[0] + .5, c[1] + .5), n) for c, (y, n) in top.items()}
BANDS = [(0, 20, 'b0'), (20, 25, 'b1'), (25, 28, 'b2'), (28, 30, 'b3'), (30, 99, 'b4')]
band = lambda o: next(k for lo, hi, k in BANDS if lo <= o < hi)
band_sf = collections.Counter(band(o) for _, o, _ in cells.values())
rects = []                                           # merged runs along x, per 1 ft row
for gz in sorted({c[1] for c in cells}):
    row = sorted(c[0] for c in cells if c[1] == gz)
    run = None
    for gx in row:
        k = band(cells[(gx, gz)][1])
        if run and run[2] == k and run[1] == gx: run[1] = gx + 1; continue
        if run: rects.append((run[0], gz, run[1] - run[0], run[2]))
        run = [gx, gx + 1, k]
    if run: rects.append((run[0], gz, run[1] - run[0], run[2]))
pitch = collections.Counter()
for (y, o, n) in cells.values():
    p = math.sqrt(n[0] ** 2 + n[2] ** 2) / max(n[1], 1e-6) * 12
    pitch['flat' if p <= 0.3 else 'low' if p < 2 else 'mid' if p < 3.95 else 'ok' if p <= 16.05 else 'steep'] += 1
NROOF = sum(pitch.values())

def spot(x, z, y):
    return dict(x=x, z=z, el=round(DATUM + y, 1), over=round(y - ground(x, z), 2), grade=round(DATUM + ground(x, z), 1))
A = D['A']; I = D['info']['rib']
SP = {
    'tip': spot(A['tip'][0], A['tip'][2], A['tip'][1]),
    'south': spot(A['swHigh'][0], A['swHigh'][2], A['swHigh'][1]),
    'primary': spot(A['primaryRidge'][0], A['primaryRidge'][2], A['primaryRidge'][1]),
    'garage': spot(A['garageTip'][0], A['garageTip'][2], A['garageTip'][1]),
    'bridge': spot(A['bridgeTip'][0], A['bridgeTip'][2], A['bridgeTip'][1]),
}
worst = max(cells.items(), key=lambda kv: kv[1][1])
assert abs(SP['tip']['over'] - CALCS['heights']['tip_over_grade']) < 0.05, 'tip over grade no longer matches calcs.json'

# footprint slope and average natural grade (VII.5 test one)
FOOT = subpaths(P['foot']['rib'])
edge = [(ground(x, z), x, z) for sp in FOOT for x, z in sp]
hi, lo = max(edge), min(edge)
slope = 100 * (hi[0] - lo[0]) / math.hypot(hi[1] - lo[1], hi[2] - lo[2])
avg_grade = DATUM + (hi[0] + lo[0]) / 2

# ------------------------------------------------------------------ 2. glazing by coplanar wall face (VII.15), 3 in cells so faces count once
def planes(arrs):
    groups = {}
    for arr in arrs:
        for t in tris(arr):
            n, a = nrm(*t)
            if a < 1e-4 or abs(n[1]) > 0.3: continue
            ab = round((math.degrees(math.atan2(n[2], n[0])) % 180) / 3) * 3 % 180
            nx, nz = math.cos(math.radians(ab)), math.sin(math.radians(ab))
            groups.setdefault((ab, round(t[0][0] * nx + t[0][2] * nz)), []).append(t)
    out = []
    for (ab, off), ts in groups.items():
        ux, uz = -math.sin(math.radians(ab)), math.cos(math.radians(ab)); c = 0.25; cs = set()
        for t in ts:
            Q = [(p[0] * ux + p[2] * uz, p[1]) for p in t]
            (x1, y1), (x2, y2), (x3, y3) = Q
            d = (y2 - y3) * (x1 - x3) + (x3 - x2) * (y1 - y3)
            if abs(d) < 1e-9: continue
            for gu in range(math.floor(min(q[0] for q in Q) / c), math.ceil(max(q[0] for q in Q) / c) + 1):
                for gy in range(math.floor(min(q[1] for q in Q) / c), math.ceil(max(q[1] for q in Q) / c) + 1):
                    px, py = (gu + .5) * c, (gy + .5) * c
                    l1 = ((y2 - y3) * (px - x3) + (x3 - x2) * (py - y3)) / d; l2 = ((y3 - y1) * (px - x3) + (x1 - x3) * (py - y3)) / d
                    if min(l1, l2, 1 - l1 - l2) >= -1e-6: cs.add((gu, gy))
        xs = [p[0] for t in ts for p in t]; zs = [p[2] for t in ts for p in t]
        out.append(dict(sf=round(len(cs) * c * c), ab=ab, off=off, x=[round(min(xs), 1), round(max(xs), 1)], z=[round(min(zs), 1), round(max(zs), 1)]))
    return sorted(out, key=lambda g: -g['sf'])
GL = planes([D['wing']['glass'], D['rib']['glass']])
# names by where each face sits in the plan (FA model faces, matched by angle and offset)
NAMES = {(90, 8): 'North wing, court face', (0, 26): 'Lower level, terrace face', (0, 0): 'Bridge, court side',
         (0, 16): 'Bridge, terrace face', (0, 36): 'Living room tip, end wall', (72, 45): 'South wing, court face',
         (72, 66): 'South wing, outer face'}
over140 = [dict(g, name=NAMES.get((g['ab'], g['off']), 'Wall face')) for g in GL if g['sf'] > 140]

# ------------------------------------------------------------------ 3. chimneys (VII.20 area, VII.5 height, CRC R1003.9 check)
CH = []
for k, nm in (('rib', 'South chimney'), ('ribN', 'North chimney')):
    s = D['chim'][k]['stone']; pts = [(s[i], s[i + 1], s[i + 2]) for i in range(0, len(s), 3)]
    ys = sorted({round(p[1], 2) for p in pts})
    base = hull([(p[0], p[2]) for p in pts if round(p[1], 2) == ys[0]])
    cap = max(D['chim'][k]['cap'][1::3])
    near = lambda R: max((cells[c][0] for c in cells if (pip(c[0] + .5, c[1] + .5, base) or dpoly((c[0] + .5, c[1] + .5), base) <= R)), default=None)
    cx = sum(p[0] for p in base) / len(base); cz = sum(p[1] for p in base) / len(base)
    CH.append(dict(name=nm, area=round(parea(base)), mass=round(DATUM + ys[-1], 1), cap=round(DATUM + cap, 1),
                   over=round(cap - ground(cx, cz), 1), adj=round(DATUM + near(1.5), 1), within10=round(DATUM + near(10), 1),
                   x=round(cx, 1), z=round(cz, 1)))

# ------------------------------------------------------------------ 4. site: lot, setbacks, easement, tree, drive
S = P['site']; LOTP = subpaths(S['lot']); SB = subpaths(S['setback'])[0]
# the model clips the lot at the terrain edge; the west (street) line runs (-125,-18.6) to (-113.67,124). Extend it to the
# north and south lines to close the lot for the diagram (drawn lighter where extended, confirm on survey)
w0, w1 = (-125.0, -18.6), (-113.67, 124.0)
dw = (w1[0] - w0[0], w1[1] - w0[1])
NE, SE = (65.73, -37.06), (69.02, 72.89)
nw = (w0[0] + dw[0] * (-37.06 - w0[1]) / dw[1], -37.06)
ds = (-156.32, 51.11)                                    # south line direction, from SE toward the street
den = dw[0] * ds[1] - dw[1] * ds[0]
s_ = ((SE[0] - w0[0]) * ds[1] - (SE[1] - w0[1]) * ds[0]) / den
sw = (w0[0] + s_ * dw[0], w0[1] + s_ * dw[1])
LOT = [nw, NE, SE, sw]
Lw = math.hypot(*dw); nin = (dw[1] / Lw, -dw[0] / Lw)   # inward normal of the street line
front = [round((p[0] - w0[0]) * nin[0] + (p[1] - w0[1]) * nin[1], 1) for p in (SB[0], SB[3])]
def off_line(dist):                                       # street line moved inward, clipped to the north and south lines
    a = (nw[0] + nin[0] * dist, nw[1] + nin[1] * dist)
    t = (-37.06 - a[1]) / dw[1]; a = (a[0] + t * dw[0], -37.06)
    b0 = (sw[0] + nin[0] * dist, sw[1] + nin[1] * dist)
    den2 = dw[0] * ds[1] - dw[1] * ds[0]
    ss = ((SE[0] - b0[0]) * ds[1] - (SE[1] - b0[1]) * ds[0]) / den2
    return a, (b0[0] + ss * dw[0], b0[1] + ss * dw[1])
sse_a, sse_b = off_line(30.0)
FZ0 = 2.0; FX0 = w0[0] + dw[0] * (FZ0 - w0[1]) / dw[1]
mpe_a, mpe_b = off_line(12.5)
TREE = S['trees'][0]
ROOF = subpaths(P['roof']['rib']['outline'])
roof_pts = [p for sp in ROOF for p in sp]
roof_out = [p for p in roof_pts if not pip(p[0], p[1], SB)]
tree_chim = min(math.hypot(TREE[0] - c['x'], TREE[1] - c['z']) for c in CH)
tree_house = min(dpoly((TREE[0], TREE[1]), sp) for sp in FOOT)
lot_sf = parea(LOT)
dr = D['drive']
pl = lambda k: [(dr[k][i], dr[k][i + 2]) for i in range(0, len(dr[k]), 3)]
DRIVE = pl(2) + pl(6)[1:] + pl(7)[1:] + (pl(1) + pl(5)[1:] + pl(4)[::-1][1:])[::-1]

# ------------------------------------------------------------------ SVG: zoning and setbacks (plan, feet, z down like A1.2)
VB1 = (-142.0, -46.0, 222.0, 188.0)
def svg_site():
    b = []
    b.append(f'<defs><pattern id="ra-sbh" width="2.2" height="2.2" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><line x1="0" y1="0" x2="0" y2="2.2" stroke="{INK}" stroke-width="0.35" opacity="0.32" {NS}/></pattern>'
             f'<pattern id="ra-dots" width="2.4" height="2.4" patternUnits="userSpaceOnUse"><circle cx="1.2" cy="1.2" r="0.2" fill="{INK}" opacity="0.38"/></pattern>'
             f'<pattern id="ra-rf" width="1.4" height="1.4" patternUnits="userSpaceOnUse" patternTransform="rotate(-30)"><line x1="0" y1="0" x2="0" y2="1.4" stroke="{INK}" stroke-width="0.3" opacity="0.5" {NS}/></pattern>'
             f'<clipPath id="ra-lotc"><path d="{poly_d(LOT)}"/></clipPath></defs>')
    # setback band = lot minus the buildable area (even odd)
    b.append(f'<path d="{poly_d(LOT)} {poly_d(SB)}" fill="url(#ra-sbh)" fill-rule="evenodd"/>')
    # snow storage easement along the street, dotted
    b.append(f'<g clip-path="url(#ra-lotc)"><path d="{poly_d([nw, sse_a, sse_b, sw])}" fill="url(#ra-dots)"/>'
             f'<path d="M{f2(sse_a[0])} {f2(sse_a[1])} L{f2(sse_b[0])} {f2(sse_b[1])}" fill="none" stroke="{INK}" stroke-width="0.6" stroke-dasharray="1.5 2.5" opacity=".55" {NS}/>'
             f'<path d="M{f2(mpe_a[0])} {f2(mpe_a[1])} L{f2(mpe_b[0])} {f2(mpe_b[1])}" fill="none" stroke="{INK}" stroke-width="0.5" stroke-dasharray="0.6 2" opacity=".5" {NS}/></g>')
    # drive
    b.append(f'<path d="{poly_d(DRIVE)}" fill="#f6f5f1" stroke="{INK}" stroke-width="0.6" opacity=".9" clip-path="url(#ra-lotc)" {NS}/>')
    # roof footprint, lightly hatched, over the plan footprint
    b.append(''.join(f'<path d="{poly_d(sp)}" fill="url(#ra-rf)" stroke="{INK}" stroke-width="0.9" {NS} stroke-linejoin="round"/>' for sp in ROOF))
    b.append(''.join(f'<path d="{poly_d(sp)}" fill="none" stroke="{INK}" stroke-width="0.5" opacity=".55" {NS}/>' for sp in FOOT))
    # setback line, lot line (traced part solid, extended part lighter)
    b.append(f'<path d="{poly_d(SB)}" fill="none" stroke="{INK}" stroke-width="0.8" stroke-dasharray="6 4" opacity=".75" {NS}/>')
    b.append(f'<path d="M{f2(w0[0])} {f2(w0[1])} L{f2(w1[0])} {f2(w1[1])} M{f2(NE[0])} {f2(NE[1])} L{f2(SE[0])} {f2(SE[1])} M-125 -37.06 L{f2(NE[0])} -37.06 M{f2(SE[0])} {f2(SE[1])} L-87.3 124" fill="none" stroke="{INK}" stroke-width="1.5" stroke-dasharray="18 4 3 4" {NS}/>')
    b.append(f'<path d="M{f2(nw[0])} {f2(nw[1])} L-125 -37.06 M{f2(w0[0])} {f2(w0[1])} L{f2(nw[0])} {f2(nw[1])} M{f2(w1[0])} {f2(w1[1])} L{f2(sw[0])} {f2(sw[1])} L-87.3 124" fill="none" stroke="{INK}" stroke-width="1" stroke-dasharray="18 4 3 4" opacity=".4" {NS}/>')
    # the signature tree
    tx, tz, tr = TREE
    b.append(f'<circle cx="{f2(tx)}" cy="{f2(tz)}" r="{f2(tr)}" fill="#f6f5f1" fill-opacity=".55" stroke="{INK}" stroke-width="0.7" {NS}/>'
             f'<circle cx="{f2(tx)}" cy="{f2(tz)}" r="{f2(tr * .62)}" fill="none" stroke="{INK}" stroke-width="0.4" opacity=".6" {NS}/>'
             f'<circle cx="{f2(tx)}" cy="{f2(tz)}" r="0.9" fill="{ACC}"/>')
    # dimension strings: north side, rear, south side, front (from the model's setback line)
    def dim(a, bb, lab_off=0):
        return f'<path d="M{f2(a[0])} {f2(a[1])} L{f2(bb[0])} {f2(bb[1])}" fill="none" stroke="{INK}" stroke-width="0.6" {NS}/>' + \
            ''.join(f'<path d="M{f2(p[0] - 1.6)} {f2(p[1] + 1.6)} L{f2(p[0] + 1.6)} {f2(p[1] - 1.6)}" stroke="{INK}" stroke-width="0.8" {NS}/>' for p in (a, bb))
    b.append(dim((-10, -37.06), (-10, -17.06)))                 # north side 20
    b.append(dim((42.4, 20.0), (42.4 + 24.4 * 0.99997, 20.0 - 24.4 * 0.0299)))   # rear, about 25
    sp_ = (8.0, 78.2)                                          # south side, square to the south line
    nS = (0.3108, 0.9505)
    b.append(dim(sp_, (sp_[0] + 20 * nS[0], sp_[1] + 20 * nS[1])))
    b.append(dim((FX0, FZ0), (FX0 + nin[0] * front[0], FZ0 + nin[1] * front[0])))
    return f'<svg xmlns="http://www.w3.org/2000/svg" class="dsvg" viewBox="{" ".join(f2(v) for v in VB1)}" preserveAspectRatio="xMidYMid meet" aria-hidden="true">{"".join(b)}</svg>'

# ------------------------------------------------------------------ SVG: roof height over natural grade (registers with A2.3)
PVB = (-78.0, -23.5, 119.2, 103.0)
TONE = {'b0': ('#1b1a18', .04), 'b1': ('#1b1a18', .16), 'b2': ('#1b1a18', .32), 'b3': (ACC, .72), 'b4': ('#8a2a12', .9)}
def svg_height():
    clip = ''.join(f'<path d="{poly_d(sp)}"/>' for sp in ROOF)
    body = ''.join(f'<rect x="{x}" y="{z}" width="{w}" height="1.02" fill="{TONE[k][0]}" fill-opacity="{TONE[k][1]}"/>' for x, z, w, k in rects)
    outl = ''.join(f'<path d="{poly_d(sp)}" fill="none" stroke="{INK}" stroke-width="0.9" {NS} stroke-linejoin="round"/>' for sp in ROOF)
    ring = ''.join(f'<circle cx="{f2(p["x"])}" cy="{f2(p["z"])}" r="1.1" fill="{ACC}" stroke="#f6f5f1" stroke-width="0.8" {NS}/>' for p in (SP['tip'], SP['south']))
    chim = ''.join(f'<circle cx="{f2(c["x"])}" cy="{f2(c["z"])}" r="0.8" fill="{INK}"/>' for c in CH)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" class="dsvg" viewBox="{" ".join(f2(v) for v in PVB)}" preserveAspectRatio="xMidYMid meet" aria-hidden="true">'
            f'<defs><clipPath id="ra-roofc">{clip}</clipPath></defs><g clip-path="url(#ra-roofc)" style="mix-blend-mode:multiply">{body}</g>{outl}{chim}{ring}</svg>')

def frac(vb, x, z): return [round((x - vb[0]) / vb[2], 4), round((z - vb[1]) / vb[3], 4)]

OUT = dict(
    calcs=CALCS,
    spots={k: dict(v, f=frac(PVB, v['x'], v['z'])) for k, v in SP.items()},
    worst=dict(over=round(worst[1][1], 2), el=round(DATUM + worst[1][0], 1)),
    bands={k: band_sf.get(k, 0) for _, _, k in BANDS},
    pitch={k: round(100 * v / NROOF, 1) for k, v in pitch.items()}, roof_cells=NROOF,
    slope=round(slope, 1), avg_grade=round(avg_grade, 1), ridge_limit=round(avg_grade + 30, 1),
    glass=over140, glass_max=GL[0]['sf'], glass_n=len(over140),
    chim=[dict(c, f=frac(PVB, c['x'], c['z'])) for c in CH],
    front=front, lot_model=round(lot_sf), roof_outside=len(roof_out),
    tree=dict(chim=round(tree_chim), house=round(tree_house, 1), f=frac(VB1, TREE[0] + TREE[2] + 13, TREE[1] - 3)),
    site=dict(f_sse=frac(VB1, (sse_a[0] + sse_b[0]) / 2 + 1, 88), f_road=frac(VB1, -128, 60),
              f_n=frac(VB1, -10, -27), f_e=frac(VB1, 54.6, 12), f_s=frac(VB1, 12.5, 96.5), f_f=frac(VB1, FX0 + nin[0] * 23, FZ0 + nin[1] * 23 + 4),
              f_build=frac(VB1, -45, 50), f_lot=frac(VB1, 10, -41.5)),
    svg_site=svg_site(), svg_height=svg_height(),
)
src = (HERE / 'reg-a.src.js').read_text()
js = src.replace('/*@DATA@*/null', json.dumps(OUT, ensure_ascii=False))
(SET / 'sheets' / 'reg-a.js').write_text(js)
print('wrote reg-a.js', len(js) // 1024, 'KB')
print(json.dumps({k: v for k, v in OUT.items() if not k.startswith('svg') and k != 'calcs'}, indent=1)[:3500])
