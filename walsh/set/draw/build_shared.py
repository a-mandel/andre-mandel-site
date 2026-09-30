#!/usr/bin/env python3
"""Walsh living set: one shared data module every crew reads (SHARED.md explains the schema).

Everything is derived from the pocket model (walsh/index.html, model-data), the drawing registration in
draw/drawings.js and draw/render_meta.json, and the crews' own built data, so plans, ceilings, sections,
elevations and schedules agree:
  plans-b  (sheets/tools/plans-b/build_rcp.py)   ceiling heights, sampled with its own method and meshes
  reg-a    (sheets/reg-a.js, reg-a.src.js)         height spots, chimneys, the A1.3 matrix rows
  sched-a  (sheets/tools/sched-a/build.py, template) door tags and anchors
  sched-b  (sheets/sched-b.js, tools/sched-b/*.json) wall planes W1 to W17, window panes and types
Room programming is André's brief of 9/30/26, placeholders at FA accuracy.

Writes draw/shared.json and draw/shared.js (window.SHARED, plus small helpers). Nothing else is touched.
Run from anywhere:  python3 walsh/set/draw/build_shared.py
"""
import collections, importlib.util, json, math, re, sys
sys.dont_write_bytecode = True           # importing the plans-b sampler leaves nothing in its folder
from pathlib import Path

import numpy as np
from shapely.geometry import Polygon, box, LineString, Point
from shapely.ops import unary_union

HERE = Path(__file__).resolve().parent            # walsh/set/draw
SET = HERE.parent                                 # walsh/set
ROOT = SET.parents[1]                             # repo root
MODEL = ROOT / 'walsh' / 'index.html'
TOOLS = SET / 'sheets' / 'tools'
DATUM = 5990.0                                    # model y 0 = elevation 5990.0
BL, TOP = 1.25, 0.5                               # v2.html: FX = x - 1.25, FY = y - 0.5 (sheet to field inches)

# ------------------------------------------------------------------ inputs
def load_model():
    for line in MODEL.read_text().splitlines():
        if 'id="model-data"' in line:
            return json.loads(re.sub(r'^<script[^>]*>', '', line).rsplit('</script>', 1)[0])
    raise SystemExit('model data not found')

def json_after(text, marker):
    i = text.index(marker) + len(marker)
    while text[i] in ' \n=': i += 1
    return json.JSONDecoder().raw_decode(text[i:])[0]

D = load_model()
P = D['plans']
L1, L2 = P['levels']['rib']['l1'], P['levels']['rib']['l2']
ROOF = P['roof']['rib']
INFO = D['info']['rib']
A = D['A']
DRW = json_after((HERE / 'drawings.js').read_text(), 'window.DRAWINGS')
META = json.loads((HERE / 'render_meta.json').read_text())
CALCS = json.loads((HERE / 'calcs.json').read_text())

def nums(s):
    return [float(v) for v in re.findall(r'-?\d+(?:\.\d+)?', s)]

def subpaths(d):
    out = []
    for sp in re.split(r'(?=M)', d):
        n = nums(sp)
        if len(n) >= 4:
            out.append(list(zip(n[0::2], n[1::2])))
    return out

def dedupe(pts, tol=0.03):
    out = []
    for p in pts:
        if not out or abs(p[0] - out[-1][0]) > tol or abs(p[1] - out[-1][1]) > tol:
            out.append(p)
    if len(out) > 2 and abs(out[0][0] - out[-1][0]) <= tol and abs(out[0][1] - out[-1][1]) <= tol:
        out.pop()
    return out

def poly(pts):
    return Polygon(dedupe(pts)).buffer(0)

def r2(v): return round(float(v), 2)
def pt2(p): return [r2(p[0]), r2(p[1])]

def ftin(v):
    f = int(math.floor(v + 1e-6)); i = round((v - f) * 12)
    if i == 12: f += 1; i = 0
    return f"{f}′ {i}″"

def about_sf(a):
    return int(round(a / 5.0) * 5)

# terrain: the same bilinear 3 ft grid as build_drawings.py and reg-a
TX0, TZ0, TS = -125.0, -44.0, 3.0
_G = {}
T = D['site']['terrain']
for i in range(0, len(T), 3):
    _G[(round((T[i] - TX0) / TS), round((T[i + 2] - TZ0) / TS))] = T[i + 1]
NX = max(k[0] for k in _G); NZ = max(k[1] for k in _G)

def ground(x, z):
    fx = min(max((x - TX0) / TS, 0), NX - 1e-6); fz = min(max((z - TZ0) / TS, 0), NZ - 1e-6)
    i, j = int(fx), int(fz); u, v = fx - i, fz - j
    g = lambda a, b: _G.get((a, b), _G.get((i, j)))
    return g(i, j) * (1 - u) * (1 - v) + g(i + 1, j) * u * (1 - v) + g(i, j + 1) * (1 - u) * v + g(i + 1, j + 1) * u * v

# ------------------------------------------------------------------ 1. coords
FIELD = dict(w=31.25, h=23.0, sheet_to_field=[-BL, -TOP])

def svg_vb(svg):
    return [float(v) for v in re.search(r'viewBox="([^"]+)"', svg).group(1).split()]

def plan_reg(view, vb, src):
    """a plan view box (sheet inches) holding an svg in model feet, preserveAspectRatio meet: fx = a x + b, fy = a z + c"""
    s = min(view['w'] / vb[2], view['h'] / vb[3])
    ox = view['x'] - BL + (view['w'] - vb[2] * s) / 2
    oy = view['y'] - TOP + (view['h'] - vb[3] * s) / 2
    return dict(kind='plan', src=src, scale=round(s, 6), fx=[round(s, 6), round(ox - vb[0] * s, 5)], fy=[round(s, 6), round(oy - vb[1] * s, 5)],
                vb=vb, view=[round(view['x'], 4), round(view['y'], 4), round(view['w'], 4), round(view['h'], 4)])

COORDS = {}
for sid in ('A1.2', 'A2.1', 'A2.2', 'A2.3'):
    v = DRW['sheets'][sid]['views'][0]
    COORDS[sid] = plan_reg(v, svg_vb(v['svg']), 'draw/drawings.js')
COORDS['A1.2']['note'] = 'Site plan, 1 in = 10 ft'
for sid in ('A2.1', 'A2.2', 'A2.3'):
    COORDS[sid]['note'] = 'Plans, 3/16 in = 1 ft, one registration'
pa = (SET / 'sheets' / 'plans-a.js').read_text()
PA = json_after(pa, 'const PA')
for v in PA['A2.0']['views']:
    if v['id'] == 'fd':
        COORDS['A2.0'] = dict(plan_reg(v, svg_vb(v['svg']), 'sheets/plans-a.js'), note='A2.0, same registration as A2.1')
for v in PA['A0.6']['views']:
    if v['id'] == 'l1':
        COORDS['A0.6'] = dict(plan_reg(v, svg_vb(v['svg']), 'sheets/plans-a.js'), note='Area diagram, level 1 view only, 1/8 in = 1 ft')
PB_TXT = (SET / 'sheets' / 'plans-b.js').read_text()
PB = json_after(PB_TXT, 'const PB')
for sid in ('A2.4', 'A2.5'):
    COORDS[sid] = dict(plan_reg(PB['view'], svg_vb(PB['sheets'][sid]['svg']), 'sheets/plans-b.js'), note='Reflected ceiling plan, same registration as A2.1')

VIEW = {'N': ((0, 0, 1), (-1, 0, 0)), 'S': ((0, 0, -1), (1, 0, 0)), 'E': ((-1, 0, 0), (0, 0, -1)), 'W': ((1, 0, 0), (0, 0, 1))}
ELEV = [('A4.0', 'N', 'North elevation', 3 / 16), ('A4.1', 'E', 'East elevation', 1 / 4), ('A4.2', 'S', 'South elevation', 3 / 16), ('A4.3', 'W', 'West elevation', 1 / 4)]
SECT = [('A3.0-2', 'A3.0', 0, 'S', 'Section 2, looking north', dict(axis='z', at=-2.0, keep=-1)),
        ('A3.0-1', 'A3.0', 1, 'W', 'Section 1, looking east', dict(axis='x', at=8.0, keep=1))]

def view_reg(name, sheet, idx, vname, title, scale, cut=None):
    m = META[name]; v = DRW['sheets'][sheet]['views'][idx]
    assert v['img'].endswith(name + '.webp'), (name, v['img'])
    r = VIEW[vname][1]
    ox, oy = v['x'] - BL, v['y'] - TOP
    out = dict(kind='ortho', sheet=sheet, img=v['img'], title=title, view=vname, scale=scale,
               right=[r[0], r[2]], h0=m['h0'], h1=m['h1'], y0=m['y0'], y1=m['y1'],
               fx=[scale, round(ox - m['h0'] * scale, 5)], fy=[-scale, round(oy + m['y1'] * scale, 5)],
               img_field=[round(ox, 4), round(oy, 4), round(v['iw'], 4), round(v['ih'], 4)])
    if cut: out['cut'] = cut
    return out

