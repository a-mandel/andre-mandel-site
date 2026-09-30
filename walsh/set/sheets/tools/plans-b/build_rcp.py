#!/usr/bin/env python3
"""Walsh living set, crew plans-b: A2.4 and A2.5 reflected ceiling plans, ribbon scheme.

Reads the pocket model (walsh/index.html, the model-data JSON) the same way draw/build_drawings.py does
(its plan extraction is copied here as build_drawings_ref.py; draw/ is never touched), and the 3D meshes for
heights: every ceiling height and spot on the sheets is sampled from the model's own joists, rafters and roof.

Writes walsh/set/sheets/plans-b.js (data plus the renderer in render.js) and the two SVGs in
walsh/set/sheets/assets/plans-b/ for reference.

Run:  python3 walsh/set/sheets/tools/plans-b/build_rcp.py [--probe]
"""
import json, math, re, sys
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
SET = HERE.parents[2]                     # walsh/set
ROOT = SET.parents[1]                     # repo root
MODEL = ROOT / 'walsh' / 'index.html'
OUT_JS = SET / 'sheets' / 'plans-b.js'
ASSETS = SET / 'sheets' / 'assets' / 'plans-b'
DATUM = 5990.0
INK, ACC, TIMBER, PAPER = '#1b1a18', '#c07a2c', '#c98a52', '#f6f5f1'
CALCS = json.loads((SET / 'draw' / 'calcs.json').read_text())

# ------------------------------------------------------------------ data (as build_drawings.py)
def load_data():
    for line in MODEL.read_text().splitlines():
        if 'id="model-data"' in line:
            return json.loads(re.sub(r'^<script[^>]*>', '', line).rsplit('</script>', 1)[0])
    raise SystemExit('model data not found')

D = load_data()
P = D['plans']
L1, L2 = P['levels']['rib']['l1'], P['levels']['rib']['l2']
ROOF = P['roof']['rib']
I = D['info']

def nums(s):
    return [float(v) for v in re.findall(r'-?\d+(?:\.\d+)?', s)]

def subpaths(d):
    out = []
    for sp in re.split(r'(?=M)', d):
        n = nums(sp)
        if len(n) >= 4:
            out.append(list(zip(n[0::2], n[1::2])))
    return out

def area(poly):
    a = 0.0
    for i in range(len(poly)):
        x1, y1 = poly[i]; x2, y2 = poly[(i + 1) % len(poly)]
        a += x1 * y2 - x2 * y1
    return a / 2

def pip(x, y, poly):
    c = False
    for i in range(len(poly)):
        x1, y1 = poly[i]; x2, y2 = poly[i - 1]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            c = not c
    return c

def f2(v):
    return f'{v:.2f}'.rstrip('0').rstrip('.')

NS = 'vector-effect="non-scaling-stroke"'

def P_(d, fill='none', stroke='none', w=0, op=1, dash=None, extra=''):
    s = f'<path d="{d}" fill="{fill}"'
    if stroke != 'none':
        s += f' stroke="{stroke}" stroke-width="{w}" {NS} stroke-linejoin="round"'
        if dash: s += f' stroke-dasharray="{dash}"'
    if op != 1: s += f' opacity="{op}"'
    return s + f' {extra}/>'

def poly_d(pts, close=True):
    return 'M' + ' L'.join(f'{f2(x)} {f2(y)}' for x, y in pts) + (' Z' if close else '')

def circle_d(cx, cy, r, n=48, wob=0.0, seed=1):
    pts = []
    for k in range(n):
        a = 2 * math.pi * k / n
        rr = r * (1 + wob * math.sin(a * 5 + seed) + wob * 0.6 * math.sin(a * 9 + seed * 2.3))
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    return poly_d(pts)

# plan registration shared with A2.1 to A2.3, so the plans stack sheet to sheet
S316 = 3 / 16
PVB = (-78.0, -23.5, 119.2, 103.0)
PSX = lambda x: 31.7 + (x - 40.4) * S316
PSY = lambda z: 2.6 + (z + 16.6) * S316
PVIEW = dict(x=round(PSX(PVB[0]), 4), y=round(PSY(PVB[1]), 4), w=round(PVB[2] * S316, 4), h=round(PVB[3] * S316, 4))

def frac(x, y):
    return [round((x - PVB[0]) / PVB[2], 5), round((y - PVB[1]) / PVB[3], 5)]

def sheet(x, z):
    return [round(PSX(x), 3), round(PSY(z), 3)]

TREE = P['site']['trees'][0]

def ftin(v):
    f = int(math.floor(v + 1e-6)); i = round((v - f) * 12)
    if i == 12: f += 1; i = 0
    return f"{f}′ {i}″"

# ------------------------------------------------------------------ heights from the 3D meshes
def tris(*arrs):
    return np.concatenate([np.array(a, dtype=float).reshape(-1, 3, 3) for a in arrs])

MESH_JOIST = tris(D['wing']['joist'], D['wing']['rafter'], D['rib']['joist'], D['rib']['timber'])
# each roof's own framing, so a sample near a glulam line never reads the next roof's joists
MESH_NORTH = tris(D['wing']['joist'], D['wing']['rafter'])      # north wing ribbon and the kitchen roof
MESH_GB = tris(D['rib']['timber'])                              # garage, entry and bridge
MESH_SOUTH = tris(D['rib']['joist'])                            # south wing: granny suite and primary suite
MESH_ROOF = tris(D['wing']['roof'], D['wing']['rear'], D['rib']['roof'])
MESH_SLAB = tris(D['extra']['slab'])

def ys_at(T, x, z):
    a, b, c = T[:, 0], T[:, 1], T[:, 2]
    v0 = c[:, [0, 2]] - a[:, [0, 2]]; v1 = b[:, [0, 2]] - a[:, [0, 2]]; v2 = np.array([x, z]) - a[:, [0, 2]]
    d00 = (v0 * v0).sum(1); d01 = (v0 * v1).sum(1); d11 = (v1 * v1).sum(1); d20 = (v2 * v0).sum(1); d21 = (v2 * v1).sum(1)
    den = d00 * d11 - d01 * d01
    ok = np.abs(den) > 1e-9
    sd = np.where(ok, den, 1)
    u = np.where(ok, (d11 * d20 - d01 * d21) / sd, -1); v = np.where(ok, (d00 * d21 - d01 * d20) / sd, -1)
    m = (u >= -1e-6) & (v >= -1e-6) & (u + v <= 1 + 1e-6)
    y = a[:, 1] + u * (c[:, 1] - a[:, 1]) + v * (b[:, 1] - a[:, 1])
    return y[m]

