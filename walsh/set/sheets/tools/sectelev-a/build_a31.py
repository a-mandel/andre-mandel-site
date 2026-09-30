#!/usr/bin/env python3
"""A3.1 Building sections, sections 3 and 4 (crew sectelev-a, 9/30/26).

Same method as A3.0 (walsh/set/draw/build_drawings.py): orthographic renders of the pocket model's three.js scene,
clipped at the cut plane by the gated ?draw hook in walsh/index.html, at 200 px per inch of sheet, 3/16 in = 1 ft.
The helpers below are copied from build_drawings.py (draw/ is never modified). Output:
  sheets/assets/sectelev-a/A3.1-3.webp, A3.1-4.webp  the two section renders
  sheets/assets/sectelev-a/a31.js                     window.A31 = placement data the sheet script reads

Run from anywhere:  python3 walsh/set/sheets/tools/sectelev-a/build_a31.py [--no-render] [--port 8907]
"""
import asyncio, base64, functools, http.server, json, math, re, socketserver, sys, threading
from pathlib import Path

HERE = Path(__file__).resolve().parent
SET = HERE.parents[2]                       # walsh/set
ROOT = SET.parents[1]                       # repo root
MODEL = ROOT / 'walsh' / 'index.html'
OUT = SET / 'sheets' / 'assets' / 'sectelev-a'
PPI = 200
DATUM = 5990.0
S316 = 3 / 16
INK, ACC = '#1b1a18', '#c07a2c'

# ------------------------------------------------------------------ copied from draw/build_drawings.py
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

def pip(x, y, poly):
    c = False
    for i in range(len(poly)):
        x1, y1 = poly[i]; x2, y2 = poly[i - 1]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            c = not c
    return c

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

FOOT = subpaths(P['foot']['rib'])
TERR = {t['k']: subpaths(t['d'])[0] for t in P['terrace']}
LEVEL_POLYS = [(subpaths(L1['lower']), 2.5), (subpaths(L1['main']), 7.5), (subpaths(L1['gar']), 10.0)]
VIEW = {'N': ((0, 0, 1), (-1, 0, 0)), 'S': ((0, 0, -1), (1, 0, 0)), 'E': ((-1, 0, 0), (0, 0, -1)), 'W': ((1, 0, 0), (0, 0, 1))}
ROOFP = subpaths(ROOF['outline'])[0]
TREE = SITE['trees'][0]

def hof(view, x, z):
    r = VIEW[view][1]
    return x * r[0] + z * r[2]

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

def f2(v):
    return f'{v:.2f}'.rstrip('0').rstrip('.')

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

class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass

async def render_all(jobs, port):
    from playwright.async_api import async_playwright
    httpd = None
    if not port:
        httpd = socketserver.TCPServer(('127.0.0.1', 0), functools.partial(Quiet, directory=str(ROOT)))
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
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
            (OUT / f'{name}.webp').write_bytes(base64.b64decode(r['url'].split(',', 1)[1]))
            r.pop('url')
            out[name] = r
            print(f'  rendered {name}.webp  {r["W"]} x {r["H"]} px', flush=True)
        await b.close()
    if httpd:
        httpd.shutdown()
    if errs:
        print('page errors:', errs)
    return out

# ------------------------------------------------------------------ A3.1: the two cuts
# Section 3: a north south cut at x = 34 through the living room, 2 ft inside its east glass, looking west (keeps x <= 34).
# Section 4: an east west cut at z = 52 through the primary suite and the lower level, looking north (keeps z <= 52).
SECT = {
    'A3.1-3': dict(view='E', clip=dict(axis='x', at=34.0, keep=-1)),
    'A3.1-4': dict(view='S', clip=dict(axis='z', at=52.0, keep=-1)),
}
TOP = 33.9    # model y at the top of each render (6023.9); the 30 ft line may run above it on the overlay
SHEET_JS = SET / 'sheets' / 'sectelev-a.js'

ROOFV = []
for key in ('wing', 'rib'):
    a = D[key]['roof']
    ROOFV += [(a[i], a[i + 1], a[i + 2]) for i in range(0, len(a), 3)]

def natural(axis, at, view, h0, h1, step=1.0):
    """natural grade along the cut, in view feet (the 30 ft line runs 30 ft over it)"""
    out = []
    c = -130.0
    while c <= 130:
        x, z = (c, at) if axis == 'z' else (at, c)
        h = hof(view, x, z)
        if h0 - 0.01 <= h <= h1 + 0.01:
            out.append([round(h, 2), round(ground(x, z), 2)])
        c += step
    out.sort()
    return out

