#!/usr/bin/env python3
"""make_hmi.py - FanSeq.tgml: operator graphic of the fan sequence, and hmi_binds.json (bind name -> target).

Left: header with unit state, current step and time; mode selector, Reset, emergency stop; the plant (damper, fan,
duct pressure) with its commands and feedbacks; the test switches. Right: the list of all steps, each with what it
does, its requirements and live status:
  done     green tick, "done in 9.5 s", requirements OK
  active   teal row, "active 3.0 s", per requirement OK / CHECKING / next
  waiting  grey, "max 20 s" (its supervision time)
  alarm    red row, the requirement that was not met in time marked NOT MET
"""
import json, os, sys
from xml.sax.saxutils import escape
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "scripts"))
from tgml import Graphic, FONT
from steps import STEPS, RUN_STEP, FIRST_STOP

W, H = 1300, 880
g = Graphic(W, H, background="#EEF1F4")
binds = {}                       # bind name -> target relative to the folder: 'SEQ/Module/Signal' or 'Cmd/X/Value'


def B(name, target):
    binds[name] = target
    return name


js_text, fill_by, rect_by, circle_by = g.text_by, g.fill_by, g.rect_by, g.circle_by     # helpers in tgml.py
button, set_button, toggle = g.button, g.set_button, g.toggle


def value(x, y, name, unit="", decimals=1, size=15, colour="#0B57D0"):
    g.value(x, y, name, decimals=decimals, unit=unit, size=size, colour=colour)


GREY, TEAL, GREEN, RED, AMBER = "#9AA0A6", "#00796B", "#1E8E3E", "#D93025", "#E37400"

# ---- header ---------------------------------------------------------------------------------------------------
g.rect(0, 0, W, 70, fill="#1F2A36", stroke="None")
g.text(20, 12, "FAN 01", size=26, bold=True, colour="#FFFFFF")
g.text(20, 46, "Start / stop sequence example", size=12, colour="#BFC7D0")
js_text(200, 14, B("UNIT_ST", "SEQ/Hmi/Unit_State"),
        [(0, "Stopped", "#FFFFFF"), (1, "Starting", "#8AB4F8"), (2, "Running", "#81C995"), (3, "Stopping", "#FDD663"),
         (4, "TRIP", "#F28B82"), (5, "SEQUENCE ALARM", "#F28B82")], size=24)
g.text(200, 48, "step", size=12, colour="#BFC7D0")
js_text(232, 46, B("STEP", "SEQ/Seq/Step"),
        [(0, "0  Idle", "#FFFFFF")] + [(k, f"{k}  {n.title()}", "#FFFFFF") for k, n, *_ in STEPS], size=14)
value(470, 46, B("STEP_T", "SEQ/Seq/Step_Time"), "s", 1, 14, "#FFFFFF")

g.text(560, 8, "MODE", size=11, colour="#BFC7D0")
for i, (v, lab) in enumerate(((0, "Off"), (1, "On"), (2, "Auto"))):
    set_button(560 + i * 78, 26, 74, 34, B("MODE", "Cmd/Mode/Value"), v, lab)
g.text(800, 8, "AUTO DEMAND", size=11, colour="#BFC7D0")
toggle(800, 26, 90, 34, B("AUTO", "Cmd/Auto_Demand/Value"), "Schedule", "#0B57D0")
button(905, 26, 90, 34, B("RESET", "Cmd/Reset/Value"), "Reset", "setValue(b.getFullBindName(),v+1);")
toggle(1010, 26, 130, 34, B("ESTOP", "Cmd/E_Stop/Value"), "Emergency stop", RED)
g.text(1160, 8, "ALARMS", size=11, colour="#BFC7D0")
g.lamp(1160, 30, B("TRIP", "SEQ/Seq/Trip"), on=RED)
g.text(1184, 31, "A trip", size=12, colour="#FFFFFF")
g.lamp(1230, 30, B("SEQ_ALM", "SEQ/Seq/Seq_Alarm"), on=AMBER)
g.text(1254, 31, "B seq", size=12, colour="#FFFFFF")

