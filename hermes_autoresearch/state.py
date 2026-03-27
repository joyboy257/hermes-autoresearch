"""
State reconstruction from autoresearch.jsonl and related files.

This module handles reading and reconstructing the autoresearch state
from the persistent JSONL log file.
"""

import json
from dataclasses import dataclass, field
from typing import Optional, Literal

from hermes_autoresearch.files import getAutoresearchRootFilePath, readAutoresearchRootFile
from hermes_autoresearch.confidence import computeConfidence


# Type definitions
@dataclass(frozen=True)
class SecondaryMetricDef:
    """Definition of a secondary metric being tracked."""
    name: str
    unit: str


@dataclass(frozen=True)
class AutoresearchRunSnapshot:
    """A single experiment run reconstructed from the log."""
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


@dataclass(frozen=True)
class AutoresearchIdeasSnapshot:
    """Summary of the ideas backlog."""
    hasBacklog: bool
    pendingCount: int
    preview: list[str]


@dataclass(frozen=True)
class AutoresearchStateSnapshot:
    """Complete state snapshot of the autoresearch session."""
    name: Optional[str]
    metricName: str
    metricUnit: str
    bestDirection: Literal["lower", "higher"]
    secondaryMetrics: list[SecondaryMetricDef]
    currentSegment: int
    currentRunCount: int
    totalRunCount: int
    currentBaselineMetric: Optional[float]
    currentBestMetric: Optional[float]
    confidence: Optional[float]
    lastRun: Optional[AutoresearchRunSnapshot]
    mode: Literal["inactive", "active"]
    hasSessionDoc: bool
    ideas: AutoresearchIdeasSnapshot


def createEmptyStateSnapshot() -> AutoresearchStateSnapshot:
    """Create an empty/default state snapshot."""
    return AutoresearchStateSnapshot(
        name=None,
        metricName="metric",
        metricUnit="",
        bestDirection="lower",
        secondaryMetrics=[],
        currentSegment=0,
        currentRunCount=0,
        totalRunCount=0,
        currentBaselineMetric=None,
        currentBestMetric=None,
        confidence=None,
        lastRun=None,
        mode="inactive",
        hasSessionDoc=False,
        ideas=AutoresearchIdeasSnapshot(
            hasBacklog=False,
            pendingCount=0,
            preview=[],
        ),
    )


def _detectAutoresearchMode(sessionDoc: Optional[str]) -> Literal["inactive", "active"]:
    """Detect if autoresearch mode is active based on session doc content."""
    if sessionDoc is None:
        return "inactive"
    
    normalized = sessionDoc.lower()
    markers = ["# autoresearch", "## objective", "## what's been tried", "## how to run"]
    
    for marker in markers:
        if marker in normalized:
            return "active"
    
    return "active" if sessionDoc.strip() else "inactive"


def _summarizeIdeasBacklog(ideasBacklog: Optional[str]) -> AutoresearchIdeasSnapshot:
    """Summarize the ideas backlog file."""
    if ideasBacklog is None:
        return AutoresearchIdeasSnapshot(
            hasBacklog=False,
            pendingCount=0,
            preview=[],
        )
    
    lines = ideasBacklog.split("\n")
    ideas = []
    
    for line in lines:
        stripped = line.strip()
        # Match list markers: -, *, +, or numbered patterns
        if stripped and any(stripped.startswith(prefix) for prefix in ["-", "*", "+"]) and len(stripped) > 1:
            # Remove list prefix
            idea_text = stripped[1:].strip()
            if idea_text:
                ideas.append(idea_text)
        elif stripped and len(ideas) > 0:
            # Continuation line (indented) - skip
            pass
        elif stripped[0].isdigit() and ". " in stripped[:5]:
            # Numbered list like "1. Something"
            parts = stripped.split(". ", 1)
            if len(parts) == 2 and parts[0].isdigit():
                idea_text = parts[1].strip()
                if idea_text:
                    ideas.append(idea_text)
    
    return AutoresearchIdeasSnapshot(
        hasBacklog=len(ideas) > 0,
        pendingCount=len(ideas),
        preview=ideas[:3],
    )


def _normalizeMetrics(metrics: Optional[dict]) -> dict[str, float]:
    """Normalize metrics dict to only include finite numeric values."""
    if not metrics or not isinstance(metrics, dict):
        return {}
    
    result = {}
    for key, value in metrics.items():
        if isinstance(value, (int, float)) and isinstance(value, (int, float)):
            if value == value:  # Not NaN
                result[key] = float(value)
    return result