def joist_under(x, z, r=1.4, mesh=None):
    """underside of the nearest joist or rafter over this point (the joists are the ceiling)"""
    M = MESH_JOIST if mesh is None else mesh
    best = None
    for dx in np.arange(-r, r + 0.01, 0.35):
        for dz in np.arange(-r, r + 0.01, 0.35):
            y = ys_at(M, x + dx, z + dz)
            if len(y):
                d = dx * dx + dz * dz
                if best is None or d < best[0] - 1e-9 or (abs(d - best[0]) < 1e-9 and y.min() < best[1]):
                    best = (d, y.min())
    return None if best is None else best[1] + DATUM

def roof_top(x, z):
    y = ys_at(MESH_ROOF, x, z)
    return None if not len(y) else y.max() + DATUM

def ceiling(x, z, mesh=None):
    j = joist_under(x, z, mesh=mesh)
    if j is not None:
        return j
    r = roof_top(x, z)
    return None if r is None else r - 1.25       # joist depth under the deck, as sampled where joists are found

SLAB_UNDER = float(MESH_SLAB[:, :, 1].min()) + DATUM      # the primary floor, seen from the lower level

# ------------------------------------------------------------------ zones
def clip(poly, f):
    """clip a polygon to the half plane f(p) >= 0 (Sutherland Hodgman, one edge)"""
    out = []
    for i in range(len(poly)):
        a, b = poly[i - 1], poly[i]
        fa, fb = f(a), f(b)
        if fb >= 0:
            if fa < 0:
                t = fa / (fa - fb); out.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))
            out.append(b)
        elif fa >= 0:
            t = fa / (fa - fb); out.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))
    return out

bp = subpaths(ROOF['beam'])
def mid(p, q): return ((p[0] + q[0]) / 2, (p[1] + q[1]) / 2)
NB_A, NB_B = mid(bp[0][0], bp[0][3]), mid(bp[0][1], bp[0][2])           # north wing fold beam centerline, NE to SW
SB_A, SB_B = mid(bp[3][0], bp[3][1]), mid(bp[3][2], bp[3][3])           # south wing beam, W to E
BB_A, BB_B = mid(bp[1][0], bp[1][3]), mid(bp[1][1], bp[1][2])           # bridge beam, x = 0
GB_A, GB_B = mid(bp[2][0], bp[2][3]), mid(bp[2][1], bp[2][2])           # granny beam, lot side

def side(a, b):
    return lambda p: (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0])

S_NB = side(NB_A, NB_B)
MAIN = subpaths(L1['main'])
WING = MAIN[0]
wing_e = clip(WING, lambda p: p[0] + 20.58 + 1e-6)                    # the north wing proper, entry off
entry = clip(WING, lambda p: -20.58 - p[0] + 1e-6)
sgn = 1 if S_NB((0, -14)) > 0 else -1                                   # kitchen side is north of the beam
kitchen = clip(wing_e, lambda p: sgn * S_NB(p))
ribbon = clip(wing_e, lambda p: -sgn * S_NB(p))
bridge = MAIN[1]
GAR = subpaths(L1['gar'])[0]
LOWER = subpaths(L1['lower'])
PRIM = subpaths(L2['prim'])
DECK2 = subpaths(L2['deck'])[0]
granny = max(MAIN[2:], key=lambda p: abs(area(p)))
FOOT = subpaths(P['foot']['rib'])
OUTLINE = subpaths(ROOF['outline'])[0]
SOUTH_EAST = [(0.0, 47.3), (30.7, 36.9), (38.4, 58.9), (0.2, 71.4)]      # the south wing roof east of the bridge wall

def inside_any(x, z, polys):
    return any(pip(x, z, p) for p in polys)

def sample(poly, floor, step=1.0, inset=1.0, fn=ceiling):
    xs = [p[0] for p in poly]; zs = [p[1] for p in poly]
    vals = []
    for x in np.arange(min(xs) + inset, max(xs) - inset + 0.01, step):
        for z in np.arange(min(zs) + inset, max(zs) - inset + 0.01, step):
            if pip(x, z, poly) and all(pip(x + dx, z + dz, poly) for dx, dz in ((inset, 0), (-inset, 0), (0, inset), (0, -inset))):
                c = fn(x, z)
                if c is not None:
                    vals.append((c - floor, x, z, c))
    return vals

def rng(vals):
    lo = min(vals); hi = max(vals)
    return lo, hi

# ------------------------------------------------------------------ joists, split by level
JOISTS = subpaths(ROOF['joist'])
def jmid(s): return mid(s[0], s[-1])
J_L2 = [s for s in JOISTS if pip(*jmid(s), SOUTH_EAST)]
J_L1 = [s for s in JOISTS if not pip(*jmid(s), SOUTH_EAST)]

def jdir(s):
    (x0, z0), (x1, z1) = s[0], s[-1]
    L = math.hypot(x1 - x0, z1 - z0)
    return ((x1 - x0) / L, (z1 - z0) / L), L

def bays(group, every=3, at=0.5, length=4.0, keep=None, phase=1):
    """linear fixtures in the joist bays: every nth bay, centered between two joists, a set fraction along them"""
    if len(group) < 2: return []
    (ux, uz), _ = jdir(group[0])
    nx, nz = -uz, ux
    order = sorted(group, key=lambda s: jmid(s)[0] * nx + jmid(s)[1] * nz)
    out = []
    for k in range(phase, len(order) - 1, every):
        a, b = order[k], order[k + 1]
        pa = (a[0][0] + (a[-1][0] - a[0][0]) * at, a[0][1] + (a[-1][1] - a[0][1]) * at)
        pb = (b[0][0] + (b[-1][0] - b[0][0]) * at, b[0][1] + (b[-1][1] - b[0][1]) * at)
        c = mid(pa, pb)
        (dx, dz), _ = jdir(a)
        if keep and not keep(c): continue
        out.append([round(c[0] - dx * length / 2, 2), round(c[1] - dz * length / 2, 2), round(c[0] + dx * length / 2, 2), round(c[1] + dz * length / 2, 2)])
    return out

