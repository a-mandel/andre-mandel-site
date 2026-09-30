import asyncio, sys
from playwright.async_api import async_playwright
async def main(ids, w=1914, h=1192, tag=''):
    async with async_playwright() as p:
        b = await p.chromium.launch(args=['--use-gl=swiftshader','--enable-webgl','--ignore-gpu-blocklist'])
        pg = await b.new_page(viewport={'width':w,'height':h})
        errs=[]
        pg.on('pageerror', lambda e: errs.append(str(e)))
        pg.on('console', lambda m: m.type=='error' and errs.append(m.text))
        for i in ids:
            await pg.goto(f'http://localhost:8909/walsh/set/v2.html#{i}')
            await pg.wait_for_timeout(3500)
            await pg.screenshot(path=f'/home/claude/tb/crews/land-a_{i}{tag}.png')
        print('errors', errs)
        await b.close()
ids = sys.argv[1].split(',')
w = int(sys.argv[2]) if len(sys.argv)>2 else 1914
h = int(sys.argv[3]) if len(sys.argv)>3 else 1192
tag = sys.argv[4] if len(sys.argv)>4 else ''
asyncio.run(main(ids,w,h,tag))
