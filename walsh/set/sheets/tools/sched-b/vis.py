from planes import *
G=collections.defaultdict(list)
for src in [('wing','glass'),('rib','glass')]:
    for k,v in plane_groups(tris(d[src[0]][src[1]]),src[0]).items(): G[k]+=v
OP=[]
for src in [('panels','wood'),('panels','white'),('sq','rib')]:
    for t in tris(d[src[0]][src[1]]):
        n=np.cross(t[1]-t[0],t[2]-t[0]); L=np.linalg.norm(n)
        if L<1e-6: continue
        OP.append((t,n/L,src[1]))
def segs(a): v=np.array(a).reshape(-1,2,3); return v
MU=[]
for src in [('wing','mull'),('rib','mull'),('panels','line')]:
    for s in segs(d[src[0]][src[1]]): MU.append((s,src[1]))
def planeinfo(k):
    items=G[k]; n=items[0][1]; dd=k[1]
    polys=[Polygon(proj(t,n)) for t,_,_ in items]
    u=unary_union([p.buffer(0.01) for p in polys if p.area>1e-4]).buffer(-0.01)
    # opaque overlays near plane
    ops=[]
    for t,nn,tag in OP:
        if abs(abs(np.dot(nn,n))-1)>0.02: continue
        if abs(np.dot(n,t.mean(0))-dd)>1.0: continue
        P=Polygon(proj(t,n))
        if P.area>1e-4: ops.append((P,tag))
    opu=unary_union([p.buffer(0.01) for p,_ in ops]) if ops else None
    vis=u.difference(opu) if opu is not None else u
    mu=[]
    for s,tag in MU:
        if abs(np.dot(n,s[0])-dd)>1.0 or abs(np.dot(n,s[1])-dd)>1.0: continue
        a=proj(s,n)
        mu.append((a,tag))
    return u,vis,ops,mu,n
if __name__=='__main__':
  for k in sorted(G):
    u,vis,ops,mu,n=planeinfo(k)
    if u.area<5: continue
    print('==',k,'glass %.0f vis %.0f'%(u.area,vis.area),'ops',collections.Counter(t for _,t in ops),'mull',collections.Counter(t for _,t in mu))
    vx=sorted(set(round(a[0][0],1) for a,t in mu if abs(a[0][0]-a[1][0])<0.05))
    hy=sorted(set(round(a[0][1],1) for a,t in mu if abs(a[0][1]-a[1][1])<0.05))
    print('  vertical mull h:',vx[:40]); print('  horiz mull y:',hy[:20])
    for g in getattr(vis,'geoms',[vis]):
        if g.area>0.5: print('   part %.1f sf bounds'%g.area, np.round(g.bounds,1), 'verts',len(g.exterior.coords))
