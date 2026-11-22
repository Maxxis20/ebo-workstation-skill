# AHU01-SIM: plant simulation as implemented

`make_sim.py` writes `AHU01-SIM.aut` (175 blocks, 236 wires, 8 constants, 120 public signals, modules IN / PLANT /
TEST, no HFB) and `sim_io.json`. `check_sim.py` re-implements the static relations below in plain Python. Every
number in the steady-state tables comes from running it (`python3 check_sim.py`).

## Interface

- `IN/<tag>`: one RI for each controller output (TF01_Ctrl, PF01_Ctrl, SC3_Ctrl, TV1_Ctrl, TV2_Ctrl, FZ01_Cmd,
  FZ02_Cmd, TF01_Cmd, PF01_Cmd, SC3_Cmd, P1_Cmd). A binary command counts as on when it is > 0.5. Bind each one to
  `Outputs/<tag>`.
- `PLANT/<tag>`: every AI is a public XPR and every DI a public XPB (20 + 8). Bind `Inputs/<tag>` to each one.
  Optional: `PLANT/HN_Pres_In` and `PLANT/HN_Temp_In`, the controller's soft inputs, driven from TEST. They are
  listed under `optional_provides`.
- The model states are public too, for trends: `T_Out`, `Room_T`, `TE*_M`, `*_Speed`, `*_Eff`, `*_Pos`,
  `*_Air`, `Eta_HR`, `HR_Ice`, `HC_Char`, `CC_Char`, `Supply_Flow`, `Exhaust_Flow`, `Settling`,
  `Day_Seconds`, `Noise1/2`.
- NC contacts: `FA01` and `SB01` read 1 when healthy and `SC3_Fault` reads 1 when there is no fault, as the
  I/O list requires.

## Relations ([F] fitted, [A] assumed in MODEL.md, [N] new here, beyond MODEL.md)

Speeds and valve positions are in %. `ns`/`ne` are the effective supply/extract fan speeds. `air_s`/`air_e`
mean the air is moving (effective speed > 5 %) [N].

