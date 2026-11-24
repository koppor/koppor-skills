#!/usr/bin/env python3
"""FMC block diagrams (compositional structures) as native PowerPoint shapes.

Library and CLI on top of python-pptx. Every element follows the FMC block
diagram reference sheet (https://www.fmc-modeling.org/notation_reference):

    agent                 angular box                      agent(), human_agent()
    storage               rounded box                      storage()
    channel               small circle on a line           *_channel()
    read access           arrow storage -> agent           read_access()
    write access          arrow agent -> storage           write_access()
    modifying access      two opposing arcs                modifying_access()
    unidirectional ch.    two filled heads, one before     unidirectional_channel()
                          and one after the circle
    bidirectional ch.     plain line through the circle    bidirectional_channel()
    request/response      plain line, circle, "R" with a   request_response_channel()
                          triangle in request direction
    structure variance    dashed rounded location          structure_variance()

All coordinates are points (1/72 inch) from the top left corner of the slide.

CLI:
    python fmc_pptx.py stencil out.pptx    build the stencil deck
    python fmc_pptx.py check deck.pptx     lint any deck, JSON on stdout
"""
from __future__ import annotations

import json
import math
import sys
from dataclasses import dataclass, field

from lxml import etree
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Pt

EMU_PER_PT = 12700

# Style. Change these module attributes before drawing to match a house style.
INK = "000000"          # borders, edges, text
PAPER = "FFFFFF"        # default fill of agents, storages and channels
SHADE = "E6E6E6"        # container agents and structure variance locations
NODE_WIDTH = 1.75       # border of agents, storages and channels, in pt
EDGE_WIDTH = 0.75       # accesses and channel lines, thinner than the borders
HEAD = "triangle"       # filled. "stealth" is filled as well. Never "arrow" (open).
HEAD_SIZE = "lg"        # "sm" | "med" | "lg"; PowerPoint scales the head with the line width
FONT = None             # None: font of the theme
FONT_SIZE = 12
CHANNEL_RADIUS = 6


@dataclass
class Node:
    """An agent, a storage or a channel, with its bounding box in pt."""
    kind: str                      # "agent" | "storage" | "channel"
    x: float
    y: float
    w: float
    h: float
    shapes: list = field(default_factory=list)

    @property
    def cx(self): return self.x + self.w / 2

    @property
    def cy(self): return self.y + self.h / 2

    @property
    def center(self): return (self.cx, self.cy)


# ----------------------------------------------------------------- basics

def new_presentation(width=960, height=540):
    """Empty 16:9 presentation (python-pptx default template is 4:3)."""
    prs = Presentation()
    prs.slide_width, prs.slide_height = Pt(width), Pt(height)
    return prs


def blank_slide(prs):
    layout = next((l for l in prs.slide_layouts if l.name == "Blank"), prs.slide_layouts[-1])
    return prs.slides.add_slide(layout)


def _rgb(hex_): return RGBColor.from_string(hex_)


def _plain(shape, fill, width, dash=False):
    """Explicit fill and line, no theme shadow."""
    if fill is None:
        shape.fill.background()
    else:
        shape.fill.solid()
        shape.fill.fore_color.rgb = _rgb(fill)
    shape.line.color.rgb = _rgb(INK)
    shape.line.width = Pt(width)
    if dash:
        _dash(shape)
    shape.shadow.inherit = False
    _no_theme_style(shape)


def _no_theme_style(shape):
    """Drop the reference to the theme's shape style: it gives connectors a shadow in many themes."""
    for st in shape._element.findall(qn("p:style")):
        shape._element.remove(st)


def _dash(shape):
    ln = shape.line._get_or_add_ln()
    for old in ln.findall(qn("a:prstDash")):
        ln.remove(old)
    d = etree.SubElement(ln, qn("a:prstDash"), val="lgDash")
    fill = ln.find(qn("a:solidFill"))
    if fill is not None:           # schema order: fill, prstDash, join, headEnd, tailEnd
        fill.addnext(d)


def _head(shape):
    """Filled arrowhead at the end of a connector or an open path."""
    ln = shape.line._get_or_add_ln()
    etree.SubElement(ln, qn("a:tailEnd"), type=HEAD, w=HEAD_SIZE, len=HEAD_SIZE)


