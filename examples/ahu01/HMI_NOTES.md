# AHU01 operator graphic: notes

Files: `make_hmi.py` (generator), `AHU01-HMI.tgml` (the graphic, built with `--bench`), `hmi_binds.json` (bind
name -> target), `AHU01-HMI_preview.png` (offline rendering, popups closed), `tgml_preview.py` (TGML -> SVG / PNG
converter used for the preview).

    python3 make_hmi.py --bench            # graphic with the test bench panel (as delivered)
    python3 make_hmi.py -o AHU01-HMI.tgml  # without it: the bench panel and its 8 binds are left out
    python3 tgml_preview.py AHU01-HMI.tgml x.svg [--open] --png x.png [--crop x,y,w,h]

Note: `hmi_binds.json` is rewritten on every run and follows the last `--bench` choice.

## Page

1600 x 900, Arial, background #EEF0F3. 502 top-level elements (1740 XML elements), 122 binds (114 controller,
8 bench), 40 info popups. Checked by the generator: well-formed XML, only the elements `tgml.py` writes (Tgml,
Rectangle, Line, Ellipse, Polygon, Path, Text, Component, Group, Bind, ConvertValue, Script, Animate, Rotate,
Translate), every bind in the table and every table entry used, every popup box entirely on the page.

- **Header** (dark bar): unit name; Run mode (`Run_Mode` as words: Stopped / Normal / Night cooling / Night
  heating / Alarm stop); Mode selector (`AOM`: Off / Manual / Auto, click to change) with info; Season selector
  (`Season_Sel`: Auto / Heating / Cooling) with info; Season in use (`Season_Mode`); Night cooling and Night
  heating states; Cooling coil water (`Heating_Mode`: chilled / warm); blinking common alarm lamp with
  `Critical_Alarm` text; Reset button (writes 1 to `Reset_Cmd`) with info.
- **Schematic** (left, x 12 ... 1182): two horizontal ducts, extract / exhaust on top (air right to left),
  outdoor / supply below (left to right), inside a unit casing; the rotor SC3 spans both ducts.
- **Setpoints** (right top): the operator setpoints of section 8 as blue clickable values; - / + step buttons on
  supply duct pressure (10 Pa), extract duct pressure (10 Pa) and setpoint curve point 1 supply value (0.5 K);
  the supply setpoint in use below.
- **Alarms** (right, two columns): one lamp per alarm of section 5 (33), class letter beside it. A = red
  blinking, B = red steady, C = amber steady.
