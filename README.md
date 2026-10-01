# Centrometal WiFi-Box — local Home Assistant integration

Home Assistant integration that acts as a **local MQTT server** for a Centrometal
boiler fitted with a **CM WiFi-Box**, so the boiler keeps reporting to Home Assistant
**even if the Centrometal cloud (`portal.centrometal.hr`) is unreachable**.

Instead of talking to the cloud over the web API, this integration makes the WiFi-Box
connect to a tiny MQTT broker embedded in Home Assistant, answers its sync handshake,
and periodically pulls all boiler values. It is part of the same ecosystem as
[`hass-centrometal-boiler`](https://github.com/AndroFlo/hass-centrometal-boiler) (the
cloud integration) and reuses the same raw codes, so the same boiler reads the same way.

> **Status: read-only (phase 1).** The integration only *reads* values — it never sends
> a control command (turn on/off, setpoints). Target boiler: **BioTec Plus** (`biopl`).

## How it works

The CM WiFi-Box (an ESP module) connects in clear MQTT 3.1.1 to `portal.centrometal.hr`
on **TCP 1883**, subscribes to `cm.srv.biopl.<serial>` and publishes to
`cm.inst.biopl.<serial>`. It only dumps its `B_*` / `C1B_*` values in reply to a server
`{"REFRESH":0}`; otherwise it just sends a `{"wf_req":"?"}` heartbeat every ~30 s.

This integration:

1. Listens on port **1883** and accepts the box's MQTT connection.
2. Answers the box's `_sync` handshake.
3. Periodically sends `{"REFRESH":0}` to pull every value.
4. Exposes each raw code as a Home Assistant sensor (push, `local_push`).

Inbound messages carry a 40-hex `_sign` whose algorithm is unknown. Because a REFRESH is
a harmless read, the broker probes three REFRESH variants (captured replay, zero `_sign`,
no `_sign`) until one triggers a value dump, then keeps it. The HA log says which worked —
that also answers whether the box verifies inbound signatures.

## Requirements

Because the WiFi-Box always connects to `portal.centrometal.hr:1883`, you must:

1. **Redirect DNS** for `portal.centrometal.hr` to the Home Assistant host, on the network
   the box uses (e.g. a `dnsmasq`/AdGuard/Pi-hole entry, or your router's local DNS).
2. Keep the integration's listen port at **1883** on that host (the default), unless you
   set up port forwarding/NAT.

> ⚠️ If you already run the Mosquitto add-on, it also uses port 1883. Either point the box
> to a different host, run this broker on another host, or free port 1883 for it.

## Installation

### HACS (custom repository)

1. HACS → ⋮ → *Custom repositories*.
2. Add `https://github.com/AndroFlo/hass-centrometal-wifibox`, category **Integration**.
3. Install *Centrometal WiFi-Box (local)* and restart Home Assistant.

### Manual

Copy `custom_components/centrometal_wifibox` into your HA `config/custom_components/`
folder and restart.

## Configuration

Settings → Devices & Services → **Add Integration** → *Centrometal WiFi-Box (local)*.
Set a name and the listen port (default 1883). Then redirect DNS as above and power-cycle
the box; sensors appear after the first value dump.

Unmapped raw codes show up as disabled `{?} <code>` sensors — enable them to discover new
values, and they can then be added to `codes.py`.

## Debugging

```yaml
logger:
  logs:
    custom_components.centrometal_wifibox: debug
```

## Roadmap

- Phase 1 (this release): read-only local server.
- Phase 2: control commands (turn on/off, pellet mode, circuits) — only once it is
  confirmed how the box handles the `_sign` of inbound messages.

## License

MIT — see [LICENSE](LICENSE).
