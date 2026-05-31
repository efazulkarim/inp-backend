"""
User repository for user data access operations.
Handles user-specific database operations and queries.
"""
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from ..models import User
from ..core.logging import get_logger
from ..core.exceptions import DatabaseError, NotFoundError, ConflictError
from .base import BaseRepository

logger = get_logger(__name__)


class UserRepository(BaseRepository[User]):
    """Repository for User model operations."""
    
    def __init__(self, db: Session):
        super().__init__(db, User)
    
    async def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email address."""
        try:
            user = self.db.query(User).filter(User.email == email).first()
            if user:
                self.logger.debug(f"Retrieved user by email: {email}")
            return user
        
        except SQLAlchemyError as e:
            self.logger.error(f"Failed to get user by email {email}: {str(e)}")
            raise DatabaseError("Failed to retrieve user by email")
    
    async def get_by_username(self, username: str) -> Optional[User]:
        """Get user by username."""
        try:
            user = self.db.query(User).filter(User.username == username).first()
            if user:
                self.logger.debug(f"Retrieved user by username: {username}")
            return user
        
        except SQLAlchemyError as e:
            self.logger.error(f"Failed to get user by username {username}: {str(e)}")
            raise DatabaseError("Failed to retrieve user by username")
    
    async def get_by_stripe_customer_id(self, stripe_customer_id: str) -> Optional[User]:
        """Get user by Stripe customer ID."""
        try:
            user = self.db.query(User).filter(User.stripe_customer_id == stripe_customer_id).first()
            if user:
                self.logger.debug(f"Retrieved user by Stripe customer ID: {stripe_customer_id}")
            return user
        
        except SQLAlchemyError as e:
            self.logger.error(f"Failed to get user by Stripe customer ID {stripe_customer_id}: {str(e)}")
            raise DatabaseError("Failed to retrieve user by Stripe customer ID")
    
    async def check_email_exists(self, email: str, exclude_user_id: Optional[int] = None) -> bool:
        """Check if email already exists, optionally excluding a specific user."""
        try:
            query = self.db.query(User).filter(User.email == email)
            if exclude_user_id:
                query = query.filter(User.id != exclude_user_id)
            
            exists = query.first() is not None
            return exists
        
        except SQLAlchemyError as e:
            self.logger.error(f"Failed to check email existence {email}: {str(e)}")
            raise DatabaseError("Failed to check email existence")
    
    async def check_username_exists(self, username: str, exclude_user_id: Optional[int] = None) -> bool:
        """Check if username already exists, optionally excluding a specific user."""
        try:
            query = self.db.query(User).filter(User.username == username)
            if exclude_user_id:
                query = query.filter(User.id != exclude_user_id)
            
            exists = query.first() is not None
            return exists
        
        except SQLAlchemyError as e:
            self.logger.error(f"Failed to check username existence {username}: {str(e)}")
            raise DatabaseError("Failed to check username existence")
    
    async def create_user(self, user_data: dict) -> User:
        """Create a new user with validation."""
        try:
            # Check for existing email
            if await self.check_email_exists(user_data.get('email')):
                raise ConflictError("Email already registered")
            
            # Check for existing username
            if await self.check_username_exists(user_data.get('username')):
                raise ConflictError("Username already taken")
            
            user = await self.create(user_data)
            self.logger.info(f"Created new user: {user.username} ({user.email})")
            return user
        
        except ConflictError:
            raise
        except Exception as e:
            self.logger.error(f"Failed to create user: {str(e)}")
            raise DatabaseError("Failed to create user")
    
    async def update_user(self, user_id: int, user_data: dict) -> User:
        """Update user with validation."""
        try:
            # Check for existing email if email is being updated
            if 'email' in user_data:
                if await self.check_email_exists(user_data['email'], exclude_user_id=user_id):
                    raise ConflictError("Email already registered")
            
            # Check for existing username if username is being updated
            if 'username' in user_data:
                if await self.check_username_exists(user_data['username'], exclude_user_id=user_id):
                    raise ConflictError("Username already taken")
            
            user = await self.update(user_id, user_data)
            self.logger.info(f"Updated user: {user.username} ({user.email})")
            return user
        
        except ConflictError:
            raise
        except Exception as e:
            self.logger.error(f"Failed to update user {user_id}: {str(e)}")
            raise DatabaseError("Failed to update user")
    
    async def get_active_users(self, skip: int = 0, limit: int = 100) -> List[User]:
        """Get active users (status = 1)."""
        try:
            users = await self.get_multi(
                skip=skip,
                limit=limit,
                filters={'status': 1},
                order_by='id',
                order_desc=True
            )
            return users
        
        except Exception as e:
            self.logger.error(f"Failed to get active users: {str(e)}")
            raise DatabaseError("Failed to retrieve active users")
    
    async def get_verified_users(self, skip: int = 0, limit: int = 100) -> List[User]:
        """Get verified users (verified = 1)."""
        try:
            users = await self.get_multi(
                skip=skip,
                limit=limit,
                filters={'verified': 1},
                order_by='id',
                order_desc=True
            )
            return users
        
        except Exception as e:
            self.logger.error(f"Failed to get verified users: {str(e)}")
            raise DatabaseError("Failed to retrieve verified users")
    
    async def get_users_by_subscription_plan(self, plan: str, skip: int = 0, limit: int = 100) -> List[User]:
        """Get users by subscription plan."""
        try:
            users = await self.get_multi(
                skip=skip,
                limit=limit,
                filters={'subscription_plan': plan},
                order_by='id',
                order_desc=True
            )
            return users
        
        except Exception as e:
            self.logger.error(f"Failed to get users by subscription plan {plan}: {str(e)}")
            raise DatabaseError("Failed to retrieve users by subscription plan")
    
    async def update_subscription_info(self, user_id: int, subscription_data: dict) -> User:
        """Update user subscription information."""
        try:
            allowed_fields = [
                'subscription_plan', 'subscription_status', 'stripe_customer_id',
                'stripe_subscription_id', 'current_period_end', 'trial_end'
            ]
            
            # Filter to only allowed subscription fields
            filtered_data = {k: v for k, v in subscription_data.items() if k in allowed_fields}
            
            user = await self.update(user_id, filtered_data)
            self.logger.info(f"Updated subscription info for user {user_id}")
            return user
        
        except Exception as e:
            self.logger.error(f"Failed to update subscription info for user {user_id}: {str(e)}")
            raise DatabaseError("Failed to update subscription information")
    
    async def activate_user(self, user_id: int) -> User:
        """Activate a user account."""
        try:
            user = await self.update(user_id, {'status': 1})
            self.logger.info(f"Activated user {user_id}")
            return user
        
        except Exception as e:
            self.logger.error(f"Failed to activate user {user_id}: {str(e)}")
            raise DatabaseError("Failed to activate user")
    
    async def deactivate_user(self, user_id: int) -> User:
        """Deactivate a user account."""
        try:
            user = await self.update(user_id, {'status': 0})
            self.logger.info(f"Deactivated user {user_id}")
            return user
        
        except Exception as e:
            self.logger.error(f"Failed to deactivate user {user_id}: {str(e)}")
            raise DatabaseError("Failed to deactivate user")
    
    async def verify_user(self, user_id: int) -> User:
        """Mark a user as verified."""
        try:
            user = await self.update(user_id, {'verified': 1})
            self.logger.info(f"Verified user {user_id}")
            return user
        
        except Exception as e:
            self.logger.error(f"Failed to verify user {user_id}: {str(e)}")
            raise DatabaseError("Failed to verify user")
    
    async def search_users(self, search_term: str, skip: int = 0, limit: int = 100) -> List[User]:
        """Search users by username, email, first name, or last name."""
        try:
            search_pattern = f"%{search_term}%"
            users = (
                self.db.query(User)
                .filter(
                    (User.username.like(search_pattern)) |
                    (User.email.like(search_pattern)) |
                    (User.first_name.like(search_pattern)) |
                    (User.last_name.like(search_pattern))
                )
                .offset(skip)
                .limit(limit)
                .all()
            )
            
            self.logger.debug(f"Found {len(users)} users matching search term: {search_term}")
            return users
        
        except SQLAlchemyError as e:
            self.logger.error(f"Failed to search users with term {search_term}: {str(e)}")
            raise DatabaseError("Failed to search users")
    
    async def get_user_statistics(self) -> dict:
        """Get user statistics."""
        try:
            total_users = await self.count()
            active_users = await self.count({'status': 1})
            verified_users = await self.count({'verified': 1})
            
            # Get subscription plan distribution
            subscription_stats = {}
            for plan in ['free', 'basic', 'pro']:
                count = await self.count({'subscription_plan': plan})
                subscription_stats[plan] = count
            
            stats = {
                'total_users': total_users,
                'active_users': active_users,
                'verified_users': verified_users,
                'subscription_distribution': subscription_stats
            }
            
            self.logger.debug("Retrieved user statistics")
            return stats
        
        except Exception as e:
            self.logger.error(f"Failed to get user statistics: {str(e)}")
            raise DatabaseError("Failed to retrieve user statistics")