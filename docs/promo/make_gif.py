"""Build the promo GIF from captured PNG frames with one shared palette.

usage: python make_gif.py <frames_dir> <out.gif> <width> <fps> <colors> [dither]
"""
import glob
import sys

from PIL import Image

frames_dir, out, width, fps, colors = sys.argv[1], sys.argv[2], int(sys.argv[3]), float(sys.argv[4]), int(sys.argv[5])
dither = Image.Dither.FLOYDSTEINBERG if (len(sys.argv) > 6 and sys.argv[6] == "fs") else Image.Dither.NONE

paths = sorted(glob.glob(f"{frames_dir}/f*.png"))
height = round(540 * width / 960)


def load(p):
    im = Image.open(p).convert("RGB").crop((0, 0, 960, 540))
    return im.resize((width, height), Image.LANCZOS)


# shared palette from ~24 frames spread across the reel, tiled into one image
sample = [load(p) for p in paths[:: max(1, len(paths) // 24)]]
sheet = Image.new("RGB", (width, height * len(sample)))
for i, im in enumerate(sample):
    sheet.paste(im, (0, i * height))
# Reserve slots for the brand/semantic colours: they cover few pixels, so an adaptive
# palette built from a mostly-dark sheet would otherwise merge red into amber.
FIXED = [
    (0x2F, 0xD4, 0x80), (0x1F, 0x8F, 0x58), (0x13, 0x40, 0x2F),   # up green + dimmed
    (0xFF, 0x5C, 0x63), (0xB0, 0x3E, 0x44), (0x4A, 0x1D, 0x26),   # down red + dimmed
    (0xFF, 0xB0, 0x20), (0xFF, 0xCC, 0x55), (0x8A, 0x60, 0x18),   # amber
    (0x4C, 0xC9, 0xF0), (0x2B, 0x7A, 0x99),                       # cyan
    (0xA7, 0x8B, 0xFA), (0x6A, 0x5A, 0xA8),                       # violet
    (0xEE, 0xF1, 0xF7), (0x8D, 0x97, 0xAB), (0x58, 0x62, 0x7A),   # text, mute, dim
]
adaptive = sheet.quantize(colors=colors - len(FIXED), method=Image.Quantize.MEDIANCUT)
pal = adaptive.getpalette()[: 3 * (colors - len(FIXED))]
for c in FIXED:
    pal += list(c)
pal += pal[:3] * (256 - colors)  # pad unused slots with an existing colour
palette = Image.new("P", (1, 1))
palette.putpalette(pal)

frames = [load(p).quantize(palette=palette, dither=dither) for p in paths]

# GIF delays are in 10ms steps; cycle 80/80/90 so the average is 83.3ms (12 fps)
base = 1000 / fps
durations = [80 if i % 3 != 2 else 90 for i in range(len(frames))] if abs(base - 83.33) < 0.5 else [round(base)] * len(frames)

frames[0].save(out, save_all=True, append_images=frames[1:], duration=durations, loop=0, optimize=True, disposal=1)
print(f"{len(frames)} frames, {width}x{height}, {sum(durations) / 1000:.1f}s")
