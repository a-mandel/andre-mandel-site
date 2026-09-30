#!/usr/bin/env python3
"""plans-a crew: A0.6 area diagrams and A2.0 lower level and foundation plan, from the pocket model.

Reuses the lead's plan extraction in walsh/set/draw/build_drawings.py by import (read only, draw/ is never written).
Writes walsh/set/sheets/plans-a.js from plans-a.tpl.js: the SVGs inline, labels as fractions of each view,
every placement in sheet inches. Numbers on the sheets are read live from DRAWINGS.calcs (calcs.json), so the
tables can never drift from the lead's calcs.

Run:  python3 walsh/set/sheets/tools/plans-a/build_plans_a.py
"""
import json, math, sys
sys.dont_write_bytecode = True        # never leave a __pycache__ in draw/
from pathlib import Path
from shapely.geometry import Polygon, LineString, MultiPolygon, Point
from shapely.ops import unary_union

HERE = Path(__file__).resolve().parent
SET = HERE.parents[2]
sys.path.insert(0, str(SET / 'draw'))
import build_drawings as bd                     # noqa: E402  (module level only computes; it writes nothing on import)

P, L1, L2, ROOF, SITE = bd.P, bd.L1, bd.L2, bd.ROOF, bd.SITE
INK, ACC, TIMBER, PAPER = bd.INK, bd.ACC, bd.TIMBER, bd.PAPER
f2, P_, poly_d, circle_d, frac, NS = bd.f2, bd.P_, bd.poly_d, bd.circle_d, bd.frac, bd.NS
TREE = bd.TREE
C = bd.C

# the lead's calcs.json must be the same numbers this model gives, or the sheets would disagree
disk = json.loads((SET / 'draw' / 'calcs.json').read_text())
if json.loads(json.dumps(C)) != disk:
    raise SystemExit('calcs.json is stale against the model: run draw/build_drawings.py first')

# ------------------------------------------------------------------ geometry
def polys(d, min_area=2.0):
    out = []
    for sp in bd.subpaths(d):
        if len(sp) >= 3 and abs(bd.area(sp)) >= min_area:
            out.append(Polygon(sp).buffer(0))
    return out

def simp(g, tol=0.06):
    return g.simplify(tol, preserve_topology=True)

def gd(g):
    """shapely geometry to an svg path d, in feet"""
    if g.is_empty: return ''
    if isinstance(g, (MultiPolygon,)) or g.geom_type == 'GeometryCollection':
        return ' '.join(gd(p) for p in g.geoms)
    if g.geom_type == 'Polygon':
        s = poly_d(list(g.exterior.coords)[:-1])
        for r in g.interiors: s += ' ' + poly_d(list(r.coords)[:-1])
        return s
    if g.geom_type in ('LineString', 'LinearRing'):
        return poly_d(list(g.coords), False)
    if g.geom_type == 'MultiLineString':
        return ' '.join(poly_d(list(l.coords), False) for l in g.geoms)
    return ''

def mend(gs):
    return unary_union([g.buffer(0.08, join_style=2) for g in gs]).buffer(-0.08, join_style=2)

GAR = mend(polys(L1['gar']))
MAIN_PARTS = polys(L1['main'])
MAIN = mend(MAIN_PARTS)
LOWER = mend(polys(L1['lower']))
PRIM = mend(polys(L2['prim']))
PDECK = mend(polys(L2['deck'], 0.5))
DECK = Polygon(bd.TERR['deck']).buffer(0)
STONE = Polygon(bd.TERR['stone']).buffer(0)
ALL = unary_union([GAR, MAIN, LOWER]).buffer(0.08, join_style=2).buffer(-0.08, join_style=2)
LOT = Polygon(bd.subpaths(SITE['lot'])[0])
ROOFG = Polygon(bd.ROOFP).buffer(0)
DRIVE = Polygon(bd.DRIVE).buffer(0)
APRON = Polygon(bd.APRON)

def hull_xz(flat):
    pts = [(flat[i], flat[i + 2]) for i in range(0, len(flat), 3)]
    return Polygon(pts).convex_hull

CHIMS = [hull_xz(bd.D['chim']['rib']['stone']), hull_xz(bd.D['chim']['ribN']['stone'])]

def columns():
    out = []
    for key in ('wing', 'rib'):
        a = bd.D[key]['col']; cl = []
        for i in range(0, len(a), 3):
            x, z = a[i], a[i + 2]
            for c in cl:
                if abs(c[0] - x) < 1.2 and abs(c[1] - z) < 1.2: c[2].append((x, z)); break
            else: cl.append([x, z, [(x, z)]])
        for c in cl:
            xs = [p[0] for p in c[2]]; zs = [p[1] for p in c[2]]
            out.append(((min(xs) + max(xs)) / 2, (min(zs) + max(zs)) / 2))
    return out

COLS = columns()

def grade_el(x, z):
    return bd.DATUM + bd.ground(x, z)

