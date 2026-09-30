"""overlays-sectelev: the one precomputed piece the overlay needs beyond SHARED.
For each elevation and section view: the 30 ft over natural grade envelope as [h, el] pairs, and the height crew's
A1.4 points (sheets/height.js HT.pts) that the view can see. Everything else (grids, levels, tags, coords) is read
from window.SHARED in the page. Writes the /*OSE:DATA*/ block in sheets/overlays-sectelev.js.

Envelope, elevations: in each 1 ft column along the face, the roof cell with the least room under 30 ft sets the line
(natural grade right under that cell, plus 30), as build_drawings.envelope() and A1.4 do; past the roof it follows the
grade at the face. Sections: natural grade along the cut plane, plus 30 (as A1.4 and A3.1).
Run: python3 walsh/set/sheets/tools/overlays-sectelev/build.py   (about 20 s)"""
import json, math, re, sys, statistics
from pathlib import Path
HERE = Path(__file__).resolve().parent
SET = HERE.parents[2]
sys.path.insert(0, str(SET / 'sheets' / 'tools' / 'height'))
sys.path.insert(0, str(SET / 'draw'))
import calc as HC                    # height crew geometry: ground(), the 0.5 ft roof raster
import build_drawings as BD          # face grade profiles, the same frames as the renders

DATUM = 5990.0
SH = json.loads((SET / 'draw' / 'shared.json').read_text())
HT = json.loads(re.search(r'const HT = (\{.*?\});\n', (SET / 'sheets' / 'height.js').read_text()).group(1))
A31 = json.loads((SET / 'sheets' / 'assets' / 'sectelev-a' / 'render_meta.json').read_text())

VIEWS = {  # name: view letter, cut (axis, at, keep) or None, h range
    'A4.0': ('N', None), 'A4.1': ('E', None), 'A4.2': ('S', None), 'A4.3': ('W', None),
    'A3.0-2': ('S', ('z', -2.0, -1)), 'A3.0-1': ('W', ('x', 8.0, 1)),
    'A3.1-3': ('E', ('x', 34.0, -1)), 'A3.1-4': ('S', ('z', 52.0, -1)),
}
RIGHT = {'N': (-1, 0), 'S': (1, 0), 'E': (0, -1), 'W': (0, 1)}
hof = lambda v, x, z: x * RIGHT[v][0] + z * RIGHT[v][1]

def rng(name):
    m = SH['coords']['views'].get(name) or A31[name]
    return m['h0'], m['h1'], m['y1']

def kept(cut, x, z):
    if not cut: return True
    ax, at, keep = cut
    c = x if ax == 'x' else z
    return (c - at) * keep >= -0.01

def smooth(vals, k):
    out = []
    for i in range(len(vals)):
        w = vals[max(0, i - k):i + k + 1]
        out.append(sum(w) / len(w))
    return out

def elevation_env(name, v):
    h0, h1, _ = rng(name)
    face = BD.elevation_grade(v)                               # [h, model y], 0.5 ft
    fg = lambda h: min(face, key=lambda p: abs(p[0] - h))[1]
    cols = {}
    for (gx, gz), (y, over) in HC.cells.items():
        x, z = (gx + .5) * HC.C, (gz + .5) * HC.C
        k = math.floor(hof(v, x, z))
        if k not in cols or over > cols[k][1]:
            cols[k] = (y - over, over)                         # grade under the tightest cell
    hs = list(range(math.floor(h0), math.ceil(h1) + 1))
    g = [cols[k][0] if k in cols else None for k in hs]
    # median over five columns inside the roof, face grade past it, then a light blend
    med = []
    for i, k in enumerate(hs):
        w = [x for x in g[max(0, i - 2):i + 3] if x is not None]
        med.append(statistics.median(w) if (g[i] is not None and w) else fg(k + .5))
    sm = smooth(med, 3)
    # never draw the line under the tightest cell's own limit: smooth where there is room, exact where it is tight
    out = [max(a, g[i]) if g[i] is not None else a for i, a in enumerate(sm)]
    return [[k + .5, round(DATUM + y + 30, 2)] for k, y in zip(hs, out)]

