"""
Unit Tests for Service Layer

Tests business logic in service classes.
"""

import pytest
from unittest.mock import Mock, patch
from app.services.user_service import UserService
from app.services.ideaboard_service import IdeaBoardService
from app.services.questionnaire_service import QuestionnaireService
from app.services.report_service import ReportService
from app.core.exceptions import ValidationError, NotFoundError, BusinessLogicError
from app.schemas import UserCreate, IdeaCreate, QuestionnaireCreate, AnswerCreate, ReportCreate


class TestUserService:
    """Test UserService business logic."""
    
    @pytest.mark.unit
    def test_create_user_success(self, user_service: UserService, test_data_factory):
        """Test successful user creation."""
        user_data = UserCreate(**test_data_factory.create_user_data())
        
        # Mock repository
        user_service.user_repo.get_by_email = Mock(return_value=None)
        user_service.user_repo.get_by_username = Mock(return_value=None)
        user_service.user_repo.create = Mock(return_value=Mock(id=1, email=user_data.email))
        
        result = user_service.create_user(user_data)
        
        assert result.id == 1
        assert result.email == user_data.email
        user_service.user_repo.create.assert_called_once()
    
    @pytest.mark.unit
    def test_create_user_duplicate_email(self, user_service: UserService, test_data_factory):
        """Test user creation with duplicate email."""
        user_data = UserCreate(**test_data_factory.create_user_data())
        
        # Mock existing user
        user_service.user_repo.get_by_email = Mock(return_value=Mock(id=1))
        
        with pytest.raises(ValidationError, match="Email already registered"):
            user_service.create_user(user_data)
    
    @pytest.mark.unit
    def test_authenticate_user_success(self, user_service: UserService):
        """Test successful user authentication."""
        email = "test@example.com"
        password = "TestPass123!"
        
        # Mock user with hashed password
        mock_user = Mock()
        mock_user.hashed_password = "hashed_password"
        user_service.user_repo.get_by_email = Mock(return_value=mock_user)
        
        with patch('app.core.security.verify_password', return_value=True):
            result = user_service.authenticate_user(email, password)
        
        assert result == mock_user
    
    @pytest.mark.unit
    def test_authenticate_user_invalid_credentials(self, user_service: UserService):
        """Test authentication with invalid credentials."""
        email = "test@example.com"
        password = "wrong_password"
        
        user_service.user_repo.get_by_email = Mock(return_value=None)
        
        result = user_service.authenticate_user(email, password)
        assert result is None


class TestIdeaBoardService:
    """Test IdeaBoardService business logic."""
    
    @pytest.mark.unit
    def test_create_idea_success(self, ideaboard_service: IdeaBoardService, test_data_factory):
        """Test successful idea creation."""
        user_id = 1
        idea_data = IdeaCreate(**test_data_factory.create_ideaboard_data())
        
        # Mock dependencies
        ideaboard_service.user_repo.get_by_id = Mock(return_value=Mock(id=user_id))
        ideaboard_service.ideaboard_repo.create = Mock(return_value=Mock(id=1, idea_name=idea_data.idea_name))
        
        result = ideaboard_service.create_idea(user_id, idea_data)
        
        assert result.id == 1
        assert result.idea_name == idea_data.idea_name
    
    @pytest.mark.unit
    def test_create_idea_user_not_found(self, ideaboard_service: IdeaBoardService, test_data_factory):
        """Test idea creation with non-existent user."""
        user_id = 999
        idea_data = IdeaCreate(**test_data_factory.create_ideaboard_data())
        
        ideaboard_service.user_repo.get_by_id = Mock(return_value=None)
        
        with pytest.raises(NotFoundError, match="User with ID 999 not found"):
            ideaboard_service.create_idea(user_id, idea_data)
    
    @pytest.mark.unit
    def test_update_progress_success(self, ideaboard_service: IdeaBoardService):
        """Test successful progress update."""
        idea_id = 1
        progress = 50
        
        mock_idea = Mock(id=idea_id, progress=0)
        ideaboard_service.ideaboard_repo.get_by_id = Mock(return_value=mock_idea)
        ideaboard_service.ideaboard_repo.update = Mock(return_value=Mock(id=idea_id, progress=progress))
        
        result = ideaboard_service.update_progress(idea_id, progress)
        
        assert result.progress == progress
    
    @pytest.mark.unit
    def test_update_progress_invalid_value(self, ideaboard_service: IdeaBoardService):
        """Test progress update with invalid value."""
        idea_id = 1
        progress = 150  # Invalid: > 100
        
        mock_idea = Mock(id=idea_id)
        ideaboard_service.ideaboard_repo.get_by_id = Mock(return_value=mock_idea)
        
        with pytest.raises(ValidationError, match="Progress must be between 0 and 100"):
            ideaboard_service.update_progress(idea_id, progress)