def grade_range(g):
    x0, z0, x1, z1 = g.bounds; v = []
    n = 40
    for i in range(n + 1):
        for j in range(n + 1):
            x = x0 + (x1 - x0) * i / n; z = z0 + (z1 - z0) * j / n
            if g.contains(Point(x, z)): v.append(grade_el(x, z))
    return min(v), max(v)

# ------------------------------------------------------------------ svg
def defs(pid, k=1.0):
    """hatches in feet; k scales the spacing for small scale keys"""
    s = lambda v: f2(v * k)
    return f'''<defs>
<pattern id="{pid}-cond" width="{s(1.1)}" height="{s(1.1)}" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><line x1="0" y1="0" x2="0" y2="{s(1.1)}" stroke="{INK}" stroke-width="0.45" opacity="0.5" {NS}/></pattern>
<pattern id="{pid}-dots" width="{s(1.4)}" height="{s(1.4)}" patternUnits="userSpaceOnUse"><circle cx="{s(.35)}" cy="{s(.4)}" r="{s(.1)}" fill="{INK}" opacity="0.5"/><circle cx="{s(1.05)}" cy="{s(1.1)}" r="{s(.08)}" fill="{INK}" opacity="0.4"/></pattern>
<pattern id="{pid}-deck" width="{s(.6)}" height="{s(.6)}" patternUnits="userSpaceOnUse"><line x1="0" y1="{s(.3)}" x2="{s(.6)}" y2="{s(.3)}" stroke="{TIMBER}" stroke-width="0.55" {NS}/></pattern>
<pattern id="{pid}-deckR" width="{s(.6)}" height="{s(.6)}" patternUnits="userSpaceOnUse" patternTransform="rotate(-18)"><line x1="0" y1="{s(.3)}" x2="{s(.6)}" y2="{s(.3)}" stroke="{TIMBER}" stroke-width="0.55" {NS}/></pattern>
<pattern id="{pid}-flag" width="{s(6)}" height="{s(6)}" patternUnits="userSpaceOnUse" patternTransform="rotate(8) scale({f2(k)})"><path d="M0 0 L2.6 0.3 L3.1 2.4 L0.4 2.8 Z M3.1 2.4 L6 2.1 M2.6 0.3 L4.4 0 M4.4 0 L6 0.6 M4.4 0 L4.7 2.2 M0.4 2.8 L0 6 M0.4 2.8 L2.2 3.4 L2.9 6 M2.2 3.4 L5.1 4.1 L6 6 M3.1 2.4 L2.2 3.4 M5.1 4.1 L4.7 2.2" fill="none" stroke="{INK}" stroke-width="0.4" opacity="0.55" {NS}/></pattern>
<pattern id="{pid}-conc" width="{s(2.2)}" height="{s(2.2)}" patternUnits="userSpaceOnUse"><circle cx="{s(.4)}" cy="{s(.5)}" r="{s(.09)}" fill="{INK}" opacity="0.45"/><circle cx="{s(1.5)}" cy="{s(.9)}" r="{s(.06)}" fill="{INK}" opacity="0.35"/><path d="M{s(1.0)} {s(1.6)} l{s(.22)} {s(-.12)} l{s(.02)} {s(.22)} Z" fill="none" stroke="{INK}" stroke-width="0.4" opacity="0.45" {NS}/><circle cx="{s(1.9)}" cy="{s(1.95)}" r="{s(.08)}" fill="{INK}" opacity="0.4"/></pattern>
<pattern id="{pid}-imp" width="{s(1.6)}" height="{s(1.6)}" patternUnits="userSpaceOnUse" patternTransform="rotate(-45)"><line x1="0" y1="0" x2="0" y2="{s(1.6)}" stroke="{INK}" stroke-width="0.45" opacity="0.55" {NS}/></pattern>
</defs>'''

def wrap(vb, body, pid, k=1.0, clip=True):
    x0, y0, w, h = vb
    cp = f'<clipPath id="{pid}-clip"><rect x="{f2(x0)}" y="{f2(y0)}" width="{f2(w)}" height="{f2(h)}"/></clipPath>'
    inner = f'<g clip-path="url(#{pid}-clip)">{body}</g>' if clip else body
    return (f'<svg xmlns="http://www.w3.org/2000/svg" class="dsvg" viewBox="{f2(x0)} {f2(y0)} {f2(w)} {f2(h)}" '
            f'preserveAspectRatio="xMidYMid meet" aria-hidden="true">{defs(pid, k)}{cp}{inner}</svg>')

