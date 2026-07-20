"""
End-to-End Tests for LLM Service with Gemini API

Tests the complete flow from idea creation to validation using Gemini 2.5 Flash.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any, List

from app.services.llm_service import (
    LLMService, 
    USE_GEMINI, 
    GEMINI_API_KEY,
    PROVIDER_NAME,
    GEMINI_CHAT_MODEL
)


class TestGeminiIntegration:
    """Test Gemini API integration end-to-end."""
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_gemini_api_key_configured(self):
        """Test that Gemini API key is properly configured."""
        # This test verifies the API key is set
        if USE_GEMINI:
            assert GEMINI_API_KEY is not None
            assert len(GEMINI_API_KEY) > 0
            assert PROVIDER_NAME == "Gemini"
        else:
            # If not configured, skip but document it
            pytest.skip("Gemini API key not configured in environment")
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_gemini_section_analysis_basic(self):
        """Test basic section analysis generation with Gemini."""
        if not USE_GEMINI:
            pytest.skip("Gemini API key not configured in environment")
        
        section_name = "Problem Validation"
        answers = [
            {"type": "rating", "value": 8},
            {"type": "text", "value": "Small businesses struggle with manual inventory tracking"},
            {"type": "text", "value": "An AI-powered inventory management system"}
        ]
        question_texts = [
            "How severe is the problem? (1-10)",
            "Describe the problem you're solving",
            "What's your proposed solution?"
        ]
        
        result = await LLMService.generate_section_analysis(
            section_name=section_name,
            answers=answers,
            question_texts=question_texts,
            max_section_score=9
        )
        
        # Verify response structure
        assert "insight" in result
        assert "recommendations" in result
        assert "score" in result
        assert "reasoning" in result
        
        # Verify data types
        assert isinstance(result["insight"], str)
        assert isinstance(result["recommendations"], list)
        assert isinstance(result["score"], int)
        assert isinstance(result["reasoning"], str)
        
        # Verify score range
        assert 0 <= result["score"] <= 9
        
        # Verify recommendations is not empty
        assert len(result["recommendations"]) > 0
        
        print(f"✓ Section Analysis Score: {result['score']}/9")
        print(f"✓ Insight: {result['insight']}")
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_gemini_strategic_overview_basic(self):
        """Test strategic overview generation with Gemini."""
        if not USE_GEMINI:
            pytest.skip("Gemini API key not configured in environment")
        
        idea_name = "AI Inventory Manager"
        all_sections_analysis = [
            {
                "section": "Problem Validation",
                "score": 8,
                "max_score": 9,
                "insight": "Clear problem identification with strong market need",
                "recommendations": ["Validate with more customers", "Document use cases"]
            },
            {
                "section": "Solution Fit",
                "score": 7,
                "max_score": 9,
                "insight": "Solution addresses core pain points effectively",
                "recommendations": ["Add competitive analysis", "Define MVP features"]
            },
            {
                "section": "Market Analysis",
                "score": 6,
                "max_score": 9,
                "insight": "Market size is substantial but needs more research",
                "recommendations": ["Research TAM/SAM/SOM", "Identify key competitors"]
            }
        ]
        
        result = await LLMService.generate_strategic_overview(
            idea_name=idea_name,
            all_sections_analysis=all_sections_analysis
        )
        
        # Verify response structure
        assert "overview" in result
        assert "strategic_next_steps" in result
        assert "key_strengths" in result
        assert "key_challenges" in result
        
        # Verify data types
        assert isinstance(result["overview"], str)
        assert isinstance(result["strategic_next_steps"], list)
        assert isinstance(result["key_strengths"], list)
        assert isinstance(result["key_challenges"], list)
        
        # Verify content is meaningful
        assert len(result["overview"]) > 20
        assert len(result["strategic_next_steps"]) >= 3
        assert len(result["key_strengths"]) >= 2
        assert len(result["key_challenges"]) >= 2
        
        print(f"✓ Strategic Overview: {result['overview'][:100]}...")
        print(f"✓ Next Steps: {len(result['strategic_next_steps'])} recommendations")
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_gemini_with_personas(self):
        """Test analysis with customer personas context."""
        if not USE_GEMINI:
            pytest.skip("Gemini API key not configured in environment")
        
        # Mock persona objects
        mock_persona = Mock()
        mock_persona.persona_name = "Small Business Owner"
        mock_persona.tag = "Primary"
        mock_persona.age_range = "35-50"
        mock_persona.role_occupation = "Retail Store Owner"
        mock_persona.industry_types = ["Retail", "E-commerce"]
        mock_persona.goals = ["Increase efficiency", "Reduce costs", "Scale business"]
        mock_persona.challenges = ["Limited time", "Budget constraints", "Technical knowledge"]
        mock_persona.pain_points = ["Manual processes", "Inventory errors", "Stockouts"]
        
        linked_personas = [mock_persona]
        
        section_name = "Customer Validation"
        answers = [
            {"type": "text", "value": "Small retail store owners aged 35-50"},
            {"type": "text", "value": "They struggle with manual inventory tracking and frequent stockouts"}
        ]
        question_texts = [
            "Who is your target customer?",
            "What are their main pain points?"
        ]
        
        result = await LLMService.generate_section_analysis(
            section_name=section_name,
            answers=answers,
            question_texts=question_texts,
            max_section_score=9,
            linked_personas=linked_personas
        )
        
        # Verify response includes persona-aware analysis
        assert "insight" in result
        assert "recommendations" in result
        assert "score" in result
        
        print(f"✓ Persona-Aware Score: {result['score']}/9")
        print(f"✓ Persona Insight: {result['insight']}")
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_gemini_full_validation_flow(self):
        """Test complete idea validation flow from start to finish."""
        if not USE_GEMINI:
            pytest.skip("Gemini API key not configured in environment")
        
        idea_name = "Smart Learning Platform"
        
        # Simulate a complete questionnaire with multiple sections
        sections_data = [
            {
                "name": "Problem Validation",
                "answers": [
                    {"type": "rating", "value": 9},
                    {"type": "text", "value": "Students struggle with personalized learning paths"}
                ],
                "questions": [
                    "How severe is the problem? (1-10)",
                    "Describe the problem"
                ],
                "max_score": 9
            },
            {
                "name": "Solution Design",
                "answers": [
                    {"type": "text", "value": "AI-powered adaptive learning platform"},
                    {"type": "rating", "value": 8}
                ],
                "questions": [
                    "Describe your solution",
                    "How innovative is it? (1-10)"
                ],
                "max_score": 9
            },
            {
                "name": "Market Opportunity",
                "answers": [
                    {"type": "text", "value": "$5B EdTech market growing at 15% annually"},
                    {"type": "text", "value": "K-12 schools and online learners"}
                ],
                "questions": [
                    "What's the market size?",
                    "Who are your target segments?"
                ],
                "max_score": 9
            },
            {
                "name": "Business Model",
                "answers": [
                    {"type": "text", "value": "SaaS subscription for schools, freemium for individuals"},
                    {"type": "rating", "value": 7}
                ],
                "questions": [
                    "What's your revenue model?",
                    "How sustainable is it? (1-10)"
                ],
                "max_score": 9
            }
        ]
        
        # Generate section analyses
        all_analyses = []
        for section in sections_data:
            analysis = await LLMService.generate_section_analysis(
                section_name=section["name"],
                answers=section["answers"],
                question_texts=section["questions"],
                max_section_score=section["max_score"]
            )
            
            all_analyses.append({
                "section": section["name"],
                "score": analysis["score"],
                "max_score": section["max_score"],
                "insight": analysis["insight"],
                "recommendations": analysis["recommendations"]
            })
            
            print(f"✓ {section['name']}: {analysis['score']}/{section['max_score']}")
        
        # Generate strategic overview
        strategic_result = await LLMService.generate_strategic_overview(
            idea_name=idea_name,
            all_sections_analysis=all_analyses
        )
        
        # Verify complete flow results
        assert len(all_analyses) == 4
        assert all("score" in a for a in all_analyses)
        assert "overview" in strategic_result
        assert "strategic_next_steps" in strategic_result
        
        # Calculate total score
        total_score = sum(a["score"] for a in all_analyses)
        max_total = sum(a["max_score"] for a in all_analyses)
        percentage = (total_score / max_total) * 100
        
        print(f"\n{'='*60}")
        print(f"IDEA VALIDATION COMPLETE: {idea_name}")
        print(f"{'='*60}")
        print(f"Total Score: {total_score}/{max_total} ({percentage:.1f}%)")
        print(f"\nStrategic Overview:")
        print(f"{strategic_result['overview']}")
        print(f"\nKey Strengths:")
        for strength in strategic_result["key_strengths"]:
            print(f"  • {strength}")
        print(f"\nKey Challenges:")
        for challenge in strategic_result["key_challenges"]:
            print(f"  • {challenge}")
        print(f"\nStrategic Next Steps:")
        for i, step in enumerate(strategic_result["strategic_next_steps"], 1):
            print(f"  {i}. {step}")
        print(f"{'='*60}\n")
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_gemini_error_handling(self):
        """Test error handling when Gemini API fails."""
        if not USE_GEMINI:
            pytest.skip("Gemini API key not configured in environment")
        
        # Test with invalid/empty answers
        section_name = "Test Section"
        answers = [
            {"type": "text", "value": ""},  # Empty answer
            {"type": "text", "value": ""}   # Empty answer
        ]
        question_texts = [
            "Question 1",
            "Question 2"
        ]
        
        result = await LLMService.generate_section_analysis(
            section_name=section_name,
            answers=answers,
            question_texts=question_texts,
            max_section_score=9
        )
        
        # Should still return valid structure even with poor input
        assert "insight" in result
        assert "recommendations" in result
        assert "score" in result
        
        print(f"✓ Error handling test passed - Score: {result['score']}")


class TestGeminiAPIResponseFormat:
    """Test Gemini API response format compatibility."""
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_gemini_json_extraction(self):
        """Test that JSON is properly extracted from Gemini responses."""
        if not USE_GEMINI:
            pytest.skip("Gemini API key not configured in environment")
        
        # Test with a prompt that should return clean JSON
        section_name = "Quick Test"
        answers = [
            {"type": "rating", "value": 7},
            {"type": "text", "value": "Testing JSON response format"}
        ]
        question_texts = [
            "Rate this (1-10)",
            "Comments"
        ]
        
        result = await LLMService.generate_section_analysis(
            section_name=section_name,
            answers=answers,
            question_texts=question_texts,
            max_section_score=9
        )
        
        # Verify all required keys are present
        required_keys = {"insight", "recommendations", "score", "reasoning"}
        assert required_keys.issubset(result.keys())
        
        # Verify score is an integer
        assert isinstance(result["score"], int)
        
        # Verify recommendations is a list of strings
        assert isinstance(result["recommendations"], list)
        assert all(isinstance(r, str) for r in result["recommendations"])
        
        print("✓ JSON extraction test passed")


# Run tests with: pytest tests/e2e/test_llm_gemini_e2e.py -v --e2e
