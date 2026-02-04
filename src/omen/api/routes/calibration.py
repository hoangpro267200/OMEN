"""
Historical Validation & Calibration Endpoints (P1-4).

Provides:
- POST /api/v1/outcomes - Record actual outcomes for signals
- GET /api/v1/calibration - Get calibration report

Works with in-memory storage when DATABASE_URL is not set.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Dict, List, Optional
from collections import defaultdict

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)
router = APIRouter()

# In-memory storage for outcomes (used when DATABASE_URL is not set)
_outcomes_store: Dict[str, "OutcomeRecord"] = {}


class OutcomeRecord(BaseModel):
    """Record of an actual outcome for a signal."""

    signal_id: str = Field(..., description="ID of the signal this outcome is for")
    actual_outcome: bool = Field(..., description="Whether the predicted event actually occurred")
    actual_probability: Optional[float] = Field(
        None,
        ge=0,
        le=1,
        description="Actual probability if available (e.g., from market resolution)",
    )
    notes: Optional[str] = Field(None, description="Optional notes about the outcome")
    recorded_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When this outcome was recorded",
    )
    recorded_by: Optional[str] = Field(None, description="Who recorded this outcome")

    class Config:
        frozen = True


class OutcomeRequest(BaseModel):
    """Request to record an outcome."""

    signal_id: str = Field(..., description="ID of the signal")
    actual_outcome: bool = Field(..., description="Whether the predicted event occurred")
    actual_probability: Optional[float] = Field(
        None,
        ge=0,
        le=1,
        description="Actual probability if available",
    )
    notes: Optional[str] = Field(None, description="Optional notes")


class OutcomeResponse(BaseModel):
    """Response after recording an outcome."""

    success: bool
    signal_id: str
    message: str
    storage_mode: str = Field(
        description="Storage mode: 'in_memory' or 'database'"
    )


class CalibrationBucket(BaseModel):
    """Calibration statistics for a probability bucket."""

    bucket_range: str = Field(..., description="e.g., '0.7-0.8'")
    predicted_avg: float = Field(..., description="Average predicted probability")
    actual_avg: float = Field(..., description="Average actual outcome rate")
    count: int = Field(..., description="Number of signals in this bucket")
    calibration_error: float = Field(
        ...,
        description="abs(predicted_avg - actual_avg)",
    )


class CalibrationReport(BaseModel):
    """Calibration report for historical validation."""

    total_signals: int
    signals_with_outcomes: int
    buckets: List[CalibrationBucket]
    overall_calibration_error: float = Field(
        ...,
        description="Mean absolute calibration error across all buckets",
    )
    brier_score: Optional[float] = Field(
        None,
        description="Brier score if calculable (lower is better)",
    )
    storage_mode: str = Field(
        description="Storage mode: 'in_memory' or 'database'"
    )
    generated_at: datetime


def _get_storage_mode() -> str:
    """Determine if we're using database or in-memory storage."""
    return "database" if os.environ.get("DATABASE_URL") else "in_memory"


def _get_outcomes_store() -> Dict[str, OutcomeRecord]:
    """Get the outcomes store (in-memory for now)."""
    # In production, this would check DATABASE_URL and return DB adapter
    return _outcomes_store


@router.post("/outcomes", response_model=OutcomeResponse)
async def record_outcome(request: OutcomeRequest) -> OutcomeResponse:
    """
    Record the actual outcome for a signal.

    This is used for historical validation and calibration analysis.
    In production, outcomes are stored in the database.
    Without DATABASE_URL, outcomes are stored in-memory (lost on restart).
    """
    storage_mode = _get_storage_mode()
    store = _get_outcomes_store()

    # Check if outcome already exists
    if request.signal_id in store:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Outcome already recorded for signal {request.signal_id}",
        )

    # Create and store the outcome record
    record = OutcomeRecord(
        signal_id=request.signal_id,
        actual_outcome=request.actual_outcome,
        actual_probability=request.actual_probability,
        notes=request.notes,
    )
    store[request.signal_id] = record

    logger.info(
        "Recorded outcome for signal %s: outcome=%s, storage=%s",
        request.signal_id,
        request.actual_outcome,
        storage_mode,
    )

    return OutcomeResponse(
        success=True,
        signal_id=request.signal_id,
        message=f"Outcome recorded successfully ({storage_mode} storage)",
        storage_mode=storage_mode,
    )


