#!/usr/bin/env python3
"""make_mqtt.py: the AHU01 signals published over MQTT, and the driver commands that set the publication up.

    python3 make_mqtt.py ['/Server 1'] [AHU01]     -> mqtt_points.json, mqtt_points.ps1, checks every point
    python3 make_mqtt.py --chunks                  -> "group chunk" lines, one driver call each (deploy_fuxa.sh)
    python3 make_mqtt.py --seen broker.txt         -> how many of the topics an `ebo.sh mqtt` listing holds

EBO publishes through an MQTT client object (`/Server 1/IoT/Broker`, broker on the same machine, value format
`@(Value)`) and its Data Groups. A data point's topic is its EBO path without the leading slash, so the AHU
signals arrive under a subtree of their own:

    Server 1/AHU01/AHU/<Module>/<Signal>          payload = the plain value (binary 0 / 1, alarm state 0 ... 5)

A free prefix such as "ahu01/..." per point is not available with what has been proven (findings, section MQTT):
the Data Group has a Topic field, and only "empty = EBO path" has been seen working; what a filled-in Topic does
with several points (one message for the group, joined with the client's message start / delimiter / end, is
the guess) has not been tried. The unit's own topic root is therefore `Server 1/<folder>/AHU/`.

The points are the controller signals the EBO graphic shows (make_hmi.py, hmi_binds.json), less the sensor
instant fault flags and the operator setpoints, split over three Data Groups (at most 10 per client), each filled
in chunks so that one driver call stays well inside its time limit.
"""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.join(HERE, "..", "..", "scripts")
sys.path.insert(0, SKILL)

PROGRAM = "AHU"                 # program object inside the folder (deploy.sh: Fb-Load '<server>/<folder>' 'AHU')
CLIENT = "Broker"               # MQTT client under /<server>/IoT, shared with other examples (DH-ex2 uses it too)
CHUNK = 17                      # data points per driver call (picker: about 10 to 20 s per point)
DEG = "\xb0C"

