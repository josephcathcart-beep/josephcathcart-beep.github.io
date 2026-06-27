#!/usr/bin/env python3
"""
pdf-to-watermarked-images.py
----------------------------
Turn a PDF into one watermarked PNG per page, ready to publish on the site
INSTEAD of the PDF. The original PDF never needs to go in your repo.

USAGE
    python3 pdf-to-watermarked-images.py  path/to/file.pdf
    python3 pdf-to-watermarked-images.py  path/to/file.pdf  --text "Further Maths etc."
    python3 pdf-to-watermarked-images.py  path/to/folder        (does every PDF inside)

Common options (all optional):
    --text   "..."   watermark wording        (default: "Further Maths etc.")
    --dpi    150      image resolution         (default: 150; 120 = smaller files)
    --out    img      output base folder       (default: img)
    --opacity 0.16    watermark strength 0–1   (default: 0.16)

OUTPUT
    img/<pdf-name>/p1.png, p2.png, ...
    and it prints the exact data-block line to paste into index.html.
"""

import sys, os, argparse
import fitz                      # PyMuPDF
from PIL import Image, ImageDraw, ImageFont


def load_font(size):
    # Try a few fonts that exist on macOS / Linux; fall back to PIL's builtin.
    candidates = [
        "/System/Library/Fonts/Supplemental/Arial.ttf",   # macOS
        "/System/Library/Fonts/Helvetica.ttc",            # macOS
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",# Linux
        "DejaVuSans.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            continue
    return ImageFont.load_default()


def tile_watermark(img, text, opacity):
    """Stamp a tiled, diagonal, semi-transparent watermark across the image."""
    base = img.convert("RGBA")
    W, H = base.size
    # watermark scales with page width so it looks the same at any DPI
    font = load_font(max(18, W // 22))

    # one tile = text drawn on a transparent layer, then rotated 30 degrees
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    alpha = int(255 * opacity)

    step_x = tw + W // 6
    step_y = th + H // 7
    y = -step_y
    row = 0
    while y < H + step_y:
        offset = (step_x // 2) if row % 2 else 0   # brick-stagger the rows
        x = -step_x + offset
        while x < W + step_x:
            draw.text((x, y), text, font=font, fill=(0, 0, 0, alpha))
            x += step_x
        y += step_y
        row += 1

    layer = layer.rotate(30, expand=False, resample=Image.BICUBIC)
    return Image.alpha_composite(base, layer).convert("RGB")


def convert(pdf_path, out_base, text, dpi, opacity):
    name = os.path.splitext(os.path.basename(pdf_path))[0]
    out_dir = os.path.join(out_base, name)
    os.makedirs(out_dir, exist_ok=True)

    doc = fitz.open(pdf_path)
    zoom = dpi / 72.0
    mat = fitz.Matrix(zoom, zoom)
    n = doc.page_count

    for i, page in enumerate(doc, start=1):
        pix = page.get_pixmap(matrix=mat)
        img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        img = tile_watermark(img, text, opacity)
        img.save(os.path.join(out_dir, f"p{i}.png"), optimize=True)

    doc.close()
    print(f"  {name}: {n} page(s) -> {out_dir}/p1..p{n}.png")
    # the line to paste into index.html (pages = page count)
    print(f'     imgDir:"{out_dir}/", pages:{n},')
    return name, n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path", help="a PDF file, or a folder of PDFs")
    ap.add_argument("--text", default="Further Maths etc.")
    ap.add_argument("--dpi", type=int, default=150)
    ap.add_argument("--out", default="img")
    ap.add_argument("--opacity", type=float, default=0.16)
    args = ap.parse_args()

    if os.path.isdir(args.path):
        pdfs = [os.path.join(args.path, f) for f in sorted(os.listdir(args.path))
                if f.lower().endswith(".pdf")]
        if not pdfs:
            print("No PDFs found in that folder."); return
    else:
        pdfs = [args.path]

    print(f'Watermark: "{args.text}"   dpi: {args.dpi}   opacity: {args.opacity}\n')
    for p in pdfs:
        convert(p, args.out, args.text, args.dpi, args.opacity)
    print("\nDone. Commit the img/ folder (NOT the source PDFs) and wire the items in index.html.")


if __name__ == "__main__":
    main()
