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

While the integration works out of the box with standard Home Assistant cards, installing these popular community cards via HACS (Home Assistant Community Store) is recommended to replicate the visual aesthetics of the official BYD app:

1.  **`power-flow-card-plus`**: Renders the live power flow diagram with animated dots showing power direction.
    *   **GitHub Repository**: [flixlix/power-flow-card-plus](https://github.com/flixlix/power-flow-card-plus)
    *   **One-Click Install**: [![Open HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=flixlix&repository=power-flow-card-plus&category=plugin)
2.  **`card-mod`**: Injects custom CSS to achieve glassmorphic borders, background blurs, and glows.
    *   **GitHub Repository**: [thomasloven/lovelace-card-mod](https://github.com/thomasloven/lovelace-card-mod)
    *   **One-Click Install**: [![Open HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=thomasloven&repository=lovelace-card-mod&category=plugin)
3.  **`apexcharts-card`**: Renders the multi-duration real-time power convergence charts.
    *   **GitHub Repository**: [RomRider/apexcharts-card](https://github.com/RomRider/apexcharts-card)
    *   **One-Click Install**: [![Open HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=RomRider&repository=apexcharts-card&category=plugin)
4.  **`mini-graph-card`**: Generates sparklines and real-time trend graphs.
    *   **GitHub Repository**: [kalkih/mini-graph-card](https://github.com/kalkih/mini-graph-card)
    *   **One-Click Install**: [![Open HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=kalkih&repository=mini-graph-card&category=plugin)

> [!NOTE]
> **Visual Progress Bars & Sliders**: Home Assistant natively supports beautiful visual progress bars and sliders out of the box using the built-in **`tile`** card with **`slider`** features! Installing deprecated custom card helpers like `bar-card` is no longer necessary or recommended.

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
