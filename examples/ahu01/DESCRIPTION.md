# AHU01: air handling unit, design specification

Generic supply and extract air handling unit with rotary heat recovery, a water heating coil with circulation
pump, a water cooling coil (which can also carry warm water), and two pressure controlled fans. Control runs as one
Function Block program `AHU01` in Schneider EcoStruxure Building Operation (EBO), on an automation server or the
Enterprise Server, cycle time 1 s.

This document is the only source for the program, the operator graphic, the plant simulation and the dashboard.
All names in `Module\Name` form are the public signal names of the program. All values are starting values.

Conventions:

- `on_delay(x, T)`: true when x has been true for T seconds. `off_delay(x, T)`: true while x is true and for T
  seconds after it falls. `delay(x, Ton, Toff)`: both.
- `rise(x)`: one-cycle pulse on the rising edge of x (EBO `TRIG (1)`).
- `PRCNT(v0, v100)(x)`: `LIMIT((x - v0) / (v100 - v0) * 100, 0, 100)`. v100 may be smaller than v0 (falling range).
- `CURVE(x; x1,y1; x2,y2; ...)`: linear between the points, held at the end values outside them. Points are always
  given with x ascending.
- `SR(set, reset)`: latch. **Every latch in this program is reset-dominant**: the block is fed
  `set AND NOT reset` on its set input, because the EBO SR block toggles when both inputs are true.
- `bad(TEx)`: `TEx < MinTemp OR TEx > MaxTemp`, evaluated every cycle without delay (the instant sensor fault flag).
  `ok(TEx)` = `NOT bad(TEx)`.
- Controllers: PIDA = incremental, PIDP = positional, both with their own output wired back to the tracking input
  (TSg) unless stated otherwise. Mode values: 0 off (output follows TSg), 1 normal, 2 forced to UMax,
  3 forced to UMin. Control error e = SP - MV; positive gain means the output rises when MV is below SP.
- "Design decision" marks behaviour that was chosen for this generic unit rather than taken over unchanged.

---

## 1. Plant

### 1.1 Overview

| Part | Tag(s) | Notes |
|---|---|---|
| Outdoor air shut-off damper | FZ01 | On/off actuator, spring return closed |
| Supply filter, stage 1 | (graphic id FLT1), pressure drop PDE3 | |
| Supply filter, stage 2 | (graphic id FLT2), pressure drop PDE1 | |
| Rotary heat exchanger | SC3 | Variable speed rotor: start command, speed signal, fault contact. Extract side pressure drop PDE4 |
| Heating coil | (graphic id HC1), valve TV1, pump P1, return water TE1 | Low temperature hot water |
| Cooling coil | (graphic id CC1), valve TV2 | Chilled water; the circuit can be switched to warm water by the plant that feeds it (soft input `Heating_Mode`) |
| Supply fan | TF01, flow measurement PDE10 | Variable speed (drive with start command and speed signal) |
| Extract filter | (graphic id FLT3), pressure drop PDE2 | |
| Extract fan | PF01, flow measurement PDE20 | Variable speed |
| Exhaust air shut-off damper | FZ02 | On/off actuator, spring return closed |
| Room sensors | TE10.1, TE10.2, TE10.3 | Three room temperatures in the served zone |
| Extended run push button | HS10 | In the served zone |
| Outdoor temperature | TE00 | Separate outdoor sensor, shaded north wall |
| Emergency stop button | SB01 | Normally closed |
| Fire alarm contact | FA01 | From the fire alarm panel, normally closed |

### 1.2 Supply air path (outdoor air intake to supply duct)

1. Outdoor air intake.
2. FZ01, outdoor air shut-off damper.
3. TE6, intake air temperature (after the damper).
4. Supply filter stage 1, with PDE3 pressure drop across it.
5. Supply filter stage 2, with PDE1 pressure drop across it.
6. SC3, rotary heat exchanger, supply side.
7. TE3, supply air temperature after heat recovery.
8. Heating coil, water side TV1 / P1 / TE1 (see 1.4).
9. TE4, supply air temperature after the heating coil.
10. Cooling coil, water side TV2 (see 1.4).
11. TE5, supply air temperature after the cooling coil.
12. TF01, supply fan, with PDE10 (inlet cone pressure difference for air flow).
13. TE2, supply air temperature (control sensor).
14. PE1, supply duct static pressure (control sensor).
15. Supply duct to the zone.

### 1.3 Extract air path (extract duct to exhaust)

1. Extract duct from the zone.
2. PE2, extract duct static pressure (control sensor).
3. TE7, extract air temperature.
4. Extract filter, with PDE2 pressure drop across it.
5. SC3, rotary heat exchanger, extract side, with PDE4 pressure drop across the extract side.
6. TE8, exhaust air temperature after heat recovery.
7. PF01, extract fan, with PDE20 (inlet cone pressure difference for air flow).
8. FZ02, exhaust air shut-off damper.
9. Exhaust air outlet.

### 1.4 Water side of the coils

Heating coil:

- TV1: two-way or three-way control valve, 0 ... 10 V modulating actuator, signal `TV1_Ctrl` 0 ... 100 %.
- P1: coil circulation pump (shunt pump between valve and coil), on/off. Command `P1_Cmd`, running feedback
  `P1_Fdb`.
- TE1: return water temperature on the coil outlet. Used for the coil minimum return temperature control and for
  freeze protection.

Cooling coil:

- TV2: control valve, modulating, signal `TV2_Ctrl` 0 ... 100 %.
- No pump and no water side sensor in this unit. The water is chilled water in normal service; when the supplying
  plant reports warm water in the circuit (`Heating_Mode` = 1) the winter sequence uses this coil as a first
  heating stage.

---

## 2. I/O list

### 2.1 Physical points

Block names in the program are the names in the first column; RI/BI blocks sit in module `Inputs`, RO/BO in module
`Outputs`. Point names on the I/O modules are `AHU01-<tag>_<kind>` (for example `AHU01-TE02_AI`).

| Name | Kind | Unit | Range | Description |
|---|---|---|---|---|
| TE00 | AI | °C | -50 ... 50 | Outdoor air temperature |
| TE1 | AI | °C | 0 ... 100 | Heating coil return water temperature |
| TE2 | AI | °C | -50 ... 100 | Supply air temperature (control) |
| TE3 | AI | °C | -50 ... 50 | Supply air after heat recovery |
| TE4 | AI | °C | -50 ... 80 | Supply air after heating coil |
| TE5 | AI | °C | -50 ... 80 | Supply air after cooling coil |
| TE6 | AI | °C | -50 ... 50 | Intake air temperature after FZ01 |
| TE7 | AI | °C | -50 ... 100 | Extract air temperature |
| TE8 | AI | °C | -50 ... 50 | Exhaust air temperature after heat recovery |
| TE10_1 | AI | °C | 0 ... 50 | Room temperature 1 (TE10.1) |
| TE10_2 | AI | °C | 0 ... 50 | Room temperature 2 (TE10.2) |
| TE10_3 | AI | °C | 0 ... 50 | Room temperature 3 (TE10.3) |
| PE1 | AI | Pa | 0 ... 500 | Supply duct static pressure, 0 ... 10 V transmitter |
| PE2 | AI | Pa | 0 ... 500 | Extract duct static pressure (measured as positive suction value) |
| PDE1 | AI | Pa | 0 ... 500 | Supply filter stage 2 pressure drop |
| PDE2 | AI | Pa | 0 ... 500 | Extract filter pressure drop |
| PDE3 | AI | Pa | 0 ... 500 | Supply filter stage 1 pressure drop |
| PDE4 | AI | Pa | 0 ... 500 | Heat exchanger pressure drop, extract side |
| PDE10 | AI | Pa | 0 ... 2000 | Supply fan inlet cone pressure difference |
| PDE20 | AI | Pa | 0 ... 2000 | Extract fan inlet cone pressure difference |
| FA01 | DI | | 0/1 | Fire alarm panel contact. Normally closed: 1 = normal, 0 = fire |
| SB01 | DI | | 0/1 | Emergency stop button. Normally closed: 1 = normal, 0 = pressed |
| HS10 | DI | | 0/1 | Extended run push button (or timer switch) in the zone, 1 = pressed |
| P1_Fdb | DI | | 0/1 | Pump P1 running feedback, 1 = running |
| TF01_Fdb | DI | | 0/1 | Supply fan running feedback from the drive, 1 = running |
| PF01_Fdb | DI | | 0/1 | Extract fan running feedback from the drive, 1 = running |
| SC3_Fault | DI | | 0/1 | Heat exchanger drive fault relay. Normally closed: 1 = normal, 0 = fault |
| Reset_DI | DI | | 0/1 | Optional alarm reset push button on the control panel, 1 = pressed |
| TF01_Ctrl | AO | % | 0 ... 100 | Supply fan speed |
| PF01_Ctrl | AO | % | 0 ... 100 | Extract fan speed |
| SC3_Ctrl | AO | % | 0 ... 100 | Heat exchanger rotor speed |
| TV1_Ctrl | AO | % | 0 ... 100 | Heating coil valve |
| TV2_Ctrl | AO | % | 0 ... 100 | Cooling coil valve |
| FZ01_Cmd | DO | | 0/1 | Open outdoor air damper |
| FZ02_Cmd | DO | | 0/1 | Open exhaust air damper |
| TF01_Cmd | DO | | 0/1 | Supply fan start |
| PF01_Cmd | DO | | 0/1 | Extract fan start |
| SC3_Cmd | DO | | 0/1 | Heat exchanger start |
| P1_Cmd | DO | | 0/1 | Heating coil pump start |

