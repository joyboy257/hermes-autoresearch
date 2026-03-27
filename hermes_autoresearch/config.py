"""
Constants and configuration for hermes-autoresearch.
"""

from typing import Final

# Canonical file names for autoresearch session
AUTORESEARCH_ROOT_FILES: Final = {
    "sessionDoc": "autoresearch.md",
    "runnerScript": "autoresearch.sh",
    "resultsLog": "autoresearch.jsonl",
    "ideasBacklog": "autoresearch.ideas.md",
    "checkpoint": "autoresearch.checkpoint.json",
    "sessionLock": "autoresearch.lock",
}

# Type alias for file key names
AutoresearchRootFileKey = str

# Default timeout for experiment commands in seconds
DEFAULT_TIMEOUT_SECONDS: Final = 600

# Number of tail lines to capture from experiment output
OUTPUT_TAIL_LINES: Final = 80

# Max queued steers in runtime state
MAX_QUEUED_STEERS: Final = 20

# Git command timeout in milliseconds
GIT_TIMEOUT_MS: Final = 30_000
