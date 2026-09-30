#!/usr/bin/env python3
"""Walsh living set: real drawings from the pocket model.

Builds every drawing sheet the living set (walsh/set/v2.html) shows between the cover and the details:
  A1.2 site plan, A2.1 level 1, A2.2 level 2, A2.3 roof (vector SVG from the model's own plan paths),
  A3.0 two sections and A4.0 to A4.3 four elevations (orthographic renders of the model's three.js scene,
  exported by the gated ?draw hook in walsh/index.html, at 200 px per inch of sheet),
  calcs.json (areas, coverage, impervious) and drawings.js (everything the sheets place, in sheet inches).

Run from anywhere:  python3 walsh/set/draw/build_drawings.py [--no-render]
It serves the repo root on a free port for the renders. Ribbon scheme throughout.
"""
import asyncio, base64, bisect, functools, http.server, json, math, re, socketserver, sys, threading
from pathlib import Path

HERE = Path(__file__).resolve().parent   # land-a copy, never writes: build() is not called
ROOT = HERE.parents[4]   # land-a copy: sheets/tools/land-a sits two levels deeper than draw/
MODEL = ROOT / 'walsh' / 'index.html'
PPI = 200                      # raster output, px per inch of sheet
DATUM = 5990.0                 # model y 0 = elevation 5990.0
LOT_SF = 27440                 # about 0.63 acres, from the prior listing (the model's lot polygon is clipped by the terrain)
WALK_ALLOW = 200               # walks, an allowance until they are drawn
INK, ACC, TIMBER, PAPER = '#1b1a18', '#c07a2c', '#c98a52', '#f6f5f1'

# ------------------------------------------------------------------ data
def load_data():
    for line in MODEL.read_text().splitlines():
        if 'id="model-data"' in line:
            return json.loads(re.sub(r'^<script[^>]*>', '', line).rsplit('</script>', 1)[0])
    raise SystemExit('model data not found')

D = load_data()
P = D['plans']
L1, L2 = P['levels']['rib']['l1'], P['levels']['rib']['l2']
ROOF = P['roof']['rib']
SITE = P['site']

def nums(s):
    return [float(v) for v in re.findall(r'-?\d+(?:\.\d+)?', s)]

def subpaths(d):
    out = []
    for sp in re.split(r'(?=M)', d):
        n = nums(sp)
        if len(n) >= 4:
            out.append(list(zip(n[0::2], n[1::2])))
    return out

def area(poly):
    a = 0.0
    for i in range(len(poly)):
        x1, y1 = poly[i]; x2, y2 = poly[(i + 1) % len(poly)]
        a += x1 * y2 - x2 * y1
    return a / 2

def path_area(d):
    return abs(sum(area(p) for p in subpaths(d)))

def pip(x, y, poly):
    c = False
    for i in range(len(poly)):
        x1, y1 = poly[i]; x2, y2 = poly[i - 1]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            c = not c
    return c

def bbox(pts):
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    return min(xs), min(ys), max(xs), max(ys)

# terrain: a 3 ft grid, x -125 to 70, z -44 to 124
TX0, TZ0, TS = -125.0, -44.0, 3.0
_grid = {}
T = D['site']['terrain']
for i in range(0, len(T), 3):
    _grid[(round((T[i] - TX0) / TS), round((T[i + 2] - TZ0) / TS))] = T[i + 1]
NX = max(k[0] for k in _grid); NZ = max(k[1] for k in _grid)

def ground(x, z):
    fx = min(max((x - TX0) / TS, 0), NX - 1e-6); fz = min(max((z - TZ0) / TS, 0), NZ - 1e-6)
    i, j = int(fx), int(fz); u, v = fx - i, fz - j
    g = lambda a, b: _grid.get((a, b), _grid.get((i, j)))
    return (g(i, j) * (1 - u) * (1 - v) + g(i + 1, j) * u * (1 - v) + g(i, j + 1) * (1 - u) * v + g(i + 1, j + 1) * u * v)

# ------------------------------------------------------------------ calcs
FOOT = subpaths(P['foot']['rib'])
TERR = {t['k']: subpaths(t['d'])[0] for t in P['terrace']}
LEVEL_POLYS = [(subpaths(L1['lower']), 2.5), (subpaths(L1['main']), 7.5), (subpaths(L1['gar']), 10.0)]

def drive_polygon():
    dr = D['drive']
    pl = lambda k: [(dr[k][i], dr[k][i + 2]) for i in range(0, len(dr[k]), 3)]
    line1 = pl(2) + pl(6)[1:] + pl(7)[1:]           # road flare, north edge to the garage apron corner
    line2 = pl(1) + pl(5)[1:] + pl(4)[::-1][1:]     # road flare, south edge and its turn
    return line1 + line2[::-1]

DRIVE = drive_polygon()
APRON = [(-63.57, 15.27), (-39.0, 15.27), (-39.0, 39.27), (-63.57, 39.27)]   # allowance: a 24 ft backup apron at the doors

def r10(v):
    return int(round(v / 10.0) * 10)

def calcs():
    A = P['areas']['rib']
    roof = path_area(ROOF['outline']); foot = path_area(P['foot']['rib'])
    drive = abs(area(DRIVE)); apron = abs(area(APRON))
    patio = abs(area(TERR['stone'])); deck = abs(area(TERR['deck'])); pdeck = path_area(L2['deck'])
    wx0, wz0, wx1, wz1 = bbox([p for sp in subpaths(L1['wall']) for p in sp])
    imperv = roof + drive + apron + patio + WALK_ALLOW
    c = {
        'note': 'About, gross to the outside face of walls. FA accuracy, confirm on survey.',
        'levels': {
            'main': {'label': 'Main level', 'el': 5997.5, 'sf': round(path_area(L1['main']))},
            'lower': {'label': 'Lower level, south wing', 'el': 5992.5, 'sf': round(path_area(L1['lower']))},
            'primary': {'label': 'Primary suite, level 2', 'el': 6004.0, 'sf': round(path_area(L2['prim']))},
        },
        'level1_conditioned': round(path_area(L1['main'])) + round(path_area(L1['lower'])),
        'level2_conditioned': round(path_area(L2['prim'])),
        'conditioned': round(path_area(L1['main'])) + round(path_area(L1['lower'])) + round(path_area(L2['prim'])),
        'model_check': A,
        'garage': round(path_area(L1['gar'])),
        'decks': {'upper_terrace': round(deck), 'primary_terrace': round(pdeck)},
        'patio_stone': round(patio),
        'overall_ft': [D['info']['overall']['w'], D['info']['overall']['d']],
        'footprint': round(foot),
        'roof_footprint': round(roof),
        'drive': round(drive), 'apron_allowance': round(apron), 'walks_allowance': WALK_ALLOW,
        'lot_sf': LOT_SF, 'lot_ac': round(LOT_SF / 43560, 2),
        'lot_note': 'Lot area about, from the prior listing, confirm on survey',
        'coverage_pct': round(100 * roof / LOT_SF, 1),
        'impervious_sf': round(imperv),
        'impervious_pct': round(100 * imperv / LOT_SF, 1),
        'heights': {'tip': 6023.0, 'tip_over_grade': D['info']['rib']['tipOver'], 'beam': 6012.0, 'garage_roof': 6016.5, 'limit_ft': 30},
    }
    return c

