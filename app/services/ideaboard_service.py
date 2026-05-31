"""
IdeaBoard management service for idea business logic operations.
Handles idea creation, updating, progress tracking, and business rules.
"""
from typing import Optional, List, Dict, Any
from datetime import datetime

from ..models import IdeaBoard
from ..core.logging import get_logger
from ..core.exceptions import (
    ValidationError, NotFoundError, BusinessLogicError, 
    AuthorizationError, ErrorContext
)
from ..repositories.dependencies import RepositoryContainer
from .base import BaseService

logger = get_logger(__name__)


class IdeaBoardService(BaseService):
    """Service for idea management operations."""
    
    def __init__(self, repositories: RepositoryContainer):
        super().__init__(repositories)
        self.max_ideas_per_user = 100  # Business rule: max ideas per user
        self.max_idea_name_length = 255
        self.max_idea_description_length = 500
        self.total_steps = 10  # Total number of steps in the idea development process
    
    async def create_idea(self, user_id: int, idea_data: Dict[str, Any]) -> IdeaBoard:
        """Create a new idea for a user."""
        with ErrorContext("create idea", self.logger):
            # Validate required fields
            self.validate_required_fields(idea_data, ['idea_name'])
            
            # Validate and sanitize input
            await self._validate_idea_data(idea_data)
            idea_data = await self._sanitize_idea_data(idea_data)
            
            # Check user's idea limit
            await self._check_user_idea_limit(user_id)
            
            # Set user_id and default values
            idea_data['user_id'] = user_id
            idea_data.setdefault('current_step', 0)
            idea_data.setdefault('is_complete', False)
            idea_data.setdefault('completed_steps', [])
            idea_data.setdefault('pin', 0)
            
            try:
                idea = await self.repositories.ideaboard.create_idea(idea_data)
                self.logger.info(f"Created idea '{idea.idea_name}' for user {user_id}")
                return idea
            
            except Exception as e:
                self.handle_repository_error("create idea", e)
    
    async def get_user_ideas(self, user_id: int, skip: int = 0, limit: int = 100) -> List[IdeaBoard]:
        """Get all ideas for a user."""
        with ErrorContext("get user ideas", self.logger):
            try:
                ideas = await self.repositories.ideaboard.get_user_ideas(user_id, skip, limit)
                return ideas
            except Exception as e:
                self.handle_repository_error("get user ideas", e)
    
    async def get_idea_by_id(self, idea_id: int, user_id: int) -> IdeaBoard:
        """Get a specific idea by ID, ensuring it belongs to the user."""
        with ErrorContext("get idea by id", self.logger):
            try:
                idea = await self.repositories.ideaboard.get_by_id_or_404(idea_id)
                self.validate_user_access(user_id, idea.user_id, "idea")
                return idea
            except Exception as e:
                self.handle_repository_error("get idea by id", e)
    
    async def update_idea(self, idea_id: int, user_id: int, update_data: Dict[str, Any]) -> IdeaBoard:
        """Update an existing idea."""
        with ErrorContext("update idea", self.logger):
            # Get existing idea and validate access
            idea = await self.get_idea_by_id(idea_id, user_id)
            
            # Validate and sanitize update data
            await self._validate_idea_update_data(update_data, idea)
            update_data = await self._sanitize_idea_data(update_data)
            
            # Remove fields that shouldn't be updated directly
            protected_fields = ['user_id', 'current_step', 'is_complete', 'completed_steps']
            for field in protected_fields:
                update_data.pop(field, None)
            
            try:
                idea = await self.repositories.ideaboard.update(idea_id, update_data)
                self.logger.info(f"Updated idea {idea_id} for user {user_id}")
                return idea
            
            except Exception as e:
                self.handle_repository_error("update idea", e)
    
    async def delete_idea(self, idea_id: int, user_id: int) -> bool:
        """Delete an idea."""
        with ErrorContext("delete idea", self.logger):
            try:
                result = await self.repositories.ideaboard.delete_user_idea(idea_id, user_id)
                self.logger.info(f"Deleted idea {idea_id} for user {user_id}")
                return result
            except Exception as e:
                self.handle_repository_error("delete idea", e)
    
    async def update_idea_progress(self, idea_id: int, user_id: int, step: int) -> IdeaBoard:
        """Update idea progress to a specific step."""
        with ErrorContext("update idea progress", self.logger):
            # Validate step
            if not isinstance(step, int) or step < 0 or step > self.total_steps:
                raise ValidationError(f"Step must be between 0 and {self.total_steps}")
            
            # Get existing idea and validate access
            idea = await self.get_idea_by_id(idea_id, user_id)
            
            # Calculate completed steps
            completed_steps = list(range(step)) if step > 0 else []
            
            try:
                idea = await self.repositories.ideaboard.update_idea_progress(
                    idea_id, step, completed_steps
                )
                self.logger.info(f"Updated progress for idea {idea_id} to step {step}")
                return idea
            
            except Exception as e:
                self.handle_repository_error("update idea progress", e)
    
    async def advance_idea_step(self, idea_id: int, user_id: int) -> IdeaBoard:
        """Advance idea to the next step."""
        with ErrorContext("advance idea step", self.logger):
            # Get current idea
            idea = await self.get_idea_by_id(idea_id, user_id)
            
            # Check if already complete
            if idea.is_complete:
                raise BusinessLogicError("Idea is already complete")
            
            # Calculate next step
            next_step = min(idea.current_step + 1, self.total_steps)
            
            return await self.update_idea_progress(idea_id, user_id, next_step)
    
    async def complete_idea_step(self, idea_id: int, user_id: int, step: int) -> IdeaBoard:
        """Mark a specific step as completed."""
        with ErrorContext("complete idea step", self.logger):
            # Validate step
            if not isinstance(step, int) or step < 0 or step >= self.total_steps:
                raise ValidationError(f"Step must be between 0 and {self.total_steps - 1}")
            
            # Get existing idea and validate access
            idea = await self.get_idea_by_id(idea_id, user_id)
            
            # Update completed steps
            completed_steps = idea.completed_steps or []
            if step not in completed_steps:
                completed_steps.append(step)
                completed_steps.sort()
            
            # Update current step to the highest completed step + 1
            current_step = max(completed_steps) + 1 if completed_steps else 0
            current_step = min(current_step, self.total_steps)
            
            try:
                idea = await self.repositories.ideaboard.update_idea_progress(
                    idea_id, current_step, completed_steps
                )
                self.logger.info(f"Completed step {step} for idea {idea_id}")
                return idea
            
            except Exception as e:
                self.handle_repository_error("complete idea step", e)
    
    async def pin_idea(self, idea_id: int, user_id: int) -> IdeaBoard:
        """Pin an idea for a user."""
        with ErrorContext("pin idea", self.logger):
            try:
                idea = await self.repositories.ideaboard.pin_idea(idea_id, user_id)
                self.logger.info(f"Pinned idea {idea_id} for user {user_id}")
                return idea
            except Exception as e:
                self.handle_repository_error("pin idea", e)
    
    async def unpin_idea(self, idea_id: int, user_id: int) -> IdeaBoard:
        """Unpin an idea for a user."""
        with ErrorContext("unpin idea", self.logger):
            try:
                idea = await self.repositories.ideaboard.unpin_idea(idea_id, user_id)
                self.logger.info(f"Unpinned idea {idea_id} for user {user_id}")
                return idea
            except Exception as e:
                self.handle_repository_error("unpin idea", e)
    
    async def get_pinned_ideas(self, user_id: int) -> List[IdeaBoard]:
        """Get all pinned ideas for a user."""
        with ErrorContext("get pinned ideas", self.logger):
            try:
                ideas = await self.repositories.ideaboard.get_pinned_ideas(user_id)
                return ideas
            except Exception as e:
                self.handle_repository_error("get pinned ideas", e)
    
    async def get_completed_ideas(self, user_id: int, skip: int = 0, limit: int = 100) -> List[IdeaBoard]:
        """Get completed ideas for a user."""
        with ErrorContext("get completed ideas", self.logger):
            try:
                ideas = await self.repositories.ideaboard.get_completed_ideas(user_id, skip, limit)
                return ideas
            except Exception as e:
                self.handle_repository_error("get completed ideas", e)
    
    async def get_in_progress_ideas(self, user_id: int, skip: int = 0, limit: int = 100) -> List[IdeaBoard]:
        """Get in-progress ideas for a user."""
        with ErrorContext("get in-progress ideas", self.logger):
            try:
                ideas = await self.repositories.ideaboard.get_in_progress_ideas(user_id, skip, limit)
                return ideas
            except Exception as e:
                self.handle_repository_error("get in-progress ideas", e)
    
    async def search_user_ideas(self, user_id: int, search_term: str, skip: int = 0, limit: int = 100) -> List[IdeaBoard]:
        """Search ideas for a user."""
        with ErrorContext("search user ideas", self.logger):
            if not search_term or len(search_term.strip()) < 2:
                raise ValidationError("Search term must be at least 2 characters long")
            
            try:
                ideas = await self.repositories.ideaboard.search_user_ideas(
                    user_id, search_term.strip(), skip, limit
                )
                return ideas
            except Exception as e:
                self.handle_repository_error("search user ideas", e)
    
    async def get_user_idea_statistics(self, user_id: int) -> Dict[str, Any]:
        """Get idea statistics for a user."""
        with ErrorContext("get user idea statistics", self.logger):
            try:
                stats = await self.repositories.ideaboard.get_user_idea_statistics(user_id)
                
                # Add additional calculated metrics
                stats['average_progress'] = self._calculate_average_progress(stats)
                stats['productivity_score'] = self._calculate_productivity_score(stats)
                
                return stats
            except Exception as e:
                self.handle_repository_error("get user idea statistics", e)
    
    async def get_recent_ideas(self, user_id: int, days: int = 7, limit: int = 10) -> List[IdeaBoard]:
        """Get recent ideas for a user."""
        with ErrorContext("get recent ideas", self.logger):
            if days <= 0 or days > 365:
                raise ValidationError("Days must be between 1 and 365")
            
            try:
                ideas = await self.repositories.ideaboard.get_recent_ideas(user_id, days, limit)
                return ideas
            except Exception as e:
                self.handle_repository_error("get recent ideas", e)
    
    async def bulk_update_ideas(self, idea_ids: List[int], user_id: int, update_data: Dict[str, Any]) -> int:
        """Bulk update multiple ideas for a user."""
        with ErrorContext("bulk update ideas", self.logger):
            if not idea_ids:
                raise ValidationError("No idea IDs provided")
            
            if len(idea_ids) > 50:  # Limit bulk operations
                raise ValidationError("Cannot update more than 50 ideas at once")
            
            # Validate update data
            await self._validate_bulk_update_data(update_data)
            
            try:
                updated_count = await self.repositories.ideaboard.bulk_update_idea_status(
                    idea_ids, user_id, update_data
                )
                self.logger.info(f"Bulk updated {updated_count} ideas for user {user_id}")
                return updated_count
            
            except Exception as e:
                self.handle_repository_error("bulk update ideas", e)
    
    # Private helper methods
    async def _validate_idea_data(self, idea_data: Dict[str, Any]) -> None:
        """Validate idea data."""
        # Validate idea name
        if 'idea_name' in idea_data:
            self.validate_string_length(
                idea_data['idea_name'], 
                'idea_name', 
                min_length=1, 
                max_length=self.max_idea_name_length
            )
        
        # Validate idea description
        if 'idea_description' in idea_data and idea_data['idea_description']:
            if len(idea_data['idea_description']) > self.max_idea_description_length:
                raise ValidationError(f"Idea description cannot exceed {self.max_idea_description_length} characters")
        
        # Validate pin value
        if 'pin' in idea_data:
            pin = idea_data['pin']
            if pin not in [0, 1]:
                raise ValidationError("Pin value must be 0 or 1")
    
    async def _validate_idea_update_data(self, update_data: Dict[str, Any], existing_idea: IdeaBoard) -> None:
        """Validate idea update data."""
        await self._validate_idea_data(update_data)
        
        # Additional validation for updates can be added here
        # For example, checking if certain fields can be updated based on idea status
        if existing_idea.is_complete and 'idea_name' in update_data:
            # Allow name changes even for completed ideas
            pass
    
    async def _validate_bulk_update_data(self, update_data: Dict[str, Any]) -> None:
        """Validate bulk update data."""
        # Only allow certain fields for bulk updates
        allowed_fields = ['pin']
        
        for field in update_data.keys():
            if field not in allowed_fields:
                raise ValidationError(f"Field '{field}' is not allowed for bulk updates")
        
        await self._validate_idea_data(update_data)
    
    async def _sanitize_idea_data(self, idea_data: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize idea data."""
        sanitized = {}
        
        for key, value in idea_data.items():
            if isinstance(value, str):
                sanitized[key] = self.sanitize_string(value)
            else:
                sanitized[key] = value
        
        return sanitized
    
    async def _check_user_idea_limit(self, user_id: int) -> None:
        """Check if user has reached the maximum number of ideas."""
        try:
            idea_count = await self.repositories.ideaboard.count({'user_id': user_id})
            
            if idea_count >= self.max_ideas_per_user:
                raise BusinessLogicError(
                    f"Maximum number of ideas ({self.max_ideas_per_user}) reached. "
                    "Please delete some ideas before creating new ones."
                )
        
        except BusinessLogicError:
            raise
        except Exception as e:
            self.handle_repository_error("check user idea limit", e)
    
    def _calculate_average_progress(self, stats: Dict[str, Any]) -> float:
        """Calculate average progress across all ideas."""
        total_ideas = stats.get('total_ideas', 0)
        if total_ideas == 0:
            return 0.0
        
        progress_distribution = stats.get('progress_distribution', {})
        total_progress = 0
        
        for step_key, count in progress_distribution.items():
            step = int(step_key.replace('step_', ''))
            total_progress += step * count
        
        max_possible_progress = total_ideas * self.total_steps
        return (total_progress / max_possible_progress * 100) if max_possible_progress > 0 else 0.0
    
    def _calculate_productivity_score(self, stats: Dict[str, Any]) -> float:
        """Calculate a productivity score based on completion rate and progress."""
        completion_rate = stats.get('completion_rate', 0)
        average_progress = self._calculate_average_progress(stats)
        
        # Weighted score: 70% completion rate, 30% average progress
        productivity_score = (completion_rate * 0.7) + (average_progress * 0.3)
        return round(productivity_score, 2)