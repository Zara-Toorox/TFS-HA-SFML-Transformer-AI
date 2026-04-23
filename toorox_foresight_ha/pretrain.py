"""Pretrain Phoenix V2 on PVGIS + ERA5 with progressive horizon curriculum. @zara

Trains the ZaraPhoenixTransformer (iTransformer + PatchTST + FiLM) on
synthetic clear-sky PV production at up to 103 PVGIS locations × 4+ tilt/azimuth
variants, blended with ERA5 reanalysis for cloud/pressure/precipitation/humidity.

Target: gain = actual_kwh / pvlib_baseline_kwh  (clamped to [0, 1.3]).
The pretrain builds this target against an explicit PVGIS reference system
peak power (`pvgis_peak_power_kwp`, default `5.0`) instead of silently assuming
`1.0 kWp`.

Phases (Option C, uniform loss, no tau-decay):
    Epochs   0 – 20  →  horizon = 24h
    Epochs  21 – 50  →  horizon = 48h
    Epochs  51 – 100 →  horizon = 72h

Hardware note (AMD RX 6600, ROCm):
    HSA_OVERRIDE_GFX_VERSION=10.3.0 python scripts/pretrain.py

Environment variables (all overridable via CLI):
    PVGIS_DIR     default /home/zara/pvgis_data
    ERA5_NPZ      default /home/zara/era5_data_training/era5_extracted.npz
    OUTPUT_DIR    default models/base
    TFS_LOG_LEVEL default INFO

Typical usage:
    # Smoke-run on 3 locations (debug)
    python scripts/pretrain.py --max-locations 3 --max-epochs 2

    # Full run on AMD with ROCm
    HSA_OVERRIDE_GFX_VERSION=10.3.0 python scripts/pretrain.py

    # Resume from last best checkpoint
    python scripts/pretrain.py --resume models/base/TFS-V2_pretrain_best.safetensors
"""

from __future__ import annotations

import argparse
import os
import signal
import sys
from pathlib import Path


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Phoenix V2 PVGIS+ERA5 pretrain",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--max-locations",
        type=int,
        default=None,
        help="Limit PVGIS locations used (default: all)",
    )
    parser.add_argument(
        "--resume",
        type=str,
        default=None,
        help="Path to .safetensors checkpoint to warm-start from",
    )
    parser.add_argument(
        "--device",
        type=str,
        default=None,
        help="Training device (default: cuda if available, else cpu)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=None,
        help="Override training batch size",
    )
    parser.add_argument(
        "--max-epochs",
        type=int,
        default=None,
        help="Override maximum training epochs",
    )
    parser.add_argument(
        "--pvgis-peak-power-kwp",
        type=float,
        default=None,
        help="Reference PVGIS system peak power in kWp used for Phoenix pretrain targets",
    )
    parser.add_argument(
        "--lr",
        type=float,
        default=None,
        help="Override peak learning rate",
    )
    parser.add_argument(
        "--num-workers",
        type=int,
        default=2,
        help="DataLoader workers (reduce to 0 if memory-constrained)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Directory for checkpoint output",
    )
    parser.add_argument(
        "--pvgis-dir",
        type=str,
        default=None,
        help="PVGIS JSON directory (overrides PVGIS_DIR env)",
    )
    parser.add_argument(
        "--era5-npz",
        type=str,
        default=None,
        help="ERA5 NPZ file path (overrides ERA5_NPZ env)",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default=None,
        choices=("DEBUG", "INFO", "WARNING", "ERROR"),
        help="Logging verbosity",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Discover data + build model, print summary, then exit",
    )
    return parser.parse_args()


def _apply_overrides(settings, args: argparse.Namespace) -> None:
    training = settings.training
    if args.batch_size is not None:
        training.pretrain_batch_size = args.batch_size
    if args.max_epochs is not None:
        training.pretrain_max_epochs = args.max_epochs
    if args.pvgis_peak_power_kwp is not None:
        training.pvgis_peak_power_kwp = args.pvgis_peak_power_kwp
    if args.lr is not None:
        training.pretrain_lr = args.lr


def _resolve_path(cli_value: str | None, env_key: str, default: str) -> Path:
    if cli_value:
        return Path(cli_value).expanduser()
    return Path(os.environ.get(env_key, default)).expanduser()


def _install_signal_handlers(log) -> None:
    def handler(signum, _frame) -> None:
        log.warning("signal_received", signum=signum)
        sys.exit(130)

    signal.signal(signal.SIGINT, handler)
    signal.signal(signal.SIGTERM, handler)