def _write(shape, text, size, anchor=MSO_ANCHOR.MIDDLE, align=PP_ALIGN.CENTER, bold=False):
    tf = shape.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = Pt(4)
    tf.margin_top = tf.margin_bottom = Pt(2)
    for k, line_ in enumerate(text.split("\n")):
        p = tf.paragraphs[0] if k == 0 else tf.add_paragraph()
        p.alignment = align
        r = p.add_run()
        r.text = line_
        r.font.size = Pt(size)
        r.font.bold = bold
        r.font.color.rgb = _rgb(INK)
        if FONT:
            r.font.name = FONT


def label(slide, x, y, w, h, text, size=None, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE, bold=False):
    """Free text, e.g. a channel name or a caption."""
    t = slide.shapes.add_textbox(Pt(x), Pt(y), Pt(w), Pt(h))
    t.text_frame.margin_left = t.text_frame.margin_right = Pt(0)
    _write(t, text, size or FONT_SIZE, anchor, align, bold)
    t.text_frame.margin_left = t.text_frame.margin_right = Pt(0)
    t.text_frame.margin_top = t.text_frame.margin_bottom = Pt(0)
    return t


_ANCHOR = {"center": (MSO_ANCHOR.MIDDLE, PP_ALIGN.CENTER), "top": (MSO_ANCHOR.TOP, PP_ALIGN.CENTER),
           "top-left": (MSO_ANCHOR.TOP, PP_ALIGN.LEFT), "bottom": (MSO_ANCHOR.BOTTOM, PP_ALIGN.CENTER)}


def _box(slide, kind, preset, x, y, w, h, name, fill, size, at, dash=False):
    if w <= 0 or h <= 0:
        raise ValueError(f"{kind} {name!r}: width and height must be positive, got {w} x {h}")
    b = slide.shapes.add_shape(preset, Pt(x), Pt(y), Pt(w), Pt(h))
    _plain(b, fill, NODE_WIDTH, dash)
    if name:
        _write(b, name, size or FONT_SIZE, *_ANCHOR[at])
    return b


# ------------------------------------------------------------------ nodes

def agent(slide, x, y, w, h, name="", fill=PAPER, size=None, at="center"):
    """Active component: an angular box. `at="top-left"` for an agent that contains others."""
    return Node("agent", x, y, w, h, [_box(slide, "agent", MSO_SHAPE.RECTANGLE, x, y, w, h, name, fill, size, at)])


def human_agent(slide, x, y, w, h, name="", fill=PAPER, size=None):
    """Agent that is a human: the agent box with a stick figure inside, the name below the figure."""
    box = _box(slide, "agent", MSO_SHAPE.RECTANGLE, x, y, w, h, "", fill, size, "center")
    out = [box]
    text_h = (size or FONT_SIZE) * 1.3 * (name.count("\n") + 1) + 2 if name else 0
    fh = max(min(h - text_h - 8, w - 8, 30), 10)             # height of the figure
    top = y + (h - text_h - fh) / 2
    cx, r = x + w / 2, fh * 0.14
    head = slide.shapes.add_shape(MSO_SHAPE.OVAL, Pt(cx - r), Pt(top), Pt(2 * r), Pt(2 * r))
    _plain(head, None, EDGE_WIDTH + 0.25)
    out.append(head)
    neck, hip, arm = top + 2 * r, top + fh * 0.62, fh * 0.30
    for x1, y1, x2, y2 in ((cx, neck, cx, hip),
                           (cx, neck + fh * 0.16, cx - arm, neck + fh * 0.02),   # arms point upwards
                           (cx, neck + fh * 0.16, cx + arm, neck + fh * 0.02),
                           (cx, hip, cx - arm * 0.85, top + fh), (cx, hip, cx + arm * 0.85, top + fh)):
        c = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Pt(x1), Pt(y1), Pt(x2), Pt(y2))
        c.line.color.rgb = _rgb(INK)
        c.line.width = Pt(EDGE_WIDTH + 0.25)
        _no_theme_style(c)
        out.append(c)
    if name:
        out.append(label(slide, x + 2, y + h - text_h - 3, w - 4, text_h, name, size))
    return Node("agent", x, y, w, h, out)


def storage(slide, x, y, w, h, name="", fill=PAPER, size=None, at="center"):
    """Passive component that holds information: a rounded box (short sides fully round)."""
    b = _box(slide, "storage", MSO_SHAPE.ROUNDED_RECTANGLE, x, y, w, h, name, fill, size, at)
    b.adjustments[0] = 0.5
    return Node("storage", x, y, w, h, [b])