def sketch(g, over=1.3, w=0.45, op=0.45, min_edge=3.5):
    """hand drafting overshoot: each long edge runs a little past its corners, a straightedge habit"""
    d = []
    geoms = g.geoms if hasattr(g, 'geoms') else [g]
    for p in geoms:
        pts = list(simp(p, 0.15).exterior.coords)
        for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
            L = math.hypot(x2 - x1, y2 - y1)
            if L < min_edge: continue
            ux, uy = (x2 - x1) / L, (y2 - y1) / L
            d.append(f'M{f2(x1 - ux * over)} {f2(y1 - uy * over)} L{f2(x1)} {f2(y1)} M{f2(x2)} {f2(y2)} L{f2(x2 + ux * over)} {f2(y2 + uy * over)}')
    return P_(' '.join(d), stroke=INK, w=w, op=op)

def tree(k=1.0, r=13):
    return (P_(circle_d(TREE[0], TREE[1], r, 60, 0.03, 2), stroke=INK, w=0.6, dash='3 2', op=0.6) +
            f'<circle cx="{TREE[0]}" cy="{TREE[1]}" r="{f2(0.55 * k)}" fill="{ACC}"/>')

def lab(vb, x, z, t, s='', k='room', **kw):
    d = dict(p=frac(vb, x, z), t=t, k=k)
    if s: d['s'] = s
    d.update(kw)
    return d

# ------------------------------------------------------------------ A0.6 area diagrams
S8 = 1 / 8
A1VB = (-79.0, -19.5, 124.0, 100.0)            # level 1 window, feet
A2VB = (-3.0, 33.0, 44.0, 42.0)                # level 2 window, around the south wing
S32 = 1 / 32
SKVB = (-128.0, -40.0, 200.0, 167.0)           # site keys, the lot

def area_l1():
    pid = 'pa61'; b = ''
    b += P_(gd(ROOFG), stroke=INK, w=0.5, dash='1.5 3', op=0.35)                  # roof over, dotted
    b += P_(gd(STONE), fill=f'url(#{pid}-flag)', stroke=INK, w=0.8)
    b += P_(gd(DECK), fill=f'url(#{pid}-deck)', stroke=TIMBER, w=0.9)
    b += P_(P['pit'], fill=PAPER, stroke=INK, w=0.55)
    b += P_(gd(GAR), fill=f'url(#{pid}-dots)', stroke=INK, w=1.3)
    b += P_(gd(MAIN), fill='rgba(27,26,24,.03)') + P_(gd(MAIN), fill=f'url(#{pid}-cond)', stroke=INK, w=1.3)
    b += P_(gd(LOWER), fill='rgba(27,26,24,.06)') + P_(gd(LOWER), fill=f'url(#{pid}-cond)', stroke=INK, w=1.3)
    for g in (GAR, MAIN, LOWER, DECK, STONE): b += sketch(g)
    b += tree()
    vb = A1VB
    labels = [
        lab(vb, 9.0, -3.2, 'Main level · 5997.5', '{levels.main.sf} sf', 'tag'),
        lab(vb, -57.3, 0.0, 'Garage and gear bay', '{garage} sf', 'tag'),
        lab(vb, 12.8, 55.0, 'Lower level · 5992.5', '{levels.lower.sf} sf', 'tag'),
        lab(vb, 26.1, 16.5, 'Upper terrace', '{decks.upper_terrace} sf', 'room'),
        lab(vb, 36.4, 50.5, 'Stone patio', '{patio_stone} sf', 'room'),
        lab(vb, 8.0, 27.5, 'Bridge', 'main level', 'room'),
        lab(vb, -10.4, 63.0, 'Granny suite', 'main level', 'room'),
    ]
    return wrap(vb, b, pid), labels

def area_l2():
    pid = 'pa62'; b = ''
    b += P_(gd(ALL), fill='rgba(27,26,24,.018)', stroke=INK, w=0.6, dash='4 3', op=0.5)       # level 1 below
    b += P_(gd(STONE), stroke=INK, w=0.5, dash='4 3', op=0.35)
    b += P_(gd(PRIM), fill='rgba(27,26,24,.06)') + P_(gd(PRIM), fill=f'url(#{pid}-cond)', stroke=INK, w=1.3)
    b += P_(gd(PDECK), fill=f'url(#{pid}-deckR)', stroke=TIMBER, w=1.0)
    b += sketch(PRIM) + sketch(PDECK, min_edge=6)
    vb = A2VB
    labels = [
        lab(vb, 12.2, 55.5, 'Primary suite · 6004.0', '{levels.primary.sf} sf', 'tag'),
        lab(vb, 31.9, 44.5, 'Primary terrace', '{decks.primary_terrace} sf', 'room'),
        lab(vb, 7.6, 37.0, 'Level 1 below', 'dashed', 'room'),
    ]
    return wrap(vb, b, pid), labels

