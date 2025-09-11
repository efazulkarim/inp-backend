"""
Report repository for report generation data access operations.
Handles report-specific database operations and queries.
"""
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import and_, desc, asc
from datetime import datetime, timedelta

from ..models import Report, IdeaBoard, User
from ..core.logging import get_logger
from ..core.exceptions import DatabaseError, NotFoundError, ValidationError
from .base import BaseRepository

logger = get_logger(__name__)


class ReportRepository(BaseRepository[Report]):
    """Repository for Report model operations."""
    
    def __init__(self, db: Session):
        super().__init__(db, Report)
    
    async def get_user_reports(self, user_id: int, skip: int = 0, limit: int = 100) -> List[Report]:
        """Get all reports for a specific user."""
        try:
            reports = await self.get_multi(
                skip=skip,
                limit=limit,
                filters={'user_id': user_id},
                order_by='created_at',
                order_desc=True
            )
            self.logger.debug(f"Retrieved {len(reports)} reports for user {user_id}")
            return reports
        
        except Exception as e:
            self.logger.error(f"Failed to get reports for user {user_id}: {str(e)}")
            raise DatabaseError("Failed to retrieve user reports")
    
    async def get_idea_reports(self, idea_id: int) -> List[Report]:
        """Get all reports for a specific idea."""
        try:
            reports = await self.get_multi(
                filters={'idea_id': idea_id},
                order_by='created_at',
                order_desc=True
            )
            self.logger.debug(f"Retrieved {len(reports)} reports for idea {idea_id}")
            return reports
        
        except Exception as e:
            self.logger.error(f"Failed to get reports for idea {idea_id}: {str(e)}")
            raise DatabaseError("Failed to retrieve idea reports")
    
    async def get_reports_by_status(self, status: str, skip: int = 0, limit: int = 100) -> List[Report]:
        """Get reports by status."""
        try:
            reports = await self.get_multi(
                skip=skip,
                limit=limit,
                filters={'status': status},
                order_by='created_at',
                order_desc=True
            )
            self.logger.debug(f"Retrieved {len(reports)} reports with status: {status}")
            return reports
        
        except Exception as e:
            self.logger.error(f"Failed to get reports by status {status}: {str(e)}")
            raise DatabaseError("Failed to retrieve reports by status")
    
    async def get_user_idea_report(self, user_id: int, idea_id: int) -> Optional[Report]:
        """Get the most recent report for a specific user and idea."""
        try:
            report = (
                self.db.query(Report)
                .filter(
                    and_(
                        Report.user_id == user_id,
                        Report.idea_id == idea_id
                    )
                )
                .order_by(desc(Report.created_at))
                .first()
            )
            
            if report:
                self.logger.debug(f"Retrieved report for user {user_id} and idea {idea_id}")
            return report
        
        except SQLAlchemyError as e:
            self.logger.error(f"Failed to get report for user {user_id} and idea {idea_id}: {str(e)}")
            raise DatabaseError("Failed to retrieve user idea report")
    
    async def create_report(self, report_data: dict) -> Report:
        """Create a new report with validation."""
        try:
            # Validate required fields
            if not report_data.get('user_id'):
                raise ValidationError("User ID is required")
            if not report_data.get('idea_id'):
                raise ValidationError("Idea ID is required")
            
            # Set default values
            report_data.setdefault('status', 'queued')
            report_data.setdefault('created_at', datetime.utcnow())
            report_data.setdefault('updated_at', datetime.utcnow())
            
            report = await self.create(report_data)
            self.logger.info(f"Created new report {report.id} for user {report.user_id}, idea {report.idea_id}")
            return report
        
        except ValidationError:
            raise
        except Exception as e:
            self.logger.error(f"Failed to create report: {str(e)}")
            raise DatabaseError("Failed to create report")
    
    async def update_report_status(self, report_id: int, status: str, error_message: Optional[str] = None) -> Report:
        """Update report status and optional error message."""
        try:
            update_data = {
                'status': status,
                'updated_at': datetime.utcnow()
            }
            
            if error_message:
                update_data['error_message'] = error_message
            
            report = await self.update(report_id, update_data)
            self.logger.info(f"Updated report {report_id} status to: {status}")
            return report
        
        except Exception as e:
            self.logger.error(f"Failed to update report status {report_id}: {str(e)}")
            raise DatabaseError("Failed to update report status")
    
    async def complete_report(self, report_id: int, content: dict) -> Report:
        """Mark report as completed with content."""
        try:
            update_data = {
                'status': 'completed',
                'content': content,
                'updated_at': datetime.utcnow(),
                'error_message': None  # Clear any previous error
            }
            
            report = await self.update(report_id, update_data)
            self.logger.info(f"Completed report {report_id}")
            return report
        
        except Exception as e:
            self.logger.error(f"Failed to complete report {report_id}: {str(e)}")
            raise DatabaseError("Failed to complete report")
    
    async def fail_report(self, report_id: int, error_message: str) -> Report:
        """Mark report as failed with error message."""
        try:
            update_data = {
                'status': 'failed',
                'error_message': error_message,
                'updated_at': datetime.utcnow()
            }
            
            report = await self.update(report_id, update_data)
            self.logger.info(f"Failed report {report_id}: {error_message}")
            return report
        
        except Exception as e:
            self.logger.error(f"Failed to fail report {report_id}: {str(e)}")
            raise DatabaseError("Failed to fail report")
    
    async def get_pending_reports(self, limit: int = 100) -> List[Report]:
        """Get reports that are queued or processing."""
        try:
            reports = await self.get_multi(
                limit=limit,
                filters={'status': ['queued', 'processing']},
                order_by='created_at',
                order_desc=False  # Process oldest first
            )
            self.logger.debug(f"Retrieved {len(reports)} pending reports")
            return reports
        
        except Exception as e:
            self.logger.error(f"Failed to get pending reports: {str(e)}")
            raise DatabaseError("Failed to retrieve pending reports")
    
    async def get_reports_with_details(self, user_id: int, skip: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
        """Get reports with idea and user details."""
        try:
            results = (
                self.db.query(Report, IdeaBoard, User)
                .join(IdeaBoard, Report.idea_id == IdeaBoard.id)
                .join(User, Report.user_id == User.id)
                .filter(Report.user_id == user_id)
                .order_by(desc(Report.created_at))
                .offset(skip)
                .limit(limit)
                .all()
            )
            
            reports_with_details = []
            for report, idea, user in results:
                reports_with_details.append({
                    'report': report,
                    'idea': idea,
                    'user': user
                })
            
            self.logger.debug(f"Retrieved {len(reports_with_details)} reports with details")
            return reports_with_details
        
        except SQLAlchemyError as e:
            self.logger.error(f"Failed to get reports with details: {str(e)}")
            raise DatabaseError("Failed to retrieve reports with details")
    
    async def get_report_statistics(self, user_id: Optional[int] = None) -> Dict[str, Any]:
        """Get report statistics, optionally filtered by user."""
        try:
            filters = {}
            if user_id:
                filters['user_id'] = user_id
            
            total_reports = await self.count(filters)
            
            # Get status distribution
            status_stats = {}
            for status in ['queued', 'processing', 'completed', 'failed']:
                status_filters = filters.copy()
                status_filters['status'] = status
                count = await self.count(status_filters)
                status_stats[status] = count
            
            # Get recent activity (last 7 days)
            seven_days_ago = datetime.utcnow() - timedelta(days=7)
            recent_reports = (
                self.db.query(Report)
                .filter(Report.created_at >= seven_days_ago)
            )
            
            if user_id:
                recent_reports = recent_reports.filter(Report.user_id == user_id)
            
            recent_count = recent_reports.count()
            
            stats = {
                'total_reports': total_reports,
                'status_distribution': status_stats,
                'recent_reports_7_days': recent_count,
                'success_rate': (status_stats['completed'] / total_reports * 100) if total_reports > 0 else 0
            }
            
            self.logger.debug(f"Retrieved report statistics for user {user_id}")
            return stats
        
        except Exception as e:
            self.logger.error(f"Failed to get report statistics: {str(e)}")
            raise DatabaseError("Failed to retrieve report statistics")
    
    async def cleanup_old_failed_reports(self, days_old: int = 30) -> int:
        """Clean up old failed reports."""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)
            
            deleted_count = (
                self.db.query(Report)
                .filter(
                    and_(
                        Report.status == 'failed',
                        Report.created_at < cutoff_date
                    )
                )
                .delete(synchronize_session=False)
            )
            
            self.db.commit()
            self.logger.info(f"Cleaned up {deleted_count} old failed reports")
            return deleted_count
        
        except SQLAlchemyError as e:
            self.db.rollback()
            self.logger.error(f"Failed to cleanup old failed reports: {str(e)}")
            raise DatabaseError("Failed to cleanup old failed reports")
    
    async def get_processing_reports_older_than(self, minutes: int = 30) -> List[Report]:
        """Get reports that have been processing for too long (likely stuck)."""
        try:
            cutoff_time = datetime.utcnow() - timedelta(minutes=minutes)
            
            stuck_reports = (
                self.db.query(Report)
                .filter(
                    and_(
                        Report.status == 'processing',
                        Report.updated_at < cutoff_time
                    )
                )
                .all()
            )
            
            self.logger.debug(f"Found {len(stuck_reports)} potentially stuck reports")
            return stuck_reports
        
        except SQLAlchemyError as e:
            self.logger.error(f"Failed to get stuck reports: {str(e)}")
            raise DatabaseError("Failed to retrieve stuck reports")
    
    async def reset_stuck_reports(self, minutes: int = 30) -> int:
        """Reset stuck processing reports back to queued status."""
        try:
            cutoff_time = datetime.utcnow() - timedelta(minutes=minutes)
            
            reset_count = (
                self.db.query(Report)
                .filter(
                    and_(
                        Report.status == 'processing',
                        Report.updated_at < cutoff_time
                    )
                )
                .update({
                    'status': 'queued',
                    'updated_at': datetime.utcnow(),
                    'error_message': 'Reset from stuck processing state'
                }, synchronize_session=False)
            )
            
            self.db.commit()
            self.logger.info(f"Reset {reset_count} stuck reports")
            return reset_count
        
        except SQLAlchemyError as e:
            self.db.rollback()
            self.logger.error(f"Failed to reset stuck reports: {str(e)}")
            raise DatabaseError("Failed to reset stuck reports")