"""sched-b · A7.1 Window schedule. Run: python3 build.py  (reads walsh/index.html, writes ../../sched-b.js)
Steps: mk_sub (model DATA) > extract (glass per wall plane, overlays removed) > panelize (4 x 8 max, level heads,
raked only at the living room tip) > wtypes (operation, frame, snap) > families and the sheet data here."""
import json, math, collections, subprocess, sys, pathlib, re
HERE = pathlib.Path(__file__).resolve().parent
for step in ('mk_sub.py', 'extract.py', 'panelize.py', 'wtypes.py'):
    subprocess.run([sys.executable, step], cwd=HERE, check=True, stdout=subprocess.DEVNULL)
T = json.load(open(HERE / 'types_raw.json'))['types']
PN = json.load(open(HERE / 'panes.json')); WALLS = PN['walls']
SUB = json.load(open(HERE / 'model_sub.json')); P = SUB['plans']
panes = [p for t in T for p in t['items']]
CFA = 3779                                   # calcs.json conditioned

def ftin(v):
    f = int(math.floor(v + 1e-6)); i = round((v - f) * 12)
    if i == 12: f += 1; i = 0
    return f"{f}′ {i}″"
# ---------------------------------------------------------------- families
def fam(p):
    steel = p['frame'] == 'steel'
    if p['raked']: return ('steel', 'raked')
    if p['wall'] in ('W3', 'W17'): return ('steel', 'clere ' + p['op'])
    if p['op'] == 'casement':
        if not steel: return ('clad', 'egress')
        return ('steel', 'slot') if p['nw'] <= 2.5 else ('steel', 'casement')
    if p['op'] == 'awning': return (p['frame'], 'awning')
    cls = 'full' if p['nh'] >= 7.0 else 'tall' if p['nh'] >= 3.5 else 'low'
    return (p['frame'], cls)
ORDER = [('steel', 'full'), ('steel', 'casement'), ('steel', 'tall'), ('steel', 'low'), ('steel', 'raked'), ('steel', 'clere fixed'),
         ('steel', 'clere awning'), ('steel', 'slot'), ('clad', 'full'), ('clad', 'tall'), ('clad', 'low'), ('clad', 'egress'), ('clad', 'awning')]
F = collections.OrderedDict((k, []) for k in ORDER)
for p in panes: F[fam(p)].append(p)
LET = 'ABCDEFGHJKLMNPQRSTUVWXYZ'   # no I or O
OPN = {'fixed': 'Fixed', 'casement': 'Casement', 'awning': 'Awning'}
FRN = {'steel': 'Dark steel', 'clad': 'Aluminum clad'}
NOTE = {
    ('steel', 'full'): 'The window wall module. North wing court face, bridge and the tip.',
    ('steel', 'casement'): 'Opens for cross air, about every 4th bay. Confirm tall sash with the maker.',
    ('steel', 'tall'): 'Middle panes under the rake at the tip, and short runs.',
    ('steel', 'low'): 'Transoms up to the level head, cedar above.',
    ('steel', 'raked'): 'The only raked glass. Head follows the ribbon at the tip. Field measure.',
    ('steel', 'clere fixed'): 'Clerestory, 2 ft of glass between two beams.',
    ('steel', 'clere awning'): 'Every other clerestory pane opens. Motorized, rain sensor.',
    ('steel', 'slot'): 'Narrow slots in the quiet north wall, open for cross air.',
    ('clad', 'full'): 'South wing window walls: granny suite, lower level, primary.',
    ('clad', 'tall'): 'Punched windows, south wing and entry.',
    ('clad', 'low'): 'Transoms and high glass, primary suite and garage.',
    ('clad', 'egress'): 'One per sleeping area per wall, placeholder. Level 2: opening control, R312.2.',
    ('clad', 'awning'): 'Garage and gear bay, high sill.',
}
def rng(vals):
    lo, hi = min(vals), max(vals)
    return ftin(lo) if abs(hi - lo) < 0.01 else f'{ftin(lo)} to {ftin(hi)}'