def structure_variance(slide, x, y, w, h, fill=SHADE):
    """Location in which agents are created and removed: a dashed storage. Draw the agents inside
    afterwards; the creating agent gets a modifying_access() to this location."""
    b = _box(slide, "storage", MSO_SHAPE.ROUNDED_RECTANGLE, x, y, w, h, "", fill, None, "center", dash=True)
    b.adjustments[0] = min(0.5, 24 / min(w, h))
    return Node("storage", x, y, w, h, [b])


def channel(slide, cx, cy, r=None):
    """A bare channel circle. Normally use the *_channel() functions, which place it on the line.
    Use this one for a channel that more than two agents share, then link() each agent to it."""
    r = r or CHANNEL_RADIUS
    o = slide.shapes.add_shape(MSO_SHAPE.OVAL, Pt(cx - r), Pt(cy - r), Pt(2 * r), Pt(2 * r))
    _plain(o, PAPER, NODE_WIDTH)
    return Node("channel", cx - r, cy - r, 2 * r, 2 * r, [o])


def dots(slide, x1, y1, x2, y2, n=3, d=2.5):
    """Three dots between two instances: 'and more of the same kind'."""
    out = []
    for k in range(n):
        t = k / (n - 1)
        px, py = x1 + (x2 - x1) * t, y1 + (y2 - y1) * t
        o = slide.shapes.add_shape(MSO_SHAPE.OVAL, Pt(px - d / 2), Pt(py - d / 2), Pt(d), Pt(d))
        _plain(o, INK, 0.25)
        out.append(o)
    return out


# --------------------------------------------------------------- geometry

def _ray_rect(o, d, x, y, w, h):
    t0, t1 = -math.inf, math.inf
    for p, v, lo, hi in ((o[0], d[0], x, x + w), (o[1], d[1], y, y + h)):
        if abs(v) < 1e-12:
            if p < lo or p > hi:
                return None
            continue
        a, b = (lo - p) / v, (hi - p) / v
        t0, t1 = max(t0, min(a, b)), min(t1, max(a, b))
    return t0 if 0 <= t0 <= t1 else None


def _ray_disc(o, d, cx, cy, r):
    fx, fy = o[0] - cx, o[1] - cy
    b = fx * d[0] + fy * d[1]
    disc = b * b - (fx * fx + fy * fy - r * r)
    if disc < 0:
        return None
    t = -b - math.sqrt(disc)
    return t if t >= 0 else None


def _hit(node, o, d):
    """First point of the outline of `node` on the ray from `o` (outside) in unit direction `d`."""
    n = node
    if n.kind == "agent":
        ts = [_ray_rect(o, d, n.x, n.y, n.w, n.h)]
    elif n.kind == "channel":
        ts = [_ray_disc(o, d, n.cx, n.cy, n.w / 2 + NODE_WIDTH / 2)]
    else:                                                   # storage: two discs and the box between them
        r = min(n.w, n.h) / 2
        if n.w >= n.h:
            ts = [_ray_disc(o, d, n.x + r, n.cy, r), _ray_disc(o, d, n.x + n.w - r, n.cy, r),
                  _ray_rect(o, d, n.x + r, n.y, n.w - 2 * r, n.h)]
        else:
            ts = [_ray_disc(o, d, n.cx, n.y + r, r), _ray_disc(o, d, n.cx, n.y + n.h - r, r),
                  _ray_rect(o, d, n.x, n.y + r, n.w, n.h - 2 * r)]
    ts = [t for t in ts if t is not None]
    if not ts:
        return None
    t = min(ts)
    return (o[0] + d[0] * t, o[1] + d[1] * t)


def _unit(p, q):
    dx, dy = q[0] - p[0], q[1] - p[1]
    n = math.hypot(dx, dy)
    if n < 1e-9:
        raise ValueError("edge of length zero")
    return (dx / n, dy / n)


