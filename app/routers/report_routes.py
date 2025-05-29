from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Response
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from app.auth import get_current_user
from app.models import Answer, User, IdeaBoard, Questionnaire, Report
from app import schemas
from app.database import get_db, SessionLocal
from datetime import datetime
import json
import os
import tempfile
from app.services.llm_service import LLMService, VULTR_CHAT_MODEL
from app.services.pdf_service import generate_report_pdf

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
        # If report exists and is not stale, return its status
        if existing_report.status == "completed":
            return {
                "report_id": existing_report.id,
                "status": "completed",
                "message": "Report already exists"
            }
        elif existing_report.status == "processing":
            # Check if it's a stale request (more than 5 minutes old)
            if (datetime.utcnow() - existing_report.updated_at).total_seconds() > 300:
                existing_report.status = "queued"  # Reset stale request
                db.commit()
            
            return {
                "report_id": existing_report.id,
                "status": existing_report.status,
                "message": "Report generation in progress" 
            }
    
    # Create a new report record or update existing one
    if existing_report:
        report = existing_report
        report.status = "queued"
        report.updated_at = datetime.utcnow()
    else:
        report = Report(
            idea_id=idea_id,
            user_id=current_user.id,
            status="queued",
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
        "status": "queued",
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
    
    # Check if report exists and is completed
    report = db.query(Report).filter(
        Report.idea_id == idea_id,
        Report.status == "completed"
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
    
    # Get the report
    report = db.query(Report).filter(
        Report.idea_id == idea_id,
        Report.status == "completed"
    ).first()
    
    if not report or not report.content:
        raise HTTPException(status_code=404, detail="Report not found or incomplete")
    
    # Generate PDF
    pdf_path = await generate_report_pdf(report.content, idea.idea_name)
    
    # Return the PDF file
    return FileResponse(
        path=pdf_path,
        filename=f"{idea.idea_name.replace(' ', '_')}_Report.pdf",
        media_type="application/pdf"
    )

# Background task function
async def generate_report_background(report_id: int, idea_id: int, user_id: int):
    """Background task to generate a report"""
    db = SessionLocal()
    try:
        # Update report status to processing
        report = db.query(Report).filter(Report.id == report_id).first()
        if not report:
            return
        report.status = "processing"
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
            report.status = "failed"
            report.error_message = "No answers found for this idea"
            db.commit()
            return

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
            try:
                analysis = await LLMService.generate_section_analysis(
                    section_info["title"],
                    [a.answer for a in section_answers],
                    [q.text for q in section_questions],
                    section_info["max_score"] # Pass max_score for the section
                )
                section_analyses.append({
                    "section": section_info["title"],
                    "score": analysis["score"],
                    "max_score": section_info["max_score"], # Store max_score
                    "insight": analysis["insight"],
                    "recommendations": analysis["recommendations"]
                })
                total_score += analysis["score"]
            except Exception as e:
                # Log the error but continue with other sections
                print(f"Error analyzing section {section_key}: {str(e)}")

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
                    "weighted_score": analysis["score"], # Placeholder for weighted_score, consider if actual weighting is needed
                    "insight": analysis["insight"],
                    "recommendations": analysis["recommendations"]
                }
                for analysis in section_analyses
            ],
            "strategic_next_steps": strategic_analysis["strategic_next_steps"]
        }
        report.status = "completed"
        report.updated_at = datetime.utcnow()
        db.commit()

    except Exception as e:
        # If any error occurs, mark report as failed
        try:
            report = db.query(Report).filter(Report.id == report_id).first()
            if report:
                report.status = "failed"
                report.error_message = str(e)
                report.updated_at = datetime.utcnow()
                db.commit()
        except:
            pass
        print(f"Error generating report: {str(e)}")
    finally:
        db.close()

# Simple test endpoint for LLM
@router.get("/test-llm")
async def test_llm_connection():
    """Test if the LLM connection (now Vultr) is working properly"""
    try:
        api_key = os.getenv("VULTR_API_KEY")
        if not api_key:
            return {
                "status": "error",
                "message": "VULTR_API_KEY environment variable not found or empty",
                "hint": "Make sure to add VULTR_API_KEY to your .env file or environment variables"
            }
            
        result = await LLMService.generate_strategic_overview(
            "Test Product for Vultr",
            [
                {
                    "section": "Test Section for Vultr",
                    "score": 10,
                    "insight": "This is a test insight for Vultr.",
                    "recommendations": ["Vultr test recommendation 1", "Vultr test recommendation 2"]
                }
            ]
        )
        
        overview_text = result.get("overview", "").lower() # Get overview safely and lowercase it

        # More explicit check for error indicators in the overview
        has_known_error_in_overview = (
            overview_text == "vultr api key not configured."
            or overview_text.startswith("vultr api http error") 
            or overview_text.startswith("vultr api request error")
            or overview_text == "unable to generate strategic overview due to an api error."
            or overview_text == "unable to generate strategic overview due to a processing error."
        )

        is_successful_llm_response = (
            result 
            and "error" not in result # No explicit 'error' key from our _make_vultr_request helper
            and result.get("overview") # Overview field must exist
            and not has_known_error_in_overview
            and len(result.get("strategic_next_steps", [])) > 0 # Heuristic for actual content
        )

        if is_successful_llm_response:
            return {
                "status": "success",
                "message": "Vultr LLM connection is working correctly and generated a valid response.",
                "sample_response": result,
                "model_used": VULTR_CHAT_MODEL
            }
        else:
            return {
                "status": "error",
                "message": "Vultr LLM API call was made, but returned an error or an unexpected/fallback response.",
                "response": result,
                "hint": "Check your VULTR_API_KEY, Vultr account status (billing, quotas), selected model ID ('{}'), and Vultr API status. The response above might contain more details from Vultr. Error 422 often means the request data was unprocessable (e.g. invalid model or parameters).".format(VULTR_CHAT_MODEL)
            }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Vultr LLM connection test failed with an unexpected exception: {str(e)}",
            "error_details": str(e)
        }
