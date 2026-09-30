# Title block studio brief (9/30/26)

Read TITLE_BLOCK_BRIEF.md first. Everything there still holds unless this file overrides it. This file is the latest word.

## What André said today, distilled
- The logo does not change. Use the brushed A lockup (../../marks/am10_lockup.webp from walsh/set/studio/). The job is to integrate it into the title block just right: scale, position under the 53.6 degree corner cut, breathing room, relation to the rules and type.
- The sheet layout follows the live Walsh web page: WALSH RESIDENCE in wide letterspaced Tenor Sans caps upper left of the field with the address, APN and phase lines under it; a footer along the bottom of the field with sheet ticks and count, the sheet title in letterspaced caps, a Garamond italic caption, a ruled data list, and pill buttons at the bottom right. The right sidebar title block stays. Reference implementation: walsh/set/v2.html.
- The sidebar title block must NOT carry the sheet index (table of contents). Too much information. The index lives on sheet A0.1 and behind the Sheet index button.
- Binding: a full 1 in black textured binding along the left edge, with rivets along its right edge. The paper runs under it to the edge.
- The grid is a true ruler. A mark at every inch: 36 across the top and bottom, 24 down the sides, measured from the paper's edges (x = 0 is the left paper edge, y = 0 the top). Numbers name the actual inch, so the first labeled mark past the binding reads 2, and the last across reads 35. Down the sides the marks are numbered 1 to 23 the same way. Every 6th mark is longer. No mark is drawn where it would land in the binding or on a rounded corner.
- Paper: a little texture, weathered, like his reference images (pale warm grey paper, soft mist, faint fibers and foxing, a whisper of old graphite, long faint construction lines running past the drawings). Subtle, never dirty, never dark. CSS gradients and inline SVG feTurbulence only, no external images.
- The top right corner of the paper flutters in the wind. It must move naturally: layered sine noise (not one repeating sine), a quick lift and a slow settle, a slightly curled flap with a soft moving shadow, occasional stillness between gusts, never cartoonish. Flat in print and with prefers-reduced-motion.

## His reference images (look at them)
/root/.claude/uploads/b0abd60a-a112-5987-bb0d-bf806619c786/ : 45ccc312-image.jpg, 0fe783bb-image.jpg, fef0720a-image.jpg, f4d7b6c9-image.jpg, 86bad856-image.jpg, 36affe7d-image.jpg, a16b8ee3-image.jpg, 932ff20a-image.jpg, 94153975-image.jpg, 05a60e16-image.jpg, 03cd5b41-image.jpg, 75aa027c-image.jpg, 2e0cabc6-image.jpg
Common thread: rendered architecture dissolving into hairline drafting, handwritten notes on thin leaders, vertical datum runs with small tick labels, tiny technical type blocks in the margins, pale misty paper, warm glowing interiors, burnt orange or red as the only accent.

## Hard rules
- Private practice. No connectors of any kind (Gmail, Drive, Calendar, Dropbox, Zoom). Work only in /home/claude/andre-mandel-site/walsh/set/studio/.
- No dashes in visible text: no em dash, no en dash, no hyphen used as punctuation.
- Dates M/D/YY. Three fonts only: Tenor Sans, EB Garamond, Nothing You Could Do (Google Fonts).
- Do not git commit or push.

## Update 9/30/26, 5:45 am (overrides the above where they differ)
- No architect of record anywhere. No AOR label, name, stamp box or seal on any sheet.
- Sidebar geometry, from v2.html (read its TBX, TXL, TXR, LK, LOCK, ENV, CUT, borderPath and the "3 in sidebar" CSS): the sidebar runs from the 32 1/2 line, 3 in wide. The lockup fills the sidebar, its mark spanning the text margins exactly. The upper right corner is not a straight cut: it follows the concave curve of the logo's roof stroke, offset about 0.3 in.
- Curved footer lines: every horizontal rule swoops like the ribbon roof, level and sagging slightly, then lifting at the right (v2's --swoop). Straight rules are out.
- Fonts: explore different typefaces across the 40, but each variation uses 2 or 3 fonts max: one hand sketch face, one sans serif, one serif. Google Fonts only. Name the three on each deck card.
