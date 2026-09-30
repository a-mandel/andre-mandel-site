"""overlays-site crew (9/30/26): dimension, grid, wing name and compliance layers over A1.2, L1.0 and L1.1.
   python3 walsh/set/sheets/tools/overlays-site/build.py
   Reads the pocket model (walsh/index.html model-data) and draw/shared.json, measures the site the way
   tools/reg-a/build_reg.py does (same lot closure, same bilinear terrain), and writes sheets/overlays-site.js
   from overlays-site.src.js beside this file. FA accuracy: about, confirm on survey."""
import json, math, re
from pathlib import Path

HERE = Path(__file__).resolve().parent
SET = HERE.parents[2]
MODEL = SET.parent / 'index.html'
SH = json.loads((SET / 'draw' / 'shared.json').read_text())
CALCS = json.loads((SET / 'draw' / 'calcs.json').read_text())
DATUM = 5990.0

for line in MODEL.read_text().splitlines():
    if 'id="model-data"' in line:
        D = json.loads(re.sub(r'^<script[^>]*>', '', line).rsplit('</script>', 1)[0]); break
P = D['plans']

# terrain, bilinear on the model's 3 ft grid (as draw/build_drawings.py and reg-a)
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

def nums(s): return [float(v) for v in re.findall(r'-?\d+(?:\.\d+)?', s)]
def subpaths(d):
    out = []
    for sp in re.split(r'(?=M)', d):
        n = nums(sp)
        if len(n) >= 4: out.append(list(zip(n[0::2], n[1::2])))
    return out
def parea(p): return abs(sum(p[i][0] * p[(i + 1) % len(p)][1] - p[(i + 1) % len(p)][0] * p[i][1] for i in range(len(p)))) / 2
def closest(p, a, b):
    dx, dz = b[0] - a[0], b[1] - a[1]; L = dx * dx + dz * dz
    t = max(0, min(1, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dz) / L)) if L else 0
    q = (a[0] + t * dx, a[1] + t * dz)
    return math.hypot(p[0] - q[0], p[1] - q[1]), q
def pip(x, y, poly):
    c = False
    for i in range(len(poly)):
        x1, y1 = poly[i]; x2, y2 = poly[i - 1]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1: c = not c
    return c
r2 = lambda v: round(v, 2)
pt = lambda p: [r2(p[0]), r2(p[1])]

# ------------------------------------------------------------------ lot, closed as reg-a closes it
S = P['site']; SB = subpaths(S['setback'])[0]
w0, w1 = (-125.0, -18.6), (-113.67, 124.0)                  # street (front) line as traced
dw = (w1[0] - w0[0], w1[1] - w0[1])
NE, SE = (65.73, -37.06), (69.02, 72.89)
nw = (w0[0] + dw[0] * (-37.06 - w0[1]) / dw[1], -37.06)
ds = (-156.32, 51.11)
den = dw[0] * ds[1] - dw[1] * ds[0]
s_ = ((SE[0] - w0[0]) * ds[1] - (SE[1] - w0[1]) * ds[0]) / den
sw = (w0[0] + s_ * dw[0], w0[1] + s_ * dw[1])
LOT = [nw, NE, SE, sw]
Lw = math.hypot(*dw); nin = (dw[1] / Lw, -dw[0] / Lw)       # inward normal of the street line
NORTH = SH['meta']['north_deg']

def bearing(a, b):
    """quadrant bearing, whole degrees, read on the model's north (sheet up is N 39.3 W)"""
    az = (math.degrees(math.atan2(b[0] - a[0], -(b[1] - a[1]))) - NORTH) % 360
    if az > 90 and az <= 270: az = (az + 180) % 360          # quote every line from its north end
    if az <= 90: return f'N {round(az)}° E'
    return f'N {round(360 - az)}° W'

