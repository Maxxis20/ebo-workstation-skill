# lora-mqtt: LoRaWAN sensor values from an MQTT broker into EBO

Import files that make EBO 7.1 subscribe to a broker fed by a LoRaWAN network server in ChirpStack (v4) format and
write the sensor's values into server values with units, plus an alarm for "the sensor stopped reporting". Proven
2026-11-23/24 on an Enterprise Server (skill findings, section "MQTT subscription: values from a broker into EBO").

**Proven** against a real LoRaWAN network server with a ChirpStack-format broker (anonymous, TCP 1883, nothing
retained, one uplink per 10 minutes): the next uplink after the import arrived in the values, and they equalled
the BACnet/IP reading of the same sensor from the same network server at that moment (2026-11-23). On 2026-11-24
all five default signals arrived from one uplink: 22,3 °C, 26 % Rh, 3 678 mV, rssi -87, counter 7163. Nothing is
retained, so the values stay 0 after an import or server restart until the next uplink. The EBO machine needs
outbound TCP 1883 to the broker only. Do not test by publishing on a real network server's uplink topic (it may
refuse, and may feed its own Modbus/BACnet side from it): rehearse on a broker of your own, as under Verify.

## Mapping

The network server publishes one JSON message per uplink on `application/<app>/device/<devEui>/event/up`, decoded
values under `/object/<key>`, device under `/deviceInfo/devEui`, no point id per value. An EBO MQTT client has one
point id pointer and one value pointer for all its messages, so:

- point id pointer `/deviceInfo/devEui`; each target value carries the devEui as its Foreign address;
- one MQTT client per signal, all on the same topic, each with its own value pointer. Pointers outside `object`
  work too: `/rxInfo/0/rssi` (radio level at the first gateway, array index in the pointer), `/fCnt` (uplink
  counter);
- each client has one Data Group, Allow subscription Yes, interval and event publishing off (it sends nothing),
  holding its one target. Each client writes only its own group's point;
- at most 4 clients per IoT Interface: the fifth signal goes on a second interface `<iot>_2`, the ninth on
  `<iot>_3`.

## Run and import

```bash
python3 make.py --deveui <devEui> [--host 127.0.0.1] [--name Sensor01] [--iot LoRa] [--topic T] \
                [--signals name=/json/pointer[@unit],...] [--server '/Server 1']
python3 make_alarm.py [--name Sensor01] [--program '/Server 1/Sensor01_Age'] [--server '/Server 1'] [--minutes 30]
```

- `lora_values.xml`: folder `<name>` with one `server.point.AV` per signal (foreign address = devEui, unit if
  given). Import first, below `/Server 1`.
- `lora_iot.xml`: IoT Interface `<iot>` (and `<iot>_2` ... after every four signals) with one MQTT client per
  signal. Import second, below `/Server 1`.
- `lora_alarm.xml`: alarm `Stale_Alarm` on `<program>/Stale` (see Staleness). Import below `/Server 1/<name>`, after
  the age program is loaded.

Import with `Ws-Import`. `--name` and `--iot` must differ: an interface and a folder of the same name make the
second import `<name>_2`, its references then point at the clients themselves and nothing subscribes. Deleting and
importing clients and values again is harmless: the values come back with the next uplink.

`--signals` default: `temperature=/object/temperature@°C, humidity=/object/humidity@%RH, vdd=/object/vdd@mV,
rssi=/rxInfo/0/rssi, fcnt=/fCnt`. Change the `object` keys to the ones your decoder writes. The unit is a key of
`UNIT` in `objects.py` (`°C`, `%`, `%RH`, `ppm`, `Pa`, `s`, `V`, `mV`) or an EBO unit code such as `0x280001`; it
goes into the file as `<PI Name="Value" Unit="..."/>`. There is no dBm unit, so rssi and fcnt have none.

**Units with a prefix**: by default an MQTT client takes a subscribed number as the base SI unit, so 3678 written
to a mV value showed 3 678 000 mV. The clients are made with `ScaleToBaseSIUnit` = 0, which keeps the number as
sent (3660 arrived as 3 660 mV). °C and % Rh were the same either way.

## Verify

- Broker log: one SUBSCRIBE per client a few seconds after the import.
- Without waiting for the sensor: put an uplink JSON in a file and send it on the EBO machine,
  `mosquitto_pub.exe -h 127.0.0.1 -t application/default/device/<devEui>/event/up -f up.json` (the broker named by
  `--host`).
- Read the values by script: `Ws-Export '/Server 1/<name>' file 'Special'`, then fetch the file with `ebo.sh get`.
  The export holds each value's live `Value` and `Unit` at that moment (about 20 s per read; no Foreign address).
- WorkStation: folder `<name>`, right-click the list's column header > `Add/Remove columns` > `Value`. The column
  is gone after the next log-on unless the layout is saved.

## Staleness

The uplink counter `fcnt` changes with every uplink, also when no reading does, so it tells whether the sensor is
still reporting. Use the age program of the room-sensor example (`../room-sensor/make_age.py` -> `SensorAge.aut`,
outputs `Age_Min` and `Stale` after 30 min) with V1 on the counter:

```bash
E=<skill>/scripts/ebo.sh
(cd ../room-sensor && python3 make_age.py); $E put ../room-sensor/SensorAge.aut 'C:\agentwork\ebo\SensorAge.aut'
$E run "Fb-Load '/Server 1' 'Sensor01_Age' 'C:\agentwork\ebo\SensorAge.aut'" 200
$E run "Log (Ws-Bind '/Server 1/Sensor01_Age' @(@('V1','/Server 1/Sensor01/fcnt/Value'),@('V2','/Server 1/Sensor01/temperature/Value'),@('V3','/Server 1/Sensor01/humidity/Value')))" 200
```

Seen 2,4 minutes after an uplink: `Age_Min` 2,43, `Stale` False. With V1 on the counter the age is "since the last
report", not "since the last change". Then `make_alarm.py` and import `lora_alarm.xml` below `/Server 1/Sensor01`:
it trips and resets (tried with the limit at 1 minute: `Alarm` 80 s after the last uplink, `Reset` seconds after
the next one; column `Alarm state` in the folder's list view shows it). The program's live values: select it in
WorkStation, tab Variables, "+" of the first row.

## Limits

- Analog values only were tried. Response messages, the group's update-rate and min/max filters were not tried.
