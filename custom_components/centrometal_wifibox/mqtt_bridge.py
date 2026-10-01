"""MQTT bridge: talks to the CM WiFi-Box through Home Assistant's MQTT broker.

Instead of embedding its own broker, this integration is a *client* of the MQTT broker
already configured in Home Assistant (e.g. the Mosquitto add-on). The WiFi-Box must be
pointed at that same broker (redirect DNS `portal.centrometal.hr` to the broker host,
and let the broker accept the box's connection).

The box publishes to `cm.inst.<product>.<serial>` and subscribes to
`cm.srv.<product>.<serial>`. It only dumps its `B_*`/`C1B_*`/`CNT_*` values in reply to a
server `{"REFRESH":0}`. So this bridge subscribes to the box's topic, answers its `_sync`
handshake, and periodically publishes REFRESH to pull values.

Inbound messages carry a 40-hex `_sign` whose algorithm is unknown. REFRESH is a harmless
read, so the variants are probed (zero `_sign` / no `_sign`, plus a replay of a `_sign`
captured from the real cloud if the user configured one) until one triggers a dump, then
that variant is kept. NO control command is ever sent.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Callable

from homeassistant.components import mqtt
from homeassistant.core import HomeAssistant, callback

_LOGGER = logging.getLogger(__name__)

REFRESH_INTERVAL = 30       # seconds between pulls once a variant works
VARIANT_TIMEOUT = 8         # seconds to wait for a dump after a REFRESH


class MqttBridge:
    """Bridges the WiFi-Box to HA over the configured MQTT broker."""

    def __init__(
        self,
        hass: HomeAssistant,
        serial: str,
        product: str,
        on_values: Callable[[str, dict[str, Any]], None],
        refresh_sign: str | None = None,
    ) -> None:
        self.hass = hass
        self.serial = serial
        self.product = product
        self.on_values = on_values
        self.refresh_sign = (refresh_sign or "").strip() or None
        self.inst_topic = f"cm.inst.{product}.{serial}"   # box -> us
        self.srv_topic = f"cm.srv.{product}.{serial}"      # us -> box
        self.srv_msg_id = 700000
        self.dump_event = asyncio.Event()
        self._unsub: Callable[[], None] | None = None
        self._task: asyncio.Task | None = None

    async def async_start(self) -> None:
        self._unsub = await mqtt.async_subscribe(
            self.hass, self.inst_topic, self._on_message, qos=0
        )
        self._task = self.hass.async_create_background_task(
            self._refresh_loop(), "centrometal_wifibox_refresh"
        )
        _LOGGER.info("Subscribed to %s; publishing REFRESH on %s",
                     self.inst_topic, self.srv_topic)

    async def async_stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
        if self._unsub is not None:
            self._unsub()

    def _next_id(self) -> int:
        self.srv_msg_id += 1
        return self.srv_msg_id

    def _refresh_variants(self) -> list[tuple[str, str]]:
        variants: list[tuple[str, str]] = []
        if self.refresh_sign:
            variants.append(
                ("A/replay",
                 json.dumps({"REFRESH": 0, "srvMsgId": self._next_id(),
                             "_sign": self.refresh_sign}))
            )
        variants.append(
            ("B/zero-sign",
             json.dumps({"REFRESH": 0, "srvMsgId": self._next_id(), "_sign": "0" * 40}))
        )
        variants.append(
            ("C/no-sign",
             json.dumps({"REFRESH": 0, "srvMsgId": self._next_id()}))
        )
        return variants

    async def _publish(self, payload: str) -> None:
        await mqtt.async_publish(self.hass, self.srv_topic, payload, qos=0)
        _LOGGER.debug("-> box %s %s", self.srv_topic, payload)

    @callback
    def _on_message(self, msg: mqtt.ReceiveMessage) -> None:
        payload = msg.payload
        _LOGGER.debug("box-> %s %s", msg.topic, payload)
        try:
            data = json.loads(payload)
        except (json.JSONDecodeError, ValueError, TypeError):
            return
        if not isinstance(data, dict):
            return

        # Sync handshake: echo the token so the box considers the session live.
        if data.get("_sync") == "id" and "_token" in data:
            ack = json.dumps({"_sync_ACK": "ok", "_token": data["_token"],
                              "srvMsgId": self._next_id(), "_sign": "0" * 40})
            self.hass.async_create_task(self._publish(ack))

        values = {k: v for k, v in data.items()
                  if k.startswith("B_") or k.startswith("C1B_") or k.startswith("CNT_")}
        if values:
            self.dump_event.set()
            self.on_values(self.serial, values)

    async def _pull_once(self, tag: str, payload: str) -> bool:
        self.dump_event.clear()
        await self._publish(payload)
        try:
            await asyncio.wait_for(self.dump_event.wait(), VARIANT_TIMEOUT)
            return True
        except asyncio.TimeoutError:
            _LOGGER.debug("REFRESH variant %s: no value dump in %ss", tag, VARIANT_TIMEOUT)
            return False

    async def _refresh_loop(self) -> None:
        working: tuple[str, str] | None = None
        while True:
            try:
                if working is not None:
                    if not await self._pull_once(*working):
                        _LOGGER.warning("REFRESH variant %s stopped answering; re-probing",
                                        working[0])
                        working = None
                else:
                    for tag, payload in self._refresh_variants():
                        if await self._pull_once(tag, payload):
                            working = (tag, payload)
                            _LOGGER.info(
                                "REFRESH variant %s works: box does not enforce inbound "
                                "_sign; locking onto it", tag)
                            break
                await asyncio.sleep(REFRESH_INTERVAL)
            except asyncio.CancelledError:
                raise
            except Exception:  # noqa: BLE001 - keep the loop alive on transient errors
                _LOGGER.exception("REFRESH loop error; retrying")
                await asyncio.sleep(REFRESH_INTERVAL)
