#!/usr/bin/env python3
"""UML 2.5.1 diagrams as native PowerPoint shapes.

Library and CLI on top of python-pptx. Every element follows the notation clauses
of OMG UML 2.5.1 (formal/17-12-05, https://www.omg.org/spec/UML/2.5.1/PDF):

    association           solid line, open head = navigable,     association()
                          x = not navigable, nothing = unspecified
    dependency            dashed line, open head                 dependency()
    generalization        solid line, hollow triangle            generalization()
    realization           dashed line, hollow triangle           realization()
    aggregation           hollow diamond at the whole            aggregation()
    composition           filled diamond at the whole            composition()
    activity edge, transition   solid line, open head            flow()
    synchronous message   solid line, filled head                message(kind="sync")
    asynchronous message  solid line, open head                  message(kind="async")
    reply, create         dashed line, open head                 message(kind="reply" | "create")

Arrowheads: an open head is <a:tailEnd type="arrow"/> (two strokes), a filled head
<a:tailEnd type="triangle"/>. Both get the same w and len, so the open head is exactly as
narrow as the filled one. A hollow triangle and a diamond have no line-end type in
DrawingML; they are drawn here as freeform shapes.

All coordinates are points (1/72 inch) from the top left corner of the slide.

CLI:
    python uml_pptx.py demo out.pptx      build the example deck
    python uml_pptx.py check deck.pptx    lint any deck, JSON on stdout
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
INK = "000000"          # outlines, edges, text
PAPER = "FFFFFF"        # fill of boxes and of hollow heads
NODE_WIDTH = 1.0        # outline of classes, actions, states, ... in pt
EDGE_WIDTH = 1.0        # edges, in pt
HEAD_W = "lg"           # width of open AND filled heads: "sm" | "med" | "lg" (scales with EDGE_WIDTH)
HEAD_LEN = "lg"         # length of open AND filled heads; the same for open and filled
TRIANGLE = (10.0, 11.0)  # hollow triangle of generalization/realization: length, base width in pt
DIAMOND = (14.0, 8.0)    # aggregation/composition diamond: length, width in pt
FONT = None             # None: font of the theme
MONO = "Consolas"       # attributes and operations; None: font of the theme
FONT_SIZE = 12
LABEL_SIZE = 10         # multiplicities, role names, guards, message names


@dataclass
class Node:
    """A drawn element with its bounding box in pt; `shape` selects how edges are clipped."""
    shape: str                     # "rect" | "ellipse" | "diamond" | "point"
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
    """Empty 16:9 presentation (the python-pptx default template is 4:3)."""
    prs = Presentation()
    prs.slide_width, prs.slide_height = Pt(width), Pt(height)
    return prs


def blank_slide(prs):
    layout = next((l for l in prs.slide_layouts if l.name == "Blank"), prs.slide_layouts[-1])
    return prs.slides.add_slide(layout)


def _rgb(hex_): return RGBColor.from_string(hex_)


def _no_theme_style(shape):
    """Drop the reference to the theme's shape style: it gives connectors a shadow in many themes."""
    for st in shape._element.findall(qn("p:style")):
        shape._element.remove(st)


def _plain(shape, fill, width, dash=False, line=True):
    if fill is None:
        shape.fill.background()
    else:
        shape.fill.solid()
        shape.fill.fore_color.rgb = _rgb(fill)
    if line:
        shape.line.color.rgb = _rgb(INK)
        shape.line.width = Pt(width)
        if dash:
            _dash(shape)
    else:
        shape.line.fill.background()
    shape.shadow.inherit = False
    _no_theme_style(shape)


def _dash(shape):
    ln = shape.line._get_or_add_ln()
    for old in ln.findall(qn("a:prstDash")):
        ln.remove(old)
    d = etree.SubElement(ln, qn("a:prstDash"), val="dash")
    fill = ln.find(qn("a:solidFill"))
    if fill is not None:           # schema order: fill, prstDash, join, headEnd, tailEnd
        fill.addnext(d)


def _line_end(shape, where, kind):
    """kind "open" -> type="arrow" (two strokes), "filled" -> type="triangle". where: "head" (start) or "tail" (end)."""
    ln = shape.line._get_or_add_ln()
    typ = {"open": "arrow", "filled": "triangle"}[kind]
    el = etree.SubElement(ln, qn("a:" + where + "End"), type=typ, w=HEAD_W, len=HEAD_LEN)
    if where == "head":            # headEnd precedes tailEnd in the schema
        tail = ln.find(qn("a:tailEnd"))
        if tail is not None:
            tail.addprevious(el)


def _write(shape, lines, size=None, anchor=MSO_ANCHOR.MIDDLE, align=PP_ALIGN.CENTER):
    """lines: list of str or (str, dict(bold=, italic=, underline=, mono=, size=))."""
    tf = shape.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = Pt(3)
    tf.margin_top = tf.margin_bottom = Pt(1)
    for k, item in enumerate(lines):
        text, fmt = (item, {}) if isinstance(item, str) else item
        p = tf.paragraphs[0] if k == 0 else tf.add_paragraph()
        p.alignment = fmt.get("align", align)
        r = p.add_run()
        r.text = text
        r.font.size = Pt(fmt.get("size", size or FONT_SIZE))
        r.font.bold = fmt.get("bold", False)
        r.font.italic = fmt.get("italic", False)
        r.font.underline = fmt.get("underline", False)
        r.font.color.rgb = _rgb(INK)
        font = MONO if fmt.get("mono") else FONT
        if font:
            r.font.name = font


def label(slide, x, y, w, h, text, size=None, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE, **fmt):
    """Free text: multiplicity, role name, guard, message name, caption."""
    t = slide.shapes.add_textbox(Pt(x), Pt(y), Pt(max(w, 1)), Pt(max(h, 1)))
    _write(t, [(line_, fmt) for line_ in text.split("\n")], size or LABEL_SIZE, anchor, align)
    tf = t.text_frame
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = Pt(0)
    return t


def _text_w(text, size):
    return max(len(line_) for line_ in text.split("\n")) * size * 0.56 + 4


