"""
MAD-based confidence scoring for experiment results.

Confidence = |best_kept - baseline| / MAD (median absolute deviation)

Confidence tiers:
- >= 2.0x = likely real improvement
- >= 1.0x = marginal (above noise but not certain)
- < 1.0x = within noise floor
"""

from typing import Optional


ConfidenceRun = tuple[float, str]  # (metric, status)


def _sorted_median(values: list[float]) -> float:
    """Compute the median of a sorted list of values."""
    if len(values) == 0:
        return 0.0
    
    sorted_values = sorted(values)
    mid = len(sorted_values) // 2
    
    if len(sorted_values) % 2 == 0:
        return (sorted_values[mid - 1] + sorted_values[mid]) / 2.0
    else:
        return sorted_values[mid]


def _is_better(current: float, best: float, direction: str) -> bool:
    """Check if current is better than best given the direction."""
    return (direction == "lower") if current < best else current > best


def computeConfidence(
    runs: list[ConfidenceRun],
    direction: str,  # "lower" | "higher"
) -> Optional[float]:
    """
    Compute the MAD-based confidence score for a set of experiment runs.
    
    Args:
        runs: List of (metric, status) tuples
        direction: "lower" or "higher" - which direction is better
    
    Returns:
        Confidence score (ratio of improvement to noise), or None if insufficient data
    """
    # Filter to usable runs with finite positive metrics
    usable_runs = [
        (metric, status) 
        for metric, status in runs 
        if isinstance(metric, (int, float)) and metric > 0 and metric == metric  # Not NaN
    ]
    
    if len(usable_runs) < 3:
        return None
    
    # Find baseline (first run with finite metric)
    baseline: Optional[float] = None
    for metric, _ in usable_runs:
        if isinstance(metric, (int, float)) and metric == metric:
            baseline = metric
            break
    
    if baseline is None:
        return None
    
    # Calculate median and MAD
    values = [metric for metric, _ in usable_runs]
    median = _sorted_median(values)
    deviations = [abs(v - median) for v in values]
    mad = _sorted_median(deviations)
    
    if mad == 0:
        return None
    
    # Find best kept run
    best_kept: Optional[float] = None
    for metric, status in usable_runs:
        if status != "keep":
            continue
        if best_kept is None or _is_better(metric, best_kept, direction):
            best_kept = metric
    
    if best_kept is None or best_kept == baseline:
        return None
    
    return abs(best_kept - baseline) / mad


def formatConfidenceLine(
    confidence: Optional[float],
    label: str = "Confidence",
) -> str:
    """Format a confidence value as a human-readable string."""
    if confidence is None:
        return f"{label}: n/a"
    return f"{label}: {describeConfidence(confidence)}"


def describeConfidence(confidence: float) -> str:
    """
    Describe what a confidence score means.
    
    Args:
        confidence: The confidence ratio (improvement / noise floor)
    
    Returns:
        Human-readable description
    """
    rendered = f"{confidence:.1f}"
    
    if confidence >= 2.0:
        return f"{rendered}x noise floor - improvement is likely real"
    elif confidence >= 1.0:
        return f"{rendered}x noise floor - improvement is above noise but marginal"
    else:
        return (
            f"{rendered}x noise floor - improvement is within noise. "
            "Consider re-running to confirm before keeping"
        )
