# Changelog

All notable changes to the Toorox ForeSight HA Add-on.

## [Unreleased]

### Added
- Phase 0: Repository scaffold (08.04.2026)
- HA Add-on manifest with `config:ro` mount
- Cherry-picked ZARA model code from standalone TFS (`model/`, `physics/`, `data/features.py`)
- Minimal `serve_forecast.py` skeleton with `/health` endpoint
- SFML database verification on startup — Add-on refuses to start without SFML
- Schema version probing for forward compatibility

### Pending
- Phase 1: Model download mechanism from GitHub Release
- Phase 2: SFML adapter (read-only DB layer)
- Phase 3: `/predict` endpoint with full inference pipeline
- Phase 4: SFML-side detection layer
- Phase 5: SFML schema migration (zara_kwh, zara_p10/p90, ensemble_group_weights extension)
- Phase 6: SFML 3-way blend integration
- Phase 7: EOD bucket weight learning for ZARA
- Phase 8: HA quantile sensors
- Phase 9: PyArmor build + HA deployment
- Phase 10: Live test phase

## [1.0.0] — Not yet released

Initial public release planned after Phases 0-10 complete.
