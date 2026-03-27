"""
Init experiment tool for autoresearch.

Initializes a new autoresearch session or resumes an existing one by:
1. Acquiring the session lock
2. Writing the config header to the results log
3. Creating/updating the checkpoint
4. Syncing the session document
"""

from typing import Any

from ..state import reconstructStateFromJsonl, createEmptyStateSnapshot, readRecentLoggedRuns
from ..checkpoint import readAutoresearchCheckpoint, writeAutoresearchCheckpoint, AutoresearchCarryForwardContext
from ..session_lock import acquireAutoresearchSessionLock, getAutoresearchSessionLockStatus
from ..git import readShortHeadCommit, readCurrentBranch
from ..logging_ import createConfigHeader, writeConfigHeader
from ..files import getAutoresearchRootFilePath, AUTORESEARCH_ROOT_FILES
from ..runtime_state import getAutoresearchRuntimeState, setAutoresearchPendingRun, consumeAutoresearchPendingRun
from ..confidence import computeConfidence, formatConfidenceLine
from ..session_doc import syncAutoresearchSessionDoc
from ..execute import executeExperimentCommand
from ..metrics import parseMetricLines


def init_experiment(
    cwd: str,
    name: str,
    metricName: str,
    bestDirection: str,
    metricUnit: str = "",
    runnerScript: str = "autoresearch.sh",
) -> dict[str, Any]:
    """
    Initialize a new autoresearch session or resume an existing one.
    
    Args:
        cwd: Working directory (repo root)
        name: Human-readable name for this experiment series
        metricName: Name of the primary metric being optimized
        metricUnit: Unit of the metric
        bestDirection: "lower" or "higher" - which is better
        runnerScript: Path to the shell script that runs experiments
    
    Returns:
        dict with status, session info, and checkpoint data
    """
    # Validate inputs
    if bestDirection not in ("lower", "higher"):
        return {
            "success": False,
            "error": f"Invalid bestDirection '{bestDirection}'. Must be 'lower' or 'higher'.",
        }
    
    # Acquire session lock
    lock_status = acquireAutoresearchSessionLock(cwd)
    if lock_status.state == "active" and not lock_status.ownedByCurrentProcess:
        return {
            "success": False,
            "error": f"Session is locked by another process (PID {lock_status.pid}). Cannot initialize.",
            "lockStatus": {
                "state": lock_status.state,
                "pid": lock_status.pid,
                "timestamp": lock_status.timestamp,
            },
        }
    
    # Read current git state
    current_commit = readShortHeadCommit(cwd)
    current_branch = readCurrentBranch(cwd)
    
    # Read existing checkpoint (for carry-forward context)
    existing_checkpoint = readAutoresearchCheckpoint(cwd)
    
    # Reconstruct current state from JSONL
    state = reconstructStateFromJsonl(cwd)
    
    # Determine if we're starting fresh or resuming
    is_resume = existing_checkpoint is not None and state.totalRunCount > 0
    
    # Write config header to JSONL
    header = createConfigHeader(
        name=name,
        metricName=metricName,
        metricUnit=metricUnit,
        bestDirection=bestDirection,
    )
    
    if is_resume:
        # Append to existing log (new segment)
        writeConfigHeader(cwd, header, mode="append")
    else:
        # Create new log
        writeConfigHeader(cwd, header, mode="create")
    
    # Get recent runs for checkpoint
    recent_runs = readRecentLoggedRuns(cwd, limit=10)
    
    # Build carry-forward context if we have a best run
    carry_forward = None
    if existing_checkpoint and existing_checkpoint.carryForwardContext:
        # Preserve existing carry-forward context
        carry_forward = existing_checkpoint.carryForwardContext
    elif recent_runs:
        # Try to carry forward best run from previous segment
        from ..state import readBestLoggedRun
        best_run = readBestLoggedRun(cwd, bestDirection)
        if best_run and best_run.status == "keep":
            carry_forward = AutoresearchCarryForwardContext(
                metricName=metricName,
                metricUnit=metricUnit,
                bestDirection=bestDirection,
                run=best_run,
            )
    
    # Consume any pending run from a previous session
    pending_run = consumeAutoresearchPendingRun(cwd)
    
    # Update state snapshot with new config
    new_state = createEmptyStateSnapshot()
    new_state = type(new_state)(
        name=name,
        metricName=metricName,
        metricUnit=metricUnit,
        bestDirection=bestDirection,
        secondaryMetrics=state.secondaryMetrics,
        currentSegment=state.currentSegment + 1 if is_resume else 0,
        currentRunCount=0,
        totalRunCount=state.totalRunCount,
        currentBaselineMetric=None,
        currentBestMetric=None,
        confidence=None,
        lastRun=None,
        mode="active",
        hasSessionDoc=state.hasSessionDoc,
        ideas=state.ideas,
    )
    
    # Write checkpoint
    checkpoint = writeAutoresearchCheckpoint(
        cwd=cwd,
        state=new_state,
        sessionStartCommit=current_commit or existing_checkpoint.sessionStartCommit if existing_checkpoint else None,
        canonicalBranch=current_branch,
        carryForwardContext=carry_forward,
        recentLoggedRuns=recent_runs[-10:] if recent_runs else [],
        pendingRun=pending_run,
    )
    
    # Sync session document
    syncAutoresearchSessionDoc(cwd, checkpoint)
    
    return {
        "success": True,
        "initialized": not is_resume,
        "resumed": is_resume,
        "session": {
            "name": name,
            "metricName": metricName,
            "metricUnit": metricUnit,
            "bestDirection": bestDirection,
            "currentSegment": new_state.currentSegment,
            "currentRunCount": 0,
            "totalRunCount": new_state.totalRunCount,
        },
        "git": {
            "commit": current_commit,
            "branch": current_branch,
        },
        "lockStatus": {
            "state": lock_status.state,
            "pid": lock_status.pid,
            "timestamp": lock_status.timestamp,
        },
        "carryForwardContext": {
            "metricName": carry_forward.metricName,
            "metricUnit": carry_forward.metricUnit,
            "bestDirection": carry_forward.bestDirection,
            "run": {
                "run": carry_forward.run.run,
                "commit": carry_forward.run.commit,
                "metric": carry_forward.run.metric,
                "description": carry_forward.run.description,
            },
        } if carry_forward else None,
        "checkpoint": {
            "path": getAutoresearchRootFilePath(cwd, "checkpoint"),
            "updatedAt": checkpoint.updatedAt,
        },
    }