| Element | Relation as implemented | Status |
|---|---|---|
| Dampers | `FZ0x_Pos = RAMP(Cmd ? 100 : 0, 1.111 %/s)` (90 s stroke) | [A] |
| Fan drive | `Speed = RAMP(LIMIT((Cmd AND NOT Fail) ? Ctrl : 0, 0, 100), 3.333 %/s)` (0-100 % in 30 s) | [A] |
| Air through dampers | `ns = TF01_Speed * FZ01_Pos / 100`, `ne = PF01_Speed * FZ02_Pos / 100` | [N] |
| Fan feedback | `Fdb = DELAY(Cmd AND NOT Fail, 3 s, 3 s)` | [N] |
| Duct pressure | `PE1 = FILT(368 (ns/100)^2, 5 s) + 1.5`, `PE2 = FILT(491 (ne/100)^2, 5 s) + 1.5` | [F] gains and offsets, [A] lag and exponent 2 |
| Fan inlet dp | `PDE10 = FILT(1627 (ns/100)^2) + 8`, `PDE20 = FILT(2182 (ne/100)^2) + 8` | [F] |
| Filters | `PDE3 = 150 (ns/100)^2 Dirt_PDE3`, `PDE1` the same with `Dirt_PDE1`, `PDE2 = 150 (ne/100)^2 Dirt_PDE2`, lag 5 s | [A] |
| Wheel | `u = (SC3_Cmd AND NOT SC3_Fail) ? SC3_Ctrl : 0`; `eta = u <= 17.5 ? 0 : 0.616 (1 - EXP((17.5 - u)/10))`; `eta_e = 1.157 eta` (0.713 at 100 %) | [F]; denominator left out (0.9997) |
| Icing | `HR_Ice = FILT(((T_o < -5 AND u > 50 AND Ice_Auto) OR Ice_Force) ? 1.5 : 0, 3600 s)` | [A]; the `Ice_Auto` gate is [N], off by default because the data shows no icing |
| PDE4 | `FILT(4.908 (PDE20raw + 0.01)^0.452 (1 + HR_Ice), 5 s) + 1.5` | [F] |
| TE6 | target `air_s ? T_o : 11.1 + 0.3 T_o`; lag 300 s moving, 3600 s stopped | [F] 11.1, [A] the rest |
| TE3 | target `air_s ? TE6 + eta (TE7 - TE6) : 17.0`; lag 60 / 1800 s | [F] / [A] |
| TE8 | target `air_e ? TE7 - eta_e (TE7 - TE6) : 13.9`; lag 60 / 1800 s | [F] / [A] |
| Pump | `P1_Fdb = DELAY(P1_Cmd AND NOT P1_Fail, 2 s, 2 s)`; circulation = `P1_Fdb` | [N] |
| Valves | `TV1_Pos`, `TV2_Pos` = `RAMP(LIMIT(Ctrl, 0, 100), 0.833 %/s)` (120 s stroke) | [A] |
| Heating coil | `hh = (1 - EXP(-TV1_Pos/20)) / 0.99326`; target TE4 = `air_s ? TE3 + (pump ? 0.73 + 0.16 HC_Capacity hh (HW_Supply_T - TE3) : 0) : 18.4`; lag 90 / 1800 s | [F] 0.73, 0.16, 20; **[N] `HC_Capacity` default 2.5** (see below); [N] no heat without the pump |
| Return water TE1 | `ref = air_s ? TE3 : 18.5`; target `pump ? ref + (air_s ? 0.157 (23 - ref) : 0) + 0.27 hh (HW_Supply_T - ref) : ref`; lag 780 s, but 300 s when air moves and the pump is off | [F] 0.157, 23, 0.27, 18.5, 780 s; [N] no pump: the water goes to the air temperature (stopped: 18.5 plant room), 300 s |
| Cooling coil | `hc = 1 - EXP(-TV2_Pos/5)`; `x = TE4 + 0.48 hc (CC_Water_T - TE4) - 0.06`; floor `L = (CC_Water_T + 3 < TE4) ? CC_Water_T + 3 : TE4 - 0.06`; target TE5 = `air_s ? MAX(x, L) : 19.1`; lag 90 / 1800 s | [F] 0.48, 5, -0.06; [A] the water temperature and the +3 K floor; [N] the floor never lifts the air above `TE4 - 0.06` |
| Supply TE2 | target `air_s ? TE5 + 0.1 ns/60 : 19.6`; lag 45 / 1800 s | [F] 0.1 K at 60 %; [N] proportional to speed |
| Room | target `20.69 + 0.057 T_o + (air_s ? 0.3 (TE2 - 20.69) + 0.35 : 0) + Room_Load`; lag `Room_Tau` (10800 s) | [F] 20.69, 0.057, 0.35; [A] 0.3, 3 h |
| Extract TE7 | target `air_e ? Room - 0.42 : Room - 3.2`; lag 300 / 3000 s | [F] |
| Room sensors | `TE10_1/2/3 = Room + 0.8 / + 0.2 / - 1.0` | [F] |
| Outdoor | `T_Out = LIMIT(profile, -40, 45)`. Profile 0 is `OT_Manual`. Profile 1 is `OT_Manual + A COS(2 pi x)`. Profile 2 is `OT_Manual + A (2 frac(x) - 1)`, where `x = (seconds of day + 32400) / (3600 OT_Period)`. With a 24 h period the peak is at 15:00 | [A] form of MODEL 10 (cosine so that the peak is at 15 h) |
| Sensors | `TAG = Broken ? -199 : model + Offset + 0.073 Noise` for temperatures (sd 0.03 K) and `model (1 + 0.024 Noise)` for pressures (sd 1 %). `Noise` = `(SIN(a t) + SIN(b t + c) + SIN(d t + e)) / 3` on the seconds of the day, two variants, 0 unless `Noise_On` | [A] amplitude, [N] form |
| Safety DI | `FA01 = NOT Fire_Alarm`, `SB01 = NOT Stop_Pressed`, `SC3_Fault = NOT SC3_Fail`, `HS10 = HS10_Press`, `Reset_DI = Reset_Press` | [N] |

Variable lags are built as `y = FILT(f ? x : y + (x - y) 20/T, 20 s)`, which gives a time constant of about T for
T >= 20 s (within about 5 %, depending on how FILT discretises). `f` = `PLANT/Settling` (see start-up).

### Departures from MODEL.md, and why

1. **`HC_Capacity` = 2.5**, so the effective heating coil effectiveness is 0.40 instead of 0.16. With the coil as
   fitted (0.16 at an assumed 50 °C water), the description's winter sequence with `Heating_Mode` = 0 cannot hold
   the supply setpoint even at -5 °C: TV1 sits at 100 % and TE2 is 5.1 K below setpoint (scenario 2g). In the
   recorded unit the warm water cooling coil did the heating (scenario 2h). At 2.5 the coil alone holds the
   setpoint down to -20 °C (TV1 45 %). Set it to 1 to get the plant as recorded.
2. Icing is off unless `Ice_Auto` or `Ice_Force` is set. MODEL's rule (T_o < -5 and rotor > 50 %) would ice the
   wheel on every cold day, and the data showed none. With icing, PDE4 = 197.6 Pa against a frost limit of
   192 Pa at 45.9 %: the margin is only 3 %.
3. Air moves only when the effective speed (speed times damper position) is above 5 %. Every running/stopped
   switch in the model uses this and not the controller's `Run`. During a start, then, the extract side
   "runs" 30 s before the supply side.
