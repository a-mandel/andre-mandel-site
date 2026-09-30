#!/usr/bin/env python3
"""cover-a: burns the drafting marks into the cover still (print only still for A0.0), then writes the WebP.
A vertical run off the tip with its ticks, a datum out to the margin, two notes in hand on thin leaders with orange dots.
Three fonts only (Tenor Sans, EB Garamond, Nothing You Could Do), sized in true inches at 200 px per inch.

  python3 walsh/set/sheets/tools/cover-a/cover_overlay.py
"""
import json, sys
from pathlib import Path
from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import sheet_data as SD

RAW = SD.RAW
OUT = SD.ROOT / 'walsh' / 'set' / 'sheets' / 'assets' / 'cover-a' / 'cover-still.webp'
FONTS = Path('/tmp/claude-0/-home-claude-andre-mandel-site/b0abd60a-a112-5987-bb0d-bf806619c786/scratchpad/fonts')
PPI = 200


def main():
    meta = json.loads((RAW / 'cover.json').read_text())
    base = Image.open(RAW / 'cover_base.png')
    W, H = base.size
    P = lambda k: SD.project(meta, SD.PTS[k])
    I = lambda v: v * PPI                 # inches to px
    tip, grd, t30, tree, pit, main_ = P('tip'), P('tipGrade'), P('tip30'), P('treeMid'), P('bench'), P('main')
    x = tip[0] * W
    y0, ytop = min(grd[1], 0.84) * H, 0.2 * H
    svg = []
    ln = lambda d, w=1.4, op=0.6, col='#1b1a18': svg.append(f'<path d="{d}" fill="none" stroke="{col}" stroke-width="{w}" stroke-opacity="{op}" stroke-linecap="round"/>')
    ln(f'M{x:.1f} {y0:.1f} V{ytop:.1f}', 1.5, 0.55)
    for f in (0.2, 0.4, 0.6, 0.8):
        yy = y0 + (ytop - y0) * f; ln(f'M{x - I(0.06):.1f} {yy:.1f} h{I(0.12):.1f}', 1.4, 0.55)
    yt = tip[1] * H; ln(f'M{x - I(0.18):.1f} {yt:.1f} h{I(0.36):.1f}', 3.2, 1, '#c07a2c')
    svg.append(f'<circle cx="{x:.1f}" cy="{yt:.1f}" r="{I(0.05):.1f}" fill="#c07a2c"/>')
    y30 = t30[1] * H - I(0.22); ln(f'M{x - I(0.14):.1f} {y30:.1f} h{I(0.28):.1f}', 2.0, 0.85)
    # datum at the main floor, out to the right margin
    mx, my = main_[0] * W, main_[1] * H
    ln(f'M{mx:.1f} {my:.1f} H{0.965 * W:.1f}', 1.3, 0.45)
    ln(f'M{0.965 * W - I(0.07):.1f} {my + I(0.07):.1f} l{I(0.14):.1f} {-I(0.14):.1f}', 2.0, 0.85)
    labels = [
        (x + I(0.22), yt, 'l', 'Tip', '6023.0 · 29.4 ft over grade', True),
        (x + I(0.22), y30, 'l', '30 ft limit', '', False),
        (0.965 * W - I(0.14), my - I(0.2), 'r', 'Main', '5997.5', False),
    ]
    # notes in hand, each on a thin curved leader ending in an orange dot
    notes = [('keep the signature tree', (tree[0] * W, tree[1] * H), ((tree[0] + 0.045) * W, 0.19 * H)),
             ('fire pit, built in bench', (pit[0] * W, pit[1] * H), ((pit[0] + 0.05) * W, 0.815 * H))]
    nh = []
    for text, (px, py), (tx, ty) in notes:
        sx, sy = tx - I(0.14), ty
        cx, cy = sx + (px - sx) * 0.18, sy + (py - sy) * 0.85
        ln(f'M{sx:.1f} {sy:.1f} Q{cx:.1f} {cy:.1f} {px:.1f} {py:.1f}', 1.6, 0.8)
        svg.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="{I(0.055):.1f}" fill="#c07a2c"/>')
        nh.append(f'<span class="note" style="left:{tx:.1f}px;top:{ty:.1f}px">{text}</span>')
    lab = ''.join(f'<span class="lab {a}" style="left:{lx:.1f}px;top:{ly:.1f}px"><b{" class=acc" if acc else ""}>{t}</b>{f"<i>{v}</i>" if v else ""}</span>' for lx, ly, a, t, v, acc in labels)
    html = f'''<!doctype html><html><head><meta charset="utf-8"><style>
@font-face{{font-family:'Tenor Sans';src:url(file://{FONTS}/tenor.woff2)}}
@font-face{{font-family:'EB Garamond';font-style:italic;src:url(file://{FONTS}/ebg-i.woff2)}}
@font-face{{font-family:'Nothing You Could Do';src:url(file://{FONTS}/nycd.woff2)}}
html,body{{margin:0;background:transparent}}
#w{{position:relative;width:{W}px;height:{H}px}}
#w img,#w svg{{position:absolute;left:0;top:0;width:{W}px;height:{H}px}}
.note{{position:absolute;font:400 {I(0.36):.0f}px/1 'Nothing You Could Do';color:#1b1a18;white-space:nowrap;transform:translate(0,-58%)}}
.lab{{position:absolute;display:flex;align-items:baseline;gap:{I(0.07):.0f}px;white-space:nowrap;transform:translate(0,-50%)}}
.lab.r{{transform:translate(-100%,-50%)}}
.lab b{{font:400 {I(0.13):.0f}px/1 'Tenor Sans';letter-spacing:.16em;text-transform:uppercase;color:#1b1a18;font-weight:400}}
.lab b.acc{{color:#c07a2c}}
.lab i{{font:italic 400 {I(0.16):.0f}px/1 'EB Garamond';color:#1b1a18}}
</style></head><body><div id="w"><img src="file://{RAW}/cover_base.png"><svg viewBox="0 0 {W} {H}">{''.join(svg)}</svg>{lab}{''.join(nh)}</div></body></html>'''
    hp = RAW / 'cover_overlay.html'; hp.write_text(html)
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(args=['--allow-file-access-from-files'])
        pg = b.new_page(viewport={'width': W, 'height': H}, device_scale_factor=1)
        pg.goto('file://' + str(hp)); pg.wait_for_function('document.fonts.status === "loaded"'); pg.wait_for_timeout(500)
        ok = pg.evaluate("() => ['Tenor Sans', 'EB Garamond', 'Nothing You Could Do'].map(f => document.fonts.check('20px \"' + f + '\"'))")
        pg.screenshot(path=str(RAW / 'cover_final.png'), omit_background=True, full_page=False)
        b.close()
    im = Image.open(RAW / 'cover_final.png').convert('RGBA')
    im.save(OUT, 'WEBP', quality=80, method=6, alpha_quality=80)
    flat = Image.new('RGBA', im.size, (246, 245, 241, 255)); flat.alpha_composite(im); flat.convert('RGB').save(RAW / 'cover_flat.jpg', quality=88)
    print(OUT, im.size, f'{OUT.stat().st_size / 1e6:.2f} MB', 'fonts', ok)


if __name__ == '__main__':
    main()