C = calcs()
fmt = lambda v: f'{int(round(v)):,}'

# ------------------------------------------------------------------ svg helpers
def f2(v):
    return f'{v:.2f}'.rstrip('0').rstrip('.')

def path(d, **a):
    at = ' '.join(f'{k.replace("_", "-")}="{v}"' for k, v in a.items())
    return f'<path d="{d}" {at}/>'

NS = 'vector-effect="non-scaling-stroke"'

def P_(d, fill='none', stroke='none', w=0, op=1, dash=None, extra=''):
    s = f'<path d="{d}" fill="{fill}"'
    if stroke != 'none':
        s += f' stroke="{stroke}" stroke-width="{w}" {NS} stroke-linejoin="round"'
        if dash: s += f' stroke-dasharray="{dash}"'
    if op != 1: s += f' opacity="{op}"'
    return s + f' {extra}/>'

def poly_d(pts, close=True):
    return 'M' + ' L'.join(f'{f2(x)} {f2(y)}' for x, y in pts) + (' Z' if close else '')

def circle_d(cx, cy, r, n=48, wob=0.0, seed=1):
    pts = []
    for k in range(n):
        a = 2 * math.pi * k / n
        rr = r * (1 + wob * math.sin(a * 5 + seed) + wob * 0.6 * math.sin(a * 9 + seed * 2.3))
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    return poly_d(pts)

def defs(pid):
    return f'''<defs>
<pattern id="{pid}-deck" width="0.5" height="0.5" patternUnits="userSpaceOnUse"><line x1="0" y1="0.25" x2="0.5" y2="0.25" stroke="{TIMBER}" stroke-width="0.5" {NS}/></pattern>
<pattern id="{pid}-deckR" width="0.5" height="0.5" patternUnits="userSpaceOnUse" patternTransform="rotate(-18)"><line x1="0" y1="0.25" x2="0.5" y2="0.25" stroke="{TIMBER}" stroke-width="0.5" {NS}/></pattern>
<pattern id="{pid}-flag" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(8)"><path d="M0 0 L2.6 0.3 L3.1 2.4 L0.4 2.8 Z M3.1 2.4 L6 2.1 M2.6 0.3 L4.4 0 M4.4 0 L6 0.6 M4.4 0 L4.7 2.2 M0.4 2.8 L0 6 M0.4 2.8 L2.2 3.4 L2.9 6 M2.2 3.4 L5.1 4.1 L6 6 M3.1 2.4 L2.2 3.4 M5.1 4.1 L4.7 2.2" fill="none" stroke="{INK}" stroke-width="0.4" opacity="0.55" {NS}/></pattern>
<pattern id="{pid}-dots" width="2" height="2" patternUnits="userSpaceOnUse"><circle cx="1" cy="1" r="0.12" fill="{INK}" opacity="0.4"/></pattern>
<pattern id="{pid}-hatch" width="1.5" height="1.5" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><line x1="0" y1="0" x2="0" y2="1.5" stroke="{INK}" stroke-width="0.4" opacity="0.4" {NS}/></pattern>
</defs>'''

def svg_wrap(vb, body, pid, clip=None):
    x0, y0, w, h = vb
    cl = ''
    if clip:
        cl = f'<clipPath id="{pid}-clip"><rect x="{f2(clip[0])}" y="{f2(clip[1])}" width="{f2(clip[2])}" height="{f2(clip[3])}"/></clipPath>'
    return (f'<svg xmlns="http://www.w3.org/2000/svg" class="dsvg" viewBox="{f2(x0)} {f2(y0)} {f2(w)} {f2(h)}" preserveAspectRatio="xMidYMid meet" '
            f'role="img" aria-hidden="true">{defs(pid)}{cl}{body}</svg>')

# ------------------------------------------------------------------ plan registration (A2.1, A2.2, A2.3 share it)
S316 = 3 / 16
PVB = (-78.0, -23.5, 119.2, 103.0)                    # plan view box in feet
PSX = lambda x: 31.7 + (x - 40.4) * S316               # feet to sheet inches: the stone patio edge clears the title block rule
PSY = lambda z: 2.6 + (z + 16.6) * S316
PVIEW = dict(x=PSX(PVB[0]), y=PSY(PVB[1]), w=PVB[2] * S316, h=PVB[3] * S316)

def frac(vb, x, y):
    return [round((x - vb[0]) / vb[2], 5), round((y - vb[1]) / vb[3], 5)]

TREE = SITE['trees'][0]      # the signature tree, front court

def dim_h(x0, x1, z, text_side=-1, ext_from=None):
    """a horizontal dimension string in feet: ticks, extension lines; returns svg and the label spot"""
    t = 0.9
    s = P_(f'M{f2(x0 - 1.5)} {f2(z)} H{f2(x1 + 1.5)}', stroke=INK, w=0.6)
    for x in (x0, x1):
        s += P_(f'M{f2(x - t)} {f2(z + t)} L{f2(x + t)} {f2(z - t)}', stroke=INK, w=1.1)
        if ext_from is not None:
            s += P_(f'M{f2(x)} {f2(ext_from - 1)} V{f2(z - 1.2)}', stroke=INK, w=0.45, op=0.7)
    return s, ((x0 + x1) / 2, z + text_side * 1.3)

