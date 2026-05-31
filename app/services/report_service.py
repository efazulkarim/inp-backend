"""
Report Service

Handles business logic for report generation and management.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.services.base import BaseService
from app.repositories.report_repository import ReportRepository
from app.repositories.user_repository import UserRepository
from app.repositories.ideaboard_repository import IdeaBoardRepository
from app.models import Report, User, IdeaBoard
from app.schemas import ReportCreate, ReportUpdate
from app.core.exceptions import ValidationError, NotFoundError, BusinessLogicError
from app.core.logging import get_logger

logger = get_logger(__name__)


class ReportService(BaseService):
    """Service for report business logic."""
    
    def __init__(
        self,
        db: Session,
        report_repo: ReportRepository,
        user_repo: UserRepository,
        ideaboard_repo: IdeaBoardRepository
    ):
        super().__init__(db)
        self.report_repo = report_repo
        self.user_repo = user_repo
        self.ideaboard_repo = ideaboard_repo
    
    def get_report_by_id(self, report_id: int) -> Optional[Report]:
        """Get report by ID."""
        try:
            report = self.report_repo.get_by_id(report_id)
            if not report:
                raise NotFoundError(f"Report with ID {report_id} not found")
            return report
        except Exception as e:
            logger.error(f"Error getting report {report_id}: {str(e)}")
            raise
    
    def get_reports_by_user(self, user_id: int, status: Optional[str] = None) -> List[Report]:
        """Get all reports for a user, optionally filtered by status."""
        try:
            # Verify user exists
            user = self.user_repo.get_by_id(user_id)
            if not user:
                raise NotFoundError(f"User with ID {user_id} not found")
            
            if status:
                return self.report_repo.get_by_user_and_status(user_id, status)
            else:
                return self.report_repo.get_by_user_id(user_id)
                
        except Exception as e:
            logger.error(f"Error getting reports for user {user_id}: {str(e)}")
            raise
    
    def create_report(self, user_id: int, report_data: ReportCreate) -> Report:
        """Create a new report."""
        try:
            # Verify user exists
            user = self.user_repo.get_by_id(user_id)
            if not user:
                raise NotFoundError(f"User with ID {user_id} not found")
            
            # Validate report data
            self._validate_report_data(report_data)
            
            # Check for duplicate reports
            if report_data.report_type:
                existing_report = self.report_repo.get_recent_report_by_type(
                    user_id, report_data.report_type
                )
                if existing_report and self._is_recent_report(existing_report):
                    raise BusinessLogicError(
                        f"A {report_data.report_type} report was already generated recently. "
                        "Please wait before generating another."
                    )
            
            # Create report with initial status
            report_dict = report_data.dict()
            report_dict.update({
                "user_id": user_id,
                "status": "pending",
                "created_at": datetime.utcnow()
            })
            
            report = self.report_repo.create(report_dict)
            
            # Start report generation process
            self._initiate_report_generation(report)
            
            logger.info(f"Created report {report.id} for user {user_id}")
            return report
            
        except Exception as e:
            logger.error(f"Error creating report for user {user_id}: {str(e)}")
            raise
    
    def update_report_status(self, report_id: int, status: str, content: Optional[str] = None) -> Report:
        """Update report status and optionally content."""
        try:
            # Verify report exists
            report = self.get_report_by_id(report_id)
            
            # Validate status transition
            self._validate_status_transition(report.status, status)
            
            update_data = {"status": status}
            if content is not None:
                update_data["content"] = content
            
            if status == "completed":
                update_data["completed_at"] = datetime.utcnow()
            elif status == "failed":
                update_data["failed_at"] = datetime.utcnow()
            
            updated_report = self.report_repo.update(report_id, update_data)
            
            logger.info(f"Updated report {report_id} status to {status}")
            return updated_report
            
        except Exception as e:
            logger.error(f"Error updating report {report_id} status: {str(e)}")
            raise
    
    def generate_progress_report(self, user_id: int, ideaboard_id: Optional[int] = None) -> Dict[str, Any]:
        """Generate a progress report for user's ideas."""
        try:
            user = self.user_repo.get_by_id(user_id)
            if not user:
                raise NotFoundError(f"User with ID {user_id} not found")
            
            # Get ideas for analysis
            if ideaboard_id:
                ideaboard = self.ideaboard_repo.get_by_id(ideaboard_id)
                if not ideaboard or ideaboard.user_id != user_id:
                    raise NotFoundError(f"IdeaBoard {ideaboard_id} not found for user {user_id}")
                ideas = [ideaboard]
            else:
                ideas = self.ideaboard_repo.get_by_user_id(user_id)
            
            # Calculate progress metrics
            total_ideas = len(ideas)
            completed_ideas = len([idea for idea in ideas if idea.progress == 100])
            in_progress_ideas = len([idea for idea in ideas if 0 < idea.progress < 100])
            not_started_ideas = len([idea for idea in ideas if idea.progress == 0])
            
            # Calculate average progress
            avg_progress = sum(idea.progress for idea in ideas) / total_ideas if total_ideas > 0 else 0
            
            # Get recent activity (last 30 days)
            thirty_days_ago = datetime.utcnow() - timedelta(days=30)
            recent_ideas = [idea for idea in ideas if idea.created_at >= thirty_days_ago]
            
            # Generate insights
            insights = self._generate_progress_insights(ideas, avg_progress, recent_ideas)
            
            report_content = {
                "report_type": "progress",
                "generated_at": datetime.utcnow().isoformat(),
                "user_id": user_id,
                "ideaboard_id": ideaboard_id,
                "summary": {
                    "total_ideas": total_ideas,
                    "completed_ideas": completed_ideas,
                    "in_progress_ideas": in_progress_ideas,
                    "not_started_ideas": not_started_ideas,
                    "average_progress": round(avg_progress, 2),
                    "completion_rate": round((completed_ideas / total_ideas * 100), 2) if total_ideas > 0 else 0
                },
                "recent_activity": {
                    "new_ideas_last_30_days": len(recent_ideas),
                    "ideas_completed_last_30_days": len([
                        idea for idea in recent_ideas if idea.progress == 100
                    ])
                },
                "insights": insights,
                "recommendations": self._generate_recommendations(ideas, avg_progress)
            }
            
            return report_content
            
        except Exception as e:
            logger.error(f"Error generating progress report for user {user_id}: {str(e)}")
            raise
    
    def generate_productivity_report(self, user_id: int, days: int = 30) -> Dict[str, Any]:
        """Generate a productivity report for the specified time period."""
        try:
            user = self.user_repo.get_by_id(user_id)
            if not user:
                raise NotFoundError(f"User with ID {user_id} not found")
            
            # Get date range
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)
            
            # Get ideas in the time period
            ideas = self.ideaboard_repo.get_by_user_id(user_id)
            period_ideas = [
                idea for idea in ideas 
                if start_date <= idea.created_at <= end_date
            ]
            
            # Calculate productivity metrics
            ideas_created = len(period_ideas)
            ideas_completed = len([idea for idea in period_ideas if idea.progress == 100])
            total_progress_made = sum(idea.progress for idea in period_ideas)
            
            # Calculate daily averages
            daily_avg_ideas = ideas_created / days if days > 0 else 0
            daily_avg_progress = total_progress_made / days if days > 0 else 0
            
            # Get productivity trends
            trends = self._calculate_productivity_trends(user_id, days)
            
            report_content = {
                "report_type": "productivity",
                "generated_at": datetime.utcnow().isoformat(),
                "user_id": user_id,
                "period": {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                    "days": days
                },
                "metrics": {
                    "ideas_created": ideas_created,
                    "ideas_completed": ideas_completed,
                    "total_progress_made": total_progress_made,
                    "daily_avg_ideas": round(daily_avg_ideas, 2),
                    "daily_avg_progress": round(daily_avg_progress, 2),
                    "completion_rate": round((ideas_completed / ideas_created * 100), 2) if ideas_created > 0 else 0
                },
                "trends": trends,
                "productivity_score": self._calculate_productivity_score(
                    ideas_created, ideas_completed, total_progress_made, days
                )
            }
            
            return report_content
            
        except Exception as e:
            logger.error(f"Error generating productivity report for user {user_id}: {str(e)}")
            raise
    
    def delete_report(self, report_id: int) -> bool:
        """Delete a report."""
        try:
            # Verify report exists
            report = self.get_report_by_id(report_id)
            
            # Delete report
            success = self.report_repo.delete(report_id)
            
            if success:
                logger.info(f"Deleted report {report_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error deleting report {report_id}: {str(e)}")
            raise
    
    def cleanup_old_reports(self, days_old: int = 90) -> int:
        """Clean up reports older than specified days."""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)
            deleted_count = self.report_repo.cleanup_old_reports(cutoff_date)
            
            logger.info(f"Cleaned up {deleted_count} reports older than {days_old} days")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Error cleaning up old reports: {str(e)}")
            raise
    
    def _validate_report_data(self, data: ReportCreate) -> None:
        """Validate report creation data."""
        if not data.report_type or len(data.report_type.strip()) < 3:
            raise ValidationError("Report type must be at least 3 characters long")
        
        valid_types = ["progress", "productivity", "summary", "analytics"]
        if data.report_type not in valid_types:
            raise ValidationError(f"Report type must be one of: {', '.join(valid_types)}")
    
    def _validate_status_transition(self, current_status: str, new_status: str) -> None:
        """Validate report status transitions."""
        valid_transitions = {
            "pending": ["processing", "failed"],
            "processing": ["completed", "failed"],
            "completed": [],  # Final state
            "failed": ["pending"]  # Can retry
        }
        
        if new_status not in valid_transitions.get(current_status, []):
            raise ValidationError(
                f"Invalid status transition from {current_status} to {new_status}"
            )
    
    def _is_recent_report(self, report: Report, hours: int = 1) -> bool:
        """Check if a report was generated recently."""
        if not report.created_at:
            return False
        
        time_diff = datetime.utcnow() - report.created_at
        return time_diff < timedelta(hours=hours)
    
    def _initiate_report_generation(self, report: Report) -> None:
        """Initiate the report generation process."""
        try:
            # Update status to processing
            self.report_repo.update(report.id, {"status": "processing"})
            
            # Generate report content based on type
            if report.report_type == "progress":
                content = self.generate_progress_report(report.user_id)
            elif report.report_type == "productivity":
                content = self.generate_productivity_report(report.user_id)
            else:
                content = {"message": f"Report type {report.report_type} not implemented yet"}
            
            # Update report with content and mark as completed
            self.report_repo.update(report.id, {
                "content": str(content),  # Convert to string for storage
                "status": "completed",
                "completed_at": datetime.utcnow()
            })
            
        except Exception as e:
            # Mark report as failed
            self.report_repo.update(report.id, {
                "status": "failed",
                "failed_at": datetime.utcnow(),
                "error_message": str(e)
            })
            logger.error(f"Report generation failed for report {report.id}: {str(e)}")
    
    def _generate_progress_insights(self, ideas: List[IdeaBoard], avg_progress: float, recent_ideas: List[IdeaBoard]) -> List[str]:
        """Generate insights based on progress data."""
        insights = []
        
        if avg_progress > 75:
            insights.append("Excellent progress! You're consistently moving your ideas forward.")
        elif avg_progress > 50:
            insights.append("Good progress on your ideas. Consider focusing on completing some projects.")
        else:
            insights.append("Many ideas are in early stages. Consider prioritizing a few for focused development.")
        
        if len(recent_ideas) > 5:
            insights.append("High idea generation rate! Make sure to balance creation with execution.")
        elif len(recent_ideas) == 0:
            insights.append("No new ideas recently. Consider brainstorming sessions to spark creativity.")
        
        return insights
    
    def _generate_recommendations(self, ideas: List[IdeaBoard], avg_progress: float) -> List[str]:
        """Generate recommendations based on idea analysis."""
        recommendations = []
        
        if avg_progress < 30:
            recommendations.append("Focus on completing 1-2 ideas before starting new ones.")
        
        incomplete_ideas = [idea for idea in ideas if idea.progress < 100]
        if len(incomplete_ideas) > 10:
            recommendations.append("Consider archiving or deprioritizing some incomplete ideas.")
        
        if len(ideas) > 0:
            recommendations.append("Set weekly progress goals for your top 3 ideas.")
            recommendations.append("Review and update idea progress regularly.")
        
        return recommendations
    
    def _calculate_productivity_trends(self, user_id: int, days: int) -> Dict[str, Any]:
        """Calculate productivity trends over time."""
        # This is a simplified implementation
        # In a real system, you'd analyze historical data more thoroughly
        return {
            "trend_direction": "stable",
            "trend_strength": "moderate",
            "peak_productivity_day": "Tuesday",
            "suggestions": ["Maintain current momentum", "Consider time-blocking for idea development"]
        }
    
    def _calculate_productivity_score(self, ideas_created: int, ideas_completed: int, total_progress: float, days: int) -> Dict[str, Any]:
        """Calculate a productivity score based on various metrics."""
        # Weighted scoring system
        creation_score = min(ideas_created * 10, 50)  # Max 50 points for creation
        completion_score = ideas_completed * 25  # 25 points per completion
        progress_score = min(total_progress / 10, 25)  # Max 25 points for progress
        
        total_score = creation_score + completion_score + progress_score
        
        # Normalize to 0-100 scale
        normalized_score = min(total_score, 100)
        
        # Determine rating
        if normalized_score >= 80:
            rating = "Excellent"
        elif normalized_score >= 60:
            rating = "Good"
        elif normalized_score >= 40:
            rating = "Fair"
        else:
            rating = "Needs Improvement"
        
        return {
            "score": round(normalized_score, 2),
            "rating": rating,
            "breakdown": {
                "creation": round(creation_score, 2),
                "completion": round(completion_score, 2),
                "progress": round(progress_score, 2)
            }
        }