def site_key(kind):
    pid = 'pa6' + kind[0]; k = 3.2; b = ''
    for c in SITE['contours']:
        b += P_(c['d'], stroke=INK, w=0.4, op=0.16)
    b += P_(SITE['setback'], stroke=INK, w=0.6, dash='5 3', op=0.45)
    b += P_(gd(LOT), fill='rgba(246,245,241,.4)', stroke=INK, w=1.1, dash='12 3 2 3')
    b += P_(gd(ALL), stroke=INK, w=0.5, op=0.5)
    if kind == 'cov':
        b += P_(gd(ROOFG), fill='rgba(27,26,24,.14)') + P_(gd(ROOFG), fill=f'url(#{pid}-imp)', stroke=INK, w=1.1)
        b += P_(gd(DRIVE), stroke=INK, w=0.5, op=0.45) + P_(gd(STONE), stroke=INK, w=0.5, op=0.4)
    else:
        for g in (ROOFG, DRIVE, APRON, STONE):
            b += P_(gd(g), fill='rgba(27,26,24,.14)') + P_(gd(g), fill=f'url(#{pid}-imp)', stroke=INK, w=0.9)
        b += P_(gd(DECK), stroke=TIMBER, w=0.8) + P_(gd(PDECK), stroke=TIMBER, w=0.8, dash='3 2')
    b += f'<circle cx="{TREE[0]}" cy="{TREE[1]}" r="1.8" fill="{ACC}"/>'
    vb = SKVB
    if kind == 'cov':
        labels = [lab(vb, -2.0, -3.5, 'Roof footprint', '{roof_footprint} sf', 'tag'),
                  lab(vb, 5.0, 108.0, 'Lot', 'about {lot_sf} sf, confirm on survey', 'room')]
    else:
        labels = [lab(vb, -95.0, 27.5, 'Drive and apron', '{drive+apron_allowance} sf', 'room'),
                  lab(vb, -2.0, -3.5, 'Roof', '{roof_footprint} sf', 'tag'),
                  lab(vb, 53.0, 45.0, 'Patio', '{patio_stone} sf', 'room', a='l'),
                  lab(vb, 5.0, 108.0, 'Walks, allowance', '{walks_allowance} sf, not drawn', 'room')]
    return wrap(vb, b, pid, k), labels

# ------------------------------------------------------------------ A2.0 lower level and foundation
PVB, S316, PSX, PSY, PVIEW = bd.PVB, bd.S316, bd.PSX, bd.PSY, bd.PVIEW      # A2.1's registration, so the plans flip in place
STEM, FOOT_OUT, FOOT_IN = 0.67, 0.67, 1.33                                   # 8 in stem, 24 in footing centered under it

def seam(a, b, half=0.5):
    """a wall strip about 2 x half wide, centered on the seam between two floor zones"""
    return (a.buffer(half) & b.buffer(half)) & ALL.buffer(0.01)

def high_grade(g, ff, clear=1.5, step=1.0):
    """the part of a floor zone where natural grade comes within clear ft of the floor: no room for a crawl space"""
    x0, z0, x1, z1 = g.bounds; cells = []
    x = x0
    while x < x1:
        z = z0
        while z < z1:
            if grade_el(x + step / 2, z + step / 2) > ff - clear:
                cells.append(Polygon([(x, z), (x + step, z), (x + step, z + step), (x, z + step)]))
            z += step
        x += step
    return unary_union(cells).buffer(1.2, join_style=1).buffer(-1.2, join_style=1).simplify(0.4) & g

MAIN_HIGH = high_grade(MAIN, 5997.5)
MAIN_HIGH_PCT = round(100 * MAIN_HIGH.area / MAIN.area)

STEP_GM = seam(GAR, MAIN)            # 2.5 ft step, garage up from the north wing
STEP_ML = seam(MAIN, LOWER)          # 5 ft step, the south wing down from the bridge and the granny wing

