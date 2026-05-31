"""
Repository dependency injection and session management utilities.
Provides factory functions and dependency injection for repositories.
"""
from typing import Generator
from sqlalchemy.orm import Session
from fastapi import Depends

from ..database import get_db
from ..core.logging import get_logger
from .user_repository import UserRepository
from .ideaboard_repository import IdeaBoardRepository
from .questionnaire_repository import QuestionnaireRepository, AnswerRepository, CustomerPersonaQuestionnaireRepository
from .report_repository import ReportRepository

logger = get_logger(__name__)


# Repository factory functions for dependency injection
def get_user_repository(db: Session = Depends(get_db)) -> UserRepository:
    """Get UserRepository instance with database session."""
    return UserRepository(db)


def get_ideaboard_repository(db: Session = Depends(get_db)) -> IdeaBoardRepository:
    """Get IdeaBoardRepository instance with database session."""
    return IdeaBoardRepository(db)


def get_questionnaire_repository(db: Session = Depends(get_db)) -> QuestionnaireRepository:
    """Get QuestionnaireRepository instance with database session."""
    return QuestionnaireRepository(db)


def get_answer_repository(db: Session = Depends(get_db)) -> AnswerRepository:
    """Get AnswerRepository instance with database session."""
    return AnswerRepository(db)


def get_customer_persona_questionnaire_repository(db: Session = Depends(get_db)) -> CustomerPersonaQuestionnaireRepository:
    """Get CustomerPersonaQuestionnaireRepository instance with database session."""
    return CustomerPersonaQuestionnaireRepository(db)


def get_report_repository(db: Session = Depends(get_db)) -> ReportRepository:
    """Get ReportRepository instance with database session."""
    return ReportRepository(db)


# Repository container for managing multiple repositories with shared session
class RepositoryContainer:
    """Container for managing multiple repositories with a shared database session."""
    
    def __init__(self, db: Session):
        self.db = db
        self._user_repo = None
        self._ideaboard_repo = None
        self._questionnaire_repo = None
        self._answer_repo = None
        self._customer_persona_questionnaire_repo = None
        self._report_repo = None
    
    @property
    def user(self) -> UserRepository:
        """Get or create UserRepository instance."""
        if self._user_repo is None:
            self._user_repo = UserRepository(self.db)
        return self._user_repo
    
    @property
    def ideaboard(self) -> IdeaBoardRepository:
        """Get or create IdeaBoardRepository instance."""
        if self._ideaboard_repo is None:
            self._ideaboard_repo = IdeaBoardRepository(self.db)
        return self._ideaboard_repo
    
    @property
    def questionnaire(self) -> QuestionnaireRepository:
        """Get or create QuestionnaireRepository instance."""
        if self._questionnaire_repo is None:
            self._questionnaire_repo = QuestionnaireRepository(self.db)
        return self._questionnaire_repo
    
    @property
    def answer(self) -> AnswerRepository:
        """Get or create AnswerRepository instance."""
        if self._answer_repo is None:
            self._answer_repo = AnswerRepository(self.db)
        return self._answer_repo
    
    @property
    def customer_persona_questionnaire(self) -> CustomerPersonaQuestionnaireRepository:
        """Get or create CustomerPersonaQuestionnaireRepository instance."""
        if self._customer_persona_questionnaire_repo is None:
            self._customer_persona_questionnaire_repo = CustomerPersonaQuestionnaireRepository(self.db)
        return self._customer_persona_questionnaire_repo
    
    @property
    def report(self) -> ReportRepository:
        """Get or create ReportRepository instance."""
        if self._report_repo is None:
            self._report_repo = ReportRepository(self.db)
        return self._report_repo
    
    def close(self):
        """Close the database session."""
        if self.db:
            self.db.close()


def get_repository_container(db: Session = Depends(get_db)) -> RepositoryContainer:
    """Get RepositoryContainer instance with database session."""
    return RepositoryContainer(db)