Totals: 20 AI, 8 DI, 5 AO, 6 DO = 39 points.

The physical channel layout is left to the project. Every AI is read without a filter in the program (filtering,
if wanted, on the I/O point).

### 2.2 Soft inputs (local objects, operator switches, values from elsewhere)

Every value that a real installation receives from another program, server or schedule is a local object of
AHU01. A project may bind it to an outside source; unbound, the default applies and the unit runs on its own.

| Name | Kind | Default | Meaning | Chosen form |
|---|---|---|---|---|
| `Operation\Time_Schedule` | BI | (schedule) | Normal running schedule. 1 = run | Local EBO digital schedule `AHU01/Schedules/Time_Schedule`, bound to this BI. Default week: Mon-Fri 06:30-18:30, Sat-Sun 09:00-15:00 |
| `Operation\Night_Schedule` | BI | (schedule) | Window in which night cooling and night heating may run | Local EBO digital schedule `AHU01/Schedules/Night_Schedule`. Default: Mon-Fri 02:00-08:00, Sat-Sun none |
| `Inputs\HN_Pres_In` | BI | 0 | Heat supply (district heating substation) water pressure alarm, 1 = alarm | Bindable input; bind to the substation's alarm signal or to a spare DI. Unbound = 0 |
| `Inputs\HN_Temp_In` | BI | 0 | Heat supply water temperature alarm, 1 = alarm | As above |
| `Operation\Heating_Mode` | PVB | 0 | 1 = the cooling coil circuit carries warm water and may be used for heating | Local writable value; may be bound to the plant that feeds the coil |
| `Operation\Season_Sel` | PVI | 0 | Season selector: 0 automatic, 1 heating season, 2 cooling season | Local operator switch; automatic season from the outdoor daily mean (4.3) |
| `Operation\AOM` | PVI | 2 | Operating mode selector: 0 off, 1 manual on, 2 automatic | Local operator switch |
| `Inputs\Reset_Cmd` | PVB (one-cycle) | 0 | Alarm reset from the graphic | Local, cleared by the program after one cycle |

Room temperatures and the outdoor temperature are physical inputs of this unit (TE10_1..3, TE00).

---

## 3. Program structure

### 3.1 Modules (public signal groups)

| Module | Content |
|---|---|
| `Inputs` | All RI/BI blocks, sensor fault flags, outdoor value in use, room mean, daily outdoor mean, air flows, reset pulse |
| `Operation` | AOM, season, schedules, HS10 extension, normal operation, night cooling, night heating, run state, run mode |
| `Alarms` | All latches, `Critical_Alarm`, all ALARM blocks and alarm limits |
| `FAN` | Damper and fan release sequence, pressure setpoints incl. low speed mode, both pressure controllers |
| `ST` | Supply temperature setpoint, the four stage controllers and their staging, start-up pre-heat, coil return water control |
| `HRU` | Heat exchanger frost protection and temperature efficiency |
| `P1` | Heating coil pump command and exercise |
| `Outputs` | All RO/BO blocks and the final output selection |

### 3.2 Hierarchical function blocks (HFB)

The module list above is normative (signal names). The HFB split below is the recommended internal structure;
a builder that cannot generate HFBs may lay the same logic out flat, keeping the signal names.

| HFB | Instances | Inputs | Outputs |
|---|---|---|---|
| `SensorCheck` | 1 | TE00, TE1..TE8, TE10_1..3, MinTemp, MaxTemp, OT_Fault_Value | `bad_TE00`..`bad_TE10_3` (instant flags), `OT`, `OT_OK`, `Room_Avg`, `Room_OK` |
| `DayMean` | 1 | OT, OT_OK | `OT_Day_Mean` |
| `CritLatch` | 8 (one per critical cause) | Cause, Reset_Pulse | Latched |
| `Modes` | 1 | AOM, Season_Sel, OT_Day_Mean, Time_Schedule, HS10, Night_Schedule, Critical_Alarm, OT, OT_OK, Room_Avg, Room_OK, night parameters | Season_Mode, Operation, Night_Cooling, Night_Heating, Run, Run_Mode |
| `FanCtrl` | 2 (Supply, Exhaust) | Run, Critical_Alarm, Fan_Delay, PV (PE), Pressure_Set, Low_Speed_Cmd, Low_Speed_SP, Gain, Ti, Td, DZ, Ctrl_Min, Ctrl_Max, StrokeTime, Fdb, K, PDE (flow) | Released (= fan start command), Speed, Flow, Pres_Dev_Cond, Fdb_Fault_Cond |
| `FilterAlarm` | 3 (PDE1, PDE3, PDE2) | Enable, Released, DP, Fan_Speed, X1, Y1, X2, Y2 | Alarm_Cond |
| `TempSeq` | 1 | TE2, TE7, OT, Run, Season_Mode, Operation, Night_Cooling, Night_Heating, Heating_Mode, setpoint parameters, tuning | Active_SP, H, C, SC3_Seq, TV1_Seq, TV2_Seq, PreHeat_Pulse, HRU_Hold, Cool_Recovery |
| `CoilProtect` | 1 | TE1, Coil_Heat_ST, Coil_Heat_ON_SP, Coil_Heat_OFF_SP, Freeze_Group | Coil_Heat_Ctrl |
| `HruFrostEff` | 1 | PDE4, PF01_Ctrl, TE3, TE6, TE7, SC3_Ctrl, Run, parameters | Frost_Active, HRU_Efficiency, Eff_Calc |
| `PumpCtrl` | 1 | OT, TE6, TE1 (and their fault flags), Run, TV1_Ctrl, Freeze_Group, P1_Fdb, clock | P1_Cmd, P1_Fault_Cond |

---

## 4. Description of operation

### 4.1 Inputs, sensor faults, derived values (module `Inputs`)

```
bad(TEx) = TEx < MinTemp OR TEx > MaxTemp            for TE00, TE1..TE8, TE10_1..TE10_3
                                                     MinTemp = -120 °C, MaxTemp = 120 °C (private constants)
OT_OK    = NOT bad(TE00)
OT       = OT_OK ? TE00 : OT_Fault_Value             OT_Fault_Value = 0 °C
```

`OT` is the outdoor temperature used by every outdoor dependent function. Design decision: on a faulty outdoor
sensor the program does not fall back to the intake sensor TE6 (which reads plant room temperature while the
dampers are closed); it uses 0 °C, which keeps pre-heat and the pump on the safe side, and blocks the night modes
(4.6) through `OT_OK`.

Room mean (design decision: mean of the healthy sensors only):

```
n        = ok(TE10_1) + ok(TE10_2) + ok(TE10_3)
Room_OK  = n >= 1
Room_Avg = Room_OK ? (sum of the healthy TE10_x) / n : 0
```

Air flows (m3/s, K factor in l/s per √Pa):

```
Supply_Flow  = Run ? TF01_K * SQRT(MAX(PDE10, 0)) / 1000 : 0          TF01_K = 350
Exhaust_Flow = Run ? PF01_K * SQRT(MAX(PDE20, 0)) / 1000 : 0          PF01_K = 350
```

Reset:

```
Reset_Pulse = rise(Reset_Cmd OR Reset_DI)
```

`Reset_Cmd` is a public writable one-cycle block (EBO `DELB` fed with 0, or equivalent): a write of 1 from the
graphic gives one pulse and the value returns to 0 in the next cycle.

### 4.2 Daily outdoor mean (`Inputs\OT_Day_Mean`)

```
minute_tick = SECOND < previous-cycle SECOND                (clock seconds wrapped)
day_tick    = HOUR   < previous-cycle HOUR                  (midnight)
on minute_tick AND OT_OK:   Sum = Sum + OT ; Cnt = Cnt + 1
on day_tick:                Sum_Held = Sum ; Cnt_Held = Cnt ; Sum = 0 ; Cnt = 0   (copy before clear)
OT_Day_Mean = Cnt_Held > 0 ? Sum_Held / Cnt_Held : 5
```

Start values: `Sum_Held` = 5, `Cnt_Held` = 1, so the mean reads 5 °C until the first midnight after a cold start.
Samples taken while TE00 is faulty are skipped (design decision).

### 4.3 Season (module `Operation`)

```
Auto_Season = SR( set:   OT_Day_Mean >= Season_Cool_OT ,          11 °C
                  reset: OT_Day_Mean <= Season_Heat_OT )          9 °C
Season_Mode = Season_Sel == 2 ? 1 : ( Season_Sel == 1 ? 0 : Auto_Season )
```

`Season_Mode` 1 = cooling season (summer sequence), 0 = heating season (winter sequence). Design decision: the
season was an outside signal; it is now decided locally from the previous day's mean outdoor temperature (so it
changes at most once a day, at midnight), with a manual override.

### 4.4 Operating modes, start and stop (module `Operation`)

```
HS10_Ext      = off_delay(HS10, HS10_Run_Time)                                   HS10_Run_Time = 3600 s
Operation     = NOT Critical_Alarm AND ( AOM == 1 OR (AOM == 2 AND (Time_Schedule OR HS10_Ext)) )
Run           = NOT Critical_Alarm AND (Operation OR Night_Cooling OR Night_Heating)
Run_Mode      = Critical_Alarm ? 4 : Operation ? 1 : Night_Cooling ? 2 : Night_Heating ? 3 : 0
```

- AOM 0 = off: the unit is stopped, including the night modes. AOM 1 = manual on: runs continuously, night modes
  not needed. AOM 2 = automatic: schedule, HS10 and night modes.
- HS10 (design decision): a press extends normal running by `HS10_Run_Time` from the moment the contact opens; a
  maintained contact (timer switch) runs the unit while closed plus the same run-on. Only in AOM 2.