def _check_size(what, w, h):
    if w <= 0 or h <= 0:
        raise ValueError(f"{what}: width and height must be positive, got {w} x {h}")


def _connector(slide, p, q, dash=False, width=None):
    c = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Pt(p[0]), Pt(p[1]), Pt(q[0]), Pt(q[1]))
    c.line.color.rgb = _rgb(INK)
    c.line.width = Pt(width or EDGE_WIDTH)
    _no_theme_style(c)
    if dash:
        _dash(c)
    return c


def _polygon(slide, pts, fill):
    """Closed freeform polygon (hollow triangle, diamond); pts in pt."""
    fb = slide.shapes.build_freeform(pts[0][0], pts[0][1], scale=EMU_PER_PT)
    fb.add_line_segments(pts[1:], close=True)
    sh = fb.convert_to_shape()
    _plain(sh, fill, EDGE_WIDTH)
    return sh


# ------------------------------------------------------------------ nodes

def class_(slide, x, y, w, name, attributes=(), operations=(), keyword=None, abstract=False,
           size=None, line_h=None, show_empty=False):
    """Class (or interface, enumeration, «actor» ...) with name, attribute and operation compartments.
    The name is centred and bold, italic if abstract; the keyword stands above it in guillemets,
    plain face (UML 2.5.1 §9.2.4.1). Empty compartments are left out unless show_empty."""
    size = size or FONT_SIZE
    lh = line_h or size * 1.25
    name_lines = ([("«" + keyword + "»", {})] if keyword else []) + \
                 [(name, {"bold": True, "italic": abstract})]
    nh = len(name_lines) * lh + 6
    secs = [s for s in (attributes, operations) if s or show_empty]
    hs = [max(len(s), 1) * lh + 6 if s else 8 for s in secs]
    h = nh + sum(hs)
    _check_size(f"class {name!r}", w, h)
    box = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Pt(x), Pt(y), Pt(w), Pt(h))
    _plain(box, PAPER, NODE_WIDTH)
    out = [box, _textbox(slide, x, y, w, nh, name_lines, size, PP_ALIGN.CENTER)]
    cy = y + nh
    for sec, hh in zip(secs, hs):
        out.append(_connector(slide, (x, cy), (x + w, cy), width=NODE_WIDTH))
        if sec:
            out.append(_textbox(slide, x + 3, cy, w - 6, hh, [(t, {"mono": True}) for t in sec], size - 1,
                                PP_ALIGN.LEFT))
        cy += hh
    return Node("rect", x, y, w, h, out)


def _textbox(slide, x, y, w, h, lines, size, align):
    t = slide.shapes.add_textbox(Pt(x), Pt(y), Pt(w), Pt(h))
    _write(t, lines, size, MSO_ANCHOR.MIDDLE, align)
    tf = t.text_frame
    tf.margin_top = tf.margin_bottom = Pt(0)
    return t


def interface(slide, x, y, w, name, operations=(), **kw):
    return class_(slide, x, y, w, name, operations=operations, keyword="interface", **kw)


def object_(slide, x, y, w, name, type_, slots=(), size=None):
    """Object (InstanceSpecification): 'name : Type' underlined and NOT bold (§9.8.4, Fig. 9.29-9.32).
    name may be empty (':Type'). slots: 'attribute = value' lines."""
    size = size or FONT_SIZE
    lh = size * 1.25
    head = f"{name} : {type_}" if name else f":{type_}"
    nh = lh + 8
    sh = len(slots) * lh + 6 if slots else 0
    h = nh + sh
    _check_size(f"object {head!r}", w, h)
    box = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Pt(x), Pt(y), Pt(w), Pt(h))
    _plain(box, PAPER, NODE_WIDTH)
    out = [box, _textbox(slide, x, y, w, nh, [(head, {"underline": True})], size, PP_ALIGN.CENTER)]
    if slots:
        out.append(_connector(slide, (x, y + nh), (x + w, y + nh), width=NODE_WIDTH))
        out.append(_textbox(slide, x + 3, y + nh, w - 6, sh, list(slots), size - 1, PP_ALIGN.LEFT))
    return Node("rect", x, y, w, h, out)


def actor(slide, cx, y, name, h=44, size=None):
    """Actor as a stick figure, name below (§18.1.4, Fig. 18.6). Returns a Node around the figure."""
    size = size or FONT_SIZE
    out, r = [], h * 0.14
    head = slide.shapes.add_shape(MSO_SHAPE.OVAL, Pt(cx - r), Pt(y), Pt(2 * r), Pt(2 * r))
    _plain(head, PAPER, NODE_WIDTH)
    out.append(head)
    neck, hip, arm = y + 2 * r, y + h * 0.62, h * 0.30
    for p, q in (((cx, neck), (cx, hip)), ((cx - arm, neck + h * 0.14), (cx + arm, neck + h * 0.14)),
                 ((cx, hip), (cx - arm * 0.8, y + h)), ((cx, hip), (cx + arm * 0.8, y + h))):
        out.append(_connector(slide, p, q, width=NODE_WIDTH))
    tw = _text_w(name, size)
    out.append(label(slide, cx - tw / 2, y + h + 2, tw, size * 1.3 * (name.count("\n") + 1), name, size))
    return Node("rect", cx - arm, y, 2 * arm, h, out)


def actor_box(slide, x, y, w, name, size=None):
    """Actor as a class rectangle with the keyword «actor» (§18.1.4, Fig. 18.7), e.g. for another system."""
    return class_(slide, x, y, w, name, keyword="actor", size=size)


def subject(slide, x, y, w, h, name, size=None):
    """System boundary of a use case diagram: rectangle, name at the top left (§18.1.4, Fig. 18.2)."""
    _check_size(f"subject {name!r}", w, h)
    box = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Pt(x), Pt(y), Pt(w), Pt(h))
    _plain(box, None, NODE_WIDTH)
    _write(box, [(name, {"bold": True})], size or FONT_SIZE, MSO_ANCHOR.TOP, PP_ALIGN.LEFT)
    return Node("rect", x, y, w, h, [box])


