"""
Text command handler for autoresearch.

Provides handle_autoresearch_command(args, cwd) for processing
text commands from the /autoresearch command interface.
"""

import re
from typing import Any, Optional

from hermes_autoresearch.state import reconstructStateFromJsonl
from hermes_autoresearch.checkpoint import readAutoresearchCheckpoint
from hermes_autoresearch.session_lock import getAutoresearchSessionLockStatus
from hermes_autoresearch.runtime_state import (
    getAutoresearchRuntimeState,
    setAutoresearchRuntimeMode,
    getAutoresearchPendingRun,
)
from hermes_autoresearch.confidence import formatConfidenceLine, describeConfidence
from hermes_autoresearch.files import getAutoresearchRootFilePath, AUTORESEARCH_ROOT_FILES


def handle_autoresearch_command(args: list[str], cwd: str) -> str:
    """
    Handle a text command from the /autoresearch interface.
    
    Supported commands:
        /autoresearch status          - Show current session status
        /autoresearch setup <name> <metric> <direction> - Initialize session
        /autoresearch resume          - Resume existing session
        /autoresearch mode <auto|on|off> - Set runtime mode
        /autoresearch pending         - Show pending run info
        /autoresearch stop            - Stop the session (release lock)
        /autoresearch help            - Show help message
    
    Args:
        args: Command arguments (first arg is the subcommand)
        cwd: Working directory
    
    Returns:
        Human-readable response string
    """
    if not args:
        return _format_help()
    
    subcommand = args[0].lower()
    rest_args = args[1:]
    
    if subcommand in ("status", "s", "st"):
        return _handle_status(cwd, rest_args)
    elif subcommand in ("setup", "init", "start"):
        return _handle_setup(cwd, rest_args)
    elif subcommand in ("resume", "res"):
        return _handle_resume(cwd, rest_args)
    elif subcommand in ("mode", "m"):
        return _handle_mode(cwd, rest_args)
    elif subcommand in ("pending", "p"):
        return _handle_pending(cwd, rest_args)
    elif subcommand in ("stop", "quit", "exit"):
        return _handle_stop(cwd, rest_args)
    elif subcommand in ("help", "h", "?"):
        return _format_help()
    elif subcommand in ("files", "f"):
        return _handle_files(cwd, rest_args)
    elif subcommand in ("ideas", "i"):
        return _handle_ideas(cwd, rest_args)
    else:
        return f"Unknown subcommand: {subcommand}\n\n{_format_help()}"


def _handle_status(cwd: str, _args: list[str]) -> str:
    """Handle status subcommand."""
    lock_status = getAutoresearchSessionLockStatus(cwd)
    checkpoint = readAutoresearchCheckpoint(cwd)
    state = reconstructStateFromJsonl(cwd)
    
    if checkpoint is None:
        return "No active autoresearch session. Run `/autoresearch setup` to initialize."
    
    lines = [
        f"**Autoresearch Status**",
        "",
        f"Session: {checkpoint.session.name or '(unnamed)'}",
        f"Metric: {checkpoint.session.metricName} ({checkpoint.session.metricUnit or 'unitless'}, {checkpoint.session.bestDirection} better)",
        f"Segment: {checkpoint.session.currentSegment} | Runs: {checkpoint.session.currentRunCount} (total: {checkpoint.session.totalRunCount})",
    ]
    
    if checkpoint.session.currentBaselineMetric is not None:
        lines.append(f"Baseline: {checkpoint.session.currentBaselineMetric}{checkpoint.session.metricUnit or ''}")
    
    if checkpoint.session.currentBestMetric is not None:
        lines.append(f"Best kept: {checkpoint.session.currentBestMetric}{checkpoint.session.metricUnit or ''}")
    
    if checkpoint.session.confidence is not None:
        lines.append(formatConfidenceLine(checkpoint.session.confidence))
    
    pending = getAutoresearchPendingRun(cwd)
    if pending:
        lines.append("")
        lines.append(f"**Pending**: `{pending.command}` - {pending.primaryMetric} (awaiting log_experiment)")
    
    lock_state = "active" if lock_status.ownedByCurrentProcess else "locked"
    lines.append("")
    lines.append(f"Lock: {lock_state} (PID {lock_status.pid})")
    
    return "\n".join(lines)


def _handle_setup(cwd: str, args: list[str]) -> str:
    """Handle setup subcommand."""
    if len(args) < 3:
        return "Usage: /autoresearch setup <name> <metric> <direction>\nExample: /autoresearch setup latency-optimization latency_ms lower"
    
    name = args[0]
    metric = args[1]
    direction = args[2].lower()
    
    if direction not in ("lower", "higher"):
        return f"Invalid direction '{direction}'. Must be 'lower' or 'higher'."
    
    # Import here to avoid circular imports and use the actual tool
    from hermes_autoresearch.tools.init_experiment import init_experiment
    
    result = init_experiment(
        cwd=cwd,
        name=name,
        metricName=metric,
        bestDirection=direction,
    )
    
    if result.get("success"):
        msg = f"Initialized autoresearch session: {name}\n"
        msg += f"Metric: {metric} ({direction} is better)"
        if result.get("carryForwardContext"):
            cf = result["carryForwardContext"]
            msg += f"\nCarry-forward: {cf['metricName']} = {cf['run']['metric']} from run #{cf['run']['run']}"
        return msg
    else:
        return f"Failed to initialize: {result.get('error', 'Unknown error')}"


