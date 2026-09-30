"""A1.2 registration proof: layer box against the view box, the roof corner against the plan's own path, and a 3x crop."""
import asyncio
from playwright.async_api import async_playwright
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(args=['--use-gl=swiftshader'])
        for vw, vh in [(1914, 1192), (390, 844)]:
            pg = await b.new_page(viewport={'width': vw, 'height': vh}, device_scale_factor=3 if vw > 1000 else 2)
            await pg.goto('http://localhost:8943/walsh/set/v2.html#A1.2', wait_until='networkidle')
            await pg.wait_for_timeout(2500)
            r = await pg.evaluate('''() => {
              const s = document.querySelector('.sheet[data-id="A1.2"]'), v = s.querySelector('.dv'), o = s.querySelector('.ovs-a12');
              const a = v.getBoundingClientRect(), c = o.getBoundingClientRect(), u = a.width / 21.4;
              const ps = v.querySelector('svg.dsvg'), os = o.querySelector('svg.ovs-svg');
              const m1 = ps.getScreenCTM(), m2 = os.getScreenCTM();
              const P = (m, x, y) => { const q = new DOMPoint(x, y).matrixTransform(m); return [q.x, q.y]; };
              const pts = [[-76.8, 8.28], [-125, -18.6], [65.73, -37.06], [-14.59, 24.67]].map(([x, y]) => { const A = P(m1, x, y), B = P(m2, x, y); return +(Math.hypot(A[0]-B[0], A[1]-B[1]) / u).toFixed(4); });
              return { box_in: [(c.left - a.left) / u, (c.top - a.top) / u, (c.width - a.width) / u, (c.height - a.height) / u].map(v => +v.toFixed(4)), point_err_in: pts, inside: o.parentElement === v };
            }''')
            print(vw, r)
            if vw > 1000:
                await pg.screenshot(path='/home/claude/tb/ov/overlays-site_A1.2_proof.png', clip={'x': 420, 'y': 255, 'width': 240, 'height': 200})
            await pg.close()
        await b.close()
asyncio.run(main())
