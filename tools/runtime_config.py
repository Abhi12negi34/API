import os


def _env_flag(name, default="false"):
    value = os.environ.get(name, default)
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


CREWAI_VERBOSE = _env_flag("CREWAI_VERBOSE", "true")
