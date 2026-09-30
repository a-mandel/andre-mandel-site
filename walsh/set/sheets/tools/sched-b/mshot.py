import asyncio
from playwright.async_api import async_playwright
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(args=['--use-gl=swiftshader'])
        pg = await b.new_page(viewport={'width': 390, 'height': 844}, device_scale_factor=1)
        await pg.goto('http://localhost:8912/walsh/set/v2.html#A7.1', wait_until='networkidle'); await pg.wait_for_timeout(3000)
        for i, y in enumerate([0, 1200, 1700, 2600]):
            await pg.evaluate(f"() => {{ const f=[...document.querySelectorAll('.field')].find(x=>x.querySelector('.sb7')); f.scrollTop={y}; }}")
            await pg.wait_for_timeout(300)
            await pg.screenshot(path=f'/home/claude/tb/crews/schedb_m{i}.png')
        await b.close()
asyncio.run(main())
