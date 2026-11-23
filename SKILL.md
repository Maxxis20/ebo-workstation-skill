---
name: ebo-workstation
description: Drive Schneider EcoStruxure Building Operation (EBO 7.1 WorkStation, Enterprise Server, the Function Block editor / Menta) on the Windows machine it is installed on, without hand clicking - create Function Block programs, load their logic from a generated .aut text file, save, read live values back, build and bind graphics, publish values over MQTT; also EBO servers run as containers (Enterprise Server, Edge Server) and bindings between two servers. Use when the task is to build, change, inspect or verify an EBO Function Block program or graphic, to read an EBO export xml, or when the user mentions Schneider EBO, EcoStruxure Building Operation, WorkStation, Enterprise Server, SmartX, AS-P, Edge Server, EBO-Servers containers, Menta or .aut files.
---

# EBO WorkStation by script

Working (2026-11-22, EBO 7.1.1): a Function Block program described in Python becomes a `.aut` text file with a
clean right-angle layout, is created on the Enterprise Server, imported in the Function Block editor, compiled,
and checked from an export, all by script. Also by script: bindings between objects, and a graphic (HMI)
generated from Python, loaded and bound. Values go out over MQTT too (EBO MQTT client, Mosquitto and FUXA on
the same machine): findings, section MQTT.

Read `reference/findings.md` before touching WorkStation: what the machine needs, the rules (one command at a
time, the driver owns keyboard and mouse while it runs), what each driver function does, the `.aut` format with its traps (pin numbers, wire
point offset), and what is still open.

## First use on a machine

Run `$E check` before anything else, and again whenever something basic fails. It prints one line per
requirement. Fix every TODO yourself where you can (`$E setup` makes the work folder and copies the block
catalogue from the user's own installation; `$E logon` starts WorkStation and logs on). Ask the user only for
what needs their hands: typing the password into the box that `logon` opens, switching Classic Mode on, starting
a stopped service, installing something. Tell them exactly what to do and wait. Also tell them, once, to keep
their hands off keyboard and mouse while a driver command runs.

## Usual sequence

```bash
E=<folder of this skill>/scripts/ebo.sh                  # run in a bash on the EBO machine itself (Git Bash)
python3 make_program.py                                   # uses scripts/aut.py, writes X.aut (+ expected.json)
$E put X.aut 'C:\agentwork\ebo\X.aut'
$E run "Fb-Load '/Server 1' 'X' 'C:\agentwork\ebo\X.aut'" 150
$E run "Log (Ws-Export '/Server 1/X' 'C:\agentwork\ebo\X.xml')" 90
$E get 'C:\agentwork\ebo\X.xml' X.xml                    # then check it against Program.expected()
$E run "Gfx-Load '/Server 1' 'G' 'C:\\agentwork\\ebo\\G.tgml'" 200        # graphic from a .tgml (scripts/tgml.py)
$E run "Log (Ws-Bind '/Server 1/G' @(@('TE1','/Server 1/X/MOD/TE1')))" 300   # bind points by typed paths
$E run "Log (Ws-Import '/Server 1' 'C:\agentwork\ebo\objs.xml')" 120       # trend logs, alarms, values, charts from scripts/objects.py
$E run "Log (Ws-Export '/Server 1/X' 'C:\agentwork\ebo\X.xml' 'Special')" 90   # Special = with every binding
python3 <skill>/scripts/ebox.py unpack X.xml out/         # any export: program text, graphics, script source; also tree | binds | aut
$E shot out.png                                           # screenshot
$E run "Log (Mq-Client '/Server 1/IoT' 'Broker'); Log (Mq-Group '/Server 1/IoT/Broker' 'G' @(@(@('X','MOD'),'TE1')))" 240   # publish over MQTT (IoT Interface first: Ws-New '/Server 1' 'IoT Interface' 'IoT')
$E mqtt 12                                                # what the local broker receives
$E fuxa project.json                                      # FUXA project from scripts/fuxa.py into the local FUXA
```

Traps that cost a retry before (details in the findings): a PIDA / PIDP needs its own output wired back to TSg; a
reload of a program drops its own input bindings, so bind again after every `Fb-Load`; an export does not hold
computed public signals; a public constant cannot be used in an expression (`const(..., public=False)` can); an
import never replaces an object (delete first, or it arrives as `Name_2`); one `ebo.sh` call at a time.

Another server than the one on this machine (a server in a container, findings "Servers in containers"):
`EBO_SERVER=<address> $E logon`; a server nobody has logged on to yet: `EBO_SERVER=<address> $E firstlogon`; plain
`$E logon` goes back to localhost. Starting a container means accepting Schneider's EULA and needs licences: that
is the user's decision, ask first.

Two servers (an Edge / automation server below the Enterprise Server; findings, "An Edge Server below an Enterprise
Server"): bind on the side of the lower server. Going down, the lower server's input is bound to the Enterprise
Server's value by absolute path (`ebox.py bind` does that; a relative path above the lower server's root is dropped
silently and reads 0). Going up, do not let the Enterprise Server read the lower server's value (reads 0, no
error): make plain value points on the Enterprise Server (`objects.py value()`), bind the lower program's output
blocks (`<tag>_OUT`) to them with `Ws-Bind`, and read those points.

