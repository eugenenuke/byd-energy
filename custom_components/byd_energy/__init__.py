"""The BYD Energy custom component."""
import asyncio
from datetime import timedelta
import logging
import time
from typing import Any, Dict

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers import aiohttp_client
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import BydEnergyApiClient, BydEnergyAuthError, BydEnergyApiClientError
from .const import CONF_PID, CONF_POLLING_INTERVAL, CONF_PRODUCT_TYPE, DEFAULT_POLLING_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.SWITCH,
    Platform.NUMBER,
    Platform.TEXT,
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up BYD Energy from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    username = entry.data[CONF_USERNAME]
    password = entry.data[CONF_PASSWORD]
    pid = entry.data[CONF_PID]
    product_type = entry.data.get(CONF_PRODUCT_TYPE, "lixia")
    polling_interval = entry.data.get(CONF_POLLING_INTERVAL, DEFAULT_POLLING_INTERVAL)

    # Persistent token storage inside config entry data
    access_token = entry.data.get("access_token")
    refresh_token = entry.data.get("refresh_token")

    session = aiohttp_client.async_get_clientsession(hass)
    client = BydEnergyApiClient(username, password, session, access_token, refresh_token)

    coordinator = BydEnergyDataUpdateCoordinator(hass, client, pid, product_type, polling_interval, entry)

    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload BYD Energy config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok


