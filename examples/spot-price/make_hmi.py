#!/usr/bin/env python3
"""make_hmi.py [AREA] - SpotPrice.tgml: operator graphic of the spot price load, and hmi_binds.json (bind name ->
target relative to the example folder).

Header: the load and why. Left: the price now (big), rank, today's average / min / max, the bridge's state.
Middle: the upcoming hours as bars (from the running hour, as far as prices are known), coloured: chosen hours
green, above the block limit red, at or below the force limit blue, others grey; the running hour outlined; the
two limits as lines. Right: the settings (price control, mode, N of each mode, limits) and the held plan.
"""
import json, os, sys
from xml.sax.saxutils import escape
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "scripts"))
from tgml import Graphic, FONT

AREA = sys.argv[1] if len(sys.argv) > 1 else "FI"
HORIZON = 36
W, H = 1300, 880
g = Graphic(W, H, background="#EEF1F4")
binds = {}
GREY, GREEN, RED, BLUE, AMBER, TEAL = "#9AA0A6", "#1E8E3E", "#D93025", "#1A73E8", "#E37400", "#00796B"


def B(name, target):
    binds[name] = target
    return name


def panel(x, y, w, h, title):
    g.rect(x, y, w, h, fill="#FFFFFF", stroke="#DADCE0", radius=8)
    g.text(x + 16, y + 12, title, size=13, bold=True, colour="#5F6368")


# ---- header --------------------------------------------------------------------------------------------------
g.rect(0, 0, W, 72, fill="#1F2933")
g.text(20, 12, "SPOT PRICE LOAD", size=26, bold=True, colour="#FFFFFF")
g.text(22, 46, f"Storage heater run by the day-ahead price, area {AREA}", size=12, colour="#C4C7C5")
g.text_by(470, 14, B("REASON", "SPOT/Ctl/Reason"), [
    (0, "PRICE CONTROL OFF - normal operation", "#C4C7C5"), (1, "CHOSEN HOUR - load on", "#81C995"),
    (2, "NOT A CHOSEN HOUR - load off", "#C4C7C5"), (3, "PRICE ABOVE BLOCK LIMIT - load off", "#F28B82"),
    (4, "PRICE AT OR BELOW FORCE LIMIT - load on", "#8AB4F8"), (5, "NO PRICE DATA - normal operation", "#FDD663")],
    size=20, default="-")
g.text(470, 46, "load", size=12, colour="#C4C7C5")
g.circle_by(508, 44, 18, B("LOAD", "SPOT/Ctl/Load_Cmd"), {0: "#5F6368", 1: GREEN})
g.text(1080, 12, "ALARMS  (ring = gone, not acknowledged)", size=11, colour="#C4C7C5")
g.alarm_state(1080, 34, B("AL_INV", "SPOT/Alarms/Price_Invalid"), d=16, colour=AMBER, blink=False)
g.text(1104, 34, "no valid price", size=12, colour="#FFFFFF")
g.alarm_state(1080, 52, B("AL_STOP", "SPOT/Alarms/Bridge_Stopped"), d=16, colour=AMBER, blink=False)
g.text(1104, 52, "bridge stopped", size=12, colour="#FFFFFF")

# ---- price now ---------------------------------------------------------------------------------------------------
panel(20, 92, 300, 330, "PRICE NOW")
UNITS = [(0, "c/kWh", "#202124"), (1, "EUR/MWh", "#202124")]
g.value(36, 120, B("PRICE", "SPOT/Hmi/Disp_Price"), decimals=2, size=40, colour="#202124")
g.text_by(200, 138, B("UNIT", "Set/Unit_MWh/Value"), UNITS, size=18, default="c/kWh")
g.text_by(38, 176, B("RES15", "SPOT/Ctl/Res15"), [(0, "this hour, VAT 0 %", "#5F6368"), (1, "this quarter, VAT 0 %", "#5F6368")], size=11, bold=False, default="VAT 0 %")
g.text(36, 204, "rank today", size=13, colour="#5F6368")
g.value(170, 202, B("RANK", "SPOT/Inputs/Rank"), decimals=0, unit="/ 24", size=16, colour="#202124")
for n, (lab, key) in enumerate((("average", "avg"), ("min", "min"), ("max", "max"))):
    g.text(36, 236 + 26 * n, f"{lab} today", size=13, colour="#5F6368")
    g.value(170, 234 + 26 * n, B(f"D_{key.upper()}", f"SPOT/Hmi/Disp_{key.capitalize()}"), decimals=2, size=15,
            colour="#202124")
    g.text_by(246, 236 + 26 * n, "UNIT", [(0, "c/kWh", "#5F6368"), (1, "EUR/MWh", "#5F6368")], size=12, bold=False,
              default="c/kWh")
