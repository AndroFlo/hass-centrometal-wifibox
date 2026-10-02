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

Leave the optional **captured REFRESH `_sign`** empty on a first run — you only need it if
the box turns out to verify inbound signatures. See
[Capturing a REFRESH `_sign`](#capturing-a-refresh-_sign) below.

Unmapped raw codes show up as disabled `{?} <code>` sensors — enable them to discover new
values, and they can then be added to `codes.py`.

### Finding the WiFi-Box serial

It is an 8-character hexadecimal string (digits and `A`-`F`). Easiest sources first:

- **The web-boiler.com account or the Centrometal app** — the boiler is listed by serial. This
  is also the name you registered the box under.
- **The cloud integration, if you already run it** —
  [`hass-centrometal-boiler`](https://github.com/AndroFlo/hass-centrometal-boiler) names each
  device `Centrometal Boiler <model> <serial>` (Settings → Devices & Services → *Centrometal
  Boiler* → the device), and every entity's unique id is `<serial>-<parameter>`.
- **The sticker** — on the WiFi-Box itself, or inside the boiler's control panel door where the
  module is fitted. Depending on the batch it is labelled *SN*, *Serial* or *ID*.
- **The boiler's own menu** — the CM controller shows the WiFi module's identifier in its
  network/WiFi information screen.

Failing all of that, read it off the network: the box authenticates to the broker with its
serial as **client id and username** (the password is a separate 8-hex string). A broker it
tries to reach logs that client id on connection, so pointing its DNS at your Mosquitto and
watching the log reveals the serial even if you have it written down nowhere:

```bash
# Mosquitto log, box connecting
grep -i "new client connected" /var/log/mosquitto/mosquitto.log
```

The same serial appears in the MQTT topics themselves (`cm.inst.biopl.<serial>`), so
subscribing to `cm.inst.#` on your broker shows it too.

## Capturing a REFRESH `_sign`

**Try without it first.** Set the integration up with the field empty and watch the log. If you
see `REFRESH variant B/zero-sign works` (or `C/no-sign`), your box does not check inbound
signatures and you are done — nothing to capture. You only need this section if *no* variant
ever answers while the box is clearly publishing (`box-> cm.inst...` lines in the log, but no
value dump).

The catch: only the **real cloud** can produce a valid `_sign`, so it can only be captured
while the box and the cloud are still talking to each other. A broker of your own that merely
accepts the box is not enough — with the cloud cut off, nobody sends a REFRESH any more and
there is no signature to see. Either capture before redirecting DNS (options B and C, which
watch the box's normal traffic), or redirect it through something that still forwards to the
cloud (option A). MQTT on port 1883 is unencrypted, so all three only have to read the bytes.

### Option A — Mosquitto as a man-in-the-middle bridge

Put your broker between the box and the cloud: it accepts the box, and forwards everything
upstream through a **bridge**, logging both directions on the way. In `mosquitto.conf`:

```
connection centrometal-capture
address portal.centrometal.hr:1883
topic # both 0 "" ""

log_type all
log_dest file /var/log/mosquitto/capture.log
```

Redirect the box's DNS to this broker (same step as the normal setup). The box reaches the
cloud as usual, so the cloud keeps polling, and `capture.log` records the REFRESH it sends —
`_sign` included. Grep the log:

```bash
grep -o '"_sign":"[0-9a-f]\{40\}"' /var/log/mosquitto/capture.log | sort -u
```

Remove the `connection` block once you are done, so the box stops reaching the cloud.

### Option B — tcpdump on the gateway

If your router, Pi-hole or HA host sits on the path between the box and the internet:

```bash
sudo tcpdump -i any -A -s0 'tcp port 1883 and host <box-ip>' | grep -o '"_sign":"[0-9a-f]\{40\}"'
```

Let it run a few minutes: the cloud polls REFRESH regularly. Keep the `_sign` that appears in a
packet travelling **towards** the box (server → box) alongside a `REFRESH` key — not one coming
from the box.

To see full payloads rather than just the signatures, drop the `grep`, or use
`tshark -i any -f 'tcp port 1883' -Y mqtt -T fields -e mqtt.msg` for decoded MQTT.

### Option C — port mirroring / ARP spoofing

On a switch that supports it, mirror the box's port and capture with Wireshark (filter `mqtt`).
Without a managed switch, `ettercap`/`bettercap` on your own LAN achieves the same. Only do this
on a network you own.

### Then

Paste the 40-hex value into the **captured REFRESH `_sign`** field, at setup or later via
*Configure* on the integration entry. The bridge then probes that replay variant first.

Be aware of two limits. The signature is replayed with a **fresh `srvMsgId`**, so if the unknown
algorithm covers that field the replay will not validate — in that case no variant can work and
phase 2 stays blocked until the algorithm is understood. And the `_sign` is specific to your box:
never paste one from someone else's capture, and treat yours as you would any other value tied to
your installation.

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
