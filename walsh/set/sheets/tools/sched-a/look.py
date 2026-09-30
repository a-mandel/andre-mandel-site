import asyncio, sys
from pathlib import Path
from playwright.async_api import async_playwright
svg = Path(sys.argv[1]).read_text()
out = sys.argv[2]
# grid overlay every 5 ft in model coords
vb = [float(v) for v in svg.split('viewBox="')[1].split('"')[0].split()]
g = ''
x = (int(vb[0]//5))*5
while x <= vb[0]+vb[2]:
    g += f'<line x1="{x}" y1="{vb[1]}" x2="{x}" y2="{vb[1]+vb[3]}" stroke="{"red" if x%10==0 else "pink"}" stroke-width="{0.12 if x%10==0 else 0.06}"/>'
    if x%10==0: g += f'<text x="{x+0.3}" y="{vb[1]+2}" font-size="1.6" fill="red">{x}</text>'
    x += 5
z = (int(vb[1]//5))*5
while z <= vb[1]+vb[3]:
    g += f'<line x1="{vb[0]}" y1="{z}" x2="{vb[0]+vb[2]}" y2="{z}" stroke="{"blue" if z%10==0 else "lightblue"}" stroke-width="{0.12 if z%10==0 else 0.06}"/>'
    if z%10==0: g += f'<text x="{vb[0]+0.5}" y="{z-0.3}" font-size="1.6" fill="blue">{z}</text>'
    z += 5
svg = svg.replace('</svg>', g + '</svg>')
svg = svg.replace('class="dsvg"', 'style="width:100%;height:100%"')
html = f'<html><body style="margin:0;background:#fff"><div style="width:{sys.argv[3]}px;height:{int(int(sys.argv[3])*vb[3]/vb[2])}px">{svg}</div></body></html>'
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page(viewport={'width': int(sys.argv[3]), 'height': int(int(sys.argv[3])*vb[3]/vb[2])})
        await pg.set_content(html)
        await pg.screenshot(path=out, full_page=True)
        await b.close()
asyncio.run(main())