VIEWS = {}
for sid, vn, t, sc in ELEV:
    VIEWS[sid] = view_reg(sid, sid, 0, vn, t, sc)
for name, sid, idx, vn, t, cut in SECT:
    VIEWS[name] = view_reg(name, sid, idx, vn, t, 3 / 16, cut)

def to_plan(sheet, x, z):
    c = COORDS[sheet]
    return [round(c['fx'][0] * x + c['fx'][1], 4), round(c['fy'][0] * z + c['fy'][1], 4)]

def to_view(name, x, el, z):
    v = VIEWS[name]
    h = x * v['right'][0] + z * v['right'][1]
    return [round(v['fx'][0] * h + v['fx'][1], 4), round(v['fy'][0] * (el - DATUM) + v['fy'][1], 4)]

# ------------------------------------------------------------------ 2. grids
bp = subpaths(ROOF['beam'])
def mid(p, q): return ((p[0] + q[0]) / 2, (p[1] + q[1]) / 2)
BEAMS = {  # centerlines, as plans-b reads them
    'FB': (mid(bp[0][0], bp[0][3]), mid(bp[0][1], bp[0][2]), INFO['beam'], 'Fold beam, north wing ribbon'),
    'BB': (mid(bp[1][0], bp[1][3]), mid(bp[1][1], bp[1][2]), INFO['bBeam'], 'Bridge beam, west wall'),
    'GB': (mid(bp[2][0], bp[2][3]), mid(bp[2][1], bp[2][2]), D['info']['granny']['beam'], 'Granny suite beam, south face'),
    'SB': (mid(bp[3][0], bp[3][1]), mid(bp[3][2], bp[3][3]), INFO['sBeam'], 'South wing fold beam'),
}

def col_centers(arr):
    t = np.array(arr, dtype=float).reshape(-1, 3)
    cl = []
    for x, y, z in t:
        for c in cl:
            if abs(c[0] - x) < 1.5 and abs(c[1] - z) < 1.5:
                c[2].append((x, y, z)); break
        else:
            cl.append([x, z, [(x, y, z)]])
    out = []
    for _, _, pts in cl:
        a = np.array(pts)
        out.append(dict(x=r2((a[:, 0].min() + a[:, 0].max()) / 2), z=r2((a[:, 2].min() + a[:, 2].max()) / 2),
                        base=round(DATUM + a[:, 1].min(), 1), top=round(DATUM + a[:, 1].max(), 1)))
    return out

POSTS = col_centers(D['wing']['col']) + col_centers(D['rib']['col'])
GAR = subpaths(L1['gar'])[0]
MAINP = subpaths(L1['main'])
FOOT = [poly(p) for p in subpaths(P['foot']['rib'])]
# the north wing from the main level polygon: its east wall, its court line (the vertices east of the link) and its north wall
M0 = dedupe(MAINP[0])
nwx1 = max(p[0] for p in M0)
nwz1 = max(p[1] for p in M0 if p[0] > -20.0)                          # court line
nwx0 = min(p[0] for p in M0 if abs(p[1] - nwz1) < 0.05)               # west wall, where the court line starts
nwz0 = min(p[1] for p in M0)                                            # north wall
LINKZ = min(p[1] for p in M0 if abs(p[0] - nwx0) < 0.05 and p[1] > nwz0 + 1)      # the link's south face
LINKX = min(p[0] for p in M0 if p[0] > min(q[0] for q in M0) + 0.1 and p[0] < nwx0 - 1)   # the porch's west edge
NWING = box(nwx0, nwz0, nwx1, nwz1)
GX0, GX1 = min(p[0] for p in GAR), max(p[0] for p in GAR)
GZ0 = min(p[1] for p in GAR); GZ1 = max(p[1] for p in GAR)
GEARZ1 = max(p[1] for p in GAR if abs(p[0] - GX0) < 0.05)
BRIDGE = poly(MAINP[1])
LOWERP = [poly(p) for p in subpaths(L1['lower'])]
LOWER = max(LOWERP, key=lambda g: g.area)
PRIM = poly(subpaths(L2['prim'])[0])
GRANNY = max((poly(p) for p in MAINP[2:]), key=lambda g: g.area)
gx = sorted({round(p[0], 2) for p in GAR})

# the south wing's skew: its north edge (the court glulam) and south face, from the lower level polygon corners
lx = LOWER.exterior.coords
lw = [p for p in lx if abs(p[0] - LOWER.bounds[0]) < 0.1]; le = [p for p in lx if abs(p[0] - LOWER.bounds[2]) < 0.1]
F_A, G_A = min(lw, key=lambda p: p[1]), max(lw, key=lambda p: p[1])      # west end, north and south corners
F_B, G_B = min(le, key=lambda p: p[1]), max(le, key=lambda p: p[1])      # east end
SKEW = math.atan2(F_B[1] - F_A[1], F_B[0] - F_A[0])
U = (math.cos(SKEW), math.sin(SKEW)); NRM = (-U[1], U[0])

def skew_z(p0, x):
    return p0[1] + (x - p0[0]) * math.tan(SKEW)

wpost = sorted([p for p in POSTS if abs(p['z'] - 7.95) < 0.2], key=lambda p: p['x'])         # north wing court posts
bpost = sorted([p for p in POSTS if abs(p['x'] - 16.02) < 0.2], key=lambda p: p['z'])        # bridge terrace posts
BRX = r2(BRIDGE.bounds[0]); BRX1 = r2(bpost[0]['x'])
NUM = {  # N-S lines, numbered west to east (x = const)
    'garage west wall': gx[0], 'gear bay wall': gx[1], 'garage east wall': r2(max(p[0] for p in GAR)),
    'north wing west wall, granny west wall': r2(nwx0),
    **{f'court post {i + 1}': p['x'] for i, p in enumerate(wpost[:-1])},
    'north wing east wall, corner post': r2(nwx1),
    'bridge beam, west wall': BRX,
    'bridge terrace glulam and posts': BRX1,
    'south wing east face': r2(LOWER.bounds[2]),
}
nums_sorted = sorted(NUM.items(), key=lambda kv: kv[1])
NUMLAB = {name: str(i + 1) for i, (name, _) in enumerate(nums_sorted)}
LETTERS = 'ABCDEFGHJKLMNPQRSTUVWXYZ'

def nline(name, z0, z1):
    x = NUM[name]
    return dict(id=NUMLAB[name], at=x, what=name, a=[x, r2(z0)], b=[x, r2(z1)])

def zline(lab, z, x0, x1, what):
    return dict(id=lab, at=r2(z), what=what, a=[r2(x0), r2(z)], b=[r2(x1), r2(z)])

def sline(lab, p0, x0, x1, what):
    return dict(id=lab, what=what, a=[r2(x0), r2(skew_z(p0, x0))], b=[r2(x1), r2(skew_z(p0, x1))])

RUN = 4.0   # lines run past the building so the bubbles clear the walls
ZA, ZB, ZC = r2(nwz0), r2(nwz1), r2(GZ1)
LF, LG = LETTERS[3 + len(bpost)], LETTERS[4 + len(bpost)]

GRIDS = [
    dict(id='north', name='North wing, entry and garage', axis_deg=0.0,
         num=[nline(n, min(ZA, GZ0) - RUN, (ZC if 'garage' in n or 'gear' in n else ZB) + RUN) for n in NUM
              if n.startswith(('garage', 'gear', 'north wing', 'court post'))],
         let=[zline('A', ZA, NUM['garage west wall'] - RUN, NUM['north wing east wall, corner post'] + RUN, 'north wall'),
              zline('B', ZB, NUM['north wing west wall, granny west wall'] - RUN, NUM['north wing east wall, corner post'] + RUN, 'court glulam, court posts at 15 ft'),
              zline('C', ZC, NUM['garage west wall'] - RUN, NUM['garage east wall'] + RUN, 'garage front, two doors')]),
    dict(id='bridge', name='Bridge', axis_deg=90.0,
         num=[],
         let=[]),
    dict(id='south', name='South wing', axis_deg=round(math.degrees(SKEW), 2),
         num=[nline('north wing west wall, granny west wall', skew_z(F_A, NUM['north wing west wall, granny west wall']) - RUN, skew_z(G_A, NUM['north wing west wall, granny west wall']) + RUN),
              nline('bridge beam, west wall', skew_z(F_A, BRX) - RUN, skew_z(G_A, BRX) + RUN),
              nline('south wing east face', skew_z(F_A, NUM['south wing east face']) - RUN, skew_z(G_A, NUM['south wing east face']) + RUN)],
         let=[sline(LF, F_A, NUM['north wing west wall, granny west wall'] - RUN, NUM['south wing east face'] + RUN, 'court glulam, north edge'),
              sline(LG, G_A, NUM['north wing west wall, granny west wall'] - RUN, NUM['south wing east face'] + RUN, 'south face')]),
]
# the bridge runs north to south, so its long lines are the lettered ones in its own frame; to keep one label per
# physical line across the house, its long lines keep their numbers and its cross lines take letters
GRIDS[1]['num'] = [nline('bridge beam, west wall', ZB - RUN, skew_z(F_A, BRX) + RUN), nline('bridge terrace glulam and posts', ZB - RUN, skew_z(F_A, BRX1) + RUN)]
GRIDS[1]['let'] = [zline('B', ZB, BRX - RUN, BRX1 + RUN, 'court glulam, north end of the bridge')] + \
    [zline(LETTERS[3 + i], p['z'], BRX - RUN, BRX1 + RUN, f'bridge post row {i + 1}') for i, p in enumerate(bpost)] + \
    [sline(LF, F_A, BRX - RUN, BRX1 + RUN, 'south end, the south wing court glulam')]

