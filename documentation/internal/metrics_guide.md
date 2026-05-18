# BYD Energy Home Assistant Integration - Parameters & Metrics Guide

This guide provides a technical reference mapping between the official **BYD Mobile Application**, the **Home Assistant (HA) custom component entities**, and the raw **hardware/cloud EEPROM registers**.

---

## ⏱️ Home Assistant Polling Loop Architecture

To optimize cloud API bandwidth and prevent IP throttling, the Home Assistant integration organizes telemetry fetching into a multi-rate scheduler.

The **Fast Loop** interval is configurable by the user during the integration setup flow, while the other loops execute at predefined elapsed-time intervals relative to it.

| Loop Name | Default Update Frequency | Configurable | Purpose & Fetched Metrics |
| :--- | :--- | :--- | :--- |
| **Fast** | `15 seconds` | **Yes** (Config Flow) | Highly dynamic electrical power flows, instantaneous SOC, and live clipping state. |
| **Medium** | `5 minutes` | No | Daily/lifetime accumulated energy values and mutable EEPROM registers. |
| **Slow** | `12 hours` | No | Static baseline specs, regional standards, and cloud OTA version checks. |
| **Static** | `Once on Startup` | N/A | Query once during config entry setup (e.g., Device Serial No. / PID). |
| **Write** | `On Demand` | N/A | Dispatched instantly on user interaction (e.g. sliding a value or toggling a switch). |

---

## 📱 Section-by-Section App Screen Mapping

### 1. Main Dashboard ("Overview" Tab)
The primary dashboard displays flow diagrams of real-time active power flows and historical daily energy totals.

| BYD Mobile App UI Element | HA Sensor / Control Name | Sensor Key / Register | HA Polling Loop | Description |
| :--- | :--- | :--- | :--- | :--- |
| **PV (kW)** | `Total PV Power` | `pvPow` | **Fast** | Instantaneous active solar generation power in kW. |
| **HVE (kW)** | `Battery Active Power` | `battPow` | **Fast** | Instantaneous battery active charge (+ W) or discharge (- W) power. |
| **HVE (%)** | `Battery State of Charge` | `soc` | **Fast** | Instantaneous State of Charge in percentage. |
| **Grid (kW)** | `Grid Meter Power` | `me1Pow` | **Fast** | Instantaneous smart meter power. Negative value indicates grid export/feed-in. |
| **Load (kW)** | `Household Load Power` | `lPow` | **Fast** | Total calculated household active consumption load. |
| **Daily Power Generation** | `Daily PV Generation` | `pvdec` | **Medium** | Daily PV solar energy accumulated generation in kWh. |
| **Daily Power Consumption** | `Daily Household Consumption` | `dec` | **Medium** | Daily household energy consumed in kWh. |
| **Daily Power Purchase** | `Daily Grid Import` | `elecDailyBuy` | **Medium** | Daily grid import energy accumulated in kWh. |
| **Daily Power Feed-In** | `Daily Grid Export` | `elecDailySale` | **Medium** | Daily grid export/feed-in energy accumulated in kWh. |

---

### 2. Inverter Configuration Screen ("Inverter")
Accessible via the device list. Exposes PCS operational telemetry and basic device info.

| BYD Mobile App UI Element | HA Sensor / Control Name | Sensor Key / Register | HA Polling Loop | Description |
| :--- | :--- | :--- | :--- | :--- |
| **Software Version No.** | `Inverter Firmware Version` | `sw_version` | **Medium** | Unified main-slave DSP and ARM firmware string. |
| **Product Model** | `Inverter Model` | `dmodname` | **Medium** | Hardware model identification (e.g., `Power-Box SH5K`). |
| **Serial No.** | `Device PID` | `pid` (Config entry) | **Static** | Product Serial number / Identifier. |
| **Rated Power** | `Inverter Rated Power` | `devCap` | **Medium** | Design rating ceiling of the Inverter in Watts. |
| **Inverter Status** | `Inverter Operation Status` | `runsta` | **Medium** | Operational status string (e.g., `OnGrid`, `OffGrid`, `Fault`). |
| **Inverter voltage** | `Grid Voltage (Phase R)` | `gVR` | **Medium** | AC grid line voltage in Volts. |
| **Inverter current** | `Grid Current (Phase R)` | `gCurrR` | **Medium** | AC grid line current in Amperes. |
| **Off-grid Voltage** | `Off-grid Voltage (Phase R)` | `ogVR` | **Medium** | Back-up/EPS active output voltage. |
| **Off-grid Current** | `Off-grid Current (Phase R)` | `ogCurrR` | **Medium** | Back-up/EPS active output current. |
| **Off-grid Power** | `Off-grid Power (Phase R)` | `ogPowR` | **Medium** | Back-up/EPS active load draw in Watts. |
| **Power On/Off (Toggle)** | `Remote Power Switch` | `remoteOnOff` | **Write / Medium** | Remote hardware inverter power state toggle. |
| **Battery Enable (Toggle)** | `Battery Storage System Toggle` | `EPSEnable` | **Write / Medium** | Enable or disable battery backup operations. |