def ftin(v):
    f = int(math.floor(v + 1e-6)); i = round((v - f) * 12)
    if i == 12: f += 1; i = 0
    return f"{f}′ {i}″"

def section_marks():
    """section cut lines on the level 1 plan; the bubbles are labels"""
    s = ''
    # section 1: x = 8, looking east (arrow points east)
    s += P_('M8 -22.4 V-12 M8 79 V75', stroke=INK, w=1.3)
    s += P_('M8 -12 V75', stroke=INK, w=0.5, dash='9 3 2 3', op=0.55)
    s += P_('M8 -22.4 H11.8 M8 79 H11.8', stroke=INK, w=1.3)
    s += P_('M11.6 -23.3 L13.4 -22.4 L11.6 -21.5 Z M11.6 78.1 L13.4 79 L11.6 79.9 Z', fill=INK)
    # section 2: z = -2, looking north (arrow points north)
    s += P_('M-81.5 -2 H-77 M40.9 -2 H38.6', stroke=INK, w=1.3)
    s += P_('M-77 -2 H38.6', stroke=INK, w=0.5, dash='9 3 2 3', op=0.55)
    s += P_('M-81.5 -2 V-5.4 M40.9 -2 V-5.4', stroke=INK, w=1.3)
    s += P_('M-82.4 -5.2 L-81.5 -7 L-80.6 -5.2 Z M40 -5.2 L40.9 -7 L41.8 -5.2 Z', fill=INK)
    return s

# ------------------------------------------------------------------ A2.1 level 1
def level1():
    pid = 'a21'
    b = ''
    b += P_(L1['cons'], stroke=INK, w=0.45, op=0.3)
    b += P_(ROOF['outline'], stroke=INK, w=0.6, dash='5 3', op=0.45)                       # roof above, dashed
    b += P_(L1['main'], fill='rgba(27,26,24,.035)')
    b += P_(L1['lower'], fill='rgba(27,26,24,.05)') + P_(L1['lower'], fill=f'url(#{pid}-hatch)')
    b += P_(L1['gar'], fill=f'url(#{pid}-dots)')
    for t in P['terrace']:
        b += P_(t['d'], fill=f'url(#{pid}-deck)' if t['k'] == 'deck' else f'url(#{pid}-flag)', stroke=INK, w=0.7)
    b += P_(P['pit'], fill=PAPER, stroke=INK, w=0.6)
    b += P_(circle_d(TREE[0], TREE[1], 13, 60, 0.03, 2), stroke=INK, w=0.6, dash='3 2', op=0.6)
    b += f'<circle cx="{TREE[0]}" cy="{TREE[1]}" r="0.55" fill="{ACC}"/>'
    b += section_marks()
    b += P_(L1['wall'], fill=INK, stroke=INK, w=0.35)
    b += P_(L1['glass'], fill=PAPER, stroke=INK, w=0.55)
    ds, dl = dim_h(-20.58, 35.82, -19.4, -1, ext_from=-15.06)
    dl = (24.0, dl[1])
    b += ds
    labels = [
        dict(p=frac(PVB, *dl), t=ftin(35.82 + 20.58), k='dim'),
        dict(p=frac(PVB, 9.0, -6.0), t='Main level · 5997.5', s=f"about {fmt(C['levels']['main']['sf'])} sf, north wing, bridge and granny wing", k='tag'),
        dict(p=frac(PVB, -57.4, -3.6), t='Garage and gear bay · 6000.0', s=f"about {fmt(C['garage'])} sf", k='tag'),
        dict(p=frac(PVB, 13.0, 58.0), t='Lower level · 5992.5', s=f"5 ft down, about {fmt(C['levels']['lower']['sf'])} sf", k='tag'),
        dict(p=frac(PVB, 8.0, 27.5), t='Bridge', s='dining in the middle', k='room'),
        dict(p=frac(PVB, -10.4, 63.5), t='Granny suite', s='main level', k='room'),
        dict(p=frac(PVB, -30.0, -10.3), t='Entry', k='room'),
        dict(p=frac(PVB, 26.0, 14.0), t='Upper terrace · 5997.25', s=f"cedar deck, about {fmt(C['decks']['upper_terrace'])} sf", k='room'),
        dict(p=frac(PVB, 32.5, 48.0), t='Lower patio', s=f"stone, about {fmt(C['patio_stone'])} sf", k='room'),
        dict(p=frac(PVB, 5.9, -22.4), t='1', k='bub', s='A3.0'),
        dict(p=frac(PVB, -84.0, -2.0), t='2', k='bub', s='A3.0'),
    ]
    return svg_wrap(PVB, b, pid), labels

# ------------------------------------------------------------------ A2.2 level 2
def level2():
    pid = 'a22'
    b = ''
    b += P_(L2['cons'], stroke=INK, w=0.45, op=0.3)
    b += P_(L2['below'], fill='rgba(27,26,24,.02)', stroke=INK, w=0.6, dash='4 3', op=0.55)          # level 1 below
    b += P_(ROOF['outline'], stroke=INK, w=0.5, dash='1.5 3', op=0.35)
    for t in P['terrace']:
        b += P_(t['d'], stroke=INK, w=0.5, dash='4 3', op=0.4)
    b += P_(circle_d(TREE[0], TREE[1], 13, 60, 0.03, 2), stroke=INK, w=0.6, dash='3 2', op=0.6)
    b += f'<circle cx="{TREE[0]}" cy="{TREE[1]}" r="0.55" fill="{ACC}"/>'
    b += P_(L2['prim'], fill='rgba(27,26,24,.05)')
    b += P_(L2['deck'], fill=f'url(#{pid}-deckR)', stroke=TIMBER, w=0.9)
    b += P_(L2['wall'], fill=INK, stroke=INK, w=0.35)
    b += P_(L2['glass'], fill=PAPER, stroke=INK, w=0.55)
    labels = [
        dict(p=frac(PVB, 12.9, 57.0), t='Primary suite · 6004.0', s=f"about {fmt(C['levels']['primary']['sf'])} sf, over the lower level", k='tag'),
        dict(p=frac(PVB, 31.8, 45.0), t='Primary terrace', s=f"cedar deck, about {fmt(C['decks']['primary_terrace'])} sf", k='room'),
        dict(p=frac(PVB, 9.0, -6.0), t='Main level below', s='roof over, open to the fold', k='room'),
        dict(p=frac(PVB, -57.4, -3.6), t='Garage below', k='room'),
        dict(p=frac(PVB, 8.0, 24.0), t='Bridge below', s='stairs inside the bridge', k='room'),
    ]
    return svg_wrap(PVB, b, pid), labels

