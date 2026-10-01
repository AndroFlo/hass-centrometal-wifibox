"""Coordinator: owns the MQTT bridge and the latest boiler values."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .const import (
    CONF_PRODUCT,
    CONF_REFRESH_SIGN,
    CONF_SERIAL,
    DEFAULT_PRODUCT,
    SIGNAL_NEW_KEYS,
    SIGNAL_UPDATE,
)
from .mqtt_bridge import MqttBridge

_LOGGER = logging.getLogger(__name__)


class WifiboxCoordinator:
    """Runs the MQTT bridge and holds the merged latest value of every raw code."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        self.serial: str = entry.data[CONF_SERIAL]
        self.product: str = entry.data.get(CONF_PRODUCT, DEFAULT_PRODUCT)
        # The replay `_sign` is user-supplied (options take precedence over setup data).
        refresh_sign: str = entry.options.get(
            CONF_REFRESH_SIGN, entry.data.get(CONF_REFRESH_SIGN, "")
        )
        self.data: dict[str, Any] = {}
        self._bridge = MqttBridge(
            hass, self.serial, self.product, self._on_values, refresh_sign
        )

    async def async_start(self) -> None:
        await self._bridge.async_start()

    async def async_stop(self) -> None:
        await self._bridge.async_stop()

    @property
    def signal_update(self) -> str:
        return f"{SIGNAL_UPDATE}_{self.entry.entry_id}"

    @property
    def signal_new_keys(self) -> str:
        return f"{SIGNAL_NEW_KEYS}_{self.entry.entry_id}"

    @callback
    def _on_values(self, serial: str, values: dict[str, Any]) -> None:
        """Called by the bridge (in the HA loop) on every value dump."""
        new_keys = [k for k in values if k not in self.data]
        self.data.update(values)
        if new_keys:
            async_dispatcher_send(self.hass, self.signal_new_keys, new_keys)
        async_dispatcher_send(self.hass, self.signal_update)
