"""overlays-sectelev: screenshots of A3.0, A3.1, A4.0 to A4.3 on port 8942, checks errors, dashes, field bounds.
usage: python3 shoot.py [ids...] [--pre tag] [--zoom] [--mobile] [--pdf]"""
import asyncio, sys, re, os
from playwright.async_api import async_playwright
PORT = 8942
OUT = '/home/claude/tb/ov'
args = sys.argv[1:]
flags = {a for a in args if a.startswith('--')}
pre = ''
if '--pre' in args: pre = args[args.index('--pre') + 1]
IDS = [a for a in args if not a.startswith('--') and a != pre] or ['A3.0', 'A3.1', 'A4.0', 'A4.1', 'A4.2', 'A4.3']
CHECK = '''(id) => {
  const s = [...document.querySelectorAll('.sheet')].find(e => e.dataset.id === id); if (!s) return {err: 'no sheet'};
  const f = s.querySelector('.field'), R = f.getBoundingClientRect(), tb = s.querySelector('.tb').getBoundingClientRect();
  const hd = s.querySelector('.rt').getBoundingClientRect(), ft = s.querySelector('.rb .ticks') || s.querySelector('.rb');
  const out = [], hit = [];
  s.querySelectorAll('.ose *').forEach(e => { const r = e.getBoundingClientRect(); if (!r.width || !r.height) return;
    if (r.right > tb.left + 1 || r.left < R.left - 1 || r.bottom > R.bottom + 1 || r.top < R.top - 1) out.push((e.getAttribute('class') || e.tagName) + ' ' + (e.textContent || '').slice(0, 24));
    if (e.classList.contains('ot') && r.left < hd.right && r.top < hd.bottom && r.bottom > hd.top && r.right > hd.left) hit.push('header ' + e.textContent.slice(0, 24)); });
  const txt = [...s.querySelectorAll('.ose')].map(e => e.innerText).join(' ');
  const dash = txt.match(/.{0,12}[\\u2013\\u2014\\u2212].{0,12}|.{0,12}\\s-\\s.{0,12}|\\w+-\\w+/g) || [];
  const fonts = [...new Set([...s.querySelectorAll('.ose *')].map(e => getComputedStyle(e).fontFamily.split(',')[0]))];
  const fh = s.querySelector('.fhtml'); let fo = null;
  if (fh) { const kids = [...fh.querySelectorAll('*')].filter(e => { const r = e.getBoundingClientRect(); return r.width && (r.right > R.right + 1 || r.bottom > R.bottom + 1); }); fo = kids.length + ' ' + kids.slice(0, 3).map(e => (e.getAttribute('class') || e.tagName)).join(', '); }
  return {out: out.slice(0, 8), n_out: out.length, hdr: hit.slice(0, 4), dash: dash.slice(0, 6), fonts, fhtml_over: fo, sw: document.documentElement.scrollWidth, cw: document.documentElement.clientWidth};
}'''
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(args=['--use-gl=swiftshader', '--enable-webgl', '--ignore-gpu-blocklist'])
        views = [(1914, 1192, '')]
        if '--mobile' in flags: views.append((390, 844, '_m'))
        for vw, vh, tag in views:
            pg = await b.new_page(viewport={'width': vw, 'height': vh})
            errs = []
            pg.on('pageerror', lambda e: errs.append(str(e)))
            pg.on('console', lambda m: errs.append('console ' + m.text) if m.type == 'error' else None)
            ids = IDS if not tag else ['A4.1']
            for i, sid in enumerate(ids):
                await pg.goto(f'http://localhost:{PORT}/walsh/set/v2.html#{sid}', wait_until='networkidle')
                await pg.wait_for_timeout(4500)
                await pg.screenshot(path=f'{OUT}/{pre}overlays-sectelev_{sid}{tag}.png', full_page=bool(tag))
                r = await pg.evaluate(CHECK, sid)
                print(sid, tag, r)
                if '--zoom' in flags and not tag and sid == 'A4.1':
                    await pg.evaluate('''() => { const s = [...document.querySelectorAll('.sheet')].find(e => e.dataset.id === 'A4.1'); s.style.setProperty('--u', '400px'); }''')
            print('errors', errs[:8])
            await pg.close()
        if '--pdf' in flags:
            pg = await b.new_page(viewport={'width': 1914, 'height': 1192})
            await pg.goto(f'http://localhost:{PORT}/walsh/set/v2.html#A3.1', wait_until='networkidle')
            await pg.wait_for_timeout(4000)
            # print A3.1 alone: drop every other sheet
            await pg.evaluate('''() => document.querySelectorAll('.sheet').forEach(s => { if (s.dataset.id !== 'A3.1') s.remove(); })''')
            await pg.emulate_media(media='print')
            await pg.wait_for_timeout(800)
            info = await pg.evaluate('''() => { const s = document.querySelector('.sheet'); const r = s.getBoundingClientRect();
               return {w: r.width, h: r.height, sw: document.documentElement.scrollWidth, sh: document.documentElement.scrollHeight}; }''')
            print('print media A3.1', info)
            await pg.pdf(path=f'{OUT}/overlays-sectelev_A3.1.pdf', width='36in', height='24in', print_background=True, prefer_css_page_size=True)
            await pg.close()
        await b.close()
asyncio.run(main())