def use_case(slide, x, y, w, h, name, size=None):
    """Use case: ellipse with the name inside (§18.1.4)."""
    _check_size(f"use case {name!r}", w, h)
    e = slide.shapes.add_shape(MSO_SHAPE.OVAL, Pt(x), Pt(y), Pt(w), Pt(h))
    _plain(e, PAPER, NODE_WIDTH)
    _write(e, name.split("\n"), size or FONT_SIZE)
    e.text_frame.margin_left = e.text_frame.margin_right = Pt(2)
    return Node("ellipse", x, y, w, h, [e])


def _rounded(slide, x, y, w, h, radius=8):
    b = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Pt(x), Pt(y), Pt(w), Pt(h))
    b.adjustments[0] = min(0.5, radius / min(w, h))
    _plain(b, PAPER, NODE_WIDTH)
    return b


def action(slide, x, y, w, h, name, call=False, size=None):
    """Action: rectangle with rounded corners (§16.2.4.1). call=True adds the rake of a
    CallBehaviorAction in the lower right corner (§16.3.4.1, Fig. 16.15)."""
    _check_size(f"action {name!r}", w, h)
    b = _rounded(slide, x, y, w, h)
    _write(b, name.split("\n"), size or FONT_SIZE)
    out = [b]
    if call:
        rx, ry, s = x + w - 13, y + h - 16, 4.5
        for p, q in (((rx, ry), (rx, ry + s)), ((rx - s, ry + s), (rx + s, ry + s)), ((rx - s, ry + s), (rx - s, ry + 2 * s)),
                     ((rx, ry + s), (rx, ry + 2 * s)), ((rx + s, ry + s), (rx + s, ry + 2 * s))):
            out.append(_connector(slide, p, q, width=NODE_WIDTH))
    return Node("rect", x, y, w, h, out)


def state(slide, x, y, w, h, name, internal=(), size=None):
    """State: rectangle with rounded corners, name inside (§14.2.4.4). internal: lines such as
    'entry / ...', 'do / ...' below a separator."""
    _check_size(f"state {name!r}", w, h)
    size = size or FONT_SIZE
    b = _rounded(slide, x, y, w, h)
    out = [b]
    if not internal:
        _write(b, [name], size)
        return Node("rect", x, y, w, h, out)
    nh = size * 1.25 + 6
    out.append(_textbox(slide, x, y, w, nh, [name], size, PP_ALIGN.CENTER))
    out.append(_connector(slide, (x, y + nh), (x + w, y + nh), width=NODE_WIDTH))
    out.append(_textbox(slide, x + 4, y + nh, w - 8, h - nh, list(internal), size - 1, PP_ALIGN.LEFT))
    return Node("rect", x, y, w, h, out)


def initial(slide, cx, cy, d=12):
    """Initial node / initial pseudostate: small filled circle (§15.3.4.1, §14.2.4.6)."""
    o = slide.shapes.add_shape(MSO_SHAPE.OVAL, Pt(cx - d / 2), Pt(cy - d / 2), Pt(d), Pt(d))
    _plain(o, INK, NODE_WIDTH)
    return Node("ellipse", cx - d / 2, cy - d / 2, d, d, [o])


def activity_final(slide, cx, cy, d=16):
    """Activity final node and final state: circle around a filled circle (§15.3.4.1, Fig. 15.27; §14.2.4.5).
    Ends the whole activity. Not to be confused with flow_final()."""
    o = slide.shapes.add_shape(MSO_SHAPE.OVAL, Pt(cx - d / 2), Pt(cy - d / 2), Pt(d), Pt(d))
    _plain(o, PAPER, NODE_WIDTH)
    i = d * 0.58
    dot = slide.shapes.add_shape(MSO_SHAPE.OVAL, Pt(cx - i / 2), Pt(cy - i / 2), Pt(i), Pt(i))
    _plain(dot, INK, 0, line=False)
    return Node("ellipse", cx - d / 2, cy - d / 2, d, d, [o, dot])


final_state = activity_final


def flow_final(slide, cx, cy, d=16):
    """Flow final node: circle with an X (§15.3.4.1, Fig. 15.28). Ends only this flow."""
    o = slide.shapes.add_shape(MSO_SHAPE.OVAL, Pt(cx - d / 2), Pt(cy - d / 2), Pt(d), Pt(d))
    _plain(o, PAPER, NODE_WIDTH)
    q = d / 2 * 0.707
    return Node("ellipse", cx - d / 2, cy - d / 2, d, d,
                [o, _connector(slide, (cx - q, cy - q), (cx + q, cy + q), width=NODE_WIDTH),
                 _connector(slide, (cx - q, cy + q), (cx + q, cy - q), width=NODE_WIDTH)])


def decision(slide, cx, cy, w=18, h=22):
    """Decision or merge node, choice pseudostate: hollow diamond (§15.3.4.3, §14.2.4.6)."""
    d = slide.shapes.add_shape(MSO_SHAPE.DIAMOND, Pt(cx - w / 2), Pt(cy - h / 2), Pt(w), Pt(h))
    _plain(d, PAPER, NODE_WIDTH)
    return Node("diamond", cx - w / 2, cy - h / 2, w, h, [d])


def bar(slide, cx, cy, length=60, thickness=4, vertical=True):
    """Fork or join node: filled bar (§15.3.4.2, Fig. 15.29)."""
    w, h = (thickness, length) if vertical else (length, thickness)
    b = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Pt(cx - w / 2), Pt(cy - h / 2), Pt(w), Pt(h))
    _plain(b, INK, NODE_WIDTH)
    return Node("rect", cx - w / 2, cy - h / 2, w, h, [b])


def note(slide, x, y, w, h, text, size=None, fold=8):
    """Comment: rectangle with a folded upper right corner (§7.2.4). Attach it with anchor_line()."""
    _check_size("note", w, h)
    s = _polygon(slide, [(x, y), (x + w - fold, y), (x + w, y + fold), (x + w, y + h), (x, y + h)], PAPER)
    out = [s, _connector(slide, (x + w - fold, y), (x + w - fold, y + fold), width=EDGE_WIDTH),
           _connector(slide, (x + w - fold, y + fold), (x + w, y + fold), width=EDGE_WIDTH),
           _textbox(slide, x + 2, y + 2, w - fold - 2, h - 4, text.split("\n"), size or LABEL_SIZE, PP_ALIGN.LEFT)]
    return Node("rect", x, y, w, h, out)


