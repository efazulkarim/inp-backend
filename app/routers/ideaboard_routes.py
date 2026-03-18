import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional, Dict
from datetime import datetime
from app.auth import get_current_user
from app.models import IdeaBoard, User, Questionnaire, Answer, CustomerPersona, IdeaPersonaLink
from app import schemas
from app.database import get_db
import json

router = APIRouter()
logger = logging.getLogger(__name__)

QUESTION_ID_PREFIX_TEMPLATE = "step_{step}_"


def _extract_step_question_id(q_uuid: str, step: int) -> str:
    """
    Extract stable question ID from q_uuid without breaking IDs containing underscores.
    Example: step_2_main_problem -> main_problem
    """
    prefix = QUESTION_ID_PREFIX_TEMPLATE.format(step=step)
    base_id = q_uuid[len(prefix):] if q_uuid.startswith(prefix) else q_uuid.split("_")[-1]
    
    mapping = {
        "audience_characteristics": "characteristics",
        "customer_personas": "customer_personas_created",
        "problem_description": "problem_description_type",
        "customer_solutions": "current_solutions_type",
        "validated_problem": "problem_validated",
        "validation_description": "validation_method",
        "market_demand_drivers": "driving_demand",
        "swot_product": "swot_your_product",
        "willing_to_pay": "willingness_to_pay",
        "tracking_metrics": "measure_metrics",
        "progress_milestones": "milestones",
        "profitable_solution": "profitability",
        "consequences": "consequences_of_not_solving",
        "urgency": "problem_urgency",
        "costs": "financial_emotional_costs",
        "product_service": "product_service_offering",
        "before_product_use": "customer_life_before",
        "after_product_use": "customer_life_after",
        "solution_solves_problem": "how_solution_solves_problem",
        "better_than_alternatives": "why_solution_better",
        "emotional_benefits": "emotional_psychological_benefits",
        "right_time_introduction": "timing_introduction",
        "other_primary_benefits_text": "other_primary_benefit_specify",
        "other_emotional_benefits_text": "other_emotional_benefit_specify",
        "other_market_demand_text": "other_driving_demand_specify",
    }
    reverse_mapping = {v: k for k, v in mapping.items()}
    return reverse_mapping.get(base_id, base_id)

