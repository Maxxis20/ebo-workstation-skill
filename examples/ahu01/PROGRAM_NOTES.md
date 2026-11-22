# AHU01 program: notes on the build

`make_program.py` writes `AHU01.aut` (program text), `expected.json` (what an export must show) and `io.json`
(every bindable public signal, generated from the same objects). `selftest_aut.py` reads the `.aut` back with
`ebox.parse_aut` and checks every wire end, every input, the name rules and every `io.json` path.
`make_program.py --only G1,G2` writes `AHU01_part.aut` with just those groups; whatever they read from other
groups comes from public test values in module `Test` (PVR / PVB named as the signal). `--list` names the groups.

Counts: 362 function blocks (532 lines incl. 170 HFB pin blocks), 707 connections, 20 HFB instances, 33 ALARM
blocks, 93 constants (91 public, 2 private), 65 operator setpoints, 260 public names.

## 1. Structure as built

Groups (`--only` names) in build order, with the module(s) they fill:

| Group | Built as | Module | Pins (in / out) |
|---|---|---|---|
| Inputs | flat | Inputs, Operation | 20 RI, 8 BI, BI HN_Pres_In / HN_Temp_In (Inputs), BI Time_Schedule / Night_Schedule (Operation), DELB Reset_Cmd, TRIG Reset_Pulse |
| SensorCheck | HFB `Inputs\SensorCheck` | Inputs | in: TE00, TE1..TE8, TE10_1..3 (12) / out: bad_TE00..bad_TE10_3, OT, OT_OK, Room_Avg, Room_OK (16) |
| DayMean | HFB `Inputs\DayMean` | Inputs | in: OT, OT_OK / out: OT_Day_Mean |
| Modes | HFB `Operation\Modes` (+ PVI AOM, Season_Sel outside) | Operation | in: AOM, Season_Sel, OT_Day_Mean, Time_Schedule, HS10, Night_Schedule, Critical_Alarm, OT, OT_OK, Room_Avg, Room_OK (11) / out: Season_Mode, Operation, Night_Cooling, Night_Heating, Run, Run_Mode (6) |
| Latches | 8 x HFB `Alarms\CL_<cause>` (function `crit_latch`) + causes flat | Alarms | in: Cause, Reset_Pulse / out: Latched |
| Fan | 2 x HFB `FAN\FanCtrl_Supply/_Exhaust` (function `fan_ctrl`) + low speed flat | FAN | in: Run, Critical_Alarm, PV, Pressure_Set, Low_Speed_Cmd, Low_Speed_SP, Gain, Ti, Td, DZ, Fdb, K, PDE, Pres_Dev (14) / out: Released, Speed, Flow, Pres_Dev_Cond, Fdb_Fault_Cond, Pressure_SP (6) |
| Filters | 3 x HFB `Alarms\FA_PDE3/1/2` (function `filter_alarm`) | Alarms | in: Enable, Released, DP, Fan_Speed / out: Alarm_Cond |
| TempSeq | HFB `ST\TempSeq` (+ PVB Heating_Mode outside) | ST | in: TE2, TE7, OT, OT_OK, bad_TE7, Run, Season_Mode, Operation, Night_Cooling, Night_Heating, Heating_Mode (11) / out: Active_SP, H, C, SC3_Seq, TV1_Seq, TV2_Seq, PreHeat_Pulse, HRU_Hold, Cool_Recovery (9) |
| CoilProtect | HFB `ST\CoilProtect` | ST | in: TE1, Freeze_Group / out: Coil_Heat_Ctrl |
| HruFrostEff | HFB `HRU\HruFrostEff` | HRU | in: PDE4, PF01_Ctrl, TE3, TE6, TE7, SC3_Ctrl, Run, bad_TE3, bad_TE6, bad_TE7 (10) / out: Frost_Active, Frost_Cond, HRU_Efficiency, Eff_Calc (4) |
| PumpCtrl | HFB `P1\PumpCtrl` | P1 | in: OT, TV1_Ctrl, Freeze_Group, P1_Fdb / out: P1_Cmd, P1_Fault_Cond |
| Outputs | flat | Outputs | per output X: public `Outputs\X` + `Outputs\X_OUT` (RO / BO) |
| Alarms | flat | Alarms | 33 ALARM blocks and the conditions not made elsewhere |

Blocks inside an HFB keep the module of the specification (e.g. `Inputs\Supply_Flow` is inside `FanCtrl_Supply`).