# --------------------------------------------------------- sequence diagram

def lifeline(slide, cx, y, name, bottom, w=None, h=24, size=None):
    """Lifeline: head rectangle with 'name:Type' (NOT underlined, §17.3.4.1, Fig. 17.14) and a dashed line."""
    size = size or FONT_SIZE
    w = w or _text_w(name, size) + 8
    box = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Pt(cx - w / 2), Pt(y), Pt(w), Pt(h))
    _plain(box, PAPER, NODE_WIDTH)
    _write(box, [name], size)
    return Node("rect", cx - w / 2, y, w, h, [box, _connector(slide, (cx, y + h), (cx, bottom), dash=True)])


def comm_lifeline(slide, x, y, name, w=None, h=24, size=None):
    """Lifeline in a communication diagram: plain rectangle with 'name:Type', not underlined, not bold
    (§17.9, Fig. 17.26). Connect two of them with association() (a link) and add communication_message()."""
    size = size or FONT_SIZE
    w = w or _text_w(name, size) + 8
    box = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Pt(x), Pt(y), Pt(w), Pt(h))
    _plain(box, PAPER, NODE_WIDTH)
    _write(box, [name], size)
    return Node("rect", x, y, w, h, [box])


def actor_lifeline(slide, cx, y, name, bottom, h=36, size=None):
    """Lifeline of an actor: stick figure as the head."""
    n = actor(slide, cx, y, name, h=h, size=size)
    top = y + h + (size or FONT_SIZE) * 1.3 + 4
    n.shapes.append(_connector(slide, (cx, top), (cx, bottom), dash=True))
    return n


def activation(slide, cx, y1, y2, w=8):
    """Execution specification: thin white rectangle on the lifeline (§17.2.4.4)."""
    b = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Pt(cx - w / 2), Pt(y1), Pt(w), Pt(y2 - y1))
    _plain(b, PAPER, NODE_WIDTH)
    return b


_MESSAGE = {"sync": (False, "filled"), "async": (False, "open"), "reply": (True, "open"), "create": (True, "open")}


def message(slide, x1, x2, y, name="", kind="sync", size=None, y2=None):
    """Message from x1 to x2 at height y (§17.4.4.1):
    sync   solid line, filled head   (caller waits)
    async  solid line, open head     (caller goes on)
    reply  dashed line, open head    (the spec also allows a filled head; keep one style per diagram)
    create dashed line, open head, ends at the head of the new lifeline"""
    dash, head = _MESSAGE[kind]
    c = _connector(slide, (x1, y), (x2, y if y2 is None else y2), dash=dash)
    _line_end(c, "tail", head)
    out = [c]
    if name:
        size = size or LABEL_SIZE
        w = _text_w(name, size)
        t = label(slide, (x1 + x2) / 2 - w / 2, y - size * 1.35 - 1, w, size * 1.3, name, size)
        t.fill.solid()                     # lifelines crossed by the message stay behind the name
        t.fill.fore_color.rgb = _rgb(PAPER)
        out.append(t)
    return out


def self_message(slide, x, y, name="", dy=14, dx=20, size=None):
    """Synchronous message to the own lifeline: out, down, back with a filled head."""
    a = _connector(slide, (x, y), (x + dx, y))
    b = _connector(slide, (x + dx, y), (x + dx, y + dy))
    c = _connector(slide, (x + dx, y + dy), (x, y + dy))
    _line_end(c, "tail", "filled")
    out = [a, b, c]
    if name:
        size = size or LABEL_SIZE
        out.append(label(slide, x + dx + 4, y, _text_w(name, size), dy, name, size, align=PP_ALIGN.LEFT))
    return out


def fragment(slide, x, y, w, h, operator, size=None):
    """Combined fragment: rectangle with the operator (alt, opt, loop, ref ...) in a pentagon at the top left (§17.6.4)."""
    _check_size(f"fragment {operator!r}", w, h)
    size = size or LABEL_SIZE
    box = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Pt(x), Pt(y), Pt(w), Pt(h))
    _plain(box, None, EDGE_WIDTH)
    tw, th, c = _text_w(operator, size) + 4, size * 1.3 + 3, 4
    tag = _polygon(slide, [(x, y), (x + tw, y), (x + tw, y + th - c), (x + tw - c, y + th), (x, y + th)], PAPER)
    return [box, tag, label(slide, x + 2, y + 1, tw - 4, th - 2, operator, size, bold=True)]


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


def _ray_ellipse(o, d, cx, cy, rx, ry):
    ox, oy = (o[0] - cx) / rx, (o[1] - cy) / ry
    dx, dy = d[0] / rx, d[1] / ry
    a, b, c = dx * dx + dy * dy, 2 * (ox * dx + oy * dy), ox * ox + oy * oy - 1
    disc = b * b - 4 * a * c
    if disc < 0:
        return None
    t = (-b - math.sqrt(disc)) / (2 * a)
    return t if t >= 0 else None


def _ray_segment(o, d, p, q):
    ex, ey = q[0] - p[0], q[1] - p[1]
    den = d[0] * ey - d[1] * ex
    if abs(den) < 1e-12:
        return None
    t = ((p[0] - o[0]) * ey - (p[1] - o[1]) * ex) / den
    s = ((p[0] - o[0]) * d[1] - (p[1] - o[1]) * d[0]) / den
    return t if t >= 0 and 0 <= s <= 1 else None


