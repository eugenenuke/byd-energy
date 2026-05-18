# BYD Energy Integration - User Setup Guide

This guide provides step-by-step instructions to install, configure, and register the BYD Energy custom component in Home Assistant.

---

## 🔌 Prerequisites & Requirements

* **Home Assistant Server**: Home Assistant OS, Home Assistant Supervised, or Home Assistant Container (2024.1.0 or newer is recommended).
* **BYD Energy Account**: A registered household account on the official BYD Energy mobile application or cloud portal.
* **Secure Communications**: The integration requires internet access to query the production BYD Cloud server (`https://energyhousehold.bydessys.com`). All telemetry data is transferred over TLS.

---

## 📦 Installation Methods

### Method 1: Via HACS UI (Recommended)
Once HACS is installed on Home Assistant:
1. Navigate to **HACS** in your Home Assistant sidebar.
2. Click the **three dots** in the top-right corner and select **Custom repositories**.
3. Paste your GitHub repository URL: `https://github.com/eugenenuke/byd-energy`.
4. Select Category: **Integration** and click **Add**.
5. The integration is now available for UI-driven installation and update checking directly from the HACS store.

### Method 2: Manual Installation (SSH / SCP)
To manually transfer the component to your Home Assistant server:
1. Open your workstation terminal where the source repository is located.
2. Create the custom components folder if it does not exist on your server:
   ```bash
   ssh root@<YOUR_HA_SERVER_IP> "mkdir -p /config/custom_components"
   ```
3. Transfer the integration files via `scp`:
   ```bash
   scp -r custom_components/byd_energy root@<YOUR_HA_SERVER_IP>:/config/custom_components/
   ```
4. Restart Home Assistant to register the new custom component (*Settings -> System -> Restart Home Assistant*).

---

## ⚙️ Configuration & UI Setup

Once the files are in place and Home Assistant has restarted, the setup is fully automated:
1. Navigate to **Settings -> Devices & Services**.
2. Click **+ Add Integration** in the bottom right corner.
3. Search for **BYD Energy** and select it.
4. Enter your BYD Energy account email and password.
5. The integration automatically initiates a secure cryptographic handshake, performs account discovery, and registers your hardware modules.

### 📊 Auto-Discovered Devices
Upon setup, the integration registers three separate physical devices to represent your smart home infrastructure:
1. **BYD Inverter**: Represents the Power Conversion System (PCS), providing real-time solar array telemetries, time scheduling slots, and mutable SOC limit sliders.
2. **BYD Battery Tower**: Represents the Battery Management System (BMS), displaying SOH, SOC, parallel module counts, cell voltages, and cycle metrics.
3. **BYD Grid Meter**: Represents your smart meter boundary (e.g., Chint DDSU666), showing active power draw and daily/lifetime import-export totalizers.
