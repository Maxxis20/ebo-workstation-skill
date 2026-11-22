#!/usr/bin/env python3
"""tgml.py - write an EBO graphic (TGML) from Python: static shapes, live values, state colours, click-to-change.

    g = Graphic(1000, 620)
    g.text(20, 20, "Boiler room", size=20, bold=True)
    g.value(120, 60, "TE1", decimals=1, unit="\xb0C")        # bind name TE1, bound later in WorkStation
    g.lamp(40, 60, "P1_RUN")                                 # grey / green by a binary
    g.save("x.tgml"); g.binds  -> names to bind

Element and script forms are taken from the components shipped with the Graphics Editor
(reference/findings.md, "Graphics"). A bound text opens WorkStation's change-value dialog when clicked.
"""
from xml.sax.saxutils import escape

FONT = "Arial"


class Graphic:
    def __init__(self, width, height, background="#F4F5F7"):
        self.w, self.h, self.bg = width, height, background
        self.items, self.binds = [], []
        self.top = []                                           # drawn last, over everything: info boxes

    def _bind(self, name):
        if name not in self.binds:
            self.binds.append(name)

    # --- static -------------------------------------------------------------------------------------
    def rect(self, x, y, w, h, fill="#FFFFFF", stroke="#9AA0A6", sw=1, radius=0, alt=None):
        """alt=(signal, colour): the fill becomes that colour while the signal is 1 or more (also on airflow, drum)."""
        inner = self._fill_bind(alt[0], alt[1], fill) if alt else ""
        self.items.append(f'<Rectangle Fill="{fill}" Height="{h}" Left="{x}" RadiusX="{radius}" RadiusY="{radius}" '
                          f'Stroke="{stroke}" StrokeWidth="{sw}" Top="{y}" Width="{w}">{inner}</Rectangle>')

    def _alt(self, alt, base, attribute="Stroke"):
        if not alt:
            return ""
        self._bind(alt[0])
        return (f'<Bind Attribute="{attribute}" Name="{alt[0]}"><ConvertValue AttributeValue="{base}" '
                f'SignalLessOrEqualTo="0"/><ConvertValue AttributeValue="{alt[1]}" SignalMoreOrEqualTo="1"/></Bind>')

    def line(self, x1, y1, x2, y2, stroke="#444444", sw=2):
        self.items.append(f'<Line Stroke="{stroke}" StrokeWidth="{sw}" X1="{x1}" X2="{x2}" Y1="{y1}" Y2="{y2}"/>')

    def pipe(self, pts, colour, sw=6):
        for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
            self.line(x1, y1, x2, y2, colour, sw)

    def text(self, x, y, s, size=13, bold=False, colour="#202124", align="Left"):
        self.items.append(f'<Text FontFamily="{FONT}" FontSize="{size}" FontWeight="{"Bold" if bold else "Normal"}" '
                          f'HorizontalAlign="{align}" Left="{x}" Stroke="{colour}" Top="{y}">{escape(s)}</Text>')

    def polygon(self, pts, fill="#FFFFFF", stroke="#444444", sw=1.5, bind=None, on="#1E8E3E", off="#BDC1C6"):
        p = " ".join(f"{x},{y}" for x, y in pts)
        inner = self._fill_bind(bind, on, off) if bind else ""
        self.items.append(f'<Polygon Fill="{fill}" Points="{p}" Stroke="{stroke}" StrokeWidth="{sw}">{inner}</Polygon>')

    # --- live ---------------------------------------------------------------------------------------
    def _fill_bind(self, name, on, off):
        self._bind(name)
        return (f'<Bind Attribute="Fill" Name="{name}"><ConvertValue AttributeValue="{off}" SignalLessOrEqualTo="0"/>'
                f'<ConvertValue AttributeValue="{on}" SignalMoreOrEqualTo="1"/></Bind>')

    def value(self, x, y, name, decimals=1, unit="", size=15, colour="#0B57D0", bold=True, align="Left"):
        """Number that follows a value. Click it in WorkStation to change the value (if it is writable)."""
        self._bind(name)
        u = (" " + unit).replace("\\", "\\\\").replace('"', '\\"') if unit else ""
        self.items.append(
            f'<Text FontFamily="{FONT}" FontSize="{size}" FontWeight="{"Bold" if bold else "Normal"}" '
            f'HorizontalAlign="{align}" Left="{x}" Stroke="{colour}" Top="{y}"><Bind Name="{name}">'
            f'<Script OnSignalChange="signal"><![CDATA[function signal(evt){{var t=evt.getTarget().getParentNode();'
            f'var v=new Number(evt.getValue());t.setAttribute("Content",v.toFixed({decimals})+"{u}");}}]]></Script>'
            f'</Bind>--</Text>')

    def state(self, x, y, name, on_text, off_text, size=13, on="#1E8E3E", off="#5F6368"):
        """Text that shows one of two words by a binary."""
        self._bind(name)
        self.items.append(
            f'<Text FontFamily="{FONT}" FontSize="{size}" FontWeight="Bold" Left="{x}" Stroke="{off}" Top="{y}">'
            f'<Bind Name="{name}"><Script OnSignalChange="signal"><![CDATA[function signal(evt){{'
            f'var t=evt.getTarget().getParentNode();var v=new Number(evt.getValue());'
            f't.setAttribute("Content",v>=1?"{on_text}":"{off_text}");t.setAttribute("Stroke",v>=1?"{on}":"{off}");'
            f'}}]]></Script></Bind>--</Text>')

    def lamp(self, x, y, name, d=18, on="#1E8E3E", off="#BDC1C6"):
        self.items.append(f'<Ellipse Fill="{off}" Height="{d}" Left="{x}" Stroke="#5F6368" StrokeWidth="1" Top="{y}" '
                          f'Width="{d}">{self._fill_bind(name, on, off)}</Ellipse>')

    def pump(self, x, y, name, d=44, left=False, direction=None):
        """Circle with a triangle that shows the flow direction: direction "right" (default), "left", "up" or "down"
        (left=True is the older way to say "left"). Colour by the value: 0 grey (stopped), 1 green (running), 2 and
        above red (fault). A plain binary gives grey / green."""
        self._bind(name)
        self.items.append(f'<Ellipse Fill="#BDC1C6" Height="{d}" Left="{x}" Stroke="#3C4043" StrokeWidth="2" Top="{y}" '
                          f'Width="{d}"><Bind Attribute="Fill" Name="{name}">'
                          f'<ConvertValue AttributeValue="#BDC1C6" SignalLessOrEqualTo="0"/>'
                          f'<ConvertValue AttributeValue="#34A853" SignalEqualTo="1"/>'
                          f'<ConvertValue AttributeValue="#D93025" SignalMoreOrEqualTo="2"/></Bind></Ellipse>')
        c = d / 2; a, b, w = d * 0.18, d * 0.27, d * 0.25           # back of the arrow, its tip, half its width
        direction = direction or ("left" if left else "right")
        k = -1 if direction in ("left", "up") else 1
        if direction in ("left", "right"):
            pts = [(x + c - a * k, y + c - w), (x + c + b * k, y + c), (x + c - a * k, y + c + w)]
        else:
            pts = [(x + c - w, y + c - a * k), (x + c, y + c + b * k), (x + c + w, y + c - a * k)]
        self.polygon(pts, fill="#FFFFFF", stroke="#3C4043")

    def valve(self, x, y, s=18):
        """Two-way valve symbol centred on (x, y), with an actuator box on top."""
        self.polygon([(x - s, y - s * 0.7), (x, y), (x - s, y + s * 0.7)], fill="#FFFFFF")
        self.polygon([(x + s, y - s * 0.7), (x, y), (x + s, y + s * 0.7)], fill="#FFFFFF")
        self.line(x, y, x, y - s * 1.2, "#444444", 2)
        self.rect(x - s * 0.6, y - s * 2.0, s * 1.2, s * 0.8, fill="#E8EAED", stroke="#444444")

    def bar(self, x, y, name, w=120, h=10, full=100.0, colour="#F29900"):
        """Horizontal bar, 0 .. full of the value = 0 .. w wide."""
        self._bind(name)
        self.rect(x, y, w, h, fill="#FFFFFF", stroke="#9AA0A6")
        self.items.append(
            f'<Rectangle Fill="{colour}" Height="{h}" Left="{x}" Stroke="None" Top="{y}" Width="1"><Bind Name="{name}">'
            f'<Script OnSignalChange="signal"><![CDATA[function signal(evt){{var r=evt.getTarget().getParentNode();'
            f'var v=new Number(evt.getValue());if(v<0)v=0;if(v>{full})v={full};'
            f'r.setAttribute("Width",Math.max(1,v*{w}/{full}));}}]]></Script></Bind></Rectangle>')

    def step_button(self, x, y, name, step, label, w=26, h=22, lo=-1e9, hi=1e9):
        """Button that adds `step` to a writable value on each click; the result is held within lo ... hi."""
        self._bind(name)
        self.items.append(
            f'<Component Clip="False" ContentHeight="{h}" ContentWidth="{w}" Height="{h}" Left="{x}" Step="{step}" '
            f'Top="{y}" Val="0" Width="{w}"><Bind Name="{name}"/>'
            f'<Rectangle Fill="#E8EAED" Height="{h}" Left="0" RadiusX="4" RadiusY="4" Stroke="#5F6368" StrokeWidth="1" '
            f'Top="0" Width="{w}"/>'
            f'<Text FontFamily="{FONT}" FontSize="14" FontWeight="Bold" HorizontalAlign="Center" Left="{w / 2}" '
            f'Stroke="#202124" Top="3">{escape(label)}</Text>'
            f'<Script OnMouseClick="clk" OnSignalChange="sig"><![CDATA[function sig(evt){{'
            f'evt.getCurrentTarget().setAttribute("Val",String(evt.getValue()));}}'
            f'function clk(evt){{evt.preventDefault();var c=evt.getCurrentTarget();'
            f'var b=c.getElementsByTagName("Bind").item(0);'
            f'setValue(b.getFullBindName(),Math.min({hi},Math.max({lo},parseFloat(c.getAttribute("Val"))+parseFloat(c.getAttribute("Step")))));}}'
            f']]></Script></Component>')

    # --- movement (forms of the shipped snippets RotationClockwise, FlowX, Blink) --------------------
    @staticmethod
    def _run(name):
        """Bind that starts an animation while the signal is 1 or more and stops it at 0."""
        return (f'<Bind Attribute="Animation" Name="{name}"><ConvertValue AttributeValue="Stop" SignalLessOrEqualTo="0"/>'
                f'<ConvertValue AttributeValue="Start" SignalMoreOrEqualTo="1"/></Bind>')

    def path(self, d, fill="None", stroke="#3C4043", sw=1.5):
        """Free shape from path data, the same letters as an SVG path: M L H V C S Q A Z."""
        self.items.append(f'<Path Fill="{fill}" PathData="{d}" Stroke="{stroke}" StrokeWidth="{sw}"/>')

    def place(self, sym, x, y, w=None, h=None, spin=None, seconds=2.0):
        """Put another Graphic in as a component at x, y, scaled to w x h. spin: bind name; while that signal is
        1 or more the whole symbol turns around its centre, one turn in `seconds`."""
        w, h = w or sym.w, h or sym.h
        for n in sym.binds:
            self._bind(n)
        rot = ""
        if spin:
            self._bind(spin)
            rot = (f'<Rotate><Animate Animation="Stop" Attribute="Angle" CalcMode="Linear" Duration="{seconds}" '
                   f'From="0" To="360">{self._run(spin)}</Animate></Rotate>')
        self.items.append(f'<Component Clip="False" ContentHeight="{sym.h}" ContentWidth="{sym.w}" Height="{h}" '
                          f'Left="{x}" Top="{y}" Width="{w}">' + "".join(sym.items) + rot + '</Component>')

    def fan(self, x, y, name, d=60, blades=7, seconds=2.0):
        """Fan seen along its shaft: housing ring and an impeller with swept blades that turns while the signal is 1
        or more."""
        import math
        self.items.append(f'<Ellipse Fill="#DADCE0" Height="{d}" Left="{x}" Stroke="#3C4043" StrokeWidth="2.5" Top="{y}" '
                          f'Width="{d}"/>')
        m = d * 0.08
        self.items.append(f'<Ellipse Fill="#F8F9FA" Height="{d - 2 * m}" Left="{x + m}" Stroke="#9AA0A6" StrokeWidth="1" '
                          f'Top="{y + m}" Width="{d - 2 * m}"/>')
        s = d - 2 * m - 2; c = s / 2; r0, r1 = c * 0.24, c * 0.96
        pol = lambda r, a: (c + r * math.cos(a), c + r * math.sin(a))
        f = lambda p: f"{p[0]:.1f},{p[1]:.1f}"
        imp = Graphic(s, s)
        for k in range(blades):
            a = 2 * math.pi * k / blades
            A, B = pol(r0, a), pol(r1, a + 0.95)                  # leading edge: root to tip, swept back
            C, D = pol(r1, a + 0.95 + 0.42), pol(r0, a + 0.75)    # trailing edge back to the hub
            c1, c2 = pol(c * 0.62, a + 0.15), pol(c * 0.9, a + 0.6)
            c3, c4 = pol(c * 0.85, a + 1.15), pol(c * 0.5, a + 0.85)
            imp.path(f"M{f(A)} C{f(c1)} {f(c2)} {f(B)} L{f(C)} C{f(c3)} {f(c4)} {f(D)} Z", fill="#5F6368", stroke="#3C4043", sw=0.8)
        imp.items.append(f'<Ellipse Fill="#3C4043" Height="{2 * r0 * 1.25:.1f}" Left="{c - r0 * 1.25:.1f}" Stroke="None" '
                         f'Top="{c - r0 * 1.25:.1f}" Width="{2 * r0 * 1.25:.1f}"/>')
        imp.items.append(f'<Ellipse Fill="#BDC1C6" Height="{r0 * 0.9:.1f}" Left="{c - r0 * 0.45:.1f}" Stroke="None" '
                         f'Top="{c - r0 * 0.45:.1f}" Width="{r0 * 0.9:.1f}"/>')
        self.place(imp, x + (d - s) / 2, y + (d - s) / 2, spin=name, seconds=seconds)

    def airflow(self, x, y, length, height, name, colour="#9AA0A6", lines=3, seconds=2.0, sw=1.3, alt=None):
        """Air shown as thin wavy streaks that drift along a duct while the signal is 1 or more: in a box from x, y,
        `length` long (negative = moving to the left) and `height` high."""
        self._bind(name)
        L = abs(length); P = 48.0; h = P / 2; n = int(L // h) + 6
        body = ""
        for i in range(lines):
            yy = height * (i + 0.5) / lines; amp = 3.5 + 1.5 * (i % 2); x0 = -P - (P / lines) * i
            d = f"M{x0:.1f},{yy:.1f}"; up = 1
            for k in range(n):
                xa = x0 + k * h
                d += f" C{xa + h / 3:.1f},{yy - up * amp * 4 / 3:.1f} {xa + 2 * h / 3:.1f},{yy - up * amp * 4 / 3:.1f} {xa + h:.1f},{yy:.1f}"
                up = -up
            body += f'<Path Fill="None" PathData="{d}" Stroke="{colour}" StrokeWidth="{sw}">{self._alt(alt, colour)}</Path>'
        frm, to = (0, P) if length > 0 else (P, 0)
        self.items.append(
            f'<Component Clip="True" ContentHeight="{height}" ContentWidth="{L}" Height="{height}" Left="{x}" Top="{y}" '
            f'Width="{L}"><Group>{body}<Translate><Animate Animation="Stop" Attribute="X" AutoReverse="False" '
            f'CalcMode="Linear" Duration="{seconds}" Freeze="False" From="{frm}" To="{to}">{self._run(name)}</Animate>'
            f'</Translate></Group></Component>')

    def drum(self, x, y, w, h, name, seconds=1.2, spacing=9, colour="#9AA0A6", down=True, alt=None):
        """A rotor seen from the side: lines across a box of w x h that travel down (or up) while the signal is 1 or
        more, so the drum looks as if it turns. Draw the body first, then this over it."""
        self._bind(name)
        n = int(h // spacing) + 3
        lines = "".join(f'<Line Stroke="{colour}" StrokeWidth="1.2" X1="0" X2="{w}" Y1="{spacing * (i - 1)}" Y2="{spacing * (i - 1)}">{self._alt(alt, colour)}</Line>'
                        for i in range(n))
        frm, to = (0, spacing) if down else (spacing, 0)
        self.items.append(
            f'<Component Clip="True" ContentHeight="{h}" ContentWidth="{w}" Height="{h}" Left="{x}" Top="{y}" Width="{w}">'
            f'<Group>{lines}<Translate><Animate Animation="Stop" Attribute="Y" AutoReverse="False" CalcMode="Linear" '
            f'Duration="{seconds}" Freeze="False" From="{frm}" To="{to}">{self._run(name)}</Animate></Translate></Group>'
            f'</Component>')

    def flow(self, x, y, length, name, vertical=False, colour="#FFFFFF", seconds=1.0, thick=4):
        """Marks that run along a pipe while the signal is 1 or more: to the right (down when vertical).
        Draw the pipe first, then this over it; a negative length runs the other way."""
        self._bind(name)
        n = int(abs(length) // 20) + 2; k = 1 if length > 0 else -1; L = abs(length)
        if vertical:
            marks = "".join(f'<Rectangle Fill="{colour}" Height="8" Left="0" Stroke="None" Top="{20 * i - 20}" '
                            f'Width="{thick}"/>' for i in range(n))
            box = f'ContentHeight="{L}" ContentWidth="{thick}" Height="{L}" Width="{thick}"'; axis = "Y"
        else:
            marks = "".join(f'<Rectangle Fill="{colour}" Height="{thick}" Left="{20 * i - 20}" Stroke="None" Top="0" '
                            f'Width="8"/>' for i in range(n))
            box = f'ContentHeight="{thick}" ContentWidth="{L}" Height="{thick}" Width="{L}"'; axis = "X"
        frm, to = (0, 20) if k > 0 else (20, 0)
        self.items.append(
            f'<Component Clip="True" {box} Left="{x}" Top="{y}"><Group>{marks}'
            f'<Translate><Animate Animation="Stop" Attribute="{axis}" AutoReverse="False" CalcMode="Linear" '
            f'Duration="{seconds}" Freeze="False" From="{frm}" To="{to}">{self._run(name)}</Animate></Translate>'
            f'</Group></Component>')

    def alarm_lamp(self, x, y, name, d=18, colour="#D93025"):
        """Lamp that is grey at 0 and blinks in `colour` while the signal is 1 or more."""
        self.items.append(f'<Ellipse Fill="#BDC1C6" Height="{d}" Left="{x}" Stroke="#5F6368" StrokeWidth="1" Top="{y}" '
                          f'Width="{d}"/>')
        self._bind(name)
        self.items.append(
            f'<Ellipse Fill="{colour}" Height="{d}" Left="{x}" Stroke="#5F6368" StrokeWidth="1" Top="{y}" Width="{d}" '
            f'Visibility="Hidden"><Animate Animation="Stop" Attribute="Visibility" AutoReverse="False" '
            f'CalcMode="Discrete" Duration="1" From="Visible" To="Hidden">{self._run(name)}</Animate></Ellipse>')

    def alarm_state(self, x, y, name, d=18, colour="#D93025", blink=True):
        """Lamp for the state of an EBO alarm object (bind it to the alarm's AlarmState, or to the public signal of
        an ALARM block): 0 normal grey; 1 alarm, not acknowledged: colour, blinking if blink; 2 acknowledged:
        colour, steady; 3 gone but not acknowledged: white with a coloured ring; 4 disabled / 5 fault: grey."""
        self._bind(name)
        cv = lambda v, col: f'<ConvertValue AttributeValue="{col}" SignalEqualTo="{v}"/>'
        self.items.append(
            f'<Ellipse Fill="#BDC1C6" Height="{d}" Left="{x}" Stroke="#5F6368" StrokeWidth="1.5" Top="{y}" Width="{d}">'
            f'<Bind Attribute="Fill" Name="{name}">{cv(0, "#BDC1C6")}{cv(1, colour)}{cv(2, colour)}{cv(3, "#FFFFFF")}'
            f'<ConvertValue AttributeValue="#BDC1C6" SignalMoreOrEqualTo="4"/></Bind>'
            f'<Bind Attribute="Stroke" Name="{name}">{cv(0, "#5F6368")}{cv(1, "#5F6368")}{cv(2, "#5F6368")}{cv(3, colour)}'
            f'<ConvertValue AttributeValue="#5F6368" SignalMoreOrEqualTo="4"/></Bind></Ellipse>')
        if blink:
            self.items.append(
                f'<Ellipse Fill="#BDC1C6" Height="{d}" Left="{x}" Stroke="#5F6368" StrokeWidth="1.5" Top="{y}" Width="{d}" '
                f'Visibility="Hidden"><Animate Animation="Stop" Attribute="Visibility" AutoReverse="False" '
                f'CalcMode="Discrete" Duration="1" From="Visible" To="Hidden"><Bind Attribute="Animation" Name="{name}">'
                f'<ConvertValue AttributeValue="Stop" SignalLessOrEqualTo="0"/><ConvertValue AttributeValue="Start" '
                f'SignalEqualTo="1"/><ConvertValue AttributeValue="Stop" SignalMoreOrEqualTo="2"/></Bind></Animate></Ellipse>')

    def info(self, x, y, title, text, w=280, side="right", d=16):
        """Small round "i" at x, y. A click on it opens a box with the title and the text (wrapped to the width
        w); a click on the box or on the "i" closes it again. side: where the box opens ("right", "left",
        "below", "above"). All boxes are drawn after everything else, so they lie on top."""
        import textwrap
        lines = []
        for para in str(text).split("\n"):
            lines += textwrap.wrap(para, max(10, int((w - 16) / 5.6))) or [""]
        h = 30 + 15 * len(lines) + 8
        bx, by = {"right": (d + 6, -4), "left": (-w - 6, -4), "below": (-w / 2 + d / 2, d + 6),
                  "above": (-w / 2 + d / 2, -h - 6)}[side]
        body = "".join(f'<Text FontFamily="{FONT}" FontSize="11" Left="{bx + 8}" Stroke="#202124" Top="{by + 28 + 15 * i}">'
                       f'{escape(l)}</Text>' for i, l in enumerate(lines))
        self.top.append(
            f'<Component Clip="False" ContentHeight="{d}" ContentWidth="{d}" Height="{d}" Left="{x}" Top="{y}" Width="{d}">'
            f'<Ellipse Fill="#1A73E8" Height="{d}" Left="0" Stroke="None" Top="0" Width="{d}"/>'
            f'<Text FontFamily="{FONT}" FontSize="{d - 4}" FontWeight="Bold" HorizontalAlign="Center" Left="{d / 2}" '
            f'Stroke="#FFFFFF" Top="1">i</Text>'
            f'<Group Name="pop" Visibility="Hidden">'
            f'<Rectangle Fill="#FFFDE7" Height="{h}" Left="{bx}" RadiusX="4" RadiusY="4" Stroke="#5F6368" StrokeWidth="1" '
            f'Top="{by}" Width="{w}"/>'
            f'<Text FontFamily="{FONT}" FontSize="12" FontWeight="Bold" Left="{bx + 8}" Stroke="#202124" Top="{by + 7}">'
            f'{escape(title)}</Text>{body}</Group>'
            f'<Script OnMouseClick="clk"><![CDATA[function clk(evt){{evt.preventDefault();'
            f'var p=evt.getCurrentTarget().getChild("pop");'
            f'p.setAttribute("Visibility",p.getAttribute("Visibility")=="Visible"?"Hidden":"Visible");}}]]></Script>'
            f'</Component>')

    @classmethod
    def from_svg(cls, path):
        """Read the plain shapes of an SVG file (path, rect, circle, ellipse, line, polygon, polyline with fill /
        stroke given as attributes or in style=) into a Graphic, to place() or to save_component(). Transforms,
        gradients, text and CSS classes are not read. EBO graphics are TGML, not SVG, but a path's data is the same."""
        import re, xml.etree.ElementTree as ET
        root = ET.parse(path).getroot()
        num = lambda v, d=0.0: float(re.sub(r"[a-z%]+$", "", v)) if v else d
        vb = [float(v) for v in re.split(r"[ ,]+", root.get("viewBox", "").strip()) if v]
        g = cls(vb[2] if len(vb) == 4 else num(root.get("width"), 100), vb[3] if len(vb) == 4 else num(root.get("height"), 100))
        for e in root.iter():
            tag = e.tag.split("}")[-1]
            st = dict(kv.split(":", 1) for kv in (e.get("style") or "").split(";") if ":" in kv)
            col = lambda k, d: {"none": "None"}.get((st.get(k) or e.get(k) or d).strip(), (st.get(k) or e.get(k) or d).strip())
            fill, stroke = col("fill", "#000000"), col("stroke", "none")
            sw = num(st.get("stroke-width") or e.get("stroke-width"), 1.0)
            if tag == "path" and e.get("d"):
                g.path(" ".join(e.get("d").split()), fill, stroke, sw)
            elif tag == "rect":
                g.rect(num(e.get("x")), num(e.get("y")), num(e.get("width")), num(e.get("height")), fill, stroke, sw, num(e.get("rx")))
            elif tag in ("circle", "ellipse"):
                rx = num(e.get("r") or e.get("rx")); ry = num(e.get("r") or e.get("ry"))
                g.items.append(f'<Ellipse Fill="{fill}" Height="{2 * ry}" Left="{num(e.get("cx")) - rx}" Stroke="{stroke}" '
                               f'StrokeWidth="{sw}" Top="{num(e.get("cy")) - ry}" Width="{2 * rx}"/>')
            elif tag == "line":
                g.line(num(e.get("x1")), num(e.get("y1")), num(e.get("x2")), num(e.get("y2")), stroke, sw)
            elif tag in ("polygon", "polyline") and e.get("points"):
                v = [float(t) for t in re.split(r"[ ,]+", e.get("points").strip()) if t]
                d = "M" + " L".join(f"{v[i]},{v[i + 1]}" for i in range(0, len(v) - 1, 2)) + (" Z" if tag == "polygon" else "")
                g.path(d, fill, stroke, sw)
        return g

    def save_component(self, path, name, description=""):
        """Write this drawing as a component file (.tgmlcomponent) for the Graphics Editor's library: put it in a
        folder below ...\\Graphics Editor\\Components and it shows in the Components pane, to drag into any graphic.
        Its bind names become the component's binding points."""
        body = "".join(self.items)
        with open(path, "w", encoding="utf-8", newline="\r\n") as f:
            f.write(f'<?xml version="1.0"?>\n<Component Clip="False" ContentHeight="{self.h}" ContentWidth="{self.w}" '
                    f'Height="{self.h}" Left="0" Name="{escape(name)}" Top="0" Width="{self.w}">{body}'
                    f'<Metadata Name="Name" Value="{escape(name)}"/><Metadata Name="Description" '
                    f'Value="{escape(description)}"/></Component>\n')
        return path

    # --- output -------------------------------------------------------------------------------------
    def tgml(self):
        body = "\n    ".join(self.items + self.top)
        return (f'<?xml version="1.0"?>\n<?tgml version="2.0"?>\n<Tgml Background="{self.bg}" Height="{self.h}" '
                f'Stretch="Uniform" Width="{self.w}">\n'
                f'    <Rectangle Fill="{self.bg}" Height="{self.h}" Left="0" Stroke="None" Top="0" Width="{self.w}"/>\n'
                f'    {body}\n</Tgml>\n')

    def save(self, path):
        with open(path, "w", encoding="utf-8", newline="\r\n") as f:
            f.write(self.tgml())
        return path
