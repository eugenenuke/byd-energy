# BYD Energy Integration - Dashboard Customization Guide

This guide provides detailed instructions for setting up, customizing, and using Home Assistant Lovelace dashboards to replicate and enhance the BYD mobile application experience.

---

## 🎨 Dashboard Options Summary

To give you maximum flexibility, five different dashboard designs are available in this repository. Each design is fully customized for different screen sizes, use-cases, and user preferences:

| Dashboard Filename | UI Aesthetic | Purpose & Layout | Frontend Card Dependencies (Optional) |
| :--- | :--- | :--- | :--- |
| **[ha_byd_dashboard.yaml](file:///usr/local/google/home/eianiuk/src/byd/ha_byd_dashboard.yaml)** | Classic App Layout | 5-tab modular replica matching every screen of the official BYD mobile application. | `power-flow-card-plus` |
| **[ha_byd_dashboard_premium.yaml](file:///usr/local/google/home/eianiuk/src/byd/ha_byd_dashboard_premium.yaml)** | Premium Glassmorphism | Dynamic dark theme with semi-transparent card blurs, custom shadow glows, and advanced real-time solar-load comparison area charts. | `card-mod`, `apexcharts-card`, `power-flow-card-plus` |
| **[ha_byd_dashboard_minimal.yaml](file:///usr/local/google/home/eianiuk/src/byd/ha_byd_dashboard_minimal.yaml)** | Minimalist Glance | Clean grid layout with high-contrast state summaries. Optimized for quick glanceability on wall-mounted smart panels. | `bar-card` |
| **[ha_byd_dashboard_gauges.yaml](file:///usr/local/google/home/eianiuk/src/byd/ha_byd_dashboard_gauges.yaml)** | Gauges & Status | Circular dials showing real-time state flows. Visually rich, zero clutter. | None |
| **[ha_byd_dashboard_analytics.yaml](file:///usr/local/google/home/eianiuk/src/byd/ha_byd_dashboard_analytics.yaml)** | Deep-Dive Charts | Designed for advanced telemetry tracking, providing detailed history graphs, BMS cell temperature bounds, and cycle counts. | `apexcharts-card`, `mini-graph-card` |

---

## 🔌 Frontend Card Dependencies (HACS)

While the integration works completely out of the box with standard Home Assistant cards, installing these popular community cards via HACS is recommended for a premium experience:

1. **`power-flow-card-plus`**: Renders a gorgeous real-time power flow diagram with animated moving dots showing exact power direction and speed (Tab 1 in most layouts).
2. **`card-mod`**: Allows custom CSS injection directly inside Lovelace cards to achieve premium glassmorphic borders, blurs, and shadow glows.
3. **`apexcharts-card`**: Renders advanced historical graphs, enabling multi-duration selection tabs (Day/Month/Year).
4. **`bar-card`**: Translates numeric state limits into clean horizontal progress bars.
5. **`mini-graph-card`**: Elegant sparklines and minimal real-time trend graphs.

---

## 🛠️ Importing Your Lovelace Dashboard

To import any of the five dashboard options:
1. Open the target dashboard YAML file (e.g., `ha_byd_dashboard_premium.yaml`) and copy its entire contents.
2. In Home Assistant UI, click the three dots in the top-right corner ➔ **Edit Dashboard**.
3. Click the three dots again ➔ **Raw Configuration Editor**.
4. Select the editor, paste the copied configuration, and click **Save**.
5. If necessary, customize the entity ID suffix strings to align with your auto-discovered inverter serial PIDs.

---

## 🧩 Dynamic Solar Array Scaling (Multi-String Support)

Systems may operate with a varying number of active PV strings (e.g., 1, 2, or 3 strings). To prevent dashboard clutter, String details can be displayed conditionally without requiring any external HACS plugins.

### Conditional Cards (Native Home Assistant Core)
The dashboard YAML uses native `conditional` cards to automatically show or hide the String 2 details. If a string is not connected (reporting `unavailable`), it is automatically hidden from the user interface:

```yaml
type: conditional
conditions:
  - condition: state
    entity: sensor.pv2_string_voltage
    state_not: "unavailable"
card:
  type: entities
  title: PV MPPT String 2
  entities:
    - entity: number.pv2_string_peak_power_limit
      name: String 2 Configured Peak Power
    - entity: sensor.pv2_string_voltage
      name: String 2 Live Voltage
    - entity: sensor.pv2_string_current
      name: String 2 Live Current
    - entity: sensor.pv2_string_active_power
      name: String 2 Live Power
```
