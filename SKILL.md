# Hermes Autoresearch Skill

## Name

`hermes-autoresearch` — Autonomous Experiment Loop for Hermes

## Description

A port of openclaw-autoresearch that runs natively as a Hermes skill. Implements an autonomous experiment loop: edit code → run benchmark → log result → keep/discard → repeat.

This skill enables systematic experimentation by maintaining checkpoint state, parsing metric outputs, computing confidence scores, and managing the experiment backlog.

## Tools

### `init_experiment`

Initialize a new autoresearch session or resume an existing one.

**Parameters:**
- `cwd` (string, required): Working directory (repo root)
- `name` (string, required): Human-readable name for the experiment series
- `metricName` (string, required): Primary metric being optimized (e.g., `latency_ms`)
- `metricUnit` (string, optional, default: ""): Unit of the metric
- `bestDirection` (string, required): `"lower"` or `"higher"` — which direction is improvement
- `runnerScript` (string, optional, default: `"autoresearch.sh"`): Path to experiment runner script

**Behavior:**
1. Acquires session lock (prevents parallel sessions)
2. Writes config header to `autoresearch.jsonl`
3. Creates checkpoint at `autoresearch.checkpoint.json`
4. Syncs session document at `autoresearch.md`

---

### `run_experiment`

Execute the experiment runner and capture metrics.

**Parameters:**
- `cwd` (string, required): Working directory
- `command` (string, optional): Command to run (defaults to runnerScript)
- `description` (string, optional): Brief description of this run
- `timeoutSeconds` (integer, optional, default: 600): Max execution time

**Behavior:**
1. Checks session lock
2. Executes experiment command
3. Parses `METRIC name=value` lines from stdout/stderr
4. Stores results as a pending run awaiting `log_experiment`

**Output Format:**
```
METRIC latency_ms=4200
METRIC throughput=100
```

---

### `log_experiment`

Log a pending run as `keep` or `discard`.

**Parameters:**
- `cwd` (string, required): Working directory
- `decision` (string, required): `"keep"` or `"discard"`
- `idea` (string, optional): For discard: lesson learned. For keep: optional description

**Behavior for `keep`:**
1. Appends result to `autoresearch.jsonl`
2. Commits to git with result data
3. Updates checkpoint with new best if improved
4. Syncs session document

**Behavior for `discard`:**
1. Appends result to `autoresearch.jsonl` with status "discard"
2. Appends idea to `autoresearch.ideas.md` backlog
3. Updates checkpoint

---

### `autoresearch_status`

Report current session status.

**Parameters:**
- `cwd` (string, required): Working directory
- `includeIdeas` (boolean, optional, default: true): Include ideas preview

**Returns:**
- Session info (name, metric, segment, runs)
- Recent runs
- Pending run (if any)
- Lock status
- Confidence score
- Best run with carry-forward context
- Ideas backlog preview

## Workflow

```
┌─────────────────────────────────────────────────────────────────────┐
│  1. init_experiment                                                 │
│     - Creates/updates autoresearch.jsonl, .checkpoint.json, .md    │
│     - Acquires session lock                                         │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│  2. [User edits code]                                               │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│  3. run_experiment                                                  │
│     - Executes autorestart.sh                                       │
│     - Parses METRIC lines from output                               │
│     - Stores as pending run                                         │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│  4. log_experiment keep|discard                                     │
│     - keep: git commit, update checkpoint/best                      │
│     - discard: log idea to backlog                                  │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                         [Repeat 2-4]
```

## File Formats

### `autoresearch.jsonl`

JSON Lines log of all experiment results.

**Config header:**
```json
{"type": "config", "name": "my-experiment", "metricName": "latency_ms", "metricUnit": "ms", "bestDirection": "lower"}
```

**Result entry:**
```json
{"run": 1, "commit": "abc1234", "metric": 4200, "metrics": {"latency_ms": 4200, "throughput": 100}, "status": "keep", "baseline": true, "description": "Initial baseline", "timestamp": 1710000000000, "segment": 0, "confidence": null}
```

### `autoresearch.checkpoint.json`

Complete session state snapshot.

```json
{
  "version": 1,
  "updatedAt": 1710000000000,
  "sessionStartCommit": "abc1234",
  "canonicalBranch": "main",
  "carryForwardContext": {
    "metricName": "latency_ms",
    "metricUnit": "ms",
    "bestDirection": "lower",
    "run": { "run": 5, "commit": "def5678", "metric": 3800, ... }
  },
  "session": { "name": "...", "metricName": "...", ... },
  "lastLoggedRun": { ... },
  "recentLoggedRuns": [ ... ],
  "pendingRun": null
}
```

### `autoresearch.md`

Session document (auto-generated):

```markdown
# Autoresearch: latency-optimization

## Metrics
- **Primary**: latency_ms (ms, lower is better)

## How to Run
`autoresearch.sh` — should emit `METRIC name=number` lines.

## What's Been Tried
- #1 baseline 4200ms abc1234 — Initial baseline
- #5 keep 3800ms def5678 — Reduced buffer size

## Plugin Checkpoint
- Last updated: 2024-03-09T12:00:00
- Runs tracked: 5 current / 12 total
- Baseline: 4200ms
- Best kept: 3800ms
- Confidence: 2.1x noise floor - improvement is likely real
```

### `autoresearch.ideas.md`

Backlog of discarded experiment lessons:

```markdown
- Larger buffer sizes increase latency (tried 64KB, 128KB)
- GC tuning had minimal impact at this scale
```

## System Prompt Injection

The `hooks.get_system_prompt_addition(cwd)` function injects context into the system prompt when active:

```
---
# Autoresearch Context

**Experiment**: latency-optimization
**Metric**: latency_ms
**Unit**: ms
**Goal**: lower is better

- Segment: 2
- Runs this segment: 5
- Total runs: 12
- Baseline: 4200ms
- Best kept: 3800ms
- Confidence: 2.1x noise floor - improvement is likely real

**Recent runs**:
- #10 keep 3850ms — Tweaked batch size
- #9 discard 4500ms — Increased retry logic
- #8 keep 3900ms — Cache warming

**Ideas backlog** (for later exploration):
- Consider connection pooling
- Async I/O might help
---
```

## Confidence Scoring

Confidence = |best_kept - baseline| / MAD (median absolute deviation)

- **≥ 2.0x**: Likely real improvement
- **≥ 1.0x**: Marginal, above noise but uncertain
- **< 1.0x**: Within noise floor, re-run recommended

## Session Lock

Prevents parallel sessions in the same directory using `autoresearch.lock`:

```json
{"pid": 12345, "timestamp": 1710000000000}
```

A stale lock (from dead process) is automatically replaced.
