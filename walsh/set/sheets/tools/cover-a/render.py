#!/usr/bin/env python3
"""cover-a: still renderings of the Ribbon scheme from the pocket model (walsh/index.html), 9/30/26.

Loads the pocket model in headless Chromium, injects render_kit.js (palette materials, sky, ground, firs, grass),
renders a color pass and a line pass in tiles, then composite.py lays the render into hairline drafting.

  python3 walsh/set/sheets/tools/cover-a/render.py [preview] [job ...]      jobs: arrival court tip aerial cover

Raw passes go to the scratch folder (RAW); composite.py writes the WebP files to walsh/set/sheets/assets/cover-a/.
"""
import base64, functools, http.server, io, json, socketserver, sys, threading, time
from pathlib import Path
from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
RAW = Path('/tmp/claude-0/-home-claude-andre-mandel-site/b0abd60a-a112-5987-bb0d-bf806619c786/scratchpad/cover-a-raw')
PPI = 200
PORT = 8901

# views: sheet size in inches (w, h), palette, camera (eye, look in model feet; y up, 5990.0 = y 0), level = two point perspective
JOBS = {
    'arrival': dict(pal='mist', w=14.5, h=6.8, eye=[-150.0, 17.5, 74.0], look=[-10.0, 17.0, 22.0], hfov=60, level=True, ty=0.5,
                    seed=5, forest=300, sigPaint=True),
    'court': dict(pal='meadow', w=14.5, h=6.8, eye=[104.0, 9.0, 70.0], look=[14.0, 16.0, 20.0], hfov=66, level=True, ty=0.52,
                  seed=9, forest=260, pitLight=2.2, noGrass=[[18, 44, 12, 34], [24, 50, 38, 58]]),
    'tip': dict(pal='dusk', w=14.5, h=6.8, eye=[114.0, 6.5, 36.0], look=[30.0, 20.0, 4.0], hfov=50, level=True, ty=0.6,
                seed=13, forest=260, pitLight=3.0, glow=[[28, 12, 0, 2.2, 40], [10, 12, -6, 1.6, 36]], noGrass=[[18, 44, 12, 34]]),
    'aerial': dict(pal='mist', w=14.5, h=6.8, eye=[59.0, 250.0, 236.0], look=[-16.0, 6.0, 20.0], hfov=37, level=False,
                   seed=21, forest=340, siteLines=True),
    'plan': dict(pal='mist', w=8, h=8, eye=[-18.0, 700.0, 30.01], look=[-18.0, 0.0, 30.0], hfov=24, level=False, forest=0),
    'cover': dict(pal='mist', w=30.75, h=22.5, eye=[128.0, 58.0, 104.0], look=[-16.0, 14.0, 28.5], hfov=62, level=True, ty=0.42,
                  seed=3, forest=420, siteLines=True, pencilR=170, ss=1.5),
}
ANCHOR_KEYS = ['tip', 'tipGrade', 'tip30', 'beam', 'beamW', 'southTip', 'bridgeTip', 'garageTip', 'tree', 'stip', 'swHigh', 'granny',
               'porch', 'gdoor', 'clere', 'sclere', 'endS', 'endE', 'post', 'patio', 'rail', 'chim', 'chimLR', 'primaryRidge', 'bridgeRidge']


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


def serve():
    socketserver.TCPServer.allow_reuse_address = True
    httpd = socketserver.ThreadingTCPServer(('127.0.0.1', PORT), functools.partial(Quiet, directory=str(ROOT)))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd


def run(names, preview=False):
    from playwright.sync_api import sync_playwright
    RAW.mkdir(parents=True, exist_ok=True)
    httpd = serve()
    kit = (HERE / 'render_kit.js').read_text()
    out = {}
    with sync_playwright() as p:
        b = p.chromium.launch(args=['--use-gl=swiftshader', '--enable-webgl', '--ignore-gpu-blocklist'])
        for name in names:
            t0 = time.time()
            J = dict(JOBS[name])
            ss = 1 if preview else (J.get('ss') or 2)
            ppi = (int(sys.argv[sys.argv.index('--ppi') + 1]) if '--ppi' in sys.argv else 40) if preview else PPI
            W, H = round(J['w'] * ppi * ss), round(J['h'] * ppi * ss)
            job = dict(J, W=W, H=H)
            ctx = b.new_context(viewport={'width': 480, 'height': 320}, reduced_motion='reduce')
            pg = ctx.new_page()
            errs = []
            pg.on('pageerror', lambda e: errs.append(str(e)))
            pg.on('console', lambda m: errs.append(m.text) if m.type == 'error' else None)
            pg.goto(f'http://127.0.0.1:{PORT}/walsh/index.html', wait_until='load')
            pg.wait_for_function('window.__fa && window.__fa.scene', timeout=240000)
            pg.wait_for_function("document.getElementById('app').dataset.mode === 'reel'", timeout=240000)
            pg.wait_for_timeout(600)
            pg.add_script_tag(content=kit)
            pg.wait_for_function('window.__rk && window.__rk.ready', timeout=60000)
            info = pg.evaluate('j => window.__rk.setup(j)', job)
            pts = pg.evaluate('() => { const A = window.__rk.A, X = window.__rk.xt, o = {}; Object.keys(A).forEach(k => o[k] = A[k]); Object.keys(X).forEach(k => o["xt_" + k] = X[k]); return o; }')
            pts['treeBase'] = [pts['tree'][0], pts['tree'][1] - 44.0 + 7.0, pts['tree'][2]]
            proj = pg.evaluate('p => window.__rk.project(p)', pts)
            for ps in ('color', 'line', 'mask'):
                img = Image.new('RGBA', (W, H))
                for ty in range(0, H, 2048):
                    for tx in range(0, W, 2048):
                        url = pg.evaluate('a => window.__rk.tile(a[0], a[1], a[2], a[3], a[4])', [ps, W, H, tx, ty])
                        img.paste(Image.open(io.BytesIO(base64.b64decode(url.split(',', 1)[1]))), (tx, ty))
                tag = '_prev' if preview else ''
                img.convert('RGB').save(RAW / f'{name}_{ps}{tag}.png')
            meta = dict(job=J, W=W, H=H, ss=ss, ppi=ppi, proj=proj, info=info)
            (RAW / f'{name}{"_prev" if preview else ""}.json').write_text(json.dumps(meta, indent=1))
            ctx.close()
            print(f'{name}: {W} x {H} ({ss}x) in {time.time() - t0:.0f} s', 'errors: ' + ' | '.join(errs[:4]) if errs else '', flush=True)
            out[name] = meta
        b.close()
    httpd.shutdown()
    return out


if __name__ == '__main__':
    a = sys.argv[1:]
    prev = 'preview' in a
    names = [x for x in a if x in JOBS] or [n for n in JOBS if n != 'plan']
    run(names, prev)