def beyond(axis, at, keep, view, bin_ft=1.0, near=3.0):
    """roofs seen beyond the cut sit over their own natural grade. Where one comes within `near` ft of its own
    30 ft line and that line differs from the line at the cut, return runs of [h, limit, roof y] so the sheet can
    show the limit that actually governs it"""
    cols = {}
    for x, y, z in ROOFV:
        c = x if axis == 'x' else z
        if (c - at) * keep < -0.01:
            continue                                           # removed by the cut
        h = hof(view, x, z)
        k = math.floor(h / bin_ft)
        lim = ground(x, z) + 30
        if k not in cols or lim - y < cols[k][0] - cols[k][1]:
            cols[k] = (lim, y, abs(c - at))
    runs, run = [], []
    for k in sorted(cols):
        lim, y, dist = cols[k]
        h = (k + 0.5) * bin_ft
        x, z = (h, at) if axis == 'z' else (at, -h)
        cut = ground(x, z) + 30
        if lim - y <= near and dist > 1.0 and abs(lim - cut) > 0.3:
            if run and h - run[-1][0] > bin_ft * 1.5:
                runs.append(run); run = []
            run.append([round(h, 2), round(lim, 2), round(y, 2)])
        elif run:
            runs.append(run); run = []
    if run:
        runs.append(run)
    out = []
    for r in runs:
        if len(r) < 2:
            continue
        lims = [p[1] for p in r]
        for i in range(len(r)):                               # a running median of three, so the line reads as one
            w = sorted(lims[max(0, i - 1):i + 2])
            r[i][1] = w[len(w) // 2]
        out.append(r)
    return out

def build(render=True, port=None):
    jobs, grades = [], {}
    for name, s in SECT.items():
        g = section_grade(s['clip']['axis'], s['clip']['at'], s['view'])
        fr = frame_for(s['view'], S316, g, pad=3.0, top=TOP, earth=2.6)
        fr['grade'] = clip_range(g, fr['h0'], fr['h1'])
        fr['clip'] = s['clip']; fr['glass'] = 'draw'; fr['wash'] = 0.22
        jobs.append((name, fr)); grades[name] = fr['grade']
    meta_path = OUT / 'render_meta.json'
    if render:
        meta = asyncio.run(render_all(jobs, port))
        meta_path.write_text(json.dumps(meta, indent=1))
    meta = json.loads(meta_path.read_text())
    views = {}
    for name, s in SECT.items():
        m, c = meta[name], s['clip']
        nat = natural(c['axis'], c['at'], s['view'], m['h0'], m['h1'])
        grade = [p for i, p in enumerate(grades[name]) if i % 2 == 0]
        views[name] = dict(img=f'sheets/assets/sectelev-a/{name}.webp', px=m['W'], py=m['H'], h0=round(m['h0'], 3), h1=round(m['h1'], 3),
                           y0=round(m['y0'], 3), y1=m['y1'], cut=[round(v, 2) for v in m['cut']], view=s['view'], at=c['at'], axis=c['axis'],
                           nat=nat, grade=grade, beyond=beyond(c['axis'], c['at'], c['keep'], s['view']))
    data = dict(views=views, key=keyplan(), datum=DATUM, ppi=PPI)
    blob = json.dumps(data, ensure_ascii=False, separators=(',', ':'))
    js = SHEET_JS.read_text()
    a, b = js.index('/*A31:DATA*/') + len('/*A31:DATA*/'), js.index('/*A31:END*/')
    SHEET_JS.write_text(js[:a] + blob + js[b:])
    print('wrote the data block into sheets/sectelev-a.js,', len(blob) // 1024, 'KB')

def keyplan():
    """plan key, not to scale: footprint, primary suite, terraces, the tree, cuts 3 and 4 in orange, A3.0 cuts faint"""
    vb = (-86.0, -26.0, 136.0, 112.0)
    b = P_(P['foot']['rib'], fill='rgba(27,26,24,.08)', stroke=INK, w=0.9)
    for t in P['terrace']:
        b += P_(t['d'], stroke=INK, w=0.5, op=0.5)
    b += P_(L2['prim'], fill='rgba(27,26,24,.12)', stroke=INK, w=0.5, op=0.7)
    b += P_('M8 -18 V80 M-79 -2 H43', stroke=INK, w=0.6, dash='3 3', op=0.3)           # A3.0 cuts, for reference
    # section 3, x = 34, looking west: the flags and arrows point to -x
    b += P_('M34 -21 V81', stroke=ACC, w=1.3, dash='6 3')
    b += P_('M34 -21 H28 M34 81 H28', stroke=ACC, w=1.3)
    b += P_('M28.6 -22.9 L25.4 -21 L28.6 -19.1 Z M28.6 79.1 L25.4 81 L28.6 82.9 Z', fill=ACC)
    # section 4, z = 52, looking north: the flags and arrows point to -z
    b += P_('M-80 52 H46', stroke=ACC, w=1.3, dash='6 3')
    b += P_('M-80 52 V46 M46 52 V46', stroke=ACC, w=1.3)
    b += P_('M-81.9 46.6 L-80 43.4 L-78.1 46.6 Z M44.1 46.6 L46 43.4 L47.9 46.6 Z', fill=ACC)
    b += f'<circle cx="{TREE[0]}" cy="{TREE[1]}" r="1.8" fill="{ACC}"/>'
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" class="dsvg" viewBox="{f2(vb[0])} {f2(vb[1])} {f2(vb[2])} {f2(vb[3])}" '
           f'preserveAspectRatio="xMidYMid meet" aria-hidden="true">{b}</svg>')
    return dict(svg=svg, vb=vb, bubbles=[[3, 34, -29.5], [3, 34, 89.5], [4, -89, 52], [4, 55, 52]],
                north=round(math.degrees(math.atan2(P['north'][0], -P['north'][1])), 1))

if __name__ == '__main__':
    port = None
    if '--port' in sys.argv:
        port = int(sys.argv[sys.argv.index('--port') + 1])
    build(render='--no-render' not in sys.argv, port=port)
