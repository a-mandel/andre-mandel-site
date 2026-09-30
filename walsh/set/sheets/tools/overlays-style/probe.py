#!/usr/bin/env python3
"""overlays-style: prints where candidate model points land (view fractions) in every still, to choose what each overlay carries."""
import math, numpy as np
CA = {  # cover-a render.py JOBS and their frames
 'arrival': ([-150,17.5,74],[-10,17,22],True,[-0.5773502691896257,0.5773502691896257,0.2674094202199276,-0.2741053150199973]),
 'court': ([104,9,70],[14,16,20],True,[-0.6494075931975106,0.6494075931975106,0.3847217689231323,-0.22437776676556737]),
 'tip': ([114,6.5,36],[30,20,4],True,[-0.4663076581549986,0.4663076581549986,0.41260418334820015,-0.024760240852350263]),
 'aerial': ([59,250,236],[-16,6,20],False,[-0.33459531950207316,0.33459531950207316,0.15691366707683432,-0.15691366707683432]),
}
def ca(name, p):
    E, T, lev, (l, r, t, b) = CA[name]; E = np.array(E, float); T = np.array(T, float)
    if lev: T[1] = E[1]
    z = E - T; z /= np.linalg.norm(z); x = np.cross([0, 1, 0], z); x /= np.linalg.norm(x); y = np.cross(z, x)
    d = np.array(p, float) - E; zc = d @ z
    if zc >= 0: return None
    u, v = (d @ x) / -zc, (d @ y) / -zc
    return ((u - l) / (r - l), (t - v) / (t - b))
def pers(eye, at, w, h, p):
    eye = np.array(eye, float); f = np.array(at, float) - eye; f /= np.linalg.norm(f)
    r = np.cross(f, [0, 1, 0]); r /= np.linalg.norm(r); u = np.cross(r, f); d = np.array(p, float) - eye; z = d @ f
    tv = math.tan(math.radians(32)); return (0.5 + (d @ r) / (z * tv * w / h) / 2, 0.5 - (d @ u) / (z * tv) / 2)
def axo(yaw, p, w=14.2, h=6.9):
    el, half, t = 0.56, 47.0, np.array([-17, 11.5, 30.0])
    r = np.array([math.cos(yaw), 0, -math.sin(yaw)]); u = np.array([-math.sin(el) * math.sin(yaw), math.cos(el), -math.sin(el) * math.cos(yaw)])
    d = np.array(p, float) - t; return (0.5 + (d @ r) / (2 * half * w / h), 0.5 - (d @ u) / (2 * half))
PTS = {'tip': [36.94, 33, 10.72], 'tipG': [36.94, 3.63, 10.72], 'g1N': [-75.78, 7, -19.06], 'g11N': [35.82, 7, -19.06], 'g11S': [35.82, 7, 11.94],
       'B5': [-9.19, 36, 7.94], 'B11': [35.82, 36, 7.94], 'A4': [-20.58, 41, -14.56], 'A11': [35.82, 41, -14.56], 'A1': [-75.78, 41, -14.56],
       'FBa': [38.06, 22, -15.75], 'FBb': [-22.91, 22, 8.92], 'D0': [-3.97, 7.5, 18.95], 'D1': [20.02, 7.5, 18.95], 'tree': [-14.59, 30, 24.67],
       'sG': [-24.58, 5, 78.8], 'chS': [24.3, 27.9, 63.9]}
f = lambda v: None if v is None else f'{v[0]:.3f},{v[1]:.3f}'
for n in CA: print(n, {k: f(ca(n, p)) for k, p in PTS.items()})
CAMS = {'arr': ([-45, 14.2, 33], [4, 15.5, 22], 19.34, 15.2), 'din': ([13.4, 13.1, 37.5], [-14.6, 16.5, 22.5], 8.78, 6.9), 'tipv': ([60, 8.0, 26], [33, 21, 8], 8.78, 6.9)}
for n, (e, a, w, h) in CAMS.items(): print(n, {k: f(pers(e, a, w, h, p)) for k, p in PTS.items()})
for n, yaw in [('sw', -math.pi / 4), ('se', math.pi / 4), ('nw', -3 * math.pi / 4), ('ne', 3 * math.pi / 4)]: print(n, {k: f(axo(yaw, p)) for k, p in PTS.items()})