## 2. Deviations from the specification

1. **HS10_Run_Time** is a public constant (program property), not a PVR: it is the off delay of a DELAY block and
   block parameters cannot be wired.
2. **P1_Ex_Day** is a public PVI `P1\P1_Ex_Day`, default 1, as instructed: the WDAY numbering for Monday was not
   found offline. **Check it in the editor help and correct the value.**
3. **Setpoint curve** (ET_X1/SP_Y1, ET_X2/SP_Y2 are operator setpoints) is an expression `ST\Temp_SP_Curve`
   (linear between the two points, held outside), because CURVE points are parameters.
4. **Engineering constants used inside logic** reach it as `LIMIT (c,c)` fed by `OpR (0)` (output = c), since a
   public constant is refused inside an expression: OT_Fault_Value, PreHeat_Valve, PreHeat_Valve_HM, Coil_Gain, Coil_Ti,
   HRU_Eff_Min_dT, P1_Ex_Hour, HeatR_Valve_SP, HeatR_dT, CoolR_Valve_SP, CoolR_dT.
5. **Daily mean**: minute tick = `MINUTE` differs from its previous-cycle value (DELI), not the SECOND wrap (same
   meaning; MINUTE is on the proven list). Sum and count are ACCUM blocks; they are cleared one cycle after the
   midnight tick (DELB) so the SHR copies take the full day first. The 00:00 sample counts to the old day.
6. **HFB pins**: single-instance HFBs hold their own operator setpoints inside instead of as pins (Modes: season
   and night parameters; TempSeq: all ST setpoints; CoilProtect: Coil_Heat_ST; HruFrostEff: PDE4_Frost,
   PDE4_Frost_Temp, HRU_Efficiency_*; PumpCtrl: P1_*). Engineering constants are block parameters, not pins
   (FanCtrl delay / limits / stroke, FilterAlarm X1..Y2, CoilProtect ON/OFF, SensorCheck Min/MaxTemp,
   OT_Fault_Value). Added pins: FanCtrl `Pres_Dev` (alarm limit) and output `Pressure_SP`; TempSeq `OT_OK`,
   `bad_TE7` (cooling recovery); HruFrostEff `bad_TE3/6/7`. PumpCtrl has its clock inside (no pin).
7. **CritLatch** set input is `Cause` itself: `set AND NOT reset` = `Cause AND NOT (Reset_Pulse AND NOT Cause)` =
   `Cause`, so set and reset are never true together.
8. Pressure deviation is multiplied out: `|PE - SP| * 100 > Dev * SP` (no division).
9. `MAX(PDE, 0)` in the air flow is `(A>0)?A:0` (no MAX function in expressions); `MAX/MIN` elsewhere as `?:`.
10. AOM / Season_Sel / weekday / hour compared by ranges (`M>1.5`, `ABS(W-D)<0.5`), not by `=`.
11. The pump command inside module P1 is `P1\P1_Run` (HFB output pin `P1_Cmd`), so `Outputs\P1_Cmd` is the only
    P1_Cmd.
12. Binary outputs are copied through `DELAY (0,0)`, the fan speeds through `LIMIT (0,100)`.
13. Units: only `°C`, `%`, `Pa`, `s` get EBO unit codes; K, %/Pa, m3/s are written without a unit (io.json keeps
    the real unit).
14. Constant names chosen where the specification gives none: `Supply_ControlInt`; the coil controller dead zone 0.1 and Td 0
    are literal OpR values.

## 3. Interpretations

- Schedules and HN_* are BI blocks (unbound = 0). With nothing bound, FA01 / SB01 / SC3_Fault / P1_Fdb read 0, so
  Fire, Stop and (once P1 runs) P1 latches trip: bind or simulate them before judging anything else.
- `Reset_Cmd` = writable public DELB fed with OpB 0; `Reset_Pulse` = TRIG(1) of `Reset_Cmd OR Reset_DI`.
- `Supply_Temp_Alm` compares TE2 with `ST\Active_SP`. HeatR alarm runs in both seasons, CoolR only with
  Season_Mode = 1 (as written).
- Coil enable: HYST(Activate = Coil_Heat_OFF_SP 12, Deactivate = Coil_Heat_ON_SP 10) on `TE1 - Coil_Heat_ST`
  gives "above", `ST\Coil_En` = NOT that.
