# ******************************************************************************
# @copyright (C) 2026 Zara-Toorox - Toorox ForeSight HA
# * This program is protected by a Proprietary Non-Commercial License.
# 1. Personal and Educational use only.
# 2. COMMERCIAL USE AND AI TRAINING ARE STRICTLY PROHIBITED.
# 3. Clear attribution to "Zara-Toorox" is required.
# * Full license terms: https://github.com/Zara-Toorox/toorox-foresight-ha/blob/main/LICENSE
# ******************************************************************************

"""Data Augmentation for solar forecast training. @zara

Generates synthetic training samples from real data through physically
plausible transformations. Each augmentation preserves the fundamental
relationship between weather conditions and solar production.

Augmentations:
    1. Gaussian Noise       — adds small noise to features (sensor uncertainty)
    2. Cloud Perturbation   — shifts cloud cover ±15% (NWP uncertainty)
    3. Temperature Shift    — shifts temperature ±2°C (microclimate variation)
    4. Production Scaling   — scales production ±10% (panel degradation, dirt)
    5. Time Jitter          — shifts sequence by ±1-2 hours (timezone edge cases)
    6. Weather Regime Swap  — replaces weather with similar day from history
    7. Dropout Masking      — randomly zeros features (missing sensor simulation)
    8. Irradiance Scaling   — scales GHI/DNI together (atmospheric variation)

Each augmentation has a probability of being applied. Multiple augmentations
can be stacked on a single sample.
"""

import numpy as np
from numpy.typing import NDArray
import structlog

logger = structlog.get_logger()


