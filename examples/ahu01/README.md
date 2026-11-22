# AHU01: a generic air handling unit for EBO

Supply and extract fan with duct pressure control, rotary heat recovery, heating coil with pump, cooling coil,
filters, freeze and frost protection, night cooling and night heating. Everything is generated from Python and
loaded into EcoStruxure Building Operation 7.1 by script (skill `ebo-workstation`).

| File | What |
|---|---|
| `DESCRIPTION.md` | description of operation: plant, I/O list, functions, alarms, setpoints, texts of the info boxes |
| `make_program.py` -> `AHU01.aut`, `io.json` | controller program: about 600 blocks in 20 hierarchical blocks, 33 alarm blocks, 8 modules, one PID per heating / cooling stage. `--only NAME` builds one function group alone. Notes and a test plan: `PROGRAM_NOTES.md` |
| `make_sim.py` -> `AHU01-SIM.aut`, `sim_io.json` | plant simulation (175 blocks) from a model fitted to trend data of a real unit (not included): test conditions and fault switches in module `TEST`. `SIM_NOTES.md`, `check_sim.py` |
| `make_hmi.py [--bench]` -> `AHU01-HMI.tgml`, `hmi_binds.json` | operator graphic: two ducts, components in plant order, turning fans, drifting air and running water marks, air colours by season, an info box per component, setpoints, alarm lamps, test bench panel. `HMI_NOTES.md`, preview `AHU01-HMI_preview.png` |
| `make_dashboard.py` -> `AHU01-objects.xml` | 20 trend logs, 3 trend charts, the dashboard `Measurements` (WebStation), the two weekly schedules (`Schedules/Time_Schedule`, `Schedules/Night_Schedule`) |
| `make_binds.py` -> `binds.json` | every binding of the set (165), written into an export by `ebox.py bind` |
| `deploy.sh` | all of the above onto a server, bound and running against the simulation: about 7 minutes |
| `make_controller.py`, `deploy_mpc.sh` -> `AHU01-MPC-points.xml`, `mpc_binds.json`, `MPC_IO.md` | the same program in a SpaceLogic MP-C-36A made offline: I/O points on terminals, bindings, terminal list |

## On a server, with the simulation

`./deploy.sh` (default `/Server 1`, folder `AHU01`). Then open `AHU01/Graphic` and press Reset once. The unit
runs in automatic when `Schedules/Time_Schedule` is on (mon-fri 06:30-18:30, sat-sun 09:00-15:00 by the server clock;
open the schedule in WorkStation to change the hours, or set the mode selector to Manual to run outside them). Test conditions are in the yellow panel of the
graphic and in `AHU01/SIM/TEST`. The dashboard is `AHU01/Dashboard/Measurements` in WebStation.

Seen on the bench (2026-11-22), outdoor -5 °C, heating season: pre-heat loads the heating valve with 75 %, then the
heating coil controller takes over; 10 minutes after the start supply air 19.3 °C at a setpoint of 19.5, heating
valve 16 %, heat recovery 100 %, fans still ramping towards 80 / 60 Pa (the model's own calculation for the settled
state: fans 46 / 35 %, valve 15 %). Cooling season at 30 °C outdoors with extract air cooler than outdoor air: the
rotor leaves the heating side, comes back as cooling recovery up to 100 %, then the cooling valve is released and
controls at a few percent; the supply temperature swings about +/- 0.8 K around the setpoint for a while (the
simulated cooling coil is strong at small openings; `ST/Cool_Gain` is the value to lower).

## How it runs

- **Start**: mode selector Auto and `Schedules/Time_Schedule` on (or Manual): dampers open, extract fan after
  30 s, supply fan after 60 s, both ramp to their duct pressure setpoints (80 / 60 Pa). Outdoors at or below 9 °C
  the start loads the heating valve with 75 % and holds the heat exchanger at 100 % for 20 minutes.
- **Supply temperature**: setpoint from the extract temperature (21.5 °C at 18 °C extract down to 16 °C at 23 °C).
  One PID controller per stage, one in control at a time: heat exchanger, then the cooling coil as a heater if its
  circuit carries warm water (`Operation/Heating_Mode`), then the heating coil. A stage is released when the one
  before has been at 100 % for 30 s and handed back when its own output has been at 0 % for 30 s. In the cooling
  season the cooling side takes over when every heating output is 0 and the supply air is 0.5 K too warm: heat
  exchanger first when the extract air is at least 2 K cooler than the outdoor air (cooling recovery), then the
  cooling valve.
- **Season**: Auto by yesterday's mean outdoor temperature (cooling from 11 °C, heating from 9 °C), or forced
  with the `-` / `+` buttons in the header of the graphic. The graphic changes its air colours with the season.
- **Night**: outside the time schedule, inside `Schedules/Night_Schedule`, the unit starts by itself for night
  cooling (room above 22 °C, cooling season) or night heating (room below 18 °C, heating season).
