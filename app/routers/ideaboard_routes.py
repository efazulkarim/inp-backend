from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from app.auth import get_current_user
from app.models import IdeaBoard, User, Questionnaire, Answer
from app import schemas
from app.database import get_db

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
        
        db.commit()
        return {"message": "Answers saved successfully", "step": step, "idea_id": idea_id}
    
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
    
    # Get all answers for this idea
    answers = db.query(Answer).filter(
        Answer.ideaBoard_id == idea_id,
        Answer.user_id == current_user.id
    ).all()
    
    # Group answers by step
    progress = {}
    total_score = 0
    
    for answer in answers:
        question = db.query(Questionnaire).filter(Questionnaire.id == answer.question_id).first()
        if question:
            step = int(question.q_uuid.split("_")[1])  # Extract step number from q_uuid
            if step not in progress:
                progress[step] = {"completed": True, "score": 0}
            # Calculate score based on answers (implement your scoring logic here)
            # progress[step]["score"] += calculate_score(answer.answer)
    
    return {
        "idea_id": idea_id,
        "total_steps": 11,
        "completed_steps": list(progress.keys()),
        "total_score": total_score,
        "progress": progress
    }

@router.get("/all-ideas/", response_model=List[schemas.IdeaResponse])
async def get_all_ideas(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all ideas for the current user"""
    ideas = db.query(IdeaBoard).filter(IdeaBoard.user_id == current_user.id).all()
    if not ideas:
        raise HTTPException(status_code=404, detail="No ideas found for this user")
    return ideas
