#!/usr/bin/env python3
"""L1.0 Landscape concept plan for the Walsh living set (crew land-a).

Registered on the A1.2 site plan: same model geometry (read through the copied build_drawings.py, which loads the
pocket model's data and never writes), same feet to sheet mapping, 1 in = 10 ft. Writes walsh/set/sheets/land-a.js.
Run:  python3 walsh/set/sheets/tools/land-a/build_l10.py
"""
import json, math, random, sys
from pathlib import Path
sys.argv = sys.argv[:1]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import build_drawings as B                      # geometry only; build() is never called
from shapely.geometry import Polygon, LineString, Point, MultiPolygon
from shapely.ops import unary_union

INK, ACC, TIMBER, PAPER = B.INK, B.ACC, B.TIMBER, B.PAPER
OUT = HERE.parents[1] / 'land-a.js'
C = B.C
SITE, P = B.SITE, B.P
f2 = B.f2
NS = 'vector-effect="non-scaling-stroke"'

# ---------------------------------------------------------------- registration (A1.2's mapping, cropped at z 115)
S10 = 0.1
VB = (-141.0, -40.0, 214.0, 155.0)
SX = lambda x: 1.95 + (x - VB[0]) * S10          # feet to sheet inches, identical to A1.2
SY = lambda z: 3.55 + (z - VB[1]) * S10
FXs = lambda s: s - 1.25                         # sheet to field inches
FYs = lambda s: s - 0.5
frac = lambda x, z: [round((x - VB[0]) / VB[2], 5), round((z - VB[1]) / VB[3], 5)]
NORTH = B.NORTH_DEG if hasattr(B, 'NORTH_DEG') else 39.3
NV = (math.sin(math.radians(NORTH)), -math.cos(math.radians(NORTH)))   # plan vector pointing north

R = random.Random(235)

# ---------------------------------------------------------------- geometry from the model
def poly(d):
    return Polygon(B.subpaths(d)[0])

FOOT = unary_union([Polygon(p) for p in B.FOOT]).buffer(0)
ROOF = Polygon(B.subpaths(ROOF_D := B.ROOF['outline'])[0]).buffer(0)
DECK = Polygon(B.TERR['deck']); STONE = Polygon(B.TERR['stone'])
DRIVE = Polygon(B.DRIVE).buffer(0); APRON = Polygon(B.APRON)
LOT = Polygon(B.subpaths(SITE['lot'])[0])
TREES = [tuple(t) for t in SITE['trees']]
SIG = TREES[0]
SIG_R = 13.0                                     # drip line, as A1.2 draws the canopy
PIT_C, PIT_R = (30.0, 24.0), 3.0
BENCH = Polygon(B.subpaths(P['pit'])[1])

# the front easement: 30 ft in from the front (Lahontan Drive) property line (III.9), confirm on survey
F0, F1 = (-125.0, -37.06), (-87.30, 124.0)
dx, dz = F1[0] - F0[0], F1[1] - F0[1]; L = math.hypot(dx, dz)
nx, nz = dz / L, -dx / L                         # inward normal (toward the lot)
EAS = LineString([(F0[0] + 30 * nx - dx / L * 20, F0[1] + 30 * nz - dz / L * 20), (F1[0] + 30 * nx + dx / L * 20, F1[1] + 30 * nz + dz / L * 20)])
EAS_ZONE = Polygon([F0, F1, (F1[0] + 30 * nx, F1[1] + 30 * nz), (F0[0] + 30 * nx, F0[1] + 30 * nz)]).buffer(0.01)

# entry walk: apron to the stem's west face, clear of the court pine's fence
WALK_LINE = [(-39.0, 36.0), (-30.0, 40.2), (-19.0, 42.4), (-5.2, 42.6)]
TPZ = Point(SIG[0], SIG[1]).buffer(SIG_R, 96)

# ---------------------------------------------------------------- pencil helpers
def jl(p0, p1, over=(0.5, 1.4), amp=0.07, step=4.0):
    """a straightedge pencil line: tiny wander, overshooting both corners"""
    x0, z0 = p0; x1, z1 = p1
    L = math.hypot(x1 - x0, z1 - z0) or 1e-6
    ux, uz = (x1 - x0) / L, (z1 - z0) / L
    a, b = R.uniform(*over), R.uniform(*over)
    x0, z0, x1, z1 = x0 - ux * a, z0 - uz * a, x1 + ux * b, z1 + uz * b
    L2 = L + a + b; n = max(2, int(L2 / step))
    ph = R.uniform(0, 6.28); pts = []
    for k in range(n + 1):
        t = k / n; w = amp * math.sin(ph + t * 3.1) * math.sin(t * math.pi)
        pts.append((x0 + (x1 - x0) * t - uz * w, z0 + (z1 - z0) * t + ux * w))
    return 'M' + ' L'.join(f'{f2(x)} {f2(z)}' for x, z in pts)

def st(w, op=1, col=INK, dash=None, cap='round'):
    s = f'fill="none" stroke="{col}" stroke-width="{w}" {NS} stroke-linecap="{cap}" stroke-linejoin="round"'
    if op != 1: s += f' stroke-opacity="{op}"'
    if dash: s += f' stroke-dasharray="{dash}"'
    return s

def edges(poly_, w, op=1, col=INK, passes=2, over=(0.5, 1.4)):
    """draw a polygon as straightedge strokes, each edge overshooting, retraced faintly"""
    out = ''
    pts = list(poly_.exterior.coords)[:-1] if hasattr(poly_, 'exterior') else poly_
    for k in range(len(pts)):
        a, b = pts[k], pts[(k + 1) % len(pts)]
        if math.hypot(b[0] - a[0], b[1] - a[1]) < 0.4: continue
        d = jl(a, b, over)
        if passes > 1: d += ' ' + jl(a, b, (0.1, 0.6), amp=0.12)
        out += f'<path d="{d}" {st(w, op, col)}/>'
    return out

def smooth_d(pts, amp=0.25, closed=False):
    """a freehand curve through points (Catmull Rom to cubic), a little wander"""
    q = [(x + R.uniform(-amp, amp), z + R.uniform(-amp, amp)) for x, z in pts]
    if closed: q = q + q[:3]
    d = f'M{f2(q[0][0])} {f2(q[0][1])}' if not closed else f'M{f2(q[1][0])} {f2(q[1][1])}'
    rng = range(1, len(q) - 2) if closed else range(0, len(q) - 1)
    for i in rng:
        p0 = q[i - 1] if i > 0 else q[i]; p1 = q[i]; p2 = q[i + 1]; p3 = q[i + 2] if i + 2 < len(q) else q[i + 1]
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        d += f' C{f2(c1[0])} {f2(c1[1])} {f2(c2[0])} {f2(c2[1])} {f2(p2[0])} {f2(p2[1])}'
    return d + (' Z' if closed else '')

def geom_d(g):
    """shapely polygon(s) to a path, holes included"""
    gs = list(g.geoms) if hasattr(g, 'geoms') else [g]
    d = ''
    for p in gs:
        if p.is_empty or p.geom_type != 'Polygon': continue
        for ring in [p.exterior] + list(p.interiors):
            c = list(ring.coords)
            d += 'M' + ' L'.join(f'{f2(x)} {f2(z)}' for x, z in c[:-1]) + ' Z '
    return d.strip()

