import asyncio, sys
from playwright.async_api import async_playwright
async def main(ids, w=1914, h=1192, suffix=''):
    async with async_playwright() as p:
        b = await p.chromium.launch(args=['--use-gl=swiftshader','--enable-webgl','--ignore-gpu-blocklist'])
        pg = await b.new_page(viewport={'width': w, 'height': h})
        errs=[]
        pg.on('pageerror', lambda e: errs.append(str(e)))
        pg.on('console', lambda m: errs.append('console '+m.type+': '+m.text) if m.type=='error' else None)
        for sid in ids:
            await pg.goto(f'http://localhost:8912/walsh/set/v2.html#{sid}', wait_until='networkidle')
            await pg.wait_for_timeout(4500)
            out=f'/home/claude/tb/crews/sched-b_{sid}{suffix}.png'
            await pg.screenshot(path=out)
            print('shot', out)
        print('errors', errs)
        await b.close()
if __name__=='__main__':
    ids=sys.argv[1].split(','); w=int(sys.argv[2]) if len(sys.argv)>2 else 1914; h=int(sys.argv[3]) if len(sys.argv)>3 else 1192
    asyncio.run(main(ids,w,h,sys.argv[4] if len(sys.argv)>4 else ''))
