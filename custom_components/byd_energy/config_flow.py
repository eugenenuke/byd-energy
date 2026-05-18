"""Config flow for BYD Energy integration."""
import logging
from typing import Any, Dict, Optional

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.helpers import aiohttp_client

from .api import BydEnergyApiClient, BydEnergyAuthError
from .const import CONF_PID, CONF_POLLING_INTERVAL, CONF_PRODUCT_TYPE, DEFAULT_POLLING_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
        vol.Optional(CONF_POLLING_INTERVAL, default=DEFAULT_POLLING_INTERVAL): vol.All(int, vol.Range(min=5, max=300)),
    }
)


class BydEnergyConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for BYD Energy."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize config flow."""
        self._auth_data: Dict[str, Any] = {}
        self._discovered_devices: list[Dict[str, Any]] = []

    async def async_step_user(self, user_input: Optional[Dict[str, Any]] = None) -> config_entries.FlowResult:
        """Handle the initial user credentials authentication step."""
        errors: Dict[str, str] = {}
        if user_input is not None:
            username = user_input[CONF_USERNAME]
            password = user_input[CONF_PASSWORD]
            polling_interval = user_input[CONF_POLLING_INTERVAL]

            session = aiohttp_client.async_get_clientsession(self.hass)
            client = BydEnergyApiClient(username, password, session)

            try:
                await client.login()
                devices = await client.get_paged_devices()
                if not devices:
                    errors["base"] = "no_devices_found"
                else:
                    self._auth_data = {
                        CONF_USERNAME: username,
                        CONF_PASSWORD: password,
                        CONF_POLLING_INTERVAL: polling_interval,
                        "access_token": client.access_token,
                        "refresh_token": client.refresh_token,
                    }
                    self._discovered_devices = devices
                    return await self.async_step_select_device()
            except BydEnergyAuthError:
                errors["base"] = "invalid_auth"
            except Exception as ex:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception in BYD Energy config flow: %s", ex)
                errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    async def async_step_select_device(self, user_input: Optional[Dict[str, Any]] = None) -> config_entries.FlowResult:
        """Handle selection of discovered hardware device."""
        errors: Dict[str, str] = {}

        device_options = {
            dev["Pid"]: f"{dev.get('ProductModel', 'BYD System')} ({dev['Pid']})"
            for dev in self._discovered_devices
            if "Pid" in dev
        }

        if not device_options:
            return self.async_abort(reason="no_devices_found")

        if user_input is not None:
            selected_pid = user_input[CONF_PID]
            selected_dev = next((dev for dev in self._discovered_devices if dev.get("Pid") == selected_pid), None)

            product_type = "lixia"
            if selected_dev and selected_dev.get("ProductType"):
                product_type = selected_dev["ProductType"]

            entry_data = {
                **self._auth_data,
                CONF_PID: selected_pid,
                CONF_PRODUCT_TYPE: product_type,
            }

            title = f"BYD {device_options.get(selected_pid, selected_pid)}"
            return self.async_create_entry(title=title, data=entry_data)

        schema = vol.Schema({vol.Required(CONF_PID): vol.In(device_options)})

        return self.async_show_form(
            step_id="select_device",
            data_schema=schema,
            errors=errors,
        )
