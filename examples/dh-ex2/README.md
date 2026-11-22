# DH-ex2: district heating substation, worked example

Written by an AI agent with this skill, from `DESCRIPTION.md` alone (Finnish Energy K2, example connection 2:
domestic hot water and heating, one control valve and one pump each).

![EBO graphic and FUXA view at the end of the build](screen.png)

| File | What |
|---|---|
| `make_program.py` → `DH-ex2.aut` | The controller: 56 function blocks, 67 wires, modules OUTDOOR, TC1_DHW, TC2_HEAT, ALARM |
| `make_sim.py` → `DH-ex2-SIM.aut` | A small plant model (16 blocks) so the loops have something to control |
| `make_hmi.py` → `DH-ex2-HMI.tgml` | Operator graphic, 96 elements, 21 bound points, buttons to step the outdoor temperature |
| `make_fuxa.py` → `DH-ex2.fuxa.json` | FUXA view of the same values over MQTT |
| `points.py` | Bindings between the three objects and the MQTT point list |

Load it (set-up from the main README done, `E` = `scripts/ebo.sh`, run from this folder):

```bash
python3 make_program.py && python3 make_sim.py && python3 make_hmi.py
$E logon
$E put DH-ex2.aut 'C:\agentwork\ebo\DH-ex2.aut'; $E put DH-ex2-SIM.aut 'C:\agentwork\ebo\DH-ex2-SIM.aut'
$E run "Fb-Load '/Server 1' 'DH-ex2' 'C:\agentwork\ebo\DH-ex2.aut'; Fb-Load '/Server 1' 'DH-ex2-SIM' 'C:\agentwork\ebo\DH-ex2-SIM.aut'" 300
$E run "$(python3 points.py bind-prog)" 300
$E put DH-ex2-HMI.tgml 'C:\agentwork\ebo\DH-ex2-HMI.tgml'
$E run "Gfx-Load '/Server 1' 'DH-ex2-HMI' 'C:\\agentwork\\ebo\\DH-ex2-HMI.tgml'" 200
$E run "$(python3 points.py bind-hmi)" 400
$E run "Ws-Open '/Server 1/DH-ex2-HMI'" 60; $E shot hmi.png
# MQTT and FUXA, if Mosquitto and FUXA run on the VM:
$E run "$(python3 points.py mqtt)" 560
python3 make_fuxa.py && $E fuxa DH-ex2.fuxa.json
```

The `.aut` and `.tgml` files can also be imported by hand: Function Block editor `File > Import...`, Graphics
Editor source view.

Checked: both programs compile and run, the loops settle at plausible values, graphic and FUXA show the same
numbers, a step of the outdoor temperature on the graphic arrives in FUXA.

Not checked: alarms, sensor faults, summer stop, pump stop. They are in the program; nobody has exercised them.
The piping in the graphic is the agent's guess, since the description has no piping drawing, and the plant model
is a teaching model, not calibrated. An example to learn from, not a design to commission.

`DESCRIPTION.md` was written for an Ouman Ouflex version of the same example. File names it mentions
(`plan.json`, `make_plan.py`, `layout.json`, `examples/dh2`) belong to that project and are not here.