def grid_in(poly, step, inset, off=(0, 0), angle=0.0):
    """recessed downlights on a grid, rotated to the room, kept inset from the walls"""
    ca, sa = math.cos(angle), math.sin(angle)
    xs = [p[0] for p in poly]; zs = [p[1] for p in poly]
    cx, cz = (min(xs) + max(xs)) / 2, (min(zs) + max(zs)) / 2
    R = max(max(xs) - min(xs), max(zs) - min(zs))
    pts = []
    for i in np.arange(-R, R, step):
        for j in np.arange(-R, R, step):
            u, v = i + off[0], j + off[1]
            x, z = cx + u * ca - v * sa, cz + u * sa + v * ca
            if pip(x, z, poly) and all(pip(x + dx, z + dz, poly) for dx, dz in ((inset, 0), (-inset, 0), (0, inset), (0, -inset), (inset * .7, inset * .7), (-inset * .7, -inset * .7), (inset * .7, -inset * .7), (-inset * .7, inset * .7))):
                pts.append([round(x, 2), round(z, 2)])
    return pts

# ------------------------------------------------------------------ probe
def probe():
    print('beams', NB_A, NB_B, SB_A, SB_B, BB_A, BB_B, GB_A, GB_B)
    print('joists L1', len(J_L1), 'L2', len(J_L2))
    print('slab under', SLAB_UNDER)
    for name, poly, fl in (('ribbon', ribbon, 5997.5), ('kitchen', kitchen, 5997.5), ('entry', entry, 5997.5), ('bridge', bridge, 5997.5),
                           ('granny', granny, 5997.5), ('garage', GAR, 6000.0)) + tuple(('prim%d' % i, p, 6004.0) for i, p in enumerate(PRIM)):
        v = sample(poly, fl)
        if not v: print(name, 'no samples'); continue
        lo = min(v); hi = max(v)
        print(f'{name:8s} n={len(v):4d} low {lo[0]:.2f} ft at ({lo[1]:.1f},{lo[2]:.1f}) el {lo[3]:.2f} · high {hi[0]:.2f} ft at ({hi[1]:.1f},{hi[2]:.1f}) el {hi[3]:.2f}')
    for n, (x, z) in dict(tip=(35.3, 9.6), nbeam=(17.04, -7.24), kitchen=(10.44, -13.46), nwall=(0, -13.8), gar_tip=(-62.5, 14.3), gar_beam=(-50, -13.5),
                          gear=(-70, -4), porch=(-30, 0), bbeam=(1.2, 27), btip=(16, 39), gbeam=(-10, 73.5), gtip=(-19.5, 54.5), sbeam=(11.4, 55.7),
                          sne=(29.8, 38.5), scorner=(36.8, 57.6), ssouth=(12, 67.5), deck2=(33, 48)).items():
        print(n, (x, z), 'joist', joist_under(x, z), 'roof', roof_top(x, z))


# ------------------------------------------------------------------ fixtures (concept placeholders)
def orient(s, u):
    (x0, z0), (x1, z1) = s[0], s[-1]
    return ((x0, z0), (x1, z1)) if (x1 - x0) * u[0] + (z1 - z0) * u[1] >= 0 else ((x1, z1), (x0, z0))

def near_edge(x, z, poly, m):
    return not all(pip(x + dx, z + dz, poly) for dx, dz in ((m, 0), (-m, 0), (0, m), (0, -m), (m * .7, m * .7), (-m * .7, -m * .7), (m * .7, -m * .7), (-m * .7, m * .7)))