4. Pump failure is a real loss of circulation: no coil heat, and TE1 relaxes to the air temperature in 300 s.
5. A fan `_Fail` trips the drive: speed ramps to 0 and the feedback drops. It is not a feedback contact fault
   alone.

## Start-up of the simulation

- `TEST/Settle` = 1 (the default) makes every slow lag run at 20 s for `Settle_Time` = 600 s after the program
  starts, or after Settle is switched 0 -> 1. The plant therefore reaches its values within about 2 min, whatever
  FILT starts from. To re-settle after big TEST changes, set Settle to 0 and then back to 1.
- If FILT starts at 0 after a load, TE1 reads below 7 °C for a few seconds. The controller's Freeze_Latch then
  trips, so **after loading the simulation, wait about 2 min and give a reset** (`Reset_Press` 1 -> 0, or
  `Inputs/Reset_Cmd`). Run controller tests after `PLANT/Settling` has gone to 0, because the plant is faster
  than real while it is 1.
- Drives start only with `TF01_Cmd` / `PF01_Cmd` bound. If the controller leaves them unbound, the fans do not
  turn.

## Healthy steady state at the defaults

Conditions: -5 °C outdoors, heating season, Heating_Mode 0, all controller defaults, AOM 2 running. These values
come from `check_sim.py` 2a. They hold after the 20 min heat recovery hold and once the room has settled
(3 h, or 2 min while Settling).

| Signal | Expected | Note |
|---|---|---|
| TF01_Ctrl | 60.0 % (at its output limit) | 140 Pa needs 61.4 % |
| PE1 | 134.0 Pa (6 Pa below setpoint, 4 %: no alarm) | |
| PF01_Ctrl | 45.9 % | |
| PE2 | 105.0 Pa | |
| PDE10 / PDE20 | 593.7 / 468.0 Pa; controller flow 8.48 / 7.53 m3/s | |
| PDE3 = PDE1 / PDE2 | 54.0 / 31.6 Pa (alarm limits 94 / 74 Pa) | |
| PDE4 | 79.9 Pa (frost limit 192 Pa) | |
| SC3_Ctrl | 100 % (sequence about 88) | |
| TV1_Ctrl | 18.4 % | |
| TV2_Ctrl | 0 % | |
| P1_Cmd / P1_Fdb | 1 / 1 | OT <= 10 |
| TE00 = TE6 | -5.0 °C | |
| TE3 | 10.6 °C | HR efficiency 61.6 % |
| TE4 / TE5 / TE2 | 20.9 / 20.8 / 20.95 °C | TE2 = setpoint |
| Supply setpoint | 20.95 °C | from TE7 |
| TE1 | 19.0 °C | coil controller enabled, output 0 |
| TE7 | 20.4 °C | |
| TE8 | 2.3 °C | |
| Room / TE10_1 / TE10_2 / TE10_3 | 20.83 / 21.6 / 21.0 / 19.8 °C | |
| FA01, SB01, SC3_Fault, TF01_Fdb, PF01_Fdb | all 1 | |
| HS10, Reset_DI | 0 | |
| Alarms | none | |

Unit stopped at -5 °C (1a): TE6 9.6, TE3 17.0, TE4 18.4, TE5 19.1, TE2 19.6, TE1 18.5, TE7 17.2, TE8 13.9,
room 20.4 °C, PE 1.5 Pa, PDE10/20 8 Pa.

Other operating points (closed loop):

| Case | SC3 | TV1 | TV2 | TE3 | TE2 = SP | TE1 | TE7 | Note |
|---|---|---|---|---|---|---|---|---|
| 2b -15 °C | 100 | 32.8 | 0 | 6.5 | 21.4 | 18.6 | 20.0 | TE8 -5.0 |
| 2c -20 °C | 100 | 45.0 | 0 | 4.5 | 21.65 | 18.5 | 19.8 | |
| 2d +8 °C, heating season | 100 | 6.1 | 0 | 16.0 | 20.3 | 19.5 | 21.0 | |
| 2e +25 °C, cooling season | 100 (cool recovery) | 0 | 3.0 | 23.0 | 19.5 | 23.0 | 21.7 | pump off |
| 2i Room_Load +2, -5 °C | 100 | 11.9 | 0 | 11.6 | 19.3 | 18.1 | 21.9 | |

## Test scenarios (TEST values; expected controller reaction)

