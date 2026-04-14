# ☀️ Toorox ForeSight HA Add-on

**A Neural Extension for Solar Forecast ML (SFML)**

The Toorox ForeSight HA Add-on integrates the **TFS HA G4v2 Transformer 4 Head** – a highly specialized neural network with 20.5 million parameters – as an optional "brain extension" for your existing Solar Forecast ML (SFML) setup.

The model acts as a "third expert opinion" within your ensemble. It helps refine forecast quality, particularly during volatile weather conditions and seasonal transitions, by identifying complex atmospheric patterns that go beyond conventional regression models.

---
**Fuel my late-night ideas with a coffee? I'd really appreciate it — keep this project running!**

<a href='https://ko-fi.com/Q5Q41NMZZY' target='_blank'><img height='36' style='border:0px;height:36px;' src='https://ko-fi.com/img/githubbutton_sm.svg' border='0' alt='Buy Me a Coffee' /></a>

---

## 🚀 Why use ForeSight?

| ✅ Ideal for you if... | ❌ Not suitable if... |
|---|---|
| You have SFML installed and working | You don't have SFML installed (Requirement!) |
| Your hardware has at least 8 GB RAM | You run HA on a RPi 4 with only 4 GB RAM |
| You want more precise forecasts during complex cloud cover | Your installation has an extremely exotic configuration |
| You are looking for a robust fallback layer | You need an extremely resource-saving system |

---

## 🧠 How it works

The Add-on operates as an intelligent extension in the background of your SFML system:

1. **Trigger** — 45 minutes before sunrise, SFML starts the forecast process.
2. **Consulting** — SFML requests an assessment from the TFS model based on current weather data and historical performance.
3. **Blending** — SFML combines this assessment with the existing ensemble (LSTM, Ridge, etc.).
4. **Output** — The optimized values flow directly into the existing SFML forecasts.

> [!CAUTION]
> **No standalone sensors:** This Add-on does **not** create any entities or sensors in Home Assistant. The generated values are **raw data** intended solely for the SFML ensemble. They are not usable as forecasts without the processing and calibration performed by SFML.

---

## 🔧 Setup

### Prerequisites

- **Solar Forecast ML (SFML)** installed and configured.
- At least **8 GB RAM** recommended for smooth inference.
- Home Assistant **2026.3.0** or newer.

### Installation

1. Go to **Settings → Add-ons → Add-on Store**.
2. Click the three dots in the top right **⋮ → Repositories**.
3. Add the repository URL: `https://github.com/Zara-Toorox/toorox-foresight-ha`
4. **Toorox ForeSight** will appear in the store → **Install**.
5. **Start** the Add-on.

> The Add-on automatically detects your SFML installation via the internal Docker network. No manual configuration is required within the Add-on interface.

---

## 📈 Automated Learning

ForeSight continuously optimizes itself to perfectly match your location:

| Interval | Action |
|-----------|-------------|
| **Every 6 hours** | Comparison of model values with the actual production data of your system. |
| **Weekly** | Fine-tuning of internal weighting (bias correction) for your local hardware. |
| **Quarterly** | Basic recalibration against seasonal drift (e.g., changes in sun position throughout the year). |

---

## ⚙️ Technical Details

| Property | Value |
|-------------|------|
| Model | **TFS HA G4v2 Transformer 4 Head** |
| Parameters | 20,465,232 |
| Forecast Horizon | 72 hours (3 days) |
| Data Format | JSON Raw Output (Inference only) |
| Memory Usage | ~400 MB RAM (during inference) |
| Port | 8780 (internal communication port) |

---

## 📄 License

Proprietary Non-Commercial — free for personal and educational use. See [LICENSE](LICENSE).

---

*Powered by Toorox ForeSight AI — Local intelligence for precise solar forecasts.*