---

### 3. Battery Storage Screen ("Battery")
Granular diagnostic telemetry and capability thresholds queried directly from the BMS.

| BYD Mobile App UI Element | HA Sensor / Control Name | Sensor Key / Register | HA Polling Loop | Description |
| :--- | :--- | :--- | :--- | :--- |
| **Tower Quantity** | `Battery Tower Quantity` | `paraNum` | **Medium** | Physical battery towers connected in parallel. |
| **Installed Capacity** | `Battery Design Capacity` | `degCap` | **Medium** | Design rating capacity in Ah. |
| **Full capacity** | `Battery Full Capacity` | `fulCap` | **Medium** | Measured maximum capacity holding in Ah. |
| **Inverter Communication State** | `PCS Connection Status` | `pcsCsta` | **Medium** | Connectivity status between the Inverter (PCS) and BMS. |
| **Remaining capacity** | `Battery Remaining Capacity` | `remCap` | **Medium** | Absolute energy remaining in the battery pack (Ah). |
| **System SOC** | `Battery State of Charge` | `soc` | **Fast** | State of Charge in percentage. |
| **System SOH** | `Battery State of Health` | `soh` | **Medium** | State of Health (battery degradation level) in percentage. |
| **System voltage** | `Battery System Voltage` | `sysVol` | **Medium** | Realtime DC battery stack voltage. |
| **Allowed charging voltage** | `Allowable Charge Voltage` | `acVol` | **Medium** | Dynamic BMS-controlled charge voltage threshold. |
| **Allowed Discharging Voltage** | `Allowable Discharge Voltage` | `adcVol` | **Medium** | Dynamic BMS-controlled discharge voltage floor. |
| **System current** | `Battery System Current` | `sysCur` | **Medium** | DC current flow in Amperes. |
| **Allowable charge current** | `Allowable Charge Current` | `acCur` | **Medium** | Dynamic maximum charging speed safety ceiling. |
| **Allowable discharge current** | `Allowable Discharge Current` | `adcCur` | **Medium** | Dynamic maximum discharging speed safety ceiling. |

---

### 4. Solar Configuration Screen ("Photovoltaic")
Real-time MPPT string electrical stats and custom physical string limits.

| BYD Mobile App UI Element | HA Sensor / Control Name | Sensor Key / Register | HA Polling Loop | Description |
| :--- | :--- | :--- | :--- | :--- |
| **PV1 Peak Power (Editable)** | `PV1 String Peak Power Limit` | `pv1MaxPower` | **Write / Medium** | Hardware PV1 maximum generation ceiling (W). |
| **PV1 Voltage** | `PV1 String Voltage` | `pv1vol` | **Fast** | Instantaneous PV1 MPPT string input voltage. |
| **PV1 Current** | `PV1 String Current` | `pv1cur` | **Fast** | Instantaneous PV1 MPPT string input current. |
| **PV2 Peak Power (Editable)** | `PV2 String Peak Power Limit` | `pv2MaxPower` | **Write / Medium** | Hardware PV2 maximum generation ceiling (W). |
| **PV2 Voltage** | `PV2 String Voltage` | `pv2vol` | **Fast** | Instantaneous PV2 MPPT string input voltage. |
| **PV2 Current** | `PV2 String Current` | `pv2cur` | **Fast** | Instantaneous PV2 MPPT string input current. |

---

### 5. Smart Meter Configuration Screen ("Electricmeter")