def foundation():
    pid = 'pa20'; b = ''
    vb = PVB
    # natural grade, the reason the foundation steps
    for c in SITE['contours']:
        b += P_(c['d'], stroke=INK, w=0.8 if c['m'] else 0.45, op=0.4 if c['m'] else 0.22)
        if c['m']:
            x, z = c['at']
            if vb[0] + 3 < x < vb[0] + vb[2] - 3 and vb[1] + 3 < z < vb[1] + vb[3] - 3 and not ALL.buffer(3).contains(Point(x, z)) and not (x < -40 and z > 12):
                b += f'<text x="{f2(x)}" y="{f2(z - 0.6)}" font-size="1.5" text-anchor="middle" fill="{INK}" opacity="0.55" font-family="Tenor Sans, sans-serif" letter-spacing=".08em">{c["el"]}</text>'
    # the tree and its root zone: no footings under the drip line
    b += P_(circle_d(TREE[0], TREE[1], 13, 60, 0.03, 2), stroke=INK, w=0.6, dash='3 2', op=0.6)
    b += P_(circle_d(TREE[0], TREE[1], 9.2, 50, 0.02, 4), stroke=ACC, w=0.6, dash='1 2.4', op=0.9)
    b += f'<circle cx="{TREE[0]}" cy="{TREE[1]}" r="0.55" fill="{ACC}"/>'
    # site pieces around the house, light
    b += P_(gd(STONE), fill=f'url(#{pid}-flag)', stroke=INK, w=0.55, dash='4 2', op=0.55)
    b += P_(gd(DECK), stroke=TIMBER, w=0.8, dash='4 2')
    b += P_(gd(PDECK), stroke=TIMBER, w=0.7, dash='1.5 2.5')
    b += P_(P['pit'], fill=PAPER, stroke=INK, w=0.5, op=0.7)
    # deck piers under the upper terrace, a 6 ft grid inside the deck, spacing per structural
    dk = DECK.buffer(-1.6)
    x0, z0, x1, z1 = dk.bounds; pier = ''
    xs = [x0 + i * (x1 - x0) / 3 for i in range(4)]
    zz = z0
    while zz <= z1 + 0.01:
        for xx in xs:
            if dk.buffer(0.05).contains(Point(xx, zz)) and not Point(xx, zz).within(Point(30, 24).buffer(4.2)):
                pier += circle_d(xx, zz, 0.75, 16) + ' '
        zz += (z1 - z0) / 5
    b += P_(pier, fill=PAPER, stroke=TIMBER, w=0.7)
    # slabs and the crawl space
    b += P_(gd(GAR), fill=f'url(#{pid}-conc)')
    b += P_(gd(LOWER), fill='rgba(27,26,24,.035)') + P_(gd(LOWER), fill=f'url(#{pid}-conc)')
    b += P_(gd(MAIN), fill='rgba(27,26,24,.018)')
    # where grade meets the main floor: slab there, or cut for the crawl space
    b += P_(gd(MAIN_HIGH), fill=f'url(#{pid}-conc)', op=0.7)
    b += P_(gd(MAIN_HIGH.boundary.difference(MAIN.boundary.buffer(0.2))), stroke=INK, w=0.7, dash='6 2 1 2', op=0.7)
    # footings, dashed each side of the stem walls
    fo = ALL.buffer(FOOT_OUT, join_style=2)
    fi = ALL.buffer(-FOOT_IN, join_style=2)
    b += P_(gd(fo.boundary) + ' ' + gd(fi.boundary), stroke=INK, w=0.6, dash='3 2', op=0.75)
    for st in (STEP_GM, STEP_ML):
        b += P_(gd((st.buffer(0.9, join_style=2) & ALL.buffer(-0.3)).boundary & ALL.buffer(-0.6)), stroke=INK, w=0.6, dash='3 2', op=0.75)
    # pad footings at the columns and posts
    pads = ''
    for x, z in COLS:
        pads += poly_d([(x - 1.4, z - 1.4), (x + 1.4, z - 1.4), (x + 1.4, z + 1.4), (x - 1.4, z + 1.4)]) + ' '
    b += P_(pads, fill='rgba(246,245,241,.7)', stroke=INK, w=0.6, dash='2 1.5', op=0.85)
    b += P_(' '.join(poly_d([(x - .38, z - .38), (x + .38, z - .38), (x + .38, z + .38), (x - .38, z + .38)]) for x, z in COLS), fill=INK)
    # chimney footings: board form concrete on a spread footing
    for ch in CHIMS:
        b += P_(gd(ch.buffer(1.6, join_style=2)), fill='rgba(246,245,241,.7)', stroke=INK, w=0.65, dash='3 2')
        b += P_(gd(ch), fill='#d6d5d1', stroke=INK, w=1.0) + P_(gd(ch), fill=f'url(#{pid}-cond)')
    # stem walls, poche, with the step walls at the level changes
    # the lower level's own walls carry its perimeter (drawn cut, below), so its stem band is left to them
    stem = (ALL.difference(ALL.buffer(-STEM, join_style=2))).difference(LOWER.buffer(0.3, join_style=2)) | STEP_GM | STEP_ML
    b += P_(gd(stem), fill=INK, stroke=INK, w=0.3)
    # the lower level itself: its walls and glass as cut, from the level 1 plan
    lc = LOWER.buffer(0.9, join_style=2).difference(MAIN.buffer(-0.2))
    b += f'<clipPath id="{pid}-low"><path d="{gd(lc)}"/></clipPath>'
    b += f'<g clip-path="url(#{pid}-low)">' + P_(L1['wall'], fill=INK, stroke=INK, w=0.35) + P_(L1['glass'], fill=PAPER, stroke=INK, w=0.55) + '</g>'
    # step arrows, down toward the lower level
    b += bd.section_marks()
    # profile line, unfolded along the two section lines
    b += P_('M-62 -2 H8 V76', stroke=ACC, w=0.9, dash='1 3', op=0.9)
    # overall dimension, as A2.1
    ds, dl = bd.dim_h(-20.58, 35.82, -19.4, -1, ext_from=-15.06)
    b += ds
    labels = [
        lab(vb, 24.0, dl[1], bd.ftin(35.82 + 20.58), '', 'dim'),
        lab(vb, -57.3, -3.4, 'Garage slab · 6000.0', 'slab on grade, {garage} sf', 'tag'),
        lab(vb, 9.0, -4.6, 'Main level · 5997.5', 'crawl space and slab', 'tag'),
        lab(vb, -12.0, -10.4, 'Grade within 18 in', 'of the floor', 'room'),
        lab(vb, 25.0, 1.8, 'Crawl space', 'grade falls away', 'room'),
        lab(vb, 12.9, 57.2, 'Lower level · 5992.5', 'slab on grade, {levels.lower.sf} sf', 'tag'),
        lab(vb, 8.0, 27.0, 'Bridge', 'crawl space, stairs inside', 'room'),
        lab(vb, -10.4, 64.0, 'Granny suite', 'crawl space', 'room'),
        lab(vb, -46.5, 8.6, 'Step · 2 1/2 ft', 'garage up', 'room'),
        lab(vb, -7.2, 42.2, 'Step · 5 ft', 'retaining, lower level down', 'room'),
        lab(vb, 26.5, 17.0, 'Upper terrace · 5997.25', 'deck on piers', 'room'),
        lab(vb, 38.6, 55.0, 'Stone patio', '5992.33, on grade', 'room'),
        lab(vb, 24.3, 70.0, 'Chimney', 'footing', 'room'),
        lab(vb, 20.8, -8.9, 'Chimney', 'footing', 'room'),
        lab(vb, 5.9, -22.4, '1', 'A3.0', 'bub'),
        lab(vb, -84.0, -2.0, '2', 'A3.0', 'bub'),
        lab(vb, -62.0, 1.6, 'A', '', 'pk'),
        lab(vb, 11.3, 1.6, 'B', '', 'pk'),
        lab(vb, 11.3, 76.0, 'C', '', 'pk'),
    ]
    # natural grade spots at the corners that set the steps
    for x, z, a in ((-75.8, 7.3, 'l'), (35.8, -14.6, 'r'), (35.8, 7.9, 'r'), (-63.6, 15.3, 'l'),
                    (25.8, 62.4, 'r'), (0.0, 70.8, 'r'), (25.8, 38.7, 'r')):
        b += P_(f'M{f2(x - 1.0)} {f2(z)} H{f2(x + 1.0)} M{f2(x)} {f2(z - 1.0)} V{f2(z + 1.0)}', stroke=ACC, w=1.0)
        labels.append(dict(p=frac(vb, x, z), t=f'{grade_el(x, z):.1f}', s='grade', k='spot' + (' r' if a == 'r' else '')))
    return wrap(vb, b, pid), labels

