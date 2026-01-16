import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

load_dotenv()

# SMTP Configuration
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM_NAME = os.getenv("SMTP_FROM_NAME", "Schema Drift Detector")


def send_reset_email(to_email: str, reset_token: str, username: str) -> bool:
    """
    Send password reset email with the reset token.
    Returns True if email sent successfully, False otherwise.
    """
    if not SMTP_USER or not SMTP_PASSWORD:
        print("⚠️ SMTP credentials not configured. Token:", reset_token)
        return False

    subject = "Password Reset Request - Schema Drift Detector"
    
    # HTML email template
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body style="margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #030712;">
        <div style="max-width: 600px; margin: 0 auto; padding: 40px 20px;">
            <div style="background: linear-gradient(135deg, rgba(99, 102, 241, 0.1), rgba(168, 85, 247, 0.1)); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 16px; padding: 40px; text-align: center;">
                
                <!-- Logo -->
                <div style="width: 60px; height: 60px; background: linear-gradient(135deg, #6366f1, #a855f7); border-radius: 12px; margin: 0 auto 24px; display: flex; align-items: center; justify-content: center;">
                    <span style="font-size: 28px;">🔐</span>
                </div>
                
                <h1 style="color: #f9fafb; font-size: 24px; margin: 0 0 16px; font-weight: 700;">Password Reset Request</h1>
                
                <p style="color: #9ca3af; font-size: 16px; line-height: 1.6; margin: 0 0 24px;">
                    Hi <strong style="color: #f9fafb;">{username}</strong>,<br>
                    We received a request to reset your password. Use the token below to reset it.
                </p>
                
                <!-- Token Box -->
                <div style="background: rgba(0, 0, 0, 0.3); border: 1px solid rgba(99, 102, 241, 0.3); border-radius: 12px; padding: 20px; margin: 24px 0;">
                    <p style="color: #9ca3af; font-size: 12px; text-transform: uppercase; letter-spacing: 1px; margin: 0 0 8px;">Your Reset Token</p>
                    <p style="color: #6366f1; font-size: 24px; font-weight: 700; font-family: monospace; margin: 0; letter-spacing: 2px;">{reset_token}</p>
                </div>
                
                <p style="color: #9ca3af; font-size: 14px; margin: 24px 0 0;">
                    ⏰ This token expires in <strong style="color: #f9fafb;">1 hour</strong>.
                </p>
                
                <hr style="border: none; border-top: 1px solid rgba(255, 255, 255, 0.1); margin: 32px 0;">
                
                <p style="color: #6b7280; font-size: 12px; margin: 0;">
                    If you didn't request this, you can safely ignore this email.<br>
                    Your password will remain unchanged.
                </p>
            </div>
            
            <p style="color: #4b5563; font-size: 12px; text-align: center; margin-top: 24px;">
                © 2025 Schema Drift Detector
            </p>
        </div>
    </body>
    </html>
    """
    
    # Plain text fallback
    text_content = f"""
    Password Reset Request - Schema Drift Detector
    
    Hi {username},
    
    We received a request to reset your password.
    
    Your Reset Token: {reset_token}
    
    This token expires in 1 hour.
    
    If you didn't request this, you can safely ignore this email.
    """

    try:
        # Create message
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{SMTP_FROM_NAME} <{SMTP_USER}>"
        msg["To"] = to_email
        
        # Attach both plain text and HTML versions
        msg.attach(MIMEText(text_content, "plain"))
        msg.attach(MIMEText(html_content, "html"))
        
        # Send email
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_USER, to_email, msg.as_string())
        
        print(f"✅ Reset email sent to {to_email}")
        return True
        
    except Exception as e:
        print(f"❌ Failed to send email: {str(e)}")
        return False


def send_verification_email(to_email: str, verification_token: str, username: str) -> bool:
    """
    Send email verification email with the verification token.
    Returns True if email sent successfully, False otherwise.
    """
    if not SMTP_USER or not SMTP_PASSWORD:
        print("⚠️ SMTP credentials not configured. Verification token:", verification_token)
        return False

    subject = "Verify Your Email - Schema Drift Detector"
    
    # HTML email template
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body style="margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #030712;">
        <div style="max-width: 600px; margin: 0 auto; padding: 40px 20px;">
            <div style="background: linear-gradient(135deg, rgba(16, 185, 129, 0.1), rgba(99, 102, 241, 0.1)); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 16px; padding: 40px; text-align: center;">
                
                <!-- Logo -->
                <div style="width: 60px; height: 60px; background: linear-gradient(135deg, #10b981, #6366f1); border-radius: 12px; margin: 0 auto 24px; display: flex; align-items: center; justify-content: center;">
                    <span style="font-size: 28px;">✉️</span>
                </div>
                
                <h1 style="color: #f9fafb; font-size: 24px; margin: 0 0 16px; font-weight: 700;">Verify Your Email</h1>
                
                <p style="color: #9ca3af; font-size: 16px; line-height: 1.6; margin: 0 0 24px;">
                    Hi <strong style="color: #f9fafb;">{username}</strong>,<br>
                    Thanks for signing up! Please verify your email address using the code below.
                </p>
                
                <!-- Token Box -->
                <div style="background: rgba(0, 0, 0, 0.3); border: 1px solid rgba(16, 185, 129, 0.3); border-radius: 12px; padding: 20px; margin: 24px 0;">
                    <p style="color: #9ca3af; font-size: 12px; text-transform: uppercase; letter-spacing: 1px; margin: 0 0 8px;">Your Verification Code</p>
                    <p style="color: #10b981; font-size: 32px; font-weight: 700; font-family: monospace; margin: 0; letter-spacing: 4px;">{verification_token}</p>
                </div>
                
                <p style="color: #9ca3af; font-size: 14px; margin: 24px 0 0;">
                    ⏰ This code expires in <strong style="color: #f9fafb;">24 hours</strong>.
                </p>
                
                <hr style="border: none; border-top: 1px solid rgba(255, 255, 255, 0.1); margin: 32px 0;">
                
                <p style="color: #6b7280; font-size: 12px; margin: 0;">
                    If you didn't create an account, you can safely ignore this email.
                </p>
            </div>
            
            <p style="color: #4b5563; font-size: 12px; text-align: center; margin-top: 24px;">
                © 2025 Schema Drift Detector
            </p>
        </div>
    </body>
    </html>
    """
    
    # Plain text fallback
    text_content = f"""
    Verify Your Email - Schema Drift Detector
    
    Hi {username},
    
    Thanks for signing up! Please verify your email address.
    
    Your Verification Code: {verification_token}
    
    This code expires in 24 hours.
    
    If you didn't create an account, you can safely ignore this email.
    """

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{SMTP_FROM_NAME} <{SMTP_USER}>"
        msg["To"] = to_email
        
        msg.attach(MIMEText(text_content, "plain"))
        msg.attach(MIMEText(html_content, "html"))
        
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_USER, to_email, msg.as_string())
        
        print(f"✅ Verification email sent to {to_email}")
        return True
        
    except Exception as e:
        print(f"❌ Failed to send verification email: {str(e)}")
        return False
