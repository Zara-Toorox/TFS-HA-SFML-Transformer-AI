#!/usr/bin/with-contenv bashio
set -e

bashio::log.info "================================================================"
bashio::log.info "  Toorox ForeSight HA Add-on — ZARA brain extension"
bashio::log.info "================================================================"

SFML_DB="${SFML_DB_PATH:-/config/solar_forecast_ml/solar_forecast.db}"

if [ ! -f "$SFML_DB" ]; then
    bashio::log.error ""
    bashio::log.error "Solar Forecast ML database not found at:"
    bashio::log.error "  $SFML_DB"
    bashio::log.error ""
    bashio::log.error "Toorox ForeSight HA is an EXTENSION for SFML and cannot run"
    bashio::log.error "without it. Please install Solar Forecast ML first via HACS,"
    bashio::log.error "configure your panels and let it produce at least one forecast,"
    bashio::log.error "then start this Add-on again."
    bashio::log.error ""
    exit 1
fi

bashio::log.info "SFML database found at $SFML_DB"

mkdir -p /data/checkpoints

bashio::log.info "Running bootstrap decrypt (ZARA model + ERA5)..."
export PYTHONPATH=/app
cd /app

CORES=$(nproc)
export OMP_NUM_THREADS=$CORES
export MKL_NUM_THREADS=$CORES
export OPENBLAS_NUM_THREADS=$CORES
export NUMEXPR_NUM_THREADS=$CORES
bashio::log.info "CPU cores detected: $CORES — threads pinned to $CORES"

if ! python3 -m toorox_foresight._bootstrap_decrypt; then
    bashio::log.error ""
    bashio::log.error "Bootstrap decryption FAILED."
    bashio::log.error "The add-on image is likely broken (missing or corrupt .enc seeds)."
    bashio::log.error ""
    exit 1
fi

if [ ! -f /data/checkpoints/pretrained_full.safetensors ]; then
    bashio::log.error "ZARA checkpoint missing at /data/checkpoints/pretrained_full.safetensors after decrypt"
    exit 1
fi

bashio::log.info "ZARA checkpoint ready at /data/checkpoints/pretrained_full.safetensors"

if [ -f /data/era5_climatology.json ]; then
    bashio::log.info "ERA5 climatology ready at /data/era5_climatology.json"
else
    bashio::log.info "No ERA5 climatology — running as g4 (no ERA5 features)"
fi

bashio::log.info "Starting ZARA inference server on port ${API_PORT:-8780}..."
exec python3 scripts/serve_forecast.py
