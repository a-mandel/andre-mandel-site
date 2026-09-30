#!/usr/bin/env python3
"""contact sheet of the cover-b probe stills over sheet paper: contact.py OUT.png [glob]"""
import glob, sys
from pathlib import Path
from PIL import Image
A = Path(__file__).resolve().parents[2] / 'assets' / 'cover-b'
fs = sorted(glob.glob(str(A / (sys.argv[2] if len(sys.argv) > 2 else '*-probe.png'))))
W = 1500; canvas = Image.new('RGB', (W, 4000), (246, 245, 241)); x = y = rowh = 0
for f in fs:
    im = Image.open(f).convert('RGBA')
    if im.size[0] > W: im = im.resize((W, round(im.size[1] * W / im.size[0])))
    if x + im.size[0] > W: x = 0; y += rowh + 12; rowh = 0
    canvas.paste(im, (x, y), im); x += im.size[0] + 12; rowh = max(rowh, im.size[1])
canvas.crop((0, 0, W, y + rowh)).save(sys.argv[1]); print([Path(f).name for f in fs])
