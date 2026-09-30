"""height crew: A1.4 Building height, method and calculation. Writes walsh/set/sheets/height.js.
   Run from anywhere:  python3 walsh/set/sheets/tools/height/build_height.py
   Inputs: walsh/index.html (model DATA, terrain), walsh/set/draw/calcs.json. Geometry and numbers in calc.py beside this
   file; layout, method diagrams and type in height.src.js. FA grade, about, confirm on survey."""
import json, math
from calc import *

INK, ACC, PAPER = '#1b1a18', '#c07a2c', '#f6f5f1'
NS = 'vector-effect="non-scaling-stroke"'
f2 = lambda v: f'{v:.2f}'.rstrip('0').rstrip('.')
poly_d = lambda pts, close=True: 'M' + ' L'.join(f'{f2(x)} {f2(y)}' for x, y in pts) + (' Z' if close else '')
def frac(vb, x, y): return [round((x - vb[0]) / vb[2], 4), round((y - vb[1]) / vb[3], 4)]

# ------------------------------------------------------------------ 1. roof over natural grade map, registers with A2.3 (same plan frame)
PVB = (-78.0, -23.5, 119.2, 103.0)
TONE = {'b0': ('#efe7da', 1), 'b1': ('#e7d7bf', 1), 'b2': ('#ddc19c', 1), 'b3': ('#d9a46a', 1), 'b4': (ACC, 1), 'b5': ('#8a2a12', 1)}
def svg_map():
    rects = []
    for gz in sorted({c[1] for c in cells}):
        row = sorted(c[0] for c in cells if c[1] == gz)
        run = None
        for gx in row:
            k = band(cells[(gx, gz)][1])
            if run and run[2] == k and run[1] == gx: run[1] = gx + 1; continue
            if run: rects.append((run[0], gz, run[1] - run[0], run[2]))
            run = [gx, gx + 1, k]
        if run: rects.append((run[0], gz, run[1] - run[0], run[2]))
    body = ''.join(f'<rect x="{f2(x * C)}" y="{f2(z * C)}" width="{f2(w * C)}" height="{C + .03:.2f}" fill="{TONE[k][0]}"/>' for x, z, w, k in rects)
    OUT = subpaths(ROOF['outline'])
    clip = ''.join(f'<path d="{poly_d(sp)}"/>' for sp in OUT)
    b = [f'<defs><clipPath id="ht-roofc">{clip}</clipPath>'
         f'<pattern id="ht-ch" width="1.2" height="1.2" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><line x1="0" y1="0" x2="0" y2="1.2" stroke="{INK}" stroke-width="0.35" opacity=".55" {NS}/></pattern></defs>']
    b.append(f'<path d="{ROOF["cons"]}" fill="none" stroke="{INK}" stroke-width="0.45" opacity=".22" {NS}/>')
    b.append(f'<g clip-path="url(#ht-roofc)">{body}</g>')
    b.append(f'<path d="{ROOF["joist"]}" fill="none" stroke="{INK}" stroke-width="0.35" opacity=".2" {NS}/>')
    b.append(f'<path d="{ROOF["glulam"]}" fill="none" stroke="{INK}" stroke-width="0.5" opacity=".5" {NS}/>')
    b.append(f'<path d="{ROOF["beam"]}" fill="{INK}" fill-opacity=".3" stroke="{INK}" stroke-width="0.45" opacity=".7" {NS}/>')
    b.append(f'<path d="{P["foot"]["rib"]}" fill="none" stroke="{INK}" stroke-width="0.55" stroke-dasharray="2 3" opacity=".5" {NS}/>')
    b.append(''.join(f'<path d="{poly_d(sp)}" fill="none" stroke="{INK}" stroke-width="1.3" stroke-linejoin="round" {NS}/>' for sp in OUT))
    b.append(f'<path d="{ROOF["chim"]}" fill="url(#ht-ch)" stroke="{INK}" stroke-width="0.9" {NS}/>')
    tx, tz, _ = P['site']['trees'][0]
    b.append(f'<circle cx="{tx}" cy="{tz}" r="13" fill="none" stroke="{INK}" stroke-width="0.6" stroke-dasharray="3 2" opacity=".5" {NS}/>'
             f'<circle cx="{tx}" cy="{tz}" r="0.55" fill="{INK}"/>')
    # critical points: a small cross, orange where within 1 ft of 30
    for p in PTS:
        hot = p['margin'] < 1 and 'chim' not in p['key']
        col = ACC if hot else INK
        x, z = p['x'], p['z']
        b.append(f'<path d="M{f2(x - 1.3)} {f2(z)} H{f2(x + 1.3)} M{f2(x)} {f2(z - 1.3)} V{f2(z + 1.3)}" stroke="{col}" stroke-width="1.1" {NS}/>')
    return f'<svg xmlns="http://www.w3.org/2000/svg" class="ht-svg" viewBox="{" ".join(f2(v) for v in PVB)}" preserveAspectRatio="xMidYMid meet" aria-hidden="true">{"".join(b)}</svg>'

