"""Binary sensor platform for BYD Energy integration."""
import logging
from typing import Optional

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .__init__ import BydEnergyDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up BYD Energy binary sensor platform from a config entry."""
    coordinator: BydEnergyDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([BydEnergyClippingBinarySensor(coordinator)])


class BydEnergyClippingBinarySensor(CoordinatorEntity[BydEnergyDataUpdateCoordinator], BinarySensorEntity):
    """Representation of a BYD Energy solar clipping alert binary sensor."""

    def __init__(self, coordinator: BydEnergyDataUpdateCoordinator) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        self._attr_has_entity_name = True
        self._attr_name = "Solar Clipping Alert"
        self._attr_unique_id = f"{coordinator.pid}_solar_clipping"
        self._attr_device_class = BinarySensorDeviceClass.PROBLEM
        self._attr_icon = "mdi:alert-outline"

    @property
    def is_on(self) -> bool:
        """Return True if solar clipping is actively occurring."""
        data = self.coordinator.data
        if not data:
            return False

        pv_rt = data.get("pv_realtimes", {})
        sys_rt = data.get("sensors", {})

        try:
            pv1vol = float(pv_rt.get("pv1vol", 0))
            pv1cur = float(pv_rt.get("pv1cur", 0))
            pv2vol = float(pv_rt.get("pv2vol", 0))
            pv2cur = float(pv_rt.get("pv2cur", 0))
            total_dc = (pv1vol * pv1cur) + (pv2vol * pv2cur)

            pv_pow_ac = float(sys_rt.get("pvPow", 0))

            # Primary clipping condition: Raw DC input exceeds 5kW while Inverter AC PV power is at conversion capacity
            if total_dc > 5000 and pv_pow_ac < 5100:
                return True
            return False
        except (ValueError, TypeError):
            return False

    @property
    def device_info(self) -> DeviceInfo:
        """Attach binary sensor to Inverter (PCS) device."""
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