g.text(36, 324, "bridge", size=13, colour="#5F6368")
g.lamp(170, 324, B("VALID", "SPOT/Inputs/Valid"), on=GREEN, off=RED)
g.text(196, 324, "valid", size=13, colour="#5F6368")
g.text(36, 350, "last beat", size=13, colour="#5F6368")
g.value(170, 348, B("BEAT_AGE", "SPOT/Ctl/Beat_Age"), decimals=0, unit="s ago", size=15, colour="#202124")
g.text(36, 376, "hours known", size=13, colour="#5F6368")
g.value(170, 374, B("KNOWN", "SPOT/Inputs/Known"), decimals=0, size=15, colour="#202124")

# ---- upcoming hours ------------------------------------------------------------------------------------------------
GX, GY, GW, GH = 340, 92, 940, 330
panel(GX, GY, GW, GH, "")
g.text_by(GX + 16, GY + 12, "RES15", [(0, "UPCOMING HOURS  (from the running hour, 36 h, VAT 0 %)", "#5F6368"), (1, "UPCOMING QUARTERS  (from the running quarter, 9 h, VAT 0 %)", "#5F6368")], size=13, default="UPCOMING PRICES")
LO, HI = -10.0, 40.0                                   # scale of the graph
X0, Y_TOP, Y_BOT = GX + 50, GY + 50, GY + GH - 46      # plot area
SC = (Y_BOT - Y_TOP) / (HI - LO)
Y0 = Y_BOT + LO * SC                                   # y of 0 c/kWh
BW = (GX + GW - 20 - X0) / HORIZON


def y_of(v):
    return Y0 - v * SC


for v in range(int(LO), int(HI) + 1, 10):
    g.line(X0 - 4, y_of(v), GX + GW - 20, y_of(v), stroke="#E8EAED" if v else "#5F6368", sw=1)
    g.text_by(X0 - 10, y_of(v) - 8, "UNIT", [(0, f"{v}", "#5F6368"), (1, f"{v * 10}", "#5F6368")], size=11,
              bold=False, align="Right", default=f"{v}")
g.text_by(X0 - 44, Y_TOP - 22, "UNIT", UNITS, size=11, bold=False, default="c/kWh")


def limit_line(name, colour, label):
    """Horizontal line at the value of a setting."""
    g._bind(name)
    g.items.append(
        f'<Line Stroke="{colour}" StrokeWidth="1.5" StrokeDashArray="6,4" X1="{X0}" X2="{GX + GW - 20:.1f}" '
        f'Y1="{Y0:.1f}" Y2="{Y0:.1f}"><Bind Name="{name}"><Script OnSignalChange="signal"><![CDATA[function '
        f'signal(evt){{var l=evt.getTarget().getParentNode();var v=new Number(evt.getValue());if(v<{LO})v={LO};'
        f'if(v>{HI})v={HI};var y={Y0:.2f}-v*{SC:.4f};l.setAttribute("Y1",y);l.setAttribute("Y2",y);}}]]>'
        f'</Script></Bind></Line>')


