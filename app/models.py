from sqlalchemy import Column, Integer, String, Text, ForeignKey, Float, DateTime , JSON, Boolean
from sqlalchemy.orm import relationship
from .database import Base
from datetime import datetime

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, index=True, nullable=False)
    first_name = Column(String(100))
    last_name = Column(String(100))
    email = Column(String(100), unique=True, index=True)
    address = Column(Text, nullable=True)
    phone = Column(String(20), nullable=True)
    role = Column(String(50), nullable=True)
    password = Column(String(255))  # Hashed password
    status = Column(Integer, default=1)
    verified = Column(Integer, default=0)

    # Stripe subscription-related columns
    subscription_plan = Column(String(50), nullable=True)  # e.g., "free", "basic", "pro"
    subscription_status = Column(String(50), nullable=True)  # e.g., "active", "canceled"
    stripe_customer_id = Column(String(255), nullable=True, unique=True)
    stripe_subscription_id = Column(String(255), nullable=True, unique=True)
    current_period_end = Column(DateTime, nullable=True)
    trial_end = Column(DateTime, nullable=True)

    # Relationship with Answer
    answers = relationship("Answer", back_populates="user", cascade="all, delete-orphan")

class Subscription(Base):
    __tablename__ = "subscription"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    payment_id = Column(String(255))
    paid_amount = Column(Float)
    payment_date = Column(DateTime)
    duration = Column(Integer)
    expiry_date = Column(DateTime)
    is_expired = Column(Integer, default=0)
    is_active = Column(Integer, default=1)

    user = relationship("User")

class Questionnaire(Base):
    __tablename__ = "questionnaire"

    id = Column(Integer, primary_key=True, index=True)
    q_uuid = Column(String(255))
    text = Column(Text)
    body = Column(Text)
    remarks = Column(Text)
    input_type = Column(String(100))
    range = Column(Text)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
    status = Column(Integer)
    
    # Relationship with Answer
    answers = relationship("Answer", back_populates="question", cascade="all, delete-orphan")


class Answer(Base):
    __tablename__ = "answers"

    id = Column(Integer, primary_key=True, index=True)
    question_id = Column(Integer, ForeignKey("questionnaire.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    ideaBoard_id = Column(Integer)
    answer = Column(JSON)  # Changed to JSON type
    created_at = Column(DateTime)
    updated_at = Column(DateTime)

    # Relationships
    user = relationship("User", back_populates="answers")
    question = relationship("Questionnaire", back_populates="answers")


class IdeaBoard(Base):
    __tablename__ = "ideaboard"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    idea_name = Column(String(255), index=True)  
    idea_description = Column(String(500))  
    pin = Column(Integer, nullable=True)
    # Add these new fields
    current_step = Column(Integer, default=0, nullable=False)
    is_complete = Column(Boolean, default=False, nullable=False)
    completed_steps = Column(JSON, default=list, nullable=True)  # Using JSON since you're using JSON elsewhere 


class Trash(Base):
    __tablename__ = "trash"

    id = Column(Integer, primary_key=True, index=True)
    idea_id = Column(Integer, nullable=False)  
    idea_name = Column(String(255), nullable=False)
    idea_description = Column(Text, nullable=True)
    user_id = Column(Integer, nullable=False)
    deleted_at = Column(DateTime)    

class Archive(Base):
    __tablename__ = "archive"

    id = Column(Integer, primary_key=True, index=True)
    idea_id = Column(Integer, nullable=False)  
    idea_name = Column(String(255), nullable=False)
    idea_description = Column(Text, nullable=True)
    user_id = Column(Integer, nullable=False)
    archived_at = Column(DateTime)

class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)
    idea_id = Column(Integer, ForeignKey("ideaboard.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    status = Column(String(50))  # queued, processing, completed, failed
    content = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)

class CustomerPersona(Base):
    __tablename__ = "customer_personas"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    idea_id = Column(Integer, ForeignKey("ideaboard.id"), nullable=True)
    persona_name = Column(String(255), nullable=False)
    tag = Column(String(100), nullable=True)
    
    # Personal information
    age_range = Column(String(50), nullable=True)
    gender = Column(String(50), nullable=True)
    education = Column(String(100), nullable=True)
    location = Column(String(100), nullable=True)
    
    # Professional information
    role = Column(String(100), nullable=True)
    company_size = Column(String(50), nullable=True)
    industry = Column(String(100), nullable=True)
    income_range = Column(String(50), nullable=True)
    work_environment = Column(String(50), nullable=True)
    
    # Goals and challenges
    goals = Column(JSON, nullable=True)  # Array of goals
    challenges = Column(JSON, nullable=True)  # Array of challenges
    
    # Behavior
    tools_used = Column(JSON, nullable=True)  # Array of tools
    decision_factors = Column(JSON, nullable=True)  # Array of decision factors
    information_sources = Column(JSON, nullable=True)  # How they stay informed
    user_journey_stage = Column(String(100), nullable=True)
    
    # Emotional triggers
    pain_points = Column(JSON, nullable=True)  # Array of pain points
    motivations = Column(JSON, nullable=True)  # Array of motivations
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
