"""zoomed crops of A1.4 at 2x: python3 zoom.py name x y w h (css px on the 1914 x 1192 view)"""
import asyncio, sys
from playwright.async_api import async_playwright
async def main():
    name, x, y, w, h = sys.argv[1], *map(int, sys.argv[2:6])
    async with async_playwright() as p:
        b = await p.chromium.launch(args=['--use-gl=swiftshader', '--enable-webgl', '--ignore-gpu-blocklist'])
        pg = await b.new_page(viewport={'width': 1914, 'height': 1192}, device_scale_factor=2)
        async def inject(route):
            r = await route.fetch(); body = await r.text()
            body = body.replace('<script src="sheets/sched-b.js"></script>', '<script src="sheets/sched-b.js"></script>\n<script src="sheets/height.js"></script>')
            await route.fulfill(response=r, body=body)
        await pg.route('**/walsh/set/v2.html*', inject)
        await pg.goto('http://localhost:8932/walsh/set/v2.html#A1.4', wait_until='networkidle')
        await pg.wait_for_timeout(6000)
        await pg.screenshot(path=f'/home/claude/tb/crews/height_zoom_{name}.png', clip=dict(x=x, y=y, width=w, height=h))
        await b.close()
asyncio.run(main())