for k in range(HORIZON):
    x = X0 + k * BW + 2
    g._bind(B(f"U{k}", f"SPOT/Hmi/G{k}"))
    cls = B(f"C{k}", f"SPOT/Hmi/U{k}")
    cv = "".join(f'<ConvertValue AttributeValue="{c}" SignalEqualTo="{v}"/>'
                 for v, c in {0: GREY, 1: GREEN, 2: RED, 3: BLUE, 4: "#F1F3F4"}.items())
    g._bind(cls)
    stroke = ' Stroke="#202124" StrokeWidth="2"' if k == 0 else ' Stroke="None"'
    g.items.append(
        f'<Rectangle Fill="{GREY}" Height="1" Left="{x:.1f}" Top="{Y0:.1f}" Width="{BW - 4:.1f}"{stroke}>'
        f'<Bind Name="U{k}"><Script OnSignalChange="signal"><![CDATA[function signal(evt){{var r=evt.getTarget()'
        f'.getParentNode();var v=new Number(evt.getValue());if(v<{LO})v={LO};if(v>{HI})v={HI};var h=Math.abs(v)*'
        f'{SC:.4f};r.setAttribute("Height",Math.max(1,h));r.setAttribute("Top",v>=0?{Y0:.2f}-h:{Y0:.2f});}}]]>'
        f'</Script></Bind><Bind Attribute="Fill" Name="{cls}">{cv}</Bind></Rectangle>')
    if k % 3 == 0:                                         # time of day under every third bar (hh:mm)
        g._bind(B(f"L{k}", f"SPOT/Hmi/L{k}"))
        g.items.append(
            f'<Text FontFamily="{FONT}" FontSize="11" HorizontalAlign="Center" Left="{x + BW / 2 - 2:.1f}" '
            f'Stroke="#5F6368" Top="{Y_BOT + 8}"><Bind Name="L{k}"><Script OnSignalChange="signal"><![CDATA['
            f'function signal(evt){{var t=evt.getTarget().getParentNode();var m=Math.round(new Number('
            f'evt.getValue()));var h=Math.floor(m/60),n=m%60;t.setAttribute("Content",(h<10?"0":"")+h+":"+'
            f'(n<10?"0":"")+n);}}]]></Script></Bind>--</Text>')
limit_line(B("L_BLOCK", "Set/Block_Above/Value"), RED, "block")
limit_line(B("L_FORCE", "Set/Force_Below/Value"), BLUE, "force")
g.text(X0 - 8, Y_BOT + 26, "now", size=11, bold=True, colour="#202124")
lx = X0 + 40
for c, t in ((GREEN, "chosen"), (GREY, "not chosen"), (RED, "above block limit (line)"),
             (BLUE, "at or below force limit (line)")):
    g.rect(lx, Y_BOT + 28, 12, 12, fill=c, stroke="None")
    g.text(lx + 18, Y_BOT + 26, t, size=11, colour="#5F6368")
    lx += 40 + 7 * len(t)

