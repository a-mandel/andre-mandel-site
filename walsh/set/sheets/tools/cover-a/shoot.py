#!/usr/bin/env python3
"""cover-a: screenshots of the crew's sheets in the living set (walsh/set/v2.html), desktop and phone, plus checks.
Google Fonts are served from local copies (the sandbox cannot reach fonts.googleapis.com).
  python3 walsh/set/sheets/tools/cover-a/shoot.py [A0.9 ...]
"""
import functools, http.server, re, socketserver, sys, threading
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
FONTS = Path('/tmp/claude-0/-home-claude-andre-mandel-site/b0abd60a-a112-5987-bb0d-bf806619c786/scratchpad/fonts')
OUT = Path('/home/claude/tb/crews')
PORT = 8901
CSS = """@font-face{font-family:'Tenor Sans';font-style:normal;font-weight:400;src:url(/__f/tenor.woff2) format('woff2')}
@font-face{font-family:'EB Garamond';font-style:normal;font-weight:400;src:url(/__f/ebg-n.woff2) format('woff2')}
@font-face{font-family:'EB Garamond';font-style:italic;font-weight:400;src:url(/__f/ebg-i.woff2) format('woff2')}
@font-face{font-family:'EB Garamond';font-style:normal;font-weight:500;src:url(/__f/ebg-n5.woff2) format('woff2')}
@font-face{font-family:'EB Garamond';font-style:italic;font-weight:500;src:url(/__f/ebg-i5.woff2) format('woff2')}
@font-face{font-family:'Nothing You Could Do';font-style:normal;font-weight:400;src:url(/__f/nycd.woff2) format('woff2')}"""


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


def route(pg):
    pg.route(re.compile(r'fonts\.googleapis\.com'), lambda r: r.fulfill(status=200, content_type='text/css', body=CSS))
    pg.route(re.compile(r'fonts\.gstatic\.com'), lambda r: r.fulfill(status=404, body=''))
    pg.route(re.compile(r'/__f/'), lambda r: r.fulfill(status=200, content_type='font/woff2', body=(FONTS / r.request.url.rsplit('/', 1)[1]).read_bytes()))


def main(ids):
    from playwright.sync_api import sync_playwright
    socketserver.TCPServer.allow_reuse_address = True
    httpd = socketserver.ThreadingTCPServer(('127.0.0.1', PORT), functools.partial(Quiet, directory=str(ROOT)))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    OUT.mkdir(parents=True, exist_ok=True)
    errs = []
    with sync_playwright() as p:
        b = p.chromium.launch(args=['--use-gl=swiftshader', '--enable-webgl', '--ignore-gpu-blocklist'])
        for w, h, tag, dpr in [(1914, 1192, '', 1), (390, 844, '_m', 2)]:
            ctx = b.new_context(viewport={'width': w, 'height': h}, device_scale_factor=dpr, has_touch=bool(tag))
            for sid in ids:
                pg = ctx.new_page(); route(pg)
                pg.on('pageerror', lambda e: errs.append(('pageerror', str(e))))
                pg.on('console', lambda m: errs.append((m.type, m.text)) if m.type == 'error' and 'model' not in m.text else None)
                pg.goto(f'http://127.0.0.1:{PORT}/walsh/set/v2.html#{sid}')
                pg.wait_for_timeout(6500)
                pg.screenshot(path=str(OUT / f'cover-a_{sid}{tag}.png'))
                if not tag:
                    info = pg.evaluate("""() => {
                      const sh = document.querySelector('.sheet.on') || document.querySelector('.sheet');
                      const f = sh.querySelector('.fhtml'); const fr = f.getBoundingClientRect();
                      const out = [];
                      f.querySelectorAll('.ca-v, .ca-v .note, .ca-v .lbl, .ca-v .vt, .ca-leg').forEach(e => { const r = e.getBoundingClientRect();
                        if (r.width && (r.left < fr.left - 1 || r.right > fr.right + 1 || r.top < fr.top - 1 || r.bottom > fr.bottom + 1)) out.push(e.className + ' ' + (e.textContent || '').slice(0, 30)); });
                      const txt = f.innerText; const dashes = (txt.match(/[\\u2013\\u2014]| - /g) || []).length;
                      const fonts = [...new Set([...f.querySelectorAll('*')].map(e => getComputedStyle(e).fontFamily.split(',')[0]))];
                      const imgs = [...f.querySelectorAll('img')].map(i => i.complete && i.naturalWidth);
                      return { out, dashes, fonts, imgs, id: sh.dataset.id || '' };
                    }""")
                    print(sid, info)
                pg.close()
            ctx.close()
        b.close()
    httpd.shutdown()
    print('errors:', errs[:10])


if __name__ == '__main__':
    main(sys.argv[1:] or ['A0.9'])
