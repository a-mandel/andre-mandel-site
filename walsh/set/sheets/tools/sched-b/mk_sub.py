"""pull the pieces sched-b needs out of the pocket model's DATA (walsh/index.html)"""
import json, re, pathlib
M = pathlib.Path(__file__).resolve().parents[4] / 'index.html'
for line in M.read_text().splitlines():
    if 'id="model-data"' in line:
        d = json.loads(re.search(r'id="model-data">(.*?)</script>', line).group(1)); break
json.dump({k: d[k] for k in ['wing', 'rib', 'panels', 'sq', 'extra', 'A', 'info', 'plans']}, open(pathlib.Path(__file__).parent / 'model_sub.json', 'w'))
print('model_sub.json from', M)
