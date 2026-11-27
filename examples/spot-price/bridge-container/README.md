# The spot price bridge as a container beside an EBO server container

`compose.yaml` runs two containers on the host network, next to an EBO Enterprise or Edge Server container that
also uses the host network:

- `mosquitto`: the broker, listening on 127.0.0.1:1883 only (nothing exposed to the LAN);
- `spotd`: the bridge (`spotd.py`, Python 3.12 with `tzdata`), live source, publishing `spot/<AREA>/...`.

```bash
cp <path of spotd.py> .                        # the bridge itself (not part of this skill)
cp config.example.json config.json              # areas, time zone; "mqtt" host 127.0.0.1
docker compose up -d --build
docker exec <mosquitto container> mosquitto_sub -h 127.0.0.1 -t 'spot/FI/now' -C 1
```

The EBO server's MQTT client `Prices` then points at 127.0.0.1 (`make_objects.py --broker 127.0.0.1`). Only the
bridge needs the internet (outbound HTTPS to the price source, one request an hour per area, every 10 minutes in
the afternoon until tomorrow's prices are out). On an Edge Server with a second network on the field side, the
prices reach the field (BACnet, Modbus, own I/O) without the field network ever seeing the internet.

Seen working 2026-11-27: 96 quarters for FI fetched, `spot/FI/now` with valid 1 on the local broker.
