"""Time platform for BYD Energy integration."""
import datetime
import logging
import re
from typing import Any, Dict, Optional

from homeassistant.components.time import TimeEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .__init__ import BydEnergyDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

TIME_DEFINITIONS = {
    "cstaT1": ("Forced Grid Charge Slot 1 Start (Backup)", "mdi:timer-play-outline"),
    "cendT1": ("Forced Grid Charge Slot 1 End (Backup)", "mdi:timer-stop-outline"),
    "cstaT2": ("Forced Grid Charge Slot 2 Start (Backup)", "mdi:timer-play-outline"),
    "cendT2": ("Forced Grid Charge Slot 2 End (Backup)", "mdi:timer-stop-outline"),
    "dcstaT1": ("Grid Export Discharge Slot 1 Start (Feed-in)", "mdi:timer-play-outline"),
    "dcendT1": ("Grid Export Discharge Slot 1 End (Feed-in)", "mdi:timer-stop-outline"),
    "dcstaT2": ("Grid Export Discharge Slot 2 Start (Feed-in)", "mdi:timer-play-outline"),
    "dcendT2": ("Grid Export Discharge Slot 2 End (Feed-in)", "mdi:timer-stop-outline"),
}


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up BYD Energy time platform."""
    coordinator: BydEnergyDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    time_entities = []
    for key, (name, icon) in TIME_DEFINITIONS.items():
        time_entities.append(BydEnergyTimeEntity(coordinator, key, name, icon))

    async_add_entities(time_entities)


class BydEnergyTimeEntity(CoordinatorEntity[BydEnergyDataUpdateCoordinator], TimeEntity):
    """Representation of a BYD Energy configuration time slot setting."""

    def __init__(
        self, coordinator: BydEnergyDataUpdateCoordinator, key: str, name: str, icon: str
    ) -> None:
        """Initialize the time entity."""
        super().__init__(coordinator)
        self._key = key
        self._attr_has_entity_name = True
        self._attr_name = name
        self._attr_unique_id = f"{coordinator.pid}_{key}"
        self._attr_icon = icon

    @property
    def native_value(self) -> Optional[datetime.time]:
        """Return current time of day value."""
        if not self.coordinator.data:
            return None
        val = self.coordinator.data.get("eeprom_settings", {}).get(self._key)
        if val is not None:
            clean_val = str(val).replace("Z", "").strip() # e.g., "04:45"
            if re.match(r"^\d{2}:\d{2}$", clean_val):
                try:
                    hour, minute = map(int, clean_val.split(":"))
                    return datetime.time(hour, minute)
                except (ValueError, TypeError):
                    pass
        return None

    async def async_set_value(self, value: datetime.time) -> None:
        """Update time slot value on device."""
        # Format datetime.time back to "HH:MMZ" string format expected by the API
        api_val = f"{value.hour:02d}:{value.minute:02d}Z"
        success = await self.coordinator.client.update_device_setting(self.coordinator.pid, self._key, api_val)
        if success:
            if self.coordinator.data and "eeprom_settings" in self.coordinator.data:
                self.coordinator.data["eeprom_settings"][self._key] = api_val
            self.async_write_ha_state()
            self.coordinator.force_medium_refresh_soon()

    @property
    def device_info(self) -> DeviceInfo:
        """Attach time entity to Inverter (PCS) device."""
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
