# -*- coding: utf-8 -*-
"""Place an SVG in a slide the way PowerPoint itself does.

PowerPoint 2016 and later store a vector picture as a PNG fallback blip plus
an svgBlip extension pointing at the SVG part. A picture stored this way stays
crisp at any zoom and, more useful here, right click then Convert to Shape
turns it into native editable shapes with real text.

This replaced an SVG to EMF route through LibreOffice, whose EMF writer
silently degraded wide colour bars into flat rectangles and dropped some text.
"""
from pptx.opc.constants import RELATIONSHIP_TYPE as RT
from pptx.opc.package import Part
from pptx.opc.packuri import PackURI
from pptx.oxml.ns import qn
from lxml import etree

SVG_NS = "http://schemas.microsoft.com/office/drawing/2016/SVG/main"
SVG_EXT_URI = "{96DAC541-7B7A-43D3-8B79-37D633B846F1}"
_R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"


def add_svg_picture(slide, png_path, svg_path, x, y, width=None, height=None):
    """Add `png_path` as the fallback and attach `svg_path` as the vector."""
    pic = slide.shapes.add_picture(str(png_path), x, y, width=width,
                                   height=height)
    part = slide.part
    pkg = part.package

    n = 1
    while True:
        pn = PackURI("/ppt/media/vector%d.svg" % n)
        if all(p.partname != pn for p in pkg.iter_parts()):
            break
        n += 1
    svg_part = Part(pn, "image/svg+xml", pkg,
                    open(str(svg_path), "rb").read())
    rId = part.relate_to(svg_part, RT.IMAGE)

    blip = pic._element.blipFill.find(qn("a:blip"))
    ext_lst = blip.find(qn("a:extLst"))
    if ext_lst is None:
        ext_lst = etree.SubElement(blip, qn("a:extLst"))
    ext = etree.SubElement(ext_lst, qn("a:ext"))
    ext.set("uri", SVG_EXT_URI)
    svg_blip = etree.SubElement(ext, "{%s}svgBlip" % SVG_NS)
    svg_blip.set("{%s}embed" % _R, rId)
    return pic


def register_svg_content_type(pptx_path):
    """Ensure [Content_Types].xml declares the svg extension."""
    import shutil
    import zipfile

    tmp = str(pptx_path) + ".tmp"
    with zipfile.ZipFile(str(pptx_path)) as zin, \
            zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
        for n in zin.namelist():
            data = zin.read(n)
            if n == "[Content_Types].xml":
                x = data.decode()
                if 'Extension="svg"' not in x:
                    x = x.replace("</Types>",
                                  '<Default Extension="svg" '
                                  'ContentType="image/svg+xml"/></Types>')
                data = x.encode()
            zout.writestr(n, data)
    shutil.move(tmp, str(pptx_path))
