"""Sensor platform for BYD Energy integration."""
import logging
from typing import Any, Dict, Optional

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import BMS_TYPE_MAP, DOMAIN, SENSOR_DEFINITIONS
from .__init__ import BydEnergyDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up BYD Energy sensor platform from a config entry."""
    coordinator: BydEnergyDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    sensors = []
    for key, (name, device_class, state_class, unit, icon) in SENSOR_DEFINITIONS.items():
        sensors.append(BydEnergySensor(coordinator, key, name, device_class, state_class, unit, icon))

    async_add_entities(sensors)


class BydEnergySensor(CoordinatorEntity[BydEnergyDataUpdateCoordinator], SensorEntity):
    """Representation of a BYD Energy sensor."""

    def __init__(
        self,
        coordinator: BydEnergyDataUpdateCoordinator,
        key: str,
        name: str,
        device_class: Optional[str],
        state_class: Optional[str],
        unit: Optional[str],
        icon: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._key = key
        self._attr_has_entity_name = True
        self._attr_name = name
        self._attr_unique_id = f"{coordinator.pid}_{key}"
        self._attr_device_class = device_class
        self._attr_state_class = state_class
        self._attr_native_unit_of_measurement = unit
        self._attr_icon = icon

    @property
    def native_value(self) -> Any:
        """Return native value of sensor."""
        data = self.coordinator.data
        if not data:
            return None

        val = None
        if self._key in data.get("today_ele", {}):
            val = data["today_ele"].get(self._key)
        elif self._key in data.get("total_ele", {}):
            val = data["total_ele"].get(self._key)
        elif self._key in data.get("pv_realtimes", {}):
            val = data["pv_realtimes"].get(self._key)
        elif self._key in data.get("pv_max_power", {}):
            val = data["pv_max_power"].get(self._key)
        elif self._key in data.get("sensors", {}):
            val = data["sensors"].get(self._key)
        elif self._key == "qaTime":
            val = data.get("base_settings", {}).get("qaTime")
        elif self._key == "grid_regulation":
            val = data.get("grid_settings", {}).get("Standard")
        elif self._key == "grid_country":
            val = data.get("grid_settings", {}).get("Nation")
        elif self._key in [
            "bms_current_version", "bms_latest_version",
            "pcs_latest_version", "dsp1_latest_version", "dsp2_latest_version",
            "f527_current_version", "f527_latest_version",
            "wifi_module_current_version", "wifi_module_latest_version"
        ]:
            val = data.get(self._key)

        if val is None:
            return None

        # Format specific floating/numeric types
        try:
            if self._attr_native_unit_of_measurement in ["W", "kW", "V", "A", "kWh", "Ah", "%", "°C", "mV"]:
                num_val = float(val)
                if self._key in ["me1Pow", "battPow"]:
                    num_val = -num_val
                return round(num_val, 2)
            return str(val).strip()
        except (ValueError, TypeError):
            return str(val).strip()

    @property
    def extra_state_attributes(self) -> Optional[Dict[str, Any]]:
        """Return entity-specific state attributes."""
        if self._key in [
            "bms_latest_version", "pcs_latest_version", 
            "dsp1_latest_version", "dsp2_latest_version", 
            "f527_latest_version", "wifi_module_latest_version"
        ]:
            size_key = self._key.replace("latest_version", "latest_size")
            if self.coordinator.data:
                size_val = self.coordinator.data.get(size_key)
                if size_val:
                    return {"file_size": size_val}
        return None

    @property
    def device_info(self) -> DeviceInfo:
        """Group sensor into specific hardware device."""
        pid = self.coordinator.pid
        sensors = self.coordinator.data.get("sensors", {}) if self.coordinator.data else {}

        if self._key in ["me1Pow", "elecDailyBuy", "elecDailySale", "elecTotalBuy", "elecTotalSale"]:
            return DeviceInfo(
                identifiers={(DOMAIN, f"{pid}_meter")},
                name=f"BYD Grid Meter ({pid})",
                manufacturer="Chint / BYD",
                model="DDSU666 Smart Meter",
            )

        battery_keys = [
            "battPow", "sysVol", "sysCur", "soc", "soh", "remCap", "fulCap", "degCap",
            "acVol", "adcVol", "acCur", "adcCur", "paraNum", "packNum",
            "pcsCsta", "intV", "extV", "curr", "maxSV", "minSV", "maxSTem", "minST",
            "avgTmp", "loopNum", "bmsDailyCharge", "bmsDailyDisCharge", "bmsTotalCharge",
            "bmsTotalDisCharge", "bms_current_version", "bms_latest_version"
        ]
        if self._key in battery_keys:
            bms_code = str(sensors.get("bmsType", "4"))
            model_name = BMS_TYPE_MAP.get(bms_code, f"Battery-Box HVE (Type {bms_code})")
            return DeviceInfo(
                identifiers={(DOMAIN, f"{pid}_battery")},
                name=f"BYD Battery Tower ({pid})",
                manufacturer="BYD",
                model=model_name,
            )

        # Default to Inverter (PCS) device
        inverter_model = str(sensors.get("dmodname", "Power-Box Inverter")).strip()
        mdsp = str(sensors.get("mdspV", "")).strip()
        fdsp = str(sensors.get("fdspV", "")).strip()
        arm = str(sensors.get("armV", "")).strip()
        sw_ver = f"{mdsp}.{fdsp}.{arm}".strip(".") if mdsp or arm else "V326"
        return DeviceInfo(
            identifiers={(DOMAIN, f"{pid}_inverter")},
            name=f"BYD Inverter ({pid})",
            manufacturer="BYD",
            model=inverter_model,
            sw_version=sw_ver,
        )
