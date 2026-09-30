#!/usr/bin/env python3
"""sched-a crew: A7.0 Door schedule.

Reads the pocket model (walsh/index.html, model-data, ribbon scheme) and writes walsh/set/sheets/sched-a.js:
the key plan as inline SVG (level 1 walls and glass, lower level and level 2 over, terraces, the tree), the
exterior door openings found in the model with their tags, plus the sheet's JS from sched-a.template.js.

Door openings (model feet, x east, z south on the plan):
  101 entry pivot      the wood panel at x -5.14, z 35.7 to 39.7 (panels.wood), bridge vestibule, faces the tree
  102 family entry     link south face, z -6.06, under the extended kitchen roof (A.porch)
  103 garage to house  gear bay wall, x -39
  104, 105 overhead    gdoor.face, two 9 x 8 doors at z 15.37
  106 lift and slide   north wing south glass, z 8.1, the three east wing bays (x 20.48 to 35.82) onto the upper terrace
  107 lift and slide   bridge east glass, x 15.9, dining onto the upper terrace
  108 granny swing     granny west glass run, x -20.72, z 55.4 to 63.4
  001 lift and slide   lower level east glass, x 26.22, onto the stone patio
  002 lower swing      wood panel on the lower level south face, x 0.15 to 4.67
  201 lift and slide   primary suite east glass, x 26.1, onto the primary terrace
Run: python3 walsh/set/sheets/tools/sched-a/build.py
"""
import json, math, re
from pathlib import Path

HERE = Path(__file__).resolve().parent
SET = HERE.parents[2]
ROOT = SET.parents[1]
MODEL = ROOT / 'walsh' / 'index.html'
INK, ACC, TIMBER, PAPER = '#1b1a18', '#c07a2c', '#c98a52', '#f6f5f1'
NS = 'vector-effect="non-scaling-stroke"'


def load():
    for line in MODEL.read_text().splitlines():
        if 'id="model-data"' in line:
            return json.loads(re.sub(r'^<script[^>]*>', '', line).rsplit('</script>', 1)[0])
    raise SystemExit('model data not found')


D = load()
P = D['plans']
L1, L2 = P['levels']['rib']['l1'], P['levels']['rib']['l2']
TREE = P['site']['trees'][0]
NORTH = math.degrees(math.atan2(P['north'][0], -P['north'][1]))


def f2(v):
    return f'{v:.2f}'.rstrip('0').rstrip('.')


def simplify(d, tol=0.04):
    """drop repeated points the model's plan paths carry at every fillet"""
    out = []
    for sp in re.split(r'(?=M)', d):
        n = [float(v) for v in re.findall(r'-?\d+(?:\.\d+)?', sp)]
        pts = list(zip(n[0::2], n[1::2]))
        if len(pts) < 2:
            continue
        keep = [pts[0]]
        for p in pts[1:]:
            if abs(p[0] - keep[-1][0]) > tol or abs(p[1] - keep[-1][1]) > tol:
                keep.append(p)
        closed = sp.strip().endswith('Z') or sp.strip().endswith('z')
        out.append('M' + ' L'.join(f'{f2(x)} {f2(y)}' for x, y in keep) + (' Z' if closed else ''))
    return ''.join(out)


def P_(d, fill='none', stroke='none', w=0, op=1, dash=None, extra=''):
    s = f'<path d="{d}" fill="{fill}"'
    if stroke != 'none':
        s += f' stroke="{stroke}" stroke-width="{w}" {NS} stroke-linejoin="round" stroke-linecap="round"'
        if dash:
            s += f' stroke-dasharray="{dash}"'
    if op != 1:
        s += f' opacity="{op}"'
    return s + f' {extra}/>'


def circle_d(cx, cy, r, n=48, wob=0.03, seed=2):
    pts = []
    for k in range(n):
        a = 2 * math.pi * k / n
        rr = r * (1 + wob * math.sin(a * 5 + seed) + wob * 0.6 * math.sin(a * 9 + seed * 2.3))
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    return 'M' + ' L'.join(f'{f2(x)} {f2(y)}' for x, y in pts) + ' Z'


# ------------------------------------------------------------------ door symbols (plan, model feet)
def gap(a, b, w=1.15):
    """paper over the wall at the opening"""
    return f'<line x1="{f2(a[0])}" y1="{f2(a[1])}" x2="{f2(b[0])}" y2="{f2(b[1])}" stroke="{PAPER}" stroke-width="{w}" stroke-linecap="butt"/>'


