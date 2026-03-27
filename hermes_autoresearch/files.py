"""
File path utilities for autoresearch canonical files.
"""

from pathlib import Path
from typing import Final

from hermes_autoresearch.config import AUTORESEARCH_ROOT_FILES

# Re-export for convenience
def getAutoresearchRootFilePath(
    cwd: str,
    file: str,
) -> str:
    """
    Get the absolute path to an autoresearch canonical file.
    
    Args:
        cwd: Working directory (repo root)
        file: Key name from AUTORESEARCH_ROOT_FILES (e.g., "resultsLog", "sessionDoc")
    
    Returns:
        Absolute path to the file
    """
    return str(Path(cwd) / AUTORESEARCH_ROOT_FILES[file])


def readAutoresearchRootFile(
    cwd: str,
    file: str,
) -> str | None:
    """
    Read the contents of an autoresearch canonical file.
    
    Args:
        cwd: Working directory (repo root)
        file: Key name from AUTORESEARCH_ROOT_FILES
    
    Returns:
        File contents as string, or None if file doesn't exist
    """
    file_path = getAutoresearchRootFilePath(cwd, file)
    if not Path(file_path).exists():
        return None
    return Path(file_path).read_text(encoding="utf-8")


def describeCanonicalFiles() -> dict[str, str]:
    """Return a copy of the AUTORESEARCH_ROOT_FILES mapping."""
    return dict(AUTORESEARCH_ROOT_FILES)
