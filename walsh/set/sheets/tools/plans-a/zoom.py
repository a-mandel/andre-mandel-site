#!/usr/bin/env python3
"""zoom into a region of a sheet at print like resolution: python3 zoom.py ID x0 y0 x1 y1 (sheet inches) out.png"""
import asyncio, sys
from playwright.async_api import async_playwright
from shot import route
sid, x0, y0, x1, y1, out = sys.argv[1], *map(float, sys.argv[2:6]), sys.argv[6]
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(args=['--use-gl=swiftshader', '--enable-webgl', '--ignore-gpu-blocklist'])
        ctx = await b.new_context(viewport={'width': 1914, 'height': 1192}, device_scale_factor=3, reduced_motion='reduce')
        pg = await ctx.new_page(); await route(pg)
        await pg.goto(f'http://127.0.0.1:8905/walsh/set/v2.html#{sid}')
        await pg.wait_for_timeout(2500)
        g = await pg.evaluate(f'''()=>{{const s=document.querySelector('.sheet[data-id="{sid}"] .paper').getBoundingClientRect();return {{l:s.left,t:s.top,u:s.width/36}}}}''')
        u = g['u']
        await pg.screenshot(path=out, clip=dict(x=g['l'] + x0 * u, y=g['t'] + y0 * u, width=(x1 - x0) * u, height=(y1 - y0) * u))
        await b.close()
asyncio.run(main())
