import os
from pathlib import Path

import yaml

from crewai_bootstrap import bootstrap_crewai_runtime

bootstrap_crewai_runtime()

from crewai import LLM


def _cfg(key: str, default: str) -> str:
    value = os.environ.get(key)
    if value is None:
        return default
    value = value.strip()
    return value or default


def _load_project_config() -> dict:
    config_path = Path(__file__).resolve().parent / "config" / "config.yaml"
    try:
        with open(config_path, "r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}
            return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _yaml_section(config: dict, key: str) -> dict:
    section = config.get(key, {})
    return section if isinstance(section, dict) else {}


PROJECT_CONFIG = _load_project_config()
OLLAMA_CONFIG = _yaml_section(PROJECT_CONFIG, "ollama")

OLLAMA_BASE_URL = _cfg("OLLAMA_BASE_URL", str(OLLAMA_CONFIG.get("host", "http://127.0.0.1:11434")))
OLLAMA_MODEL = _cfg("OLLAMA_MODEL", str(OLLAMA_CONFIG.get("model", "gemma3:27b")))

# CrewAI's Ollama provider reads OLLAMA_HOST, so keep it aligned with the
# workspace configuration unless the caller already supplied a value.
os.environ.setdefault("OLLAMA_HOST", OLLAMA_BASE_URL)


def get_llm(model: str | None = None, base_url: str | None = None, **kwargs) -> LLM:
    selected_model = model or OLLAMA_MODEL
    selected_base_url = base_url or OLLAMA_BASE_URL

    # Ensure model has the ollama/ prefix that LiteLLM requires
    if not selected_model.startswith("ollama/"):
        selected_model = f"ollama/{selected_model}"

    # Make sure any downstream OpenAI-compatible client sees the same host.
    os.environ["OLLAMA_HOST"] = selected_base_url

    llm = LLM(
        model=selected_model,
        base_url=selected_base_url,
        api_key=_cfg("OLLAMA_API_KEY", "ollama"),
        **kwargs,
    )

    # Gemma 3 on Ollama can answer well, but CrewAI's native tool-calling path
    # trips on this model. Force the text-based ReAct path so the agents still
    # use the local Ollama model without tool-call failures.
    try:
        object.__setattr__(llm, "supports_function_calling", lambda: False)
    except Exception:
        pass

    return llm


default_llm = get_llm()
