"""Emitter: dual-path signal emission (ledger-first, hot path to RiskCast)."""

from omen.infrastructure.emitter.signal_emitter import (
    DuplicateSignalError,
    EmitResult,
    EmitStatus,
    HotPathError,
    RetryConfig,
    SignalEmitter,
)

__all__ = [
    "SignalEmitter",
    "EmitResult",
    "EmitStatus",
    "RetryConfig",
    "HotPathError",
    "DuplicateSignalError",
]