def _isBetter(current: float, best: float, direction: str) -> bool:
    """Check if current is better than best given the direction."""
    return current < best if direction == "lower" else current > best


def _inferMetricUnit(name: str) -> str:
    """Infer the unit for a metric based on its name."""
    if "µs" in name or name.endswith("_µs"):
        return "µs"
    if "ms" in name or name.endswith("_ms"):
        return "ms"
    if "sec" in name or name.endswith("_s"):
        return "s"
    if "kb" in name or name.endswith("_kb"):
        return "kb"
    if "mb" in name or name.endswith("_mb"):
        return "mb"
    return ""


def reconstructStateFromJsonl(cwd: str) -> AutoresearchStateSnapshot:
    """
    Reconstruct the complete autoresearch state from the JSONL log.
    
    This parses the autoresearch.jsonl file and combines it with other
    state files to create a complete snapshot.
    """
    session_doc = readAutoresearchRootFile(cwd, "sessionDoc")
    ideas_backlog = readAutoresearchRootFile(cwd, "ideasBacklog")
    jsonl_content = readAutoresearchRootFile(cwd, "resultsLog")
    
    # Initialize mutable state
    state: dict = {
        "name": None,
        "metricName": "metric",
        "metricUnit": "",
        "bestDirection": "lower",
        "currentSegment": 0,
        "currentRunCount": 0,
        "totalRunCount": 0,
        "currentBaselineMetric": None,
        "currentBestMetric": None,
        "confidence": None,
        "lastRun": None,
        "mode": _detectAutoresearchMode(session_doc),
        "hasSessionDoc": session_doc is not None,
        "ideas": _summarizeIdeasBacklog(ideas_backlog),
        "secondaryMetrics": [],
    }
    
    if jsonl_content is None:
        result = createEmptyStateSnapshot()
        return AutoresearchStateSnapshot(
            name=state["name"],
            metricName=state["metricName"],
            metricUnit=state["metricUnit"],
            bestDirection=state["bestDirection"],
            secondaryMetrics=[],
            currentSegment=state["currentSegment"],
            currentRunCount=state["currentRunCount"],
            totalRunCount=state["totalRunCount"],
            currentBaselineMetric=state["currentBaselineMetric"],
            currentBestMetric=state["currentBestMetric"],
            confidence=state["confidence"],
            lastRun=state["lastRun"],
            mode=state["mode"],
            hasSessionDoc=state["hasSessionDoc"],
            ideas=state["ideas"],
        )
    
    current_secondary_metrics: dict[str, SecondaryMetricDef] = {}
    current_segment_runs: list[tuple[float, str]] = []
    current_run_index = 0
    has_seen_any_run = False
    
    lines = [line.strip() for line in jsonl_content.split("\n") if line.strip()]
    
    for line in lines:
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        
        # Handle config header
        if entry.get("type") == "config":
            if entry.get("name"):
                state["name"] = entry["name"]
            if entry.get("metricName"):
                state["metricName"] = entry["metricName"]
            if entry.get("metricUnit") is not None:
                state["metricUnit"] = entry["metricUnit"]
            if entry.get("bestDirection") in ("lower", "higher"):
                state["bestDirection"] = entry["bestDirection"]
            
            if has_seen_any_run:
                state["currentSegment"] += 1
            
            state["currentRunCount"] = 0
            state["currentBaselineMetric"] = None
            state["currentBestMetric"] = None
            state["confidence"] = None
            current_run_index = 0
            current_segment_runs = []
            current_secondary_metrics = {}
            continue
        
        # Skip entries without a metric
        if not isinstance(entry.get("metric"), (int, float)):
            continue
        
        has_seen_any_run = True
        current_run_index += 1
        state["currentRunCount"] = current_run_index
        state["totalRunCount"] += 1
        
        metric = float(entry["metric"])
        is_baseline = entry.get("baseline") is True or current_run_index == 1
        
        run = AutoresearchRunSnapshot(
            run=entry.get("run", current_run_index) if isinstance(entry.get("run"), int) else current_run_index,
            commit=entry.get("commit", ""),
            metric=metric,
            metrics=_normalizeMetrics(entry.get("metrics")),
            status=entry.get("status", "keep"),
            baseline=is_baseline,
            description=entry.get("description", ""),
            timestamp=entry.get("timestamp", 0),
            segment=entry.get("segment", state["currentSegment"]),
            confidence=entry.get("confidence"),
        )
        
        # Track baseline metric
        if state["currentBaselineMetric"] is None:
            state["currentBaselineMetric"] = run.metric
        
        # Track best kept metric
        if run.status == "keep" and run.metric > 0:
            if state["currentBestMetric"] is None or _isBetter(run.metric, state["currentBestMetric"], state["bestDirection"]):
                state["currentBestMetric"] = run.metric
        
        # Track secondary metrics
        for metric_name in run.metrics:
            if metric_name not in current_secondary_metrics:
                current_secondary_metrics[metric_name] = SecondaryMetricDef(
                    name=metric_name,
                    unit=_inferMetricUnit(metric_name),
                )
        
        # For confidence calculation
        current_segment_runs.append((run.metric, run.status))
        state["lastRun"] = run
    
    # Compute confidence from the current segment's runs
    state["confidence"] = computeConfidence(current_segment_runs, state["bestDirection"])
    state["secondaryMetrics"] = list(current_secondary_metrics.values())
    
    return AutoresearchStateSnapshot(
        name=state["name"],
        metricName=state["metricName"],
        metricUnit=state["metricUnit"],
        bestDirection=state["bestDirection"],
        secondaryMetrics=state["secondaryMetrics"],
        currentSegment=state["currentSegment"],
        currentRunCount=state["currentRunCount"],
        totalRunCount=state["totalRunCount"],
        currentBaselineMetric=state["currentBaselineMetric"],
        currentBestMetric=state["currentBestMetric"],
        confidence=state["confidence"],
        lastRun=state["lastRun"],
        mode=state["mode"],
        hasSessionDoc=state["hasSessionDoc"],
        ideas=state["ideas"],
    )


