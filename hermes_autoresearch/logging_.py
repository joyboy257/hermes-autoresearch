"""
JSONL logging utilities for autoresearch experiment results.

autoresearch.jsonl format:
- Config headers: {"type": "config", "name": "...", "metricName": "...", ...}
- Result entries: {"run": 1, "commit": "abc1234", "metric": 4200, ...}
"""

import json
from dataclasses import dataclass, asdict
from typing import Optional, Literal

from hermes_autoresearch.files import getAutoresearchRootFilePath


@dataclass(frozen=True)
class AutoresearchConfigHeader:
    """Configuration header written to autoresearch.jsonl on init."""
    type: Literal["config"]
    name: str
    metricName: str
    metricUnit: str
    bestDirection: Literal["lower", "higher"]


@dataclass(frozen=True)
class AutoresearchResultEntry:
    """A single experiment result entry in autoresearch.jsonl."""
    run: int
    commit: str
    metric: float
    metrics: dict[str, float]
    status: Literal["keep", "discard", "crash"]
    baseline: bool
    description: str
    timestamp: int
    segment: int
    confidence: Optional[float]


def createConfigHeader(
    name: str,
    metricName: str,
    metricUnit: str,
    bestDirection: Literal["lower", "higher"],
) -> AutoresearchConfigHeader:
    """Create a new config header object."""
    return AutoresearchConfigHeader(
        type="config",
        name=name,
        metricName=metricName,
        metricUnit=metricUnit,
        bestDirection=bestDirection,
    )


def writeConfigHeader(
    cwd: str,
    header: AutoresearchConfigHeader,
    mode: Literal["create", "append"],
) -> None:
    """
    Write the config header to autoresearch.jsonl.
    
    Args:
        cwd: Working directory (repo root)
        header: Config header to write
        mode: "create" to overwrite, "append" to add to existing file
    """
    jsonl_path = getAutoresearchRootFilePath(cwd, "resultsLog")
    line = json.dumps(asdict(header)) + "\n"
    
    if mode == "append":
        with open(jsonl_path, "a", encoding="utf-8") as f:
            f.write(line)
    else:
        with open(jsonl_path, "w", encoding="utf-8") as f:
            f.write(line)


def appendResultEntry(cwd: str, entry: AutoresearchResultEntry) -> None:
    """
    Append a result entry to autoresearch.jsonl.
    
    Args:
        cwd: Working directory (repo root)
        entry: Result entry to append
    """
    jsonl_path = getAutoresearchRootFilePath(cwd, "resultsLog")
    with open(jsonl_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(asdict(entry)) + "\n")
