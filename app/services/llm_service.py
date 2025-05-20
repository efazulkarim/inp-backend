from typing import Dict, Any, List
import google.generativeai as genai
from datetime import datetime
import os
import json
from dotenv import load_dotenv

# Try multiple possible locations for the .env file
# Adjusted paths for the 'app/services' directory
possible_env_paths = [
    os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env'),  # project root
    os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'),  # app directory
    os.path.join(os.path.dirname(__file__), '.env'),  # services directory (less likely but possible)
    '.env' # current working directory (if script run from root)
]

env_found = False
for env_path in possible_env_paths:
    if os.path.exists(env_path):
        print(f"[LLM Service] 💡 Found .env file at: {env_path}")
        load_dotenv(dotenv_path=env_path)
        env_found = True
        break

if not env_found:
    print("[LLM Service] ⚠️ WARNING: No .env file found in any standard location!")


# Get API key from environment
api_key = os.getenv("GOOGLE_API_KEY")
print(f"[LLM Service] API key found: {'Yes' if api_key else 'No'}")
print(f"[LLM Service] API key length: {len(api_key) if api_key else 0}")

# Configure Google Gemini
genai.configure(api_key=api_key)

class LLMService:
    @staticmethod
    async def generate_section_analysis(
        section_name: str,
        answers: List[Dict[str, Any]],
        question_texts: List[str]
    ) -> Dict[str, Any]:
        """Generate analysis for a specific section using Gemini"""
        
        # Construct the prompt
        prompt = f"""
        Based on the following answers for the {section_name} section of a business idea validation questionnaire, provide:
        1. A detailed insight (2-3 sentences)
        2. Two specific, actionable recommendations
        3. A score out of 15 based on the completeness and quality of the answers

        Questions and Answers:
        {'-' * 50}
        """
        
        for q, a in zip(question_texts, answers):
            prompt += f"\nQ: {q}\nA: {str(a)}\n"

        prompt += """
        Please provide your analysis in the following JSON format ONLY (no other text):
        {
            "insight": "your detailed insight here",
            "recommendations": ["recommendation 1", "recommendation 2"],
            "score": number between 0 and 15,
            "reasoning": "brief explanation of the score"
        }
        """

        try:
            print(f"[LLM Service] Trying to initialize Gemini model...")
            # Initialize Gemini model - using a more recent model but keeping the old API format
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            print(f"[LLM Service] Sending request to Gemini...")
            # Generate response
            response = await model.generate_content_async(prompt)
            
            print(f"[LLM Service] Received response from Gemini")
            # Parse the response
            response_text = response.text
            # Find the JSON part (between first { and last })
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            json_str = response_text[json_start:json_end]
            
            # Parse JSON
            analysis = json.loads(json_str)
            return analysis
            
        except Exception as e:
            print(f"[LLM Service] Error in LLM service: {str(e)}")
            # Fallback response
            return {
                "insight": f"Unable to generate insight for {section_name} due to technical error.",
                "recommendations": [
                    "Please try regenerating the report",
                    "Contact support if the issue persists"
                ],
                "score": 0,
                "reasoning": "Error in analysis generation"
            }

    @staticmethod
    async def generate_strategic_overview(
        idea_name: str,
        all_sections_analysis: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate overall strategic analysis using Gemini"""
        
        prompt = "Please write a brief analysis of a business idea in JSON format with these fields: overview, strategic_next_steps, key_strengths, key_challenges"

        try:
            print(f"[LLM Service] Trying to initialize Gemini model for strategic overview...")
            # Initialize Gemini model - using a more recent model but keeping the old API format
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            print(f"[LLM Service] Sending strategic overview request to Gemini...")
            # Generate response
            response = await model.generate_content_async(prompt)
            
            print(f"[LLM Service] Received strategic overview response from Gemini")
            # Parse the response
            response_text = response.text
            # Find the JSON part (between first { and last })
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            json_str = response_text[json_start:json_end]
            
            print(f"[LLM Service] Response text: {response_text[:100]}...")
            
            # Parse JSON
            strategic_analysis = json.loads(json_str)
            return strategic_analysis
            
        except Exception as e:
            print(f"[LLM Service] Error in strategic overview generation: {str(e)}")
            return {
                "overview": "Unable to generate strategic overview due to technical error.",
                "strategic_next_steps": ["Please try regenerating the report"],
                "key_strengths": [],
                "key_challenges": []
            }
