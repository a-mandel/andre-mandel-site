"""sectelev-b: pull the north wing plan (walls, glass, interior placeholders, chimney, hearth) out of the pocket model
DATA for A5.0, clipped to the wing, and write plan_data.json next to this file. build.py inlines it into sectelev-b.js."""
import json, re
from pathlib import Path
HERE = Path(__file__).parent
ROOT = HERE.parents[3]                      # walsh/
html = (ROOT / 'index.html').read_text()
m = re.search(r'<script type="application/json" id="model-data">', html)
D, _ = json.JSONDecoder().raw_decode(html[m.end():])
X0, X1, Z0, Z1 = -23.0, 38.5, -17.0, 10.5    # the north wing and a little around it

def subpaths(d):
    out = []
    for sp in re.findall(r'M[^M]*', d):
        pts = [tuple(map(float, p)) for p in re.findall(r'(-?\d+\.?\d*)[ ,](-?\d+\.?\d*)', sp)]
        if pts: out.append((sp.strip(), pts))
    return out

def keep(d):
    r = []
    for sp, pts in subpaths(d):
        xs = [p[0] for p in pts]; zs = [p[1] for p in pts]
        if max(xs) >= X0 and min(xs) <= X1 and max(zs) >= Z0 and min(zs) <= Z1:
            r.append(sp)
    return ''.join(r)

def dedupe(d):   # the model paths carry runs of near duplicate points; drop repeats to keep the file small
    out = []
    for sp, pts in subpaths(d):
        q = []
        for p in pts:
            if not q or abs(p[0] - q[-1][0]) > 0.04 or abs(p[1] - q[-1][1]) > 0.04: q.append(p)
        if len(q) < 2: continue
        s = 'M' + ' L'.join(f'{x:.2f} {z:.2f}' for x, z in q)
        if sp.rstrip().endswith('Z'): s += 'Z'
        out.append(s)
    return ''.join(out)

def corners(b):   # box triangles to its 4 plan corners, ordered around
    s = sorted(set((round(b[i], 2), round(b[i + 2], 2)) for i in range(0, len(b), 3)))
    import math
    cx = sum(p[0] for p in s) / len(s); cz = sum(p[1] for p in s) / len(s)
    s.sort(key=lambda p: math.atan2(p[1] - cz, p[0] - cx))
    ys = [b[i + 1] for i in range(0, len(b), 3)]
    return {'p': s, 'y': [round(min(ys), 2), round(max(ys), 2)]}

L1 = D['plans']['levels']['rib']['l1']
f = D['interior']['furn']
out = {
    'box': [X0, Z0, X1 - X0, Z1 - Z0],
    'wall': dedupe(keep(L1['wall'])),
    'glass': dedupe(keep(L1['glass'])),
    'furn': [corners(f[i:i + 108]) for i in range(0, len(f), 108)],
    'hearth': corners(D['interior']['stone']),
    'chim': corners(D['chim']['ribN']['stone']),
    'info': {k: D['info']['rib'][k] for k in ('beam', 'kitchenRoof', 'kitchenEave', 'clereSill', 'clereTop', 'tip')},
    'chimTop': D['info']['chim']['ribN'],
    'wing': D['info']['wing'],
}
(HERE / 'plan_data.json').write_text(json.dumps(out, separators=(',', ':')))
print('wall', len(out['wall']), 'glass', len(out['glass']), 'furn', len(out['furn']))
