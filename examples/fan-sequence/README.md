# Fan start / stop sequence (step chain) for EBO

A small, self-contained example of the step chain pattern: one fan with a shut-off damper, five steps, simulated
feedbacks so it runs without I/O, fault injection, and a graphic that lists every step with its live status.
Everything is generated from Python and loaded into EcoStruxure Building Operation 7.1 by script (skill
`ebo-workstation`).

| Step | Name | Does | Requirements (in order) | Settle | Supervision |
|---|---|---|---|---|---|
| 0 | Idle | - | - | - | - |
| 1 | Damper open | opens the shut-off damper | damper open end switch | 2 s | 20 s |
| 2 | Fan start | starts the fan | fan running feedback; duct pressure 50 Pa or more | 3 s | 20 s |
| 3 | Run | fan runs | fan running feedback; damper open (watched all the time) | - | 5 s |
| 4 | Fan stop | stops the fan | fan feedback off; duct pressure below 20 Pa | 2 s | 30 s |
| 5 | Run-on, damper close | waits 10 s, then closes the damper | run-on time passed; damper closed end switch | 1 s | 40 s |

The table lives in `steps.py`; program, graphic and tests read it from there.

## What it ran on

An EcoStruxure Building Operation 7.1.1.132 **Enterprise Server only**, with WorkStation on the same Windows
machine: no automation server, no field controller, no I/O. The program runs on the Enterprise Server, and the
field is simulated inside the program (module `Sim`: damper stroke as a ramp, fan feedback as a delay, duct
pressure as a ramp). On a controller the `Sim` module goes and the inputs are bound to real points instead; that
was not tried here. The broker for the test harness (Mosquitto) runs on the same machine.

## How it behaves

- **Start**: mode On, or Auto with Auto demand. Step 1 begins. Requirements are checked in order; `RQ_AT` says
  which one is being checked now (one step forward per cycle while met, back at once to the first one not met).
  When every requirement has held for the settle time, the next step begins.
- **Supervision**: a requirement not met within the step's supervision time gives the **sequence alarm** (class B):
  the step and the requirement are kept (`AL_Step`, `AL_Req`), the alarm object of that step and requirement trips
  (`Alarms/Seq_S<k>_R<j>`, its text names both), a start or run step jumps to the first stop step, and the stop
  steps run in order. A new start needs Reset.
- **Run step**: its requirements are watched all the time; a lost one starts the supervision time (5 s).
- **Demand off**: from any start step or the run step, jump to step 4 (ordered stop).
- **Trip** (class A, emergency stop): step 0 at once; the commands drop in the same cycle (interlock in the
  command expressions, not through the chain); held until Reset with the emergency stop released.
- **Step durations** `D1` ... `D5` are stored when a step is left and cleared at a new start; the graphic shows them
  as "done in 6.0 s".

## Why a Function Block program

A step chain reads more naturally as text, and EBO has Script programs. But the Function Block route is the one
the skill can load, compile, check and bind by script today (`.aut` from `aut.py`, `Fb-Load`, `ebox.py bind`); a
Script program round trip is still open. In Function Block form the chain is a set of expressions closed through
one-cycle delays (`DELI` / `DELR` / `DELB`): every cycle computes the new step, timers and check pointer from the
values of the cycle before. 112 blocks, cycle 500 ms.

## Files

| File | What |
|---|---|
| `steps.py` | the step table |
| `make_program.py` -> `FanSeq.aut`, `io.json` | the program: modules Inputs, Seq, Req, Outputs, Sim, Hmi, Alarms |
| `make_hmi.py` -> `FanSeq.tgml`, `hmi_binds.json` | the graphic: header (unit state, step, time, mode, Reset, emergency stop), plant, test switches, steps list |
| `make_objects.py` -> `FanSeq-cmd.xml`, `FanSeq-iot.xml`, `binds.json` | command values (folder Cmd), MQTT client (commands in, trace out), every binding |
| `deploy.sh` | all of it onto a server, bound: about 7 minutes |
| `run_tests.sh`, `seqtest.ps1`, `analyze.py` | the four test scenarios: commands by MQTT, trace by MQTT, screenshots, timeline |
| `test-out/` | timelines, screenshots of the graphic and of the alarm list from the last run (results: `TESTS.md`) |

## On a server

`./deploy.sh` (default `/Server 1`, folder `FanSeq`; the IoT Interface is `FanSeq_IoT`, broker on the same
machine). Open `FanSeq/Graphic`, mode On; the alarms in `FanSeq/AlarmList` (an Alarm View). Tests: `./run_tests.sh [out dir] [t1 t2 t3 t4]`.