def _ends(a, b):
    """End points of a straight edge between a and b (each a Node or an (x, y) point): horizontal or
    vertical where the two overlap, otherwise from centre to centre."""
    an, bn = isinstance(a, Node), isinstance(b, Node)
    if not an and not bn:
        return tuple(a), tuple(b)
    if an and bn:
        lo, hi = max(a.y, b.y), min(a.y + a.h, b.y + b.h)
        if hi > lo and (a.x + a.w <= b.x or b.x + b.w <= a.x):
            o = ((a.x + a.w + b.x) / 2 if a.x < b.x else (b.x + b.w + a.x) / 2, (lo + hi) / 2)
            return (_hit(a, o, (math.copysign(1, a.cx - o[0]), 0)), _hit(b, o, (math.copysign(1, b.cx - o[0]), 0)))
        lo, hi = max(a.x, b.x), min(a.x + a.w, b.x + b.w)
        if hi > lo and (a.y + a.h <= b.y or b.y + b.h <= a.y):
            o = ((lo + hi) / 2, (a.y + a.h + b.y) / 2 if a.y < b.y else (b.y + b.h + a.y) / 2)
            return (_hit(a, o, (0, math.copysign(1, a.cy - o[1]))), _hit(b, o, (0, math.copysign(1, b.cy - o[1]))))
        return (_hit(a, b.center, _unit(b.center, a.center)) or a.center,
                _hit(b, a.center, _unit(a.center, b.center)) or b.center)
    node, p = (a, tuple(b)) if an else (b, tuple(a))
    if node.y < p[1] < node.y + node.h:
        d = (math.copysign(1, node.cx - p[0]), 0)
    elif node.x < p[0] < node.x + node.w:
        d = (0, math.copysign(1, node.cy - p[1]))
    else:
        d = _unit(p, node.center)
    q = _hit(node, p, d) or node.center
    return (q, p) if an else (p, q)


def _kind(node, allowed, role):
    if isinstance(node, Node) and node.kind not in allowed:
        raise ValueError(f"{role} must be {' or '.join(allowed)}, got {node.kind}: FMC block diagrams are "
                         "bipartite, agents connect to storages and channels only")


# ------------------------------------------------------------------ edges

def _line(slide, p, q, head=False):
    c = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Pt(p[0]), Pt(p[1]), Pt(q[0]), Pt(q[1]))
    c.line.color.rgb = _rgb(INK)
    c.line.width = Pt(EDGE_WIDTH)
    _no_theme_style(c)
    if head:
        _head(c)
    return c


def _bezier(p0, c1, c2, p3, t):
    u = 1 - t
    return tuple(u ** 3 * p0[k] + 3 * u * u * t * c1[k] + 3 * u * t * t * c2[k] + t ** 3 * p3[k] for k in (0, 1))


def path(slide, commands, head=False):
    """Open path as one shape: [("M", p), ("L", p), ("C", c1, c2, p), ...], arrowhead at the end.
    For curves and for lines with bends; a single straight line is better drawn with link()."""
    pts, cur = [], None
    for cmd in commands:
        if cmd[0] == "C":
            pts += [_bezier(cur, cmd[1], cmd[2], cmd[3], k / 24) for k in range(25)]
        else:
            pts.append(cmd[1])
        cur = cmd[-1]
    x0, y0 = min(p[0] for p in pts), min(p[1] for p in pts)
    w, h = max(max(p[0] for p in pts) - x0, 0.1), max(max(p[1] for p in pts) - y0, 0.1)
    sh = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Pt(x0), Pt(y0), Pt(w), Pt(h))
    a = "http://schemas.openxmlformats.org/drawingml/2006/main"

    def pt(parent, p):
        etree.SubElement(parent, f"{{{a}}}pt", x=str(round((p[0] - x0) * EMU_PER_PT)), y=str(round((p[1] - y0) * EMU_PER_PT)))

    cust = etree.Element(f"{{{a}}}custGeom")
    for tag in ("avLst", "gdLst", "ahLst", "cxnLst"):
        etree.SubElement(cust, f"{{{a}}}{tag}")
    etree.SubElement(cust, f"{{{a}}}rect", l="0", t="0", r="r", b="b")
    pl = etree.SubElement(cust, f"{{{a}}}pathLst")
    pa = etree.SubElement(pl, f"{{{a}}}path", w=str(round(w * EMU_PER_PT)), h=str(round(h * EMU_PER_PT)), fill="none")
    for cmd in commands:
        el = etree.SubElement(pa, f"{{{a}}}" + {"M": "moveTo", "L": "lnTo", "C": "cubicBezTo"}[cmd[0]])
        for p in cmd[1:]:
            pt(el, p)
    sp_pr = sh._element.spPr
    sp_pr.replace(sp_pr.find(qn("a:prstGeom")), cust)
    _plain(sh, None, EDGE_WIDTH)
    if head:
        _head(sh)
    return sh


