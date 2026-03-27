"""
Experiment command execution with timeout.
"""

import subprocess
from dataclasses import dataclass
from typing import Optional

from hermes_autoresearch.config import DEFAULT_TIMEOUT_SECONDS, OUTPUT_TAIL_LINES


@dataclass(frozen=True)
class ExperimentExecutionResult:
    command: str
    exitCode: Optional[int]
    durationSeconds: float
    passed: bool
    crashed: bool
    timedOut: bool
    tailOutput: str
    stdout: str
    stderr: str


def executeExperimentCommand(
    command: str,
    cwd: str,
    timeoutSeconds: Optional[int] = None,
) -> ExperimentExecutionResult:
    """
    Execute an experiment command with timeout.
    
    Args:
        command: Shell command to run
        cwd: Working directory
        timeoutSeconds: Timeout in seconds (default: 600)
    
    Returns:
        ExperimentExecutionResult with outcome details
    """
    timeout = timeoutSeconds if timeoutSeconds is not None else DEFAULT_TIMEOUT_SECONDS
    startedAt = _time_ms()
    
    try:
        result = subprocess.run(
            ["bash", "-c", command],
            timeout=timeout,
            capture_output=True,
            text=True,
            cwd=cwd,
        )
        duration = (_time_ms() - startedAt) / 1000.0
        passed = result.returncode == 0
        timedOut = False
    except subprocess.TimeoutExpired as e:
        duration = timeout
        passed = False
        timedOut = True
        stdout = e.stdout.decode("utf-8") if e.stdout else ""
        stderr = e.stderr.decode("utf-8") if e.stderr else ""
        return ExperimentExecutionResult(
            command=command,
            exitCode=None,
            durationSeconds=duration,
            passed=False,
            crashed=True,
            timedOut=True,
            tailOutput=_createOutputTail(stdout, stderr),
            stdout=stdout,
            stderr=stderr,
        )
    except Exception as e:
        duration = (_time_ms() - startedAt) / 1000.0
        return ExperimentExecutionResult(
            command=command,
            exitCode=-1,
            durationSeconds=duration,
            passed=False,
            crashed=True,
            timedOut=False,
            tailOutput=str(e),
            stdout="",
            stderr=str(e),
        )
    
    return ExperimentExecutionResult(
        command=command,
        exitCode=result.returncode,
        durationSeconds=duration,
        passed=passed,
        crashed=not passed,
        timedOut=False,
        tailOutput=_createOutputTail(result.stdout, result.stderr),
        stdout=result.stdout,
        stderr=result.stderr,
    )


def _time_ms() -> float:
    """Get current time in milliseconds."""
    return __import__("time").time() * 1000


def _createOutputTail(stdout: str, stderr: str) -> str:
    """Create a tail of the combined output."""
    combined = "\n".join(s for s in [stdout, stderr] if s.strip()).strip()
    if not combined:
        return ""
    lines = combined.split("\n")
    return "\n".join(lines[-OUTPUT_TAIL_LINES:])