- `Run_Mode` for display: 0 stopped, 1 normal, 2 night cooling, 3 night heating, 4 stopped by critical alarm.
- Start: when `Run` rises the dampers open at once, the extract fan starts after 30 s, the supply fan after 60 s
  (4.7). Temperature control starts with `Run`.
- Stop: when `Run` falls, in the same cycle: damper commands, fan start commands and fan speeds go to 0, heat
  exchanger to 0, cooling valve to 0. The heating valve stays under the coil return water control (4.11) and the
  pump under its own logic (4.12). No fan run-on.

### 4.5 Critical alarms, latches and reset (module `Alarms`)

Eight causes, each held by a `CritLatch`:

```
Latched_x = SR( set: Cause_x , reset: Reset_Pulse AND NOT Cause_x )
```

(a reset while the cause is still present has no effect; the latch stays set.)

| Latch | Cause (set condition) |
|---|---|
| `Freeze_Latch` | `TE1 <= Freeze_SP OR bad(TE1) OR ( Run AND (TE2 <= Freeze_SP OR bad(TE2)) )`. `Freeze_SP` = 6 °C |
| `Fire_Latch` | `FA01 == 0` |
| `Stop_Latch` | `SB01 == 0` |
| `P1_Latch` | `P1_Fault_Cond` (4.12): pump commanded but no running feedback for `P1_Fdb_Delay` |
| `HN_Pres_Latch` | `HN_Pres_In == 1` |
| `HN_Temp_Latch` | `HN_Temp_In == 1` |
| `Supply_Fire_Latch` | `TE2 >= Supply_Fire_Temp` (50 °C) |
| `Exhaust_Fire_Latch` | `TE7 >= Exhaust_Fire_Temp` (50 °C) |

```
Critical_Alarm = OR of the eight latches
Freeze_Group   = Freeze_Latch OR P1_Latch            (forces the heating valve open, 4.11)
```

The control logic uses the latch outputs directly, never the state of an alarm object (design decision). Each latch
also feeds its own ALARM block (section 5), so every critical cause produces its own alarm.

Effect of `Critical_Alarm`: `Operation`, the night modes and `Run` drop; dampers close; fans stop; heat exchanger
and cooling valve 0 %. With `Freeze_Group` the heating valve goes to 100 % and the pump runs.

### 4.6 Night cooling and night heating (module `Operation`)

Both only in AOM 2, only while `Operation` is false, and only inside `Night_Schedule`. In either mode the unit runs
as in normal operation (same pressure setpoints) but with a fixed supply temperature setpoint (4.9).

Night cooling:

```
NC_Room = SR( set:   Room_Avg >= Night_Cool_Start_T ,                         22 °C
              reset: Room_Avg <= Night_Cool_Stop_T OR Operation OR NOT Room_OK )   19 °C
NC_OT   = OT_OK AND Night_Cool_OT_Min <= OT AND OT <= Night_Cool_OT_Max       12 ... 19 °C
Night_Cooling = AOM == 2 AND NOT Operation AND NOT Critical_Alarm AND Season_Mode == 1
                AND Night_Schedule AND Night_Cool_Mode
                AND delay(NC_OT, Night_Cond_Delay, Night_Cond_Delay)          60 s / 60 s
                AND delay(NC_Room, Night_Cond_Delay, Night_Cond_Delay)
```

Night heating:

```
NH_Room = SR( set:   Room_Avg <= Night_Heat_Start_T ,                         18 °C
              reset: Room_Avg >= Night_Heat_Stop_T OR Operation OR NOT Room_OK )   20 °C
NH_OT   = Night_Heat_OT_Min <= OT_Day_Mean AND OT_Day_Mean <= Night_Heat_OT_Max    -15 ... 0 °C
Night_Heating = AOM == 2 AND NOT Operation AND NOT Critical_Alarm AND Season_Mode == 0
                AND Night_Schedule AND Night_Heat_Mode AND OT_OK AND NH_OT
                AND delay(NH_Room, Night_Cond_Delay, Night_Cond_Delay)
```

Night heating is allowed only after a day whose mean outdoor temperature was between -15 and 0 °C. During night
cooling the summer sequence runs with the night setpoint, so the cooling valve may open (not free cooling only).

### 4.7 Dampers and fan release (module `FAN`)

```
FZ01_Cmd = FZ02_Cmd = Run
TF01_Cmd = Supply_Released  = on_delay(Run, Supply_Fan_Delay)      60 s
PF01_Cmd = Exhaust_Released = on_delay(Run, Exhaust_Fan_Delay)     30 s
```

(`Run` already contains `NOT Critical_Alarm`.) The dampers open first; the extract fan starts 30 s later, the
supply fan 60 s later. Design decision: the source unit had no fan start outputs (the fan commands drove the
dampers); AHU01 has separate damper and fan start outputs. A project whose drives start from the analog signal
leaves `TF01_Cmd`/`PF01_Cmd` unbound.

### 4.8 Fan pressure control (module `FAN`, HFB `FanCtrl` twice)

| | Supply `FAN\Supply_PIDP` | Extract `FAN\Exhaust_PIDP` |
|---|---|---|
| Type | PIDP (positional), own output on TSg | PIDP, own output on TSg |
| MV | PE1 | PE2 |
| SP | `FAN\Supply_Pressure_SP` | `FAN\Exhaust_Pressure_SP` |
| Action | direct heating sense: e = SP - MV, gain positive, speed rises when pressure is low | same |
| ControlInt / StrokeTime | 1 s / 20 s (`Supply_StrokeTime`) | 1 s / 20 s |
| UMin / UMax | `Supply_Ctrl_Min_SP` 20 % / `Supply_Ctrl_Max_SP` 60 % | `Exhaust_Ctrl_Min_SP` 20 % / `Exhaust_Ctrl_Max_SP` 60 % |
| Gain / Ti / Td / dead zone | 0.05 / 60 s / 0 s / 1 Pa | 0.05 / 60 s / 0 s / 1 Pa |
| Mode | `Supply_Released ? 1 : 3` | `Exhaust_Released ? 1 : 3` |

```
TF01_Ctrl = Supply_Released  ? LIMIT(Supply_PIDP,  Supply_Ctrl_Min_SP,  Supply_Ctrl_Max_SP)  : 0
PF01_Ctrl = Exhaust_Released ? LIMIT(Exhaust_PIDP, Exhaust_Ctrl_Min_SP, Exhaust_Ctrl_Max_SP) : 0
```

While not released the controller sits at UMin (20 %) and the output is 0; at release the fan starts at 20 % and
the controller takes over. Design decision: the controller limits equal the output limits (the source let the
controller run to 110 % behind a 60 % output limit, which wound up).

Pressure setpoints, with the optional cold-weather reduction ("low speed mode"):

```
Cold          = SR( set: OT <= Low_Speed_Temp_SP , reset: OT >= Low_Speed_Temp_SP + Low_Speed_Deviation )
                                                                         -10 °C, 2 K
Low_Speed_Cmd = off_delay(Cold AND Low_Speed_Mode, Low_Speed_Delay_Off)  600 s, Low_Speed_Mode = 0 (off)
Supply_Pressure_SP  = Low_Speed_Cmd ? CURVE(OT; -20,50; -15,65; -10,75; -5,80)  : Supply_Pressure_Set   80 Pa
Exhaust_Pressure_SP = Low_Speed_Cmd ? CURVE(OT; -20,40; -15,50;  -10,55;  -5,60)  : Exhaust_Pressure_Set  60 Pa
```

Curve points are the constants `Temp_X1..4`/`Press_Y1..4` (supply) and `Temp1_X1..4`/`Press1_Y1..4` (extract).
Design decision: the curve values are new; the source values raised the pressure in "low speed" mode. The mode is
off by default. The same setpoints apply in normal running and in both night modes.

### 4.9 Supply temperature setpoint (module `ST`)

```
Temp_SP      = ok(TE7) ? CURVE(TE7; ET_X1,SP_Y1; ET_X2,SP_Y2) : ST_Fault_SP
                           18 °C -> 21.5 °C ; 23 °C -> 16 °C            ST_Fault_SP = 19 °C
Heat_Temp_SP = Night_Heating ? LIMIT(Night_Heat_ST, Night_Heat_Min_Temp, Night_Heat_Max_Temp) : Temp_SP
                               27 °C, limits 18 ... 35
Cool_Temp_SP = Night_Cooling ? LIMIT(Night_Cool_ST, Night_Cool_Min_Temp, Night_Cool_Max_Temp) : Temp_SP
                               17 °C, limits 15 ... 25
Active_SP    = Season_Mode ? Cool_Temp_SP : Heat_Temp_SP
```

Extract air compensation: with extract air at 18 °C or below the supply setpoint is 21.5 °C; it falls linearly to
16 °C at 23 °C extract air and stays there above.

### 4.10 Supply temperature control sequence (module `ST`, HFB `TempSeq`)

One PIDA controller per stage on TE2, so each loop has its own tuning, and one of them in control at a time.

| Controller | Acts on | Direction | Gain / Ti | In control when |
|---|---|---|---|---|
| `ST\HRU_PIDA` | Heat exchanger `SC3_Seq` | heats (cools while `Rotor_Cools`) | `HRU_Gain` 1.5, `HRU_Ti` 45 s | `HRU_Act` |
| `ST\CCH_PIDA` | Cooling coil used for heating `TV2_Heat_Seq` | heats | `CCH_Gain` 2, `CCH_Ti` 45 s | `CCH_Act` |
| `ST\HC_PIDA` | Heating valve `TV1_Seq` | heats | `HC_Gain` 1.5, `HC_Ti` 45 s | `HC_Act` |
| `ST\Cool_PIDA` | Cooling valve `TV2_Cool_Seq` | cools | `Cool_Gain` 2.5, `Cool_Ti` 45 s | `Cool_Act` |