def spacing(lines, kind, grid):
    out = []
    if kind == 'num':
        ls = sorted(lines, key=lambda l: l['at'])
        for a, b in zip(ls, ls[1:]):
            d = b['at'] - a['at']
            out.append(dict(a=a['id'], b=b['id'], ft=r2(d), text=ftin(d)))
        if len(ls) > 1:
            d = ls[-1]['at'] - ls[0]['at']
            out.append(dict(a=ls[0]['id'], b=ls[-1]['id'], ft=r2(d), text=ftin(d), overall=True))
        return out
    # lettered: parallel pairs square to the lines; a skewed line against a level one is measured on the wing's centerline
    ls = lines
    cx = (BRX + BRX1) / 2 if grid == 'bridge' else None
    def zat(l, x):
        (x0, z0), (x1, z1) = l['a'], l['b']
        return z0 + (z1 - z0) * (x - x0) / (x1 - x0)
    def dist(a, b):
        da = math.atan2(a['b'][1] - a['a'][1], a['b'][0] - a['a'][0]); db = math.atan2(b['b'][1] - b['a'][1], b['b'][0] - b['a'][0])
        if abs(da - db) < 1e-3:
            return abs(zat(b, a['a'][0]) - a['a'][1]) * math.cos(da), None
        x = cx if cx is not None else (a['a'][0] + a['b'][0]) / 2
        return abs(zat(b, x) - zat(a, x)), f'on the centerline, x {x:.1f}'
    for a, b in zip(ls, ls[1:]):
        d, note = dist(a, b)
        s = dict(a=a['id'], b=b['id'], ft=r2(d), text=ftin(d))
        if note: s['note'] = note
        out.append(s)
    if len(ls) > 1:
        tot = sum(s['ft'] for s in out)
        out.append(dict(a=ls[0]['id'], b=ls[-1]['id'], ft=r2(tot), text=ftin(tot), overall=True))
    return out

for g in GRIDS:
    g['num'].sort(key=lambda l: l['at'])
    g['num_spacing'] = spacing(g['num'], 'num', g['id'])
    g['let_spacing'] = spacing(g['let'], 'let', g['id'])
REFS = [dict(id=k, what=w, a=pt2(a), b=pt2(b), el=el) for k, (a, b, el, w) in BEAMS.items()]
tg = sorted([p for p in POSTS if p['base'] < 5993 and p['x'] > 29], key=lambda p: p['z'])
REFS.append(dict(id='TG', what='Terrace glulam, south wing east posts', a=[tg[0]['x'], tg[0]['z']], b=[tg[-1]['x'], tg[-1]['z']], el=None))
GRID_NOTE = ('Walls on their outside face (the footprint), glulams and posts on their centerline, from the model. '
             'Numbers are N to S lines, one label per physical line across the house, west to east; letters run E to W, north to south. '
             'Beams off the grid are reference lines.')

# ------------------------------------------------------------------ 3. rooms
sys.path.insert(0, str(TOOLS / 'plans-b'))
_argv = sys.argv; sys.argv = [_argv[0]]
spec = importlib.util.spec_from_file_location('build_rcp', TOOLS / 'plans-b' / 'build_rcp.py')
RCP = importlib.util.module_from_spec(spec); spec.loader.exec_module(RCP)
sys.argv = _argv
FB_A, FB_B = BEAMS['FB'][0], BEAMS['FB'][1]

def half(a, b, side_pt, far=400):
    """the half plane on side_pt's side of the line a b, as a big polygon"""
    L = math.hypot(b[0] - a[0], b[1] - a[1]); ux, uz = (b[0] - a[0]) / L, (b[1] - a[1]) / L
    nx, nz = -uz, ux
    if (side_pt[0] - a[0]) * nx + (side_pt[1] - a[1]) * nz < 0: nx, nz = -nx, -nz
    p0 = (a[0] - ux * far, a[1] - uz * far); p1 = (a[0] + ux * far, a[1] + uz * far)
    return Polygon([p0, p1, (p1[0] + nx * far, p1[1] + nz * far), (p0[0] + nx * far, p0[1] + nz * far)])

def para(s0, s1, t0, t1, A_=F_A, B_=F_B, D_=G_A):
    """a piece of the south wing parallelogram in its own frame: s along the skew, t across (0 north, 1 south)"""
    e1 = (B_[0] - A_[0], B_[1] - A_[1]); e2 = (D_[0] - A_[0], D_[1] - A_[1])
    q = lambda s, t: (A_[0] + e1[0] * s + e2[0] * t, A_[1] + e1[1] * s + e2[1] * t)
    return Polygon([q(s0, t0), q(s1, t0), q(s1, t1), q(s0, t1)])

north_of_fb = half(FB_A, FB_B, (0, -14))
CHIM_N = Polygon([(p[0], p[1]) for p in json.loads((TOOLS / 'sectelev-b' / 'plan_data.json').read_text())['chim']['p']]) \
    if (TOOLS / 'sectelev-b' / 'plan_data.json').exists() else Point(20.8, -11.4).buffer(3.0)
cx0, cz0, cx1, cz1 = CHIM_N.bounds
LINK = poly(MAINP[0]).intersection(box(GX1, nwz0, nwx0, LINKZ))
outl = dedupe(subpaths(ROOF['outline'])[0], 0.3)
porch_z1 = max(p[1] for p in outl if LINKX < p[0] < nwx0 and abs(p[1] - nwz1) < 1.0)      # the roof edge over the porch
PB_FURN = json.loads((TOOLS / 'sectelev-b' / 'plan_data.json').read_text())['furn']
tall = max(PB_FURN, key=lambda f: f['y'][1] - f['y'][0])                  # the tall block the model carries: fridge and pantry
PANTRY = box(nwx0, nwz0, max(p[0] for p in tall['p']), max(p[1] for p in tall['p']))
POWDER = box(cx1 + 0.2, nwz0, cx1 + 6.2, nwz0 + 5.6)
KITCHEN = NWING.intersection(box(nwx0, nwz0, BRX1, nwz1)).intersection(north_of_fb).union(
    NWING.intersection(box(nwx0, nwz0, BRX, nwz1))).difference(PANTRY)
LIVING = NWING.difference(KITCHEN).difference(PANTRY).difference(POWDER)
bz0 = ZB; bzs = skew_z(F_A, BRX)
STAIR = BRIDGE.intersection(box(BRX, 30.5, BRX + 4.0, 50))
BAR = box(BRX + 4.6, 33.0, BRX + 6.6, 40.0)
NOOK = BRIDGE.intersection(box(BRX1 - 6.0, bz0, BRX1, bz0 + 7.0))
DINING = BRIDGE.intersection(box(BRX, bpost[0]['z'] - 1.5, BRX1, bpost[-1]['z'] + 1.5)).difference(NOOK).difference(STAIR).difference(BAR)
VEST = max((poly(p) for p in MAINP[2:]), key=lambda g: g.intersection(box(-5.5, 34, 0, 49)).area).intersection(box(-5.5, 34, BRX, 49))
TERR = {t['k']: poly(subpaths(t['d'])[0]) for t in P['terrace']}
DECK2 = poly(subpaths(L2['deck'])[0])
pit_c = D['xt']['anchors']['pit']
PIT = Point(pit_c[0], pit_c[2]).buffer(3.0)
bench = D['xt']['bench']
bpts = np.array(bench, dtype=float).reshape(-1, 3)
BENCH = Polygon([(x, z) for x, _, z in bpts]).convex_hull
FIRE = unary_union([PIT, BENCH]).convex_hull
t_split = 0.5
GAR_P = box(gx[1], nwz0, GX1, GZ1)
GEAR = box(GX0, GZ0, gx[1], GEARZ1)
ENTRY_X = (GX1 + nwx0) / 2                         # placeholder split of the link: mudroom by the garage, entry by the wing
FF = dict(lower=5992.5, main=5997.5, garage=6000.0, primary=6004.0)
MN, MG, MS = RCP.MESH_NORTH, RCP.MESH_GB, RCP.MESH_SOUTH