# the unfolded step profile: along section 2 (z = -2) from the garage east to the section 1 line, then south along it
PH, PV = 3 / 64, 3 / 16                        # horizontal 3/64 in = 1 ft, vertical 3/16 in = 1 ft (4x)
PATH = [(-62.0, -2.0), (8.0, -2.0), (8.0, 76.0)]
EL0, EL1 = 5988.5, 6002.5

def profile():
    pid = 'pa2p'
    samples = []
    s = 0.0
    for (ax, az), (bx, bz) in zip(PATH, PATH[1:]):
        L = math.hypot(bx - ax, bz - az); n = int(L / 0.5)
        for i in range(n + (1 if (bx, bz) == PATH[-1] else 0)):
            t = i / n; x, z = ax + (bx - ax) * t, az + (bz - az) * t
            samples.append((s + L * t, x, z))
        s += L
    total = s
    def zone(x, z):
        p = Point(x, z)
        if GAR.buffer(0.01).contains(p): return 'G'
        if LOWER.buffer(0.01).contains(p): return 'L'
        if MAIN.buffer(0.01).contains(p): return 'M'
        return None
    FF = {'G': 6000.0, 'M': 5997.5, 'L': 5992.5}
    # svg units: x in feet along the path, y in feet of elevation times 4 (so both axes share the viewBox)
    X = lambda sv: sv
    Y = lambda el: (EL1 - el) * (PV / PH)
    W, H = total, (EL1 - EL0) * (PV / PH)
    b = ''
    # datum lines every 5 ft
    for el in (5990, 5995, 6000):
        b += P_(f'M0 {f2(Y(el))} H{f2(W)}', stroke=INK, w=0.4, dash='2 4', op=0.35)
    # grade
    g = [(X(sv), Y(grade_el(x, z))) for sv, x, z in samples]
    b += P_(poly_d(g + [(W, H), (0, H)]), fill='rgba(27,26,24,.05)')
    b += P_(poly_d(g, False), stroke=INK, w=0.9, op=0.8)
    # runs of each zone along the path
    runs, cur = [], None
    for sv, x, z in samples:
        zn = zone(x, z)
        if zn != (cur[0] if cur else None):
            if cur: runs.append(cur)
            cur = [zn, sv, sv] if zn else None
            if not zn: cur = None
        if cur: cur[2] = sv
    if cur: runs.append(cur)
    pieces, walls = '', ''
    for zn, sa, sb in runs:
        ff = FF[zn]
        if zn == 'M':      # framed floor over a crawl space
            pieces += poly_d([(X(sa), Y(ff)), (X(sb), Y(ff)), (X(sb), Y(ff - 1.0)), (X(sa), Y(ff - 1.0))])
        else:              # slab
            pieces += poly_d([(X(sa), Y(ff)), (X(sb), Y(ff)), (X(sb), Y(ff - 0.5)), (X(sa), Y(ff - 0.5))])
    b += P_(pieces, fill='rgba(27,26,24,.22)', stroke=INK, w=0.9)
    # stem walls and footings at each run end: down to below the lower grade
    ends = []
    for i, (zn, sa, sb) in enumerate(runs):
        for sv, side in ((sa, 1), (sb, -1)):
            ends.append((sv, zn, side))
    done = []
    for sv, zn, side in ends:
        if any(abs(sv - d) < 1.0 for d in done): continue
        done.append(sv)
        x, z = next((x, z) for s2, x, z in samples if abs(s2 - sv) < 0.3)
        tops = [FF[zn2] for s3, zn2, _ in ends if abs(s3 - sv) < 1.0]
        top = max(tops)
        gr = min(grade_el(*_xz(sv, samples, -1.0)), grade_el(*_xz(sv, samples, 1.0)), min(tops) - 0.5)
        bot = gr - 2.0
        w = 0.67
        x0 = X(sv) - (w if side < 0 else 0)
        b += P_(poly_d([(x0, Y(top)), (x0 + w, Y(top)), (x0 + w, Y(bot)), (x0, Y(bot))]), fill=INK)
        b += P_(poly_d([(x0 - 0.67, Y(bot)), (x0 + w + 0.67, Y(bot)), (x0 + w + 0.67, Y(bot - 1.0)), (x0 - 0.67, Y(bot - 1.0))]), fill='rgba(27,26,24,.35)', stroke=INK, w=0.6)
    # the turn at B
    sB = math.hypot(PATH[1][0] - PATH[0][0], PATH[1][1] - PATH[0][1])
    b += P_(f'M{f2(X(sB))} 0 V{f2(H)}', stroke=ACC, w=0.6, dash='1 3')
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" class="dsvg" viewBox="0 0 {f2(W)} {f2(H)}" preserveAspectRatio="none" aria-hidden="true">{b}</svg>')
    fr = lambda sv, el: [round(X(sv) / W, 5), round(Y(el) / H, 5)]
    rmid = {zn: (sa + sb) / 2 for zn, sa, sb in runs}
    labels = [
        dict(p=fr(rmid.get('G', 10), 6001.4), t='6000.0', s='garage slab', k='pf'),
        dict(p=fr(sB - 22, 5999.1), t='5997.5', s='main floor', k='pf'),
        dict(p=fr(rmid.get('L', 150), 5994.2), t='5992.5', s='lower slab', k='pf'),
        dict(p=[0.0, fr(0, 5988.9)[1]], t='A', k='pk'), dict(p=[round(X(sB) / W, 5), fr(0, 5988.9)[1]], t='B', k='pk'), dict(p=[1.0, fr(0, 5988.9)[1]], t='C', k='pk'),
    ]
    for el in (5990, 5995, 6000):
        labels.append(dict(p=[0.0, fr(0, el)[1]], t=str(el), k='pd'))
    return svg, labels, W * PH, H * PH