All four: ControlInt 1 s, output 0 ... 100 %, `Temp_Derivative_Time` 0 s, `Temp_Dead_Zone` 0.1 K, SP = `Active_SP`,
mode 1 when in control and 0 otherwise, TSg = the stage output below. A heating controller has MV = TE2 and SP =
setpoint; a cooling one has the two exchanged, so its output rises when the supply air is too warm. A controller
that is not in control follows its stage output (0 or 100 %) and takes over from there without a bump.

```
Heat_Active = NOT Season_Mode AND (Operation OR Night_Heating)
Cool_Active = Season_Mode AND (Operation OR Night_Cooling)
Temp_Active = Heat_Active OR Cool_Active
Cool_Recovery = SR( set: ok(TE7) AND OT_OK AND TE7 <= OT - Cool_Recovery_Hist ,
                    reset: TE7 >= OT + Cool_Recovery_Hist OR bad(TE7) OR NOT OT_OK )      2 K
Rotor_Cools = Cool_Recovery AND Season_Mode       extract air cooler than outdoor air: the rotor is a cooling stage
CCH_Avail   = NOT Season_Mode AND Heating_Mode    warm water in the cooling coil circuit
```

Stages. Heating side, in this order: heat exchanger, cooling coil with warm water (only with `CCH_Avail`), heating
coil. Cooling side (cooling season only), in this order: heat exchanger (only with `Rotor_Cools`), cooling valve.
A stage that is not available is left out of the chain. Stages below the one in control are held at 100 %, stages
above it at 0 %.

```
Heat_Side  = (Temp_Active OR PreHeat_Pulse) AND NOT Cool_Side
Stage_CCH  = SR( set: Heat_Side AND CCH_Avail AND rotor at 100 % (or Rotor_Cools) for Stage_Up_Delay, or pre-heat ,
                 reset: own output 0 % for Stage_Down_Delay (rotor available, heating coil not released)
                        OR NOT CCH_Avail OR NOT Heat_Side )
Stage_HC   = SR( set: Heat_Side AND stage before it at 100 % for Stage_Up_Delay, or pre-heat ,
                 reset: own output 0 % for Stage_Down_Delay (a stage before it exists) OR NOT Heat_Side )
Cool_Side  = SR( set: Cool_Active AND every heating output 0 % AND TE2 > Active_SP + Neutral_Zone for Stage_Up_Delay ,
                 reset: every cooling output 0 % AND TE2 < Active_SP - Neutral_Zone for Stage_Down_Delay
                        OR NOT Cool_Active )
Stage_Cool = SR( set: Cool_Side AND (NOT Rotor_Cools, at once; else rotor at 100 % for Stage_Up_Delay) ,
                 reset: Rotor_Cools AND own output 0 % for Stage_Down_Delay OR NOT Cool_Side )
                 "at 100 %" = 99.5 % or more, "0 %" = 0.5 % or less; Stage_Up_Delay 30 s, Stage_Down_Delay 30 s,
                 Neutral_Zone 0.5 K; every latch is reset dominant

HRU_Act  = (Heat_Side AND NOT Rotor_Cools AND NOT Stage_CCH AND NOT Stage_HC) OR (Cool_Side AND Rotor_Cools AND NOT Stage_Cool)
CCH_Act  = Heat_Side AND Stage_CCH AND NOT Stage_HC
HC_Act   = Heat_Side AND Stage_HC
Cool_Act = Cool_Side AND Stage_Cool

SC3_Seq      = HRU_Act ? HRU_PIDA : (rotor stage passed ? 100 : 0)
TV2_Heat_Seq = CCH_Act ? CCH_PIDA : (Stage_CCH AND Stage_HC ? 100 : 0)
TV1_Seq      = PreHeat_Pulse ? (Heating_Mode ? PreHeat_Valve_HM : PreHeat_Valve) : (HC_Act ? HC_PIDA : 0)     50 / 75 %
TV2_Cool_Seq = Cool_Act ? Cool_PIDA : 0
TV2_Seq      = TV2_Heat_Seq + TV2_Cool_Seq        (never both: one valve, warm or chilled water)
```

In the heating season the cooling side is never entered. In the cooling season the heating side still works (rotor,
then heating coil), the neutral zone keeps the two sides apart, and with `Rotor_Cools` the rotor is not used as a
heater (it would cool).

Start-up pre-heat:

```
PreHeat_Pulse = off_delay( rise(Run) AND OT <= PreHeat_Heat_ST AND NOT Season_Mode , PreHeat_Heat_Delay )
                                         9 °C                                          1 s
HRU_Hold      = Run AND off_delay(PreHeat_Pulse, HRU_Preheat_Del)                       1200 s
```

The pre-heat pulse releases every heating stage at the start in cold weather and loads the heating coil controller
with `PreHeat_Valve` (75 %, or `PreHeat_Valve_HM` 50 % with `Heating_Mode`): heat exchanger 100 %, cooling coil 100 %
if it carries warm water, so the coil is already warm when the supply fan starts 60 s later. For the next 20 minutes
the heat exchanger is held at 100 % to cover the start-up temperature drop.

Outputs (module `Outputs`):

```
SC3_Ctrl = NOT Run ? 0
         : Frost_Active ? MIN(SC3_Seq_Final, Frost_HRU_Ctrl)                       50 %
         : SC3_Seq_Final
  where SC3_Seq_Final = (NOT Season_Mode AND HRU_Hold) ? 100 : SC3_Seq
SC3_Cmd  = SC3_Ctrl > 1
TV2_Ctrl = Run ? TV2_Seq : 0
TV1_Ctrl = MAX( Run ? TV1_Seq : 0 , Coil_Heat_Ctrl )
```

Design decision: heat exchanger frost protection limits the rotor speed to at most 50 % (the source set it to 50 %
even when the sequence asked for less, which could raise the speed).

### 4.11 Heating coil return water control and freeze protection (module `ST`, HFB `CoilProtect`)

`ST\Coil_Heat_PIDA` keeps the coil return water TE1 above `Coil_Heat_ST`, whether the unit runs or not.

| Item | Value |
|---|---|
| Type | PIDA, own output on TSg |
| MV / SP | TE1 / `Coil_Heat_ST` 10 °C |
| ControlInt, UMin, UMax, StrokeTime | 1 s, 0, 100, 0 |
| Gain / Ti / Td / dead zone | `Coil_Gain` 5 / `Coil_Ti` 60 s / 0 s / 0.1 K |
| Enable | `Coil_En` = HYST on `TE1 - Coil_Heat_ST`: on when below `Coil_Heat_ON_SP` 10 K, off when above `Coil_Heat_OFF_SP` 12 K (so enabled below 20 °C return water, disabled above 22 °C) |
| Mode | `Freeze_Group ? 2 : (Coil_En ? 1 : 3)` |

```
Coil_Heat_Ctrl = (Freeze_Group OR Coil_En) ? Coil_Heat_PIDA : 0
```

Freeze protection as a whole:

1. Return water TE1 at or below 6 °C (any time), supply air TE2 at or below 6 °C while running, or a fault on
   either sensor sets `Freeze_Latch` (4.5).
2. The latch is critical: the unit stops, dampers close, heat exchanger and cooling valve 0 %.
3. `Freeze_Group` (freeze latch or pump alarm) forces the coil controller to 100 %, so TV1 opens fully, and keeps
   the pump commanded (4.12).
4. The state holds until the cause has cleared and a reset is given.

Design decision: TE2 takes part only while `Run` is true (a cold, stagnant supply duct of a stopped unit is not a
coil freeze risk and would otherwise trip the unit before the morning start).

### 4.12 Heating coil pump P1 (module `P1`, HFB `PumpCtrl`)

```
P1_OT_Need = SR( set: OT <= P1_Start_OT , reset: OT >= P1_Stop_OT )                     9 °C / 11 °C
P1_Ex      = off_delay( rise(WDAY == P1_Ex_Day AND HOUR == P1_Ex_Hour) , P1_Ex_Time )   Monday, 10 h, 60 s
P1_Air_Need   = SR( set: Run AND (TE6 <= P1_Start_OT OR bad(TE6)) ,
                     reset: NOT Run OR (ok(TE6) AND TE6 >= P1_Stop_OT) )               intake air, while the unit runs
P1_Water_Need = SR( set: TE1 <= P1_Start_TE1 OR bad(TE1) ,                              12 °C
                     reset: ok(TE1) AND TE1 >= P1_Stop_TE1 )                            14 °C
P1_Need    = P1_OT_Need OR P1_Air_Need OR P1_Water_Need OR TV1_Ctrl > 0 OR Freeze_Group OR P1_Ex
P1_Cmd     = off_delay(P1_Need, P1_Off_Delay)                                           300 s
P1_Fault_Cond = on_delay( P1_Cmd AND NOT P1_Fdb , P1_Fdb_Delay )                        30 s
```

Design decision (all of 4.12): the source unit supervised the pump feedback but had no pump output. AHU01 commands
the pump: in cold weather continuously, otherwise whenever the heating valve is open, during freeze protection, and
for a weekly 60 s exercise. `P1_Ex_Day` uses the numbering of the EBO `WDAY` block (verify Monday's number when
building). The pump does not stop on the outdoor sensor
alone: the intake air TE6 (while the unit runs, with the same two limits) and the coil return water TE1 must be warm
too, and a fault of either keeps it running. A missing feedback while commanded sets the critical `P1_Latch`.