types = []
for k, items in F.items():
    if not items: continue
    L = LET[len(types)]
    for p in items: p['type'] = L
    ws = [p['nw'] for p in items]; hs = [p['nh'] for p in items]
    mw = collections.Counter(ws).most_common(1)[0][0]; mh = collections.Counter(hs).most_common(1)[0][0]
    t = dict(t=L, fam=k[1], frame=k[0], n=len(items), op=OPN[items[0]['op']], frm=FRN[k[0]],
             w=rng(ws), h=rng(hs), dw=mw, dh=mh, where=' '.join(sorted({p['wall'] for p in items}, key=lambda s: int(s[1:]))),
             egress='Yes, R310' if k[1] == 'egress' else 'No', note=NOTE[k], sf=round(sum(p['w'] * p['h'] if not p['raked'] else p['w'] * (p['yl'] + p['yr'] - 2 * p['y0']) / 2 for p in items)))
    if k[1] == 'raked':
        lo = min(min(p['yl'], p['yr']) - p['y0'] for p in items); hi = max(max(p['yl'], p['yr']) - p['y0'] for p in items)
        t['h'] = f'{ftin(round(lo * 2) / 2)} to {ftin(round(hi * 2) / 2)}, raked'
        rise = max(abs(p['yl'] - p['yr']) for p in items)
        t['dh'] = round(hi * 2) / 2; t['rise'] = round(rise, 2)
    types.append(t)
# ---------------------------------------------------------------- walls
def wall_sf(tag):
    return sum(p['w'] * p['h'] if not p['raked'] else p['w'] * (p['yl'] + p['yr'] - 2 * p['y0']) / 2 for p in panes if p['wall'] == tag)
FACEV = {'N': (0, -1), 'S': (0, 1), 'E': (1, 0), 'W': (-1, 0)}
walls = []
for w in WALLS:
    tag = w['tag']; nx, nz = w['n']; d = w['d']
    fx, fz = FACEV[w['face']]
    s = 1 if nx * fx + nz * fz >= 0 else -1
    segs = []
    for pi, part in enumerate(w['parts']):
        pp = [p for p in panes if p['wall'] == tag and p['part'] == pi]
        if not pp: continue
        h0, h1 = min(p['h0'] for p in pp), max(p['h1'] for p in pp)
        pt = lambda h, o=0: (round(nx * d - nz * h + s * nx * o, 2), round(nz * d + nx * h + s * nz * o, 2))
        segs.append([*pt(h0, 1.0), *pt(h1, 1.0)])
    sf = wall_sf(tag)
    lets = sorted({p['type'] for p in panes if p['wall'] == tag})
    walls.append(dict(tag=tag, name=w['name'], face=w['face'], sf=round(sf), types=' '.join(lets), n=sum(1 for p in panes if p['wall'] == tag),
                      flag=sf > 140, segs=segs, out=[round(s * nx, 3), round(s * nz, 3)]))
walls.sort(key=lambda w: int(w['tag'][1:]))
tot = sum(w['sf'] for w in walls)
# ---------------------------------------------------------------- key plan
VB = (-82.0, -26.0, 128.0, 110.0)
def nums(s): return [float(v) for v in re.findall(r'-?\d+(?:\.\d+)?', s)]
tree = P['site']['trees'][0]
north = math.degrees(math.atan2(P['north'][0], -P['north'][1]))
key = dict(vb=VB, foot=P['foot']['rib'], terr=[t['d'] for t in P['terrace']], tree=[tree[0], tree[1]], north=round(north, 1))
data = dict(types=types, walls=walls, key=key, tot=dict(panes=len(panes), sf=round(tot), cfa=CFA, pct=round(100 * tot / CFA), over=sum(1 for w in walls if w['flag'])))
src = (HERE / 'sheet_template.js').read_text().replace('/*DATA*/null', json.dumps(data, ensure_ascii=False, separators=(',', ':')))
(HERE.parents[1] / 'sched-b.js').write_text(src)
print('types', len(types), 'panes', len(panes), 'glass sf', round(tot), 'pct cfa', data['tot']['pct'])
for t in types: print(t['t'], t['n'], t['fam'], t['frame'], t['w'], '|', t['h'], t['where'])
for w in walls: print(w['tag'], w['name'], w['sf'], w['types'], 'FLAG' if w['flag'] else '')
