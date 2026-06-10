---
name: llm-provider-fallback
description: Multi-provider LLM routing for app/services/llm_service.py. Use when adding a new LLM provider, fixing provider-specific bugs, or adjusting the priority chain. Priority: OpenRouter > ApiFreeLLM > GLM > Vultr.
---

# LLM provider fallback — `inp-backend`

## Priority chain (immutable order)

```
OpenRouter  >  ApiFreeLLM  >  GLM  >  Vultr
```

A new provider slots in at a specific position. The order is product, not technical: OpenRouter is the production default; ApiFreeLLM is the free-tier backup; GLM and Vultr are the last-resort fallbacks.

## How selection works

```python
# app/services/llm_service.py — selection at module load
USE_OPENROUTER = bool(OPENROUTER_API_KEY)
USE_APIFREELL = not USE_OPENROUTER and bool(APIFREELL_API_KEY)
USE_GLM = not USE_OPENROUTER and not USE_APIFREELL and bool(GLM_API_KEY)
USE_VULTR = not any([USE_OPENROUTER, USE_APIFREELL, USE_GLM])  # implicit, no key check

if USE_OPENROUTER:
    ACTIVE_API_KEY = OPENROUTER_API_KEY
    ACTIVE_API_BASE_URL = OPENROUTER_API_BASE_URL
    ACTIVE_CHAT_MODEL = OPENROUTER_CHAT_MODEL
    PROVIDER_NAME = "OpenRouter"
# ... etc
```

Selection is at module load. There is **no per-request fallback**: if the active provider fails, the request fails (the helper returns a structured error). This is intentional — adds latency if a provider dies mid-flight is worse than asking the user to retry.

## Provider matrix

| Provider     | base URL                                | stream    | response_format json_object | max_tokens default |
|--------------|-----------------------------------------|-----------|-----------------------------|--------------------|
| OpenRouter   | `https://openrouter.ai/api/v1`          | optional  | supported                   | caller decides     |
| ApiFreeLLM   | `https://api.apifreellm.com/v1`         | optional  | unsupported                 | caller decides     |
| GLM          | `https://api.z.ai/api/coding/paas/v4`   | optional  | partial                     | 2048 injected      |
| Vultr        | `https://api.vultrinference.com/v1`     | optional  | unsupported                 | caller decides     |

## Request shape (unified)

```python
request_payload = {
    "model": ACTIVE_CHAT_MODEL,
    "messages": [...],
    "temperature": 0.5,  # or 0.7 for strategic overview
    "stream": False,      # always False; we parse JSON, not SSE
}
if USE_GLM:
    request_payload["max_tokens"] = request_payload.get("max_tokens", 2048)
```

`stream: False` is set on every request regardless of provider.

## Response extraction (unified)

```python
content = api_response.get("choices", [{}])[0].get("message", {}).get("content", "")
# Robust JSON extraction: first '{' to last '}'
start = content.find("{")
end = content.rfind("}")
if start == -1 or end == -1 or end <= start:
    raise ValueError("No JSON object in response")
analysis = json.loads(content[start : end + 1])
```

This works for all four providers. Don't try `response_format: json_object` — not all support it.

## Error shape (contract)

Every error path returns `_get_error_response(...)` with the full key set:

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

`token_usage` is added on success; failure returns `token_usage=0` from the helper.

## Adding a new provider (checklist)

1. **Env keys** in `app/core/config.py` `Settings`: `<P>_API_KEY`, `<P>_CHAT_MODEL`.
2. **`.env.example`** with the new keys + a comment.
3. **Provider block** in `llm_service.py` (URLs, defaults).
4. **Priority chain** — pick a position. Default: above Vultr (the last-resort).
5. **`USE_<P>` flag** and if/elif cascade. Order must match the priority chain.
6. **`PROVIDER_NAME`** and `ACTIVE_*` triple.
7. **Early-return** in `_make_chat_request` for missing key — name the right env key in the error.
8. **Mock fixture** in `tests/unit/test_llm_service.py` using `respx` to intercept the call.
9. **Run the full pytest suite** — must not regress existing providers.

## Don't do

- Don't change the priority order without a product call.
- Don't remove or rename keys in `_get_error_response`.
- Don't switch to SSE / streaming on these endpoints.
- Don't log the API key (not even truncated).
- Don't add a third-party framework (LangChain, LlamaIndex). Use raw `httpx`.
- Don't add per-request fallback — module-load selection only.
- Don't change temperature defaults without measuring output quality.