def link(slide, a, b, via=(), head=False):
    """Plain line from a to b (Node or point), optionally through the points in `via`.
    Building block of the channels; also connects further agents to a shared channel()."""
    if not via:
        return [_line(slide, *_ends(a, b), head=head)]
    p, _ = _ends(a, via[0])
    _, q = _ends(via[-1], b)
    return [path(slide, [("M", p)] + [("L", tuple(v)) for v in via] + [("L", q)], head=head)]


def read_access(slide, agent_, storage_, via=()):
    """The agent reads the storage: arrow from the storage to the agent."""
    _kind(agent_, ("agent",), "reader"), _kind(storage_, ("storage",), "source of a read access")
    return link(slide, storage_, agent_, via=tuple(reversed(via)), head=True)


def write_access(slide, agent_, storage_, via=()):
    """The agent overwrites the storage: arrow from the agent to the storage."""
    _kind(agent_, ("agent",), "writer"), _kind(storage_, ("storage",), "target of a write access")
    return link(slide, agent_, storage_, via=via, head=True)


def modifying_access(slide, agent_, storage_):
    """The agent reads and changes the storage: two opposing arcs, one head at each end. As on the
    reference sheet the pair runs clockwise: the upper arc points to the right."""
    _kind(agent_, ("agent",), "modifier"), _kind(storage_, ("storage",), "target of a modifying access")
    p, q = _ends(agent_, storage_)
    u = _unit(p, q)
    n = (u[1], -u[0])                      # on screen (y grows downwards): left of the direction
    length = math.hypot(q[0] - p[0], q[1] - p[1])
    s = min(0.15 * length, 5.0)            # distance of the arc ends from the axis; the apex is at 2 s
    mid = ((p[0] + q[0]) / 2, (p[1] + q[1]) / 2)
    out = []
    for sign, src, dst, ps, pd, d in ((1, agent_, storage_, p, q, u), (-1, storage_, agent_, q, p, (-u[0], -u[1]))):
        off = (n[0] * s * sign, n[1] * s * sign)
        m = (mid[0] + off[0], mid[1] + off[1])
        start = isinstance(src, Node) and _hit(src, m, (-d[0], -d[1])) or (ps[0] + off[0], ps[1] + off[1])
        end = isinstance(dst, Node) and _hit(dst, m, d) or (pd[0] + off[0], pd[1] + off[1])
        k = (off[0] * 4 / 3, off[1] * 4 / 3)
        v = ((end[0] - start[0]) / 3, (end[1] - start[1]) / 3)
        c1 = (start[0] + v[0] + k[0], start[1] + v[1] + k[1])
        c2 = (end[0] - v[0] + k[0], end[1] - v[1] + k[1])
        out.append(path(slide, [("M", start), ("C", c1, c2, end)], head=True))
    return out


def _name(slide, node, c, u, name, size, side, r, inside):
    """Name of a channel: next to the circle, or inside a circle that is large enough for it."""
    if not name:
        return
    if inside:
        node.shapes.append(label(slide, c[0] - r, c[1] - r, 2 * r, 2 * r, name, size or 6))
    else:
        node.shapes.append(_channel_label(slide, c, u, name, size, side, r))


def _on_line(p, q, at):
    return (p[0] + (q[0] - p[0]) * at, p[1] + (q[1] - p[1]) * at)


def _channel_label(slide, c, u, text, size, side, r):
    """Name of the channel next to the circle, on the given side of the line (+1 or -1)."""
    size = size or FONT_SIZE - 2
    w, h, gap = max(len(text) * size * 0.62, 12), size * 1.3, r + NODE_WIDTH / 2 + 2
    if abs(u[0]) >= abs(u[1]):             # horizontal line: below (+1) or above (-1)
        return label(slide, c[0] - w / 2, c[1] + gap if side > 0 else c[1] - gap - h, w, h, text, size)
    if side > 0:                           # vertical line: left
        return label(slide, c[0] - gap - w, c[1] - h / 2, w, h, text, size, align=PP_ALIGN.RIGHT)
    return label(slide, c[0] + gap, c[1] - h / 2, w, h, text, size, align=PP_ALIGN.LEFT)