def clg_range(g, floor, mesh=None, fixed=None):
    if fixed is not None:
        return [round(fixed - floor, 2), round(fixed - floor, 2)], [round(fixed, 1), round(fixed, 1)]
    polys = [g] if g.geom_type == 'Polygon' else list(g.geoms)
    vals = []
    for pg in polys:
        pts = [tuple(c) for c in pg.exterior.coords]
        for inset in (1.0, 0.5):
            v = RCP.sample(pts, floor, 1.0, inset, lambda x, z: RCP.ceiling(x, z, mesh))
            if v: vals += v; break
    if not vals: return None, None
    lo, hi = min(vals), max(vals)
    return [round(lo[0], 2), round(hi[0], 2)], [round(lo[3], 1), round(hi[3], 1)]

LOW_CLG = RCP.SLAB_UNDER
GEAR_CLG = RCP.roof_top(-70, -4) - 1.25
ROOMS_SPEC = [
    # id, name, level key, geometry, wing, ceiling source, placeholder, note
    ('living', 'Living room', 'main', LIVING, 'north', dict(mesh=MN), True, 'Double height under the ribbon, the lifted tip and the fireplace'),
    ('kitchen', 'Kitchen', 'main', KITCHEN, 'north', dict(mesh=MN), True, 'Island on the dining axis, back wall angled with the fold beam'),
    ('pantry', 'Pantry', 'main', PANTRY, 'north', dict(mesh=MN), True, 'Northwest corner of the north wing'),
    ('powder', 'Powder room', 'main', POWDER, 'north', dict(mesh=MN), True, 'Behind the fireplace, northeast corner'),
    ('entry', 'Entry', 'main', LINK.intersection(box(ENTRY_X, nwz0, nwx0, LINKZ)), 'north', dict(mesh=MG), True, 'Off the porch, between the garage and the north wing'),
    ('mudroom', 'Mudroom and family entry', 'main', LINK.intersection(box(GX1, nwz0, ENTRY_X, LINKZ)), 'north', dict(mesh=MG), True, 'From the garage'),
    ('porch', 'Porch', 'main', box(LINKX, LINKZ, nwx0, porch_z1), 'north', dict(mesh=MG), False, 'Exterior, under the entry roof'),
    ('garage', 'Garage', 'garage', GAR_P, 'north', dict(mesh=MG), False, 'Two garage doors'),
    ('gear', 'Gear bay', 'garage', GEAR, 'north', dict(fixed=GEAR_CLG), False, 'Flat ceiling'),
    ('dining', 'Dining', 'main', DINING, 'bridge', dict(mesh=MG), True, 'The middle of the bridge'),
    ('stair', 'Main stair', 'main', STAIR, 'bridge', dict(mesh=MG), True, 'Up to level 2, inside the bridge'),
    ('bar', 'Bar', 'main', BAR, 'bridge', dict(mesh=MG), True, 'Faces east, just east of the stair'),
    ('nook', 'Breakfast nook', 'main', NOOK, 'bridge', dict(mesh=MG), True, 'Bridge northeast corner'),
    ('vestibule', 'Vestibule', 'main', VEST, 'bridge', dict(mesh=MG), True, 'Not in the 9/30 program; door 101 on the door schedule opens here'),
    ('granny', 'Granny suite', 'main', GRANNY, 'south', dict(mesh=MS), False, 'South center, main level'),
    ('flex', 'Flex room', 'lower', LOWER.intersection(para(0.34, 1.0, 0.0, t_split)), 'south', dict(fixed=LOW_CLG), True, 'Opens to the lower patio'),
    ('bunk', 'Bunk and game room', 'lower', LOWER.intersection(para(0.34, 1.0, t_split, 1.0)), 'south', dict(fixed=LOW_CLG), True, 'East views'),
    ('bunk_bath', 'Bunk bath', 'lower', LOWER.intersection(para(0.0, 0.34, 0.62, 1.0)), 'south', dict(fixed=LOW_CLG), True, 'Pulled toward the core'),
    ('gym', 'Gym', 'lower', LOWER.intersection(para(0.0, 0.34, 0.0, 0.62)), 'south', dict(fixed=LOW_CLG), True, 'By the stair'),
    ('primary', 'Primary suite', 'primary', PRIM, 'south', dict(mesh=MS), False, 'Over the lower level'),
    ('primary_terrace', 'Primary terrace', 'primary', DECK2, 'south', None, False, 'Cedar deck to the east'),
    ('upper_terrace', 'Upper terrace', 'terrace', TERR['deck'], 'court', None, False, 'Cedar deck off the living room'),
    ('lower_patio', 'Lower patio', 'patio', TERR['stone'], 'court', None, False, 'Stone'),
    ('fire_pit', 'Fire pit', 'terrace', FIRE, 'court', None, True, 'Semicircular bench'),
]
LEVEL_EL = dict(main=5997.5, lower=5992.5, garage=6000.0, primary=6004.0, terrace=D['xt']['levels'][0], patio=D['xt']['levels'][1])

def label_point(g):
    c = g.centroid
    return c if g.contains(c) else g.representative_point()

ROOMS = []
for rid, name, lev, g, wing, cs, ph, note in ROOMS_SPEC:
    g = g.buffer(0)
    if g.geom_type == 'MultiPolygon':
        g = max(g.geoms, key=lambda q: q.area)
    g = g.simplify(0.05)
    lp = label_point(g)
    r = dict(id=rid, name=name, level=lev, ff=LEVEL_EL[lev], wing=wing, label=pt2((lp.x, lp.y)),
             poly=[pt2(p) for p in list(g.exterior.coords)[:-1]], sf_about=about_sf(g.area), placeholder=ph, note=note)
    if cs:
        h, el = clg_range(g, LEVEL_EL[lev], **cs)
        if h:
            r['ceiling_ft'] = h; r['ceiling_el'] = el
            r['ceiling_text'] = f'about {ftin(h[0])}' if abs(h[1] - h[0]) < 0.05 else f'about {ftin(h[0])} to {ftin(h[1])}'
    ROOMS.append(r)

# ------------------------------------------------------------------ 4. dims
PLAN_SHEETS = {'main': ['A2.0', 'A2.1', 'A2.4'], 'primary': ['A2.2', 'A2.5'], 'roof': ['A2.3']}
DIMS = []

def dim(did, level, e0, e1, off, text=None, note=None):
    """a dimension string: e0 e1 are the measured points (model feet), off the offset vector to the string line"""
    L = math.hypot(e1[0] - e0[0], e1[1] - e0[1])
    s0 = (e0[0] + off[0], e0[1] + off[1]); s1 = (e1[0] + off[0], e1[1] + off[1])
    d = dict(id=did, sheets=PLAN_SHEETS[level], e=[pt2(e0), pt2(e1)], s=[pt2(s0), pt2(s1)], ft=r2(L), text=text or ftin(L))
    if note: d['note'] = note
    DIMS.append(d)

allx = [p[0] for g in FOOT for p in g.exterior.coords] + [p[0] for p in DECK2.exterior.coords]
allz = [p[1] for g in FOOT for p in g.exterior.coords]
X0, X1, Z0, Z1 = min(allx), max(allx), min(allz), max(allz)
dim('overall_ew', 'main', (X0, Z0), (X1, Z0), (0, -9.0), ftin(D['info']['overall']['w']), 'Overall, the garage to the primary terrace edge')
dim('overall_ns', 'main', (X0, Z0), (X0, Z1), (-6.0, 0), ftin(D['info']['overall']['d']), 'Overall, north wall to the granny suite south corner')
dim('north_wing_len', 'main', (nwx0, ZA), (nwx1, ZA), (0, -4.84), ftin(D['info']['wing']['len']), 'Matches the A2.1 string')
dim('north_wing_depth', 'main', (nwx1, ZA), (nwx1, ZB), (5.5, 0), ftin(D['info']['wing']['depth']))
dim('garage_w', 'main', (NUM['gear bay wall'], ZC), (NUM['garage east wall'], ZC), (0, 4.5))
dim('garage_d', 'main', (NUM['garage west wall'], GZ0), (NUM['garage west wall'], GEARZ1), (-4.0, 0), note='Gear bay')
dim('bridge_w', 'main', (BRX, 12.0), (BRIDGE.bounds[2], 12.0), (0, 0), note='Bridge about 16 ft in the model, the brief says about 20 ft')
dim('bridge_len_w', 'main', (BRX, ZB), (BRX, skew_z(F_A, BRX)), (-3.0, 0), note='West wall, court glulam to the south wing')
SO = (NRM[0] * 5.0, NRM[1] * 5.0) if NRM[1] > 0 else (-NRM[0] * 5.0, -NRM[1] * 5.0)          # 5 ft outside the south face
SN = (SO[0] / 5.0, SO[1] / 5.0)
dim('south_w', 'main', G_A, G_B, SO, note='South wing lower level and primary suite, along the skew')
gw0 = (NUM['north wing west wall, granny west wall'], skew_z(G_A, NUM['north wing west wall, granny west wall']))
dim('granny_w', 'main', gw0, (BRX, skew_z(G_A, BRX)), SO, note='Granny suite, along the skew')
sd = abs((G_A[0] - F_A[0]) * NRM[0] + (G_A[1] - F_A[1]) * NRM[1])
e0 = (NUM['south wing east face'] + 3.0, skew_z(F_A, NUM['south wing east face'] + 3.0))
dim('south_depth', 'main', e0, (e0[0] + SN[0] * sd, e0[1] + SN[1] * sd), (U[0] * 4.0, U[1] * 4.0), note='Square to the south wing')
dim('primary_w', 'primary', G_A, G_B, SO, note='Primary suite along the skew')
dim('primary_terrace', 'primary', (DECK2.bounds[0], 50.0), (DECK2.bounds[2], 50.0), (0, 0), note='Deck depth at the middle')
# grid to grid strings, chained, from the grids
for g in GRIDS:
    nl = g['num']
    for a, b in zip(nl, nl[1:]):
        if g['id'] == 'north':
            dim(f"grid_{g['id']}_{a['id']}_{b['id']}", 'main', (a['at'], ZA), (b['at'], ZA), (0, -7.2), note='Grid to grid')
        elif g['id'] == 'bridge':
            dim(f"grid_{g['id']}_{a['id']}_{b['id']}", 'main', (a['at'], 22.0), (b['at'], 22.0), (0, 0), note='Grid to grid')
        else:
            za, zb = skew_z(G_A, a['at']), skew_z(G_A, b['at'])
            dim(f"grid_{g['id']}_{a['id']}_{b['id']}", 'main', (a['at'], za), (b['at'], zb), (0, 9.0), note='Grid to grid, measured in x')
