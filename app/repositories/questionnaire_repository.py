"""
Questionnaire and Answer repository for questionnaire data access operations.
Handles questionnaire and answer-specific database operations and queries.
"""
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import and_, desc

from ..models import Questionnaire, Answer, CustomerPersonaQuestionnaire, User, IdeaBoard
from ..core.logging import get_logger
from ..core.exceptions import DatabaseError, NotFoundError, ValidationError
from .base import BaseRepository

logger = get_logger(__name__)


class QuestionnaireRepository(BaseRepository[Questionnaire]):
    """Repository for Questionnaire model operations."""
    
    def __init__(self, db: Session):
        super().__init__(db, Questionnaire)
    
    async def get_active_questionnaires(self, skip: int = 0, limit: int = 100) -> List[Questionnaire]:
        """Get active questionnaires (status = 1)."""
        try:
            questionnaires = await self.get_multi(
                skip=skip,
                limit=limit,
                filters={'status': 1},
                order_by='id',
                order_desc=False
            )
            self.logger.debug(f"Retrieved {len(questionnaires)} active questionnaires")
            return questionnaires
        
        except Exception as e:
            self.logger.error(f"Failed to get active questionnaires: {str(e)}")
            raise DatabaseError("Failed to retrieve active questionnaires")
    
    async def get_by_uuid(self, q_uuid: str) -> Optional[Questionnaire]:
        """Get questionnaire by UUID."""
        try:
            questionnaire = await self.get_by_field('q_uuid', q_uuid)
            if questionnaire:
                self.logger.debug(f"Retrieved questionnaire by UUID: {q_uuid}")
            return questionnaire
        
        except Exception as e:
            self.logger.error(f"Failed to get questionnaire by UUID {q_uuid}: {str(e)}")
            raise DatabaseError("Failed to retrieve questionnaire by UUID")
    
    async def get_questionnaires_by_input_type(self, input_type: str) -> List[Questionnaire]:
        """Get questionnaires by input type."""
        try:
            questionnaires = await self.get_multi_by_field('input_type', input_type)
            self.logger.debug(f"Retrieved {len(questionnaires)} questionnaires with input type: {input_type}")
            return questionnaires
        
        except Exception as e:
            self.logger.error(f"Failed to get questionnaires by input type {input_type}: {str(e)}")
            raise DatabaseError("Failed to retrieve questionnaires by input type")


class AnswerRepository(BaseRepository[Answer]):
    """Repository for Answer model operations."""
    
    def __init__(self, db: Session):
        super().__init__(db, Answer)
    
    async def get_user_answers(self, user_id: int, skip: int = 0, limit: int = 100) -> List[Answer]:
        """Get all answers for a specific user."""
        try:
            answers = await self.get_multi(
                skip=skip,
                limit=limit,
                filters={'user_id': user_id},
                order_by='id',
                order_desc=True
            )
            self.logger.debug(f"Retrieved {len(answers)} answers for user {user_id}")
            return answers
        
        except Exception as e:
            self.logger.error(f"Failed to get answers for user {user_id}: {str(e)}")
            raise DatabaseError("Failed to retrieve user answers")
    
    async def get_idea_answers(self, ideaboard_id: int) -> List[Answer]:
        """Get all answers for a specific idea."""
        try:
            answers = await self.get_multi_by_field('ideaBoard_id', ideaboard_id)
            self.logger.debug(f"Retrieved {len(answers)} answers for idea {ideaboard_id}")
            return answers
        
        except Exception as e:
            self.logger.error(f"Failed to get answers for idea {ideaboard_id}: {str(e)}")
            raise DatabaseError("Failed to retrieve idea answers")
    
    async def get_user_idea_answers(self, user_id: int, ideaboard_id: int) -> List[Answer]:
        """Get answers for a specific user and idea combination."""
        try:
            answers = await self.get_multi(
                filters={'user_id': user_id, 'ideaBoard_id': ideaboard_id},
                order_by='question_id'
            )
            self.logger.debug(f"Retrieved {len(answers)} answers for user {user_id} and idea {ideaboard_id}")
            return answers
        
        except Exception as e:
            self.logger.error(f"Failed to get answers for user {user_id} and idea {ideaboard_id}: {str(e)}")
            raise DatabaseError("Failed to retrieve user idea answers")
    
    async def get_answer_by_question(self, user_id: int, question_id: int, ideaboard_id: int) -> Optional[Answer]:
        """Get a specific answer by user, question, and idea."""
        try:
            answer = (
                self.db.query(Answer)
                .filter(
                    and_(
                        Answer.user_id == user_id,
                        Answer.question_id == question_id,
                        Answer.ideaBoard_id == ideaboard_id
                    )
                )
                .first()
            )
            
            if answer:
                self.logger.debug(f"Retrieved answer for user {user_id}, question {question_id}, idea {ideaboard_id}")
            return answer
        
        except SQLAlchemyError as e:
            self.logger.error(f"Failed to get answer by question: {str(e)}")
            raise DatabaseError("Failed to retrieve answer by question")
    
    async def create_or_update_answer(self, answer_data: dict) -> Answer:
        """Create a new answer or update existing one."""
        try:
            # Check if answer already exists
            existing_answer = await self.get_answer_by_question(
                answer_data['user_id'],
                answer_data['question_id'],
                answer_data['ideaBoard_id']
            )
            
            if existing_answer:
                # Update existing answer
                answer = await self.update(existing_answer.id, answer_data)
                self.logger.info(f"Updated answer {existing_answer.id}")
            else:
                # Create new answer
                from datetime import datetime
                answer_data.setdefault('created_at', datetime.utcnow())
                answer_data.setdefault('updated_at', datetime.utcnow())
                
                answer = await self.create(answer_data)
                self.logger.info(f"Created new answer {answer.id}")
            
            return answer
        
        except Exception as e:
            self.logger.error(f"Failed to create or update answer: {str(e)}")
            raise DatabaseError("Failed to create or update answer")
    
    async def get_answers_with_questions(self, user_id: int, ideaboard_id: int) -> List[Dict[str, Any]]:
        """Get answers with their corresponding questions."""
        try:
            results = (
                self.db.query(Answer, Questionnaire)
                .join(Questionnaire, Answer.question_id == Questionnaire.id)
                .filter(
                    and_(
                        Answer.user_id == user_id,
                        Answer.ideaBoard_id == ideaboard_id
                    )
                )
                .order_by(Questionnaire.id)
                .all()
            )
            
            answers_with_questions = []
            for answer, question in results:
                answers_with_questions.append({
                    'answer': answer,
                    'question': question
                })
            
            self.logger.debug(f"Retrieved {len(answers_with_questions)} answers with questions")
            return answers_with_questions
        
        except SQLAlchemyError as e:
            self.logger.error(f"Failed to get answers with questions: {str(e)}")
            raise DatabaseError("Failed to retrieve answers with questions")
    
    async def get_completion_status(self, user_id: int, ideaboard_id: int) -> Dict[str, Any]:
        """Get questionnaire completion status for a user and idea."""
        try:
            # Get total active questions
            total_questions = (
                self.db.query(Questionnaire)
                .filter(Questionnaire.status == 1)
                .count()
            )
            
            # Get answered questions
            answered_questions = (
                self.db.query(Answer)
                .filter(
                    and_(
                        Answer.user_id == user_id,
                        Answer.ideaBoard_id == ideaboard_id
                    )
                )
                .count()
            )
            
            completion_percentage = (answered_questions / total_questions * 100) if total_questions > 0 else 0
            
            status = {
                'total_questions': total_questions,
                'answered_questions': answered_questions,
                'remaining_questions': total_questions - answered_questions,
                'completion_percentage': round(completion_percentage, 2),
                'is_complete': answered_questions >= total_questions
            }
            
            self.logger.debug(f"Retrieved completion status for user {user_id}, idea {ideaboard_id}")
            return status
        
        except SQLAlchemyError as e:
            self.logger.error(f"Failed to get completion status: {str(e)}")
            raise DatabaseError("Failed to retrieve completion status")
    
    async def delete_idea_answers(self, ideaboard_id: int, user_id: int) -> int:
        """Delete all answers for a specific idea and user."""
        try:
            deleted_count = (
                self.db.query(Answer)
                .filter(
                    and_(
                        Answer.ideaBoard_id == ideaboard_id,
                        Answer.user_id == user_id
                    )
                )
                .delete(synchronize_session=False)
            )
            
            self.db.commit()
            self.logger.info(f"Deleted {deleted_count} answers for idea {ideaboard_id}, user {user_id}")
            return deleted_count
        
        except SQLAlchemyError as e:
            self.db.rollback()
            self.logger.error(f"Failed to delete answers for idea {ideaboard_id}: {str(e)}")
            raise DatabaseError("Failed to delete idea answers")


