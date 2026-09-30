import json, math, collections
from shapely.geometry import Polygon, box, LineString
W=json.load(open('walls_raw.json'))
# wall planes, in the order they read around the house (plan north is the model's -z, as on A4.x)
NAMES={
 (90,8.0):  ('W1','North wing, court face','S','Kitchen, dining and living under the ribbon'),
 (0,36.0):  ('W2','Living room tip, east end','E','The tip: the one raked wall'),
 (68,-0.5): ('W3','Clerestory at the fold','S','2 ft of glass between the two beams'),
 (90,-15.0):('W4','North wall','N','Quiet side, slots only'),
 (0,-76.0): ('W5','Garage, west end','W','Garage and gear bay'),
 (0,-38.5): ('W6','Entry, east face','E','Entry'),
 (0,0.0):   ('W7','Bridge and primary, west','W','Bridge onto the tree court; primary high glass'),
 (90,35.0): ('W8','Bridge, south jog','N','Bridge'),
 (0,-5.0):  ('W9','Bridge south, west face','W','Bridge'),
 (0,16.0):  ('W10','Bridge, terrace face','E','Bridge onto the upper terrace'),
 (72,44.5): ('W11','South wing, court face','N','Granny suite and primary suite'),
 (0,26.0):  ('W12','South wing, east end','E','Lower level and primary suite'),
 (72,65.5): ('W13','South wing, south face','S','Granny, lower level, primary'),
 (72,64.0): ('W14','South wing, south jog','S','Lower level and primary'),
 (0,-20.5): ('W15','Granny suite, west','W','Granny suite'),
 (0,-18.5): ('W16','Granny suite, west jog','W','Granny suite'),
 (94,55.5): ('W17','South wing clerestory','S','2 ft of glass under the south ribbon'),
}
LIV_H = -15.4          # court face: the living room runs from about x 15.4 to the tip (h = -x)
def raked_zone(key, h0, h1):
    if key == (0, 36.0): return True
    if key == (90, 8.0): return h1 <= LIV_H + 0.05
    return False
def tops(P, h, y0=-5):
    ln = LineString([(h, y0), (h, 60)]).intersection(P)
    if ln.is_empty: return None
    gs = [g for g in getattr(ln, 'geoms', [ln]) if g.length > 0.3]
    if not gs: return None
    g = max(gs, key=lambda g: g.length)      # the main run of glass at this station
    ys = [c[1] for c in g.coords]
    return min(ys), max(ys)
panes = []
walls = []
for w in W:
    key = tuple(w['key']); tag, name, face, room = NAMES[key]
    wa = 0; wparts = []
    for pi, p in enumerate(w['parts']):
        P = Polygon(p['poly'], p.get('holes') or []).buffer(0)
        Wd = p['h1'] - p['h0']
        hs = [p['h0'] + Wd * (0.01 + 0.98 * i / 120) for i in range(121)]
        tb = [(h, tops(P, h)) for h in hs]
        # openings: runs of samples with at least 1 ft of glass; each gets one level head (the lowest top in the run)
        runs, cur = [], []
        for h, t in tb:
            if t and t[1] - t[0] > 1.0: cur.append((h, t))
            elif cur: runs.append(cur); cur = []
        if cur: runs.append(cur)
        for run in runs:
          rh0 = max(p['h0'], run[0][0] - Wd / 240); rh1 = min(p['h1'], run[-1][0] + Wd / 240)
          if run[0][0] - p['h0'] < Wd / 60: rh0 = p['h0']
          if p['h1'] - run[-1][0] < Wd / 60: rh1 = p['h1']
          if rh1 - rh0 < 0.8: continue
          ts = [t for _, t in run]
          psill = min(t[0] for t in ts); phead = min(t[1] for t in ts)
          n = max(1, math.ceil((rh1 - rh0) / 4.0 - 0.02)); cw = (rh1 - rh0) / n
          for c in range(n):
            a, b = rh0 + c * cw, rh0 + (c + 1) * cw
            rk = raked_zone(key, a, b)
            sill = psill
            if rk:
                tl, tr = tops(P, a + 0.02)[1], tops(P, b - 0.02)[1]
                head = min(tl, tr)
            else:
                head = phead
                rect = box(a, sill, b, head)
                if P.intersection(rect).area < 0.6 * rect.area: continue
            H = head - sill
            if H < 0.8: continue
            if rk:
                # raked columns: the standard 8 ft pane at the bottom; above it m panes, the top one takes the rake, none over 8 ft
                y1 = sill + 8.0
                a_, b_ = min(tl, tr) - y1, max(tl, tr) - y1
                if a_ < 1.0:
                    rows = [(sill, head)]
                else:
                    m = max(1, math.ceil(b_ / 8.0 - 1e-6)); r = a_ / m
                    rows = [(sill, y1)] + [(y1 + k * r, y1 + (k + 1) * r) for k in range(m)]
            elif H <= 8.25: rows = [(sill, sill + min(H, 8.0))]
            else:
                rows = [(sill, sill + 8.0)]
                rem = head - (sill + 8.0)
                if rem >= 1.0:          # a sliver under 1 ft is dropped: the head comes down and cedar fills above
                    m = max(1, math.ceil(rem / 8.0 - 0.02)); rh = rem / m
                    for k in range(m): rows.append((sill + 8 + k * rh, sill + 8 + (k + 1) * rh))
            for ri, (y0, y1) in enumerate(rows):
                pane = dict(wall=tag, key=list(key), part=pi, col=c, row=ri, h0=round(a, 2), h1=round(b, 2), y0=round(y0, 2), y1=round(y1, 2),
                            w=round(cw, 3), h=round(y1 - y0, 3), raked=False)
                if rk and ri == len(rows) - 1:
                    pane['raked'] = True
                    pane['yl'] = round(tl, 2); pane['yr'] = round(tr, 2)
                    pane['hmax'] = round(max(tl, tr) - y0, 2)
                panes.append(pane)
                wa += pane['w'] * (pane.get('yl', y1) + pane.get('yr', y1) - 2 * y0) / 2
        wparts.append(p)
    walls.append(dict(tag=tag, key=list(key), name=name, face=face, room=room, area_model=w['area'], area=round(wa, 1), n=w['n'], d=w['d'], parts=w['parts']))
json.dump(dict(walls=walls, panes=panes), open('panes.json', 'w'))
C = collections.Counter()
for p in panes:
    k = ('R' if p['raked'] else '', round(p['w'] * 12), round(p['h'] * 12) if not p['raked'] else 0)
    C[k] += 1
for k, v in sorted(C.items(), key=lambda kv: -kv[1]): print(k, v)
print(len(panes), 'panes')
for w in walls: print(w['tag'], w['name'], w['face'], 'model', w['area_model'], 'panelized', w['area'])
