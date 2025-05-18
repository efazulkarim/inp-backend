from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from app.database import get_db
from app.models import IdeaBoard, Archive, User
from app.schemas import ArchiveSchema, MessageResponse
from app.auth import get_current_user  # Assuming you're using auth to get the current user

router = APIRouter()

# Function to get the current user and database session
def get_user_and_db(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    return user, db

# Archive idea
@router.post("/archive-idea/{idea_id}", response_model=dict)
def archive_idea(
    idea_id: int,
    user_and_db: tuple[User, Session] = Depends(get_user_and_db),
):
    user, db = user_and_db  # Extract user and db from the tuple

    # Fetch idea from IdeaBoard (checking user ID for ownership)
    idea = db.query(IdeaBoard).filter(IdeaBoard.id == idea_id, IdeaBoard.user_id == user.id).first()
    if not idea:
        raise HTTPException(status_code=404, detail="Idea not found or not owned by the current user")

    # Move idea to Archive table
    archive = Archive(
        idea_id=idea.id,
        idea_name=idea.idea_name,
        idea_description=idea.idea_description,
        user_id=idea.user_id,
        archived_at=datetime.utcnow()
    )
    db.add(archive)
    db.delete(idea)  # Remove from IdeaBoard
    db.commit()

    return {"detail": "Idea archived successfully"}

# Get all archived ideas for the current user
@router.get("/get-all-archive", response_model=list[ArchiveSchema])
def get_all_archive(user_and_db: tuple[User, Session] = Depends(get_user_and_db)):
    user, db = user_and_db  # Extract user and db from the tuple

    archived_ideas = db.query(Archive).filter(Archive.user_id == user.id).all()
    if not archived_ideas:
        raise HTTPException(status_code=404, detail="No archived ideas found for this user")

    return archived_ideas

# Restore idea from archive back to ideaboard
@router.post("/restore/{archive_id}", response_model=MessageResponse)
def restore_from_archive(
    archive_id: int,
    user_and_db: tuple[User, Session] = Depends(get_user_and_db),
):
    user, db = user_and_db  # Extract user and db from the tuple

    # Find the archived idea
    archive_item = db.query(Archive).filter(
        Archive.id == archive_id,
        Archive.user_id == user.id
    ).first()

    if not archive_item:
        raise HTTPException(status_code=404, detail="Archived idea not found or not owned by the current user")

    # Check if an idea with the same ID already exists in IdeaBoard
    existing_idea = db.query(IdeaBoard).filter(IdeaBoard.id == archive_item.idea_id).first()
    if existing_idea:
        raise HTTPException(status_code=400, detail="Cannot restore: An idea with this ID already exists")

    # Create new IdeaBoard entry
    restored_idea = IdeaBoard(
        id=archive_item.idea_id,  # Preserve the original ID
        idea_name=archive_item.idea_name,
        idea_description=archive_item.idea_description,
        user_id=archive_item.user_id
    )

    try:
        # Add restored idea and remove from archive
        db.add(restored_idea)
        db.delete(archive_item)
        db.commit()
        return {"msg": "Idea restored successfully from archive"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error restoring idea: {str(e)}")

# Delete individual archived idea
@router.delete("/{archive_id}", response_model=MessageResponse)
def delete_archived_idea(
    archive_id: int,
    user_and_db: tuple[User, Session] = Depends(get_user_and_db),
):
    user, db = user_and_db  # Extract user and db from the tuple

    # Find and verify ownership of the archived idea
    archive_item = db.query(Archive).filter(
        Archive.id == archive_id,
        Archive.user_id == user.id
    ).first()

    if not archive_item:
        raise HTTPException(status_code=404, detail="Archived idea not found or not owned by the current user")

    try:
        # Delete the archived item
        db.delete(archive_item)
        db.commit()
        return {"msg": "Archived idea deleted successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error deleting archived idea: {str(e)}")