# Transaction management utilities
class TransactionManager:
    """Context manager for database transactions."""
    
    def __init__(self, db: Session):
        self.db = db
        self.logger = get_logger(f"{self.__class__.__name__}")
    
    def __enter__(self):
        self.logger.debug("Starting database transaction")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            try:
                self.db.commit()
                self.logger.debug("Transaction committed successfully")
            except Exception as e:
                self.db.rollback()
                self.logger.error(f"Failed to commit transaction: {str(e)}")
                raise
        else:
            self.db.rollback()
            self.logger.error(f"Transaction rolled back due to exception: {exc_val}")
        return False


def get_transaction_manager(db: Session = Depends(get_db)) -> TransactionManager:
    """Get TransactionManager instance with database session."""
    return TransactionManager(db)


# Repository testing utilities
class TestRepositoryContainer(RepositoryContainer):
    """Repository container for testing with additional utilities."""
    
    def __init__(self, db: Session):
        super().__init__(db)
        self.logger = get_logger(f"{self.__class__.__name__}")
    
    def cleanup_test_data(self):
        """Clean up test data from all tables."""
        try:
            # Note: This is a basic cleanup - in real tests you'd want more sophisticated cleanup
            self.logger.warning("Cleaning up test data - this should only be used in tests!")
            
            # Clean up in reverse dependency order
            from ..models import Answer, Report, IdeaBoard, User, Questionnaire
            
            self.db.query(Answer).delete()
            self.db.query(Report).delete()
            self.db.query(IdeaBoard).delete()
            # Be careful with User cleanup in tests
            
            self.db.commit()
            self.logger.info("Test data cleanup completed")
        
        except Exception as e:
            self.db.rollback()
            self.logger.error(f"Failed to cleanup test data: {str(e)}")
            raise
    
    def create_test_user(self, **kwargs) -> 'User':
        """Create a test user with default values."""
        from ..models import User
        
        default_data = {
            'username': 'test_user',
            'email': 'test@example.com',
            'first_name': 'Test',
            'last_name': 'User',
            'status': 1,
            'verified': 1
        }
        default_data.update(kwargs)
        
        user = User(**default_data)
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        
        self.logger.debug(f"Created test user: {user.username}")
        return user
    
    def create_test_idea(self, user_id: int, **kwargs) -> 'IdeaBoard':
        """Create a test idea with default values."""
        from ..models import IdeaBoard
        
        default_data = {
            'user_id': user_id,
            'idea_name': 'Test Idea',
            'idea_description': 'Test idea description',
            'current_step': 0,
            'is_complete': False,
            'pin': 0
        }
        default_data.update(kwargs)
        
        idea = IdeaBoard(**default_data)
        self.db.add(idea)
        self.db.commit()
        self.db.refresh(idea)
        
        self.logger.debug(f"Created test idea: {idea.idea_name}")
        return idea


def get_test_repository_container(db: Session) -> TestRepositoryContainer:
    """Get TestRepositoryContainer instance for testing."""
    return TestRepositoryContainer(db)


# Repository health check utilities
async def check_repository_health(db: Session) -> dict:
    """Check the health of repository connections and basic operations."""
    health_status = {
        'database_connection': False,
        'repositories': {},
        'errors': []
    }
    
    try:
        # Test basic database connection
        db.execute("SELECT 1")
        health_status['database_connection'] = True
        
        # Test each repository
        repositories = {
            'user': UserRepository(db),
            'ideaboard': IdeaBoardRepository(db),
            'questionnaire': QuestionnaireRepository(db),
            'answer': AnswerRepository(db),
            'report': ReportRepository(db)
        }
        
        for repo_name, repo in repositories.items():
            try:
                # Test basic count operation
                await repo.count()
                health_status['repositories'][repo_name] = True
            except Exception as e:
                health_status['repositories'][repo_name] = False
                health_status['errors'].append(f"{repo_name}: {str(e)}")
        
        logger.debug("Repository health check completed")
        
    except Exception as e:
        health_status['errors'].append(f"Database connection: {str(e)}")
        logger.error(f"Repository health check failed: {str(e)}")
    
    return health_status