- **Protection**: freeze (coil return water or supply air at or below 6 °C), fire alarm, emergency stop, pump
  fault, heat supply faults and the two fire risk temperatures stop the unit and latch until Reset. The coil
  return water is kept at 10 °C or more at all times. Pump P1 runs in cold weather and whenever the valve is
  open; it stops only when the outdoor sensor, the intake air (unit running) and the return water all say warm.
  The heat exchanger slows down when its pressure drop shows frost.
- **Alarms**: 33 alarm blocks in three classes (A stops the unit, B fault, C service), shown as lamps on the
  graphic.

Everything is in `DESCRIPTION.md` with formulas and the list of setpoints.

## In a controller (prepared offline, not downloaded)

`./deploy_mpc.sh` (default `/Server 1/BACnet/IP Network`, device `AHU01-MPC`; the BACnet Interface must exist: New >
BACnet Interface on the server). It makes the MP-C-36A, loads the program as a SpaceLogic Function Block Program,
imports the I/O points with their terminals and writes the bindings: program inputs read the points, output points
read the program's output blocks. Result on the bench: 39 points, 73 bindings, read back in
`AHU01-MPC-export.xml`. Graphic, trend logs and dashboard go in as on the server, with the program path of the device.

Terminals: `MPC_IO.md`. 34 points are wired; outdoor temperature, the three room temperatures and the remote
reset come in as BACnet values, because 39 points do not fit on 36 terminals (an IP-IO-DI10 beside the
controller is the other way). An automation server (AS-P) cannot be prepared like this: it needs a connection.

## Over MQTT, with a FUXA view (seen working 2026-11-22: 92 of 92 topics on the broker, live values in FUXA)

The Data Groups are imported from `AHU01-mqtt.xml` (written by `make_mqtt.py`); the dialog picker of
`mqtt_points.ps1` picked wrong rows on modules with many signals and is no longer used for the points. The whole
script takes about 2 minutes. Text below this line that speaks of chunks, the picker or "not verified" predates that.

`./deploy_fuxa.sh` (same arguments as `deploy.sh`), after `deploy.sh`. It has EBO publish 92 signals of the
program to the Mosquitto broker on the same machine and loads a FUXA view of the unit that reads them back
(findings, section MQTT, for broker and FUXA).

- `make_mqtt.py` -> `mqtt_points.json`, `mqtt_points.ps1`: the points (measurements, control outputs, states and
  modes, setpoints in use, critical alarm and the 33 alarms; the graphic's binds less the sensor fault flags and
  the operator setpoints), each checked to be a public signal of `AHU01.aut` and to agree with `hmi_binds.json`.
  Three Data Groups under the MQTT client `/Server 1/IoT/Broker`: `AHU01_Meas` (25), `AHU01_Ctrl` (33),
  `AHU01_Alarms` (34); event driven plus every 10 s.
- Topics: EBO names each topic after the data point's path, so the unit's signals arrive as
  `Server 1/AHU01/AHU/<Module>/<Signal>` (e.g. `Server 1/AHU01/AHU/Inputs/TE2`), payload the plain value: binary
  0 / 1, run mode and selectors as their number, an alarm as its alarm state (0 normal, 1 alarm, 2 acknowledged,
  3 reset, 4 disabled, 5 fault). A free prefix such as `ahu01/` is not available with what has been tried: the
  Data Group has a Topic field, but only "empty = EBO path" has been seen working.
- `make_fuxa.py` -> `AHU01.fuxa.json`: MQTT device on `mqtt://127.0.0.1:1883`, one tag per topic (tag name = bind
  name of the EBO graphic), one view `AHU01` (1540 x 900) in the arrangement of the EBO graphic: header with
  run mode, selectors, season, night modes, critical alarm; extract duct on top (right to left), supply duct
  below (left to right), rotor across both, coils with pump and valves, fans and dampers as lamps, live values;
  alarm lamps on the right. Read-only; numbers and lamps only (what FUXA can be given without clicking).
- `deploy_fuxa.sh`: makes the IoT Interface and the client if missing, deletes and re-creates the three groups,
  fills them in chunks of 17 points (one `ebo.sh run` each, about 20 to 30 minutes in all), lists what the
  broker receives for 25 s and counts the topics, then `ebo.sh fuxa AHU01.fuxa.json`. Show it with
  `ebo.sh run "Log (Web-Top 'http://127.0.0.1:1881/' 'FUXA' 0 0 1600 1000)"`.

After a new `deploy.sh`: run `deploy_fuxa.sh` again. The groups live outside the folder, so they survive the delete
and import, but whether their data points find the re-imported signals again is not verified; the script deletes
and re-creates the groups, so it does not depend on it.

Not verified: everything on the EBO machine. In particular the picker on modules with many signals (`Alarms` has 72, `Inputs`
61, where the DH-ex2 run had at most 6): `mqtt_points.ps1` skips rows scrolled out of view and walks the list with
the arrow key when the signal is not among the visible rows (a guess at how the list behaves), and reports a
point it cannot pick as `MISSING` instead of stopping. The number of data points one group accepts is not known.

## Not verified

Download to a device, live I/O, the alarm objects tripping in the alarm list, and most rows of the test plan
in `PROGRAM_NOTES.md` (start, run, pressure control and the temperature sequence were seen working).
