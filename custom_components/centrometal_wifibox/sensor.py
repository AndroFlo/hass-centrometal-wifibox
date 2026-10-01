"""Sensor platform: one entity per raw Centrometal code the box reports.

Entities are created dynamically as codes appear in the value dumps. Known codes get
a friendly name/unit/device_class (see codes.py); unknown codes are exposed as
disabled-by-default `{?} <code>` sensors so new values can be discovered.
"""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .codes import DIAGNOSTIC_CODES, KNOWN_CODES
from .const import DOMAIN, MANUFACTURER, UNKNOWN_PREFIX
from .coordinator import WifiboxCoordinator

# Units for which a numeric value is a live measurement.
_MEASUREMENT_UNITS = {"rpm", "% O2", "kOhm", "%"}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: WifiboxCoordinator = hass.data[DOMAIN][entry.entry_id]
    added: set[str] = set()

    @callback
    def _add_entities(codes: list[str] | None = None) -> None:
        source = codes if codes is not None else list(coordinator.data)
        new_entities = []
        for code in source:
            if code in added or code.startswith("_"):
                continue
            added.add(code)
            new_entities.append(WifiboxSensor(coordinator, code))
        if new_entities:
            async_add_entities(new_entities)

    # Any codes already received before the platform loaded.
    _add_entities()
    entry.async_on_unload(
        async_dispatcher_connect(hass, coordinator.signal_new_keys, _add_entities)
    )


class WifiboxSensor(SensorEntity):
    """A single raw code exposed as a sensor."""

    _attr_should_poll = False
    _attr_has_entity_name = False

    def __init__(self, coordinator: WifiboxCoordinator, code: str) -> None:
        self.coordinator = coordinator
        self.code = code
        serial = coordinator.serial or "centrometal"
        self._attr_unique_id = f"{serial}_{code}"

        desc = KNOWN_CODES.get(code)
        if desc is not None:
            unit, icon, device_class, name = desc
            self._attr_name = name
            self._attr_native_unit_of_measurement = unit
            self._attr_device_class = device_class
            self._attr_icon = icon
            if device_class == SensorDeviceClass.TEMPERATURE:
                self._attr_state_class = SensorStateClass.MEASUREMENT
            elif unit in _MEASUREMENT_UNITS:
                self._attr_state_class = SensorStateClass.MEASUREMENT
            if code in DIAGNOSTIC_CODES:
                self._attr_entity_category = EntityCategory.DIAGNOSTIC
                self._attr_entity_registry_enabled_default = False
        else:
            # Unmapped raw code: keep it, but disabled by default.
            self._attr_name = f"{UNKNOWN_PREFIX} {code}"
            self._attr_icon = "mdi:help-circle-outline"
            self._attr_entity_category = EntityCategory.DIAGNOSTIC
            self._attr_entity_registry_enabled_default = False

    @property
    def native_value(self) -> Any:
        return self.coordinator.data.get(self.code)

    @property
    def available(self) -> bool:
        return self.code in self.coordinator.data

    @property
    def device_info(self) -> DeviceInfo:
        serial = self.coordinator.serial or "centrometal"
        product = self.coordinator.data.get("B_PRODNAME") or "WiFi-Box"
        return DeviceInfo(
            identifiers={(DOMAIN, serial)},
            manufacturer=MANUFACTURER,
            name=f"{MANUFACTURER} {product}",
            model=self.coordinator.data.get("B_PRODNAME"),
            sw_version=self.coordinator.data.get("B_VER"),
            serial_number=serial,
        )

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, self.coordinator.signal_update, self.async_write_ha_state
            )
        )
