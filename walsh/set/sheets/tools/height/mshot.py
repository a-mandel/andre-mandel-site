import asyncio
from playwright.async_api import async_playwright
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(args=['--use-gl=swiftshader', '--enable-webgl', '--ignore-gpu-blocklist'])
        pg = await b.new_page(viewport={'width': 390, 'height': 844})
        async def inject(route):
            r = await route.fetch(); body = await r.text()
            body = body.replace('<script src="sheets/sched-b.js"></script>', '<script src="sheets/sched-b.js"></script>\n<script src="sheets/height.js"></script>')
            await route.fulfill(response=r, body=body)
        await pg.route('**/walsh/set/v2.html*', inject)
        await pg.goto('http://localhost:8932/walsh/set/v2.html#A1.4', wait_until='networkidle')
        await pg.wait_for_timeout(4000)
        info = await pg.evaluate('''() => { const r = document.querySelector('.ht-root'); let e = r; while (e && !(e.scrollHeight > e.clientHeight + 4 && /auto|scroll/.test(getComputedStyle(e).overflowY))) e = e.parentElement;
            if (!e) return null; e.id = e.id || 'htscroll'; return [e.id, e.scrollHeight, e.clientHeight]; }''')
        print(info)
        if info:
            k = 0
            for y in range(0, info[1], 760):
                await pg.evaluate(f'document.getElementById("{info[0]}").scrollTop = {y}')
                await pg.wait_for_timeout(400)
                await pg.screenshot(path=f'/home/claude/tb/crews/height_A1.4_m{k}.png'); k += 1
            print(k)
        await b.close()
asyncio.run(main())