SIDES = [('north', nw, NE), ('east', NE, SE), ('south', SE, sw), ('front', sw, nw)]
lot_lines = [dict(side=k, a=pt(a), b=pt(b), ft=round(math.hypot(b[0] - a[0], b[1] - a[1]), 1), brg=bearing(a, b)) for k, a, b in SIDES]

# ------------------------------------------------------------------ roof edge (the drip line counts in setbacks) and walls
ROOF = subpaths(P['roof']['rib']['outline'])[0]
FOOT = subpaths(P['foot']['rib'])
def tight(a, b):
    best = None
    for p in ROOF:
        d, q = closest(p, a, b)
        if best is None or d < best[0]: best = (d, p, q)
    return best
tight_d = {k: tight(a, b) for k, a, b in SIDES}

# garage roof corner past the traced front setback line
sbw = (SB[3], SB[0])                                         # setback west edge, south to north
def side_of(p, a, b): return ((b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0])) / math.hypot(b[0] - a[0], b[1] - a[1])
over = max((( -side_of(p, *sbw)) if not pip(p[0], p[1], SB) else 0, p) for p in ROOF)
enc_ft, enc_p = over
_, enc_q = closest(enc_p, *sbw)

# setback distances off each lot line, measured square to it
def sq_dist(p, a, b): return abs(side_of(p, a, b))
front_sb = [round(sq_dist(SB[0], sw, nw), 1), round(sq_dist(SB[3], sw, nw), 1)]
rear_sb = [round(sq_dist(SB[1], NE, SE), 1), round(sq_dist(SB[2], NE, SE), 1)]

# ------------------------------------------------------------------ drive
dr = D['drive']
pl = lambda k: [(dr[k][i], dr[k][i + 2]) for i in range(0, len(dr[k]), 3)]
north_edge = pl(6) + pl(7)[1:]
south_edge = pl(5)
def x_on_front(z): return w0[0] + dw[0] * (z - w0[1]) / dw[1]
# width: mean square distance from the south edge to the north edge along the straight run
wid = []
for p in pl(5)[3:-3]:
    wid.append(min(closest(p, north_edge[i], north_edge[i + 1])[0] for i in range(len(north_edge) - 1)))
drive_w = sum(wid) / len(wid)
# centerline length: straight run from the front line to the apron edge (x -63.57), plus the bend
cl = [((a[0] + b[0]) / 2, (a[1] + b[1]) / 2) for a, b in zip(pl(6), pl(5))]
start_z = cl[0][1]
xs0 = x_on_front(start_z)
cl = [(xs0, start_z)] + [p for p in cl if xs0 < p[0] < -63.57]
cl.append((-63.57, cl[-1][1] + (cl[-1][1] - cl[-2][1]) / (cl[-1][0] - cl[-2][0]) * (-63.57 - cl[-1][0])))
drive_len = sum(math.hypot(cl[i + 1][0] - cl[i][0], cl[i + 1][1] - cl[i][1]) for i in range(len(cl) - 1))
WA = min(pl(6), key=lambda p: abs(p[0] + 114.5))
drive = dict(w=round(drive_w, 1), len=round(drive_len), a=pt(cl[0]), b=pt(cl[-1]),
             wa=pt(WA), wb=pt(min(((closest(WA, south_edge[i], south_edge[i + 1])[1]) for i in range(len(south_edge) - 1)),
                                  key=lambda q: math.hypot(q[0] - WA[0], q[1] - WA[1]))))

# ------------------------------------------------------------------ the signature tree
TR = S['trees'][0]
best = None
for sp in FOOT:
    for i in range(len(sp)):
        d, q = closest((TR[0], TR[1]), sp[i], sp[(i + 1) % len(sp)])
        if best is None or d < best[0]: best = (d, q)
tree = dict(at=[TR[0], TR[1]], crown=13.0, footing=round(best[0], 1), fq=pt(best[1]))

