"""Central configuration for Toorox ForeSight HA. @zara

Loads HA add-on options from /data/options.json, provides typed access
and path helpers for the state directory.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ForecastTiming(BaseSettings):
    """Forecast and finetune schedule configuration. @zara"""

    model_config = SettingsConfigDict(extra="ignore")

    forecast_times: list[str] = Field(default_factory=lambda: ["00:30", "sunrise-45"])
    finetune_time: str = "00:00"
    auto_finetune: bool = True
    forecast_cache_ttl_seconds: int = 6 * 3600


class ModelArchitecture(BaseSettings):
    """Transformer architecture hyperparameters. @zara"""

    model_config = SettingsConfigDict(extra="ignore")

    d_model: int = 256
    n_heads: int = 8
    n_encoder_layers: int = 6
    n_decoder_layers: int = 4
    d_ff: int = 1024
    patch_size: int = 6
    seq_len: int = 168
    horizon: int = 72
    n_temporal_features: int = 28
    n_weather_variates: int = 10
    n_physics_features: int = 8
    n_geometry_features: int = 3
    n_quantiles: int = 3
    max_groups: int = 8
    dropout: float = 0.1
    use_rope: bool = True
    use_flash_attention: bool = True


class TrainingConfig(BaseSettings):
    """Training hyperparameters for pretrain and finetune. @zara"""

    model_config = SettingsConfigDict(extra="ignore")

    pretrain_lr: float = 1e-4
    pretrain_batch_size: int = 32
    pretrain_max_epochs: int = 100
    pvgis_peak_power_kwp: float = 5.0
    pretrain_warmup_epochs: int = 10
    pretrain_weight_decay: float = 0.01
    pretrain_grad_clip: float = 1.0

    curriculum_horizons: list[int] = Field(default_factory=lambda: [24, 48, 72])
    curriculum_epoch_boundaries: list[int] = Field(default_factory=lambda: [8, 25, 100])

    finetune_lr: float = 5e-5
    finetune_max_epochs: int = 20
    finetune_early_stopping_patience: int = 5
    finetune_min_samples: int = 50
    finetune_validation_ratio: float = 0.2

    lora_rank: int = 8
    lora_alpha: int = 16
    lora_dropout: float = 0.05

    loss_quantile_weight: float = 0.60
    loss_calibration_weight: float = 0.15
    loss_monotonic_weight: float = 0.05
    loss_temporal_weight: float = 0.10
    loss_physics_weight: float = 0.10

    augmentation_flag_probability: float = 0.10
    mixup_alpha: float = 0.2
    noise_std: float = 0.01


class WeatherConfig(BaseSettings):
    """Weather pipeline configuration. @zara"""

    model_config = SettingsConfigDict(extra="ignore")

    open_meteo_url: str = "https://api.open-meteo.com/v1/forecast"
    open_meteo_models: list[str] = Field(
        default_factory=lambda: ["icon_seamless", "gfs_seamless", "ecmwf_ifs025"]
    )
    brightsky_url: str = "https://api.brightsky.dev/weather"
    cache_ttl_seconds: int = 3600
    request_timeout_seconds: int = 20
    fetch_horizon_hours: int = 96


class SFMLConfig(BaseSettings):
    """Solar Forecast ML database integration. @zara"""

    model_config = SettingsConfigDict(extra="ignore")

    db_path: Path = Path("/config/solar_forecast_ml/solar_forecast.db")
    readonly: bool = True
    query_timeout_seconds: int = 15


class PhysicsConfig(BaseSettings):
    """Physics baseline constants (aligned with SFML PhysicsEngine). @zara"""

    model_config = SettingsConfigDict(extra="ignore")

    temp_coefficient: float = -0.004
    stc_temperature: float = 25.0
    noct: float = 45.0
    noct_irradiance: float = 800.0
    noct_ambient: float = 20.0
    albedo: float = 0.2
    system_efficiency: float = 0.90
    gain_clamp_min: float = 0.0
    gain_clamp_max: float = 1.3
    baseline_min_threshold_kwh: float = 0.02


class TFSSettings(BaseSettings):
    """Root settings aggregator. Loads from HA add-on options.json. @zara"""

    model_config = SettingsConfigDict(env_prefix="TFS_", extra="ignore")

    latitude: float | None = None
    longitude: float | None = None
    timezone_str: str = "Europe/Berlin"
    log_level: str = "INFO"

    state_dir: Path = Path(os.environ.get("TFS_STATE_DIR", "/config/toorox_foresight_ha"))
    model_dir: Path = Path(os.environ.get("TFS_MODEL_DIR", "/app/models"))

    api_host: str = "0.0.0.0"
    api_port: int = 8780

    timing: ForecastTiming = Field(default_factory=ForecastTiming)
    model: ModelArchitecture = Field(default_factory=ModelArchitecture)
    training: TrainingConfig = Field(default_factory=TrainingConfig)
    weather: WeatherConfig = Field(default_factory=WeatherConfig)
    sfml: SFMLConfig = Field(default_factory=SFMLConfig)
    physics: PhysicsConfig = Field(default_factory=PhysicsConfig)

    @property
    def state_db_path(self) -> Path:
        return self.state_dir / "tfs.db"

    @property
    def lora_dir(self) -> Path:
        return self.state_dir / "lora"

    @property
    def base_model_dir(self) -> Path:
        return self.model_dir / "base"

    @property
    def status_file(self) -> Path:
        return self.state_dir / "state.json"


def load_settings() -> TFSSettings:
    """Load settings from HA options.json + environment. @zara"""
    settings = TFSSettings()

    options_path = os.environ.get("TFS_OPTIONS_JSON")
    if options_path and Path(options_path).exists():
        with open(options_path) as f:
            options: dict[str, Any] = json.load(f)
        for key in ("latitude", "longitude", "log_level"):
            if key in options and options[key] is not None:
                setattr(settings, key, options[key])
        if "forecast_times" in options and options["forecast_times"]:
            settings.timing.forecast_times = list(options["forecast_times"])
        if "finetune_time" in options:
            settings.timing.finetune_time = options["finetune_time"]
        if "auto_finetune" in options:
            settings.timing.auto_finetune = bool(options["auto_finetune"])

    settings.state_dir.mkdir(parents=True, exist_ok=True)
    settings.lora_dir.mkdir(parents=True, exist_ok=True)

    return settings


_settings: TFSSettings | None = None


def get_settings() -> TFSSettings:
    """Return cached settings instance. @zara"""
    global _settings
    if _settings is None:
        _settings = load_settings()
    return _settings
