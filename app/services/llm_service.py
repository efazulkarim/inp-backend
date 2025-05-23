from typing import Dict, Any, List
import httpx  # Import httpx
# import google.generativeai as genai # No longer needed
# from openai import AsyncOpenAI # No longer needed
from datetime import datetime
import os
import json
from dotenv import load_dotenv

# Robust .env loading
possible_env_paths = [
    os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env"),
    os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"),
    os.path.join(os.path.dirname(__file__), ".env"),
    ".env"
]
env_found = False
for env_path in possible_env_paths:
    if os.path.exists(env_path):
        print(f"[LLM Service] 💡 Found .env file at: {env_path}")
        load_dotenv(dotenv_path=env_path)
        env_found = True
        break
if not env_found:
    print("[LLM Service] ⚠️ WARNING: No .env file found!")

# Vultr API Configuration
VULTR_API_KEY = os.getenv("VULTR_API_KEY")
VULTR_API_BASE_URL = "https://api.vultrinference.com/v1"
VULTR_CHAT_MODEL = "deepseek-r1-distill-qwen-32b" # Replace with your desired Vultr model ID
# print(f"[LLM Service] Vultr API Key found: {'Yes' if VULTR_API_KEY else 'No'}")

class LLMService:
    @staticmethod
    async def _make_vultr_request(payload: Dict[str, Any]) -> Dict[str, Any]:
        """Helper method to make requests to Vultr API"""
        if not VULTR_API_KEY:
            print("[LLM Service - Vultr] CRITICAL ERROR: VULTR_API_KEY not found.")
            # Return a structure that matches an error response from the main methods
            return {
                "error": "VULTR_API_KEY not configured",
                "insight": "Vultr API Key not configured.", # For section_analysis fallback
                "recommendations": ["Please configure VULTR_API_KEY in .env"], # For section_analysis fallback
                "score": 0, # For section_analysis fallback
                "reasoning": "API Key missing.", # For section_analysis fallback
                "overview": "Vultr API Key not configured.", # For strategic_overview fallback
                "strategic_next_steps": ["Please configure VULTR_API_KEY in .env"], # For strategic_overview fallback
                "key_strengths": [], # For strategic_overview fallback
                "key_challenges": [] # For strategic_overview fallback
            }

        headers = {
            "Authorization": f"Bearer {VULTR_API_KEY}",
            "Content-Type": "application/json"
        }
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{VULTR_API_BASE_URL}/chat/completions",
                    json=payload,
                    headers=headers,
                    timeout=60.0 # Increased timeout for potentially longer LLM responses
                )
                response.raise_for_status()  # Raise an exception for HTTP errors (4xx or 5xx)
                result = response.json()
                token_usage = result.get("usage", {}).get("total_tokens", 0)
                return result, token_usage
            except httpx.HTTPStatusError as e:
                print(f"[LLM Service - Vultr] HTTP error: {e.response.status_code} - {e.response.text}")
                # Try to parse error response from Vultr if available
                try:
                    error_details = e.response.json()
                except json.JSONDecodeError:
                    error_details = e.response.text
                return {
                    "error": "Vultr API HTTP error",
                    "status_code": e.response.status_code,
                    "details": error_details,
                    # Fallback fields for direct use by calling methods
                    "insight": f"Vultr API HTTP error {e.response.status_code}.",
                    "recommendations": ["Check Vultr API status and your request."],
                    "score": 0,
                    "reasoning": f"HTTP {e.response.status_code}",
                    "overview": f"Vultr API HTTP error {e.response.status_code}.",
                    "strategic_next_steps": ["Check Vultr API status and your request."],
                    "key_strengths": [],
                    "key_challenges": []
                }
            except httpx.RequestError as e:
                print(f"[LLM Service - Vultr] Request error: {e}")
                return {
                     "error": "Vultr API Request error",
                     "details": str(e),
                    "insight": "Vultr API request error.",
                    "recommendations": ["Check network or Vultr service status."],
                    "score": 0,
                    "reasoning": "Request Error",
                    "overview": "Vultr API request error.",
                    "strategic_next_steps": ["Check network or Vultr service status."],
                    "key_strengths": [],
                    "key_challenges": []
                }


    @staticmethod
    async def generate_section_analysis(
        section_name: str,
        answers: List[Dict[str, Any]], # Expecting answers in format {"type": "...", "value": ...}
        question_texts: List[str]
    ) -> Dict[str, Any]:
        """Generate analysis for a specific section using Vultr"""
        
        system_message_content = (
            f"You are an expert business analyst. Based on the following answers for the '{section_name}' section "
            f"of a business idea validation questionnaire, provide:\n"
            f"1. A detailed insight (2-3 sentences).\n"
            f"2. Two specific, actionable recommendations.\n"
            f"3. A score out of 15 based on the completeness and quality of the answers.\n"
            f"4. A brief reasoning for the score.\n\n"
            f"Respond ONLY with a valid JSON object in the following format (no other text or explanations before or after the JSON object). Ensure the JSON is well-formed:\n" # Added "Ensure the JSON is well-formed"
            f"{{\n"
            f"    \"insight\": \"your detailed insight here\",\n"
            f"    \"recommendations\": [\"recommendation 1\", \"recommendation 2\"],\n"
            f"    \"score\": <integer_between_0_and_15>,\n" # Changed to <integer_between_0_and_15> for clarity
            f"    \"reasoning\": \"brief explanation of the score\"\n"
            f"}}"
        )
        
        user_content_parts = [f"Section: {section_name}", "Questions and Answers:", '-' * 20]
        for i, (q_text, ans_obj) in enumerate(zip(question_texts, answers)):
            answer_value = ans_obj.get('value', 'Not answered')
            user_content_parts.append(f"Q{i+1}: {q_text}")
            user_content_parts.append(f"A{i+1}: {answer_value}")
            user_content_parts.append("")
        
        vultr_payload = {
            "model": VULTR_CHAT_MODEL,
            "messages": [
                {"role": "system", "content": system_message_content},
                {"role": "user", "content": "\\n".join(user_content_parts)}
            ],
            "temperature": 0.5,
            # Vultr's API might not explicitly have a "response_format: json_object" like OpenAI.
            # The strictness of the system prompt is key here.
        }

        try:
            print(f"[LLM Service - Vultr] Sending request for section '{section_name}' to {VULTR_CHAT_MODEL}...")
            api_response, token_usage = await LLMService._make_vultr_request(vultr_payload)
            
            if "error" in api_response: # Check if helper returned an error structure
                print(f"[LLM Service - Vultr] Error in section analysis for '{section_name}': {api_response.get('details', api_response.get('error'))}")
                return { # Fallback response matching expected structure
                    "insight": api_response.get("insight", f"Unable to generate insight for {section_name} due to an API error."),
                    "recommendations": api_response.get("recommendations", ["Try again later."]),
                    "score": api_response.get("score", 0),
                    "reasoning": api_response.get("reasoning", "Error in Vultr API call."),
                    "token_usage": token_usage
                }

            print(f"[LLM Service - Vultr] Received response from {VULTR_CHAT_MODEL} for section '{section_name}'.")
            
            # Assuming Vultr response structure: response['choices'][0]['message']['content']
            response_content_str = api_response.get("choices", [{}])[0].get("message", {}).get("content", "")
            
            if response_content_str:
                try:
                    # More robust JSON extraction: find the first '{' and last '}'
                    json_start_index = response_content_str.find('{')
                    json_end_index = response_content_str.rfind('}')
                    
                    if json_start_index != -1 and json_end_index != -1 and json_end_index > json_start_index:
                        json_substring = response_content_str[json_start_index : json_end_index + 1]
                        # print(f"[LLM Service - Vultr] Extracted JSON substring: {json_substring}") # For debugging
                        analysis = json.loads(json_substring)
                        required_keys = {"insight", "recommendations", "score", "reasoning"}
                        if not required_keys.issubset(analysis.keys()):
                            raise ValueError(f"Missing one or more required keys in LLM JSON response. Got: {analysis.keys()}. Original response: {response_content_str}")
                        return analysis
                    else:
                        raise ValueError(f"Could not find a valid JSON structure ({{...}}) in the LLM response. Response: '{response_content_str}'")
                except json.JSONDecodeError as je:
                    print(f"[LLM Service - Vultr] JSONDecodeError for section '{section_name}': {je}. Response: '{response_content_str}'")
                    raise ValueError(f"Failed to decode JSON from Vultr for section '{section_name}'. Content: {response_content_str}")
            else:
                raise ValueError(f"Empty response content from Vultr for section '{section_name}'. Full API response: {api_response}")
            
        except Exception as e:
            print(f"[LLM Service - Vultr] General error in section analysis for '{section_name}': {e}")
            return {
                "insight": f"Unable to generate insight for {section_name} due to a processing error.",
                "recommendations": ["Try again later.", "Review service logs."],
                "score": 0,
                "reasoning": "Error in Vultr analysis processing.",
                "token_usage": token_usage
            }

    @staticmethod
    async def generate_strategic_overview(
        idea_name: str,
        all_sections_analysis: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate overall strategic analysis using Vultr"""
        
        system_prompt_content = (
            f"You are an expert business strategist.\n"
            f"Given the idea name and analyses of various sections of a business validation questionnaire, "
            f"provide an overall strategic analysis.\n"
            f"Respond ONLY with a valid JSON object in the following format. Ensure the JSON is well-formed:\n"
            f"{{\n"
            f"    \"overview\": \"A concise overall summary of the business idea's potential based on the section analyses (3-4 sentences).\",\n"
            f"    \"strategic_next_steps\": [\"List 3-5 actionable strategic next steps for the user to pursue.\"],\n" # Changed to "List 3-5"
            f"    \"key_strengths\": [\"List 2-3 key strengths identified from the analyses.\"],\n"
            f"    \"key_challenges\": [\"List 2-3 key challenges or weaknesses identified.\"]\n"
            f"}}"
        )

        user_content_parts = [f"Business Idea Name: {idea_name}", "\\nSection Analyses Summary:"]
        for i, section_data in enumerate(all_sections_analysis):
            recommendations_str = ", ".join(section_data.get('recommendations', []))
            user_content_parts.append(
                f"\\nSection {i+1}: {section_data.get('section', 'N/A')}\\n"
                f"  Score: {section_data.get('score', 'N/A')}/15\\n"
                f"  Insight: {section_data.get('insight', 'N/A')}\\n"
                f"  Recommendations: {recommendations_str}"
            )
        user_prompt = "\\n".join(user_content_parts)
        
        vultr_payload = {
            "model": VULTR_CHAT_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt_content},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.7,
        }

        try:
            print(f"[LLM Service - Vultr] Sending strategic overview request for '{idea_name}' to {VULTR_CHAT_MODEL}...")
            api_response, token_usage = await LLMService._make_vultr_request(vultr_payload)

            if "error" in api_response: # Check if helper returned an error structure
                print(f"[LLM Service - Vultr] Error in strategic overview for '{idea_name}': {api_response.get('details', api_response.get('error'))}")
                return { # Fallback response matching expected structure
                    "overview": api_response.get("overview", "Unable to generate strategic overview due to an API error."),
                    "strategic_next_steps": api_response.get("strategic_next_steps", ["Try again later."]),
                    "key_strengths": api_response.get("key_strengths", []),
                    "key_challenges": api_response.get("key_challenges", []),
                    "token_usage": token_usage
                }

            print(f"[LLM Service - Vultr] Received strategic overview response from {VULTR_CHAT_MODEL}.")
            
            response_content_str = api_response.get("choices", [{}])[0].get("message", {}).get("content", "")

            if response_content_str:
                try:
                    # More robust JSON extraction: find the first '{' and last '}'
                    json_start_index = response_content_str.find('{')
                    json_end_index = response_content_str.rfind('}')

                    if json_start_index != -1 and json_end_index != -1 and json_end_index > json_start_index:
                        json_substring = response_content_str[json_start_index : json_end_index + 1]
                        # print(f"[LLM Service - Vultr] Extracted JSON substring for overview: {json_substring}") # For debugging
                        strategic_analysis = json.loads(json_substring)
                        required_keys = {"overview", "strategic_next_steps", "key_strengths", "key_challenges"}
                        if not required_keys.issubset(strategic_analysis.keys()):
                            raise ValueError(f"Missing one or more required keys in LLM JSON response for overview. Got: {strategic_analysis.keys()}. Original response: {response_content_str}")
                        return strategic_analysis
                    else:
                        raise ValueError(f"Could not find a valid JSON structure ({{...}}) in the LLM response for overview. Response: '{response_content_str}'")
                except json.JSONDecodeError as je:
                    print(f"[LLM Service - Vultr] JSONDecodeError for strategic overview '{idea_name}': {je}. Response: {response_content_str}")
                    raise ValueError(f"Failed to decode JSON from Vultr for strategic overview '{idea_name}'. Content: {response_content_str}")
            else:
                raise ValueError(f"Empty response content for strategic overview from Vultr for '{idea_name}'. Full API response: {api_response}")
            
        except Exception as e:
            print(f"[LLM Service - Vultr] General error in strategic overview generation for '{idea_name}': {e}")
            return {
                "overview": "Unable to generate strategic overview due to a processing error.",
                "strategic_next_steps": ["Try again later.", "Review service logs."],
                "key_strengths": [],
                "key_challenges": [],
                "token_usage": token_usage
            }
