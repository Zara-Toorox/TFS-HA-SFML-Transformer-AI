"""Runtime context refresh helpers for trusted SFML-backed state. @zara"""

from __future__ import annotations

from ..logging_setup import get_logger
from ..physics.panel import PanelGroupConfig
from .state import AppState

logger = get_logger(__name__)


def _panel_group_signature(groups: PanelGroupConfig) -> tuple[tuple[str, float, float, float], ...]:
    return tuple(
        (g.name, float(g.power_kwp), float(g.tilt_deg), float(g.azimuth_deg))
        for g in groups.groups
    )


async def refresh_panel_groups_from_sfml(state: AppState) -> PanelGroupConfig:
    """Refresh trusted panel groups from SFML before forecast execution. @zara

    This prevents TFS from persisting stale bootstrap-time panel-group truth
    after SFML has changed or the add-on process has outlived older runtime
    context.
    """

    if state.sfml_reader is None:
        if state.panel_groups is None:
            raise RuntimeError("Panel groups unavailable and SFML reader missing")
        return state.panel_groups

    sfml_groups = await state.sfml_reader.get_panel_groups()
    if not sfml_groups:
        raise RuntimeError("No trusted panel groups available from SFML during runtime refresh")

    refreshed = PanelGroupConfig.from_dicts(
        [
            {
                "name": g.name,
                "power_kwp": g.power_kwp,
                "tilt": g.tilt_deg,
                "azimuth": g.azimuth_deg,
            }
            for g in sfml_groups
        ]
    )

    previous = state.panel_groups
    if previous is None:
        state.panel_groups = refreshed
        logger.info(
            "runtime_panel_groups_initialized",
            panel_groups=refreshed.group_count,
            names=[g.name for g in refreshed.groups],
        )
        return refreshed

    if _panel_group_signature(previous) != _panel_group_signature(refreshed):
        state.panel_groups = refreshed
        state.last_result = None
        state.last_result_at = None
        logger.warning(
            "runtime_panel_groups_changed",
            previous_count=previous.group_count,
            current_count=refreshed.group_count,
            previous_names=[g.name for g in previous.groups],
            current_names=[g.name for g in refreshed.groups],
        )
        return refreshed

    return previous
