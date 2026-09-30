# ANDRE MANDEL title block brief (9/30/26)

The shared brief every title block agent reads first. Lead: the coordinating Claude session. Owner: André Mandel.

## The idea
A living plan set. The web page IS the drawing sheet. On a big screen you see a true 24 x 36 sheet (landscape, 36 wide by 24 tall, 3:2) inside a title block, and you page through the set like a bound set. Printing or saving to PDF gives the same sheet at true size. The title block is the framework every deliverable lives in: the table of contents is always visible, issuances build up over time, and the live 3D model sits inside the cover sheet.

## Hard rules
- Private practice (ANDRE MANDEL). Never use Gmail, Google Drive, Calendar, Dropbox, Zoom or any other connector. Work only in this repo.
- No dashes of any kind in any visible text: no em dash, no en dash, no hyphen used as punctuation. Use commas, periods, the middle dot ( · ) or restructure.
- Dates in M/D/YY.
- White, airy, pale paper, black hairlines. Burnt orange is the only accent. No dark page styling (a small ink sheet number cell is fine).
- Self contained single HTML file per option. Fonts only from Google Fonts. No other external scripts or CDNs are needed.

## Sheet geometry (inches, origin top left)
- Sheet 36 x 24. Border margins: 3/4 in left (binding side), 1/2 in top, right, bottom. Border rectangle x 0.75 to 35.5, y 0.5 to 23.5, rounded corners.
- Inch tick marks in the margins on all four sides, set up as a zone grid: numbers across, letters down, I and O skipped. Every 6th tick longer.
- Bound on the LEFT. Suggest the binding visually in the left margin (binding strip, screw posts) without going dark.
- Title block on the RIGHT, running full height. Default: from the 31/32 grid line (x 32.0) to the right border, 3 1/2 in wide, so its text reads on a laptop. An option may argue for a different width, but say why.
- Upper right corner of the border is cut on the angle of the logo's roof stroke: 53.6 degrees from horizontal (dx/dy = 0.738), with rounded fillets easing into the cut. The logo nests under the cut and holds the corner.
- André wants FEW lines in the title block. One vertical rule separating it from the drawing, plus only what is truly needed.

## Screen behavior
- Desktop: scale the whole sheet to fit the window (compute px per inch from the viewport), centered on a slightly deeper paper desk with a soft shadow. Keep a small floating control (previous, sheet number, next, print) outside the sheet.
- Paging: arrow keys, clicks on the title block index, swipe. Sheets turn like a bound set, hinging on the left edge.
- Deep links: #A2.1 opens that sheet.
- Mobile (narrow or portrait): the drawing area fills the screen and the title block collapses into a compact bottom strip with the logo mark, sheet number, sheet title and a button for the index.
- Readable text: on a 1914 x 1192 window the sheet renders at roughly 46 px per inch, so use max(px floor, inches) font sizes (about 10 px floor for data, 9 px for labels).
- Print: @page size 36in 24in, margin 0, one sheet per page, px per inch = true inches. Where the live model iframe sits, print the still image instead.

## Brand
- Logo: the brushed A lockup (roof stroke, post, bar, MANDEL beneath) at ../marks/am10_lockup.webp (357 x 520 px, transparent). The mark alone: ../marks/am10_mark.webp. Name alone: ../marks/am10_name.webp. Paths are relative to walsh/set/. From walsh/set/options/ use ../../marks/...
  - Roof stroke right edge envelope in lockup px: x = 23 + 0.738 y. Use this to keep a constant gap between the stroke and the corner cut.
- Type (three fonts only):
  - Tenor Sans for titles and labels, letterspaced caps.
  - EB Garamond (italic especially) as the secondary serif.
  - Nothing You Could Do for handwritten notes.
  - Google Fonts URL: https://fonts.googleapis.com/css2?family=EB+Garamond:ital,wght@0,400;0,500;1,400;1,500&family=Tenor+Sans&family=Nothing+You+Could+Do&display=swap
- Colors from the live Walsh page: paper #f6f5f1, paper 2 #ebe9e3, ink #1b1a18, muted #6c6963, rule rgba(27,26,24,.2), accent #c07a2c.
- Inspiration: Zaha Hadid, Lebbeus Woods, Libeskind drawings; Studio Cognitive Pulse drafting overlays. Modern, hand sketch feel, CAD precise title block, not corny.

## Title block content (CHxTLD standard, adapted)
- Firm: ANDRÉ MANDEL · Residential design. 40 Edith St #4, San Francisco CA 94133 · 510.459.7686 · andre.mandel@gmail.com
- Project: Walsh Residence. Lahontan Lot 235. 8154 Lahontan Drive, Truckee CA. APN 108 160 012 000. Zoning RS PD 1.7. Placer County. Owner: Dustin Walsh, Elevated Developers.
- Agency and permits: Lahontan design review (LCC) no. pending. Placer County building permit no. pending. Very High FHSZ · Chapter 7A.
- Issuances table directly under the project, dynamic from data, newest first: no., date, issued for. Current data: 1 · 9/28/26 · Feasibility FA2. 2 · 9/30/26 · Living set, cartoon.
- Sheet index (table of contents) always visible and clickable, current sheet highlighted.
- Stamp area: Architect of record, Joseph Benveniste, AIA. Stamp at design review submittal.
- Sheet title, scale, date, drawn by (AM), and a "Feasibility · not for construction" status line.
- Sheet number, large.
- Small line: © 2026 André Mandel. Drawings are instruments of service.

## The cartoon set (use this data)
General: A0.0 Cover · the site (live model), A0.1 Sheet index and project data.
Feasibility: F1.0 Regulatory report, F2.0 Budget framework, F3.0 Preliminary timeline, F4.0 Outline specifications.
Architectural: A1.0 Site plan (1/8 in = 1 ft), A2.1 Main level plan (3/16), A2.2 Lower level plan (3/16), A2.3 Roof plan (3/16), A3.1 Elevations west and north (3/16), A3.2 Elevations east and south (3/16), A4.1 Building sections (3/16), A5.1 Exterior materials and colors, A6.1 Wildfire hardening · Chapter 7A, A9.1 Perspectives.
Landscape: L1.0 Landscape concept.

Cartoon sheets show where each view goes: dashed rounded boxes, a view title bubble under each (view number, title in Tenor caps, scale in Garamond italic) and one short handwritten note in Nothing You Could Do with a thin leader ending in an orange dot. Good notes: "keep the signature tree", "every roof under 30 ft", "approach from the west", "Very High FHSZ, full 7A", "LCC meets the 2nd Wednesday", "cedar, dark steel, board form concrete".

A0.0 holds the live model: an iframe to ../../?sheet (from options/) or ../?sheet (from set/) filling the drawing area. Print fallback image: ../../preview-house.jpg (from options/).

## Verify before reporting
Serve the repo root with `python3 -m http.server` and screenshot with Playwright (python, already installed) at 1914 x 1192 and at 390 x 844, cover sheet and one cartoon sheet each. Check: no text overflow, logo clear of the corner cut, no dashes in visible text, iframe loads. Also print to PDF at 36 x 24 in and confirm one sheet per page.