### 4.13 Heat exchanger frost protection and efficiency (module `HRU`, HFB `HruFrostEff`)

Frost protection:

```
PDE4_SP      = CURVE(PF01_Ctrl; 0,100; 100,300)                         Pa over extract fan speed %
Frost_Cond   = PDE4_Frost AND Run AND (TE6 <= PDE4_Frost_Temp OR bad(TE6)) AND PDE4 > PDE4_SP     0 °C
Frost_Active = off_delay(Frost_Cond, Frost_Hold)                        300 s
```

When ice builds on the extract side of the rotor (pressure drop above the speed dependent limit, intake air at or
below 0 °C) the rotor speed is limited to `Frost_HRU_Ctrl` (4.10), overriding the start-up hold too. Design
decision: `Frost_Hold` keeps the limit for 300 s after the condition clears to stop it from hunting.

Temperature efficiency (supply side):

```
Eff_En      = SR( set: SC3_Ctrl >= HRU_Efficiency_Start , reset: SC3_Ctrl <= HRU_Efficiency_Stop )   50 % / 45 %
Eff_Calc    = HRU_Efficiency_Cal AND Run AND Eff_En AND ok(TE3) AND ok(TE6) AND ok(TE7)
              AND (TE7 - TE6) >= HRU_Eff_Min_dT                                                        3 K
HRU_Efficiency = Eff_Calc ? LIMIT( (TE3 - TE6) * 100 / (TE7 - TE6) , 0, 100 ) : 0                      %
```

Design decision: the minimum temperature difference guards the division and keeps a meaningless value off the
graphic in mild weather.

### 4.14 Manual overrides

- `AOM`: off / manual on / automatic (4.4).
- `Season_Sel`: automatic / heating / cooling season (4.3).
- Enables: `Night_Cool_Mode`, `Night_Heat_Mode`, `Low_Speed_Mode`, `PDE4_Frost`, `HRU_Efficiency_Cal`, filter
  presence flags.
- Individual outputs: by EBO override (forcing) of the output points, not by program logic (design decision, same
  as the source). A forced output is shown on the graphic by the point's forced indication.

---

## 5. Alarms

Each alarm is an ALARM block in module `Alarms` (it creates a change-of-state alarm object). Delay = the block's on
delay; off delay 0. Priority classes: A = critical, EBO priority 1; B = EBO priority 2; C = EBO priority 3. Reset
text for all: "Alarm cleared".

| Name | Condition (alarm when true) | Delay | Class | Text |
|---|---|---|---|---|
| `Freeze_Alm` | `Freeze_Latch` | 0 s | A | Freeze protection tripped: coil return water or supply air too cold. Unit stopped |
| `Fire_Alm` | `Fire_Latch` | 0 s | A | Fire alarm from the fire panel. Unit stopped |
| `Stop_Alm` | `Stop_Latch` | 0 s | A | Emergency stop button pressed. Unit stopped |
| `P1_Alm` | `P1_Latch` | 0 s | A | Heating coil pump P1 not running. Unit stopped |
| `HN_Pres_Alm` | `HN_Pres_Latch` | 0 s | A | Heat supply water pressure alarm. Unit stopped |
| `HN_Temp_Alm` | `HN_Temp_Latch` | 0 s | A | Heat supply water temperature alarm. Unit stopped |
| `Supply_Fire_Alm` | `Supply_Fire_Latch` | 0 s | A | Supply air temperature at fire limit. Unit stopped |
| `Exhaust_Fire_Alm` | `Exhaust_Fire_Latch` | 0 s | A | Extract air temperature at fire limit. Unit stopped |
| `TE00_Alm` | `bad(TE00)` | 180 s | B | Outdoor temperature sensor TE00 faulty |
| `TE1_Alm` ... `TE8_Alm` | `bad(TEx)` (8 alarms) | 180 s | B | Temperature sensor TEx faulty (x filled in) |
| `TE10_1_Alm` ... `TE10_3_Alm` | `bad(TE10_x)` (3 alarms) | 180 s | B | Room temperature sensor TE10.x faulty |
| `Supply_Temp_Alm` | `Supply_Released AND ABS(TE2 - Active_SP) > Supply_Temp_Dev` (5 K) | 300 s | B | Supply air temperature deviates from setpoint |
| `Supply_Pres_Alm` | `Supply_Released AND ABS(PE1 - Supply_Pressure_SP) * 100 / Supply_Pressure_SP > Supply_Pres_Dev` (25 %) | 900 s | B | Supply duct pressure deviates from setpoint |
| `Exhaust_Pres_Alm` | the same with PE2, `Exhaust_Pressure_SP`, `Exhaust_Released`, `Exhaust_Pres_Dev` (25 %) | 900 s | B | Extract duct pressure deviates from setpoint |
| `TF01_Alm` | `TF01_Cmd AND NOT TF01_Fdb` | 900 s | B | Supply fan TF01 commanded but not running |
| `PF01_Alm` | `PF01_Cmd AND NOT PF01_Fdb` | 900 s | B | Extract fan PF01 commanded but not running |
| `HRU_Alm` | `SC3_Fault == 0` | 180 s | B | Heat recovery drive SC3 fault |
| `HRU_Frost_Alm` | `Frost_Cond` | 180 s | B | Heat recovery icing: rotor speed limited |
| `HRU_Efficiency_Alm` | `Eff_Calc AND TE6 <= HRU_Temp_SP AND HRU_Efficiency <= HRU_Efficiency_SP AND SC3_Ctrl >= HRU_Ctrl_SP AND NOT Frost_Active` (5 °C, 40 %, 90 %) | 300 s | B | Heat recovery efficiency low |
| `HeatR_Alm` | `Run AND ok(TE3) AND ok(TE4) AND TV1_Ctrl >= HeatR_Valve_SP AND (TE4 - TE3) < HeatR_dT` (30 %, 1 K) | 300 s | B | Heating coil gives no heat although the valve is open |
| `CoolR_Alm` | `Run AND Season_Mode AND ok(TE4) AND ok(TE5) AND TV2_Ctrl >= CoolR_Valve_SP AND (TE4 - TE5) < CoolR_dT` (30 %, 1 K) | 300 s | B | Cooling coil gives no cooling although the valve is open |
| `PDE3_Alm` | `PDE3_Filter AND Supply_Released AND PDE3 > CURVE(TF01_Ctrl; 0,10; 100,150)` | 300 s | C | Supply filter stage 1 dirty |
| `PDE1_Alm` | `PDE1_Filter AND Supply_Released AND PDE1 > CURVE(TF01_Ctrl; 0,10; 100,150)` | 300 s | C | Supply filter stage 2 dirty |
| `PDE2_Alm` | `PDE2_Filter AND Exhaust_Released AND PDE2 > CURVE(PF01_Ctrl; 0,10; 100,150)` | 300 s | C | Extract filter dirty |

Totals: 8 class A, 22 class B, 3 class C = 33 alarms. `Alarms\Critical_Alarm` is a public signal for graphics and
dashboards, not an alarm of its own.

---

## 6. Setpoints and parameters

"Op" = operator setpoint: public, writable, kept over a power failure (PVR/PVB/PVI, flag 7). "Eng" = engineering
constant (`[Const]`, public, changeable as a program property). "Priv" = private constant.

### 6.1 Inputs, Operation, P1

| Name | Module | Default | Unit | Range | Kind | Meaning |
|---|---|---|---|---|---|---|
| Freeze_SP | Inputs | 6 | °C | 3 ... 10 | Op | Freeze protection limit for TE1 and TE2 |
| TF01_K | Inputs | 350 | | 1 ... 2000 | Op | Supply fan flow factor |
| PF01_K | Inputs | 350 | | 1 ... 2000 | Op | Extract fan flow factor |
| MinTemp | Inputs | -120 | °C | | Priv | Sensor fault lower limit |
| MaxTemp | Inputs | 120 | °C | | Priv | Sensor fault upper limit |
| OT_Fault_Value | Inputs | 0 | °C | -30 ... 10 | Eng | Outdoor value used while TE00 is faulty |
| AOM | Operation | 2 | | 0 / 1 / 2 | Op | Off / manual on / automatic |
| Season_Sel | Operation | 0 | | 0 / 1 / 2 | Op | Automatic / heating / cooling season |
| Heating_Mode | Operation | 0 | | 0 / 1 | Op | Warm water available in the cooling coil |
| Season_Cool_OT | Operation | 11 | °C | 5 ... 20 | Op | Daily mean that switches to cooling season |
| Season_Heat_OT | Operation | 9 | °C | 0 ... 15 | Op | Daily mean that switches to heating season |
| HS10_Run_Time | Operation | 3600 | s | 0 ... 14400 | Op | Run-on after HS10 |
| Night_Cool_Mode | Operation | 1 | | 0 / 1 | Op | Night cooling enabled |
| Night_Cool_Start_T | Operation | 22 | °C | 20 ... 30 | Op | Room mean that starts night cooling |
| Night_Cool_Stop_T | Operation | 19 | °C | 15 ... 25 | Op | Room mean that stops night cooling |
| Night_Cool_OT_Min | Operation | 12 | °C | 0 ... 20 | Op | Lowest outdoor temperature for night cooling |
| Night_Cool_OT_Max | Operation | 19 | °C | 10 ... 25 | Op | Highest outdoor temperature for night cooling |
| Night_Heat_Mode | Operation | 1 | | 0 / 1 | Op | Night heating enabled |
| Night_Heat_Start_T | Operation | 18 | °C | 15 ... 22 | Op | Room mean that starts night heating |
| Night_Heat_Stop_T | Operation | 20 | °C | 17 ... 25 | Op | Room mean that stops night heating |
| Night_Heat_OT_Min | Operation | -15 | °C | -30 ... 0 | Op | Lowest previous-day mean for night heating |
| Night_Heat_OT_Max | Operation | 0 | °C | -10 ... 10 | Op | Highest previous-day mean for night heating |
| Night_Cond_Delay | Operation | 60 | s | | Eng | On and off delay of the night conditions |
| P1_Start_OT | P1 | 9 | °C | 0 ... 15 | Op | Pump runs continuously below this outdoor temperature |
| P1_Stop_OT | P1 | 11 | °C | 2 ... 20 | Op | ... until it rises above this |
| P1_Start_TE1 | P1 | 12 | °C | 5 ... 20 | Op | Pump also runs while the coil return water is at or below this |
| P1_Stop_TE1 | P1 | 14 | °C | 7 ... 25 | Op | ... until it rises above this |
| P1_Off_Delay | P1 | 300 | s | 0 ... 1800 | Eng | Pump run-on |
| P1_Fdb_Delay | P1 | 30 | s | 5 ... 120 | Eng | Feedback supervision delay |
| P1_Ex_Day | P1 | Monday | | WDAY value | Eng | Exercise weekday |
| P1_Ex_Hour | P1 | 10 | h | 0 ... 23 | Eng | Exercise hour |
| P1_Ex_Time | P1 | 60 | s | 10 ... 600 | Eng | Exercise duration |

