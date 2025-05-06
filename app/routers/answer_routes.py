from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.auth import get_current_user  # Assuming you're using auth to get the current user
from app.models import Answer, User
from app import schemas
from app.database import get_db
from typing import Dict, Any, List
import json
from datetime import datetime

router = APIRouter()

# Route to save an answer (POST /answers)
@router.post("/answers", response_model=schemas.AnswerResponse)
async def save_answer(
    answer: schemas.AnswerCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        # Check if an answer already exists for the same question_id and ideaBoard_id
        existing_answer = db.query(Answer).filter(
            Answer.question_id == answer.question_id,
            Answer.ideaBoard_id == answer.ideaBoard_id
        ).first()

        if existing_answer:
            # Handle cases where the answer is not a list
            if isinstance(existing_answer.answer, dict):
                # Convert existing dictionary to a list
                existing_answer_data = [existing_answer.answer]
            elif isinstance(existing_answer.answer, list):
                existing_answer_data = existing_answer.answer
            else:
                # If it's neither, raise an error
                raise HTTPException(status_code=400, detail="Existing answer format is invalid")

            # Append the new answer to the existing data
            new_answer_data = answer.answer  # This is already in JSON format
            existing_answer_data.append(new_answer_data)

            # Update the record in the database
            existing_answer.answer = existing_answer_data  # Directly assign the updated list
            existing_answer.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(existing_answer)
            return existing_answer
        else:
            # If no existing answer is found, create a new one
            db_answer = Answer(
                **answer.dict(),
                user_id=current_user.id,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.add(db_answer)
            db.commit()
            db.refresh(db_answer)
            return db_answer
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail="Database error: Unable to save answer") from e

# Route to get all answers or by question ID (GET /answers)
@router.get("/answers", response_model=List[schemas.AnswerPublic])
async def get_answers(question_id: int = None, 
                db: Session = Depends(get_db),
                current_user: User = Depends(get_current_user)):
    # If question_id is provided, filter by it; otherwise, get all answers
    if question_id:
        answers = db.query(Answer).filter(Answer.question_id == question_id).all()
    else:
        answers = db.query(Answer).all()

    if not answers:
        raise HTTPException(status_code=404, detail="No answers found")

    return answers
