"""Number platform for BYD Energy integration."""
import logging
from typing import Any, Dict, Optional

from homeassistant.components.number import NumberEntity, NumberDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfPower
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .__init__ import BydEnergyDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

NUMBER_DEFINITIONS = {
    "minGrEle": ("Feed-in Stop SOC", NumberDeviceClass.BATTERY, PERCENTAGE, 10, 100, 5, "mdi:battery-minus"),
    "minSoc": ("Battery Discharge Stop Floor", NumberDeviceClass.BATTERY, PERCENTAGE, 10, 100, 5, "mdi:battery-sync"),
    "maxSoc": ("Battery Charge Stop Ceiling", NumberDeviceClass.BATTERY, PERCENTAGE, 10, 100, 5, "mdi:battery-plus"),
    "pv1MaxPower": ("PV1 String Peak Power Limit", NumberDeviceClass.POWER, UnitOfPower.WATT, 0, 10000, 10, "mdi:solar-power"),
    "pv2MaxPower": ("PV2 String Peak Power Limit", NumberDeviceClass.POWER, UnitOfPower.WATT, 0, 10000, 10, "mdi:solar-power"),
}


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up BYD Energy number platform."""
    coordinator: BydEnergyDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    numbers = []
    for key, (name, device_class, unit, min_val, max_val, step, icon) in NUMBER_DEFINITIONS.items():
        numbers.append(BydEnergyNumber(coordinator, key, name, device_class, unit, min_val, max_val, step, icon))

    async_add_entities(numbers)


class BydEnergyNumber(CoordinatorEntity[BydEnergyDataUpdateCoordinator], NumberEntity):
    """Representation of a BYD Energy configuration number parameter."""

    def __init__(
        self,
        coordinator: BydEnergyDataUpdateCoordinator,
        key: str,
        name: str,
        device_class: Optional[NumberDeviceClass],
        unit: str,
        min_val: float,
        max_val: float,
        step: float,
        icon: str,
    ) -> None:
        """Initialize the number entity."""
        super().__init__(coordinator)
        self._key = key
        self._attr_has_entity_name = True
        self._attr_name = name
        self._attr_unique_id = f"{coordinator.pid}_{key}"
        self._attr_device_class = device_class
        self._attr_native_unit_of_measurement = unit
        self._min_val = min_val
        self._max_val = max_val
        self._attr_native_step = step
        self._attr_icon = icon

    @property
    def native_value(self) -> Optional[float]:
        """Return the current value."""
        if not self.coordinator.data:
            return None

        val = None
        if self._key in ["pv1MaxPower", "pv2MaxPower"]:
            val = self.coordinator.data.get("pv_max_power", {}).get(self._key)
        else:
            val = self.coordinator.data.get("eeprom_settings", {}).get(self._key)

        try:
            if val is not None:
                return float(val)
        except (ValueError, TypeError):
            pass
        return None

    @property
    def native_min_value(self) -> float:
        """Return dynamic minimum allowed value enforcing cross-register bounds."""
        if not self.coordinator.data or self._key in ["pv1MaxPower", "pv2MaxPower"]:
            return self._min_val

        eeprom = self.coordinator.data.get("eeprom_settings", {})
        try:
            if self._key == "minGrEle":
                # Feed-in Stop SOC lower bound is the Battery Discharge Stop Floor (minSoc)
                return float(eeprom.get("minSoc", self._min_val))
            elif self._key == "maxSoc":
                # Battery Charge Stop Ceiling lower bound is the Feed-in Stop SOC (minGrEle)
                return float(eeprom.get("minGrEle", self._min_val))
        except (ValueError, TypeError):
            pass
        return self._min_val

    @property
    def native_max_value(self) -> float:
        """Return dynamic maximum allowed value enforcing cross-register bounds."""
        if not self.coordinator.data or self._key in ["pv1MaxPower", "pv2MaxPower"]:
            return self._max_val

        eeprom = self.coordinator.data.get("eeprom_settings", {})
        try:
            if self._key == "minGrEle":
                # Feed-in Stop SOC upper bound is the Battery Charge Stop Ceiling (maxSoc)
                return float(eeprom.get("maxSoc", self._max_val))
            elif self._key == "minSoc":
                # Battery Discharge Stop Floor upper bound is the Feed-in Stop SOC (minGrEle)
                return float(eeprom.get("minGrEle", self._max_val))
        except (ValueError, TypeError):
            pass
        return self._max_val

    async def async_set_native_value(self, value: float) -> None:
        """Set new value with dynamic boundary safety guardrails."""
        int_val = int(value)
        
        # Pre-write range check safety safeguard
        if int_val < self.native_min_value or int_val > self.native_max_value:
            _LOGGER.error(
                "Value %d for %s is outside dynamic safe bounds [%d, %d]",
                int_val, self._attr_name, self.native_min_value, self.native_max_value
            )
            return

        success = False

        if self._key == "pv1MaxPower":
            success = await self.coordinator.client.update_pv_max_power(self.coordinator.pid, 1, int_val)
            if success and self.coordinator.data and "pv_max_power" in self.coordinator.data:
                self.coordinator.data["pv_max_power"]["pv1MaxPower"] = int_val
        elif self._key == "pv2MaxPower":
            success = await self.coordinator.client.update_pv_max_power(self.coordinator.pid, 2, int_val)
            if success and self.coordinator.data and "pv_max_power" in self.coordinator.data:
                self.coordinator.data["pv_max_power"]["pv2MaxPower"] = int_val
        else:
            # e.g. minGrEle, minSoc, maxSoc
            # NOTE: These are physically mutable hardware registers on the device.
            success = await self.coordinator.client.update_device_setting(self.coordinator.pid, self._key, int_val)
            if success and self.coordinator.data and "eeprom_settings" in self.coordinator.data:
                self.coordinator.data["eeprom_settings"][self._key] = str(int_val)

        if success:
            self.async_write_ha_state()
            self.coordinator.force_medium_refresh_soon()

    @property
    def device_info(self) -> DeviceInfo:
        """Attach number entity to Inverter (PCS) device."""
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
