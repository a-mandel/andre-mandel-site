#!/usr/bin/env python3
"""cover-a: projects model points through each rendering's camera and writes the numbers the A0.9 sheet overlays use
into the data block of walsh/set/sheets/cover-a.js (between the @data markers). Same camera math as render_kit.js.

  python3 walsh/set/sheets/tools/cover-a/sheet_data.py
"""
import json, math, re
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
RAW = Path('/tmp/claude-0/-home-claude-andre-mandel-site/b0abd60a-a112-5987-bb0d-bf806619c786/scratchpad/cover-a-raw')
SHEET = ROOT / 'walsh' / 'set' / 'sheets' / 'cover-a.js'
DATUM = 5990.0

for line in (ROOT / 'walsh' / 'index.html').read_text().splitlines():
    if 'id="model-data"' in line:
        D = json.loads(re.sub(r'^<script[^>]*>', '', line).rsplit('</script>', 1)[0]); break
A = D['A']; X = D['xt']['anchors']; T0 = D['site']['trees'][0]
PTS = {
    'tip': A['tip'], 'tipGrade': A['tipGrade'], 'tip30': A['tip30'], 'beam': A['beam'], 'garageTip': A['garageTip'],
    'treeMid': [T0[0], T0[1] + 30.0, T0[2]], 'treeBase': [T0[0], T0[1], T0[2]], 'gdoor': A['gdoor'], 'bridge': [13.0, 16.0, 31.0],
    'bridgeW': [9.0, 12.0, 31.0], 'eglass': A['eglass'], 'pit': X['pit'], 'bench': X['bench'], 'terrace': X['terrace'],
    'chimS': [24.3, 27.9, 63.9], 'chimSmid': [24.3, 21.0, 63.9], 'chimN': [20.75, 27.6, -11.4], 'main': A['wingSE'], 'mainW': A['wingSW'],
    'primary': [18.7, 14.0, 60.0], 'primaryRidge': A['primaryRidge'], 'granny': A['granny'], 'lower': X['lower'], 'pdeck': X['pdeck'],
    'drive': [-76.0, 11.5, 34.0], 'porch': A['porch'], 'clere': A['clere'], 'post': A['post'], 'stip': A['stip'],
}


def basis(eye, look, level):
    E = np.array(eye, float); Tg = np.array(look, float)
    if level: Tg[1] = E[1]
    z = E - Tg; z /= np.linalg.norm(z)
    x = np.cross([0, 1, 0], z); x /= np.linalg.norm(x)
    y = np.cross(z, x)
    return E, x, y, z


def project(meta, p):
    J, fr = meta['job'], meta['info']['frame']
    E, x, y, z = basis(J['eye'], J['look'], J.get('level'))
    d = np.array(p, float) - E
    xc, yc, zc = d @ x, d @ y, d @ z
    if zc >= 0: return None
    u, v = xc / -zc, yc / -zc
    return [round((u - fr['l']) / (fr['r'] - fr['l']), 4), round((fr['t'] - v) / (fr['t'] - fr['b']), 4)]


def build():
    out = {}
    for name in ('arrival', 'court', 'tip', 'aerial', 'cover'):
        mp = RAW / f'{name}.json'
        if not mp.exists(): continue
        meta = json.loads(mp.read_text())
        # check against the page's own projection
        js = meta['proj']['tip'][:2]; py = project(meta, A['tip'])
        assert abs(js[0] - py[0]) < 2e-3 and abs(js[1] - py[1]) < 2e-3, (name, js, py)
        fr = meta['info']['frame']
        pr = {k: project(meta, v) for k, v in PTS.items()}
        pr = {k: v for k, v in pr.items() if v and -0.2 < v[0] < 1.2 and -0.2 < v[1] < 1.2}
        hz = round(fr['t'] / (fr['t'] - fr['b']), 4) if meta['job'].get('level') else None
        eye_ft = meta['job']['eye'][1] - 0.0
        out[name] = dict(p=pr, hz=hz, eye=round(DATUM + eye_ft, 1))
    return out


if __name__ == '__main__':
    data = build()
    js = SHEET.read_text()
    blk = '/* @data (sheet_data.py) */\nconst CA_P = ' + json.dumps({k: v for k, v in data.items()}, separators=(',', ':')) + ';\n/* @end */'
    js2 = re.sub(r'/\* @data \(sheet_data\.py\) \*/.*?/\* @end \*/', lambda m: blk, js, flags=re.S)
    if js2 == js and '@data' not in js: raise SystemExit('no @data block in cover-a.js')
    SHEET.write_text(js2)
    print(json.dumps(data, indent=1)[:3000])
