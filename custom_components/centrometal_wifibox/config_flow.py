"""Config flow for the Centrometal WiFi-Box (local) integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.components import mqtt
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import callback

from .const import (
    CONF_NAME,
    CONF_PRODUCT,
    CONF_REFRESH_SIGN,
    CONF_SERIAL,
    DEFAULT_NAME,
    DEFAULT_PRODUCT,
    DOMAIN,
)

SIGN_LENGTH = 40


def _invalid_sign(value: str) -> bool:
    """A `_sign`, when given, must be 40 hex characters."""
    if not value:
        return False
    if len(value) != SIGN_LENGTH:
        return True
    try:
        int(value, 16)
    except ValueError:
        return True
    return False


class WifiboxConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the initial setup."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        # The integration is a client of HA's MQTT broker; it needs one configured.
        if not await mqtt.async_wait_for_mqtt_client(self.hass):
            return self.async_abort(reason="mqtt_unavailable")

        errors: dict[str, str] = {}
        if user_input is not None:
            serial = user_input[CONF_SERIAL].strip()
            sign = user_input.get(CONF_REFRESH_SIGN, "").strip()
            if _invalid_sign(sign):
                errors[CONF_REFRESH_SIGN] = "invalid_sign"
            else:
                await self.async_set_unique_id(f"{DOMAIN}_{serial}")
                self._abort_if_unique_id_configured()
                user_input[CONF_SERIAL] = serial
                user_input[CONF_REFRESH_SIGN] = sign
                return self.async_create_entry(
                    title=user_input.get(CONF_NAME, DEFAULT_NAME), data=user_input
                )

        schema = vol.Schema(
            {
                vol.Required(CONF_NAME, default=DEFAULT_NAME): str,
                vol.Required(CONF_SERIAL): str,
                vol.Required(CONF_PRODUCT, default=DEFAULT_PRODUCT): str,
                vol.Optional(CONF_REFRESH_SIGN, default=""): str,
            }
        )
        return self.async_show_form(
            step_id="user", data_schema=schema, errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> WifiboxOptionsFlow:
        return WifiboxOptionsFlow()


class WifiboxOptionsFlow(OptionsFlow):
    """Let the replay `_sign` be set or changed after setup."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            sign = user_input.get(CONF_REFRESH_SIGN, "").strip()
            if _invalid_sign(sign):
                errors[CONF_REFRESH_SIGN] = "invalid_sign"
            else:
                return self.async_create_entry(data={CONF_REFRESH_SIGN: sign})

        current = self.config_entry.options.get(
            CONF_REFRESH_SIGN, self.config_entry.data.get(CONF_REFRESH_SIGN, "")
        )
        schema = vol.Schema(
            {vol.Optional(CONF_REFRESH_SIGN, default=current): str}
        )
        return self.async_show_form(
            step_id="init", data_schema=schema, errors=errors
        )
