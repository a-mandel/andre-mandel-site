#!/usr/bin/env python3
"""Screenshot living set sheets: shot.py PORT OUTPREFIX ID [ID ...] [--mobile]"""
import asyncio, sys
from playwright.async_api import async_playwright
async def main():
    port, pre, *ids = sys.argv[1:]
    mob = '--mobile' in ids; ids = [i for i in ids if i != '--mobile']
    async with async_playwright() as p:
        b = await p.chromium.launch(args=['--use-gl=swiftshader', '--enable-webgl', '--ignore-gpu-blocklist'])
        vp = {'width': 390, 'height': 844} if mob else {'width': 1914, 'height': 1192}
        ctx = await b.new_context(viewport=vp, reduced_motion='reduce', device_scale_factor=2 if mob else 1)
        for i in ids:
            pg = await ctx.new_page(); errs = []
            pg.on('pageerror', lambda e: errs.append(str(e)))
            pg.on('console', lambda m: errs.append('console ' + m.text) if m.type == 'error' else None)
            await pg.goto(f'http://127.0.0.1:{port}/walsh/set/v2.html#{i}')
            await pg.wait_for_timeout(4500)
            out = f'{pre}_{i}{"_m" if mob else ""}.png'
            await pg.screenshot(path=out)
            print(out, errs)
            await pg.close()
        await b.close()
asyncio.run(main())