def bidirectional_channel(slide, a1, a2, name=None, at=0.5, size=None, label_side=1, r=None, name_inside=False):
    """Both agents send and receive: a plain line, the circle on it, no arrowheads.
    `at` moves the circle along the line (0 = at a1, 1 = at a2); `label_side` flips the name to the
    other side of the line; `name_inside` writes it into the circle (give a radius `r` that fits)."""
    _kind(a1, ("agent",), "end of a channel"), _kind(a2, ("agent",), "end of a channel")
    r = r or CHANNEL_RADIUS
    p, q = _ends(a1, a2)
    out = [_line(slide, p, q)]
    c = _on_line(p, q, at)
    node = channel(slide, *c, r=r)
    node.shapes = out + node.shapes
    _name(slide, node, c, _unit(p, q), name, size, label_side, r, name_inside)
    return node


def unidirectional_channel(slide, sender, receiver, name=None, at=0.5, size=None, label_side=1, r=None,
                           name_inside=False):
    """Information flows from sender to receiver only: two filled heads, one where the line enters
    the circle and one at the receiver."""
    _kind(sender, ("agent",), "sender"), _kind(receiver, ("agent",), "receiver")
    p, q = _ends(sender, receiver)
    u, c = _unit(p, q), _on_line(p, q, at)
    r = r or CHANNEL_RADIUS
    edge = r + NODE_WIDTH / 2
    out = [_line(slide, p, (c[0] - u[0] * edge, c[1] - u[1] * edge), head=True),
           _line(slide, (c[0] + u[0] * edge, c[1] + u[1] * edge), q, head=True)]
    node = channel(slide, *c, r=r)
    node.shapes = out + node.shapes
    _name(slide, node, c, u, name, size, label_side, r, name_inside)
    return node


def request_response_channel(slide, client, server, name=None, at=0.5, size=None, label_side=1, r=None):
    """The client asks, the server answers: a bidirectional channel marked with "R" and a small
    filled triangle that points from the client to the server."""
    r = r or CHANNEL_RADIUS
    node = bidirectional_channel(slide, client, server, at=at, r=r)
    p, q = _ends(client, server)
    u, c = _unit(p, q), node.center
    gap = r + NODE_WIDTH / 2 + 1.5
    tb, tl, fs = 5.0, 7.0, 8                             # triangle: base and length; font size of the "R"
    if abs(u[0]) >= abs(u[1]):                           # horizontal: "R" and triangle above the circle
        y, sx = c[1] - gap - fs - 1, math.copysign(1, u[0])
        r_box = (c[0] - sx * 4.5 - 4, y - 1, 8, fs + 2)
        tri = (c[0] + sx * 4, y + fs / 2 + 0.5)
        side = 1
    else:                                                # vertical: "R" above the triangle, right of the circle
        x, sy = c[0] + gap + 4.5, math.copysign(1, u[1])
        r_box = (x - 4, c[1] - sy * 5 - fs / 2 - 1, 8, fs + 2)
        tri = (x, c[1] + sy * 5)
        side = 1
    node.shapes.append(label(slide, *r_box, "R", fs))
    t = slide.shapes.add_shape(MSO_SHAPE.ISOSCELES_TRIANGLE, Pt(tri[0] - tb / 2), Pt(tri[1] - tl / 2), Pt(tb), Pt(tl))
    t.rotation = (math.degrees(math.atan2(u[1], u[0])) + 90) % 360
    _plain(t, INK, 0.25)
    node.shapes.append(t)
    if name:
        node.shapes.append(_channel_label(slide, c, u, name, size, side if label_side > 0 else -side, r))
    return node


def group(slide, *items):
    """Group nodes and edges into one PowerPoint group, e.g. to copy a pattern by hand."""
    shapes = []
    for it in items:
        if isinstance(it, Node):
            shapes += it.shapes
        elif isinstance(it, (list, tuple)):
            for s in it:
                shapes += s.shapes if isinstance(s, Node) else [s]
        else:
            shapes.append(it)
    return slide.shapes.add_group_shape(shapes)


# ------------------------------------------------------------------- lint

def check(pptx_path):
    """Problems that python-pptx writes without complaint: sizes below zero (PowerPoint refuses the
    file) and open arrowheads (no FMC edge has one)."""
    prs = Presentation(pptx_path)
    a = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
    findings = []
    for idx, slide in enumerate(prs.slides, 1):
        for el in slide._element.iter(a + "ext"):
            if int(el.get("cx", 0)) < 0 or int(el.get("cy", 0)) < 0:
                findings.append({"slide": idx, "rule": "negative-size", "detail": f"cx={el.get('cx')} cy={el.get('cy')}"})
        for tag in ("headEnd", "tailEnd"):
            for el in slide._element.iter(a + tag):
                if el.get("type") == "arrow":
                    findings.append({"slide": idx, "rule": "open-arrowhead",
                                     "detail": f"{tag} type=arrow; FMC heads are filled (triangle or stealth)"})
    return findings


