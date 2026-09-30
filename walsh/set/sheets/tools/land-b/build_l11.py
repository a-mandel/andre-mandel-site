#!/usr/bin/env python3
"""L1.1 Defensible space and planting, land-b crew (9/30/26).

Builds walsh/set/sheets/land-b.js from:
  sheets/tools/land-b/A1.2.svg   a copy of draw/A1.2.svg (site linework, lot, roof, terraces, trees), never draw/ itself
  draw/build_drawings.py         read only, for the terrain (slope) and the footprint (dripline check)
  sheets/tools/land-b/l11_sheet.js  the hand written sheet template

Zones are true offsets (shapely) from the structure: the roof edge plus the attached upper terrace deck,
clipped to the lot line as drawn on A1.2. 1 in = 20 ft on the sheet.

Run:  python3 walsh/set/sheets/tools/land-b/build_l11.py
"""
import importlib.util, json, math, random, re, sys
sys.dont_write_bytecode = True   # never write into draw/
from pathlib import Path
from shapely.geometry import Polygon, Point, LineString, MultiPolygon, box
from shapely.ops import unary_union

HERE = Path(__file__).resolve().parent
SET = HERE.parents[2]
DRAW = SET / 'draw'
INK, ACC = '#1b1a18', '#c07a2c'

spec = importlib.util.spec_from_file_location('bd', DRAW / 'build_drawings.py')
bd = importlib.util.module_from_spec(spec); spec.loader.exec_module(bd)

SRC = (HERE / 'A1.2.svg').read_text()
f2 = lambda v: f'{v:.2f}'.rstrip('0').rstrip('.') if abs(v) < 1e5 else str(v)

# ------------------------------------------------------------------ geometry from the A1.2 copy
els = re.findall(r'<(path|circle|text)\b([^>]*)>', SRC)
def attr(a, k):
    m = re.search(rf'\b{k}="([^"]*)"', a); return m.group(1) if m else None

contours, labels_el, trees = [], [], []
drive = apron = drive_cl = setback = lot = roof_d = beam_d = chim_d = deck_d = stone_d = None
pending = []
for tag, a in els:
    if tag == 'text':
        continue
    if tag == 'circle':
        r = float(attr(a, 'r')); cx, cy = float(attr(a, 'cx')), float(attr(a, 'cy'))
        if attr(a, 'fill') in (INK, ACC) and r in (0.55, 1.1):
            outer = pending[-2] if len(pending) >= 2 else None
            pts = list(zip(*[iter(bd.nums(outer))] * 2)) if outer else []
            rad = round(2 * sum(math.hypot(x - cx, y - cy) for x, y in pts) / len(pts)) / 2 if pts else 6.0
            trees.append(dict(x=cx, z=cy, r=round(rad, 1), sig=(attr(a, 'fill') == ACC), d=outer, d2=pending[-1]))
            pending = []
        continue
    d = attr(a, 'd'); fill = attr(a, 'fill'); dash = attr(a, 'stroke-dasharray'); op = attr(a, 'opacity')
    if d is None:
        continue
    if fill == 'none' and op in ('0.3', '0.55') and dash is None and attr(a, 'stroke-width') in ('0.45', '0.85'):
        contours.append((d, op == '0.55'))
    elif fill == 'rgba(27,26,24,.07)':
        drive = d
    elif fill == 'rgba(27,26,24,.035)':
        apron = d
    elif dash == '6 4':
        setback = d
    elif dash == '18 4 3 4':
        lot = d
    elif fill == 'url(#a12-deck)':
        deck_d = d
    elif fill == 'url(#a12-flag)':
        stone_d = d
    elif fill == '#e9e6df':
        roof_d = d
    elif fill == INK:
        beam_d = d
    elif fill == '#d6d5d1':
        chim_d = d
    elif fill == 'none' and attr(a, 'stroke-width') == '0.9' and op == '0.9':
        drive_cl = d
    else:
        pending.append(d)