for sp in GRIDS[1]['let_spacing']:
    if sp.get('overall'): continue
    la = next(l for l in GRIDS[1]['let'] if l['id'] == sp['a']); lb = next(l for l in GRIDS[1]['let'] if l['id'] == sp['b'])
    xa = BRX1 + 3.5
    za = la['a'][1] if la['a'][1] == la['b'][1] else skew_z(F_A, (BRX + BRX1) / 2)
    zb = lb['a'][1] if lb['a'][1] == lb['b'][1] else skew_z(F_A, (BRX + BRX1) / 2)
    dim(f"grid_bridge_{sp['a']}_{sp['b']}", 'main', (xa, za), (xa, zb), (0, 0), sp['text'], 'Grid to grid')

# ------------------------------------------------------------------ 5. levels
PB_L = {l['t']: l for s in PB['sheets'].values() for l in s['labels'] if isinstance(l.get('t'), str)}
plate_s = next(float(re.findall(r'\d{4}\.\d', t)[0]) for t in PB_L if t.startswith('Plate') and '6004' not in t and float(re.findall(r'\d{4}\.\d', t)[0]) > 6007)
plate_n = next(float(re.findall(r'\d{4}\.\d', t)[0]) for t in PB_L if t.startswith('Plate') and float(re.findall(r'\d{4}\.\d', t)[0]) < 6007)
deck2_y = [y for x, y, z in np.array(D['xt']['deckTop'], dtype=float).reshape(-1, 3) if DECK2.buffer(0.3).contains(Point(x, z))]
LEVELS = [
    dict(id='datum', name='Model datum', el=DATUM, kind='datum', note='Model y 0'),
    dict(id='lower_ff', name='Lower level FF', el=FF['lower'], kind='floor'),
    dict(id='patio', name='Lower patio', el=LEVEL_EL['patio'], kind='floor'),
    dict(id='terrace', name='Upper terrace', el=LEVEL_EL['terrace'], kind='floor'),
    dict(id='main_ff', name='Main level FF', el=FF['main'], kind='floor'),
    dict(id='garage_ff', name='Garage and gear bay FF', el=FF['garage'], kind='floor'),
    dict(id='primary_ff', name='Primary suite FF, level 2', el=FF['primary'], kind='floor', note='11 ft 6 in over the lower level'),
    dict(id='primary_terrace', name='Primary terrace deck', el=round(DATUM + max(deck2_y), 2) if deck2_y else FF['primary'], kind='floor'),
    dict(id='granny_head', name='Granny suite glass head', el=D['info']['granny']['head'], kind='plate'),
    dict(id='main_plate', name='Main level plate', el=plate_n, kind='plate', note='Glass heads, as on A2.4'),
    dict(id='kitchen_eave', name='Kitchen roof eave', el=INFO['kitchenEave'], kind='plate'),
    dict(id='kitchen_roof', name='Kitchen roof, flat zone', el=INFO['kitchenRoof'], kind='roof'),
    dict(id='lower_beam', name='Clerestory sill, lower beam', el=INFO['lowerBeam'], kind='beam'),
    dict(id='granny_beam', name='Granny suite beam', el=D['info']['granny']['beam'], kind='beam'),
    dict(id='bridge_beam', name='Bridge beam', el=INFO['bBeam'], kind='beam'),
    dict(id='clere_top', name='Clerestory head, north', el=INFO['clereTop'], kind='plate'),
    dict(id='porch_end', name='Porch roof end', el=D['info']['ends']['porch'], kind='roof'),
    dict(id='primary_plate', name='Primary suite plate, south wall', el=round(plate_s, 1), kind='plate', note='As on A2.5'),
    dict(id='fold_beam', name='Fold beam, north wing', el=INFO['beam'], kind='beam'),
    dict(id='south_beam', name='South wing beam, clerestory sill', el=INFO['sBeam'], kind='beam'),
    dict(id='granny_tip', name='Granny suite tip', el=D['info']['granny']['tip'], kind='tip'),
    dict(id='south_clere_top', name='South clerestory head', el=INFO['sClere'][1], kind='plate'),
    dict(id='bridge_tip', name='Bridge tip', el=INFO['bridge'], kind='tip'),
    dict(id='garage_tip', name='Garage tip', el=INFO['garage'], kind='tip'),
    dict(id='end_south', name='Ribbon end, south', el=D['info']['ends']['south'], kind='tip'),
    dict(id='end_east', name='Ribbon end, east', el=D['info']['ends']['east'], kind='tip'),
    dict(id='south_tip', name='South wing tip', el=INFO['south'], kind='tip'),
    dict(id='primary_ridge', name='Primary suite high point', el=round(DATUM + A['primaryRidge'][1], 1), kind='ridge'),
    dict(id='south_high', name='South wing high corner', el=round(DATUM + A['swHigh'][1], 1), kind='tip'),
    dict(id='tip', name='Living room tip, max', el=INFO['tip'], kind='tip'),
]
LEVELS.sort(key=lambda l: l['el'])
for l in LEVELS: l['model_y'] = round(l['el'] - DATUM, 2)

# ------------------------------------------------------------------ 6. heights (Design Book VII.5, the reg-a method)
RA_TXT = (SET / 'sheets' / 'reg-a.js').read_text()
RA_SRC = (TOOLS / 'reg-a' / 'reg-a.src.js').read_text()
pre = RA_SRC[:RA_SRC.index('/*@DATA@*/null')]
RA = json.JSONDecoder().raw_decode(RA_TXT[len(pre):])[0]

def tris(a):
    return np.array(a, dtype=float).reshape(-1, 3, 3)
TOP_ = {}
for arr in (D['rib']['roof'], D['wing']['roof'], D['rib']['deck'], D['wing']['deck']):
    for t in tris(arr):
        n = np.cross(t[1] - t[0], t[2] - t[0]); L = np.linalg.norm(n)
        if L < 2e-5: continue
        n = n / L
        if n[1] < 0 and -n[1] > 0.08: n = -n
        if n[1] < 0.08: continue
        (x1, _, z1), (x2, _, z2), (x3, _, z3) = t
        d = (z2 - z3) * (x1 - x3) + (x3 - x2) * (z1 - z3)
        if abs(d) < 1e-9: continue
        for gx_ in range(math.floor(t[:, 0].min()), math.ceil(t[:, 0].max()) + 1):
            for gz_ in range(math.floor(t[:, 2].min()), math.ceil(t[:, 2].max()) + 1):
                px, pz = gx_ + .5, gz_ + .5
                l1 = ((z2 - z3) * (px - x3) + (x3 - x2) * (pz - z3)) / d; l2 = ((z3 - z1) * (px - x3) + (x1 - x3) * (pz - z3)) / d
                if min(l1, l2, 1 - l1 - l2) < -1e-6: continue
                y = l1 * t[0][1] + l2 * t[1][1] + (1 - l1 - l2) * t[2][1]
                if (gx_, gz_) not in TOP_ or y > TOP_[(gx_, gz_)]: TOP_[(gx_, gz_)] = y
CELLS = {c: (y, y - ground(c[0] + .5, c[1] + .5)) for c, y in TOP_.items()}

def roof_near(x, z, r=1.0):
    best = None
    for gx_ in range(math.floor(x - r), math.floor(x + r) + 1):
        for gz_ in range(math.floor(z - r), math.floor(z + r) + 1):
            if (gx_, gz_) in TOP_ and (best is None or TOP_[(gx_, gz_)] > best): best = TOP_[(gx_, gz_)]
    return best

