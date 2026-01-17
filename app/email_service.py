import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import current_app


class EmailService:
    def __init__(self):
        self.smtp_server = os.environ.get("MAIL_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.environ.get("MAIL_PORT", 587))
        self.smtp_username = os.environ.get("MAIL_USERNAME")
        self.smtp_password = os.environ.get("MAIL_PASSWORD")
        self.use_tls = os.environ.get("MAIL_USE_TLS", "True").lower() == "true"
    
    def send_password_reset(self, email: str, reset_token: str):
        """Send password reset email"""
        reset_url = f"http://localhost:5000/auth/reset-password?token={reset_token}"
        
        subject = "Password Reset - My Diary"
        body = f"""
        Hello,
        
        You requested a password reset for your My Diary account.
        
        Click the link below to reset your password:
        {reset_url}
        
        This link will expire in 1 hour for security reasons.
        
        If you didn't request this password reset, please ignore this email.
        
        Best regards,
        My Diary Team
        """
        
        return self._send_email(email, subject, body)
    
    def _send_email(self, to_email: str, subject: str, body: str):
        """Send email using SMTP"""
        if not all([self.smtp_username, self.smtp_password]):
            current_app.logger.error("Email credentials not configured")
            return False
        
        try:
            msg = MIMEMultipart()
            msg['From'] = self.smtp_username
            msg['To'] = to_email
            msg['Subject'] = subject
            
            msg.attach(MIMEText(body, 'plain'))
            
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            if self.use_tls:
                server.starttls()
            
            server.login(self.smtp_username, self.smtp_password)
            server.send_message(msg)
            server.quit()
            
            return True
        except Exception as e:
            current_app.logger.error(f"Failed to send email: {str(e)}")
            return False


# Global email service instance
email_service = EmailService()