def wob_circle(cx, cz, r, n=40, wob=0.04, seed=1):
    pts = []
    for k in range(n):
        a = 2 * math.pi * k / n
        rr = r * (1 + wob * math.sin(a * 3 + seed) + wob * 0.5 * math.sin(a * 7 + seed * 1.7))
        pts.append((cx + rr * math.cos(a), cz + rr * math.sin(a)))
    return pts

# ---------------------------------------------------------------- plant symbols (feet, centered on cx, cz)
def conifer(cx, cz, r, seed, sig=False, shadow=True):
    rr = random.Random(seed)
    s = ''
    if shadow:
        s += f'<circle cx="{f2(cx + NV[0] * r * .32)}" cy="{f2(cz + NV[1] * r * .32)}" r="{f2(r * .98)}" fill="{INK}" fill-opacity="{.07 if sig else .05}"/>'
    n = max(30, int(r * 6.2)) // 2 * 2; pts = []
    for k in range(n):
        a = 2 * math.pi * k / n + rr.uniform(-.04, .04)
        q = r * (1.0 + rr.uniform(-.035, .035)) if k % 2 == 0 else r * rr.uniform(.9, .95)
        pts.append((cx + q * math.cos(a), cz + q * math.sin(a)))
    s += f'<path d="M{" L".join(f"{f2(x)} {f2(z)}" for x, z in pts)} Z" fill="{PAPER}" fill-opacity=".55" {st(1.0 if sig else .6, .85 if sig else .72)}/>'
    c2 = wob_circle(cx + rr.uniform(-.2, .2), cz + rr.uniform(-.2, .2), r * .93, 36, .05, seed)
    s += f'<path d="M{" L".join(f"{f2(x)} {f2(z)}" for x, z in c2)} Z" {st(.4, .28)}/>'
    m = rr.randint(13, 17) if not sig else 26
    d = ''
    for k in range(m):
        a = 2 * math.pi * k / m + rr.uniform(-.12, .12)
        r0, r1 = r * .12, r * rr.uniform(.55, .82)
        ex, ez = cx + r1 * math.cos(a), cz + r1 * math.sin(a)
        d += f'M{f2(cx + r0 * math.cos(a))} {f2(cz + r0 * math.sin(a))} L{f2(ex)} {f2(ez)} '
        for s2 in (-1, 1):
            b = a + s2 * .5; ln = r * .16
            d += f'M{f2(ex - ln * .2 * math.cos(a))} {f2(ez - ln * .2 * math.sin(a))} L{f2(ex + ln * math.cos(b) * .6)} {f2(ez + ln * math.sin(b) * .6)} '
    s += f'<path d="{d}" {st(.42 if not sig else .55, .5 if not sig else .62)}/>'
    s += f'<circle cx="{f2(cx)}" cy="{f2(cz)}" r="{f2(max(.45, r * .07))}" fill="{ACC if sig else INK}"/>'
    return s

def aspen(cx, cz, r, seed, shadow=True):
    rr = random.Random(seed)
    s = ''
    if shadow:
        s += f'<circle cx="{f2(cx + NV[0] * r * .3)}" cy="{f2(cz + NV[1] * r * .3)}" r="{f2(r * .95)}" fill="{INK}" fill-opacity=".04"/>'
    m = 9; a0 = rr.uniform(0, 6.28)
    P_ = [(cx + r * .86 * math.cos(a0 + 2 * math.pi * k / m), cz + r * .86 * math.sin(a0 + 2 * math.pi * k / m)) for k in range(m)]
    d = f'M{f2(P_[0][0])} {f2(P_[0][1])}'
    for k in range(m):
        a = a0 + 2 * math.pi * (k + .5) / m; p = P_[(k + 1) % m]
        d += f' Q{f2(cx + r * 1.2 * math.cos(a))} {f2(cz + r * 1.2 * math.sin(a))} {f2(p[0])} {f2(p[1])}'
    s += f'<path d="{d} Z" fill="{PAPER}" fill-opacity=".5" {st(.55, .7)}/>'
    d = ''
    for k in range(4):
        a = a0 + k * 1.57 + rr.uniform(-.3, .3); l1 = r * .55
        ex, ez = cx + l1 * math.cos(a), cz + l1 * math.sin(a)
        d += f'M{f2(cx)} {f2(cz)} L{f2(ex)} {f2(ez)} M{f2(ex)} {f2(ez)} L{f2(ex + r * .2 * math.cos(a + .6))} {f2(ez + r * .2 * math.sin(a + .6))} '
    s += f'<path d="{d}" {st(.4, .45)}/><circle cx="{f2(cx)}" cy="{f2(cz)}" r="{f2(r * .08)}" fill="{INK}"/>'
    return s

def shrub(cx, cz, r, kind, seed):
    rr = random.Random(seed)
    c = wob_circle(cx, cz, r, 18, .08, seed)
    s = f'<path d="M{" L".join(f"{f2(x)} {f2(z)}" for x, z in c)} Z" fill="{PAPER}" fill-opacity=".45" {st(.5, .72)}/>'
    if kind == 'rib':          # wax currant: three berries
        for k in range(3):
            a = rr.uniform(0, 6.28) + k * 2.1
            s += f'<circle cx="{f2(cx + r * .38 * math.cos(a))}" cy="{f2(cz + r * .38 * math.sin(a))}" r="{f2(r * .11)}" fill="{INK}" fill-opacity=".7"/>'
    elif kind == 'ame':        # serviceberry: a five point star
        d = ''.join(f'M{f2(cx)} {f2(cz)} L{f2(cx + r * .62 * math.cos(a))} {f2(cz + r * .62 * math.sin(a))} ' for a in [k * 1.2566 - 1.57 for k in range(5)])
        s += f'<path d="{d}" {st(.4, .6)}/>'
    elif kind == 'sym':        # snowberry: a ring inside
        s += f'<circle cx="{f2(cx)}" cy="{f2(cz)}" r="{f2(r * .45)}" {st(.4, .55)}/>'
    elif kind == 'cor':        # redtwig dogwood: twigs past the edge
        d = ''
        for k in range(7):
            a = k * .8976 + rr.uniform(-.1, .1)
            d += f'M{f2(cx + r * .3 * math.cos(a))} {f2(cz + r * .3 * math.sin(a))} L{f2(cx + r * 1.18 * math.cos(a))} {f2(cz + r * 1.18 * math.sin(a))} '
        s += f'<path d="{d}" {st(.42, .6, ACC)}/>'
    return s

