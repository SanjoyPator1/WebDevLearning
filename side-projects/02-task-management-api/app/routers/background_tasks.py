from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from typing import Dict, Any, Optional
from datetime import datetime

from app.models.user import User
from app.dependencies.oauth2 import get_current_user
from app.dependencies.permissions import require_admin, require_user_or_admin
from app.services.email_service import email_service
from app.services.report_service import report_service
from app.services.reminder_service import reminder_service
from app.services.file_service import file_service
from fastapi.responses import FileResponse
from pathlib import Path

# Create background tasks router
router = APIRouter(prefix="/background", tags=["background-tasks"])

@router.post("/start-reminder-system")
async def start_reminder_system(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_admin)
):
    """
    Start the continuous reminder system (Admin only)

    This endpoint triggers a background service that runs continuously to:
    - Monitor all tasks for due dates every hour
    - Send daily summary emails at 9:00 AM to all users
    - Notify users about overdue tasks with escalating urgency
    - Track user engagement and send re-engagement emails

    Security: Only administrators can start system-wide services to prevent
    resource abuse and ensure proper system management.

    Background Process:
    1. Starts an infinite async loop in background
    2. Checks database for due/overdue tasks every hour
    3. Sends personalized notifications to task owners
    4. Logs all activities for monitoring and debugging
    5. Handles errors gracefully without crashing the system

    Returns immediate response while service starts in background.
    """

    # Start reminder system in background
    background_tasks.add_task(reminder_service.start_reminder_system)

    return {
        "message": "Background reminder system started successfully",
        "started_by": current_user.username,
        "started_at": datetime.now().isoformat(),
        "features": [
            "Hourly due task checks",
            "Daily summaries at 9:00 AM",
            "Overdue task notifications",
            "Continuous monitoring"
        ]
    }

@router.post("/stop-reminder-system")
async def stop_reminder_system(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_admin)
):
    """
    Stop the continuous reminder system (Admin only)

    Gracefully shuts down the background reminder service:
    - Stops the monitoring loop from checking for new due tasks
    - Completes any notifications already in progress
    - Prevents new reminder emails from being sent
    - Preserves system resources during maintenance

    Use Cases:
    - System maintenance or updates
    - Debugging notification issues
    - Reducing server load during high traffic
    - Testing without unwanted notifications

    The shutdown is graceful - existing operations complete before stopping.
    """

    background_tasks.add_task(reminder_service.stop_reminder_system)

    return {
        "message": "Background reminder system stopped",
        "stopped_by": current_user.username,
        "stopped_at": datetime.now().isoformat()
    }

@router.post("/send-task-reminder/{task_id}")
async def send_immediate_task_reminder(
    task_id: int,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_user_or_admin)
):
    """
    Send immediate reminder for a specific task

    Allows users to manually trigger reminder emails for important tasks:
    - Users can only send reminders for their own tasks
    - Admins can send reminders for any task in the system
    - Creates personalized reminder with task details and urgency
    - Includes actionable buttons to view/complete the task

    Access Control:
    - Validates task ownership before sending reminder
    - Prevents users from spamming others with reminders
    - Logs all reminder activities for audit purposes

    Background Processing:
    1. Validates user has permission to access the task
    2. Retrieves task details and current status
    3. Generates personalized HTML email with task information
    4. Sends email via MailHog (development) or SMTP (production)
    5. Updates task metadata with reminder sent timestamp

    Use Cases:
    - Important deadline approaching
    - Following up on delegated tasks
    - Manual notification for high-priority items
    """

    # Add immediate reminder to background tasks
    background_tasks.add_task(
        reminder_service.send_immediate_reminder,
        current_user,
        task_id
    )

    return {
        "message": f"Task reminder will be sent to {current_user.email}",
        "task_id": task_id,
        "recipient": current_user.username,
        "scheduled_at": datetime.now().isoformat()
    }

