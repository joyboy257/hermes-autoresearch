"""
Session document (autoresearch.md) synchronization.

The session doc is auto-updated after each init/run/log operation with
current metrics, runs, and checkpoint state.
"""

import os
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from hermes_autoresearch.checkpoint import AutoresearchCheckpoint

from hermes_autoresearch.config import AUTORESEARCH_ROOT_FILES
from hermes_autoresearch.files import getAutoresearchRootFilePath
from hermes_autoresearch.confidence import formatConfidenceLine


def syncAutoresearchSessionDoc(cwd: str, checkpoint: "AutoresearchCheckpoint") -> None:
    """
    Synchronize the session document (autoresearch.md) with current checkpoint state.
    
    Args:
        cwd: Working directory (repo root)
        checkpoint: Current checkpoint data
    """
    session_doc_path = getAutoresearchRootFilePath(cwd, "sessionDoc")
    existing = ""
    if os.path.exists(session_doc_path):
        with open(session_doc_path, "r", encoding="utf-8") as f:
            existing = f.read()
    
    doc = _ensureTitle(existing, checkpoint.session.name)
    
    # Update Metrics section
    doc = _upsertSection(
        doc,
        "## Metrics",
        f"- **Primary**: {checkpoint.session.metricName} ({checkpoint.session.metricUnit or 'unitless'}, {checkpoint.session.bestDirection} is better)",
    )
    
    # Update How to Run section
    doc = _upsertSection(
        doc,
        "## How to Run",
        f"`{AUTORESEARCH_ROOT_FILES['runnerScript']}` — should emit `METRIC name=number` lines for {checkpoint.session.metricName}.",
    )
    
    # Update What's Been Tried section
    doc = _upsertSection(doc, "## What's Been Tried", _buildTriedSection(checkpoint))
    
    # Update Plugin Checkpoint section
    doc = _upsertSection(doc, "## Plugin Checkpoint", _buildCheckpointSection(checkpoint))
    
    with open(session_doc_path, "w", encoding="utf-8") as f:
        f.write(doc.rstrip() + "\n")


def _ensureTitle(doc: str, sessionName: str | None) -> str:
    """Ensure the document has a proper title."""
    trimmed = doc.strip()
    if not trimmed:
        return f"# Autoresearch: {sessionName or 'Session'}\n"
    
    # If document starts with a heading, keep it
    if re.match(r"^#\s+", trimmed):
        return trimmed
    
    # Otherwise prepend title
    return f"# Autoresearch: {sessionName or 'Session'}\n\n{trimmed}"


def _upsertSection(doc: str, heading: str, body: str) -> str:
    """
    Insert or update a markdown section in the document.
    
    Args:
        doc: Current document content
        heading: Section heading (e.g., "## Metrics")
        body: New section body content
    
    Returns:
        Updated document
    """
    escaped_heading = re.escape(heading)
    # Match section from heading to next heading or end of document
    section_re = re.compile(rf"(^{escaped_heading}\n)([\s\S]*?)(?=^##\s|\Z)", re.Multiline)
    rendered = f"{heading}\n{body.strip()}\n\n"
    
    if section_re.search(doc):
        return section_re.sub(rendered, doc)
    
    # Section doesn't exist, append it
    return f"{doc.rstrip()}\n\n{rendered}"


def _buildTriedSection(checkpoint: "AutoresearchCheckpoint") -> str:
    """Build the 'What's Been Tried' section content."""
    if not checkpoint.recentLoggedRuns:
        return "- No logged experiments yet."
    
    lines = []
    for run in checkpoint.recentLoggedRuns:
        metric_unit = checkpoint.session.metricUnit
        rendered_metric = f"{run.metric}{metric_unit}" if metric_unit else str(run.metric)
        baseline_label = " baseline" if run.baseline else ""
        lines.append(f"- #{run.run}{baseline_label} {run.status} {rendered_metric} {run.commit} — {run.description}")
    
    return "\n".join(lines)


def _buildCheckpointSection(checkpoint: "AutoresearchCheckpoint") -> str:
    """Build the 'Plugin Checkpoint' section content."""
    from datetime import datetime
    
    lines = [
        f"- Last updated: {datetime.fromtimestamp(checkpoint.updatedAt / 1000).isoformat()}",
        f"- Runs tracked: {checkpoint.session.currentRunCount} current / {checkpoint.session.totalRunCount} total",
        f"- Baseline: {_formatMetric(checkpoint.session.currentBaselineMetric, checkpoint.session.metricUnit)}",
        f"- Best kept: {_formatMetric(checkpoint.session.currentBestMetric, checkpoint.session.metricUnit)}",
        f"- {formatConfidenceLine(checkpoint.session.confidence)}",
    ]
    
    if checkpoint.canonicalBranch:
        lines.append(f"- Canonical branch: {checkpoint.canonicalBranch}")
    
    if checkpoint.carryForwardContext:
        cf = checkpoint.carryForwardContext
        lines.append(
            f"- Carry-forward best: {cf.metricName} {_formatMetric(cf.run.metric, cf.metricUnit)} "
            f"from #{cf.run.run} {cf.run.commit} — {cf.run.description}"
        )
    
    if checkpoint.lastLoggedRun:
        llr = checkpoint.lastLoggedRun
        lines.append(
            f"- Last logged run: #{llr.run} {llr.status} {llr.commit} — {llr.description}"
        )
    
    if checkpoint.pendingRun:
        pr = checkpoint.pendingRun
        lines.append(
            f"- Pending run awaiting log_experiment: {pr.command} "
            f"({_formatMetric(pr.primaryMetric, checkpoint.session.metricUnit)})"
        )
    
    return "\n".join(lines)


def _formatMetric(value: float | None, unit: str) -> str:
    """Format a metric value with its unit."""
    if value is None:
        return "n/a"
    return f"{value}{unit}"