def bay_lights(group, zone, every=3, rows=(0.5,), length=4.0, phase=1, margin=1.2, skip=None):
    """linear fixtures between joists: every nth bay, on the bay centerline, inside the zone, clear of the walls"""
    if len(group) < 2: return []
    ang = lambda s: math.atan2(jdir(s)[0][1], jdir(s)[0][0]) % math.pi
    med = sorted(ang(s) for s in group)[len(group) // 2]
    group = [s for s in group if min(abs(ang(s) - med), math.pi - abs(ang(s) - med)) < 0.17]   # one framing direction only
    if len(group) < 2: return []
    u, _ = jdir(group[0])
    if (abs(u[1]) > abs(u[0]) and u[1] < 0) or (abs(u[0]) >= abs(u[1]) and u[0] < 0): u = (-u[0], -u[1])
    nrm = (-u[1], u[0])
    order = sorted(group, key=lambda s: jmid(s)[0] * nrm[0] + jmid(s)[1] * nrm[1])
    out = []
    for k in range(phase, len(order) - 1, every):
        (a0, a1), (b0, b1) = orient(order[k], u), orient(order[k + 1], u)
        c0, c1 = mid(a0, b0), mid(a1, b1)
        ts = [t for t in np.linspace(0, 1, 121) if pip(c0[0] + (c1[0] - c0[0]) * t, c0[1] + (c1[1] - c0[1]) * t, zone)
              and not near_edge(c0[0] + (c1[0] - c0[0]) * t, c0[1] + (c1[1] - c0[1]) * t, zone, margin)]
        if len(ts) < 3: continue
        t0, t1 = ts[0], ts[-1]
        L = math.hypot(c1[0] - c0[0], c1[1] - c0[1])
        run = (t1 - t0) * L
        ln = min(length, run * 0.55)
        if ln < 1.5: continue
        for f in rows:
            t = t0 + (t1 - t0) * f
            cx, cz = c0[0] + (c1[0] - c0[0]) * t, c0[1] + (c1[1] - c0[1]) * t
            if skip and skip(cx, cz): continue
            out.append([round(cx - u[0] * ln / 2, 2), round(cz - u[1] * ln / 2, 2), round(cx + u[0] * ln / 2, 2), round(cz + u[1] * ln / 2, 2)])
    return out

def in_zone(group, zone):
    return [s for s in group if any(pip(*(s[0][0] + (s[-1][0] - s[0][0]) * t, s[0][1] + (s[-1][1] - s[0][1]) * t), zone) for t in (0.2, 0.35, 0.5, 0.65, 0.8))]

def beam_angle(a, b):
    return math.atan2(b[1] - a[1], b[0] - a[0])

def offset_line(a, b, d, t0=0.0, t1=1.0):
    L = math.hypot(b[0] - a[0], b[1] - a[1]); nx, nz = -(b[1] - a[1]) / L, (b[0] - a[0]) / L
    p = (a[0] + (b[0] - a[0]) * t0 + nx * d, a[1] + (b[1] - a[1]) * t0 + nz * d)
    q = (a[0] + (b[0] - a[0]) * t1 + nx * d, a[1] + (b[1] - a[1]) * t1 + nz * d)
    return p, q

def soffit_ok(x, z):
    return pip(x, z, OUTLINE) and not inside_any(x, z, FOOT)

def ext_lights(pts):
    ok = []
    for x, z in pts:
        if soffit_ok(x, z): ok.append([x, z])
        else: print('  dropped exterior light, not under a soffit:', (x, z))
    return ok

# ------------------------------------------------------------------ svg
def defs(pid):
    return f'''<defs>
<pattern id="{pid}-dots" width="2" height="2" patternUnits="userSpaceOnUse"><circle cx="1" cy="1" r="0.1" fill="{INK}" opacity="0.35"/></pattern>
<pattern id="{pid}-sof" width="1.2" height="1.2" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><line x1="0" y1="0" x2="0" y2="1.2" stroke="{INK}" stroke-width="0.35" opacity="0.28" {NS}/></pattern>
<pattern id="{pid}-flat" width="3" height="3" patternUnits="userSpaceOnUse"><path d="M0 1.5 H3" stroke="{INK}" stroke-width="0.3" opacity="0.22" {NS}/></pattern>
<filter id="{pid}-glow" x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur stdDeviation="0.55"/></filter>
</defs>'''

def svg_wrap(body, pid):
    x0, y0, w, h = PVB
    return (f'<svg xmlns="http://www.w3.org/2000/svg" class="dsvg" viewBox="{f2(x0)} {f2(y0)} {f2(w)} {f2(h)}" preserveAspectRatio="xMidYMid meet" '
            f'role="img" aria-hidden="true">{defs(pid)}{body}</svg>')

def beam_band(a, b, w):
    L = math.hypot(b[0] - a[0], b[1] - a[1]); nx, nz = -(b[1] - a[1]) / L * w / 2, (b[0] - a[0]) / L * w / 2
    return poly_d([(a[0] + nx, a[1] + nz), (b[0] + nx, b[1] + nz), (b[0] - nx, b[1] - nz), (a[0] - nx, a[1] - nz)])

def clerestory(a, b, d, pid):
    """the clerestory glass at a fold, seen from below: a thin band beside the beam, mullions at 4 ft"""
    p, q = offset_line(a, b, d, 0.02, 0.98)
    r, s_ = offset_line(a, b, d + 0.55 * (1 if d > 0 else -1), 0.02, 0.98)
    o = P_(poly_d([p, q, s_, r]), fill=PAPER, stroke=INK, w=0.5)
    L = math.hypot(q[0] - p[0], q[1] - p[1])
    for k in range(1, int(L // 4)):
        t = k * 4 / L
        o += P_(f'M{f2(p[0] + (q[0] - p[0]) * t)} {f2(p[1] + (q[1] - p[1]) * t)} L{f2(r[0] + (s_[0] - r[0]) * t)} {f2(r[1] + (s_[1] - r[1]) * t)}', stroke=INK, w=0.4, op=0.7)
    return o

def lights_svg(L, pid):
    o = ''
    for a, b in L.get('cove', []):
        d = f'M{f2(a[0])} {f2(a[1])} L{f2(b[0])} {f2(b[1])}'
        o += f'<path d="{d}" stroke="{ACC}" stroke-width="1.6" stroke-linecap="round" opacity="0.28" filter="url(#{pid}-glow)" fill="none"/>'
        o += P_(d, stroke=ACC, w=1.8)
        o += P_(d, stroke=PAPER, w=0.5, dash='3 5')
    for x0, z0, x1, z1 in L.get('lin', []):
        d = f'M{f2(x0)} {f2(z0)} L{f2(x1)} {f2(z1)}'
        o += P_(d, stroke=INK, w=2.7, extra='stroke-linecap="round"') + P_(d, stroke=ACC, w=1.5, extra='stroke-linecap="round"')
    for x, z in L.get('rec', []):
        o += f'<circle cx="{f2(x)}" cy="{f2(z)}" r="0.62" fill="{PAPER}" stroke="{INK}" stroke-width="0.8" {NS}/><circle cx="{f2(x)}" cy="{f2(z)}" r="0.26" fill="{ACC}"/>'
    for x, z in L.get('pend', []):
        o += (f'<circle cx="{f2(x)}" cy="{f2(z)}" r="1.1" fill="{PAPER}" stroke="{INK}" stroke-width="0.8" {NS}/>'
              + P_(f'M{f2(x - 0.78)} {f2(z - 0.78)} L{f2(x + 0.78)} {f2(z + 0.78)} M{f2(x - 0.78)} {f2(z + 0.78)} L{f2(x + 0.78)} {f2(z - 0.78)}', stroke=INK, w=0.6)
              + f'<circle cx="{f2(x)}" cy="{f2(z)}" r="0.34" fill="{ACC}"/>')
    for x, z in L.get('ext', []):
        o += (f'<circle cx="{f2(x)}" cy="{f2(z)}" r="0.62" fill="{PAPER}" stroke="{INK}" stroke-width="0.8" {NS}/>'
              + f'<path d="M{f2(x - 0.62)} {f2(z)} A0.62 0.62 0 0 0 {f2(x + 0.62)} {f2(z)} Z" fill="{ACC}"/>')
    return o

def arrow(p, q, pid):
    """ceiling rises from p to q"""
    ang = math.atan2(q[1] - p[1], q[0] - p[0]); h = 1.1
    l = (q[0] - h * math.cos(ang - 0.4), q[1] - h * math.sin(ang - 0.4)); r = (q[0] - h * math.cos(ang + 0.4), q[1] - h * math.sin(ang + 0.4))
    return P_(f'M{f2(p[0])} {f2(p[1])} L{f2(q[0])} {f2(q[1])}', stroke=INK, w=0.7, op=0.75) + P_(poly_d([q, l, r]), fill=INK, op=0.75)

def tree():
    return (P_(circle_d(TREE[0], TREE[1], 13, 60, 0.03, 2), stroke=INK, w=0.6, dash='3 2', op=0.5)
            + f'<circle cx="{TREE[0]}" cy="{TREE[1]}" r="0.55" fill="{ACC}"/>')

# ------------------------------------------------------------------ labels
def spot_mark(x, z, hot=False):
    return P_(f'M{f2(x - 1.2)} {f2(z)} H{f2(x + 1.2)} M{f2(x)} {f2(z - 1.2)} V{f2(z + 1.2)}', stroke=ACC if hot else INK, w=1.1)

def clg(x, z, floor, at=None, k='clg', pre='', mesh=None):
    """a ceiling height tag, sampled from the model at (x, z) or at a given elevation"""
    el = at if at is not None else ceiling(x, z, mesh)
    return dict(p=frac(x, z), t=pre + ftin(el - floor), s=f'{el:.1f}', k=k), el

def pct_range(poly, floor, mesh, step=1.0, inset=1.0):
    v = sample(poly, floor, step, inset, lambda x, z: ceiling(x, z, mesh))
    return min(v), max(v)

def about(lo, hi):
    return f'about {ftin(lo)} to {ftin(hi)}'

# ------------------------------------------------------------------ A2.4 level 1
def level1():
    pid = 'a24'
    b = P_(L1['cons'], stroke=INK, w=0.45, op=0.28)
    # soffits beyond the walls: the roof outline, hatched where it overhangs, dashed at the eave
    b += P_(ROOF['outline'], fill=f'url(#{pid}-sof)') + P_(P['foot']['rib'], fill=PAPER)
    b += P_(ROOF['outline'], stroke=INK, w=0.7, dash='5 3', op=0.6)
    b += tree()
    # ceiling zones
    b += P_(poly_d(kitchen), fill=f'url(#{pid}-flat)') + P_(poly_d(kitchen), fill='rgba(27,26,24,.025)')
    for p in LOWER: b += P_(poly_d(p), fill=f'url(#{pid}-flat)') + P_(poly_d(p), fill='rgba(27,26,24,.035)')
    gear = [(-75.78, -15.06), (-63.58, -15.06), (-63.58, 7.27), (-75.78, 7.27)]
    b += P_(poly_d(gear), fill=f'url(#{pid}-flat)')
    # joists, the ceiling (not over the lower level, which sees the primary floor)
    jd = ' '.join(poly_d(s, False) for s in J_L1)
    b += P_(jd, stroke=TIMBER, w=0.75)
    # glulams at the glass lines, beams, posts, clerestory
    b += P_(ROOF['glulam'], fill=TIMBER, stroke='#8a4f1e', w=0.5, extra='fill-opacity="0.45"')
    b += clerestory(NB_A, NB_B, -0.75 * sgn, pid)
    for a_, b_, w in ((NB_A, NB_B, 0.95), (BB_A, BB_B, 0.9), (GB_A, GB_B, 0.9)):
        b += P_(beam_band(a_, b_, w), fill='#d9d6cf', stroke=INK, w=0.9)
    for x0, z0, x1, z1 in COLS_L1:
        b += P_(poly_d([(x0, z0), (x1, z0), (x1, z1), (x0, z1)]), fill=INK)
    # walls and glass at the cut
    b += P_(L1['wall'], fill=INK, stroke=INK, w=0.35, op=0.88)
    b += P_(L1['glass'], fill=PAPER, stroke=INK, w=0.55)
    # rise arrows
    for p, q in ARROWS_L1: b += arrow(p, q, pid)
    b += lights_svg(LIGHTS_L1, pid)
    spots = [((17.04, -7.24), False), ((36.94, 10.72), True), ((4.0, -14.56), False), ((0.0, 20.0), False), ((17.02, 39.56), False), ((-63.58, 15.27), False), ((-10.8, 74.3), False)]
    for (x, z), hot in spots: b += spot_mark(x, z, hot)
    return svg_wrap(b, pid)

def level2():
    pid = 'a25'
    b = P_(L2['cons'], stroke=INK, w=0.45, op=0.28)
    b += P_(L2['below'], fill='rgba(27,26,24,.02)', stroke=INK, w=0.6, dash='4 3', op=0.45)
    b += P_(ROOF['outline'], stroke=INK, w=0.5, dash='1.5 3', op=0.35)
    for t in P['terrace']:
        b += P_(t['d'], stroke=INK, w=0.5, dash='4 3', op=0.3)
    b += tree()
    # the south wing roof over the primary suite and its terrace: soffit beyond the walls
    b += P_(poly_d(SE_ROOF), fill=f'url(#{pid}-sof)') + P_(L2['prim'], fill=PAPER)
    b += P_(poly_d(SE_ROOF), stroke=INK, w=0.7, dash='5 3', op=0.6)
    b += P_(' '.join(poly_d(s, False) for s in J_L2), stroke=TIMBER, w=0.75)
    b += P_(GLULAM_SE, fill=TIMBER, stroke='#8a4f1e', w=0.5, extra='fill-opacity="0.45"')
    b += clerestory(SB_A, SB_B, CLR_S, pid)
    b += P_(beam_band(SB_A, SB_B, 0.95), fill='#d9d6cf', stroke=INK, w=0.9)
    for x0, z0, x1, z1 in COLS_L2:
        b += P_(poly_d([(x0, z0), (x1, z0), (x1, z1), (x0, z1)]), fill=INK)
    b += P_(L2['wall'], fill=INK, stroke=INK, w=0.35, op=0.88)
    b += P_(L2['glass'], fill=PAPER, stroke=INK, w=0.55)
    for p, q in ARROWS_L2: b += arrow(p, q, pid)
    b += lights_svg(LIGHTS_L2, pid)
    for (x, z), hot in (((8.2, 56.2), False), ((30.76, 33.96), False), ((12.0, 66.6), False)):
        b += spot_mark(x, z, hot)
    return svg_wrap(b, pid)

# posts, from the model's column meshes (plan boxes)
def col_boxes(arr):
    t = np.array(arr, dtype=float).reshape(-1, 3)[:, [0, 2]]
    cl = []
    for x, z in t:
        for c in cl:
            if abs(c[0] - x) < 1.5 and abs(c[1] - z) < 1.5:
                c[2].append((x, z)); break
        else:
            cl.append([x, z, [(x, z)]])
    out = []
    for _, _, pts in cl:
        a = np.array(pts); out.append([round(float(v), 2) for v in (*a.min(0), *a.max(0))])
    return out

COLS = col_boxes(D['wing']['col']) + col_boxes(D['rib']['col'])
COLS_L2 = [c for c in COLS if pip((c[0] + c[2]) / 2, (c[1] + c[3]) / 2, SOUTH_EAST)]
COLS_L1 = [c for c in COLS if c not in COLS_L2]

# the south wing roof (east of the bridge wall): the part of the roof outline inside SOUTH_EAST
SE_ROOF = clip(clip(OUTLINE, lambda p: p[0] - 0.02), lambda p: (p[1] - 47.3) * 30.7 - (p[0]) * (36.9 - 47.3))   # south of the court glulam line
GL_SUB = subpaths(ROOF['glulam'])
GLULAM_SE = ' '.join(poly_d(clip(clip(g, lambda p: p[0] - 0.02), lambda p: (p[1] - 46.6) * 30.7 - (p[0]) * (36.2 - 46.6))) for g in GL_SUB if len(clip(clip(g, lambda p: p[0] - 0.02), lambda p: (p[1] - 46.6) * 30.7 - (p[0]) * (36.2 - 46.6))) > 2)
S_SB = side(SB_A, SB_B)
NORTH_D = 1 if S_SB((20, 45)) > 0 else -1             # offset sign toward the primary suite's high (north) side
CLR_S = -0.75 * NORTH_D                               # clerestory band drawn on the low side, the cove on the high side

# ------------------------------------------------------------------ lighting layout, level 1
def build_lights():
    g_north = in_zone(J_L1, wing_e)
    g_bridge = in_zone(J_L1, bridge)
    g_granny = in_zone(J_L1, granny)
    g_entry = in_zone(J_L1, entry)
    g_garage = [s for s in in_zone(J_L1, GAR) if s not in g_entry]
    dining = lambda x, z: 22.0 < z < 33.5
    L1L = dict(
        cove=[offset_line(NB_A, NB_B, 0.95 * -sgn, 0.05, 0.95)],
        lin=bay_lights(g_north, ribbon, every=3, rows=(0.25, 0.72), length=3.0, phase=1, margin=1.4)
            + bay_lights(g_bridge, bridge, every=3, rows=(0.5,), length=4.0, phase=1, margin=1.4, skip=dining)
            + bay_lights(g_granny, granny, every=3, rows=(0.4,), length=4.0, phase=1, margin=1.4)
            + bay_lights(g_entry, entry, every=3, rows=(0.3,), length=3.0, phase=1, margin=1.2)
            + bay_lights(g_garage, [(-63.58, -14.56), (-39.0, -14.56), (-39.0, 15.27), (-63.58, 15.27)], every=4, rows=(0.3, 0.72), length=4.0, phase=2, margin=1.5),
        rec=grid_in(kitchen, 6.0, 2.4, off=(1.0, 0.5), angle=beam_angle(NB_B, NB_A))
            + sum((grid_in(p, 6.5, 2.2, angle=beam_angle(SB_A, SB_B)) for p in LOWER if abs(area(p)) > 50), [])
            + [[-69.7, -10.6], [-69.7, 0.9]],
        pend=[[8.0, 27.8]],
        ext=ext_lights([[-35.5, 4.6], [-29.5, 4.6], [-23.5, 4.6],            # porch soffit
                        [-57.0, 16.4], [-45.0, 16.4],                          # over the two garage doors
                        [-13.0, 9.6], [-4.0, 9.6], [22.0, 9.6], [31.0, 9.6], # court eave of the north wing
                        [-1.1, 19.0], [-1.1, 31.0],                            # bridge, west to the tree
                        [36.9, -6.0]]),                                        # east end, the living room tip side
    )
    return L1L

def build_lights2():
    prim = PRIM[0]
    ns = (lambda p: S_SB(p)) if S_SB((20, 45)) > 0 else (lambda p: -S_SB(p))
    pn, ps = clip(prim, ns), clip(prim, lambda p: -ns(p))
    g = in_zone(J_L2, prim)
    return dict(
        cove=[offset_line(SB_A, SB_B, 0.95 * NORTH_D, 0.05, 0.66)],
        lin=bay_lights(g, pn, every=3, rows=(0.5,), length=4.0, phase=1, margin=1.3)
            + bay_lights(g, ps, every=3, rows=(0.5,), length=3.0, phase=2, margin=1.0),
        ext=ext_lights([[31.5, 44.0], [33.8, 51.0], [35.6, 56.5]]),
    )

def perp_arrow(a, b, t, off, ln, toward):
    """an arrow square to a beam, starting off the beam at fraction t, running ln ft toward a point"""
    L = math.hypot(b[0] - a[0], b[1] - a[1]); nx, nz = -(b[1] - a[1]) / L, (b[0] - a[0]) / L
    px, pz = a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t
    if (toward[0] - px) * nx + (toward[1] - pz) * nz < 0: nx, nz = -nx, -nz
    return ((round(px + nx * off, 2), round(pz + nz * off, 2)), (round(px + nx * (off + ln), 2), round(pz + nz * (off + ln), 2)))

ARROWS_L1 = [perp_arrow(NB_A, NB_B, 0.52, 2.2, 6.5, (36.9, 10.7)), ((2.4, 14.0), (10.4, 14.0)),
             perp_arrow(GB_A, GB_B, 0.62, 2.4, 7.0, (-10, 50)), ((-51.5, -11.2), (-51.5, -2.2))]
ARROWS_L2 = [perp_arrow(SB_A, SB_B, 0.42, 2.2, 7.0, (20, 40)), perp_arrow(SB_A, SB_B, 0.32, 8.8, -6.0, (10, 70))]

# ------------------------------------------------------------------ build
MESH_WALL = tris(D['rib']['wall'], D['wing']['wall'])

def wall_top(x, z, r=0.6):
    best = None
    for dx in np.arange(-r, r + 0.01, 0.2):
        for dz in np.arange(-r, r + 0.01, 0.2):
            y = ys_at(MESH_WALL, x + dx, z + dz)
            if len(y) and (best is None or y.max() > best): best = y.max()
    return None if best is None else best + DATUM

def half(poly, f):
    return clip(poly, f)

def build():
    global LIGHTS_L1, LIGHTS_L2
    ASSETS.mkdir(parents=True, exist_ok=True)
    LIGHTS_L1 = build_lights(); LIGHTS_L2 = build_lights2()
    svg1, svg2 = level1(), level2()
    (ASSETS / 'A2.4.svg').write_text(svg1)
    (ASSETS / 'A2.5.svg').write_text(svg2)
    MAIN_FF, GAR_FF, LOW_FF, PRIM_FF = 5997.5, 6000.0, 5992.5, 6004.0
    gar = [(-63.58, -14.56), (-39.0, -14.56), (-39.0, 15.27), (-63.58, 15.27)]
    gear_el = roof_top(-70, -4) - 1.25
    prim = PRIM[0]
    north_side = (lambda p: S_SB(p)) if S_SB((20, 45)) > 0 else (lambda p: -S_SB(p))
    prim_n = half(prim, north_side); prim_s = half(prim, lambda p: -north_side(p))
    MN, MG, MS = MESH_NORTH, MESH_GB, MESH_SOUTH
    R = dict(rib=pct_range(ribbon, MAIN_FF, MN), kit=pct_range(kitchen, MAIN_FF, MN), ent=pct_range(entry, MAIN_FF, MG),
             bri=pct_range(bridge, MAIN_FF, MG), gra=pct_range(granny, MAIN_FF, MS), gar=pct_range(gar, GAR_FF, MG),
             pn=pct_range(prim_n, PRIM_FF, MS), ps=pct_range(prim_s, PRIM_FF, MS))
    low_prim = R['ps'][0]
    plate_n = 6006.5                     # main level plates: the glass heads and the lower beam soffit sit at 6006.5 in the model
    plate_s = wall_top(12.0, 67.0)
    soffit2 = ceiling(33.0, 48.0, MS) - PRIM_FF
    for k, (lo, hi) in R.items(): print(f'  {k:4s} {ftin(lo[0])} at ({lo[1]:.1f},{lo[2]:.1f}) to {ftin(hi[0])} at ({hi[1]:.1f},{hi[2]:.1f})')
    print('  gear', ftin(gear_el - GAR_FF), ' lower', ftin(SLAB_UNDER - LOW_FF), ' plates', plate_n, plate_s, ' terrace soffit', ftin(soffit2))
    tip_over = CALCS['heights']['tip_over_grade']
    rg = lambda k: about(R[k][0][0], R[k][1][0])

    def C(x, z, fl, mesh, **kw):
        return clg(x, z, fl, mesh=mesh, **kw)[0]

    lab1 = [
        dict(p=frac(15.5, 3.2), t='Ribbon ceiling', s='the joists are the ceiling', k='tag'),
        dict(p=frac(-4.0, -9.6), t='Flat zone · kitchen roof', s='rafters at 1/4 in per ft', k='tag'),
        dict(p=frac(-51.3, 4.5), t='Garage · 6000.0', s='joists exposed', k='tag'),
        dict(p=frac(-69.7, -4.0), t='Gear bay', s='flat', k='room'),
        dict(p=frac(-29.8, -8.9), t='Entry', k='room'),
        dict(p=frac(-29.8, 0.6), t='Porch', s='soffit, exterior', k='room'),
        dict(p=frac(8.0, 38.4), t='Bridge', s='joists square to the west beam', k='room'),
        dict(p=frac(8.0, 25.2), t='Pendant', s='dining, placeholder', k='lite'),
        dict(p=frac(-10.4, 59.2), t='Granny suite', s='its own sheet', k='room'),
        dict(p=frac(13.2, 58.4), t='Lower level · 5992.5', s='flat, the primary floor over', k='tag'),
        # ceiling heights, sampled from each roof's own framing
        C(-7.0, 3.4, MAIN_FF, MN), C(31.0, 5.4, MAIN_FF, MN), C(13.0, -12.0, MAIN_FF, MN), C(-30.0, -7.1, MAIN_FF, MG),
        C(-45.0, -12.0, GAR_FF, MG), C(-58.5, 11.6, GAR_FF, MG), dict(p=frac(-69.7, 4.6), t=ftin(gear_el - GAR_FF), s=f'{gear_el:.1f}', k='clg'),
        C(12.6, 36.0, MAIN_FF, MG), C(12.8, 17.0, MAIN_FF, MG), C(-6.0, 69.0, MAIN_FF, MS), C(-17.0, 56.5, MAIN_FF, MS),
        dict(p=frac(23.6, 52.4), t=ftin(SLAB_UNDER - LOW_FF), s=f'{SLAB_UNDER:.1f}', k='clg'),
        # spots, matching A2.3 and A3.0
        dict(p=frac(17.04, -7.24), t='Beam 6012.0', s='clerestory 6008.0 to 6010.0', k='spot'),
        dict(p=frac(36.94, 10.72), t='Tip 6023.0', s=f'roof, {tip_over:.1f} ft over grade', k='spot r', hot=True),
        dict(p=frac(4.0, -14.56), t=f'Plate {plate_n:.1f}', s=f'{plate_n - MAIN_FF:.0f} ft over the floor', k='spot'),
        dict(p=frac(0.0, 20.0), t='Beam 6009.5', s='bridge', k='spot r'),
        dict(p=frac(17.02, 39.56), t='Tip 6015.2', s='bridge', k='spot'),
        dict(p=frac(-63.58, 15.27), t='Tip 6016.5', s='garage and mud', k='spot'),
        dict(p=frac(-10.8, 74.3), t='Beam 6009.0', s='granny suite', k='spot'),
    ]
    lab2 = [
        dict(p=frac(11.5, 47.6), t='Primary suite · 6004.0', s='under the south wing fold', k='tag'),
        dict(p=frac(32.2, 52.5), t='Primary terrace', s='soffit, exterior', k='room'),
        dict(p=frac(8.0, -4.0), t='Level 1 below', s='see A2.4', k='room'),
        dict(p=frac(8.0, 26.0), t='Bridge below', s='stairs inside the bridge', k='room'),
        dict(p=frac(-10.4, 62.0), t='Granny suite below', s='see A2.4', k='room'),
        C(23.2, 42.6, PRIM_FF, MS), C(20.5, 52.8, PRIM_FF, MS), C(19.0, 61.6, PRIM_FF, MS),
        dict(p=frac(6.2, 65.9), t=ftin(low_prim[0]), s=f'lowest {low_prim[3]:.1f}', k='clg low'),
        dict(p=frac(33.0, 45.4), t=ftin(soffit2), s=f'{soffit2 + PRIM_FF:.1f}', k='clg'),
        dict(p=frac(8.2, 56.2), t='Beam 6013.0', s='clerestory 6013.0 to 6015.0', k='spot r'),
        dict(p=frac(30.76, 33.96), t='Roof 6022.9', s='the northeast corner', k='spot'),
        dict(p=frac(12.0, 66.6), t=f'Plate {plate_s:.1f}', s=f'{plate_s - PRIM_FF:.0f} ft over the floor', k='spot'),
    ]
    tab1 = dict(title='Level 1 ceilings', rows=[
        ['Ribbon, main 5997.5', rg('rib')],
        ['Flat zone, kitchen roof', rg('kit')],
        ['Entry', rg('ent')],
        ['Bridge', rg('bri')],
        ['Granny suite', rg('gra')],
        ['Lower level, flat', f'about {ftin(SLAB_UNDER - LOW_FF)}'],
        ['Garage, 6000.0', rg('gar')],
        ['Gear bay, flat', f'about {ftin(gear_el - GAR_FF)}'],
    ], foot='To the underside of the joists, sampled from the pocket model. FA accuracy, confirm with framing.')
    tab2 = dict(title='Level 2 ceilings', rows=[
        ['North of the beam', rg('pn')],
        ['South of the beam', rg('ps')],
        ['Lowest, southwest corner', f'about {ftin(low_prim[0])}'],
        ['Clerestory at the fold', '6013.0 to 6015.0'],
        ['Plate, south wall', f'{plate_s:.1f} · {ftin(plate_s - PRIM_FF)}'],
        ['Terrace soffit', f'about {ftin(soffit2)}'],
    ], foot='Primary floor 6004.0. The south edge reads under 7 ft: CRC R305.1 wants half a sloped room at 7 ft or more. Confirm.')
    legend = [
        ['cove', 'Cove at the fold', 'on the lower beam, washing up the joists'],
        ['lin', 'Linear between joists', 'every third bay, dimmable'],
        ['rec', 'Recessed downlight', 'flat zones only, IC rated, airtight'],
        ['pend', 'Pendant', 'placeholder'],
        ['ext', 'Eave downlight', 'shielded, full cutoff, warm'],
        ['joist', 'Exposed joist', '2 ft oc, square to the beam'],
        ['glulam', 'Glulam at the glass line', 'curved, sagging about 2 ft'],
        ['beam', 'Level beam', 'clerestory glass beside it'],
        ['eave', 'Eave or soffit beyond', 'dashed, hatched soffit'],
        ['clg', 'Ceiling height', 'over the floor, and elevation'],
        ['up', 'Ceiling rises', 'toward the lifted corner'],
    ]
    notes = [
        'Concept lighting. Every fixture is a placeholder for the lighting and electrical design. Confirm.',
        'The joists are the finished ceiling. Linear fixtures sit between them, fed through the bays; no cans through the roof deck.',
        'Recessed downlights only under the flat zones, IC rated and airtight. High efficacy, JA8 where required, dimmers or vacancy sensors, 2025 California Energy Code §150.0(k).',
        'Exterior: shielded full cutoff downlights, 2700K or warmer, aimed down, on a photocontrol with motion sensor or time clock. Dark sky, per the Lahontan Design Book. Confirm.',
        'Eave fixtures keep the Chapter 7A soffit whole: surface mounted or rated boxes, no open penetrations. CRC R337, Very High FHSZ.',
        'Smoke and CO alarms hardwired and interconnected, CRC R314 and R315. Locations follow the room layout.',
        'Heights from the pocket model, FA accuracy. Beams, tips and plates match A2.3 and A3.0.',
    ]
    data = dict(
        view=PVIEW,
        sheets={
            'A2.4': dict(svg=svg1, labels=lab1, vt=dict(n=1, t='Level 1 reflected ceiling plan', s='3/16 in = 1 ft', x=10.4, y=18.75),
                         north=dict(x=13.1, y=14.4, s=1.1),
                         notes=[dict(text='cove washes the fold', t=[19.0, 10.0], p=sheet(*offset_line(NB_A, NB_B, 0.95 * -sgn, 0.62, 0.62)[0]), a='r'),
                                dict(text='shielded, dark sky', t=[14.4, 11.7], p=sheet(-45.0, 16.4), a='r')],
                         blocks=[dict(kind='table', x=1.9, y=4.0, w=5.9, **tab1), dict(kind='legend', x=1.9, y=9.9, w=5.9, title='Concept lighting · confirm', rows=legend)]),
            'A2.5': dict(svg=svg2, labels=lab2, vt=dict(n=1, t='Level 2 reflected ceiling plan', s='3/16 in = 1 ft', x=10.4, y=18.75),
                         north=dict(x=18.6, y=17.9, s=1.1),
                         notes=[dict(text='a second fold, a second cove', t=[27.4, 10.4], p=sheet(*offset_line(SB_A, SB_B, 0.95 * NORTH_D, 0.3, 0.3)[0]), a='l'),
                                dict(text='headroom, check here', t=[26.7, 19.25], p=sheet(1.3, 69.3), a='l')],
                         blocks=[dict(kind='table', x=1.9, y=4.0, w=5.9, **tab2), dict(kind='legend', x=1.9, y=8.7, w=5.9, title='Concept lighting · confirm', rows=legend),
                                 dict(kind='notes', x=9.9, y=9.35, w=7.6, title='Ceiling and lighting notes', rows=notes)]),
        },
        colors=dict(ink=INK, acc=ACC, timber=TIMBER, paper=PAPER),
        tick=dict(sc=S316, ft=[0, 4, 8, 16]),
    )
    js = (HERE / 'render.js').read_text()
    body = ('/* plans-b crew: A2.4 and A2.5 reflected ceiling plans, ribbon scheme.\n'
            '   Built by sheets/tools/plans-b/build_rcp.py from the pocket model; edit the script or render.js, not this file. */\n'
            '(function () {\nconst PB = ' + json.dumps(data, ensure_ascii=False) + ';\n' + js + '\n})();\n')
    OUT_JS.write_text(body)
    print('wrote', OUT_JS, len(body) // 1024, 'KB')

if __name__ == '__main__':
    if '--probe' in sys.argv:
        probe()
    else:
        build()