def small(cx, cz, r, kind, seed):
    rr = random.Random(seed)
    if kind == 'fes':          # bunchgrass: a fountain of blades
        d = ''
        for k in range(11):
            a = k * .571 + rr.uniform(-.15, .15); l = r * rr.uniform(.7, 1.05)
            d += f'M{f2(cx)} {f2(cz)} Q{f2(cx + l * .5 * math.cos(a - .25))} {f2(cz + l * .5 * math.sin(a - .25))} {f2(cx + l * math.cos(a))} {f2(cz + l * math.sin(a))} '
        return f'<path d="{d}" {st(.38, .62)}/>'
    if kind == 'pen':          # penstemon: a six point burst with a dot
        d = ''.join(f'M{f2(cx + r * .25 * math.cos(a))} {f2(cz + r * .25 * math.sin(a))} L{f2(cx + r * math.cos(a))} {f2(cz + r * math.sin(a))} ' for a in [k * 1.047 + .3 for k in range(6)])
        return f'<path d="{d}" {st(.42, .7)}/><circle cx="{f2(cx)}" cy="{f2(cz)}" r="{f2(r * .2)}" fill="{ACC}"/>'
    if kind == 'eri':          # buckwheat: a low cushion, dotted
        c = wob_circle(cx, cz, r * .85, 14, .1, seed)
        return (f'<path d="M{" L".join(f"{f2(x)} {f2(z)}" for x, z in c)} Z" fill="{INK}" fill-opacity=".05" {st(.4, .6)}/>'
                + ''.join(f'<circle cx="{f2(cx + r * .4 * math.cos(a))}" cy="{f2(cz + r * .4 * math.sin(a))}" r="{f2(r * .09)}" fill="{INK}" fill-opacity=".6"/>' for a in (0.4, 2.5, 4.6)))
    if kind == 'ach':          # yarrow: three florets
        return ''.join(f'<circle cx="{f2(cx + r * .45 * math.cos(a))}" cy="{f2(cz + r * .45 * math.sin(a))}" r="{f2(r * .34)}" {st(.38, .62)}/>' for a in (0.2, 2.3, 4.4))
    if kind == 'mah':          # creeping Oregon grape: holly crosses
        d = ''
        for k in range(3):
            ox, oz = cx + r * .5 * math.cos(k * 2.1 + .5), cz + r * .5 * math.sin(k * 2.1 + .5); q = r * .32
            d += f'M{f2(ox - q)} {f2(oz - q)} L{f2(ox + q)} {f2(oz + q)} M{f2(ox - q)} {f2(oz + q)} L{f2(ox + q)} {f2(oz - q)} '
        return f'<path d="{d}" {st(.4, .6)}/>'
    if kind == 'jun':          # rush: upright ticks
        d = ''.join(f'M{f2(cx + o)} {f2(cz + r * .7)} L{f2(cx + o * 1.5)} {f2(cz - r * .8)} ' for o in (-r * .45, 0, r * .45))
        return f'<path d="{d}" {st(.4, .65)}/>'
    return ''