# tag (= bind name in make_hmi.py), Module/Signal, label, unit, decimals (None = binary or state number)
MEAS = [
    *[(t, f"Inputs/{t}", f"Temperature {t}", DEG, 1) for t in
      ("TE00", "TE1", "TE2", "TE3", "TE4", "TE5", "TE6", "TE7", "TE8", "TE10_1", "TE10_2", "TE10_3")],
    ("OT_DAY", "Inputs/OT_Day_Mean", "Previous day outdoor mean", DEG, 1),
    ("ROOM_AVG", "Inputs/Room_Avg", "Room mean", DEG, 1),
    *[(p, f"Inputs/{p}", f"Pressure {p}", "Pa", 1) for p in ("PE1", "PE2", "PDE1", "PDE2", "PDE3", "PDE4", "PDE10", "PDE20")],
    ("Q_SUP", "Inputs/Supply_Flow", "Supply air flow", "m3/s", 2),
    ("Q_EXH", "Inputs/Exhaust_Flow", "Extract air flow", "m3/s", 2),
    ("HRU_EFF", "HRU/HRU_Efficiency", "Heat recovery efficiency", "%", 1),
]
CTRL = [
    # control outputs
    ("FZ01", "Outputs/FZ01_Cmd", "Outdoor air damper open", "", None),
    ("FZ02", "Outputs/FZ02_Cmd", "Exhaust air damper open", "", None),
    ("SC3", "Outputs/SC3_Ctrl", "Rotor speed", "%", 1),
    ("SC3_CMD", "Outputs/SC3_Cmd", "Rotor start", "", None),
    ("TV1", "Outputs/TV1_Ctrl", "Heating valve", "%", 1),
    ("P1_CMD", "Outputs/P1_Cmd", "Pump P1 command", "", None),
    ("TV2", "Outputs/TV2_Ctrl", "Cooling valve", "%", 1),
    ("TF01", "Outputs/TF01_Ctrl", "Supply fan speed", "%", 1),
    ("TF01_CMD", "Outputs/TF01_Cmd", "Supply fan start", "", None),
    ("PF01", "Outputs/PF01_Ctrl", "Extract fan speed", "%", 1),
    ("PF01_CMD", "Outputs/PF01_Cmd", "Extract fan start", "", None),
    # states and modes
    ("RUN", "Operation/Run", "Unit running", "", None),
    ("RUN_MODE", "Operation/Run_Mode", "Run mode (0 stopped, 1 normal, 2 night cooling, 3 night heating, 4 alarm stop)", "", None),
    ("AOM", "Operation/AOM", "Mode selector (0 off, 1 manual, 2 auto)", "", None),
    ("SEASON_SEL", "Operation/Season_Sel", "Season selector (0 auto, 1 heating, 2 cooling)", "", None),
    ("SEASON", "Operation/Season_Mode", "Season in use (0 heating, 1 cooling)", "", None),
    ("NIGHT_COOL", "Operation/Night_Cooling", "Night cooling", "", None),
    ("NIGHT_HEAT", "Operation/Night_Heating", "Night heating", "", None),
    ("HEAT_MODE", "Operation/Heating_Mode", "Warm water in cooling coil (0 chilled, 1 warm)", "", None),
    ("HS10_EXT", "Operation/HS10_Ext", "Extended run active", "", None),
    ("P1_FDB", "Inputs/P1_Fdb", "Pump P1 running", "", None),
    ("TF01_FDB", "Inputs/TF01_Fdb", "Supply fan running", "", None),
    ("PF01_FDB", "Inputs/PF01_Fdb", "Extract fan running", "", None),
    ("SC3_OK", "Inputs/SC3_Fault", "Rotor drive healthy (1 = normal)", "", None),
    ("HS10", "Inputs/HS10", "Extended run button", "", None),
    ("SB01", "Inputs/SB01", "Emergency stop (1 = normal)", "", None),
    ("FA01", "Inputs/FA01", "Fire alarm contact (1 = normal)", "", None),
    ("FROST", "HRU/Frost_Active", "Rotor frost limit active", "", None),
    ("FREEZE", "Alarms/Freeze_Latch", "Freeze protection tripped", "", None),
    # setpoints in use
    ("ACT_SP", "ST/Active_SP", "Supply temperature setpoint in use", DEG, 1),
    ("PE1_SP", "FAN/Supply_Pressure_SP", "Supply pressure setpoint in use", "Pa", 1),
    ("PE2_SP", "FAN/Exhaust_Pressure_SP", "Extract pressure setpoint in use", "Pa", 1),
    ("PDE4_SP", "HRU/PDE4_SP", "Rotor frost pressure limit", "Pa", 1),
]
# alarms of the description, section 5: name, class, label. Payload = alarm object state (findings: 0 normal,
# 1 alarm, 2 acknowledged, 3 reset not acknowledged, 4 disabled, 5 fault); Critical_Alarm is a plain 0 / 1.
ALARMS = [
    ("Freeze_Alm", "A", "Freeze protection"), ("Fire_Alm", "A", "Fire alarm FA01"),
    ("Stop_Alm", "A", "Emergency stop SB01"), ("P1_Alm", "A", "Pump P1 not running"),
    ("HN_Pres_Alm", "A", "Heat supply pressure"), ("HN_Temp_Alm", "A", "Heat supply temperature"),
    ("Supply_Fire_Alm", "A", "Supply air fire limit"), ("Exhaust_Fire_Alm", "A", "Extract air fire limit"),
    ("TE00_Alm", "B", "Sensor TE00"), *[(f"TE{i}_Alm", "B", f"Sensor TE{i}") for i in range(1, 9)],
    *[(f"TE10_{i}_Alm", "B", f"Sensor TE10.{i}") for i in range(1, 4)],
    ("Supply_Temp_Alm", "B", "Supply temp. deviation"), ("Supply_Pres_Alm", "B", "Supply pressure dev."),
    ("Exhaust_Pres_Alm", "B", "Extract pressure dev."), ("TF01_Alm", "B", "Supply fan TF01"),
    ("PF01_Alm", "B", "Extract fan PF01"), ("HRU_Alm", "B", "Rotor drive SC3"),
    ("HRU_Frost_Alm", "B", "Rotor icing"), ("HRU_Efficiency_Alm", "B", "Rotor efficiency low"),
    ("HeatR_Alm", "B", "Heating coil no effect"), ("CoolR_Alm", "B", "Cooling coil no effect"),
    ("PDE3_Alm", "C", "Supply filter 1 dirty"), ("PDE1_Alm", "C", "Supply filter 2 dirty"),
    ("PDE2_Alm", "C", "Extract filter dirty"),
]
ALM = [("CRIT", "Alarms/Critical_Alarm", "Critical alarm", "", None)] + \
      [(n, f"Alarms/{n}", f"{label} (class {cls})", "", None) for n, cls, label in ALARMS]

