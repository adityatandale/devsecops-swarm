# 🛡️ Self-Healing Autonomous Multi-Agent DevSecOps Engineer

A stateful, event-driven swarm of AI agents that **watches microservice logs, localises the faulty function with
Tree-sitter ASTs, generates a fix with a local open-weight coding model, validates it in an ephemeral Docker
sandbox (tests + security scan), retries on failure, and opens a pull request** - no cloud LLM, no human in the loop
until review.

```
 logs ──► Sentry ──► Architect ──► Patch Engine ──► Sandbox ──┬─ pass ─► GitOps (PR) ─► Qdrant (learn)
          (Qdrant)   (Tree-sitter)  (Ollama/vLLM)    (Docker)   ├─ fail & attempts<3 ─► back to Patch Engine
                                                                └─ fail & attempts=3 ─► Escalate to human
```

## Features
| Agent | Responsibility | Tech |
|---|---|---|
| **Sentry** | Parses JSON logs, detects crashes (traceback) and latency anomalies, builds a normalised error *signature*, retrieves similar past fixes | Qdrant, sentence-transformers |
| **Architect** | Maps the stack trace to repo code, isolates the exact function deterministically (no LLM guessing) | Tree-sitter (stdlib `ast` fallback) |
| **Patch Engine** | Prompts a local coder LLM with trace + function + past fixes + previous failure output; validates syntax/name before applying | Ollama or vLLM (OpenAI API) |
| **Sandbox Executor** | Runs `pytest` and `bandit` in a network-less, memory/CPU/PID-limited, capability-dropped container | Docker SDK |
| **GitOps** | Branch, commit, push, open authenticated PR with root-cause + diff + validation report | GitPython, GitHub REST |
| **Orchestrator** | Conditional graph with self-correcting retry loop and escalation | LangGraph |
| **Dashboard** | Timeline, diffs, sandbox logs, metrics | Streamlit |

Safety by design: the live repo is never touched during the loop (ephemeral copy), sandbox has `network_mode=none`,
patches are AST-validated, PRs require human review, secrets never appear in error messages.

## Quick start
```bash
python -m venv .venv && source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env && export $(grep -v '^#' .env | xargs)   # or set variables manually

# 1. Local LLM (pick one)
docker compose up -d ollama qdrant
docker exec -it $(docker compose ps -q ollama) ollama pull deepseek-coder:6.7b
#   vLLM alternative: python -m vllm.entrypoints.openai.api_server --model deepseek-ai/deepseek-coder-6.7b-instruct
#   then LLM_BASE_URL=http://localhost:8000/v1 LLM_MODEL=deepseek-ai/deepseek-coder-6.7b-instruct

# 2. Sandbox image
docker build -t devsecops-sandbox:latest sandbox/

# 3. Seed the vector memory, inject a bug, let the swarm heal it
python main.py seed
python -m swarm.simulate                 # writes a ZeroDivisionError crash to demo_service/logs/app.log
python main.py run                       # dry-run PR (patch + PR text saved in runs/)
streamlit run dashboard.py               # visual demo for your viva
```
No GPU / no Docker? `python main.py run --sandbox local` works for development (no isolation - demo code only).
Use `QDRANT_URL=http://localhost:6333` for the server; default is embedded storage in `.qdrant/`.

### Real pull requests
Point `--repo` at a git clone of your service and set `DRY_RUN_PR=false GITHUB_TOKEN=... GITHUB_REPO=owner/repo`,
then `python main.py run --repo /path/to/clone --log /path/to/app.log --real-pr`.
Use a fine-grained token with only *Contents: write* and *Pull requests: write* on that repo.

## Evaluation (for your report)
```bash
python benchmarks/evaluate.py --sandbox docker --ablate
```
Runs 4 injected bug classes (KeyError, IndexError off-by-one, TypeError on None, ZeroDivision) and reports
fix rate, attempts and latency **with vs. without Qdrant memory** (ablation). Add your own cases: copy a folder in
`benchmarks/cases/`, add `app.py`, `tests/`, and `case.json` (`module` + `call` that triggers the bug).
Results land in `benchmarks/results.json`. Try both models (DeepSeek-Coder-7B vs Llama-3-8B) and compare.

## Tests
`pytest` runs unit tests (log parsing, AST isolation, patch safety) and a mocked end-to-end pipeline test.

## Limitations & future work (mention in viva)
Python-only localisation (Tree-sitter grammars exist for other languages); single-function patches; correctness
bounded by the quality of the repo's test suite; local mode lacks isolation; add multi-file patches, a Reviewer
agent, and Prometheus/OpenTelemetry ingestion for performance incidents.
