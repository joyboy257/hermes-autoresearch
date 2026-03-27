"""
Checkpoint management for autoresearch state persistence.

The checkpoint file (autoresearch.checkpoint.json) stores a complete snapshot
of the session state for recovery and context injection.
"""

import json
from dataclasses import dataclass, field, asdict
from typing import Optional, Any

from hermes_autoresearch.files import getAutoresearchRootFilePath
from hermes_autoresearch.state import AutoresearchRunSnapshot
from hermes_autoresearch.runtime_state import PendingExperimentRun


@dataclass(frozen=True)
class AutoresearchCarryForwardContext:
    """Context carried forward from a previous segment."""
    metricName: str
    metricUnit: str
    bestDirection: str
    run: AutoresearchRunSnapshot


@dataclass(frozen=True)
class AutoresearchCheckpoint:
    """Complete checkpoint data for the autoresearch session."""
    version: int  # Always 1
    updatedAt: int  # Unix timestamp in ms
    sessionStartCommit: Optional[str]
    canonicalBranch: Optional[str]
    carryForwardContext: Optional[AutoresearchCarryForwardContext]
    session: "AutoresearchSessionInfo"
    lastLoggedRun: Optional[AutoresearchRunSnapshot]
    recentLoggedRuns: list[AutoresearchRunSnapshot]
    pendingRun: Optional[PendingExperimentRun]


@dataclass(frozen=True)
class AutoresearchSessionInfo:
    """Session information stored in checkpoint."""
    name: Optional[str]
    metricName: str
    metricUnit: str
    bestDirection: str
    currentSegment: int
    currentRunCount: int
    totalRunCount: int
    currentBaselineMetric: Optional[float]
    currentBestMetric: Optional[float]
    confidence: Optional[float]


def readAutoresearchCheckpoint(cwd: str) -> Optional[AutoresearchCheckpoint]:
    """
    Read the checkpoint file if it exists and is valid.
    
    Returns None if checkpoint doesn't exist or is corrupted.
    """
    checkpoint_path = getAutoresearchRootFilePath(cwd, "checkpoint")
    
    import os
    if not os.path.exists(checkpoint_path):
        return None
    
    try:
        with open(checkpoint_path, "r", encoding="utf-8") as f:
            parsed = json.load(f)
        
        if not isinstance(parsed.get("version"), int) or parsed.get("version") != 1:
            return None
        
        return _parseCheckpoint(parsed)
    except (json.JSONDecodeError, OSError):
        return None


def _parseCheckpoint(parsed: dict) -> Optional[AutoresearchCheckpoint]:
    """Parse a raw dict into an AutoresearchCheckpoint."""
    try:
        session_data = parsed.get("session", {})
        
        session = AutoresearchSessionInfo(
            name=session_data.get("name"),
            metricName=session_data.get("metricName", "metric"),
            metricUnit=session_data.get("metricUnit", ""),
            bestDirection=session_data.get("bestDirection", "lower"),
            currentSegment=session_data.get("currentSegment", 0),
            currentRunCount=session_data.get("currentRunCount", 0),
            totalRunCount=session_data.get("totalRunCount", 0),
            currentBaselineMetric=session_data.get("currentBaselineMetric"),
            currentBestMetric=session_data.get("currentBestMetric"),
            confidence=session_data.get("confidence"),
        )
        
        carry_forward = None
        cf_data = parsed.get("carryForwardContext")
        if cf_data and isinstance(cf_data, dict):
            run_data = cf_data.get("run", {})
            run = AutoresearchRunSnapshot(
                run=run_data.get("run", 0),
                commit=run_data.get("commit", ""),
                metric=run_data.get("metric", 0.0),
                metrics=run_data.get("metrics", {}),
                status=run_data.get("status", "keep"),
                baseline=run_data.get("baseline", False),
                description=run_data.get("description", ""),
                timestamp=run_data.get("timestamp", 0),
                segment=run_data.get("segment", 0),
                confidence=run_data.get("confidence"),
            )
            carry_forward = AutoresearchCarryForwardContext(
                metricName=cf_data.get("metricName", ""),
                metricUnit=cf_data.get("metricUnit", ""),
                bestDirection=cf_data.get("bestDirection", "lower"),
                run=run,
            )
        
        pending_run = None
        pr_data = parsed.get("pendingRun")
        if pr_data and isinstance(pr_data, dict):
            pending_run = PendingExperimentRun(
                command=pr_data.get("command", ""),
                commit=pr_data.get("commit"),
                primaryMetric=pr_data.get("primaryMetric"),
                metrics=pr_data.get("metrics", {}),
                durationSeconds=pr_data.get("durationSeconds", 0.0),
                exitCode=pr_data.get("exitCode"),
                passed=pr_data.get("passed", False),
                timedOut=pr_data.get("timedOut", False),
                tailOutput=pr_data.get("tailOutput", ""),
                capturedAt=pr_data.get("capturedAt", 0),
            )
        
        last_logged = None
        ll_data = parsed.get("lastLoggedRun")
        if ll_data and isinstance(ll_data, dict):
            last_logged = AutoresearchRunSnapshot(
                run=ll_data.get("run", 0),
                commit=ll_data.get("commit", ""),
                metric=ll_data.get("metric", 0.0),
                metrics=ll_data.get("metrics", {}),
                status=ll_data.get("status", "keep"),
                baseline=ll_data.get("baseline", False),
                description=ll_data.get("description", ""),
                timestamp=ll_data.get("timestamp", 0),
                segment=ll_data.get("segment", 0),
                confidence=ll_data.get("confidence"),
            )
        
        recent_runs = []
        for run_data in parsed.get("recentLoggedRuns", []):
            if isinstance(run_data, dict):
                recent_runs.append(AutoresearchRunSnapshot(
                    run=run_data.get("run", 0),
                    commit=run_data.get("commit", ""),
                    metric=run_data.get("metric", 0.0),
                    metrics=run_data.get("metrics", {}),
                    status=run_data.get("status", "keep"),
                    baseline=run_data.get("baseline", False),
                    description=run_data.get("description", ""),
                    timestamp=run_data.get("timestamp", 0),
                    segment=run_data.get("segment", 0),
                    confidence=run_data.get("confidence"),
                ))
        
        return AutoresearchCheckpoint(
            version=parsed.get("version", 1),
            updatedAt=parsed.get("updatedAt", 0),
            sessionStartCommit=parsed.get("sessionStartCommit"),
            canonicalBranch=parsed.get("canonicalBranch"),
            carryForwardContext=carry_forward,
            session=session,
            lastLoggedRun=last_logged,
            recentLoggedRuns=recent_runs,
            pendingRun=pending_run,
        )
    except Exception:
        return None


