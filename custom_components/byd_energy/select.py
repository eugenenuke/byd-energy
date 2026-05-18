"""Select platform for BYD Energy integration."""
import logging
from typing import Any, Dict, Optional

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, WORK_MODE_MAP
from .__init__ import BydEnergyDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up BYD Energy select platform."""
    coordinator: BydEnergyDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities([BydEnergySelect(coordinator)])


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
        # Find key corresponding to the selected value string
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
            # Write-through caching to give instantaneous UI update
            if self.coordinator.data and "eeprom_settings" in self.coordinator.data:
                self.coordinator.data["eeprom_settings"]["workMode"] = str(int_val)
            self.async_write_ha_state()
            # Safety delayed cloud reload after 3 seconds
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
