#!/usr/bin/env python3
"""cover-a composite (9/30/26): lays each rendering into hairline drafting on transparent paper.

Inside a brushed vignette the render reads in full color; toward its edge the color goes to pencil grey and dries out
in marker streaks; past it only the model's own hairlines remain (hidden lines removed), with the pencil firs.
The result is RGBA WebP, so the sheet's own weathered paper shows through.

  python3 walsh/set/sheets/tools/cover-a/composite.py [preview] [job ...]
"""
import json, sys
from pathlib import Path
import numpy as np
from PIL import Image
from scipy import ndimage as ndi

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
RAW = Path('/tmp/claude-0/-home-claude-andre-mandel-site/b0abd60a-a112-5987-bb0d-bf806619c786/scratchpad/cover-a-raw')
OUT = ROOT / 'walsh' / 'set' / 'sheets' / 'assets' / 'cover-a'
INK = np.array([27, 26, 24], np.float32) / 255
PAPER = np.array([246, 245, 241], np.float32) / 255

# the vignette per view: center and radii as fractions of the frame, stroke angle (deg), how far the color reaches
MASK = {
    'arrival': dict(c=(0.47, 0.5), r=(0.5, 0.56), ang=-8, reach=0.94, ground=0.7),
    'court': dict(c=(0.5, 0.5), r=(0.53, 0.62), ang=-6, reach=0.94),
    'tip': dict(c=(0.5, 0.5), r=(0.6, 0.64), ang=-10, reach=0.94),
    'aerial': dict(c=(0.5, 0.5), r=(0.54, 0.62), ang=-14, reach=0.94),
    'cover': dict(c=(0.57, 0.52), r=(0.43, 0.43), ang=-9, reach=0.94),
    'plan': dict(c=(0.5, 0.5), r=(0.5, 0.5), ang=0, reach=0.94),
}


