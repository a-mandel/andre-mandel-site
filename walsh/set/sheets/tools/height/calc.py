"""height crew: shared geometry and the height calculation, from the pocket model (walsh/index.html DATA)."""
import json, re, math, collections
from pathlib import Path
HERE = Path(__file__).resolve().parent
SET = HERE.parents[2]
MODEL = SET.parent / 'index.html'
CALCS = json.loads((SET / 'draw' / 'calcs.json').read_text())
DATUM = 5990.0
for line in MODEL.read_text().splitlines():
    if 'id="model-data"' in line:
        D = json.loads(re.sub(r'^<script[^>]*>', '', line).rsplit('</script>', 1)[0]); break
P = D['plans']; ROOF = P['roof']['rib']
# terrain: same bilinear 3 ft grid as draw/build_drawings.py and reg-a
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
def tris(a):
    for i in range(0, len(a) - 8, 9):
        yield (a[i], a[i + 1], a[i + 2]), (a[i + 3], a[i + 4], a[i + 5]), (a[i + 6], a[i + 7], a[i + 8])
def up(t):
    (p, q, r) = t
    ux, uy, uz = q[0] - p[0], q[1] - p[1], q[2] - p[2]; vx, vy, vz = r[0] - p[0], r[1] - p[1], r[2] - p[2]
    n = (uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx); L = math.sqrt(sum(c * c for c in n)) or 1
    return n[1] / L, L / 2
ROOFS = [D['rib']['roof'], D['wing']['roof'], D['wing']['rear']]
# ---- top of roof raster, 0.5 ft cells (roofing surface, the highest point per cell)
C = 0.5
top = {}
for arr in ROOFS:
    for t in tris(arr):
        ny, a = up(t)
        if a < 1e-6: continue
        (x1, y1, z1), (x2, y2, z2), (x3, y3, z3) = t
        d = (z2 - z3) * (x1 - x3) + (x3 - x2) * (z1 - z3)
        if abs(d) < 1e-9: continue
        xs = (x1, x2, x3); zs = (z1, z2, z3)
        for gx in range(math.floor(min(xs) / C), math.ceil(max(xs) / C) + 1):
            for gz in range(math.floor(min(zs) / C), math.ceil(max(zs) / C) + 1):
                px, pz = (gx + .5) * C, (gz + .5) * C
                l1 = ((z2 - z3) * (px - x3) + (x3 - x2) * (pz - z3)) / d; l2 = ((z3 - z1) * (px - x3) + (x1 - x3) * (pz - z3)) / d
                if min(l1, l2, 1 - l1 - l2) < -1e-6: continue
                y = l1 * y1 + l2 * y2 + (1 - l1 - l2) * y3
                if y > top.get((gx, gz), -1e9): top[(gx, gz)] = y
cells = {c: (y, y - ground((c[0] + .5) * C, (c[1] + .5) * C)) for c, y in top.items()}
# ---- exact vertices (roof planes are flat, grade bilinear: the worst point sits at a vertex or in a cell)
verts = []
for arr in ROOFS:
    for i in range(0, len(arr), 3):
        x, y, z = arr[i], arr[i + 1], arr[i + 2]
        verts.append((y - ground(x, z), x, y, z))
vmax = max(verts)
def roof_at(x, z, r=0.8):
    """highest roofing within r ft of a plan point, and height over grade there"""
    best = None
    for (o, vx, vy, vz) in verts:
        if abs(vx - x) <= r and abs(vz - z) <= r and (best is None or vy > best[1]): best = (o, vy, vx, vz)
    return best
def region_max(pred):
    return max(((o, x, y, z) for (o, x, y, z) in verts if pred(x, z)), default=None)
def spot(name, key, x, z, y, note=''):
    g = ground(x, z)
    return dict(name=name, key=key, x=round(x, 2), z=round(z, 2), el=round(DATUM + y, 2), grade=round(DATUM + g, 2),
                over=round(y - g, 2), margin=round(30 - (y - g), 2), note=note)