# ------------------------------------------------------------------ natural grade at the building's outer corners
CORNERS = [('garage NW', (-76.8, -16.06)), ('garage SW', (-76.8, 8.28)), ('garage SE', (-65.59, 17.29)),
           ('north wing NE', (37.83, -16.58)), ('north wing SE', (36.96, 10.73)),
           ('south wing NE', (32.43, 33.4)), ('south wing SE', (40.37, 57.66)), ('south wing SW', (-21.61, 78.37)),
           ('granny NW', (-21.62, 51.06))]                       # roof outline corners, the building as drawn
spots = [dict(name=n, at=list(p), el=round(DATUM + ground(*p), 1)) for n, p in CORNERS]
# cross check against the height crew's roof corners (same terrain method)
hp = {p['id']: p for p in SH['heights']['points']}
chk = abs(DATUM + ground(-75.5, -15.5) - hp['corner_1']['grade'])
assert chk < 0.05, f'grade method drifted from SHARED heights by {chk}'

# ------------------------------------------------------------------ grids, bubbles at the extents only
grids = {g['id']: g for g in SH['grids']['grids']}
bub = []
for l in grids['north']['num']: bub.append(dict(id=l['id'], at=[l['at'], -21.0], lead=[[l['at'], -16.58], [l['at'], -20.0]]))
for l in grids['north']['let']: bub.append(dict(id=l['id'], at=[-90.0, l['at']], lead=[[-77.6, l['at']], [-89.0, l['at']]]))
for l in grids['south']['num']:
    b = l['b']; bub.append(dict(id=l['id'], at=[b[0], b[1] + 2.4], lead=[[b[0], b[1] - 1.5], [b[0], b[1] + 1.4]]))
for l in grids['south']['let']:
    a = l['a']; ux, uz = (a[0] - l['b'][0]), (a[1] - l['b'][1]); L = math.hypot(ux, uz); ux, uz = ux / L, uz / L
    tip = (a[0] + 4.0 * ux, a[1] + 4.0 * uz)                   # west ends, clear of the east setback strings
    bub.append(dict(id=l['id'], at=pt((tip[0] + 0.9 * ux, tip[1] + 0.9 * uz)), lead=[pt(a), pt(tip)]))

# ------------------------------------------------------------------ compliance tags for the site plan, straight from SHARED
tags = [dict(id=t['id'], at=t['at'], text=t['text'], status=t['status'], n=t['a13']['n'], row=t['a13']['name'],
             sec=t['a13']['section'], note=t.get('note', '')) for t in SH['tags']['tags'] if 'A1.2' in t['sheets'] or 'L1.0' in t['sheets'] and t['id'] == 'T11']

OUT = dict(
    built='9/30/26', north=NORTH, lot=[pt(p) for p in LOT], lot_lines=lot_lines, lot_sf=round(parea(LOT)),
    street=[pt(w0), pt(w1)], nin=[round(nin[0], 5), round(nin[1], 5)],
    setback=[pt(p) for p in SB], front_sb=front_sb, rear_sb=rear_sb,
    roof=[pt(p) for p in ROOF],
    tight={k: dict(ft=round(v[0], 1), p=pt(v[1]), q=pt(v[2])) for k, v in tight_d.items()},
    enc=dict(inch=round(enc_ft * 12), p=pt(enc_p), q=pt(enc_q)),
    drive=drive, tree=tree, spots=spots, bubbles=bub, tags=tags,
    calcs=dict(roof_pct=CALCS.get('coverage_pct'), imp_pct=CALCS.get('impervious_pct'), lot_sf=CALCS.get('lot_sf')),
    matrix={m['n']: m for m in SH['tags']['matrix']},
)
src = (HERE / 'overlays-site.src.js').read_text()
(SET / 'sheets' / 'overlays-site.js').write_text(src.replace('/*@DATA@*/null', json.dumps(OUT, ensure_ascii=False)))
print(json.dumps({k: v for k, v in OUT.items() if k not in ('roof', 'bubbles', 'matrix')}, indent=0, ensure_ascii=False)[:4000])
