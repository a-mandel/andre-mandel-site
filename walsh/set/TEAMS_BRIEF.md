# Living set crews brief (9/30/26)

Twelve builders in six teams fill out the Walsh Residence living set, modeled on a full CD set's sheet structure, drawn in André Mandel's style. The lead (the coordinating session) merges, verifies and publishes. You build one or two sheets and give advice.

## Read first
1. walsh/set/TITLE_BLOCK_BRIEF.md and walsh/set/STUDIO_BRIEF.md: style, rules, brand.
2. walsh/set/v2.html: the living set. Its SET object, fieldCartoon, fieldDraw, viewTitle, noteHTML, the site header and footer, the --swoop curved rules, the type variables, the print CSS.
3. walsh/set/draw/: build_drawings.py, drawings.js, calcs.json, the SVG plans and WebP elevations and sections cut from the model. Reuse the numbers in calcs.json; never contradict them.
4. The pocket model walsh/index.html (3.7 MB, never read it whole: grep -n and cut -c1-300). It has DATA, the ribbon scheme, a gated ?draw hook (window.__draw = drawKit(), used by build_drawings.py for orthographic renders) and the ?sheet mode.
5. The precedent CD set: /mnt/user-data/uploads/GARGENTA_CDv4_090220.pdf (70 pages, 36 x 24). Architectural sheets are pages 1 to 31: A0.0 cover rendering, materials and approvals; A0.1 project data, vicinity, sheet index; A0.2 and A0.3 general notes; A0.5 axonometrics; A0.6 area diagrams; A0.9 renderings; A1.1 survey; A1.2 site plan with coverage calcs; A2.0 to A2.3 plans; A2.4 and A2.5 reflected ceiling and electrical plans; A3.0 and A3.1 sections; A4.0 and A4.1 elevations; A5.x interior elevations and finish schedules; A6.x details; A7.0 door schedule; A7.1 window schedule; L1.0 landscape. Use it for content, structure and what a real sheet carries (pdftoppm -f N -l N -r 40 to look at a page). It is another firm's set: never copy its branding, names, text or title block. Our look is our own.
6. André's reference imagery for style: the 13 images listed in STUDIO_BRIEF.md, and his personal Dropbox WALSH folder if you can reach it through the linked computer (read only; /Users/mangomushroom/Library/CloudStorage/Dropbox-Personal/AM/PROJECTS/WALSH, INTERNAL/REFERENCE holds the Vance Fox precedents). Never write there.

## How your sheet plugs in (do not edit v2.html or walsh/index.html)
Write only your own file walsh/set/sheets/<crew>.js plus your assets in walsh/set/sheets/assets/<crew>/ and any build scripts in walsh/set/sheets/tools/<crew>/. Register each sheet:

```js
LIVING_SHEETS.push({
  id: 'A7.0', group: 'Architectural', title: 'Door schedule', short: 'Door schedule', foot: 'Door schedule',
  scale: 'None', issued: [4],
  cap: 'One honest line in André\'s voice.',
  data: ['3 or 4 short facts'],
  notes: [ { text: 'handwritten note', t: [x, y], p: [x, y], a: 'l' } ],   // sheet inches; optional
  html: ctx => `...`   // the drawing field, positioned in field inches with ctx.U(n); origin at the field's top left
});
```
ctx gives U (inches to CSS), esc, viewTitle(num, title, scale), noteHTML, FX and FY (sheet inches to field inches), SET, DRW (drawings.js data), BL, TBX, W (31.25) and H (23, the field size in inches). An existing id replaces that sheet; a new id slots in by group and number. Keep your views inside the field between the site header (top about 3.4 in) and the footer (bottom about 4.3 in of the field), and left of the title block. Asset paths are relative to walsh/set/ (sheets/assets/<crew>/...). Prefer inline SVG for linework and tables (crisp in PDF); rasters at 200 px per inch of sheet, WebP or JPEG, small files.

## Rules
- Private practice, ANDRÉ MANDEL. No connectors of any kind: no Gmail, Google Drive, Calendar, Dropbox connector, Zoom. Work only inside /home/claude/andre-mandel-site (plus the read only personal Dropbox folder above). Do not git commit or push.
- No architect of record anywhere. No dashes in visible text (no em dash, en dash, or hyphen used as punctuation). Dates M/D/YY. Qualify estimates with "about". FA accuracy, confirm on survey.
- 2025 California codes (Title 24, CRC, CBC, CALGreen, California WUI Code, Title 24 Part 7) effective 1/1/26. Never cite 2022 or older. Lahontan is Very High FHSZ.
- Style: pale weathered paper, black hairlines, burnt orange as the one accent, curved swoop rules instead of straight horizontal rules, handwritten notes on thin leaders ending in orange dots, three fonts only (Tenor Sans titles and labels, EB Garamond italic values, Nothing You Could Do notes). Pencil sketch plans, straightedge, monochrome graphite. Modern with a hand sketch feel, never corny, never dark.
- Design facts to respect: ribbon scheme; the front court tree is the signature, preserved; bridge about 20 ft wide with dining in the middle, stairs only inside the bridge; L2 FF 12 ft over L1; SE wing steps down one 5 to 6 ft step; granny suite at main L1; glass square and panelized, panes 4 ft by 8 ft max, raked glass only at the living room tip; chimneys board form concrete, 4 ft above adjacent roofs; every roof under 30 ft over natural grade; open plan for now, no room programming unless your sheet needs placeholders (label them as such).

## Verify before you report
Serve the repo root with python3 -m http.server on your own port (8900 plus your crew number, listed in your prompt). Playwright chromium (args --use-gl=swiftshader --enable-webgl --ignore-gpu-blocklist). Screenshot each of your sheets at 1914 x 1192 (walsh/set/v2.html#<id>) to /home/claude/tb/crews/<crew>_<id>.png and one at 390 x 844. Check no page errors, no dashes, nothing outside the field, fonts as specified. Look at your screenshots and fix what reads poorly. Other crews are writing their own files at the same time; ignore their sheets.

## Report back (under 220 words)
1. Sheets built, what is on each, how you made them.
2. ADVICE: three to six proposals to improve efficiency, workflow, automation or style for this whole living set practice. Write each as a yes or no question André can answer with one swipe, plus one line of context. Example: "Render all stills from one shared camera list in draw/, so every sheet agrees? · Today each crew picks its own cameras."
