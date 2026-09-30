import json, re, numpy as np
from shapely.geometry import Polygon, Point
d=json.load(open('model_sub.json')); W=json.load(open('walls_raw.json'))
def nums(s): return [float(v) for v in re.findall(r'-?\d+(?:\.\d+)?', s)]
def subpaths(s):
    out=[]
    for sp in re.split(r'(?=M)', s):
        v=nums(sp)
        if len(v)>=6: out.append(list(zip(v[0::2],v[1::2])))
    return out
F=[Polygon(p).buffer(0) for p in subpaths(d['plans']['foot']['rib'])]
print('foot parts',len(F),[round(f.area) for f in F])
for w in W:
    nx,nz=w['n']; dd=w['d']; r=(-nz,nx)
    for p in w['parts']:
        hc=(p['h0']+p['h1'])/2
        x=nx*dd+r[0]*hc; z=nz*dd+r[1]*hc
        ins=any(f.contains(Point(x+2*nx,z+2*nz)) for f in F); ins2=any(f.contains(Point(x-2*nx,z-2*nz)) for f in F)
        ox,oz=(-nx,-nz) if ins and not ins2 else (nx,nz)
        ang=(np.degrees(np.arctan2(ox,-oz)))%360
        print(w['key'],'part h %.0f..%.0f y %.0f..%.0f'%(p['h0'],p['h1'],p['y0'],p['y1']),'plan c (%.1f,%.1f)'%(x,z),'in+',ins,'in-',ins2,'faces %.0f'%ang)