# ------------------------------------------------------------------ A2.3 roof
def roofplan():
    pid = 'a23'
    b = ''
    b += P_(ROOF['cons'], stroke=INK, w=0.45, op=0.3)
    b += P_(P['foot']['rib'], stroke=INK, w=0.55, dash='2 3', op=0.5)
    b += P_(ROOF['outline'], fill=PAPER, stroke=INK, w=1.4)
    b += P_(ROOF['joist'], stroke=TIMBER, w=0.6)
    b += P_(ROOF['glulam'], fill=TIMBER, stroke='#8a4f1e', w=0.5, extra='fill-opacity="0.5"')
    b += P_(ROOF['beam'], fill=INK, stroke=INK, w=0.5)
    b += P_(ROOF['chim'], fill='#d6d5d1', stroke=INK, w=1.0)
    b += P_(circle_d(TREE[0], TREE[1], 13, 60, 0.03, 2), stroke=INK, w=0.6, dash='3 2', op=0.6)
    b += f'<circle cx="{TREE[0]}" cy="{TREE[1]}" r="0.55" fill="{ACC}"/>'
    labels = []
    for x, z, t, m in ROOF['spots']:
        b += P_(f'M{f2(x - 1.2)} {f2(z)} H{f2(x + 1.2)} M{f2(x)} {f2(z - 1.2)} V{f2(z + 1.2)}', stroke=ACC if m else INK, w=1.1)
        el = float(re.findall(r'\d{4}\.\d', t)[0])
        lab = t if not t[0].isdigit() else f'Roof {t}'
        labels.append(dict(p=frac(PVB, x, z), t=lab.replace('beam', 'Beam').replace('kitchen', 'Kitchen roof'),
                           s=(f'max, {C["heights"]["tip_over_grade"]:.1f} ft over grade' if m else ''), k='spot' + (' r' if x > 25 else ''), hot=bool(m)))
    labels += [
        dict(p=frac(PVB, 5.0, -11.5), t='Ribbon roof', s='standing seam, joists square to the beam', k='room'),
        dict(p=frac(PVB, -57.0, 3.0), t='Garage roof · 6016.5', k='room'),
        dict(p=frac(PVB, 24.0, 64.5), t='Chimney', s='board form concrete', k='room'),
    ]
    return svg_wrap(PVB, b, pid), labels

# ------------------------------------------------------------------ A1.2 site plan, 1 in = 10 ft
S10 = 0.1
SVB = (-141.0, -40.0, 214.0, 162.0)
SSX = lambda x: 1.95 + (x - SVB[0]) * S10
SSY = lambda z: 3.55 + (z - SVB[1]) * S10

def siteplan():
    pid = 'a12'
    b = ''
    clip = (SVB[0], SVB[1], SVB[2], SVB[3])
    b += f'<g clip-path="url(#{pid}-clip)">'
    for c in SITE['contours']:
        b += P_(c['d'], stroke=INK, w=0.85 if c['m'] else 0.45, op=0.55 if c['m'] else 0.3)
        if c['m']:
            x, z = c['at']
            b += f'<text x="{f2(x)}" y="{f2(z - 0.6)}" font-size="1.6" text-anchor="middle" fill="{INK}" opacity="0.65" font-family="Tenor Sans, sans-serif" letter-spacing=".08em">{c["el"]}</text>'
    b += P_(poly_d(DRIVE), fill='rgba(27,26,24,.07)', stroke=INK, w=0.9)
    b += P_(poly_d(APRON), fill='rgba(27,26,24,.035)', stroke=INK, w=0.6, dash='3 2')
    b += P_(SITE['drive'], stroke=INK, w=0.9, op=0.9)
    b += P_(SITE['setback'], stroke=INK, w=0.8, dash='6 4', op=0.65)
    b += P_(SITE['lot'], stroke=INK, w=1.5, dash='18 4 3 4')
    for t in P['terrace']:
        b += P_(t['d'], fill=f'url(#{pid}-deck)' if t['k'] == 'deck' else f'url(#{pid}-flag)', stroke=INK, w=0.6)
    b += P_(ROOF['outline'], fill='#e9e6df', stroke=INK, w=1.5)
    b += P_(ROOF['joist'], stroke=TIMBER, w=0.35, op=0.7)
    b += P_(ROOF['beam'], fill=INK)
    b += P_(ROOF['chim'], fill='#d6d5d1', stroke=INK, w=0.8)
    for i, (x, z, r) in enumerate(SITE['trees']):
        rr = 13 if i == 0 else r
        b += P_(circle_d(x, z, rr, 54, 0.045, i + 1), stroke='#2c5a37' if i == 0 else INK, w=1.1 if i == 0 else 0.6, op=0.9 if i == 0 else 0.6)
        b += P_(circle_d(x, z, rr * 0.62, 40, 0.06, i + 3), stroke='#2c5a37' if i == 0 else INK, w=0.45, op=0.5)
        b += f'<circle cx="{x}" cy="{z}" r="{1.1 if i == 0 else 0.55}" fill="{ACC if i == 0 else INK}"/>'
    b += '</g>'
    labels = [
        dict(p=frac(SVB, 2.0, -8.0), t='Walsh Residence', s='ribbon scheme, roof shown', k='tag'),
        dict(p=frac(SVB, -120.0, -26.0), t='Property line', s='from the lot data, confirm on survey', k='room', a='l'),
        dict(p=frac(SVB, 0.0, 90.0), t='Setbacks', s='dashed', k='room'),
        dict(p=frac(SVB, -100.0, 43.5), t='Driveway', s='from the CAD trace', k='room'),
        dict(p=frac(SVB, -51.0, 31.0), t='Apron', s='allowance', k='room'),
        dict(p=frac(SVB, 26.0, 20.0), t='Rear court', s='terraces', k='room'),
        dict(p=frac(SVB, -30.0, 40.5), t='Front court', k='room'),
        dict(p=frac(SVB, -136.5, 96.0), t='Lahontan Drive', k='road'),
    ]
    return svg_wrap(SVB, b, pid, clip), labels

