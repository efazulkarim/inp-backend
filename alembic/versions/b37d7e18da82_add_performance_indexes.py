"""add_performance_indexes

Revision ID: b37d7e18da82
Revises: be8f733f36e5
Create Date: 2025-09-02 20:08:31.855276

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b37d7e18da82'
down_revision: Union[str, None] = 'be8f733f36e5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add performance indexes for better query performance
    
    # Users table indexes
    op.create_index('idx_users_email', 'users', ['email'])
    op.create_index('idx_users_username', 'users', ['username'])
    op.create_index('idx_users_status', 'users', ['status'])
    op.create_index('idx_users_verified', 'users', ['verified'])
    op.create_index('idx_users_subscription_plan', 'users', ['subscription_plan'])
    op.create_index('idx_users_stripe_customer_id', 'users', ['stripe_customer_id'])
    
    # IdeaBoard table indexes
    op.create_index('idx_ideaboard_user_id', 'ideaboard', ['user_id'])
    op.create_index('idx_ideaboard_pin', 'ideaboard', ['pin'])
    op.create_index('idx_ideaboard_is_complete', 'ideaboard', ['is_complete'])
    op.create_index('idx_ideaboard_current_step', 'ideaboard', ['current_step'])
    op.create_index('idx_ideaboard_user_pin', 'ideaboard', ['user_id', 'pin'])
    op.create_index('idx_ideaboard_user_complete', 'ideaboard', ['user_id', 'is_complete'])
    
    # Answers table indexes
    op.create_index('idx_answers_ideaboard_id', 'answers', ['ideaBoard_id'])
    op.create_index('idx_answers_user_id', 'answers', ['user_id'])
    op.create_index('idx_answers_question_id', 'answers', ['question_id'])
    op.create_index('idx_answers_user_idea', 'answers', ['user_id', 'ideaBoard_id'])
    op.create_index('idx_answers_user_question', 'answers', ['user_id', 'question_id'])
    
    # Reports table indexes
    op.create_index('idx_reports_idea_id', 'reports', ['idea_id'])
    op.create_index('idx_reports_user_id', 'reports', ['user_id'])
    op.create_index('idx_reports_status', 'reports', ['status'])
    op.create_index('idx_reports_created_at', 'reports', ['created_at'])
    op.create_index('idx_reports_idea_status', 'reports', ['idea_id', 'status'])
    op.create_index('idx_reports_user_status', 'reports', ['user_id', 'status'])
    
    # Questionnaire table indexes
    op.create_index('idx_questionnaire_status', 'questionnaire', ['status'])
    op.create_index('idx_questionnaire_uuid', 'questionnaire', ['q_uuid'])
    op.create_index('idx_questionnaire_input_type', 'questionnaire', ['input_type'])
    
    # Customer Persona table indexes
    op.create_index('idx_customer_personas_user_id', 'customer_personas', ['user_id'])
    op.create_index('idx_customer_personas_created_at', 'customer_personas', ['created_at'])
    
    # Customer Persona Questionnaire indexes
    op.create_index('idx_customer_persona_questionnaire_status', 'customer_persona_questionnaire', ['status'])
    op.create_index('idx_customer_persona_questionnaire_category', 'customer_persona_questionnaire', ['category'])
    op.create_index('idx_customer_persona_questionnaire_uuid', 'customer_persona_questionnaire', ['q_uuid'])
    
    # Idea Persona Link indexes
    op.create_index('idx_idea_persona_links_idea_id', 'idea_persona_links', ['idea_id'])
    op.create_index('idx_idea_persona_links_persona_id', 'idea_persona_links', ['persona_id'])
    op.create_index('idx_idea_persona_links_user_id', 'idea_persona_links', ['user_id'])
    
    # Subscription table indexes
    op.create_index('idx_subscription_user_id', 'subscription', ['user_id'])
    op.create_index('idx_subscription_is_active', 'subscription', ['is_active'])
    op.create_index('idx_subscription_is_expired', 'subscription', ['is_expired'])
    op.create_index('idx_subscription_expiry_date', 'subscription', ['expiry_date'])


def downgrade() -> None:
    # Remove performance indexes
    
    # Users table indexes
    op.drop_index('idx_users_email', 'users')
    op.drop_index('idx_users_username', 'users')
    op.drop_index('idx_users_status', 'users')
    op.drop_index('idx_users_verified', 'users')
    op.drop_index('idx_users_subscription_plan', 'users')
    op.drop_index('idx_users_stripe_customer_id', 'users')
    
    # IdeaBoard table indexes
    op.drop_index('idx_ideaboard_user_id', 'ideaboard')
    op.drop_index('idx_ideaboard_pin', 'ideaboard')
    op.drop_index('idx_ideaboard_is_complete', 'ideaboard')
    op.drop_index('idx_ideaboard_current_step', 'ideaboard')
    op.drop_index('idx_ideaboard_user_pin', 'ideaboard')
    op.drop_index('idx_ideaboard_user_complete', 'ideaboard')
    
    # Answers table indexes
    op.drop_index('idx_answers_ideaboard_id', 'answers')
    op.drop_index('idx_answers_user_id', 'answers')
    op.drop_index('idx_answers_question_id', 'answers')
    op.drop_index('idx_answers_user_idea', 'answers')
    op.drop_index('idx_answers_user_question', 'answers')
    
    # Reports table indexes
    op.drop_index('idx_reports_idea_id', 'reports')
    op.drop_index('idx_reports_user_id', 'reports')
    op.drop_index('idx_reports_status', 'reports')
    op.drop_index('idx_reports_created_at', 'reports')
    op.drop_index('idx_reports_idea_status', 'reports')
    op.drop_index('idx_reports_user_status', 'reports')
    
    # Questionnaire table indexes
    op.drop_index('idx_questionnaire_status', 'questionnaire')
    op.drop_index('idx_questionnaire_uuid', 'questionnaire')
    op.drop_index('idx_questionnaire_input_type', 'questionnaire')
    
    # Customer Persona table indexes
    op.drop_index('idx_customer_personas_user_id', 'customer_personas')
    op.drop_index('idx_customer_personas_created_at', 'customer_personas')
    
    # Customer Persona Questionnaire indexes
    op.drop_index('idx_customer_persona_questionnaire_status', 'customer_persona_questionnaire')
    op.drop_index('idx_customer_persona_questionnaire_category', 'customer_persona_questionnaire')
    op.drop_index('idx_customer_persona_questionnaire_uuid', 'customer_persona_questionnaire')
    
    # Idea Persona Link indexes
    op.drop_index('idx_idea_persona_links_idea_id', 'idea_persona_links')
    op.drop_index('idx_idea_persona_links_persona_id', 'idea_persona_links')
    op.drop_index('idx_idea_persona_links_user_id', 'idea_persona_links')
    
    # Subscription table indexes
    op.drop_index('idx_subscription_user_id', 'subscription')
    op.drop_index('idx_subscription_is_active', 'subscription')
    op.drop_index('idx_subscription_is_expired', 'subscription')
    op.drop_index('idx_subscription_expiry_date', 'subscription')
