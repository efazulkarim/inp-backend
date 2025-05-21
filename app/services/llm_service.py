from typing import Dict, Any, List
# import google.generativeai as genai # No longer needed
from openai import AsyncOpenAI # Import AsyncOpenAI
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


# Get OpenAI API key from environment
# The AsyncOpenAI client will use the OPENAI_API_KEY environment variable by default.
# You can also pass it directly: client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
client = AsyncOpenAI()
OPENAI_MODEL = "gpt-4o-mini" # Using gpt-4o-mini as requested

# print(f"[LLM Service] OpenAI API key found: {\'Yes\' if os.getenv(\'OPENAI_API_KEY\') else \'No\'}") # Optional: for debugging

class LLMService:
    @staticmethod
    async def generate_section_analysis(
        section_name: str,
        answers: List[Dict[str, Any]], # Expecting answers in format {"type": "...", "value": ...}
        question_texts: List[str]
    ) -> Dict[str, Any]:
        """Generate analysis for a specific section using OpenAI"""
        
        system_message_content = (
            f"You are an expert business analyst. Based on the following answers for the '{section_name}' section "
            f"of a business idea validation questionnaire, provide:\n"
            f"1. A detailed insight (2-3 sentences).\n"
            f"2. Two specific, actionable recommendations.\n"
            f"3. A score out of 15 based on the completeness and quality of the answers.\n"
            f"4. A brief reasoning for the score.\n\n"
            f"Respond ONLY with a valid JSON object in the following format (no other text or explanations before or after the JSON object):\n"
            f"{{\n"
            f"    \"insight\": \"your detailed insight here\",\n"
            f"    \"recommendations\": [\"recommendation 1\", \"recommendation 2\"],\n"
            f"    \"score\": <integer between 0 and 15>,\n"
            f"    \"reasoning\": \"brief explanation of the score\"\n"
            f"}}"
        )
        prompt_messages = [{"role": "system", "content": system_message_content}]
        
        user_content_parts = [f"Section: {section_name}", "Questions and Answers:", '-' * 20]
        for i, (q_text, ans_obj) in enumerate(zip(question_texts, answers)):
            # ans_obj is expected to be like {"type": "multiple_choice", "value": ["option_a"]}
            # or {"type": "text", "value": "user text"}
            answer_value = ans_obj.get('value', 'Not answered')
            user_content_parts.append(f"Q{i+1}: {q_text}")
            user_content_parts.append(f"A{i+1}: {answer_value}")
            user_content_parts.append("") # For a blank line
        
        prompt_messages.append({"role": "user", "content": "\\n".join(user_content_parts)})

        try:
            print(f"[LLM Service - OpenAI] Sending request for section '{section_name}' to {OPENAI_MODEL}...")
            
            response = await client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=prompt_messages,
                response_format={"type": "json_object"}, # Request JSON output
                temperature=0.5, # Adjust for creativity vs. determinism
            )
            
            print(f"[LLM Service - OpenAI] Received response from {OPENAI_MODEL} for section '{section_name}'.")
            
            response_content = response.choices[0].message.content
            if response_content:
                analysis = json.loads(response_content)
            return analysis
            else:
                raise ValueError("Empty response content from OpenAI.")
            
        except Exception as e:
            print(f"[LLM Service - OpenAI] Error in section analysis for '{section_name}': {e}")
            # Fallback response
            return {
                "insight": f"Unable to generate insight for {section_name} due to an AI service error.",
                "recommendations": ["Try again later.", "Contact support if persistent."],
                "score": 0,
                "reasoning": "Error in OpenAI analysis generation."
            }

    @staticmethod
    async def generate_strategic_overview(
        idea_name: str,
        all_sections_analysis: List[Dict[str, Any]] # List of {"section": ..., "score": ..., "insight": ..., "recommendations": ...}
    ) -> Dict[str, Any]:
        """Generate overall strategic analysis using OpenAI"""
        
        system_prompt_content = (
            f"You are an expert business strategist.\n"
            f"Given the idea name and analyses of various sections of a business validation questionnaire, "
            f"provide an overall strategic analysis.\n"
            f"Respond ONLY with a valid JSON object in the following format:\n"
            f"{{\n"
            f"    \"overview\": \"A concise overall summary of the business idea's potential based on the section analyses (3-4 sentences).\",\n"
            f"    \"strategic_next_steps\": [\"3-5 actionable strategic next steps for the user to pursue.\"],\n"
            f"    \"key_strengths\": [\"List 2-3 key strengths identified from the analyses.\"],\n"
            f"    \"key_challenges\": [\"List 2-3 key challenges or weaknesses identified.\"]\n"
            f"}}"
        )

        user_content_parts = [f"Business Idea Name: {idea_name}", "\nSection Analyses Summary:"]
        for i, section_data in enumerate(all_sections_analysis):
            recommendations_str = ", ".join(section_data.get('recommendations', []))
            user_content_parts.append(
                f"\nSection {i+1}: {section_data.get('section', 'N/A')}\n"
                f"  Score: {section_data.get('score', 'N/A')}/15\n"
                f"  Insight: {section_data.get('insight', 'N/A')}\n"
                f"  Recommendations: {recommendations_str}"
            )
        user_prompt = "\n".join(user_content_parts)
        
        prompt_messages = [
            {"role": "system", "content": system_prompt_content},
            {"role": "user", "content": user_prompt}
        ]

        try:
            print(f"[LLM Service - OpenAI] Sending strategic overview request for '{idea_name}' to {OPENAI_MODEL}...")
            
            response = await client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=prompt_messages,
                response_format={"type": "json_object"}, # Request JSON output
                temperature=0.7, # Slightly more creative for overview
            )
            
            print(f"[LLM Service - OpenAI] Received strategic overview response from {OPENAI_MODEL}.")
            
            response_content = response.choices[0].message.content
            if response_content:
                strategic_analysis = json.loads(response_content)
            return strategic_analysis
            else:
                raise ValueError("Empty response content for strategic overview from OpenAI.")
            
        except Exception as e:
            print(f"[LLM Service - OpenAI] Error in strategic overview generation for '{idea_name}': {e}")
            return {
                "overview": "Unable to generate strategic overview due to an AI service error.",
                "strategic_next_steps": ["Try again later."],
                "key_strengths": [],
                "key_challenges": []
            }
