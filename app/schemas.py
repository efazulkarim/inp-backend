from pydantic import BaseModel, EmailStr
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
    total_steps: int
    completed_steps: List[int]
    total_score: int
    progress: Dict[int, StepProgress]

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
