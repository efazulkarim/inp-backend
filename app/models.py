from sqlalchemy import Column, Integer, String, Text, ForeignKey, Float, DateTime , JSON
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
