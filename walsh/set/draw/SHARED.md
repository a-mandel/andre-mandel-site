# SHARED: one data module for every crew

Built by `draw/build_shared.py` (run `python3 walsh/set/draw/build_shared.py`, about 20 s). It reads the pocket model and the crews' built data and writes `draw/shared.json` and `draw/shared.js`. Never edit either by hand; rebuild after the model, `drawings.js`, or a crew's data changes.

## How a crew reads it

**In the page.** `v2.html` loads `draw/shared.js` before the crew files, so `window.SHARED` is ready when a sheet or overlay renders (overlays also get it as `ctx.SHARED`). Helpers:

```js
const S = window.SHARED;
S.plan('A2.1', x, z)        // model feet to field inches on any plan sheet in S.coords.plans
S.view('A4.1', x, el, z)    // a model point at elevation el to field inches on an elevation or section view
S.viewsOn('A3.0')           // ['A3.0-2', 'A3.0-1']
S.ftin(15.01)               // "15′ 0″"
LIVING_OVERLAYS.push({ id: 'A2.1', z: 5, html: ctx => { const [fx, fy] = S.plan('A2.1', 35.82, -14.56); return `<i style="left:${ctx.U(fx)};top:${ctx.U(fy)}"></i>`; } });
```

**In Python.** `json.loads(Path('walsh/set/draw/shared.json').read_text())`. Same data; apply `fx`, `fy` yourself (below).

## Units and frames

Model feet: x east on the plan, z down the sheet (south), y up; elevation = 5990.0 + y. Field inches: origin at the field's top left, 31.25 by 23 (sheet inches minus 1.25 and 0.5). Registration is checked in the browser: footprint corners on A2.1 and the A4.1 image frame land within 0.001 in.

## Schema

| Key | What |
|---|---|
| `meta` | datum, north angle, sources, the FA note |
| `coords.plans[sheet]` | `fx = fx[0]·x + fx[1]`, `fy = fy[0]·z + fy[1]`, scale, source. A1.2, A2.0 to A2.5 (one registration), A0.6 level 1 view |
| `coords.views[name]` | A4.0 to A4.3, A3.0-1, A3.0-2: `h = x·right[0] + z·right[1]`, `fx = fx[0]·h + fx[1]`, `fy = fy[0]·(el − 5990) + fy[1]`; image frame, cut plane |
| `grids.grids[]` | north (with entry and garage), bridge, south: `num` and `let` lines (`id`, `a`, `b` in model feet, `what`), `num_spacing`, `let_spacing` in ft and ft in text. One label per physical line across the house; letters skip I and O |
| `grids.refs`, `grids.posts` | beams off the grid (fold beam, bridge, granny, south beam, terrace glulam) with elevations; every post from the model |
| `rooms[]` | `id`, `name`, `level`, `ff`, `wing`, `label`, `poly`, `sf_about`, `ceiling_ft`, `ceiling_el`, `ceiling_text`, `placeholder`, `note`. Ceilings sampled with the A2.4 and A2.5 method |
| `dims[]` | `sheets`, `e` (measured points), `s` (the string line), `ft`, `text`, `note` |
| `levels[]` | every floor, plate, beam, tip and ridge: `name`, `el`, `model_y`, `kind` |
| `heights` | `meta` (VII.5 method, average grade, ridge limit, slope) and `points[]`: `at`, `el`, `grade`, `over`, `margin`, `flag` (within 1 ft of 30), chimneys with the R1003.9 check |
| `tags` | `matrix` (the A1.3 rows) and `tags[]`: `id`, `sheets`, `at`, `el`, `text`, `status` (meets, variance, confirm), `a13` row, `at_field` precomputed per sheet or view |
| `walls[]` | W1 to W17 as on A7.1: segments on the glass line, anchor, glass sf, types, over 140 sf |
| `openings` | `doors[]` (A7.0 tags, anchors, wall), `windows[]` (every pane: type letter, wall, anchor, sill, head), `window_types` |
| `disagreements` | what the build found between sheets |

Rooms are the 9/30/26 program, placed as placeholders at FA accuracy. Label them as such on any sheet.
