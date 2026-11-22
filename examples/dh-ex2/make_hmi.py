#!/usr/bin/env python3
"""DH-ex2-HMI: graphic of both loops with live values; outdoor temperature and tapping of the model by buttons."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "scripts"))
from tgml import Graphic
from points import HMI

RED, BLUE, GREY, ALM, CIRC = "#D93025", "#1A73E8", "#5F6368", "#D93025", "#E8710A"
DEG = "\xb0C"


def panel(g, x, y, w, h, title):
    g.rect(x, y, w, h, radius=8)
    g.text(x + 14, y + 10, title, size=15, bold=True)


def buttons(g, x, y, name, steps, lo, hi):
    for i, s in enumerate(steps):
        g.step_button(x + i * 50, y, name, s, ("+" if s > 0 else "−") + str(abs(s)), w=42, h=26, lo=lo, hi=hi)


def loop(g, x, title, te_label, te, sp, tv, tvpos, pump, pump_label, prim, sec_out, sec_in, circulation):
    st, trip = pump_label + "_ST", pump_label + "_TRIP"
    """One exchanger loop: primary side with control valve on the left, secondary side on the right.
    Pump placement as in the K1 example drawing: the hot water pump sits on the circulation pipe, which joins the
    cold water feed of the exchanger; the heating pump sits on the return, pumping into the exchanger."""
    panel(g, x, 50, 395, 530, title)
    ex, ey = x + 170, 190                                              # exchanger
    g.pipe([(x + 20, ey + 30), (ex, ey + 30)], RED); g.pipe([(ex, ey + 150), (x + 20, ey + 150)], BLUE)
    g.pipe([(ex + 60, ey + 30), (x + 375, ey + 30)], RED); g.pipe([(x + 375, ey + 150), (ex + 60, ey + 150)], BLUE)
    if circulation:                                                    # from the building, through the pump, into the cold feed
        g.pipe([(x + 375, ey + 90), (x + 256, ey + 90), (x + 256, ey + 150)], CIRC, 4)
        g.pump(x + 292, ey + 68, st, left=True)
        g.text(x + 292, ey + 114, pump_label, bold=True); g.state(x + 319, ey + 114, pump_label + "_ON", "RUN", "STOP")
        g.text(x + 292, ey + 50, "circulation", colour=GREY)
        g.text(x + 268, ey + 160, sec_in, colour=GREY)
    else:                                                              # on the return, pumping into the exchanger
        g.pump(x + 292, ey + 128, st, left=True)
        g.text(x + 292, ey + 106, pump_label, bold=True); g.state(x + 319, ey + 106, pump_label + "_ON", "RUN", "STOP")
        g.text(x + 268, ey + 178, sec_in, colour=GREY)
    g.rect(ex, ey, 60, 180, fill="#E8EAED", stroke="#3C4043", sw=2)
    g.line(ex, ey + 180, ex + 60, ey, "#3C4043", 2)
    g.text(x + 20, ey - 34, prim, colour=GREY); g.text(x + 20, ey + 160, "district heating return", colour=GREY)
    g.text(x + 240, ey + 2, sec_out, colour=GREY)
    g.text(x + 20, ey + 232, f"Pump {pump_label} motor protection (model)", colour=GREY)
    g.step_button(x + 20, ey + 254, trip, 1, "trip", w=60, h=26, lo=0, hi=1)
    g.step_button(x + 88, ey + 254, trip, -1, "reset", w=60, h=26, lo=0, hi=1)
    g.state(x + 164, ey + 259, trip, "TRIPPED", "healthy", on=ALM)
    g.valve(x + 95, ey + 30)
    g.text(x + 60, ey + 52, tv[:3], bold=True); g.value(x + 92, ey + 50, tv, unit="%")
    g.bar(x + 60, ey + 76, tv, w=90)
    g.text(x + 60, ey + 94, "model position", size=11, colour=GREY); g.value(x + 60, ey + 108, tvpos, unit="%", size=12, colour=GREY)
    g.text(x + 250, 90, te_label, colour=GREY); g.value(x + 250, 108, te, unit=DEG, size=26)
    g.line(x + 345, ey + 30, x + 345, 150, "#444444", 1)
    g.text(x + 20, 90, "Set value", colour=GREY); g.value(x + 20, 108, sp, unit=DEG, size=26, colour="#188038")


def build():
    g = Graphic(1100, 600)
    g.text(20, 12, "DH-ex2  District heating substation: domestic hot water and heating", size=20, bold=True)
    panel(g, 20, 50, 250, 200, "Outdoor temperature")
    g.text(34, 80, "model, click to change", colour=GREY); g.value(34, 98, "TOUT", unit=DEG, size=26)
    buttons(g, 34, 136, "TOUT", (-5, -1, 1, 5), -50, 50)
    g.text(34, 174, "controller TE2B", colour=GREY); g.value(150, 172, "TE2B", unit=DEG)
    g.text(34, 196, "filtered TE2B_F", colour=GREY); g.value(150, 194, "TE2B_F", unit=DEG)
    g.text(34, 220, "Summer stop", colour=GREY); g.state(150, 220, "SUMMER", "ACTIVE", "off", on="#F29900")
    panel(g, 20, 262, 250, 106, "Hot water tapping (model)")
    g.value(34, 292, "DHW_TAP", unit="l/min", size=22); buttons(g, 34, 328, "DHW_TAP", (-3, -1, 1, 3), 0, 30)
    panel(g, 20, 380, 250, 200, "Alarms")
    for i, (n, label) in enumerate([("ALARM_SUM", "Common alarm (HS)"), ("TE2B_FAULT", "TE2B sensor fault"),
                                    ("TE1_FAULT", "TE1 sensor fault"), ("DHW_TEMP_ALM", "Hot water temperature"),
                                    ("TE2A_FAULT", "TE2A sensor fault"), ("HEAT_TEMP_ALM", "Heating supply temperature"),
                                    ("P1_FAULT", "P1 pump fault"), ("P2_FAULT", "P2 pump fault")]):
        g.lamp(34, 410 + i * 21, n, d=15, on=ALM); g.text(60, 409 + i * 21, label, bold=(i == 0))
    loop(g, 285, "TC1  Domestic hot water", "TE1 hot water", "TE1", "DHW_SP", "TV1", "TV1_POS", "P1_RUN", "P1",
         "district heating supply", "hot water", "cold water", True)
    loop(g, 690, "TC2  Heating", "TE2A supply", "TE2A", "HEAT_SP", "TV2", "TV2_POS", "P2_RUN", "P2",
         "district heating supply", "heating supply", "heating return", False)
    missing = set(g.binds) ^ set(HMI)
    assert not missing, missing
    return g


if __name__ == "__main__":
    g = build()
    g.save(os.path.join(HERE, "DH-ex2-HMI.tgml"))
    print("elements:", len(g.items), "bind names:", len(g.binds))