def hpoint(hid, name, x, z, y, kind, src):
    g = ground(x, z); over = y - g
    return dict(id=hid, name=name, kind=kind, at=pt2((x, z)), el=round(DATUM + y, 2), grade=round(DATUM + g, 2), over=round(over, 2),
                margin=round(30 - over, 2), flag=bool(over >= 29.0), over_limit=bool(over > 30.0), src=src)

HEIGHTS = []
named = [('tip', 'Living room tip, max', 'tip'), ('swHigh', 'South wing high corner', 'tip'), ('primaryRidge', 'Primary suite high point', 'ridge'),
         ('southTip', 'South wing tip', 'tip'), ('stip', 'South wing east post tip', 'tip'), ('bridgeTip', 'Bridge tip', 'tip'),
         ('garageTip', 'Garage tip', 'tip'), ('granny', 'Granny suite tip', 'tip'), ('endS', 'Ribbon end, south', 'tip'), ('endE', 'Ribbon end, east', 'tip')]
for key, name, kind in named:
    x, y, z = A[key]
    rn = roof_near(x, z, 1.2)
    if rn is None or abs(rn - y) > 0.7:
        continue                                      # an anchor from another scheme or a label spot, not this roof
    HEIGHTS.append(hpoint(key, name, x, z, y, kind, 'model anchor'))
for x, z, t, m in ROOF['spots']:
    el = float(re.findall(r'\d{4}\.\d', t)[0])
    if any(abs(h['at'][0] - x) < 1.5 and abs(h['at'][1] - z) < 1.5 for h in HEIGHTS): continue
    HEIGHTS.append(hpoint('spot_' + re.sub(r'\W+', '_', t).strip('_').lower(), 'Roof spot ' + t, x, z, el - DATUM, 'spot', 'A2.3 roof spot'))
# roof corners: the outline's main corners, the highest roof cell within a foot inside each
outline = outl
OUTP = Polygon(outline).buffer(0)
k = 0
for i, (x, z) in enumerate(outline):
    a, b = outline[i - 1], outline[(i + 1) % len(outline)]
    if math.hypot(x - a[0], z - a[1]) < 3 or math.hypot(b[0] - x, b[1] - z) < 3: continue     # the porch sawtooth and small jogs
    ins = [(gx_, gz_) for gx_ in range(math.floor(x) - 2, math.floor(x) + 2) for gz_ in range(math.floor(z) - 2, math.floor(z) + 2)
           if (gx_, gz_) in CELLS and OUTP.contains(Point(gx_ + .5, gz_ + .5)) and math.hypot(gx_ + .5 - x, gz_ + .5 - z) < 2.0]
    if not ins: continue
    c = max(ins, key=lambda c: CELLS[c][1])
    k += 1
    HEIGHTS.append(hpoint(f'corner_{k}', f'Roof corner {k}', c[0] + .5, c[1] + .5, CELLS[c][0], 'corner', 'roof outline corner, 1 ft cell'))
# the governing cell, and any other local high points over 25 ft
worst = max(CELLS.items(), key=lambda kv: kv[1][1])
HEIGHTS.append(hpoint('worst_cell', 'Tightest roof cell', worst[0][0] + .5, worst[0][1] + .5, worst[1][0], 'cell', '1 ft raster, as on A1.3'))
for c, (y, o) in sorted(CELLS.items(), key=lambda kv: -kv[1][1]):
    if o < 25: break
    if all(CELLS.get((c[0] + i, c[1] + j), (0, -99))[1] <= o for i in range(-4, 5) for j in range(-4, 5)) and \
            all(math.hypot(h['at'][0] - c[0] - .5, h['at'][1] - c[1] - .5) > 4 for h in HEIGHTS):
        HEIGHTS.append(hpoint(f'high_{len(HEIGHTS)}', 'Local high point', c[0] + .5, c[1] + .5, y, 'cell', '1 ft raster, local maximum'))
for ch in RA['chim']:
    g = ground(ch['x'], ch['z'])
    HEIGHTS.append(dict(id='chim_' + ch['name'].split()[0].lower(), name=ch['name'] + ' cap', kind='chimney', at=[ch['x'], ch['z']], el=ch['cap'],
                        grade=round(DATUM + g, 2), over=round(ch['cap'] - DATUM - g, 2), limit=34.0, margin=round(34 - (ch['cap'] - DATUM - g), 2),
                        flag=False, over_limit=False, within10=ch['within10'], adjacent=ch['adj'],
                        r1003_9=bool(ch['cap'] >= ch['within10'] + 2.0), src='A1.3, VII.5 allows 4 ft over'))
HEIGHTS.sort(key=lambda h: -h['over'])
edge = [(ground(x, z), x, z) for g in FOOT for x, z in g.exterior.coords]
hi_, lo_ = max(edge), min(edge)
HMETA = dict(method='Design Book VII.5: no point over 30 ft above the natural grade beneath it; the ridge within 30 ft of average natural grade; '
                    '36 ft only where the footprint slopes over 15%. Chimney masses up to 4 ft more. Natural grade from the model terrain, bilinear on its 3 ft grid, '
                    'as build_drawings.py and reg-a. FA accuracy, confirm on survey.',
             limit_ft=30.0, flag_ft=29.0, avg_grade=round(DATUM + (hi_[0] + lo_[0]) / 2, 1), ridge_limit=round(DATUM + (hi_[0] + lo_[0]) / 2 + 30, 1),
             footprint_slope_pct=round(100 * (hi_[0] - lo_[0]) / math.hypot(hi_[1] - lo_[1], hi_[2] - lo_[2]), 1),
             governs='30 ft' if 100 * (hi_[0] - lo_[0]) / math.hypot(hi_[1] - lo_[1], hi_[2] - lo_[2]) <= 15 else '36 ft',
             flagged=[h['id'] for h in HEIGHTS if h['flag']])
assert abs(next(h for h in HEIGHTS if h['id'] == 'tip')['over'] - CALCS['heights']['tip_over_grade']) < 0.05, 'tip no longer matches calcs.json'

# ------------------------------------------------------------------ 8. walls and openings (before the tags, which cite them)
SB_TXT = (SET / 'sheets' / 'sched-b.js').read_text()
SBD = json.JSONDecoder().raw_decode(SB_TXT[SB_TXT.index('{"types":'):])[0]
PN = json.loads((TOOLS / 'sched-b' / 'panes.json').read_text())
TR = json.loads((TOOLS / 'sched-b' / 'types_raw.json').read_text())
WN = {w['tag']: w for w in PN['walls']}

def fam(p):   # sched-b build.py, verbatim logic
    steel = p['frame'] == 'steel'
    if p['raked']: return ('steel', 'raked')
    if p['wall'] in ('W3', 'W17'): return ('steel', 'clere ' + p['op'])
    if p['op'] == 'casement':
        if not steel: return ('clad', 'egress')
        return ('steel', 'slot') if p['nw'] <= 2.5 else ('steel', 'casement')
    if p['op'] == 'awning': return (p['frame'], 'awning')
    cls = 'full' if p['nh'] >= 7.0 else 'tall' if p['nh'] >= 3.5 else 'low'
    return (p['frame'], cls)
TYPE_OF = {(t['frame'], t['fam']): t['t'] for t in SBD['types']}

def wall_xz(tag, h):
    w = WN[tag]; nx, nz = w['n']; d = w['d']
    return (nx * d - nz * h, nz * d + nx * h)

WINDOWS = []
for t in TR['types']:
    for p in t['items']:
        typ = TYPE_OF[fam(p)]
        x, z = wall_xz(p['wall'], (p['h0'] + p['h1']) / 2)
        top = max(p['yl'], p['yr']) if p['raked'] else p['y1']
        WINDOWS.append(dict(tag=typ, wall=p['wall'], at=pt2((x, z)), sill=round(DATUM + p['y0'], 2), head=round(DATUM + top, 2),
                            w=r2(p['w']), h=r2(p['h']), raked=bool(p['raked']), zone=p.get('zone')))
cnt = collections.Counter(w['tag'] for w in WINDOWS)
for t in SBD['types']:
    assert cnt[t['t']] == t['n'], ('window type count differs from sched-b', t['t'], cnt[t['t']], t['n'])
WALLS = []
for w in SBD['walls']:
    ox, oz = w['out']
    segs = [[r2(s[0] - ox), r2(s[1] - oz), r2(s[2] - ox), r2(s[3] - oz)] for s in w['segs']]       # sched-b draws them 1 ft outside
    L = [math.hypot(s[2] - s[0], s[3] - s[1]) for s in segs]
    k_ = max(range(len(segs)), key=lambda i: L[i])
    s = segs[k_]
    ws = [x for x in WINDOWS if x['wall'] == w['tag']]
    WALLS.append(dict(id=w['tag'], name=w['name'], face=w['face'], out=w['out'], segs=segs, anchor=pt2(((s[0] + s[2]) / 2, (s[1] + s[3]) / 2)),
                      glass_sf=w['sf'], types=w['types'].split(), panes=w['n'], over_140=w['flag'],
                      el=[round(min(x['sill'] for x in ws), 2), round(max(x['head'] for x in ws), 2)] if ws else None))
