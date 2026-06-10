---
paths:
  - "app/services/llm_service.py"
  - "app/services/subscription_config.py"
  - "app/routers/**"
---

# LLM provider rules

These rules apply to `app/services/llm_service.py`, related config, and any router that calls the LLM service.

## Provider priority chain — immutable

```
OpenRouter  >  ApiFreeLLM  >  GLM  >  Vultr
```

- Adding a new provider means inserting it at a specific position. The order is product-driven, not technical.
- Reordering is a breaking change. Don't.

## Selection

- Selection is at module load. There is no per-request fallback.
- If the active provider fails, the request fails (the helper returns a structured error). This is intentional — adds latency if a provider dies mid-flight is worse than asking the user to retry.

## Error shape — contract

`_get_error_response()` keys are a public contract:

```python
{
    "error": str,
    "insight": str,
    "recommendations": list[str],
    "score": int,
    "reasoning": str,
    "overview": str,
    "strategic_next_steps": list[str],
    "key_strengths": list[str],
    "key_challenges": list[str],
    # plus on transport errors:
    "status_code": int | None,
    "details": ...,
}
```

- Never remove or rename existing keys.
- New keys must default to `None` or `[]`.
- `token_usage` is added on success; failure returns `0` from the helper.

## Request shape

- `stream: False` always. The JSON extractor doesn't handle SSE.
- `temperature`: `0.5` for `generate_section_analysis`, `0.7` for `generate_strategic_overview`.
- `max_tokens`: default 2048 for GLM, caller-decides for the others.

## Response extraction

- Robust JSON extraction: first `{` to last `}` substring. Don't try `response_format: json_object` — not all providers support it.
- If extraction fails, raise `ValueError` with the raw response included in the error message.

## Auth

- All API keys come from env via `app/core/config.py` `Settings`. Never hardcode.
- Never log a key. Never return a key in a response.
- Never include a key in an exception message.

## Don't

- Don't introduce a third-party LLM framework (LangChain, LlamaIndex). Use raw `httpx`.
- Don't add a cache layer here without a project-level decision.
- Don't change the prompt templates without product consultation.
- Don't switch to streaming.
- Don't add per-request fallback.
- Don't change the temperature defaults without measuring output quality.
