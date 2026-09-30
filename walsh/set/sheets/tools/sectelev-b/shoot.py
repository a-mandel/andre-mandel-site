"""sectelev-b: serve check. Screenshots of A5.0 and A5.1 at 1914 x 1192 and one at 390 x 844, page errors, dash scan."""
import sys, re
from playwright.sync_api import sync_playwright
PORT = 8908
OUT = '/home/claude/tb/crews'
ids = sys.argv[1:] or ['A5.0', 'A5.1']
with sync_playwright() as p:
    b = p.chromium.launch(args=['--use-gl=swiftshader', '--enable-webgl', '--ignore-gpu-blocklist'])
    errs = []
    for sid in ids:
        pg = b.new_page(viewport={'width': 1914, 'height': 1192})
        pg.on('pageerror', lambda e: errs.append(str(e)))
        pg.on('console', lambda m: errs.append(m.text) if m.type == 'error' else None)
        pg.goto(f'http://localhost:{PORT}/walsh/set/v2.html#{sid}', wait_until='networkidle')
        pg.wait_for_timeout(7000)
        pg.screenshot(path=f'{OUT}/sectelev-b_{sid}.png')
        # visible text on the current sheet, scanned for dashes
        txt = pg.evaluate("""() => { const s = document.querySelector('.sheet.on'); return s ? s.innerText : ''; }""")
        bad = [l for l in txt.split('\n') if re.search(r'[–—]| - |\w-\s|\s-\w', l)]
        print(sid, 'dash lines:', bad[:8])
        # anything of ours outside the field box
        o = pg.evaluate("""() => { const s = document.querySelector('.sheet.on'); const f = s.querySelector('.field').getBoundingClientRect();
          const out = []; s.querySelectorAll('.seb *').forEach(e => { const r = e.getBoundingClientRect(); if (!r.width) return;
            if (r.left < f.left - 1 || r.right > f.right + 1 || r.top < f.top - 1 || r.bottom > f.bottom + 1) out.push(e.className.baseVal !== undefined ? e.tagName : (e.className || e.tagName) + ' ' + Math.round(r.right - f.right) + ',' + Math.round(r.bottom - f.bottom)); });
          const tb = s.querySelector('.tb'); return { out: out.slice(0, 10), tbLeft: tb ? tb.getBoundingClientRect().left : null,
            maxRight: Math.max(...[...s.querySelectorAll('.seb *')].map(e => e.getBoundingClientRect().right)),
            maxBottom: Math.max(...[...s.querySelectorAll('.seb *')].map(e => e.getBoundingClientRect().bottom)), fieldBottom: f.bottom,
            fonts: [...new Set([...s.querySelectorAll('.seb *')].map(e => getComputedStyle(e).fontFamily.split(',')[0]))] }; }""")
        print(sid, o)
        pg.close()
    pg = b.new_page(viewport={'width': 390, 'height': 844}, device_scale_factor=2)
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto(f'http://localhost:{PORT}/walsh/set/v2.html#{ids[-1]}', wait_until='networkidle')
    pg.wait_for_timeout(2000)
    pg.screenshot(path=f'{OUT}/sectelev-b_{ids[-1]}_mobile.png')
    pg.evaluate("document.querySelector('.sheet.on .field').scrollTop = 900")
    pg.wait_for_timeout(400)
    pg.screenshot(path=f'{OUT}/sectelev-b_{ids[-1]}_mobile2.png')
    print('errors:', errs)
    b.close()