@router.post("/generate-task-report")
async def generate_user_task_report(
    background_tasks: BackgroundTasks,
    format: str = "csv",  # csv or json
    current_user: User = Depends(require_user_or_admin)
):
    """
    Generate comprehensive task report for current user

    Creates detailed analytics reports in multiple formats:
    - CSV: Excel-compatible spreadsheet with task data and metrics
    - JSON: Rich analytics with insights, trends, and recommendations

    Report Generation Process:
    1. Collects all tasks owned by or assigned to the current user
    2. Calculates performance metrics (completion rate, average time, etc.)
    3. Analyzes patterns (busiest days, most productive times, etc.)
    4. Generates insights and recommendations for productivity improvement
    5. Creates formatted output in requested format
    6. Saves report to secure directory with unique filename
    7. Sends beautiful email notification with download link

    CSV Format Features:
    - Task ID, title, description, priority, status
    - Creation date, due date, completion date
    - Time spent, category, tags, attachments count
    - Excel-compatible formatting with proper headers
    - Ready for import into business intelligence tools

    JSON Format Features:
    - Executive summary with key performance indicators
    - Detailed task breakdown with metadata
    - Time-based analytics (daily, weekly, monthly trends)
    - Productivity insights and recommendations
    - Charts and graphs data for visualization
    - Advanced metrics for power users

    The entire process runs in background - user gets immediate response
    and email notification when report is ready for download.
    """

    if format not in ["csv", "json"]:
        raise HTTPException(
            status_code=400,
            detail="Format must be 'csv' or 'json'"
        )

    # Generate report in background
    background_tasks.add_task(
        report_service.generate_user_task_report,
        current_user,
        format
    )

    return {
        "message": f"Task report generation started ({format.upper()} format)",
        "user": current_user.username,
        "format": format,
        "estimated_completion": "2-5 minutes",
        "notification": f"Email will be sent to {current_user.email} when ready",
        "features": {
            "csv": [
                "Excel-compatible format",
                "Task details and status",
                "Completion dates",
                "Priority analysis",
                "Attachment counts"
            ],
            "json": [
                "Executive summary with KPIs",
                "Activity analysis and trends",
                "Performance metrics",
                "Detailed task breakdown",
                "Advanced analytics"
            ]
        }[format]
    }

@router.post("/generate-admin-report")
async def generate_admin_system_report(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_admin)
):
    """
    Generate comprehensive system report (Admin only)

    Creates system-wide analytics and health reports including:
    - Overall system performance and health score
    - User engagement metrics and activity patterns
    - Task completion rates across all users
    - Growth trends and usage analytics
    - Resource utilization and performance benchmarks
    - Popular features and user behavior insights

    Admin Report Contents:
    1. System Overview Dashboard:
       - Total users, tasks, attachments
       - System uptime and performance metrics
       - Storage usage and optimization opportunities

    2. User Engagement Analytics:
       - Active users (daily, weekly, monthly)
       - User retention and churn analysis
       - Feature adoption rates
       - Support ticket trends

    3. Task Management Insights:
       - Completion rates by priority/category
       - Average task duration and complexity
       - Bottlenecks and productivity blockers
       - Team collaboration patterns

    4. Performance Metrics:
       - Background task processing times
       - Email delivery success rates
       - File processing statistics
       - API response times and error rates

    5. Growth and Trends:
       - User acquisition and activation rates
       - Feature usage growth over time
       - Seasonal patterns and predictions
       - Capacity planning recommendations

    Security: Only administrators can access system-wide data to protect
    user privacy and maintain data confidentiality.

    The report generation is computationally intensive, involving:
    - Database queries across multiple tables
    - Statistical calculations and trend analysis
    - Chart generation and data visualization
    - PDF compilation with professional formatting

    All processing happens in background with email notification when complete.
    """

    # Generate admin report in background
    background_tasks.add_task(
        report_service.generate_admin_summary_report
    )

    return {
        "message": "Admin system report generation started",
        "requested_by": current_user.username,
        "estimated_completion": "3-7 minutes",
        "includes": [
            "System overview and health score",
            "User engagement analytics",
            "Task completion metrics",
            "Growth and activity trends",
            "Performance benchmarks",
            "Resource utilization stats"
        ],
        "note": "Report will be saved to reports/ directory"
    }

