#!/usr/bin/env python3
"""overlays-style: screenshots of A0.9, A9.1, A0.5 at 1914 x 1192 (and 390 x 844), a registration crop around the tip hook of each still,
page errors and a dash check over the overlay text. Needs a server on the repo root:  python3 -m http.server 8944"""
import sys, asyncio
from pathlib import Path
from playwright.async_api import async_playwright
from PIL import Image
OUT = Path('/home/claude/tb/ov'); OUT.mkdir(parents=True, exist_ok=True)
IDS = sys.argv[1].split(',') if len(sys.argv) > 1 else ['A0.9', 'A9.1', 'A0.5']
TAG = sys.argv[2] if len(sys.argv) > 2 else ''
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(args=['--use-gl=swiftshader', '--enable-webgl', '--ignore-gpu-blocklist'])
        for sid in IDS:
            for vp in [(1914, 1192), (390, 844)]:
                pg = await b.new_page(viewport={'width': vp[0], 'height': vp[1]}, device_scale_factor=1 if vp[0] < 1000 else 2)
                errs = []
                pg.on('pageerror', lambda e: errs.append(str(e)))
                pg.on('console', lambda m: errs.append('console ' + m.text) if m.type == 'error' else None)
                await pg.goto(f'http://localhost:8944/walsh/set/v2.html#{sid}', wait_until='networkidle')
                await pg.wait_for_timeout(3500)
                suf = '_m' if vp[0] < 1000 else ''
                f = OUT / f'overlays-style_{sid}{suf}{TAG}.png'
                await pg.screenshot(path=str(f))
                info = await pg.evaluate("""(id)=>{const s=document.querySelector('.sheet[data-id="'+id+'"]')||document; const ov=[...s.querySelectorAll('.fover')];
                  const txt=ov.map(e=>e.innerText).join(' ');
                  const hooks=[...s.querySelectorAll('.os-hook')].map(h=>{const r=h.getBoundingClientRect(); return [h.closest('.os-v').dataset.os, r.x, r.y]});
                  return {txt, hooks, n: ov.length}}""", sid)
                bad = [c for c in info['txt'] if c in '—–'] + (['hyphen'] if ' - ' in info['txt'] or '-' in info['txt'] else [])
                print(sid, vp, 'errors:', errs[:5], 'dashes:', bad[:3], 'overlays:', info['n'], 'chars:', len(info['txt']))
                if vp[0] > 1000:
                    im = Image.open(f)
                    for k, x, y in info['hooks']:
                        X, Y = int(x * 2), int(y * 2); R = 170
                        im.crop((max(0, X - R), max(0, Y - R), X + R, Y + R)).save(OUT / f'overlays-style_{sid}_tip_{k}{TAG}.png')
                        print('  tip hook', k, round(x), round(y))
                await pg.close()
        await b.close()
asyncio.run(main())
