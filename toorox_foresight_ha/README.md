# Toorox ForeSight HA — Phoenix V2

Welcome to Toorox ForeSight HA.

TFS is the first transformer-based forecast service in the Toorox solar stack
and is delivered as a Home Assistant add-on. It extends the existing Solar
Forecast ML Hubble AI Stack with a pretrained 4-head Transformer AI and is
designed as an operational ensemble component. TFS is not intended to operate
as a standalone forecast service.

## Hardware

Recommended practical split:

- Home Assistant host:
  - runtime inference
  - forecast serving
  - LoRA finetuning
- dedicated GPU host:
  - larger model experiments
  - checkpoint evaluation
  - longer offline training runs

The current project layout intentionally keeps runtime operation lightweight and
separates heavier model work from the production add-on.

## Finetune

Finetuning is intended as a lightweight site-specific recalibration step, not
as full retraining of the base model.

Current operational profile from the code:

- maximum `20` epochs
- early stopping patience `5`
- minimum dataset size `50` samples
- validation split `20 %`
- LoRA rank `8`

Practical guidance:

- finetune is designed as a short operational job
- typical runs should be measured in minutes, not many hours
- actual duration depends mainly on:
  - number of available samples
  - host CPU performance
  - storage performance
  - current early-stopping behavior

Typical commands:

```bash
python scripts/finetune.py
python scripts/finetune.py --force
```

## Purpose

TFS adds a learned forecast component on top of the existing deterministic and
statistical forecast stack.

The runtime focuses on:

- robust short- and mid-range solar forecasting
- quantile output (`p10`, `p50`, `p90`) for downstream uncertainty handling
- site-specific adaptation through LoRA finetuning
- integration into the existing SFML and Home Assistant environment

TFS is especially useful in conditions where pure physics or standard models
tend to become less reliable, such as diffuse light, shifting cloud fields, or
more complex shading situations.

## Runtime Overview

At runtime, TFS combines:

- historical production and weather context from SFML
- blended forecast weather data
- astronomy and panel geometry context
- a frozen Phoenix base model
- an optional customer-specific LoRA adapter
- physics-based post-processing and plausibility guards

Forecast runs and quantiles are persisted in the TFS state database and exposed
through a compact internal API.

## Model Profile

Current Phoenix V2 runtime profile:

- transformer-based sequence model
- 168 hours historical context
- 72 hours forecast horizon
- quantile output: `p10`, `p50`, `p90`
- gain-learning relative to a physics baseline
- LoRA-based site-specific adaptation with a frozen base model
- verified parameter count: `11,906,051`

The exact internal implementation details are intentionally not fully disclosed
here.

## Main Settings

The runtime is configured through add-on options and `TFS_*` environment
variables.

Most relevant operational settings:

- location:
  - `latitude`
  - `longitude`
  - `timezone`
- forecast schedule:
  - `forecast_times`
- nightly finetune time:
  - `finetune_time`
- automatic finetune:
  - `auto_finetune`
- log level:
  - `log_level`
- model and state paths:
  - `TFS_MODEL_DIR`
  - `TFS_STATE_DIR`

Important current default behavior:

- forecast cache TTL: `6h`
- nightly finetune enabled by default
- finetune uses early stopping
- base model and LoRA state are managed separately

## API

```text
GET  /health
POST /api/forecast/run?forecast_type=sfml
GET  /api/forecast/quantiles?date=YYYY-MM-DD
POST /api/lora/refinetune[?force=true]
GET  /api/admin/status
```

Intended use:

- `/health` for add-on health and version checks
- `/api/forecast/run` for the SFML-facing forecast contract
- `/api/forecast/quantiles` for quantile-aware downstream consumers
- `/api/lora/refinetune` for manual recalibration
- `/api/admin/status` for runtime and adapter state inspection

The add-on listens internally on port `8780`.

## Data Sources

TFS currently uses:

- SFML production and historical weather data in read-only mode
- forecast weather data from:
  - Open-Meteo
  - BrightSky

Runtime output is written into the TFS state area, especially:

- forecast runs
- hourly quantiles
- adapter and runtime state

## Deployment Notes

TFS is packaged as a Home Assistant add-on.

Relevant runtime paths:

- base models:
  - `/app/models/base`
- LoRA adapters:
  - `/config/toorox_foresight_ha/lora`
- TFS state database:
  - `/config/toorox_foresight_ha/tfs.db`

Release builds use the protected staging path and ship encrypted base-model
artifacts for runtime loading.

## Docker

Minimal example of a compose.yaml file for running in a docker-container:
```yaml
services:
  toorox-foresight:
    container_name: toorox-foresight
    build: 
      context: https://github.com/Zara-Toorox/TFS-HA-SFML-Transformer-AI.git
      dockerfile: toorox_foresight_ha/Dockerfile
      args:
        BUILD_FROM: "ubuntu:24.04"  # or 22.04
        APP_SOURCE_ROOT: ./toorox_foresight_ha
    restart: unless-stopped
    ports:
      - "8780:8780"
    volumes:
      - ./<full or relaive path to homeassit config>:/config
    environment:
      - TZ=Europe/Berlin
      - TFS_TIMEZONE_STR=Europe/Berlin
      - TFS_LATITUDE=53.0  # enter your latitde
      - TFS_LONGITUDE=12.0  # enter your longitude
      - TFS_STATE_DIR=/config/toorox_foresight_ha
```
With a compose.yaml file like this, docker handles automatically the pulling of the rpository and the building of the container.

## License

Proprietary. © 2026 Zara-Toorox.
