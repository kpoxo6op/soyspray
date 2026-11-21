#!/usr/bin/env python3
"""Cut a generated wood-engraving master into the site's one-ink web files.

  python3 tools/art.py MASTER.png epictetus handbook-001 [--blank x0,y0,x1,y1 ...] [--fill x0,y0,x1,y1 ...]

Writes art/<book>/<slug>-<W>x<H>.<hash8>.{avif,webp} at 480, 960 and 1440 wide.
Every pixel is black; the alpha channel is the ink. Needs Pillow with AVIF and WebP.
Masters are not kept in the repository.
"""
import hashlib, io, pathlib, sys
from PIL import Image, ImageChops, ImageDraw, ImageOps

WIDTHS = (480, 960, 1440)
BUDGET = {480: 20, 960: 40, 1440: 70}          # KB per file
LO, HI = 0.20, 0.85                            # levels: darker than LO is ink, lighter than HI is ground
MARGIN = 0.03                                  # blank margin round the trimmed print, of its longer side
MIN_ASPECT = 1.5                               # narrow subjects are padded out to 3:2, wide ones keep their shape

def cut(path, blanks, fills=()):
    g = Image.open(path).convert('L')
    d = ImageDraw.Draw(g)
    for b in blanks: d.rectangle(b, fill=255)  # retouch: paint a stray mark out to ground
    for b in fills: d.rectangle(b, fill=0)     # retouch: close a patch of marks up to solid ink
    lo, hi = round(255 * LO), round(255 * HI)
    ink = ImageOps.invert(g.point([0 if v <= lo else 255 if v >= hi else round((v - lo) * 255 / (hi - lo)) for v in range(256)]))
    box = ink.point(lambda v: 255 if v > 96 else 0).getbbox()
    ink = ink.crop(box)
    m = round(max(ink.size) * MARGIN)
    w, h = ink.width + 2 * m, ink.height + 2 * m
    w = max(w, round(h * MIN_ASPECT))
    canvas = Image.new('L', (w, h), 0)
    canvas.paste(ink, ((w - ink.width) // 2, (h - ink.height) // 2))
    return canvas

def encode(alpha, fmt, q):
    """AVIF: q is the quality. WebP: lossless, with the ink quantised to q levels, which stays as crisp as type."""
    if fmt == 'webp': alpha = alpha.point([round(round(v / 255 * (q - 1)) * 255 / (q - 1)) for v in range(256)])
    im = Image.new('RGBA', alpha.size, (0, 0, 0, 0)); im.putalpha(alpha)
    out = io.BytesIO()
    if fmt == 'avif': im.save(out, 'AVIF', quality=q, speed=0)
    else: im.save(out, 'WEBP', lossless=True, quality=100, method=6)
    return out.getvalue()

STEPS = {'avif': range(50, 13, -4), 'webp': (8, 6, 5, 4, 3)}

def main():
    args = sys.argv[1:]; boxes = {'--blank': [], '--fill': []}
    for flag, found in boxes.items():
        while flag in args:
            i = args.index(flag); found.append(tuple(int(n) for n in args[i + 1].split(','))); del args[i:i + 2]
    master, book, slug = args
    out = pathlib.Path(__file__).resolve().parent.parent / 'art' / book; out.mkdir(parents=True, exist_ok=True)
    for old in out.glob(slug + '-*'): old.unlink()
    full = cut(master, boxes['--blank'], boxes['--fill'])
    for w in WIDTHS:
        h = round(full.height * w / full.width)
        alpha = full.resize((w, h), Image.LANCZOS)
        for fmt in ('avif', 'webp'):
            for q in STEPS[fmt]:
                body = encode(alpha, fmt, q)
                if len(body) <= BUDGET[w] * 1024: break
            else: sys.exit(f'{slug} {w}w {fmt}: {len(body)} bytes is over budget; the engraving is too fine')
            name = f'{slug}-{w}x{h}.{hashlib.sha256(body).hexdigest()[:8]}.{fmt}'
            (out / name).write_bytes(body); print(f'{name}  {len(body) / 1024:.1f} KB  q{q}')
    cover = sum(full.histogram()[128:]) / (full.width * full.height)
    print(f'ink covers {cover:.0%} of the canvas')

if __name__ == '__main__': main()
