#!/usr/bin/env python3
"""cover-b stills for the Walsh living set: A0.5 axonometrics and A9.1 perspectives, rendered from the pocket model.

Drives walsh/index.html (the pocket model) in headless chromium through its window.__fa hook, never edits it:
  axonometrics  true parallel projection (the model's perspective camera gets an orthographic projection matrix),
                sumi style (pale massing, black hairlines, warm timber), trees faint, from the four corners
  perspectives  the model's own saved eye level views (entry, dining, living ...) on its wide lens, annotated style
People and cars are hidden in every still. The composite's paper is lifted out, so each still is ink on a clear
ground (RGBA WebP) and the sheet's own weathered paper shows through; the edges dissolve into the paper.

Run:  python3 walsh/set/sheets/tools/cover-b/render_stills.py [PORT] [--probe] [--only name,name]
Needs a server on the repo root at PORT (default 8902).
"""
import asyncio, base64, io, json, math, sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageFilter

HERE = Path(__file__).resolve().parent
SET = HERE.parents[2]
OUT = SET / 'sheets' / 'assets' / 'cover-b'
RAW = Path('/home/claude/tb/crews/cover-b_raw')          # full canvas grabs, kept so the post pass can rerun alone
PPI = 200                                   # px per inch of sheet
CEN = [-19.15, 15, 31.2]                    # the model's orbit center (VIEWS.house.t)

# ---------------------------------------------------------------- the jobs
# axonometrics: 14.2 x 6.9 in each on the sheet. yaw 0 looks from +z (south), +pi/2 from +x (east); plan north is -z
AXO_W, AXO_H = 14.2, 6.9
AXO_EL = 0.56                                # about 32 degrees down, a touch flatter than isometric
AXO_HALF = 47.0                              # half the frame height in feet
AXO_T = [-17.0, 11.5, 30.0]
AXO = [
    ('axo-sw', -math.pi / 4),
    ('axo-se', math.pi / 4),
    ('axo-nw', -3 * math.pi / 4),
    ('axo-ne', 3 * math.pi / 4),
]
# perspectives: the model's saved eye level views. sizes in sheet inches
PERS = [
    ('pers-arrival', 'entry', 19.34, 15.2),
    ('pers-dining', 'dining', 8.78, 6.9),
    # the living room tip from the east grade, below the lifted corner (the saved terrace view, stepped back and down)
    ('pers-tip', 'terrace', 8.78, 6.9, dict(eye=[60, 8.0, 26], at=[33, 21, 8])),
]
PROBE_EXTRA = [
    ('probe-terrace', 'terrace', 8.78, 6.9),
    ('probe-tipC', 'terrace', 8.78, 6.9, dict(eye=[52, 7.8, 32], at=[33, 19, 8])),
    ('probe-tipD', 'terrace', 8.78, 6.9, dict(eye=[50, 7.8, 42], at=[33, 20, 9])),
    ('probe-tipE', 'terrace', 8.78, 6.9, dict(eye=[60, 8.0, 26], at=[33, 21, 8])),
]

SETUP_JS = r'''async () => {
  const F = window.__fa, THREE = F.THREE, scene = F.scene, app = document.getElementById('app');
  // the loader hands over to the reel when it is done; wait for that, or the reel takes the camera back mid capture
  for (let i = 0; i < 600 && app.dataset.mode !== 'reel'; i++) await new Promise(r => setTimeout(r, 100));
  F.enterModel();
  await new Promise(r => setTimeout(r, 900));
  if (app.dataset.mode !== 'model' || F.S.scheme !== 'rib') throw new Error('model not in ribbon model mode: ' + app.dataset.mode + ' ' + F.S.scheme);
  scene.updateMatrixWorld(true);
  const D = JSON.parse(document.getElementById('model-data').textContent);
  const hidden = [];
  scene.traverse(o => {
    if (!o.geometry || !o.geometry.attributes || !o.geometry.attributes.position) return;
    const n = o.geometry.attributes.position.count;
    // people: the figures drawn from DATA.people
    if (o.isLineSegments && n * 3 === D.people.length) { o.visible = false; hidden.push('people'); return; }
    // cars: parked on the drive, west of x -85 (the same rule drawKit uses)
    const b = new THREE.Box3().setFromObject(o);
    if (b.max.x < -85 && b.min.y > 11 && b.max.y < 18 && b.max.x - b.min.x < 20 && b.max.z - b.min.z < 12 && (o.isMesh || o.isLineSegments)) { o.visible = false; hidden.push('car'); }
  });
  // the compass rose, its ring, axes and letters: flat on the court at about 7.5 (a model graphic, not part of the site)
  scene.traverse(o => {
    if (!o.visible || !o.geometry || !o.geometry.attributes || !o.geometry.attributes.position) return;
    const b = new THREE.Box3().setFromObject(o);
    if (b.max.y - b.min.y < 0.05 && b.min.y > 7.45 && b.max.y < 7.72) { o.visible = false; hidden.push('compass'); }
  });
  // fog under our control: the axonometric camera stands far off, so the model's own fog would swallow it
  const fog = scene.fog;
  ['near', 'far'].forEach(k => { let v = fog[k]; Object.defineProperty(fog, k, { get() { const c = window.__cb && window.__cb.fog; return c ? c[k === 'near' ? 0 : 1] : v; }, set(x) { v = x; }, configurable: true }); });
  window.__cb = { hidden, trees: [], canopy: [], contours: [], fog: null };
  scene.traverse(o => {
    const m = o.material; if (!m || !m.color) return;
    const h = m.color.getHexString();
    if (h === '2c5a37') window.__cb.trees.push(o);
    if (h === '9dbb8f') window.__cb.canopy.push(o);
    if (h === 'c3cdb8' || h === '9fae93') window.__cb.contours.push(o);
  });
  return hidden;
}'''

