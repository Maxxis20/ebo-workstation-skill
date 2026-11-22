#!/usr/bin/env python3
"""FUXA project: MQTT device subscribed to the topics EBO publishes, one view with the live values."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "scripts"))
from fuxa import Fuxa
from points import MQTT, topic

GREY = "#5f6368"


def build():
    f = Fuxa("DH-ex2 over MQTT", width=720, height=300)
    t = {n: f.tag(n, topic(p)) for n, p in MQTT.items()}

    def num(x, y, label, tag, fill="#0b57d0", size=22):
        f.text(x, y, label, 12, fill=GREY); f.value(x, y + 26, t[tag], size=size, fill=fill)

    def lamp(x, y, label, tag, on="#34a853"):
        f.lamp(x + 10, y, t[tag], on=on); f.text(x + 28, y + 4, label, 12)

    f.text(16, 26, "District heating substation DH-ex2, live from EBO over MQTT", 16, weight="bold")
    f.box(12, 40, 200, 150); f.text(24, 62, "Outdoor", 14, weight="bold")
    num(24, 84, "model TOUT, \xb0C", "TOUT"); num(24, 134, "TE2B, \xb0C", "TE2B")
    num(116, 134, "TE2B_F, \xb0C", "TE2B_F", fill=GREY)
    f.box(12, 200, 200, 88); f.text(24, 222, "Common alarm", 14, weight="bold")
    lamp(24, 254, "ALARM_SUM", "ALARM_SUM", on="#d93025"); num(150, 236, "payload", "ALARM_SUM", fill=GREY, size=16)
    for x, title, te, sp, tv, pos, run, on in [(224, "TC1 Hot water", "TE1", "DHW_SP", "TV1", "TV1_POS", "P1_RUN", "P1_ON"),
                                               (472, "TC2 Heating", "TE2A", "HEAT_SP", "TV2", "TV2_POS", "P2_RUN", "P2_ON")]:
        f.box(x, 40, 236, 248); f.text(x + 12, 62, title, 14, weight="bold")
        num(x + 12, 84, te + ", \xb0C", te); num(x + 124, 84, "set value, \xb0C", sp, fill="#188038")
        f.line(x + 12, 124, x + 224, 124, "#dadce0", 1)
        num(x + 12, 146, tv + " command, %", tv); num(x + 124, 146, "at the model, %", pos, fill=GREY)
        f.line(x + 12, 186, x + 224, 186, "#dadce0", 1)
        lamp(x + 12, 214, run[:2] + " run command", run); num(x + 150, 196, "payload", run, fill=GREY, size=16)
        lamp(x + 12, 250, run[:2] + " running at the model", on)
    return f


if __name__ == "__main__":
    f = build()
    f.save(os.path.join(HERE, "DH-ex2.fuxa.json"))
    print(f.stats())
