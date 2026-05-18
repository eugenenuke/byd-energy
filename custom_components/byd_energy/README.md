.3
0
# BYD Energy Home Assistant Custom Component

[![GitHub Release](https://img.shields.io/github/release/eugenenuke/byd_energy.svg)](https://github.com/eugenenuke/byd_energy/releases)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)

A production-ready Home Assistant (HA) custom component for monitoring and controlling BYD Energy household solutions (PV panel strings, Inverters/PCS, Battery Storage systems/BMS, and Smart Meters).

Since official API documentation does not exist, this component operates via reverse-engineered HTTP REST endpoints communicating securely over TLS with the BYD Energy production cloud (`https://energyhousehold.bydessys.com`).

---

## Key Features

* 🔐 **Secure Cryptographic Handshake**: Plaintext passwords are never transmitted over the wire. The integration performs an initial security key exchange and encrypts passwords locally using `AES-256-CBC` (via `pycryptodome`).
* 🔄 **Self-Healing Authentication Lifecycle**: Automatically handles session expiration and refresh token exchanges behind the scenes without interrupting sensor updates.
* 🪄 **Zero-Friction Automated Setup**: On first setup, you only input your username and password. Home Assistant automatically discovers all associated hardware serial numbers (PIDs), product series (`lixia`, `chunfen`), and inverter models (e.g., `XD3-6KTL`).
* 📊 **Unified Multi-Device Architecture**: Grouped into 3 logically separated hardware devices in Home Assistant: *BYD Inverter*, *BYD Battery Tower*, and *BYD Grid Meter*.
* ⚡ **Native Energy Dashboard Ready**: Perfectly supplies all required entities for HA's native Energy Dashboard (Solar panels, Battery systems, Grid consumption & return).
* ☀️ **Advanced Solar Clipping Alert**: Monitors raw MPPT string parameters (`pv1vol`, `pv1cur`) and activates a real-time dashboard clipping alert when DC solar generation exceeds the inverter's hard AC conversion limit while the battery is full.

---

## Installation Instructions (SCP / SSH)

To install this custom component onto your physical Home Assistant server (e.g., Home Assistant OS on a Raspberry Pi or Intel NUC), follow these step-by-step instructions:

### Step 1: Enable SSH on Home Assistant Server
1. In your Home Assistant UI, navigate to **Settings -> Profile (your username in bottom left)** and ensure **Advanced Mode** is turned ON.
2. Navigate to **Settings -> Add-ons -> Add-on store**.
3. Search for and install **Terminal & SSH** (or **Advanced SSH & Web Terminal**).
4. Once installed, go to the add-on's **Configuration** tab and set a secure SSH password (or paste your public SSH key). Save and start the add-on.

### Step 2: Transfer Files via SCP
From your Linux workstation terminal where this source code is located, transfer the custom component directory to your Home Assistant server using `scp`:

```bash
# 1. SSH into HA server to ensure the custom_components directory exists
ssh root@<YOUR_HA_SERVER_IP> "mkdir -p /config/custom_components"

# 2. Copy the entire byd_energy folder to the HA server
scp -r /usr/local/google/home/eianiuk/src/byd/custom_components/byd_energy root@<YOUR_HA_SERVER_IP>:/config/custom_components/
```
*(Replace `<YOUR_HA_SERVER_IP>` with the actual IP address or hostname of your Home Assistant server).*

### Step 3: Restart Home Assistant Core
Home Assistant only detects new custom components during startup.
1. In Home Assistant UI, navigate to **Settings -> System -> Power Button (top right) -> Restart Home Assistant**.

### Step 4: Configure Integration in UI
1. Once Home Assistant has restarted, navigate to **Settings -> Devices & Services**.
2. Click **+ Add Integration** in the bottom right corner.
3. Search for **BYD Energy** and select it.
4. Enter your BYD Energy account email and password. Home Assistant will automatically discover your hardware devices and configure all sensors!

---

## ⚡ Configuring the Home Assistant Energy Dashboard

Home Assistant custom integrations do not automatically populate the Energy Dashboard. Once the BYD Energy integration is configured in your UI, you must manually assign the sensors by navigating to **Settings -> Dashboards -> Energy**.

### 🏆 Daily vs. Lifetime Metrics (Crucial Best Practice)
The integration exposes both `Daily` and `Lifetime` energy totals. **For the Energy Dashboard, `Lifetime` sensors are strongly recommended.**
* **Why**: Daily sensors reset to `0 kWh` at exactly midnight on the physical BYD hardware. If Home Assistant's cloud polling interval does not happen to sync exactly at `23:59:59`, Home Assistant might miss the final fraction of a kilowatt-hour before the reset.
* **The Solution**: `Lifetime` sensors (e.g., `Lifetime Grid Import`) continuously count upwards forever. Home Assistant's core database flawlessly samples these continuous counters every hour and handles daily/monthly/yearly slicing with 100% mathematical precision.

### 🔌 Electricity Grid Configuration

Under the **Electricity grid** section, configure your grid connection as follows:

1. **Grid Consumption (Import)**
   * Click **Add consumption**.
   * Select entity: **`Lifetime Grid Import`** (`sensor.byd_grid_meter_<pid>_lifetime_grid_import`).

2. **Return to Grid (Export)**
   * Click **Add return**.
   * Select entity: **`Lifetime Grid Export`** (`sensor.byd_grid_meter_<pid>_lifetime_grid_export`).

3. **Type of Power Measurement**
   * Select **Standard**.
   * Select entity: **`Grid Meter Power`** (`sensor.byd_grid_meter_<pid>_grid_meter_power`).
   * *Explanation*: The BYD Energy integration automatically normalizes raw cloud telemetry so that `Grid Meter Power` adheres to standard Home Assistant conventions (**+ Watts for grid import/consumption**, **- Watts for grid export/feed-in**). Setting this to Standard ensures flawless real-time animated power flow on your energy gauges.

### ☀️ Solar Panels Configuration

Under the **Solar panels** section:
1. Click **Add solar production**.
2. **Solar production energy**: Select **`Total PV Generation`** (`sensor.byd_inverter_<pid>_total_pv_generation`). *(Using the Lifetime total metric ensures seamless synchronization).*
3. **Solar production power**: Select **`Total PV Power`** (`sensor.byd_inverter_<pid>_total_pv_power`). *(Supplies real-time Watts to animate the solar production gauge).*

### 🔋 Battery Storage Configuration

Under the **Battery systems** section:
1. Click **Add battery system**.
2. **Energy going in to the battery**: Select **`Lifetime Battery Charged Energy`** (`sensor.byd_battery_tower_<pid>_lifetime_battery_charged_energy`).
3. **Energy coming out of the battery**: Select **`Lifetime Battery Discharged Energy`** (`sensor.byd_battery_tower_<pid>_lifetime_battery_discharged_energy`).
4. **Type of Power Measurement**: Select **Standard** and choose **`Battery Active Power`** (`sensor.byd_battery_tower_<pid>_battery_active_power`). *(Note: The integration automatically normalizes this sensor to **+ Watts for battery charging**, **- Watts for battery discharging**, ensuring accurate real-time animation).*

### 💶 Cost Tracking & Time-of-Use (ToU) Helper Setup

If you have a Time-of-Use tariff (e.g., a cheap overnight charging rate and a standard day rate), do not use a static flat price. Instead, choose **Use an entity with current price**.

To create a custom price entity for a tariff such as **6.99c/kWh (€0.0699) from 2:00 AM to 5:00 AM**, and **41.77c/kWh (€0.4177) at all other times**:

#### Method 1: Via UI Helper (Recommended)
1. Navigate to **Settings -> Devices & Services -> Helpers**.
2. Click **+ Create Helper** and select **Template -> Template a sensor**.
3. Configure the fields exactly as follows:
   * **Name**: `Electricity Tariff Price`
   * **State template**: Paste the following Jinja2 code:
     ```jinja2
     {% set h = now().hour %}
     {% if h >= 2 and h < 5 %}
       0.0699
     {% else %}
       0.4177
     {% endif %}
     ```
   * **Unit of measurement**: Type `EUR/kWh` (or `€/kWh`). *Note: This is a free-form text box; even if it doesn't appear in the dropdown list, simply type it in.*
   * **Device class**: Leave blank / None. *(Note: Home Assistant's validator restricts `Monetary` to pure currency totals; for unit rates like EUR/kWh, leaving Device class blank is required).*
   * **State class**: Leave blank / None.
   * **Link to device / Select a device**: Leave this blank / None. (This helper is standalone and does not need to be attached to any physical hardware).
4. Click **Submit**. Now, in your Grid Consumption cost tracking settings in the Energy Dashboard, select **Use an entity with current price** and choose `sensor.electricity_tariff_price`.

> [!NOTE]
> **Local Time vs. UTC**: The Jinja2 `now()` function automatically uses your Home Assistant server's configured local time zone (*Settings -> System -> General -> Time zone*) and seamlessly handles Daylight Saving Time shifts. You do not need to perform any UTC offset calculations.

#### Method 2: Via `configuration.yaml`
Alternatively, add this block to your `configuration.yaml` file and restart Home Assistant:
```yaml
template:
  - sensor:
      - name: "Electricity Tariff Price"
        unit_of_measurement: "EUR/kWh"
        state: >
          {% set h = now().hour %}
          {% if h >= 2 and h < 5 %}
            0.0699
          {% else %}
            0.4177
          {% endif %}
```

---

## 🎛️ Inverter Remote Control & Energy Management

The integration actively supports real-time parameter modification (via EEPROM register POST commands) directly from your Home Assistant dashboard. 

To make BYD's technical terminology immediately intuitive for smart home automation, parameters are exposed using standard energy management conventions:

### 1. Forced Grid Charging (BYD "Backup" Mode)
*Useful for taking advantage of cheap time-of-use or overnight electricity tariffs by forcing the battery to charge at maximum inverter capacity (5 kW) from the grid.*
* 🔘 **Toggles**: `Forced Grid Charge Slot 1` / `Slot 2` *(BYD: Grid charging sign 1/2 enabling)*
* ⏰ **Start & End Times**: Editable text inputs (`HH:MM` format) for `Forced Grid Charge Slot 1 Start/End` and `Slot 2 Start/End` *(BYD: cstaT1/cendT1)*
* 🎯 **Max Target SOC**: Editable number slider (`10% - 100%`) for `Forced Grid Charge Max Target SOC`. Forced charging will automatically stop when battery charge reaches this percentage *(BYD: Charge Stop SOC / maxSoc)*.

### 2. Grid Export Discharge (BYD "Feed-in" Mode)
*Configures time windows where the battery is permitted to discharge to power the home and export excess energy back to the electrical grid.*
* 🔘 **Toggles**: `Grid Export Discharge Slot 1` / `Slot 2` *(BYD: Grid discharging sign 1/2 enabling)*
* ⏰ **Start & End Times**: Editable text inputs (`HH:MM` format) for `Grid Export Discharge Slot 1 Start/End` and `Slot 2 Start/End` *(BYD: dcstaT1/dcendT1)*
* 🛑 **Stop SOC**: Editable number slider (`10% - 100%`) for `Grid Export Stop SOC`. Discharging to the grid will automatically halt when battery charge drops below this threshold to preserve emergency reserves *(BYD: Discharge Stop SOC / minSoc)*.

### 3. Hardware System Toggles
* 🔌 **Inverter Remote Power**: Remotely turn the inverter unit ON (`1`) or OFF (`0`) *(BYD: remoteOnOff)*.
* 🔋 **Battery Storage System Enabled**: Remotely enable or disable battery EPS operation *(BYD: EPSEnable)*.

---

## Supported Sensors & Controls Matrix

| HA Hardware Device | Sensor Name | HA Device Class | Unit / Format | Description |
| :--- | :--- | :--- | :--- | :--- |
| **BYD Inverter** | `Total PV Power` | `power` | `W` | Combined AC solar generation |
| **BYD Inverter** | `Inverter Rated Power` | `power` | `W` | Inverter AC continuous power capacity |
| **BYD Inverter** | `Inverter Operation Status` | None | None | Real-time inverter operating state (e.g. OnGrid) |
| **BYD Inverter** | `Grid Voltage (Phase R)` | `voltage` | `V` | On-grid AC voltage |
| **BYD Inverter** | `Grid Current (Phase R)` | `current` | `A` | On-grid AC current |
| **BYD Inverter** | `Off-grid Voltage (Phase R)` | `voltage` | `V` | Backup/EPS off-grid AC voltage |
| **BYD Inverter** | `Off-grid Current (Phase R)` | `current` | `A` | Backup/EPS off-grid AC current |
| **BYD Inverter** | `Off-grid Power (Phase R)` | `power` | `W` | Backup/EPS off-grid active power |
| **BYD Inverter** | `Daily PV Generation` | `energy` | `kWh` | Daily solar yield *(Energy Dashboard)* |
| **BYD Inverter** | `PV1 String Voltage` | `voltage` | `V` | Raw MPPT String 1 voltage |
| **BYD Inverter** | `PV1 String Peak Power` | `power` | `W` | MPPT String 1 configured peak power rating |
| **BYD Inverter** | `PV2 String Peak Power` | `power` | `W` | MPPT String 2 configured peak power rating |
| **BYD Inverter** | `Solar Clipping Alert` | `problem` | `on/off` | Active when DC surplus > Inverter capacity |
| **BYD Battery Tower** | `State of Charge` | `battery` | `%` | High-precision battery SOC |
| **BYD Battery Tower** | `State of Health` | None | `%` | Long-term battery SOH |
| **BYD Battery Tower** | `Allowable Charge Voltage` | `voltage` | `V` | Inverter allowed charging voltage limit |
| **BYD Battery Tower** | `Allowable Discharge Voltage` | `voltage` | `V` | Inverter allowed discharging voltage limit |
| **BYD Battery Tower** | `Allowable Charge Current` | `current` | `A` | Inverter allowed charging current limit |
| **BYD Battery Tower** | `Allowable Discharge Current` | `current` | `A` | Inverter allowed discharging current limit |
| **BYD Battery Tower** | `Battery Tower Quantity` | None | None | Installed battery towers in parallel |
| **BYD Battery Tower** | `Battery Module Quantity` | None | None | Installed battery pack modules |
| **BYD Battery Tower** | `Daily Battery Charged` | `energy` | `kWh` | Daily charged energy *(Energy Dashboard)* |
| **BYD Grid Meter** | `Daily Grid Import` | `energy` | `kWh` | Daily imported grid energy *(Energy Dashboard)* |
| **BYD Grid Meter** | `Daily Grid Export` | `energy` | `kWh` | Daily exported grid feed-in *(Energy Dashboard)* |

---

## License
This project is licensed under the MIT License - see the LICENSE file for details.