# ------------------------------------------------------------------ 2. sections: cut the model's meshes with a vertical plane
CATS = [('roof', [D['rib']['roof'], D['wing']['roof'], D['wing']['rear']], 1.35, 1.0),
        ('wall', [D['rib']['wall'], D['wing']['wall']], 0.9, 0.9),
        ('glass', [D['rib']['glass'], D['wing']['glass']], 0.5, 0.55),
        ('timber', [D['rib']['glulam'], D['wing']['glulam'], D['rib']['beam'], D['wing']['beam']], 0.5, 0.6),
        ('deck', [D['rib']['deck'], D['wing']['deck']], 0.6, 0.7),
        ('slab', [D['slab']], 0.9, 0.9),
        ('chim', [D['chim']['rib']['stone'], D['chim']['ribN']['stone'], D['chim']['rib']['cap'], D['chim']['ribN']['cap']], 0.9, 0.9)]
def cut(O, u, s0, s1):
    n = (-u[1], u[0])
    segs = {}
    for name, arrs, w, op in CATS:
        out = []
        for arr in arrs:
            for t in tris(arr):
                d = [(p[0] - O[0]) * n[0] + (p[2] - O[1]) * n[1] for p in t]
                pts = []
                for i in range(3):
                    a, bb = t[i], t[(i + 1) % 3]; da, db = d[i], d[(i + 1) % 3]
                    if (da < 0) != (db < 0):
                        k = da / (da - db)
                        x = a[0] + k * (bb[0] - a[0]); y = a[1] + k * (bb[1] - a[1]); z = a[2] + k * (bb[2] - a[2])
                        pts.append(((x - O[0]) * u[0] + (z - O[1]) * u[1], y))
                if len(pts) == 2 and max(pts[0][0], pts[1][0]) >= s0 and min(pts[0][0], pts[1][0]) <= s1:
                    out.append(pts)
        segs[name] = out
    return segs
def section(key, O, u, s0, s1, e0, e1, pt, cutnote, beyond=None):
    """O plan origin (x, z), u plan unit direction (s increases to the right); e0 e1 elevation range (ft over DATUM)"""
    segs = cut(O, u, s0, s1)
    W, H = s1 - s0, e1 - e0
    Y = lambda y: f2(e1 - y)            # svg y, 0 at the top
    X = lambda s: f2(s - s0)
    gr = [(s, ground(O[0] + s * u[0], O[1] + s * u[1])) for s in [s0 + i * 0.5 for i in range(int(W / 0.5) + 1)]]
    b = [f'<defs><clipPath id="ht-{key}c"><rect x="0" y="0" width="{f2(W)}" height="{f2(H)}"/></clipPath>'
         f'<pattern id="ht-{key}e" width="1.6" height="1.6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><line x1="0" y1="0" x2="0" y2="1.6" stroke="{INK}" stroke-width="0.35" opacity=".3" {NS}/></pattern></defs><g clip-path="url(#ht-{key}c)">']
    # earth under natural grade, lightly hatched, fading down
    earth = 'M' + ' L'.join(f'{X(s)} {Y(g)}' for s, g in gr) + f' L{X(s1)} {f2(H)} L{X(s0)} {f2(H)} Z'
    b.append(f'<path d="{earth}" fill="url(#ht-{key}e)"/>')
    # level datums, faint
    for el, lab in ((7.5, 'L1'), (19.5, 'L2')):
        pass
    for name, arrs, w, op in CATS:
        if not segs[name]: continue
        col = INK
        d = ''.join(f'M{X(a[0])} {Y(a[1])} L{X(c[0])} {Y(c[1])}' for a, c in segs[name])
        b.append(f'<path d="{d}" fill="none" stroke="{col}" stroke-width="{w}" opacity="{op}" stroke-linecap="round" {NS}/>')
    # the roof edge beyond the cut, where the point sits, drawn lighter
    if beyond:
        bs = cut(beyond, u, s0, s1)['roof']
        d = ''.join(f'M{X(a[0])} {Y(a[1])} L{X(c[0])} {Y(c[1])}' for a, c in bs)
        b.append(f'<path d="{d}" fill="none" stroke="{INK}" stroke-width="0.6" opacity=".45" stroke-dasharray="3 2" {NS}/>')
    # foundation, schematic: from the ends of the floor down to a foot under grade
    sl = [p for seg in segs['slab'] for p in seg]
    if sl:
        lo_s, hi_s = min(p[0] for p in sl), max(p[0] for p in sl); fy = min(p[1] for p in sl)
        for sx in (lo_s, hi_s):
            gy = ground(O[0] + sx * u[0], O[1] + sx * u[1]) - 1.0
            b.append(f'<path d="M{X(sx)} {Y(fy)} V{Y(gy)}" stroke="{INK}" stroke-width="0.7" stroke-dasharray="2 2" opacity=".6" {NS}/>')
    # natural grade line
    b.append(f'<path d="{"M" + " L".join(f"{X(s)} {Y(g)}" for s, g in gr)}" fill="none" stroke="{INK}" stroke-width="1.2" {NS}/>')
    # the 30 ft envelope, dashed orange, parallel to grade
    b.append(f'<path d="{"M" + " L".join(f"{X(s)} {Y(g + 30)}" for s, g in gr)}" fill="none" stroke="{ACC}" stroke-width="1.1" stroke-dasharray="5 3" {NS}/>')
    b.append('</g>')
    # the measured dimension at the point: from grade straight up to the roof
    ps = (pt['x'] - O[0]) * u[0] + (pt['z'] - O[1]) * u[1]
    g, r = pt['grade'] - DATUM, pt['el'] - DATUM
    x = X(ps)
    b.append(f'<path d="M{x} {Y(g)} V{Y(r)}" stroke="{ACC}" stroke-width="1.2" {NS}/>')
    for yy in (g, r):
        b.append(f'<path d="M{f2(ps - s0 - .9)} {Y(yy - .9)} L{f2(ps - s0 + .9)} {Y(yy + .9)}" stroke="{ACC}" stroke-width="1.2" {NS}/>')
    b.append(f'<circle cx="{x}" cy="{Y(r)}" r=".45" fill="{ACC}"/>')
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" class="ht-svg" viewBox="0 0 {f2(W)} {f2(H)}" preserveAspectRatio="none" aria-hidden="true">{"".join(b)}</svg>'
    # grade at both ends and the envelope label anchor
    return dict(svg=svg, w=W, h=H, s0=s0, e1=e1, ps=round(ps, 2), el0=DATUM + e0, el1=DATUM + e1,
                f_pt=[round((ps - s0) / W, 4), round((e1 - r) / H, 4)], f_gr=[round((ps - s0) / W, 4), round((e1 - g) / H, 4)],
                f_mid=[round((ps - s0) / W, 4), round((e1 - (g + r) / 2) / H, 4)],
                f_env=[round((W - 1.5) / W, 4), round((e1 - (gr[-4][1] + 30)) / H, 4)],
                f_envL=[round(1.5 / W, 4), round((e1 - (gr[3][1] + 30)) / H, 4)],
                f_grd=[round((W - 1.5) / W, 4), round((e1 - gr[-4][1]) / H, 4)],
                cut=cutnote)
