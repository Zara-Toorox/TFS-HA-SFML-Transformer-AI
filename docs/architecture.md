# Architecture

The full architecture document, decision log, feature mapping ZARA ↔ SFML,
phase plan, API specification, and risk register lives in the Notfallkoffer:

**`/srv/share/Notfallkoffer/23_toorox_foresight_ha_addon.md`**

That document is the **source of truth** for this project. Every design
decision is captured there with rationale. If you are continuing development
across sessions, read it first.

## Quick architecture summary

```
┌────────────────────────────────────────────────────────────┐
│  Home Assistant Container                                   │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐  │
│  │  SFML (Custom Component)                             │  │
│  │  • Master of solar_forecast.db                      │  │
│  │  • 15-step EOD workflow with daily learning         │  │
│  │  • Hubble ensemble: LSTM + Ridge + Physics + MLP    │  │
│  │  • If TFS detected: 3-way blend with ZARA           │  │
│  └─────────────────────────────────────────────────────┘  │
│                          │                                  │
│                          │ HTTP POST /predict (try/fallback)│
│                          ▼                                  │
│  ┌─────────────────────────────────────────────────────┐  │
│  │  Toorox ForeSight HA Add-on (this repo)             │  │
│  │  • ZARA Transformer 20.5M params                    │  │
│  │  • Read-only mount of SFML's solar_forecast.db      │  │
│  │  • POST /predict + GET /health, nothing else        │  │
│  │  • No UI, no config, no own database, no scheduler  │  │
│  └─────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────┘
```

## Repository layout

```
12_TFS_HA/
├── README.md                       # User-facing project doc
├── CHANGELOG.md                    # Repo-level changelog
├── LICENSE                         # MIT
├── hacs.json                       # HACS metadata
├── .gitignore
├── docs/
│   └── architecture.md             # This file (pointer to Doc 23)
└── toorox_foresight_ha/            # Add-on slug directory
    ├── config.yaml                 # HA Add-on manifest
    ├── Dockerfile
    ├── build.yaml
    ├── run.sh
    ├── requirements.txt
    ├── DOCS.md                     # Add-on user docs (shown in HA UI)
    ├── CHANGELOG.md                # Add-on release notes
    ├── icon.svg                    # (TODO: add)
    ├── toorox_foresight/           # Python package
    │   ├── __init__.py
    │   ├── model/                  # ZARA Transformer (cherry-picked)
    │   │   ├── __init__.py
    │   │   ├── transformer.py
    │   │   ├── components.py
    │   │   ├── forecast_assembler.py
    │   │   └── forecast_validator.py
    │   ├── physics/
    │   │   ├── __init__.py
    │   │   └── solar.py
    │   ├── data/
    │   │   ├── __init__.py
    │   │   └── features.py         # ZARA's 38-feature schema
    │   └── sfml_adapter/           # NEW (Phase 2)
    │       └── __init__.py
    └── scripts/
        └── serve_forecast.py       # Minimal /health server (Phase 0/1)
```

## Phase status

| Phase | Status | Notes |
|---|---|---|
| 0. Repository scaffold | ✅ Done | This commit |
| 1. TFS strip-down + model download | 🚧 In progress | Skeleton done, model download mechanism pending |
| 2. SFML adapter | ⏳ Pending | Read-only DB layer |
| 3. /predict endpoint | ⏳ Pending | Wires adapter into ZARA inference |
| 4. SFML detection layer | ⏳ Pending | SFML side: detect TFS Add-on |
| 5. SFML schema migration | ⏳ Pending | Add zara_kwh / zara_p10/p90 columns |
| 6. SFML 3-way blend | ⏳ Pending | The actual integration |
| 7. EOD bucket weight learning | ⏳ Pending | Adaptive weights for ZARA |
| 8. HA quantile sensors | ⏳ Pending | Expose P10/P90 to HA |
| 9. PyArmor build + deploy | ⏳ Pending | Production deployment |
| 10. Live test phase | ⏳ Pending | Multi-day validation |

## Cross-references

- **Standalone Toorox ForeSight Docker:** `/home/zara/Github/11_toorox_foresight/`
  + `/srv/share/Notfallkoffer/22_toorox_foresight.md`
- **Solar Forecast ML:** `/home/zara/Github/01_solar_forecast_ml/`
- **This project (HA Add-on):** `/home/zara/Github/12_TFS_HA/`
  + `/srv/share/Notfallkoffer/23_toorox_foresight_ha_addon.md`