def readRecentLoggedRuns(cwd: str, limit: int) -> list[AutoresearchRunSnapshot]:
    """
    Read the most recent logged runs from the JSONL.
    
    Args:
        cwd: Working directory
        limit: Maximum number of runs to return (0 = return none)
    
    Returns:
        List of recent AutoresearchRunSnapshot objects
    """
    runs = _readAllLoggedRuns(cwd)
    return [] if limit <= 0 else runs[-limit:]


def readBestLoggedRun(
    cwd: str,
    direction: str,
    segment: Optional[int] = None,
) -> Optional[AutoresearchRunSnapshot]:
    """
    Find the best run in the log for a given direction and optional segment.
    
    Args:
        cwd: Working directory
        direction: "lower" or "higher"
        segment: If provided, only consider runs in this segment
    
    Returns:
        The best AutoresearchRunSnapshot, or None if no runs exist
    """
    runs = _readAllLoggedRuns(cwd)
    
    if segment is not None:
        runs = [r for r in runs if r.segment == segment]
    
    if not runs:
        return None
    
    # First try to find best among keep runs
    keep_runs = [r for r in runs if r.status == "keep"]
    candidates = keep_runs if keep_runs else runs
    
    best = candidates[0]
    for run in candidates[1:]:
        if _isBetter(run.metric, best.metric, direction):
            best = run
    
    return best


def _readAllLoggedRuns(cwd: str) -> list[AutoresearchRunSnapshot]:
    """Read all logged runs from the JSONL file."""
    jsonl_content = readAutoresearchRootFile(cwd, "resultsLog")
    if jsonl_content is None:
        return []
    
    runs: list[AutoresearchRunSnapshot] = []
    current_segment = 0
    current_run_index = 0
    has_seen_any_run = False
    
    lines = [line.strip() for line in jsonl_content.split("\n") if line.strip()]
    
    for line in lines:
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        
        # Handle config header
        if entry.get("type") == "config":
            if has_seen_any_run:
                current_segment += 1
            current_run_index = 0
            continue
        
        # Skip entries without a metric
        if not isinstance(entry.get("metric"), (int, float)):
            continue
        
        has_seen_any_run = True
        current_run_index += 1
        
        metric = float(entry["metric"])
        is_baseline = entry.get("baseline") is True or current_run_index == 1
        
        runs.append(AutoresearchRunSnapshot(
            run=entry.get("run", current_run_index) if isinstance(entry.get("run"), int) else current_run_index,
            commit=entry.get("commit", ""),
            metric=metric,
            metrics=_normalizeMetrics(entry.get("metrics")),
            status=entry.get("status", "keep"),
            baseline=is_baseline,
            description=entry.get("description", ""),
            timestamp=entry.get("timestamp", 0),
            segment=entry.get("segment", current_segment),
            confidence=entry.get("confidence"),
        ))
    
    return runs
