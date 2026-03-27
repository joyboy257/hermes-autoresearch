"""
Ideas backlog management for discarded experiment follow-ups.

When an experiment is discarded, the idea from log_experiment is appended
to autoresearch.ideas.md for future exploration.
"""

import os
from hermes_autoresearch.files import getAutoresearchRootFilePath


def appendIdeaBacklogEntry(cwd: str, idea: str) -> None:
    """
    Append an idea to the ideas backlog file.
    
    Args:
        cwd: Working directory (repo root)
        idea: The idea/lesson learned to append
    """
    normalized = idea.strip()
    if not normalized:
        return
    
    ideas_path = getAutoresearchRootFilePath(cwd, "ideasBacklog")
    
    # Check if file exists and has content
    prefix = ""
    if os.path.exists(ideas_path):
        existing = open(ideas_path, "r", encoding="utf-8").read().strip()
        if existing:
            prefix = "\n"
    
    with open(ideas_path, "a", encoding="utf-8") as f:
        f.write(f"{prefix}- {normalized}\n")
