"""
Questionnaire Service

Handles business logic for questionnaires and answers.
"""

from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from app.services.base import BaseService
from app.repositories.questionnaire_repository import QuestionnaireRepository, AnswerRepository
from app.repositories.user_repository import UserRepository
from app.models import Questionnaire, Answer, User
from app.schemas import QuestionnaireCreate, AnswerCreate, AnswerUpdate
from app.core.exceptions import ValidationError, NotFoundError, BusinessLogicError
from app.core.logging import get_logger

logger = get_logger(__name__)


class QuestionnaireService(BaseService):
    """Service for questionnaire business logic."""
    
    def __init__(
        self,
        db: Session,
        questionnaire_repo: QuestionnaireRepository,
        answer_repo: AnswerRepository,
        user_repo: UserRepository
    ):
        super().__init__(db)
        self.questionnaire_repo = questionnaire_repo
        self.answer_repo = answer_repo
        self.user_repo = user_repo
    
    def get_questionnaire_by_id(self, questionnaire_id: int) -> Optional[Questionnaire]:
        """Get questionnaire by ID."""
        try:
            questionnaire = self.questionnaire_repo.get_by_id(questionnaire_id)
            if not questionnaire:
                raise NotFoundError(f"Questionnaire with ID {questionnaire_id} not found")
            return questionnaire
        except Exception as e:
            logger.error(f"Error getting questionnaire {questionnaire_id}: {str(e)}")
            raise
    
    def get_questionnaires_by_user(self, user_id: int) -> List[Questionnaire]:
        """Get all questionnaires for a user."""
        try:
            # Verify user exists
            user = self.user_repo.get_by_id(user_id)
            if not user:
                raise NotFoundError(f"User with ID {user_id} not found")
            
            return self.questionnaire_repo.get_by_user_id(user_id)
        except Exception as e:
            logger.error(f"Error getting questionnaires for user {user_id}: {str(e)}")
            raise
    
    def create_questionnaire(self, user_id: int, questionnaire_data: QuestionnaireCreate) -> Questionnaire:
        """Create a new questionnaire."""
        try:
            # Verify user exists
            user = self.user_repo.get_by_id(user_id)
            if not user:
                raise NotFoundError(f"User with ID {user_id} not found")
            
            # Validate questionnaire data
            self._validate_questionnaire_data(questionnaire_data)
            
            # Create questionnaire
            questionnaire = self.questionnaire_repo.create({
                "user_id": user_id,
                **questionnaire_data.dict()
            })
            
            logger.info(f"Created questionnaire {questionnaire.id} for user {user_id}")
            return questionnaire
            
        except Exception as e:
            logger.error(f"Error creating questionnaire for user {user_id}: {str(e)}")
            raise
    
    def get_answer_by_id(self, answer_id: int) -> Optional[Answer]:
        """Get answer by ID."""
        try:
            answer = self.answer_repo.get_by_id(answer_id)
            if not answer:
                raise NotFoundError(f"Answer with ID {answer_id} not found")
            return answer
        except Exception as e:
            logger.error(f"Error getting answer {answer_id}: {str(e)}")
            raise
    
    def get_answers_by_questionnaire(self, questionnaire_id: int) -> List[Answer]:
        """Get all answers for a questionnaire."""
        try:
            # Verify questionnaire exists
            self.get_questionnaire_by_id(questionnaire_id)
            
            return self.answer_repo.get_by_questionnaire_id(questionnaire_id)
        except Exception as e:
            logger.error(f"Error getting answers for questionnaire {questionnaire_id}: {str(e)}")
            raise
    
    def create_answer(self, answer_data: AnswerCreate) -> Answer:
        """Create a new answer."""
        try:
            # Verify questionnaire exists
            self.get_questionnaire_by_id(answer_data.questionnaire_id)
            
            # Validate answer data
            self._validate_answer_data(answer_data)
            
            # Check if answer already exists for this question
            existing_answer = self.answer_repo.get_by_questionnaire_and_question(
                answer_data.questionnaire_id,
                answer_data.question_id
            )
            
            if existing_answer:
                raise BusinessLogicError(
                    f"Answer already exists for question {answer_data.question_id} "
                    f"in questionnaire {answer_data.questionnaire_id}"
                )
            
            # Create answer
            answer = self.answer_repo.create(answer_data.dict())
            
            logger.info(f"Created answer {answer.id} for questionnaire {answer_data.questionnaire_id}")
            return answer
            
        except Exception as e:
            logger.error(f"Error creating answer: {str(e)}")
            raise
    
    def update_answer(self, answer_id: int, answer_data: AnswerUpdate) -> Answer:
        """Update an existing answer."""
        try:
            # Verify answer exists
            self.get_answer_by_id(answer_id)
            
            # Validate update data
            self._validate_answer_update_data(answer_data)
            
            # Update answer
            updated_answer = self.answer_repo.update(answer_id, answer_data.dict(exclude_unset=True))
            
            logger.info(f"Updated answer {answer_id}")
            return updated_answer
            
        except Exception as e:
            logger.error(f"Error updating answer {answer_id}: {str(e)}")
            raise
    
    def delete_answer(self, answer_id: int) -> bool:
        """Delete an answer."""
        try:
            # Verify answer exists
            self.get_answer_by_id(answer_id)
            
            # Delete answer
            success = self.answer_repo.delete(answer_id)
            
            if success:
                logger.info(f"Deleted answer {answer_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error deleting answer {answer_id}: {str(e)}")
            raise
    
    def get_questionnaire_completion_status(self, questionnaire_id: int) -> Dict[str, Any]:
        """Get completion status for a questionnaire."""
        try:
            questionnaire = self.get_questionnaire_by_id(questionnaire_id)
            answers = self.get_answers_by_questionnaire(questionnaire_id)
            
            # Calculate completion metrics
            total_questions = len(questionnaire.questions) if questionnaire.questions else 0
            answered_questions = len(answers)
            completion_percentage = (answered_questions / total_questions * 100) if total_questions > 0 else 0
            
            return {
                "questionnaire_id": questionnaire_id,
                "total_questions": total_questions,
                "answered_questions": answered_questions,
                "completion_percentage": round(completion_percentage, 2),
                "is_complete": answered_questions >= total_questions,
                "answers": answers
            }
            
        except Exception as e:
            logger.error(f"Error getting completion status for questionnaire {questionnaire_id}: {str(e)}")
            raise
    
    def calculate_questionnaire_score(self, questionnaire_id: int) -> Dict[str, Any]:
        """Calculate score for a completed questionnaire."""
        try:
            completion_status = self.get_questionnaire_completion_status(questionnaire_id)
            
            if not completion_status["is_complete"]:
                raise BusinessLogicError(f"Questionnaire {questionnaire_id} is not complete")
            
            answers = completion_status["answers"]
            
            # Basic scoring logic - can be enhanced based on business rules
            total_score = 0
            max_possible_score = 0
            
            for answer in answers:
                if answer.answer_value and isinstance(answer.answer_value, (int, float)):
                    total_score += float(answer.answer_value)
                    max_possible_score += 10  # Assuming max score per question is 10
            
            percentage_score = (total_score / max_possible_score * 100) if max_possible_score > 0 else 0
            
            return {
                "questionnaire_id": questionnaire_id,
                "total_score": total_score,
                "max_possible_score": max_possible_score,
                "percentage_score": round(percentage_score, 2),
                "grade": self._calculate_grade(percentage_score)
            }
            
        except Exception as e:
            logger.error(f"Error calculating score for questionnaire {questionnaire_id}: {str(e)}")
            raise
    
    def _validate_questionnaire_data(self, data: QuestionnaireCreate) -> None:
        """Validate questionnaire creation data."""
        if not data.title or len(data.title.strip()) < 3:
            raise ValidationError("Questionnaire title must be at least 3 characters long")
        
        if data.description and len(data.description) > 1000:
            raise ValidationError("Questionnaire description cannot exceed 1000 characters")
    
    def _validate_answer_data(self, data: AnswerCreate) -> None:
        """Validate answer creation data."""
        if not data.question_id:
            raise ValidationError("Question ID is required")
        
        if not data.answer_value:
            raise ValidationError("Answer value is required")
        
        # Validate answer value based on type
        if isinstance(data.answer_value, str) and len(data.answer_value.strip()) == 0:
            raise ValidationError("Answer value cannot be empty")
    
    def _validate_answer_update_data(self, data: AnswerUpdate) -> None:
        """Validate answer update data."""
        if data.answer_value is not None:
            if isinstance(data.answer_value, str) and len(data.answer_value.strip()) == 0:
                raise ValidationError("Answer value cannot be empty")
    
    def _calculate_grade(self, percentage_score: float) -> str:
        """Calculate letter grade based on percentage score."""
        if percentage_score >= 90:
            return "A"
        elif percentage_score >= 80:
            return "B"
        elif percentage_score >= 70:
            return "C"
        elif percentage_score >= 60:
            return "D"
        else:
            return "F"