# Changelog

All notable changes to the BYD Energy Home Assistant custom component will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.0-beta] - 2026-05-18

### Added
- **Select Platform (`select.py`)**: Exposes the Inverter Operating Mode (`workMode` register) as an interactive dropdown entity (`"Self-use"`, `"Feed-in Priority"`, and `"Backup"`), supporting real-time write mutations and state changes.
- **Firmware Upgrade Diagnostics**: Added individual sensor tracking for WiFi stick (`sensor.wifi_stick_firmware_version`), Inverter main DSP (`sensor.main_dsp_version`), Inverter auxiliary DSP (`sensor.slave_dsp_version`), and BMS modules, facilitating OTA update indicators.
- **Options Flow Configuration**: Implemented user-friendly HA configure options flows to dynamically customize the Fast, Medium, and Slow polling loops frequencies with strict safety check boundaries.
- **Grid Country Sensor**: Exposed `sensor.grid_country` mapping the cloud `"Nation"` parameters for quick country grid regulation checks.
- **Lovelace System Dashboard**: Appended `ha_byd_dashboard.yaml` at the repository root, providing a 5-tab dashboard replica of the official app, including moving-dots power flows, BMS details, and conditional solar array cards.
- **HACS UI Support**: Added `hacs.json` metadata to support immediate UI-driven custom repository installation.

### Changed
- **Deferred Medium Loop Refresh**: Integrated a 3-second delayed background GET refresh upon setting writes to guarantee hardware-to-cloud sync without dashboard lag or flickers.
- **SOC Sliders 5% Snapping**: Changed the step size of `minSoc`, `maxSoc`, and `minGrEle` number sliders in Home Assistant to 5% to snap sliders cleanly and dramatically reduce redundant REST calls.

## [0.2.0-beta] - 2026-05-17

### Added
- **Switch Platform (`switch.py`)**: Added active toggle switches for remote inverter power (`remoteOnOff`), battery storage system EPS (`EPSEnable`), forced grid charge time slots (`gcF1ena`, `gcF2ena`), and grid export discharge time slots (`gdcF1ena`, `gdcF2ena`).
- **Number Platform (`number.py`)**: Added validation-bounded number sliders for grid export stop SOC (`minSoc`), forced grid charge max target SOC (`maxSoc`), and PV1/PV2 string peak power limits (`pv1MaxPower`, `pv2MaxPower`).
- **Text Platform (`text.py`)**: Added editable time slot inputs (`HH:MM` format) with built-in regex formatting and automatic `HH:MMZ` API translation for inverter charging and discharging time windows.
- **New Device Sensors**: Added `Inverter Operation Status`, `Inverter Rated Power`, `Off-grid Voltage/Current/Power`, `Allowable Battery Voltage/Current`, `Battery Tower Quantity`, and `Battery Module Quantity`.
- **Unified Firmware String**: Combined inverter Main DSP, Slave DSP, and ARM version strings into a unified firmware version attribute on the Inverter device info card (e.g., `V505.V103.V327`).

### Fixed
- **Power Sign Normalization**: Inverted raw cloud telemetry for `Grid Meter Power` (`me1Pow`) and `Battery Active Power` (`battPow`) to strictly adhere to Home Assistant Core conventions (+ Watts for import/charging, - Watts for export/discharging).
- **Null Sensor Overwrites**: Implemented robust null collision protection in the update coordinator's `_populate_sensors` loop to prevent unpopulated BMS slave registers from overriding active battery capacity, SOC, and SOH data.

## [0.1.0-beta] - Initial Release

### Added
- Automated discovery of BYD Inverters, Battery Towers, and Grid Smart Meters via cloud API.
- Real-time power sensors and historical daily/total energy counters compatible with Home Assistant native Energy Dashboard.
- AES-256-CBC credential encryption and self-healing JWT session refresh.