GROUPS = [("AHU01_Meas", MEAS), ("AHU01_Ctrl", CTRL), ("AHU01_Alarms", ALM)]   # Data Group name -> points
ALARM_CLASS = {n: cls for n, cls, _ in ALARMS}


def points(server="/Server 1", folder="AHU01"):
    """-> [dict]: tag, group, module/signal, picker path (tree parts under the server), property, topic, ..."""
    seg = server.strip("/").split("/")                       # '/Server 1' -> ['Server 1']; deeper servers allowed
    under = seg[1:] + folder.strip("/").split("/")           # folders between the server and the program
    out = []
    for group, rows in GROUPS:
        for tag, target, label, unit, digits in rows:
            mod, sig = target.split("/")
            out.append({"tag": tag, "group": group, "target": target, "label": label, "unit": unit,
                        "digits": digits, "path": under + [PROGRAM, mod], "property": sig,
                        "topic": "/".join(seg[:1] + under + [PROGRAM, mod, sig])})
    return out


def check(pts):
    """Every point must be a public signal of the program and (where they list it) agree with io.json / hmi_binds.json."""
    import ebox
    with open(os.path.join(HERE, "AHU01.aut"), encoding="latin-1") as f:
        top, *_ = ebox.parse_aut(f.read())
    public = set()
    for _, sc in top.walk():                                   # HFB insides too: their blocks carry Module\Name
        for b in sc.blocks.values():
            if b.public and "\\" in b.name:
                public.add(b.name.replace("\\", "/"))
    io = json.load(open(os.path.join(HERE, "io.json"), encoding="utf-8"))
    listed = {r.get("block") for r in io["inputs"]} | {r.get("signal") for r in io["outputs"]} | \
             {r["path"] for k in ("setpoints", "alarms", "states") for r in io[k]}
    hb = json.load(open(os.path.join(HERE, "hmi_binds.json"), encoding="utf-8"))["controller"]
    bad, tags, topics, not_io = [], set(), set(), []
    for p in pts:
        if p["target"] not in public:
            bad.append(f"{p['tag']}: {p['target']} is not a public signal of AHU01.aut")
        if p["tag"] in hb and hb[p["tag"]] != p["target"]:
            bad.append(f"{p['tag']}: hmi_binds.json says {hb[p['tag']]}, here {p['target']}")
        if p["tag"] not in hb:
            bad.append(f"{p['tag']}: not a bind of the EBO graphic (hmi_binds.json)")
        if p["target"] not in listed:
            not_io.append(p["target"])
        if p["tag"] in tags or p["topic"] in topics:
            bad.append(f"{p['tag']}: twice")
        tags.add(p["tag"]); topics.add(p["topic"])
    return bad, not_io


