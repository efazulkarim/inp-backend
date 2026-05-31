"""
Routes for optional metric modules that extend the core 11-step validation.
"""
import json
import logging
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import (
    Answer,
    IdeaBoard,
    IdeaModuleSelection,
    MetricModule,
    Questionnaire,
    User,
)
from app import schemas
from app.services.subscription_service import SubscriptionService

logger = logging.getLogger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# List available modules
# ---------------------------------------------------------------------------

@router.get("/modules", response_model=List[schemas.MetricModuleResponse])
async def list_modules(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return every metric module defined by the platform."""
    modules = (
        db.query(MetricModule)
        .order_by(MetricModule.sort_order)
        .all()
    )
    return modules


# ---------------------------------------------------------------------------
# Enable / disable modules for an idea
# ---------------------------------------------------------------------------

@router.post(
    "/ideas/{idea_id}/modules",
    response_model=schemas.ModuleSelectionResponse,
    status_code=201,
)
async def enable_module(
    idea_id: int,
    body: schemas.ModuleSelectionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Enable a metric module for a specific idea (subscription-gated)."""
    idea = _get_owned_idea(idea_id, current_user, db)

    modules_limit = await SubscriptionService.get_user_limit(
        current_user, "metric_modules"
    )
    if modules_limit == 0:
        raise HTTPException(
            status_code=403,
            detail="Your subscription plan does not include metric modules. Please upgrade.",
        )

    current_count = (
        db.query(IdeaModuleSelection)
        .filter(
            IdeaModuleSelection.idea_id == idea_id,
            IdeaModuleSelection.user_id == current_user.id,
        )
        .count()
    )
    if modules_limit != float("inf") and current_count >= modules_limit:
        raise HTTPException(
            status_code=429,
            detail=f"Module limit reached ({int(modules_limit)}). Upgrade to enable more.",
        )

    module = db.query(MetricModule).filter(MetricModule.id == body.module_id).first()
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")

    existing = (
        db.query(IdeaModuleSelection)
        .filter(
            IdeaModuleSelection.idea_id == idea_id,
            IdeaModuleSelection.module_id == body.module_id,
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="Module already enabled for this idea")

    selection = IdeaModuleSelection(
        idea_id=idea_id,
        module_id=module.id,
        user_id=current_user.id,
        created_at=datetime.utcnow(),
    )
    db.add(selection)
    db.commit()
    db.refresh(selection)

    return _selection_to_response(selection, module)


@router.get("/ideas/{idea_id}/modules", response_model=schemas.IdeaModulesResponse)
async def get_idea_modules(
    idea_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all modules enabled for an idea."""
    _get_owned_idea(idea_id, current_user, db)

    selections = (
        db.query(IdeaModuleSelection)
        .filter(IdeaModuleSelection.idea_id == idea_id)
        .all()
    )

    items = []
    for sel in selections:
        module = db.query(MetricModule).filter(MetricModule.id == sel.module_id).first()
        if module:
            items.append(_selection_to_response(sel, module))

    return schemas.IdeaModulesResponse(idea_id=idea_id, modules=items)


@router.delete("/ideas/{idea_id}/modules/{module_id}")
async def disable_module(
    idea_id: int,
    module_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Remove a module from an idea."""
    _get_owned_idea(idea_id, current_user, db)

    selection = (
        db.query(IdeaModuleSelection)
        .filter(
            IdeaModuleSelection.idea_id == idea_id,
            IdeaModuleSelection.module_id == module_id,
            IdeaModuleSelection.user_id == current_user.id,
        )
        .first()
    )
    if not selection:
        raise HTTPException(status_code=404, detail="Module selection not found")

    db.delete(selection)
    db.commit()
    return {"message": "Module disabled successfully"}


# ---------------------------------------------------------------------------
# Module questions
# ---------------------------------------------------------------------------

@router.get(
    "/ideas/{idea_id}/module-questions/{module_slug}",
    response_model=schemas.ModuleQuestionsResponse,
)
async def get_module_questions(
    idea_id: int,
    module_slug: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return the questions for a specific metric module."""
    _get_owned_idea(idea_id, current_user, db)

    module = db.query(MetricModule).filter(MetricModule.slug == module_slug).first()
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")

    _assert_module_enabled(idea_id, module.id, db)

    questions = (
        db.query(Questionnaire)
        .filter(
            Questionnaire.module_slug == module_slug,
            Questionnaire.status == 1,
        )
        .all()
    )

    details = []
    for q in questions:
        q_id = q.q_uuid.split("_", 2)[-1] if "_" in q.q_uuid else f"q_{q.id}"

        options = None
        if q.range:
            try:
                parsed = json.loads(q.range)
                if isinstance(parsed, list):
                    options = parsed
                elif isinstance(parsed, dict) and "options" in parsed:
                    options = parsed["options"]
            except (json.JSONDecodeError, TypeError):
                pass

        question_type = "text"
        if q.input_type:
            lower = q.input_type.lower()
            if lower in ("checkbox", "multiple", "multiple_choice"):
                question_type = "multiple_choice"
            elif lower in ("radio", "single", "single_choice"):
                question_type = "single_choice"
            elif lower == "slider":
                question_type = "slider"
            elif lower == "textarea":
                question_type = "textarea"

        details.append(
            schemas.ModuleQuestionDetail(
                id=q_id,
                question_text=q.text,
                description=q.body,
                question_type=question_type,
                options=options,
            )
        )

    return schemas.ModuleQuestionsResponse(
        module_slug=module_slug,
        module_title=module.title,
        questions=details,
    )


# ---------------------------------------------------------------------------
# Save module answers
# ---------------------------------------------------------------------------

@router.post(
    "/ideas/{idea_id}/module-answers/{module_slug}",
    response_model=schemas.ModuleAnswerSaveResponse,
)
async def save_module_answers(
    idea_id: int,
    module_slug: str,
    payload: schemas.ModuleAnswerCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Save answers for a module's questions."""
    _get_owned_idea(idea_id, current_user, db)

    module = db.query(MetricModule).filter(MetricModule.slug == module_slug).first()
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")

    _assert_module_enabled(idea_id, module.id, db)

    questions = (
        db.query(Questionnaire)
        .filter(
            Questionnaire.module_slug == module_slug,
            Questionnaire.status == 1,
        )
        .all()
    )

    q_map = {}
    for q in questions:
        q_id = q.q_uuid.split("_", 2)[-1] if "_" in q.q_uuid else f"q_{q.id}"
        q_map[q_id] = q.id

    for item in payload.questions:
        db_question_id = q_map.get(item.id)
        if db_question_id is None:
            continue

        answer_data = {"type": item.type, "value": item.value}

        existing = (
            db.query(Answer)
            .filter(
                Answer.question_id == db_question_id,
                Answer.ideaBoard_id == idea_id,
                Answer.user_id == current_user.id,
            )
            .first()
        )

        if existing:
            existing.answer = answer_data
            existing.updated_at = datetime.utcnow()
        else:
            new_answer = Answer(
                question_id=db_question_id,
                ideaBoard_id=idea_id,
                user_id=current_user.id,
                answer=answer_data,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            db.add(new_answer)

    db.commit()

    return schemas.ModuleAnswerSaveResponse(
        message="Module answers saved successfully",
        module_slug=module_slug,
        idea_id=idea_id,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_owned_idea(idea_id: int, user: User, db: Session) -> IdeaBoard:
    idea = (
        db.query(IdeaBoard)
        .filter(IdeaBoard.id == idea_id, IdeaBoard.user_id == user.id)
        .first()
    )
    if not idea:
        raise HTTPException(status_code=404, detail="Idea not found")
    return idea


def _assert_module_enabled(idea_id: int, module_id: int, db: Session) -> None:
    enabled = (
        db.query(IdeaModuleSelection)
        .filter(
            IdeaModuleSelection.idea_id == idea_id,
            IdeaModuleSelection.module_id == module_id,
        )
        .first()
    )
    if not enabled:
        raise HTTPException(
            status_code=400,
            detail="This module is not enabled for the idea. Enable it first.",
        )


def _selection_to_response(
    selection: IdeaModuleSelection,
    module: MetricModule,
) -> schemas.ModuleSelectionResponse:
    return schemas.ModuleSelectionResponse(
        id=selection.id,
        idea_id=selection.idea_id,
        module_id=selection.module_id,
        module_slug=module.slug,
        module_title=module.title,
        created_at=selection.created_at,
    )