def swing(hinge, closed_end, open_end):
    r = math.hypot(closed_end[0] - hinge[0], closed_end[1] - hinge[1])
    # sweep: pick the short arc
    cr = (closed_end[0] - hinge[0]) * (open_end[1] - hinge[1]) - (closed_end[1] - hinge[1]) * (open_end[0] - hinge[0])
    sw = 1 if cr > 0 else 0
    s = P_(f'M{f2(hinge[0])} {f2(hinge[1])} L{f2(open_end[0])} {f2(open_end[1])}', stroke=INK, w=1.1)
    s += P_(f'M{f2(closed_end[0])} {f2(closed_end[1])} A{f2(r)} {f2(r)} 0 0 {sw} {f2(open_end[0])} {f2(open_end[1])}', stroke=INK, w=0.5, op=0.75)
    return s


def slide(a, b, inward, n=4, dashed=False):
    """lift and slide: two tracks, panel joints"""
    ux, uy = b[0] - a[0], b[1] - a[1]
    L = math.hypot(ux, uy)
    nx, ny = inward
    s = ''
    for off, w in ((0.0, 1.0), (0.55, 1.0)):
        s += P_(f'M{f2(a[0] + nx * off)} {f2(a[1] + ny * off)} L{f2(b[0] + nx * off)} {f2(b[1] + ny * off)}', stroke=INK, w=w, dash='2 1.2' if dashed else None)
    for k in range(1, n):
        t = k / n
        px, py = a[0] + ux * t, a[1] + uy * t
        s += P_(f'M{f2(px)} {f2(py)} L{f2(px + nx * 0.55)} {f2(py + ny * 0.55)}', stroke=INK, w=0.7)
    return s


def overhead(a, b):
    return P_(f'M{f2(a[0])} {f2(a[1])} L{f2(b[0])} {f2(b[1])}', stroke=INK, w=1.3) + \
        P_(f'M{f2(a[0])} {f2(a[1] - 1.2)} L{f2(b[0])} {f2(b[1] - 1.2)}', stroke=INK, w=0.6, dash='2 1.5', op=0.7)


# door: id, mid (the orange dot), tag position, svg
DOORS = []
b = ''
# 101 entry pivot, west face of the vestibule at x -5.14, opens east into the vestibule
b += gap((-5.14, 35.7), (-5.14, 39.7))
b += swing((-5.14, 36.7), (-5.14, 39.7), (-2.14, 36.7))
b += P_('M-5.14 35.7 L-5.14 36.7', stroke=INK, w=1.1)
DOORS.append(('101', (-5.14, 38.2), (-13.5, 44.5)))
# 102 family entry, link south face z -6.06, opens north into the mudroom
b += gap((-31.5, -6.06), (-28.5, -6.06))
b += swing((-31.5, -6.06), (-28.5, -6.06), (-31.5, -9.06))
DOORS.append(('102', (-30.0, -6.06), (-30.0, 1.2)))
# 103 garage to house, the gear bay wall at x -39, opens east into the link
b += gap((-38.8, -12.5), (-38.8, -9.5))
b += swing((-38.8, -12.5), (-38.8, -9.5), (-35.8, -12.5))
DOORS.append(('103', (-38.8, -11.0), (-47.5, -8.5)))
# 104, 105 overhead, garage south face
for tag, x0, x1 in (('104', -61.08, -52.08), ('105', -50.08, -41.08)):
    b += gap((x0, 15.27), (x1, 15.27), 1.3)
    b += overhead((x0, 15.27), (x1, 15.27))
    DOORS.append((tag, ((x0 + x1) / 2, 15.27), ((x0 + x1) / 2, 22.5)))
