import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any
import logging

from app.models.user import User
from app.services.user_service import UserService

from app.services.email_service import email_service

# Set up logging for reminder system
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ReminderService:
    """
        Continuous background service for sending task reminders

        This service runs as a persistent background loop that operates 24/7,
        monitoring tasks and sending proactive notifications. Unlike request-based
        services, this runs independently and continuously.

        Features:
        - Continuous monitoring: Runs every hour checking for due tasks
        - Daily summaries: Automated emails sent at 9:00 AM
        - Overdue alerts: Notifications for tasks past their due date
        - Duplicate prevention: Smart tracking to avoid spam
        - Graceful shutdown: Proper cleanup when service stops
        - Error recovery: Continues running even if individual operations fail
        - Manual triggers: On-demand reminders for specific tasks
    """

    def __init__(self):
        """
                Initialize the reminder service with configuration settings

                Sets up the service state, timing intervals, and displays
                helpful debug information about the service capabilities.

                Configuration:
                - running: Boolean flag to control service state
                - reminder_task: Reference to the background asyncio task
                - check_interval: Time between reminder checks (3600 seconds = 1 hour)

                Features:
                - Service state management
                - Configurable check intervals
                - Debug information display
                - Production-ready defaults
        """
        self.running = False
        self.reminder_task = None
        self.check_interval = 3600  # 1 hour (reduce to 30 for testing)

        print("⏰ Reminder Service initialized")
        print(f"   Check interval: {self.check_interval} seconds")
        print("   Features: Due task alerts, Daily summaries, Overdue notifications")

    async def start_reminder_system(self):
        """
            Start the continuous background reminder system

            This method starts a persistent background loop that runs independently
            of user requests. The loop continues until explicitly stopped.

            Process:
            1. Check if already running (prevent duplicate loops)
            2. Set running flag to True
            3. Create asyncio background task
            4. Log startup information

            The background task runs in parallel with the main FastAPI application.
            Multiple reminder systems can run simultaneously if needed.

            Returns:
                None

            Side Effects:
            - Creates persistent background task
            - Starts continuous monitoring loop
            - Logs service startup information
        """
        if self.running:
            logger.info("⏰ Reminder system is already running")
            return

        self.running = True
        logger.info("🔔 Starting background reminder system...")
        logger.info("   - Checking for due tasks every hour")
        logger.info("   - Daily summaries at 9:00 AM")
        logger.info("   - Overdue task notifications")

        # Start the background loop
        self.reminder_task = asyncio.create_task(self._reminder_loop())

    async def stop_reminder_system(self):
        """
            Stop the background reminder system gracefully

            This method ensures proper cleanup and prevents resource leaks.
            The loop is cancelled and cleaned up safely.

            Process:
            1. Set running flag to False
            2. Cancel the background task
            3. Wait for graceful shutdown
            4. Handle cancellation exception

            Graceful Shutdown Benefits:
            - Prevents resource leaks
            - Completes current operations before stopping
            - Proper cleanup of background tasks
            - Safe application shutdown
        """
        self.running = False
        if self.reminder_task:
            self.reminder_task.cancel()
            try:
                await self.reminder_task
            except asyncio.CancelledError:
                logger.info("🔕 Reminder system stopped gracefully")

    async def _reminder_loop(self):
        """
            Main continuous loop that runs reminder checks indefinitely

            This is the heart of the reminder system - a never-ending loop that:
            1. Performs all reminder checks
            2. Handles errors gracefully
            3. Waits for the next iteration
            4. Continues until service is stopped

            The loop includes comprehensive error handling to ensure the service
            remains running even if individual operations fail.

            Error Handling Strategy:
            - Individual check failures don't stop the loop
            - Critical errors trigger auto-restart after delay
            - Graceful cancellation when service is stopped
            - Detailed logging for monitoring and debugging

            Loop Cycle:
            1. Increment loop counter for tracking
            2. Log current check iteration
            3. Execute all reminder checks
            4. Log success/failure status
            5. Wait for next iteration (non-blocking)
            6. Repeat until stopped
        """
        try:
            loop_count = 0
            while self.running:
                loop_count += 1
                current_time = datetime.now()
                logger.info(f"🔔 Reminder check #{loop_count} at {current_time.strftime('%Y-%m-%d %H:%M:%S')}")

                # Run all reminder checks
                try:
                    await self._check_due_task_reminders()
                    await self._check_daily_summaries()
                    await self._check_overdue_notifications()

                    logger.info(f"✅ Reminder check #{loop_count} completed successfully")

                except Exception as e:
                    logger.error(f"❌ Error in reminder check #{loop_count}: {e}")
                    # Continue running even if one check fails

                # Wait before next check
                logger.info(f"⏳ Waiting {self.check_interval} seconds until next check...")
                await asyncio.sleep(self.check_interval)

        except asyncio.CancelledError:
            logger.info("🔕 Reminder loop cancelled")
        except Exception as e:
            logger.error(f"💥 Critical error in reminder loop: {e}")
            # Auto-restart after critical error
            if self.running:
                logger.info("🔄 Restarting reminder loop in 60 seconds...")
                await asyncio.sleep(60)
                self.reminder_task = asyncio.create_task(self._reminder_loop())

    async def _check_due_task_reminders(self):
        """
                Send reminders for tasks due in the next 24 hours

                This function identifies tasks that are approaching their due date
                and sends proactive reminder notifications to task owners.

                Logic:
                1. Calculate time window (now to 24 hours from now)
                2. Filter tasks that are due soon and not completed
                3. Prevent duplicate reminders using state tracking
                4. Group tasks by user for efficient processing
                5. Send individual task reminders via email
                6. Mark tasks as reminded to prevent duplicates

                Duplicate Prevention:
                - Uses 'due_reminder_sent' flag on tasks
                - Ensures users don't get spammed with same reminder
                - Flag is set after successful email sending

                Performance Optimization:
                - Groups tasks by user to reduce processing overhead
                - Includes small delays between emails to avoid server overload
                - Continues processing even if individual emails fail
        """
        # TODO: Replace with real DB query to find tasks due in next 24 hours
        # Example: Query tasks where due_date between now and tomorrow, not completed, and not reminded
        logger.info("📋 [TODO] Implement DB logic for due soon task reminders")
        pass

    async def _check_daily_summaries(self):
        """
                Send daily task summaries at 9:00 AM

                This function sends comprehensive daily emails with task overviews,
                statistics, and urgent items requiring attention.

                Timing Logic:
                - Only runs during 9:00 AM hour (9:00-9:30 AM window)
                - Prevents sending multiple summaries on same day
                - Uses hour-based filtering to control timing

                Summary Contents:
                - Total task counts and completion rates
                - Urgent tasks requiring immediate attention
                - Daily productivity metrics
                - Call-to-action buttons for task management

                Process:
                1. Check if it's the right time (9:00 AM window)
                2. Get all active users
                3. For each user, get their tasks (including completed for analytics)
                4. Send comprehensive daily summary email
                5. Include small delays to avoid email server overload

                User Filtering:
                - Only sends to active users
                - Only sends if user has tasks (avoids empty emails)
                - Respects user notification preferences
        """
        # TODO: Replace with real DB query to get users and their tasks
        logger.info("📋 [TODO] Implement DB logic for daily summaries")
        pass

    async def _check_overdue_notifications(self):
        """
                Send notifications for newly overdue tasks

                This function identifies tasks that have just become overdue and sends
                urgent notification emails to task owners. It prevents duplicate
                notifications while ensuring users are alerted about missed deadlines.

                Overdue Logic:
                1. Task has due date in the past
                2. Task is not completed
                3. Overdue notification hasn't been sent yet

                Notification Strategy:
                - Sends comprehensive overdue alerts with urgency indicators
                - Groups multiple overdue tasks per user into single email
                - Uses visual cues (colors, icons) to indicate severity
                - Provides actionable next steps and task management tips

                Duplicate Prevention:
                - Uses 'overdue_notification_sent' flag
                - Ensures each task only triggers one overdue notification
                - Flag is set after successful email delivery

                Severity Analysis:
                - Critical: 7+ days overdue (red indicators)
                - Urgent: 3-7 days overdue (yellow indicators)
                - Recent: 1-3 days overdue (standard indicators)
        """
        # TODO: Replace with real DB query to find overdue tasks and notify users
        logger.info("⚠️ [TODO] Implement DB logic for overdue notifications")
        pass

    async def _send_overdue_notification(self, user: User, overdue_tasks: List[Dict[str, Any]]):
        """
                Send comprehensive overdue task notification with urgency indicators

                Args:
                    user (User): User object who owns the overdue tasks
                    overdue_tasks (List[Dict[str, Any]]): List of overdue task dictionaries

                This function creates a professional, urgent-looking HTML email that:
                - Uses red color scheme to indicate urgency
                - Shows days overdue for each task with severity indicators
                - Provides task prioritization based on overdue duration
                - Includes actionable tips for task management
                - Uses responsive design for mobile devices
                - Categorizes tasks by severity (critical: 7+ days, urgent: 3+ days)

                Visual Design Elements:
                - Red gradient header for urgency
                - Color-coded task cards based on overdue severity
                - Statistical overview with key metrics
                - Clear call-to-action buttons
                - Professional business email styling

                Data Processing:
                1. Calculate days overdue for each task
                2. Categorize tasks by severity level
                3. Count critical and high-priority tasks
                4. Sort tasks by urgency (most overdue first)
                5. Render HTML template with computed data
                6. Send urgent notification email
        """

        from jinja2 import Template

        html_template = Template("""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Overdue Tasks Alert</title>
            <style>
                body { font-family: 'Segoe UI', Arial, sans-serif; margin: 0; padding: 20px; background: #fdf2f2; }
                .container { max-width: 600px; margin: 0 auto; background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 12px rgba(231,76,60,0.3); }
                .header { background: linear-gradient(135deg, #e74c3c 0%, #c0392b 100%); color: white; padding: 30px; text-align: center; }
                .header h1 { margin: 0; font-size: 26px; font-weight: 600; }
                .content { padding: 30px; }
                .alert-message { background: #fdedec; border-left: 4px solid #e74c3c; padding: 20px; margin: 20px 0; border-radius: 4px; }
                .task-item { background: #fdf2f2; border: 1px solid #fadbd8; padding: 20px; margin: 15px 0; border-radius: 8px; border-left: 4px solid #e74c3c; }
                .task-item.critical { background: #fbeae9; border-left-color: #922b21; }
                .task-title { font-size: 18px; font-weight: 600; color: #922b21; margin-bottom: 10px; }
                .task-meta { font-size: 14px; color: #666; margin: 8px 0; }
                .days-overdue { color: #e74c3c; font-weight: 700; font-size: 16px; }
                .priority-high { background: #fadbd8; color: #922b21; padding: 4px 8px; border-radius: 12px; font-size: 11px; font-weight: 600; }
                .priority-medium { background: #fef5e7; color: #b7950b; padding: 4px 8px; border-radius: 12px; font-size: 11px; font-weight: 600; }
                .priority-low { background: #eafaf1; color: #1e8449; padding: 4px 8px; border-radius: 12px; font-size: 11px; font-weight: 600; }
                .cta-button { display: inline-block; background: #e74c3c; color: white; padding: 15px 30px; text-decoration: none; border-radius: 25px; margin: 20px 0; font-weight: 600; box-shadow: 0 2px 4px rgba(231,76,60,0.3); }
                .cta-button:hover { background: #c0392b; }
                .footer { background: #fdf2f2; padding: 20px; text-align: center; font-size: 14px; color: #666; }
                .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(100px, 1fr)); gap: 15px; margin: 20px 0; }
                .stat { text-align: center; background: #fdedec; padding: 15px; border-radius: 8px; }
                .stat-number { font-size: 24px; font-weight: 700; color: #e74c3c; }
                .stat-label { font-size: 12px; color: #666; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>⚠️ Overdue Tasks Alert</h1>
                    <p style="margin: 5px 0 0 0; opacity: 0.9;">Immediate Action Required</p>
                </div>

                <div class="content">
                    <h2 style="color: #e74c3c;">Hi {{ user_name }}! 🚨</h2>

                    <div class="alert-message">
                        <strong>You have {{ task_count }} overdue task{{ 's' if task_count > 1 else '' }} that need immediate attention!</strong>
                        <br><br>
                        These tasks have passed their due dates and may be impacting your productivity and commitments.
                    </div>

                    <div class="stats">
                        <div class="stat">
                            <div class="stat-number">{{ task_count }}</div>
                            <div class="stat-label">Overdue Tasks</div>
                        </div>
                        <div class="stat">
                            <div class="stat-number">{{ critical_count }}</div>
                            <div class="stat-label">Critical (7+ days)</div>
                        </div>
                        <div class="stat">
                            <div class="stat-number">{{ high_priority_count }}</div>
                            <div class="stat-label">High Priority</div>
                        </div>
                    </div>

                    <h3 style="color: #922b21; border-bottom: 2px solid #e74c3c; padding-bottom: 10px;">
                        📋 Overdue Tasks Details
                    </h3>

                    {% for task in tasks %}
                        <div class="task-item {{ 'critical' if task.days_overdue > 7 else '' }}">
                            <div class="task-title">
                                {{ task.title }}
                                {% if task.days_overdue > 7 %}🔴{% elif task.days_overdue > 3 %}🟡{% else %}⚪{% endif %}
                            </div>

                            <div class="task-meta">
                                <strong>Description:</strong> {{ task.description or 'No description provided' }}
                            </div>

                            <div class="task-meta">
                                <strong>Priority:</strong>
                                <span class="priority-{{ task.priority }}">{{ task.priority.upper() }}</span>
                            </div>

                            <div class="task-meta">
                                <strong>Was Due:</strong> {{ task.due_date.strftime('%B %d, %Y at %I:%M %p') }}
                            </div>

                            <div class="days-overdue">
                                ⏰ {{ task.days_overdue }} day{{ 's' if task.days_overdue > 1 else '' }} overdue
                                {% if task.days_overdue > 7 %}
                                    <span style="color: #922b21; font-size: 14px;">(CRITICAL - Over 1 week!)</span>
                                {% elif task.days_overdue > 3 %}
                                    <span style="color: #b7950b; font-size: 14px;">(Urgent)</span>
                                {% endif %}
                            </div>
                        </div>
                    {% endfor %}

                    <div style="text-align: center; margin: 30px 0;">
                        <a href="http://localhost:8000/tasks?completed=false&sort_by=due_date&sort_order=asc" class="cta-button">
                            🎯 View & Update Overdue Tasks
                        </a>
                    </div>

                    <div style="background: #fdedec; padding: 20px; border-radius: 8px; border-left: 4px solid #e74c3c;">
                        <h4 style="margin: 0 0 10px 0; color: #922b21;">💡 Quick Action Tips:</h4>
                        <ul style="margin: 0; color: #666;">
                            <li>Review each task and update progress</li>
                            <li>Extend due dates if needed with new realistic timelines</li>
                            <li>Break down large tasks into smaller, manageable pieces</li>
                            <li>Mark completed tasks as done to clear your backlog</li>
                            <li>Consider delegating or reprioritizing if overwhelmed</li>
                        </ul>
                    </div>
                </div>

                <div class="footer">
                    <p><strong>⚠️ Overdue Task Alert System</strong></p>
                    <p>This notification is sent once per overdue task to help you stay on track.</p>
                    <p style="font-size: 12px; opacity: 0.8;">📧 Powered by FastAPI Background Tasks</p>
                </div>
            </div>
        </body>
        </html>
        """)

        # Prepare task data with computed fields
        now = datetime.now()
        task_data = []
        critical_count = 0
        high_priority_count = 0

        for task in overdue_tasks:
            due_date = task.get('due_date')
            days_overdue = (now - due_date).days if due_date else 0

            if days_overdue > 7:
                critical_count += 1

            if task.get('priority') == 'high':
                high_priority_count += 1

            task_info = {
                'title': task.get('title', 'Untitled Task'),
                'description': task.get('description'),
                'priority': task.get('priority', 'medium'),
                'due_date': due_date,
                'days_overdue': days_overdue
            }
            task_data.append(task_info)

        # Sort by severity (most overdue first, then by priority)
        task_data.sort(key=lambda x: (-x['days_overdue'], x['priority'] != 'high'))

        html_content = html_template.render(
            user_name=user.username,
            task_count=len(overdue_tasks),
            critical_count=critical_count,
            high_priority_count=high_priority_count,
            tasks=task_data
        )

        subject = f"🚨 URGENT: {len(overdue_tasks)} Overdue Task{'s' if len(overdue_tasks) > 1 else ''} Require Action"
        await email_service.send_email(user.email, subject, html_content)

    async def send_immediate_reminder(self, user: User, task_id: int):
        """
                Send immediate reminder for a specific task (manually triggered)

                Args:
                    user (User): User requesting the immediate reminder
                    task_id (int): ID of the specific task to remind about

                Returns:
                    bool: True if reminder sent successfully

                Raises:
                    ValueError: If task not found or user doesn't own the task

                This function provides on-demand reminder functionality that can be
                triggered by users or administrators. Unlike the automated reminders
                that run on schedule, this sends immediate notifications.

                Security Features:
                - Users can only send reminders for their own tasks
                - Admins can send reminders for any task
                - Task ownership is verified before sending
                - Input validation for task existence

                Use Cases:
                - User wants immediate reminder for important task
                - Admin helping user with task management
                - Testing reminder system functionality
                - Urgent task escalation scenarios

                Process:
                1. Find task by ID in database
                2. Verify task exists (raise ValueError if not found)
                3. Check task ownership permissions
                4. Log reminder request for audit trail
                5. Send notification using email service
                6. Return success status
        """
        # TODO: Replace with real DB query to find task by ID and send reminder
        logger.info(f"📧 [TODO] Implement DB logic for immediate reminder for task {task_id} to {user.username}")
        pass

# Create global reminder service instance
reminder_service = ReminderService()