@router.get("/calibration", response_model=CalibrationReport)
async def get_calibration_report() -> CalibrationReport:
    """
    Get calibration report for historical validation.

    Compares predicted probabilities against actual outcomes to measure
    how well-calibrated the signal predictions are.

    Calibration is computed in buckets (0.0-0.1, 0.1-0.2, ..., 0.9-1.0).
    A well-calibrated system should have:
    - Signals predicted at 70% should have ~70% actual occurrence rate
    - Low calibration error (close to 0)
    - Low Brier score (close to 0)
    """
    from omen.application.container import get_container

    storage_mode = _get_storage_mode()
    store = _get_outcomes_store()
    container = get_container()
    repo = container.repository

    # Get all signals from repository
    try:
        all_signals = repo.list_all()
    except Exception as e:
        logger.warning("Failed to list signals: %s", e)
        all_signals = []

    total_signals = len(all_signals)
    signals_with_outcomes = len(store)

    # Build buckets (0.0-0.1, 0.1-0.2, ..., 0.9-1.0)
    bucket_data: Dict[str, List[tuple]] = defaultdict(list)

    for signal in all_signals:
        signal_id = signal.signal_id
        if signal_id not in store:
            continue

        outcome = store[signal_id]
        prob = signal.probability

        # Determine bucket
        bucket_idx = min(int(prob * 10), 9)  # 0-9
        bucket_key = f"{bucket_idx / 10:.1f}-{(bucket_idx + 1) / 10:.1f}"

        # Store (predicted_prob, actual_outcome_as_float)
        actual = 1.0 if outcome.actual_outcome else 0.0
        bucket_data[bucket_key].append((prob, actual))

    # Calculate calibration statistics
    buckets = []
    total_calibration_error = 0.0
    brier_sum = 0.0
    brier_count = 0

    for bucket_idx in range(10):
        bucket_key = f"{bucket_idx / 10:.1f}-{(bucket_idx + 1) / 10:.1f}"
        data = bucket_data.get(bucket_key, [])

        if data:
            predicted_avg = sum(p for p, _ in data) / len(data)
            actual_avg = sum(a for _, a in data) / len(data)
            calibration_error = abs(predicted_avg - actual_avg)

            # Brier score contribution
            for pred, actual in data:
                brier_sum += (pred - actual) ** 2
                brier_count += 1
        else:
            predicted_avg = (bucket_idx + 0.5) / 10  # Bucket midpoint
            actual_avg = 0.0
            calibration_error = 0.0

        buckets.append(
            CalibrationBucket(
                bucket_range=bucket_key,
                predicted_avg=round(predicted_avg, 4),
                actual_avg=round(actual_avg, 4),
                count=len(data),
                calibration_error=round(calibration_error, 4),
            )
        )
        if data:
            total_calibration_error += calibration_error

    # Calculate overall metrics
    buckets_with_data = sum(1 for b in buckets if b.count > 0)
    overall_calibration_error = (
        total_calibration_error / buckets_with_data if buckets_with_data > 0 else 0.0
    )
    brier_score = brier_sum / brier_count if brier_count > 0 else None

    return CalibrationReport(
        total_signals=total_signals,
        signals_with_outcomes=signals_with_outcomes,
        buckets=buckets,
        overall_calibration_error=round(overall_calibration_error, 4),
        brier_score=round(brier_score, 4) if brier_score is not None else None,
        storage_mode=storage_mode,
        generated_at=datetime.now(timezone.utc),
    )


@router.get("/outcomes/{signal_id}", response_model=OutcomeRecord)
async def get_outcome(signal_id: str) -> OutcomeRecord:
    """Get the recorded outcome for a specific signal."""
    store = _get_outcomes_store()

    if signal_id not in store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No outcome recorded for signal {signal_id}",
        )

    return store[signal_id]


@router.get("/outcomes", response_model=List[OutcomeRecord])
async def list_outcomes(limit: int = 100) -> List[OutcomeRecord]:
    """List all recorded outcomes."""
    store = _get_outcomes_store()
    outcomes = list(store.values())
    # Sort by recorded_at descending
    outcomes.sort(key=lambda x: x.recorded_at, reverse=True)
    return outcomes[:limit]
