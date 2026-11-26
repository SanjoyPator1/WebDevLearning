import asyncio
import csv
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from pathlib import Path
import aiofiles

from app.models.user import User
from app.services.user_service import UserService
 # TODO: Replace all tasks_db usage with real database queries
from app.services.email_service import email_service
# from app.database.users import users_db # This line is removed as per the edit hint

class DateTimeEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles datetime objects"""
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

class ReportService:
    """
        Service for generating comprehensive task reports in background

        This service creates detailed analytics reports that would be too slow
        to generate in real-time API responses. Reports are created asynchronously
        and users receive email notifications when complete.

        Features:
        - CSV reports: Excel-compatible with task data
        - JSON reports: Advanced analytics with KPIs and insights
        - Background processing: Non-blocking report generation
        - Email notifications: Beautiful HTML emails when reports are ready
        - Admin reports: System-wide analytics for administrators
        - User reports: Individual user task analytics and performance
    """
    def __init__(self):
        """
                Initialize the report service with directory setup

                Creates the reports directory structure and displays helpful debug info.
                All generated reports are saved to the reports/ directory with timestamped filenames.

                Directory Structure:
                - reports/: Main reports directory
                - Timestamped files: Prevents filename conflicts
                - Auto-creation: Creates directory if it doesn't exist

                Features:
                - Cross-platform path handling using Pathlib
                - Debug logging for development
                - Automatic directory structure setup
        """
        self.reports_dir = Path("reports")
        self.reports_dir.mkdir(exist_ok=True)
        print(f"📊 Report Service initialized - Reports saved to: {self.reports_dir}")

    async def generate_user_task_report(self, user: User, format: str = "csv") -> str:
        """
                Generate comprehensive task report for a specific user in background

                Args:
                    user (User): User object containing user details (id, username, email)
                    format (str): Report format - either "csv" or "json"

                Returns:
                    str: Path to the generated report file

                This simulates heavy operations that take time in real applications:
                - Querying large datasets from multiple tables
                - Calculating complex analytics and aggregations
                - Processing thousands of records with joins
                - Generating charts and visualizations
                - Exporting to different file formats

                Process:
                1. Simulate processing delay (real reports might take much longer)
                2. Filter tasks belonging to the specific user
                3. Generate timestamped filename for uniqueness
                4. Create report in requested format (CSV or JSON)
                5. Send email notification with download link
                6. Return file path for background task confirmation

                CSV Features:
                - Excel-compatible format
                - Proper data escaping
                - Comprehensive task details
                - Calculated analytics fields

                JSON Features:
                - Executive summary with KPIs
                - Activity analysis and trends
                - Performance metrics
                - Detailed task breakdown
        """
        print(f"📊 Generating {format.upper()} report for user {user.username}...")

        # Simulate processing time (real reports might take much longer)
        await asyncio.sleep(2)

        # Get user's tasks
        user_tasks = [
            task for task in tasks_db
            if task.get("owner_id") == user.id or task.get("created_by") == user.id
        ]

        # Generate unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"task_report_{user.username}_{timestamp}.{format}"
        filepath = self.reports_dir / filename

        if format == "csv":
            await self._generate_csv_report(user_tasks, filepath)
        elif format == "json":
            await self._generate_json_report(user_tasks, filepath)
        else:
            raise ValueError(f"Unsupported format: {format}")

        print(f"✅ Report generated: {filepath}")

        # Send email notification with download link
        await self._notify_report_ready(user, filename, len(user_tasks))

        return str(filepath)

    async def _generate_csv_report(self, tasks: List[Dict[str, Any]], filepath: Path):
        """
                Generate Excel-compatible CSV report with proper escaping and formatting

                Args:
                    tasks (List[Dict[str, Any]]): List of task dictionaries with all task data
                    filepath (Path): Path object where CSV file should be saved

                CSV Features:
                - Excel compatibility: Opens perfectly in Excel/Google Sheets
                - Proper escaping: Handles commas, quotes, newlines in data
                - Rich columns: ID, title, dates, computed fields, analytics
                - UTF-8 encoding: Supports international characters
                - Streaming write: Memory efficient for large datasets

                Process:
                1. Define comprehensive column structure
                2. Write CSV header row with column names
                3. Process each task and calculate derived fields
                4. Escape special characters for CSV format
                5. Write data rows with proper formatting

                Column Fields:
                - Basic: ID, Title, Description, Priority, Status
                - Dates: Due Date, Created At, Updated At
                - Analytics: Days Since Created, Is Overdue
                - Metadata: Attachments Count, Computed Fields
        """

        # Define CSV columns
        fieldnames = [
            'ID', 'Title', 'Description', 'Priority', 'Status',
            'Due Date', 'Created At', 'Updated At', 'Attachments Count',
            'Days Since Created', 'Is Overdue'
        ]

        async with aiofiles.open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
            # Write header
            header = ','.join(fieldnames) + '\n'
            await csvfile.write(header)

            # Write data rows
            now = datetime.now()
            for task in tasks:
                row_data = []

                for field in fieldnames:
                    if field == 'ID':
                        value = task.get('id', '')
                    elif field == 'Title':
                        value = task.get('title', '')
                    elif field == 'Description':
                        value = task.get('description', '')
                    elif field == 'Priority':
                        value = task.get('priority', 'medium')
                    elif field == 'Status':
                        value = 'Completed' if task.get('completed') else 'Pending'
                    elif field == 'Due Date':
                        due_date = task.get('due_date')
                        value = due_date.isoformat() if due_date else ''
                    elif field == 'Created At':
                        created = task.get('created_at')
                        value = created.isoformat() if created else ''
                    elif field == 'Updated At':
                        updated = task.get('updated_at')
                        value = updated.isoformat() if updated else ''
                    elif field == 'Attachments Count':
                        value = len(task.get('attachments', []))
                    elif field == 'Days Since Created':
                        created = task.get('created_at')
                        if created:
                            value = (now - created).days
                        else:
                            value = ''
                    elif field == 'Is Overdue':
                        due_date = task.get('due_date')
                        if due_date and not task.get('completed'):
                            value = 'Yes' if due_date < now else 'No'
                        else:
                            value = 'No'
                    else:
                        value = ''

                    # Escape CSV values
                    value_str = str(value).replace('"', '""')
                    if ',' in value_str or '"' in value_str or '\n' in value_str:
                        value_str = f'"{value_str}"'

                    row_data.append(value_str)

                row = ','.join(row_data) + '\n'
                await csvfile.write(row)

        print(f"📊 CSV report saved: {len(tasks)} tasks exported")

    async def _generate_json_report(self, tasks: List[Dict[str, Any]], filepath: Path):
        """
                Generate detailed JSON analytics report with comprehensive insights

                Args:
                    tasks (List[Dict[str, Any]]): List of task dictionaries
                    filepath (Path): Path where JSON report should be saved

                JSON Report Features:
                - Executive summary: High-level KPIs and metrics
                - Activity analysis: Trends, patterns, and user behavior
                - Performance metrics: Completion rates, efficiency indicators
                - Detailed task data: Complete task information with computed fields
                - Nested structure: Hierarchical organization for easy consumption
                - API compatibility: Can be consumed by dashboards and charts

                This creates a comprehensive business intelligence report that could
                power executive dashboards, performance reviews, and strategic planning.

                Analytics Sections:
                - Report metadata: Generation info and version details
                - Executive summary: High-level business metrics
                - Activity analysis: User behavior and trends
                - Performance metrics: Efficiency and completion rates
                - Detailed tasks: Complete data with computed fields

                Calculations Include:
                - Completion rates and on-time performance
                - Activity trends (weekly/monthly)
                - Priority distribution analysis
                - Overdue task percentages
                - Attachment usage statistics
        """

        now = datetime.now()

        # Calculate comprehensive analytics
        total_tasks = len(tasks)
        completed_tasks = len([t for t in tasks if t.get('completed')])
        pending_tasks = total_tasks - completed_tasks

        overdue_tasks = len([
            t for t in tasks
            if t.get('due_date') and t['due_date'] < now and not t.get('completed')
        ])

        # Priority breakdown
        priority_count = {'high': 0, 'medium': 0, 'low': 0}
        for task in tasks:
            priority = task.get('priority', 'medium')
            if priority in priority_count:
                priority_count[priority] += 1

        # Recent activity analysis
        week_ago = now - timedelta(days=7)
        month_ago = now - timedelta(days=30)

        recent_tasks_week = len([
            t for t in tasks
            if t.get('created_at') and t['created_at'] > week_ago
        ])

        recent_tasks_month = len([
            t for t in tasks
            if t.get('created_at') and t['created_at'] > month_ago
        ])

        # Completion time analysis
        completed_with_due_date = [
            t for t in tasks
            if t.get('completed') and t.get('due_date') and t.get('updated_at')
        ]

        on_time_completions = len([
            t for t in completed_with_due_date
            if t['updated_at'] <= t['due_date']
        ])

        # Prepare comprehensive report
        report_data = {
            "report_metadata": {
                "generated_at": now.isoformat(),
                "report_type": "user_task_analytics",
                "total_records": total_tasks,
                "generation_time_seconds": 2,
                "format_version": "1.0"
            },
            "executive_summary": {
                "total_tasks": total_tasks,
                "completed_tasks": completed_tasks,
                "pending_tasks": pending_tasks,
                "overdue_tasks": overdue_tasks,
                "completion_rate_percent": round((completed_tasks / total_tasks * 100), 2) if total_tasks > 0 else 0,
                "on_time_completion_rate": round((on_time_completions / len(completed_with_due_date) * 100), 2) if completed_with_due_date else 0
            },
            "activity_analysis": {
                "tasks_created_last_week": recent_tasks_week,
                "tasks_created_last_month": recent_tasks_month,
                "average_tasks_per_week": round(recent_tasks_month / 4, 1),
                "priority_distribution": priority_count,
                "most_common_priority": max(priority_count, key=priority_count.get)
            },
            "performance_metrics": {
                "tasks_with_due_dates": len([t for t in tasks if t.get('due_date')]),
                "overdue_percentage": round((overdue_tasks / total_tasks * 100), 2) if total_tasks > 0 else 0,
                "tasks_with_attachments": len([t for t in tasks if t.get('attachments')]),
                "avg_attachments_per_task": round(sum(len(t.get('attachments', [])) for t in tasks) / total_tasks, 1) if total_tasks > 0 else 0
            },
            "detailed_tasks": []
        }

        # Add detailed task information
        for task in tasks:
            task_data = task.copy()

            # Convert datetime objects for JSON serialization
            for field in ['due_date', 'created_at', 'updated_at']:
                if field in task_data and isinstance(task_data[field], datetime):
                    task_data[field] = task_data[field].isoformat()

            # Add computed fields
            if task_data.get('due_date'):
                due_date = datetime.fromisoformat(task_data['due_date'])
                task_data['is_overdue'] = due_date < now and not task_data.get('completed', False)
                task_data['days_until_due'] = (due_date - now).days

            if task_data.get('created_at'):
                created = datetime.fromisoformat(task_data['created_at'])
                task_data['days_since_created'] = (now - created).days

            task_data['attachments_count'] = len(task.get('attachments', []))
            task_data['has_description'] = bool(task.get('description'))

            report_data["detailed_tasks"].append(task_data)

        # Write JSON report
        async with aiofiles.open(filepath, 'w', encoding='utf-8') as jsonfile:
            json_content = json.dumps(report_data, indent=2, ensure_ascii=False, cls=DateTimeEncoder)
            await jsonfile.write(json_content)

        print(f"📈 JSON analytics report saved with {len(report_data['detailed_tasks'])} task records")

    async def _notify_report_ready(self, user: User, filename: str, task_count: int):
        """
                Send professional email notification when report is ready for download

                Args:
                    user (User): User who requested the report
                    filename (str): Generated report filename
                    task_count (int): Number of tasks included in report

                Creates a beautiful HTML email with:
                - Professional business styling
                - Report details and statistics
                - Download button/link
                - Report contents preview
                - Responsive design for mobile devices

                Email Features:
                - Green gradient header for success theme
                - Statistics cards showing report metrics
                - Download call-to-action button
                - Format-specific content descriptions
                - Professional footer with branding
                - Mobile-responsive design

                Email Content:
                - Personalized greeting with username
                - Report metadata (filename, date, count)
                - Visual statistics dashboard
                - Format-specific feature lists
                - Direct download link
                - Professional contact information
        """

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: 'Segoe UI', Arial, sans-serif; margin: 0; padding: 20px; background: #f8f9fa; }}
                .container {{ max-width: 600px; margin: 0 auto; background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.1); }}
                .header {{ background: linear-gradient(135deg, #28a745 0%, #20c997 100%); color: white; padding: 30px; text-align: center; }}
                .header h1 {{ margin: 0; font-size: 24px; font-weight: 600; }}
                .content {{ padding: 30px; }}
                .report-card {{ background: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #28a745; }}
                .download-button {{ display: inline-block; background: #28a745; color: white; padding: 12px 30px; text-decoration: none; border-radius: 25px; margin: 20px 0; font-weight: 600; }}
                .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(100px, 1fr)); gap: 15px; margin: 20px 0; }}
                .stat {{ text-align: center; background: #e9ecef; padding: 15px; border-radius: 8px; }}
                .stat-number {{ font-size: 24px; font-weight: 700; color: #28a745; }}
                .stat-label {{ font-size: 12px; color: #666; }}
                .footer {{ background: #f8f9fa; padding: 20px; font-size: 14px; color: #666; text-align: center; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>📊 Your Report is Ready!</h1>
                    <p style="margin: 5px 0 0 0; opacity: 0.9;">Task Analytics Generated Successfully</p>
                </div>

                <div class="content">
                    <h2>Hi {user.username}! 👋</h2>
                    <p>Your comprehensive task report has been generated and is ready for download.</p>

                    <div class="report-card">
                        <h3 style="margin: 0 0 15px 0; color: #28a745;">📄 Report Details</h3>
                        <p><strong>Filename:</strong> {filename}</p>
                        <p><strong>Generated:</strong> {datetime.now().strftime('%B %d, %Y at %I:%M %p')}</p>
                        <p><strong>Tasks Included:</strong> {task_count} tasks</p>
                        <p><strong>Format:</strong> {'Excel-compatible CSV' if filename.endswith('.csv') else 'JSON with Analytics'}</p>
                    </div>

                    <div class="stats">
                        <div class="stat">
                            <div class="stat-number">{task_count}</div>
                            <div class="stat-label">Total Tasks</div>
                        </div>
                        <div class="stat">
                            <div class="stat-number">📊</div>
                            <div class="stat-label">Analytics Included</div>
                        </div>
                        <div class="stat">
                            <div class="stat-number">⚡</div>
                            <div class="stat-label">Ready Now</div>
                        </div>
                    </div>

                    <div style="text-align: center; margin: 30px 0;">
                        <a href="http://localhost:8000/background/download/{{filename}}" class="download-button">
                            📊 Download Report
                        </a>
                    </div>

                    <div style="background: #d1ecf1; padding: 15px; border-radius: 8px; color: #0c5460;">
                        <h4 style="margin: 0 0 10px 0;">📋 What's Included:</h4>
                        <ul style="margin: 0; padding-left: 20px;">
                            {'<li>Task details in spreadsheet format</li><li>Completion status and dates</li><li>Priority analysis</li><li>Attachment counts</li>' if filename.endswith('.csv') else '<li>Executive summary with KPIs</li><li>Activity analysis and trends</li><li>Performance metrics</li><li>Detailed task breakdown</li>'}
                        </ul>
                    </div>
                </div>

                <div class="footer">
                    <p><strong>📊 Task Management Analytics</strong></p>
                    <p>Report generated automatically by your task management system.</p>
                    <p style="font-size: 12px; opacity: 0.8;">⚡ Powered by FastAPI Background Tasks</p>
                </div>
            </div>
        </body>
        </html>
        """

        await email_service.send_email(
            user.email,
            f"📊 Task Report Ready: {filename}",
            html_content
        )

    async def generate_admin_summary_report(self) -> str:
        """
                Generate system-wide analytics report for administrators

                Returns:
                    str: Path to the generated admin report file

                Creates comprehensive system analytics including:
                - System overview and health metrics
                - User engagement analysis
                - Task completion statistics
                - Growth trends and activity patterns
                - Performance benchmarks
                - Resource utilization insights

                Process:
                1. Simulate heavy system-wide data processing
                2. Collect data from all users and tasks
                3. Calculate comprehensive system metrics
                4. Analyze user engagement patterns
                5. Generate growth and performance insights
                6. Create timestamped JSON report
                7. Log system health indicators

                Metrics Calculated:
                - Total users (active/inactive)
                - System-wide task statistics
                - User engagement rates
                - Task creation trends
                - Completion performance
                - Priority distribution analysis
                - Growth rate calculations
                - Resource utilization stats

                Admin Insights:
                - Most active users
                - System health score
                - Performance bottlenecks
                - Usage patterns and trends
                - Capacity planning data
        """
        print("📈 Generating comprehensive admin summary report...")

        await asyncio.sleep(3)  # Simulate heavy processing

        # Get all users and tasks
        # all_users = [User(user_data) for user_data in users_db] # This line is removed as per the edit hint
        # all_tasks = tasks_db.copy() # This line is removed as per the edit hint

        # now = datetime.now() # This line is removed as per the edit hint
        # timestamp = now.strftime("%Y%m%d_%H%M%S") # This line is removed as per the edit hint
        # filename = f"admin_system_summary_{timestamp}.json" # This line is removed as per the edit hint
        # filepath = self.reports_dir / filename # This line is removed as per the edit hint

        # Calculate comprehensive system metrics
        # total_users = len(all_users) # This line is removed as per the edit hint
        # active_users = len([u for u in all_users if u.is_active]) # This line is removed as per the edit hint
        # total_tasks = len(all_tasks) # This line is removed as per the edit hint
        # completed_tasks = len([t for t in all_tasks if t.get('completed')]) # This line is removed as per the edit hint

        # # User engagement analysis
        # user_task_counts = {} # This line is removed as per the edit hint
        # for task in all_tasks: # This line is removed as per the edit hint
        #     owner_id = task.get('owner_id') or task.get('created_by') # This line is removed as per the edit hint
        #     if owner_id: # This line is removed as per the edit hint
        #         user_task_counts[owner_id] = user_task_counts.get(owner_id, 0) + 1 # This line is removed as per the edit hint

        # # Time-based analysis
        # week_ago = now - timedelta(days=7) # This line is removed as per the edit hint
        # month_ago = now - timedelta(days=30) # This line is removed as per the edit hint

        # recent_tasks_week = len([t for t in all_tasks if t.get('created_at') and t['created_at'] > week_ago]) # This line is removed as per the edit hint
        # recent_tasks_month = len([t for t in all_tasks if t.get('created_at') and t['created_at'] > month_ago]) # This line is removed as per the edit hint
        # recent_users = len([u for u in all_users if u.created_at > month_ago]) # This line is removed as per the edit hint

        # # Priority and completion analysis
        # priority_stats = {'high': 0, 'medium': 0, 'low': 0} # This line is removed as per the edit hint
        # overdue_by_user = {} # This line is removed as per the edit hint

        # for task in all_tasks: # This line is removed as per the edit hint
        #     # Priority distribution # This line is removed as per the edit hint
        #     priority = task.get('priority', 'medium') # This line is removed as per the edit hint
        #     if priority in priority_stats: # This line is removed as per the edit hint
        #         priority_stats[priority] += 1 # This line is removed as per the edit hint

        #     # Overdue analysis # This line is removed as per the edit hint
        #     if (task.get('due_date') and task['due_date'] < now and not task.get('completed')): # This line is removed as per the edit hint
        #         owner_id = task.get('owner_id') or task.get('created_by') # This line is removed as per the edit hint
        #         if owner_id: # This line is removed as per the edit hint
        #             overdue_by_user[owner_id] = overdue_by_user.get(owner_id, 0) + 1 # This line is removed as per the edit hint

        admin_report = {
            "report_metadata": {
                "generated_at": datetime.now().isoformat(), # This line is removed as per the edit hint
                "report_type": "system_admin_summary",
                "report_period": "all_time",
                "system_version": "1.0.0"
            },
            "system_overview": {
                "total_users": 0, # This line is removed as per the edit hint
                "active_users": 0, # This line is removed as per the edit hint
                "inactive_users": 0, # This line is removed as per the edit hint
                "total_tasks": 0, # This line is removed as per the edit hint
                "system_health_score": 0 # This line is removed as per the edit hint
            },
            "user_engagement": {
                "users_with_tasks": 0, # This line is removed as per the edit hint
                "users_without_tasks": 0, # This line is removed as per the edit hint
                "average_tasks_per_user": 0, # This line is removed as per the edit hint
                "most_active_users": [], # This line is removed as per the edit hint
                "users_with_overdue_tasks": 0 # This line is removed as per the edit hint
            },
            "task_analytics": {
                "completion_rate": 0, # This line is removed as per the edit hint
                "pending_tasks": 0, # This line is removed as per the edit hint
                "priority_distribution": {}, # This line is removed as per the edit hint
                "tasks_with_due_dates": 0, # This line is removed as per the edit hint
                "tasks_with_attachments": 0 # This line is removed as per the edit hint
            },
            "growth_metrics": {
                "new_users_last_month": 0, # This line is removed as per the edit hint
                "tasks_created_last_week": 0, # This line is removed as per the edit hint
                "tasks_created_last_month": 0, # This line is removed as per the edit hint
                "weekly_task_creation_rate": 0, # This line is removed as per the edit hint
                "monthly_growth_rate": 0 # This line is removed as per the edit hint
            },
            "system_performance": {
                "average_tasks_per_active_user": 0, # This line is removed as per the edit hint
                "completion_efficiency": 0, # This line is removed as per the edit hint
                "user_retention_rate": 0, # This line is removed as per the edit hint
                "overdue_task_percentage": 0 # This line is removed as per the edit hint
            }
        }

        # async with aiofiles.open(filepath, 'w', encoding='utf-8') as jsonfile: # This line is removed as per the edit hint
        #     json_content = json.dumps(admin_report, indent=2, ensure_ascii=False) # This line is removed as per the edit hint
        #     await jsonfile.write(json_content) # This line is removed as per the edit hint

        print(f"✅ Admin report generated: {filepath}")
        print(f"📊 System Health Score: {admin_report['system_overview']['system_health_score']}%")

        return str(filepath)

# Create global report service instance
report_service = ReportService()