- Each stage controller's TSg is its own stage output block (`ST\SC3_Seq`, `TV2_Heat_Seq`, `TV1_Seq`, `TV2_Cool_Seq`).
- The four stage latches (`Stage_CCH`, `Stage_HC`, `Cool_Side`, `Stage_Cool`) are SR blocks whose set and reset
  expressions read the latches and the stage outputs back (loops through XPB, DELAY, SR).
- Season_Mode is binary (1 = cooling). Run_Mode is an XPI.
- In io.json, AOM, Season_Sel, Heating_Mode are listed under both `inputs` (soft) and `setpoints`; `constants` is an
  extra section (program properties, bindable as `AHU01/<name>`).

## 4. Most likely to fail compilation

1. Constant names as parameters of PIDA / PIDP / PRCNT / HYST (proven only for DELAY, FILT, LIMIT, CURVE).
   Bisect: `--only CoilProtect` (HYST, PIDA), `--only Fan` (PIDP), `--only TempSeq` (PIDA).
2. Feedback loops through more than one block (stage output -> PIDA TSg and stage latches; Run -> ... -> Critical_Alarm -> Run;
   SC3_Ctrl -> Eff_En; P1_Fault -> Freeze_Group -> P1). Each group alone has at most the PIDA loops.
3. ACCUM / SHR / DELI / MINUTE / HOUR / WDAY (`--only DayMean`, `--only PumpCtrl`).
4. Big HFBs (SensorCheck 16 outputs, FanCtrl 14 inputs) and pin names equal to inner block names (`OT` pin vs
   `Inputs\OT`).

## 5. Test plan (against the plant simulation)

Preconditions: FA01 = SB01 = SC3_Fault = 1, P1_Fdb follows P1_Cmd, TF01_Fdb / PF01_Fdb follow the fan commands,
all temperatures plausible, TE1 > 21 °C, AOM = 2, Time_Schedule = 1, Reset_Cmd pulsed once after binding.

