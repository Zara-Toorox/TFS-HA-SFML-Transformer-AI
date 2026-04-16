# Changelog — Add-on slug `toorox_foresight_ha`

This file tracks Add-on releases visible in the HA Supervisor UI.
The repo-level [CHANGELOG.md](../CHANGELOG.md) tracks the broader project.

## [1.2.3] — 2026-04-16

**Who is affected:**
Every user who has ever changed their panel configuration in SFML — e.g.
corrected a tilt or azimuth value, renamed a group, or experienced temporary
sensor trouble during SFML's astronomy caching.

### What was wrong
TFS automatically discovers your panel groups from SFML. SFML stores one entry
per group per day and keeps historical configuration instead of overwriting it.

If your setup ever changed — say you had two groups at one azimuth for a few
days, then corrected them — SFML's history contains both versions side by side.

TFS v1.2.1 and earlier treated every unique tilt/azimuth combination as a
separate group. The result: two real groups could turn into four (or more)
ghost groups in TFS's internal model.

### Impact on the Transformer
This was more than cosmetic. The consequences were:

- Model architecture was built with the inflated group count — for example,
  four output heads instead of two
- Training was noisy: duplicate groups shared the same name but had different
  orientations; the model received the same actual yields for both, learning an
  inconsistent mapping
- Weather data was fetched using only the first group's orientation —
  whichever version happened to be enumerated first
- Forecast responses to SFML contained duplicate group names; SFML's blend
  logic kept only one of each by name, effectively discarding half of TFS's
  per-group predictions

SFML's ensemble blend masked the problem well enough that it wasn't immediately
visible — but forecast quality was quietly degraded, and anyone who had ever
reconfigured their panels was running a model that didn't match their actual
setup.

### What v1.2.3 does
The group discovery now reads only the most recent snapshot of each panel
group. Historical rows from past configurations are ignored.

**Result:** two physical groups produce exactly two TFS groups, with the
current orientation and capacity — no matter how many times the configuration
has changed.

### ⚠️ Important: First-Start Fine-Tune After Update
Because the Transformer's architecture depends on the group count, installations
that were running with inflated groups need to re-initialize the model once
after updating. TFS handles this automatically:

1. Update via the HA Add-on Store (v1.2.1 → v1.2.3)
2. Restart the add-on
3. TFS detects the changed group count and triggers a new fine-tuning run
4. First-run fine-tune duration: 10–45 minutes depending on CPU
5. Do not interrupt the fine-tune — aborting corrupts the checkpoint

After fine-tuning completes, SFML automatically picks up the improved per-group
predictions on the next forecast cycle. No manual action required.

### 🙏 Thanks
Big thanks to the customer who flagged the duplicate-group issue in the forum
([simon42](https://community.simon42.com/)) and provided a database dump for
diagnosis. This fix would have taken much longer to find without that concrete
evidence.

**Big thanks to:**

- Kaysen889
- Ottokar
- Joachim

## [1.2.0] — 2026-04-16

### Azimuth Compatibility Fix
Open-Meteo API rejected weather requests with HTTP 400 for panels not facing
exactly south. TFS now converts compass azimuth (0° = North) to the Open-Meteo
convention (0° = South, ±180° range) before every request. No configuration
change required.

## [1.0.x] — 2026-04-14

### Phase 0 — Repository scaffold
- Initial Add-on manifest (`config.yaml`)
- Dockerfile based on `amd64-base-debian:bookworm`
- Minimal `serve_forecast.py` with `/health` endpoint
- Refuses to start without SFML database
- Cherry-picked ZARA model code from standalone TFS project

## Format

This project follows [Keep a Changelog](https://keepachangelog.com/) and
[Semantic Versioning](https://semver.org/). Pre-1.0 releases are unstable.