def _hit(n, o, d):
    """First point of the outline of node n on the ray from o (outside) in unit direction d."""
    if n.shape == "point":
        return n.center
    if n.shape == "ellipse":
        t = _ray_ellipse(o, d, n.cx, n.cy, n.w / 2, n.h / 2)
    elif n.shape == "diamond":
        pts = [(n.cx, n.y), (n.x + n.w, n.cy), (n.cx, n.y + n.h), (n.x, n.cy)]
        ts = [_ray_segment(o, d, pts[k], pts[(k + 1) % 4]) for k in range(4)]
        ts = [t for t in ts if t is not None]
        t = min(ts) if ts else None
    else:
        t = _ray_rect(o, d, n.x, n.y, n.w, n.h)
    return None if t is None else (o[0] + d[0] * t, o[1] + d[1] * t)


def _unit(p, q):
    dx, dy = q[0] - p[0], q[1] - p[1]
    n = math.hypot(dx, dy)
    if n < 1e-9:
        raise ValueError("edge of length zero")
    return (dx / n, dy / n)


def _ends(a, b):
    """End points of a straight edge between a and b (each a Node or an (x, y) point): horizontal or
    vertical where the boxes overlap, otherwise from centre to centre; clipped at the outlines."""
    an, bn = isinstance(a, Node), isinstance(b, Node)
    if not an and not bn:
        return tuple(a), tuple(b)
    if an and bn:
        lo, hi = max(a.y, b.y), min(a.y + a.h, b.y + b.h)
        if hi > lo and (a.x + a.w <= b.x or b.x + b.w <= a.x) and a.shape == b.shape == "rect":
            o = ((a.x + a.w + b.x) / 2 if a.x < b.x else (b.x + b.w + a.x) / 2, (lo + hi) / 2)
            return (_hit(a, o, (math.copysign(1, a.cx - o[0]), 0)), _hit(b, o, (math.copysign(1, b.cx - o[0]), 0)))
        lo, hi = max(a.x, b.x), min(a.x + a.w, b.x + b.w)
        if hi > lo and (a.y + a.h <= b.y or b.y + b.h <= a.y) and a.shape == b.shape == "rect":
            o = ((lo + hi) / 2, (a.y + a.h + b.y) / 2 if a.y < b.y else (b.y + b.h + a.y) / 2)
            return (_hit(a, o, (0, math.copysign(1, a.cy - o[1]))), _hit(b, o, (0, math.copysign(1, b.cy - o[1]))))
        return (_hit(a, b.center, _unit(b.center, a.center)) or a.center,
                _hit(b, a.center, _unit(a.center, b.center)) or b.center)
    node, p = (a, tuple(b)) if an else (b, tuple(a))
    if node.shape == "rect" and node.y < p[1] < node.y + node.h:
        d = (math.copysign(1, node.cx - p[0]), 0)
    elif node.shape == "rect" and node.x < p[0] < node.x + node.w:
        d = (0, math.copysign(1, node.cy - p[1]))
    else:
        d = _unit(p, node.center)
    q = _hit(node, p, d) or node.center
    return (q, p) if an else (p, q)


def _route(a, b, via):
    """Polyline points from a to b through via, end points clipped at the outlines."""
    if not via:
        p, q = _ends(a, b)
        return [p, q]
    p, _ = _ends(a, via[0])
    _, q = _ends(via[-1], b)
    return [p] + [tuple(v) for v in via] + [q]


# ------------------------------------------------------------------ edges

def edge(slide, a, b, via=(), dash=False, start=None, end=None):
    """Generic edge as one connector per segment. start/end: None, "open", "filled",
    "triangle" (hollow), "diamond" (hollow), "filled_diamond", "x". Returns the shapes."""
    pts = _route(a, b, via)
    p0, p1 = pts[0], pts[1]
    q0, q1 = pts[-2], pts[-1]
    deco = []
    # shorten the line under a hollow or filled shape at the ends
    if start in ("triangle", "diamond", "filled_diamond"):
        u = _unit(p0, p1)
        L = TRIANGLE[0] if start == "triangle" else DIAMOND[0]
        deco += _end_shape(slide, p0, (-u[0], -u[1]), start)
        pts[0] = (p0[0] + u[0] * L, p0[1] + u[1] * L)
    if end in ("triangle", "diamond", "filled_diamond"):
        u = _unit(q0, q1)
        L = TRIANGLE[0] if end == "triangle" else DIAMOND[0]
        deco += _end_shape(slide, q1, u, end)
        pts[-1] = (q1[0] - u[0] * L, q1[1] - u[1] * L)
    segs = [_connector(slide, pts[k], pts[k + 1], dash=dash) for k in range(len(pts) - 1)]
    if start in ("open", "filled"):
        _line_end(segs[0], "head", start)
    if end in ("open", "filled"):
        _line_end(segs[-1], "tail", end)
    if start == "x":
        deco += _x_mark(slide, p0, _unit(p0, p1))
    if end == "x":
        deco += _x_mark(slide, q1, _unit(q1, q0))
    return segs + deco


def _end_shape(slide, tip, u, kind):
    """Hollow triangle or diamond whose tip touches `tip`; u points from the line into the tip."""
    n = (-u[1], u[0])
    if kind == "triangle":
        L, W = TRIANGLE
        base = (tip[0] - u[0] * L, tip[1] - u[1] * L)
        pts = [tip, (base[0] + n[0] * W / 2, base[1] + n[1] * W / 2), (base[0] - n[0] * W / 2, base[1] - n[1] * W / 2)]
        return [_polygon(slide, pts, PAPER)]
    L, W = DIAMOND
    mid = (tip[0] - u[0] * L / 2, tip[1] - u[1] * L / 2)
    pts = [tip, (mid[0] + n[0] * W / 2, mid[1] + n[1] * W / 2), (tip[0] - u[0] * L, tip[1] - u[1] * L),
           (mid[0] - n[0] * W / 2, mid[1] - n[1] * W / 2)]
    return [_polygon(slide, pts, INK if kind == "filled_diamond" else PAPER)]


def _x_mark(slide, end, u, dist=9, s=3.5):
    """Small x across the line near an association end: not navigable (§11.5.4, Fig. 11.29)."""
    c = (end[0] + u[0] * dist, end[1] + u[1] * dist)
    n = (-u[1], u[0])
    a = ((u[0] + n[0]) * s, (u[1] + n[1]) * s)
    b = ((u[0] - n[0]) * s, (u[1] - n[1]) * s)
    return [_connector(slide, (c[0] - a[0], c[1] - a[1]), (c[0] + a[0], c[1] + a[1])),
            _connector(slide, (c[0] - b[0], c[1] - b[1]), (c[0] + b[0], c[1] + b[1]))]