assert roof_d and lot and deck_d and trees, 'A1.2 geometry not found'
spoly = lambda d: unary_union([Polygon(p).buffer(0) for p in bd.subpaths(d) if len(p) >= 3])
ROOF = spoly(roof_d)
DECK = Polygon(bd.subpaths(deck_d)[0]).buffer(0)
STONE = Polygon(bd.subpaths(stone_d)[0]).buffer(0)
CHIM = spoly(chim_d)
FOOT = spoly(bd.P['foot']['rib'])                 # walls, for the dripline check
LOTP = Polygon(bd.subpaths(lot)[0][:4]).buffer(0)  # the lot quad as drawn (clipped at the model's terrain edge)
STRUCT = unary_union([ROOF, DECK])                 # zones measured from the roof edge and the attached deck

Z0 = STRUCT.buffer(5, quad_segs=24).difference(STRUCT)
Z1 = STRUCT.buffer(30, quad_segs=24).difference(STRUCT.buffer(5, quad_segs=24))
Z2 = STRUCT.buffer(100, quad_segs=24).difference(STRUCT.buffer(30, quad_segs=24))
R100 = STRUCT.buffer(100, quad_segs=24)
Z0L, Z1L, Z2L = (z.intersection(LOTP) for z in (Z0, Z1, Z2))

def pd(g):
    """shapely polygon(s) to an svg path, feet"""
    if g.is_empty:
        return ''
    polys = list(g.geoms) if hasattr(g, 'geoms') else [g]
    out = []
    for p in polys:
        if p.geom_type != 'Polygon':
            continue
        for ring in [p.exterior, *p.interiors]:
            c = list(ring.coords)
            out.append('M' + ' L'.join(f'{f2(x)} {f2(y)}' for x, y in c) + 'Z')
    return ''.join(out)

def ld(g):
    if g.is_empty:
        return ''
    ls = list(g.geoms) if hasattr(g, 'geoms') else [g]
    out = []
    for l in ls:
        if l.geom_type == 'LineString':
            out.append('M' + ' L'.join(f'{f2(x)} {f2(y)}' for x, y in l.coords))
        elif l.geom_type == 'Polygon':
            out.append(pd(l))
    return ''.join(out)

# ------------------------------------------------------------------ analysis
def slope_pct(x, z, h=1.5):
    gx = (bd.ground(x + h, z) - bd.ground(x - h, z)) / (2 * h)
    gz = (bd.ground(x, z + h) - bd.ground(x, z - h)) / (2 * h)
    return 100 * math.hypot(gx, gz)

