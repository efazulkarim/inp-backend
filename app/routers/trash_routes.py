from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from datetime import datetime
from app.database import get_db
from app.models import IdeaBoard, Trash, User
from app.schemas import TrashSchema
from app.auth import get_current_user  # Assuming you're using auth to get the current user

router = APIRouter()

# Function to get the current user and database session
def get_user_and_db(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    return user, db

# Move idea to trash
@router.post("/move-to-trash/{idea_id}", response_model=dict)
def move_to_trash(
    idea_id: int,
    background_tasks: BackgroundTasks,
    user_and_db: tuple[User, Session] = Depends(get_user_and_db),
):
    user, db = user_and_db  # Extract user and db from the tuple

    # Fetch idea from IdeaBoard (checking user ID for ownership)
    idea = db.query(IdeaBoard).filter(IdeaBoard.id == idea_id, IdeaBoard.user_id == user.id).first()
    if not idea:
        raise HTTPException(status_code=404, detail="Idea not found or not owned by the current user")

    # Move idea to Trash table
    trash = Trash(
        idea_id=idea.id,  # Add idea_id explicitly
        idea_name=idea.idea_name,
        idea_description=idea.idea_description,
        user_id=idea.user_id,
        deleted_at=datetime.utcnow()
    )
    db.add(trash)
    db.delete(idea)  # Remove from IdeaBoard
    db.commit()

    # Schedule deletion after 5 minutes
    background_tasks.add_task(delete_idea_after_time, trash.id, db)

    return {"detail": "Idea moved to trash"}


# Get all trashed ideas for the current user
@router.get("/get-all-trash", response_model=list[TrashSchema])
def get_all_trash(user_and_db: tuple[User, Session] = Depends(get_user_and_db)):
    user, db = user_and_db  # Extract user and db from the tuple

    trashed_ideas = db.query(Trash).filter(Trash.user_id == user.id).all()
    if not trashed_ideas:
        raise HTTPException(status_code=404, detail="No trashed ideas found for this user")

    return trashed_ideas

# Function to delete trash after 5 minutes (using asyncio for non-blocking sleep)
async def delete_idea_after_time(trash_id: int, db: Session):
    import asyncio
    await asyncio.sleep(5 * 60)  # Wait for 5 minutes (non-blocking)
    db.query(Trash).filter(Trash.id == trash_id).delete()
    db.commit()
