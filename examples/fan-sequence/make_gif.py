#!/usr/bin/env python3
"""make_gif.py [test-out dir] - test-out/fan-sequence.gif: the screenshots of the graphic from the four tests, in
order, each with a caption line (test and moment). Needs Pillow."""
import glob, os, re, sys
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "test-out")
WIDTH, BAND, MS = 960, 34, 1800                       # frame width, caption band height, ms per frame
TESTS = {"t1": "normal start and stop", "t2": "requirement not met in time, Reset",
         "t3": "run-step requirement lost", "t4": "trip in Run"}


def font(size):
    for f in ("/System/Library/Fonts/Helvetica.ttc", "C:/Windows/Fonts/arial.ttf",
              "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        if os.path.exists(f):
            return ImageFont.truetype(f, size)
    return ImageFont.load_default()


frames, f = [], font(17)
for path in sorted(glob.glob(os.path.join(OUT, "t[1-4]-[0-9]-*.png"))):
    t, n, what = re.match(r"(t\d)-(\d)-(.+)\.png", os.path.basename(path)).groups()
    im = Image.open(path).convert("RGB")
    im = im.resize((WIDTH, round(im.height * WIDTH / im.width)), Image.LANCZOS)
    fr = Image.new("RGB", (WIDTH, im.height + BAND), "#1F2933")
    fr.paste(im, (0, BAND))
    ImageDraw.Draw(fr).text((12, 8), f"{t}  {TESTS[t]}  -  {n} {what.replace('-', ' ')}", font=f, fill="#FFFFFF")
    frames.append(fr.quantize(colors=256, method=Image.Quantize.FASTOCTREE, dither=Image.Dither.NONE))
dst = os.path.join(OUT, "fan-sequence.gif")
frames[0].save(dst, save_all=True, append_images=frames[1:], duration=MS, loop=0, optimize=True)
print(f"{dst}: {len(frames)} frames, {os.path.getsize(dst) // 1024} kB")
