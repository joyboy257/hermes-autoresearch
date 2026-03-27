"""
In-memory runtime state for autoresearch operations.

This module maintains per-cwd runtime state for:
- pending_run: Pending experiment run awaiting log_experiment
- run_in_flight: Whether an experiment is currently running
- queued_steers: User messages captured during experiment window
- pending_command: Setup/resume commands from /autoresearch
"""

from dataclasses import dataclass, field
from typing import Optional, Literal

from hermes_autoresearch.config import MAX_QUEUED_STEERS


@dataclass(frozen=True)
class AutoresearchRuntimeSnapshot:
    """Immutable snapshot of runtime state for a single cwd."""
    mode: Literal["auto", "on", "off"]
    runInFlight: bool
    queuedSteers: list[str]
    needsContinuationReminder: bool
    pendingCommand: Optional[dict]
    pendingRun: Optional["PendingExperimentRun"]


@dataclass(frozen=True)
class PendingExperimentRun:
    """A run_experiment result awaiting log_experiment."""
    command: str
    commit: Optional[str]
    primaryMetric: Optional[float]
    metrics: dict[str, float]
    durationSeconds: float
    exitCode: Optional[int]
    passed: bool
    timedOut: bool
    tailOutput: str
    capturedAt: int


@dataclass
class MutableAutoresearchRuntimeState:
    """Mutable runtime state for a single cwd."""
    mode: Literal["auto", "on", "off"] = "auto"
    runInFlight: bool = False
    queuedSteers: list[str] = field(default_factory=list)
    needsContinuationReminder: bool = False
    pendingCommand: Optional[dict] = None
    pendingRun: Optional[PendingExperimentRun] = None


# Per-cwd runtime states
_runtime_states: dict[str, MutableAutoresearchRuntimeState] = {}

AutoresearchRuntimeMode = Literal["auto", "on", "off"]


def _getMutableRuntimeState(cwd: str) -> MutableAutoresearchRuntimeState:
    """Get or create mutable runtime state for a cwd."""
    if cwd not in _runtime_states:
        _runtime_states[cwd] = MutableAutoresearchRuntimeState()
    return _runtime_states[cwd]


def getAutoresearchRuntimeState(cwd: str) -> dict:
    """Get a snapshot of the current runtime state."""
    state = _getMutableRuntimeState(cwd)
    return {
        "mode": state.mode,
        "runInFlight": state.runInFlight,
        "queuedSteers": list(state.queuedSteers),
        "needsContinuationReminder": state.needsContinuationReminder,
        "pendingCommand": state.pendingCommand,
        "pendingRun": state.pendingRun,
    }


def setAutoresearchRuntimeMode(cwd: str, mode: str) -> dict:
    """Set the runtime mode (auto/on/off)."""
    state = _getMutableRuntimeState(cwd)
    state.mode = mode  # type: ignore
    return getAutoresearchRuntimeState(cwd)


def setAutoresearchRunInFlight(cwd: str, inFlight: bool) -> dict:
    """Set whether an experiment is currently in flight."""
    state = _getMutableRuntimeState(cwd)
    state.runInFlight = inFlight
    return getAutoresearchRuntimeState(cwd)


def queueAutoresearchSteer(cwd: str, steer: str) -> dict:
    """Add a user steer message to the queue."""
    normalized = steer.strip()
    if not normalized:
        return getAutoresearchRuntimeState(cwd)
    
    state = _getMutableRuntimeState(cwd)
    state.queuedSteers.append(normalized)
    if len(state.queuedSteers) > MAX_QUEUED_STEERS:
        state.queuedSteers = state.queuedSteers[-MAX_QUEUED_STEERS:]
    return getAutoresearchRuntimeState(cwd)


def consumeAutoresearchSteers(cwd: str) -> list[str]:
    """Remove and return all queued steers."""
    state = _getMutableRuntimeState(cwd)
    queued = list(state.queuedSteers)
    state.queuedSteers = []
    return queued


def clearAutoresearchSteers(cwd: str) -> dict:
    """Clear all queued steers without returning them."""
    state = _getMutableRuntimeState(cwd)
    state.queuedSteers = []
    return getAutoresearchRuntimeState(cwd)


def setAutoresearchPendingCommand(cwd: str, command: Optional[dict]) -> dict:
    """Set the pending autorearch command (setup/resume)."""
    state = _getMutableRuntimeState(cwd)
    state.pendingCommand = command
    return getAutoresearchRuntimeState(cwd)


def consumeAutoresearchPendingCommand(cwd: str) -> Optional[dict]:
    """Remove and return the pending command."""
    state = _getMutableRuntimeState(cwd)
    pending = state.pendingCommand
    state.pendingCommand = None
    return pending


def setAutoresearchContinuationReminder(cwd: str, needsReminder: bool) -> dict:
    """Set whether a continuation reminder is needed."""
    state = _getMutableRuntimeState(cwd)
    state.needsContinuationReminder = needsReminder
    return getAutoresearchRuntimeState(cwd)


def consumeAutoresearchContinuationReminder(cwd: str) -> bool:
    """Remove and return the continuation reminder flag."""
    state = _getMutableRuntimeState(cwd)
    needs = state.needsContinuationReminder
    state.needsContinuationReminder = False
    return needs


def setAutoresearchPendingRun(cwd: str, pending: Optional[PendingExperimentRun]) -> dict:
    """Set the pending experiment run."""
    state = _getMutableRuntimeState(cwd)
    state.pendingRun = pending
    return getAutoresearchRuntimeState(cwd)


def getAutoresearchPendingRun(cwd: str) -> Optional[PendingExperimentRun]:
    """Get the current pending experiment run."""
    return _getMutableRuntimeState(cwd).pendingRun


def consumeAutoresearchPendingRun(cwd: str) -> Optional[PendingExperimentRun]:
    """Remove and return the pending experiment run."""
    state = _getMutableRuntimeState(cwd)
    pending = state.pendingRun
    state.pendingRun = None
    return pending


def clearAutoresearchRuntimeState(cwd: str) -> None:
    """Clear all runtime state for a cwd."""
    if cwd in _runtime_states:
        del _runtime_states[cwd]
