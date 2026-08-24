"""Config flow for LSA SAF."""
from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult, OptionsFlowWithReload
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import NumberSelector, NumberSelectorConfig, NumberSelectorMode

from .api import LsaSafAuthError, LsaSafError
from .products.fire import ActiveFireClient
from .const import (
    CONF_DEDUP_HOURS,
    CONF_DEDUP_RADIUS_KM,
    CONF_MIN_CONFIDENCE,
    CONF_MIN_FRP_MW,
    CONF_PASSWORD,
    CONF_RADIUS_KM,
    CONF_SCAN_INTERVAL_MINUTES,
    CONF_USERNAME,
    DEFAULT_DEDUP_HOURS,
    DEFAULT_DEDUP_RADIUS_KM,
    DEFAULT_MIN_CONFIDENCE,
    DEFAULT_MIN_FRP_MW,
    DEFAULT_RADIUS_KM,
    DEFAULT_SCAN_INTERVAL_MINUTES,
    DOMAIN,
    MAX_RADIUS_KM,
    MIN_RADIUS_KM,
)


class LsaSafConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle an LSA SAF config flow."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            client = ActiveFireClient(
                async_get_clientsession(self.hass),
                user_input[CONF_USERNAME],
                user_input[CONF_PASSWORD],
            )
            try:
                await client.async_test_auth()
            except LsaSafAuthError:
                errors["base"] = "invalid_auth"
            except LsaSafError:
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(user_input[CONF_USERNAME].strip().lower())
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title="LSA SAF",
                    data={
                        CONF_USERNAME: user_input[CONF_USERNAME].strip(),
                        CONF_PASSWORD: user_input[CONF_PASSWORD],
                    },
                    options=_default_options(),
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_USERNAME): str,
                    vol.Required(CONF_PASSWORD): str,
                }
            ),
            errors=errors,
        )

    async def async_step_reauth(
        self, entry_data: dict[str, Any]
    ) -> ConfigFlowResult:
        """Start reauthentication after a runtime authentication failure."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Validate replacement credentials and update the existing entry."""
        entry = self._get_reauth_entry()
        errors: dict[str, str] = {}

        if user_input is not None:
            username = user_input[CONF_USERNAME].strip()
            password = user_input[CONF_PASSWORD]
            client = ActiveFireClient(
                async_get_clientsession(self.hass),
                username,
                password,
            )
            try:
                await client.async_test_auth()
            except LsaSafAuthError:
                errors["base"] = "invalid_auth"
            except LsaSafError:
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(username.lower())
                self._abort_if_unique_id_mismatch(reason="wrong_account")
                return self.async_update_reload_and_abort(
                    entry,
                    data_updates={
                        CONF_USERNAME: username,
                        CONF_PASSWORD: password,
                    },
                )

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_USERNAME,
                    default=entry.data.get(CONF_USERNAME, ""),
                ): str,
                vol.Required(CONF_PASSWORD): str,
            }
        )
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=schema,
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> config_entries.OptionsFlow:
        return LsaSafOptionsFlow()


class LsaSafOptionsFlow(OptionsFlowWithReload):
    """Handle LSA SAF integration options."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        current = _default_options() | dict(self.config_entry.options)
        schema = vol.Schema(
            {
                vol.Required(CONF_RADIUS_KM): NumberSelector(
                    NumberSelectorConfig(min=MIN_RADIUS_KM, max=MAX_RADIUS_KM, step=1, unit_of_measurement="km", mode=NumberSelectorMode.BOX)
                ),
                vol.Required(CONF_MIN_CONFIDENCE): NumberSelector(
                    NumberSelectorConfig(min=0, max=1, step=0.05, mode=NumberSelectorMode.SLIDER)
                ),
                vol.Required(CONF_MIN_FRP_MW): NumberSelector(
                    NumberSelectorConfig(min=0, max=1000, step=1, unit_of_measurement="MW", mode=NumberSelectorMode.BOX)
                ),
                vol.Required(CONF_SCAN_INTERVAL_MINUTES): NumberSelector(
                    NumberSelectorConfig(min=2, max=30, step=1, unit_of_measurement="min", mode=NumberSelectorMode.BOX)
                ),
                vol.Required(CONF_DEDUP_RADIUS_KM): NumberSelector(
                    NumberSelectorConfig(min=0.5, max=20, step=0.5, unit_of_measurement="km", mode=NumberSelectorMode.BOX)
                ),
                vol.Required(CONF_DEDUP_HOURS): NumberSelector(
                    NumberSelectorConfig(min=1, max=48, step=1, unit_of_measurement="h", mode=NumberSelectorMode.BOX)
                ),
            }
        )
        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(schema, current),
        )


def _default_options() -> dict[str, Any]:
    return {
        CONF_RADIUS_KM: DEFAULT_RADIUS_KM,
        CONF_MIN_CONFIDENCE: DEFAULT_MIN_CONFIDENCE,
        CONF_MIN_FRP_MW: DEFAULT_MIN_FRP_MW,
        CONF_SCAN_INTERVAL_MINUTES: DEFAULT_SCAN_INTERVAL_MINUTES,
        CONF_DEDUP_RADIUS_KM: DEFAULT_DEDUP_RADIUS_KM,
        CONF_DEDUP_HOURS: DEFAULT_DEDUP_HOURS,
    }
