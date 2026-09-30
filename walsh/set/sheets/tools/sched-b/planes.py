import json, numpy as np, collections, math
from shapely.geometry import Polygon, LineString
from shapely.ops import unary_union
d=json.load(open('model_sub.json'))
def tris(a): return np.array(a).reshape(-1,3,3)
def plane_groups(T, tag):
    out=collections.defaultdict(list)
    for t in T:
        n=np.cross(t[1]-t[0],t[2]-t[0]); L=np.linalg.norm(n)
        if L<1e-6: continue
        n=n/L
        if abs(n[1])>0.3: continue  # skip non vertical
        n=n.copy(); n[1]=0; n/=np.linalg.norm(n)
        # canonical: angle in [0,180)
        ang=math.degrees(math.atan2(n[2],n[0]))
        if ang<0: ang+=180; n=-n
        if ang>=179.5: ang-=180; n=-n
        dd=float(np.dot(n,t.mean(0)))
        out[(round(ang/2)*2, round(dd*2)/2)].append((t,n,tag))
    return out
def proj(t,n):
    r=np.array([-n[2],0,n[0]])  # horizontal in plane
    return [(float(np.dot(p,r)), float(p[1])) for p in t]
if __name__=='__main__':
    G=collections.defaultdict(list)
    for src in [('wing','glass'),('rib','glass')]:
        for k,v in plane_groups(tris(d[src[0]][src[1]]),src[0]).items(): G[k]+=v
    tot=0
    for k in sorted(G):
        items=G[k]; n=items[0][1]
        polys=[Polygon(proj(t,n)) for t,_,_ in items]
        u=unary_union([p.buffer(0.01) for p in polys if p.area>1e-4]).buffer(-0.01)
        tot+=u.area
        b=u.bounds
        print(k, 'n',np.round(n,2), 'src',set(i[2] for i in items),'area %.1f'%u.area,'bounds h %.1f..%.1f y %.1f..%.1f'%(b[0],b[2],b[1],b[3]), 'parts', len(getattr(u,'geoms',[u])))
    print('total',tot)