# ---------------------------------------------------------------- the plan
def build_plan():
    pid = 'l10'
    b = ''
    defs = f'''<defs>
<pattern id="{pid}-deck" width="0.5" height="0.5" patternUnits="userSpaceOnUse" patternTransform="rotate(90)"><line x1="0" y1="0.25" x2="0.5" y2="0.25" stroke="{TIMBER}" stroke-width="0.5" {NS}/></pattern>
<pattern id="{pid}-flag" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(8)"><path d="M0 0 L2.6 0.3 L3.1 2.4 L0.4 2.8 Z M3.1 2.4 L6 2.1 M2.6 0.3 L4.4 0 M4.4 0 L6 0.6 M4.4 0 L4.7 2.2 M0.4 2.8 L0 6 M0.4 2.8 L2.2 3.4 L2.9 6 M2.2 3.4 L5.1 4.1 L6 6 M3.1 2.4 L2.2 3.4 M5.1 4.1 L4.7 2.2" fill="none" stroke="{INK}" stroke-width="0.4" opacity="0.5" {NS}/></pattern>
<pattern id="{pid}-grav" width="1.4" height="1.2" patternUnits="userSpaceOnUse"><circle cx=".35" cy=".3" r=".16" fill="none" stroke="{INK}" stroke-width=".35" opacity=".45" {NS}/><circle cx="1.05" cy=".9" r=".12" fill="none" stroke="{INK}" stroke-width=".35" opacity=".45" {NS}/></pattern>
<pattern id="{pid}-rev" width="7" height="7" patternUnits="userSpaceOnUse">{''.join(f'<circle cx="{f2(R.uniform(0, 7))}" cy="{f2(R.uniform(0, 7))}" r=".13" fill="{INK}" opacity=".32"/>' for _ in range(9))}<path d="M1.2 5.6 l.35 -.9 M1.6 5.7 l.05 -1 M2 5.6 l-.3 -.85 M4.8 2.1 l.35 -.9 M5.2 2.2 l.05 -1 M5.6 2.1 l-.3 -.85" stroke="{INK}" stroke-width=".35" opacity=".4" {NS}/></pattern>
<pattern id="{pid}-snow" width="3" height="3" patternUnits="userSpaceOnUse" patternTransform="rotate(-45)"><line x1="0" y1="1.5" x2="3" y2="1.5" stroke="{INK}" stroke-width=".4" opacity=".38" {NS}/></pattern>
<pattern id="{pid}-rock" width="5" height="5" patternUnits="userSpaceOnUse">{''.join(f'<ellipse cx="{f2(x)}" cy="{f2(y)}" rx="{f2(r)}" ry="{f2(r * .75)}" transform="rotate({R.randint(0, 90)} {f2(x)} {f2(y)})" fill="{PAPER}" stroke="{INK}" stroke-width=".4" opacity=".6" {NS}/>' for x, y, r in [(1, 1.1, .8), (3.6, .9, .65), (2.3, 3, .9), (4.4, 3.6, .55), (.6, 4.2, .5)])}</pattern>
<clipPath id="{pid}-clip"><rect x="{VB[0]}" y="{VB[1]}" width="{VB[2]}" height="{VB[3]}"/></clipPath>
</defs>'''

    # --- zones (computed)
    bldg = unary_union([ROOF, DECK]).buffer(0)
    zone0 = bldg.buffer(5, join_style=2).difference(bldg).difference(STONE).difference(DRIVE).difference(APRON)
    zone1 = bldg.buffer(30, 24)
    walk_poly = LineString(WALK_LINE).buffer(2.5, cap_style=2)
    paving = unary_union([DRIVE, APRON, walk_poly])

    # snow storage: pervious ground beside the drive and apron, outside the 30 ft front easement, off every root zone
    roots = unary_union([Point(x, z).buffer((SIG_R + 1) if i == 0 else r + 1) for i, (x, z, r) in enumerate(TREES)])
    snow_raw = [Polygon([(-78.5, 47.2), (-66.5, 47.8), (-63.5, 54.5), (-63.5, 62.0), (-78.5, 62.0)]),
                Polygon([(-62.0, 41.2), (-40.5, 41.2), (-40.5, 58.0), (-62.0, 60.0)]),
                Polygon([(-75.0, 31.6), (-66.3, 23.5), (-66.3, 19.5), (-71.0, 22.5)])]
    snow = unary_union(snow_raw).difference(EAS_ZONE).difference(roots).difference(paving.buffer(0.6)).difference(zone0).buffer(0)
    snow = MultiPolygon([g for g in (snow.geoms if hasattr(snow, 'geoms') else [snow]) if g.area > 20])

    # enhanced planting, limited and drip irrigated: the court edges and the lower patio's south rim
    enh_raw = [Polygon([(-38.6, 22.0), (-28.0, 20.5), (-26.0, 37.8), (-38.4, 34.5)]),
               Polygon([(-38.0, 45.5), (-22.5, 45.8), (-22.5, 53.0), (-38.0, 55.0)]),
               Polygon([(24.5, 64.5), (37.6, 60.6), (42.6, 62.6), (45.5, 64.2), (43.0, 69.5), (28.5, 72.0), (24.5, 69.5)])]
    enh = unary_union(enh_raw).difference(TPZ.buffer(0.8)).difference(zone0).difference(walk_poly.buffer(0.5)).difference(ROOF.buffer(0.5)).buffer(0)
    enh = MultiPolygon([g for g in (enh.geoms if hasattr(enh, 'geoms') else [enh]) if g.area > 15])

    # swales and the dispersal field (conceptual, sized by civil)
    SW_N = [(-80, -25.5), (-50, -24.5), (-20, -23.5), (10, -23.2), (32, -22.0), (41, -16), (46, -5), (50.5, 6), (53.2, 17), (55.0, 27)]
    SW_S = [(-38.5, 58.5), (-30, 66), (-22, 84.5), (-8, 83.5), (8, 78.5), (26, 72.8), (38, 70.5), (47, 67), (53.5, 58)]
    SW_D = [(-78.5, 61.5), (-60, 60.8), (-44, 59.3), (-38.5, 58.5)]
    disp = Polygon(wob_circle(57.5, 42.5, 1, 30, 0, 1)).buffer(0)
    disp = Polygon([(57.5 + 5.2 * math.cos(a) + .6 * math.sin(3 * a), 42.5 + 13.5 * math.sin(a)) for a in [k * 2 * math.pi / 40 for k in range(40)]]).buffer(0)

    # disturbed ground back to native: everything the work touches, less what is built or planted
    lim = unary_union([bldg.buffer(14, 16), STONE.buffer(10), DRIVE.buffer(7), APRON.buffer(7), walk_poly.buffer(6),
                       LineString(SW_N).buffer(4), LineString(SW_S).buffer(4), LineString(SW_D).buffer(4), disp.buffer(4), snow.buffer(3)]).buffer(0)
    lim = lim.simplify(1.2).intersection(LOT).difference(EAS_ZONE.difference(DRIVE.buffer(7))).buffer(0)
    reveg = lim.difference(bldg).difference(STONE).difference(paving).difference(zone0).difference(enh).difference(snow).difference(TPZ).difference(disp).difference(BENCH)

    # ---- body
    b += f'<g clip-path="url(#{pid}-clip)">'
    for c in SITE['contours']:
        b += f'<path d="{c["d"]}" {st(.75 if c["m"] else .4, .42 if c["m"] else .24)}/>'
        if c['m']:
            x, z = c['at']
            b += f'<text x="{f2(x)}" y="{f2(z - .6)}" font-size="1.6" text-anchor="middle" fill="{INK}" opacity=".55" font-family="Tenor Sans, sans-serif" letter-spacing=".08em">{c["el"]}</text>'
    # zone 1, then the fills
    b += f'<path d="{geom_d(zone1)}" {st(.55, .5, INK, "1 5")}/>'
    b += f'<path d="{geom_d(reveg)}" fill="url(#{pid}-rev)" fill-rule="evenodd"/>'
    b += f'<path d="{smooth_d(list(lim.exterior.coords)[:-1] if lim.geom_type == "Polygon" else list(max(lim.geoms, key=lambda g: g.area).exterior.coords)[:-1], .15, True)}" {st(.6, .5, INK, "10 3 2 3")}/>'
    b += f'<path d="{geom_d(zone0)}" fill="url(#{pid}-grav)" fill-rule="evenodd"/>'
    b += f'<path d="{geom_d(snow)}" fill="url(#{pid}-snow)" {st(.7, .7, INK, "4 2.5")}/>'
    for g in enh.geoms:
        b += f'<path d="{geom_d(g)}" fill="{INK}" fill-opacity=".035"/>'
        b += f'<path d="{smooth_d(list(g.exterior.coords)[:-1], .12, True)}" {st(.65, .7)}/>'
    b += f'<path d="{geom_d(disp)}" fill="url(#{pid}-rock)"/>' + f'<path d="{smooth_d(list(disp.exterior.coords)[:-1], .2, True)}" {st(.6, .6)}/>'
    # lot, setbacks, easement
    b += f'<path d="{SITE["setback"]}" {st(.7, .5, INK, "6 4")}/>'
    b += f'<path d="{SITE["lot"]}" {st(1.4, 1, INK, "18 4 3 4")}/>'
    ec = list(EAS.coords)
    b += f'<path d="M{f2(ec[0][0])} {f2(ec[0][1])} L{f2(ec[1][0])} {f2(ec[1][1])}" {st(.8, .7, INK, "2 3")}/>'
    # drive, apron, walk
    b += f'<path d="{geom_d(DRIVE)}" fill="{INK}" fill-opacity=".06"/>' + edges(DRIVE.simplify(.3), .8, .85, passes=1, over=(0.1, .5))
    b += f'<path d="{geom_d(APRON)}" fill="{INK}" fill-opacity=".04"/>' + f'<path d="{geom_d(APRON)}" {st(.6, .7, INK, "3 2")}/>'
    wl = LineString(WALK_LINE); n = int(wl.length / 3.4); walk_sf = 0.0
    for k in range(n):
        p0 = wl.interpolate(k * wl.length / n + .3); p1 = wl.interpolate((k + 1) * wl.length / n - .3)
        ux, uz = p1.x - p0.x, p1.y - p0.y; L2 = math.hypot(ux, uz); ux, uz = ux / L2, uz / L2
        wv = 2.5 + R.uniform(-.15, .15)
        q = [(p0.x - uz * wv, p0.y + ux * wv), (p1.x - uz * wv, p1.y + ux * wv), (p1.x + uz * wv, p1.y - ux * wv), (p0.x + uz * wv, p0.y - ux * wv)]
        walk_sf += Polygon(q).area
        b += f'<path d="{poly_d(q)}" fill="{PAPER}" {st(.55, .8)}/>'
    # terraces, pit and bench
    b += f'<path d="{geom_d(STONE)}" fill="url(#{pid}-flag)"/>' + edges(STONE, .75, .9)
    b += f'<path d="{geom_d(DECK)}" fill="url(#{pid}-deck)"/>' + edges(DECK, .75, .9)
    b += f'<path d="{geom_d(BENCH)}" fill="{PAPER}" {st(.7, .9)}/>'
    b += f'<path d="{geom_d(BENCH)}" fill="{INK}" fill-opacity=".08"/>'
    b += f'<circle cx="{PIT_C[0]}" cy="{PIT_C[1]}" r="{PIT_R}" fill="{PAPER}" {st(.8, .95)}/><circle cx="{PIT_C[0]}" cy="{PIT_C[1]}" r="{PIT_R * .62}" fill="{INK}" fill-opacity=".12" {st(.5, .7)}/>'
    # the house, a pale ghost under its roof line
    b += f'<path d="{geom_d(ROOF)}" fill="#ebe8e1" fill-opacity=".92"/>' + edges(ROOF.simplify(.25), 1.1, .9)
    b += f'<path d="{B.P["foot"]["rib"]}" {st(.5, .45, INK, "3 2")}/>'
    b += f'<path d="{B.ROOF["beam"]}" fill="{INK}" opacity=".7"/>'
    b += f'<path d="{B.ROOF["chim"]}" fill="#d6d5d1" {st(.7, .8)}/>'
    # swales: freehand, flow chevrons
    for line in (SW_N, SW_S, SW_D):
        b += f'<path d="{smooth_d(line, .1)}" {st(.9, .75, INK, "5 2.2")}/>'
        ls = LineString(line)
        for k in range(1, int(ls.length / 14) + 1):
            s0 = k * 14 - 1
            p = ls.interpolate(s0); p2 = ls.interpolate(s0 + 1)
            ux, uz = p2.x - p.x, p2.y - p.y; L2 = math.hypot(ux, uz) or 1; ux, uz = ux / L2, uz / L2
            a = (p.x - ux * 1.4 - uz * 1.0, p.y - uz * 1.4 + ux * 1.0); c = (p.x - ux * 1.4 + uz * 1.0, p.y - uz * 1.4 - ux * 1.0)
            b += f'<path d="M{f2(a[0])} {f2(a[1])} L{f2(p.x)} {f2(p.y)} L{f2(c[0])} {f2(c[1])}" {st(.7, .8)}/>'
    b += '</g>'

    # ---- plants
    plants = {k: 0 for k in ('pin', 'asp', 'rib', 'ame', 'sym', 'cor', 'fes', 'pen', 'eri', 'ach', 'mah', 'jun')}
    pl = ''
    # native shrubs in the revegetation, outside zone 1, off the roots
    spots = [(-58, -27), (-30, -28), (2, -29.5), (24, -28.5), (-84, 3.5), (-86, 55), (-68, 66), (-40, 72), (-6, 92), (18, 86), (58, 76), (62, 14), (-50, 97), (-24, 98)]
    kinds = ['ame', 'rib', 'sym', 'ame', 'rib', 'sym', 'rib', 'ame', 'sym', 'rib', 'ame', 'sym', 'rib', 'ame']
    placed_pts = []
    keep_out = unary_union([bldg.buffer(7), paving.buffer(2), STONE.buffer(2), snow.buffer(1), enh.buffer(1), disp.buffer(2), EAS_ZONE])
    for (x, z), k in zip(spots, kinds):
        if not LOT.contains(Point(x, z)) or roots.contains(Point(x, z)) or keep_out.contains(Point(x, z)): continue
        for j in range(R.choice((2, 3))):
            px, pz = x + R.uniform(-3.5, 3.5) * (j > 0), z + R.uniform(-3, 3) * (j > 0)
            if any(math.hypot(px - a, pz - c) < 3.4 for a, c in placed_pts) or roots.contains(Point(px, pz)) or keep_out.contains(Point(px, pz)) or not LOT.contains(Point(px, pz)): continue
            placed_pts.append((px, pz)); pl += shrub(px, pz, 2.0, k, R.randint(0, 999)); plants[k] += 1
    # aspens by the dispersal field and the south swale
    for x, z in [(49.0, 75.5), (53.5, 72.0), (57.0, 77.0), (52.0, 80.5), (61.5, 64.5)]:
        pl += aspen(x, z, 3.4, R.randint(0, 999)); plants['asp'] += 1
    # rushes along the swale mouths and the dispersal rim
    for x, z in [(50.5, 60.5), (52.8, 55.5), (54.8, 30.5), (56.8, 33.5), (60.8, 54.5), (61.8, 50.5)]:
        pl += small(x, z, .9, 'jun', R.randint(0, 999)); plants['jun'] += 1
    # enhanced beds: a few shrubs at the back, perennials and grasses in drifts
    for gi, g in enumerate(enh.geoms):
        minx, minz, maxx, maxz = g.bounds
        pts = []
        tries = 0
        while tries < 1400:
            tries += 1
            x, z = R.uniform(minx, maxx), R.uniform(minz, maxz)
            if not g.buffer(-1.0).contains(Point(x, z)): continue
            if any(math.hypot(x - a, z - c) < 2.7 for a, c in pts): continue
            pts.append((x, z))
        for x, z in pts:
            if Point(x, z).distance(TPZ) < 3.6:
                k = 'mah'
            else:
                h = math.sin(x * .21 + gi) + math.cos(z * .17 - gi * .7)
                k = 'fes' if h > .7 else 'pen' if h > .05 else 'ach' if h > -.45 else 'eri'
            if k in ('fes', 'pen', 'eri', 'ach', 'mah'):
                pl += small(x, z, 1.15, k, R.randint(0, 999)); plants[k] += 1
        # shrubs: dogwood and currant at the bed's far edge
        far = [(x, z) for x, z in pts]
        far.sort(key=lambda p: -Point(p).distance(FOOT))
        for x, z in far[:2]:
            k = 'cor' if gi != 1 else 'rib'
            pl += shrub(x, z, 1.9, k, R.randint(0, 999)); plants[k] += 1
    # existing pines, kept; the court pine fenced at its drip line
    for i, (x, z, r) in enumerate(TREES):
        if i == 0: continue
        pl += conifer(x, z, r, 40 + i); plants['pin'] += 1
    pl += conifer(SIG[0], SIG[1], SIG_R, 7, sig=True); plants['pin'] += 1
    # tree protection fence: at the drip line, the house closes the east side
    arc = Point(SIG[0], SIG[1]).buffer(SIG_R + .3, 128).exterior.difference(ROOF.buffer(1.2))
    arcs = list(arc.geoms) if hasattr(arc, 'geoms') else [arc]
    fence = ''
    for a in arcs:
        c = list(a.coords)
        fence += f'<path d="M{" L".join(f"{f2(x)} {f2(z)}" for x, z in c)}" {st(1.2, .95, ACC, "2.2 1.4")}/>'
        n = int(a.length / 6)
        for k in range(n + 1):
            p = a.interpolate(k * a.length / max(n, 1))
            fence += f'<rect x="{f2(p.x - .38)}" y="{f2(p.y - .38)}" width=".76" height=".76" fill="{PAPER}" stroke="{ACC}" stroke-width=".8" {NS}/>'

    body = f'<g clip-path="url(#{pid}-clip)">{b}{pl}{fence}</g>'
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" class="dsvg" viewBox="{f2(VB[0])} {f2(VB[1])} {f2(VB[2])} {f2(VB[3])}" preserveAspectRatio="xMidYMid meet" '
           f'role="img" aria-label="Landscape concept plan">{defs}{body}</svg>')
    areas = dict(snow=round(snow.area), enh=round(enh.area), reveg=round(reveg.area), zone0=round(zone0.area), walk=round(walk_sf),
                 paved=round(DRIVE.area + APRON.area + walk_sf), disp=round(disp.area), tpz=round(TPZ.area))
    return svg, plants, areas