def _end_labels(slide, pts, at_start, above, below, size):
    """Multiplicity above and role name below the line, close to one end."""
    out = []
    p, q = (pts[0], pts[1]) if at_start else (pts[-1], pts[-2])
    u = _unit(p, q)
    horizontal = abs(u[0]) >= abs(u[1])
    for text, side in ((above, -1), (below, 1)):
        if not text:
            continue
        w, h = _text_w(text, size), size * 1.3
        bx, by = p[0] + u[0] * 12, p[1] + u[1] * 12
        if horizontal:
            x = bx if u[0] > 0 else bx - w
            y = by - h - 1 if side < 0 else by + 1
            align = PP_ALIGN.LEFT if u[0] > 0 else PP_ALIGN.RIGHT
        else:
            x = bx + 3 if side < 0 else bx - w - 3
            y = by if u[1] > 0 else by - h
            align = PP_ALIGN.LEFT if side < 0 else PP_ALIGN.RIGHT
        out.append(label(slide, x, y, w, h, text, size, align=align))
    return out


_END = {None: None, "unspecified": None, "navigable": "open", "x": "x"}


def association(slide, a, b, a_end=None, b_end=None, via=(), name=None,
                a_mult=None, b_mult=None, a_role=None, b_role=None, size=None):
    """Association: solid line (§11.5.4). Per end: None = navigability unspecified (no mark),
    "navigable" = open head, "x" = not navigable. Both ends navigable: give both "navigable" (two heads).
    Multiplicity above the line, role name below, at the end they belong to."""
    shapes = edge(slide, a, b, via, start=_END[a_end], end=_END[b_end])
    pts = _route(a, b, via)
    size = size or LABEL_SIZE
    shapes += _end_labels(slide, pts, True, a_mult, a_role, size)
    shapes += _end_labels(slide, pts, False, b_mult, b_role, size)
    if name:
        shapes.append(_mid_label(slide, pts, name, size))
    return shapes


def link(slide, a, b, via=(), a_role=None, b_role=None, size=None):
    """Link between two objects: solid line, usually without heads (§9.8.4, Fig. 9.30)."""
    return association(slide, a, b, via=via, a_role=a_role, b_role=b_role, size=size)


def _mid_label(slide, pts, text, size, side=-1):
    k = (len(pts) - 1) // 2
    p, q = pts[k], pts[k + 1]
    m = ((p[0] + q[0]) / 2, (p[1] + q[1]) / 2)
    w, h = _text_w(text, size), size * 1.3
    if abs(q[0] - p[0]) >= abs(q[1] - p[1]):
        return label(slide, m[0] - w / 2, m[1] - h - 1 if side < 0 else m[1] + 1, w, h, text, size)
    return label(slide, m[0] + 4, m[1] - h / 2, w, h, text, size, align=PP_ALIGN.LEFT)


def dependency(slide, client, supplier, keyword=None, via=(), size=None):
    """Dependency: dashed line, open head at the supplier (§7.7.4, Fig. 7.18). keyword e.g. "use"."""
    shapes = edge(slide, client, supplier, via, dash=True, end="open")
    if keyword:
        shapes.append(_mid_label(slide, _route(client, supplier, via), "«" + keyword + "»", size or LABEL_SIZE))
    return shapes


def generalization(slide, specific, general, via=()):
    """Generalization: solid line, hollow triangle at the general classifier (§9.2.4.2)."""
    return edge(slide, specific, general, via, end="triangle")


def realization(slide, implementing, contract, via=()):
    """Realization / interface realization: dashed line, hollow triangle at the interface (§7.7.4, §10.4.4)."""
    return edge(slide, implementing, contract, via, dash=True, end="triangle")


def aggregation(slide, whole, part, part_navigable=False, via=(), whole_mult=None, part_mult=None,
                part_role=None, size=None):
    """Shared aggregation: hollow diamond at the WHOLE (§11.5.4)."""
    shapes = edge(slide, whole, part, via, start="diamond", end="open" if part_navigable else None)
    pts = _route(whole, part, via)
    size = size or LABEL_SIZE
    pts0 = _shift_start(pts, DIAMOND[0])
    return shapes + _end_labels(slide, pts0, True, whole_mult, None, size) + \
        _end_labels(slide, pts, False, part_mult, part_role, size)


def composition(slide, whole, part, part_navigable=False, via=(), whole_mult=None, part_mult=None,
                part_role=None, size=None):
    """Composite aggregation: filled diamond at the WHOLE (§11.5.4)."""
    shapes = edge(slide, whole, part, via, start="filled_diamond", end="open" if part_navigable else None)
    pts = _route(whole, part, via)
    size = size or LABEL_SIZE
    pts0 = _shift_start(pts, DIAMOND[0])
    return shapes + _end_labels(slide, pts0, True, whole_mult, None, size) + \
        _end_labels(slide, pts, False, part_mult, part_role, size)


def _shift_start(pts, d):
    u = _unit(pts[0], pts[1])
    return [(pts[0][0] + u[0] * d, pts[0][1] + u[1] * d)] + pts[1:]


def flow(slide, a, b, via=(), guard=None, size=None):
    """Activity edge (control or object flow) or state transition: solid line, open head (§15.2.4, §14.2.4.8).
    guard / transition label 'trigger [guard] / effect' is written near the start of the line."""
    shapes = edge(slide, a, b, via, end="open")
    if guard:
        size = size or LABEL_SIZE
        pts = _route(a, b, via)
        p, q = pts[0], pts[1]
        u = _unit(p, q)
        w, h = _text_w(guard, size), size * 1.3 * (guard.count("\n") + 1)
        if abs(u[0]) >= abs(u[1]):
            x = p[0] + 4 if u[0] > 0 else p[0] - 4 - w
            shapes.append(label(slide, x, p[1] - h - 1, w, h, guard, size,
                                align=PP_ALIGN.LEFT if u[0] > 0 else PP_ALIGN.RIGHT))
        else:
            y = p[1] + 2 if u[1] > 0 else p[1] - h - 2
            shapes.append(label(slide, p[0] + 4, y, w, h, guard, size, align=PP_ALIGN.LEFT))
    return shapes


