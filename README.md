# hermes-autoresearch

Autonomous experiment loop for Hermes — edit code, run benchmark, log result, keep/discard, repeat.

A port of [openclaw-autoresearch](https://github.com/joyboy257/openclaw-autoresearch) that runs natively as a Hermes skill with checkpointing, confidence scoring, and ideas backlog management.

## Overview

`hermes-autoresearch` implements a systematic experimentation loop:

1. **Initialize** a session with a metric to optimize
2. **Edit code** to improve the metric
3. **Run experiment** to benchmark changes
4. **Log result** as keep or discard
5. **Repeat** — confidence grows as evidence accumulates

The system maintains:
- **Checkpoint state** for session recovery
- **JSONL results log** for full history
- **Session document** summarizing current state
- **Ideas backlog** for discarded directions
- **Confidence scoring** (MAD-based) to distinguish real improvements from noise

## Installation

```bash
pip install hermes-autoresearch
```

Or install from source:

```bash
cd hermes-autoresearch
pip install -e .
```

## Quick Start

### 1. Create an experiment runner script

`autoresearch.sh`:
```bash
#!/bin/bash
# Your benchmark here
./run_benchmark --quiet
# Emit METRIC lines:
echo "METRIC latency_ms=$(./get_latency)"
echo "METRIC throughput=$(./get_throughput)"
```

### 2. Initialize a session

```python
from hermes_autoresearch import init_experiment

result = init_experiment(
    cwd="/path/to/project",
    name="latency-optimization",
    metricName="latency_ms",
    metricUnit="ms",
    bestDirection="lower",
)
```

### 3. Run experiments

```python
from hermes_autoresearch import run_experiment

result = run_experiment(
    cwd="/path/to/project",
    description="Reduced buffer size",
)
# Results stored as "pending" awaiting log_experiment
```

### 4. Log decisions

```python
from hermes_autoresearch import log_experiment

# Keep a good result
log_experiment(
    cwd="/path/to/project",
    decision="keep",
    idea="Reduced buffer size improved latency",
)

# Or discard and learn
log_experiment(
    cwd="/path/to/project",
    decision="discard",
    idea="Larger buffer increased memory pressure without throughput gain",
)
```

### 5. Check status

```python
from hermes_autoresearch import autoresearch_status

status = autoresearch_status(cwd="/path/to/project")
print(status)
```

## CLI Usage

```bash
# Initialize
/autoresearch setup my-experiment latency_ms lower

# Check status
/autoresearch status

# View pending
/autoresearch pending

# Stop session
/autoresearch stop
```

## Architecture

```
hermes_autoresearch/
├── checkpoint.py        # Checkpoint read/write
├── commands.py          # /autoresearch text commands
├── config.py           # Constants and file names
├── confidence.py       # MAD-based confidence scoring
├── execute.py          # Command execution with timeout
├── files.py            # Path utilities
├── git.py              # Git operations
├── hooks.py            # System prompt injection
├── ideas.py            # Ideas backlog management
├── logging_.py         # JSONL append utilities
├── metrics.py          # METRIC line parsing
├── session_doc.py      # Session document sync
├── session_lock.py     # Session lock management
├── state.py            # State reconstruction
├── tools/              # MCP tool implementations
│   ├── init_experiment.py
│   ├── run_experiment.py
│   ├── log_experiment.py
│   ├── autoresearch_status.py
│   └── schemas.py      # Tool parameter schemas
└── runtime_state.py    # In-memory runtime state
```

## File Formats

| File | Purpose |
|------|---------|
| `autoresearch.jsonl` | JSON Lines log of all runs |
| `autoresearch.checkpoint.json` | Session state snapshot |
| `autoresearch.md` | Human-readable session summary |
| `autoresearch.ideas.md` | Backlog of discarded ideas |
| `autoresearch.lock` | Session lock (PID + timestamp) |
| `autoresearch.sh` | Experiment runner script |

## Confidence Scoring

Confidence = |best - baseline| / MAD

- **≥ 2.0x**: Likely real improvement
- **≥ 1.0x**: Marginal, above noise
- **< 1.0x**: Within noise, re-run recommended

## License

MIT License

Original author: Gianfranco Piana

---

For detailed documentation, see [SKILL.md](./SKILL.md).
