"""Config flow for the Centrometal WiFi-Box (local) integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import callback

from .const import CONF_NAME, CONF_PORT, DEFAULT_NAME, DEFAULT_PORT, DOMAIN


class WifiboxConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the initial setup."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            await self.async_set_unique_id(f"{DOMAIN}_{user_input[CONF_PORT]}")
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=user_input.get(CONF_NAME, DEFAULT_NAME), data=user_input
            )

        schema = vol.Schema(
            {
                vol.Required(CONF_NAME, default=DEFAULT_NAME): str,
                vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return WifiboxOptionsFlow(config_entry)


class WifiboxOptionsFlow(OptionsFlow):
    """Allow changing the listen port after setup."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            data = {**self.config_entry.data, **user_input}
            self.hass.config_entries.async_update_entry(self.config_entry, data=data)
            return self.async_create_entry(title="", data={})

        current_port = self.config_entry.data.get(CONF_PORT, DEFAULT_PORT)
        schema = vol.Schema({vol.Required(CONF_PORT, default=current_port): int})
        return self.async_show_form(step_id="init", data_schema=schema)
