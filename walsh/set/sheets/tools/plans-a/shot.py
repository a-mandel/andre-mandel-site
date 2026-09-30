#!/usr/bin/env python3
"""plans-a crew: screenshot our sheets from the living set, check errors, dashes and field bounds.
usage: python3 shot.py [ids...]   (server on port 8905 at the repo root)"""
import asyncio, sys, re
from playwright.async_api import async_playwright
IDS = sys.argv[1:] or ['A0.6', 'A2.0']
OUT = '/home/claude/tb/crews'
FD = '/tmp/claude-0/-home-claude-andre-mandel-site/b0abd60a-a112-5987-bb0d-bf806619c786/scratchpad/fonts'
FONTS = {
  'tenor': f'{FD}/tenor-sans/package/files/tenor-sans-latin-400-normal.woff2',
  'ebgn': f'{FD}/eb-garamond/package/files/eb-garamond-latin-400-normal.woff2',
  'ebgi': f'{FD}/eb-garamond/package/files/eb-garamond-latin-400-italic.woff2',
  'ebgn5': f'{FD}/eb-garamond/package/files/eb-garamond-latin-500-normal.woff2',
  'ebgi5': f'{FD}/eb-garamond/package/files/eb-garamond-latin-500-italic.woff2',
  'nycd': f'{FD}/nothing-you-could-do/package/files/nothing-you-could-do-latin-400-normal.woff2',
}
CSS = """@font-face{font-family:'Tenor Sans';font-style:normal;font-weight:400;src:url(/__f/tenor) format('woff2')}
@font-face{font-family:'EB Garamond';font-style:normal;font-weight:400;src:url(/__f/ebgn) format('woff2')}
@font-face{font-family:'EB Garamond';font-style:italic;font-weight:400;src:url(/__f/ebgi) format('woff2')}
@font-face{font-family:'EB Garamond';font-style:normal;font-weight:500;src:url(/__f/ebgn5) format('woff2')}
@font-face{font-family:'EB Garamond';font-style:italic;font-weight:500;src:url(/__f/ebgi5) format('woff2')}
@font-face{font-family:'Nothing You Could Do';font-style:normal;font-weight:400;src:url(/__f/nycd) format('woff2')}"""
async def route(pg):
    await pg.route(re.compile(r'fonts\.googleapis\.com'), lambda r: r.fulfill(status=200, content_type='text/css', body=CSS))
    await pg.route(re.compile(r'fonts\.gstatic\.com'), lambda r: r.fulfill(status=404, body=''))
    await pg.route(re.compile(r'/__f/'), lambda r: r.fulfill(status=200, content_type='font/woff2', body=open(FONTS[r.request.url.rsplit('/', 1)[1]], 'rb').read()))
CHECK = '''sid => {
  const s = document.querySelector(`.sheet[data-id="${sid}"]`); if (!s) return {missing: true};
  const f = s.querySelector('.fhtml') || s.querySelector('.field'), fr = s.querySelector('.field').getBoundingClientRect();
  const tb = s.querySelector('.tb').getBoundingClientRect(), u = fr.width / 31.25;
  const txt = f.innerText + ' ' + s.querySelector('.rb').innerText;
  const out = [];
  f.querySelectorAll('*').forEach(e => { if (e.closest('svg') && e.tagName !== 'svg') return; const r = e.getBoundingClientRect(); if (!r.width) return;
    if (r.left < fr.left - 1 || r.right > tb.left + 1 || r.top < fr.top + 3.2 * u || r.bottom > fr.bottom - 1.2 * u)
      out.push((e.getAttribute('class') || e.tagName) + ' ' + (e.innerText || '').slice(0, 20) + ' ' + [r.left - fr.left, r.top - fr.top, r.right - fr.left, r.bottom - fr.top].map(v => (v / u).toFixed(2)).join(','));
  });
  const fonts = new Set(); f.querySelectorAll('*').forEach(e => { if (e.innerText && e.children.length === 0) fonts.add(getComputedStyle(e).fontFamily.split(',')[0]); });
  return {dash: (txt.match(/[\\u2012-\\u2015]|\\s-\\s|\\w-\\s|\\s-\\w/g) || []), out: out.slice(0, 20), fonts: [...fonts], ok: document.fonts.check('12px "Tenor Sans"')};
}'''
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(args=['--use-gl=swiftshader', '--enable-webgl', '--ignore-gpu-blocklist'])
        for vw, vh, tag in ((1914, 1192, ''), (390, 844, '_m')):
            ctx = await b.new_context(viewport={'width': vw, 'height': vh}, reduced_motion='reduce')
            for sid in IDS:
                pg = await ctx.new_page(); await route(pg)
                errs = []
                pg.on('pageerror', lambda e: errs.append(str(e)))
                pg.on('console', lambda m: errs.append('console ' + m.text) if m.type == 'error' else None)
                await pg.goto(f'http://127.0.0.1:8905/walsh/set/v2.html#{sid}')
                await pg.wait_for_timeout(2500)
                await pg.screenshot(path=f'{OUT}/plans-a_{sid}{tag}.png', full_page=False)
                if not tag:
                    print(sid, await pg.evaluate(CHECK, sid), errs[:5])
                else:
                    print(sid, 'mobile', errs[:5])
                await pg.close()
            await ctx.close()
        await b.close()
if __name__ == "__main__":
    asyncio.run(main())
