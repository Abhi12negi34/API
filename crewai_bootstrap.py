from __future__ import annotations

import os
from pathlib import Path


def bootstrap_crewai_runtime() -> Path:
    """
    Make CrewAI use workspace-local settings and stable UTF-8 defaults.

    CrewAI reads its storage location during import, so this must run before
    any `crewai` module is imported.
    """
    storage_root = Path.cwd() / ".crewai_storage"
    storage_root.mkdir(parents=True, exist_ok=True)

    project_name = Path.cwd().name or "ai-api-testing-agent"
    os.environ.setdefault("CREWAI_STORAGE_DIR", project_name)
    os.environ.setdefault("OPENAI_API_KEY", "mock_key")
    os.environ.setdefault("PYTHONUTF8", "1")
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")

    return storage_root