def writeAutoresearchCheckpoint(
    cwd: str,
    state: Any,  # AutoresearchStateSnapshot
    sessionStartCommit: Optional[str],
    canonicalBranch: Optional[str],
    carryForwardContext: Optional[AutoresearchCarryForwardContext],
    recentLoggedRuns: list[AutoresearchRunSnapshot],
    pendingRun: Optional[PendingExperimentRun],
) -> AutoresearchCheckpoint:
    """
    Write the checkpoint file with the current state.
    
    This is called after init_experiment, run_experiment, and log_experiment
    to persist the state for recovery and context injection.
    """
    checkpoint_path = getAutoresearchRootFilePath(cwd, "checkpoint")
    
    checkpoint_data = {
        "version": 1,
        "updatedAt": int(1000 * __import__("time".time())),
        "sessionStartCommit": sessionStartCommit,
        "canonicalBranch": canonicalBranch,
        "carryForwardContext": None,
        "session": {
            "name": state.name,
            "metricName": state.metricName,
            "metricUnit": state.metricUnit,
            "bestDirection": state.bestDirection,
            "currentSegment": state.currentSegment,
            "currentRunCount": state.currentRunCount,
            "totalRunCount": state.totalRunCount,
            "currentBaselineMetric": state.currentBaselineMetric,
            "currentBestMetric": state.currentBestMetric,
            "confidence": state.confidence,
        },
        "lastLoggedRun": None,
        "recentLoggedRuns": [
            {
                "run": r.run,
                "commit": r.commit,
                "metric": r.metric,
                "metrics": r.metrics,
                "status": r.status,
                "baseline": r.baseline,
                "description": r.description,
                "timestamp": r.timestamp,
                "segment": r.segment,
                "confidence": r.confidence,
            }
            for r in recentLoggedRuns
        ],
        "pendingRun": None,
    }
    
    if carryForwardContext is not None:
        checkpoint_data["carryForwardContext"] = {
            "metricName": carryForwardContext.metricName,
            "metricUnit": carryForwardContext.metricUnit,
            "bestDirection": carryForwardContext.bestDirection,
            "run": {
                "run": carryForwardContext.run.run,
                "commit": carryForwardContext.run.commit,
                "metric": carryForwardContext.run.metric,
                "metrics": carryForwardContext.run.metrics,
                "status": carryForwardContext.run.status,
                "baseline": carryForwardContext.run.baseline,
                "description": carryForwardContext.run.description,
                "timestamp": carryForwardContext.run.timestamp,
                "segment": carryForwardContext.run.segment,
                "confidence": carryForwardContext.run.confidence,
            },
        }
    
    if pendingRun is not None:
        checkpoint_data["pendingRun"] = {
            "command": pendingRun.command,
            "commit": pendingRun.commit,
            "primaryMetric": pendingRun.primaryMetric,
            "metrics": pendingRun.metrics,
            "durationSeconds": pendingRun.durationSeconds,
            "exitCode": pendingRun.exitCode,
            "passed": pendingRun.passed,
            "timedOut": pendingRun.timedOut,
            "tailOutput": pendingRun.tailOutput,
            "capturedAt": pendingRun.capturedAt,
        }
    
    if state.lastRun is not None:
        last_run = state.lastRun
        checkpoint_data["lastLoggedRun"] = {
            "run": last_run.run,
            "commit": last_run.commit,
            "metric": last_run.metric,
            "metrics": last_run.metrics,
            "status": last_run.status,
            "baseline": last_run.baseline,
            "description": last_run.description,
            "timestamp": last_run.timestamp,
            "segment": last_run.segment,
            "confidence": last_run.confidence,
        }
    
    with open(checkpoint_path, "w", encoding="utf-8") as f:
        json.dump(checkpoint_data, f, indent=2)
        f.write("\n")
    
    return _parseCheckpoint(checkpoint_data)  # type: ignore


def deleteAutoresearchCheckpoint(cwd: str) -> None:
    """Delete the checkpoint file if it exists."""
    checkpoint_path = getAutoresearchRootFilePath(cwd, "checkpoint")
    
    import os
    if os.path.exists(checkpoint_path):
        os.unlink(checkpoint_path)
