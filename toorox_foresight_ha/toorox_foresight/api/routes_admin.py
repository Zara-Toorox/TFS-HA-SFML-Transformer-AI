"""Admin routes — LoRA refinetune triggers, status introspection. @zara"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query, Request

from .schemas import AdminRefinetuneResponse

router = APIRouter()


@router.post("/api/lora/refinetune", response_model=AdminRefinetuneResponse)
async def trigger_refinetune(
    request: Request,
    force: bool = Query(default=False),
) -> AdminRefinetuneResponse:
    """Manually trigger a LoRA re-finetune cycle. @zara

    Does not block — schedules the job and returns immediately.
    """
    state = request.app.state.tfs
    if state.scheduler is None:
        raise HTTPException(status_code=503, detail="Scheduler not ready")

    triggered_at = datetime.now(timezone.utc)
    accepted, reason = state.scheduler.schedule_immediate_finetune(force=force)
    if accepted:
        state.last_refinetune_requested_at = triggered_at
        state.refinetune_status = "queued"

    return AdminRefinetuneResponse(
        accepted=accepted,
        reason=reason,
        triggered_at=triggered_at.isoformat(),
    )


@router.get("/api/admin/status")
async def admin_status(request: Request) -> dict:
    """Full state snapshot for diagnostics. @zara"""
    state = request.app.state.tfs
    last_at = state.last_result_at.isoformat() if state.last_result_at else None
    refine_requested_at = (
        state.last_refinetune_requested_at.isoformat()
        if state.last_refinetune_requested_at
        else None
    )
    refine_at = state.last_refinetune_at.isoformat() if state.last_refinetune_at else None
    adapter_info = None
    if state.lora_loader is not None:
        try:
            info = state.lora_loader.inspect("default")
            adapter_info = {
                "status": info.status.value,
                "path": str(info.path),
                "base_hash_current": info.base_hash_current,
                "base_hash_adapter": info.base_hash_adapter,
                "trained_at": info.trained_at,
                "val_loss": info.val_loss,
                "samples": info.samples,
            }
        except Exception as exc:
            adapter_info = {"error": str(exc)}

    return {
        "last_forecast_at": last_at,
        "last_refinetune_requested_at": refine_requested_at,
        "last_refinetune_at": refine_at,
        "refinetune_status": state.refinetune_status,
        "panel_groups": [g.name for g in state.panel_groups.groups] if state.panel_groups else [],
        "adapter": adapter_info,
    }