# doors: sched-a's own door list (its build.py, run up to the key plan, writes nothing) and its template rows
SA = (TOOLS / 'sched-a' / 'build.py').read_text()
ns = {'__file__': str(TOOLS / 'sched-a' / 'build.py'), '__name__': 'sched_a_doors'}
exec(compile(SA[:SA.index('# ------------------------------------------------------------------ key plan')], 'sched-a/build.py', 'exec'), ns)
TPL = (TOOLS / 'sched-a' / 'sched-a.template.js').read_text()
ROWS_A = {m[0]: m for m in re.findall(r"\['(\d{3})', '([^']+)', '([A-E])', '([^']+)', '([^']+)', '([^']+)', '([^']+)', '([^']+)', '([^']+)', '([^']+)'\]", TPL)}
DOORS = []
for tag, (x, z), _ in ns['DOORS']:
    r = ROWS_A.get(tag)
    ff = FF['lower'] if tag[0] == '0' else FF['primary'] if tag[0] == '2' else FF['garage'] if tag in ('104', '105') else FF['main']
    wall = min(WALLS, key=lambda w: min(LineString([(s[0], s[1]), (s[2], s[3])]).distance(Point(x, z)) for s in w['segs']))
    dwall = min(LineString([(s[0], s[1]), (s[2], s[3])]).distance(Point(x, z)) for s in wall['segs'])
    d = dict(tag=tag, at=pt2((x, z)), ff=ff, name=r[1] if r else None, type=r[2] if r else None, w=r[3] if r else None, h=r[4] if r else None,
             frame=r[5] if r else None, wall=wall['id'] if dwall < 1.5 else None)
    DOORS.append(d)

# ------------------------------------------------------------------ 7. tags
ROWS_TXT = RA_SRC[RA_SRC.index('const ROWS = ['):RA_SRC.index('const WORD')]
MATRIX = []
for i, blk in enumerate(re.split(r"\n    \['", ROWS_TXT)[1:]):
    name = blk.split("'", 1)[0]
    sec = re.search(r"', '([IVX]+\.\d+(?: · [IVX]+\.\d+)*)',", blk).group(1)
    st = re.findall(r"'(meets|variance|confirm)'\]", blk)[-1]
    MATRIX.append(dict(n=i + 1, name=name, section=sec, status=st))
MROW = {m['name']: m for m in MATRIX}

def row(name):
    m = MROW[name]
    return dict(n=m['n'], name=m['name'], section=m['section'])

TAGS = []
def tag(tid, sheets, at, text, status, mrow, el=None, note=None):
    t = dict(id=tid, sheets=sheets, at=pt2(at), text=text, status=status, a13=row(mrow) if mrow else None)
    if el is not None: t['el'] = round(el, 2)
    if note: t['note'] = note
    TAGS.append(t)

H = {h['id']: h for h in HEIGHTS}
ELEV_OF = {'N': 'A4.0', 'E': 'A4.1', 'S': 'A4.2', 'W': 'A4.3'}
tp = H['tip']
tag('T01', ['A2.3', 'A4.0', 'A4.1', 'A1.3'], tp['at'], f"VII.5 tip {tp['over']:.1f} ft over grade", 'meets', 'Height', tp['el'], 'Within 1 ft of 30 ft, confirm on survey')
sw = H.get('swHigh') or H['worst_cell']
tag('T02', ['A2.3', 'A4.1', 'A4.2', 'A1.3'], sw['at'], f"VII.5 {sw['over']:.1f} ft, the tightest point", 'meets', 'Height', sw['el'], 'Within 1 ft of 30 ft, confirm on survey')
if 'primaryRidge' in H:
    pr = H['primaryRidge']
    tag('T03', ['A2.3', 'A4.2'], pr['at'], f"VII.5 {pr['over']:.1f} ft over grade", 'meets', 'Height', pr['el'], 'Within 1 ft of 30 ft')
cen = OUTP.intersection(NWING).centroid
tag('T04', ['A2.3', 'A4.0', 'A4.2', 'A1.3'], (cen.x, cen.y), 'roof under 4:12, Design Variance', 'variance', 'Roof form and pitch', None,
    f"About {RA['pitch']['ok']}% of the roof at 4:12 or steeper, {RA['pitch']['flat']}% flat")
kx, kz = next((x, z) for x, z, t, m in ROOF['spots'] if t.startswith('kitchen'))
tag('T05', ['A2.3'], (kx, kz), 'VII.13 flat zone 1/4:12, under a third', 'meets', 'Roof form and pitch', INFO['kitchenRoof'])
tag('T06', ['A2.3', 'A0.2'], (cen.x + 6, cen.y + 4), 'IX.5 standing seam, Class A', 'confirm', 'Roofing', None, 'Ballast rule for the flattest runs rides with the variance')
for w in WALLS:
    if not w['over_140']: continue
    l2 = any(x['zone'] == 'primary' for x in WINDOWS if x['wall'] == w['id'])
    sheets = ['A7.1', ELEV_OF.get(w['face'], 'A4.1'), 'A2.1'] + (['A2.2'] if l2 else [])
    tag(f"T_{w['id']}", sheets, w['anchor'], f"VII.15 glass {w['glass_sf']} sf, mitigate", 'confirm', 'Glazing',
        (w['el'][0] + w['el'][1]) / 2 if w['el'] else None, f"{w['id']} {w['name']}, over 140 sf: LCC approval and reflectivity mitigation")
for ch in RA['chim']:
    cid = 'chim_' + ch['name'].split()[0].lower()
    tag(f"T_{cid}_area", ['A2.3', 'A1.3'], (ch['x'], ch['z']), f"VII.20 chimney about {ch['area']} sf", 'meets' if 18 <= ch['area'] <= 60 else 'confirm', 'Chimneys', ch['cap'])
    ok = ch['cap'] >= ch['within10'] + 2.0
    tag(f"T_{cid}_cap", ['A2.3', 'A4.0' if ch['z'] < 0 else 'A4.2', 'A3.0'], (ch['x'], ch['z']), 'chimney cap, CRC R1003.9 confirm', 'meets' if ok else 'confirm',
        'Chimneys', ch['cap'], f"Cap {ch['cap']}, roofs within 10 ft reach {ch['within10']}; 2 ft over them wants {ch['within10'] + 2:.1f}")
outside = [p for p in outline if not Polygon(subpaths(P['site']['setback'])[0]).contains(Point(p))]
if outside:
    tag('T07', ['A1.2', 'A1.3'], outside[0], 'III.6 roof edge over the front setback, about 9 in', 'confirm', 'Setbacks', None, 'Front line traces about 46 to 47 ft, confirm on survey')
tag('T08', ['A1.2', 'A1.3'], (A['drive'][0], A['drive'][2]), f"III.7 impervious about {CALCS['impervious_pct']}%", 'confirm', 'Impervious coverage', None, 'Under 30% by listing, tight on the model lot lines')
tag('T09', ['A2.1', 'A0.6'], tuple(P['levels']['rib']['tags']['main']), f"VII.4 about {CALCS['conditioned']:,} sf conditioned", 'meets', 'Living area')
tag('T10', ['A2.1', 'A3.0'], ((gx[1] + GX1) / 2, (nwz0 + GZ1) / 2), 'XI.14 slab at the garage only', 'meets', 'Slab on grade')
tr_ = P['site']['trees'][0]
tag('T11', ['A1.2', 'L1.0'], (tr_[0], tr_[1]), f"IV.20 the tree, about {RA['tree']['house']:.0f} ft to the walls", 'confirm', 'Defensible space', None, 'Limbed up, Zone 0 rules pending')
ap = (-51.0, 31.0)
tag('T12', ['A1.2'], ap, 'III.9 snow storage 30% of paving', 'confirm', 'Snow', None, f"About {math.ceil((CALCS['drive'] + CALCS['apron_allowance']) * 0.3 / 10) * 10} sf, clear of the easement")
tag('T13', ['A2.3', 'A4.2'], (A['porch'][0], A['porch'][2]), 'VII.14 no shedding over the entry', 'confirm', 'Snow')
gd = next(d for d in DOORS if d['tag'] == '104')
tag('T14', ['A2.3', 'A4.2'], (gd['at'][0], gd['at'][1]), 'VII.14 no shedding at the garage doors', 'confirm', 'Snow')
tag('T15', ['A2.4', 'L1.0'], (-29.5, 4.6), 'VIII.2 shielded, full cutoff', 'confirm', 'Exterior lighting')
tag('T16', ['A7.1'], WALLS[0]['anchor'], 'IX.6 wood, matte clad frames', 'confirm', 'Window frames')
tag('T17', ['A4.1', 'A0.0'], (A['clad'][0], A['clad'][2]), 'IX.4 wood 30% of wall area', 'confirm', 'Wall materials', DATUM + A['clad'][1])
tag('T18', ['A4.1', 'A0.0'], (A['clad'][0] + 4, A['clad'][2]), 'IX.2 LRV 15 to 40, matte', 'confirm', 'Colors', DATUM + A['clad'][1] - 2)
lowest = next((l for l in PB['sheets']['A2.5']['labels'] if l.get('k') == 'clg low'), None)
tag('T19', ['A2.5', 'A3.1'], (1.3, 69.3), f"headroom {lowest['t'] if lowest else 'under 7 ft'}, CRC R305.1 confirm", 'confirm', None, None,
    'South edge of the primary suite, half a sloped room at 7 ft or more')
