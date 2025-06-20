from typing import Dict, Any, List
import httpx  # Import httpx
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
VULTR_CHAT_MODEL = "deepseek-r1-distill-llama-70b"
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
        question_texts: List[str],
        max_section_score: int = 9, # Default to 9, can be 10 for the last section
        linked_personas: List[Any] = None  # Add optional personas parameter
    ) -> Dict[str, Any]:
        """Generate analysis for a specific section using Vultr"""
        
        # Build persona context if available
        persona_context = ""
        if linked_personas:
            persona_context = "\n\nCustomer Personas Context:\n"
            for persona in linked_personas:
                persona_context += f"\nPersona: {persona.persona_name}"
                if persona.tag:
                    persona_context += f" ({persona.tag})"
                persona_context += f"\n- Age Range: {persona.age_range}"
                persona_context += f"\n- Role: {persona.role_occupation}"
                persona_context += f"\n- Industry: {', '.join(persona.industry_types) if persona.industry_types else 'N/A'}"
                persona_context += f"\n- Goals: {', '.join(persona.goals[:3]) if persona.goals else 'N/A'}"
                persona_context += f"\n- Challenges: {', '.join(persona.challenges[:3]) if persona.challenges else 'N/A'}"
                persona_context += f"\n- Pain Points: {', '.join(persona.pain_points[:3]) if persona.pain_points else 'N/A'}"
                persona_context += "\n"
        
        system_message_content = f"""You are an expert business analyst and startup mentor. Your task is to analyze the user's answers for a specific section of their idea validation process. The section is '{section_name}'.

{persona_context}

Please provide:
1.  **Score**: An integer score from 0 to {max_section_score}, where {max_section_score} is excellent and 0 is poor or insufficient information. Base this score on the completeness, clarity, and strength of the answers provided for the questions in this section.{' Consider how well the answers align with the linked customer personas.' if linked_personas else ''}
2.  **Insight**: A concise (2-3 sentences) key insight derived from the user's answers for this section. This should highlight the most critical takeaway.{' Reference the customer personas where relevant.' if linked_personas else ''}
3.  **Recommendations**: 2-3 actionable recommendations (each a short phrase or sentence) to help the user improve this section of their idea or to consider next steps related to this section.{' Tailor recommendations to the specific customer personas.' if linked_personas else ''}
4.  **Reasoning**: A brief (1-2 sentences) explanation of why you gave the score you did, referencing specific aspects of the answers or lack thereof.{' Include how well the solution addresses the personas needs.' if linked_personas else ''}

Format your response strictly as a JSON object with the keys "score" (int), "insight" (str), "recommendations" (list of str), and "reasoning" (str).
Example JSON (if max_section_score was 9):
{{
  "score": 8,
  "insight": "The user has clearly identified a significant problem and has initial thoughts on a solution.",
  "recommendations": [
    "Further validate the problem with a larger sample size.",
    "Detail the unique selling proposition more clearly.",
    "Outline potential risks and mitigation strategies."
  ],
  "reasoning": "Score reflects good problem identification but needs more detail on solution differentiation and risk assessment."
}}
"""
        
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
        all_sections_analysis: List[Dict[str, Any]],
        linked_personas: List[Any] = None  # Add optional personas parameter
    ) -> Dict[str, Any]:
        """Generate overall strategic analysis using Vultr"""
        
        # Build persona context if available
        persona_summary = ""
        if linked_personas:
            persona_summary = f"\n\nThe business is targeting {len(linked_personas)} customer persona(s):\n"
            for persona in linked_personas:
                persona_summary += f"- {persona.persona_name}: {persona.role_occupation or 'N/A'} in {', '.join(persona.industry_types[:2]) if persona.industry_types else 'N/A'} industry\n"
        
        system_prompt_content = (
            f"You are an expert business strategist.\n"
            f"Given the idea name and analyses of various sections of a business validation questionnaire, "
            f"provide an overall strategic analysis.\n"
            f"{persona_summary}"
            f"Respond ONLY with a valid JSON object in the following format. Ensure the JSON is well-formed:\n"
            f"{{\n"
            f"    \"overview\": \"A concise overall summary of the business idea's potential based on the section analyses{' and how well it serves the target personas' if linked_personas else ''} (3-4 sentences).\",\n"
            f"    \"strategic_next_steps\": [\"List 3-5 actionable strategic next steps for the user to pursue{', considering the specific needs of their target personas' if linked_personas else ''}.\"],\n" # Changed to "List 3-5"
            f"    \"key_strengths\": [\"List 2-3 key strengths identified from the analyses{', especially in relation to serving the target personas' if linked_personas else ''}.\"],\n"
            f"    \"key_challenges\": [\"List 2-3 key challenges or weaknesses identified{', particularly in meeting persona needs' if linked_personas else ''}.\"]\n"
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
