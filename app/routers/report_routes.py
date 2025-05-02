from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from app.auth import get_current_user
from app.models import Answer, User, IdeaBoard, Questionnaire
from app import schemas
from app.database import get_db
from datetime import datetime
from app.services.llm_service import LLMService

router = APIRouter()

def calculate_section_score(answers: List[Any], max_score: int) -> int:
    """Calculate score for a section based on completeness and quality of answers"""
    if not answers:
        return 0
    # Implement scoring logic based on answer completeness and quality
    return max_score  # Placeholder - implement actual scoring logic

def generate_insights(answers: Dict[str, Any], section: str) -> str:
    """Generate AI-powered insights based on answers for a specific section"""
    # This is where you'll integrate with your AI service
    # For now, returning placeholder insights
    return f"Based on the provided answers, the {section} analysis shows strong potential..."

@router.get("/report/{idea_id}", response_model=schemas.ReportResponse)
async def generate_report(
    idea_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Generate a comprehensive report for an idea using LLM analysis"""
    # Verify idea belongs to user
    idea = db.query(IdeaBoard).filter(
        IdeaBoard.id == idea_id,
        IdeaBoard.user_id == current_user.id
    ).first()
    
    if not idea:
        raise HTTPException(status_code=404, detail="Idea not found")

    # Get all answers for this idea
    answers = db.query(Answer).filter(
        Answer.ideaBoard_id == idea_id,
        Answer.user_id == current_user.id
    ).all()

    if not answers:
        raise HTTPException(status_code=404, detail="No answers found for this idea")

    # Group answers by section
    sections = {
        "target_audience": {"title": "Target audience"},
        "customer_needs": {"title": "Customer needs"},
        "articulate_solution": {"title": "Articulate solution"},
        "key_benefits": {"title": "Key benefits & advantages"},
        "market_opportunities": {"title": "Market opportunities"},
        "competitive_advantages": {"title": "Competitive advantages"},
        "customer_adoption": {"title": "Customer adoption potential"},
        "key_metrics": {"title": "Key metrics & goal"}
    }

    # Process each section with LLM
    section_analyses = []
    total_score = 0

    for section_key, section_info in sections.items():
        # Get questions and answers for this section
        section_questions = db.query(Questionnaire).filter(
            Questionnaire.q_uuid.startswith(f"step_{section_key}_")
        ).all()
        
        section_answers = [
            answer for answer in answers
            if answer.question_id in [q.id for q in section_questions]
        ]
        
        # Generate analysis using LLM
        analysis = await LLMService.generate_section_analysis(
            section_info["title"],
            [a.answer for a in section_answers],
            [q.text for q in section_questions]
        )
        
        section_analyses.append({
            "section": section_info["title"],
            "score": analysis["score"],
            "insight": analysis["insight"],
            "recommendations": analysis["recommendations"]
        })
        total_score += analysis["score"]

    # Generate strategic overview
    strategic_analysis = await LLMService.generate_strategic_overview(
        idea.idea_name,
        section_analyses
    )

    # Format the response
    report_sections = [
        schemas.ReportSection(
            category=analysis["section"],
            score=analysis["score"],
            weighted_score=analysis["score"],  # Can implement custom weighting if needed
            insight=analysis["insight"],
            recommendations=analysis["recommendations"]
        )
        for analysis in section_analyses
    ]

    return schemas.ReportResponse(
        idea_name=idea.idea_name,
        overall_score=total_score,
        report_overview=strategic_analysis["overview"],
        sections=report_sections,
        strategic_next_steps=strategic_analysis["strategic_next_steps"]
    )