def section_env(name, v, cut):
    h0, h1, _ = rng(name)
    ax, at, _k = cut
    out = []
    h = math.floor(h0)
    while h <= h1 + 1:
        if ax == 'z':
            x = h * RIGHT[v][0] if RIGHT[v][0] else None; z = at
        else:
            z = h * RIGHT[v][1] if RIGHT[v][1] else None; x = at
        out.append([h, round(DATUM + HC.ground(x, z) + 30, 2)])
        h += 1
    return out

pts = {p['key']: p for p in HT['pts']}
data = {'src': 'sheets/tools/overlays-sectelev/build.py', 'env': {}, 'pts': {}, 'a31': {}}
for name, (v, cut) in VIEWS.items():
    env = section_env(name, v, cut) if cut else elevation_env(name, v)
    data['env'][name] = [[round(h, 1), e] for h, e in env]
    vis = []
    for p in HT['pts']:
        if kept(cut, p['x'], p['z']):
            h = hof(v, p['x'], p['z'])
            h0, h1, _ = rng(name)
            if h0 + 1 <= h <= h1 - 1: vis.append(p['key'])
    data['pts'][name] = vis
data['heights'] = {k: {kk: p[kk] for kk in ('name', 'x', 'z', 'el', 'grade', 'over', 'margin', 'limit') if kk in p} for k, p in pts.items()}
data['test1'] = {k: HT['test1'][k] for k in ('avg', 'hi', 'lo', 'slope', 'limit_ft', 'ridge', 'limit_el', 'margin')}
for k, m in A31.items():   # A3.1 frames: sectelev-a places section 3 at sheet (1.9, 3.55), section 4 at (1.9, 11.55), 3/16 in
    x, y = (1.9, 3.55) if k.endswith('3') else (1.9, 11.55)
    s = 3 / 16
    data['a31'][k] = {'right': list(RIGHT[VIEWS[k][0]]), 'fx': [s, round(x - 1.25 - m['h0'] * s, 5)], 'fy': [-s, round(y - 0.5 + m['y1'] * s, 5)],
                      'img_field': [round(x - 1.25, 4), round(y - 0.5, 4), round(m['W'] / 200, 4), round(m['H'] / 200, 4)], 'h0': m['h0'], 'h1': m['h1']}

# report: where a roof point in view pokes over the drawn line (should be none)
for name in ('A4.0', 'A4.1', 'A4.2', 'A4.3'):
    v = VIEWS[name][0]
    env = dict((math.floor(h), e) for h, e in data['env'][name])
    worst = None
    for (gx, gz), (y, over) in HC.cells.items():
        x, z = (gx + .5) * HC.C, (gz + .5) * HC.C
        k = math.floor(hof(v, x, z))
        d = env.get(k, 1e9) - (DATUM + y)
        if worst is None or d < worst[0]: worst = (round(d, 2), k, round(DATUM + y, 2))
    print(name, 'least clearance, drawn envelope over roof:', worst, 'points', data['pts'][name])
for n in ('A3.0-2', 'A3.0-1', 'A3.1-3', 'A3.1-4'): print(n, 'points', data['pts'][n])

js = (SET / 'sheets' / 'overlays-sectelev.js')
src = js.read_text()
blob = json.dumps(data, separators=(',', ':'), ensure_ascii=False)
src2 = re.sub(r'/\*OSE:DATA\*/.*?/\*OSE:END\*/', lambda m: '/*OSE:DATA*/' + blob + '/*OSE:END*/', src, flags=re.S)
if src2 == src and '/*OSE:DATA*/' not in src: print('no data marker in overlays-sectelev.js')
js.write_text(src2)
print('wrote', len(blob) // 1024, 'KB of data')