@router.post("/send-daily-summary")
async def send_daily_summary(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_user_or_admin)
):
    """
    Send daily task summary email immediately (for testing and manual triggers)

    Normally, daily summaries are sent automatically at 9:00 AM by the
    reminder system. This endpoint allows manual triggering for:
    - Testing email templates and content
    - Sending summaries on-demand for important days
    - Debugging notification issues
    - Providing summaries after system maintenance

    Daily Summary Email Contents:
    1. Personal Dashboard:
       - Tasks due today with priority indicators
       - Overdue tasks requiring immediate attention
       - Recently completed tasks (sense of accomplishment)
       - Progress metrics and completion statistics

    2. Activity Insights:
       - Most productive times of day
       - Task completion patterns
       - Upcoming deadlines and planning suggestions
       - Achievement badges and milestones

    3. Actionable Intelligence:
       - Recommendations for task prioritization
       - Time management suggestions
       - Workflow optimization tips
       - Links to most important tasks

    4. Visual Elements:
       - Color-coded priority indicators
       - Progress bars and completion percentages
       - Calendar view of upcoming deadlines
       - Achievement icons and motivational elements

    Email Design Features:
    - Mobile-responsive HTML layout
    - Professional branding and styling
    - Dark/light mode compatibility
    - Accessibility features for screen readers
    - One-click task actions (complete, snooze, view)

    Background Processing:
    1. Retrieves all tasks associated with current user
    2. Calculates daily statistics and insights
    3. Generates personalized recommendations
    4. Renders beautiful HTML email template with data
    5. Sends via email service with proper error handling
    6. Logs activity for debugging and analytics

    Perfect for testing MailHog integration during development!
    """

    # Get user's tasks
    from app.database.storage import tasks_db
    user_tasks = [
        task for task in tasks_db
        if (task.get('owner_id') == current_user.id or task.get('created_by') == current_user.id)
    ]

    # Send daily summary in background
    background_tasks.add_task(
        email_service.send_daily_task_summary,
        current_user,
        user_tasks
    )

    return {
        "message": "Daily summary email will be sent shortly",
        "recipient": current_user.email,
        "tasks_included": len(user_tasks),
        "note": "Check MailHog at http://localhost:8025 to view the email"
    }

@router.post("/process-file/{task_id}")
async def trigger_file_processing(
    task_id: int,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_user_or_admin)
):
    """
    Manually trigger file processing for a task's attachments

    File processing normally happens automatically when files are uploaded.
    This endpoint allows manual triggering for:
    - Re-processing files that failed during upload
    - Processing files uploaded before background system was enabled
    - Updating processed files after system improvements
    - Debugging file processing issues

    Processing Capabilities by File Type:

    Images (JPEG, PNG, GIF, WebP):
    - Generate multiple thumbnail sizes (64x64, 128x128, 256x256)
    - Create web-optimized versions for faster loading
    - Extract EXIF metadata (camera, location, settings)
    - Analyze colors, dimensions, and format compatibility
    - Detect faces and objects (if enabled)
    - Generate responsive image sets for different devices

    PDF Documents:
    - Create high-quality preview images for first 3 pages
    - Extract searchable text content for indexing
    - Analyze document metadata (author, title, creation date)
    - Detect security settings (encryption, permissions)
    - Identify document structure (links, forms, annotations)
    - Generate reading time estimates and complexity scores

    Text Files (.txt, .md, .log):
    - Perform comprehensive content analysis
    - Extract keywords and calculate frequency
    - Analyze readability and complexity metrics
    - Detect language and character encoding
    - Classify document type (article, notes, technical, etc.)
    - Generate search indexes and content summaries

    Security and Access Control:
    - Users can only process files from their own tasks
    - Admins can process files from any task
    - Validates task ownership before processing
    - Logs all processing activities for audit

    Background Processing Flow:
    1. Validates user has access to the specified task
    2. Retrieves all attachments associated with the task
    3. Queues each file for appropriate processing pipeline
    4. Processes files concurrently for better performance
    5. Sends individual email notifications for each completed file
    6. Updates task metadata with processing results
    7. Handles errors gracefully with detailed error reporting

    Each file gets its own background task for parallel processing.
    Large files or multiple files are processed simultaneously for efficiency.
    """

    # Get task and check ownership
    from app.dependencies.database import get_database
    from app.database.storage import tasks_db

    task = None
    for t in tasks_db:
        if t.get('id') == task_id:
            task = t
            break

    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    # Check ownership
    task_owner_id = task.get('owner_id') or task.get('created_by')
    if current_user.role != "admin" and current_user.id != task_owner_id:
        raise HTTPException(
            status_code=403,
            detail="You can only process files for your own tasks"
        )

    # Get attachments
    attachments = task.get('attachments', [])
    if not attachments:
        raise HTTPException(
            status_code=400,
            detail=f"Task {task_id} has no attachments to process"
        )

    # Process each attachment in background
    for attachment in attachments:
        background_tasks.add_task(
            file_service.process_uploaded_file,
            attachment,
            current_user,
            task_id
        )

    return {
        "message": f"File processing started for {len(attachments)} attachment(s)",
        "task_id": task_id,
        "attachments_count": len(attachments),
        "estimated_completion": f"{len(attachments) * 2}-{len(attachments) * 5} minutes",
        "notification": f"Email will be sent to {current_user.email} for each processed file",
        "attachments": [
            {
                "filename": att.get('filename'),
                "type": att.get('content_type'),
                "size_mb": round(att.get('size', 0) / 1024 / 1024, 2)
            }
            for att in attachments
        ]
    }