TIP = next(p for p in PTS if p['key'] == 'tip'); SC = next(p for p in PTS if p['key'] == 'south')
S1 = section('s1', (35.0, 0.0), (0.0, 1.0), -21.0, 19.0, -3.0, 40.0, TIP, 'Cut 2 ft inside the tip, the tip edge beyond dashed', beyond=(36.9, 0.0))
edge = (-0.9497, 0.3133)
O2 = (SC['x'] + 3.0 * edge[0], SC['z'] + 3.0 * edge[1])
Ob = (SC['x'] + 0.1 * edge[0], SC['z'] + 0.1 * edge[1])
S2 = section('s2', O2, (0.3133, 0.9497), -16.0, 30.0, -3.0, 40.0, SC, 'Cut square to the south wing, 3 ft inside the corner, the corner beyond dashed', beyond=Ob)

# ------------------------------------------------------------------ 3. shared.json check (if the data builder has written it)
shared = SET / 'draw' / 'shared.json'
SH = None
if shared.exists():
    try: SH = json.loads(shared.read_text()).get('heights')
    except Exception as e: SH = {'error': str(e)}

OUT = dict(
    pts=[dict(p, f=frac(PVB, p['x'], p['z'])) for p in PTS], test1=TEST1,
    test1_f=dict(hi=frac(PVB, *TEST1['hi_xz']), lo=frac(PVB, *TEST1['lo_xz'])),
    bands={k: round(band_sf.get(k, 0) * C * C) for k in ('b0', 'b1', 'b2', 'b3', 'b4', 'b5')}, roof_sf=round(len(cells) * C * C),
    calcs=CALCS['heights'], tree_f=frac(PVB, P['site']['trees'][0][0], P['site']['trees'][0][1]),
    map=svg_map(), pvb=PVB,
    s1={k: v for k, v in S1.items()}, s2={k: v for k, v in S2.items()},
)
src = (HERE / 'height.src.js').read_text()
js = src.replace('/*@DATA@*/null', json.dumps(OUT, ensure_ascii=False))
(SET / 'sheets' / 'height.js').write_text(js)
print('wrote height.js', len(js) // 1024, 'KB')
for p in PTS: print(f"{p['name']:28s} el {p['el']:.2f} grade {p['grade']:.2f} over {p['over']:.2f} margin {p['margin']:.2f}")
print('test one', TEST1)
print('bands sf', OUT['bands'], 'roof', OUT['roof_sf'])
print('shared.json heights:', json.dumps(SH)[:1500] if SH else 'not present')
