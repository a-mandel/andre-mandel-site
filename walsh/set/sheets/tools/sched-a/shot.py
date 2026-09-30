import asyncio, sys, re
from playwright.async_api import async_playwright
URL = 'http://127.0.0.1:8911/walsh/set/v2.html#A7.0'
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(args=['--use-gl=swiftshader', '--enable-webgl', '--ignore-gpu-blocklist'])
        for (w, h, name) in ((1914, 1192, 'sched-a_A7.0.png'), (390, 844, 'sched-a_A7.0_mobile.png')):
            ctx = await b.new_context(viewport={'width': w, 'height': h}, reduced_motion='reduce')
            pg = await ctx.new_page()
            errs = []
            pg.on('pageerror', lambda e: errs.append(str(e)))
            pg.on('console', lambda m: errs.append('console ' + m.type + ': ' + m.text) if m.type in ('error',) else None)
            await pg.goto(URL)
            await pg.wait_for_timeout(3500)
            await pg.screenshot(path=f'/home/claude/tb/crews/{name}')
            if w > 1000:
                # dash check and bounds check on the visible sheet
                info = await pg.evaluate('''() => {
                  const sh = [...document.querySelectorAll('.sheet.on')].pop();
                  const txt = sh ? sh.querySelector('.fhtml').innerText : '';
                  const f = sh.querySelector('.field').getBoundingClientRect();
                  const u = parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--u')) || 0;
                  const out = [];
                  sh.querySelectorAll('.fhtml *').forEach(el => { const r = el.getBoundingClientRect(); if (!r.width) return;
                    if (r.right > f.right + 1 || r.left < f.left - 1 || r.top < f.top - 1 || r.bottom > f.bottom + 1) out.push(el.className && el.className.baseVal !== undefined ? el.tagName : el.className + ' ' + el.textContent.slice(0, 30)); });
                  const fonts = new Set(); sh.querySelectorAll('.fhtml *').forEach(el => fonts.add(getComputedStyle(el).fontFamily.split(',')[0]));
                  return { txt, out: out.slice(0, 20), fonts: [...fonts], fieldBottom: f.bottom, fieldRight: f.right, u };
                }''')
                t = info['txt']
                print('dashes:', re.findall(r'.{0,20}[‒–—―].{0,20}|.{0,15}\s-\s.{0,15}|.{0,10}\w-\w.{0,10}', t))
                print('outside field:', info['out'])
                print('fonts:', info['fonts'])
            print(name, 'errors:', errs)
            await ctx.close()
        await b.close()
asyncio.run(main())
