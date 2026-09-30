"""sectelev-b: inline plan_data.json into sheet_src.js and write sheets/sectelev-b.js. Run extract_plan.py first if the model changed."""
from pathlib import Path
HERE = Path(__file__).parent
src = (HERE / 'sheet_src.js').read_text()
data = (HERE / 'plan_data.json').read_text()
out = src.replace('/*PLAN_DATA*/null', data)
(HERE.parents[1] / 'sectelev-b.js').write_text(out)
print('wrote', len(out), 'bytes')