transition = flow


def include(slide, base, included, size=None):
    """«include»: dashed, open head, from the base use case to the included one (§18.1.4, Fig. 18.4)."""
    return dependency(slide, base, included, keyword="include", size=size)


def extend(slide, extension, extended, size=None):
    """«extend»: dashed, open head, from the extending use case to the extended one (§18.1.4, Fig. 18.3)."""
    return dependency(slide, extension, extended, keyword="extend", size=size)


def communication_message(slide, a, b, text, at=0.5, offset=8, length=26, size=None, reverse=False):
    """Message in a communication diagram: small arrow with an open head parallel to the link,
    sequence number and name beside it (§17.4.4.1, Fig. 17.26)."""
    p, q = _ends(a, b)
    if reverse:
        p, q = q, p
    u = _unit(p, q)
    n = (u[1], -u[0])                                   # left of the direction on screen
    m = (p[0] + (q[0] - p[0]) * at + n[0] * offset, p[1] + (q[1] - p[1]) * at + n[1] * offset)
    c = _connector(slide, (m[0] - u[0] * length / 2, m[1] - u[1] * length / 2),
                   (m[0] + u[0] * length / 2, m[1] + u[1] * length / 2))
    _line_end(c, "tail", "open")
    size = size or LABEL_SIZE
    w, h = _text_w(text, size), size * 1.3
    t = label(slide, m[0] - w / 2 + n[0] * (h / 2 + 6), m[1] - h / 2 + n[1] * (h / 2 + 6), w, h, text, size)
    return [c, t]


