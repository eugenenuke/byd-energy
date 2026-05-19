"""Binary sensor platform for BYD Energy integration."""
import logging
import re
from typing import Any, Dict, Optional

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
    async_add_entities([
        BydEnergyClippingBinarySensor(coordinator),
        BydEnergyFirmwareUpdateAvailable(coordinator),
    ])


def is_newer_version(installed: Optional[str], latest: Optional[str]) -> bool:
    """Return True if latest version is strictly newer than installed version."""
    if not installed or not latest:
        return False
    inst_str = str(installed).replace("V", "").replace("v", "").strip()
    lat_str = str(latest).replace("V", "").replace("v", "").strip()
    if inst_str == lat_str:
        return False

    try:
        # Parse list of all numbers: "1.2.47" -> [1, 2, 47]
        inst_parts = [int(x) for x in re.findall(r"\d+", inst_str)]
        lat_parts = [int(x) for x in re.findall(r"\d+", lat_str)]
        
        # Digit-by-digit comparison
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


class BydEnergyFirmwareUpdateAvailable(CoordinatorEntity[BydEnergyDataUpdateCoordinator], BinarySensorEntity):
    """Representation of a unified BYD Inverter & Battery firmware update available binary sensor."""

    def __init__(self, coordinator: BydEnergyDataUpdateCoordinator) -> None:
        """Initialize the update binary sensor."""
        super().__init__(coordinator)
        self._attr_has_entity_name = True
        self._attr_name = "Firmware Update Available"
        self._attr_unique_id = f"{coordinator.pid}_firmware_update_available"
        self._attr_device_class = BinarySensorDeviceClass.UPDATE
        self._attr_icon = "mdi:cellphone-arrow-down"

    @property
    def is_on(self) -> bool:
        """Return True if ANY tracked component has an update available."""
        data = self.coordinator.data
        if not data:
            return False

        # Track versions maps
        arm_curr = data.get("sensors", {}).get("armV", "V326")
        arm_latest = data.get("pcs_latest_version")
        
        dsp1_curr = data.get("sensors", {}).get("mdspV", "V505")
        dsp1_latest = data.get("dsp1_latest_version")

        dsp2_curr = data.get("sensors", {}).get("fdspV", "V103")
        dsp2_latest = data.get("dsp2_latest_version")

        bms_curr = data.get("bms_current_version", "V1.9.0")
        bms_latest = data.get("bms_latest_version")

        mcu1_curr = data.get("wifi_module_current_version", "V1.1.29")
        mcu1_latest = data.get("wifi_module_latest_version")

        mcu2_curr = data.get("f527_current_version", "V1.2.47")
        mcu2_latest = data.get("f527_latest_version")

        return (
            is_newer_version(arm_curr, arm_latest)
            or is_newer_version(dsp1_curr, dsp1_latest)
            or is_newer_version(dsp2_curr, dsp2_latest)
            or is_newer_version(bms_curr, bms_latest)
            or is_newer_version(mcu1_curr, mcu1_latest)
            or is_newer_version(mcu2_curr, mcu2_latest)
        )

    @property
    def extra_state_attributes(self) -> Optional[Dict[str, Any]]:
        """Expose individual component update availability details in entity attributes."""
        data = self.coordinator.data
        if not data:
            return None

        arm_curr = data.get("sensors", {}).get("armV", "V326")
        arm_latest = data.get("pcs_latest_version")
        
        dsp1_curr = data.get("sensors", {}).get("mdspV", "V505")
        dsp1_latest = data.get("dsp1_latest_version")

        dsp2_curr = data.get("sensors", {}).get("fdspV", "V103")
        dsp2_latest = data.get("dsp2_latest_version")

        bms_curr = data.get("bms_current_version", "V1.9.0")
        bms_latest = data.get("bms_latest_version")

        mcu1_curr = data.get("wifi_module_current_version", "V1.1.29")
        mcu1_latest = data.get("wifi_module_latest_version")

        mcu2_curr = data.get("f527_current_version", "V1.2.47")
        mcu2_latest = data.get("f527_latest_version")

        return {
            "arm_update_available": is_newer_version(arm_curr, arm_latest),
            "dsp1_update_available": is_newer_version(dsp1_curr, dsp1_latest),
            "dsp2_update_available": is_newer_version(dsp2_curr, dsp2_latest),
            "bms_update_available": is_newer_version(bms_curr, bms_latest),
            "wifi_mcu1_update_available": is_newer_version(mcu1_curr, mcu1_latest),
            "wifi_mcu2_update_available": is_newer_version(mcu2_curr, mcu2_latest),
        }

    @property
    def device_info(self) -> DeviceInfo:
        """Attach update binary sensor to Inverter (PCS) device."""
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