class CustomerPersonaQuestionnaireRepository(BaseRepository[CustomerPersonaQuestionnaire]):
    """Repository for Customer Persona Questionnaire model operations."""
    
    def __init__(self, db: Session):
        super().__init__(db, CustomerPersonaQuestionnaire)
    
    async def get_active_questionnaires(self, skip: int = 0, limit: int = 100) -> List[CustomerPersonaQuestionnaire]:
        """Get active customer persona questionnaires."""
        try:
            questionnaires = await self.get_multi(
                skip=skip,
                limit=limit,
                filters={'status': 1},
                order_by='id',
                order_desc=False
            )
            self.logger.debug(f"Retrieved {len(questionnaires)} active customer persona questionnaires")
            return questionnaires
        
        except Exception as e:
            self.logger.error(f"Failed to get active customer persona questionnaires: {str(e)}")
            raise DatabaseError("Failed to retrieve active customer persona questionnaires")
    
    async def get_by_category(self, category: str) -> List[CustomerPersonaQuestionnaire]:
        """Get questionnaires by category."""
        try:
            questionnaires = await self.get_multi_by_field('category', category)
            self.logger.debug(f"Retrieved {len(questionnaires)} questionnaires for category: {category}")
            return questionnaires
        
        except Exception as e:
            self.logger.error(f"Failed to get questionnaires by category {category}: {str(e)}")
            raise DatabaseError("Failed to retrieve questionnaires by category")
    
    async def get_categories(self) -> List[str]:
        """Get all unique categories."""
        try:
            categories = (
                self.db.query(CustomerPersonaQuestionnaire.category)
                .filter(CustomerPersonaQuestionnaire.status == 1)
                .distinct()
                .all()
            )
            
            category_list = [category[0] for category in categories if category[0]]
            self.logger.debug(f"Retrieved {len(category_list)} unique categories")
            return category_list
        
        except SQLAlchemyError as e:
            self.logger.error(f"Failed to get categories: {str(e)}")
            raise DatabaseError("Failed to retrieve categories")
    
    async def get_by_uuid(self, q_uuid: str) -> Optional[CustomerPersonaQuestionnaire]:
        """Get customer persona questionnaire by UUID."""
        try:
            questionnaire = await self.get_by_field('q_uuid', q_uuid)
            if questionnaire:
                self.logger.debug(f"Retrieved customer persona questionnaire by UUID: {q_uuid}")
            return questionnaire
        
        except Exception as e:
            self.logger.error(f"Failed to get customer persona questionnaire by UUID {q_uuid}: {str(e)}")
            raise DatabaseError("Failed to retrieve customer persona questionnaire by UUID")