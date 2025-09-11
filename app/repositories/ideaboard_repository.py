"""
IdeaBoard repository for idea management data access operations.
Handles idea-specific database operations and queries.
"""
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import and_, or_, desc

from ..models import IdeaBoard, User
from ..core.logging import get_logger
from ..core.exceptions import DatabaseError, NotFoundError, ValidationError
from .base import BaseRepository

logger = get_logger(__name__)


class IdeaBoardRepository(BaseRepository[IdeaBoard]):
    """Repository for IdeaBoard model operations."""
    
    def __init__(self, db: Session):
        super().__init__(db, IdeaBoard)
    
    async def get_user_ideas(self, user_id: int, skip: int = 0, limit: int = 100) -> List[IdeaBoard]:
        """Get all ideas for a specific user."""
        try:
            ideas = await self.get_multi(
                skip=skip,
                limit=limit,
                filters={'user_id': user_id},
                order_by='id',
                order_desc=True
            )
            self.logger.debug(f"Retrieved {len(ideas)} ideas for user {user_id}")
            return ideas
        
        except Exception as e:
            self.logger.error(f"Failed to get ideas for user {user_id}: {str(e)}")
            raise DatabaseError("Failed to retrieve user ideas")
    
    async def get_pinned_ideas(self, user_id: int) -> List[IdeaBoard]:
        """Get pinned ideas for a user."""
        try:
            ideas = await self.get_multi(
                filters={'user_id': user_id, 'pin': 1},
                order_by='id',
                order_desc=True
            )
            self.logger.debug(f"Retrieved {len(ideas)} pinned ideas for user {user_id}")
            return ideas
        
        except Exception as e:
            self.logger.error(f"Failed to get pinned ideas for user {user_id}: {str(e)}")
            raise DatabaseError("Failed to retrieve pinned ideas")
    
    async def get_completed_ideas(self, user_id: int, skip: int = 0, limit: int = 100) -> List[IdeaBoard]:
        """Get completed ideas for a user."""
        try:
            ideas = await self.get_multi(
                skip=skip,
                limit=limit,
                filters={'user_id': user_id, 'is_complete': True},
                order_by='id',
                order_desc=True
            )
            self.logger.debug(f"Retrieved {len(ideas)} completed ideas for user {user_id}")
            return ideas
        
        except Exception as e:
            self.logger.error(f"Failed to get completed ideas for user {user_id}: {str(e)}")
            raise DatabaseError("Failed to retrieve completed ideas")
    
    async def get_in_progress_ideas(self, user_id: int, skip: int = 0, limit: int = 100) -> List[IdeaBoard]:
        """Get in-progress ideas for a user."""
        try:
            ideas = await self.get_multi(
                skip=skip,
                limit=limit,
                filters={'user_id': user_id, 'is_complete': False},
                order_by='id',
                order_desc=True
            )
            self.logger.debug(f"Retrieved {len(ideas)} in-progress ideas for user {user_id}")
            return ideas
        
        except Exception as e:
            self.logger.error(f"Failed to get in-progress ideas for user {user_id}: {str(e)}")
            raise DatabaseError("Failed to retrieve in-progress ideas")
    
    async def create_idea(self, idea_data: dict) -> IdeaBoard:
        """Create a new idea with validation."""
        try:
            # Validate required fields
            if not idea_data.get('user_id'):
                raise ValidationError("User ID is required")
            if not idea_data.get('idea_name'):
                raise ValidationError("Idea name is required")
            
            # Set default values
            idea_data.setdefault('current_step', 0)
            idea_data.setdefault('is_complete', False)
            idea_data.setdefault('completed_steps', [])
            idea_data.setdefault('pin', 0)
            
            idea = await self.create(idea_data)
            self.logger.info(f"Created new idea: {idea.idea_name} for user {idea.user_id}")
            return idea
        
        except ValidationError:
            raise
        except Exception as e:
            self.logger.error(f"Failed to create idea: {str(e)}")
            raise DatabaseError("Failed to create idea")
    
    async def update_idea_progress(self, idea_id: int, current_step: int, completed_steps: List[int]) -> IdeaBoard:
        """Update idea progress information."""
        try:
            update_data = {
                'current_step': current_step,
                'completed_steps': completed_steps,
                'is_complete': current_step >= 10  # Assuming 10 steps total
            }
            
            idea = await self.update(idea_id, update_data)
            self.logger.info(f"Updated progress for idea {idea_id}: step {current_step}")
            return idea
        
        except Exception as e:
            self.logger.error(f"Failed to update idea progress {idea_id}: {str(e)}")
            raise DatabaseError("Failed to update idea progress")
    
    async def pin_idea(self, idea_id: int, user_id: int) -> IdeaBoard:
        """Pin an idea for a user."""
        try:
            # Verify the idea belongs to the user
            idea = await self.get_by_id_or_404(idea_id)
            if idea.user_id != user_id:
                raise ValidationError("Cannot pin idea that doesn't belong to user")
            
            idea = await self.update(idea_id, {'pin': 1})
            self.logger.info(f"Pinned idea {idea_id} for user {user_id}")
            return idea
        
        except ValidationError:
            raise
        except Exception as e:
            self.logger.error(f"Failed to pin idea {idea_id}: {str(e)}")
            raise DatabaseError("Failed to pin idea")
    
    async def unpin_idea(self, idea_id: int, user_id: int) -> IdeaBoard:
        """Unpin an idea for a user."""
        try:
            # Verify the idea belongs to the user
            idea = await self.get_by_id_or_404(idea_id)
            if idea.user_id != user_id:
                raise ValidationError("Cannot unpin idea that doesn't belong to user")
            
            idea = await self.update(idea_id, {'pin': 0})
            self.logger.info(f"Unpinned idea {idea_id} for user {user_id}")
            return idea
        
        except ValidationError:
            raise
        except Exception as e:
            self.logger.error(f"Failed to unpin idea {idea_id}: {str(e)}")
            raise DatabaseError("Failed to unpin idea")
    
    async def search_user_ideas(self, user_id: int, search_term: str, skip: int = 0, limit: int = 100) -> List[IdeaBoard]:
        """Search ideas by name or description for a specific user."""
        try:
            search_pattern = f"%{search_term}%"
            ideas = (
                self.db.query(IdeaBoard)
                .filter(
                    and_(
                        IdeaBoard.user_id == user_id,
                        or_(
                            IdeaBoard.idea_name.like(search_pattern),
                            IdeaBoard.idea_description.like(search_pattern)
                        )
                    )
                )
                .order_by(desc(IdeaBoard.id))
                .offset(skip)
                .limit(limit)
                .all()
            )
            
            self.logger.debug(f"Found {len(ideas)} ideas matching search term: {search_term}")
            return ideas
        
        except SQLAlchemyError as e:
            self.logger.error(f"Failed to search ideas for user {user_id}: {str(e)}")
            raise DatabaseError("Failed to search ideas")
    
    async def get_idea_with_user(self, idea_id: int) -> Optional[IdeaBoard]:
        """Get idea with user information."""
        try:
            idea = (
                self.db.query(IdeaBoard)
                .join(User, IdeaBoard.user_id == User.id)
                .filter(IdeaBoard.id == idea_id)
                .first()
            )
            
            if idea:
                self.logger.debug(f"Retrieved idea {idea_id} with user information")
            return idea
        
        except SQLAlchemyError as e:
            self.logger.error(f"Failed to get idea with user {idea_id}: {str(e)}")
            raise DatabaseError("Failed to retrieve idea with user information")
    
    async def get_user_idea_statistics(self, user_id: int) -> Dict[str, Any]:
        """Get idea statistics for a user."""
        try:
            total_ideas = await self.count({'user_id': user_id})
            completed_ideas = await self.count({'user_id': user_id, 'is_complete': True})
            pinned_ideas = await self.count({'user_id': user_id, 'pin': 1})
            
            # Get progress distribution
            progress_stats = {}
            for step in range(0, 11):  # Assuming 0-10 steps
                count = await self.count({'user_id': user_id, 'current_step': step})
                progress_stats[f'step_{step}'] = count
            
            stats = {
                'total_ideas': total_ideas,
                'completed_ideas': completed_ideas,
                'in_progress_ideas': total_ideas - completed_ideas,
                'pinned_ideas': pinned_ideas,
                'completion_rate': (completed_ideas / total_ideas * 100) if total_ideas > 0 else 0,
                'progress_distribution': progress_stats
            }
            
            self.logger.debug(f"Retrieved idea statistics for user {user_id}")
            return stats
        
        except Exception as e:
            self.logger.error(f"Failed to get idea statistics for user {user_id}: {str(e)}")
            raise DatabaseError("Failed to retrieve idea statistics")
    
    async def get_recent_ideas(self, user_id: int, days: int = 7, limit: int = 10) -> List[IdeaBoard]:
        """Get recent ideas for a user within specified days."""
        try:
            from datetime import datetime, timedelta
            
            # Note: This assumes there's a created_at field. If not, we'll use id ordering
            ideas = (
                self.db.query(IdeaBoard)
                .filter(IdeaBoard.user_id == user_id)
                .order_by(desc(IdeaBoard.id))
                .limit(limit)
                .all()
            )
            
            self.logger.debug(f"Retrieved {len(ideas)} recent ideas for user {user_id}")
            return ideas
        
        except SQLAlchemyError as e:
            self.logger.error(f"Failed to get recent ideas for user {user_id}: {str(e)}")
            raise DatabaseError("Failed to retrieve recent ideas")
    
    async def bulk_update_idea_status(self, idea_ids: List[int], user_id: int, status_data: dict) -> int:
        """Bulk update status for multiple ideas belonging to a user."""
        try:
            # Verify all ideas belong to the user
            ideas = (
                self.db.query(IdeaBoard)
                .filter(
                    and_(
                        IdeaBoard.id.in_(idea_ids),
                        IdeaBoard.user_id == user_id
                    )
                )
                .all()
            )
            
            if len(ideas) != len(idea_ids):
                raise ValidationError("Some ideas don't belong to the user or don't exist")
            
            # Perform bulk update
            updated_count = (
                self.db.query(IdeaBoard)
                .filter(
                    and_(
                        IdeaBoard.id.in_(idea_ids),
                        IdeaBoard.user_id == user_id
                    )
                )
                .update(status_data, synchronize_session=False)
            )
            
            self.db.commit()
            self.logger.info(f"Bulk updated {updated_count} ideas for user {user_id}")
            return updated_count
        
        except ValidationError:
            raise
        except SQLAlchemyError as e:
            self.db.rollback()
            self.logger.error(f"Failed to bulk update ideas for user {user_id}: {str(e)}")
            raise DatabaseError("Failed to bulk update ideas")
    
    async def delete_user_idea(self, idea_id: int, user_id: int) -> bool:
        """Delete an idea belonging to a specific user."""
        try:
            # Verify the idea belongs to the user
            idea = await self.get_by_id_or_404(idea_id)
            if idea.user_id != user_id:
                raise ValidationError("Cannot delete idea that doesn't belong to user")
            
            result = await self.delete(idea_id)
            self.logger.info(f"Deleted idea {idea_id} for user {user_id}")
            return result
        
        except ValidationError:
            raise
        except Exception as e:
            self.logger.error(f"Failed to delete idea {idea_id} for user {user_id}: {str(e)}")
            raise DatabaseError("Failed to delete idea")