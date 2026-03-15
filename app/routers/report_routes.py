import logging
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from app.auth import get_current_user
from app.models import Answer, User, IdeaBoard, Questionnaire, Report, CustomerPersona, IdeaPersonaLink
from app import schemas
from app.database import get_db, SessionLocal
from datetime import datetime
import json
import os
import tempfile
from app.services.llm_service import LLMService, ACTIVE_CHAT_MODEL, PROVIDER_NAME
from app.services.pdf_service import generate_report_pdf
from app.services.subscription_service import SubscriptionService
from app.constants import (
    REPORT_STATUS_QUEUED,
    REPORT_STATUS_PROCESSING,
    REPORT_STATUS_COMPLETED,
    REPORT_STATUS_FAILED,
    REPORT_STALE_THRESHOLD_SECONDS,
)
from io import BytesIO
import asyncio

logger = logging.getLogger(__name__)
router = APIRouter()
ENVIRONMENT = os.getenv("ENVIRONMENT", "development").lower()

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

@router.post("/generate/{idea_id}", response_model=schemas.ReportRequestResponse)
async def request_report_generation(
    idea_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Request a report to be generated asynchronously"""
    # Verify idea belongs to user
    idea = db.query(IdeaBoard).filter(
        IdeaBoard.id == idea_id,
        IdeaBoard.user_id == current_user.id
    ).first()
    
    if not idea:
        raise HTTPException(status_code=404, detail="Idea not found")

    # Verify the idea is complete
    if not idea.is_complete:
        raise HTTPException(
            status_code=400, 
            detail="Cannot generate report for incomplete idea. All steps must be completed."
        )
        
    # Check if a report is already being generated or exists
    existing_report = db.query(Report).filter(
        Report.idea_id == idea_id
    ).first()
    
    if existing_report:
        if existing_report.status == REPORT_STATUS_COMPLETED:
            return {
                "report_id": existing_report.id,
                "status": REPORT_STATUS_COMPLETED,
                "message": "Report already exists"
            }
        if existing_report.status == REPORT_STATUS_PROCESSING:
            elapsed = (datetime.utcnow() - existing_report.updated_at).total_seconds()
            if elapsed > REPORT_STALE_THRESHOLD_SECONDS:
                existing_report.status = REPORT_STATUS_QUEUED
                db.commit()
                logger.warning(
                    "Report %s stale (%.0fs), reset to queued",
                    existing_report.id,
                    elapsed,
                )

            return {
                "report_id": existing_report.id,
                "status": existing_report.status,
                "message": "Report generation in progress"
            }

    reports_limit = await SubscriptionService.get_user_limit(
        current_user, "reports_per_month"
    )
    if reports_limit == 0:
        raise HTTPException(
            status_code=403,
            detail="Active subscription required to generate reports.",
        )
    if reports_limit != float("inf"):
        from datetime import timedelta
        from app.constants import BILLING_PERIOD_DAYS

        if current_user.current_period_end:
            period_start = current_user.current_period_end - timedelta(
                days=BILLING_PERIOD_DAYS
            )
        else:
            period_start = datetime.utcnow() - timedelta(days=BILLING_PERIOD_DAYS)

        reports_this_period = db.query(Report).filter(
            Report.user_id == current_user.id,
            Report.status == REPORT_STATUS_COMPLETED,
            Report.created_at >= period_start,
        ).count()
        if reports_this_period >= reports_limit:
            raise HTTPException(
                status_code=429,
                detail=f"Report limit reached ({reports_limit} per billing period). Upgrade to generate more.",
            )

    if existing_report:
        report = existing_report
        report.status = REPORT_STATUS_QUEUED
        report.updated_at = datetime.utcnow()
    else:
        report = Report(
            idea_id=idea_id,
            user_id=current_user.id,
            status=REPORT_STATUS_QUEUED,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.add(report)
        
    db.commit()
    db.refresh(report)
    
    # Start the background task to generate the report
    background_tasks.add_task(
        generate_report_background, 
        report.id, 
        idea_id, 
        current_user.id
    )
    
    return {
        "report_id": report.id,
        "status": REPORT_STATUS_QUEUED,
        "message": "Report generation has been queued"
    }

@router.get("/status/{report_id}", response_model=schemas.ReportStatusResponse)
async def check_report_status(
    report_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Check the status of a report generation request"""
    report = db.query(Report).filter(
        Report.id == report_id,
        Report.user_id == current_user.id
    ).first()
    
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
        
    return {
        "report_id": report.id,
        "status": report.status,
        "created_at": report.created_at,
        "updated_at": report.updated_at,
        "error_message": report.error_message
    }

@router.get("/report/{idea_id}", response_model=schemas.ReportResponse)
async def get_report(
    idea_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a completed report for an idea"""
    # Verify idea belongs to user
    idea = db.query(IdeaBoard).filter(
        IdeaBoard.id == idea_id,
        IdeaBoard.user_id == current_user.id
    ).first()
    
    if not idea:
        raise HTTPException(status_code=404, detail="Idea not found")
    
    report = db.query(Report).filter(
        Report.idea_id == idea_id,
        Report.status == REPORT_STATUS_COMPLETED
    ).first()
    
    if not report:
        # If no completed report exists, check if one is in progress
        in_progress = db.query(Report).filter(
            Report.idea_id == idea_id
        ).first()
        
        if in_progress:
            raise HTTPException(
                status_code=202, 
                detail=f"Report is {in_progress.status}. Please check status endpoint."
            )
        else:
            raise HTTPException(
                status_code=404, 
                detail="No report found. Please request a report generation first."
            )
    
    # Return the report content
    return report.content

@router.get("/download/{idea_id}")
async def download_report(
    idea_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Download report as PDF"""
    # Verify idea belongs to user
    idea = db.query(IdeaBoard).filter(
        IdeaBoard.id == idea_id,
        IdeaBoard.user_id == current_user.id
    ).first()
    
    if not idea:
        raise HTTPException(status_code=404, detail="Idea not found")
    
    report = db.query(Report).filter(
        Report.idea_id == idea_id,
        Report.status == REPORT_STATUS_COMPLETED
    ).first()

    if not report or not report.content:
        raise HTTPException(status_code=404, detail="Report not found or incomplete")

    pdf_bytes = await generate_report_pdf(report.content, idea.idea_name)
    filename = f"{idea.idea_name.replace(' ', '_')}_Report.pdf"

    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )

async def generate_report_background(report_id: int, idea_id: int, user_id: int):
    """Background task to generate a report."""
    db = SessionLocal()
    try:
        report = db.query(Report).filter(Report.id == report_id).first()
        if not report:
            logger.warning("Report %s not found for background generation", report_id)
            return
        report.status = REPORT_STATUS_PROCESSING
        report.updated_at = datetime.utcnow()
        db.commit()

        # Get idea details
        idea = db.query(IdeaBoard).filter(IdeaBoard.id == idea_id).first()

        # Get all answers for this idea
        answers = db.query(Answer).filter(
            Answer.ideaBoard_id == idea_id,
            Answer.user_id == user_id
        ).all()

        if not answers:
            report.status = REPORT_STATUS_FAILED
            report.error_message = "No answers found for this idea"
            db.commit()
            return

        # Get linked customer personas - make this optional
        linked_personas = []
        try:
            persona_links = db.query(IdeaPersonaLink).filter(
                IdeaPersonaLink.idea_id == idea_id
            ).all()
            
            for link in persona_links:
                persona = db.query(CustomerPersona).filter(
                    CustomerPersona.id == link.persona_id
                ).first()
                if persona:
                    linked_personas.append(persona)
        except Exception as e:
            logger.warning(
                "Could not load linked personas for idea %s: %s",
                idea_id,
                e,
                exc_info=False,
            )
            linked_personas = []

        # Group answers by section with max scores
        sections = {
            "target_audience": {"title": "Target audience", "max_score": 9},
            "problem_identification": {"title": "Problem Identification", "max_score": 9},
            "consequence_of_not_solving": {"title": "Consequence of not solving the problem", "max_score": 9},
            "articulate_solution": {"title": "Articulate solution", "max_score": 9},
            "before_after": {"title": "Before & After", "max_score": 9},
            "key_benefits": {"title": "Key benefits & Differentiation", "max_score": 9},
            "market_opportunity": {"title": "Market Opportunity", "max_score": 9},
            "competitive_advantage": {"title": "Competitive Advantage", "max_score": 9},
            "customer_adoption": {"title": "Customer Adoption Potential", "max_score": 9},
            "success_metrics": {"title": "Success Metrics & Goals", "max_score": 9},
            "feasibility": {"title": "Feasibility", "max_score": 10} # Last section has max_score 10
        }

        step_map = {
            "target_audience": 1,
            "problem_identification": 2,
            "consequence_of_not_solving": 3,
            "articulate_solution": 4,
            "before_after": 5,
            "key_benefits": 6,
            "market_opportunity": 7,
            "competitive_advantage": 8,
            "customer_adoption": 9,
            "success_metrics": 10,
            "feasibility": 11,
        }

        # Build section payloads (sync DB reads - session not safe for concurrent access)
        section_payloads = []
        for section_key, section_info in sections.items():
            step_num = step_map[section_key]
            section_questions = db.query(Questionnaire).filter(
                Questionnaire.q_uuid.startswith(f"step_{step_num}_")
            ).all()
            section_answers = [
                a for a in answers
                if a.question_id in [q.id for q in section_questions]
            ]
            section_payloads.append(
                (section_key, section_info, section_questions, section_answers)
            )

        async def analyze_section(
            section_key: str,
            section_info: dict,
            question_texts: list,
            answer_values: list,
        ):
            try:
                analysis = await LLMService.generate_section_analysis(
                    section_info["title"],
                    answer_values,
                    question_texts,
                    section_info["max_score"],
                )
                return {
                    "section": section_info["title"],
                    "score": analysis["score"],
                    "max_score": section_info["max_score"],
                    "weighted_score": section_info["max_score"],
                    "insight": analysis["insight"],
                    "recommendations": analysis["recommendations"],
                }
            except Exception as e:
                logger.error(
                    "Error analyzing section %s: %s",
                    section_key,
                    e,
                    exc_info=True,
                )
                return None

        tasks = [
            analyze_section(
                sk,
                si,
                [q.text for q in sq],
                [a.answer for a in sa],
            )
            for sk, si, sq, sa in section_payloads
        ]
        raw_results = await asyncio.gather(*tasks, return_exceptions=False)
        section_analyses = [r for r in raw_results if r is not None]
        total_score = sum(s["score"] for s in section_analyses)

        # Generate strategic overview
        strategic_analysis = await LLMService.generate_strategic_overview(
            idea.idea_name,
            section_analyses
        )

        # Save the report data
        report.content = {
            "idea_name": idea.idea_name,
            "overall_score": total_score,
            "report_overview": strategic_analysis["overview"],
            "sections": [
                {
                    "category": analysis["section"],
                    "score": analysis["score"],
                    "max_score": analysis["max_score"], # Include max_score for PDF generation
                    "weighted_score": analysis["weighted_score"], # Use the weighted_score we set earlier (equal to max_score)
                    "insight": analysis["insight"],
                    "recommendations": analysis["recommendations"]
                }
                for analysis in section_analyses
            ],
            "strategic_next_steps": strategic_analysis["strategic_next_steps"]
        }
        report.status = REPORT_STATUS_COMPLETED
        report.updated_at = datetime.utcnow()
        db.commit()

    except Exception as e:
        logger.exception("Report generation failed for report_id=%s: %s", report_id, e)
        try:
            report = db.query(Report).filter(Report.id == report_id).first()
            if report:
                report.status = REPORT_STATUS_FAILED
                report.error_message = "Report generation failed"
                report.updated_at = datetime.utcnow()
                db.commit()
        except Exception as commit_err:
            logger.error(
                "Failed to persist report failure state: %s",
                commit_err,
                exc_info=True,
            )
    finally:
        db.close()

# Simple test endpoint for LLM
@router.get("/test-llm")
async def test_llm_connection():
    """Test if the LLM connection (GLM or Vultr) is working properly"""
    if ENVIRONMENT == "production":
        raise HTTPException(status_code=404, detail="Not found")
    try:
        api_key = os.getenv("GLM_API_KEY") or os.getenv("VULTR_API_KEY")
        if not api_key:
            return {
                "status": "error",
                "message": "No LLM API key found. Set GLM_API_KEY or VULTR_API_KEY in .env",
                "hint": "Add GLM_API_KEY (for GLM Coding Plan) or VULTR_API_KEY (for Vultr) to your .env file"
            }

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

        overview_text = result.get("overview", "").lower()

        has_known_error_in_overview = (
            overview_text == f"{PROVIDER_NAME.lower()} api key not configured."
            or overview_text.startswith(f"{PROVIDER_NAME.lower()} api http error")
            or overview_text.startswith(f"{PROVIDER_NAME.lower()} api request error")
            or overview_text == "unable to generate strategic overview due to an api error."
            or overview_text == "unable to generate strategic overview due to a processing error."
        )

        is_successful_llm_response = (
            result
            and "error" not in result
            and result.get("overview")
            and not has_known_error_in_overview
            and len(result.get("strategic_next_steps", [])) > 0
        )

        if is_successful_llm_response:
            return {
                "status": "success",
                "message": f"{PROVIDER_NAME} LLM connection is working correctly and generated a valid response.",
                "sample_response": result,
                "model_used": ACTIVE_CHAT_MODEL,
                "provider": PROVIDER_NAME
            }
        else:
            return {
                "status": "error",
                "message": f"{PROVIDER_NAME} LLM API call was made, but returned an error or an unexpected/fallback response.",
                "response": result,
                "hint": f"Check your API key, {PROVIDER_NAME} account status, model ID ('{ACTIVE_CHAT_MODEL}'), and API status. Error 422 often means the request data was unprocessable."
            }
    except Exception as e:
        return {
            "status": "error",
            "message": "LLM connection test failed with an unexpected exception."
        }