class SolarAugmentor:
    """Physically plausible data augmentation for solar forecasting. @zara"""

    def __init__(
        self,
        noise_std: float = 0.02,
        cloud_shift_max: float = 15.0,
        temp_shift_max: float = 2.0,
        production_scale_range: tuple[float, float] = (0.90, 1.10),
        time_jitter_max: int = 2,
        feature_dropout_rate: float = 0.05,
        irradiance_scale_range: tuple[float, float] = (0.85, 1.15),
        p_noise: float = 0.5,
        p_cloud: float = 0.3,
        p_temp: float = 0.3,
        p_production: float = 0.3,
        p_time_jitter: float = 0.2,
        p_feature_dropout: float = 0.2,
        p_irradiance: float = 0.3,
    ) -> None:
        self.noise_std = noise_std
        self.cloud_shift_max = cloud_shift_max
        self.temp_shift_max = temp_shift_max
        self.production_scale_range = production_scale_range
        self.time_jitter_max = time_jitter_max
        self.feature_dropout_rate = feature_dropout_rate
        self.irradiance_scale_range = irradiance_scale_range
        self.p_noise = p_noise
        self.p_cloud = p_cloud
        self.p_temp = p_temp
        self.p_production = p_production
        self.p_time_jitter = p_time_jitter
        self.p_feature_dropout = p_feature_dropout
        self.p_irradiance = p_irradiance

    def augment_sample(
        self,
        temporal: NDArray,
        weather: NDArray,
        physics: NDArray,
        targets: NDArray,
        rng: np.random.Generator | None = None,
    ) -> tuple[NDArray, NDArray, NDArray, NDArray]:
        """Apply random augmentations to a single training sample. @zara

        Args:
            temporal: (seq_len, n_features) historical features
            weather:  (horizon, n_weather) future weather
            physics:  (horizon, n_physics) solar geometry
            targets:  (horizon,) actual kWh

        Returns:
            Augmented copies of all four tensors
        """
        rng = rng or np.random.default_rng()
        temporal = temporal.copy()
        weather = weather.copy()
        physics = physics.copy()
        targets = targets.copy()

        if rng.random() < self.p_noise:
            temporal = self._add_noise(temporal, rng)
            weather = self._add_noise(weather, rng, std=self.noise_std * 0.5)

        if rng.random() < self.p_cloud:
            weather = self._perturb_clouds(weather, rng)

        if rng.random() < self.p_temp:
            weather = self._shift_temperature(weather, rng)

        if rng.random() < self.p_production:
            targets = self._scale_production(targets, rng)

        if rng.random() < self.p_time_jitter:
            temporal = self._time_jitter(temporal, rng)

        if rng.random() < self.p_feature_dropout:
            temporal = self._feature_dropout(temporal, rng)

        if rng.random() < self.p_irradiance:
            weather = self._scale_irradiance(weather, rng)

        return temporal, weather, physics, targets

    def _add_noise(self, data: NDArray, rng: np.random.Generator, std: float | None = None) -> NDArray:
        """Add Gaussian noise to all features. @zara"""
        noise = rng.normal(0, std or self.noise_std, size=data.shape).astype(data.dtype)
        return np.clip(data + noise, 0.0, None)

    def _perturb_clouds(self, weather: NDArray, rng: np.random.Generator) -> NDArray:
        """Shift cloud cover by a consistent offset across all hours. @zara"""
        shift = rng.uniform(-self.cloud_shift_max, self.cloud_shift_max)
        cloud_idx = 7
        if weather.shape[1] > cloud_idx:
            weather[:, cloud_idx] = np.clip(weather[:, cloud_idx] + shift, 0, 100)
        for layer_idx in [8, 9, 10]:
            if weather.shape[1] > layer_idx:
                weather[:, layer_idx] = np.clip(weather[:, layer_idx] + shift * 0.7, 0, 100)
        return weather

    def _shift_temperature(self, weather: NDArray, rng: np.random.Generator) -> NDArray:
        """Shift temperature by a consistent offset. @zara"""
        shift = rng.uniform(-self.temp_shift_max, self.temp_shift_max)
        temp_idx = 0
        if weather.shape[1] > temp_idx:
            weather[:, temp_idx] += shift
        return weather

    def _scale_production(self, targets: NDArray, rng: np.random.Generator) -> NDArray:
        """Scale production values (simulates panel degradation/dirt). @zara"""
        scale = rng.uniform(*self.production_scale_range)
        return np.maximum(targets * scale, 0.0)

    def _time_jitter(self, temporal: NDArray, rng: np.random.Generator) -> NDArray:
        """Shift temporal sequence by 1-2 hours (roll). @zara"""
        shift = rng.integers(-self.time_jitter_max, self.time_jitter_max + 1)
        if shift != 0:
            temporal = np.roll(temporal, shift, axis=0)
            if shift > 0:
                temporal[:shift] = 0
            else:
                temporal[shift:] = 0
        return temporal

    def _feature_dropout(self, data: NDArray, rng: np.random.Generator) -> NDArray:
        """Randomly zero out entire feature columns (missing sensor). @zara"""
        n_features = data.shape[1]
        mask = rng.random(n_features) > self.feature_dropout_rate
        return data * mask[np.newaxis, :]

    def _scale_irradiance(self, weather: NDArray, rng: np.random.Generator) -> NDArray:
        """Scale GHI and DNI together (atmospheric variation). @zara"""
        scale = rng.uniform(*self.irradiance_scale_range)
        ghi_idx = 1
        dni_idx = 2
        diffuse_idx = 3
        for idx in [ghi_idx, dni_idx, diffuse_idx]:
            if weather.shape[1] > idx:
                weather[:, idx] = np.maximum(weather[:, idx] * scale, 0.0)
        return weather


def augment_dataset(
    samples: list[dict],
    augmentor: SolarAugmentor,
    multiplier: int = 3,
    seed: int = 42,
) -> list[dict]:
    """Augment an entire dataset, creating `multiplier` copies of each sample. @zara

    Args:
        samples: list of dicts with 'temporal', 'weather', 'physics', 'targets' numpy arrays
        augmentor: configured SolarAugmentor
        multiplier: how many augmented copies per original (3 = 4x data total)
        seed: random seed for reproducibility

    Returns:
        Original samples + augmented copies
    """
    rng = np.random.default_rng(seed)
    augmented = list(samples)

    for sample in samples:
        for _ in range(multiplier):
            t, w, p, tgt = augmentor.augment_sample(
                sample["temporal"],
                sample["weather"],
                sample["physics"],
                sample["targets"],
                rng=rng,
            )
            augmented.append({
                **sample,
                "temporal": t,
                "weather": w,
                "physics": p,
                "targets": tgt,
            })

    logger.info(
        "augmentation_complete",
        original=len(samples),
        augmented=len(augmented),
        multiplier=multiplier + 1,
    )
    return augmented