class BydEnergyDataUpdateCoordinator(DataUpdateCoordinator[Dict[str, Any]]):
    """Class to manage fetching BYD Energy data from the cloud."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: BydEnergyApiClient,
        pid: str,
        product_type: str,
        polling_interval: int,
        entry: ConfigEntry,
    ) -> None:
        """Initialize data update coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=polling_interval),
        )
        self.client = client
        self.pid = pid
        self.product_type = product_type
        self._entry = entry
        self._last_medium_fetch = 0.0
        self._last_slow_fetch = 0.0

    async def _async_update_data(self) -> Dict[str, Any]:
        """Fetch consolidated data from BYD cloud using multi-rate loops."""
        now = time.time()
        
        # Initialize or copy data cache structure
        if self.data is not None:
            data = self.data.copy()
        else:
            data = {
                "sensors": {},
                "today_ele": {},
                "total_ele": {},
                "pv_realtimes": {},
                "online_state": {},
                "pv_max_power": {},
                "eeprom_settings": {},
                "base_settings": {},
                "grid_settings": {},
                "bms_type": None,
                "bms_current_version": None,
                "bms_latest_version": None,
                "pcs_current_version": None,
                "pcs_latest_version": None,
                "f527_current_version": None,
                "f527_latest_version": None,
            }

        # 1. Fast Loop (always executed: power flows, fast SOC, online connectivity status)
        tasks = {
            "sys": self.client.get_realtime_data_list(self.product_type, self.pid, "sys"),
            "pv_realtimes": self.client.get_pv_realtimes(self.product_type, self.pid),
            "online_state": self.client.get_online_state(self.pid),
        }

        # 2. Medium Loop (every 5 minutes / 300 seconds: daily energy totals, eeprom, cell diagnostics)
        do_medium = (self.data is None) or (now - self._last_medium_fetch >= 300)
        if do_medium:
            tasks.update({
                "pcs": self.client.get_realtime_data_list(self.product_type, self.pid, "pcs"),
                "batterySystem": self.client.get_realtime_data_list(self.product_type, self.pid, "batterySystem"),
                "bms": self.client.get_realtime_data_list(self.product_type, self.pid, "bms", child_no="1"),
                "eleme": self.client.get_realtime_data_list(self.product_type, self.pid, "eleme"),
                "today_ele": self.client.get_today_ele_data(self.product_type, self.pid),
                "total_ele": self.client.get_total_ele_data_new(self.product_type, self.pid),
                "pv_max_power": self.client.get_pv_max_power_output(self.pid),
                "eeprom_settings": self.client.get_device_eeprom_settings(self.product_type, self.pid),
            })

        # 3. Slow Loop (every 12 hours / 43200 seconds: static installation info, grid regulatory standards, available OTA firmware)
        do_slow = (self.data is None) or (now - self._last_slow_fetch >= 43200)
        if do_slow:
            tasks.update({
                "base_settings": self.client.get_device_base_settings(self.product_type, self.pid),
                "grid_settings": self.client.get_device_grid_settings(self.product_type, self.pid),
                "bms_type": self.client.get_bms_type(self.pid),
                "bms_current_version": self.client.get_current_upgrade_version("bms", self.pid),
                "bms_latest_version": self.client.get_latest_version(self.product_type, "bms"),
                "pcs_current_version": self.client.get_current_upgrade_version("pcs", self.pid),
                "pcs_latest_version": self.client.get_latest_version(self.product_type, "pcs"),
                "f527_current_version": self.client.get_current_upgrade_version("f527", self.pid),
                "f527_latest_version": self.client.get_latest_version(self.product_type, "f527"),
            })

        try:
            # Gather tasks dynamically
            keys = list(tasks.keys())
            coroutines = list(tasks.values())
            results = await asyncio.gather(*coroutines, return_exceptions=True)
            task_results = dict(zip(keys, results))

            # Check for token updates and persist to HA config entry if changed
            new_data = {**self._entry.data}
            changed = False
            if self.client.access_token != self._entry.data.get("access_token"):
                new_data["access_token"] = self.client.access_token
                changed = True
            if self.client.refresh_token != self._entry.data.get("refresh_token"):
                new_data["refresh_token"] = self.client.refresh_token
                changed = True
            if changed:
                self.hass.config_entries.async_update_entry(self._entry, data=new_data)
                _LOGGER.debug("Persisted refreshed tokens to Home Assistant config entry")

            # Validate results for authentication failures
            for key, res in task_results.items():
                if isinstance(res, BydEnergyAuthError):
                    raise ConfigEntryAuthFailed("BYD Energy session expired and authentication failed") from res
                if isinstance(res, Exception):
                    _LOGGER.warning("Error fetching subsystem metric for %s: %s", key, res)

            # Helper to populate sensor dictionary
            def _populate_sensors(metric_list: Any) -> None:
                if metric_list and isinstance(metric_list, list):
                    for item in metric_list:
                        if isinstance(item, dict) and "jsonName" in item:
                            val = item.get("jsonValue")
                            if val is not None or data["sensors"].get(item["jsonName"]) is None:
                                data["sensors"][item["jsonName"]] = val

            # Populate Fast Loop results
            if "sys" in task_results and not isinstance(task_results["sys"], Exception):
                _populate_sensors(task_results["sys"])
            if "pv_realtimes" in task_results and not isinstance(task_results["pv_realtimes"], Exception):
                data["pv_realtimes"] = task_results["pv_realtimes"]
            if "online_state" in task_results and not isinstance(task_results["online_state"], Exception):
                data["online_state"] = task_results["online_state"]

            # Populate Medium Loop results
            if do_medium:
                if "pcs" in task_results and not isinstance(task_results["pcs"], Exception):
                    _populate_sensors(task_results["pcs"])
                if "batterySystem" in task_results and not isinstance(task_results["batterySystem"], Exception):
                    _populate_sensors(task_results["batterySystem"])
                if "bms" in task_results and not isinstance(task_results["bms"], Exception):
                    _populate_sensors(task_results["bms"])
                if "eleme" in task_results and not isinstance(task_results["eleme"], Exception):
                    _populate_sensors(task_results["eleme"])
                if "today_ele" in task_results and not isinstance(task_results["today_ele"], Exception):
                    data["today_ele"] = task_results["today_ele"]
                if "total_ele" in task_results and not isinstance(task_results["total_ele"], Exception):
                    data["total_ele"] = task_results["total_ele"]
                if "pv_max_power" in task_results and not isinstance(task_results["pv_max_power"], Exception):
                    data["pv_max_power"] = task_results["pv_max_power"]
                if "eeprom_settings" in task_results and not isinstance(task_results["eeprom_settings"], Exception):
                    data["eeprom_settings"] = task_results["eeprom_settings"]
                self._last_medium_fetch = now

            # Populate Slow Loop results
            if do_slow:
                if "base_settings" in task_results and not isinstance(task_results["base_settings"], Exception):
                    data["base_settings"] = task_results["base_settings"]
                if "grid_settings" in task_results and not isinstance(task_results["grid_settings"], Exception):
                    data["grid_settings"] = task_results["grid_settings"]
                if "bms_type" in task_results and not isinstance(task_results["bms_type"], Exception):
                    data["bms_type"] = task_results["bms_type"]
                if "bms_current_version" in task_results and not isinstance(task_results["bms_current_version"], Exception):
                    data["bms_current_version"] = task_results["bms_current_version"]
                if "bms_latest_version" in task_results and not isinstance(task_results["bms_latest_version"], Exception):
                    data["bms_latest_version"] = task_results["bms_latest_version"]
                if "pcs_current_version" in task_results and not isinstance(task_results["pcs_current_version"], Exception):
                    data["pcs_current_version"] = task_results["pcs_current_version"]
                if "pcs_latest_version" in task_results and not isinstance(task_results["pcs_latest_version"], Exception):
                    data["pcs_latest_version"] = task_results["pcs_latest_version"]
                if "f527_current_version" in task_results and not isinstance(task_results["f527_current_version"], Exception):
                    data["f527_current_version"] = task_results["f527_current_version"]
                if "f527_latest_version" in task_results and not isinstance(task_results["f527_latest_version"], Exception):
                    data["f527_latest_version"] = task_results["f527_latest_version"]
                self._last_slow_fetch = now

            return data

        except ConfigEntryAuthFailed:
            raise
        except BydEnergyAuthError as err:
            raise ConfigEntryAuthFailed("BYD Energy session expired") from err
        except BydEnergyApiClientError as err:
            raise UpdateFailed(f"Error communicating with BYD Energy API: {err}") from err
        except Exception as err:
            raise UpdateFailed(f"Unexpected error updating BYD Energy: {err}") from err