# ---- settings ------------------------------------------------------------------------------------------------------
panel(20, 442, 620, 418, "SETTINGS")
row = lambda n: 482 + 42 * n
g.text(36, row(0) + 8, "Price control", size=14, colour="#202124")
g.toggle(250, row(0), 120, 34, B("CTL", "Set/Ctl_On/Value"), "On", GREEN)
g.set_button(400, row(0), 100, 34, B("RES", "Set/Res/Value"), 0, "Hourly")
g.set_button(510, row(0), 110, 34, "RES", 1, "15 min")
g.text(400, row(0) - 16, "prices for the limits and the graph", size=10, colour="#5F6368")
g.text(36, row(1) + 8, "Choose hours by", size=14, colour="#202124")
g.set_button(250, row(1), 170, 34, B("MODE", "Set/Mode/Value"), 0, "N cheapest hours")
g.set_button(430, row(1), 190, 34, "MODE", 1, "Cheapest N in a row")
g.text(36, row(2) + 8, "N cheapest hours of today", size=14, colour="#202124")
g.step_button(250, row(2) + 4, B("N_CHEAP", "Set/N_Cheap/Value"), -1, "-", lo=1, hi=24)
g.value(286, row(2) + 4, "N_CHEAP", decimals=0, unit="h", size=16, colour="#0B57D0")
g.step_button(336, row(2) + 4, "N_CHEAP", 1, "+", lo=1, hi=24)
g.text(36, row(3) + 8, "Cheapest N hours in a row", size=14, colour="#202124")
g.step_button(250, row(3) + 4, B("N_BLOCK", "Set/N_Block/Value"), -1, "-", lo=1, hi=12)
g.value(286, row(3) + 4, "N_BLOCK", decimals=0, unit="h", size=16, colour="#0B57D0")
g.step_button(336, row(3) + 4, "N_BLOCK", 1, "+", lo=1, hi=12)
g.text(380, row(3) + 8, "(1 to 12)", size=12, colour="#5F6368")
g.text(36, row(4) + 8, "Off above (block limit)", size=14, colour="#202124")
g.value(250, row(4) + 6, "L_BLOCK", decimals=2, unit="c/kWh", size=16, colour=RED)
g.text(36, row(5) + 8, "On at or below (force limit)", size=14, colour="#202124")
g.value(250, row(5) + 6, "L_FORCE", decimals=2, unit="c/kWh", size=16, colour=BLUE)
g.text(400, row(4) + 8, "click a number to change it", size=11, colour="#5F6368")
g.text(36, row(6) + 8, "Normal operation demand", size=14, colour="#202124")
g.toggle(250, row(6), 120, 34, B("NORMAL", "Set/Normal_Demand/Value"), "Demand", AMBER)
g.text(380, row(6) + 8, "(stands in for a thermostat)", size=11, colour="#5F6368")
g.text(36, row(7) + 8, "Show prices in", size=14, colour="#202124")
g.set_button(250, row(7), 100, 34, "UNIT", 0, "c/kWh")
g.set_button(360, row(7), 110, 34, "UNIT", 1, "EUR/MWh")
g.text(480, row(7) + 10, "(settings stay in c/kWh)", size=11, colour="#5F6368")
g.text(36, row(8) + 4, "Without valid prices, or with price control off, the load follows normal operation.",
       size=11, colour="#5F6368")

# ---- the plan ------------------------------------------------------------------------------------------------------
panel(660, 442, 620, 418, "PLAN")
g.text_by(676, 486, B("BMODE", "SPOT/Ctl/Block_Mode"), [(0, "N cheapest hours of today", "#202124"),
          (1, "cheapest hours in a row: block held until it has run", "#202124")], size=15, default="-")
g.text(676, 530, "N-th cheapest price today", size=13, colour="#5F6368")
g.value(930, 528, B("N_PRICE", "SPOT/Hmi/Disp_N_Price"), decimals=2, size=15, colour="#202124")
g.text_by(1010, 530, "UNIT", [(0, "c/kWh", "#5F6368"), (1, "EUR/MWh", "#5F6368")], size=12, bold=False,
          default="c/kWh")
g.text(676, 566, "block planned", size=13, colour="#5F6368")
g.lamp(930, 566, B("PLANNED", "SPOT/Plan/Planned"), on=TEAL)
g.text(676, 596, "starts in", size=13, colour="#5F6368")
g.value(930, 594, B("P_WAIT", "SPOT/Plan/Plan_Wait"), decimals=0, unit="h", size=15, colour="#202124")
g.text(676, 626, "hours left of it", size=13, colour="#5F6368")
g.value(930, 624, B("P_LEFT", "SPOT/Plan/Plan_Left"), decimals=0, unit="h", size=15, colour="#202124")
g.text(676, 656, "running now", size=13, colour="#5F6368")
g.lamp(930, 656, B("INBLOCK", "SPOT/Plan/In_Block"), on=GREEN)
g.text(676, 686, "cheapest block now starts in", size=13, colour="#5F6368")
g.value(930, 684, B("B_IN", "SPOT/Block/Best_In"), decimals=0, unit="h", size=15, colour="#202124")
g.text(676, 730, "The block is planned again only when it has run, or while it still waits when more hours",
       size=11, colour="#5F6368")
g.text(676, 746, "become known (tomorrow's prices, about 14:00) or N changes: no postponing for ever.", size=11,
       colour="#5F6368")

g.save(os.path.join(HERE, "SpotPrice.tgml"))
json.dump(binds, open(os.path.join(HERE, "hmi_binds.json"), "w"), indent=1)
print(f"SpotPrice.tgml: {len(g.items)} items, {len(g.binds)} bind names")
