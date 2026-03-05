"""
Langfuse observability adapter for tabular ML models.
=====================================================

Concept mapping: ML → Langfuse
──────────────────────────────
  Prediction pipeline     →  Trace           (groups all steps)
  Feature engineering      →  Span            (non-model step)
  Model inference          →  Generation      (unlocks model dashboards)
  Post-processing          →  Span            (risk classification)
  Fraud probability        →  Score NUMERIC   (time series in dashboards)
  Risk level / decision    →  Score CATEGORICAL
  Ground truth feedback    →  Score BOOLEAN   (real precision/recall)
  Data drift signals       →  Score NUMERIC   (feature distribution tracking)
  Model version            →  Generation.model
  Anomaly flags            →  Trace tags      (quick filtering)

The generation hack: XGBoost inference declared as a "generation" to
inherit Langfuse's native model dashboards (latency, version comparison).

Scores are the ONLY path to dashboard charts. Metadata is filterable
but not chartable — so key features go into scores for drift monitoring.

Env vars: LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY, LANGFUSE_BASE_URL,
          LANGFUSE_ENABLED (default "true").
If keys are missing, all calls are silent no-ops.
"""
from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger("fraud_api.observability")

_langfuse = None
_enabled = False


def init_langfuse():
    """Initialize Langfuse client. Silent no-op if keys are missing."""
    global _langfuse, _enabled

    if os.getenv("LANGFUSE_ENABLED", "true").lower() == "false":
        logger.info("Langfuse disabled via LANGFUSE_ENABLED=false")
        return

    pk = os.getenv("LANGFUSE_PUBLIC_KEY")
    sk = os.getenv("LANGFUSE_SECRET_KEY")
    if not pk or not sk:
        logger.info("Langfuse keys not set — tracing disabled")
        return

    try:
        from langfuse import Langfuse
        _langfuse = Langfuse(
            public_key=pk,
            secret_key=sk,
            host=os.getenv("LANGFUSE_BASE_URL", "https://cloud.langfuse.com"),
        )
        _enabled = True
        logger.info("Langfuse tracing enabled (key: %s...)", pk[:12])
    except Exception as e:
        logger.warning("Langfuse init failed: %s", e)


def shutdown_langfuse():
    """Flush pending events on app shutdown."""
    if _langfuse:
        try:
            _langfuse.flush()
        except Exception:
            pass


def trace_prediction(
    *,
    request_id: str,
    raw_input: dict[str, Any],
    engineered_features: dict[str, float],
    feature_engineering_ms: float,
    inference_ms: float,
    fraud_probability: float,
    threshold: float,
    is_fraud: bool,
    risk_level: str,
    recommended_action: str,
    risk_factors: list[str],
    model_version: str,
    n_features: int,
):
    """Trace a complete prediction. Non-blocking (SDK batches async)."""
    if not _enabled:
        return

    try:
        _send_trace(
            request_id=request_id,
            raw_input=raw_input,
            engineered_features=engineered_features,
            feature_engineering_ms=feature_engineering_ms,
            inference_ms=inference_ms,
            fraud_probability=fraud_probability,
            threshold=threshold,
            is_fraud=is_fraud,
            risk_level=risk_level,
            recommended_action=recommended_action,
            risk_factors=risk_factors,
            model_version=model_version,
            n_features=n_features,
        )
    except Exception as e:
        logger.warning("Langfuse trace failed: %s", e)