LOOK_JS = r'''async (o) => {
  const F = window.__fa, THREE = F.THREE, cam = F.cam, camera = F.camera;
  // pale massing for the axonometrics (the sumi palette, set on the materials: the page's style switch is internal)
  const PALE = { 'efece6': 0xf1efea, 'b9b3a8': 0xe6e3dc, '5f666d': 0xf7f7f5, 'b98a58': 0xd8a877, 'd9e2cd': 0xf4f3f0 };
  if (!window.__cb.mats) { const ms = new Set(); F.scene.traverse(x => { if (x.material && x.material.color) ms.add(x.material); }); window.__cb.mats = [...ms].map(m => [m, m.color.getHex()]); }
  window.__cb.mats.forEach(([m, h0]) => { const k = h0.toString(16).padStart(6, '0'); m.color.setHex(o.style === 'pale' && PALE[k] != null ? PALE[k] : h0); });
  F.S.trees = true; F.S.notes = false; F.S.inside = false; F.S.roof = false;
  // trees: faint graphite in the axonometrics, the model's own green in the perspectives
  const T = window.__cb;
  const tset = new Set(T.trees.map(t => t.material));
  tset.forEach(m => { if (m.userData.o0 == null) m.userData.o0 = m.opacity;
    m.color.setHex(o.faint ? 0x8a877f : 0x4a4843); m.opacity = o.faint ? 0.42 : 0.78; m.transparent = true; m.needsUpdate = true; });
  new Set(T.canopy.map(t => t.material)).forEach(m => { m.opacity = 0.035; m.color.setHex(0xd6d3cc); m.needsUpdate = true; });
  T.canopy.forEach(c => { c.visible = !!o.faint; });   // eye level: the trees are their hand drawn lines only, no grey cones
  new Set(T.contours.map(t => t.material)).forEach(m => { if (!m.userData.c0) m.userData.c0 = m.color.getHex(); m.color.setHex(m.userData.c0 === 0x9fae93 ? 0xa9a6a0 : 0xcac7c0); m.needsUpdate = true; });
  T.fog = o.axo ? [o.dist - 60, o.dist + 420] : null;
  if (o.axo) {
    const half = o.half, near = 1, far = 4000;
    camera.updateProjectionMatrix = function () {
      const a = this.aspect;
      this.projectionMatrix.makeOrthographic(-half * a, half * a, half, -half, near, far);
      this.projectionMatrixInverse.copy(this.projectionMatrix).invert();
    };
    F.S.room = false; F.apply();
    F.look(o.yaw, o.el, o.dist, o.t); cam.fp = 1;
  } else {
    delete camera.updateProjectionMatrix;
    F.goTo(o.view);
    await new Promise(r => setTimeout(r, 900));
    if (o.eye) {   // a nudge off the saved view: same idea, framed for the sheet
      const e = o.eye, a = o.at, dx = e[0] - a[0], dy = e[1] - a[1], dz = e[2] - a[2], d = Math.hypot(dx, dy, dz);
      F.S.room = !!o.room; F.apply();
      F.look(Math.atan2(dx, dz), Math.asin(dy / d), d, a); cam.fp = 1;
    }
    if (o.fov) { const upd = THREE.PerspectiveCamera.prototype.updateProjectionMatrix; camera.updateProjectionMatrix = function () { this.fov = o.fov; upd.call(this); }; }
  }
  F.poke();
  for (let i = 0; i < 4; i++) await new Promise(r => requestAnimationFrame(() => r()));
  await new Promise(r => setTimeout(r, 250));
  F.poke();
  for (let i = 0; i < 3; i++) await new Promise(r => requestAnimationFrame(() => r()));
  if (document.getElementById('app').dataset.mode !== 'model') throw new Error('left model mode');
  return document.getElementById('cv').toDataURL('image/png');
}'''


