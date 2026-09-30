import sys, asyncio, re
F='/tmp/claude-0/-home-claude/b0abd60a-a112-5987-bb0d-bf806619c786/scratchpad/fonts/'
FILES={'tenor':F+'fontsource-tenor-sans-5.3.0/package/files/tenor-sans-latin-400-normal.woff2',
 'ebgn':F+'fontsource-eb-garamond-5.3.0/package/files/eb-garamond-latin-400-normal.woff2',
 'ebgi':F+'fontsource-eb-garamond-5.3.0/package/files/eb-garamond-latin-400-italic.woff2',
 'ebgn5':F+'fontsource-eb-garamond-5.3.0/package/files/eb-garamond-latin-500-normal.woff2',
 'ebgi5':F+'fontsource-eb-garamond-5.3.0/package/files/eb-garamond-latin-500-italic.woff2',
 'nycd':F+'fontsource-nothing-you-could-do-5.3.0/package/files/nothing-you-could-do-latin-400-normal.woff2'}
CSS=''.join(f"@font-face{{font-family:'{fam}';font-style:{st};font-weight:{w};src:url(/__f/{k}.woff2) format('woff2')}}" for k,fam,st,w in [('tenor','Tenor Sans','normal',400),('ebgn','EB Garamond','normal',400),('ebgi','EB Garamond','italic',400),('ebgn5','EB Garamond','normal',500),('ebgi5','EB Garamond','italic',500),('nycd','Nothing You Could Do','normal',400)])
async def route(pg):
    await pg.route(re.compile(r'fonts\.googleapis\.com'), lambda r: r.fulfill(status=200, content_type='text/css', body=CSS))
    await pg.route(re.compile(r'/__f/'), lambda r: r.fulfill(status=200, content_type='font/woff2', body=open(FILES[r.request.url.split('/__f/')[1].split('.')[0]],'rb').read()))
from playwright.async_api import async_playwright
ids = sys.argv[1].split(',') if len(sys.argv) > 1 else []
mobile = len(sys.argv) > 2
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(args=['--use-gl=swiftshader','--enable-webgl','--ignore-gpu-blocklist'])
        for i in ids:
            vp = {'width':390,'height':844} if mobile else {'width':1914,'height':1192}
            pg = await b.new_page(viewport=vp, device_scale_factor=2 if mobile else 1)
            await route(pg)
            errs = []
            pg.on('pageerror', lambda e: errs.append(str(e)))
            pg.on('console', lambda m: errs.append('console '+m.text) if m.type=='error' else None)
            await pg.goto(f'http://localhost:8904/walsh/set/v2.html#{i}', wait_until='networkidle')
            await pg.wait_for_timeout(4500)
            out = f'/home/claude/tb/crews/reg-b_{i}{"_m" if mobile else ""}.png'
            await pg.screenshot(path=out)
            # checks: dashes and overflow in my sheet
            res = await pg.evaluate('''(id)=>{
              const s=[...document.querySelectorAll('.sheet')].find(e=>e.dataset.id===id); if(!s) return 'missing';
              const t=s.querySelector('.fhtml')?.innerText||'';
              const d=[...t.matchAll(/.{0,20}[–—].{0,20}|.{0,15}\\s-\\s.{0,15}/g)].map(m=>m[0]);
              const f=s.querySelector('.field').getBoundingClientRect();
              const u=parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--u'));
              let over=[]; s.querySelectorAll('.fhtml *').forEach(e=>{const r=e.getBoundingClientRect(); if(!r.width||e.classList.contains('rgx')) return;
                 if(r.right>f.left+31.25*u+1||r.left<f.left-1||r.top<f.top+3.2*u||r.bottom>f.bottom-4.2*u) over.push(e.className+':'+(e.textContent||'').slice(0,30)+' '+Math.round((r.bottom-f.top)/u*10)/10)});
              const fonts=new Set(); s.querySelectorAll('.fhtml *').forEach(e=>fonts.add(getComputedStyle(e).fontFamily.split(',')[0]));
              const cols=[...s.querySelectorAll('.rgc,.rgd')].map(c=>{const r=c.getBoundingClientRect();return [+((r.left-f.left)/u).toFixed(2),+((r.bottom-f.top)/u).toFixed(2)]});
              const tg={}; s.querySelectorAll('.rgt dt').forEach(dt=>{if(/Height|Codes/.test(dt.textContent)){const r=dt.parentNode.getBoundingClientRect(); tg[dt.textContent]=[+((r.left-f.left)/u+1.25).toFixed(2),+((r.top-f.top)/u+.5).toFixed(2),+((r.right-f.left)/u+1.25).toFixed(2),+((r.bottom-f.top)/u+.5).toFixed(2)]}});
              return JSON.stringify({cols, tg, dash:d, over:over.slice(0,12), nover:over.length, fonts:[...fonts], u});
            }''', i)
            print(i, 'errors:', errs, res if not mobile else '')
            await pg.close()
        await b.close()
if __name__ == "__main__": asyncio.run(main())
