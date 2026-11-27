# Test results (2026-11-27, EBO 7.1.1.132 Enterprise Server only, on a Windows machine)

What it ran on: one Enterprise Server with WorkStation and the MQTT broker on the same Windows machine; no
automation server, no field controller, field simulated in the program (README, "What it ran on").

Commands go in through the MQTT client's subscription (`fanseq/cmd`), the program's signals come out through its
data groups; `analyze.py` turns the trace into a timeline (`test-out/<test>-timeline.txt`). Trace times are whole
seconds (mosquitto_sub on Windows has no sub-second time format), so an event can show up to 1 s before the action
that caused it. The step durations are the program's own (`D1` ... `D5`, cycle 500 ms).

Screenshots: `test-out/<test>-<n>-<what>.png`, cropped to the graphic; `test-out/<test>-al<n>-<what>.png`, the alarm
list (an Alarm View object `FanSeq/AlarmList`, quick filter `FanSeq`). Opening the alarm list takes 20 to 35 s and the
actions after it wait, so in t2 to t4 the later times are later than planned in `run_tests.sh`. Each test starts
with Off, faults off, emergency stop released and one Reset; until the new start the durations of the run before
still show (cleared at the start).

## t1 normal start and stop - pass

Mode On at 5 s: step 1 at 4.8 (trace second), step 2 at 10.8, step 3 (Run) at 17.8. Mode Off at 30.0: step 4 at
29.8, step 5 at 37.8, idle at 52.8. Fan command off one cycle after step 4, damper command off when the 10 s run-on
was over (48.8).

| Step | Duration | Made of |
|---|---|---|
| 1 Damper open | 6.0 s | damper stroke about 4 s, settle 2 s |
| 2 Fan start | 7.0 s | feedback after 2 s, pressure to 50 Pa about 1.3 s, settle 3 s |
| 3 Run | 12.0 s | until demand off |
| 4 Fan stop | 8.0 s | feedback off after 2 s, pressure below 20 Pa about 3.3 s, settle 2 s |
| 5 Run-on, damper close | 15.0 s | run-on 10 s, damper stroke 4 s, settle 1 s |

Screenshots t1-1 (step 1 checking), t1-2 (step 2: damper done in 6.0 s, fan feedback CHECKING, pressure next),
t1-3 (Run, all OK), t1-4, t1-5 (stop steps), t1-6 (idle, all durations shown).

## t2 requirement not met in time, ordered stop, Reset - pass

Damper fault on at 5, Mode On at 6: step 1 at 6.4 waits on "damper open end switch". At 26.4 (20 s supervision):
sequence alarm, AL_Step 1, AL_Req 1, step 4; step 5 at 30.4; idle at 42.4 with the alarm held, Mode still On, no
restart. Fault off and Reset at 51.7: alarm cleared and step 1 in the same trace second, Run at 64.4 (D1 6.0 s,
D2 7.0 s).

- t2-2: header SEQUENCE ALARM, amber B lamp lit, step 1 row red "ALARM 20.0 s" with the requirement NOT MET, step 4
  active.
- t2-3: held at idle, alarm and B lamp still on, stop steps done in 4.0 s and 12.0 s.
- t2-al1-active: alarm list, `Seq_S1_R1` active (priority 2), text "Sequence alarm: step 1 DAMPER OPEN, requirement
  1 (Damper open end switch) not met in 20 s".
- t2-al2-reset: taken right after the Reset: `Seq_S1_R1` returned to normal.
- t2-4, t2-5: running again.

## t3 run-step requirement lost - pass

Run at 17.6. Fan feedback fault at 26.0 (feedback 0 at 25.6 in the trace): supervision of the run step, 5 s; at
29.6: sequence alarm AL_Step 3, AL_Req 1, step 4, fan command off one cycle later; step 5 at 33.6, idle at 48.6.
Fault off, Mode Off and Reset at 71.0: alarm cleared at 70.6 (trace second).

- t3-3: header SEQUENCE ALARM, B lamp lit, step 3 row red with "Fan running feedback NOT MET", "Damper open end
  switch OK", step 4 active with both OK.
- t3-al1-active: `Seq_S3_R1` active, text "Sequence alarm: step 3 RUN, requirement 1 (Fan running feedback) not met
  in 5 s".
- t3-al2-reset: after the Reset, `Seq_S3_R1` returned to normal.

## t4 trip in Run - pass

Run at 17.7. Emergency stop at 26.0: in the same trace second step 0, trip 1, damper command 0, fan command 0 (the
commands drop in the cycle of the trip, through the interlock in the command expressions); fan feedback 0 two
seconds later. Emergency stop released and Reset at 54.6: trip 0 and step 1 at once (Mode still On), Run at 67.7.

- t4-2, t4-3: header TRIP, step 0 Idle, damper 0 %, fan stopped, red A lamp lit.
- t4-al1-active: `Trip_Alarm` active, priority 1, text "Emergency stop: fan sequence tripped, fan and damper stopped
  at once".
- t4-al2-reset: after release and Reset, `Trip_Alarm` returned to normal.
- t4-4: running again.

## Alarm objects

Checked in the alarm list in t2, t3 and t4: each test's alarm object goes active with a text that names the step
and the requirement (or the trip), and returns to normal after Reset. Not done: acknowledging them; the "Count"
column also counts the earlier runs on the same server.

The first run of these tests showed the sequence alarms with an empty text: the requirement was in single quotes in
the text, and the .aut string is in single quotes too. The requirement is now in brackets, and `aut.py` refuses a
single quote in an alarm text.

## Seen on the way

- The graphic updates about 1 s behind the program.
- Header alarm lamps: the blinking `alarm_lamp` never showed lit in a screenshot (the capture lands in the hidden
  half of the blink); plain lamps (red trip, amber sequence alarm) are used.
- WorkStation logs off after 5 idle minutes and a new log-on closes the graphic: `run_tests.sh` logs on and opens
  the graphic right before each test.
