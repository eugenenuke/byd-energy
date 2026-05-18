# BYD Energy Integration - Troubleshooting & Configuration Tips Guide

This guide details troubleshooting steps for common issues and provides templates for advanced Home Assistant configurations.

---

## ⚠️ Safety Lock for Advanced Controls

By default, the integration implements a safety lock on potentially critical write controls (e.g., **Inverter Remote Power** and **Battery Storage System Enabled**). This prevents accidental shutoffs, grid drops, or system-wide battery disables.

When the safety lock is active:
* Toggle switches for these controls remain fully visible on your dashboard.
* Any click/toggle attempt will be rejected. Home Assistant will display a warning toast: *"Advanced controls are locked..."*, and the switch will immediately flip back to its original position.
* No remote command payload is dispatched to the BYD Cloud.

### How to Unlock Advanced Controls (Power Users Only)
To unlock these switches and enable remote write operations:
1. Navigate to **Settings -> Devices & Services** inside Home Assistant.
2. Find the **BYD Energy** integration card.
3. Click **Configure** (or **Options**).
4. Check the box: **"Enable Untested Advanced Write Controls (Inverter Power / Battery Enable)"**.
5. Click **Submit**.

Once submitted, the safety lock is released, and toggling the switches will issue write commands directly to the physical hardware.

---

## ⏱️ Rate Limiting & Cloud Throttling (HTTP 429)

Because the integration communicates with the BYD production cloud servers, reducing the polling frequencies significantly can trigger rate-limiting blockades.

### Symptoms
* Home Assistant logs display `HTTP 429 (Too Many Requests)`.
* Sensors fail to update and display `unavailable`.
* EEPROM parameter sliders revert or fail to save upon interaction.

### Solution
1. Increase the **Medium Polling Interval** (EEPROM configurations) in the integration options flow back to the default **`300s` (5 minutes)**.
2. Increase the **Slow Polling Interval** (BMS metadata and OTA version checks) back to the default **`43200s` (12 hours)**.
3. Ensure your internet connection is stable. The cloud service may temporarily ban IP addresses for up to 24 hours if they exceed safety thresholds.

---

## 🔐 Session Expired & Auth Failures

The integration implements a self-healing JWT token refresh cycle. However, if you change your account password or your account is logged in on multiple concurrent third-party apps, the session may be invalidated.

### Solution
1. Navigate to **Settings -> Devices & Services -> BYD Energy**.
2. Click the three dots and select **Reconfigure**.
3. Enter your updated BYD email credentials and password. The integration will regenerate your cryptographic key material and re-establish the secure cloud session.

---

## 💶 Advanced Cost Tracking (Time-of-Use Tariff Setup)

To configure cost tracking for the Home Assistant Energy Dashboard with a Time-of-Use (ToU) tariff (e.g., cheaper night charging rates), do not use flat prices. Instead, use a **Template Sensor Helper**.

### Tariff Setup Example
For a tariff with a night rate of **€0.0699/kWh** between **2:00 AM and 5:00 AM**, and a day rate of **€0.4177/kWh** at all other times:

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
   * **Unit of measurement**: Type `EUR/kWh` (or `€/kWh`).
   * **Device class**: Leave blank.
   * **State class**: Leave blank.
4. Click **Submit**.
5. Go to **Settings -> Dashboards -> Energy**, edit your Grid Consumption, select **Use an entity with current price**, and choose `sensor.electricity_tariff_price`.

#### Method 2: Via `configuration.yaml`
Alternatively, append this block to your `configuration.yaml` file and restart Home Assistant:

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
