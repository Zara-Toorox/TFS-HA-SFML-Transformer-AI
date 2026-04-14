<h1 align="center">Toorox ForeSight HA — TFS G4v2</h1>

<p align="center">
  <strong>The Neural Brain Extension for Solar Forecast ML (SFML) — 20.5M Parameter Transformer, 100% Local, 100% Private</strong>
</p>

<p align="center">
  <a href="https://github.com/Zara-Toorox/TFS-HA-SFML-Transformer-AI"><img src="https://img.shields.io/badge/version-1.0.1-blue.svg" alt="Version"></a>
  <a href="https://www.home-assistant.io/addons/"><img src="https://img.shields.io/badge/HA%20Add--on-Repository-41BDF5.svg" alt="HA Add-on"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-Proprietary%20Non--Commercial-green.svg" alt="License"></a>
  <img src="https://img.shields.io/badge/platform-amd64%20%7C%20aarch64-lightgrey.svg" alt="Platform">
</p>

Toorox ForeSight HA integrates the **TFS HA G4v2 Transformer 4-Head** — a specialized neural network with **20.5 million parameters** — as an optional brain extension for your existing Solar Forecast ML (SFML) installation. It acts as a third expert opinion within the SFML ensemble, refining forecast quality during volatile weather and seasonal transitions by capturing complex atmospheric patterns beyond conventional regression.

**Fuel my late-night ideas with a coffee? I'd really appreciate it — keep this project running!**

<a href='https://ko-fi.com/Q5Q41NMZZY' target='_blank'><img height='36' style='border:0px;height:36px;' src='https://ko-fi.com/img/githubbutton_sm.svg' border='0' alt='Buy Me a Coffee' /></a>

