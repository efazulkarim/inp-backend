"""
Test Configuration and Fixtures

Provides common test fixtures and configuration for the test suite.
"""

import pytest
import tempfile
import os
from typing import Generator, Dict, Any
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from fastapi.testclient import TestClient
from app.main import app
from app.database import get_db, Base
from app.core.config import get_settings
from app.repositories.dependencies import get_repository_container
from app.services.user_service import UserService
from app.services.ideaboard_service import IdeaBoardService
from app.services.questionnaire_service import QuestionnaireService
from app.services.report_service import ReportService
from app.models import User, IdeaBoard, Questionnaire, Answer, Report


# Test database URL
TEST_DATABASE_URL = "sqlite:///./test.db"


@pytest.fixture(scope="session")
def test_engine():
    """Create test database engine."""
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def test_db(test_engine) -> Generator[Session, None, None]:
    """Create test database session."""
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    
    connection = test_engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
def client(test_db: Session) -> Generator[TestClient, None, None]:
    """Create test client with database override."""
    def override_get_db():
        try:
            yield test_db
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as test_client:
        yield test_client
    
    app.dependency_overrides.clear()


@pytest.fixture
def test_user_data() -> Dict[str, Any]:
    """Test user data."""
    return {
        "email": "test@example.com",
        "username": "testuser",
        "password": "TestPass123!",
        "first_name": "Test",
        "last_name": "User"
    }


@pytest.fixture
def test_user(test_db: Session, test_user_data: Dict[str, Any]) -> User:
    """Create test user."""
    from app.core.security import get_password_hash
    
    user = User(
        email=test_user_data["email"],
        username=test_user_data["username"],
        hashed_password=get_password_hash(test_user_data["password"]),
        first_name=test_user_data["first_name"],
        last_name=test_user_data["last_name"]
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


@pytest.fixture
def test_ideaboard(test_db: Session, test_user: User) -> IdeaBoard:
    """Create test ideaboard."""
    ideaboard = IdeaBoard(
        idea_name="Test Idea",
        idea_description="Test idea description",
        user_id=test_user.id,
        progress=0
    )
    test_db.add(ideaboard)
    test_db.commit()
    test_db.refresh(ideaboard)
    return ideaboard


@pytest.fixture
def test_questionnaire(test_db: Session, test_user: User) -> Questionnaire:
    """Create test questionnaire."""
    questionnaire = Questionnaire(
        title="Test Questionnaire",
        description="Test questionnaire description",
        user_id=test_user.id
    )
    test_db.add(questionnaire)
    test_db.commit()
    test_db.refresh(questionnaire)
    return questionnaire


@pytest.fixture
def test_answer(test_db: Session, test_questionnaire: Questionnaire) -> Answer:
    """Create test answer."""
    answer = Answer(
        questionnaire_id=test_questionnaire.id,
        question_id=1,
        answer_value="Test answer"
    )
    test_db.add(answer)
    test_db.commit()
    test_db.refresh(answer)
    return answer


@pytest.fixture
def test_report(test_db: Session, test_user: User) -> Report:
    """Create test report."""
    report = Report(
        user_id=test_user.id,
        report_type="progress",
        status="completed",
        content="Test report content"
    )
    test_db.add(report)
    test_db.commit()
    test_db.refresh(report)
    return report


@pytest.fixture
def repository_container(test_db: Session):
    """Get repository container for testing."""
    return get_repository_container(test_db)


@pytest.fixture
def user_service(test_db: Session, repository_container) -> UserService:
    """Create user service for testing."""
    return UserService(
        db=test_db,
        user_repo=repository_container.user_repository
    )


@pytest.fixture
def ideaboard_service(test_db: Session, repository_container) -> IdeaBoardService:
    """Create ideaboard service for testing."""
    return IdeaBoardService(
        db=test_db,
        ideaboard_repo=repository_container.ideaboard_repository,
        user_repo=repository_container.user_repository
    )


@pytest.fixture
def questionnaire_service(test_db: Session, repository_container) -> QuestionnaireService:
    """Create questionnaire service for testing."""
    return QuestionnaireService(
        db=test_db,
        questionnaire_repo=repository_container.questionnaire_repository,
        answer_repo=repository_container.answer_repository,
        user_repo=repository_container.user_repository
    )


@pytest.fixture
def report_service(test_db: Session, repository_container) -> ReportService:
    """Create report service for testing."""
    return ReportService(
        db=test_db,
        report_repo=repository_container.report_repository,
        user_repo=repository_container.user_repository,
        ideaboard_repo=repository_container.ideaboard_repository
    )


@pytest.fixture
def auth_headers(client: TestClient, test_user_data: Dict[str, Any]) -> Dict[str, str]:
    """Get authentication headers for test requests."""
    # First create the user
    client.post("/auth/register", json=test_user_data)
    
    # Then login to get token
    login_data = {
        "email": test_user_data["email"],
        "password": test_user_data["password"]
    }
    response = client.post("/auth/login", json=login_data)
    token = response.json()["access_token"]
    
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def mock_settings():
    """Mock settings for testing."""
    class MockSettings:
        DATABASE_URL = TEST_DATABASE_URL
        SECRET_KEY = "test-secret-key"
        ALGORITHM = "HS256"
        ACCESS_TOKEN_EXPIRE_MINUTES = 30
        ENVIRONMENT = "test"
        DEBUG = True
        
    return MockSettings()


# Test data factories
class TestDataFactory:
    """Factory for creating test data."""
    
    @staticmethod
    def create_user_data(email: str = None, username: str = None) -> Dict[str, Any]:
        """Create user test data."""
        return {
            "email": email or "test@example.com",
            "username": username or "testuser",
            "password": "TestPass123!",
            "first_name": "Test",
            "last_name": "User"
        }
    
    @staticmethod
    def create_ideaboard_data(name: str = None) -> Dict[str, Any]:
        """Create ideaboard test data."""
        return {
            "idea_name": name or "Test Idea",
            "idea_description": "Test idea description",
            "pin": 0
        }
    
    @staticmethod
    def create_questionnaire_data(title: str = None) -> Dict[str, Any]:
        """Create questionnaire test data."""
        return {
            "title": title or "Test Questionnaire",
            "description": "Test questionnaire description"
        }
    
    @staticmethod
    def create_answer_data(questionnaire_id: int, question_id: int = 1) -> Dict[str, Any]:
        """Create answer test data."""
        return {
            "questionnaire_id": questionnaire_id,
            "question_id": question_id,
            "answer_value": "Test answer"
        }
    
    @staticmethod
    def create_report_data(report_type: str = "progress") -> Dict[str, Any]:
        """Create report test data."""
        return {
            "report_type": report_type,
            "description": "Test report description"
        }


@pytest.fixture
def test_data_factory():
    """Test data factory fixture."""
    return TestDataFactory