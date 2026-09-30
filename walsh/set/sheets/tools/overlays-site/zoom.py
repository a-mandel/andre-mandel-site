"""zoomed crops at 2x for review, and the A1.2 registration proof. python3 zoom.py <id> x y w h name"""
import asyncio, sys
from playwright.async_api import async_playwright
async def main():
    sid, x, y, w, h, name = sys.argv[1], *map(int, sys.argv[2:6]), sys.argv[6]
    async with async_playwright() as p:
        b = await p.chromium.launch(args=['--use-gl=swiftshader'])
        pg = await b.new_page(viewport={'width': 1914, 'height': 1192}, device_scale_factor=2)
        await pg.goto(f'http://localhost:8943/walsh/set/v2.html#{sid}', wait_until='networkidle')
        await pg.wait_for_timeout(2500)
        await pg.screenshot(path=f'/home/claude/tb/ov/overlays-site_zoom_{name}.png', clip={'x': x, 'y': y, 'width': w, 'height': h})
        await b.close()
asyncio.run(main())
