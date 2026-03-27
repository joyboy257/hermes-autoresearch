"""
hermes-autoresearch - Autonomous experiment loop for Hermes skills.

A port of openclaw-autoresearch that runs natively as a Hermes skill.
Implements: edit code → run benchmark → log result → keep/discard.
"""

from hermes_autoresearch.config import (
    AUTORESEARCH_ROOT_FILES,
    DEFAULT_TIMEOUT_SECONDS,
    OUTPUT_TAIL_LINES,
)
from hermes_autoresearch.state import (
    AutoresearchStateSnapshot,
    AutoresearchRunSnapshot,
    AutoresearchIdeasSnapshot,
    createEmptyStateSnapshot,
    reconstructStateFromJsonl,
    readRecentLoggedRuns,
    readBestLoggedRun,
)
from hermes_autoresearch.confidence import (
    computeConfidence,
    formatConfidenceLine,
    describeConfidence,
)
from hermes_autoresearch.files import (
    AUTORESEARCH_ROOT_FILES,
    getAutoresearchRootFilePath,
    readAutoresearchRootFile,
)
from hermes_autoresearch.checkpoint import (
    AutoresearchCheckpoint,
    readAutoresearchCheckpoint,
    writeAutoresearchCheckpoint,
    deleteAutoresearchCheckpoint,
)
from hermes_autoresearch.logging_ import (
    AutoresearchConfigHeader,
    AutoresearchResultEntry,
    createConfigHeader,
    writeConfigHeader,
    appendResultEntry,
)
from hermes_autoresearch.ideas import appendIdeaBacklogEntry
from hermes_autoresearch.session_doc import syncAutoresearchSessionDoc
from hermes_autoresearch.session_lock import (
    AutoresearchSessionLock,
    AutoresearchSessionLockStatus,
    readAutoresearchSessionLock,
    getAutoresearchSessionLockStatus,
    acquireAutoresearchSessionLock,
    removeAutoresearchSessionLock,
)
from hermes_autoresearch.metrics import parseMetricLines
from hermes_autoresearch.runtime_state import (
    AutoresearchRuntimeSnapshot,
    AutoresearchRuntimeMode,
    PendingExperimentRun,
    getAutoresearchRuntimeState,
    setAutoresearchRuntimeMode,
    setAutoresearchRunInFlight,
    queueAutoresearchSteer,
    consumeAutoresearchSteers,
    clearAutoresearchSteers,
    setAutoresearchPendingRun,
    getAutoresearchPendingRun,
    consumeAutoresearchPendingRun,
    setAutoresearchContinuationReminder,
    consumeAutoresearchContinuationReminder,
    clearAutoresearchRuntimeState,
)
from hermes_autoresearch.execute import (
    ExperimentExecutionResult,
    executeExperimentCommand,
)
from hermes_autoresearch.git import (
    GitCommandResult,
    GitKeepResult,
    readShortHeadCommit,
    readCurrentBranch,
    countCommitsSince,
    commitKeptExperiment,
)
from hermes_autoresearch.hooks import get_system_prompt_addition
from hermes_autoresearch.commands import handle_autoresearch_command

__version__ = "1.0.5"
__author__ = "Joy Boy"
__license__ = "MIT"

__all__ = [
    # Config
    "AUTORESEARCH_ROOT_FILES",
    "DEFAULT_TIMEOUT_SECONDS",
    "OUTPUT_TAIL_LINES",
    # State
    "AutoresearchStateSnapshot",
    "AutoresearchRunSnapshot",
    "AutoresearchIdeasSnapshot",
    "createEmptyStateSnapshot",
    "reconstructStateFromJsonl",
    "readRecentLoggedRuns",
    "readBestLoggedRun",
    # Confidence
    "computeConfidence",
    "formatConfidenceLine",
    "describeConfidence",
    # Files
    "getAutoresearchRootFilePath",
    "readAutoresearchRootFile",
    # Checkpoint
    "AutoresearchCheckpoint",
    "readAutoresearchCheckpoint",
    "writeAutoresearchCheckpoint",
    "deleteAutoresearchCheckpoint",
    # Logging
    "AutoresearchConfigHeader",
    "AutoresearchResultEntry",
    "createConfigHeader",
    "writeConfigHeader",
    "appendResultEntry",
    # Ideas
    "appendIdeaBacklogEntry",
    # Session Doc
    "syncAutoresearchSessionDoc",
    # Session Lock
    "AutoresearchSessionLock",
    "AutoresearchSessionLockStatus",
    "readAutoresearchSessionLock",
    "getAutoresearchSessionLockStatus",
    "acquireAutoresearchSessionLock",
    "removeAutoresearchSessionLock",
    # Metrics
    "parseMetricLines",
    # Runtime State
    "AutoresearchRuntimeSnapshot",
    "AutoresearchRuntimeMode",
    "PendingExperimentRun",
    "getAutoresearchRuntimeState",
    "setAutoresearchRuntimeMode",
    "setAutoresearchRunInFlight",
    "queueAutoresearchSteer",
    "consumeAutoresearchSteers",
    "clearAutoresearchSteers",
    "setAutoresearchPendingRun",
    "getAutoresearchPendingRun",
    "consumeAutoresearchPendingRun",
    "setAutoresearchContinuationReminder",
    "consumeAutoresearchContinuationReminder",
    "clearAutoresearchRuntimeState",
    # Execute
    "ExperimentExecutionResult",
    "executeExperimentCommand",
    # Git
    "GitCommandResult",
    "GitKeepResult",
    "readShortHeadCommit",
    "readCurrentBranch",
    "countCommitsSince",
    "commitKeptExperiment",
    # Hooks
    "get_system_prompt_addition",
    # Commands
    "handle_autoresearch_command",
]