def _send_trace(
    *,
    request_id: str,
    raw_input: dict[str, Any],
    engineered_features: dict[str, float],
    feature_engineering_ms: float,
    inference_ms: float,
    fraud_probability: float,
    threshold: float,
    is_fraud: bool,
    risk_level: str,
    recommended_action: str,
    risk_factors: list[str],
    model_version: str,
    n_features: int,
):
    prediction_output = {
        "is_fraud": is_fraud,
        "fraud_probability": round(fraud_probability, 6),
        "risk_level": risk_level,
        "recommended_action": recommended_action,
        "risk_factors": risk_factors,
    }

    tags = _build_tags(
        is_fraud=is_fraud,
        risk_level=risk_level,
        amt=raw_input.get("amt", 0),
        distance=engineered_features.get("distance_km", 0),
        is_night=engineered_features.get("is_night", 0),
    )

    # ── Root trace ──────────────────────────────────────────────────
    with _langfuse.start_as_current_observation(
        as_type="span",
        name="fraud-prediction",
        input=raw_input,
        output=prediction_output,
        metadata={
            "request_id": request_id,
            "model_version": model_version,
            "feature_engineering_ms": round(feature_engineering_ms, 2),
            "inference_ms": round(inference_ms, 2),
            "total_latency_ms": round(feature_engineering_ms + inference_ms, 2),
            "threshold": threshold,
        },
    ):
        # Tags are set via update_current_trace (not a constructor arg)
        _langfuse.update_current_trace(tags=tags)

        # ── Span: Feature Engineering ───────────────────────────────
        with _langfuse.start_as_current_observation(
            as_type="span",
            name="feature-engineering",
            input=raw_input,
            output=engineered_features,
            metadata={"latency_ms": round(feature_engineering_ms, 2)},
        ):
            pass

        # ── Generation: Model Inference ─────────────────────────────
        # Using "generation" (not "span") to unlock native Langfuse
        # model dashboards: latency per model, version comparison, usage.
        with _langfuse.start_as_current_observation(
            as_type="generation",
            name="model-inference",
            model=f"xgboost-fraud-{model_version}",
            input=engineered_features,
            output={
                "fraud_probability": round(fraud_probability, 6),
                "is_fraud": is_fraud,
                "threshold": threshold,
            },
            usage_details={
                "input": n_features,
                "output": 1,
            },
            metadata={"latency_ms": round(inference_ms, 2)},
        ):
            pass

        # ── Span: Risk Classification ───────────────────────────────
        with _langfuse.start_as_current_observation(
            as_type="span",
            name="risk-classification",
            input={
                "fraud_probability": round(fraud_probability, 6),
                "threshold": threshold,
            },
            output={
                "risk_level": risk_level,
                "recommended_action": recommended_action,
                "risk_factors": risk_factors,
            },
        ):
            pass

        # ── Scores ──────────────────────────────────────────────────
        # score_current_trace attaches scores to the root trace.
        # These are the ONLY values that appear in dashboard charts.

        # Tier 1: Model output
        _langfuse.score_current_trace(
            name="fraud_probability",
            value=fraud_probability,
            data_type="NUMERIC",
            comment=f"threshold={threshold}",
        )
        _langfuse.score_current_trace(
            name="risk_level",
            value=risk_level,
            data_type="CATEGORICAL",
        )
        _langfuse.score_current_trace(
            name="decision",
            value=recommended_action,
            data_type="CATEGORICAL",
        )

        # Tier 2: Data drift signals (top features by importance)
        distance = engineered_features.get("distance_km", 0)
        _langfuse.score_current_trace(
            name="distance_km",
            value=round(distance, 2),
            data_type="NUMERIC",
            comment="customer-merchant distance (top feature)",
        )
        _langfuse.score_current_trace(
            name="amount_usd",
            value=raw_input.get("amt", 0),
            data_type="NUMERIC",
            comment="transaction amount (drift monitoring)",
        )


def _build_tags(
    *, is_fraud: bool, risk_level: str, amt: float,
    distance: float, is_night: float,
) -> list[str]:
    """Dynamic tags for filtering in Langfuse UI."""
    tags = [f"risk:{risk_level}"]
    if is_fraud:
        tags.append("fraud_detected")
    if amt > 500:
        tags.append("high_value")
    if distance > 100:
        tags.append("far_merchant")
    if is_night:
        tags.append("night_transaction")
    return tags


def score_trace_feedback(
    trace_id: str,
    is_actually_fraud: bool,
    comment: str | None = None,
):
    """Score a past prediction with ground truth (human feedback loop)."""
    if not _enabled:
        return

    try:
        _langfuse.create_score(
            trace_id=trace_id,
            name="ground_truth",
            value=int(is_actually_fraud),
            data_type="BOOLEAN",
            comment=comment or "",
        )
    except Exception as e:
        logger.warning("Langfuse feedback score failed: %s", e)
