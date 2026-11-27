"""steps.py - the step table of the fan start / stop sequence: one source for the program, the graphic and the tests.

Step 0 is idle. Each step: number, name, what it does, its requirements (checked in order), settle time (all
requirements must hold that long before the next step), supervision time (a requirement not met that long gives the
sequence alarm). Step 3 is the run step: no settle, its requirements are watched all the time and a lost one is
supervised by its supervision time. Steps 4 and 5 are the stop steps.
"""
RUN_STEP = 3
FIRST_STOP = 4
RUNON_S = 10           # run-on time of step 5, s

STEPS = [
    (1, "DAMPER OPEN", "Opens the shut-off damper",
     ["Damper open end switch"], 2.0, 20.0),
    (2, "FAN START", "Starts the fan",
     ["Fan running feedback", "Duct pressure 50 Pa or more"], 3.0, 20.0),
    (3, "RUN", "Fan runs; requirements watched",
     ["Fan running feedback", "Damper open end switch"], 0.0, 5.0),
    (4, "FAN STOP", "Stops the fan",
     ["Fan running feedback off", "Duct pressure below 20 Pa"], 2.0, 30.0),
    (5, "RUN-ON, DAMPER CLOSE", f"Waits {RUNON_S} s, then closes the damper",
     [f"Run-on time {RUNON_S} s passed", "Damper closed end switch"], 1.0, 40.0),
]
N_REQ = max(len(s[3]) for s in STEPS)
