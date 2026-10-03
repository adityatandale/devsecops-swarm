"""Central configuration (environment-variable driven)."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _flag(name: str, default: str) -> bool:
    return os.getenv(name, default).strip().lower() in ("1", "true", "yes", "on")


RUNS_DIR = Path(os.getenv("RUNS_DIR", ROOT / "runs"))

# LLM (any OpenAI-compatible server: Ollama or vLLM)
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://localhost:11434/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "deepseek-coder:6.7b")
LLM_API_KEY = os.getenv("LLM_API_KEY", "ollama")
LLM_TIMEOUT = float(os.getenv("LLM_TIMEOUT", "180"))

# Vector DB
QDRANT_URL = os.getenv("QDRANT_URL", "")
QDRANT_PATH = Path(os.getenv("QDRANT_PATH", ROOT / ".qdrant"))

# Sentry
LATENCY_THRESHOLD_MS = float(os.getenv("LATENCY_THRESHOLD_MS", "1000"))

# Patch loop + sandbox
MAX_ATTEMPTS = int(os.getenv("MAX_ATTEMPTS", "3"))
SANDBOX_MODE = os.getenv("SANDBOX_MODE", "docker")  # docker | local
SANDBOX_IMAGE = os.getenv("SANDBOX_IMAGE", "devsecops-sandbox:latest")
SANDBOX_TIMEOUT = int(os.getenv("SANDBOX_TIMEOUT", "120"))

# Pull request
DRY_RUN_PR = _flag("DRY_RUN_PR", "true")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
GITHUB_REPO = os.getenv("GITHUB_REPO", "")
BASE_BRANCH = os.getenv("BASE_BRANCH", "main")