### 6.2 FAN

| Name | Default | Unit | Range | Kind | Meaning |
|---|---|---|---|---|---|
| Supply_Pressure_Set | 80 | Pa | 20 ... 400 | Op | Supply duct pressure setpoint |
| Exhaust_Pressure_Set | 60 | Pa | 20 ... 400 | Op | Extract duct pressure setpoint |
| Supply_Gain / Exhaust_Gain | 0.05 | %/Pa | 0.001 ... 1 | Op | Pressure controller gain |
| Supply_Integral_T / Exhaust_Integral_T | 60 | s | 5 ... 600 | Op | Integral time |
| Supply_Deriv_Time / Exhaust_Deriv_Time | 0 | s | 0 ... 60 | Op | Derivative time |
| Supply_Dead_Zone / Exhaust_Dead_Zone | 1 | Pa | 0 ... 10 | Op | Dead zone |
| Supply_Ctrl_Min_SP / Exhaust_Ctrl_Min_SP | 20 | % | 0 ... 50 | Eng | Minimum fan speed |
| Supply_Ctrl_Max_SP / Exhaust_Ctrl_Max_SP | 60 | % | 50 ... 100 | Eng | Maximum fan speed |
| Supply_StrokeTime / Exhaust_StrokeTime | 20 | s | | Eng | PIDP stroke (ramp) time |
| Supply_ControlInt / Exhaust_ControlInt | 1 | s | | Eng | Controller interval |
| Supply_Fan_Delay | 60 | s | 0 ... 300 | Eng | Supply fan release after damper opening |
| Exhaust_Fan_Delay | 30 | s | 0 ... 300 | Eng | Extract fan release after damper opening |
| Low_Speed_Mode | 0 | | 0 / 1 | Op | Cold weather pressure reduction enabled |
| Low_Speed_Temp_SP | -10 | °C | -30 ... 0 | Op | Outdoor temperature that starts it |
| Low_Speed_Deviation | 2 | K | 0.5 ... 5 | Op | Hysteresis |
| Low_Speed_Delay_Off | 600 | s | | Eng | Hold after the cold condition clears |
| Temp_X1..X4 / Press_Y1..Y4 | -20/50, -15/65, -10/75, -5/80 | °C / Pa | | Eng | Supply low speed curve |
| Temp1_X1..X4 / Press1_Y1..Y4 | -20/40, -15/50, -10/55, -5/60 | °C / Pa | | Eng | Extract low speed curve |

### 6.3 ST

| Name | Default | Unit | Range | Kind | Meaning |
|---|---|---|---|---|---|
| ET_X1 / SP_Y1 | 18 / 21.5 | °C | | Op | Setpoint curve point 1 (extract / supply) |
| ET_X2 / SP_Y2 | 23 / 16 | °C | | Op | Setpoint curve point 2 |
| ST_Fault_SP | 19 | °C | 15 ... 25 | Op | Supply setpoint while TE7 is faulty |
| HRU_Gain / HRU_Ti | 1.5 / 45 | - / s | 0.1 ... 20 / 10 ... 600 | Op | Heat exchanger controller gain, integral time |
| CCH_Gain / CCH_Ti | 2 / 45 | - / s | same | Op | Cooling coil as heater controller |
| HC_Gain / HC_Ti | 1.5 / 45 | - / s | same | Op | Heating coil controller |
| Cool_Gain / Cool_Ti | 2.5 / 45 | - / s | same | Op | Cooling valve controller |
| Neutral_Zone | 0.5 | K | 0.2 ... 3 | Op | Band around the setpoint between the heating and the cooling side |
| Stage_Up_Delay / Stage_Down_Delay | 30 / 30 | s | | Eng | Time at 100 % before the next stage is released / at 0 % before it is handed back |
| Temp_Derivative_Time | 0 | s | 0 ... 60 | Op | Derivative time |
| Temp_Dead_Zone | 0.1 | K | 0 ... 1 | Op | Dead zone |
| Night_Cool_ST | 17 | °C | 15 ... 25 | Op | Supply setpoint in night cooling |
| Night_Heat_ST | 27 | °C | 18 ... 35 | Op | Supply setpoint in night heating |
| Night_Cool_Min_Temp / Max | 15 / 25 | °C | | Eng | Limits of Night_Cool_ST |
| Night_Heat_Min_Temp / Max | 18 / 35 | °C | | Eng | Limits of Night_Heat_ST |
| Cool_Recovery_Hist | 2 | K | 0.5 ... 5 | Op | Cooling recovery hysteresis |
| PreHeat_Heat_ST | 9 | °C | -10 ... 15 | Op | Pre-heat at start when outdoor at or below |
| PreHeat_Heat_Delay | 1 | s | 1 ... 60 | Eng | Pre-heat pulse length |
| PreHeat_Valve / PreHeat_Valve_HM | 75 / 50 | % | | Eng | Heating valve position loaded by pre-heat (without / with `Heating_Mode`) |
| HRU_Preheat_Del | 1200 | s | 0 ... 3600 | Eng | Rotor 100 % hold after pre-heat |
| Frost_HRU_Ctrl | 50 | % | 0 ... 100 | Op | Rotor speed limit in frost protection |
| Coil_Heat_ST | 10 | °C | 5 ... 30 | Op | Minimum coil return water temperature |
| Coil_Heat_ON_SP / OFF_SP | 10 / 12 | K | | Eng | Enable hysteresis of the coil controller |
| Coil_Gain / Coil_Ti | 5 / 60 | %/K / s | | Eng | Coil controller tuning |
| Heat/Cool controller limits | -10 ... 150 / -50 ... 150 | | | Eng | UMin / UMax |
| Split points | 4.10 tables | | | Eng | PRCNT values (`Heat_HRU` 10/75, `Heat_HM_HRU` 10/45, `Heat_HM_Cool` 50/100, `Heat_Heat` 75/145, `Heat_HM_Heat` 100/150, `Cool_HRU` 10/100, `Cool_CR_HRU` -10/-30, `Cool_Cool` -10/-50, `Cool_CR_Cool` -30/-50, `Cool_Heat` 100/150) |

### 6.4 Alarms and HRU

| Name | Module | Default | Unit | Kind | Meaning |
|---|---|---|---|---|---|
| Supply_Fire_Temp | Alarms | 50 | °C | Op | Supply air fire limit |
| Exhaust_Fire_Temp | Alarms | 50 | °C | Op | Extract air fire limit |
| Supply_Temp_Dev | Alarms | 5 | K | Op | Supply temperature deviation limit |
| Supply_Pres_Dev / Exhaust_Pres_Dev | Alarms | 25 | % | Op | Pressure deviation limits |
| PDE1_Filter / PDE2_Filter / PDE3_Filter | Alarms | 1 | | Op | Filter fitted (1) / filter alarm off (0) |
| PDE1/2/3_X1, Y1, X2, Y2 | Alarms | 0, 10, 100, 150 | %, Pa | Eng | Filter alarm curve over fan speed |
| PDE4_Frost | Alarms | 1 | | Op | Rotor frost protection enabled |
| PDE4_Frost_Temp | Alarms | 0 | °C | Op | Frost protection active at intake temperature at or below |
| PDE4_X1, Y1, X2, Y2 | Alarms | 0, 100, 100, 300 | %, Pa | Eng | Frost limit curve over extract fan speed |
| Frost_Hold | Alarms | 300 | s | Eng | Frost limit hold time |
| HRU_Temp_SP | Alarms | 5 | °C | Op | Efficiency alarm only at intake temperature at or below |
| HRU_Efficiency_SP | Alarms | 40 | % | Op | Efficiency alarm limit |
| HRU_Ctrl_SP | Alarms | 90 | % | Op | Efficiency alarm only at rotor speed at or above |
| HeatR_Valve_SP / HeatR_dT | Alarms | 30 / 1 | % / K | Eng | Heating coil function alarm |
| CoolR_Valve_SP / CoolR_dT | Alarms | 30 / 1 | % / K | Eng | Cooling coil function alarm |
| HRU_Efficiency_Cal | HRU | 1 | | Op | Efficiency calculation enabled |
| HRU_Efficiency_Start / Stop | HRU | 50 / 45 | % | Op | Calculate when rotor speed above / stop below |
| HRU_Eff_Min_dT | HRU | 3 | K | Eng | Minimum TE7 - TE6 for the calculation |

