# BYD Energy Home Assistant Custom Component

[![GitHub Release](https://img.shields.io/github/release/eugenenuke/byd-energy.svg)](https://github.com/eugenenuke/byd-energy/releases)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=eugenenuke&repository=byd-energy&category=integration)

> [!WARNING]
> **UNTESTED HARDWARE CONTROLS & LIABILITY DISCLAIMER**
>
> This integration is entirely reverse-engineered from official BYD Energy mobile application bundles. Official API documentation does not exist.
>
> High-risk write controls - specifically **"Power On/Off"** (`remoteOnOff` / Inverter Remote Power) and **"Battery Enable"** (`EPSEnable` / Battery Storage System Enabled - **have not been tested on physical hardware**. Activating these controls carries a risk of accidental home blackouts, battery tower offline drops, or grid disconnection.
>
> To protect your system, these controls are **locked by default** in the integration's backend. Enabling them requires a conscious action in the integration's Configure settings. Use them at your own risk. The authors accept no responsibility or liability for any hardware damage, electrical blackouts, or financial loss.

A production-ready Home Assistant (HA) custom component for monitoring and controlling BYD Energy household solutions (PV panel strings, Inverters/PCS, Battery Storage systems/BMS, and Smart Meters).

---

## 🚀 Key Features

* 🔐 **Secure Cryptographic Handshake**: Local AES-256 credential encryption. Plaintext passwords are never transmitted.
* 🔄 **Self-Healing Session Management**: Automatically handles session expiration and token exchanges without interrupting telemetry feeds.
* 🪄 **Zero-Friction Automated Setup**: Instantly auto-discovers all associated hardware serial numbers (PIDs), product series, and inverter models.
* 📊 **Unified Multi-Device Architecture**: Groups sensors logically into *BYD Inverter*, *BYD Battery Tower*, and *BYD Grid Meter* devices in Home Assistant.
* ⚡ **Energy Dashboard Ready**: Out-of-the-box compatibility with Home Assistant's native Energy Dashboard.
* ☀️ **Advanced Solar Clipping Alert**: Activates a real-time dashboard alert when surplus solar generation exceeds Inverter continuous capacity.

---

## 📖 Documentation Directory (Home Assistant Best Practices)

To ensure maximum clarity, this repository structures documentation into dedicated directories depending on your needs:

### 📱 User Guides & Setup
* **[User Installation & Setup Guide](file:///usr/local/google/home/eianiuk/src/byd/documentation/user/user_setup_guide.md)**: Step-by-step SSH/SCP manual installs, prerequisites, and HACS Custom Repository configurations.
* **[Lovelace Dashboard Customization Guide](file:///usr/local/google/home/eianiuk/src/byd/documentation/user/dashboard_customization.md)**: Walks you through importing our **5 different dashboard options**, managing multi-array solar setups, and installing optional frontend HACS cards.
* **[Troubleshooting & Helper Configuration](file:///usr/local/google/home/eianiuk/src/byd/documentation/user/troubleshooting.md)**: Guide to managing API rate limits (HTTP 429), authentication reconfigurations, and configuring a dynamic time-of-use (ToU) tariff price helper.

### ⚙️ Developer Records & Specifications
* **[Multi-Rate Polling Loop Architecture](file:///usr/local/google/home/eianiuk/src/byd/documentation/internal/api_polling_architecture.md)**: Details Fast, Medium, and Slow scheduler loops and write-through caching structures.
* **[Parameters & Metrics Registers Guide](file:///usr/local/google/home/eianiuk/src/byd/documentation/internal/metrics_guide.md)**: Complete mappings between BYD mobile application fields and raw EEPROM parameter registers.

---

## 🔌 Frontend Dashboard Recommendations
Integrations inside Home Assistant provide backend data feeds but do not supply custom UI graphics. To replicate the beautiful visual flow and diagnostic cards of the official BYD app, we recommend installing the following community plugins via HACS:
1. **`power-flow-card-plus`**: Adds live animated power flows with moving dots between solar, battery, grid, and home.
2. **`apexcharts-card`**: For advanced custom historical graphs with Day/Month/Year selectors.
3. **`bar-card`**: Translates configuration sliders into sleek progress bars.
4. **`card-mod`**: Enables glassmorphic borders, background blurs, and shadow glows inside standard cards.

---

## License
This project is licensed under the MIT License - see the LICENSE file for details.
