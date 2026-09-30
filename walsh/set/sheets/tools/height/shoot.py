"""screenshots of A1.4 through a served repo root; injects sheets/height.js into v2.html in flight (v2.html untouched)."""
import asyncio, sys, re, subprocess, time, os
from playwright.async_api import async_playwright
PORT = 8932
ROOT = '/home/claude/andre-mandel-site'
OUT = '/home/claude/tb/crews'
async def main():
    os.makedirs(OUT, exist_ok=True)
    async with async_playwright() as p:
        b = await p.chromium.launch(args=['--use-gl=swiftshader', '--enable-webgl', '--ignore-gpu-blocklist'])
        for vw, vh, tag in [(1914, 1192, ''), (390, 844, '_m')]:
            pg = await b.new_page(viewport={'width': vw, 'height': vh})
            async def inject(route):
                r = await route.fetch(); body = await r.text()
                if 'sheets/height.js' not in body:
                    body = body.replace('<script src="sheets/sched-b.js"></script>', '<script src="sheets/sched-b.js"></script>\n<script src="sheets/height.js"></script>')
                await route.fulfill(response=r, body=body)
            await pg.route('**/walsh/set/v2.html*', inject)
            errs = []
            pg.on('pageerror', lambda e: errs.append(str(e)))
            pg.on('console', lambda m: errs.append('console ' + m.text) if m.type == 'error' else None)
            await pg.goto(f'http://localhost:{PORT}/walsh/set/v2.html#A1.4', wait_until='networkidle')
            await pg.wait_for_timeout(6000)
            await pg.screenshot(path=f'{OUT}/height_A1.4{tag}.png', full_page=bool(tag))
            txt = await pg.evaluate('''() => { const s = document.querySelector('.sheet.on') || document.body; return s.innerText; }''')
            bad = re.findall(r'.{0,20}[–—−].{0,20}|.{0,15}\\s-\\s.{0,15}|\\w+-\\w+', txt)
            print(vw, 'dash hits', bad[:8])
            fonts = await pg.evaluate('''() => [...new Set([...document.querySelectorAll('.ht-root *')].map(e => getComputedStyle(e).fontFamily.split(',')[0]))]''')
            print(vw, 'fonts', fonts)
            if not tag:
                ov = await pg.evaluate('''() => { const f = document.querySelector('.sheet.on .fhtml') || document.querySelector('.fhtml'); if (!f) return 'no field';
                  const tb = document.querySelector('.sheet.on .tb'); const R = f.parentElement.getBoundingClientRect(); const tbx = tb ? tb.getBoundingClientRect().left : 1e9;
                  return [...f.querySelectorAll('.ht-root *')].filter(e => { const r = e.getBoundingClientRect(); return r.width && (r.right > tbx + 1 || r.left < R.left - 1 || r.bottom > R.bottom + 1); }).slice(0, 6).map(e => e.className + ' ' + (e.textContent || '').slice(0, 30)); }''')
                print('outside', ov)
            print(vw, 'errors', errs[:8])
            await pg.close()
        await b.close()
asyncio.run(main())