| # | Function | Set | Expect |
|---|---|---|---|
| 1 | Sensor fault | TE3 = 150 (or -130) | `Inputs\bad_TE3` = 1 at once; `TE3_Alm` after 180 s; back in range: flag 0 |
| 2 | Outdoor fallback | TE00 = 150 | `OT` = 0, `OT_OK` = 0, night modes blocked, `TE00_Alm` after 180 s |
| 3 | Room mean | TE10_1/2/3 = 20/22/150 | `Room_Avg` = 21, `Room_N` = 2; all three bad: `Room_OK` = 0, `Room_Avg` = 0 |
| 4 | Daily mean | after a midnight | `OT_Day_Mean` = mean of the minute samples (`DM_Sum_Held / DM_Cnt_Held`); cold start: 5 |
| 5 | Season | Season_Sel 2 / 1 / 0 | `Season_Mode` 1 / 0 / `Auto_Season` (set at day mean >= 12, reset <= 10) |
| 6 | AOM | AOM 0 / 1 / 2 with Time_Schedule 0 | Operation 0 / 1 / 0; `Run_Mode` 0 / 1 / 0 |
| 7 | HS10 | AOM 2, schedule 0, HS10 pulse | `HS10_Ext`, `Operation` = 1 for 3600 s after HS10 drops |
| 8 | Start sequence | Run rises | FZ01/FZ02_Cmd at once; PF01_Cmd after 30 s; TF01_Cmd after 60 s; speeds 0 until released, then from 20 % |
| 9 | Pressure control | released, PE1 below SP | TF01_Ctrl rises (max 60 %); PE1 > SP: falls (min 20 %); same PE2 / PF01_Ctrl |
| 10 | Low speed | Low_Speed_Mode 1, TE00 = -12 | `Low_Speed_Cmd` = 1, `Supply_Pressure_SP` = 122 Pa (curve at -12), `Exhaust_Pressure_SP` = 91; TE00 = -7: stays 600 s, then 140 / 105 |
| 11 | Air flow | Run, PDE10 = 100 | `Supply_Flow` = 3.48 m3/s; stopped: 0 |
| 12 | Supply setpoint | TE7 = 19 / 21.5 / 24 / 150 | `Temp_SP` 22.5 / 19.75 / 17 / 20 |
| 13 | Heating stages | Season 0, TE2 below SP | `HRU_Act`: SC3_Seq rises; 30 s at 100 %: `Stage_HC` 1, `HC_Act`, SC3_Seq held 100, TV1_Seq rises from 0; Heating_Mode 1: `Stage_CCH` first (TV2_Seq), then `Stage_HC`; TE2 above SP: the stage in control falls to 0, 30 s later it is handed back and the one before resumes from 100 |
| 14 | Pre-heat | Season 0, TE00 <= 10, start | `PreHeat_Pulse` ~1 s -> `Stage_HC` 1 (and `Stage_CCH` with Heating_Mode), SC3_Seq 100, TV1_Seq starts at 71 % (50 % with Heating_Mode); `HRU_Hold` 1200 s: SC3_Ctrl 100 |
| 15 | Cooling stages | Season 1, TE2 above SP + 0.5 with every heating output 0 for 30 s | `Cool_Side` 1, `Stage_Cool` 1 at once, `Cool_Act`: TV2_Seq rises; with TE7 <= OT - 2: `Cool_Recovery` 1, `Rotor_Cools`: SC3_Seq rises first (`HRU_Act`), 30 s at 100 %: `Stage_Cool`; TE2 below SP - 0.5 with every cooling output 0 for 30 s: `Cool_Side` 0 |
| 16 | Stop | Run falls | same cycle: dampers, fan commands, speeds, SC3_Ctrl, TV2_Ctrl to 0; TV1_Ctrl = Coil_Heat_Ctrl |
| 17 | Coil return water | stopped, TE1 = 15 | Coil_En 1, TV1_Ctrl opens until TE1 ~11; TE1 > 23: Coil_En 0, Coil_Heat_Ctrl 0 |
| 18 | Freeze | TE1 = 6 (or TE2 = 6 while running) | `Freeze_Latch`, `Critical_Alarm`, `Freeze_Alm`; unit stops, TV1_Ctrl 100, P1_Cmd 1, Run_Mode 4; reset while cold: stays; warm + reset: clears |
| 19 | Fire / stop / HN | FA01 = 0, SB01 = 0, HN_Pres_In = 1, HN_Temp_In = 1, TE2 >= 50, TE7 >= 50 (one at a time) | own latch + class A alarm, unit stops; reset after the cause clears |
| 20 | Pump | TE00 = 5 | P1_Cmd 1 (cold); TE00 = 13 and TV1 0: off after 300 s; P1_Fdb = 0 while commanded: `P1_Fault_Cond` after 30 s, `P1_Latch`, valve 100 %, pump stays on |
| 21 | Pump exercise | P1_Ex_Day = today's WDAY, hour 10 | P1_Ex 60 s at 10:00, P1_Cmd for 60 + 300 s |
| 22 | Night cooling | AOM 2, schedule 0, Night_Schedule 1, Season 1, Room_Avg 24, TE00 15 | after 60 s `Night_Cooling` 1, Run_Mode 2, Active_SP 18; Room_Avg 20: stops after 60 s |
| 23 | Night heating | Season 0, day mean -5, Room_Avg 18, Night_Schedule 1 | `Night_Heating` after 60 s, Run_Mode 3, Active_SP 28; Room_Avg 21: stops |
| 24 | Rotor frost | Run, TE6 = -5, PDE4 above CURVE(PF01_Ctrl; 0,100; 100,300) | `Frost_Cond`, `Frost_Active`, SC3_Ctrl <= 50 %; `HRU_Frost_Alm` after 180 s; holds 300 s after it clears |
| 25 | Efficiency | Run, SC3_Ctrl >= 50, TE6 0, TE7 20, TE3 12 | `Eff_Calc` 1, `HRU_Efficiency` 60 %; TE3 = 6 (30 %) with SC3 >= 90, TE6 <= 5: `HRU_Efficiency_Alm` after 300 s |
| 26 | Deviation alarms | TE2 off Active_SP by > 5 K; PE1 off by > 25 % | `Supply_Temp_Alm` after 300 s; `Supply_Pres_Alm` after 900 s (same for PE2) |
| 27 | Fan feedback | TF01_Fdb = 0 while TF01_Cmd | `TF01_Alm` after 900 s (PF01 likewise) |
| 28 | Coil function | Run, TV1_Ctrl >= 30, TE4 - TE3 < 1 | `HeatR_Alm` after 300 s; Season 1, TV2_Ctrl >= 30, TE4 - TE5 < 1: `CoolR_Alm` |
| 29 | Filters | released, PDE3 > 10 + 1.4 x TF01_Ctrl | `PDE3_Alm` after 300 s; PDE3_Filter 0 blocks it (PDE1, PDE2 likewise) |
| 30 | HRU drive | SC3_Fault = 0 | `HRU_Alm` after 180 s (not critical) |