def poly_d(pts):
    return 'M' + ' L'.join(f'{f2(x)} {f2(z)}' for x, z in pts) + ' Z'

# ---------------------------------------------------------------- symbols for the palette strip
def sym_svg(kind):
    if kind == 'pin': inner = conifer(0, 0, 4.2, 9, shadow=False)
    elif kind == 'sig': inner = conifer(0, 0, 4.2, 7, sig=True, shadow=False)
    elif kind == 'asp': inner = aspen(0, 0, 3.6, 3, shadow=False)
    elif kind in ('rib', 'ame', 'sym', 'cor'): inner = shrub(0, 0, 3.0, kind, 5)
    else: inner = small(0, 0, 3.2, kind, 5)
    return f'<svg viewBox="-5 -5 10 10" aria-hidden="true">{inner}</svg>'

def swatch(kind):
    pid = 'l10'
    fills = {'rev': f'url(#{pid}-rev)', 'grav': f'url(#{pid}-grav)', 'snow': f'url(#{pid}-snow)', 'rock': f'url(#{pid}-rock)'}
    if kind == 'fence':
        return f'<svg viewBox="0 0 16 8" aria-hidden="true"><path d="M1 4 H15" {st(1.2, 1, ACC, "2.2 1.4")}/><rect x="3.6" y="3.6" width=".8" height=".8" fill="{PAPER}" stroke="{ACC}" stroke-width=".8" {NS}/><rect x="11.6" y="3.6" width=".8" height=".8" fill="{PAPER}" stroke="{ACC}" stroke-width=".8" {NS}/></svg>'
    if kind == 'swale':
        return f'<svg viewBox="0 0 16 8" aria-hidden="true"><path d="M1 4 H15" {st(.9, .8, INK, "5 2.2")}/><path d="M7.6 3 L9 4 L7.6 5" {st(.7, .8)}/></svg>'
    if kind == 'z1':
        return f'<svg viewBox="0 0 16 8" aria-hidden="true"><path d="M1 4 H15" {st(.7, .6, INK, "1 5")}/></svg>'
    if kind == 'lim':
        return f'<svg viewBox="0 0 16 8" aria-hidden="true"><path d="M1 4 H15" {st(.7, .6, INK, "10 3 2 3")}/></svg>'
    if kind == 'eas':
        return f'<svg viewBox="0 0 16 8" aria-hidden="true"><path d="M1 4 H15" {st(.8, .7, INK, "2 3")}/></svg>'
    if kind == 'enh':
        return f'<svg viewBox="0 0 16 8" aria-hidden="true"><rect x="1" y="1" width="14" height="6" rx="1.6" fill="{INK}" fill-opacity=".035" {st(.65, .7)}/>{small(5, 4, 1.8, "pen", 2)}{small(10.5, 4, 1.8, "fes", 3)}</svg>'
    return f'<svg viewBox="0 0 16 8" aria-hidden="true"><rect x="1" y="1" width="14" height="6" rx="1.2" fill="{fills[kind]}" {st(.6, .6, INK, "4 2.5" if kind == "snow" else None)}/></svg>'