def _xz(sv, samples, d):
    t = sv + d
    best = min(samples, key=lambda s: abs(s[0] - t))
    return best[1], best[2]

# ------------------------------------------------------------------ legends: small swatches, 6 by 3 ft of drawing
def swatch(pid, body):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" class="sw" viewBox="0 0 6 3" preserveAspectRatio="none" aria-hidden="true">'
            f'{defs(pid, 0.62)}{body}</svg>')

BOX = 'M0.3 0.3 H5.7 V2.7 H0.3 Z'

def legend_a06():
    return [
        dict(svg=swatch('pl1', P_(BOX, fill='rgba(27,26,24,.05)') + P_(BOX, fill='url(#pl1-cond)', stroke=INK, w=1.1)), k='Conditioned', v='{conditioned} sf'),
        dict(svg=swatch('pl2', P_(BOX, fill='url(#pl2-dots)', stroke=INK, w=1.1)), k='Garage', v='{garage} sf'),
        dict(svg=swatch('pl3', P_(BOX, fill='url(#pl3-deck)', stroke=TIMBER, w=1.0)), k='Decks and terraces', v='{decks.upper_terrace+decks.primary_terrace} sf'),
        dict(svg=swatch('pl4', P_(BOX, fill='url(#pl4-flag)', stroke=INK, w=0.9)), k='Stone patio', v='{patio_stone} sf'),
        dict(svg=swatch('pl5', P_(BOX, fill='rgba(27,26,24,.14)') + P_(BOX, fill='url(#pl5-imp)', stroke=INK, w=0.9)), k='Covered or impervious', v='site keys'),
    ]

