"""
Session lock management for preventing parallel autoresearch sessions.

The lock file (autoresearch.lock) contains a JSON object with pid and timestamp.
"""

import os
import json
import errno
from dataclasses import dataclass
from typing import Optional

from hermes_autoresearch.files import getAutoresearchRootFilePath


@dataclass(frozen=True)
class AutoresearchSessionLock:
    """Represents the lock data stored in autoresearch.lock."""
    pid: int
    timestamp: int


@dataclass(frozen=True)
class AutoresearchSessionLockStatus:
    """Current status of the session lock."""
    state: str  # "missing" | "active" | "stale"
    pid: Optional[int]
    timestamp: Optional[int]
    ownedByCurrentProcess: bool


def readAutoresearchSessionLock(cwd: str) -> Optional[AutoresearchSessionLock]:
    """
    Read the current session lock data.
    
    Returns None if lock file doesn't exist or is invalid.
    """
    lock_path = getAutoresearchRootFilePath(cwd, "sessionLock")
    if not os.path.exists(lock_path):
        return None
    
    try:
        with open(lock_path, "r", encoding="utf-8") as f:
            parsed = json.load(f)
        
        if not isinstance(parsed.get("pid"), int) or not isinstance(parsed.get("timestamp"), int):
            return None
        
        return AutoresearchSessionLock(
            pid=parsed["pid"],
            timestamp=parsed["timestamp"],
        )
    except (json.JSONDecodeError, OSError):
        return None


def isProcessAlive(pid: int) -> bool:
    """
    Check if a process with the given PID is alive.
    
    Uses os.kill(pid, 0) which doesn't actually send a signal but checks
    if the process exists and we have permission to send signals to it.
    """
    if not isinstance(pid, int) or pid <= 0:
        return False
    
    try:
        os.kill(pid, 0)
        return True
    except OSError as e:
        # EPERM means process exists but we don't have permission
        # ESRCH means process doesn't exist
        return e.errno == errno.EPERM


def getAutoresearchSessionLockStatus(cwd: str) -> AutoresearchSessionLockStatus:
    """
    Get the current status of the session lock.
    """
    lock = readAutoresearchSessionLock(cwd)
    
    if lock is None:
        return AutoresearchSessionLockStatus(
            state="missing",
            pid=None,
            timestamp=None,
            ownedByCurrentProcess=False,
        )
    
    active = isProcessAlive(lock.pid)
    return AutoresearchSessionLockStatus(
        state="active" if active else "stale",
        pid=lock.pid,
        timestamp=lock.timestamp,
        ownedByCurrentProcess=lock.pid == os.getpid(),
    )


def acquireAutoresearchSessionLock(cwd: str) -> AutoresearchSessionLockStatus:
    """
    Acquire the session lock for the current process.
    
    If the lock is held by another active process, returns the status
    of that lock without modifying it.
    """
    status = getAutoresearchSessionLockStatus(cwd)
    
    if status.state == "active" and not status.ownedByCurrentProcess:
        return status
    
    next_lock = AutoresearchSessionLock(
        pid=os.getpid(),
        timestamp=int(1000 * __import__("time").time()),
    )
    
    lock_path = getAutoresearchRootFilePath(cwd, "sessionLock")
    with open(lock_path, "w", encoding="utf-8") as f:
        json.dump({"pid": next_lock.pid, "timestamp": next_lock.timestamp}, f, indent=2)
    
    return AutoresearchSessionLockStatus(
        state="active",
        pid=next_lock.pid,
        timestamp=next_lock.timestamp,
        ownedByCurrentProcess=True,
    )


def removeAutoresearchSessionLock(cwd: str) -> None:
    """Remove the session lock file if it exists."""
    lock_path = getAutoresearchRootFilePath(cwd, "sessionLock")
    if os.path.exists(lock_path):
        os.unlink(lock_path)