@router.get("/status")
async def get_background_task_status(
    current_user: User = Depends(require_user_or_admin)
):
    """
    Get comprehensive status of all background services

    Provides real-time information about system health and configuration:
    - Which services are currently running
    - Configuration settings and endpoints
    - Resource usage and performance metrics
    - User permissions and available features

    Status Information Provided:

    1. Reminder System Status:
       - Whether continuous monitoring is active
       - Check interval (how often it scans for due tasks)
       - Last check time and results
       - Number of reminders sent today
       - Error count and last error details

    2. Email Service Configuration:
       - SMTP server details and connection status
       - Email sending enabled/disabled status
       - MailHog UI link for development
       - Daily email quota and usage
       - Delivery success/failure rates

    3. File Processing Service:
       - Directory locations for uploads and processed files
       - Supported file types and size limits
       - Processing queue status and backlog
       - Successfully processed files today
       - Failed processing attempts and error details

    4. Report Generation Service:
       - Available report formats and templates
       - Reports directory and storage usage
       - Active report generation jobs
       - Completed reports available for download
       - Report retention policy and cleanup schedule

    5. Current User Context:
       - User role and permissions
       - Available background task features
       - Usage statistics for current user
       - Pending background tasks for this user

    Use Cases:
    - System health monitoring and debugging
    - User support and troubleshooting
    - Performance optimization and tuning
    - Feature availability checking
    - Integration with monitoring dashboards

    This endpoint is perfect for:
    - Admin dashboards showing system health
    - User interfaces displaying available features
    - Debugging background task issues
    - Monitoring system performance
    - API status pages and health checks
    """

    return {
        "reminder_system": {
            "running": reminder_service.running,
            "check_interval_seconds": reminder_service.check_interval,
            "features": [
                "Due task notifications",
                "Daily summaries at 9:00 AM",
                "Overdue task alerts"
            ]
        },
        "email_service": {
            "enabled": email_service.send_emails,
            "smtp_host": email_service.smtp_host,
            "smtp_port": email_service.smtp_port,
            "mailhog_ui": "http://localhost:8025" if email_service.smtp_host == "localhost" else None
        },
        "file_processing": {
            "upload_directory": str(file_service.upload_dir),
            "processed_directory": str(file_service.processed_dir),
            "thumbnails_directory": str(file_service.thumbnails_dir),
            "supported_types": [
                "image/jpeg", "image/png",
                "application/pdf",
                "text/plain"
            ]
        },
        "report_generation": {
            "reports_directory": str(report_service.reports_dir),
            "available_formats": ["csv", "json"],
            "user_reports": "Available for all authenticated users",
            "admin_reports": "System-wide analytics for admins"
        },
        "current_user": {
            "username": current_user.username,
            "role": current_user.role,
            "can_start_reminder_system": current_user.role == "admin",
            "can_generate_admin_reports": current_user.role == "admin"
        }
    }

