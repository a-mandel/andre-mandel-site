import asyncio, sys, re
from playwright.async_api import async_playwright
PORT = 8903
IDS = sys.argv[1:] or ['F1.0', 'A1.3']
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(args=['--use-gl=swiftshader', '--enable-webgl', '--ignore-gpu-blocklist'])
        for vw, vh, tag in [(1914, 1192, ''), (390, 844, '_m')]:
            pg = await b.new_page(viewport={'width': vw, 'height': vh})
            errs = []
            pg.on('pageerror', lambda e: errs.append(str(e)))
            pg.on('console', lambda m: errs.append('console ' + m.text) if m.type == 'error' else None)
            for i in IDS:
                if tag and i != IDS[0]: continue
                await pg.goto(f'http://localhost:{PORT}/walsh/set/v2.html#{i}', wait_until='networkidle')
                await pg.wait_for_timeout(2500)
                await pg.screenshot(path=f'/home/claude/tb/crews/reg-a_{i}{tag}.png')
                txt = await pg.evaluate('''() => { const s=[...document.querySelectorAll('.sheet')].find(e=>getComputedStyle(e).display!=='none' && e.getBoundingClientRect().width>0 && e.classList.contains('on')) || document.querySelector('.sheet.on') || document; return s.innerText; }''')
                bad = [m for m in re.findall(r'.{0,20}[–—].{0,20}|.{0,15}\s-\s.{0,15}', txt)]
                print(vw, i, 'dash hits', bad[:5])
            print(vw, 'errors', errs[:8])
            await pg.close()
        await b.close()
asyncio.run(main())