def ps1(pts, server, client_parent):
    """PowerShell for the driver: the point lists and three helpers built on the driver's own functions."""
    q = lambda s: "'" + str(s).replace("'", "''") + "'"
    L = ["# written by make_mqtt.py: AHU01 data points for the EBO MQTT client. Dot-source after ebo.ps1.",
         f"$MQ_IOT = {q(client_parent)}; $MQ_CLIENT = {q(client_parent + '/' + CLIENT)}",
         "$MQ = [ordered]@{}"]
    for group, _ in GROUPS:
        rows = [p for p in pts if p["group"] == group]
        L.append(f"$MQ[{q(group)}] = @(" + ",".join(
            "@(@(" + ",".join(q(x) for x in p["path"]) + ")," + q(p["property"]) + ")" for p in rows) + ")")
    L.append(r'''
# Like Dp-Pick (ebo.ps1), for modules with more rows than the picker shows: rows scrolled out of view are skipped
# instead of clicked at a position outside the list, and when no visible row matches, the selection is walked
# down with the arrow key, reading the Path box each step. The arrow-key walk is NOT yet seen working.
function Ahu-Pick($parts, $prop) {
  $d = Fg-Root; $n = $d
  $first = New-Object System.Windows.Automation.AndCondition((New-Object System.Windows.Automation.PropertyCondition($A::NameProperty, "/$($parts[0])")), (New-Object System.Windows.Automation.PropertyCondition($A::ControlTypeProperty, $CT::TreeItem)))
  $t = [Diagnostics.Stopwatch]::StartNew()
  while ($t.Elapsed.TotalSeconds -lt 10 -and -not $d.FindFirst($TS::Descendants, $first)) { Start-Sleep -Milliseconds 300 }
  foreach ($p in $parts) {
    $c = New-Object System.Windows.Automation.AndCondition((New-Object System.Windows.Automation.PropertyCondition($A::NameProperty, "/$p")), (New-Object System.Windows.Automation.PropertyCondition($A::ControlTypeProperty, $CT::TreeItem)))
    $n = $n.FindFirst($TS::Descendants, $c); if (-not $n) { Keys '{ESC}'; throw "no tree item $p" }
    try { $n.GetCurrentPattern([System.Windows.Automation.ExpandCollapsePattern]::Pattern).Expand() } catch {}; Start-Sleep -Milliseconds 900
  }
  Ui-Click (Ui-ById $n 'objectNameTextBlock' 2); Start-Sleep -Milliseconds 1500
  $vp = $d.FindFirst($TS::Descendants, (New-Object System.Windows.Automation.PropertyCondition($A::ControlTypeProperty, $CT::Edit))).GetCurrentPattern([System.Windows.Automation.ValuePattern]::Pattern)
  $done = { Ui-Invoke (Ui-Find $d 'Select' $CT::Button 3); Start-Sleep -Milliseconds 800; "$($parts -join '/')/$prop" }
  $all = @($d.FindAll($TS::Descendants, (New-Object System.Windows.Automation.PropertyCondition($A::ControlTypeProperty, $CT::DataItem))) | ? { -not $_.Current.BoundingRectangle.IsEmpty })
  $rows = @($all | ? { -not $_.Current.IsOffscreen }); if (-not $rows.Count) { $rows = $all }
  foreach ($r in $rows) {
    $b = $r.Current.BoundingRectangle
    Click ([int]($b.X + 200)) ([int]($b.Y + $b.Height / 2)); Start-Sleep -Milliseconds 150
    if (($vp.Current.Value -replace '.*/', '') -eq $prop) { return (& $done) }
  }
  if ($rows.Count) {                                          # walk on below the visible rows
    $last = $vp.Current.Value; $same = 0
    for ($i = 0; $i -lt 250 -and $same -lt 3; $i++) {
      Keys '{DOWN}'; Start-Sleep -Milliseconds 150; $v = $vp.Current.Value
      if (($v -replace '.*/', '') -eq $prop) { return (& $done) }
      if ($v -eq $last) { $same++ } else { $same = 0; $last = $v }
    }
  }
  Keys '{ESC}'; throw "property $prop not found under $($parts -join '/')"
}
# Add points to the Data Group whose page is on screen; a point that cannot be picked is reported, not fatal.
function Ahu-Points($points) {
  $script:AhuOk = 0
  foreach ($p in $points) {
    $add = Ui-ById (Prop-Grid) 'AddButton' 5; if (-not $add) { throw 'no Data points add button on this page' }
    Ws-Front; Ui-Click $add; if (-not (Wait-Fg '^Select Object' 8)) { throw 'data point picker did not open' }
    try { Log ('data point ' + (Ahu-Pick $p[0] $p[1])); $script:AhuOk++ }
    catch { Log "MISSING $($p[0] -join '/')/$($p[1]): $($_.Exception.Message)"; if (Wait-Fg '^Select Object' 1) { Keys '{ESC}'; Start-Sleep 1 } }
  }
}
# Interface and client if missing (Mq-Client sets host 127.0.0.1, no TLS, value format @(Value)); earlier AHU01
# groups are deleted, since their data points pointed at objects that deploy.sh has deleted and imported again.
function Ahu-MqSetup {
  $srv = $MQ_IOT.Substring(0, $MQ_IOT.LastIndexOf('/')); $iot = $MQ_IOT.Substring($MQ_IOT.LastIndexOf('/') + 1)
  $cl = $MQ_CLIENT.Substring($MQ_CLIENT.LastIndexOf('/') + 1); Ws-Front
  if (-not (Ws-TreeItem $MQ_IOT)) { Log (Ws-New $srv 'IoT Interface' $iot) }
  if (-not (Ws-TreeItem $MQ_CLIENT)) { Log (Mq-Client $MQ_IOT $cl) } else { Log "client $MQ_CLIENT is there" }
  foreach ($g in $MQ.Keys) { if (Ws-TreeItem "$MQ_CLIENT/$g") { Log (Ws-Delete "$MQ_CLIENT/$g") } }
}
# One chunk of one group: chunk 0 creates the group (event driven, every 10 s), later chunks add to it.
function Ahu-MqChunk($group, $chunk, $size) {
  $all = $MQ[$group]; $pts = @()
  for ($k = $chunk * $size; $k -lt [Math]::Min($all.Count, ($chunk + 1) * $size); $k++) { $pts += ,$all[$k] }
  if ($chunk -eq 0) { Log (Mq-Group $MQ_CLIENT $group @() 10) } else { [void](Ws-Select "$MQ_CLIENT/$group"); Start-Sleep 3 }
  Ahu-Points $pts
  if ($script:AhuOk) { Ws-Save }
  Log "group ${group}: chunk $chunk added $($script:AhuOk) of $($pts.Count); listed now $(@(Mq-Listed).Count) of $($all.Count)"
}
''')
    return "\n".join(L) + "\n"