def group(slide, *items):
    """Group nodes and edges into one PowerPoint group."""
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
    file), line ends that have no meaning in UML (stealth, diamond, oval: draw diamonds and hollow
    triangles as shapes), and open and filled heads of different size on one slide."""
    prs = Presentation(pptx_path)
    a = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
    findings = []
    for idx, slide in enumerate(prs.slides, 1):
        for el in slide._element.iter(a + "ext"):
            if int(el.get("cx", 0)) < 0 or int(el.get("cy", 0)) < 0:
                findings.append({"slide": idx, "rule": "negative-size", "detail": f"cx={el.get('cx')} cy={el.get('cy')}"})
        sizes = {}
        for tag in ("headEnd", "tailEnd"):
            for el in slide._element.iter(a + tag):
                typ = el.get("type", "none")
                if typ in ("none",):
                    continue
                if typ not in ("arrow", "triangle"):
                    findings.append({"slide": idx, "rule": "non-uml-line-end",
                                     "detail": f"{tag} type={typ}; UML uses arrow (open) or triangle (filled), "
                                               "hollow triangles and diamonds are separate shapes"})
                    continue
                sizes.setdefault(typ, set()).add((el.get("w", "med"), el.get("len", "med")))
        if "arrow" in sizes and "triangle" in sizes and sizes["arrow"] != sizes["triangle"]:
            findings.append({"slide": idx, "rule": "head-size-mismatch",
                             "detail": f"open heads {sorted(sizes['arrow'])} vs filled heads {sorted(sizes['triangle'])}; "
                                       "give both the same w and len"})
    return findings


# ------------------------------------------------------------------- demo

SOURCE = ("Notation: OMG UML 2.5.1 (formal/17-12-05), https://www.omg.org/spec/UML/2.5.1. "
          "Drawn with uml_pptx.py (koppor-skills, MIT).")


def _title(slide, text):
    label(slide, 40, 18, 880, 30, text, 24, align=PP_ALIGN.LEFT, bold=True)
    label(slide, 40, 512, 880, 14, SOURCE, 8, align=PP_ALIGN.LEFT)


def demo(out_path):
    prs = new_presentation()
    props = prs.core_properties
    props.title, props.author, props.last_modified_by = "UML 2.5.1 notation examples", "uml_pptx.py", "uml_pptx.py"
    props.keywords = "UML, class diagram, sequence diagram, activity diagram, state machine, use case"

    # 1 --- class diagram edges
    s = blank_slide(prs)
    _title(s, "UML class diagram: relationships")
    rows = [
        ("Association, navigability unspecified", lambda a, b: association(s, a, b)),
        ("Association, navigable to B (open head)", lambda a, b: association(s, a, b, b_end="navigable")),
        ("Association, navigable both ways (two heads)", lambda a, b: association(s, a, b, "navigable", "navigable")),
        ("A end not navigable (x), B end navigable", lambda a, b: association(s, a, b, "x", "navigable")),
        ("Dependency «use»: dashed, open head", lambda a, b: dependency(s, a, b, "use")),
        ("Generalization: A is a B (hollow triangle)", lambda a, b: generalization(s, a, b)),
        ("Realization: A implements B (dashed, hollow triangle)", lambda a, b: realization(s, a, b)),
        ("Aggregation: hollow diamond at the whole A", lambda a, b: aggregation(s, a, b)),
        ("Composition: filled diamond at the whole A", lambda a, b: composition(s, a, b, whole_mult="1", part_mult="*")),
    ]
    for k, (text, draw) in enumerate(rows):
        y = 64 + k * 48
        a, b = class_(s, 40, y, 60, "A"), class_(s, 250, y, 60, "B")
        draw(a, b)
        label(s, 330, y, 600, 26, text, 14, align=PP_ALIGN.LEFT)

    # 2 --- class and object diagram
    s = blank_slide(prs)
    _title(s, "UML class diagram and object diagram")
    prac = class_(s, 40, 70, 250, "Practice", ["- name: String"], ["+ book(p: Patient): Appointment"])
    appt = class_(s, 380, 70, 200, "Appointment", ["- start: LocalDateTime", "- free: Boolean = true"], ["+ cancel()"])
    pat = class_(s, 720, 80, 110, "Patient")
    person = class_(s, 720, 180, 110, "Person", abstract=True)
    notif = interface(s, 380, 230, 200, "Notifier", ["+ send(text: String)"])
    mail = class_(s, 350, 340, 110, "MailNotifier")
    sms = class_(s, 500, 340, 110, "SmsNotifier")
    composition(s, prac, appt, whole_mult="1", part_mult="*")
    association(s, appt, pat, b_end="navigable", a_mult="*", b_mult="0..1", b_role="patient")
    generalization(s, pat, person)
    dependency(s, appt, notif, "use")
    realization(s, mail, (mail.cx, notif.y + notif.h))
    realization(s, sms, (sms.cx, notif.y + notif.h))
    label(s, 40, 420, 300, 20, "Objects (underlined, not bold):", 12, align=PP_ALIGN.LEFT)
    o1 = object_(s, 40, 446, 160, "p", "Practice", ['name = "Riverside"'])
    o2 = object_(s, 300, 446, 160, "a1", "Appointment", ["free = false"])
    o3 = object_(s, 560, 452, 100, "", "Patient")
    link(s, o1, o2)
    link(s, o2, o3, b_role="patient")

    # 3 --- sequence diagram
    s = blank_slide(prs)
    _title(s, "UML sequence diagram")
    bottom = 470
    actor_lifeline(s, 90, 64, "Patient", bottom)
    svc = lifeline(s, 330, 70, ":BookingService", bottom)
    mailer = lifeline(s, 760, 70, ":MailNotifier", bottom)
    activation(s, 330, 150, 440)
    message(s, 90, 326, 150, "book(slot)", "sync")
    self_message(s, 334, 180, "reserve(slot)")
    b = lifeline(s, 560, 222, "b:Booking", bottom)
    message(s, 334, b.x, 234, "new", "create")
    fragment(s, 250, 290, 600, 90, "opt")
    label(s, 340, 300, 200, 14, "[mail address known]", LABEL_SIZE, align=PP_ALIGN.LEFT)
    message(s, 334, 760, 350, "confirm(b)", "async")
    message(s, 326, 90, 440, "book: b", "reply")
    label(s, 40, 486, 880, 18, "Filled head: synchronous. Open head: asynchronous. Dashed: reply or create. "
          "Lifeline heads are not underlined.", 11, align=PP_ALIGN.LEFT)

    # 4 --- activity diagram and state machine
    s = blank_slide(prs)
    _title(s, "UML activity diagram and state machine")
    i = initial(s, 50, 120)
    srch = action(s, 80, 100, 110, 40, "Search free\nslots")
    d = decision(s, 230, 120)
    ch = action(s, 280, 64, 110, 32, "Choose slot")
    nt = action(s, 280, 200, 110, 32, "Show notice")
    ff = flow_final(s, 440, 216)
    f = bar(s, 440, 130, 110)
    rs = action(s, 480, 86, 130, 36, "Reserve slot", call=True)
    sm = action(s, 480, 142, 130, 32, "Send mail")
    j = bar(s, 650, 130, 110)
    af = activity_final(s, 690, 130)
    flow(s, i, srch)
    flow(s, srch, d)
    flow(s, (d.cx, d.y), ch, via=[(d.cx, ch.cy)], guard="[found]")
    flow(s, (d.cx, d.y + d.h), nt, via=[(d.cx, nt.cy)], guard="[else]")
    flow(s, nt, ff)
    flow(s, ch, (f.x, ch.cy))
    flow(s, (f.x + f.w, rs.cy), rs)
    flow(s, (f.x + f.w, sm.cy), sm)
    flow(s, rs, (j.x, rs.cy))
    flow(s, sm, (j.x, sm.cy))
    flow(s, j, af)
    label(s, 710, 122, 220, 16, "activity final: ends the activity", 10, align=PP_ALIGN.LEFT)
    label(s, 460, 208, 220, 16, "flow final: ends this flow only", 10, align=PP_ALIGN.LEFT)

    si = initial(s, 50, 330)
    fr = state(s, 90, 310, 100, 40, "free")
    bk = state(s, 400, 300, 170, 60, "booked", ["entry / send confirmation"])
    fs = final_state(s, 720, 330)
    transition(s, si, fr)
    transition(s, fr, (bk.x, 330), guard="book(p) [p.registered] / reserve")
    transition(s, (bk.cx, bk.y + bk.h), (fr.cx, fr.y + fr.h), via=[(bk.cx, 410), (fr.cx, 410)])
    label(s, 260, 412, 120, 14, "cancel", LABEL_SIZE)
    transition(s, bk, fs, guard="after 1 day")

    # 5 --- use case and communication diagram
    s = blank_slide(prs)
    _title(s, "UML use case diagram and communication diagram")
    subject(s, 180, 70, 450, 230, "Booking app")
    p = actor(s, 90, 120, "Patient")
    uc1 = use_case(s, 220, 110, 150, 56, "Book\nappointment")
    uc2 = use_case(s, 450, 110, 150, 56, "Identify\npatient")
    uc3 = use_case(s, 220, 220, 150, 56, "Send SMS\nreminder")
    gw = actor_box(s, 720, 230, 140, "SMS gateway")
    association(s, p, uc1)
    include(s, uc1, uc2)
    extend(s, uc3, uc1)
    association(s, uc3, gw)
    c1 = comm_lifeline(s, 120, 400, ":BookingService")
    c2 = comm_lifeline(s, 520, 400, ":MailNotifier")
    association(s, c1, c2)
    communication_message(s, c1, c2, "1: confirm(b)")
    label(s, 40, 460, 880, 30, "Communication diagram: link between lifelines (not underlined), small open arrow "
          "with sequence number beside it.", 11, align=PP_ALIGN.LEFT)

    prs.save(out_path)
    return out_path


def main(argv):
    if len(argv) == 3 and argv[1] == "demo":
        print(demo(argv[2]))
        return 0
    if len(argv) == 3 and argv[1] == "check":
        findings = check(argv[2])
        print(json.dumps({"file": argv[2], "findings": findings}, indent=2))
        return 1 if findings else 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
