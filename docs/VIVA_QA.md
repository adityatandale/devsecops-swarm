# Likely viva questions

- **How is this different from RAG?** RAG answers from retrieved text. Here, retrieval is only a hint; the system acts:
  localises, generates, executes tests, observes failures, retries, and submits PRs - a closed agentic loop.
- **Why Tree-sitter instead of asking the LLM where the bug is?** Deterministic, fast, language-agnostic, and keeps the
  prompt tiny so 7B models work.
- **What if the fix passes tests but is wrong?** Tests bound correctness; hence mandatory human PR review, bandit scan, and
  recommendations to strengthen tests. Reported as a limitation.
- **Is running generated code safe?** Ephemeral container, no network, CPU/mem/PID limits, all capabilities dropped,
  copy of the repo (live code untouched).
- **Prompt injection from logs?** Logs are untrusted input; the LLM can only output one function, validated by AST and
  executed only inside the sandbox; cannot reach git or network.
- **Why local models?** Privacy of source code, cost, offline use.
- **How do you measure success?** Fix rate, attempts-to-fix, latency, ablation with/without memory.
