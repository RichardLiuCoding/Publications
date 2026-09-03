# -*- coding: utf-8 -*-
"""Report pairs of text labels whose drawn boxes intersect, per figure.

Catches the class of defect that is easy to miss by eye at review resolution:
a tick label running under a neighbouring panel, an annotation sitting on a
marker, a legend covering a data point. Text drawn with its own opaque bbox is
allowed to sit on top of an image, so those are reported separately as
deliberate.
"""
import itertools
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import make_ms_figures as M

M.KEEP_OPEN = True


def patch_boxes(ax, r):
    """Bounding boxes of drawn shapes, excluding background slabs."""
    out = []
    for p in ax.patches:
        try:
            bb = p.get_window_extent(renderer=r)
        except Exception:
            continue
        if bb.width <= 0 or bb.height <= 0:
            continue
        if bb.width > 0.45 * ax.figure.bbox.width:      # a background slab
            continue
        if bb.height > 0.45 * ax.figure.bbox.height:
            continue
        out.append(bb)
    return out


def boxes(fig):
    r = fig.canvas.get_renderer()
    out = []
    for ax in fig.axes:
        items = list(ax.texts)
        items += [t for t in ax.get_xticklabels() + ax.get_yticklabels()
                  if t.get_text()]
        items += [ax.xaxis.label, ax.yaxis.label, ax.title]
        lg = ax.get_legend()
        for t in items:
            if not t.get_text().strip() or not t.get_visible():
                continue
            try:
                bb = t.get_window_extent(renderer=r)
            except Exception:
                continue
            shielded = t.get_bbox_patch() is not None
            out.append((bb, t.get_text()[:38].replace("\n", " "), shielded,
                        ax))
        if lg is not None:
            out.append((lg.get_window_extent(renderer=r), "[legend]", True, ax))
    for t in fig.texts:
        if not t.get_text().strip():
            continue
        out.append((t.get_window_extent(renderer=r),
                    t.get_text()[:38].replace("\n", " "),
                    t.get_bbox_patch() is not None, None))
    return out


def overlaps(fig, name, pad=-1.0):
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    bs = boxes(fig)
    hits = []
    # text sitting on top of a drawn shape
    for ax in fig.axes:
        pbs = patch_boxes(ax, r)
        for a, ta, sa, axa in bs:
            if sa or axa is not ax:
                continue
            for b in pbs:
                ax0 = max(a.x0, b.x0) + 2.0
                ax1 = min(a.x1, b.x1) - 2.0
                ay0 = max(a.y0, b.y0) + 2.0
                ay1 = min(a.y1, b.y1) - 2.0
                if not (ax1 > ax0 and ay1 > ay0):
                    continue
                # a container that fully encloses the label is the intended
                # relationship, not a collision
                contains = (b.x0 <= a.x0 + 1 and b.x1 >= a.x1 - 1
                            and b.y0 <= a.y0 + 1 and b.y1 >= a.y1 - 1)
                inside = (a.x0 <= b.x0 + 1 and a.x1 >= b.x1 - 1
                          and a.y0 <= b.y0 + 1 and a.y1 >= b.y1 - 1)
                if contains or inside:
                    continue
                hits.append(((ax1 - ax0) * (ay1 - ay0), ta, "<shape>", True))
                break
    for (a, ta, sa, axa), (b, tb, sb, axb) in itertools.combinations(bs, 2):
        if sa or sb:                     # one of them carries an opaque box
            continue
        ax0 = max(a.x0, b.x0) + pad
        ax1 = min(a.x1, b.x1) - pad
        ay0 = max(a.y0, b.y0) + pad
        ay1 = min(a.y1, b.y1) - pad
        if ax1 > ax0 and ay1 > ay0:
            area = (ax1 - ax0) * (ay1 - ay0)
            hits.append((area, ta, tb, axa is axb))
    hits.sort(reverse=True)
    if not hits:
        print("  %-34s clean" % name)
    for area, ta, tb, same in hits[:8]:
        print("  %-34s %6.0f px2  %-30s | %-30s %s"
              % (name, area, ta, tb, "same panel" if same else "ACROSS PANELS"))
    return len(hits)


if __name__ == "__main__":
    only = set(sys.argv[1:])
    total = 0
    for fn in (M.fig1, M.fig2, M.fig3, M.fig4, M.fig5, M.fig6, M.fig7,
               M.fig8, M.fig9, M.fig10):
        if only and fn.__name__ not in only:
            continue
        plt.close("all")
        fn()
        f = M.LAST["fig"]
        total += overlaps(f, fn.__name__)
    print("\ntotal overlapping text pairs:", total)
