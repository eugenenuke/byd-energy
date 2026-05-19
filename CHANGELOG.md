# Changelog

All notable changes to the BYD Energy Home Assistant custom component will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.4.2-beta] - 2026-05-19

### Fixed
- **Integer Settings Sliders**: Cast the `native_value` return type from `float` to `int` inside `number.py` for all 5 percentage and power configuration registers. This natively removes decimal dots (e.g., `4500` instead of `4500.0`) across all Lovelace sliders and cards with zero database or template history conflicts.

## [0.4.1-beta] - 2026-05-19

### Added
- **Defensive Cloud Energy Sensors**: Registered `loadDailyConsume` as `Daily Household Consumption (Cloud)` and `pvDailyProduct` as `Daily PV Generation (Cloud)` inside the custom component backend to match the BYD Mobile App's daily energy numbers by the digit.
- **Non-Breaking Metric Coexistence**: Retained the raw real-time `dec` sensor completely untouched as `Daily Household Consumption` to guarantee 100% backward-compatibility for existing custom templates and automations.

### Lovelace Upgrades (Local scratch dashboard)
- **High-Fidelity Real-Time Split Power Chart**: Integrated custom `apexcharts-card` in Tab 1 showing positive real-time active kW curves (PV generation, battery discharge, grid import) above the `0` line and negative active kW curves (household load, battery charging, grid export) below the `0` line, mimicking the mobile app layout.
- **Day-Switching Historical Energy Picker**: Added native `energy-date-selection` and `energy-usage-graph` cards to Tab 1 for helper-free daily grid history navigation.
- **SolCast Forecasting Overlay**: Appended the native `energy-solar-graph` card to Tab 3 to overlay actual PV production history with the predicted SolCast curve.
- **Seamless Header Subtitling**: Snugged card-mod styled Markdown subtitles (`*Feed-in Priority*` and `*Backup*`) directly under native card titles in Tab 4 and Tab 5, removing heavy separators.

## [0.4.0-beta] - 2026-05-19

### Added
- **Hour and Minute Split Dropdowns**: Added 16 new virtual select dropdown entities representing Hour and Minute splits for all 8 inverter scheduling registers, enabling touch-friendly selection in Lovelace.
- **Upgrade File Sizes**: Exposed the upgrade file size dynamically as an attribute on all latest available firmware sensors.
- **Unified Firmware Update Available Sensor**: Added a binary sensor indicating if a newer firmware version is available for any inverter or battery component, with custom detailed attributes.
- **Self-Healing Sidebar Notifications**: Added automatic persistent notifications that aggregate all pending firmware updates and dynamically dismiss themselves once all components are up to date.

### Changed
- **Unified Cloud Firmware Polling**: Consolidated 6 individual slow HTTP requests into a single unified cloud query, optimizing network bandwidth and API performance.

## [0.3.4-beta] - 2026-05-19

### Fixed
- **Resolved Namespace Shadowing Crash**: Fixed a critical Python namespace shadowing conflict where our new `time` platform module (`time.py`) collided with the built-in Python standard library `time` inside `__init__.py` and `api.py`. Solved by explicitly importing the standard library as `sys_time`, fully restoring all BYD sensors and metrics to active, functional states.

## [0.3.3-beta] - 2026-05-19

### Added
- **Native Lovelace Time Picker Platform (`time.py`)**: Migrated the 8 time slot configuration registers from the `text` platform to the native Home Assistant **`time`** platform. This natively enables standard HTML5 touch-friendly time selector dials without requiring custom HACS plugins or helper automations, and formats time strings bi-directionally (`HH:MMZ`) on the fly.
- **Lovelace Clickable Flow Cards**: Configured card-level `clickable_entities: true` on the main animated power flow diagram to enable click-to-open history popups for Solar, Grid, and Battery bubbles.
- **Dynamic Battery Flow Icon Overrides**: Styled the active power row using dynamic `card-mod` CSS variables inside the `:host` block, automatically rendering a red up-arrow on discharge and a green down-arrow on charge.

### Fixed
- **Restored Clean Friendly Names**: Reverted yesterday's daily/total battery energy sensor name swaps to naturally align friendly names and icons with their entity ID keys, resolving naming confusion inside the HA Energy Dashboard configuration dropdowns.
- **Cleaned Settings Tab Layout**: Rearranged cards inside the Settings & Controls tab to place parameter controls at the bottom, removed redundant glance cards/MPPT peak limits, and updated legacy database-locked entity IDs.

## [0.3.2-beta] - 2026-05-18

### Added
- **HACS Brands CDN Logo PR Guide**: Created a step-by-step PR setup guide inside `scratch/hacs_brand_registration.md` to register the custom domain as an alias to reuse the official red BYD logo globally in HACS.

### Fixed
- **Energy Dashboard Calculated Consumption**: Swapped the daily and total battery charged/discharged energy registers (`bmsDailyCharge` / `bmsDailyDisCharge` and `bmsTotalCharge` / `bmsTotalDisCharge`) to align correctly with Home Assistant's calculations, resolving the `19 kW` consumption spike at 5:00 AM during grid charging.
- **My Home Assistant Redirect Badge**: Corrected the spelling typo in `README.md` from `my.homeassistant.io` to `my.home-assistant.io` to restore the redirect badge.

## [0.3.1-beta] - 2026-05-18

### Added
- **Safety Toggle Lock**: Implemented a dual-layer safety lock protecting high-risk, untested write controls ("Inverter Power On/Off" and "Battery Enable") from accidental triggers by default.
- **Options Flow Safety Checkbox**: Added a secure "Enable Untested Advanced Write Controls" checkbox to the integration options config flow, allowing power users to explicitly release the safety lock.
- **UI Error Toast Navigation**: Customized the Home Assistant error popup notification message to output a detailed warning with exact UI settings navigation directions when locked controls are clicked.

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
