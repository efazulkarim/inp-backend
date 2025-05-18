from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from app.database import get_db
from app.models import IdeaBoard, Trash, User
from app.schemas import TrashSchema, MessageResponse
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

    # Schedule cleanup of old trash items
    background_tasks.add_task(cleanup_old_trash, db)

    return {"detail": "Idea moved to trash"}

# Get all trashed ideas for the current user
@router.get("/get-all-trash", response_model=list[TrashSchema])
def get_all_trash(user_and_db: tuple[User, Session] = Depends(get_user_and_db)):
    user, db = user_and_db  # Extract user and db from the tuple

    trashed_ideas = db.query(Trash).filter(Trash.user_id == user.id).all()
    if not trashed_ideas:
        raise HTTPException(status_code=404, detail="No trashed ideas found for this user")

    return trashed_ideas

# Restore idea from trash back to ideaboard
@router.post("/restore/{trash_id}", response_model=MessageResponse)
def restore_from_trash(
    trash_id: int,
    user_and_db: tuple[User, Session] = Depends(get_user_and_db),
):
    user, db = user_and_db  # Extract user and db from the tuple

    # Find the trashed idea
    trash_item = db.query(Trash).filter(
        Trash.id == trash_id,
        Trash.user_id == user.id
    ).first()

    if not trash_item:
        raise HTTPException(status_code=404, detail="Trashed idea not found or not owned by the current user")

    # Check if an idea with the same ID already exists in IdeaBoard
    existing_idea = db.query(IdeaBoard).filter(IdeaBoard.id == trash_item.idea_id).first()
    if existing_idea:
        raise HTTPException(status_code=400, detail="Cannot restore: An idea with this ID already exists")

    # Create new IdeaBoard entry
    restored_idea = IdeaBoard(
        id=trash_item.idea_id,  # Preserve the original ID
        idea_name=trash_item.idea_name,
        idea_description=trash_item.idea_description,
        user_id=trash_item.user_id
    )

    try:
        # Add restored idea and remove from trash
        db.add(restored_idea)
        db.delete(trash_item)
        db.commit()
        return {"msg": "Idea restored successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error restoring idea: {str(e)}")

# Delete all trash for the current user
@router.delete("/delete-all-trash", response_model=MessageResponse)
def delete_all_trash(user_and_db: tuple[User, Session] = Depends(get_user_and_db)):
    user, db = user_and_db  # Extract user and db from the tuple

    # Delete all trash items for the user
    result = db.query(Trash).filter(Trash.user_id == user.id).delete()
    db.commit()

    if result == 0:
        raise HTTPException(status_code=404, detail="No trashed ideas found to delete")

    return {"msg": f"Successfully deleted {result} trashed items"}

# Function to clean up old trash (items older than 7 days)
async def cleanup_old_trash(db: Session):
    try:
        # Calculate the cutoff date (7 days ago)
        cutoff_date = datetime.utcnow() - timedelta(days=7)
        
        # Delete items older than 7 days
        db.query(Trash).filter(Trash.deleted_at <= cutoff_date).delete()
        db.commit()
    except Exception as e:
        print(f"Error cleaning up old trash: {str(e)}")
    finally:
        db.close()
