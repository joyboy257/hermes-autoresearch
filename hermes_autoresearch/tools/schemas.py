"""
Tool schemas for autoresearch MCP tools.

Defines dict schemas for init/run/log/status tool parameters.
"""

INIT_EXPERIMENT_SCHEMA = {
    "name": "init_experiment",
    "description": "Initialize a new autoresearch session or resume an existing one. Acquires session lock, writes config header to results log, creates checkpoint, and syncs session document.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "cwd": {
                "type": "string",
                "description": "Working directory (repo root) for the experiment",
            },
            "name": {
                "type": "string",
                "description": "Human-readable name for this experiment series",
            },
            "metricName": {
                "type": "string",
                "description": "Name of the primary metric being optimized (e.g., 'latency_ms', 'error_rate')",
            },
            "metricUnit": {
                "type": "string",
                "description": "Unit of the metric (e.g., 'ms', 'µs', '%', 'errors/s')",
                "default": "",
            },
            "bestDirection": {
                "type": "string",
                "enum": ["lower", "higher"],
                "description": "Which direction represents improvement ('lower' for latency/error_rate, 'higher' for throughput/accuracy)",
            },
            "runnerScript": {
                "type": "string",
                "description": "Path to the shell script that runs a single experiment and emits METRIC lines",
                "default": "autoresearch.sh",
            },
        },
        "required": ["cwd", "name", "metricName", "bestDirection"],
    },
}

RUN_EXPERIMENT_SCHEMA = {
    "name": "run_experiment",
    "description": "Execute the experiment runner script, parse METRIC output lines, and store results as a pending run awaiting log_experiment.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "cwd": {
                "type": "string",
                "description": "Working directory (repo root) where the experiment should run",
            },
            "command": {
                "type": "string",
                "description": "Command to execute (defaults to the runnerScript from init_experiment)",
            },
            "description": {
                "type": "string",
                "description": "Brief description of what this experiment run is testing",
                "default": "",
            },
            "timeoutSeconds": {
                "type": "integer",
                "description": "Maximum seconds to wait for the experiment to complete",
                "default": 600,
            },
        },
        "required": ["cwd"],
    },
}

LOG_EXPERIMENT_SCHEMA = {
    "name": "log_experiment",
    "description": "Log a pending experiment run as 'keep' or 'discard'. For kept runs: commits to git, updates checkpoint and session doc. For discarded runs: appends idea to backlog.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "cwd": {
                "type": "string",
                "description": "Working directory (repo root) of the experiment",
            },
            "decision": {
                "type": "string",
                "enum": ["keep", "discard"],
                "description": "Whether to keep this experiment's results or discard and log a lesson instead",
            },
            "idea": {
                "type": "string",
                "description": "For discard: what was learned or why this direction was unhelpful. For keep: optional description of what worked",
                "default": "",
            },
        },
        "required": ["cwd", "decision"],
    },
}

STATUS_SCHEMA = {
    "name": "autoresearch_status",
    "description": "Report the current status of the autoresearch session including session info, recent runs, pending run, lock status, and confidence.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "cwd": {
                "type": "string",
                "description": "Working directory (repo root) to check status for",
            },
            "includeIdeas": {
                "type": "boolean",
                "description": "Include the ideas backlog preview in the status",
                "default": True,
            },
        },
        "required": ["cwd"],
    },
}
