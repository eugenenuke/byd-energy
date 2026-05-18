"""Constants for the BYD Energy custom component."""
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.const import (
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfPower,
    UnitOfTemperature,
    PERCENTAGE,
)

DOMAIN = "byd_energy"
BASE_URL = "https://energyhousehold.bydessys.com"

CONF_PID = "pid"
CONF_PRODUCT_TYPE = "product_type"
CONF_POLLING_INTERVAL = "polling_interval"
DEFAULT_POLLING_INTERVAL = 15
CONF_MEDIUM_POLLING_INTERVAL = "medium_polling_interval"
DEFAULT_MEDIUM_POLLING_INTERVAL = 300
CONF_SLOW_POLLING_INTERVAL = "slow_polling_interval"
DEFAULT_SLOW_POLLING_INTERVAL = 43200

HARDCODED_IV = "secret&aes&2024&"

# Hardware series decodes
BMS_TYPE_MAP = {
    "1": "Battery Box-LV5.0",
    "2": "Battery-Box HVB",
    "3": "Battery-Box LV5.0+",
    "4": "Battery-Box HVE",
    "5": "Battery-Box HVS+",
    "6": "Battery-Box HVM+",
}

ONLINE_STATE_MAP = {
    0: "Offline",
    1: "Online",
    2: "Fault",
}

WORK_MODE_MAP = {
    "0": "Self-use",
    "1": "Feed-in Priority",
    "2": "Backup",
}