# ---------------------------------------------------------------- write the sheet
def main():
    svg, Q, A = build_plan()
    snow_pct = round(100 * A['snow'] / A['paved'])
    # the palette follows Lahontan's Form 5 plant list: natural and enhanced vegetation, symbol, names, size, quantity, LCC
    natural = [
        ('sig', 'Pinus spp.', 'Signature court pine', 'Existing', '1', 'kept, fenced at the drip line, limbed up'),
        ('pin', 'Pinus spp.', 'Existing pines', 'Existing', str(Q['pin'] - 1), 'kept close, species on the tree survey'),
        ('asp', 'Populus tremuloides', 'Quaking aspen', '15 gal', str(Q['asp']), 'clumps at the dispersal field'),
        ('ame', 'Amelanchier utahensis', 'Utah serviceberry', '5 gal', str(Q['ame']), ''),
        ('rib', 'Ribes cereum', 'Wax currant', '5 gal', str(Q['rib']), ''),
        ('sym', 'Symphoricarpos rotundifolius', 'Mountain snowberry', '5 gal', str(Q['sym']), ''),
    ]
    enhanced = [
        ('cor', 'Cornus sericea', 'Redtwig dogwood', '5 gal', str(Q['cor'])),
        ('fes', 'Festuca idahoensis', 'Idaho fescue', '1 gal', str(Q['fes'])),
        ('pen', 'Penstemon newberryi', 'Mountain pride', '1 gal', str(Q['pen'])),
        ('eri', 'Eriogonum umbellatum', 'Sulfur buckwheat', '1 gal', str(Q['eri'])),
        ('ach', 'Achillea millefolium', 'Western yarrow', '1 gal', str(Q['ach'])),
        ('mah', 'Mahonia repens', 'Creeping Oregon grape', '1 gal', str(Q['mah'])),
        ('jun', 'Juncus balticus', 'Baltic rush', '1 gal', str(Q['jun'])),
    ]
    seed = [('Elymus elymoides', 'Squirreltail'), ('Festuca idahoensis', 'Idaho fescue'), ('Elymus glaucus', 'Blue wildrye'),
            ('Poa secunda', 'Sandberg bluegrass'), ('Lupinus argenteus', 'Silver lupine'), ('Eriogonum umbellatum', 'Sulfur buckwheat'),
            ('Achillea millefolium', 'Western yarrow'), ('Penstemon speciosus', 'Showy penstemon')]
    legend = [('fence', 'Tree protection fence', 'at the drip line'), ('grav', 'Zone 0', '5 ft, noncombustible'),
              ('z1', 'Zone 1', '30 ft, lean and green'), ('enh', 'Enhanced planting', f'about {A["enh"]:,} sf, drip'),
              ('rev', 'Native revegetation', 'seed mix, no irrigation'), ('snow', 'Snow storage', f'about {A["snow"]:,} sf'),
              ('swale', 'Swale', 'conceptual, by civil'), ('rock', 'Rock dispersal', 'sized by civil'),
              ('lim', 'Limit of work', 'confirm on grading'), ('eas', 'Front easement', '30 ft, confirm')]
    notes = [
        'Native revegetation on all disturbed ground. Enhanced planting kept small, on drip.',
        f'Snow storage about {A["snow"]:,} sf, about {snow_pct}% of the paving, outside the 30 ft front easement.',
        'Nothing inside the court pine fence: no grading, trenching, storage or irrigation. Arborist to confirm.',
        'Zone 0 gravel within 5 ft of walls and decks. Pines limbed up, crowns clear of roofs.',
        'Swales and grades conceptual, civil to size. Names, sizes and counts about, FA accuracy.',
    ]
    labels = [
        dict(p=frac(SIG[0] - 1, SIG[1] - 3.5), t='Signature pine', s='kept, fenced at the drip line', k='tag'),
        dict(p=frac(8.5, -3.0), t='Walsh Residence', s='roof outline', k='room'),
        dict(p=frac(-33.0, 28.5), t='Front court', k='room'),
        dict(p=frac(-19.0, 45.4), t='Entry walk', s='stone slabs', k='room'),
        dict(p=frac(-100.0, 42.8), t='Drive', k='room'),
        dict(p=frac(-51.0, 27.0), t='Apron', k='room'),
        dict(p=frac(-52.0, 49.0), t='Snow storage', s=f'about {A["snow"]:,} sf in all', k='room'),
        dict(p=frac(26.0, 13.5), t='Upper terrace', s='cedar deck', k='room'),
        dict(p=frac(24.0, 34.2), t='Fire pit', s='semicircular bench', k='room'),
        dict(p=frac(36.0, 47.0), t='Lower patio', s='stone, steps down', k='room'),
        dict(p=frac(57.5, 42.5), t='Rock dispersal', k='room'),
        dict(p=frac(-6.0, -27.0), t='Swale', s='to the dispersal field', k='room'),
        dict(p=frac(-2.0, 88.5), t='Swale', k='room'),
        dict(p=frac(-40.0, -19.0), t='Zone 0', s='5 ft, gravel', k='room'),
        dict(p=frac(-57.0, 78.5), t='Native revegetation', s='Lahontan seed mix', k='room'),
        dict(p=frac(36.0, 75.5), t='Enhanced', s='drip', k='room'),
        dict(p=frac(-86.0, 88.0), t='Front easement', s='30 ft, confirm', k='room'),
        dict(p=frac(-120.0, -26.0), t='Property line', s='confirm on survey', k='room'),
        dict(p=frac(-136.5, 96.0), t='Lahontan Drive', k='road'),
    ]
    view = dict(x=FXs(SX(VB[0])), y=FYs(SY(VB[1])), w=VB[2] * S10, h=VB[3] * S10)
    # sheet notes, sheet inches
    notes_hand = [
        dict(text='keep the signature tree', t=[SX(-85), SY(-1.5)], p=[SX(SIG[0] - 13.3), SY(SIG[1])], a='r'),
        dict(text='pines kept close', t=[SX(40), SY(-32)], p=[SX(52.5), SY(-17.5)], a='r'),
        dict(text='terraces step down with the land', t=[SX(22), SY(104)], p=[SX(34), SY(55)], a='r'),
    ]
    data = dict(view=view, svg=svg, labels=labels, natural=natural, enhanced=enhanced, seed=seed, legend=legend,
                notes=notes, sym={k: sym_svg(k) for k in set([r[0] for r in natural] + [r[0] for r in enhanced])},
                sw={k: swatch(k) for k, _, _ in legend}, areas=A, snowPct=snow_pct, north=NORTH)
    js = JS.replace('__DATA__', json.dumps(data, ensure_ascii=False)).replace('__NOTES__', json.dumps(notes_hand)) \
        .replace('__NX__', f'{SX(61.0):.3f}').replace('__NY__', f'{SY(104.0):.3f}').replace('__SNOW__', f'{A["snow"]:,}').replace('__PCT__', str(snow_pct))
    OUT.write_text(js)
    print('wrote', OUT, len(js) // 1024, 'KB', A, Q)

JS = r'''/* land-a crew · L1.0 Landscape concept plan, 1 in = 10 ft, registered on the A1.2 site plan.
   Built by sheets/tools/land-a/build_l10.py from the pocket model's site data; edit the builder, not this file. */
(function () {
  const D = __DATA__;
  const SX_N = __NX__, SY_N = __NY__;
  const P = v => +(v * 100).toFixed(3);
  const CSS = `
.la-v{--l-b:max(calc(7.5px * var(--fl)),calc(var(--u) * .105));--l-i:max(calc(8.5px * var(--fl)),calc(var(--u) * .125))}
.la-strip{position:absolute}
.la-strip h3{margin:0;font:400 max(calc(10px * var(--fl)),calc(var(--u) * .2))/1.1 var(--ft);letter-spacing:.18em;text-transform:uppercase}
.la-strip .la-sub{margin:calc(var(--u)*.06) 0 calc(var(--u)*.14);font:italic 400 max(calc(9px * var(--fl)),calc(var(--u) * .14))/1.25 var(--fs);color:var(--muted)}
.la-gp{display:flex;justify-content:space-between;align-items:baseline;margin:calc(var(--u)*.16) 0 calc(var(--u)*.02);font:400 max(calc(7.5px * var(--fl)),calc(var(--u) * .112))/1.2 var(--ft);letter-spacing:.18em;text-transform:uppercase;color:var(--accent)}
.la-gp span{color:var(--muted);letter-spacing:.14em}
.la-pr{display:grid;grid-template-columns:calc(var(--u)*.4) 1fr calc(var(--u)*.62) calc(var(--u)*.34) calc(var(--u)*.34);align-items:center;column-gap:calc(var(--u)*.1);
  padding:calc(var(--u)*.06) 0 calc(var(--u)*.01);background:var(--swoop) no-repeat 0 0 / 100% calc(var(--u) * .07)}
.la-pr.hd{background:none;padding:0;font:400 max(calc(6.5px * var(--fl)),calc(var(--u) * .085))/1.1 var(--ft);letter-spacing:.14em;text-transform:uppercase;color:var(--muted)}
.la-pr svg{width:calc(var(--u)*.34);height:calc(var(--u)*.34);overflow:visible;display:block}
.la-pr .nm{display:flex;flex-direction:column;min-width:0}
.la-pr .nm i{font:italic 400 max(calc(9px * var(--fl)),calc(var(--u) * .14))/1.12 var(--fs);white-space:nowrap}
.la-pr .nm b{font:400 max(calc(6.5px * var(--fl)),calc(var(--u) * .085))/1.25 var(--ft);letter-spacing:.14em;text-transform:uppercase;color:var(--muted);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.la-pr .sz{font:italic 400 max(calc(8.5px * var(--fl)),calc(var(--u) * .125))/1.1 var(--fs);color:var(--muted);white-space:nowrap}
.la-pr .q{font:italic 400 max(calc(9px * var(--fl)),calc(var(--u) * .14))/1.1 var(--fs);text-align:right;font-variant-numeric:lining-nums}
.la-pr .lc{justify-self:end;width:calc(var(--u)*.13);height:calc(var(--u)*.13);border:1px solid rgba(27,26,24,.4);border-radius:2px}
.la-pr.hd .lc{border:0;width:auto;height:auto}
.la-seed{display:grid;grid-template-columns:1fr 1fr;column-gap:calc(var(--u)*.2);margin-top:calc(var(--u)*.04)}
.la-seed span{padding:calc(var(--u)*.06) 0 calc(var(--u)*.01);background:var(--swoop) no-repeat 0 0 / 100% calc(var(--u) * .07);white-space:nowrap}
.la-seed i{font:italic 400 max(calc(8.5px * var(--fl)),calc(var(--u) * .128))/1.2 var(--fs)}
.la-seed b{font:400 max(calc(6.5px * var(--fl)),calc(var(--u) * .08))/1.2 var(--ft);letter-spacing:.12em;text-transform:uppercase;color:var(--muted);margin-left:.5em}
.la-lg{display:grid;grid-template-columns:1fr 1fr;column-gap:calc(var(--u)*.2);row-gap:calc(var(--u)*.07);margin-top:calc(var(--u)*.06)}
.la-lg .li{display:grid;grid-template-columns:calc(var(--u)*.46) 1fr;column-gap:calc(var(--u)*.08);align-items:center}
.la-lg svg{width:calc(var(--u)*.46);height:calc(var(--u)*.23);overflow:visible;display:block}
.la-lg b{display:block;font:400 max(calc(6.5px * var(--fl)),calc(var(--u) * .09))/1.2 var(--ft);letter-spacing:.14em;text-transform:uppercase;white-space:nowrap}
.la-lg i{display:block;font:italic 400 max(calc(8px * var(--fl)),calc(var(--u) * .118))/1.15 var(--fs);color:var(--muted);white-space:nowrap}
.la-nt{margin:calc(var(--u)*.04) 0 0;padding:0;list-style:none;counter-reset:n}
.la-nt li{position:relative;padding:calc(var(--u)*.05) 0 calc(var(--u)*.02) calc(var(--u)*.22);font:italic 400 max(calc(8.5px * var(--fl)),calc(var(--u) * .125))/1.25 var(--fs);color:var(--ink)}
.la-nt li::before{counter-increment:n;content:counter(n);position:absolute;left:0;top:calc(var(--u)*.06);font:400 max(calc(7px * var(--fl)),calc(var(--u) * .1))/1.2 var(--ft);color:var(--accent)}
@media screen and (max-width:760px), screen and (max-aspect-ratio:1/1) and (max-width:1100px){
  .fhtml:has(> .la-root){position:relative;inset:auto}
  .la-root .la-strip{position:relative;left:auto !important;top:auto !important;width:auto !important;margin:0 0 30px}
  .la-root .la-pr{grid-template-columns:30px 1fr 46px 26px 20px;column-gap:8px;padding:6px 0 2px;background-size:100% 6px}
  .la-root .la-pr svg{width:26px;height:26px}
  .la-root .la-pr .lc{width:10px;height:10px}
  .la-root .la-seed,.la-root .la-lg{grid-template-columns:1fr}
  .la-root .la-lg .li{grid-template-columns:40px 1fr;column-gap:10px}
  .la-root .la-lg svg{width:40px;height:20px}
  .la-root .la-seed span{padding:6px 0 1px;background-size:100% 6px}
  .la-root .la-gp{margin:16px 0 4px}
  .la-root .la-nt li{padding:5px 0 2px 16px}
}
`;
  function strip(ctx) {
    const U = ctx.U, e = ctx.esc;
    const hd = `<div class="la-pr hd"><span>Key</span><span>Botanical · common name</span><span>Size</span><span style="text-align:right">Qty</span><span class="lc">LCC</span></div>`;
    const row = r => `<div class="la-pr">${D.sym[r[0]]}<span class="nm"><i>${e(r[1])}</i><b>${e(r[2])}</b></span><span class="sz">${e(r[3])}</span><span class="q">${e(r[4])}</span><span class="lc"></span></div>`;
    return `<div class="la-strip" style="left:${U(ctx.FX(24.15))};top:${U(ctx.FY(3.85))};width:${U(7.95)}">
      <h3>Plant palette</h3><p class="la-sub">Keyed to the plan, set up like Lahontan's plant list. LCC column for the Final submittal.</p>
      <div class="la-gp">Natural vegetation<span>native, no irrigation</span></div>${hd}${D.natural.map(row).join('')}
      <div class="la-gp">Enhanced vegetation<span>limited, drip</span></div>${hd}${D.enhanced.map(row).join('')}
      <div class="la-gp">Revegetation seed mix<span>rates by the supplier</span></div>
      <div class="la-seed">${D.seed.map(s => `<span><i>${e(s[0])}</i><b>${e(s[1])}</b></span>`).join('')}</div>
      <div class="la-gp">Legend</div>
      <div class="la-lg">${D.legend.map(l => `<div class="li">${D.sw[l[0]]}<div><b>${e(l[1])}</b><i>${e(l[2])}</i></div></div>`).join('')}</div>
      <div class="la-gp">Landscape notes</div>
      <ol class="la-nt">${D.notes.map(n => `<li>${e(n)}</li>`).join('')}</ol>
    </div>`;
  }
  function bar(ctx) {
    const ft = [0, 10, 20, 30], sc = 0.1, L = 30;
    let r = '';
    for (let k = 1; k < ft.length; k++) r += `<rect x="${ft[k - 1] / L}" y="0" width="${(ft[k] - ft[k - 1]) / L}" height="1" class="${k % 2 ? 'on' : ''}"/>`;
    return `<span class="gbar" style="width:${ctx.U(L * sc)}"><svg viewBox="0 0 1 1" preserveAspectRatio="none" aria-hidden="true">${r}</svg>${ft.map(v => `<span style="left:${P(v / L)}%">${v}${v === L ? ' ft' : ''}</span>`).join('')}</span>`;
  }
  function north(ctx, x, y, s) {
    const a = D.north, r = a * Math.PI / 180;
    return `<div class="dnorth" style="left:${ctx.U(ctx.FX(x) - s / 2)};top:${ctx.U(ctx.FY(y) - s / 2)};width:${ctx.U(s)};height:${ctx.U(s)}" aria-label="North">
      <svg viewBox="-1 -1 2 2" aria-hidden="true"><circle r=".78"/><g transform="rotate(${a})"><path class="nd" d="M0 -.98 L.2 .18 L0 .02 L-.2 .18 Z"/><path class="nl" d="M0 .02 V.78"/></g></svg>
      <span style="left:${P(.5 + .62 * Math.sin(r))}%;top:${P(.5 - .62 * Math.cos(r))}%">N</span></div>`;
  }
  const lbl = l => `<span class="lbl ${l.k || 'room'}" style="left:${P(l.p[0])}%;top:${P(l.p[1])}%"><b>${l.t}</b>${l.s ? `<i>${l.s}</i>` : ''}</span>`;
  LIVING_SHEETS.push({
    id: 'L1.0', group: 'Landscape', title: 'Landscape concept plan', short: 'Landscape concept', foot: 'Landscape concept',
    scale: '1 in = 10 ft', issued: [4],
    cap: 'Pines kept close and the court pine fenced at its drip line. Terraces step down with the land, the rest of the lot goes back to native.',
    data: ['Court pine fenced at the drip line', 'Snow storage about __SNOW__ sf, about __PCT__% of paving', 'Native revegetation, limited enhanced', 'Zone 0, 5 ft noncombustible'],
    notes: __NOTES__,
    html: ctx => {
      const U = ctx.U, v = D.view;
      return `<style>${CSS}</style><div class="la-root">
        <div class="view dv la-v" style="left:${U(v.x)};top:${U(v.y)};width:${U(v.w)};height:${U(v.h)};--ar:${(v.w / v.h).toFixed(4)}">${D.svg}${D.labels.map(lbl).join('')}</div>
        ${strip(ctx)}
        <div class="dvt" style="left:${U(ctx.FX(24.15))};top:${U(ctx.FY(18.35))}">${ctx.viewTitle(1, 'Landscape concept plan', '1 in = 10 ft')}${bar(ctx)}</div>
        ${north(ctx, SX_N, SY_N, 1.0)}</div>`;
    }
  });
})();
'''

if __name__ == '__main__':
    main()