@router.post("/create-idea/", response_model=schemas.IdeaResponse)
async def create_idea(
    idea: schemas.IdeaCreate, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    """Create a new idea and start the questionnaire process"""
    try:
        new_idea = IdeaBoard(
            idea_name=idea.idea_name,
            idea_description=idea.idea_description,
            user_id=current_user.id,
            pin=idea.pin
        )
        db.add(new_idea)
        db.commit()
        db.refresh(new_idea)
        return new_idea
    except Exception:
        raise HTTPException(status_code=400, detail="Error creating idea")

@router.get("/questions/{step}", response_model=schemas.QuestionnaireResponse)
async def get_step_questions(
    step: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get questions for a specific step (1-11)"""
    if not 1 <= step <= 11:
        raise HTTPException(status_code=400, detail="Invalid step number")
    
    questions = db.query(Questionnaire).filter(
        Questionnaire.status == 1,
        Questionnaire.q_uuid.like(f"step\\_{step}\\_%", escape="\\")
    ).all()
    
    if not questions:
        raise HTTPException(status_code=404, detail=f"No questions found for step {step}")
    
    return {"step": step, "questions": questions}


    

@router.post("/steps/{idea_id}/{step}", response_model=schemas.AnswerResponse)
async def save_step_data(
    idea_id: int,
    step: int,
    step_data: schemas.StepDataCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Save answers for a specific step using improved format"""
    # Verify idea belongs to user
    idea = db.query(IdeaBoard).filter(
        IdeaBoard.id == idea_id,
        IdeaBoard.user_id == current_user.id
    ).first()
    
    if not idea:
        raise HTTPException(status_code=404, detail="Idea not found")
    
    try:
        if step_data.step_number != step:
            raise HTTPException(
                status_code=400,
                detail=f"step_number ({step_data.step_number}) must match URL step ({step})",
            )

        # Get questions for this step to map IDs to database questions
        questions = db.query(Questionnaire).filter(
            Questionnaire.status == 1,
            Questionnaire.q_uuid.like(f"step\\_{step}\\_%", escape="\\")
        ).all()

        if not questions:
            raise HTTPException(status_code=404, detail=f"No questions found for step {step}")
        
        # Create a mapping of question identifiers to DB IDs
        question_map = {_extract_step_question_id(q.q_uuid, step): q.id for q in questions}
        allowed_question_ids = set(question_map.keys())

        submitted_question_ids = [q.id for q in step_data.questions]
        unknown_question_ids = [qid for qid in submitted_question_ids if qid not in allowed_question_ids]
        if unknown_question_ids:
            # Just ignore unknown question IDs from frontend (e.g. 'other' text fields not strictly in DB)
            print(f"Warning: Ignoring unknown question IDs for step {step}: {unknown_question_ids}")
        
        # Save each answer
        for question in step_data.questions:
            if question.id in question_map:
                db_question_id = question_map[question.id]
                
                existing_answer = db.query(Answer).filter(
                    Answer.question_id == db_question_id,
                    Answer.ideaBoard_id == idea_id,
                    Answer.user_id == current_user.id
                ).first()
                
                answer_data = {
                    "type": question.type,
                    "value": question.value
                }
                
                if existing_answer:
                    existing_answer.answer = answer_data
                    existing_answer.updated_at = datetime.utcnow()
                else:
                    new_answer = Answer(
                        question_id=db_question_id,
                        ideaBoard_id=idea_id,
                        user_id=current_user.id,
                        answer=answer_data,
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow()
                    )
                    db.add(new_answer)
        
        # Update progress tracking
        if not idea.completed_steps:
            idea.completed_steps = []
            
        # Add this step to completed_steps if not already there
        if step not in idea.completed_steps:
            completed_steps = idea.completed_steps.copy() if idea.completed_steps else []
            completed_steps.append(step)
            idea.completed_steps = completed_steps
        
        # Update current_step to next step if this is the highest step completed
        if step >= (idea.current_step or 0):
            idea.current_step = step + 1
        
        # If this is the final step (step 11), mark as complete
        if step == 11:
            idea.is_complete = True
        
        db.commit()
        return {
            "message": "Answers saved successfully", 
            "step": step, 
            "idea_id": idea_id,
            "current_step": idea.current_step,
            "is_complete": idea.is_complete
        }
    
    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        logger.exception("Failed saving ideaboard step %s for idea %s: %s", step, idea_id, exc)
        raise HTTPException(status_code=400, detail="Error saving answers")

@router.get("/progress/{idea_id}", response_model=schemas.IdeaProgressResponse)
async def get_idea_progress(
    idea_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get the progress of an idea's questionnaire"""
    # Verify idea belongs to user
    idea = db.query(IdeaBoard).filter(
        IdeaBoard.id == idea_id,
        IdeaBoard.user_id == current_user.id
    ).first()
    
    if not idea:
        raise HTTPException(status_code=404, detail="Idea not found")
    
    # Format response according to updated schema
    return {
        "idea_id": idea_id,
        "current_step": idea.current_step or 0,
        "is_complete": idea.is_complete or False,
        "completed_steps": idea.completed_steps or [],
        "total_steps": 11
    }
    

@router.get("/all-ideas/", response_model=List[schemas.IdeaResponse])
async def get_all_ideas(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all ideas for the current user"""
    ideas = db.query(IdeaBoard).filter(IdeaBoard.user_id == current_user.id).all()
    return ideas  # The schemas.IdeaResponse should include current_step, is_complete fields

# New endpoint with improved format
@router.get("/steps/{step}", response_model=schemas.StepQuestionsResponse)
async def get_step_data(
    step: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get questions for a specific step in frontend-friendly format"""
    if not 1 <= step <= 11:
        raise HTTPException(status_code=400, detail="Invalid step number")
    
    questions = db.query(Questionnaire).filter(
        Questionnaire.status == 1,
        Questionnaire.q_uuid.like(f"step\\_{step}\\_%", escape="\\")
    ).all()
    
    if not questions:
        raise HTTPException(status_code=404, detail=f"No questions found for step {step}")
    
    # Step titles mapping
    step_titles = {
        1: "Target Audience",
        2: "Problem Identification",
        3: "Consequence of not solving the problem",
        4: "Articulate solution",
        5: "Before & After",
        6: "Key benefits & Differentiation",
        7: "Market Opportunity",
        8: "Competitive Advantage",
        9: "Customer Adoption Potential",
        10: "Success Metrics & Goals",
        11: "Feasibility"
    }
    
    # Step descriptions mapping
    step_descriptions = {
        1: "Knowing who you are building for is the foundation of your business. Let's identify your ideal customer.",
        2: "The best businesses solve real problems. Let's define the problem you're solving.",
        # Add descriptions for other steps
    }
    
    # Process questions into frontend-friendly format
    question_details = []
    for q in questions:
        # Extract the question ID from the q_uuid
        # Format: step_{step}_{question_id}
        try:
            question_id = _extract_step_question_id(q.q_uuid, step)
        except:
            question_id = f"q_{q.id}"
            
        # Parse range field if it contains options
        options = None
        if q.range:
            try:
                options_data = json.loads(q.range)
                if isinstance(options_data, list):
                    options = options_data
                elif isinstance(options_data, dict) and "options" in options_data:
                    options = options_data["options"]
            except:
                # If range is not valid JSON, ignore it
                pass
                
        question_type = "text"
        if q.input_type:
            if q.input_type.lower() in ["checkbox", "multiple"]:
                question_type = "multiple_choice"
            elif q.input_type.lower() in ["radio", "single"]:
                question_type = "single_choice"
                
        question_details.append(
            schemas.QuestionDetail(
                id=question_id,
                question_text=q.text,
                description=q.body if q.body else None,
                question_type=question_type,
                options=options
            )
        )
    
    return schemas.StepQuestionsResponse(
        step_number=step,
        title=step_titles.get(step, f"Step {step}"),
        description=step_descriptions.get(step),
        questions=question_details
    )

@router.post("/ideas/{idea_id}/link-persona", response_model=schemas.PersonaLinkResponse)
async def link_persona_to_idea(
    idea_id: int,
    persona_link: schemas.PersonaLinkCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Link an existing customer persona to an idea"""
    # Verify idea belongs to user
    idea = db.query(IdeaBoard).filter(
        IdeaBoard.id == idea_id,
        IdeaBoard.user_id == current_user.id
    ).first()
    
    if not idea:
        raise HTTPException(status_code=404, detail="Idea not found")
    
    # Verify persona belongs to user
    persona = db.query(CustomerPersona).filter(
        CustomerPersona.id == persona_link.persona_id,
        CustomerPersona.user_id == current_user.id
    ).first()
    
    if not persona:
        raise HTTPException(status_code=404, detail="Customer persona not found")
    
    try:
        # Check if link already exists
        existing_link = db.query(IdeaPersonaLink).filter(
            IdeaPersonaLink.idea_id == idea_id,
            IdeaPersonaLink.persona_id == persona_link.persona_id
        ).first()
        
        if existing_link:
            raise HTTPException(status_code=400, detail="This persona is already linked to this idea")
        
        # Create the link
        new_link = IdeaPersonaLink(
            idea_id=idea_id,
            persona_id=persona_link.persona_id,
            user_id=current_user.id
        )
        
        db.add(new_link)
        db.commit()
        db.refresh(new_link)
        
        return {
            "id": new_link.id,
            "idea_id": new_link.idea_id,
            "persona_id": new_link.persona_id,
            "persona_name": persona.persona_name,
            "created_at": new_link.created_at
        }
    except HTTPException:
        raise
    except Exception:
        # If persona linking fails (e.g., table doesn't exist), return an error
        print("Error linking persona to idea")
        raise HTTPException(status_code=500, detail="Persona linking is not available at this time")

@router.get("/ideas/{idea_id}/personas", response_model=schemas.IdeaPersonasResponse)
async def get_idea_personas(
    idea_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all customer personas linked to an idea"""
    # Verify idea belongs to user
    idea = db.query(IdeaBoard).filter(
        IdeaBoard.id == idea_id,
        IdeaBoard.user_id == current_user.id
    ).first()
    
    if not idea:
        raise HTTPException(status_code=404, detail="Idea not found")
    
    # Get all linked personas - make this optional
    personas = []
    try:
        persona_links = db.query(IdeaPersonaLink).filter(
            IdeaPersonaLink.idea_id == idea_id
        ).all()
        
        for link in persona_links:
            persona = db.query(CustomerPersona).filter(
                CustomerPersona.id == link.persona_id
            ).first()
            if persona:
                personas.append(persona)
    except Exception:
        # If persona linking fails (e.g., table doesn't exist), return empty list
        print(f"Warning: Could not load linked personas for idea {idea_id}")
        personas = []
    
    return {
        "idea_id": idea_id,
        "personas": personas
    }

@router.delete("/ideas/{idea_id}/personas/{persona_id}")
async def unlink_persona_from_idea(
    idea_id: int,
    persona_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Remove a persona link from an idea"""
    # Verify idea belongs to user
    idea = db.query(IdeaBoard).filter(
        IdeaBoard.id == idea_id,
        IdeaBoard.user_id == current_user.id
    ).first()
    
    if not idea:
        raise HTTPException(status_code=404, detail="Idea not found")
    
    try:
        # Find and delete the link
        link = db.query(IdeaPersonaLink).filter(
            IdeaPersonaLink.idea_id == idea_id,
            IdeaPersonaLink.persona_id == persona_id,
            IdeaPersonaLink.user_id == current_user.id
        ).first()
        
        if not link:
            raise HTTPException(status_code=404, detail="Persona link not found")
        
        db.delete(link)
        db.commit()
        
        return {"message": "Persona unlinked successfully"}
    except HTTPException:
        raise
    except Exception:
        # If persona unlinking fails (e.g., table doesn't exist), return an error
        print("Error unlinking persona from idea")
        raise HTTPException(status_code=500, detail="Persona unlinking is not available at this time")
