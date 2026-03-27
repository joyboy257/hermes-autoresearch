"""
Git operations for autoresearch.

Handles reading git state and committing experiment results.
"""

import subprocess
import json
from dataclasses import dataclass
from typing import Optional, Any

from hermes_autoresearch.config import GIT_TIMEOUT_MS


@dataclass(frozen=True)
class GitCommandResult:
    """Result of a git command execution."""
    code: int | None
    stdout: str
    stderr: str
    combinedOutput: str


def _runGitCommand(cwd: str, args: list[str]) -> GitCommandResult:
    """Run a git command and return the result."""
    try:
        result = subprocess.run(
            ["git"] + args,
            timeout=GIT_TIMEOUT_MS / 1000,
            capture_output=True,
            text=True,
            cwd=cwd,
        )
        stdout = result.stdout
        stderr = result.stderr
        combined = f"{stdout}{stderr}".strip() or _describeTermination(result.returncode)
        return GitCommandResult(
            code=result.returncode,
            stdout=stdout,
            stderr=stderr,
            combinedOutput=combined,
        )
    except subprocess.TimeoutExpired:
        return GitCommandResult(
            code=None,
            stdout="",
            stderr="",
            combinedOutput="git command timed out",
        )
    except Exception as e:
        return GitCommandResult(
            code=-1,
            stdout="",
            stderr="",
            combinedOutput=str(e),
        )


def _describeTermination(code: int) -> str:
    """Describe a process termination code."""
    return ""


def readShortHeadCommit(cwd: str) -> Optional[str]:
    """Read the short (7-char) HEAD commit hash."""
    result = _runGitCommand(cwd, ["rev-parse", "--short=7", "HEAD"])
    if result.code == 0 and result.stdout.strip():
        return result.stdout.strip()
    return None


def readCurrentBranch(cwd: str) -> Optional[str]:
    """Read the current branch name."""
    result = _runGitCommand(cwd, ["branch", "--show-current"])
    if result.code == 0 and result.stdout.strip():
        return result.stdout.strip()
    return None


def countCommitsSince(cwd: str, sinceCommit: str) -> Optional[int]:
    """Count commits between sinceCommit and HEAD."""
    result = _runGitCommand(cwd, ["rev-list", "--count", f"{sinceCommit}..HEAD"])
    if result.code != 0:
        return None
    count = result.stdout.strip()
    if count.isdigit():
        return int(count)
    return None


@dataclass(frozen=True)
class GitKeepResult:
    """Result of committing a kept experiment."""
    attempted: bool
    committed: bool
    commit: str
    summary: str
    command: GitCommandResult


def commitKeptExperiment(
    cwd: str,
    description: str,
    metricName: str,
    metric: float,
    metrics: dict[str, float],
    commit: str,
) -> GitKeepResult:
    """Commit the experiment result to git."""
    result_data = {"status": "keep", **(metrics if metrics else {}), metricName: metric}
    commit_msg = f"{description}\n\nResult: {json.dumps(result_data)}"
    
    # Check for repo root
    root_result = _runGitCommand(cwd, ["rev-parse", "--show-toplevel"])
    if root_result.code != 0 or not root_result.stdout.strip():
        return GitKeepResult(
            attempted=True,
            committed=False,
            commit=commit,
            summary=f"Git repo check failed (exit {root_result.code}): {_truncateOutput(root_result.combinedOutput)}",
            command=root_result,
        )
    
    repo_root = root_result.stdout.strip()
    
    # Git add -A
    add_result = _runGitCommand(repo_root, ["add", "-A"])
    if add_result.code != 0:
        return GitKeepResult(
            attempted=True,
            committed=False,
            commit=commit,
            summary=f"Git add failed (exit {add_result.code}): {_truncateOutput(add_result.combinedOutput)}",
            command=add_result,
        )
    
    # Check if anything to commit
    diff_result = _runGitCommand(repo_root, ["diff", "--cached", "--quiet"])
    if diff_result.code == 0:
        return GitKeepResult(
            attempted=True,
            committed=False,
            commit=commit,
            summary="Git: nothing to commit (working tree clean)",
            command=diff_result,
        )
    if diff_result.code != 1:
        return GitKeepResult(
            attempted=True,
            committed=False,
            commit=commit,
            summary=f"Git diff check failed (exit {diff_result.code}): {_truncateOutput(diff_result.combinedOutput)}",
            command=diff_result,
        )
    
    # Git commit
    commit_result = _runGitCommand(repo_root, ["commit", "-m", commit_msg])
    if commit_result.code != 0:
        return GitKeepResult(
            attempted=True,
            committed=False,
            commit=commit,
            summary=f"Git commit failed (exit {commit_result.code}): {_truncateOutput(commit_result.combinedOutput)}",
            command=commit_result,
        )
    
    # Get the actual commit hash
    rev_result = _runGitCommand(repo_root, ["rev-parse", "--short=7", "HEAD"])
    actual_commit = rev_result.stdout.strip()[:7] if rev_result.code == 0 and rev_result.stdout.strip() else commit
    first_line = commit_result.combinedOutput.split("\n")[0].strip() or "commit created"
    
    return GitKeepResult(
        attempted=True,
        committed=True,
        commit=actual_commit,
        summary=f"Git: committed - {first_line}",
        command=commit_result,
    )


def _truncateOutput(output: str, max_len: int = 200) -> str:
    """Truncate output for display."""
    if not output:
        return "no output"
    return output[:max_len] + "..." if len(output) > max_len else output
