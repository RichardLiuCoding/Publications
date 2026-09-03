# -*- coding: utf-8 -*-
"""Bake the vertical flip out of the rasters matplotlib embeds in an SVG.

matplotlib writes every imshow bitmap as

    <image transform="scale(1 -1) translate(0 -T)" x=X y=Y width=W height=H .../>

because its data space is y-up and SVG is y-down. LibreOffice's SVG import
ignores that transform on <image> elements, so every raster came out mirrored
in the EMF while the axes and text around it stayed correct. Here the bitmap is
flipped in the file and the transform is dropped, so no importer has to
interpret it.

Mapping: the transform is translate(0, D) then scale(1, -1), so a point py
lands at -(py + D). The element box spans py in [y, y+h], so its top edge in
the final frame is -(y + h) - D. Note D is negative in matplotlib output, so
the sign matters and getting it wrong pushes the image off the canvas.
"""
import base64
import io as _io
import re

from PIL import Image

IMG = re.compile(r'<image\b[^>]*/>', re.S)
ATTR = re.compile(r'(\w[\w:-]*)\s*=\s*"([^"]*)"', re.S)
FLIP = re.compile(r'scale\(1\s+-1\)\s*translate\(0\s+(-?[\d.eE+-]+)\)')


def bake(svg_text):
    """Return (new_svg, n_baked, n_skipped)."""
    baked = [0, 0]

    def one(m):
        tag = m.group(0)
        a = dict(ATTR.findall(tag))
        tr = a.get("transform", "")
        f = FLIP.search(tr)
        href = a.get("xlink:href") or a.get("href") or ""
        if not f or not href.startswith("data:image/png;base64,"):
            baked[1] += 1
            return tag
        D = float(f.group(1))
        x = float(a["x"])
        y = float(a["y"])
        w = float(a["width"])
        h = float(a["height"])

        raw = base64.b64decode(href.split(",", 1)[1])
        im = Image.open(_io.BytesIO(raw)).transpose(Image.FLIP_TOP_BOTTOM)
        buf = _io.BytesIO()
        im.save(buf, format="PNG")
        new_href = "data:image/png;base64," + \
            base64.b64encode(buf.getvalue()).decode("ascii")

        keep = " ".join('%s="%s"' % (k, v) for k, v in a.items()
                        if k not in ("transform", "x", "y", "width", "height",
                                     "xlink:href", "href"))
        baked[0] += 1
        return ('<image %s x="%.6f" y="%.6f" width="%.6f" height="%.6f" '
                'xlink:href="%s"/>'
                % (keep, x, -(y + h) - D, w, h, new_href))

    return IMG.sub(one, svg_text), baked[0], baked[1]


if __name__ == "__main__":
    import sys
    from pathlib import Path
    for p in sys.argv[1:]:
        t = Path(p).read_text()
        out, n, k = bake(t)
        Path(p).write_text(out)
        print("  %-40s baked %d, left alone %d" % (Path(p).name, n, k))
