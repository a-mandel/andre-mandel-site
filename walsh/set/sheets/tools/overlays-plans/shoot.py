#!/usr/bin/env python3
"""overlays-plans: screenshots of A2.0 to A2.5 and A0.6 with overlays, desktop and phone, plus checks.
Fonts served from local copies. Serve the repo root on 8941 first.
  python3 walsh/set/sheets/tools/overlays-plans/shoot.py [A2.1,A2.2] [suffix]
"""
import re, sys, json
from pathlib import Path
from playwright.sync_api import sync_playwright
FONTS = Path('/tmp/claude-0/-home-claude-andre-mandel-site/b0abd60a-a112-5987-bb0d-bf806619c786/scratchpad/fonts')
CSS = """@font-face{font-family:'Tenor Sans';src:url(/__f/tenor.woff2) format('woff2')}
@font-face{font-family:'EB Garamond';font-style:normal;font-weight:400;src:url(/__f/ebg-n.woff2) format('woff2')}
@font-face{font-family:'EB Garamond';font-style:italic;font-weight:400;src:url(/__f/ebg-i.woff2) format('woff2')}
@font-face{font-family:'EB Garamond';font-style:normal;font-weight:500;src:url(/__f/ebg-n5.woff2) format('woff2')}
@font-face{font-family:'EB Garamond';font-style:italic;font-weight:500;src:url(/__f/ebg-i5.woff2) format('woff2')}
@font-face{font-family:'Nothing You Could Do';src:url(/__f/nycd.woff2) format('woff2')}"""
IDS = sys.argv[1].split(',') if len(sys.argv) > 1 and sys.argv[1] and not sys.argv[1].startswith('-') else ['A2.0','A2.1','A2.2','A2.3','A2.4','A2.5','A0.6']
TAG = sys.argv[2] if len(sys.argv) > 2 and not sys.argv[2].startswith('-') else ''
OUT = '/home/claude/tb/ov'
def route(pg):
    pg.route(re.compile(r'fonts\.googleapis\.com'), lambda r: r.fulfill(status=200, content_type='text/css', body=CSS))
    pg.route(re.compile(r'fonts\.gstatic\.com'), lambda r: r.fulfill(status=404, body=''))
    pg.route(re.compile(r'/__f/'), lambda r: r.fulfill(status=200, content_type='font/woff2', body=(FONTS / r.request.url.rsplit('/', 1)[1]).read_bytes()))
CHECK = """(id)=>{const s=document.querySelector('.sheet[data-id="'+id+'"]'); if(!s) return {err:'nosheet'};
 const ov=[...s.querySelectorAll('.fover')]; const txt=ov.map(e=>e.textContent).join(' ');
 const fld=(s.querySelector('.fhtml')||s.querySelector('.view')||s).closest('.field')||s.querySelector('.field');
 const fb=fld?fld.getBoundingClientRect():null; let out=0, n=0;
 ov.forEach(o=>o.querySelectorAll('.opx *').forEach(e=>{const b=e.getBoundingClientRect(); if(!b.width&&!b.height) return; n++; if(fb&&(b.left<fb.left-1||b.right>fb.right+1||b.top<fb.top-1||b.bottom>fb.bottom+1)) out++;}));
 return {dash:(txt.match(/[\\u2012-\\u2015]| - /g)||[]).length, chars:txt.length, els:n, outside:out, fonts:[...new Set([...document.fonts].filter(f=>f.status=='loaded').map(f=>f.family))]};}"""
with sync_playwright() as p:
    b = p.chromium.launch(args=['--use-gl=swiftshader','--enable-webgl','--ignore-gpu-blocklist'])
    for w, h, suf, dpr in [(1914,1192,'',2 if '--zoom' in sys.argv else 1), (390,844,'_m',2)]:
        ctx = b.new_context(viewport={'width':w,'height':h}, device_scale_factor=dpr, has_touch=bool(suf))
        for sid in IDS:
            if suf and sid != 'A2.1': continue
            pg = ctx.new_page(); route(pg); errs = []
            pg.on('pageerror', lambda e: errs.append(str(e)))
            pg.on('console', lambda m: errs.append(m.text) if m.type == 'error' else None)
            pg.goto(f'http://localhost:8941/walsh/set/v2.html#{sid}', wait_until='networkidle'); pg.wait_for_timeout(2500)
            pg.screenshot(path=f'{OUT}/overlays-plans_{sid}{suf}{TAG}.png')
            print(sid, w, 'errors', errs[:4], json.dumps(pg.evaluate(CHECK, sid)))
            if sid == 'A2.1' and not suf and '--zoom' in sys.argv:
                for k, (x, y, w, h) in enumerate([(1000, 30, 640, 470), (1000, 480, 640, 500), (480, 30, 600, 470)]):
                    pg.screenshot(path=f'{OUT}/overlays-plans_A2.1_zoom{k + 1}{TAG}.png', clip={'x': x, 'y': y, 'width': w, 'height': h})
            pg.close()
        ctx.close()
    b.close()
