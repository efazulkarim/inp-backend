"""
User management service for user business logic operations.
Handles user registration, authentication, profile management, and business rules.
"""
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from passlib.context import CryptContext

from ..models import User
from ..core.logging import get_logger
from ..core.exceptions import (
    ValidationError, NotFoundError, ConflictError, 
    AuthenticationError, BusinessLogicError, ErrorContext
)
from ..repositories.dependencies import RepositoryContainer
from .base import BaseService, CRUDService

logger = get_logger(__name__)

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class UserService(BaseService):
    """Service for user management operations."""
    
    def __init__(self, repositories: RepositoryContainer):
        super().__init__(repositories)
    
    async def create_user(self, user_data: Dict[str, Any]) -> User:
        """Create a new user with validation and password hashing."""
        with ErrorContext("create user", self.logger):
            # Validate required fields
            self.validate_required_fields(user_data, ['username', 'email', 'password'])
            
            # Validate and sanitize input
            await self._validate_user_data(user_data)
            user_data = await self._sanitize_user_data(user_data)
            
            # Hash password
            user_data['password'] = self._hash_password(user_data['password'])
            
            # Set default values
            user_data.setdefault('status', 1)
            user_data.setdefault('verified', 0)
            user_data.setdefault('subscription_plan', 'free')
            user_data.setdefault('subscription_status', 'active')
            
            try:
                user = await self.repositories.user.create_user(user_data)
                self.logger.info(f"Created new user: {user.username} ({user.email})")
                return user
            
            except Exception as e:
                self.handle_repository_error("create user", e)
    
    async def authenticate_user(self, username_or_email: str, password: str) -> Optional[User]:
        """Authenticate user by username/email and password."""
        with ErrorContext("authenticate user", self.logger):
            try:
                # Try to find user by username or email
                user = await self.repositories.user.get_by_username(username_or_email)
                if not user:
                    user = await self.repositories.user.get_by_email(username_or_email)
                
                if not user:
                    self.logger.warning(f"Authentication failed: user not found - {username_or_email}")
                    return None
                
                # Check if user is active
                if user.status != 1:
                    self.logger.warning(f"Authentication failed: user inactive - {username_or_email}")
                    raise AuthenticationError("User account is inactive")
                
                # Verify password
                if not self._verify_password(password, user.password):
                    self.logger.warning(f"Authentication failed: invalid password - {username_or_email}")
                    return None
                
                self.logger.info(f"User authenticated successfully: {user.username}")
                return user
            
            except AuthenticationError:
                raise
            except Exception as e:
                self.handle_repository_error("authenticate user", e)
    
    async def get_user_by_id(self, user_id: int) -> User:
        """Get user by ID."""
        with ErrorContext("get user by id", self.logger):
            try:
                user = await self.repositories.user.get_by_id_or_404(user_id)
                return user
            except Exception as e:
                self.handle_repository_error("get user by id", e)
    
    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email address."""
        with ErrorContext("get user by email", self.logger):
            try:
                user = await self.repositories.user.get_by_email(email)
                return user
            except Exception as e:
                self.handle_repository_error("get user by email", e)
    
    async def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username."""
        with ErrorContext("get user by username", self.logger):
            try:
                user = await self.repositories.user.get_by_username(username)
                return user
            except Exception as e:
                self.handle_repository_error("get user by username", e)
    
    async def update_user_profile(self, user_id: int, update_data: Dict[str, Any]) -> User:
        """Update user profile information."""
        with ErrorContext("update user profile", self.logger):
            # Validate update data
            await self._validate_profile_update_data(update_data, user_id)
            update_data = await self._sanitize_user_data(update_data)
            
            # Remove sensitive fields that shouldn't be updated via profile update
            sensitive_fields = ['password', 'status', 'verified', 'stripe_customer_id', 'stripe_subscription_id']
            for field in sensitive_fields:
                update_data.pop(field, None)
            
            try:
                user = await self.repositories.user.update_user(user_id, update_data)
                self.logger.info(f"Updated profile for user {user_id}")
                return user
            
            except Exception as e:
                self.handle_repository_error("update user profile", e)
    
    async def change_password(self, user_id: int, current_password: str, new_password: str) -> User:
        """Change user password with current password verification."""
        with ErrorContext("change password", self.logger):
            # Get current user
            user = await self.get_user_by_id(user_id)
            
            # Verify current password
            if not self._verify_password(current_password, user.password):
                raise AuthenticationError("Current password is incorrect")
            
            # Validate new password
            self._validate_password(new_password)
            
            # Hash new password and update
            hashed_password = self._hash_password(new_password)
            
            try:
                user = await self.repositories.user.update(user_id, {'password': hashed_password})
                self.logger.info(f"Password changed for user {user_id}")
                return user
            
            except Exception as e:
                self.handle_repository_error("change password", e)
    
    async def reset_password(self, email: str, new_password: str) -> User:
        """Reset user password (for password reset functionality)."""
        with ErrorContext("reset password", self.logger):
            # Find user by email
            user = await self.get_user_by_email(email)
            if not user:
                raise NotFoundError("User not found with this email address")
            
            # Validate new password
            self._validate_password(new_password)
            
            # Hash new password and update
            hashed_password = self._hash_password(new_password)
            
            try:
                user = await self.repositories.user.update(user.id, {'password': hashed_password})
                self.logger.info(f"Password reset for user {user.id}")
                return user
            
            except Exception as e:
                self.handle_repository_error("reset password", e)
    
    async def activate_user(self, user_id: int) -> User:
        """Activate a user account."""
        with ErrorContext("activate user", self.logger):
            try:
                user = await self.repositories.user.activate_user(user_id)
                self.logger.info(f"Activated user {user_id}")
                return user
            except Exception as e:
                self.handle_repository_error("activate user", e)
    
    async def deactivate_user(self, user_id: int) -> User:
        """Deactivate a user account."""
        with ErrorContext("deactivate user", self.logger):
            try:
                user = await self.repositories.user.deactivate_user(user_id)
                self.logger.info(f"Deactivated user {user_id}")
                return user
            except Exception as e:
                self.handle_repository_error("deactivate user", e)
    
    async def verify_user(self, user_id: int) -> User:
        """Mark a user as verified."""
        with ErrorContext("verify user", self.logger):
            try:
                user = await self.repositories.user.verify_user(user_id)
                self.logger.info(f"Verified user {user_id}")
                return user
            except Exception as e:
                self.handle_repository_error("verify user", e)
    
    async def update_subscription_info(self, user_id: int, subscription_data: Dict[str, Any]) -> User:
        """Update user subscription information."""
        with ErrorContext("update subscription info", self.logger):
            # Validate subscription data
            await self._validate_subscription_data(subscription_data)
            
            try:
                user = await self.repositories.user.update_subscription_info(user_id, subscription_data)
                self.logger.info(f"Updated subscription info for user {user_id}")
                return user
            
            except Exception as e:
                self.handle_repository_error("update subscription info", e)
    
    async def get_users_by_subscription_plan(self, plan: str, skip: int = 0, limit: int = 100) -> List[User]:
        """Get users by subscription plan."""
        with ErrorContext("get users by subscription plan", self.logger):
            try:
                users = await self.repositories.user.get_users_by_subscription_plan(plan, skip, limit)
                return users
            except Exception as e:
                self.handle_repository_error("get users by subscription plan", e)
    
    async def search_users(self, search_term: str, skip: int = 0, limit: int = 100) -> List[User]:
        """Search users by username, email, or name."""
        with ErrorContext("search users", self.logger):
            if not search_term or len(search_term.strip()) < 2:
                raise ValidationError("Search term must be at least 2 characters long")
            
            try:
                users = await self.repositories.user.search_users(search_term.strip(), skip, limit)
                return users
            except Exception as e:
                self.handle_repository_error("search users", e)
    
    async def get_user_statistics(self) -> Dict[str, Any]:
        """Get user statistics."""
        with ErrorContext("get user statistics", self.logger):
            try:
                stats = await self.repositories.user.get_user_statistics()
                return stats
            except Exception as e:
                self.handle_repository_error("get user statistics", e)
    
    async def check_username_availability(self, username: str, exclude_user_id: Optional[int] = None) -> bool:
        """Check if username is available."""
        with ErrorContext("check username availability", self.logger):
            try:
                exists = await self.repositories.user.check_username_exists(username, exclude_user_id)
                return not exists
            except Exception as e:
                self.handle_repository_error("check username availability", e)
    
    async def check_email_availability(self, email: str, exclude_user_id: Optional[int] = None) -> bool:
        """Check if email is available."""
        with ErrorContext("check email availability", self.logger):
            try:
                exists = await self.repositories.user.check_email_exists(email, exclude_user_id)
                return not exists
            except Exception as e:
                self.handle_repository_error("check email availability", e)
    
    # Private helper methods
    async def _validate_user_data(self, user_data: Dict[str, Any]) -> None:
        """Validate user data for creation/update."""
        # Validate username
        if 'username' in user_data:
            username = user_data['username']
            self.validate_string_length(username, 'username', min_length=3, max_length=50)
            
            # Check for invalid characters
            import re
            if not re.match(r'^[a-zA-Z0-9_]+$', username):
                raise ValidationError("Username can only contain letters, numbers, and underscores")
        
        # Validate email
        if 'email' in user_data:
            self.validate_email_format(user_data['email'])
        
        # Validate password
        if 'password' in user_data:
            self._validate_password(user_data['password'])
        
        # Validate names
        for field in ['first_name', 'last_name']:
            if field in user_data and user_data[field]:
                self.validate_string_length(user_data[field], field, min_length=1, max_length=100)
        
        # Validate phone
        if 'phone' in user_data and user_data['phone']:
            phone = user_data['phone']
            if len(phone) > 20:
                raise ValidationError("Phone number is too long")
    
    async def _validate_profile_update_data(self, update_data: Dict[str, Any], user_id: int) -> None:
        """Validate profile update data."""
        await self._validate_user_data(update_data)
        
        # Additional validation for updates
        if 'username' in update_data:
            available = await self.check_username_availability(update_data['username'], user_id)
            if not available:
                raise ConflictError("Username is already taken")
        
        if 'email' in update_data:
            available = await self.check_email_availability(update_data['email'], user_id)
            if not available:
                raise ConflictError("Email is already registered")
    
    async def _validate_subscription_data(self, subscription_data: Dict[str, Any]) -> None:
        """Validate subscription data."""
        valid_plans = ['free', 'basic', 'pro']
        valid_statuses = ['active', 'canceled', 'past_due', 'unpaid']
        
        if 'subscription_plan' in subscription_data:
            plan = subscription_data['subscription_plan']
            if plan not in valid_plans:
                raise ValidationError(f"Invalid subscription plan. Must be one of: {valid_plans}")
        
        if 'subscription_status' in subscription_data:
            status = subscription_data['subscription_status']
            if status not in valid_statuses:
                raise ValidationError(f"Invalid subscription status. Must be one of: {valid_statuses}")
    
    async def _sanitize_user_data(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize user data."""
        sanitized = {}
        
        for key, value in user_data.items():
            if isinstance(value, str):
                sanitized[key] = self.sanitize_string(value)
            else:
                sanitized[key] = value
        
        # Normalize email to lowercase
        if 'email' in sanitized:
            sanitized['email'] = sanitized['email'].lower()
        
        return sanitized
    
    def _validate_password(self, password: str) -> None:
        """Validate password strength."""
        if len(password) < 8:
            raise ValidationError("Password must be at least 8 characters long")
        
        if len(password) > 128:
            raise ValidationError("Password is too long")
        
        # Check for at least one letter and one number
        import re
        if not re.search(r'[A-Za-z]', password):
            raise ValidationError("Password must contain at least one letter")
        
        if not re.search(r'\d', password):
            raise ValidationError("Password must contain at least one number")
    
    def _hash_password(self, password: str) -> str:
        """Hash a password."""
        return pwd_context.hash(password)
    
    def _verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash."""
        return pwd_context.verify(plain_password, hashed_password)