#!/usr/bin/env python3
"""tgml_preview.py - render a TGML graphic as SVG (and PNG with headless Chrome) to check a layout offline.

    python3 tgml_preview.py AHU01-HMI.tgml out.svg [--open] [--png out.png] [--crop x,y,w,h] [--scale 2]

Reads Rectangle, Line, Ellipse, Polygon, Path, Text and Component (offset and scaling, Clip). Live texts show a
sample ("-88.8 °C" with the decimals and unit of their script, the longer word of a state), so their widths can be
checked. Groups that start hidden (the info popups) are drawn only with --open; blink overlays are not drawn.
Animations, binds and scripts are ignored. Not a faithful EBO renderer: fonts and text metrics are approximate.
"""
import re, sys, subprocess, os, xml.etree.ElementTree as ET
from xml.sax.saxutils import escape

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"


def colour(v):
    return "none" if v in (None, "None", "Transparent") else v


def sample_text(e):
    """Text content of a TGML Text, with a sample for a bound one."""
    bind = e.find("Bind")
    if bind is None:
        return e.text or ""
    s = bind.find("Script")
    code = s.text if s is not None else ""
    m = re.search(r'toFixed\((\d+)\)\+"([^"]*)"', code)
    if m:
        d = int(m.group(1)); unit = m.group(2).encode().decode("unicode_escape") if "\\" in m.group(2) else m.group(2)
        return ("-88." + "8" * d if d else "-888") + unit
    m = re.search(r'v>=1\?"([^"]*)":"([^"]*)"', code)
    if m:
        return max(m.group(1), m.group(2), key=len)
    m = re.search(r'var w=\[([^\]]*)\]', code)
    if m:
        return max(re.findall(r'"([^"]*)"', m.group(1)), key=len)
    return (bind.tail or "").strip() or "--"


class Conv:
    def __init__(self, show_open):
        self.show_open, self.out, self.nclip = show_open, [], 0

    def el(self, e):
        tag = e.tag; a = e.attrib; o = self.out
        if a.get("Visibility") == "Hidden" and not (self.show_open and tag == "Group"):
            return
        if tag == "Rectangle":
            o.append(f'<rect x="{a["Left"]}" y="{a["Top"]}" width="{a["Width"]}" height="{a["Height"]}" '
                     f'rx="{a.get("RadiusX", 0)}" fill="{colour(a.get("Fill"))}" stroke="{colour(a.get("Stroke"))}" '
                     f'stroke-width="{a.get("StrokeWidth", 1)}"/>')
        elif tag == "Line":
            o.append(f'<line x1="{a["X1"]}" y1="{a["Y1"]}" x2="{a["X2"]}" y2="{a["Y2"]}" stroke="{colour(a.get("Stroke"))}" '
                     f'stroke-width="{a.get("StrokeWidth", 1)}"/>')
        elif tag == "Ellipse":
            w, h = float(a["Width"]), float(a["Height"])
            o.append(f'<ellipse cx="{float(a["Left"]) + w / 2}" cy="{float(a["Top"]) + h / 2}" rx="{w / 2}" ry="{h / 2}" '
                     f'fill="{colour(a.get("Fill"))}" stroke="{colour(a.get("Stroke"))}" stroke-width="{a.get("StrokeWidth", 1)}"/>')
        elif tag == "Polygon":
            o.append(f'<polygon points="{a["Points"]}" fill="{colour(a.get("Fill"))}" stroke="{colour(a.get("Stroke"))}" '
                     f'stroke-width="{a.get("StrokeWidth", 1)}"/>')
        elif tag == "Path":
            o.append(f'<path d="{a["PathData"]}" fill="{colour(a.get("Fill"))}" stroke="{colour(a.get("Stroke"))}" '
                     f'stroke-width="{a.get("StrokeWidth", 1)}"/>')
        elif tag == "Text":
            size = float(a.get("FontSize", 12))
            anchor = {"Center": "middle", "Right": "end"}.get(a.get("HorizontalAlign"), "start")
            o.append(f'<text x="{a["Left"]}" y="{float(a["Top"]) + size * 0.9:.1f}" font-family="Arial" '
                     f'font-size="{size}" font-weight="{"bold" if a.get("FontWeight") == "Bold" else "normal"}" '
                     f'text-anchor="{anchor}" fill="{colour(a.get("Stroke"))}">{escape(sample_text(e))}</text>')
        elif tag == "Component":
            x, y = float(a.get("Left", 0)), float(a.get("Top", 0))
            cw, ch = float(a.get("ContentWidth", 1)), float(a.get("ContentHeight", 1))
            sx, sy = float(a.get("Width", cw)) / cw, float(a.get("Height", ch)) / ch
            clip = ""
            if a.get("Clip") == "True":
                self.nclip += 1
                o.append(f'<clipPath id="c{self.nclip}"><rect x="0" y="0" width="{cw}" height="{ch}"/></clipPath>')
                clip = f' clip-path="url(#c{self.nclip})"'
            o.append(f'<g transform="translate({x},{y}) scale({sx},{sy})"><g{clip}>')
            for c in e:
                self.el(c)
            o.append('</g></g>')
        elif tag in ("Group", "Layer"):
            o.append('<g>')
            for c in e:
                self.el(c)
            o.append('</g>')
        # Bind, Script, Animate, Rotate, Translate, ConvertValue: no picture


def convert(src, dst, show_open=False, crop=None):
    root = ET.parse(src).getroot()
    w, h = root.get("Width"), root.get("Height")
    vb = crop or (0, 0, w, h)
    c = Conv(show_open)
    for e in root:
        c.el(e)
    with open(dst, "w", encoding="utf-8") as f:
        f.write(f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="{" ".join(map(str, vb))}" '
                f'preserveAspectRatio="xMinYMin meet"><rect width="100%" height="100%" fill="{root.get("Background", "#fff")}"/>'
                + "\n".join(c.out) + '</svg>\n')
    return int(float(w)), int(float(h))


def png(svg, out, w, h, scale=1):
    subprocess.run([CHROME, "--headless", "--disable-gpu", "--hide-scrollbars", f"--force-device-scale-factor={scale}",
                    f"--screenshot={out}", f"--window-size={w},{h}", "file://" + os.path.abspath(svg)],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


if __name__ == "__main__":
    args = sys.argv[1:]
    src, dst = args[0], args[1]
    crop = None
    if "--crop" in args:
        crop = [float(v) for v in args[args.index("--crop") + 1].split(",")]
    w, h = convert(src, dst, "--open" in args, crop)
    if "--png" in args:
        scale = float(args[args.index("--scale") + 1]) if "--scale" in args else 1
        png(dst, args[args.index("--png") + 1], w, h, scale)
