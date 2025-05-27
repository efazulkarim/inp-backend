from pydantic import BaseModel, EmailStr, validator, root_validator
from typing import Optional, Dict, Any, List, Union
from datetime import datetime

# Schema for user registration
class UserBase(BaseModel):
    email: EmailStr
    username: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None

class UserCreate(UserBase):
    password: str

class UserDisplay(UserBase):
    id: int

    class Config:
        orm_mode = True

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserMe(UserBase):
    role: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None

    class Config:
        orm_mode = True

class Token(BaseModel):
    access_token: str
    token_type: str
    refresh_token: Optional[str] = None

class IdeaCreate(BaseModel):
    idea_name: str
    idea_description: Optional[str] = None
    pin: Optional[int] = None

class IdeaResponse(IdeaCreate):
    id: int
    user_id: int
    current_step: Optional[int] = 0
    is_complete: Optional[bool] = False
    completed_steps: Optional[List[int]] = []

    class Config:
        orm_mode = True

class QuestionBase(BaseModel):
    text: str
    body: Optional[str] = None
    remarks: Optional[str] = None
    input_type: str
    range: Optional[str] = None

class QuestionResponse(QuestionBase):
    id: int
    q_uuid: str
    status: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True

class QuestionnaireResponse(BaseModel):
    step: int
    questions: List[QuestionResponse]

class AnswerCreate(BaseModel):
    answers: Dict[int, Any]  # question_id -> answer_data

class AnswerResponse(BaseModel):
    message: str
    step: int
    idea_id: int
    current_step: Optional[int] = None
    is_complete: Optional[bool] = None

class AnswerPublic(BaseModel): 
    id: int
    question_id: int
    ideaBoard_id: int
    answer: Any 
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True 

class StepProgress(BaseModel):
    completed: bool
    score: int

class IdeaProgressResponse(BaseModel):
    idea_id: int
    current_step: int
    is_complete: bool
    completed_steps: List[int]
    total_steps: int

    class Config:
        orm_mode = True

class MessageResponse(BaseModel):
    msg: str

    class Config:
        orm_mode = True

class TrashSchema(BaseModel):
    id: int
    idea_name: str
    idea_description: str
    user_id: int
    deleted_at: datetime

    class Config:
        orm_mode = True

class ArchiveSchema(BaseModel):
    id: int
    idea_name: str
    idea_description: str
    user_id: int
    archived_at: datetime

    class Config:
        orm_mode = True

class ReportSection(BaseModel):
    category: str
    score: int
    weighted_score: int
    insight: str
    recommendations: List[str]

    class Config:
        orm_mode = True

class ReportResponse(BaseModel):
    idea_name: str
    overall_score: int
    report_overview: str
    sections: List[ReportSection]
    strategic_next_steps: List[str]

    class Config:
        orm_mode = True

class ForgotPassword(BaseModel):
    email: EmailStr

class ResetPassword(BaseModel):
    token: str
    new_password: str

# New schemas for improved ideaboard API
class QuestionData(BaseModel):
    id: str  # Readable ID like "age", "location"
    type: str  # "text", "multiple_choice", "single_choice"
    value: Union[str, List[str]]  # String for text/single choice, list for multiple choice

class StepDataCreate(BaseModel):
    step_number: int
    questions: List[QuestionData]

class QuestionDetail(BaseModel):
    id: str
    question_text: str
    description: Optional[str] = None
    question_type: str
    options: Optional[List[str]] = None
    
class StepQuestionsResponse(BaseModel):
    step_number: int
    title: str
    description: Optional[str] = None
    questions: List[QuestionDetail]
    
    class Config:
        orm_mode = True

# Report related schemas
class ReportRequestResponse(BaseModel):
    report_id: int
    status: str
    message: str

class ReportStatusResponse(BaseModel):
    report_id: int
    status: str
    created_at: datetime
    updated_at: datetime
    error_message: Optional[str] = None
    
    class Config:
        orm_mode = True

class ReportSectionRecommendation(BaseModel):
    title: str
    description: str
    
    class Config:
        orm_mode = True

class ReportDetailSection(BaseModel):
    category: str
    score: int
    weighted_score: int
    insight: str
    recommendations: List[str]
    
    class Config:
        orm_mode = True

class PDFExportOptions(BaseModel):
    include_charts: bool = True
    include_recommendations: bool = True
    custom_branding: Optional[str] = None

# CustomerPersona schemas
class CustomerPersonaBase(BaseModel):
    persona_name: str
    tag: Optional[str] = None
    idea_id: Optional[int] = None
    # 1. Personal Information
    age_range: Optional[str] = None
    gender_identity: Optional[str] = None
    education_level: Optional[str] = None
    location_region: Optional[str] = None
    # 2. Professional Information
    role_occupation: Optional[str] = None
    company_size: Optional[str] = None
    industry_types: Optional[List[str]] = None
    annual_income: Optional[str] = None
    work_styles: Optional[List[str]] = None
    tech_proficiency: Optional[int] = None
    # 3. Goals & Challenges
    goals: Optional[List[str]] = None
    challenges: Optional[List[str]] = None
    # 4. Behavior and Decision-Making
    tools_used: Optional[List[str]] = None
    info_sources: Optional[List[str]] = None
    decision_factors: Optional[List[str]] = None
    # 5. Emotional Triggers and Motivations
    emotions: Optional[List[str]] = None
    motivations: Optional[List[str]] = None
    # 6. User Journey
    user_journey_stage: Optional[str] = None
    # 7. Pain Points
    pain_points: Optional[List[str]] = None
    # 8. Preferred Features & Communication
    preferred_features: Optional[List[str]] = None
    preferred_communication_channels: Optional[List[str]] = None

    @validator('tech_proficiency')
    def tech_proficiency_range(cls, v):
        if v is not None and not (0 <= v <= 10):
            raise ValueError('tech_proficiency must be between 0 and 10')
        return v

class CustomerPersonaCreate(CustomerPersonaBase):
    pass

class CustomerPersonaUpdate(CustomerPersonaBase):
    persona_name: Optional[str] = None
    
class CustomerPersonaResponse(CustomerPersonaBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        orm_mode = True

class CustomerPersonaQuestionnaireBase(BaseModel):
    q_uuid: str
    text: str
    body: Optional[str] = None
    remarks: Optional[str] = None
    input_type: str
    range: Optional[List[Any]] = None
    status: Optional[int] = 1

class CustomerPersonaQuestionnaireResponse(CustomerPersonaQuestionnaireBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True
