# ******************************************************************************
# @copyright (C) 2026 Zara-Toorox - Toorox ForeSight HA
# * This program is protected by a Proprietary Non-Commercial License.
# 1. Personal and Educational use only.
# 2. COMMERCIAL USE AND AI TRAINING ARE STRICTLY PROHIBITED.
# 3. Clear attribution to "Zara-Toorox" is required.
# * Full license terms: https://github.com/Zara-Toorox/toorox-foresight-ha/blob/main/LICENSE
# ******************************************************************************

"""API dependency injection — service singletons. @zara"""

_forecast_service = None
_model_service = None


def get_forecast_service():
    global _forecast_service
    if _forecast_service is None:
        raise RuntimeError("Forecast service not initialized")
    return _forecast_service


def get_model_service():
    global _model_service
    if _model_service is None:
        raise RuntimeError("Model service not initialized")
    return _model_service


def init_services(forecast_svc, model_svc) -> None:
    global _forecast_service, _model_service
    _forecast_service = forecast_svc
    _model_service = model_svc
