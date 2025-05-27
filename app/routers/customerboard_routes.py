from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from app.auth import get_current_user
from app.models import CustomerPersona, User, IdeaBoard, CustomerPersonaQuestionnaire
from app import schemas
from app.database import get_db
import json

router = APIRouter()

@router.post("/personas", response_model=schemas.CustomerPersonaResponse)
async def create_persona(
    persona: schemas.CustomerPersonaCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new customer persona"""
    
    # If an idea_id is provided, verify it belongs to the user
    if persona.idea_id:
        idea = db.query(IdeaBoard).filter(
            IdeaBoard.id == persona.idea_id,
            IdeaBoard.user_id == current_user.id
        ).first()
        
        if not idea:
            raise HTTPException(status_code=404, detail="Idea not found or not owned by the current user")
    
    # Create new persona with all 8 sections and new field names
    db_persona = CustomerPersona(
        user_id=current_user.id,
        persona_name=persona.persona_name,
        tag=persona.tag,
        idea_id=persona.idea_id,
        # 1. Personal Information
        age_range=persona.age_range,
        gender_identity=persona.gender_identity,
        education_level=persona.education_level,
        location_region=persona.location_region,
        # 2. Professional Information
        role_occupation=persona.role_occupation,
        company_size=persona.company_size,
        industry_types=persona.industry_types,
        annual_income=persona.annual_income,
        work_styles=persona.work_styles,
        tech_proficiency=persona.tech_proficiency,
        # 3. Goals & Challenges
        goals=persona.goals,
        challenges=persona.challenges,
        # 4. Behavior and Decision-Making
        tools_used=persona.tools_used,
        info_sources=persona.info_sources,
        decision_factors=persona.decision_factors,
        # 5. Emotional Triggers and Motivations
        emotions=persona.emotions,
        motivations=persona.motivations,
        # 6. User Journey
        user_journey_stage=persona.user_journey_stage,
        # 7. Pain Points
        pain_points=persona.pain_points,
        # 8. Preferred Features & Communication
        preferred_features=persona.preferred_features,
        preferred_communication_channels=persona.preferred_communication_channels,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    db.add(db_persona)
    db.commit()
    db.refresh(db_persona)
    return db_persona

@router.get("/personas", response_model=List[schemas.CustomerPersonaResponse])
async def get_all_personas(
    idea_id: Optional[int] = None,
    skip: int = 0, 
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all customer personas for the current user"""
    
    query = db.query(CustomerPersona).filter(CustomerPersona.user_id == current_user.id)
    
    if idea_id:
        query = query.filter(CustomerPersona.idea_id == idea_id)
        
    personas = query.offset(skip).limit(limit).all()
    return personas

@router.get("/personas/{persona_id}", response_model=schemas.CustomerPersonaResponse)
async def get_persona(
    persona_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific customer persona by ID"""
    
    persona = db.query(CustomerPersona).filter(
        CustomerPersona.id == persona_id,
        CustomerPersona.user_id == current_user.id
    ).first()
    
    if not persona:
        raise HTTPException(status_code=404, detail="Customer persona not found")
        
    return persona

@router.put("/personas/{persona_id}", response_model=schemas.CustomerPersonaResponse)
async def update_persona(
    persona_id: int,
    persona_update: schemas.CustomerPersonaUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a customer persona"""
    
    # Find the persona
    db_persona = db.query(CustomerPersona).filter(
        CustomerPersona.id == persona_id,
        CustomerPersona.user_id == current_user.id
    ).first()
    
    if not db_persona:
        raise HTTPException(status_code=404, detail="Customer persona not found")
    
    # If idea_id is provided, verify it belongs to the user
    if persona_update.idea_id:
        idea = db.query(IdeaBoard).filter(
            IdeaBoard.id == persona_update.idea_id,
            IdeaBoard.user_id == current_user.id
        ).first()
        
        if not idea:
            raise HTTPException(status_code=404, detail="Idea not found or not owned by the current user")
    
    # Update persona with values from persona_update if they're not None, using new field names
    update_data = persona_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        if value is not None:
            setattr(db_persona, key, value)
    
    db_persona.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(db_persona)
    
    return db_persona

@router.delete("/personas/{persona_id}", response_model=schemas.MessageResponse)
async def delete_persona(
    persona_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a customer persona"""
    
    # Find the persona
    db_persona = db.query(CustomerPersona).filter(
        CustomerPersona.id == persona_id,
        CustomerPersona.user_id == current_user.id
    ).first()
    
    if not db_persona:
        raise HTTPException(status_code=404, detail="Customer persona not found")
    
    # Delete the persona
    db.delete(db_persona)
    db.commit()
    
    return {"msg": "Customer persona deleted successfully"}

@router.get("/personas/idea/{idea_id}", response_model=List[schemas.CustomerPersonaResponse])
async def get_personas_by_idea(
    idea_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all customer personas associated with a specific idea"""
    
    # Verify idea belongs to user
    idea = db.query(IdeaBoard).filter(
        IdeaBoard.id == idea_id,
        IdeaBoard.user_id == current_user.id
    ).first()
    
    if not idea:
        raise HTTPException(status_code=404, detail="Idea not found or not owned by the current user")
    
    # Get all personas for this idea
    personas = db.query(CustomerPersona).filter(
        CustomerPersona.idea_id == idea_id,
        CustomerPersona.user_id == current_user.id
    ).all()
    
    return personas

@router.get("/customerboard/questions", response_model=List[schemas.CustomerPersonaQuestionnaireResponse])
async def get_customerboard_questions(
    db: Session = Depends(get_db),
):
    """Get all customerboard (persona) questions"""
    questions = db.query(CustomerPersonaQuestionnaire).filter(CustomerPersonaQuestionnaire.status == 1).all()
    result = []
    for q in questions:
        options = None
        if q.range:
            try:
                options = json.loads(q.range)
                if not isinstance(options, list):
                    print(f"Invalid range for q_uuid {q.q_uuid}: {options}")
                    options = None
            except Exception as e:
                print(f"Error parsing range for q_uuid {q.q_uuid}: {e}")
                options = None
        input_type = q.input_type
        if input_type == "multiple_choice":
            input_type = "checkbox-group"
        elif input_type == "single_choice":
            input_type = "radio-group"
        result.append({
            "q_uuid": q.q_uuid,
            "text": q.text,
            "input_type": input_type,
            "range": options,
            "category": q.category,
            "id": q.id,
            "body": q.body,
            "remarks": q.remarks,
            "status": q.status,
            "created_at": q.created_at,
            "updated_at": q.updated_at
        })
    return result 