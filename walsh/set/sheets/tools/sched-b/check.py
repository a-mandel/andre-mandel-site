import asyncio, re
from playwright.async_api import async_playwright
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(args=['--use-gl=swiftshader','--enable-webgl','--ignore-gpu-blocklist'])
        errs=[]
        for vw,vh,suf in [(1914,1192,''),(390,844,'_m')]:
            pg = await b.new_page(viewport={'width': vw, 'height': vh})
            pg.on('pageerror', lambda e: errs.append(str(e)))
            await pg.goto('http://localhost:8912/walsh/set/v2.html#A7.1', wait_until='networkidle'); await pg.wait_for_timeout(3500)
            info = await pg.evaluate('''() => {
              const sh=[...document.querySelectorAll('.sheet')].find(s=>s.querySelector('.sb7') && getComputedStyle(s).visibility!=='hidden') || document.querySelector('.sb7').closest('.sheet');
              const sb=sh.querySelector('.sb7'); const txt=sh.innerText;
              const f=sh.querySelector('.field').getBoundingClientRect();
              const out=[]; sb.querySelectorAll('.sb-blk').forEach(e=>{const r=e.getBoundingClientRect(); if(r.right>f.right+1||r.bottom>f.bottom+1||r.left<f.left-1) out.push(e.className+' '+JSON.stringify([r.left,r.top,r.right,r.bottom]))});
              const fonts=new Set(); sb.querySelectorAll('*').forEach(e=>fonts.add(getComputedStyle(e).fontFamily.split(',')[0]));
              return {dash:(sb.innerText.match(/.{0,20}[\\u2012\\u2013\\u2014\\u2015-].{0,20}/g)||[]), out, fonts:[...fonts], sw:document.documentElement.scrollWidth, cw:document.documentElement.clientWidth, field:[f.right,f.bottom]};
            }''')
            print(suf, info)
            if suf:
                await pg.screenshot(path='/home/claude/tb/crews/sched-b_A7.1_390.png')
                el = await pg.query_selector('.sheet:has(.sb7) .field')
                full = await pg.evaluate("() => { const f=[...document.querySelectorAll('.field')].find(x=>x.querySelector('.sb7')); return f.scrollHeight }")
                print('field scrollHeight', full)
            await pg.close()
        print('errors', errs); await b.close()
asyncio.run(main())
