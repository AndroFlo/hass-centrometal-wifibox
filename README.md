# Centrometal WiFi-Box — local Home Assistant integration

Home Assistant integration that reads a Centrometal boiler fitted with a **CM WiFi-Box**
**through your own MQTT broker** (e.g. the Mosquitto add-on), so the boiler keeps reporting
to Home Assistant **even if the Centrometal cloud (`portal.centrometal.hr`) is unreachable**.

The WiFi-Box already speaks MQTT — that is how it talks to the cloud — but in a proprietary
Centrometal dialect (topics `cm.inst/cm.srv`, a `_sync` handshake, a `REFRESH` trigger,
`B_*` payloads), not generic MQTT with Home Assistant discovery. This integration acts as a
**client of your MQTT broker**: it subscribes to the box's topic, answers its handshake,
periodically pulls all values, and turns each raw code into a Home Assistant sensor. It is
part of the same ecosystem as
[`hass-centrometal-boiler`](https://github.com/AndroFlo/hass-centrometal-boiler) (the cloud
integration) and reuses the same raw codes, so the same boiler reads the same way.

> **Status: read-only (phase 1).** The integration only *reads* values — it never sends a
> control command (turn on/off, setpoints). Target boiler: **BioTec Plus** (`biopl`).

## How it works

```
CM WiFi-Box ──MQTT──► your broker (Mosquitto) ◄──MQTT── this integration (HA)
                                                    subscribe cm.inst.<product>.<serial>
                                                    publish   cm.srv.<product>.<serial>
```

1. The box connects to your MQTT broker (see **Requirements**) and publishes to
   `cm.inst.<product>.<serial>`; it subscribes to `cm.srv.<product>.<serial>`.
2. This integration (an MQTT client, `dependencies: ["mqtt"]`) subscribes to the box's topic.
3. It answers the box's `_sync` handshake.
4. It periodically publishes `{"REFRESH":0}` on the server topic to pull every value — the
   box only dumps its `B_*`/`C1B_*`/`CNT_*` values in reply to a REFRESH.
5. Each raw code becomes a push sensor (`local_push`).

Inbound messages carry a 40-hex `_sign` whose algorithm is unknown. Because a REFRESH is a
harmless read, the bridge probes REFRESH variants until one triggers a value dump, then keeps
it: zero `_sign`, no `_sign`, and — only if you configured one — a replay of a `_sign` you
captured yourself from the real cloud. No capture is shipped with the integration. The HA log
says which variant worked, which also answers whether the box verifies inbound signatures.

## Requirements

- An **MQTT broker configured in Home Assistant** (e.g. the Mosquitto add-on + the MQTT
  integration). This component is a client of it.
- The WiFi-Box must reach that broker. Because the box always connects to
  `portal.centrometal.hr:1883`, you must, on the network the box uses:
  1. **Redirect DNS** for `portal.centrometal.hr` to your MQTT broker host (router local DNS,
     AdGuard/Pi-hole, `dnsmasq`…).
  2. Let the broker **accept the box's connection** (client id / username = the box serial,
     an 8-hex password). Configure a matching MQTT user or an ACL for it.

No port conflict here: the box connects to your existing broker on 1883 — this integration
never opens a listening socket.

## Installation

### HACS (custom repository)

1. HACS → ⋮ → *Custom repositories*.
2. Add `https://github.com/AndroFlo/hass-centrometal-wifibox`, category **Integration**.
3. Install *Centrometal WiFi-Box (local)* and restart Home Assistant.

### Manual

Copy `custom_components/centrometal_wifibox` into your HA `config/custom_components/` folder
and restart.

## Configuration

Settings → Devices & Services → **Add Integration** → *Centrometal WiFi-Box (local)*.
Enter a name, the **WiFi-Box serial** (e.g. `XXXXXXXX`) and the **boiler type** used in the
topic (`biopl` for BioTec Plus). Then set up DNS + broker access as above; sensors appear
after the first value dump.

The optional **captured REFRESH `_sign`** (40 hex) is for the case where the unsigned variants
get no answer, meaning your box verifies inbound signatures. Capture a cloud REFRESH on
`cm.srv.<product>.<serial>` before redirecting DNS, and paste its `_sign` here — or later via
*Configure* on the integration entry. Leave it empty otherwise.

Unmapped raw codes show up as disabled `{?} <code>` sensors — enable them to discover new
values, and they can then be added to `codes.py`.

## Debugging

```yaml
logger:
  logs:
    custom_components.centrometal_wifibox: debug
```

## Roadmap

- Phase 1 (this release): read-only, over your MQTT broker.
- Phase 2: control commands (turn on/off, pellet mode, circuits) — only once it is confirmed
  how the box handles the `_sign` of inbound messages.

## License

MIT — see [LICENSE](LICENSE).
