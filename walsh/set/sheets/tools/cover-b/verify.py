#!/usr/bin/env python3
"""cover-b checks: images load, nothing past the field or into the footer or title block, no dashes in visible text"""
import asyncio, json, sys
from playwright.async_api import async_playwright
async def main():
    port = sys.argv[1] if len(sys.argv) > 1 else '8902'
    async with async_playwright() as p:
        b = await p.chromium.launch(args=['--use-gl=swiftshader', '--enable-webgl', '--ignore-gpu-blocklist'])
        pg = await (await b.new_context(viewport={'width': 1914, 'height': 1192}, reduced_motion='reduce')).new_page()
        errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
        for sid in ('A0.5', 'A9.1'):
            await pg.goto(f'http://127.0.0.1:{port}/walsh/set/v2.html#{sid}'); await pg.wait_for_timeout(3500)
            r = await pg.evaluate('''sid => {
              const sh = document.querySelector(`.sheet[data-id="${sid}"]`), f = sh.querySelector('.field').getBoundingClientRect();
              const tb = sh.querySelector('.tb').getBoundingClientRect(), rb = sh.querySelector('.rb .rdata').getBoundingClientRect(), rt = sh.querySelector('.rt').getBoundingClientRect();
              const bad = [];
              sh.querySelectorAll('.fhtml .view, .fhtml .note, .fhtml .vt, .fhtml .dkey').forEach(e => { const r = e.getBoundingClientRect();
                if (r.left < f.left - 1 || r.right > tb.left + 1 || r.bottom > rb.top + 1 || r.top < rt.bottom - 40) bad.push([e.className, Math.round(r.left), Math.round(r.top), Math.round(r.right), Math.round(r.bottom)]); });
              const imgs = [...sh.querySelectorAll('.fhtml img')].map(i => [i.getAttribute('src'), i.naturalWidth]);
              const txt = sh.querySelector('.fhtml').innerText + ' ' + sh.querySelector('.rb').innerText;
              const dash = (txt.match(/[\\u2012-\\u2015]|\\s-\\s|\\w-\\s|\\s-\\w/g) || []);
              return { bad, imgs, dash, fields: [Math.round(f.left), Math.round(tb.left), Math.round(rb.top)] };
            }''', sid)
            print(sid, json.dumps(r))
        print('page errors', errs)
        await b.close()
asyncio.run(main())