# ------------------------------------------------------------------ key plans (not to scale) and the north arrow
def keyplan(pid, mode, arg=None):
    vb = (-80.0, -20.0, 124.0, 102.0)
    b = P_(P['foot']['rib'], fill='rgba(27,26,24,.1)', stroke=INK, w=0.9)
    for t in P['terrace']:
        b += P_(t['d'], stroke=INK, w=0.5, op=0.5)
    if mode == 'sections':
        b += P_('M8 -18 V80', stroke=ACC, w=1.2, dash='6 3')
        b += P_('M-79 -2 H43', stroke=ACC, w=1.2, dash='6 3')
        b += P_('M8 -18 H14 M8 80 H14 M-79 -2 V-8 M43 -2 V-8', stroke=ACC, w=1.2)
    else:
        # an arrow pointing at the face in view
        x, z, ang = arg
        b += f'<g transform="translate({x} {z}) rotate({ang})"><path d="M0 -9 L5 3 L0 0 L-5 3 Z" fill="{ACC}"/></g>'
    b += f'<circle cx="{TREE[0]}" cy="{TREE[1]}" r="1.6" fill="{ACC}"/>'
    return svg_wrap(vb, b, pid), vb

NORTH_DEG = math.degrees(math.atan2(P['north'][0], -P['north'][1]))

# ------------------------------------------------------------------ elevations and sections: frames, grade, render
VIEW = {  # forward, right (h = p . right)
    'N': ((0, 0, 1), (-1, 0, 0)), 'S': ((0, 0, -1), (1, 0, 0)),
    'E': ((-1, 0, 0), (0, 0, -1)), 'W': ((1, 0, 0), (0, 0, 1)),
}
ALLP = FOOT + [TERR['stone'], TERR['deck']]
ROOFP = subpaths(ROOF['outline'])[0]

def hof(view, x, z):
    r = VIEW[view][1]
    return x * r[0] + z * r[2]

def hits(polys, axis, c):
    """coordinates where the line axis = c crosses the polygons (axis 'x': a vertical plan line, returns z)"""
    out = []
    for poly in polys:
        for i in range(len(poly)):
            a, b = poly[i - 1], poly[i]
            ka, kb = (a[0], b[0]) if axis == 'x' else (a[1], b[1])
            if (ka - c) * (kb - c) < 0 or (ka == c and kb != c):
                t = (c - ka) / (kb - ka)
                out.append(a[1] + (b[1] - a[1]) * t if axis == 'x' else a[0] + (b[0] - a[0]) * t)
    return out

ROOFV = []
for key in ('wing', 'rib'):
    a = D[key]['roof']
    ROOFV += [(a[i], a[i + 1], a[i + 2]) for i in range(0, len(a), 3)]

