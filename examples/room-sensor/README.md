# Room sensor faceplate: a page of its own and a click-open box

One drawing (`roomface.py`) used twice:

- `make_hmi.py` writes `RoomSensor.tgml`, a page for one sensor: temperature with a thermometer whose colour runs
  from blue (20 °C and below) through green to red (25 °C and above), humidity with a bar, battery voltage with
  a low lamp, and "Last new value: n min ago" with a lamp that turns red when the value is old.
- `ahu01/make_hmi.py` opens the same drawing as a box at each room sensor of the air handling unit (green "T"
  mark): live temperature, room mean, sensor fault, alarm lamp. `Graphic.popup()` in `tgml.py` does that.
- `make_age.py` writes `SensorAge.aut`, the small program behind "Last new value": seconds since any of three
  watched values changed. For devices that are polled and carry no time stamp. It is the last change, not the
  last report: a reading that repeats all three numbers does not reset it. For a sensor that reports a counter
  (the LoRaWAN uplink counter over MQTT), bind V1 to the counter and the age becomes "since the last report":
  see `../lora-mqtt` (Staleness).

```bash
python3 make_age.py
python3 make_hmi.py "Room 101" "/Server 1/BACnet/IP Network/Sensor/Application" Temp Humidity Vdd "/Server 1/Room101_Age"
E=<skill>/scripts/ebo.sh
$E put SensorAge.aut 'C:\agentwork\ebo\SensorAge.aut'; $E put RoomSensor.tgml 'C:\agentwork\ebo\RoomSensor.tgml'
$E run "Fb-Load '/Server 1' 'Room101_Age' 'C:\agentwork\ebo\SensorAge.aut'" 200
$E run "Log (Ws-Bind '/Server 1/Room101_Age' @(@('V1','<target>'),@('V2','<target>'),@('V3','<target>')))" 200   # binds.json: age_program
$E run "Gfx-Load '/Server 1' 'Room101' 'C:\\agentwork\\ebo\\RoomSensor.tgml'" 200
$E run "Log (Ws-Bind '/Server 1/Room101' @(@('T','<target>'), ...))" 200                                         # binds.json: graphic
```