[Website & Documentation](https://zara-toorox.github.io/index.html)

---

## 🧠 Stop Guessing. Start Reasoning.

<img src="toorox_foresight_ha/logo.png" alt="Toorox ForeSight HA — AI Brain Extension for SFML" align="left" width="250">

While traditional solar models extrapolate, the TFS G4v2 Transformer **reasons** across the entire 72-hour weather horizon at once. Trained on 360 European PV sites and 13 years of ERA5 climate normals, it sees the relationships between cloud dynamics, temperature gradients, and radiation patterns that regression-based models simply cannot encode.

The Add-on runs entirely on your Home Assistant hardware. No cloud, no subscriptions, no data leakage — just a dedicated neural co-processor for your existing SFML ensemble, trained once on real PV physics and continuously fine-tuned on your individual roof. The pretrained model is delivered ready-to-use (AES-256 encrypted, PyArmor-protected), and fine-tunes itself on your SFML production history on first start.

<br clear="both">

---

## 🚀 Why use ForeSight?

| ✅ Ideal for you if... | ❌ Not suitable if... |
|---|---|
| You have SFML installed and working | You don't have SFML installed (hard requirement!) |
| Your hardware has at least 8 GB RAM | You run HA on a RPi 4 with only 4 GB RAM |
| You want more precise forecasts during complex cloud cover | Your installation has an extremely exotic configuration |
| You are looking for a robust fallback layer | You need an extremely resource-saving system |

---

## 🔁 How it works

The Add-on operates as an intelligent extension in the background of your SFML system:

1. **Trigger** — 45 minutes before sunrise, SFML starts the forecast process.
2. **Consulting** — SFML requests an assessment from the TFS model based on current weather data and historical performance.
3. **Blending** — SFML combines this assessment with the existing ensemble (LSTM, Ridge, Physics backbone).
4. **Output** — The optimized values flow directly into the existing SFML forecasts and sensors.

> [!CAUTION]
> **No standalone sensors:** This Add-on does **not** create any entities or sensors in Home Assistant. The generated values are **raw data** intended solely for the SFML ensemble. They are not usable as forecasts without the processing and calibration performed by SFML.

---

## 🧪 The G4v2 Transformer Architecture

| Component | Specification |
|---|---|
| Model | **TFS HA G4v2 Transformer 4-Head** |
| Parameters | **20,465,232** |
| Encoder / Decoder Layers | 6 / 4 |
| Attention Heads | 8 (Multi-Head) |
| Hidden Dim (d_model) | 256 |
| Feed-Forward Dim | 1,024 |
| Mixture-of-Experts | 4 experts, top-2 routing |
| Positional Encoding | RoPE (Rotary) |
| Normalization | RMSNorm + SwiGLU activation |
| Quantiles (Uncertainty) | P10 / P50 / P90 |
| Forecast Horizon | 72 hours |
| Features | 47 per hour (weather, physics, ERA5 climate, temporal) |

The architecture was pre-trained on a curated dataset of 360 European PV installations across 13 years of ERA5 climate data — giving it a physics-grounded prior before it ever sees your roof.

---

## 📈 Automated Learning

ForeSight continuously optimizes itself to match your location:

| Interval | Action |
|---|---|
| **First Start** | Fine-tuning on the full SFML production history (typically 80%+ val-loss reduction) |
| **Every 6 hours** | Drift detection: compares recent forecasts with actual production |
| **Nightly (02:00)** | Incremental fine-tuning on new production data |
| **Quarterly** | Basic recalibration against the original pretrained baseline (prevents catastrophic forgetting) |

---

## 🔧 Installation

### Prerequisites

- **Solar Forecast ML (SFML)** installed and configured — the Add-on reads its SQLite database to seed itself.
- At least **8 GB RAM** recommended.
- Home Assistant **2026.3.0** or newer.

### Installation Steps

1. Open **Settings → Add-ons → Add-on Store**.
2. Click the three dots in the top right: **⋮ → Repositories**.
3. Add this repository URL:
   ```
   https://github.com/Zara-Toorox/TFS-HA-SFML-Transformer-AI
   ```
4. **Toorox ForeSight** will appear in the store → **Install**.
5. **Start** the Add-on.

> The Add-on automatically detects your SFML installation via the Home Assistant `/config/` share. No manual configuration is required. Panel groups, location, and timezone are seeded directly from the SFML configuration.

---

## 🛡️ Your Data Stays Yours — A Privacy Commitment

Toorox ForeSight was designed around the same non-negotiable principle as SFML: **your data never leaves your home.**

- **No Large Language Models involved** — no ChatGPT, Claude, Gemini, or Grok in the loop. The TFS Transformer is a custom architecture running fully on your CPU.
- **No telemetry, no analytics, no tracking** — no background callbacks, no error reporting endpoints.
- **Fully offline-capable** — after the initial Docker image build, the Add-on operates entirely within your local network. Weather data is the only external dependency (public Open-Meteo endpoints, coordinates only).

> In short: What happens in your Home Assistant, stays in your Home Assistant.

---

## 🔐 Protected Code Notice

The machine-learning core of this Add-on is obfuscated with an official **PyArmor** license, and the pretrained model weights (~79 MB) are AES-256 encrypted inside the distribution image.

**Why is the code protected?**

1. **Protection against AI Training** — to prevent the source code and model weights from being ingested by ChatGPT, Claude, Gemini, or other Large Language Models without permission.
2. **Intellectual Property Protection** — the TFS G4v2 architecture and its pretrained weights represent substantial R&D investment.
3. **Open Source with Limits** — free for personal use, but the source code is proprietary and subject to a Non-Commercial License.
4. **Unfortunately necessary** — prior releases have been copied without consent, repackaged into commercial apps, and fed into LLMs. I reluctantly feel compelled to protect the source code and weights.
5. **Transparency** — if you have a legitimate interest, I'm happy to discuss the internals. Reach out via GitHub Issues or Discussions.

The protection has **no impact on functionality**. The Add-on behaves identically to an unprotected build.

*Toorox ForeSight HA — Copyright (C) 2026 Zara-Toorox · Protected with PyArmor 9.2.4 and AES-256*

---

## 📄 License

Proprietary Non-Commercial — free for personal and educational use. See [LICENSE](LICENSE).

---

## 👤 Credits

**Developer:** [Zara-Toorox](https://github.com/Zara-Toorox)

Thanks to Simon42 and the users & contributors of the German-speaking HA forum "simon42" for their testing, feedback, and discussion.

**Support-Forum:** [simon42 Community](https://community.simon42.com/t/ueber-die-kategorie-einrichtung-hilfe/79817) | [Issues](https://github.com/Zara-Toorox/TFS-HA-SFML-Transformer-AI/issues) | [Discussions](https://github.com/Zara-Toorox/TFS-HA-SFML-Transformer-AI/discussions)

---

*Developed with ☀️, late-night passion, and a stiff glass of Grog during Germany's wintertime.*