# Sensor definitions: (name, device_class, state_class, unit, icon)
SENSOR_DEFINITIONS = {
    # --- Realtime sys ---
    "pvPow": ("Total PV Power", SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT, UnitOfPower.WATT, "mdi:solar-power"),
    "lPow": ("Household Load Power", SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT, UnitOfPower.WATT, "mdi:home-lightning-bolt"),
    "battPow": ("Battery Active Power", SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT, UnitOfPower.WATT, "mdi:battery-charging-high"),
    "me1Pow": ("Grid Meter Power", SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT, UnitOfPower.WATT, "mdi:transmission-tower"),
    "pvtec": ("Total PV Generation", SensorDeviceClass.ENERGY, SensorStateClass.TOTAL_INCREASING, UnitOfEnergy.KILO_WATT_HOUR, "mdi:solar-power"),
    "pvdec": ("Daily PV Generation", SensorDeviceClass.ENERGY, SensorStateClass.TOTAL_INCREASING, UnitOfEnergy.KILO_WATT_HOUR, "mdi:solar-power"),
    "tec": ("Total Household Consumption", SensorDeviceClass.ENERGY, SensorStateClass.TOTAL_INCREASING, UnitOfEnergy.KILO_WATT_HOUR, "mdi:home-lightning-bolt"),
    "dec": ("Daily Household Consumption", SensorDeviceClass.ENERGY, SensorStateClass.TOTAL_INCREASING, UnitOfEnergy.KILO_WATT_HOUR, "mdi:home-lightning-bolt"),

    # --- Realtime pcs ---
    "gVR": ("Grid Voltage (Phase R)", SensorDeviceClass.VOLTAGE, SensorStateClass.MEASUREMENT, UnitOfElectricPotential.VOLT, "mdi:sine-wave"),
    "gCurrR": ("Grid Current (Phase R)", SensorDeviceClass.CURRENT, SensorStateClass.MEASUREMENT, UnitOfElectricCurrent.AMPERE, "mdi:current-ac"),
    "envTmp": ("Inverter Ambient Temperature", SensorDeviceClass.TEMPERATURE, SensorStateClass.MEASUREMENT, UnitOfTemperature.CELSIUS, "mdi:thermometer"),
    "mdspV": ("Main DSP Version", None, None, None, "mdi:chip"),
    "fdspV": ("Slave DSP Version", None, None, None, "mdi:chip"),
    "armV": ("ARM Version", None, None, None, "mdi:chip"),
    "dmodname": ("Inverter Model", None, None, None, "mdi:information"),
    "devCap": ("Inverter Rated Power", SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT, UnitOfPower.WATT, "mdi:flash"),
    "runsta": ("Inverter Operation Status", None, None, None, "mdi:state-machine"),
    "ogVR": ("Off-grid Voltage (Phase R)", SensorDeviceClass.VOLTAGE, SensorStateClass.MEASUREMENT, UnitOfElectricPotential.VOLT, "mdi:power-plug-off"),
    "ogCurrR": ("Off-grid Current (Phase R)", SensorDeviceClass.CURRENT, SensorStateClass.MEASUREMENT, UnitOfElectricCurrent.AMPERE, "mdi:power-plug-off"),
    "ogPowR": ("Off-grid Power (Phase R)", SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT, UnitOfPower.WATT, "mdi:power-plug-off"),

    # --- Realtime batterySystem ---
    "sysVol": ("Battery System Voltage", SensorDeviceClass.VOLTAGE, SensorStateClass.MEASUREMENT, UnitOfElectricPotential.VOLT, "mdi:battery"),
    "sysCur": ("Battery System Current", SensorDeviceClass.CURRENT, SensorStateClass.MEASUREMENT, UnitOfElectricCurrent.AMPERE, "mdi:current-dc"),
    "soc": ("Battery State of Charge", SensorDeviceClass.BATTERY, SensorStateClass.MEASUREMENT, PERCENTAGE, "mdi:battery-high"),
    "soh": ("Battery State of Health", None, SensorStateClass.MEASUREMENT, PERCENTAGE, "mdi:heart-pulse"),
    "remCap": ("Battery Remaining Capacity", None, SensorStateClass.MEASUREMENT, "Ah", "mdi:battery-50"),
    "fulCap": ("Battery Full Capacity", None, SensorStateClass.MEASUREMENT, "Ah", "mdi:battery"),
    "degCap": ("Battery Design Capacity", None, SensorStateClass.MEASUREMENT, "Ah", "mdi:battery-check"),
    "acVol": ("Allowable Charge Voltage", SensorDeviceClass.VOLTAGE, SensorStateClass.MEASUREMENT, UnitOfElectricPotential.VOLT, "mdi:lightning-bolt"),
    "adcVol": ("Allowable Discharge Voltage", SensorDeviceClass.VOLTAGE, SensorStateClass.MEASUREMENT, UnitOfElectricPotential.VOLT, "mdi:lightning-bolt-outline"),
    "acCur": ("Allowable Charge Current", SensorDeviceClass.CURRENT, SensorStateClass.MEASUREMENT, UnitOfElectricCurrent.AMPERE, "mdi:current-dc"),
    "adcCur": ("Allowable Discharge Current", SensorDeviceClass.CURRENT, SensorStateClass.MEASUREMENT, UnitOfElectricCurrent.AMPERE, "mdi:current-dc"),
    "paraNum": ("Battery Tower Quantity", None, None, None, "mdi:server"),
    "packNum": ("Battery Module Quantity", None, None, None, "mdi:package-variant"),
    "pcsCsta": ("PCS Connection Status", None, None, None, "mdi:check-network"),

    # --- Realtime bms ---
    "intV": ("Internal Battery Voltage", SensorDeviceClass.VOLTAGE, SensorStateClass.MEASUREMENT, UnitOfElectricPotential.VOLT, "mdi:battery-positive"),
    "extV": ("External Battery Voltage", SensorDeviceClass.VOLTAGE, SensorStateClass.MEASUREMENT, UnitOfElectricPotential.VOLT, "mdi:battery"),
    "curr": ("BMS Total Current", SensorDeviceClass.CURRENT, SensorStateClass.MEASUREMENT, UnitOfElectricCurrent.AMPERE, "mdi:current-dc"),
    "maxSV": ("Max Cell Voltage", SensorDeviceClass.VOLTAGE, SensorStateClass.MEASUREMENT, "mV", "mdi:lightning-bolt"),
    "minSV": ("Min Cell Voltage", SensorDeviceClass.VOLTAGE, SensorStateClass.MEASUREMENT, "mV", "mdi:lightning-bolt-outline"),
    "maxSTem": ("Max Cell Temperature", SensorDeviceClass.TEMPERATURE, SensorStateClass.MEASUREMENT, UnitOfTemperature.CELSIUS, "mdi:thermometer-chevron-up"),
    "minST": ("Min Cell Temperature", SensorDeviceClass.TEMPERATURE, SensorStateClass.MEASUREMENT, UnitOfTemperature.CELSIUS, "mdi:thermometer-chevron-down"),
    "avgTmp": ("Avg Cell Temperature", SensorDeviceClass.TEMPERATURE, SensorStateClass.MEASUREMENT, UnitOfTemperature.CELSIUS, "mdi:thermometer"),
    "loopNum": ("Battery Cycle Count", None, SensorStateClass.TOTAL_INCREASING, None, "mdi:sync"),

    # --- PV Realtime ---
    "pv1vol": ("PV1 String Voltage", SensorDeviceClass.VOLTAGE, SensorStateClass.MEASUREMENT, UnitOfElectricPotential.VOLT, "mdi:solar-panel-large"),
    "pv2vol": ("PV2 String Voltage", SensorDeviceClass.VOLTAGE, SensorStateClass.MEASUREMENT, UnitOfElectricPotential.VOLT, "mdi:solar-panel-large"),
    "pv1cur": ("PV1 String Current", SensorDeviceClass.CURRENT, SensorStateClass.MEASUREMENT, UnitOfElectricCurrent.AMPERE, "mdi:current-dc"),
    "pv2cur": ("PV2 String Current", SensorDeviceClass.CURRENT, SensorStateClass.MEASUREMENT, UnitOfElectricCurrent.AMPERE, "mdi:current-dc"),
    "pv1Pow": ("PV1 String Active Power", SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT, UnitOfPower.WATT, "mdi:solar-power"),
    "pv2Pow": ("PV2 String Active Power", SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT, UnitOfPower.WATT, "mdi:solar-power"),
    "pv1MaxPower": ("PV1 String Peak Power", SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT, UnitOfPower.WATT, "mdi:solar-power"),
    "pv2MaxPower": ("PV2 String Peak Power", SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT, UnitOfPower.WATT, "mdi:solar-power"),

    # --- Daily/Total Stats ---
    "elecDailyBuy": ("Daily Grid Import", SensorDeviceClass.ENERGY, SensorStateClass.TOTAL_INCREASING, UnitOfEnergy.KILO_WATT_HOUR, "mdi:transmission-tower-import"),
    "elecDailySale": ("Daily Grid Export", SensorDeviceClass.ENERGY, SensorStateClass.TOTAL_INCREASING, UnitOfEnergy.KILO_WATT_HOUR, "mdi:transmission-tower-export"),
    "bmsDailyCharge": ("Daily Battery Charged Energy", SensorDeviceClass.ENERGY, SensorStateClass.TOTAL_INCREASING, UnitOfEnergy.KILO_WATT_HOUR, "mdi:battery-arrow-up"),
    "bmsDailyDisCharge": ("Daily Battery Discharged Energy", SensorDeviceClass.ENERGY, SensorStateClass.TOTAL_INCREASING, UnitOfEnergy.KILO_WATT_HOUR, "mdi:battery-arrow-down"),
    "elecTotalBuy": ("Lifetime Grid Import", SensorDeviceClass.ENERGY, SensorStateClass.TOTAL_INCREASING, UnitOfEnergy.KILO_WATT_HOUR, "mdi:transmission-tower-import"),
    "elecTotalSale": ("Lifetime Grid Export", SensorDeviceClass.ENERGY, SensorStateClass.TOTAL_INCREASING, UnitOfEnergy.KILO_WATT_HOUR, "mdi:transmission-tower-export"),
    "bmsTotalCharge": ("Lifetime Battery Charged Energy", SensorDeviceClass.ENERGY, SensorStateClass.TOTAL_INCREASING, UnitOfEnergy.KILO_WATT_HOUR, "mdi:battery-arrow-up"),
    "bmsTotalDisCharge": ("Lifetime Battery Discharged Energy", SensorDeviceClass.ENERGY, SensorStateClass.TOTAL_INCREASING, UnitOfEnergy.KILO_WATT_HOUR, "mdi:battery-arrow-down"),

    # --- Informational / Static slow ---
    "qaTime": ("Installation Date", None, None, None, "mdi:calendar-check"),
    "grid_regulation": ("Grid Standard Regulation", None, None, None, "mdi:handshake"),
    "grid_country": ("Grid Country Regulation", None, None, None, "mdi:earth"),
    "bms_current_version": ("BMS Firmware Version", None, None, None, "mdi:firmware"),
    "bms_latest_version": ("BMS Latest Available Firmware", None, None, None, "mdi:firmware"),
    "pcs_latest_version": ("Inverter Latest Available Firmware", None, None, None, "mdi:firmware"),
    "f527_current_version": ("WiFi Stick Firmware Version", None, None, None, "mdi:wifi-cog"),
    "f527_latest_version": ("WiFi Stick Latest Available Firmware", None, None, None, "mdi:wifi-cog"),
}
