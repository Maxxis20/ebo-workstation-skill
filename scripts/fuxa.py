#!/usr/bin/env python3
"""fuxa.py - FUXA project generator: one MQTT device, one tag per topic, one view with live values.

For a FUXA 1.3.5 that runs beside the Mosquitto broker (findings, section MQTT). EBO publishes each
data point on its own topic (the EBO path without the leading slash, e.g. "Server 1/Prog/MODULE/Signal") with the
plain number as payload, so every tag is a raw MQTT tag whose address is the topic.

    from fuxa import Fuxa
    f = Fuxa("DH over MQTT", width=760, height=430)
    te1 = f.tag("TE1", "Server 1/DH/TC1/TE1")
    f.box(20, 60, 340, 120); f.text(36, 86, "Hot water, °C", 12, fill="#5f6368")
    f.value(36, 120, te1, digits=1); f.lamp(300, 112, f.tag("P1", "Server 1/DH/TC1/P1_RUN"), on="#34a853")
    f.save("project.json")          # then: ebo.sh fuxa project.json ; ebo.sh run "Web-Top 'http://127.0.0.1:1881/' 'FUXA' 800 600 780 520"

Coordinates are svg pixels from the top left of the view; a text's y is its baseline. Forms proven 2026-11-21:
a live number is a group type "svg-ext-value" holding one text; a lamp is a group type "svg-ext-gauge_semaphore"
holding one ellipse, coloured by value range. FUXA does not draw a unit and ignores zero decimals, so write the
unit into a label and expect "1" for a binary value with digits=0 only by luck (it shows the raw payload).
"""
import json
from xml.sax.saxutils import escape


class Fuxa:
    def __init__(self, name, width=800, height=480, broker="mqtt://127.0.0.1:1883", background="#f4f5f7", title=None):
        self.name, self.w, self.h, self.broker, self.bg = name, width, height, broker, background
        self.title = title or name
        self.tags, self.items, self.svg, self.n = {}, {}, [], 0

    def _id(self, prefix):
        self.n += 1
        return f"{prefix}_{self.n:03d}"

    def tag(self, name, topic):
        """Subscribe to a topic. Returns the tag id to hand to value() and lamp()."""
        tid = "t_" + name
        if tid in self.tags:
            raise ValueError(f"tag {name} defined twice")
        self.tags[tid] = {"id": tid, "name": name, "type": "raw", "address": topic, "memaddress": topic,
                          "options": {"subs": [topic]},
                          "daq": {"enabled": False, "interval": 60, "changed": False, "restored": False}}
        return tid

    def text(self, x, y, s, size=13, weight="normal", fill="#202124", anchor="start"):
        self.svg.append(f'<text id="{self._id("svg")}" x="{x}" y="{y}" font-family="Arial" font-size="{size}" '
                        f'font-weight="{weight}" fill="{fill}" text-anchor="{anchor}" stroke="none" '
                        f'xml:space="preserve">{escape(str(s))}</text>')

    def box(self, x, y, w, h, fill="#ffffff", stroke="#9aa0a6", radius=8):
        self.svg.append(f'<rect id="{self._id("svg")}" x="{x}" y="{y}" width="{w}" height="{h}" rx="{radius}" '
                        f'ry="{radius}" fill="{fill}" stroke="{stroke}" stroke-width="1"/>')

    def line(self, x1, y1, x2, y2, stroke="#5f6368", width=2):
        self.svg.append(f'<line id="{self._id("svg")}" x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{stroke}" '
                        f'stroke-width="{width}"/>')

    def value(self, x, y, tag, digits=1, size=22, fill="#0b57d0", anchor="start"):
        """Live number of a tag."""
        self._known(tag); gid = self._id("VAL")
        self.svg.append(f'<g id="{gid}" type="svg-ext-value"><text id="{gid}_t" x="{x}" y="{y}" font-family="Arial" '
                        f'font-size="{size}" font-weight="bold" fill="{fill}" text-anchor="{anchor}" stroke="none" '
                        f'xml:space="preserve">--</text></g>')
        self.items[gid] = {"id": gid, "type": "svg-ext-value", "name": self.tags[tag]["name"], "label": "Value",
                           "property": {"variableId": tag, "events": [], "actions": [],
                                        "ranges": [{"type": "unit", "min": 0, "max": 0, "text": "", "fractionDigits": digits}]}}

    def lamp(self, x, y, tag, on="#34a853", off="#bdc1c6", r=10):
        """Circle that takes colour `on` while the tag is 1 and `off` while it is 0. x, y is the centre."""
        self._known(tag); gid = self._id("LMP")
        self.svg.append(f'<g id="{gid}" type="svg-ext-gauge_semaphore"><ellipse id="{gid}_e" cx="{x}" cy="{y}" rx="{r}" '
                        f'ry="{r}" fill="{off}" stroke="#5f6368" stroke-width="1.5"/></g>')
        self.items[gid] = {"id": gid, "type": "svg-ext-gauge_semaphore", "name": self.tags[tag]["name"], "label": "HtmlSemaphore",
                           "property": {"variableId": tag, "events": [], "actions": [],
                                        "ranges": [{"min": 0, "max": 0, "color": off}, {"min": 1, "max": 1, "color": on}]}}

    def _known(self, tag):
        if tag not in self.tags:
            raise ValueError(f"unknown tag id {tag!r}: use the value returned by tag()")

    def project(self):
        content = (f'<svg width="{self.w}" height="{self.h}" xmlns="http://www.w3.org/2000/svg" '
                   'xmlns:svg="http://www.w3.org/2000/svg" xmlns:html="http://www.w3.org/1999/xhtml">'
                   '<g><title>Layer 1</title>' + "".join(self.svg) + "</g></svg>")
        return {
            "version": "1.01", "name": self.name,
            "server": {"id": "0", "name": "FUXA Server", "type": "FuxaServer", "property": {}, "tags": {}, "polling": 1000},
            "devices": {"d_mqtt": {"id": "d_mqtt", "name": "MQTT", "enabled": True, "type": "MQTTclient", "polling": 1000,
                                   "property": {"address": self.broker}, "tags": self.tags}},
            "hmi": {"views": [{"id": "v_main", "name": self.name, "items": self.items, "variables": {}, "svgcontent": content,
                               "profile": {"width": self.w, "height": self.h, "bkcolor": self.bg}}],
                    "layout": {"navigation": {"mode": "void", "type": "block", "bkcolor": "#263238", "fgcolor": "#ffffff", "items": []},
                               "header": {"title": self.title, "alarms": "hide", "infos": "hide", "bkcolor": "#263238",
                                          "fgcolor": "#ffffff", "height": 46, "dateTimeDisplay": ""},
                               "start": "v_main", "loginonstart": False, "loginoverlaycolor": "none", "showdev": False,
                               "inputdialog": "no", "hidenavigation": True}},
            "charts": [], "alarms": [], "scripts": [], "texts": [], "recipes": [], "ar": {"enabled": False, "markers": []},
        }

    def save(self, path):
        with open(path, "w", encoding="ascii") as f:
            json.dump(self.project(), f)                        # ascii: non-ASCII as \u escapes, safe through the transfer
        return path

    def stats(self):
        return {"tags": len(self.tags), "live items": len(self.items), "svg elements": len(self.svg)}
