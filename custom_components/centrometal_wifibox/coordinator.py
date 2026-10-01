"""Coordinator: owns the local broker and the latest boiler values."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .broker import LocalBroker
from .const import CONF_PORT, DEFAULT_PORT, SIGNAL_NEW_KEYS, SIGNAL_UPDATE

_LOGGER = logging.getLogger(__name__)


class WifiboxCoordinator:
    """Runs the broker and holds the merged latest value of every raw code."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        self.port: int = entry.data.get(CONF_PORT, DEFAULT_PORT)
        self.data: dict[str, Any] = {}
        self.serial: str | None = None
        self._broker = LocalBroker(self.port, self._on_values, self._on_connect)

    async def async_start(self) -> None:
        await self._broker.start()

    async def async_stop(self) -> None:
        await self._broker.stop()

    @property
    def signal_update(self) -> str:
        return f"{SIGNAL_UPDATE}_{self.entry.entry_id}"

    @property
    def signal_new_keys(self) -> str:
        return f"{SIGNAL_NEW_KEYS}_{self.entry.entry_id}"

    @callback
    def _on_connect(self, serial: str) -> None:
        self.serial = serial or self.serial

    @callback
    def _on_values(self, serial: str | None, values: dict[str, Any]) -> None:
        """Called by the broker (in the HA loop) on every value dump."""
        self.serial = serial or self.serial
        new_keys = [k for k in values if k not in self.data]
        self.data.update(values)
        if new_keys:
            async_dispatcher_send(self.hass, self.signal_new_keys, new_keys)
        async_dispatcher_send(self.hass, self.signal_update)
