"""The BYD Energy custom component."""
import asyncio
from datetime import timedelta
import logging
import time as sys_time
from typing import Any, Dict

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers import aiohttp_client
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import BydEnergyApiClient, BydEnergyAuthError, BydEnergyApiClientError
from .const import (
    CONF_PID,
    CONF_POLLING_INTERVAL,
    CONF_PRODUCT_TYPE,
    DEFAULT_POLLING_INTERVAL,
    DOMAIN,
    CONF_MEDIUM_POLLING_INTERVAL,
    DEFAULT_MEDIUM_POLLING_INTERVAL,
    CONF_SLOW_POLLING_INTERVAL,
    DEFAULT_SLOW_POLLING_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.SWITCH,
    Platform.NUMBER,
    Platform.TIME,
    Platform.SELECT,
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up BYD Energy from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    username = entry.data[CONF_USERNAME]
    password = entry.data[CONF_PASSWORD]
    pid = entry.data[CONF_PID]
    product_type = entry.data.get(CONF_PRODUCT_TYPE, "lixia")
    polling_interval = entry.options.get(
        CONF_POLLING_INTERVAL, entry.data.get(CONF_POLLING_INTERVAL, DEFAULT_POLLING_INTERVAL)
    )
    medium_polling_interval = entry.options.get(
        CONF_MEDIUM_POLLING_INTERVAL, entry.data.get(CONF_MEDIUM_POLLING_INTERVAL, DEFAULT_MEDIUM_POLLING_INTERVAL)
    )
    slow_polling_interval = entry.options.get(
        CONF_SLOW_POLLING_INTERVAL, entry.data.get(CONF_SLOW_POLLING_INTERVAL, DEFAULT_SLOW_POLLING_INTERVAL)
    )

    # Persistent token storage inside config entry data
    access_token = entry.data.get("access_token")
    refresh_token = entry.data.get("refresh_token")

    session = aiohttp_client.async_get_clientsession(hass)
    client = BydEnergyApiClient(username, password, session, access_token, refresh_token)

    coordinator = BydEnergyDataUpdateCoordinator(
        hass,
        client,
        pid,
        product_type,
        polling_interval,
        medium_polling_interval,
        slow_polling_interval,
        entry,
    )

    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Register options update listener
    entry.async_on_unload(entry.add_update_listener(async_update_options))

    # Register custom service to force a full refresh of all loops
    async def handle_force_refresh(call) -> None:
        coordinator = hass.data[DOMAIN][entry.entry_id]
        await coordinator.async_force_full_refresh()

    hass.services.async_register(DOMAIN, "force_refresh", handle_force_refresh)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update by reloading the entry."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload BYD Energy config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
        # Unregister the custom service when integration is unloaded
        hass.services.async_remove(DOMAIN, "force_refresh")
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
        medium_polling_interval: int,
        slow_polling_interval: int,
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
        self.medium_polling_interval = medium_polling_interval
        self.slow_polling_interval = slow_polling_interval
        self._entry = entry
        self._last_medium_fetch = 0.0
        self._last_slow_fetch = 0.0
        self._bms_type = None

    def force_medium_refresh_soon(self) -> None:
        """Schedule a forced Medium Loop refresh after a 3-second safety delay to ensure cloud-to-hardware sync."""
        async def _deferred_refresh() -> None:
            await asyncio.sleep(3.0)
            self._last_medium_fetch = 0.0  # Bypass the 5-minute time gate
            await self.async_request_refresh()

        self.hass.async_create_task(_deferred_refresh())

    async def async_force_full_refresh(self) -> None:
        """Force a full refresh of all three loops (Fast, Medium, and Slow) instantly."""
        _LOGGER.debug("Forcing instant full refresh of all three BYD polling loops")
        self._last_medium_fetch = 0.0  # Bypass Medium Loop time gate
        self._last_slow_fetch = 0.0    # Bypass Slow Loop time gate
        await self.async_refresh()     # Trigger immediate data refresh

    async def _async_update_data(self) -> Dict[str, Any]:
        """Fetch consolidated data from BYD cloud using multi-rate loops."""
        now = sys_time.time()
        
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

        # 2. Medium Loop (daily energy totals, eeprom, cell diagnostics)
        do_medium = (self.data is None) or (now - self._last_medium_fetch >= self.medium_polling_interval)
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

        # 3. Slow Loop (static installation info, grid regulatory standards, available OTA firmware)
        do_slow = (self.data is None) or (now - self._last_slow_fetch >= self.slow_polling_interval)
        if do_slow:
            if self._bms_type is None:
                try:
                    self._bms_type = await self.client.get_bms_type(self.pid) or "4"
                except Exception:
                    self._bms_type = "4"

            pcs_model = "Power-Box SH5K"
            if self.data and "pcs" in self.data:
                pcs_items = self.data.get("pcs", [])
                if pcs_items and isinstance(pcs_items, list):
                    pcs_model = str(pcs_items[0].get("pcsType", "Power-Box SH5K")).strip()

            tasks.update({
                "base_settings": self.client.get_device_base_settings(self.product_type, self.pid),
                "grid_settings": self.client.get_device_grid_settings(self.product_type, self.pid),
                "latest_versions": self.client.get_all_latest_versions("lixia", pcs_model, self._bms_type),
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
                
                data["bms_type"] = self._bms_type

                # Set default/known current versions for BMS and Wifi Stick locally
                data["bms_current_version"] = "V1.9.0"
                data["f527_current_version"] = "V1.2.47"
                data["wifi_module_current_version"] = "V1.1.29"

                # Set default latest versions and sizes
                data["pcs_latest_version"] = None
                data["pcs_latest_size"] = None
                data["dsp1_latest_version"] = None
                data["dsp1_latest_size"] = None
                data["dsp2_latest_version"] = None
                data["dsp2_latest_size"] = None
                data["bms_latest_version"] = None
                data["bms_latest_size"] = None
                data["f527_latest_version"] = None
                data["f527_latest_size"] = None
                data["wifi_module_latest_version"] = None
                data["wifi_module_latest_size"] = None

                if "latest_versions" in task_results and not isinstance(task_results["latest_versions"], Exception):
                    lv_res = task_results["latest_versions"] or {}
                    version_list = lv_res.get("DeviceVersionList", [])
                    if isinstance(version_list, list):
                        for item in version_list:
                            dtype = item.get("DeviceType")
                            lver = item.get("LatestVersion")
                            fsize = item.get("FileSize")
                            
                            fsize_str = None
                            if fsize is not None:
                                try:
                                    fsize_val = float(fsize)
                                    if fsize_val >= 1024 * 1024:
                                        fsize_str = f"{fsize_val / (1024*1024):.2f} MB"
                                    else:
                                        fsize_str = f"{fsize_val / 1024:.2f} KB"
                                except (ValueError, TypeError):
                                    fsize_str = f"{fsize} bytes"

                            if dtype == "arm":
                                data["pcs_latest_version"] = lver
                                data["pcs_latest_size"] = fsize_str
                            elif dtype == "dsp1":
                                data["dsp1_latest_version"] = lver
                                data["dsp1_latest_size"] = fsize_str
                            elif dtype == "dsp2":
                                data["dsp2_latest_version"] = lver
                                data["dsp2_latest_size"] = fsize_str
                            elif dtype == "bms":
                                data["bms_latest_version"] = lver
                                data["bms_latest_size"] = fsize_str
                            elif dtype == "f527":
                                data["f527_latest_version"] = lver
                                data["f527_latest_size"] = fsize_str
                            elif dtype == "wifiModule":
                                data["wifi_module_latest_version"] = lver
                                data["wifi_module_latest_size"] = fsize_str

                self._last_slow_fetch = now
                # Trigger firmware update check and update native Home Assistant sidebar notifications
                self._async_check_firmware_notifications(data)

            return data

        except ConfigEntryAuthFailed:
            raise
        except BydEnergyAuthError as err:
            raise ConfigEntryAuthFailed("BYD Energy session expired") from err
        except BydEnergyApiClientError as err:
            raise UpdateFailed(f"Error communicating with BYD Energy API: {err}") from err
        except Exception as err:
            raise UpdateFailed(f"Unexpected error updating BYD Energy: {err}") from err

    def _is_newer(self, installed: Optional[str], latest: Optional[str]) -> bool:
        """Return True if latest version is strictly newer than installed version."""
        if not installed or not latest or latest == "unknown" or installed == "unknown":
            return False
        inst = str(installed).replace("V", "").replace("v", "").strip()
        lat = str(latest).replace("V", "").replace("v", "").strip()
        if inst == lat:
            return False
        try:
            inst_parts = [int(x) for x in re.findall(r"\d+", inst)]
            lat_parts = [int(x) for x in re.findall(r"\d+", lat)]
            for i in range(max(len(inst_parts), len(lat_parts))):
                inst_val = inst_parts[i] if i < len(inst_parts) else 0
                lat_val = lat_parts[i] if i < len(lat_parts) else 0
                if lat_val > inst_val:
                    return True
                if lat_val < inst_val:
                    return False
        except Exception:
            pass
        return False

    def _async_check_firmware_notifications(self, data: Dict[str, Any]) -> None:
        """Aggregates and triggers/dismisses HA persistent notifications for pending firmware upgrades."""
        # 1. Fetch current and latest versions from cache
        arm_curr = data.get("sensors", {}).get("armV", "V326")
        arm_latest = data.get("pcs_latest_version")
        arm_size = data.get("pcs_latest_size")

        dsp1_curr = data.get("sensors", {}).get("mdspV", "V505")
        dsp1_latest = data.get("dsp1_latest_version")
        dsp1_size = data.get("dsp1_latest_size")

        dsp2_curr = data.get("sensors", {}).get("fdspV", "V103")
        dsp2_latest = data.get("dsp2_latest_version")
        dsp2_size = data.get("dsp2_latest_size")

        bms_curr = data.get("bms_current_version")
        bms_latest = data.get("bms_latest_version")
        bms_size = data.get("bms_latest_size")

        mcu1_curr = data.get("wifi_module_current_version")
        mcu1_latest = data.get("wifi_module_latest_version")
        mcu1_size = data.get("wifi_module_latest_size")

        mcu2_curr = data.get("f527_current_version")
        mcu2_latest = data.get("f527_latest_version")
        mcu2_size = data.get("f527_latest_size")

        # 2. Check pending updates (only for active, non-null elements)
        updates = []
        
        # Inverter Subsystem
        inverter_updates = []
        if arm_curr and arm_latest and self._is_newer(arm_curr, arm_latest):
            inverter_updates.append(f"*   **ARM**: `{arm_curr}` ➔ **`{arm_latest}`** ({arm_size or 'unknown size'})")
        if dsp1_curr and dsp1_latest and self._is_newer(dsp1_curr, dsp1_latest):
            inverter_updates.append(f"*   **DSP1**: `{dsp1_curr}` ➔ **`{dsp1_latest}`** ({dsp1_size or 'unknown size'})")
        if dsp2_curr and dsp2_latest and self._is_newer(dsp2_curr, dsp2_latest):
            inverter_updates.append(f"*   **DSP2**: `{dsp2_curr}` ➔ **`{dsp2_latest}`** ({dsp2_size or 'unknown size'})")

        if inverter_updates:
            updates.append(f"### 🎛️ Power-Box SH5K (Inverter)\n" + "\n".join(inverter_updates))

        # Battery Subsystem (skip if battery is not present)
        if bms_curr and bms_latest and self._is_newer(bms_curr, bms_latest):
            updates.append(f"### 🔋 HVE Tower (Battery BMS)\n*   **BMS**: `{bms_curr}` ➔ **`{bms_latest}`** ({bms_size or 'unknown size'})")

        # WiFi/LAN Module Subsystem (skip if WiFi info is missing)
        wifi_updates = []
        if mcu1_curr and mcu1_latest and self._is_newer(mcu1_curr, mcu1_latest):
            wifi_updates.append(f"*   **MCU 1** (wifiModule): `{mcu1_curr}` ➔ **`{mcu1_latest}`** ({mcu1_size or 'unknown size'})")
        if mcu2_curr and mcu2_latest and self._is_newer(mcu2_curr, mcu2_latest):
            wifi_updates.append(f"*   **MCU 2** (f527): `{mcu2_curr}` ➔ **`{mcu2_latest}`** ({mcu2_size or 'unknown size'})")

        if wifi_updates:
            updates.append(f"### 📶 Smart WiFi/LAN Module\n" + "\n".join(wifi_updates))

        notification_id = f"byd_energy_{self.pid}_update"

        # 3. Trigger or self-heal dismiss
        if updates:
            msg_body = (
                f"New firmware upgrades are available for your **BYD Solar Installation ({self.pid})**!\n\n"
                + "\n\n".join(updates)
            )
            self.hass.async_create_task(
                self.hass.services.async_call(
                    "persistent_notification",
                    "create",
                    {
                        "title": f"BYD Firmware Update Available ({self.pid})",
                        "message": msg_body,
                        "notification_id": notification_id,
                    }
                )
            )
            _LOGGER.info("Consolidated firmware update notification issued for %s", self.pid)
        else:
            # Self-heal: automatically dismiss notification if all are up-to-date
            self.hass.async_create_task(
                self.hass.services.async_call(
                    "persistent_notification",
                    "dismiss",
                    {
                        "notification_id": notification_id,
                    }
                )
            )
