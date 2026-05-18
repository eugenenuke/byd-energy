"""Text platform for BYD Energy integration."""
import logging
import re
from typing import Any, Dict, Optional

from homeassistant.components.text import TextEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .__init__ import BydEnergyDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

TEXT_DEFINITIONS = {
    "cstaT1": ("Forced Grid Charge Slot 1 Start (Backup)", "mdi:clock-start"),
    "cendT1": ("Forced Grid Charge Slot 1 End (Backup)", "mdi:clock-end"),
    "cstaT2": ("Forced Grid Charge Slot 2 Start (Backup)", "mdi:clock-start"),
    "cendT2": ("Forced Grid Charge Slot 2 End (Backup)", "mdi:clock-end"),
    "dcstaT1": ("Grid Export Discharge Slot 1 Start (Feed-in)", "mdi:clock-start"),
    "dcendT1": ("Grid Export Discharge Slot 1 End (Feed-in)", "mdi:clock-end"),
    "dcstaT2": ("Grid Export Discharge Slot 2 Start (Feed-in)", "mdi:clock-start"),
    "dcendT2": ("Grid Export Discharge Slot 2 End (Feed-in)", "mdi:clock-end"),
}


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up BYD Energy text platform."""
    coordinator: BydEnergyDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    texts = []
    for key, (name, icon) in TEXT_DEFINITIONS.items():
        texts.append(BydEnergyText(coordinator, key, name, icon))

    async_add_entities(texts)


class BydEnergyText(CoordinatorEntity[BydEnergyDataUpdateCoordinator], TextEntity):
    """Representation of a BYD Energy time window text input."""

    def __init__(
        self, coordinator: BydEnergyDataUpdateCoordinator, key: str, name: str, icon: str
    ) -> None:
        """Initialize the text entity."""
        super().__init__(coordinator)
        self._key = key
        self._attr_has_entity_name = True
        self._attr_name = name
        self._attr_unique_id = f"{coordinator.pid}_{key}"
        self._attr_icon = icon

    @property
    def native_value(self) -> Optional[str]:
        """Return current time window string."""
        if not self.coordinator.data:
            return None
        val = self.coordinator.data.get("eeprom_settings", {}).get(self._key)
        if val is not None:
            return str(val).replace("Z", "").strip()
        return None

    async def async_set_value(self, value: str) -> None:
        """Update time window string."""
        clean_val = value.strip().replace("Z", "")
        if not re.match(r"^\d{2}:\d{2}$", clean_val):
            _LOGGER.error("Invalid time string format for %s: %s (must be HH:MM)", self._key, value)
            return

        api_val = f"{clean_val}Z"
        success = await self.coordinator.client.update_device_setting(self.coordinator.pid, self._key, api_val)
        if success:
            if self.coordinator.data and "eeprom_settings" in self.coordinator.data:
                self.coordinator.data["eeprom_settings"][self._key] = api_val
            self.async_write_ha_state()

    @property
    def device_info(self) -> DeviceInfo:
        """Attach text entity to Inverter (PCS) device."""
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