tag('T20', ['A2.1', 'A7.0'], (BRIDGE.bounds[2], 12.0), 'bridge about 16 ft, brief says 20, confirm', 'confirm', None, None, 'Design fact check, not a Design Book row')
for t in TAGS:
    t['at_field'] = {}
    for s in t['sheets']:
        if s in COORDS: t['at_field'][s] = to_plan(s, *t['at'])
        elif t.get('el') is not None:
            for vn, v in VIEWS.items():
                if v['sheet'] == s: t['at_field'][vn] = to_view(vn, t['at'][0], t['el'], t['at'][1])

# ------------------------------------------------------------------ checks against the sheets
DISAGREE = []
g7 = {g['name']: g['sf'] for g in RA['glass']}
pairs = [('W1', 'North wing, court face'), ('W2', 'Living room tip, end wall'), ('W7', 'Bridge, court side'), ('W10', 'Bridge, terrace face'),
         ('W11', 'South wing, court face'), ('W12', 'Lower level, terrace face'), ('W13', 'South wing, outer face')]
for wid, nm in pairs:
    w = next(x for x in WALLS if x['id'] == wid)
    if nm in g7 and abs(g7[nm] - w['glass_sf']) > 20:
        DISAGREE.append(f"Glass on {wid}: A7.1 (sched-b, panelized) about {w['glass_sf']} sf, A1.3 (reg-a, model face) about {g7[nm]} sf")
DISAGREE.append(f"Bridge width: model about {BRIDGE.bounds[2] - BRX:.1f} ft outside to outside (info bWidth {INFO['bWidth']}), the brief says about 20 ft")
d101 = next(d for d in DOORS if d['tag'] == '101'); d102 = next(d for d in DOORS if d['tag'] == '102')
DISAGREE.append(f"Main entry: A7.0 puts 101 at the bridge vestibule ({d101['at']}), and 102 off the porch as the family entry; the 9/30 program puts the entry at the porch and the family entry at the garage")
d107 = next(d for d in DOORS if d['tag'] == '107')
if d107['frame'] and 'clad' in d107['frame'].lower():
    DISAGREE.append('Door 107 frame is aluminum clad on A7.0; A7.1 frames the bridge glass in dark steel')
DISAGREE.append('Stair: the program puts it along the rear court glass with the bar just east of it; the rear court (terraces) is east on A1.2, so the bar would land outside. Placeholder puts the stair on the west glass')
DISAGREE.append(f"Height figure: A1.2 and A2.3 quote the tip, {CALCS['heights']['tip_over_grade']} ft over grade, as the max; the governing point is the south wing corner at {H['swHigh']['over'] if 'swHigh' in H else '?'} ft, the tightest cell {H['worst_cell']['over']} ft (A1.3 agrees)")

# the fire pit: the plan path's arc (SVG endpoint form) against the model's pit mesh
m_ = re.match(r'M([\d.-]+) ([\d.-]+) A([\d.]+) [\d.]+ 0 (\d) (\d) ([\d.-]+) ([\d.-]+)', P['pit'])
if m_:
    x1_, y1_, r_, fa_, fs_, x2_, y2_ = (float(v) for v in m_.groups())
    mx_, my_ = (x1_ + x2_) / 2, (y1_ + y2_) / 2; dx_, dy_ = x2_ - x1_, y2_ - y1_; L_ = math.hypot(dx_, dy_)
    h_ = math.sqrt(max(r_ * r_ - (L_ / 2) ** 2, 0)); nx_, ny_ = -dy_ / L_, dx_ / L_
    sgn_ = -1 if fa_ == fs_ else 1                   # SVG F.6.5: the center sign flips when the flags agree
    pc_ = (mx_ + sgn_ * h_ * nx_, my_ + sgn_ * h_ * ny_)
    pm_ = np.array(D['xt']['pit'], dtype=float).reshape(-1, 3)
    pm_c = ((pm_[:, 0].min() + pm_[:, 0].max()) / 2, (pm_[:, 2].min() + pm_[:, 2].max()) / 2)
    if math.hypot(pc_[0] - pm_c[0], pc_[1] - pm_c[1]) > 1.0:
        DISAGREE.append(f"Fire pit: A2.1 draws the pit circle centered near ({pc_[0]:.0f}, {pc_[1]:.0f}), the model's pit is at ({pm_c[0]:.0f}, {pm_c[1]:.0f}) inside the bench; the plan path's arc flags pick the far center")

# ------------------------------------------------------------------ write
OUT = dict(
    meta=dict(built='9/30/26', by='draw/build_shared.py', scheme='ribbon', datum=DATUM, units='model feet: x east on the plan, z down the sheet (south), y up; el = 5990.0 + y',
              north_deg=DRW['north'], note='FA accuracy, about, confirm on survey. Room programming is a placeholder.',
              sources=['walsh/index.html model-data', 'draw/drawings.js', 'draw/render_meta.json', 'draw/calcs.json', 'sheets/plans-b.js and tools/plans-b/build_rcp.py',
                       'sheets/reg-a.js and tools/reg-a/reg-a.src.js', 'tools/sched-a/build.py and sched-a.template.js', 'sheets/sched-b.js and tools/sched-b/panes.json, types_raw.json',
                       'tools/sectelev-b/plan_data.json']),
    coords=dict(field=FIELD, plans=COORDS, views=VIEWS,
                how='Field inches, origin at the field top left (what ctx.U positions in a sheet or overlay). Plan: fx = fx[0] * x + fx[1], fy = fy[0] * z + fy[1]. '
                    'Ortho view: h = x * right[0] + z * right[1]; fx = fx[0] * h + fx[1]; fy = fy[0] * (el - 5990) + fy[1].'),
    grids=dict(note=GRID_NOTE, grids=GRIDS, refs=REFS, posts=POSTS),
    rooms=ROOMS,
    dims=DIMS,
    levels=LEVELS,
    heights=dict(meta=HMETA, points=HEIGHTS),
    tags=dict(status=['meets', 'variance', 'confirm'], matrix=MATRIX, tags=TAGS),
    walls=WALLS,
    openings=dict(doors=DOORS, windows=WINDOWS, window_types=[{k: t[k] for k in ('t', 'fam', 'frame', 'n', 'op', 'frm', 'w', 'h', 'where')} for t in SBD['types']]),
    disagreements=DISAGREE,
)
txt = json.dumps(OUT, ensure_ascii=False, separators=(',', ':'))
(HERE / 'shared.json').write_text(json.dumps(OUT, ensure_ascii=False, indent=1))
HELP = r'''
/* helpers: model feet to field inches */
(function (S) {
  S.plan = function (sheet, x, z) { const c = S.coords.plans[sheet]; return c ? [c.fx[0] * x + c.fx[1], c.fy[0] * z + c.fy[1]] : null; };
  S.view = function (name, x, el, z) { const v = S.coords.views[name]; if (!v) return null; const h = x * v.right[0] + z * v.right[1]; return [v.fx[0] * h + v.fx[1], v.fy[0] * (el - S.meta.datum) + v.fy[1]]; };
  S.viewsOn = function (sheet) { return Object.keys(S.coords.views).filter(k => S.coords.views[k].sheet === sheet); };
  S.ftin = function (v) { let f = Math.floor(v + 1e-6), i = Math.round((v - f) * 12); if (i === 12) { f += 1; i = 0; } return f + '′ ' + i + '″'; };
})(window.SHARED);
'''
(HERE / 'shared.js').write_text('/* built by draw/build_shared.py from the pocket model and the crews\' data; do not edit by hand. See draw/SHARED.md */\n'
                                'window.SHARED = ' + txt + ';\n' + HELP)
print('wrote shared.json and shared.js', len(txt) // 1024, 'KB')
print('grids', [(g['id'], [l['id'] for l in g['num']], [l['id'] for l in g['let']]) for g in GRIDS])
for r in ROOMS: print(f"  {r['id']:16s} {r['level']:8s} about {r['sf_about']:5d} sf  {r.get('ceiling_text', '')}")
print('heights flagged', HMETA['flagged'])
print('tags', len(TAGS), 'dims', len(DIMS), 'walls', len(WALLS), 'doors', len(DOORS), 'windows', len(WINDOWS))
for d in DISAGREE: print('  !', d)