def lift_paper(png_bytes, fade=None, feather=0.0, cut=0.06):
    """ink on a clear ground: divide out the paper color, alpha from how far each pixel sits below white.
    fade: (cx, cy, rx, ry, power) an elliptical dissolve toward the edges, in fractions of the frame"""
    im = Image.open(io.BytesIO(png_bytes)).convert('RGB')
    a = np.asarray(im).astype(np.float32) / 255.0
    h, w, _ = a.shape
    # the paper is the brightest common tone: sample the corners' upper percentile
    pap = np.percentile(a.reshape(-1, 3), 99.2, axis=0)
    c = np.clip(a / np.maximum(pap, 1e-3), 0, 1)
    # lift near white to clear: grain on the canvas paper goes, faint washes stay
    alpha = 1.0 - c.min(axis=2)
    alpha = np.clip((alpha - cut) / (1 - cut), 0, 1)
    col = np.where(alpha[..., None] > 1e-3, (c - (1 - alpha[..., None])) / np.maximum(alpha[..., None], 1e-3), 0)
    col = np.clip(col, 0, 1)
    # the paper color back into the ink's hue so light washes read warm, not grey
    if fade:
        cx, cy, rx, ry, pw = fade
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        d = np.sqrt(((xx / w - cx) / rx) ** 2 + ((yy / h - cy) / ry) ** 2)
        k = np.clip(1.0 - np.clip(d - 1.0, 0, None) / 0.45, 0, 1) ** pw
        alpha = alpha * k
    if feather:
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        e = np.minimum(np.minimum(xx, w - 1 - xx), np.minimum(yy, h - 1 - yy)) / (feather * min(w, h))
        e = np.clip(e, 0, 1); alpha = alpha * (e * e * (3 - 2 * e))
    out = np.dstack([col * 255, alpha * 255]).astype(np.uint8)
    return Image.fromarray(out, 'RGBA')


async def main():
    from playwright.async_api import async_playwright
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    port = int(args[0]) if args else 8902
    probe = '--probe' in sys.argv
    only = None
    for a in sys.argv[1:]:
        if a.startswith('--only='):
            only = set(a.split('=', 1)[1].split(','))
    scale = 0.25 if probe else 1.0
    OUT.mkdir(parents=True, exist_ok=True)
    jobs = []
    for name, yaw in AXO:
        jobs.append((name, dict(axo=True, yaw=yaw, el=AXO_EL, half=AXO_HALF, t=AXO_T, dist=900, style='pale', faint=True), AXO_W, AXO_H,
                     (0.5, 0.5, 0.4, 0.42, 1.4)))
    for name, view, w, h, *ex in PERS + (PROBE_EXTRA if probe else []):
        jobs.append((name, dict(axo=False, view=view, style='annot', faint=False, **(ex[0] if ex else {})), w, h, 'feather'))
    if only:
        jobs = [j for j in jobs if j[0] in only]
    meta = {}
    RAW.mkdir(parents=True, exist_ok=True)
    post_only = '--post' in sys.argv

    def post(name, raw, w, h, fade, o):
        im = lift_paper(raw, None if fade == 'feather' else fade, 0.035 if fade == 'feather' else 0.0)
        dst = OUT / (name + ('-probe.png' if probe else '.webp'))
        if probe:
            im.save(dst)
        else:
            im.save(dst, 'WEBP', quality=78, alpha_quality=70, method=4)   # alpha quality is most of the weight
        meta[name] = dict(px=im.size[0], py=im.size[1], w=w, h=h, view=o.get('view'), yaw=o.get('yaw'), el=o.get('el'))
        print(f'{name}: {im.size[0]} x {im.size[1]} px, {dst.stat().st_size // 1024} KB', flush=True)

    if post_only:
        for name, o, w, h, fade in jobs:
            f = RAW / f'{name}.png'
            if f.exists():
                post(name, f.read_bytes(), w, h, fade, o)
    else:
      async with async_playwright() as p:
        b = await p.chromium.launch(args=['--use-gl=swiftshader', '--enable-webgl', '--ignore-gpu-blocklist'])
        for name, o, w, h, fade in jobs:
            W, H = round(w * PPI * scale / 2), round(h * PPI * scale / 2)     # css px; the model renders at DPR 2
            ctx = await b.new_context(viewport={'width': W, 'height': H}, device_scale_factor=2, reduced_motion='reduce')
            pg = await ctx.new_page()
            errs = []
            pg.on('pageerror', lambda e: errs.append(str(e)))
            await pg.goto(f'http://127.0.0.1:{port}/walsh/index.html')
            await pg.wait_for_function('window.__fa && window.__fa.scene && window.__fa.cam', timeout=240000)
            await pg.wait_for_timeout(1500)
            hid = await pg.evaluate(SETUP_JS)
            url = await pg.evaluate(LOOK_JS, o)
            raw = base64.b64decode(url.split(',', 1)[1])
            if not probe:
                (RAW / f'{name}.png').write_bytes(raw)
            post(name, raw, w, h, fade, o)
            print('   hidden', sorted(set(hid)), len(hid), errs or '', flush=True)
            await ctx.close()
        await b.close()
    if not probe and not only:
        (OUT / 'stills.json').write_text(json.dumps(meta, indent=1))

asyncio.run(main())
