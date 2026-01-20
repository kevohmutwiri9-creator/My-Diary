import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime, timedelta
from flask import current_app
import json

class EmailService:
    def __init__(self):
        self.smtp_server = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = int(os.environ.get('SMTP_PORT', '587'))
        self.smtp_username = os.environ.get('SMTP_USERNAME', '')
        self.smtp_password = os.environ.get('SMTP_PASSWORD', '')
        self.from_email = os.environ.get('FROM_EMAIL', '')
    
    def send_email(self, to_email, subject, body, html_body=None):
        """Send email notification"""
        try:
            msg = MIMEMultipart()
            msg['From'] = self.from_email
            msg['To'] = to_email
            msg['Subject'] = subject
            
            # Attach both plain text and HTML
            msg.attach(MIMEText(body, 'plain'))
            if html_body:
                msg.attach(MIMEText(html_body, 'html'))
            
            # Send email
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.smtp_username, self.smtp_password)
            text = msg.as_string()
            server.sendmail(self.from_email, to_email, text)
            server.quit()
            
            return True
        except Exception as e:
            current_app.logger.error(f"Email send failed: {str(e)}")
            return False
    
    def send_daily_reminder(self, user_email, user_name):
        """Send daily writing reminder"""
        subject = f"Daily Writing Reminder - {datetime.now().strftime('%B %d, %Y')}"
        
        body = f"""
Hi {user_name},

This is your daily reminder to write in your diary!

Writing regularly helps you:
- Track your emotional patterns
- Maintain mental clarity
- Build a personal record
- Improve self-awareness

Take a few minutes today to reflect on your thoughts and feelings.

Click here to write: https://my-diary-m7lx.onrender.com/new-entry

Best regards,
My Diary Team
        """
        
        html_body = f"""
<html>
<body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 20px; border-radius: 10px;">
        <h2 style="color: white; text-align: center;">Daily Writing Reminder</h2>
        <p style="color: white; font-size: 16px;">Hi {user_name},</p>
        <div style="background: white; padding: 20px; border-radius: 8px; margin: 20px 0;">
            <p>This is your daily reminder to write in your diary!</p>
            <h3>Benefits of Daily Writing:</h3>
            <ul>
                <li>Track your emotional patterns</li>
                <li>Maintain mental clarity</li>
                <li>Build a personal record</li>
                <li>Improve self-awareness</li>
            </ul>
            <div style="text-align: center; margin: 30px 0;">
                <a href="https://my-diary-m7lx.onrender.com/new-entry" 
                   style="background: #667eea; color: white; padding: 12px 30px; text-decoration: none; border-radius: 25px; font-weight: bold;">
                    Write Now
                </a>
            </div>
        </div>
        <p style="color: white; text-align: center; font-size: 14px;">Best regards,<br>My Diary Team</p>
    </div>
</body>
</html>
        """
        
        return self.send_email(user_email, subject, body, html_body)
    
    def send_weekly_summary(self, user_email, user_name, entries_data):
        """Send weekly summary of diary entries"""
        subject = f"Weekly Diary Summary - {datetime.now().strftime('%B %d, %Y')}"
        
        total_entries = entries_data.get('total_entries', 0)
        avg_mood = entries_data.get('avg_mood', 'N/A')
        top_moods = entries_data.get('top_moods', [])
        
        body = f"""
Hi {user_name},

Here's your weekly diary summary!

📊 This Week's Stats:
- Total Entries: {total_entries}
- Average Mood: {avg_mood}
- Top Moods: {', '.join(top_moods[:3])}

📝 Writing Highlights:
{entries_data.get('highlights', 'No specific highlights this week.')}

Keep up the great work with your diary!

Best regards,
My Diary Team
        """
        
        html_body = f"""
<html>
<body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 20px; border-radius: 10px;">
        <h2 style="color: white; text-align: center;">Weekly Diary Summary</h2>
        <p style="color: white; font-size: 16px;">Hi {user_name},</p>
        <div style="background: white; padding: 20px; border-radius: 8px; margin: 20px 0;">
            <h3 style="color: #667eea;">📊 This Week's Stats</h3>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin: 20px 0;">
                <div style="background: #f8f9fa; padding: 15px; border-radius: 8px;">
                    <h4>Total Entries</h4>
                    <p style="font-size: 24px; font-weight: bold; color: #667eea;">{total_entries}</p>
                </div>
                <div style="background: #f8f9fa; padding: 15px; border-radius: 8px;">
                    <h4>Average Mood</h4>
                    <p style="font-size: 24px; font-weight: bold; color: #764ba2;">{avg_mood}</p>
                </div>
            </div>
            <div style="background: #e3f2fd; padding: 15px; border-radius: 8px; margin: 20px 0;">
                <h4>Top Moods</h4>
                <p>{', '.join(top_moods[:3])}</p>
            </div>
            <div style="background: #fff3cd; padding: 15px; border-radius: 8px; margin: 20px 0;">
                <h4>📝 Writing Highlights</h4>
                <p>{entries_data.get('highlights', 'No specific highlights this week.')}</p>
            </div>
            <div style="text-align: center; margin: 30px 0;">
                <a href="https://my-diary-m7lx.onrender.com/dashboard" 
                   style="background: #667eea; color: white; padding: 12px 30px; text-decoration: none; border-radius: 25px; font-weight: bold;">
                    View Full Dashboard
                </a>
            </div>
        </div>
        <p style="color: white; text-align: center; font-size: 14px;">Best regards,<br>My Diary Team</p>
    </div>
</body>
</html>
        """
        
        return self.send_email(user_email, subject, body, html_body)
    
    def send_monthly_insights(self, user_email, user_name, insights_data):
        """Send monthly insights and patterns"""
        subject = f"Monthly Insights - {datetime.now().strftime('%B %Y')}"
        
        writing_streak = insights_data.get('writing_streak', 0)
        most_productive_day = insights_data.get('most_productive_day', 'N/A')
        total_words = insights_data.get('total_words', 0)
        
        body = f"""
Hi {user_name},

Here are your monthly diary insights!

🎯 Key Achievements:
- Writing Streak: {writing_streak} days
- Most Productive Day: {most_productive_day}
- Total Words Written: {total_words:,}

📈 Patterns & Insights:
{insights_data.get('patterns', 'Continue your writing journey to discover more patterns.')}

🌟 Recommendation:
{insights_data.get('recommendation', 'Keep up the excellent work with your diary!')}

Best regards,
My Diary Team
        """
        
        html_body = f"""
<html>
<body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 20px; border-radius: 10px;">
        <h2 style="color: white; text-align: center;">Monthly Insights</h2>
        <p style="color: white; font-size: 16px;">Hi {user_name},</p>
        <div style="background: white; padding: 20px; border-radius: 8px; margin: 20px 0;">
            <h3 style="color: #667eea;">🎯 Key Achievements</h3>
            <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 15px; margin: 20px 0;">
                <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; text-align: center;">
                    <h4>Writing Streak</h4>
                    <p style="font-size: 24px; font-weight: bold; color: #28a745;">{writing_streak} days</p>
                </div>
                <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; text-align: center;">
                    <h4>Most Productive Day</h4>
                    <p style="font-size: 20px; font-weight: bold; color: #ffc107;">{most_productive_day}</p>
                </div>
                <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; text-align: center;">
                    <h4>Total Words</h4>
                    <p style="font-size: 24px; font-weight: bold; color: #17a2b8;">{total_words:,}</p>
                </div>
            </div>
            
            <div style="background: #e3f2fd; padding: 15px; border-radius: 8px; margin: 20px 0;">
                <h4>📈 Patterns & Insights</h4>
                <p>{insights_data.get('patterns', 'Continue your writing journey to discover more patterns.')}</p>
            </div>
            
            <div style="background: #fff3cd; padding: 15px; border-radius: 8px; margin: 20px 0;">
                <h4>🌟 Recommendation</h4>
                <p>{insights_data.get('recommendation', 'Keep up the excellent work with your diary!')}</p>
            </div>
            
            <div style="text-align: center; margin: 30px 0;">
                <a href="https://my-diary-m7lx.onrender.com/advanced-analytics" 
                   style="background: #667eea; color: white; padding: 12px 30px; text-decoration: none; border-radius: 25px; font-weight: bold;">
                    View Advanced Analytics
                </a>
            </div>
        </div>
        <p style="color: white; text-align: center; font-size: 14px;">Best regards,<br>My Diary Team</p>
    </div>
</body>
</html>
        """
        
        return self.send_email(user_email, subject, body, html_body)

# Global email service instance
email_service = EmailService()