# ---- plant ----------------------------------------------------------------------------------------------------
px, py = 20, 90
g.rect(px, py, 680, 400, fill="#FFFFFF", stroke="#C4C7C5", radius=8)
g.text(px + 16, py + 12, "PLANT (simulated)", size=12, bold=True, colour="#5F6368")
dy = py + 170
g.rect(px + 30, dy, 620, 90, fill="#E8F0FE", stroke="#5F6368", sw=2)
g.text(px + 40, dy + 36, "Outdoor air", size=13, colour="#5F6368")
g.text(px + 560, dy + 36, "Supply air", size=13, colour="#5F6368")
# damper: frame and blades, colour by position (closed grey, moving amber, open green)
dx = px + 170
g.items.append(
    f'<Rectangle Fill="{GREY}" Height="90" Left="{dx}" Stroke="#3C4043" StrokeWidth="2" Top="{dy}" Width="26">'
    f'<Bind Name="{B("DMP_POS", "SEQ/Sim/Damper_Pos")}"><Script OnSignalChange="signal"><![CDATA[function signal(evt){{'
    f'var r=evt.getTarget().getParentNode();var v=new Number(evt.getValue());'
    f'r.setAttribute("Fill",v>=95?"{GREEN}":(v<=5?"{GREY}":"{AMBER}"));}}]]></Script></Bind></Rectangle>')
g._bind("DMP_POS")
for k in range(4):
    g.line(dx + 4, dy + 12 + k * 21, dx + 22, dy + 18 + k * 21, "#FFFFFF", 2)
g.text(dx - 10, dy - 66, "Damper FZ01", size=13, bold=True)
value(dx - 10, dy - 46, "DMP_POS", "%", 0)
g.text(dx - 10, dy + 100, "cmd", size=11, colour="#5F6368")
g.lamp(dx + 18, dy + 100, B("DMP_CMD", "SEQ/Outputs/Damper_Cmd"), d=14)
g.text(dx - 10, dy + 120, "open", size=11, colour="#5F6368")
g.lamp(dx + 18, dy + 120, B("DMP_OPEN", "SEQ/Sim/Damper_Open"), d=14)
g.text(dx - 10, dy + 140, "closed", size=11, colour="#5F6368")
g.lamp(dx + 28, dy + 140, B("DMP_CLOSED", "SEQ/Sim/Damper_Closed"), d=14, on="#5F6368", off="#FFFFFF")
# fan
fx = px + 330
g.fan(fx, dy + 10, B("FAN_FDB", "SEQ/Sim/Fan_Fdb"), d=70)
g.text(fx, dy - 66, "Fan TF01", size=13, bold=True)
js_text(fx, dy - 46, "FAN_FDB", [(0, "stopped", "#5F6368"), (1, "running", GREEN)], size=14)
g.text(fx, dy + 100, "cmd", size=11, colour="#5F6368")
g.lamp(fx + 28, dy + 100, B("FAN_CMD", "SEQ/Outputs/Fan_Cmd"), d=14)
g.text(fx, dy + 120, "feedback", size=11, colour="#5F6368")
g.lamp(fx + 56, dy + 120, "FAN_FDB", d=14)
# pressure
qx = px + 480
g.text(qx, dy - 66, "Duct pressure PE1", size=13, bold=True)
value(qx, dy - 46, B("PRES", "SEQ/Sim/Duct_Pressure"), "Pa", 0)
g.line(qx + 30, dy - 22, qx + 30, dy, "#5F6368", 2)
g.items.append(f'<Ellipse Fill="#FFFFFF" Height="10" Left="{qx + 25}" Stroke="#5F6368" StrokeWidth="2" '
               f'Top="{dy - 5}" Width="10"/>')
g.text(px + 16, py + 360, "Demand", size=12, colour="#5F6368")
g.lamp(px + 80, py + 360, B("DEMAND", "SEQ/Seq/Demand"), d=14)
g.text(px + 120, py + 360, "Supervision", size=12, colour="#5F6368")
g.bar(px + 200, py + 363, B("SUP_PCT", "SEQ/Hmi/Sup_Pct"), w=200, h=10, colour=AMBER)
value(px + 410, py + 358, B("SUP_T", "SEQ/Seq/Sup_Time"), "s", 1, 12, "#5F6368")
g.text(px + 470, py + 360, "Checking req.", size=12, colour="#5F6368")
value(px + 560, py + 358, B("RQ_AT", "SEQ/Seq/RQ_AT"), "", 0, 12, "#5F6368")