class TestQuestionnaireService:
    """Test QuestionnaireService business logic."""
    
    @pytest.mark.unit
    def test_create_questionnaire_success(self, questionnaire_service: QuestionnaireService, test_data_factory):
        """Test successful questionnaire creation."""
        user_id = 1
        questionnaire_data = QuestionnaireCreate(**test_data_factory.create_questionnaire_data())
        
        # Mock dependencies
        questionnaire_service.user_repo.get_by_id = Mock(return_value=Mock(id=user_id))
        questionnaire_service.questionnaire_repo.create = Mock(
            return_value=Mock(id=1, title=questionnaire_data.title)
        )
        
        result = questionnaire_service.create_questionnaire(user_id, questionnaire_data)
        
        assert result.id == 1
        assert result.title == questionnaire_data.title
    
    @pytest.mark.unit
    def test_create_answer_success(self, questionnaire_service: QuestionnaireService, test_data_factory):
        """Test successful answer creation."""
        questionnaire_id = 1
        answer_data = AnswerCreate(**test_data_factory.create_answer_data(questionnaire_id))
        
        # Mock dependencies
        questionnaire_service.questionnaire_repo.get_by_id = Mock(return_value=Mock(id=questionnaire_id))
        questionnaire_service.answer_repo.get_by_questionnaire_and_question = Mock(return_value=None)
        questionnaire_service.answer_repo.create = Mock(return_value=Mock(id=1, answer_value=answer_data.answer_value))
        
        result = questionnaire_service.create_answer(answer_data)
        
        assert result.id == 1
        assert result.answer_value == answer_data.answer_value
    
    @pytest.mark.unit
    def test_create_answer_duplicate(self, questionnaire_service: QuestionnaireService, test_data_factory):
        """Test answer creation with duplicate question."""
        questionnaire_id = 1
        answer_data = AnswerCreate(**test_data_factory.create_answer_data(questionnaire_id))
        
        # Mock existing answer
        questionnaire_service.questionnaire_repo.get_by_id = Mock(return_value=Mock(id=questionnaire_id))
        questionnaire_service.answer_repo.get_by_questionnaire_and_question = Mock(return_value=Mock(id=1))
        
        with pytest.raises(BusinessLogicError, match="Answer already exists"):
            questionnaire_service.create_answer(answer_data)
    
    @pytest.mark.unit
    def test_calculate_questionnaire_score(self, questionnaire_service: QuestionnaireService):
        """Test questionnaire score calculation."""
        questionnaire_id = 1
        
        # Mock completion status
        mock_completion = {
            "questionnaire_id": questionnaire_id,
            "is_complete": True,
            "answers": [
                Mock(answer_value=8),
                Mock(answer_value=7),
                Mock(answer_value=9)
            ]
        }
        
        questionnaire_service.get_questionnaire_completion_status = Mock(return_value=mock_completion)
        
        result = questionnaire_service.calculate_questionnaire_score(questionnaire_id)
        
        assert result["questionnaire_id"] == questionnaire_id
        assert result["total_score"] == 24
        assert result["percentage_score"] == 80.0
        assert result["grade"] == "B"


class TestReportService:
    """Test ReportService business logic."""
    
    @pytest.mark.unit
    def test_create_report_success(self, report_service: ReportService, test_data_factory):
        """Test successful report creation."""
        user_id = 1
        report_data = ReportCreate(**test_data_factory.create_report_data())
        
        # Mock dependencies
        report_service.user_repo.get_by_id = Mock(return_value=Mock(id=user_id))
        report_service.report_repo.get_recent_report_by_type = Mock(return_value=None)
        report_service.report_repo.create = Mock(return_value=Mock(id=1, report_type=report_data.report_type))
        
        with patch.object(report_service, '_initiate_report_generation'):
            result = report_service.create_report(user_id, report_data)
        
        assert result.id == 1
        assert result.report_type == report_data.report_type
    
    @pytest.mark.unit
    def test_update_report_status_success(self, report_service: ReportService):
        """Test successful report status update."""
        report_id = 1
        new_status = "completed"
        
        mock_report = Mock(id=report_id, status="processing")
        report_service.report_repo.get_by_id = Mock(return_value=mock_report)
        report_service.report_repo.update = Mock(return_value=Mock(id=report_id, status=new_status))
        
        result = report_service.update_report_status(report_id, new_status)
        
        assert result.status == new_status
    
    @pytest.mark.unit
    def test_update_report_status_invalid_transition(self, report_service: ReportService):
        """Test report status update with invalid transition."""
        report_id = 1
        new_status = "processing"
        
        mock_report = Mock(id=report_id, status="completed")
        report_service.report_repo.get_by_id = Mock(return_value=mock_report)
        
        with pytest.raises(ValidationError, match="Invalid status transition"):
            report_service.update_report_status(report_id, new_status)
    
    @pytest.mark.unit
    def test_generate_progress_report(self, report_service: ReportService):
        """Test progress report generation."""
        user_id = 1
        
        # Mock dependencies
        report_service.user_repo.get_by_id = Mock(return_value=Mock(id=user_id))
        mock_ideas = [
            Mock(progress=100, created_at=Mock()),
            Mock(progress=50, created_at=Mock()),
            Mock(progress=0, created_at=Mock())
        ]
        report_service.ideaboard_repo.get_by_user_id = Mock(return_value=mock_ideas)
        
        result = report_service.generate_progress_report(user_id)
        
        assert result["user_id"] == user_id
        assert result["summary"]["total_ideas"] == 3
        assert result["summary"]["completed_ideas"] == 1
        assert result["summary"]["average_progress"] == 50.0
    
    @pytest.mark.unit
    def test_calculate_productivity_score(self, report_service: ReportService):
        """Test productivity score calculation."""
        ideas_created = 5
        ideas_completed = 2
        total_progress = 300
        days = 30
        
        result = report_service._calculate_productivity_score(
            ideas_created, ideas_completed, total_progress, days
        )
        
        assert "score" in result
        assert "rating" in result
        assert "breakdown" in result
        assert 0 <= result["score"] <= 100