| # | Set | Expected |
|---|---|---|
| 1 | Defaults | Steady state as above, no alarm |
| 2 | `OT_Manual` -15, then -20 | TV1 33 %, then 45 %; SC3 100 %; no alarm |
| 3 | `OT_Profile` 1, `OT_Period` 1, `OT_Amplitude` 4 | Sine from -9 to -1 °C each hour; TV1 follows; tests tracking |
| 4 | `OT_Manual` 25, controller `Season_Sel` 2 | Cool recovery latches (TE7 21.7 <= 23); SC3 100 %; TV2 about 3 %; TE2 19.5 |
| 5 | `Room_Load` +2 (or -2) | TE7 21.9, setpoint falls to 19.3, TV1 12 % (-2: setpoint up) |
| 6 | `HC_Capacity` 1 | TV1 100 %, TE2 17.1 vs SP 22.2 (-5.1 K): `Supply_Temp_Alm` after 300 s |
| 7 | `HC_Capacity` 1, `CC_Water_T` 30, controller `Heating_Mode` 1 | As recorded: TV2 100 %, TV1 4 %, TE5 20.8 |
| 8 | `Fire_Alarm` 1 | FA01 0: Fire_Latch, unit stops; TV1 under coil control. Back to 0 + reset: restarts |
| 9 | `Stop_Pressed` 1 | SB01 0: Stop_Latch, as 8 |
| 10 | `TF01_Fail` 1 | Supply fan stops, TF01_Fdb 0: `TF01_Alm` after 900 s, `Supply_Pres_Alm` after 900 s; TE2 drifts to 19.6 |
| 11 | `PF01_Fail` 1 | As 10 for extract: `PF01_Alm`, `Exhaust_Pres_Alm`; TE7 falls towards room -3.2 |
| 12 | `P1_Fail` 1 | P1_Fdb 0: `P1_Latch` after 30 s, critical stop, Freeze_Group keeps TV1 100 % and P1 commanded; TE1 relaxes to 18.5 |
| 13 | `SC3_Fail` 1 at -5 °C | SC3_Fault 0: `HRU_Alm` 180 s; TE3 = TE6 = -5; TV1 100 %, TE2 17.8 (-4.2 K, below the 5 K alarm); `HRU_Efficiency_Alm` after 300 s (efficiency 0 %) |
| 14 | `SC3_Fail` 1 and `OT_Manual` -20 | TE1 settles at 5.7 and TE2 at 8.8: `Freeze_Latch` when TE1 <= 7 (about 30 min, TE1 time constant 780 s), critical stop |
| 15 | `TE1_Offset` -13 (or `TE1_Broken` 1) | TE1 at 6.0 (or -199): `Freeze_Latch` at once; reset is refused until it is cleared |
| 16 | `TE2_Broken` 1 while running | bad(TE2): `Freeze_Latch` and `TE2_Alm` after 180 s |
| 17 | `TE00_Broken` 1 | OT = 0 °C in the controller, `TE00_Alm` 180 s; night modes blocked |
| 18 | `TE7_Broken` 1 | Setpoint = ST_Fault_SP 20 °C; `TE7_Alm`; cooling recovery reset |
| 19 | `TE10_1_Broken` 1 | Room mean of the two healthy sensors (21.0 / 19.8 -> 20.4); `TE10_1_Alm` |
| 20 | `Ice_Force` 1 at -5 °C (or `Ice_Auto` 1 at -15 °C) | PDE4 rises towards 197.6 Pa (time constant `Ice_Tau` 3600 s; set it to 300 for a quick test) and crosses 192 Pa after about 3 time constants (ice factor 1.43 of 1.5): `Frost_Cond`, SC3 limited to 50 %, `HRU_Frost_Alm` 180 s. At 50 % Ice_Auto stops building, so the ice decays and the limit releases after `Frost_Hold` |
| 21 | `Dirt_PDE3` (or 1, 2) 2.0 | PDE3 108 Pa > 94 Pa: `PDE3_Alm` after 300 s (extract: PDE2 63 vs 74 Pa needs about 2.4) |
| 22 | `HS10_Press` 1 then 0, outside the schedule | Unit runs for HS10_Run_Time 3600 s after release |
| 23 | `Reset_Press` 1 then 0 | Reset pulse for the latches |
| 24 | `HN_Pres_Alarm` / `HN_Temp_Alarm` 1 (only with the optional binding) | HN latches, critical stop |
| 25 | `HW_Supply_T` 15 at -15 °C | TV1 100 %, TE2 9.4 (-13 K): `Supply_Temp_Alm`; TE1 10.1 (no freeze trip; at -20 °C TE2 7.9 and TE1 8.8, still above 7) |
| 26 | `Noise_On` 1 | 0.03 K / 1 % noise; loops should stay quiet (dead zones 0.1 K / 1 Pa) |

Night modes need the controller's schedules. For example, night heating: previous-day mean between -15 and 0,
inside `Night_Schedule`, room <= 19 °C. With the room model, set `Room_Load` -2 with the unit stopped at -5 °C
(room target 20.4 - 2 = 18.4).
