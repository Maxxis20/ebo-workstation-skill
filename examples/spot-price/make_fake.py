#!/usr/bin/env python3
"""make_fake.py - fake/<name>.json: price files for the bridge's fake source (tools/spotprice/spotd.py), one per
test step. Each file sets the bridge's clock, so a test moves time by writing the next file. c/kWh without VAT.
"""
import json, os
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "fake")
DAY = "2026-01-15"

# a winter weekday: cheap night, morning and evening peaks above the 20 c/kWh block limit
NORMAL = [3.1, 2.6, 2.2, 2.0, 2.4, 4.8, 9.5, 21.0, 26.5, 22.0, 14.0, 12.5,
          12.0, 11.5, 11.0, 12.8, 16.0, 23.5, 27.0, 21.5, 15.0, 10.5, 7.0, 4.5]
# windy and sunny: negative around noon
NEGATIVE = [4.0, 3.5, 3.2, 3.0, 3.1, 4.0, 6.5, 9.0, 7.5, 4.0, 1.2, -0.4,
            -1.5, -2.1, -0.8, 0.6, 3.5, 8.0, 11.0, 9.5, 7.0, 5.5, 4.8, 4.2]
# the rest of today has its cheapest three hours at 15-17; tomorrow's night is cheaper still
TODAY_B = [8.0] * 12 + [10.0, 11.0, 9.0, 3.0, 3.2, 3.1, 12.0, 14.0, 13.0, 11.0, 9.0, 8.5]
TOMORROW_B = [6.0, 4.0, 1.0, 0.9, 1.1, 5.0, 9.0, 13.0, 15.0, 12.0, 10.0, 9.5,
              9.0, 8.8, 8.6, 9.2, 11.0, 15.0, 17.0, 14.0, 11.0, 9.0, 8.0, 7.0]
# hold: the cheapest three hours from 15 on today; tomorrow first dear, then (a later file) cheap at night
TODAY_F = [9.0] * 12 + [10.0, 11.0, 10.5, 2.0, 2.1, 2.2, 12.0, 14.0, 13.0, 11.0, 9.0, 8.5]
TOMORROW_F_DEAR = [9.0] * 24
TOMORROW_F_CHEAP = [5.0, 3.0, 0.5, 0.4, 0.6, 4.0] + [9.0] * 18

# 15 minute prices: the normal day with a pattern inside each hour; at 12:15 one quarter above the block limit
# although the hour as a whole (13.75) is not
QUARTERS = [round(h + d, 2) for h in NORMAL for d in (-1.0, 0.5, 1.0, -0.5)]
QUARTERS[48:52] = [9.0, 25.0, 11.0, 10.0]

FILES = {
    "n_0330": (NORMAL, None, "03:30"), "n_0830": (NORMAL, None, "08:30"), "n_1230": (NORMAL, None, "12:30"),
    "n_1230_dead": (NORMAL, None, "12:30", True),
    "neg_1330": (NEGATIVE, None, "13:30"),
    "tm_1230": (TODAY_B, None, "12:30"), "tm_1330": (TODAY_B, None, "13:30"), "tm_1405": (TODAY_B, TOMORROW_B, "14:05"),
    "fr_1430": (TODAY_F, TOMORROW_F_DEAR, "14:30"), "fr_1530": (TODAY_F, TOMORROW_F_DEAR, "15:30"),
    "fr_1630": (TODAY_F, TOMORROW_F_CHEAP, "16:30"), "fr_1730": (TODAY_F, TOMORROW_F_CHEAP, "17:30"),
    "fr_1830": (TODAY_F, TOMORROW_F_CHEAP, "18:30"),
    "q_1220": (QUARTERS, None, "12:20"),
}
os.makedirs(OUT, exist_ok=True)
for name, (today, tomorrow, clock, *dead) in FILES.items():
    d = {"clock": f"{DAY}T{clock}:00", "today": today, "tomorrow": tomorrow, "dead": bool(dead and dead[0]),
         "max_age_s": 20 if dead else 21600}
    json.dump(d, open(os.path.join(OUT, name + ".json"), "w"))
print(f"fake/: {len(FILES)} files")