def legend_a20():
    return [
        dict(svg=swatch('pm1', P_('M0.3 1.1 H5.7 V1.9 H0.3 Z', fill=INK)), k='Stem wall', v='concrete, per structural'),
        dict(svg=swatch('pm2', P_('M0.3 0.7 H5.7 M0.3 2.3 H5.7', stroke=INK, w=0.8, dash='3 2') + P_('M0.3 1.2 H5.7 V1.8 H0.3 Z', fill=INK)), k='Footing', v='dashed, below frost'),
        dict(svg=swatch('pm3', P_(BOX, fill='url(#pm3-conc)', stroke=INK, w=0.9)), k='Slab on grade', v='or grade within 18 in'),
        dict(svg=swatch('pm4', P_(BOX, fill='rgba(27,26,24,.018)', stroke=INK, w=0.9)), k='Crawl space', v='where grade falls away'),
        dict(svg=swatch('pm5', P_('M1.6 0.2 H4.4 V2.8 H1.6 Z', fill='rgba(246,245,241,.7)', stroke=INK, w=0.8, dash='2 1.5') + P_('M2.6 1.1 H3.4 V1.9 H2.6 Z', fill=INK)), k='Pad footing', v='columns and posts'),
        dict(svg=swatch('pm6', P_(circle_d(1.8, 1.5, 0.75, 16) + ' ' + circle_d(4.2, 1.5, 0.75, 16), fill=PAPER, stroke=TIMBER, w=0.9)), k='Deck pier', v='spacing per structural'),
        dict(svg=swatch('pm7', P_('M1.9 1.5 H4.1 M3 0.4 V2.6', stroke=ACC, w=1.2)), k='Natural grade', v='from the model terrain'),
        dict(svg=swatch('pm8', P_('M0.3 1.5 C2 0.4 4 0.4 5.7 1.5', stroke=ACC, w=0.9, dash='1 2.4')), k='Tree root zone', v='no footings inside'),
    ]

# ------------------------------------------------------------------ build
def build():
    out = {}
    l1, l1l = area_l1(); l2, l2l = area_l2(); kc, kcl = site_key('cov'); ki, kil = site_key('imp')
    out['A0.6'] = dict(
        views=[
            dict(id='l1', x=1.9, y=3.95, w=A1VB[2] * S8, h=A1VB[3] * S8, svg=l1, labels=l1l),
            dict(id='l2', x=18.3, y=3.95, w=A2VB[2] * S8, h=A2VB[3] * S8, svg=l2, labels=l2l),
            dict(id='kc', x=18.2, y=13.35, w=SKVB[2] * S32, h=SKVB[3] * S32, svg=kc, labels=kcl),
            dict(id='ki', x=24.95, y=13.35, w=SKVB[2] * S32, h=SKVB[3] * S32, svg=ki, labels=kil),
        ],
        north=[dict(x=14.9, y=16.95, s=0.9)],
        legend=legend_a06(),
    )
    sx = lambda x: 1.9 + (x - A1VB[0]) * S8
    sy = lambda z: 3.95 + (z - A1VB[1]) * S8
    out['A0.6']['notes'] = [
        dict(text='the court wraps the tree', t=[sx(-31), sy(47)], p=[sx(TREE[0] - 9.6), sy(TREE[1] + 8.6)], a='r'),
    ]
    fd, fdl = foundation()
    pr, prl, pw, ph = profile()
    gmin = min(grade_range(g)[0] for g in (GAR, MAIN, LOWER)); gmax = max(grade_range(g)[1] for g in (GAR, MAIN, LOWER))
    out['A2.0'] = dict(
        views=[dict(id='fd', **PVIEW, svg=fd, labels=fdl),
               dict(id='pr', x=2.6, y=14.15, w=pw, h=ph, svg=pr, labels=prl)],
        north=[dict(x=13.1, y=14.4, s=1.1)],
        grade=[round(gmin, 1), round(gmax, 1)],
        high=MAIN_HIGH_PCT,
        cols=len(COLS),
        legend=legend_a20(),
        notes=[dict(text='no footings in the root zone', t=[PSX(-28), PSY(19.5)], p=[PSX(TREE[0] - 8.4), PSY(TREE[1] - 3.2)], a='r'),
               dict(text='the house steps down with the land', t=[PSX(-24), PSY(41)], p=[PSX(8.0), PSY(44.3)], a='r')],
    )
    out['calcs'] = C
    data = json.dumps(out, ensure_ascii=False, separators=(',', ':'))
    tpl = (HERE / 'plans-a.tpl.js').read_text()
    js = tpl.replace('/*PA_DATA*/null', data)
    (SET / 'sheets' / 'plans-a.js').write_text(js)
    print('wrote sheets/plans-a.js', len(js) // 1024, 'KB · grade under the house', gmin, gmax, '· columns', len(COLS))

if __name__ == '__main__':
    build()