def main(argv):
    if argv and argv[0] == "--chunks":
        for group, rows in GROUPS:
            for i in range((len(rows) + CHUNK - 1) // CHUNK):
                print(group, i, CHUNK)
        return 0
    if argv and argv[0] == "--seen":
        seen = {l.rstrip("\r\n").rsplit(" ", 1)[0] for l in open(argv[1], encoding="utf-8", errors="replace") if " " in l}
        want = json.load(open(os.path.join(HERE, "mqtt_points.json"), encoding="utf-8"))
        missing = [p["topic"] for p in want if p["topic"] not in seen]
        print(f"{len(want) - len(missing)} of {len(want)} topics seen on the broker")
        for t in missing:
            print("  not seen:", t)
        return 0 if not missing else 1
    server = argv[0] if argv else "/Server 1"
    folder = argv[1] if len(argv) > 1 else "AHU01"
    pts = points(server, folder)
    bad, not_io = check(pts)
    if bad:
        print("\n".join(bad), file=sys.stderr)
        return 1
    with open(os.path.join(HERE, "mqtt_points.json"), "w", encoding="utf-8") as f:
        json.dump(pts, f, indent=1, ensure_ascii=False)
    with open(os.path.join(HERE, "mqtt_points.ps1"), "w", encoding="ascii", newline="\r\n") as f:
        f.write(ps1(pts, server, "/" + server.strip("/").split("/")[0] + "/IoT"))   # interface under the server itself
    # the same three groups as an import file: the way that works on modules with many signals (the dialog picker
    # of mqtt_points.ps1 picked wrong rows there). Import below the MQTT client after deleting the old groups.
    sys.path.insert(0, SKILL)
    from objects import ObjectSet
    client = "/" + server.strip("/").split("/")[0] + "/IoT/" + CLIENT
    oset = ObjectSet(parent=client)
    for g, _rows in GROUPS:
        oset.mqtt_group(None, g, ["/" + "/".join([server.strip("/")] + p["path"] + [p["property"]])
                                  for p in pts if p["group"] == g])
    oset.save(os.path.join(HERE, "AHU01-mqtt.xml"))
    root = pts[0]["topic"].rsplit("/", 2)[0]
    print(f"mqtt_points.json, mqtt_points.ps1: {len(pts)} points in {len(GROUPS)} groups "
          f"({', '.join(f'{g} {len(r)}' for g, r in GROUPS)}), topics under '{root}/', all public in AHU01.aut"
          + (f"; not in io.json (computed signals): {', '.join(not_io)}" if not_io else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
