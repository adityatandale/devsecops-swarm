# Final Year Project Report - Outline (fill with your results)

**Title:** Self-Healing Autonomous Multi-Agent DevSecOps Engineer

1. **Abstract** (150-200 words): problem (MTTR of production bugs), approach (multi-agent graph with sandboxed
   verification), result (fix rate X/4 on benchmark, mean attempts Y), conclusion.
2. **Introduction:** motivation, problem statement, objectives, scope, contributions.
3. **Literature survey** (verify each citation before use): ReAct (Yao et al., 2022); Reflexion (Shinn et al., 2023);
   Self-Debugging (Chen et al., 2023); SWE-bench (Jimenez et al., 2023); SWE-agent (Yang et al., 2024);
   Agentless (Xia et al., 2024); Automated Program Repair (GenProg, Le Goues et al.); LangGraph docs; Tree-sitter.
4. **System analysis:** functional / non-functional requirements, use-case diagram, risk analysis (unsafe code execution).
5. **System design:** architecture diagram (docs/ARCHITECTURE.md), state schema, agent prompts, sequence diagram, data flow.
6. **Implementation:** module-by-module (`swarm/`), technologies, key algorithms (signature normalisation, AST
   isolation, byte-exact patch splice, retry loop).
7. **Security design:** sandbox hardening, token handling, human-in-the-loop, threat model (prompt injection via logs!).
8. **Testing & evaluation:** unit tests; benchmark table; ablation (with/without Qdrant); model comparison
   (DeepSeek-Coder-7B vs Llama-3-8B); latency; failure analysis.
9. **Results & discussion:** screenshots of dashboard, sample PR, limitations.
10. **Conclusion & future work.** 11. **References.** 12. **Appendix:** setup guide, code listings, sample logs.

## Suggested demo script (5 minutes)
1. Show running service log -> `python -m swarm.simulate` injects a crash.
2. `streamlit run dashboard.py` -> click *Run swarm now*; narrate each agent in the timeline.
3. Show the diff, sandbox output, and generated PR text in `runs/`.
4. Re-inject the same bug: show Qdrant retrieving the stored fix (score in Sentry event).
5. Show benchmark table and the failed-attempt → retry example.
