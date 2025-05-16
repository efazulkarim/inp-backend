import asyncio
import json
from app.services.llm_service import LLMService

async def test_llm():
    print("Testing LLM service with a simple prompt...")
    
    # Test with a minimal analysis
    result = await LLMService.generate_strategic_overview(
        "Test Product",
        [
            {
                "section": "Test Section",
                "score": 10,
                "insight": "This is a test insight.",
                "recommendations": ["Test recommendation 1", "Test recommendation 2"]
            }
        ]
    )
    
    print("Result received from LLM:")
    print(json.dumps(result, indent=2))

# Run the test
if __name__ == "__main__":
    asyncio.run(test_llm()) 