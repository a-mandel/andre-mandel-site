"""zoom proof: python3 zoom.py A4.1 x0 y0 x1 y1 [tag]  (field inches) at device scale 3, to /home/claude/tb/ov/"""
import asyncio, sys
from playwright.async_api import async_playwright
sid = sys.argv[1]; x0, y0, x1, y1 = map(float, sys.argv[2:6]); tag = sys.argv[6] if len(sys.argv) > 6 else 'zoom'
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(args=['--use-gl=swiftshader'])
        pg = await b.new_page(viewport={'width': 1914, 'height': 1192}, device_scale_factor=3)
        await pg.goto(f'http://localhost:8942/walsh/set/v2.html#{sid}', wait_until='networkidle')
        await pg.wait_for_timeout(4500)
        r = await pg.evaluate('''(id) => { const s = [...document.querySelectorAll('.sheet')].find(e => e.dataset.id === id); const f = s.querySelector('.field').getBoundingClientRect(); return [f.left, f.top, f.width / 31.25]; }''', sid)
        L, Tp, u = r
        await pg.screenshot(path=f'/home/claude/tb/ov/overlays-sectelev_{sid}_{tag}.png', clip={'x': L + x0 * u, 'y': Tp + y0 * u, 'width': (x1 - x0) * u, 'height': (y1 - y0) * u})
        await b.close()
asyncio.run(main())
