---
name: ebo-workstation
description: Drive Schneider EcoStruxure Building Operation (EBO 7.1 WorkStation, Enterprise Server, the Function Block editor / Menta) on the Windows machine it is installed on, without hand clicking - create Function Block programs, load their logic from a generated .aut text file, save, read live values back, build and bind graphics, publish values over MQTT. Use when the task is to build, change, inspect or verify an EBO Function Block program or graphic, to read an EBO export xml, or when the user mentions Schneider EBO, EcoStruxure Building Operation, WorkStation, Enterprise Server, SmartX, AS-P, Menta or .aut files.
---

# EBO WorkStation by script

Working (2026-11-21, EBO 7.1.1): a Function Block program described in Python becomes a `.aut` text file with a
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
$E shot out.png                                           # screenshot
$E run "Log (Mq-Client '/Server 1/IoT' 'Broker'); Log (Mq-Group '/Server 1/IoT/Broker' 'G' @(@(@('X','MOD'),'TE1')))" 240   # publish over MQTT (IoT Interface first: Ws-New '/Server 1' 'IoT Interface' 'IoT')
$E mqtt 12                                                # what the local broker receives
$E fuxa project.json                                      # FUXA project from scripts/fuxa.py into the local FUXA
```

Traps that cost a retry before (details in the findings): a PIDA needs its own output wired back to TSg; a reload
of a program drops its own input bindings, so bind again after every `Fb-Load`; an export does not hold computed
public signals; one `ebo.sh` call at a time.

WorkStation logs off when idle (5 minutes for the built-in administrators): run `$E logon` first (starts it if
needed, logs on, harmless when already logged on). When it has to log on, a Windows credential box opens on the
screen for the user to fill in: tell them to look at the screen. **Never ask for the password in the chat and
never read it from anywhere yourself.** Classic Mode must be on.

To check a generated file without the server, start the editor alone and use `File > Open`, then
`Options > Simulate` (findings, "Started alone").

## Files

- `scripts/aut.py`: Function Block program generator (blocks, constants, wires, layout, routing).
- `scripts/tgml.py`: graphic (HMI) generator: shapes, live values, state colours, click-to-change.
- `scripts/fuxa.py`: FUXA project generator (MQTT device, tags, a view with live numbers and lamps).
- `scripts/ebo.sh`, `scripts/win/cli.ps1`, `scripts/win/lib.ps1`, `scripts/win/ebo.ps1`: driver.
- `reference/MentaBlocks.xml`: the editor's block catalogue (pins, parameters). Not shipped: copy it from your
  own installation (findings, "The machine").
- `examples/blink.aut`: smallest program that imports, compiles and runs.
- `examples/dh-ex2/`: worked example (controller with four modules, plant model in closed loop, graphic, MQTT,
  FUXA view) with the commands to load it. Read it for the patterns; do not copy it when asked to design something
  from a description of your own.

The WorkStation automation API needs an SDK licence key; do not work around it.
