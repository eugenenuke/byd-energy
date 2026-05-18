"""Switch platform for BYD Energy integration."""
import logging
from typing import Any, Dict, Optional

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, CONF_ENABLE_ADVANCED_CONTROLS
from .__init__ import BydEnergyDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

SWITCH_DEFINITIONS = {
    "remoteOnOff": ("Inverter Remote Power", "mdi:power"),
    "EPSEnable": ("Battery Storage System Enabled", "mdi:battery-charging"),
    "gcF1ena": ("Forced Grid Charge Slot 1 (Backup)", "mdi:timer-outline"),
    "gcF2ena": ("Forced Grid Charge Slot 2 (Backup)", "mdi:timer-outline"),
    "gdcF1ena": ("Grid Export Discharge Slot 1 (Feed-in)", "mdi:timer-outline"),
    "gdcF2ena": ("Grid Export Discharge Slot 2 (Feed-in)", "mdi:timer-outline"),
}


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up BYD Energy switch platform."""
    coordinator: BydEnergyDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    switches = []
    for key, (name, icon) in SWITCH_DEFINITIONS.items():
        switches.append(BydEnergySwitch(coordinator, key, name, icon))

    async_add_entities(switches)


class BydEnergySwitch(CoordinatorEntity[BydEnergyDataUpdateCoordinator], SwitchEntity):
    """Representation of a BYD Energy configuration switch."""

    def __init__(
        self, coordinator: BydEnergyDataUpdateCoordinator, key: str, name: str, icon: str
    ) -> None:
        """Initialize the switch."""
        super().__init__(coordinator)
        self._key = key
        self._attr_has_entity_name = True
        self._attr_name = name
        self._attr_unique_id = f"{coordinator.pid}_{key}"
        self._attr_icon = icon

    @property
    def is_on(self) -> bool:
        """Return true if the switch is on."""
        if not self.coordinator.data:
            return False
        val = self.coordinator.data.get("eeprom_settings", {}).get(self._key)
        return str(val).strip() == "1"

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        if self._key in ["remoteOnOff", "EPSEnable"]:
            if not self.coordinator._entry.options.get(CONF_ENABLE_ADVANCED_CONTROLS, False):
                _LOGGER.warning("Attempted to toggle advanced control %s while safety lock is active.", self._key)
                raise HomeAssistantError(
                    "Untested advanced write control is locked for safety. To enable, go to: "
                    "Settings -> Devices & Services -> BYD Energy -> Configure, check the unlock safety box, and submit."
                )

        success = await self.coordinator.client.update_device_setting(self.coordinator.pid, self._key, 1)
        if success:
            if self.coordinator.data and "eeprom_settings" in self.coordinator.data:
                self.coordinator.data["eeprom_settings"][self._key] = "1"
            self.async_write_ha_state()
            self.coordinator.force_medium_refresh_soon()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        if self._key in ["remoteOnOff", "EPSEnable"]:
            if not self.coordinator._entry.options.get(CONF_ENABLE_ADVANCED_CONTROLS, False):
                _LOGGER.warning("Attempted to toggle advanced control %s while safety lock is active.", self._key)
                raise HomeAssistantError(
                    "Untested advanced write control is locked for safety. To enable, go to: "
                    "Settings -> Devices & Services -> BYD Energy -> Configure, check the unlock safety box, and submit."
                )

        success = await self.coordinator.client.update_device_setting(self.coordinator.pid, self._key, 0)
        if success:
            if self.coordinator.data and "eeprom_settings" in self.coordinator.data:
                self.coordinator.data["eeprom_settings"][self._key] = "0"
            self.async_write_ha_state()
            self.coordinator.force_medium_refresh_soon()

    @property
    def device_info(self) -> DeviceInfo:
        """Attach switch to Inverter (PCS) device."""
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
