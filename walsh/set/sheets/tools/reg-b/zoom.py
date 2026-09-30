import sys, asyncio, re
sys.path.insert(0, '.')
from shot import route
from playwright.async_api import async_playwright
sid, x, y, w, h, out = sys.argv[1], *map(int, sys.argv[2:6]), sys.argv[6]
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(args=['--use-gl=swiftshader','--enable-webgl','--ignore-gpu-blocklist'])
        pg = await b.new_page(viewport={'width':1914,'height':1192}, device_scale_factor=2)
        await route(pg)
        await pg.goto(f'http://localhost:8904/walsh/set/v2.html#{sid}', wait_until='networkidle')
        await pg.wait_for_timeout(4500)
        await pg.screenshot(path=out, clip={'x':x,'y':y,'width':w,'height':h})
        await b.close()
asyncio.run(main())