Count: 65 operator setpoints and 94 engineering / private constants (paired names counted individually, the ten
PRCNT split pairs as 20 values, the six curves as 32 values).

---

## 7. Component descriptions for the info popups

**FZ01 Outdoor air damper.** Shut-off damper at the outdoor air intake. It opens as soon as the unit is started
and closes immediately when the unit stops or a critical alarm trips. It is an open/closed damper with spring
return, so it also closes on power failure. The fans are only released after it has had time to open.

**FZ02 Exhaust air damper.** Shut-off damper at the exhaust air outlet. It opens and closes together with the
outdoor air damper. The extract fan is released 30 s after it opens. Closed when stopped and on power failure.

**TE00 Outdoor temperature.** Outdoor air temperature from a sensor outside the building. It is used for
start-up pre-heat, the heating coil pump, the season changeover (daily mean), night cooling and night heating,
cooling recovery and the optional fan low speed mode. A faulty sensor gives an alarm after 3 minutes; the unit then
assumes 0 °C and does not run the night modes.

**TE6 Intake air temperature.** Temperature of the outdoor air just behind the intake damper, before the filters.
It is the cold side reference for the heat recovery efficiency and enables the heat recovery frost protection at
0 °C and below. While the unit is stopped it shows plant room temperature rather than outdoor temperature.

**Supply filter stage 1 (PDE3).** First filter stage in the outdoor air. It keeps coarse dust away from the
second stage and the coils. Its condition is supervised by the pressure drop PDE3.

**PDE3 Filter pressure drop, stage 1.** Pressure difference across the first supply filter. An alarm "filter
dirty" is given when the pressure drop has been above the limit for 5 minutes; the limit rises with the supply fan
speed from 10 Pa at 0 % to 150 Pa at 100 %. The alarm can be switched off when no filter is fitted.

**Supply filter stage 2 (PDE1).** Second, finer filter stage in the outdoor air, before the heat recovery. Its
condition is supervised by the pressure drop PDE1.

**PDE1 Filter pressure drop, stage 2.** Pressure difference across the second supply filter. Alarm "filter dirty"
after 5 minutes above the speed dependent limit (10 Pa at 0 % to 150 Pa at 100 % supply fan speed).

**SC3 Rotary heat exchanger.** Rotating wheel that transfers heat (and in summer, cooling) from the extract air to
the supply air. Its speed 0 ... 100 % is the first stage of the supply temperature sequence. At a cold start it runs
at 100 % for 20 minutes. When ice builds on the extract side its speed is limited to 50 %. A drive fault gives an
alarm after 3 minutes.

**PDE4 Heat exchanger pressure drop.** Pressure difference across the extract side of the rotor. It rises when
ice builds up. At intake temperature 0 °C or below, a value above the limit (100 Pa at 0 % to 300 Pa at 100 %
extract fan speed) activates frost protection: rotor speed limited to 50 % and alarm after 3 minutes.

**HRU efficiency.** Calculated temperature efficiency of the heat recovery, (TE3 - TE6) / (TE7 - TE6). Shown only
when the rotor runs above 50 % and the temperature difference is large enough. In cold weather an efficiency below
40 % at 90 % rotor speed or more gives an alarm after 5 minutes.

**TE3 Temperature after heat recovery.** Supply air temperature after the rotor. Used for the heat recovery
efficiency and to check that the heating coil heats.

**Heating coil (HC1).** Hot water coil that heats the supply air after the heat recovery. It is the last heating
stage of the supply temperature sequence. Its return water is kept at least at 10 °C at all times to protect it
from freezing.

**TV1 Heating valve.** Control valve of the heating coil, 0 ... 100 %. It opens after the heat recovery has
reached full speed (in the cooling season after the rotor as well). Independent of the sequence it opens to keep
the coil return water above 10 °C, and it opens fully when freeze protection trips or the pump fails.

**P1 Heating coil pump.** Circulation pump of the heating coil. It runs continuously when the outdoor temperature
is 9 °C or below, whenever the heating valve is open, and during freeze protection, with a 5 minute run-on. It is
exercised once a week for 1 minute. If it does not report running within 30 s of its command the unit stops with a
critical alarm.

**TE1 Coil return water temperature.** Water temperature leaving the heating coil. It is controlled to at least
10 °C by the heating valve. At 6 °C or below, or on a sensor fault, freeze protection trips: the unit stops, the
valve opens fully and an alarm is given; reset is needed.

**TE4 Temperature after heating coil.** Supply air temperature after the heating coil. With TE3 it shows the
coil's heating effect; if the heating valve is open at least 30 % but the air warms less than 1 K, an alarm is
given after 5 minutes.

**Cooling coil (CC1).** Water coil after the heating coil. In the cooling season it cools the supply air with
chilled water. When the supplying plant reports warm water in the circuit, it is used in the heating season as a
heating stage between the heat recovery and the heating coil.

**TV2 Cooling valve.** Control valve of the cooling coil, 0 ... 100 %. In the cooling season it opens when the
supply air is too warm, after the heat recovery has done what it can. It closes when the unit stops.

**TE5 Temperature after cooling coil.** Supply air temperature after the cooling coil. With TE4 it shows the
cooling effect; if the cooling valve is open at least 30 % but the air cools less than 1 K, an alarm is given after
5 minutes.

**TF01 Supply fan.** Variable speed fan that blows the treated air into the supply duct. It is started 60 s after
the dampers open and its speed (20 ... 60 %) is controlled to hold the supply duct pressure PE1. If it does not
report running while commanded, an alarm is given after 15 minutes.

**PDE10 Supply fan flow measurement.** Pressure difference at the supply fan inlet cone. The supply air flow in
m3/s is calculated from it with the fan's K factor and shown next to it.

**TE2 Supply air temperature.** Temperature of the air going to the rooms; the main control sensor of the unit.
Its setpoint follows the extract temperature (21.5 °C at 18 °C extract air down to 16 °C at 23 °C). A deviation of
more than 5 K gives an alarm after 5 minutes. 6 °C or below while running trips freeze protection, 50 °C or above
trips the unit as a fire risk.

**PE1 Supply duct pressure.** Static pressure in the supply duct; the supply fan speed is controlled to its
setpoint (80 Pa). A deviation of more than 25 % from the setpoint for 15 minutes gives an alarm.

**PE2 Extract duct pressure.** Static pressure (suction) in the extract duct; the extract fan speed is controlled
to its setpoint (60 Pa). A deviation of more than 25 % for 15 minutes gives an alarm.

**TE7 Extract air temperature.** Temperature of the air returning from the rooms. It sets the supply temperature
setpoint, decides on cooling recovery in summer and is the warm side reference of the heat recovery efficiency.
50 °C or above trips the unit as a fire risk.

**Extract filter (PDE2).** Filter in the extract air that protects the heat recovery wheel. Its condition is
supervised by the pressure drop PDE2.

**PDE2 Extract filter pressure drop.** Pressure difference across the extract filter. Alarm "filter dirty" after
5 minutes above the limit, which rises with the extract fan speed from 10 Pa at 0 % to 150 Pa at 100 %.

**TE8 Exhaust air temperature.** Temperature of the air leaving the heat recovery towards the exhaust. Shown for
information; a very low value together with rising PDE4 indicates icing of the wheel.

**PF01 Extract fan.** Variable speed fan that draws air from the rooms. It is started 30 s after the dampers open
and its speed (20 ... 60 %) is controlled to hold the extract duct pressure PE2. If it does not report running while
commanded, an alarm is given after 15 minutes.

**PDE20 Extract fan flow measurement.** Pressure difference at the extract fan inlet cone, from which the extract
air flow in m3/s is calculated.

**TE10.1, TE10.2, TE10.3 Room temperatures.** Three room temperature sensors in the served zone. Their mean
(faulty sensors left out) starts and stops night cooling (above 22 °C / below 19 °C) and night heating (below
18 °C / above 20 °C). Each sensor gives a fault alarm after 3 minutes. (One popup per sensor with this text and its
own number.)

**HS10 Extended run button.** Push button in the zone. In automatic mode a press runs the unit for 1 hour beyond
the schedule (or extends the current run). It has no effect when the mode selector is Off or Manual.

**SB01 Emergency stop.** Stop button on the unit. Pressing it stops the unit at once with a critical alarm. After
releasing the button the unit restarts only after an alarm reset.

**FA01 Fire alarm.** Contact from the fire alarm panel. On a fire alarm the unit stops at once, dampers close and a
critical alarm is given. After the fire panel is reset, the unit needs an alarm reset to restart.

**Operating mode selector (AOM).** Selects how the unit runs: Off (stopped, also at night), Manual (runs
continuously) or Auto (time schedule, extended run button and night cooling / heating). Critical alarms stop the
unit in every position. The current state is shown as run mode: stopped, normal, night cooling, night heating or
alarm stop.

**Season selector.** Selects the temperature sequence: Auto, Heating season or Cooling season. In Auto the unit
switches to the cooling season when the previous day's mean outdoor temperature is 11 °C or more and back to
heating at 9 °C or less. Night heating is only possible in the heating season, night cooling only in the cooling
season.

**Alarm reset.** Resets the latched critical alarms (freeze, fire, emergency stop, pump, heat supply, fire risk
temperatures). A reset only clears alarms whose cause has gone; the unit then restarts by itself if the mode
selector and schedule ask for it.

Count: 38 popup texts (35 components and sensors, plus mode selector, season selector and reset); the room
sensor text serves three sensors, so 40 graphic objects carry a popup.

