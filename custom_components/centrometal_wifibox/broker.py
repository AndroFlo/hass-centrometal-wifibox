"""Minimal read-only MQTT 3.1.1 broker that stands in for the Centrometal cloud.

The CM WiFi-Box connects to portal.centrometal.hr:1883 in clear text, subscribes to
`cm.srv.biopl.<serial>` and publishes to `cm.inst.biopl.<serial>`. It only dumps its
`B_*` / `C1B_*` values in reply to a server `{"REFRESH":0}`; otherwise it just sends a
`{"wf_req":"?"}` heartbeat. So this broker accepts the box, answers its `_sync`, and
periodically sends REFRESH to pull values.

Inbound messages carry a 40-hex `_sign`; it is unknown whether the box verifies it, so
REFRESH (a harmless read) is probed with three variants until one triggers a value dump,
then that variant is kept. NO control command is ever sent.

This module is self-contained (no third-party deps) and runs inside the Home Assistant
event loop.
"""

from __future__ import annotations

import asyncio
import json
import logging
import struct
from typing import Any, Callable

_LOGGER = logging.getLogger(__name__)

SERVER_TOPIC_DOT = "cm.srv.biopl.{serial}"

REFRESH_INTERVAL = 30       # seconds between pulls once a variant works
VARIANT_TIMEOUT = 8         # seconds to wait for a dump after a REFRESH

# Variant A: exact bytes captured from the real cloud (replay).
CAPTURED_REFRESH = (
    '{"REFRESH":0,"srvMsgId":594808,'
    '"_sign":"7edb5d72f79952ec22bea5ea5c98bda40c726502"}'
)


def _encode_remaining_length(n: int) -> bytes:
    out = bytearray()
    while True:
        byte, n = n % 128, n // 128
        out.append(byte | (0x80 if n else 0))
        if not n:
            return bytes(out)


def _read_string(data: bytes, pos: int) -> tuple[str, int]:
    (length,) = struct.unpack_from("!H", data, pos)
    pos += 2
    return data[pos:pos + length].decode("utf-8", "replace"), pos + length


