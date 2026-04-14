# ******************************************************************************
# @copyright (C) 2026 Zara-Toorox - Toorox ForeSight HA
# * This program is protected by a Proprietary Non-Commercial License.
# 1. Personal and Educational use only.
# 2. COMMERCIAL USE AND AI TRAINING ARE STRICTLY PROHIBITED.
# 3. Clear attribution to "Zara-Toorox" is required.
# * Full license terms: https://github.com/Zara-Toorox/toorox-foresight-ha/blob/main/LICENSE
# ******************************************************************************

"""Central configuration for Toorox ForeSight. @zara"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field


class PanelGroup(BaseModel):
    """Single panel group configuration. @zara"""
    name: str = "default"
    tilt: float = 30.0
    azimuth: float = 180.0
    peak_power_kw: float = 10.0
    module_count: int = 20
    efficiency_stc: float = 0.21


class SensorMapping(BaseModel):
    """Maps Home Assistant entity IDs to ForeSight data fields. @zara"""
    power_w: str = ""
    yield_today_kwh: str = ""
    group1_kwh: str = ""
    group2_kwh: str = ""
    group3_kwh: str = ""
    group4_kwh: str = ""
    temperature: str = ""
    humidity: str = ""
    radiation: str = ""
    lux: str = ""
    pressure: str = ""
    rain: str = ""
    wind: str = ""
    consumption_kwh: str = ""


class ModelConfig(BaseModel):
    """ZARA Transformer model hyperparameters. @zara"""
    d_model: int = 256
    n_heads: int = 8
    n_encoder_layers: int = 6
    n_decoder_layers: int = 4
    n_experts: int = 4
    top_k_experts: int = 2
    d_ff: int = 1024
    dropout: float = 0.2
    max_seq_len: int = 168
    forecast_horizon: int = 72
    patch_size: int = 6
    n_quantiles: int = 3
    quantiles: list[float] = [0.1, 0.5, 0.9]
    use_flash_attention: bool = True
    use_rope: bool = True
    activation: str = "swiglu"
    norm: str = "rmsnorm"
    compile_model: bool = True
    mixed_precision: str = "bfloat16"
    gradient_checkpointing: bool = True


class TrainingConfig(BaseModel):
    """Training hyperparameters. @zara"""
    batch_size: int = 64
    learning_rate: float = 1e-4
    weight_decay: float = 0.01
    warmup_steps: int = 500
    max_epochs: int = 200
    patience: int = 15
    min_delta: float = 1e-5
    grad_clip_norm: float = 1.0
    label_smoothing: float = 0.0
    scheduler: str = "cosine"
    optimizer: str = "adamw"
    physics_loss_weight: float = 0.15
    quantile_loss_weight: float = 0.85


class DatabaseConfig(BaseModel):
    """Database configuration. @zara"""
    url: str = "sqlite+aiosqlite:///data/foresight.db"
    echo: bool = False
    pool_size: int = 5


class SchedulerConfig(BaseModel):
    """Forecast scheduling configuration. @zara"""
    forecast_times: list[str] = ["00:30", "sunrise-45m"]
    reforecast_enabled: bool = True
    training_time: str = "02:00"
    training_day: str = "daily"


DEFAULT_WEATHER_SOURCES: list[str] = ["icon_seamless", "gfs_seamless", "ecmwf_ifs025"]


class ForeSightConfig(BaseModel):
    """Root configuration for Toorox ForeSight. @zara"""

    instance_name: str = "foresight"
    data_dir: Path = Path("data")
    log_level: str = "INFO"
    api_host: str = "0.0.0.0"
    api_port: int = 8780
    latitude: float = 52.65
    longitude: float = 13.49
    altitude: float = 34.0
    timezone: str = "Europe/Berlin"

    weather_sources: list[str] = DEFAULT_WEATHER_SOURCES

    panel_groups: list[PanelGroup] = [PanelGroup()]
    sensors: SensorMapping = SensorMapping()
    model: ModelConfig = ModelConfig()
    training: TrainingConfig = TrainingConfig()
    database: DatabaseConfig = DatabaseConfig()
    scheduler: SchedulerConfig = SchedulerConfig()

    model_config = ConfigDict(protected_namespaces=())

    @staticmethod
    def default_yaml_path() -> Path:
        """Return the default config.yaml location relative to data_dir. @zara"""
        return Path("data/config.yaml")

    @classmethod
    def load_from_yaml(cls, path: Path | str | None = None) -> "ForeSightConfig":
        """Load config from a yaml file; create defaults if missing. @zara

        On first run the file is created with default values so the user has
        a clean template to edit. Sensitive fields are persisted as-is —
        the API layer is responsible for redacting them on read.
        """
        target = Path(path) if path is not None else cls.default_yaml_path()
        if not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            instance = cls()
            instance.save_to_yaml(target)
            return instance

        with target.open("r", encoding="utf-8") as fh:
            raw: dict[str, Any] = yaml.safe_load(fh) or {}
        return cls.model_validate(raw)

    def save_to_yaml(self, path: Path | str | None = None) -> Path:
        """Persist config to yaml. Returns the written path. @zara"""
        target = Path(path) if path is not None else self.default_yaml_path()
        target.parent.mkdir(parents=True, exist_ok=True)
        data = self.model_dump(mode="json")
        with target.open("w", encoding="utf-8") as fh:
            yaml.safe_dump(
                data, fh,
                sort_keys=False, allow_unicode=True, default_flow_style=False,
            )
        return target

    def to_public_dict(self) -> dict[str, Any]:
        """Return config as dict. @zara"""
        return self.model_dump(mode="json")