---

## 8. Signals for the operator graphic and the dashboard

### 8.1 Values at each component

| Component | Show | Adjustable from the graphic |
|---|---|---|
| FZ01, FZ02 | `FZ01_Cmd` / `FZ02_Cmd` open / closed | |
| TE6, TE3, TE4, TE5, TE8, TE00 | value °C, sensor fault state | |
| TE2 | value, `Active_SP`, deviation alarm | `SP_Y1`, `SP_Y2`, `ET_X1`, `ET_X2` (settings page) |
| TE7 | value | |
| PDE1, PDE2, PDE3 | value Pa, filter alarm | |
| SC3 | `SC3_Ctrl` %, `SC3_Cmd`, fault, frost state `Frost_Active` | `Frost_HRU_Ctrl` |
| PDE4 | value, `PDE4_SP` | |
| HRU efficiency | `HRU_Efficiency` % | |
| TV1 | `TV1_Ctrl` % | `Coil_Heat_ST` |
| P1 | `P1_Cmd`, `P1_Fdb`, alarm | |
| TE1 | value, freeze state | `Freeze_SP` |
| TV2 | `TV2_Ctrl` % | |
| TF01, PF01 | `TF01_Ctrl`/`PF01_Ctrl` %, command, feedback, alarm | |
| PDE10, PDE20 | value Pa and `Supply_Flow` / `Exhaust_Flow` m3/s | |
| PE1, PE2 | value, `Supply_Pressure_SP` / `Exhaust_Pressure_SP` | `Supply_Pressure_Set`, `Exhaust_Pressure_Set` |
| TE10.1 ... TE10.3 | values, `Room_Avg` | |
| HS10 | state, `HS10_Ext` | |
| Unit header | `Run_Mode`, `Season_Mode`, `Critical_Alarm`, `Heating_Mode` | `AOM`, `Season_Sel`, Reset (`Reset_Cmd`) |

A settings page holds: fan tuning and limits, low speed mode, setpoint curve, controller tuning, night cooling and
night heating parameters (with `Night_Schedule` state and `Room_Avg`), pre-heat values, pump values, alarm limits.

### 8.2 Trend logs and the measurement dashboard

| Signal | Interval | Dashboard |
|---|---|---|
| TE2, `Active_SP` | 1 min | yes |
| PE1, `Supply_Pressure_SP`, PE2, `Exhaust_Pressure_SP` | 1 min | yes |
| TF01_Ctrl, PF01_Ctrl, SC3_Ctrl, TV1_Ctrl, TV2_Ctrl | 1 min | yes |
| TE00, TE6, TE3, TE4, TE5, TE7, TE8 | 5 min | yes |
| TE1 | 1 min | yes |
| TE10_1, TE10_2, TE10_3, `Room_Avg` | 5 min | yes (`Room_Avg`) |
| `Supply_Flow`, `Exhaust_Flow` | 5 min | yes |
| PDE1, PDE2, PDE3 | 15 min | yes (filter state) |
| PDE4 | 5 min | |
| `HRU_Efficiency` | 15 min | yes |
| `OT_Day_Mean` | 1 h | |
| `Run_Mode`, `Season_Mode`, `Critical_Alarm`, `P1_Cmd`, `P1_Fdb`, `Frost_Active` | change of value | yes (state tiles) |

---

## 9. Simulation notes

A plant model closing every loop needs the following responses (numbers are derived elsewhere from trend data):

- **Dampers**: FZ01/FZ02 commands to damper position with a travel time; air can only flow with the dampers open.
- **Fans**: fan speed (TF01_Ctrl / PF01_Ctrl, only while TF01_Cmd / PF01_Cmd) gives air flow against the duct
  system; PE1 rises with supply flow (roughly with its square), PE2 with extract flow. PDE10 / PDE20 rise with
  the square of the respective flow. TF01_Fdb / PF01_Fdb follow the start commands with a short delay.
- **Filters**: PDE1, PDE3 rise with the square of the supply flow, PDE2 with the extract flow; a dirt factor lets a
  test raise them.
- **Intake**: TE6 = outdoor temperature TE00 when air flows; relaxes towards plant room temperature when stopped.
- **Heat recovery**: TE3 = TE6 + efficiency(SC3_Ctrl, flows) * (TE7 - TE6), efficiency rising with rotor speed and
  saturating; TE8 = TE7 - (heat taken) by an energy balance with the extract flow. PDE4 rises with extract flow and
  with an ice factor that grows when TE8 is below freezing and decays when the rotor slows. SC3_Fault normally 1.
- **Heating coil**: TE4 = TE3 + heat from the coil, which grows with TV1_Ctrl (valve characteristic) and needs the
  pump running; first order lag of tens of seconds. TE1 falls with air flow and cold TE3, rises with valve
  opening; with the unit stopped and the valve closed TE1 drifts towards plant room temperature, with no pump
  running it drops in cold air. P1_Fdb follows P1_Cmd.
- **Cooling coil**: TE5 = TE4 - cooling as a function of TV2_Ctrl and of the water temperature; when the test sets
  `Heating_Mode` = 1 the same valve heats instead.
- **Supply**: TE2 = TE5 plus fan heat (small, rises with speed), lag; with no flow TE2 relaxes to duct ambient.
- **Room / extract**: room mean responds slowly to supply air temperature times flow, internal gains and outdoor
  losses; TE7 follows the room mean plus a small offset; TE10_x are the room mean with small individual offsets.
- **Outdoor**: TE00 as a test input (daily profile), plus a clock so the daily mean, schedules and the weekly pump
  exercise can be tested.
- **Safety inputs**: FA01 and SB01 must be 1 for the unit to run; HN_Pres_In / HN_Temp_In 0. Each is a test
  input to exercise the critical chain. Reset via `Reset_Cmd`.

---

## 10. Deviations from the source and design decisions

Deviations from the source unit (in generic words):

1. **Fire alarm** is a real input (FA01, normally closed) that trips the unit through a latch; in the source the
   input was unbound and held healthy.
2. **Outdoor temperature** is its own sensor TE00. In the source the "outdoor" value was the intake duct sensor,
   which reads plant room temperature while the unit is stopped. On a TE00 fault a fixed substitute (0 °C) is used
   and the night modes are blocked; no fallback to the intake sensor.
3. **Heating coil pump** now has a command output with outdoor, valve and freeze conditions, run-on and a weekly
   exercise; the feedback alarm applies only while commanded. In the source there was no pump output and a missing
   feedback tripped the unit at any time.
4. **Second heating and second cooling valve dropped**: the source calculated two signals with no consumer. With
   warm water in the cooling coil, the cooling valve range now runs 50 ... 100 instead of 50 ... 75 (removing the
   dead band left by the missing second valve). The cooling controller's lower limit is -50 instead of -110.
5. **Separate damper and fan start outputs**; in the source the fan commands drove the dampers.
6. **Fan controller limits** equal the output limits (20 ... 60 %); in the source the controller could run to
   110 % and wind up behind the 60 % output limit.
7. **Values from other programs and servers made local**: night mode master switches dropped (the local enables
   remain); heat supply alarms are bindable local inputs, default 0; the coil heating-mode flag is a local
   writable value, default 0; the season is decided locally from the daily outdoor mean with a manual selector;
   schedules are local schedule objects.
8. **Stop button and heat supply alarms** have their own alarm blocks; in the source they stopped the unit without
   an alarm of their own.
9. **Single alarm layer**: delays and priorities are in the ALARM blocks; the critical chain uses the latches, not
   the alarm states.
10. **Fan and heat exchanger feedback/fault selectors removed**: fixed to running feedback for the fans and a fault
    contact for the heat exchanger, as the source unit was configured. Unused inputs dropped; the unbound manual
    reset input became an optional reset DI.
11. **Night modes only in automatic** (the source allowed them with the selector at off).
12. **Outputs gated by Run**: the 20 minute rotor hold after pre-heat no longer runs the rotor of a stopped unit.
13. **Heat exchanger frost protection** limits the rotor to at most 50 % (instead of setting 50 %) and holds for
    300 s.
14. **Low speed curves** replaced with values that reduce pressure; the function stays off by default.
15. **Coil function alarms** redefined as "valve open but no temperature change" (the source expressions were
    ambiguous). The extract filter alarm text names the extract filter.
16. **Sequence controllers rest at 0 when inactive** instead of holding their last value.
17. Removed leftovers: unused pre-heat rotor delay constant, an ineffective reset-loop delay, an unused HFB
    input, crossed room sensor bindings, misspelt names.
17. **One controller per stage** (heat exchanger, cooling coil as heater, heating coil, cooling valve) with a
    staging rule, instead of one sequence controller per season with split ranges: the loops differ, so each gets
    its own gain and integral time.

Design decisions where the source was inferred or unverified:

- SR latches reset-dominant (the source relied on cause and reset not coinciding).
- One write of `Reset_Cmd` = one reset pulse; reset ineffective while the cause persists.
- PRCNT limited to 0 ... 100 %; CURVE held at end values.
- Pre-heat pulse loads the heating controller through its tracking input.
- HS10 run-on time in the program (1 h); the source had none.
- Freeze check on TE2 only while running.
- Room mean from healthy sensors only; daily mean skips faulty samples; setpoint fallback when TE7 is faulty.
- Efficiency calculation guarded by a minimum temperature difference and limited to 0 ... 100 %.
- Setpoint curve point 1 at 19.0 °C (source 18.96 °C, displayed as 19.0).
- `Heating_Mode` default 0 (chilled water), since a stand-alone unit has no plant reporting warm water.
