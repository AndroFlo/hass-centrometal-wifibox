"""The Centrometal WiFi-Box (local) integration.

Acts as a local MQTT server the boiler's CM WiFi-Box connects to instead of the
Centrometal cloud, so Home Assistant keeps reading the boiler even if the cloud is
down. Read only for now (no control command is sent).
"""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import DOMAIN
from .coordinator import WifiboxCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up the integration from a config entry."""
    coordinator = WifiboxCoordinator(hass, entry)
    try:
        await coordinator.async_start()
    except OSError as err:
        _LOGGER.error("Cannot start the WiFi-Box broker on port %s: %s",
                      coordinator.port, err)
        raise ConfigEntryNotReady(
            f"Cannot bind MQTT port {coordinator.port}: {err}"
        ) from err

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        coordinator: WifiboxCoordinator = hass.data[DOMAIN].pop(entry.entry_id)
        await coordinator.async_stop()
    return unloaded


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the entry when its options change (e.g. the listen port)."""
    await hass.config_entries.async_reload(entry.entry_id)
