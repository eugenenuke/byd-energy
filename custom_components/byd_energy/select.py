"""Select platform for BYD Energy integration."""
import logging
import re
from typing import Any, Dict, Optional

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, WORK_MODE_MAP
from .__init__ import BydEnergyDataUpdateCoordinator
from .time import TIME_DEFINITIONS

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up BYD Energy select platform."""
    coordinator: BydEnergyDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = [BydEnergySelect(coordinator)]

    # Register Hour and Minute virtual split selects for each of the 8 time slots
    for key, (name, icon) in TIME_DEFINITIONS.items():
        entities.append(BydEnergyTimeSelect(coordinator, key, is_hour=True, name=f"{name} Hour", icon=icon))
        entities.append(BydEnergyTimeSelect(coordinator, key, is_hour=False, name=f"{name} Minute", icon=icon))

    async_add_entities(entities)


class BydEnergySelect(CoordinatorEntity[BydEnergyDataUpdateCoordinator], SelectEntity):
    """Representation of a BYD Inverter configuration select."""

    def __init__(self, coordinator: BydEnergyDataUpdateCoordinator) -> None:
        """Initialize the select entity."""
        super().__init__(coordinator)
        self._attr_has_entity_name = True
        self._attr_name = "Inverter Operating Mode"
        self._attr_unique_id = f"{coordinator.pid}_workMode"
        self._attr_icon = "mdi:cog"

    @property
    def options(self) -> list[str]:
        """Return set of selectable operating mode options."""
        return ["Self-use", "Feed-in Priority", "Backup"]

    @property
    def current_option(self) -> Optional[str]:
        """Return currently selected operating mode."""
        if not self.coordinator.data:
            return None
        val = self.coordinator.data.get("eeprom_settings", {}).get("workMode")
        if val is not None:
            return WORK_MODE_MAP.get(str(val).strip(), "Self-use")
        return None

    async def async_select_option(self, option: str) -> None:
        """Write selected operating mode to inverter EEPROM."""
        int_val = None
        for k, v in WORK_MODE_MAP.items():
            if v == option:
                int_val = int(k)
                break

        if int_val is None:
            _LOGGER.error("Invalid option chosen: %s", option)
            return

        success = await self.coordinator.client.update_device_setting(
            self.coordinator.pid, "workMode", int_val
        )

        if success:
            if self.coordinator.data and "eeprom_settings" in self.coordinator.data:
                self.coordinator.data["eeprom_settings"]["workMode"] = str(int_val)
            self.async_write_ha_state()
            self.coordinator.force_medium_refresh_soon()

    @property
    def device_info(self) -> DeviceInfo:
        """Group select entity under Inverter (PCS) device."""
        pid = self.coordinator.pid
        sensors = self.coordinator.data.get("sensors", {}) if self.coordinator.data else {}
        inverter_model = str(sensors.get("dmodname", "Power-Box Inverter")).strip()
        sw_ver = str(sensors.get("armV", "V326")).strip()
        return DeviceInfo(
            identifiers={(DOMAIN, f"{pid}_inverter")},
            name=f"BYD Inverter ({pid})",
            manufacturer="BYD",
            model=inverter_model,
            sw_version=sw_ver,
        )


class BydEnergyTimeSelect(CoordinatorEntity[BydEnergyDataUpdateCoordinator], SelectEntity):
    """Representation of a virtual Hour or Minute selector split for a BYD Inverter time slot."""

    def __init__(
        self,
        coordinator: BydEnergyDataUpdateCoordinator,
        key: str,
        is_hour: bool,
        name: str,
        icon: str,
    ) -> None:
        """Initialize the virtual time split select."""
        super().__init__(coordinator)
        self._key = key
        self._is_hour = is_hour
        self._attr_has_entity_name = True
        self._attr_name = name
        suffix = "hour" if is_hour else "minute"
        self._attr_unique_id = f"{coordinator.pid}_{key}_{suffix}"
        self._attr_icon = icon

    @property
    def options(self) -> list[str]:
        """Return dropdown selection list options."""
        if self._is_hour:
            # Hour dropdown options: 00 to 23
            return [f"{h:02d}" for h in range(24)]
        else:
            # Minute dropdown options: 00 to 55 in 5-minute steps
            return [f"{m:02d}" for m in range(0, 60, 5)]

    @property
    def current_option(self) -> Optional[str]:
        """Return currently selected option in dropdown."""
        if not self.coordinator.data:
            return None
        val = self.coordinator.data.get("eeprom_settings", {}).get(self._key)
        if val is not None:
            clean_val = str(val).replace("Z", "").strip() # e.g., "04:45"
            if re.match(r"^\d{2}:\d{2}$", clean_val):
                parts = clean_val.split(":")
                if self._is_hour:
                    return parts[0]
                else:
                    # Minute dropdown value (force/round to nearest 5-minute option if API returns odd minute)
                    try:
                        raw_min = int(parts[1])
                        rounded_min = round(raw_min / 5) * 5
                        if rounded_min >= 60:
                            rounded_min = 55
                        return f"{rounded_min:02d}"
                    except (ValueError, TypeError):
                        return parts[1]
        return None

    async def async_select_option(self, option: str) -> None:
        """Write the combined time string back to Inverter EEPROM registers."""
        if not self.coordinator.data:
            return

        # 1. Read current values from the cache as fallback defaults
        current_val = self.coordinator.data.get("eeprom_settings", {}).get(self._key)
        current_hour = "00"
        current_minute = "00"

        if current_val is not None:
            clean_val = str(current_val).replace("Z", "").strip()
            if re.match(r"^\d{2}:\d{2}$", clean_val):
                parts = clean_val.split(":")
                current_hour = parts[0]
                current_minute = parts[1]

        # 2. Combine the updated select value with the other cached half
        if self._is_hour:
            new_hour = option
            new_minute = current_minute
        else:
            new_hour = current_hour
            new_minute = option

        api_val = f"{new_hour}:{new_minute}Z"

        # 3. Perform single Cloud API setting write
        success = await self.coordinator.client.update_device_setting(self.coordinator.pid, self._key, api_val)
        if success:
            if self.coordinator.data and "eeprom_settings" in self.coordinator.data:
                self.coordinator.data["eeprom_settings"][self._key] = api_val
            self.async_write_ha_state()
            self.coordinator.force_medium_refresh_soon()

    @property
    def device_info(self) -> DeviceInfo:
        """Attach virtual select entity to Inverter (PCS) device."""
        pid = self.coordinator.pid
        sensors = self.coordinator.data.get("sensors", {}) if self.coordinator.data else {}
        inverter_model = str(sensors.get("dmodname", "Power-Box Inverter")).strip()
        sw_ver = str(sensors.get("armV", "V326")).strip()
        return DeviceInfo(
            identifiers={(DOMAIN, f"{pid}_inverter")},
            name=f"BYD Inverter ({pid})",
            manufacturer="BYD",
            model=inverter_model,
            sw_version=sw_ver,
        )
