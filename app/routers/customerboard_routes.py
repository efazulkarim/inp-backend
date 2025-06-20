from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime
from app.auth import get_current_user
from app.models import CustomerPersona, User, IdeaBoard, CustomerPersonaQuestionnaire, IdeaPersonaLink
from app import schemas
from app.database import get_db
import json

router = APIRouter()

@router.post("/personas/debug")
async def debug_create_persona(
    persona_data: Dict[str, Any],
    current_user: User = Depends(get_current_user)
):
    """Debug endpoint to see what data is being sent"""
    try:
        # Try to parse it as CustomerPersonaCreate
        persona = schemas.CustomerPersonaCreate(**persona_data)
        return {
            "status": "success",
            "message": "Data is valid",
            "parsed_data": persona.dict()
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "received_data": persona_data,
            "expected_fields": {
                "required": ["persona_name"],
                "optional": [
                    "tag", "age_range", "gender_identity", "education_level",
                    "location_region", "role_occupation", "company_size", "industry_types",
                    "annual_income", "work_styles", "tech_proficiency", "goals", "challenges",
                    "tools_used", "info_sources", "decision_factors", "emotions", "motivations",
                    "user_journey_stage", "pain_points", "preferred_features",
                    "preferred_communication_channels"
                ],
                "list_fields": [
                    "industry_types", "work_styles", "goals", "challenges", "tools_used",
                    "info_sources", "decision_factors", "emotions", "motivations",
                    "pain_points", "preferred_features", "preferred_communication_channels"
                ],
                "integer_fields": ["tech_proficiency (0-10)"]
            }
        }

@router.post("/personas/test-minimal")
async def test_minimal_persona(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Test creating a persona with minimal data"""
    try:
        # Create with only required field
        db_persona = CustomerPersona(
            user_id=current_user.id,
            persona_name="Test Persona",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        db.add(db_persona)
        db.commit()
        db.refresh(db_persona)
        
        # Convert to response format
        return {
            "status": "success",
            "message": "Minimal persona created successfully",
            "persona": {
                "id": db_persona.id,
                "persona_name": db_persona.persona_name,
                "user_id": db_persona.user_id,
                "created_at": db_persona.created_at,
                "updated_at": db_persona.updated_at
            }
        }
    except Exception as e:
        db.rollback()
        return {
            "status": "error",
            "message": f"Error creating minimal persona: {str(e)}"
        }

@router.post("/personas", response_model=schemas.CustomerPersonaResponse)
async def create_persona(
    persona: schemas.CustomerPersonaCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new customer persona"""
    
    try:
        # Validate the data
        persona_dict = persona.dict()
        
        # Create new persona with all 8 sections and new field names
        db_persona = CustomerPersona(
            user_id=current_user.id,
            persona_name=persona.persona_name,
            tag=persona.tag,
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
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        # Log the actual error for debugging
        print(f"Error creating persona: {str(e)}")
        print(f"Persona data: {persona.dict()}")
        raise HTTPException(
            status_code=422,
            detail=f"Error creating persona: {str(e)}. Please check that all fields are in the correct format."
        )

@router.get("/personas", response_model=List[schemas.CustomerPersonaResponse])
async def get_all_personas(
    skip: int = 0, 
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all customer personas for the current user"""
    
    query = db.query(CustomerPersona).filter(CustomerPersona.user_id == current_user.id)
    
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
    
    # Get all personas linked to this idea through IdeaPersonaLink
    persona_links = db.query(IdeaPersonaLink).filter(
        IdeaPersonaLink.idea_id == idea_id
    ).all()
    
    personas = []
    for link in persona_links:
        persona = db.query(CustomerPersona).filter(
            CustomerPersona.id == link.persona_id
        ).first()
        if persona:
            personas.append(persona)
    
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