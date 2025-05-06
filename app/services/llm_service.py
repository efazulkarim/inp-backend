from typing import Dict, Any, List
import google.generativeai as genai
from datetime import datetime
import os
import json
from dotenv import load_dotenv

load_dotenv()

# Configure Google Gemini
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

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
            # Initialize Gemini model
            model = genai.GenerativeModel('gemini-pro')
            
            # Generate response
            response = await model.generate_content_async(prompt)
            
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
            print(f"Error in LLM service: {str(e)}")
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
        
        prompt = f"""
        Based on the following section-wise analysis of the business idea "{idea_name}", provide:
        1. A comprehensive overview (2-3 sentences)
        2. 4-5 strategic next steps
        
        Section Analysis:
        {'-' * 50}
        """
        
        for analysis in all_sections_analysis:
            prompt += f"\n{analysis['section']}\n"
            prompt += f"Score: {analysis['score']}/15\n"
            prompt += f"Insight: {analysis['insight']}\n"
            prompt += "Recommendations:\n"
            for rec in analysis['recommendations']:
                prompt += f"- {rec}\n"
            prompt += f"{'-' * 50}\n"

        prompt += """
        Please provide your analysis in the following JSON format ONLY (no other text):
        {
            "overview": "comprehensive overview here",
            "strategic_next_steps": ["step 1", "step 2", "step 3", "step 4"],
            "key_strengths": ["strength 1", "strength 2"],
            "key_challenges": ["challenge 1", "challenge 2"]
        }
        """

        try:
            # Initialize Gemini model
            model = genai.GenerativeModel('gemini-pro')
            
            # Generate response
            response = await model.generate_content_async(prompt)
            
            # Parse the response
            response_text = response.text
            # Find the JSON part (between first { and last })
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            json_str = response_text[json_start:json_end]
            
            # Parse JSON
            strategic_analysis = json.loads(json_str)
            return strategic_analysis
            
        except Exception as e:
            print(f"Error in LLM service: {str(e)}")
            return {
                "overview": "Unable to generate strategic overview due to technical error.",
                "strategic_next_steps": ["Please try regenerating the report"],
                "key_strengths": [],
                "key_challenges": []
            }