A = D['A']
PTS = []
PTS.append(spot('Living room tip', 'tip', A['tip'][0], A['tip'][2], A['tip'][1], 'raked glass below, the signature lift'))
o, x, y, z = vmax
PTS.append(spot('South wing NE corner', 'south', x, z, y, 'the high corner of the south roof'))
foot = subpaths(P['foot']['rib'])
def roof_xz(x, z):
    c = (math.floor(x / C), math.floor(z / C))
    return top.get(c, max((top.get((c[0] + i, c[1] + j), -1e9) for i in (-1, 0, 1) for j in (-1, 0, 1))))
# ribbon fold beams: the roofing right over each beam
for nm, k, key in (('Roof over the north fold beam', 'beam', 'beam'), ('Roof over the south fold beam', 'sbeam', 'sbeam')):
    PTS.append(spot(nm, key, A[k][0], A[k][2], roof_xz(A[k][0], A[k][2])))
g = region_max(lambda x, z: -5 <= x <= 17 and 11 < z < 40); PTS.append(spot('Bridge high point', 'bridge', g[1], g[3], g[2]))
g = region_max(lambda x, z: x < -5 and z > 40); PTS.append(spot('Granny suite roof high point', 'granny', g[1], g[3], g[2]))
g = region_max(lambda x, z: x < -38); PTS.append(spot('Garage high point', 'garage', g[1], g[3], g[2]))
# chimney caps (caps are excluded; masses may rise 4 ft over the allowable roof height, VII.5)
CH = []
for k, nm in (('rib', 'South chimney cap'), ('ribN', 'North chimney cap')):
    c = D['chim'][k]['cap']; i = max(range(len(c) // 3), key=lambda i: c[3 * i + 1])
    s = D['chim'][k]['stone']; sx = s[0::3]; sz = s[2::3]; cx = (min(sx) + max(sx)) / 2; cz = (min(sz) + max(sz)) / 2
    p = spot(nm, 'chim' + k, cx, cz, c[3 * i + 1]); p['mass'] = round(DATUM + max(s[1::3]), 2); p['limit'] = 34.0
    p['margin'] = round(34 - p['over'], 2); CH.append(p)
PTS += CH
# ---- test one: ridge over average natural grade (highest and lowest natural grade at the footprint edges)
edge = [(ground(x, z), x, z) for sp in foot for x, z in sp]
hi, lo = max(edge), min(edge)
slope = 100 * (hi[0] - lo[0]) / math.hypot(hi[1] - lo[1], hi[2] - lo[2])
avg = DATUM + (hi[0] + lo[0]) / 2
ridge_el = DATUM + max(v[2] for v in verts)
TEST1 = dict(hi=round(DATUM + hi[0], 2), lo=round(DATUM + lo[0], 2), hi_xz=[round(hi[1], 1), round(hi[2], 1)], lo_xz=[round(lo[1], 1), round(lo[2], 1)],
             avg=round(avg, 2), slope=round(slope, 1), limit_ft=30 if slope <= 15 else 36, ridge=round(ridge_el, 2),
             ridge_over=round(ridge_el - avg, 2))
TEST1['limit_el'] = round(avg + TEST1['limit_ft'], 2); TEST1['margin'] = round(TEST1['limit_el'] - ridge_el, 2)
# ---- bands for the map
BANDS = [(-99, 20, 'b0'), (20, 25, 'b1'), (25, 28, 'b2'), (28, 29, 'b3'), (29, 30, 'b4'), (30, 99, 'b5')]
band = lambda o: next(k for lo_, hi_, k in BANDS if lo_ <= o < hi_)
band_sf = collections.Counter(band(o) for _, o in cells.values())
if __name__ == '__main__':
    for p in PTS: print(p)
    print('vmax', vmax)
    print('test1', TEST1)
    print({k: v * C * C for k, v in band_sf.items()}, 'roof sf', len(cells) * C * C)
    print('cell max', max(o for _, o in cells.values()))
