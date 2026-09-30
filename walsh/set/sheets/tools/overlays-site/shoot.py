"""overlays-site crew: screenshots of A1.2, L1.0, L1.1, F1.0 on port 8943, checks errors and dashes.
   python3 walsh/set/sheets/tools/overlays-site/shoot.py [ids...]"""
import asyncio, sys, re, os
from playwright.async_api import async_playwright
PORT = 8943
OUT = '/home/claude/tb/ov'
IDS = sys.argv[1:] or ['A1.2', 'L1.0', 'L1.1', 'F1.0']
async def main():
    os.makedirs(OUT, exist_ok=True)
    async with async_playwright() as p:
        b = await p.chromium.launch(args=['--use-gl=swiftshader', '--enable-webgl', '--ignore-gpu-blocklist'])
        runs = [(i, 1914, 1192, '') for i in IDS] + ([('A1.2', 390, 844, '_m')] if 'A1.2' in IDS else [])
        for sid, vw, vh, tag in runs:
            pg = await b.new_page(viewport={'width': vw, 'height': vh})
            errs = []
            pg.on('pageerror', lambda e: errs.append(str(e)))
            pg.on('console', lambda m: errs.append('console ' + m.text) if m.type == 'error' else None)
            await pg.goto(f'http://localhost:{PORT}/walsh/set/v2.html#{sid}', wait_until='networkidle')
            await pg.wait_for_timeout(3500)
            await pg.screenshot(path=f'{OUT}/overlays-site_{sid}{tag}.png', full_page=False)
            txt = await pg.evaluate('''(id) => [...document.querySelectorAll(`.sheet[data-id="${id}"] .ovs`)].map(e => e.innerText).join(' | ')''', sid)
            bad = re.findall(r'.{0,20}[–—−].{0,20}|.{0,15}\s-\s.{0,15}|[A-Za-z]+-[A-Za-z]+', txt)
            n = await pg.evaluate('''(id) => document.querySelectorAll(`.sheet[data-id="${id}"] .ovs`).length''', sid)
            fonts = await pg.evaluate('''(id) => [...new Set([...document.querySelectorAll(`.sheet[data-id="${id}"] .ovs *`)].filter(e=>e.childNodes.length && [...e.childNodes].some(c=>c.nodeType===3&&c.textContent.trim())).map(e => getComputedStyle(e).fontFamily.split(',')[0]))]''', sid)
            print(sid, vw, 'ovs', n, 'dashes', bad[:6], 'fonts', fonts, 'errors', errs[:6])
            if not tag:
                ov = await pg.evaluate('''(id) => { const s = document.querySelector(`.sheet[data-id="${id}"]`); const tb = s.querySelector('.tb'); const f = s.querySelector('.field').getBoundingClientRect(); const tbx = tb ? tb.getBoundingClientRect().left : 1e9;
                  return [...s.querySelectorAll('.ovs span, .ovs b, .ovs i')].filter(e => { const r = e.getBoundingClientRect(); return r.width && (r.right > tbx + 1 || r.left < f.left - 1 || r.bottom > f.bottom + 1 || r.top < f.top - 1); }).slice(0, 6).map(e => (e.textContent || '').slice(0, 40)); }''', sid)
                print('   outside', ov)
            await pg.close()
        await b.close()
asyncio.run(main())
