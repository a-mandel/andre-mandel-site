"""sched-b: derive the Ribbon scheme glazing from the pocket model, panelize it to André's rule
(panes 4 ft wide by 8 ft tall max, square everywhere, raked only at the living room tip), group into types."""
from vis import *
import math, json
# merge coplanar groups: same angle within 4 deg, offset within 1.1 ft
keys=[k for k in sorted(G) if planeinfo(k)[0].area>3]
merged=[]
for k in keys:
    for m in merged:
        if abs(m[0][0]-k[0])<=4 and abs(m[0][1]-k[1])<=1.1: m.append(k); break
    else: merged.append([k])
def part_top(P, h0, h1, y0):
    """lowest top of polygon P between h0 and h1 (sampled)"""
    tops=[]
    for i in range(7):
        h=h0+(h1-h0)*(0.03+0.94*i/6)
        ln=LineString([(h,y0-1),(h,60)]).intersection(P)
        if ln.is_empty: continue
        ys=[c[1] for g in getattr(ln,'geoms',[ln]) for c in g.coords]
        tops.append((h,max(ys),min(ys)))
    return tops
OUT=[]
for grp in merged:
    base=grp[0]; n=G[base][0][1]
    parts=[]; area=0
    for k in grp:
        u,vis,ops,mu,nn=planeinfo(k)
        s=1 if np.dot(nn,n)>0 else -1
        for g in getattr(vis,'geoms',[vis]):
            if g.is_empty or g.area<0.5: continue
            if s<0: g=Polygon([(-x,y) for x,y in g.exterior.coords])
            parts.append(g)
    U_=unary_union([p.buffer(0.12) for p in parts]).buffer(-0.12)
    # overlays (solid cedar or white bays, cedar above square heads) near any plane of the group
    ops=[]
    for k in grp:
        _,_,oo,_,nn=planeinfo(k)
        s_=1 if np.dot(nn,n)>0 else -1
        for P,t in oo: ops.append(P if s_>0 else Polygon([(-x,y) for x,y in P.exterior.coords]))
    if ops: U_=U_.difference(unary_union([o.buffer(0.02) for o in ops]))
    U_=U_.buffer(0)
    geoms=[g for g in getattr(U_,'geoms',[U_]) if g.area>0.8]
    rec=dict(key=base, n=[round(float(n[0]),3),round(float(n[2]),3)], d=base[1], parts=[])
    for g in geoms:
        b=g.bounds
        rec['parts'].append(dict(h0=round(b[0],2),h1=round(b[2],2),y0=round(b[1],2),y1=round(b[3],2),area=round(g.area,1),
            prof=[[round(h,2),round(t,2),round(bo,2)] for h,t,bo in part_top(g,b[0],b[2],b[1])],
            poly=[[round(x,2),round(y,2)] for x,y in g.simplify(0.05).exterior.coords],
            holes=[[[round(x,2),round(y,2)] for x,y in r.coords] for r in g.simplify(0.05).interiors if Polygon(r).area>0.3]))
    rec['area']=round(sum(p['area'] for p in rec['parts']),1)
    OUT.append(rec)
json.dump(OUT,open('walls_raw.json','w'),indent=0)
for r in OUT:
    print(r['key'], r['n'], 'area',r['area'])
    for p in r['parts']: print('   h %.1f..%.1f y %.1f..%.1f a %.1f'%(p['h0'],p['h1'],p['y0'],p['y1'],p['area']), 'tops',[t[1] for t in p['prof']])