def envelope(view, bin_ft=2.0):
    """the 30 ft line as it bears on this face: in each column, the roof point with the least room under its limit
    (natural grade right under it, plus 30), smoothed over three columns"""
    cols = {}
    for x, y, z in ROOFV:
        k = math.floor(hof(view, x, z) / bin_ft)
        lim = ground(x, z) + 30
        if k not in cols or lim - y < cols[k][0] - cols[k][1]:
            cols[k] = (lim, y)
    ks = sorted(cols)
    out = []
    for i, k in enumerate(ks):
        near = sorted(cols[j][0] for j in ks[max(0, i - 1):i + 2])
        out.append([round((k + 0.5) * bin_ft, 2), round(near[len(near) // 2], 2), round(cols[k][1], 2)])
    return out

def elevation_grade(view):
    axis = 'x' if view in 'NS' else 'z'
    xs = [p[0] for p in ROOFP]; zs = [p[1] for p in ROOFP]
    lo, hi = (min(xs), max(xs)) if axis == 'x' else (min(zs), max(zs))
    prof, last = [], None
    c = lo - 5
    while c <= hi + 5:
        hs = hits(ALLP, axis, c)
        if hs:
            if view == 'N': f = min(hs) - 0.5; y = ground(c, f)
            elif view == 'S': f = max(hs) + 0.5; y = ground(c, f)
            elif view == 'E': f = max(hs) + 0.5; y = ground(f, c)
            else: f = min(hs) - 0.5; y = ground(f, c)
            last = y
        prof.append([c, last])
        c += 0.5
    # hold the ends
    first = next(v for _, v in prof if v is not None)
    for p in prof:
        if p[1] is None: p[1] = first
        else: break
    out = []
    for c, y in prof:
        h = hof(view, c, 0) if axis == 'x' else hof(view, 0, c)
        out.append([round(h, 2), round(y, 2)])
    out.sort()
    return out

def section_grade(axis, at, view):
    """natural grade along the cut, dipping to one foot under the floor wherever the cut runs inside the house"""
    lo, hi = (-125, 70) if axis == 'z' else (-44, 124)
    prof = []
    c = lo
    while c <= hi:
        x, z = (c, at) if axis == 'z' else (at, c)
        g = ground(x, z)
        top = g
        for polys, ff in LEVEL_POLYS:
            if any(pip(x, z, p) for p in polys):
                top = min(g, ff - 1.0)
                break
        if pip(x, z, TERR['stone']):
            top = min(g, 2.33 - 0.6)
        prof.append([round(hof(view, x, z), 2), round(top, 2)])
        c += 0.5
    prof.sort()
    # close slivers: a dip or a spike narrower than 2 ft is a polygon seam, not a room
    for _ in range(2):
        for i in range(1, len(prof) - 1):
            for w in (1, 2, 3):
                if i + w < len(prof):
                    l, r = prof[i - 1][1], prof[i + w][1]
                    mid = [prof[i + k][1] for k in range(w)]
                    if all(abs(v - l) > 0.3 and abs(v - r) > 0.3 for v in mid) and abs(l - r) < 0.6:
                        for k in range(w):
                            prof[i + k][1] = round((l + r) / 2, 2)
    return prof

def clip_range(prof, h0, h1):
    return [p for p in prof if h0 - 1 <= p[0] <= h1 + 1]

def frame_for(view, scale, grade, pad=3.0, top=35.5, earth=3.5):
    hs = [hof(view, x, z) for x, z in ROOFP]
    h0, h1 = min(hs) - pad, max(hs) + pad
    g = [y for h, y in grade if h0 <= h <= h1]
    y0 = min(g) - earth - 0.4
    return dict(view=view, h0=round(h0, 2), h1=round(h1, 2), y0=round(y0, 2), y1=top, ppf=PPI * scale, ppi=PPI, earth=earth)

class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass

def serve():
    handler = functools.partial(Quiet, directory=str(ROOT))
    httpd = socketserver.TCPServer(('127.0.0.1', 0), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd

async def render_all(jobs):
    from playwright.async_api import async_playwright
    httpd = serve()
    port = httpd.server_address[1]
    out = {}
    async with async_playwright() as p:
        b = await p.chromium.launch(args=['--use-gl=swiftshader', '--enable-webgl', '--ignore-gpu-blocklist'])
        ctx = await b.new_context(viewport={'width': 1200, 'height': 800}, reduced_motion='reduce')
        pg = await ctx.new_page()
        errs = []
        pg.on('pageerror', lambda e: errs.append(str(e)))
        await pg.goto(f'http://127.0.0.1:{port}/walsh/index.html?draw')
        await pg.wait_for_function('window.__draw && window.__draw.ready', timeout=180000)
        for name, o in jobs:
            r = await pg.evaluate('o => window.__draw.ortho(o)', o)
            (HERE / f'{name}.webp').write_bytes(base64.b64decode(r['url'].split(',', 1)[1]))
            r.pop('url')
            out[name] = r
            print(f'  rendered {name}.webp  {r["W"]} x {r["H"]} px', flush=True)
        await b.close()
    httpd.shutdown()
    if errs:
        print('page errors:', errs)
    return out

# ------------------------------------------------------------------ build
ELEV = [  # sheet, view, title, scale label, scale (in per ft)
    ('A4.0', 'N', 'North elevation', '3/16 in = 1 ft', 3 / 16),
    ('A4.1', 'E', 'East elevation', '1/4 in = 1 ft', 1 / 4),
    ('A4.2', 'S', 'South elevation', '3/16 in = 1 ft', 3 / 16),
    ('A4.3', 'W', 'West elevation', '1/4 in = 1 ft', 1 / 4),
]
SECT = [  # name, view, clip, title
    ('A3.0-1', 'W', dict(axis='x', at=8.0, keep=1), 'Section 1 · through the bridge, looking east'),
    ('A3.0-2', 'S', dict(axis='z', at=-2.0, keep=-1), 'Section 2 · through the garage and living room, looking north'),
]

LEVELS_EL = {  # datum tags per view: (label, model y)
    'N': [('Tip', 33.0), ('Garage roof', 26.5), ('Beam', 22.0), ('Garage', 10.0), ('Main', 7.5)],
    'S': [('Tip', 33.0), ('Primary', 14.0), ('Main', 7.5), ('Lower', 2.5)],
    'E': [('Tip', 33.0), ('Primary', 14.0), ('Main', 7.5), ('Lower', 2.5)],
    'W': [('Tip', 33.0), ('Garage roof', 26.5), ('Primary', 14.0), ('Garage', 10.0), ('Main', 7.5)],
    'S1': [('Tip', 33.0), ('Bridge', 25.2), ('Primary', 14.0), ('Main', 7.5), ('Lower', 2.5)],
    'S2': [('Garage roof', 26.5), ('Beam', 22.0), ('Garage', 10.0), ('Main', 7.5)],
}
DW = 2.2   # datum run width, inches, to the right of every raster view

def raster_view(name, m, sc, grade, levels, x, y, section=False, vname=None):
    """a raster view placed at sheet inches (x, y): the image, the datum run at its right, the 30 ft line"""
    iw, ih = m['W'] / PPI, m['H'] / PPI
    X = lambda h: (h - m['h0']) * sc
    Y = lambda yy: (m['y1'] - yy) * sc
    W = iw + DW
    ov, labels = '', []
    dx = iw + 0.3
    for lab, yy in levels:
        py = Y(yy)
        ov += f'<path d="M{f2(iw - 0.1)} {f2(py)} H{f2(dx + 0.3)}" fill="none" stroke="{INK}" stroke-width="0.5" stroke-dasharray="3 3" opacity=".55" {NS}/>'
        ov += f'<path d="M{f2(dx)} {f2(py)} l0.09 -0.14 h-0.18 Z" fill="{ACC if lab == "Tip" else INK}"/>'
        labels.append(dict(p=[round((dx + 0.18) / W, 5), round(py / ih, 5)], t=lab, s=f'{DATUM + yy:.1f}', k='dat'))
    if not section:
        # drawn only where a roof comes within 6 ft of it, so the line reads where it governs
        runs, run = [], []
        for h, lim, ry in envelope(vname):
            if lim - ry <= 6:
                run.append((X(h), Y(lim)))
            elif run:
                runs.append(run); run = []
        if run: runs.append(run)
        d = ' '.join(poly_d(r, False) for r in runs if len(r) > 1)
        ov += f'<path d="{d}" fill="none" stroke="{ACC}" stroke-width="0.9" stroke-dasharray="6 4" {NS}/>'
    v = dict(img=f'draw/{name}.webp', iw=round(iw, 4), ih=round(ih, 4), x=round(x, 4), y=round(y, 4), w=round(W, 4), h=round(ih, 4),
             ov=ov, labels=labels, px=m['W'], py=m['H'])
    to_sheet = lambda h, yy: [round(x + X(h), 3), round(y + Y(yy), 3)]
    return v, to_sheet

def bar(sc, ticks):
    return dict(sc=sc, ft=ticks)

def table(x, y, w, title, rows, foot=None):
    return dict(x=x, y=y, w=w, title=title, rows=rows, foot=foot)

def build(render=True):
    jobs, grades = [], {}
    for sid, v, t, sl, sc in ELEV:
        g = elevation_grade(v)
        fr = frame_for(v, sc, g)
        fr['grade'] = clip_range(g, fr['h0'], fr['h1'])
        fr['glass'] = 'draw'; fr['wash'] = 0.22
        jobs.append((sid, fr)); grades[sid] = fr['grade']
    for name, v, clip, t in SECT:
        g = section_grade(clip['axis'], clip['at'], v)
        fr = frame_for(v, S316, g, pad=4.0, earth=3.0)
        fr['grade'] = clip_range(g, fr['h0'], fr['h1'])
        fr['clip'] = clip; fr['glass'] = 'draw'; fr['wash'] = 0.22
        jobs.append((name, fr)); grades[name] = fr['grade']
    meta_path = HERE / 'render_meta.json'
    if render:
        meta = asyncio.run(render_all(jobs))
        meta_path.write_text(json.dumps(meta, indent=1))
    meta = json.loads(meta_path.read_text())
    (HERE / 'calcs.json').write_text(json.dumps(C, indent=1, ensure_ascii=False))
    lv = C['levels']
    FOOT_NOTE = 'About, gross to the outside face. FA accuracy, confirm on survey.'
    sheets = {}

    # ---------------- A1.2 site plan
    svg, labels = siteplan()
    (HERE / 'A1.2.svg').write_text(svg)
    sx, sy = SSX, SSY
    sheets['A1.2'] = dict(
        views=[dict(x=sx(SVB[0]), y=sy(SVB[1]), w=SVB[2] * S10, h=SVB[3] * S10, svg=svg, labels=labels)],
        vt=[dict(n=1, t='Site plan', s='1 in = 10 ft', x=24.3, y=17.2, bar=bar(S10, [0, 10, 20, 40]))],
        north=dict(x=29.9, y=15.1, s=1.1),
        tables=[table(24.3, 4.0, 7.1, 'Site data', [
            ['Lot area', f"about {fmt(LOT_SF)} sf · {C['lot_ac']} ac"],
            ['Zoning', 'RS PD 1.7 · Placer County'],
            ['Roof footprint', f"about {fmt(C['roof_footprint'])} sf"],
            ['Building coverage', f"about {C['coverage_pct']}%"],
            ['Drive and apron', f"about {fmt(C['drive'] + C['apron_allowance'])} sf"],
            ['Impervious', f"about {fmt(C['impervious_sf'])} sf · {C['impervious_pct']}%"],
            ['High point', f"6023.0 · {C['heights']['tip_over_grade']:.1f} ft over grade"],
        ], 'Lot area about, from the prior listing, confirm on survey. Driveway from the CAD trace, apron an allowance.')],
        notes=[dict(text='keep the signature tree', t=[sx(-62), sy(100)], p=[sx(TREE[0] - 9), sy(TREE[1] + 9)], a='l'),
               dict(text='approach from the west', t=[sx(-126), sy(80)], p=[sx(-104), sy(42)], a='l')])

    # ---------------- A2.1, A2.2, A2.3 plans, one registration
    plan_vt = lambda t: [dict(n=1, t=t, s='3/16 in = 1 ft', x=10.4, y=18.75, bar=bar(S316, [0, 4, 8, 16]))]
    north = dict(x=13.1, y=14.4, s=1.1)
    svg, labels = level1(); (HERE / 'A2.1.svg').write_text(svg)
    sheets['A2.1'] = dict(
        views=[dict(**PVIEW, svg=svg, labels=labels)], vt=plan_vt('Level 1 plan'), north=north,
        tables=[table(1.9, 4.0, 5.9, 'Level 1 areas', [
            ['Main level · 5997.5', f"about {fmt(lv['main']['sf'])} sf"],
            ['Lower level · 5992.5', f"about {fmt(lv['lower']['sf'])} sf"],
            ['Level 1 conditioned', f"about {fmt(C['level1_conditioned'])} sf"],
            ['Garage and gear bay', f"about {fmt(C['garage'])} sf"],
            ['Upper terrace, cedar', f"about {fmt(C['decks']['upper_terrace'])} sf"],
            ['Lower patio, stone', f"about {fmt(C['patio_stone'])} sf"],
            ['Overall', f"about {C['overall_ft'][0]:.0f} by {C['overall_ft'][1]:.0f} ft"],
        ], FOOT_NOTE + ' Walls and glass cut 4 ft above each floor.')],
        notes=[dict(text='bridge, dining in the middle', t=[PSX(-25), PSY(44)], p=[PSX(6), PSY(33)], a='r'),
               dict(text='the court wraps the tree', t=[PSX(-62), PSY(24)], p=[PSX(TREE[0] - 12.6), PSY(TREE[1] + 2)], a='l')])
    svg, labels = level2(); (HERE / 'A2.2.svg').write_text(svg)
    sheets['A2.2'] = dict(
        views=[dict(**PVIEW, svg=svg, labels=labels)], vt=plan_vt('Level 2 plan'), north=north,
        tables=[table(1.9, 4.0, 5.9, 'Level 2 areas', [
            ['Primary suite · 6004.0', f"about {fmt(lv['primary']['sf'])} sf"],
            ['Primary terrace, cedar', f"about {fmt(C['decks']['primary_terrace'])} sf"],
            ['Level 1 conditioned', f"about {fmt(C['level1_conditioned'])} sf"],
            ['Total conditioned', f"about {fmt(C['conditioned'])} sf"],
            ['Garage, not included', f"about {fmt(C['garage'])} sf"],
        ], FOOT_NOTE + ' Level 1 dashed below.')],
        notes=[dict(text='the suite sits over the lower level', t=[PSX(-58), PSY(60)], p=[PSX(4), PSY(62)], a='l'),
               dict(text='stairs only inside the bridge', t=[PSX(-58), PSY(33)], p=[PSX(3), PSY(30)], a='l')])
    svg, labels = roofplan(); (HERE / 'A2.3.svg').write_text(svg)
    sheets['A2.3'] = dict(
        views=[dict(**PVIEW, svg=svg, labels=labels)], vt=plan_vt('Roof plan'), north=north,
        tables=[table(1.9, 4.0, 5.9, 'Coverage and impervious', [
            ['Lot area', f"about {fmt(LOT_SF)} sf"],
            ['Roof, to the drip line', f"about {fmt(C['roof_footprint'])} sf"],
            ['Building coverage', f"about {C['coverage_pct']}%"],
            ['Driveway', f"about {fmt(C['drive'])} sf"],
            ['Apron, allowance', f"about {fmt(C['apron_allowance'])} sf"],
            ['Lower patio, stone', f"about {fmt(C['patio_stone'])} sf"],
            ['Walks, allowance', f"about {fmt(WALK_ALLOW)} sf"],
            ['Impervious', f"about {fmt(C['impervious_sf'])} sf · {C['impervious_pct']}%"],
            ['Decks with gaps', f"about {fmt(C['decks']['upper_terrace'] + C['decks']['primary_terrace'])} sf, apart"],
        ], 'Lot area about, from the prior listing, confirm on survey. FA accuracy.')],
        notes=[dict(text='the tip lifts to the court', t=[PSX(-4), PSY(-22.2)], p=[PSX(36.4), PSY(10.3)], a='l'),
               dict(text='every roof under 30 ft', t=[PSX(-58), PSY(40)], p=[PSX(-37.5), PSY(17.8)], a='l')])

    # ---------------- A3.0 sections, stacked
    m2, m1 = meta['A3.0-2'], meta['A3.0-1']
    v2, s2 = raster_view('A3.0-2', m2, S316, grades['A3.0-2'], LEVELS_EL['S2'], 1.9, 3.5, section=True)
    v1, s1 = raster_view('A3.0-1', m1, S316, grades['A3.0-1'], LEVELS_EL['S1'], 1.9, 3.5 + v2['h'] + 1.15, section=True)
    v2['labels'] += [dict(p=frac_v(v2, s2, 20, 12), t='Living', k='room'), dict(p=frac_v(v2, s2, -52, 14), t='Garage', k='room')]
    v1['labels'] += [dict(p=frac_v(v1, s1, -3, 13.5), t='Living', k='room'), dict(p=frac_v(v1, s1, 26, 12), t='Bridge', s='dining', k='room'),
                     dict(p=frac_v(v1, s1, 56, 20), t='Primary suite', k='room'), dict(p=frac_v(v1, s1, 56, 7), t='Lower level', k='room')]
    sheets['A3.0'] = dict(
        views=[v2, v1],
        vt=[dict(n=2, t='Section 2 · garage and living, looking north', s='3/16 in = 1 ft', x=1.9, y=3.5 + v2['h'] + 0.22, bar=bar(S316, [0, 4, 8, 16])),
            dict(n=1, t='Section 1 · the bridge, looking east', s='3/16 in = 1 ft', x=1.9, y=v1['y'] + v1['h'] + 0.22, bar=bar(S316, [0, 4, 8, 16]))],
        keys=[dict(x=25.2, y=v1['y'] + 0.4, w=5.6, k='sections', t='Key plan', s='Section cuts')],
        notes=[dict(text='clerestory at the fold', t=s2(-4, 36.5), p=s2(13.6, 19.2), a='r'),
               dict(text='one step down with the land', t=s1(66, -7.5), p=s1(58, 3.2), a='l')])
    # ---------------- A4.x elevations, one per sheet
    for sid, v, t, sl, sc in ELEV:
        m = meta[sid]
        iw = m['W'] / PPI
        x = 1.6 + (30.5 - (iw + DW)) / 2
        y = 5.9 if sc == 0.25 else 6.4
        view, to = raster_view(sid, m, sc, grades[sid], LEVELS_EL[v], x, y, vname=v)
        env = [e for e in envelope(v) if e[1] - e[2] <= 6]
        ea = env[0]
        view['labels'].append(dict(p=frac_v(view, to, ea[0], ea[1] + 1.1), t='30 ft over natural grade', k='lim'))
        tip = to(hof(v, 36.94, 10.72), 32.8)
        tip_left = (tip[0] - x) / iw < 0.5
        ny = y - 1.25
        if v in 'NE':
            second = dict(text='the tip lifts to the court', p=tip)
        elif v == 'S':
            second = dict(text='two doors face the drive', p=to(-51, 18.0))
        else:
            second = dict(text='arrival at the west end', p=to(4, 20.0))
        sl_ = (second['p'][0] - x) / iw < 0.5
        second.update(t=[x + 0.02 * iw, ny], a='l') if sl_ else second.update(t=[x + 0.98 * iw, ny], a='r')
        side = [e for e in env if ((to(e[0], 0)[0] - x) / iw >= 0.5) == sl_] or env
        eb = min(side, key=lambda e: e[1] - e[2])
        fp = to(eb[0], eb[1])
        fl = (fp[0] - x) / iw < 0.5
        first = dict(text='every roof under 30 ft', p=fp, t=[fp[0] + 1.6, ny - 0.55] if fl else [fp[0] - 1.6, ny - 0.55], a='l' if fl else 'r')
        sheets[sid] = dict(views=[view],
                           vt=[dict(n=1, t=t, s=sl, x=x, y=y + view['h'] + 0.3, bar=bar(sc, [0, 4, 8, 16]))],
                           keys=[dict(x=x + iw + DW - 3.4, y=y + view['h'] + 0.45, w=3.4, k=v, t='Key plan', s='Face in view')],
                           notes=[first, second])
    keys = dict(sections=keyplan('ksec', 'sections')[0])
    for v, a in {'N': (-20, -21, 180), 'E': (44, 20, 270), 'S': (10, 80, 0), 'W': (-82, 30, 90)}.items():
        keys[v] = keyplan('k' + v.lower(), 'arrow', a)[0]
    js = 'window.DRAWINGS = ' + json.dumps(dict(calcs=C, sheets=sheets, north=round(NORTH_DEG, 1), keys=keys, keyAr=124 / 102), ensure_ascii=False) + ';\n'
    (HERE / 'drawings.js').write_text('/* built by build_drawings.py from the pocket model; do not edit by hand */\n' + js)
    print('wrote drawings.js', len(js) // 1024, 'KB')

def frac_v(v, to, h, y):
    sx, sy = to(h, y)
    return [round((sx - v['x']) / v['w'], 5), round((sy - v['y']) / v['h'], 5)]

if __name__ == '__main__':
    build(render='--no-render' not in sys.argv)
