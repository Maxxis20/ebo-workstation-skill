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

    def _bind(self, name):
        if name not in self.binds:
            self.binds.append(name)

    # --- static -------------------------------------------------------------------------------------
    def rect(self, x, y, w, h, fill="#FFFFFF", stroke="#9AA0A6", sw=1, radius=0):
        self.items.append(f'<Rectangle Fill="{fill}" Height="{h}" Left="{x}" RadiusX="{radius}" RadiusY="{radius}" '
                          f'Stroke="{stroke}" StrokeWidth="{sw}" Top="{y}" Width="{w}"/>')

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

    def pump(self, x, y, name, d=44, left=False):
        """Circle with a triangle that shows the flow direction (to the right, or to the left). Colour by the value:
        0 grey (stopped), 1 green (running), 2 and above red (fault). A plain binary gives grey / green."""
        self._bind(name)
        self.items.append(f'<Ellipse Fill="#BDC1C6" Height="{d}" Left="{x}" Stroke="#3C4043" StrokeWidth="2" Top="{y}" '
                          f'Width="{d}"><Bind Attribute="Fill" Name="{name}">'
                          f'<ConvertValue AttributeValue="#BDC1C6" SignalLessOrEqualTo="0"/>'
                          f'<ConvertValue AttributeValue="#34A853" SignalEqualTo="1"/>'
                          f'<ConvertValue AttributeValue="#D93025" SignalMoreOrEqualTo="2"/></Bind></Ellipse>')
        c = d / 2
        k = -1 if left else 1
        self.polygon([(x + c - 8 * k, y + c - 11), (x + c + 12 * k, y + c), (x + c - 8 * k, y + c + 11)], fill="#FFFFFF", stroke="#3C4043")

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

    # --- output -------------------------------------------------------------------------------------
    def tgml(self):
        body = "\n    ".join(self.items)
        return (f'<?xml version="1.0"?>\n<?tgml version="2.0"?>\n<Tgml Background="{self.bg}" Height="{self.h}" '
                f'Stretch="Uniform" Width="{self.w}">\n'
                f'    <Rectangle Fill="{self.bg}" Height="{self.h}" Left="0" Stroke="None" Top="0" Width="{self.w}"/>\n'
                f'    {body}\n</Tgml>\n')

    def save(self, path):
        with open(path, "w", encoding="utf-8", newline="\r\n") as f:
            f.write(self.tgml())
        return path
