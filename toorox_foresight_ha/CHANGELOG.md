# Changelog — Add-on slug `toorox_foresight_ha`

This file tracks Add-on releases visible in the HA Supervisor UI.
The repo-level [CHANGELOG.md](../CHANGELOG.md) tracks the broader project.

## [Unreleased]

### Phase 0 — Repository scaffold (08.04.2026)
- Initial Add-on manifest (`config.yaml`)
- Dockerfile based on `amd64-base-debian:bookworm`
- Minimal `serve_forecast.py` with `/health` endpoint
- Refuses to start without SFML database
- Cherry-picked ZARA model code from standalone TFS project

### Pending phases (1-10)
See [docs/architecture.md](../docs/architecture.md) for the full plan.

## Format

This project follows [Keep a Changelog](https://keepachangelog.com/) and
[Semantic Versioning](https://semver.org/). Pre-1.0 releases are unstable.