- **Bottom**: Zone (TE10.1-3 with fault circles, room mean, HS10, extended run), Outdoor and safety (TE00,
  yesterday's mean, SB01, FA01), Test bench (only with `--bench`, yellow panel).

## Component order as drawn

Supply duct, left to right: Outdoor air -> FZ01 damper -> TE6 -> FLT1 filter (PDE3) -> FLT2 filter (PDE1) ->
SC3 rotor -> TE3 -> HC1 heating coil -> TE4 -> CC1 cooling coil -> TE5 -> TF01 fan (PDE10, flow) -> [casing
ends] -> TE2 (with setpoint in use and deviation alarm) -> PE1 (with setpoint in use) -> Supply air to the zone.

Extract duct, right to left: Extract air from the zone -> PE2 (setpoint in use) -> TE7 -> [casing] -> FLT3
filter (PDE2) -> SC3 rotor (PDE4 with its limit and frost state above it) -> TE8 -> PF01 fan (PDE20, flow) ->
FZ02 damper -> Exhaust air.

Water side: HC1 from the left: heating water in -> TV1 valve -> P1 pump -> riser into the coil; return riser
with TE1 (freeze state, freeze limit, minimum return setpoint) -> return. CC1 from the right: chilled water in
-> TV2 valve -> riser into the coil; return riser -> return.

Sensors: temperatures are small circles on the duct edge (white, red while the instant fault flag `bad_TEx` is
true); pressures are small squares (tappings). Live values are dark, setpoints blue.

## Movement

- Fans TF01 / PF01: impeller turns while the running feedback `TF01_Fdb` / `PF01_Fdb` is 1.
- Rotor: seen from the side across both ducts, its lines travel while `SC3_Cmd` is 1; orange in the heating season,
  light blue in the cooling season.
- Marks run along both ducts while `Operation\Run` is 1 (colour per air section: outdoor blue, extract / supply
  after the rotor orange, exhaust grey). In the cooling season (`Operation\Season_Mode` = 1) the duct fills, the
  streaks and the arrows change places: outdoor orange, supply after the rotor and extract light blue.
- Heating circuit: the loop between coil and bypass (and the bypass) runs while `P1_Fdb` is 1; the pipes below the
  bypass only while `TV1_Ctrl` >= 1 % (valve closed: the pump circulates in the closed loop). Cooling circuit pipes
  while `TV2_Ctrl` >= 1 %.
- Header: `-` / `+` buttons step the mode selector (`AOM`) and the season selector (`Season_Sel`) through 0 ... 2. Water side drawn as a
  shunt group in counterflow: supply pipe on the side where the air leaves the coil (pump P1 on it), return on the
  side where the air enters (TE1 at the coil outlet, control valve on the return), bypass with a check valve between
  them on the heating coil. The freeze limit, coil return minimum and rotor frost limit are in the Setpoints panel
  only.
- Blinking: `Critical_Alarm` in the header and the eight class A alarm lamps.
- Damper blades green while the damper command is 1, grey when 0. Pump P1 green while `P1_Fdb` is 1.

## Binds (from the one table `BINDS` / `ALARMS` / `BENCH` in make_hmi.py)

Controller (114):
`RUN` Operation/Run, `RUN_MODE` Operation/Run_Mode, `AOM` Operation/AOM, `SEASON_SEL` Operation/Season_Sel,
`SEASON` Operation/Season_Mode, `NIGHT_COOL` Operation/Night_Cooling, `NIGHT_HEAT` Operation/Night_Heating,
`HEAT_MODE` Operation/Heating_Mode, `CRIT` Alarms/Critical_Alarm, `RESET` Inputs/Reset_Cmd, `FZ01`
Outputs/FZ01_Cmd, `FZ02` Outputs/FZ02_Cmd, `TE00` `TE1` ... `TE8` `TE10_1..3` Inputs/<same>, `<TE>_BAD`
Inputs/bad_<TE> (12), `OT_DAY` Inputs/OT_Day_Mean, `ROOM_AVG` Inputs/Room_Avg, `PE1` `PE2` `PDE1` `PDE2` `PDE3`
`PDE4` `PDE10` `PDE20` Inputs/<same>, `PE1_SP` FAN/Supply_Pressure_SP, `PE2_SP` FAN/Exhaust_Pressure_SP, `Q_SUP`
Inputs/Supply_Flow, `Q_EXH` Inputs/Exhaust_Flow, `SC3` Outputs/SC3_Ctrl, `SC3_CMD` Outputs/SC3_Cmd, `SC3_OK`
Inputs/SC3_Fault, `FROST` HRU/Frost_Active, `PDE4_SP` HRU/PDE4_SP, `HRU_EFF` HRU/HRU_Efficiency, `TV1`
Outputs/TV1_Ctrl, `P1_CMD` Outputs/P1_Cmd, `P1_FDB` Inputs/P1_Fdb, `FREEZE` Alarms/Freeze_Latch, `TV2`
Outputs/TV2_Ctrl, `TF01` Outputs/TF01_Ctrl, `TF01_CMD` Outputs/TF01_Cmd, `TF01_FDB` Inputs/TF01_Fdb, `PF01`
Outputs/PF01_Ctrl, `PF01_CMD` Outputs/PF01_Cmd, `PF01_FDB` Inputs/PF01_Fdb, `ACT_SP` ST/Active_SP, `HS10`
Inputs/HS10, `HS10_EXT` Operation/HS10_Ext, `SB01` Inputs/SB01, `FA01` Inputs/FA01, `PE1_SET`
FAN/Supply_Pressure_Set, `PE2_SET` FAN/Exhaust_Pressure_Set, `ET_X1` `SP_Y1` `ET_X2` `SP_Y2` ST/<same>,
`COIL_ST` ST/Coil_Heat_ST, `FREEZE_SP` Inputs/Freeze_SP, `FROST_LIM` ST/Frost_HRU_Ctrl, and the 33 alarms of
section 5, bind name = alarm name, target Alarms/<name>.

Bench (8, names taken from `make_sim.py` TESTS, which appeared in this folder while the graphic was being
made): `B_OT` TEST/OT_Manual, `B_HWT` TEST/HW_Supply_T, `B_FIRE` TEST/Fire_Alarm, `B_ESTOP` TEST/Stop_Pressed,
`B_P1F` TEST/P1_Fail, `B_SC3F` TEST/SC3_Fail, `B_TF01F` TEST/TF01_Fail, `B_ICE` TEST/Ice_Force. Switches have
0 / 1 buttons (1 = fault present); outdoor temperature has -5 / -1 / +1 / +5 buttons (held within -40 ... 40),
the heating water supply temperature -5 / +5 (0 ... 90, lower it to provoke a freeze trip).

## Popups (40)

FZ01, FZ02, TE00, TE6, FLT1, PDE3, FLT2, PDE1, SC3, PDE4, HRU efficiency, TE3, HC1, TV1, P1, TE1, TE4, CC1, TV2,
TE5, TF01, PDE10, TE2, PE1, PE2, TE7, FLT3, PDE2, TE8, PF01, PDE20, TE10.1, TE10.2, TE10.3 (same text, own
title), HS10, SB01, FA01, mode selector, season selector, alarm reset. Texts are section 7 verbatim (the room
sensor sentence "One popup per sensor ..." left out, as it is an instruction). Popup width 300; the side is
chosen by the generator so the box lies on the page (`make_hmi.py` stops if one does not fit).

## Deviations from the description

- `SC3_Fault` is shown as a state ("drive ok" / "DRIVE FAULT") because it is normally closed (1 = healthy).
- Sensor fault state is shown by the instant flags `bad_TEx` (the HFB `SensorCheck` outputs); if the flat
  program names them differently, correct the table. The delayed sensor alarms are in the Alarms panel.
- The "settings page" of section 8 is not made; the setpoint curve points, coil and frost values are in the
  Setpoints panel instead. `Heating_Mode` is shown in the header (click to change).
- `HRU_Frost_Alm` is only in the Alarms panel; at the rotor the frost state `Frost_Active` is shown.
- The heating valve is drawn as a two-way valve (the description allows two- or three-way).

## Not verified offline

- How EBO really renders: the preview uses approximate Arial metrics; text Top -> baseline offset (0.9 x size)
  is a guess; value widths were checked with "-88.8 °C" / "-888 Pa" samples and the longer word of each state.
- The multi-word state text for `Run_Mode`, `AOM`, `Season_Sel` is written in the script (`HMI.mstate`) with
  the same Text / Bind / Script form as `Graphic.state`, but has not run in EBO. Whether a click on these and on
  the `state` texts opens the change dialog (they carry an OnSignalChange script) is untested.
- Reset: `step_button` adds 1 to the last value it saw (0), so it writes 1; relies on the program clearing
  `Reset_Cmd` the next cycle.
- Whether binding to ALARM block outputs (`Alarms/<name>`) gives 0 / 1 as expected.
- Flow marks on the cooling pipes start at `TV2_Ctrl` >= 1 and stop at <= 0; between 0 and 1 % the state is
  whatever it was.
- Popup z-order: each info mark is its own Component in `g.top`, so an open box can be covered by the "i" marks
  of info components written after it (visible in the all-open preview). Behaviour of a click on such a mark
  through an open box is untested.
- Popup line wrapping uses tgml.py's 5.6 px per character estimate at 11 px.
