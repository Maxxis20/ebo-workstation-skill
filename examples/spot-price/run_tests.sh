#!/usr/bin/env bash
# run_tests.sh [out dir] [test ...] - play the spot price test scenarios on the server (after deploy.sh): a bridge
# with the fake source on the EBO machine, settings by MQTT, screenshots, timelines.
#   t1 normal day (N cheapest hours): chosen hour, above the block limit, not chosen, price control off
#   t2 negative prices: forced on
#   t3 cheapest 3 h in a row: planned, counts down, planned again when tomorrow's prices arrive while waiting
#   t4 held block: runs to its end although cheaper hours appear, then planned again
#   t5 source dead: valid 0 -> normal operation and alarm, back
#   t6 bridge stopped: beat still -> normal operation and alarm after 60 s, back
#   t7 15 minute prices: a quarter above the block limit inside an hour that is not; prices shown in EUR/MWh
# Needs: the spot price bridge (SPOTD=<path of spotd.py>), a Python 3.9+ with tzdata on the EBO machine (PY below), the broker there.
set -euo pipefail
H=$(cd "$(dirname "$0")" && pwd); S=$H/../../scripts; E=$S/ebo.sh
BRIDGE=${SPOTD:?set SPOTD to the path of the spot price bridge spotd.py}
OUT=${1:-$H/test-out}; shift || true; TESTS=${*:-t1 t2 t3 t4 t5 t6 t7}; W='C:\agentwork\ebo'; SD='C:\agentwork\spot'
mkdir -p "$OUT"; cd "$H"
python3 make_fake.py >/dev/null
"$E" put spottest.ps1 "$W\\spottest.ps1" >/dev/null
"$E" put "$BRIDGE" "$SD\\spotd.py" >/dev/null
printf '{"tz": "Europe/Helsinki", "source": "fake", "fake": "fake.json", "areas": [{"area": "FI"}],\n "mqtt": {"host": "127.0.0.1", "prefix": "spot"}}\n' > "$OUT/.config.json"
"$E" put "$OUT/.config.json" "$SD\\config.json" >/dev/null; rm "$OUT/.config.json"
for f in fake/*.json; do "$E" put "$f" "$SD\\fake\\$(basename "$f")" >/dev/null; done
"$E" run ". $W\\spottest.ps1; Spot-Fake 'n_1230'; Spot-Start; Start-Sleep 12; Log ('bridge: ' + ((Get-Content $SD\\spotd.log -ea 0) -join ' | '))" 60 | tail -1

# every test: price control on, N cheapest hours mode, defaults, plan cleared (mode 0 drops it)
PRE="@(0,'set','Ctl_On',1),@(0,'set','Mode',0),@(0,'set','N_Cheap',6),@(0,'set','N_Block',3),@(0,'set','Block_Above',20),@(0,'set','Force_Below',0),@(0,'set','Normal_Demand',1),@(0,'set','Res',0),@(0,'set','Unit_MWh',0)"
scn(){ case $1 in
 t1) echo "@(1,'fake','n_0330'),@(25,'shot','1-chosen'),@(27,'fake','n_0830'),@(50,'shot','2-blocked'),@(52,'fake','n_1230'),@(75,'shot','3-not-chosen'),@(77,'set','Ctl_On',0),@(85,'shot','4-ctl-off'),@(87,'set','Ctl_On',1),@(90,'end')";;
 t2) echo "@(1,'fake','neg_1330'),@(25,'shot','1-forced'),@(27,'end')";;
 t3) echo "@(1,'fake','tm_1230'),@(15,'set','Mode',1),@(30,'shot','1-planned'),@(32,'fake','tm_1330'),@(52,'shot','2-counting'),@(54,'fake','tm_1405'),@(75,'shot','3-replanned'),@(77,'end')";;
 t4) echo "@(1,'fake','fr_1430'),@(15,'set','Mode',1),@(30,'shot','1-planned'),@(32,'fake','fr_1530'),@(52,'shot','2-running'),@(54,'fake','fr_1630'),@(74,'shot','3-still-held'),@(76,'fake','fr_1730'),@(96,'fake','fr_1830'),@(118,'shot','4-replanned'),@(120,'end')";;
 t5) echo "@(1,'fake','n_1230'),@(20,'shot','1-ok'),@(22,'fake','n_1230_dead'),@(60,'shot','2-invalid'),@(62,'alarms','al1-active'),@(88,'fake','n_1230'),@(112,'shot','3-back'),@(114,'alarms','al2-reset'),@(116,'end')";;
 t7) echo "@(1,'fake','q_1220'),@(25,'shot','1-hourly'),@(27,'set','Res',1),@(45,'shot','2-quarters'),@(47,'set','Unit_MWh',1),@(55,'shot','3-eur-mwh'),@(57,'set','Unit_MWh',0),@(58,'set','Res',0),@(60,'end')";;
 t6) echo "@(1,'fake','n_1230'),@(20,'shot','1-ok'),@(22,'stop'),@(95,'shot','2-stopped'),@(97,'alarms','al1-active'),@(122,'start'),@(146,'shot','3-back'),@(148,'alarms','al2-reset'),@(150,'end')";;
 esac; }
for t in $TESTS; do
  # WorkStation logs off after 5 idle minutes and a new log-on closes the graphic: log on and open it right here
  "$E" logon | tail -1
  "$E" run "Ws-Open '/Server 1/SpotPrice/Graphic'; Ws-Front; Log 'graphic open'" 120 | tail -1
  "$E" run ". $W\\spottest.ps1; Log (Scn '$t' @($PRE,$(scn $t)))" 400 | tail -4
  for f in $("$E" sys "Get-ChildItem $W\\spot\\$t.txt,$W\\spot\\$t.act,$W\\spot\\$t-*.png | % Name" | tr -d '\r'); do
    "$E" get "$W\\spot\\$f" "$OUT/$f" >/dev/null
  done
  echo "== $t"; python3 analyze.py "$OUT/$t.txt" "$OUT/$t.act" | tee "$OUT/$t-timeline.txt"
done
