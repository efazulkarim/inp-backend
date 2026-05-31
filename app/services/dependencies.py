"""
Service Layer Dependencies

Provides dependency injection for service layer components.
"""

from typing import Generator
from fastapi import Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.repositories.dependencies import get_repository_container, RepositoryContainer
from app.services.user_service import UserService
from app.services.ideaboard_service import IdeaBoardService
from app.services.questionnaire_service import QuestionnaireService
from app.services.report_service import ReportService


def get_user_service(
    db: Session = Depends(get_db),
    repos: RepositoryContainer = Depends(get_repository_container)
) -> UserService:
    """Get user service instance."""
    return UserService(
        db=db,
        user_repo=repos.user_repository
    )


def get_ideaboard_service(
    db: Session = Depends(get_db),
    repos: RepositoryContainer = Depends(get_repository_container)
) -> IdeaBoardService:
    """Get ideaboard service instance."""
    return IdeaBoardService(
        db=db,
        ideaboard_repo=repos.ideaboard_repository,
        user_repo=repos.user_repository
    )


def get_questionnaire_service(
    db: Session = Depends(get_db),
    repos: RepositoryContainer = Depends(get_repository_container)
) -> QuestionnaireService:
    """Get questionnaire service instance."""
    return QuestionnaireService(
        db=db,
        questionnaire_repo=repos.questionnaire_repository,
        answer_repo=repos.answer_repository,
        user_repo=repos.user_repository
    )


def get_report_service(
    db: Session = Depends(get_db),
    repos: RepositoryContainer = Depends(get_repository_container)
) -> ReportService:
    """Get report service instance."""
    return ReportService(
        db=db,
        report_repo=repos.report_repository,
        user_repo=repos.user_repository,
        ideaboard_repo=repos.ideaboard_repository
    )


class ServiceContainer:
    """Container for all service instances."""
    
    def __init__(
        self,
        user_service: UserService,
        ideaboard_service: IdeaBoardService,
        questionnaire_service: QuestionnaireService,
        report_service: ReportService
    ):
        self.user_service = user_service
        self.ideaboard_service = ideaboard_service
        self.questionnaire_service = questionnaire_service
        self.report_service = report_service


def get_service_container(
    user_service: UserService = Depends(get_user_service),
    ideaboard_service: IdeaBoardService = Depends(get_ideaboard_service),
    questionnaire_service: QuestionnaireService = Depends(get_questionnaire_service),
    report_service: ReportService = Depends(get_report_service)
) -> ServiceContainer:
    """Get service container with all services."""
    return ServiceContainer(
        user_service=user_service,
        ideaboard_service=ideaboard_service,
        questionnaire_service=questionnaire_service,
        report_service=report_service
    )