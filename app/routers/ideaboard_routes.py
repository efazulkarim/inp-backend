from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional, Dict
from datetime import datetime
from app.auth import get_current_user
from app.models import IdeaBoard, User, Questionnaire, Answer
from app import schemas
from app.database import get_db
import json

router = APIRouter()

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
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error creating idea: {str(e)}")

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
        Questionnaire.q_uuid.startswith(f"step_{step}_")
    ).all()
    
    if not questions:
        raise HTTPException(status_code=404, detail=f"No questions found for step {step}")
    
    return {"step": step, "questions": questions}

@router.post("/answers/{idea_id}/{step}", response_model=schemas.AnswerResponse)
async def save_step_answers(
    idea_id: int,
    step: int,
    answers: schemas.AnswerCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Save answers for a specific step"""
    # Verify idea belongs to user
    idea = db.query(IdeaBoard).filter(
        IdeaBoard.id == idea_id,
        IdeaBoard.user_id == current_user.id
    ).first()
    
    if not idea:
        raise HTTPException(status_code=404, detail="Idea not found")
    
    try:
        # Save each answer
        for question_id, answer_data in answers.answers.items():
            existing_answer = db.query(Answer).filter(
                Answer.question_id == question_id,
                Answer.ideaBoard_id == idea_id,
                Answer.user_id == current_user.id
            ).first()
            
            if existing_answer:
                existing_answer.answer = answer_data
                existing_answer.updated_at = datetime.utcnow()
            else:
                new_answer = Answer(
                    question_id=question_id,
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
    
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Error saving answers: {str(e)}")

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
        # Get questions for this step to map IDs to database questions
        questions = db.query(Questionnaire).filter(
            Questionnaire.status == 1,
            Questionnaire.q_uuid.startswith(f"step_{step}_")
        ).all()
        
        # Create a mapping of question identifiers to DB IDs
        question_map = {q.q_uuid.split('_')[-1]: q.id for q in questions}
        
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
    
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Error saving answers: {str(e)}")

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
        Questionnaire.q_uuid.startswith(f"step_{step}_")
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
        # Assuming format: step_1_question_id
        try:
            parts = q.q_uuid.split('_')
            question_id = parts[-1]
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
