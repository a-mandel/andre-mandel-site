import asyncio, sys
from playwright.async_api import async_playwright
from PIL import Image
sid = sys.argv[1]
OUT='/tmp/claude-0/-home-claude-andre-mandel-site/b0abd60a-a112-5987-bb0d-bf806619c786/scratchpad/rega/'
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(args=['--use-gl=swiftshader'])
        pg = await b.new_page(viewport={'width':390,'height':844})
        await pg.goto(f'http://localhost:8903/walsh/set/v2.html#{sid}', wait_until='networkidle'); await pg.wait_for_timeout(1500)
        H = await pg.evaluate('''() => { const f=[...document.querySelectorAll('.field')].find(f=>f.getBoundingClientRect().width>0 && f.scrollHeight>f.clientHeight && f.closest('.sheet') && getComputedStyle(f.closest('.sheet')).visibility!=='hidden' && f.querySelector('.ra-root')); window.__f=f; return f? [f.scrollHeight,f.clientHeight]:null }''')
        print(H)
        shots=[]; y=0; k=0
        while y < H[0]:
            await pg.evaluate(f'window.__f.scrollTop={y}'); await pg.wait_for_timeout(300)
            fn=OUT+f'ms{k}.png'; await pg.screenshot(path=fn, clip={'x':0,'y':0,'width':390,'height':H[1]}); shots.append(fn); y+=H[1]-40; k+=1
        ims=[Image.open(f) for f in shots]
        W=Image.new('RGB',(390*len(ims),ims[0].height),'white')
        for i,im in enumerate(ims): W.paste(im,(390*i,0))
        W.save(OUT+f'mob_{sid}.png'); print(len(ims))
        await b.close()
asyncio.run(main())
