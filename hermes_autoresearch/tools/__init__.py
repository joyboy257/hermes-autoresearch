"""
Autoresearch tools package.

Exports all 4 MCP tools as a TOOLS dict for Hermes integration.
"""

from hermes_autoresearch.tools.init_experiment import init_experiment
from hermes_autoresearch.tools.run_experiment import run_experiment
from hermes_autoresearch.tools.log_experiment import log_experiment
from hermes_autoresearch.tools.autoresearch_status import autoresearch_status
from hermes_autoresearch.tools.schemas import (
    INIT_EXPERIMENT_SCHEMA,
    RUN_EXPERIMENT_SCHEMA,
    LOG_EXPERIMENT_SCHEMA,
    STATUS_SCHEMA,
)


TOOLS = {
    "init_experiment": {
        "function": init_experiment,
        "schema": INIT_EXPERIMENT_SCHEMA,
    },
    "run_experiment": {
        "function": run_experiment,
        "schema": RUN_EXPERIMENT_SCHEMA,
    },
    "log_experiment": {
        "function": log_experiment,
        "schema": LOG_EXPERIMENT_SCHEMA,
    },
    "autoresearch_status": {
        "function": autoresearch_status,
        "schema": STATUS_SCHEMA,
    },
}


__all__ = [
    "TOOLS",
    "init_experiment",
    "run_experiment",
    "log_experiment",
    "autoresearch_status",
    "INIT_EXPERIMENT_SCHEMA",
    "RUN_EXPERIMENT_SCHEMA",
    "LOG_EXPERIMENT_SCHEMA",
    "STATUS_SCHEMA",
]
