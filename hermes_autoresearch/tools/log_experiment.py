"""
Log experiment tool for autoresearch.

Logs a pending experiment run as 'keep' or 'discard':
- For 'keep': commits to git, updates checkpoint and session doc
- For 'discard': appends idea to backlog for future exploration
"""

import time
from typing import Any

from ..state import reconstructStateFromJsonl, readBestLoggedRun, readRecentLoggedRuns
from ..checkpoint import readAutoresearchCheckpoint, writeAutoresearchCheckpoint, AutoresearchCarryForwardContext
from ..session_lock import acquireAutoresearchSessionLock, getAutoresearchSessionLockStatus
from ..git import readShortHeadCommit, readCurrentBranch, commitKeptExperiment
from ..logging_ import writeConfigHeader, appendResultEntry, AutoresearchResultEntry, createConfigHeader
from ..files import getAutoresearchRootFilePath, AUTORESEARCH_ROOT_FILES
from ..ideas import appendIdeaBacklogEntry
from ..runtime_state import (
    getAutoresearchRuntimeState, 
    setAutoresearchRunInFlight,
    getAutoresearchPendingRun, 
    setAutoresearchPendingRun,
    consumeAutoresearchPendingRun,
)
from ..confidence import computeConfidence, formatConfidenceLine
from ..session_doc import syncAutoresearchSessionDoc


def log_experiment(
    cwd: str,
    decision: str,
    idea: str = "",
) -> dict[str, Any]:
    """
    Log a pending experiment run as keep or discard.
    
    Args:
        cwd: Working directory (repo root)
        decision: "keep" or "discard"
        idea: For discard: lesson learned. For keep: optional description
    
    Returns:
        dict with log results and updated state
    """
    # Validate decision
    if decision not in ("keep", "discard"):
        return {
            "success": False,
            "error": f"Invalid decision '{decision}'. Must be 'keep' or 'discard'.",
        }
    
    # Check session lock
    lock_status = getAutoresearchSessionLockStatus(cwd)
    if lock_status.state == "active" and not lock_status.ownedByCurrentProcess:
        return {
            "success": False,
            "error": f"Session is locked by another process (PID {lock_status.pid}). Cannot log experiment.",
            "lockStatus": {
                "state": lock_status.state,
                "pid": lock_status.pid,
            },
        }
    
    # Get pending run
    pending_run = getAutoresearchPendingRun(cwd)
    if pending_run is None:
        return {
            "success": False,
            "error": "No pending run to log. Call run_experiment first.",
        }
    
    # Get checkpoint and state
    checkpoint = readAutoresearchCheckpoint(cwd)
    state = reconstructStateFromJsonl(cwd)
    
    # Prepare run data
    commit = pending_run.commit or readShortHeadCommit(cwd) or ""
    primary_metric = pending_run.primaryMetric
    
    if primary_metric is None:
        return {
            "success": False,
            "error": "Pending run has no primary metric. Cannot log.",
        }
    
    # Determine if this is the baseline run
    current_run_count = state.currentRunCount + 1
    is_baseline = current_run_count == 1
    
    # Build result entry
    entry = AutoresearchResultEntry(
        run=current_run_count,
        commit=commit,
        metric=primary_metric,
        metrics=pending_run.metrics,
        status=decision,
        baseline=is_baseline,
        description=idea or f"Run #{current_run_count}",
        timestamp=pending_run.capturedAt,
        segment=state.currentSegment,
        confidence=None,
    )
    
    # Append to results log
    appendResultEntry(cwd, entry)
    
    # Consume pending run
    consumeAutoresearchPendingRun(cwd)
    
    # Update runtime state
    setAutoresearchRunInFlight(cwd, False)
    
    # Reconstruct state after logging
    new_state = reconstructStateFromJsonl(cwd)
    
    # Compute new confidence
    segment_runs = []
    from ..state import _readAllLoggedRuns
    all_runs = _readAllLoggedRuns(cwd)
    for run in all_runs:
        if run.segment == new_state.currentSegment:
            segment_runs.append((run.metric, run.status))
    
    new_confidence = computeConfidence(segment_runs, new_state.bestDirection)
    
    # Update state with confidence
    new_state = type(new_state)(
        name=new_state.name,
        metricName=new_state.metricName,
        metricUnit=new_state.metricUnit,
        bestDirection=new_state.bestDirection,
        secondaryMetrics=new_state.secondaryMetrics,
        currentSegment=new_state.currentSegment,
        currentRunCount=new_state.currentRunCount,
        totalRunCount=new_state.totalRunCount,
        currentBaselineMetric=new_state.currentBaselineMetric,
        currentBestMetric=new_state.currentBestMetric,
        confidence=new_confidence,
        lastRun=new_state.lastRun,
        mode=new_state.mode,
        hasSessionDoc=new_state.hasSessionDoc,
        ideas=new_state.ideas,
    )
    
    # Get recent runs
    recent_runs = readRecentLoggedRuns(cwd, limit=10)
    
    # Prepare carry-forward context
    carry_forward = checkpoint.carryForwardContext if checkpoint else None
    if decision == "keep":
        # Update carry-forward context with best kept run
        best_run = readBestLoggedRun(cwd, new_state.bestDirection)
        if best_run and best_run.status == "keep":
            carry_forward = AutoresearchCarryForwardContext(
                metricName=new_state.metricName,
                metricUnit=new_state.metricUnit,
                bestDirection=new_state.bestDirection,
                run=best_run,
            )
    
    # Write updated checkpoint
    updated_checkpoint = writeAutoresearchCheckpoint(
        cwd=cwd,
        state=new_state,
        sessionStartCommit=checkpoint.sessionStartCommit if checkpoint else readShortHeadCommit(cwd),
        canonicalBranch=checkpoint.canonicalBranch if checkpoint else readCurrentBranch(cwd),
        carryForwardContext=carry_forward,
        recentLoggedRuns=recent_runs,
        pendingRun=None,
    )
    
    # Sync session document
    syncAutoresearchSessionDoc(cwd, updated_checkpoint)
    
    # Handle based on decision
    result_data = {
        "success": True,
        "decision": decision,
        "run": {
            "run": current_run_count,
            "commit": commit,
            "metric": primary_metric,
            "metrics": pending_run.metrics,
            "baseline": is_baseline,
            "description": idea or f"Run #{current_run_count}",
        },
        "session": {
            "currentRunCount": new_state.currentRunCount,
            "totalRunCount": new_state.totalRunCount,
            "currentBaselineMetric": new_state.currentBaselineMetric,
            "currentBestMetric": new_state.currentBestMetric,
            "confidence": new_state.confidence,
        },
    }
    
    if decision == "keep":
        # Commit to git
        git_result = commitKeptExperiment(
            cwd=cwd,
            description=idea or f"Experiment run #{current_run_count}",
            metricName=new_state.metricName,
            metric=primary_metric,
            metrics=pending_run.metrics,
            commit=commit,
        )
        result_data["git"] = {
            "attempted": git_result.attempted,
            "committed": git_result.committed,
            "commit": git_result.commit,
            "summary": git_result.summary,
        }
    else:
        # Append idea to backlog
        if idea:
            appendIdeaBacklogEntry(cwd, idea)
            result_data["ideasBacklog"] = {
                "appended": True,
                "idea": idea,
            }
        else:
            result_data["ideasBacklog"] = {
                "appended": False,
                "reason": "No idea provided",
            }
    
    return result_data
