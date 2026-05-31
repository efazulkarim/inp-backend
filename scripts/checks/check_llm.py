"""
Test script for LLM service (GLM Coding Plan or Vultr).
Run with: python scripts/checks/check_llm.py
"""
import asyncio
import json
import os
import sys
from pathlib import Path

# Ensure app imports resolve when this script is run by path.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# Load .env before importing llm_service
try:
    from dotenv import load_dotenv
    for env_path in [
        os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "app", ".env"),
        os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env"),
    ]:
        if os.path.exists(env_path):
            load_dotenv(dotenv_path=env_path)
            break
except ImportError:
    pass  # llm_service will load .env when imported

from app.services.llm_service import (
    LLMService,
    ACTIVE_CHAT_MODEL,
    PROVIDER_NAME,
    USE_GLM,
)


async def test_strategic_overview() -> bool:
    """Test generate_strategic_overview returns valid structure."""
    print(f"\n[Test] Using provider: {PROVIDER_NAME} (model: {ACTIVE_CHAT_MODEL})")
    print("[Test] Calling generate_strategic_overview...")

    result = await LLMService.generate_strategic_overview(
        "Test Product",
        [
            {
                "section": "Problem Validation",
                "score": 8,
                "insight": "Clear problem identification with initial solution ideas.",
                "recommendations": ["Validate with more users.", "Refine value proposition."],
            }
        ],
    )

    print("\n[Result] Raw response:")
    print(json.dumps(result, indent=2))

    # Assertions
    has_error = "error" in result
    has_overview = bool(result.get("overview"))
    has_next_steps = len(result.get("strategic_next_steps", [])) > 0
    error_overview = (
        result.get("overview", "").lower().startswith(f"{PROVIDER_NAME.lower()} api")
        or "not configured" in result.get("overview", "").lower()
        or "unable to generate" in result.get("overview", "").lower()
    )

    if has_error or not has_overview or error_overview:
        print(f"\n[FAIL] {PROVIDER_NAME} returned an error or fallback response.")
        return False

    if not has_next_steps:
        print("\n[FAIL] Missing strategic_next_steps in response.")
        return False

    print("\n[PASS] LLM returned valid strategic overview with next steps.")
    return True


async def test_section_analysis() -> bool:
    """Test generate_section_analysis returns valid structure."""
    print(f"\n[Test] Using provider: {PROVIDER_NAME} (model: {ACTIVE_CHAT_MODEL})")
    print("[Test] Calling generate_section_analysis...")

    result = await LLMService.generate_section_analysis(
        section_name="Problem Validation",
        answers=[{"type": "text", "value": "Users struggle to find reliable local services."}],
        question_texts=["What problem does your idea solve?"],
    )

    print("\n[Result] Raw response:")
    print(json.dumps(result, indent=2))

    required_keys = {"insight", "recommendations", "score", "reasoning"}
    has_all_keys = required_keys.issubset(result.keys())
    has_error = "error" in result
    valid_score = isinstance(result.get("score"), (int, float))

    if has_error or not has_all_keys:
        print(f"\n[FAIL] {PROVIDER_NAME} returned an error or incomplete response.")
        return False

    if not valid_score:
        print("\n[FAIL] Missing or invalid score in response.")
        return False

    print("\n[PASS] LLM returned valid section analysis.")
    return True


async def main() -> int:
    """Run all LLM tests."""
    api_key = os.getenv("GLM_API_KEY") or os.getenv("VULTR_API_KEY")
    if not api_key:
        print("[ERROR] No LLM API key found. Set GLM_API_KEY or VULTR_API_KEY in .env")
        return 1

    print("=" * 60)
    print("LLM Service Test")

    results = []
    results.append(await test_strategic_overview())
    results.append(await test_section_analysis())

    passed = sum(results)
    total = len(results)
    print("\n" + "=" * 60)
    print(f"Results: {passed}/{total} tests passed")
    return 0 if passed == total else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