def _handle_resume(cwd: str, _args: list[str]) -> str:
    """Handle resume subcommand."""
    from hermes_autoresearch.tools.init_experiment import init_experiment
    
    checkpoint = readAutoresearchCheckpoint(cwd)
    if checkpoint is None:
        return "No session to resume. Run `/autoresearch setup` first."
    
    result = init_experiment(
        cwd=cwd,
        name=checkpoint.session.name or "Resumed Session",
        metricName=checkpoint.session.metricName,
        bestDirection=checkpoint.session.bestDirection,
        metricUnit=checkpoint.session.metricUnit,
    )
    
    if result.get("success"):
        return f"Resumed session: {checkpoint.session.name or 'unnamed'}\nSegment: {result['session']['currentSegment']}"
    else:
        return f"Failed to resume: {result.get('error', 'Unknown error')}"


def _handle_mode(cwd: str, args: list[str]) -> str:
    """Handle mode subcommand."""
    if not args:
        state = getAutoresearchRuntimeState(cwd)
        return f"Current mode: {state['mode']}"
    
    mode = args[0].lower()
    if mode not in ("auto", "on", "off"):
        return f"Invalid mode '{mode}'. Must be 'auto', 'on', or 'off'."
    
    setAutoresearchRuntimeMode(cwd, mode)
    return f"Mode set to: {mode}"


def _handle_pending(cwd: str, _args: list[str]) -> str:
    """Handle pending subcommand."""
    pending = getAutoresearchPendingRun(cwd)
    
    if pending is None:
        return "No pending run. Run an experiment first."
    
    lines = [
        "**Pending Run**",
        "",
        f"Command: `{pending.command}`",
        f"Commit: {pending.commit or 'unknown'}",
    ]
    
    if pending.primaryMetric is not None:
        lines.append(f"Metric: {pending.primaryMetric}")
    
    if pending.metrics:
        lines.append("All metrics:")
        for name, value in pending.metrics.items():
            lines.append(f"  - {name}: {value}")
    
    lines.append(f"Duration: {pending.durationSeconds:.1f}s")
    lines.append(f"Passed: {pending.passed}")
    
    if pending.timedOut:
        lines.append("⚠️ Timed out")
    
    lines.append("")
    lines.append("Run `/autoresearch log keep <description>` or `/autoresearch log discard <idea>` to log this run.")
    
    return "\n".join(lines)


def _handle_stop(cwd: str, _args: list[str]) -> str:
    """Handle stop subcommand."""
    from hermes_autoresearch.session_lock import removeAutoresearchSessionLock
    from hermes_autoresearch.runtime_state import clearAutoresearchRuntimeState
    
    removeAutoresearchSessionLock(cwd)
    clearAutoresearchRuntimeState(cwd)
    
    return "Autoresearch session stopped and lock released."


def _handle_files(cwd: str, _args: list[str]) -> str:
    """Handle files subcommand."""
    lines = ["**Autoresearch Files**", ""]
    for key, path in AUTORESEARCH_ROOT_FILES.items():
        full_path = getAutoresearchRootFilePath(cwd, key)
        lines.append(f"- {key}: `{full_path}`")
    return "\n".join(lines)


def _handle_ideas(cwd: str, _args: list[str]) -> str:
    """Handle ideas subcommand."""
    state = reconstructStateFromJsonl(cwd)
    
    if not state.ideas.hasBacklog:
        return "No ideas in backlog."
    
    lines = ["**Ideas Backlog**", ""]
    for i, idea in enumerate(state.ideas.preview, 1):
        lines.append(f"{i}. {idea}")
    
    if state.ideas.pendingCount > len(state.ideas.preview):
        lines.append(f"\n... and {state.ideas.pendingCount - len(state.ideas.preview)} more.")
    
    return "\n".join(lines)


def _format_help() -> str:
    """Format the help message."""
    return """**Autoresearch Commands**

Setup/Resume:
  /autoresearch setup <name> <metric> <direction>  - Initialize new session
  /autoresearch resume                               - Resume existing session

Status:
  /autoresearch status                               - Show session status
  /autoresearch pending                              - Show pending run
  /autoresearch ideas                                - Show ideas backlog
  /autoresearch files                                - Show file paths

Control:
  /autoresearch mode <auto|on|off>                   - Set runtime mode
  /autoresearch stop                                 - Stop session, release lock

Help:
  /autoresearch help                                 - Show this help

Workflow:
  1. /autoresearch setup <name> <metric> <direction>
  2. Edit code
  3. run_experiment (via tool)
  4. log_experiment keep|discard (via tool)
  5. Repeat from step 2
"""
