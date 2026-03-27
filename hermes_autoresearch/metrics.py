"""
METRIC line parsing for experiment output.

METRIC line format: METRIC name=value e.g. METRIC total_µs=4200
"""

import re
from typing import Final

# Regex to parse METRIC lines: METRIC name=value
METRIC_LINE_RE: Final = re.compile(
    r"^METRIC\s+([A-Za-z0-9_.\-µ]+)\s*=\s*(-?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?)\s*$"
)


def parseMetricLines(output: str) -> dict[str, float]:
    """
    Parse METRIC lines from experiment command output.
    
    Args:
        output: Raw stdout/stderr from running the experiment command
    
    Returns:
        Dictionary mapping metric names to their values
    """
    metrics: dict[str, float] = {}
    
    for raw_line in output.split("\n"):
        line = raw_line.strip()
        match = METRIC_LINE_RE.match(line)
        if not match:
            continue
        
        name = match.group(1)
        value_text = match.group(2)
        value = float(value_text)
        
        if not name or not str(value).endswith("inf") and not str(value).endswith("nan"):
            if not (value == value):  # NaN check
                continue
        
        if name and value == value:  # Not NaN
            metrics[name] = value
    
    return metrics