def _dry_run_summary(trainer, log, args) -> int:
    from toorox_foresight.data.era5_reader import ERA5TimeSeries
    from toorox_foresight.data.pvgis_reader import discover_pvgis_locations
    from toorox_foresight.model.transformer import PhoenixConfig, ZaraPhoenixTransformer
    from toorox_foresight.training.dataset import PRETRAIN_GEOMETRIES

    geometries = [(g.tilt_deg, g.azimuth_deg) for g in PRETRAIN_GEOMETRIES]
    locations = discover_pvgis_locations(trainer._pvgis_dir, geometries)
    if args.max_locations is not None:
        locations = locations[: args.max_locations]

    log.info(
        "dry_run_locations",
        total_discovered=len(locations),
        required_geometries=geometries,
    )

    era5 = ERA5TimeSeries(trainer._era5_npz)
    era5.load()

    arch = trainer._arch
    config = PhoenixConfig(
        n_temporal_features=arch.n_temporal_features + arch.n_geometry_features,
        n_weather_variates=arch.n_weather_variates,
        n_physics_features=arch.n_physics_features,
        n_geometry_features=arch.n_geometry_features,
        seq_len=arch.seq_len,
        horizon=arch.horizon,
        patch_size=arch.patch_size,
        d_model=arch.d_model,
        n_heads=arch.n_heads,
        n_encoder_layers=arch.n_encoder_layers,
        n_decoder_layers=arch.n_decoder_layers,
        d_ff=arch.d_ff,
        n_quantiles=arch.n_quantiles,
    )
    model = ZaraPhoenixTransformer(config)
    params = model.count_parameters()
    total_m = params["total"] / 1e6

    log.info(
        "dry_run_model",
        total_params_m=round(total_m, 2),
        encoder_params_m=round(params["encoder"] / 1e6, 2),
        decoder_params_m=round(params["decoder"] / 1e6, 2),
        film_encoder_m=round(params["film_encoder"] / 1e6, 2),
        film_decoder_m=round(params["film_decoder"] / 1e6, 2),
    )
    print(
        f"\n[dry-run] locations={len(locations)} "
        f"params={total_m:.2f}M "
        f"curriculum={trainer._train.curriculum_horizons} "
        f"max_epochs={trainer._train.pretrain_max_epochs}"
    )
    return 0


def main() -> int:
    args = _parse_args()

    sys.path.insert(0, str(_project_root()))

    from toorox_foresight.config import get_settings
    from toorox_foresight.logging_setup import configure_logging, get_logger
    from toorox_foresight.training.pretrain import Pretrainer

    log_level = args.log_level or os.environ.get("TFS_LOG_LEVEL", "INFO")
    configure_logging(log_level)
    log = get_logger("pretrain")

    settings = get_settings()
    _apply_overrides(settings, args)

    pvgis_dir = _resolve_path(args.pvgis_dir, "PVGIS_DIR", "/home/zara/pvgis_data")
    era5_npz = _resolve_path(
        args.era5_npz,
        "ERA5_NPZ",
        "/home/zara/era5_data_training/era5_extracted.npz",
    )
    output_dir = _resolve_path(
        args.output_dir,
        "OUTPUT_DIR",
        str(settings.base_model_dir),
    )

    if not pvgis_dir.exists():
        log.error("pvgis_dir_missing", path=str(pvgis_dir))
        return 1
    if not era5_npz.exists():
        log.error("era5_npz_missing", path=str(era5_npz))
        return 1
    output_dir.mkdir(parents=True, exist_ok=True)

    log.info(
        "pretrain_prepare",
        pvgis_dir=str(pvgis_dir),
        era5_npz=str(era5_npz),
        output_dir=str(output_dir),
        device=args.device or "auto",
        batch_size=settings.training.pretrain_batch_size,
        pvgis_peak_power_kwp=settings.training.pvgis_peak_power_kwp,
        max_epochs=settings.training.pretrain_max_epochs,
        lr=settings.training.pretrain_lr,
        curriculum_horizons=settings.training.curriculum_horizons,
        curriculum_boundaries=settings.training.curriculum_epoch_boundaries,
        max_locations=args.max_locations,
    )

    trainer = Pretrainer(
        architecture=settings.model,
        training=settings.training,
        pvgis_dir=pvgis_dir,
        era5_npz=era5_npz,
        output_dir=output_dir,
        device=args.device,
        num_workers=args.num_workers,
    )

    if args.resume:
        resume_path = Path(args.resume).expanduser()
        if not resume_path.exists():
            log.error("resume_checkpoint_missing", path=str(resume_path))
            return 1
        trainer.resume_from = resume_path
        log.info("pretrain_resume_scheduled", path=str(resume_path))

    if args.dry_run:
        return _dry_run_summary(trainer, log, args)

    _install_signal_handlers(log)

    try:
        result = trainer.run(max_locations=args.max_locations)
    except KeyboardInterrupt:
        log.warning("pretrain_interrupted")
        return 130
    except Exception as exc:
        log.error("pretrain_failed", error=str(exc), exc_info=True)
        return 2

    log.info(
        "pretrain_complete",
        best_val_loss=round(result.best_val_loss, 6),
        best_epoch=result.best_epoch,
        total_epochs=result.total_epochs,
        total_time_min=round(result.total_time_seconds / 60.0, 1),
        checkpoint=str(result.checkpoint_path),
        params_m=round(result.parameter_count / 1e6, 2),
    )
    print(
        f"\n✓ Pretrain done. best_val={result.best_val_loss:.6f} "
        f"epoch={result.best_epoch} "
        f"params={result.parameter_count / 1e6:.2f}M "
        f"time={result.total_time_seconds / 60.0:.1f}min\n"
        f"checkpoint: {result.checkpoint_path}\n"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