class _BoxSession:
    """One connected WiFi-Box."""

    def __init__(self, broker: "LocalBroker", reader, writer) -> None:
        self.broker = broker
        self.reader = reader
        self.writer = writer
        self.peer = writer.get_extra_info("peername")
        self.serial: str | None = None
        self.sub_topic: str | None = None
        self.srv_msg_id = 700000
        self.dump_event = asyncio.Event()
        self._refresh_task: asyncio.Task | None = None

    # ---- framing ----
    async def _read_packet(self) -> tuple[int, bytes]:
        first = await self.reader.readexactly(1)
        multiplier, length = 1, 0
        while True:
            (byte,) = await self.reader.readexactly(1)
            length += (byte & 0x7F) * multiplier
            if not byte & 0x80:
                break
            multiplier *= 128
        body = await self.reader.readexactly(length) if length else b""
        return first[0], body

    async def _send(self, first_byte: int, body: bytes = b"") -> None:
        self.writer.write(bytes([first_byte]) + _encode_remaining_length(len(body)) + body)
        await self.writer.drain()

    async def _publish(self, topic: str, payload: str) -> None:
        topic_b = topic.encode("utf-8")
        body = struct.pack("!H", len(topic_b)) + topic_b + payload.encode("utf-8")
        await self._send(0x30, body)
        _LOGGER.debug("-> box PUBLISH %s %s", topic, payload)

    def _next_id(self) -> int:
        self.srv_msg_id += 1
        return self.srv_msg_id

    def _server_topic(self) -> str:
        return self.sub_topic or SERVER_TOPIC_DOT.format(serial=self.serial or "UNKNOWN")

    def _refresh_variants(self) -> list[tuple[str, str]]:
        return [
            ("A/replay", CAPTURED_REFRESH),
            ("B/zero-sign",
             json.dumps({"REFRESH": 0, "srvMsgId": self._next_id(), "_sign": "0" * 40})),
            ("C/no-sign",
             json.dumps({"REFRESH": 0, "srvMsgId": self._next_id()})),
        ]

    # ---- handlers ----
    async def _on_connect(self, body: bytes) -> None:
        pos = 0
        _proto, pos = _read_string(body, pos)
        pos += 1                       # protocol level
        pos += 1                       # connect flags
        pos += 2                       # keepalive
        client_id, pos = _read_string(body, pos)
        self.serial = client_id or self.serial
        _LOGGER.info("WiFi-Box CONNECT from %s (serial=%s)", self.peer, self.serial)
        await self._send(0x20, bytes([0x00, 0x00]))   # CONNACK accepted
        if self.serial:
            self.broker.on_connect(self.serial)

    async def _on_subscribe(self, body: bytes) -> None:
        (packet_id,) = struct.unpack_from("!H", body, 0)
        pos = 2
        codes = bytearray()
        while pos < len(body):
            topic, pos = _read_string(body, pos)
            pos += 1                   # requested QoS
            self.sub_topic = topic
            codes.append(0x00)
            _LOGGER.debug("SUBSCRIBE %s", topic)
        await self._send(0x90, struct.pack("!H", packet_id) + bytes(codes))

    async def _on_publish(self, first_byte: int, body: bytes) -> None:
        qos = (first_byte >> 1) & 0x03
        topic, pos = _read_string(body, 0)
        if qos > 0:
            (packet_id,) = struct.unpack_from("!H", body, pos)
            pos += 2
            await self._send(0x40, struct.pack("!H", packet_id))   # PUBACK
        payload = body[pos:].decode("utf-8", "replace")
        _LOGGER.debug("box-> PUBLISH %s %s", topic, payload)

        try:
            data = json.loads(payload)
        except (json.JSONDecodeError, ValueError):
            return
        if not isinstance(data, dict):
            return

        if data.get("_sync") == "id" and "_token" in data:
            ack = json.dumps({"_sync_ACK": "ok", "_token": data["_token"],
                              "srvMsgId": self._next_id(), "_sign": "0" * 40})
            await self._publish(self._server_topic(), ack)

        values = {k: v for k, v in data.items()
                  if k.startswith("B_") or k.startswith("C1B_") or k.startswith("CNT_")}
        if values:
            self.dump_event.set()
            self.broker.on_values(self.serial, values)

    # ---- refresh loop ----
    async def _pull_once(self, tag: str, payload: str) -> bool:
        self.dump_event.clear()
        await self._publish(self._server_topic(), payload)
        try:
            await asyncio.wait_for(self.dump_event.wait(), VARIANT_TIMEOUT)
            return True
        except asyncio.TimeoutError:
            _LOGGER.debug("REFRESH variant %s: no value dump in %ss", tag, VARIANT_TIMEOUT)
            return False

    async def _refresh_loop(self) -> None:
        while self.sub_topic is None:
            await asyncio.sleep(0.5)
        working: tuple[str, str] | None = None
        while True:
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

    # ---- lifecycle ----
    async def run(self) -> None:
        self._refresh_task = asyncio.ensure_future(self._refresh_loop())
        try:
            while True:
                first_byte, body = await self._read_packet()
                ptype = first_byte >> 4
                if ptype == 1:          # CONNECT
                    await self._on_connect(body)
                elif ptype == 3:        # PUBLISH
                    await self._on_publish(first_byte, body)
                elif ptype == 8:        # SUBSCRIBE
                    await self._on_subscribe(body)
                elif ptype == 12:       # PINGREQ
                    await self._send(0xD0)   # PINGRESP
                elif ptype == 14:       # DISCONNECT
                    _LOGGER.info("WiFi-Box %s disconnected", self.peer)
                    break
                # PUBACK(4)/PUBREC(5)/PUBREL(6)/PUBCOMP(7): nothing to do.
        except (asyncio.IncompleteReadError, ConnectionError):
            _LOGGER.info("WiFi-Box %s connection closed", self.peer)
        finally:
            if self._refresh_task:
                self._refresh_task.cancel()
            self.writer.close()


class LocalBroker:
    """Listens on a TCP port and serves one or more WiFi-Box sessions."""

    def __init__(
        self,
        port: int,
        on_values: Callable[[str | None, dict[str, Any]], None],
        on_connect: Callable[[str], None],
    ) -> None:
        self.port = port
        self.on_values = on_values
        self.on_connect = on_connect
        self._server: asyncio.AbstractServer | None = None

    async def start(self) -> None:
        self._server = await asyncio.start_server(self._handle, "0.0.0.0", self.port)
        _LOGGER.info("Centrometal WiFi-Box broker listening on 0.0.0.0:%s (read only)",
                     self.port)

    async def stop(self) -> None:
        if self._server is not None:
            self._server.close()
            try:
                await self._server.wait_closed()
            except Exception:  # noqa: BLE001 - best effort on shutdown
                pass
            self._server = None

    async def _handle(self, reader, writer) -> None:
        await _BoxSession(self, reader, writer).run()