# ---- test switches ----------------------------------------------------------------------------------------------
ty = py + 420
g.rect(px, ty, 680, 120, fill="#FFF8E1", stroke="#F9AB00", radius=8)
g.text(px + 16, ty + 12, "TEST (fault injection)", size=12, bold=True, colour="#B06000")
toggle(px + 16, ty + 40, 200, 34, B("F_DAMPER", "Cmd/Fault_Damper/Value"), "Damper does not open", AMBER)
toggle(px + 236, ty + 40, 200, 34, B("F_FAN", "Cmd/Fault_Fan/Value"), "Fan feedback lost", AMBER)
g.text(px + 16, ty + 88, "Last sequence alarm: step", size=12, colour="#5F6368")
js_text(px + 172, ty + 87, B("AL_STEP", "SEQ/Seq/AL_Step"),
        [(0, "-", "#5F6368")] + [(k, f"{k} {n.title()}", RED) for k, n, *_ in STEPS], size=12)
g.text(px + 380, ty + 88, "requirement", size=12, colour="#5F6368")
value(px + 456, ty + 86, B("AL_REQ", "SEQ/Seq/AL_Req"), "", 0, 12, RED)

# ---- steps panel ------------------------------------------------------------------------------------------------
sx, sy, sw = 720, 90, 560
g.rect(sx, sy, sw, 770, fill="#FFFFFF", stroke="#1F2A36", sw=2, radius=8)
g.text(sx + 16, sy + 12, "Start / stop steps", size=16, bold=True)
g.text(sx + sw - 16, sy + 16, "settle / supervision per step", size=11, colour="#5F6368", align="Right")
y = sy + 44
for k, name, does, reqs, settle, tmax in STEPS:
    if k == FIRST_STOP:
        g.text(sx + 16, y, "STOP", size=11, bold=True, colour="#5F6368"); y += 18
    h = 52 + 18 * len(reqs)
    st = B(f"ST{k}", f"SEQ/Hmi/ST{k}")
    rect_by(sx + 10, y, sw - 20, h, st, {0: "#F8F9FA", 1: "#E0F2F1", 2: "#FFFFFF", 3: "#FCE8E6"})
    circle_by(sx + 22, y + 10, 24, st, {0: "#DADCE0", 1: TEAL, 2: GREEN, 3: RED})
    js_text(sx + 34, y + 14, st, [(0, str(k), "#3C4043"), (1, str(k), "#FFFFFF"), (2, "✓", "#FFFFFF"),
                                  (3, "!", "#FFFFFF")], size=13, align="Center")
    g.text(sx + 56, y + 8, name.title(), size=15, bold=True)
    g.text(sx + 56, y + 28, does + (f"  (settle {settle:g} s)" if settle else ""), size=11, colour="#5F6368")
    js_text(sx + sw - 90, y + 10, st, [(0, "max", GREY), (1, "active", TEAL), (2, "done in", GREEN),
                                       (3, "ALARM", RED)], size=11, align="Right")
    value(sx + sw - 82, y + 8, B(f"SHOW{k}", f"SEQ/Hmi/SHOW{k}"), "s", 1, 13, "#3C4043")
    for j, r in enumerate(reqs, 1):
        ry = y + 46 + 18 * (j - 1)
        g.text(sx + 56, ry, f"– {r}", size=12, colour="#3C4043")
        js_text(sx + sw - 24, ry, B(f"RS{k}_{j}", f"SEQ/Hmi/RS{k}_{j}"),
                [(0, "", GREY), (1, "OK", GREEN), (2, "CHECKING", AMBER), (3, "next", GREY), (4, "NOT MET", RED)],
                size=12, align="Right")
    y += h + 8

g.save(os.path.join(HERE, "FanSeq.tgml"))
json.dump(binds, open(os.path.join(HERE, "hmi_binds.json"), "w"), indent=1)
missing = [b for b in g.binds if b not in binds]
if missing:
    sys.exit(f"bind names without a target: {missing}")
print(f"FanSeq.tgml: {len(g.items)} items, {len(binds)} bind names")