| BYD Mobile App UI Element | HA Sensor / Control Name | Sensor Key / Register | HA Polling Loop | Description |
| :--- | :--- | :--- | :--- | :--- |
| **Power of electric meter** | `Grid Meter Power` | `me1Pow` | **Fast** | Raw real-time power reading at smart grid boundaries. |

---

### 6. Scheduled Charge/Discharge Settings ("Scheduled C/D Setting")
Allows visual setting of SOC target thresholds and specific time slots under separate tabs.

| BYD Mobile App UI Element | HA Sensor / Control Name | Sensor Key / Register | HA Polling Loop | Description & Interaction Mappings |
| :--- | :--- | :--- | :--- | :--- |
| **Feed-in Stop SOC** *(Feed-in Priority)* | `Feed-in Stop SOC` | **`minGrEle`** | **Write / Medium** | Grid export floor limit. Inverter stops grid feed-in from battery when SOC hits this limit. *Bounded by: `[minSoc, maxSoc]`.* |
| **Battery Max SOC** *(Backup)* | `Battery Charge Stop Ceiling` | **`maxSoc`** | **Write / Medium** | Battery charging stop threshold. *Must be strictly higher than `minGrEle` / `minSoc`.* |
| **Time Slot 1 / 2 (Toggles)** | *Various Switches* | `gcF1ena` / `gcF2ena`<br>`gdcF1ena` / `gdcF2ena` | **Write / Medium** | Time slot active/inactive toggles. |
| **Time Slot 1 / 2 (Time Windows)** | *Various Texts* | `gcF1` / `gcF2`<br>`gdcF1` / `gdcF2` | **Write / Medium** | Editable time window strings (e.g., `02:01-04:59`). |

---

### 7. Information & Subsystem Diagnostics ("Setting" Menu sub-screens)

| BYD Mobile App UI Element | HA Sensor / Control Name | Sensor Key / Register | HA Polling Loop | Description |
| :--- | :--- | :--- | :--- | :--- |
| **Country/Region** | (Metadata) | `Nation` | **Slow** | Installation territory (e.g., `Ireland`). |
| **Grid Regulations** | `Grid Standard Regulation` | `grid_regulation` | **Slow** | Hardware-selected regional compliance standard (e.g., `EN50549`). |
| **Installation Time** | `Installation Date` | `qaTime` | **Slow** | Static recorded installation startup date (`YYYY-MM-DD`). |
| **BMS (Firmware Upgrade)** | `BMS Firmware Version` | `bms_current_version` | **Slow** | Current active BMS software code (`V1.9.0`). |
| **BMS (New Version check)** | `BMS Latest Available Firmware` | `bms_latest_version` | **Slow** | Latest available software version on BYD server. |
| **Inverter (New Version check)** | `Inverter Latest Available Firmware` | `pcs_latest_version` | **Slow** | Latest available software version on BYD server for PCS. |
| **Smart WiFi/LAN MCU** | `WiFi Stick Firmware Version` | `f527_current_version` | **Slow** | Current active WiFi module firmware version (`V1.1.29`). |
| **Smart WiFi/LAN MCU check** | `WiFi Stick Latest Available Firmware` | `f527_latest_version` | **Slow** | Latest available WiFi module firmware version on BYD server. |

---

## 🔄 Allowed Ranges & Boundary Interdependencies

The official app validates slider inputs based on reciprocal boundaries loaded directly from the device active EEPROM registers:

```javascript
Feed_in_Stop_SOC_Min = Battery_Discharge_Stop_Floor (minSoc)
Feed_in_Stop_SOC_Max = Battery_Charge_Stop_Ceiling (maxSoc)

Battery_Charge_Stop_Ceiling_Min = Feed_in_Stop_SOC (minGrEle)
```

### Dynamic Safety Guards in Home Assistant
To prevent sending invalid payloads that might cause cloud setting rejections, the Home Assistant component mirrors this logic inside `number.py`:
* Adjusting the `Battery Discharge Stop Floor` (`minSoc`) dynamically updates the lower limit of the `Feed-in Stop SOC` (`minGrEle`) slider.
* Adjusting the `Battery Charge Stop Ceiling` (`maxSoc`) dynamically updates the upper limit of the `Feed-in Stop SOC` (`minGrEle`) slider.
