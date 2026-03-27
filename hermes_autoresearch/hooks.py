"""
Hermes hook for system prompt context injection.

Provides get_system_prompt_addition(cwd) to inject autoresearch context
into Hermes system prompts for aware code generation.
"""

from typing import Optional

from hermes_autoresearch.checkpoint import readAutoresearchCheckpoint
from hermes_autoresearch.state import reconstructStateFromJsonl
from hermes_autoresearch.session_lock import getAutoresearchSessionLockStatus
from hermes_autoresearch.runtime_state import getAutoresearchPendingRun
from hermes_autoresearch.confidence import formatConfidenceLine, describeConfidence


def get_system_prompt_addition(cwd: str) -> str:
    """
    Generate a system prompt addition describing the current autoresearch context.
    
    This is called by Hermes to inject experiment context into the system prompt
    when generating code, so the model is aware of current experiments and goals.
    
    Args:
        cwd: Working directory (repo root)
    
    Returns:
        Markdown string describing the current autoresearch session, or empty string if inactive.
    """
    # Check if session is active
    lock_status = getAutoresearchSessionLockStatus(cwd)
    if lock_status.state != "active" or not lock_status.ownedByCurrentProcess:
        return ""
    
    # Get checkpoint
    checkpoint = readAutoresearchCheckpoint(cwd)
    if checkpoint is None:
        return ""
    
    # Get state
    state = reconstructStateFromJsonl(cwd)
    
    # Build context section
    lines = [
        "",
        "---",
        "# Autoresearch Context",
        "",
    ]
    
    # Session info
    if checkpoint.session.name:
        lines.append(f"**Experiment**: {checkpoint.session.name}")
    
    lines.append(f"**Metric**: {checkpoint.session.metricName}")
    if checkpoint.session.metricUnit:
        lines.append(f"**Unit**: {checkpoint.session.metricUnit}")
    lines.append(f"**Goal**: {checkpoint.session.bestDirection} is better")
    
    # Run stats
    lines.append("")
    lines.append(f"- Segment: {checkpoint.session.currentSegment}")
    lines.append(f"- Runs this segment: {checkpoint.session.currentRunCount}")
    lines.append(f"- Total runs: {checkpoint.session.totalRunCount}")
    
    # Baseline and best
    if checkpoint.session.currentBaselineMetric is not None:
        baseline_str = f"{checkpoint.session.currentBaselineMetric}"
        if checkpoint.session.metricUnit:
            baseline_str += checkpoint.session.metricUnit
        lines.append(f"- Baseline: {baseline_str}")
    
    if checkpoint.session.currentBestMetric is not None:
        best_str = f"{checkpoint.session.currentBestMetric}"
        if checkpoint.session.metricUnit:
            best_str += checkpoint.session.metricUnit
        lines.append(f"- Best kept: {best_str}")
    
    # Confidence
    if checkpoint.session.confidence is not None:
        lines.append(f"- {formatConfidenceLine(checkpoint.session.confidence)}")
    
    # Pending run
    pending_run = getAutoresearchPendingRun(cwd)
    if pending_run is not None:
        lines.append("")
        lines.append("**Pending run** awaiting log_experiment:")
        lines.append(f"- Command: `{pending_run.command}`")
        if pending_run.primaryMetric is not None:
            lines.append(f"- Metric: {pending_run.primaryMetric}")
        lines.append(f"- Duration: {pending_run.durationSeconds:.1f}s")
    
    # Carry-forward context
    if checkpoint.carryForwardContext:
        cf = checkpoint.carryForwardContext
        lines.append("")
        lines.append("**Carry-forward best**:")
        lines.append(f"- {cf.metricName}: {cf.run.metric} (run #{cf.run.run})")
        lines.append(f"- {cf.run.description}")
    
    # Recent runs
    if checkpoint.recentLoggedRuns:
        lines.append("")
        lines.append("**Recent runs**:")
        for run in checkpoint.recentLoggedRuns[-5:]:
            baseline_marker = " [baseline]" if run.baseline else ""
            status_marker = f" [{run.status}]" if run.status != "keep" else ""
            lines.append(f"- #{run.run}{baseline_marker}{status_marker} {run.metric} — {run.description}")
    
    # Ideas backlog preview
    if state.ideas.hasBacklog and state.ideas.preview:
        lines.append("")
        lines.append("**Ideas backlog** (for later exploration):")
        for idea in state.ideas.preview[:3]:
            lines.append(f"- {idea}")
        if state.ideas.pendingCount > 3:
            lines.append(f"- ... and {state.ideas.pendingCount - 3} more")
    
    lines.append("---")
    lines.append("")
    
    return "\n".join(lines)


def get_short_status(cwd: str) -> str:
    """
    Get a short one-line status summary for quick reference.
    
    Args:
        cwd: Working directory (repo root)
    
    Returns:
        Short status string or empty string if not active.
    """
    lock_status = getAutoresearchSessionLockStatus(cwd)
    if lock_status.state != "active" or not lock_status.ownedByCurrentProcess:
        return ""
    
    checkpoint = readAutoresearchCheckpoint(cwd)
    if checkpoint is None:
        return ""
    
    pending = getAutoresearchPendingRun(cwd)
    pending_str = " (pending log)" if pending else ""
    
    return (
        f"autoresearch: {checkpoint.session.name or 'session'} | "
        f"seg {checkpoint.session.currentSegment} | "
        f"runs {checkpoint.session.currentRunCount}/{checkpoint.session.totalRunCount} | "
        f"best: {checkpoint.session.currentBestMetric}{checkpoint.session.metricUnit or ''}{pending_str}"
    )