# 106 living room to the upper terrace, south face z 7.94
b += gap((20.48, 7.94), (35.82, 7.94), 0.9)
b += slide((20.48, 7.94), (35.82, 7.94), (0, -1))
DOORS.append(('106', (28.15, 7.94), (29.5, 13.5)))
# 107 dining to the upper terrace, bridge east face x 15.9
b += gap((15.9, 20.0), (15.9, 36.0), 0.9)
b += slide((15.9, 20.0), (15.9, 36.0), (-1, 0))
DOORS.append(('107', (15.9, 28.0), (21.0, 35.5)))
# 108 granny suite, west face x -20.72, opens east
b += gap((-20.72, 57.0), (-20.72, 60.0), 0.9)
b += swing((-20.72, 57.0), (-20.72, 60.0), (-17.72, 57.0))
DOORS.append(('108', (-20.72, 58.5), (-28.5, 58.5)))
# 001 flex room to the lower patio, x 26.22
b += gap((26.22, 42.0), (26.22, 58.0), 0.9)
b += slide((26.22, 42.0), (26.22, 58.0), (-1, 0))
DOORS.append(('001', (26.22, 54.0), (33.5, 64.5)))
# 201 primary suite to the primary terrace, x 26.1, level 2 over 001 (dashed)
b += slide((26.62, 43.0), (26.62, 59.0), (1, 0), dashed=True)
DOORS.append(('201', (27.2, 46.0), (41.0, 40.5)))
# 002 lower level south door, the wood panel at x 0.15 to 4.67; leaf hinged at the east end, opens north
u = (0.951, -0.307); n = (-0.307, -0.951)
hinge = (4.67, 67.75); closed = (hinge[0] - 3.5 * u[0], hinge[1] - 3.5 * u[1]); opn = (hinge[0] + 3.5 * n[0], hinge[1] + 3.5 * n[1])
b += gap((0.15, 69.21), (4.67, 67.75), 0.9)
b += P_(f'M0.15 69.21 L{f2(closed[0])} {f2(closed[1])}', stroke=INK, w=1.1)
b += swing(hinge, closed, opn)
DOORS.append(('002', (2.4, 68.5), (6.5, 76.5)))
DOOR_SVG = b

# ------------------------------------------------------------------ key plan
VB = (-80.0, -21.0, 125.0, 100.0)


def keyplan():
    s = ''
    s += P_(simplify(P['foot']['rib']), fill='rgba(27,26,24,.035)')
    for t in P['terrace']:
        s += P_(t['d'], fill='none', stroke=INK, w=0.45, op=0.45)
    s += P_(simplify(L1['lower']), fill='rgba(27,26,24,.05)')
    s += P_(simplify(L2['prim']), stroke=INK, w=0.55, dash='3 2', op=0.5)
    s += P_(L2['deck'], stroke=TIMBER, w=0.8, dash='3 2', op=0.9)
    s += P_(circle_d(TREE[0], TREE[1], 13, 60), stroke=INK, w=0.5, dash='2.5 2', op=0.5)
    s += f'<circle cx="{TREE[0]}" cy="{TREE[1]}" r="0.9" fill="{ACC}" opacity=".85"/>'
    s += P_(simplify(L1['wall']), fill=INK, stroke=INK, w=0.25)
    s += P_(simplify(L1['glass']), fill=PAPER, stroke=INK, w=0.4)
    s += DOOR_SVG
    # leaders from each tag to its door
    for tag, (mx, mz), (tx, tz) in DOORS:
        dx, dz = mx - tx, mz - tz
        L = math.hypot(dx, dz)
        r = 2.25
        sx, sz = tx + dx / L * r, tz + dz / L * r
        cx, cz = sx + (mx - sx) * 0.2, sz + (mz - sz) * 0.85
        s += P_(f'M{f2(sx)} {f2(sz)} Q{f2(cx)} {f2(cz)} {f2(mx)} {f2(mz)}', stroke=INK, w=0.5, op=0.8)
        s += f'<circle cx="{f2(mx)}" cy="{f2(mz)}" r="0.55" fill="{ACC}"/>'
    x0, y0, w, h = VB
    return (f'<svg xmlns="http://www.w3.org/2000/svg" class="dsvg" viewBox="{f2(x0)} {f2(y0)} {f2(w)} {f2(h)}" '
            f'preserveAspectRatio="xMidYMid meet" aria-hidden="true">{s}</svg>')


def frac(x, z):
    return [round((x - VB[0]) / VB[2], 5), round((z - VB[1]) / VB[3], 5)]


KEY = {
    'svg': keyplan(),
    'ar': VB[2] / VB[3],
    'north': round(NORTH, 1),
    'tags': [{'n': t, 'p': frac(*tp)} for t, _, tp in DOORS],
    'labels': [
        {'t': 'Garage', 'p': frac(-57.5, -4.0)},
        {'t': 'North wing', 'p': frac(8.0, -4.0)},
        {'t': 'Bridge', 'p': frac(8.0, 17.0)},
        {'t': 'Upper terrace', 'p': frac(27.5, 17.5)},
        {'t': 'Granny', 's': 'suite, main level', 'p': frac(-10.0, 64.0)},
        {'t': 'Lower level', 's': 'primary suite over', 'p': frac(12.5, 55.5)},
        {'t': 'Front court', 'p': frac(-26.0, 30.0)},
    ],
}

tpl = (HERE / 'sched-a.template.js').read_text()
out = tpl.replace('__KEY__', json.dumps(KEY, separators=(',', ':')))
(SET / 'sheets' / 'sched-a.js').write_text(out)
print('wrote sched-a.js', len(out), 'bytes; north', round(NORTH, 1))