A real BACnet/IP controller (SpaceLogic RP-C / MP-C; findings, "A real field controller on a container server"):
the server needs the device network itself (a container on host or ipvlan networking, not published ports), then
Device Discovery, `Initialize ID`, the device object with `Ws-New`, and the discovered row dragged onto it
(`Drag`). A blue arrow on an object means Download / Upload to the device is still owed.

Things that need no clicking at all (findings, "What production programs showed" and "Objects from a file"):
alarms as ALARM blocks in the program (`p.alarm(...)`), constants bound in the program file
(`p.const(..., bind=)`), trend logs / alarms / server values / weekly schedules / trend charts from `objects.py`, and many bindings
at once: Special export, `ebox.py bind`, delete, `Ws-Import` (7 s instead of 5 s per point).

WorkStation logs off when idle (5 minutes for the built-in administrators): run `$E logon` first (starts it if
needed, logs on, harmless when already logged on). When it has to log on, a Windows credential box opens on the
screen for the user to fill in: tell them to look at the screen. **Never ask for the password in the chat and
never read it from anywhere yourself.** Classic Mode must be on (the driver switches it on when it finds it off).

To check a generated file without the server, start the editor alone and use `File > Open`, then
`Options > Simulate` (findings, "Started alone").

## Files

- `scripts/aut.py`: Function Block program generator (blocks, constants, wires, layout, routing).
- `scripts/tgml.py`: graphic (HMI) generator: shapes, live values, state colours, click-to-change, movement (turning
  fan, marks running along a pipe, blinking lamp), symbols from SVG files, component files for the editor's library.
- `scripts/objects.py`: import file writer for objects without an editor: folders, trend logs, alarms, values, weekly
  schedules, charts, dashboards with gauges, live values, period charts and embedded graphics (shown in WebStation).
- `scripts/ebox.py`: export reader (object tree, bindings, unpack program text / graphics / script source,
  program text summary with HFBs), binding writer, and programs / graphics out of a server backup (`xbk`).
- `scripts/fuxa.py`: FUXA project generator (MQTT device, tags, a view with live numbers and lamps).
- `scripts/ebo.sh`, `scripts/win/cli.ps1`, `scripts/win/lib.ps1`, `scripts/win/ebo.ps1`: driver.
- `reference/MentaBlocks.xml`: the editor's block catalogue (pins, parameters). Not shipped: copy it from your
  own installation (findings, "The machine").
- `examples/blink.aut`: smallest program that imports, compiles and runs.
- `examples/dh-ex2/`: worked example (controller with four modules, plant model in closed loop, graphic, MQTT,
  FUXA view) with the commands to load it. Read it for the patterns; do not copy it when asked to design something
  from a description of your own.
- `examples/ahu01/`: larger worked example (air handling unit: hierarchical blocks, staged PID controllers, alarms,
  simulation, animated graphic with info boxes and season colours, schedules, dashboard, MP-C controller, MQTT /
  FUXA); `deploy.sh` there is the pattern for loading a whole set and binding it from one file.

The WorkStation automation API needs an SDK licence key; do not work around it.
