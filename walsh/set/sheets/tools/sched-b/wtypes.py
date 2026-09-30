import json, collections, math
D = json.load(open('panes.json')); panes = D['panes']; walls = {w['tag']: w for w in D['walls']}
def plan_xz(p):
    w = walls[p['wall']]; nx, nz = w['n']; d = w['d']; h = (p['h0'] + p['h1']) / 2
    return nx * d - nz * h, nz * d + nx * h
FL = {'lower': 2.5, 'main': 7.5, 'garage': 10.0, 'primary': 14.0}
def zone(p):
    x, z = plan_xz(p); y0 = p['y0']
    if p['wall'] in ('W3', 'W17'): return 'clerestory'
    if p['wall'] in ('W5',): return 'garage'
    if p['wall'] in ('W6',): return 'entry'
    if p['wall'] == 'W4': return 'garage' if x < -38 else 'north wing'
    if z < 9: return 'north wing'
    if p['wall'] in ('W7', 'W8', 'W9', 'W10') and z < 47: return 'bridge'
    if y0 < 6 or (p['row'] > 0 and p['wall'] in ('W12', 'W13', 'W14') and p['y0'] < 13): return 'lower'
    if y0 >= 13.5 or (p['row'] > 0 and p['y0'] >= 13.5): return 'primary'
    return 'granny'
for p in panes: p['zone'] = zone(p)
# frames: dark steel in the north wing, the bridge and the clerestories; aluminum clad in the south wing, garage and entry
STEEL = {'north wing', 'bridge', 'clerestory'}
for p in panes: p['frame'] = 'steel' if p['zone'] in STEEL else 'clad'
# operation (FA placeholders, rooms not yet programmed)
for p in panes: p['op'] = 'fixed'; p['egress'] = False
byw = collections.defaultdict(list)
for p in panes: byw[(p['wall'], p['part'])].append(p)
def bottoms(lst): return sorted([p for p in lst if p['row'] == 0 and not p['raked']], key=lambda p: p['h0'])
used_egress = set()
for (wtag, part), lst in byw.items():
    b = bottoms(lst)
    if not b: continue
    z = b[0]['zone']
    if z == 'clerestory':
        for i, p in enumerate(sorted(lst, key=lambda p: p['h0'])):
            if i % 2 == 1: p['op'] = 'awning'
    elif z == 'garage' and wtag == 'W5':
        for p in b: p['op'] = 'awning'
    elif z in ('granny', 'lower', 'primary'):
        # one egress casement per sleeping zone per wall, near the middle; placeholders until the rooms are set
        sill_ok = [p for p in b if p['w'] >= 2.5 and p['h'] >= 4.5 and (p['y0'] - FL[{'granny': 'main', 'lower': 'lower', 'primary': 'primary'}[z]]) * 12 <= 44]
        if sill_ok and (z, wtag) not in used_egress:
            q = sill_ok[len(sill_ok) // 2]; q['op'] = 'casement'; q['egress'] = True; used_egress.add((z, wtag))
    elif z in ('north wing', 'bridge') and wtag in ('W1', 'W7', 'W10'):
        for i, p in enumerate(b):
            if i % 4 == 1: p['op'] = 'casement'
    elif wtag == 'W4' and z == 'north wing':
        for p in b: p['op'] = 'casement'
# cluster into types: sizes snap to 6 in nominal (never over 4 ft wide or 8 ft tall); every raked pane is one family
def snap(v, cap): return min(cap, max(1.0, round(v * 2) / 2))
for p in panes: p['nw'] = snap(p['w'], 4.0); p['nh'] = snap(p['h'], 8.0)
groups = collections.OrderedDict()
for p in sorted(panes, key=lambda p: (p['raked'], p['op'] != 'fixed', p['frame'], -p['nh'], -p['nw'])):
    k = ('R', p['frame']) if p['raked'] else (p['op'], p['frame'], p['nw'], p['nh'])
    groups.setdefault(k, []).append(p)
types = []
for k, items in groups.items():
    t = dict(raked=items[0]['raked'], op=items[0]['op'], frame=items[0]['frame'], w=items[0]['nw'], h=items[0]['nh'], items=items)
    if t['raked']:
        hs = [max(p['yl'], p['yr']) - p['y0'] for p in items] + [min(p['yl'], p['yr']) - p['y0'] for p in items]
        t['hmin'], t['hmax'] = min(hs), max(hs)
    types.append(t)
for t in sorted(types, key=lambda t: -len(t['items'])):
    print(len(t['items']), t['op'], t['frame'], 'R' if t['raked'] else '', t['w'], t['h'], sorted(set(p['wall'] for p in t['items'])), sorted(set(p['zone'] for p in t['items'])), sum(p['egress'] for p in t['items']))
print(len(types), 'types')
json.dump(dict(types=[{k: v for k, v in t.items() if k != 'items'} | dict(items=t['items']) for t in types]), open('types_raw.json', 'w'))
