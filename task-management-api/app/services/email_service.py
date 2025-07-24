import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict, Any
from jinja2 import Template
import asyncio
from datetime import datetime, timedelta
import re

from app.config import settings
from app.database.users import User

class EmailService:
    """
        Async email service with MailHog integration for development

        This service handles sending beautiful HTML emails in the background.
        All emails are sent to MailHog during development, which captures
        them and displays them in a web interface at http://localhost:8025

        Features:
        - Async email sending (non-blocking)
        - HTML + plain text versions for compatibility
        - Professional email templates with CSS styling
        - MailHog integration for safe development testing
        - Error handling and logging

        MailHog Setup:
        1. brew install mailhog
        2. mailhog
        3. View emails at http://localhost:8025
    """

    def __init__(self):
        """
                Initialize the email service with MailHog configuration

                Sets up SMTP connection details and displays helpful debug information.
                In production, these settings would point to real SMTP servers like Gmail, SendGrid, or AWS SES.

                Configuration loaded from app.config.settings:
                - smtp_host: SMTP server hostname (localhost for MailHog)
                - smtp_port: SMTP server port (1025 for MailHog)
                - smtp_user: SMTP username (empty for MailHog)
                - smtp_password: SMTP password (empty for MailHog)
                - smtp_from_email: Sender email address with display name
                - send_emails: Boolean flag to enable/disable email sending

                Displays:
                - SMTP configuration details
                - Development mode indicators
                - MailHog access URLs
                - Setup instructions
        """
        self.smtp_host = settings.smtp_host
        self.smtp_port = settings.smtp_port
        self.smtp_user = settings.smtp_user
        self.smtp_password = settings.smtp_password
        self.from_email = settings.smtp_from_email
        self.send_emails = settings.send_emails

        print(f"📧 Email Service initialized:")
        print(f"   SMTP Server: {self.smtp_host}:{self.smtp_port}")
        print(f"   Mode: {'MailHog (Development)' if self.smtp_host == 'localhost' else 'Production SMTP'}")
        if self.smtp_host == "localhost":
            print(f"   📱 View emails: http://localhost:8025")
            print(f"   💡 Start MailHog: mailhog")

    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: str = None
    ) -> bool:
        """
                Send email via MailHog or real SMTP server

                Args:
                    to_email (str): Recipient's email address
                    subject (str): Email subject line
                    html_content (str): Rich HTML content with styling, images, buttons
                    text_content (str, optional): Plain text version. Auto-generated if not provided.

                Returns:
                    bool: True if email sent successfully, False if failed

                Process:
                1. Check if email sending is enabled in configuration
                2. Create MIME multipart message container
                3. Set required email headers (Subject, From, To, Date)
                4. Generate plain text version from HTML if not provided
                5. Create separate MIME parts for text and HTML content
                6. Send email asynchronously using aiosmtplib
                7. Log success/failure with debugging information

                MailHog Benefits:
                - Actually renders HTML emails (not just console text)
                - Test email formatting and CSS
                - Mobile-responsive preview
                - Email search and management
        """

        if not self.send_emails:
            print(f"📧 EMAIL DISABLED: To: {to_email}, Subject: {subject}")
            return False

        try:
            # Create multipart email message
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = self.from_email
            message["To"] = to_email
            message["Date"] = datetime.now().strftime("%a, %d %b %Y %H:%M:%S %z")

            # Create plain text version from HTML (fallback for old email clients)
            if not text_content:
                text_content = re.sub('<[^<]+?>', '', html_content)
                text_content = re.sub(r'\s+', ' ', text_content).strip()

            # Attach text and HTML versions
            text_part = MIMEText(text_content, "plain", "utf-8")
            html_part = MIMEText(html_content, "html", "utf-8")

            message.attach(text_part)
            message.attach(html_part)

            # Send email to MailHog
            await aiosmtplib.send(
                message,
                hostname=self.smtp_host,
                port=self.smtp_port,
                # MailHog doesn't require authentication
                use_tls=False if self.smtp_host == "localhost" else True,
                username=self.smtp_user if self.smtp_user else None,
                password=self.smtp_password if self.smtp_password else None,
            )

            print(f"✅ Email sent to MailHog: {to_email} - {subject}")
            print(f"📱 View at: http://localhost:8025")
            return True

        except Exception as e:
            print(f"❌ Failed to send email: {e}")
            print(f"💡 Make sure MailHog is running: mailhog")
            return False

    async def send_task_due_notification(self, user: User, task: Dict[str, Any]):
        """
                Send beautiful HTML notification when task is due

                Args:
                    user (User): User object containing username, email, etc.
                    task (Dict[str, Any]): Dictionary containing task data (title, description, due_date, priority, etc.)

                Creates a professional email with:
                - Branded header with gradient colors
                - Task details displayed in a styled card
                - Priority-based color coding (red=high, orange=medium, green=low)
                - Call-to-action button linking to the task
                - Mobile-responsive design that works on phones
                - Accessibility features for screen readers

                Process:
                1. Create HTML template with Jinja2 placeholders
                2. Map task priority to appropriate colors
                3. Render template with actual user/task data
                4. Send email using send_email method

                Priority Color Mapping:
                - high: #e74c3c (red) - urgent
                - medium: #f39c12 (orange) - moderate
                - low: #27ae60 (green) - low priority
        """

        html_template = Template("""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Task Due Reminder</title>
            <style>
                body {
                    font-family: 'Segoe UI', Arial, sans-serif;
                    margin: 0;
                    padding: 20px;
                    background-color: #f5f5f5;
                    line-height: 1.6;
                }
                .container {
                    max-width: 600px;
                    margin: 0 auto;
                    background: white;
                    border-radius: 12px;
                    overflow: hidden;
                    box-shadow: 0 4px 12px rgba(0,0,0,0.1);
                }
                .header {
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 30px;
                    text-align: center;
                }
                .header h1 {
                    margin: 0;
                    font-size: 24px;
                    font-weight: 600;
                }
                .content {
                    padding: 30px;
                }
                .greeting {
                    font-size: 18px;
                    margin-bottom: 20px;
                    color: #333;
                }
                .task-card {
                    background: #f8f9fa;
                    padding: 20px;
                    border-radius: 8px;
                    margin: 20px 0;
                    border-left: 5px solid {{ priority_color }};
                }
                .task-title {
                    font-size: 20px;
                    font-weight: 600;
                    color: #2c3e50;
                    margin-bottom: 10px;
                }
                .task-detail {
                    margin: 8px 0;
                    color: #555;
                }
                .task-detail strong {
                    color: #2c3e50;
                    font-weight: 600;
                }
                .priority-badge {
                    display: inline-block;
                    padding: 4px 12px;
                    border-radius: 20px;
                    font-size: 12px;
                    font-weight: 600;
                    text-transform: uppercase;
                    background: {{ priority_color }};
                    color: white;
                }
                .cta-button {
                    display: inline-block;
                    background: #667eea;
                    color: white;
                    padding: 12px 30px;
                    text-decoration: none;
                    border-radius: 25px;
                    margin: 20px 0;
                    font-weight: 600;
                    transition: background 0.3s ease;
                }
                .cta-button:hover {
                    background: #5a67d8;
                }
                .footer {
                    background: #f8f9fa;
                    padding: 20px 30px;
                    font-size: 14px;
                    color: #666;
                    border-top: 1px solid #eee;
                }
                .footer a {
                    color: #667eea;
                    text-decoration: none;
                }

                /* Mobile responsive */
                @media (max-width: 600px) {
                    .container { margin: 10px; }
                    .header, .content { padding: 20px; }
                    .greeting { font-size: 16px; }
                    .task-title { font-size: 18px; }
                }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>⏰ Task Due Reminder</h1>
                    <p style="margin: 5px 0 0 0; opacity: 0.9;">Don't let deadlines slip by!</p>
                </div>

                <div class="content">
                    <div class="greeting">Hi {{ user_name }}! 👋</div>

                    <p>This is a friendly reminder that your task is due soon:</p>

                    <div class="task-card">
                        <div class="task-title">{{ task_title }}</div>

                        <div class="task-detail">
                            <strong>Description:</strong>
                            {{ task_description or 'No description provided' }}
                        </div>

                        <div class="task-detail">
                            <strong>Priority:</strong>
                            <span class="priority-badge">{{ priority }}</span>
                        </div>

                        <div class="task-detail">
                            <strong>Due Date:</strong>
                            {{ due_date.strftime('%B %d, %Y at %I:%M %p') if due_date else 'No due date set' }}
                        </div>

                        <div class="task-detail">
                            <strong>Status:</strong>
                            {{ 'Completed ✅' if completed else 'Pending ⏳' }}
                        </div>
                    </div>

                    {% if not completed %}
                        <div style="text-align: center; margin: 30px 0;">
                            <a href="http://localhost:8000/tasks/{{ task_id }}" class="cta-button">
                                🎯 View Task Details
                            </a>
                        </div>

                        <p style="color: #e74c3c; font-weight: 600; text-align: center;">
                            ⚡ Time to take action and complete this task!
                        </p>
                    {% else %}
                        <div style="text-align: center; background: #d4edda; padding: 20px; border-radius: 8px; color: #155724;">
                            <h3 style="margin: 0;">🎉 Congratulations!</h3>
                            <p style="margin: 10px 0 0 0;">You've already completed this task. Great job!</p>
                        </div>
                    {% endif %}
                </div>

                <div class="footer">
                    <p><strong>Task Management System</strong></p>
                    <p>
                        This is an automated notification.
                        You can update your notification preferences in your
                        <a href="http://localhost:8000/auth/me">account settings</a>.
                    </p>
                    <p style="margin-top: 15px; font-size: 12px; opacity: 0.8;">
                        📧 Powered by FastAPI Background Tasks
                    </p>
                </div>
            </div>
        </body>
        </html>
        """)

        # Priority color mapping
        priority_colors = {
            "high": "#e74c3c",
            "medium": "#f39c12",
            "low": "#27ae60"
        }

        priority = task.get("priority", "medium")
        priority_color = priority_colors.get(priority, "#f39c12")

        # Render email
        html_content = html_template.render(
            user_name=user.username,
            task_title=task.get("title", "Untitled Task"),
            task_description=task.get("description"),
            priority=priority,
            priority_color=priority_color,
            due_date=task.get("due_date"),
            completed=task.get("completed", False),
            task_id=task.get("id")
        )

        # Send email
        subject = f"⏰ Task Due: {task.get('title', 'Untitled Task')}"
        await self.send_email(user.email, subject, html_content)

    async def send_daily_task_summary(self, user: User, tasks: List[Dict[str, Any]]):
        """
                Send daily task summary with statistics and urgent tasks

                Args:
                    user (User): User object containing username, email, etc.
                    tasks (List[Dict[str, Any]]): List of all user's tasks

                Creates a comprehensive daily email with:
                - Task statistics dashboard (total, pending, completed, overdue)
                - Urgent tasks requiring attention (due today or overdue)
                - Color-coded priority indicators
                - Progress metrics and completion rates
                - Time-of-day greeting (morning/afternoon/evening)
                - Mobile-responsive grid layout

                Process:
                1. Calculate comprehensive statistics from tasks
                2. Identify urgent tasks (due today or overdue)
                3. Sort urgent tasks by priority (overdue first, then due today)
                4. Determine appropriate greeting based on time of day
                5. Render HTML template with statistics and task data
                6. Send email using send_email method

                Statistics Calculated:
                - Total tasks count
                - Completed vs pending tasks
                - Overdue tasks count
                - Completion rate percentage
                - Critical tasks (7+ days overdue)
                - High priority tasks count

                Urgent Task Analysis:
                - Tasks due today
                - Overdue tasks with days count
                - Priority-based sorting
                - Visual indicators for severity
        """

        html_template = Template("""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Daily Task Summary</title>
            <style>
                body {
                    font-family: 'Segoe UI', Arial, sans-serif;
                    margin: 0;
                    padding: 20px;
                    background-color: #f8f9fa;
                }
                .container {
                    max-width: 650px;
                    margin: 0 auto;
                    background: white;
                    border-radius: 12px;
                    overflow: hidden;
                    box-shadow: 0 4px 12px rgba(0,0,0,0.1);
                }
                .header {
                    background: linear-gradient(135deg, #2196F3 0%, #21CBF3 100%);
                    color: white;
                    padding: 30px;
                    text-align: center;
                }
                .header h1 { margin: 0; font-size: 26px; font-weight: 600; }
                .content { padding: 30px; }
                .greeting { font-size: 18px; margin-bottom: 25px; color: #333; }

                .stats-grid {
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
                    gap: 15px;
                    margin: 25px 0;
                }
                .stat-card {
                    background: #f8f9fa;
                    padding: 20px;
                    border-radius: 8px;
                    text-align: center;
                    border: 2px solid #e9ecef;
                    transition: transform 0.2s ease;
                }
                .stat-card:hover { transform: translateY(-2px); }
                .stat-number {
                    font-size: 32px;
                    font-weight: 700;
                    color: #2196F3;
                    margin-bottom: 5px;
                }
                .stat-label {
                    font-size: 14px;
                    color: #666;
                    font-weight: 500;
                }

                .task-item {
                    background: white;
                    border: 1px solid #e9ecef;
                    padding: 20px;
                    margin: 15px 0;
                    border-radius: 8px;
                    border-left: 4px solid #2196F3;
                    transition: box-shadow 0.2s ease;
                }
                .task-item:hover { box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
                .task-item.overdue { border-left-color: #e74c3c; background: #fdf2f2; }
                .task-item.due-today { border-left-color: #f39c12; background: #fefbf3; }

                .task-title { font-size: 18px; font-weight: 600; color: #2c3e50; margin-bottom: 8px; }
                .task-meta { font-size: 14px; color: #666; margin: 5px 0; }
                .task-priority {
                    display: inline-block;
                    padding: 3px 8px;
                    border-radius: 12px;
                    font-size: 11px;
                    font-weight: 600;
                    text-transform: uppercase;
                }
                .priority-high { background: #fee; color: #c53030; }
                .priority-medium { background: #fffbeb; color: #d69e2e; }
                .priority-low { background: #f0fff4; color: #38a169; }

                .no-tasks {
                    background: #e6fffa;
                    padding: 30px;
                    border-radius: 8px;
                    text-align: center;
                    color: #2c7a7b;
                    margin: 20px 0;
                }

                .cta-button {
                    display: inline-block;
                    background: #2196F3;
                    color: white;
                    padding: 15px 35px;
                    text-decoration: none;
                    border-radius: 25px;
                    margin: 25px 0;
                    font-weight: 600;
                    transition: all 0.3s ease;
                }
                .cta-button:hover {
                    background: #1976D2;
                    transform: translateY(-1px);
                }

                .footer {
                    background: #f8f9fa;
                    padding: 25px;
                    font-size: 14px;
                    color: #666;
                    border-top: 1px solid #e9ecef;
                    text-align: center;
                }

                @media (max-width: 600px) {
                    .stats-grid { grid-template-columns: repeat(2, 1fr); }
                    .stat-number { font-size: 24px; }
                }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>📋 Daily Task Summary</h1>
                    <p style="margin: 5px 0 0 0; opacity: 0.9;">{{ today_date }}</p>
                </div>

                <div class="content">
                    <div class="greeting">Good {{ time_of_day }}, {{ user_name }}! 🌟</div>

                    <p>Here's your task overview for today:</p>

                    <div class="stats-grid">
                        <div class="stat-card">
                            <div class="stat-number">{{ total_tasks }}</div>
                            <div class="stat-label">Total Tasks</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-number" style="color: #f39c12;">{{ pending_tasks }}</div>
                            <div class="stat-label">Pending</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-number" style="color: #27ae60;">{{ completed_tasks }}</div>
                            <div class="stat-label">Completed</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-number" style="color: #e74c3c;">{{ overdue_tasks }}</div>
                            <div class="stat-label">Overdue</div>
                        </div>
                    </div>

                    {% if urgent_tasks %}
                        <h3 style="color: #2c3e50; border-bottom: 2px solid #2196F3; padding-bottom: 10px;">
                            🚨 Tasks Requiring Attention ({{ urgent_tasks|length }})
                        </h3>

                        {% for task in urgent_tasks %}
                            <div class="task-item {{ 'overdue' if task.is_overdue else 'due-today' if task.is_due_today else '' }}">
                                <div class="task-title">{{ task.title }}</div>
                                <div class="task-meta">
                                    {{ task.description or 'No description' }}
                                </div>
                                <div class="task-meta">
                                    <strong>Due:</strong> {{ task.due_date.strftime('%B %d at %I:%M %p') if task.due_date else 'No due date' }}
                                    {% if task.is_overdue %}
                                        <span style="color: #e74c3c; font-weight: 600;">({{ task.days_overdue }} days overdue)</span>
                                    {% elif task.is_due_today %}
                                        <span style="color: #f39c12; font-weight: 600;">(Due today!)</span>
                                    {% endif %}
                                </div>
                                <div class="task-meta">
                                    <span class="task-priority priority-{{ task.priority }}">{{ task.priority }}</span>
                                </div>
                            </div>
                        {% endfor %}
                    {% else %}
                        <div class="no-tasks">
                            <h3 style="margin: 0 0 10px 0;">🎉 All Caught Up!</h3>
                            <p style="margin: 0;">No urgent tasks today. You're doing great!</p>
                        </div>
                    {% endif %}

                    <div style="text-align: center; margin: 30px 0;">
                        <a href="http://localhost:8000/tasks" class="cta-button">
                            📱 View All Tasks
                        </a>
                    </div>

                    {% if completion_rate %}
                        <div style="background: #e8f5e8; padding: 20px; border-radius: 8px; text-align: center;">
                            <strong style="color: #2d5a2d;">📈 Completion Rate: {{ completion_rate }}%</strong>
                            <br>
                            <small style="color: #5a5a5a;">Keep up the excellent work!</small>
                        </div>
                    {% endif %}
                </div>

                <div class="footer">
                    <p><strong>📧 Daily Summary from Task Management System</strong></p>
                    <p>You can adjust notification preferences in your account settings.</p>
                </div>
            </div>
        </body>
        </html>
        """)

        # Calculate statistics
        now = datetime.now()
        total_tasks = len(tasks)
        completed_tasks = len([t for t in tasks if t.get("completed")])
        pending_tasks = total_tasks - completed_tasks
        overdue_tasks = len([
            t for t in tasks
            if t.get("due_date") and t["due_date"] < now and not t.get("completed")
        ])

        completion_rate = round((completed_tasks / total_tasks * 100)) if total_tasks > 0 else 0

        # Get urgent tasks (due today or overdue)
        urgent_tasks = []
        for task in tasks:
            if task.get("completed"):
                continue

            due_date = task.get("due_date")
            if not due_date:
                continue

            is_overdue = due_date < now
            is_due_today = due_date.date() == now.date()

            if is_overdue or is_due_today:
                task_info = {
                    "title": task.get("title", "Untitled"),
                    "description": task.get("description"),
                    "priority": task.get("priority", "medium"),
                    "due_date": due_date,
                    "is_overdue": is_overdue,
                    "is_due_today": is_due_today,
                    "days_overdue": (now - due_date).days if is_overdue else 0
                }
                urgent_tasks.append(task_info)

        # Sort by urgency (overdue first, then due today, then by due date)
        urgent_tasks.sort(key=lambda x: (not x["is_overdue"], not x["is_due_today"], x["due_date"]))

        # Determine time of day
        hour = now.hour
        if hour < 12:
            time_of_day = "morning"
        elif hour < 17:
            time_of_day = "afternoon"
        else:
            time_of_day = "evening"

        # Render email
        html_content = html_template.render(
            user_name=user.username,
            today_date=now.strftime("%A, %B %d, %Y"),
            time_of_day=time_of_day,
            total_tasks=total_tasks,
            pending_tasks=pending_tasks,
            completed_tasks=completed_tasks,
            overdue_tasks=overdue_tasks,
            urgent_tasks=urgent_tasks,
            completion_rate=completion_rate
        )

        # Send daily summary email
        subject = f"📋 Daily Summary - {pending_tasks} pending tasks"
        await self.send_email(user.email, subject, html_content)

# Create global email service instance
email_service = EmailService()