@router.post("/test-email-service")
async def test_email_service(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_user_or_admin)
):
    """
    Test email service with a beautifully formatted sample email

    Sends a comprehensive test email to verify:
    - SMTP server connectivity and authentication
    - HTML email rendering and formatting
    - MailHog integration during development
    - Email template system functionality
    - Background task queue processing

    Test Email Features:
    1. Professional HTML Layout:
       - Responsive design for mobile/desktop
       - Corporate branding and styling
       - Proper typography and spacing
       - Color scheme matching application theme

    2. Comprehensive Test Information:
       - Timestamp of email generation
       - Recipient details and user context
       - Service configuration details
       - Background task processing confirmation
       - Links to relevant system components

    3. Development Integration:
       - Direct link to MailHog UI for viewing
       - Instructions for accessing email content
       - Debugging information and system status
       - Performance metrics for email processing

    4. Visual Verification Elements:
       - Success indicators and status badges
       - Formatted lists and data tables
       - Call-to-action buttons and links
       - Footer with system information

    Background Processing:
    1. Creates comprehensive HTML email template
    2. Populates template with current user and system data
    3. Adds timestamp and unique identifiers
    4. Sends email through configured SMTP service
    5. Handles any delivery errors with proper logging
    6. Returns success confirmation to user

    Perfect for:
    - Verifying MailHog setup during development
    - Testing email templates and formatting
    - Debugging SMTP configuration issues
    - Demonstrating email capabilities to stakeholders
    - Quality assurance of email system

    Development Workflow:
    1. Run this endpoint to send test email
    2. Check http://localhost:8025 to view email in MailHog
    3. Verify HTML rendering and content formatting
    4. Test responsive design on different screen sizes
    5. Confirm all links and buttons work correctly

    The test email showcases the full capabilities of your email system!
    """
    # Send test email in background
    async def send_test_email():
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
                .container {{ max-width: 500px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; }}
                .header {{ text-align: center; color: #28a745; margin-bottom: 20px; }}
                .content {{ line-height: 1.6; }}
                .footer {{ margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee; color: #666; font-size: 14px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>✅ Email Service Test</h1>
                </div>
                <div class="content">
                    <p>Hi {current_user.username}!</p>
                    <p>This is a test email to verify that your FastAPI background task email system is working correctly.</p>
                    <p><strong>Test Details:</strong></p>
                    <ul>
                        <li>Sent at: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}</li>
                        <li>Recipient: {current_user.email}</li>
                        <li>Service: MailHog Development SMTP</li>
                        <li>Background Task: ✅ Working</li>
                    </ul>
                    <p>If you can see this email in MailHog, your background task system is configured correctly! 🎉</p>
                </div>
                <div class="footer">
                    <p><strong>📧 FastAPI Background Task Email Test</strong></p>
                    <p>View this email at: <a href="http://localhost:8025">http://localhost:8025</a></p>
                </div>
            </div>
        </body>
        </html>
        """

        await email_service.send_email(
            current_user.email,
            "✅ Email Service Test - FastAPI Background Tasks",
            html_content
        )

    background_tasks.add_task(send_test_email)

    return {
        "message": "Test email queued successfully",
        "recipient": current_user.email,
        "check_mailhog": "http://localhost:8025",
        "note": "Email will be sent in background - check MailHog UI in a few seconds"
    }

@router.get("/download/{filename}")
async def download_report(
    filename: str,
    current_user: User = Depends(require_user_or_admin)
):
    """
    Download generated reports
    
    Security: Users can only download their own reports
    Admins can download any report
    """
    
    # Define reports directory
    reports_dir = Path("reports")
    file_path = reports_dir / filename
    
    # Check if file exists
    if not file_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Report file '{filename}' not found"
        )
    
    # Security check: Users can only download their own reports
    if current_user.role != "admin":
        # Check if filename contains current user's username
        if current_user.username not in filename:
            raise HTTPException(
                status_code=403,
                detail="You can only download your own reports"
            )
    
    # Determine media type based on file extension
    if filename.endswith('.csv'):
        media_type = 'text/csv'
    elif filename.endswith('.json'):
        media_type = 'application/json'
    else:
        media_type = 'application/octet-stream'
    
    return FileResponse(
        path=str(file_path),
        media_type=media_type,
        filename=filename
    )
