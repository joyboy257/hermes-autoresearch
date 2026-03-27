"""
Run experiment tool for autoresearch.

Executes the experiment runner script, parses METRIC output lines,
and stores results as a pending run awaiting log_experiment.
"""

import time
from typing import Any, Optional

from ..state import reconstructStateFromJsonl, readBestLoggedRun
from ..checkpoint import readAutoresearchCheckpoint, writeAutoresearchCheckpoint
from ..session_lock import acquireAutoresearchSessionLock, getAutoresearchSessionLockStatus
from ..git import readShortHeadCommit, readCurrentBranch
from ..logging_ import writeConfigHeader, appendResultEntry
from ..files import getAutoresearchRootFilePath, AUTORESEARCH_ROOT_FILES
from ..runtime_state import (
    getAutoresearchRuntimeState, 
    setAutoresearchRunInFlight,
    getAutoresearchPendingRun, 
    setAutoresearchPendingRun,
    consumeAutoresearchPendingRun,
)
from ..confidence import computeConfidence, formatConfidenceLine
from ..session_doc import syncAutoresearchSessionDoc
from ..execute import executeExperimentCommand
from ..metrics import parseMetricLines


def run_experiment(
    cwd: str,
    command: Optional[str] = None,
    description: str = "",
    timeoutSeconds: int = 600,
) -> dict[str, Any]:
    """
    Execute an experiment and store results as a pending run.
    
    Args:
        cwd: Working directory (repo root)
        command: Command to execute (defaults to runnerScript from config)
        description: Brief description of what this experiment tests
        timeoutSeconds: Maximum seconds to wait
    
    Returns:
        dict with execution results and pending run info
    """
    # Check session lock
    lock_status = getAutoresearchSessionLockStatus(cwd)
    if lock_status.state == "active" and not lock_status.ownedByCurrentProcess:
        return {
            "success": False,
            "error": f"Session is locked by another process (PID {lock_status.pid}). Cannot run experiment.",
            "lockStatus": {
                "state": lock_status.state,
                "pid": lock_status.pid,
            },
        }
    
    # Check for existing pending run
    existing_pending = getAutoresearchPendingRun(cwd)
    if existing_pending is not None:
        return {
            "success": False,
            "error": "There is already a pending run awaiting log_experiment. Call log_experiment first.",
            "pendingRun": {
                "command": existing_pending.command,
                "primaryMetric": existing_pending.primaryMetric,
                "capturedAt": existing_pending.capturedAt,
            },
        }
    
    # Get checkpoint and config
    checkpoint = readAutoresearchCheckpoint(cwd)
    if checkpoint is None:
        return {
            "success": False,
            "error": "No autoresearch session initialized. Call init_experiment first.",
        }
    
    # Determine command to run
    if command is None:
        command = AUTORESEARCH_ROOT_FILES.get("runnerScript", "autoresearch.sh")
    
    # Mark experiment as in-flight
    setAutoresearchRunInFlight(cwd, True)
    
    try:
        # Execute the experiment
        result = executeExperimentCommand(
            command=command,
            cwd=cwd,
            timeoutSeconds=timeoutSeconds,
        )
        
        # Parse metrics from output
        combined_output = f"{result.stdout}\n{result.stderr}"
        metrics = parseMetricLines(combined_output)
        
        # Determine primary metric
        primary_metric = None
        metric_name = checkpoint.session.metricName
        
        if metric_name in metrics:
            primary_metric = metrics[metric_name]
        elif metrics:
            # Use first available metric as primary
            primary_metric = next(iter(metrics.values()))
            metric_name = next(iter(metrics.keys()))
        
        # Create pending run
        from ..runtime_state import PendingExperimentRun
        pending_run = PendingExperimentRun(
            command=command,
            commit=readShortHeadCommit(cwd),
            primaryMetric=primary_metric,
            metrics=metrics,
            durationSeconds=result.durationSeconds,
            exitCode=result.exitCode,
            passed=result.passed,
            timedOut=result.timedOut,
            tailOutput=result.tailOutput,
            capturedAt=int(time.time() * 1000),
        )
        
        setAutoresearchPendingRun(cwd, pending_run)
        
        # Reconstruct state and update checkpoint
        state = reconstructStateFromJsonl(cwd)
        recent_runs = state.ideas.preview  # Just for placeholder
        
        from ..state import readRecentLoggedRuns
        recent = readRecentLoggedRuns(cwd, limit=10)
        
        # Update checkpoint with pending run
        updated_checkpoint = writeAutoresearchCheckpoint(
            cwd=cwd,
            state=state,
            sessionStartCommit=checkpoint.sessionStartCommit,
            canonicalBranch=checkpoint.canonicalBranch,
            carryForwardContext=checkpoint.carryForwardContext,
            recentLoggedRuns=recent,
            pendingRun=pending_run,
        )
        
        return {
            "success": True,
            "pending": True,
            "command": command,
            "description": description,
            "execution": {
                "exitCode": result.exitCode,
                "durationSeconds": result.durationSeconds,
                "passed": result.passed,
                "timedOut": result.timedOut,
                "crashed": result.crashed,
            },
            "metrics": {
                "primary": {
                    "name": metric_name,
                    "value": primary_metric,
                } if primary_metric is not None else None,
                "all": metrics,
            },
            "pendingRun": {
                "command": pending_run.command,
                "primaryMetric": pending_run.primaryMetric,
                "metrics": pending_run.metrics,
                "durationSeconds": pending_run.durationSeconds,
                "passed": pending_run.passed,
                "capturedAt": pending_run.capturedAt,
            },
            "checkpoint": {
                "updatedAt": updated_checkpoint.updatedAt,
            },
        }
        
    finally:
        setAutoresearchRunInFlight(cwd, False)