random.seed(235)
def band_slope(band):
    minx, miny, maxx, maxy = band.bounds; v = []
    while len(v) < 1500:
        x, z = random.uniform(minx, maxx), random.uniform(miny, maxy)
        if band.contains(Point(x, z)) and -122 < x < 67 and -41 < z < 121:
            v.append(slope_pct(x, z))
    v.sort(); return round(v[len(v) // 2], 1), round(v[int(len(v) * .95)], 1)

SL1, SL2 = band_slope(Z1L), band_slope(Z2L)

def zone_of(p):
    if STRUCT.buffer(5).contains(p): return 0
    if STRUCT.buffer(30).contains(p): return 1
    if STRUCT.buffer(100).contains(p): return 2
    return 3

TREES = []
for i, t in enumerate(trees):
    p = Point(t['x'], t['z'])
    TREES.append(dict(n=i + 1, x=t['x'], z=t['z'], r=t['r'], sig=t['sig'], zone=zone_of(p),
                      roof=round(p.distance(ROOF), 1), wall=round(p.distance(FOOT), 1),
                      chim=round(p.distance(CHIM), 1)))
# canopy gaps, flat to mild slope rule: 10 ft between canopies
for t in TREES:
    t['gaps'] = []
    for u in TREES:
        if u is t: continue
        g = math.hypot(t['x'] - u['x'], t['z'] - u['z']) - t['r'] - u['r']
        if g < 10 and max(t['zone'], u['zone']) <= 2:
            t['gaps'].append((u['n'], round(g, 1)))

def action(t):
    a = ['limb 6 ft']
    if t['sig']:
        return 'Keep · limb 6 ft · off the roof · arborist'
    if t['r'] >= t['roof']:
        a.append('prune off the roof')
    elif t['r'] + 5 > t['roof']:
        a.append('limbs clear of the roof')
    if t['chim'] - t['r'] < 10:
        a.append('10 ft off the chimney')
    if t['gaps']:
        a.append('crowns close to T' + ', T'.join(str(n) for n, _ in t['gaps']))
    if t['zone'] >= 2:
        a.append('thin brush below')
    s = ' · '.join(a)
    return s[0].upper() + s[1:]

for t in TREES:
    t['act'] = action(t)

SIG = next(t for t in TREES if t['sig'])
AREAS = dict(z0=round(Z0L.area, -1), z1=round(Z1L.area, -1), z2=round(Z2L.area, -1), lot=round(LOTP.area, -1))

# ------------------------------------------------------------------ plan, 1 in = 20 ft
PVB = (-168.0, -52.0, 272.0, 200.0)
def defs(pid):
    rnd = random.Random(7)
    grav = ''.join(f'<circle cx="{rnd.uniform(0, 3):.2f}" cy="{rnd.uniform(0, 3):.2f}" r="{rnd.uniform(.09, .2):.2f}"/>' for _ in range(9))
    return (f'<defs>'
            f'<pattern id="{pid}-z0" width="3" height="3" patternUnits="userSpaceOnUse"><rect width="3" height="3" fill="{INK}" fill-opacity=".07"/><g fill="{INK}" fill-opacity=".5">{grav}</g></pattern>'
            f'<pattern id="{pid}-z1" width="1.6" height="1.6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><line x1="0" y1="0" x2="0" y2="1.6" stroke="{INK}" stroke-width=".5" stroke-opacity=".34" vector-effect="non-scaling-stroke"/></pattern>'
            f'<pattern id="{pid}-z2" width="3.4" height="3.4" patternUnits="userSpaceOnUse" patternTransform="rotate(-30)"><line x1="0" y1="0" x2="0" y2="3.4" stroke="{INK}" stroke-width=".5" stroke-opacity=".2" vector-effect="non-scaling-stroke"/></pattern>'
            f'<pattern id="{pid}-deck" width="1" height="1" patternUnits="userSpaceOnUse"><line x1="0" y1=".5" x2="1" y2=".5" stroke="{INK}" stroke-width=".5" stroke-opacity=".35" vector-effect="non-scaling-stroke"/></pattern>'
            f'<filter id="{pid}-soft" x="-5%" y="-5%" width="110%" height="110%"><feGaussianBlur stdDeviation=".35"/></filter>'
            f'</defs>')

def P_(d, fill='none', stroke=None, w=0.6, op=None, dash=None, extra=''):
    s = f'<path d="{d}" fill="{fill}"'
    if stroke: s += f' stroke="{stroke}" stroke-width="{w}" vector-effect="non-scaling-stroke" stroke-linejoin="round" stroke-linecap="round"'
    if op is not None: s += f' opacity="{op}"'
    if dash: s += f' stroke-dasharray="{dash}"'
    return s + extra + '/>'

def svg_wrap(vb, body, pid, cls='lb-svg'):
    x0, y0, w, h = vb
    return (f'<svg xmlns="http://www.w3.org/2000/svg" class="{cls}" viewBox="{f2(x0)} {f2(y0)} {f2(w)} {f2(h)}" preserveAspectRatio="xMidYMid meet" aria-hidden="true">'
            f'{defs(pid)}<clipPath id="{pid}-clip"><rect x="{f2(x0)}" y="{f2(y0)}" width="{f2(w)}" height="{f2(h)}"/></clipPath><g clip-path="url(#{pid}-clip)">{body}</g></svg>')

def frac(vb, x, y):
    return [round((x - vb[0]) / vb[2], 5), round((y - vb[1]) / vb[3], 5)]

def site_base(pid, detail=False):
    b = ''
    for d, major in contours:
        b += P_(d, stroke=INK, w=0.8 if major else 0.4, op=0.42 if major else 0.22)
    b += P_(drive, fill='rgba(27,26,24,.05)', stroke=INK, w=0.8, op=.8)
    b += P_(apron, stroke=INK, w=0.5, dash='3 2', op=.6)
    b += P_(setback, stroke=INK, w=0.6, dash='6 4', op=0.45)
    return b

def zones_svg(pid, clip_lot=True):
    b = ''
    zz = (Z2L, Z1L, Z0L) if clip_lot else (Z2, Z1, Z0)
    b += P_(pd(zz[0]), fill=f'url(#{pid}-z2)')
    b += P_(pd(zz[1]), fill=f'url(#{pid}-z1)')
    b += P_(pd(zz[1]), fill=INK, extra=' fill-opacity=".025"')
    b += P_(pd(zz[2]), fill=f'url(#{pid}-z0)')
    # zone edges: thin dashed pencil lines, the 100 ft line carries on past the lot as a ghost
    for dist, w, op, dash in ((5, .7, .75, '2 1.4'), (30, .7, .6, '5 2.5')):
        ring = STRUCT.buffer(dist, quad_segs=24).exterior
        b += P_(ld(ring.intersection(LOTP) if clip_lot else ring), stroke=INK, w=w, op=op, dash=dash)
    r100 = R100.exterior
    b += P_(ld(r100.intersection(LOTP)), stroke=INK, w=.7, op=.55, dash='9 3 2 3')
    b += P_(ld(r100.difference(LOTP)), stroke=INK, w=.5, op=.28, dash='2 3')
    return b

def house_svg(pid):
    b = P_(pd(STONE), fill='rgba(27,26,24,.05)', stroke=INK, w=.5, op=.7)
    b += P_(pd(DECK), fill=f'url(#{pid}-deck)', stroke=INK, w=.6)
    b += P_(roof_d, fill='#ebe8e1', stroke=INK, w=1.3)
    b += P_(beam_d, fill=INK, op=.85)
    b += P_(chim_d, fill='#d6d5d1', stroke=INK, w=.8)
    return b

def trees_svg(pid, sig_detail=False):
    b = ''
    for t, raw in zip(TREES, trees):
        if t['sig']:
            b += P_(raw['d'], stroke=INK, w=1.0, op=.9)
            b += P_(raw['d2'], stroke=INK, w=.45, op=.5)
            b += f'<circle cx="{t["x"]}" cy="{t["z"]}" r="{1.4 if sig_detail else 1.1}" fill="{ACC}"/>'
        else:
            b += P_(raw['d'], stroke=INK, w=.6, op=.6)
            b += P_(raw['d2'], stroke=INK, w=.4, op=.4)
            b += f'<circle cx="{t["x"]}" cy="{t["z"]}" r=".55" fill="{INK}"/>'
    return b

def lot_svg():
    return P_(lot, stroke=INK, w=1.4, dash='18 4 3 4')

# radial dimensions: from the roof edge out to the lot line, ticks at 5, 30 and 100 ft where they fall inside the lot
def ray(sx, sz, ux, uz, lab_side=1):
    far = LineString([(sx, sz), (sx + ux * 400, sz + uz * 400)])
    hit = far.intersection(LOTP.exterior)
    pts = list(hit.geoms) if hasattr(hit, 'geoms') else [hit]
    e = min(pts, key=lambda p: Point(sx, sz).distance(p))
    L = Point(sx, sz).distance(e)
    b = P_(f'M{f2(sx)} {f2(sz)} L{f2(e.x)} {f2(e.y)}', stroke=INK, w=.6, op=.85)
    labs = []
    nx, nz = -uz * lab_side, ux * lab_side
    for d in [0] + [v for v in (5, 30, 100) if v < L - 2] + [L]:
        x, z = sx + ux * d, sz + uz * d
        t = 1.3
        b += P_(f'M{f2(x - ux * t + nx * t)} {f2(z - uz * t + nz * t)} L{f2(x + ux * t - nx * t)} {f2(z + uz * t - nz * t)}', stroke=INK, w=1.1)
    marks = [v for v in (5, 30, 100) if v < L - 2]
    for d in marks:
        x, z = sx + ux * (d - (2.5 if d == 5 else 9)), sz + uz * (d - (2.5 if d == 5 else 9))
        labs.append(dict(p=frac(PVB, x + nx * 3.2, z + nz * 3.2), t=f'{d} ft', k='dim'))
    x, z = sx + ux * (L + 7), sz + uz * (L + 7)
    labs.append(dict(p=frac(PVB, x, z), t=f'lot line, about {L:.0f} ft', k='dim'))
    return b, labs, L

def radial():
    b1, l1, n = ray(0.0, -16.58, 0.0, -1.0)
    b2, l2, w = ray(-76.8, 0.0, -1.0, 0.0, -1)
    return b1 + b2, l1 + l2, (round(n, 1), round(w, 1))

rb, rlabs, RAY = radial()
_hz = LineString([(20, 47.0), (80, 47.0)]).intersection(Z0)
_hz = max(list(_hz.geoms) if hasattr(_hz, 'geoms') else [_hz], key=lambda g: g.length)
_zx = (_hz.coords[0][0] + _hz.coords[-1][0]) / 2
rb += P_(f'M56 47 L{f2(_zx)} 47', stroke=INK, w=.6, op=.8) + f'<circle cx="{f2(_zx)}" cy="47" r=".9" fill="{ACC}"/>'
plan_body = site_base('l11p') + zones_svg('l11p') + lot_svg() + P_(ld(LineString(bd.subpaths(lot)[1])), stroke=INK, w=.6, op=.35, dash='18 4 3 4') + house_svg('l11p') + trees_svg('l11p') + rb
PLAN_SVG = svg_wrap(PVB, plan_body, 'l11p')

def tlabel(t, vb, dx=None, dz=None):
    ang = math.radians(-35)
    dx = t['r'] * .72 + 1.5 if dx is None else dx
    dz = -t['r'] * .72 - 1.0 if dz is None else dz
    return dict(p=frac(vb, t['x'] + dx, t['z'] + dz), t=f"T{t['n']}", k='tt')

plan_labels = [
    dict(p=frac(PVB, -90.0, 104.0), t='Zone 2 · 30 to 100 ft', s='reduce fuel, a natural mosaic', k='zn', a='l'),
    dict(p=frac(PVB, -66.0, -28.5), t='Zone 1 · 5 to 30 ft', s='lean, clean and green', k='zn', a='l'),
    dict(p=frac(PVB, 57.0, 47.0), t='Zone 0 · 0 to 5 ft', s='ember resistant, nothing that burns', k='zn', a='l'),
    dict(p=frac(PVB, -163.0, 131.0), t='100 ft reach', s='past the lot line, the neighbors', k='zn2', a='l'),
    dict(p=frac(PVB, 33.0, -46.5), t='Zone 1 past the line', s='the neighbors and Lahontan', k='zn2', a='l'),
    dict(p=frac(PVB, 58.0, 118.0), t='Lot line', s='as on A1.2, confirm on survey', k='zn2', a='l'),
    dict(p=frac(PVB, -140.0, 70.0), t='Lahontan Drive', k='road'),
    dict(p=frac(PVB, -20.0, -3.0), t='Walsh Residence', s='roof edge and deck, the structure', k='tag'),
    dict(p=frac(PVB, 29.0, 49.0), t='Stone patio', k='sm'),
]
plan_labels += rlabs
for t in TREES:
    if t['sig']:
        continue
    plan_labels.append(tlabel(t, PVB))
plan_labels.append(dict(p=frac(PVB, SIG['x'] + 8.5, SIG['z'] - 12.5), t='T1', k='tt hot'))

# ------------------------------------------------------------------ signature tree, 1 in = 10 ft
TVB = (-40.0, 0.0, 50.0, 45.0)
tb = site_base('l11t')
tb += zones_svg('l11t')
tb += house_svg('l11t')
# dripline protection fence (Design Book IV.11), tick marks outward
cx, cz, r = SIG['x'], SIG['z'], SIG['r']
fence = Point(cx, cz).buffer(r, quad_segs=32).difference(STRUCT.buffer(1.5))
tb += P_(ld(fence.exterior if fence.geom_type == 'Polygon' else fence), stroke=INK, w=.9, op=.9, dash='1.2 1.1')
ticks = ''
for k in range(0, 360, 12):
    a = math.radians(k)
    x0, z0 = cx + math.cos(a) * r, cz + math.sin(a) * r
    if STRUCT.buffer(2).contains(Point(x0, z0)):
        continue
    ticks += f'M{f2(x0)} {f2(z0)} L{f2(cx + math.cos(a) * (r + 1.1))} {f2(cz + math.sin(a) * (r + 1.1))}'
tb += P_(ticks, stroke=INK, w=.6, op=.7)
tb += trees_svg('l11t', True)
# limb clearance ring: no limbs within 5 ft of the roof (drawn as the overhang to prune)
over = Point(cx, cz).buffer(r, quad_segs=32).intersection(STRUCT.buffer(5, quad_segs=24))
tb += P_(pd(over), fill=ACC, extra=' fill-opacity=".16"')
tb += P_(pd(over), stroke=ACC, w=.8, op=.9)
# trunk to wall dimension
from shapely.ops import nearest_points
wp = nearest_points(FOOT.boundary, Point(cx, cz))[0]
tb += P_(f'M{f2(cx)} {f2(cz)} L{f2(wp.x)} {f2(wp.y)}', stroke=INK, w=.6, op=.85, dash='1 1')
tb += P_(ld(FOOT.boundary.intersection(box(*TVB[:2], TVB[0] + TVB[2], TVB[1] + TVB[3]))), stroke=INK, w=.5, op=.55, dash='3 1.5')
TREE_SVG = svg_wrap(TVB, tb, 'l11t')
mx, mz = (cx + wp.x) / 2, (cz + wp.y) / 2
tree_labels = [
    dict(p=frac(TVB, cx - 1.5, cz + 3.4), t='T1', s='signature tree', k='tt hot'),
    dict(p=frac(TVB, mx + 1.5, mz - 1.8), t=f"about {SIG['wall']:.0f} ft", k='dim'),
    dict(p=frac(TVB, -38.5, 34.0), t='Dripline fence', s='4 ft, Design Book IV.11', k='sm', a='l'),
]

# ------------------------------------------------------------------ zones in section, 1 in = 8 ft, a diagram
SVB = (-6.0, -30.0, 108.8, 33.0)     # x feet from the roof edge (0), y feet, up negative; 1 in = 12 ft
def sect():
    b = ''
    g = 0.0
    # ground: a gentle fall away from the house
    gy = lambda x: 0.03 * max(x, 0)
    pts = [(x, gy(x)) for x in range(-6, 104, 2)]
    b += P_('M' + ' L'.join(f'{f2(x)} {f2(y)}' for x, y in pts), stroke=INK, w=1.1)
    # earth hatch
    eh = ''.join(f'M{x} {f2(gy(x) + .1)} l-1.6 2.2' for x in range(-4, 104, 2))
    b += P_(eh, stroke=INK, w=.4, op=.35)
    # the house: wall, glass line, roof eave overhang
    b += P_('M-6 -11.5 L1.2 -12.4', stroke=INK, w=1.2)                          # roof, eave at 0
    b += P_('M-2.6 0 V-11.8', stroke=INK, w=1.0)                                 # wall
    b += P_('M-6 -11.2 H-2.6', stroke=INK, w=.4, op=.5)
    b += P_('M-6 0 H-2.6 V-11.8 H-6 Z', fill=INK, extra=' fill-opacity=".05"')
    # zone bands on the ground
    b += P_(f'M0 {f2(gy(0))} L5 {f2(gy(5))} L5 {f2(gy(5) + 1.1)} L0 {f2(gy(0) + 1.1)} Z', fill='url(#l11s-z0)')
    # gravel dots on grade in zone 0
    rnd = random.Random(3)
    b += ''.join(f'<circle cx="{rnd.uniform(.2, 4.8):.2f}" cy="{rnd.uniform(-.35, -.05):.2f}" r=".16" fill="{INK}" fill-opacity=".55"/>' for _ in range(26))
    # zone ticks and hairlines up the section
    for x in (0, 5, 30, 100):
        b += P_(f'M{x} {f2(gy(x) + 1.6)} V-29', stroke=INK, w=.5, op=.35, dash='1.5 1.5')
    # zone 1: a limbed pine, 6 ft clear, and spaced low shrubs
    def pine(x, h_clear, top=-34, spread=6.5, lean=0):
        s = P_(f'M{x} {f2(gy(x))} L{x + lean} {top}', stroke=INK, w=1.2)
        tiers = ''
        y = -h_clear
        k = 0
        while y > top:
            w_ = spread * (1 - (y + h_clear) / (top + h_clear) * .55)
            tiers += f'M{f2(x - w_)} {f2(y + .8)} Q{f2(x - w_ * .35)} {f2(y - 1.3)} {x} {f2(y - 2.2)} Q{f2(x + w_ * .35)} {f2(y - 1.3)} {f2(x + w_)} {f2(y + .8)}'
            y -= 2.6; k += 1
        s += P_(tiers, stroke=INK, w=.6, op=.75)
        return s
    def shrub(x, h, w_):
        y0 = gy(x)
        return P_(f'M{f2(x - w_ / 2)} {f2(y0)} Q{f2(x - w_ / 2)} {f2(y0 - h)} {x} {f2(y0 - h)} Q{f2(x + w_ / 2)} {f2(y0 - h)} {f2(x + w_ / 2)} {f2(y0)}', stroke=INK, w=.7, op=.8, fill=INK, extra=' fill-opacity=".05"')
    b += pine(20, 6.0)
    b += shrub(10, 2.0, 3.0) + shrub(16.2, 2.0, 3.0) + shrub(27, 1.6, 2.4)
    # vertical spacing: 3 times the shrub height below the limbs (shown at the 16 ft shrub under the pine)
    # horizontal spacing arrow between shrubs: 2 times shrub height
    b += P_(f'M11.5 {f2(gy(11) - 2.6)} H14.7', stroke=ACC, w=.8)
    b += P_(f'M20 {f2(gy(20))} V-6', stroke=ACC, w=.8)
    b += P_(f'M18.8 -6 H21.2', stroke=ACC, w=.8)
    # zone 2: pines with 10 ft canopy gaps, grass 4 in, mosaic shrubs
    b += pine(52, 6.0, spread=5.5) + pine(73, 6.0, spread=5.5) + pine(93, 6.0, spread=5.5)
    b += P_(f'M57.5 -9 H67.5', stroke=ACC, w=.8)
    for x in (57.5, 67.5):
        b += P_(f'M{x} -9.8 V-8.2', stroke=ACC, w=.8)
    b += shrub(40, 2.4, 4) + shrub(47, 1.8, 3) + shrub(63, 2.2, 3.6) + shrub(84, 2.0, 3.2)
    grass = ''.join(f'M{x} {f2(gy(x))} l.2 -.5 M{x + .5} {f2(gy(x + .5))} l-.15 -.45' for x in range(31, 102, 2))
    b += P_(grass, stroke=INK, w=.5, op=.55)
    return b

SECT_SVG = svg_wrap(SVB, sect(), 'l11s')
sect_labels = [
    dict(p=frac(SVB, 2.5, -27.2), t='Zone 0', s='0 to 5 ft', k='zs'),
    dict(p=frac(SVB, 17.5, -27.2), t='Zone 1', s='5 to 30 ft', k='zs'),
    dict(p=frac(SVB, 65.0, -27.2), t='Zone 2', s='30 to 100 ft or the lot line', k='zs'),
    dict(p=frac(SVB, 13.1, -4.6), t='2 × height', k='dim'),
    dict(p=frac(SVB, 22.0, -3.3), t='6 ft clear', s='3 × shrub height', k='dim', a='l'),
    dict(p=frac(SVB, 62.5, -10.9), t='10 ft between crowns', k='dim'),
    dict(p=frac(SVB, 2.5, 1.9), t='gravel', k='dim'),
    dict(p=frac(SVB, 83.0, 1.9), t='grass cut to 4 in', k='dim'),
    dict(p=frac(SVB, -3.6, -14.6), t='roof edge', k='dim'),
]

G = dict(
    plan=dict(vb=PVB, svg=PLAN_SVG, labels=plan_labels),
    tree=dict(vb=TVB, svg=TREE_SVG, labels=tree_labels),
    sect=dict(vb=SVB, svg=SECT_SVG, labels=sect_labels),
    ray=[round(v, 3) for v in RAY],
    areas=AREAS, slope=dict(z1=SL1, z2=SL2),
    sig=dict(r=SIG['r'], wall=SIG['wall'], roof=SIG['roof'], chim=SIG['chim']),
    trees=[dict(n=t['n'], zone=t['zone'], r=t['r'], roof=t['roof'], act=t['act']) for t in TREES],
    north=round(bd.NORTH_DEG, 1),
)

tmpl = (HERE / 'l11_sheet.js').read_text()
out = ('/* land-b crew · L1.1 Defensible space and planting. GENERATED by sheets/tools/land-b/build_l11.py from\n'
       '   sheets/tools/land-b/A1.2.svg (a copy of draw/A1.2.svg) and l11_sheet.js. Edit those, then rebuild. */\n'
       '(function () {\nconst G = ' + json.dumps(G, ensure_ascii=False, separators=(',', ':')) + ';\n' + tmpl + '\n})();\n')
(SET / 'sheets' / 'land-b.js').write_text(out)
print('trees', [(t['n'], t['zone'], t['r'], t['roof'], t['act']) for t in TREES])
print('areas', AREAS, 'slope', SL1, SL2, 'sig', G['sig'], 'bytes', len(out))
