"""Thin client for any OpenAI-compatible server (Ollama, vLLM)."""
from .config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL, LLM_TIMEOUT


def chat(system: str, user: str, temperature: float = 0.1, max_tokens: int = 1500) -> str:
    from openai import OpenAI  # imported lazily so the rest of the package works without it

    client = OpenAI(base_url=LLM_BASE_URL, api_key=LLM_API_KEY, timeout=LLM_TIMEOUT)
    resp = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return resp.choices[0].message.content or ""