# ---------------------------------------------------------------- stencil

SOURCE = ("Notation: FMC block diagram reference sheet, https://www.fmc-modeling.org/notation_reference. "
          "Drawn with fmc_pptx.py (koppor-skills, MIT).")


def _title(slide, text):
    label(slide, 40, 22, 880, 30, text, 24, align=PP_ALIGN.LEFT, bold=True)
    label(slide, 40, 508, 880, 14, SOURCE, 8, align=PP_ALIGN.LEFT)


def _caption(slide, x, y, head, body, w=250):
    label(slide, x, y, w, 16, head, 12, align=PP_ALIGN.LEFT, bold=True)
    label(slide, x, y + 17, w, 30, body, 10, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP)


def stencil(out_path):
    prs = new_presentation()
    props = prs.core_properties
    props.title, props.author, props.last_modified_by = "FMC block diagram stencil", "fmc_pptx.py", "fmc_pptx.py"
    props.subject, props.keywords = "Fundamental Modeling Concepts", "FMC, block diagram, stencil"

    # 1 --- elements and access types
    s = blank_slide(prs)
    _title(s, "FMC block diagram: elements and access")
    y = 80
    group(s, agent(s, 40, y, 80, 44, "A"))
    group(s, human_agent(s, 135, y - 4, 44, 52))
    _caption(s, 200, y, "Agent, human agent", "Active: does something. Always angular. Name it with a noun.")
    y = 160
    group(s, storage(s, 40, y, 80, 44, "S"))
    group(s, channel(s, 157, y + 22))
    _caption(s, 200, y, "Storage, channel", "Passive locations: hold or pass information. Always rounded.")
    y = 240
    group(s, link(s, (40, y + 12), (120, y + 12)), link(s, (40, y + 32), (120, y + 32), head=True))
    _caption(s, 200, y, "Edges", "Thin lines. Arrowheads are filled. An agent is only ever connected to a location.")

    x, y = 500, 80
    a, st = agent(s, x, y, 70, 44, "A"), storage(s, x + 130, y, 70, 44, "S")
    group(s, a, st, read_access(s, a, st))
    _caption(s, x + 220, y, "Read access", "A reads S. The arrow points to the agent.", 200)
    y = 160
    a, st = agent(s, x, y, 70, 44, "A"), storage(s, x + 130, y, 70, 44, "S")
    group(s, a, st, write_access(s, a, st))
    _caption(s, x + 220, y, "Write access", "A overwrites S. The arrow points to the storage.", 200)
    y = 240
    a, st = agent(s, x, y, 70, 44, "A"), storage(s, x + 130, y, 70, 44, "S")
    group(s, a, st, modifying_access(s, a, st))
    _caption(s, x + 220, y, "Modifying access (read and write)", "A changes parts of S. Two opposing arcs.", 200)
    y = 330
    a1, st, a2 = agent(s, x, y, 50, 70, "A1"), storage(s, x + 75, y, 50, 70, "S"), agent(s, x + 150, y, 50, 70, "A2")
    group(s, a1, st, a2, modifying_access(s, a1, st), modifying_access(s, a2, st))
    _caption(s, x + 220, y, "Shared storage", "A1 and A2 communicate through S.", 200)

    y = 330
    a1 = agent(s, 40, y, 44, 70, "A1")
    loc = structure_variance(s, 130, y - 12, 110, 94)
    a2 = agent(s, 168, y, 44, 70, "A2")
    acc = modifying_access(s, (84, y + 18), loc)
    ch = bidirectional_channel(s, (84, y + 54), (168, y + 54), at=0.22)
    group(s, a1, loc, a2, acc, ch)
    _caption(s, 260, y, "Structure variance", "A1 creates and removes A2 inside the dashed location: "
             "modifying access to the location.", 200)

    # 2 --- channels
    s = blank_slide(prs)
    _title(s, "FMC block diagram: channels")
    x, y = 40, 90
    a1, a2 = agent(s, x, y, 70, 44, "A1"), agent(s, x + 150, y, 70, 44, "A2")
    group(s, a1, a2, unidirectional_channel(s, a1, a2))
    _caption(s, x + 250, y, "Unidirectional channel",
             "Information flows from A1 to A2 only. Two filled heads: into the circle and into A2.", 300)
    y = 190
    a1, a2 = agent(s, x, y, 70, 44, "A1"), agent(s, x + 150, y, 70, 44, "A2")
    group(s, a1, a2, bidirectional_channel(s, a1, a2))
    _caption(s, x + 250, y, "Bidirectional channel", "Information flows in both directions. No arrowheads.", 300)
    y = 290
    a1, a2 = agent(s, x, y, 70, 44, "A1"), agent(s, x + 150, y, 70, 44, "A2")
    group(s, a1, a2, request_response_channel(s, a1, a2))
    _caption(s, x + 250, y, "Request/response channel",
             "A1 asks, A2 answers. The triangle next to the R points from the requester to the responder.", 300)
    y = 390
    a1, a2 = agent(s, x, y, 70, 74, "A1"), agent(s, x + 150, y, 70, 74, "A2")
    req = unidirectional_channel(s, (x + 70, y + 55), (x + 150, y + 55), name="REQ", r=10, name_inside=True)
    res = unidirectional_channel(s, (x + 150, y + 19), (x + 70, y + 19), name="RES", r=10, name_inside=True)
    group(s, a1, a2, req, res)
    _caption(s, x + 250, y, "Request/response, detailed",
             "The same as two unidirectional channels. Use the R form above unless the two directions differ.", 300)

    x, y = 640, 90
    top, bottom = agent(s, x, y, 90, 36, "Client"), agent(s, x, y + 110, 90, 36, "Server")
    group(s, top, bottom, request_response_channel(s, top, bottom, name="HTTP"))
    top, bottom = agent(s, x + 150, y, 90, 36, "Server"), agent(s, x + 150, y + 110, 90, 36, "Client")
    group(s, top, bottom, request_response_channel(s, bottom, top, name="HTTP"))
    _caption(s, x, y + 160, "Vertical channels",
             "R above or below its triangle, beside the circle; the name of the channel on the other side.", 250)
    y = 330
    a1, a2 = agent(s, x, y, 70, 36, "Worker 1"), agent(s, x + 170, y, 70, 36, "Worker n")
    group(s, a1, a2, dots(s, x + 105, y + 18, x + 135, y + 18))
    _caption(s, x, y + 50, "Several of a kind", "Draw the first and the last instance, three dots between them.", 250)

    # 3 --- example
    s = blank_slide(prs)
    _title(s, "FMC block diagram: example")
    user = human_agent(s, 60, 185, 70, 90, "Customer")
    client = agent(s, 190, 150, 130, 160, "Client", fill=SHADE, at="top-left")
    browser = agent(s, 205, 195, 100, 70, "Web browser")
    shop = agent(s, 390, 90, 330, 340, "Shop server", fill=SHADE, at="top-left")
    web = agent(s, 410, 130, 110, 200, "Web\napplication")
    orders = agent(s, 590, 130, 110, 60, "Order\nservice")
    catalog = agent(s, 590, 270, 110, 60, "Catalogue\nservice")
    db = storage(s, 770, 130, 120, 60, "Orders")
    products = storage(s, 770, 270, 120, 60, "Products")
    cfg = storage(s, 410, 365, 110, 44, "Configuration")
    bidirectional_channel(s, user, browser)
    request_response_channel(s, browser, web, name="HTTPS", at=0.45)
    request_response_channel(s, web, orders)
    request_response_channel(s, web, catalog)
    modifying_access(s, orders, db)
    read_access(s, catalog, products)
    read_access(s, web, cfg)
    label(s, 60, 440, 830, 40,
          "Customer and web browser exchange information in both directions. The web browser sends requests to the web "
          "application, which sends requests to two services. The order service changes the orders, the catalogue "
          "service and the web application only read. Grey marks agents that contain other agents.",
          11, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP)

    prs.save(out_path)
    return out_path


def main(argv):
    if len(argv) == 3 and argv[1] == "stencil":
        print(stencil(argv[2]))
        return 0
    if len(argv) == 3 and argv[1] == "check":
        findings = check(argv[2])
        print(json.dumps({"file": argv[2], "findings": findings}, indent=2))
        return 1 if findings else 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
