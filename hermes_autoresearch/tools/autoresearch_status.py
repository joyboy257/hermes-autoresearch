"""
Autoresearch status tool.

Reports the current status of the autoresearch session including:
- Session info (name, metric, segment, runs)
- Recent runs
- Pending run
- Lock status
- Confidence score
- Ideas backlog preview
"""

from typing import Any

from ..state import reconstructStateFromJsonl, readRecentLoggedRuns, readBestLoggedRun
from ..checkpoint import readAutoresearchCheckpoint
from ..session_lock import getAutoresearchSessionLockStatus
from ..git import readShortHeadCommit, readCurrentBranch
from ..confidence import formatConfidenceLine, describeConfidence
from ..files import getAutoresearchRootFilePath, AUTORESEARCH_ROOT_FILES
from ..runtime_state import getAutoresearchPendingRun


def autoresearch_status(
    cwd: str,
    includeIdeas: bool = True,
) -> dict[str, Any]:
    """
    Get the current status of the autoresearch session.
    
    Args:
        cwd: Working directory (repo root)
        includeIdeas: Whether to include ideas backlog preview
    
    Returns:
        dict with complete session status
    """
    # Get checkpoint
    checkpoint = readAutoresearchCheckpoint(cwd)
    
    # Get lock status
    lock_status = getAutoresearchSessionLockStatus(cwd)
    
    # Get pending run
    pending_run = getAutoresearchPendingRun(cwd)
    
    # Reconstruct state
    state = reconstructStateFromJsonl(cwd)
    
    # Get recent runs
    recent_runs = readRecentLoggedRuns(cwd, limit=10)
    
    # Get best run
    best_run = None
    if state.currentSegment > 0 or state.totalRunCount > 0:
        best_run = readBestLoggedRun(cwd, state.bestDirection)
    
    # Build status response
    status: dict[str, Any] = {
        "active": lock_status.state == "active" and lock_status.ownedByCurrentProcess,
        "lockStatus": {
            "state": lock_status.state,
            "ownedByCurrentProcess": lock_status.ownedByCurrentProcess,
            "pid": lock_status.pid,
            "timestamp": lock_status.timestamp,
        },
    }
    
    if checkpoint is None:
        status["initialized"] = False
        status["session"] = None
        status["checkpoint"] = None
        return status
    
    status["initialized"] = True
    
    # Session info from checkpoint
    status["session"] = {
        "name": checkpoint.session.name,
        "metricName": checkpoint.session.metricName,
        "metricUnit": checkpoint.session.metricUnit,
        "bestDirection": checkpoint.session.bestDirection,
        "currentSegment": checkpoint.session.currentSegment,
        "currentRunCount": checkpoint.session.currentRunCount,
        "totalRunCount": checkpoint.session.totalRunCount,
        "currentBaselineMetric": checkpoint.session.currentBaselineMetric,
        "currentBestMetric": checkpoint.session.currentBestMetric,
        "confidence": checkpoint.session.confidence,
        "confidenceDescription": describeConfidence(checkpoint.session.confidence) if checkpoint.session.confidence else None,
    }
    
    # Git info
    current_commit = readShortHeadCommit(cwd)
    current_branch = readCurrentBranch(cwd)
    status["git"] = {
        "currentCommit": current_commit,
        "currentBranch": current_branch,
        "sessionStartCommit": checkpoint.sessionStartCommit,
        "canonicalBranch": checkpoint.canonicalBranch,
    }
    
    # Recent runs
    status["recentRuns"] = [
        {
            "run": run.run,
            "commit": run.commit,
            "metric": run.metric,
            "status": run.status,
            "baseline": run.baseline,
            "description": run.description,
            "segment": run.segment,
        }
        for run in recent_runs
    ]
    
    # Best run
    if best_run:
        status["bestRun"] = {
            "run": best_run.run,
            "commit": best_run.commit,
            "metric": best_run.metric,
            "status": best_run.status,
            "description": best_run.description,
        }
    
    # Pending run
    if pending_run:
        status["pendingRun"] = {
            "command": pending_run.command,
            "commit": pending_run.commit,
            "primaryMetric": pending_run.primaryMetric,
            "metrics": pending_run.metrics,
            "durationSeconds": pending_run.durationSeconds,
            "passed": pending_run.passed,
            "timedOut": pending_run.timedOut,
            "capturedAt": pending_run.capturedAt,
        }
    
    # Carry-forward context
    if checkpoint.carryForwardContext:
        cf = checkpoint.carryForwardContext
        status["carryForward"] = {
            "metricName": cf.metricName,
            "metricUnit": cf.metricUnit,
            "bestDirection": cf.bestDirection,
            "run": {
                "run": cf.run.run,
                "commit": cf.run.commit,
                "metric": cf.run.metric,
                "status": cf.run.status,
                "description": cf.run.description,
            },
        }
    
    # Ideas backlog
    if includeIdeas:
        status["ideas"] = {
            "hasBacklog": state.ideas.hasBacklog,
            "pendingCount": state.ideas.pendingCount,
            "preview": state.ideas.preview,
        }
    
    # File locations
    status["files"] = {
        key: getAutoresearchRootFilePath(cwd, key)
        for key in AUTORESEARCH_ROOT_FILES
    }
    
    return status