def smooth(a, e0, e1):
    t = np.clip((a - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


def noise(h, w, scale, seed, aniso=None, ang=0.0):
    """smooth value noise in 0..1; aniso=(sy, sx) stretches it into strokes, turned by ang degrees"""
    r = np.random.default_rng(seed)
    sh, sw = max(4, int(h / scale) + 4), max(4, int(w / scale) + 4)
    n = r.random((sh, sw)).astype(np.float32)
    if aniso:
        big = max(sh, sw)
        n = r.random((big * 2, big * 2)).astype(np.float32)
        n = ndi.gaussian_filter(n, aniso)
        n = ndi.rotate(n, ang, reshape=False, order=1, mode='reflect')
        o = big // 2
        n = n[o:o + sh, o:o + sw]
    else:
        n = ndi.gaussian_filter(n, 1.0)
    n = (n - n.min()) / (np.ptp(n) + 1e-6)
    return np.asarray(Image.fromarray((n * 255).astype(np.uint8)).resize((w, h), Image.BICUBIC), np.float32) / 255


def compose(name, preview=False):
    tag = '_prev' if preview else ''
    meta = json.loads((RAW / f'{name}{tag}.json').read_text())
    ss = meta['ss']
    col = Image.open(RAW / f'{name}_color{tag}.png').convert('RGB')
    lin = Image.open(RAW / f'{name}_line{tag}.png').convert('RGB')
    W, H = round(col.width / ss), round(col.height / ss)
    # lines: darkness, thickened a hair at render scale, then down
    L = np.asarray(lin, np.float32) / 255
    D = 1 - (L @ np.array([0.299, 0.587, 0.114], np.float32))
    D = np.clip(D * 1.25, 0, 1)
    k = 3 if ss >= 2 else 2
    D = ndi.grey_dilation(D, size=(k, k))
    D = np.asarray(Image.fromarray((D * 255).astype(np.uint8)).resize((W, H), Image.BOX), np.float32) / 255
    C = np.asarray(col.resize((W, H), Image.LANCZOS), np.float32) / 255
    # the mask is worked out at a reduced size (it is soft), then brought up
    q = max(1, round(max(W, H) / 1600))
    w, h = -(-W // q), -(-H // q)
    P = MASK[name]
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    ex = (xx / w - P['c'][0]) / P['r'][0]
    ey = (yy / h - P['c'][1]) / P['r'][1]
    e = np.sqrt(ex * ex + ey * ey)
    sc = max(w, h)
    mott = noise(h, w, sc / 9, 11)
    fine = noise(h, w, sc / 60, 12)
    strk = noise(h, w, sc / 70, 13, aniso=(0.8, 16), ang=P['ang'])
    strk2 = noise(h, w, sc / 110, 14, aniso=(0.6, 22), ang=P['ang'] + 4)
    # the building (and the signature tree) hold; the sky only as a halo around them; the ground below the horizon
    mk = Image.open(RAW / f'{name}_mask{tag}.png').convert('L').resize((w, h), Image.BOX)
    Hm = (np.asarray(mk, np.float32) / 255 > 0.08).astype(np.float32)
    Hs = np.clip(ndi.gaussian_filter(ndi.grey_dilation(Hm, size=(int(sc * 0.012) | 1,) * 2), sc * 0.012) * 1.6, 0, 1)
    Hs2 = np.clip(ndi.gaussian_filter(Hm, sc * 0.05) * 3.0, 0, 1)
    fr = meta['info']['frame']
    if meta['job'].get('level'):
        VH = fr['t'] / (fr['t'] - fr['b'])
        G = smooth(yy / h, VH - 0.01, VH + 0.1)
    else:
        G = np.ones_like(yy)
    hold = np.maximum.reduce([Hs, G * P.get('ground', 0.9), Hs2 * P.get('halo', 0.75)])
    f = e + 0.2 * (mott - 0.5) + 0.34 * (strk - 0.5) + 0.12 * (strk2 - 0.5) + 0.05 * (fine - 0.5) + (1 - hold) * P.get('hk', 0.55)
    reach = P['reach']
    M = 1 - smooth(f, reach - 0.2, reach)
    dry = smooth(strk2 * 0.7 + fine * 0.3, 0.25, 0.75)          # dry brush: the edge breaks up along the strokes
    M = np.clip(M * (0.72 + 0.28 * dry) + (M > 0.97) * 0.28 * (1 - dry), 0, 1)
    M = np.where(f < reach - 0.25, 1.0, M).astype(np.float32)
    # everything, linework included, trails off before the frame so no view ends on a hard rectangle
    bd = np.minimum.reduce([xx, w - 1 - xx, yy * (w / h) * 0.5 + 0 * yy, (h - 1 - yy) * (w / h) * 0.5]) / w
    edge = smooth(bd + 0.03 * (fine - 0.5) + 0.02 * (strk - 0.5), 0.0, P.get('edge', 0.05))
    up = lambda a: np.asarray(Image.fromarray((np.clip(a, 0, 1) * 65535).astype(np.uint16)).resize((W, H), Image.BICUBIC), np.float32)[:H, :W] / 65535
    M, edge = up(M), up(edge)
    # the fringe goes pencil grey before it lets go
    lum = C @ np.array([0.299, 0.587, 0.114], np.float32)
    grey = PAPER[None, None, :] * (1 - 0.62 * (1 - lum[..., None]))
    t = smooth(M, 0.25, 0.9)[..., None]
    Ct = grey * (1 - t) + C * t
    ac = M
    al = D * (0.2 + 0.62 * (1 - smooth(M, 0.3, 1.0)))
    ac = ac * edge; al = al * edge
    A = al + ac * (1 - al)
    RGB = (INK[None, None, :] * al[..., None] + Ct * (ac * (1 - al))[..., None]) / np.maximum(A, 1e-4)[..., None]
    out = np.dstack([np.clip(RGB, 0, 1), np.clip(A, 0, 1)])
    im = Image.fromarray((out * 255 + 0.5).astype(np.uint8), 'RGBA')
    OUT.mkdir(parents=True, exist_ok=True)
    if preview:
        dest = RAW / f'{name}{tag}.webp'; im.save(dest, 'WEBP', quality=84, method=6, alpha_quality=80)
    elif name == 'cover':      # the cover gets its drafting marks burned in by cover_overlay.py
        dest = RAW / 'cover_base.png'; im.save(dest, optimize=False, compress_level=3)
    else:
        dest = OUT / f'{name}.webp'; im.save(dest, 'WEBP', quality=84, method=6, alpha_quality=80)
    # a flat check print on paper
    flat = Image.new('RGBA', im.size, tuple(int(v * 255) for v in PAPER) + (255,)); flat.alpha_composite(im)
    flat.convert('RGB').save(RAW / f'{name}{tag}_flat.jpg', quality=88)
    print(dest, im.size, f'{dest.stat().st_size / 1e6:.2f} MB', flush=True)
    return dest


if __name__ == '__main__':
    a = sys.argv[1:]
    prev = 'preview' in a
    names = [x for x in a if x in MASK] or [n for n in MASK if n != 'plan']
    for n in names:
        compose(n, prev)
