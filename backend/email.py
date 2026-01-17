import os
from dotenv import load_dotenv

load_dotenv()

# Resend Configuration (works from cloud platforms like Render)
RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
FROM_EMAIL = os.getenv("FROM_EMAIL", "Schema Drift Detector <onboarding@resend.dev>")

def send_verification_email(to_email: str, verification_token: str, username: str) -> bool:
    """
    Send email verification email using Resend API.
    Returns True if email sent successfully, False otherwise.
    """
    if not RESEND_API_KEY:
        print(f"⚠️ RESEND_API_KEY not configured. Verification code: {verification_token}")
        return False

    try:
        import resend
        resend.api_key = RESEND_API_KEY

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
                    
                    <div style="width: 60px; height: 60px; background: linear-gradient(135deg, #10b981, #6366f1); border-radius: 12px; margin: 0 auto 24px; display: flex; align-items: center; justify-content: center;">
                        <span style="font-size: 28px;">✉️</span>
                    </div>
                    
                    <h1 style="color: #f9fafb; font-size: 24px; margin: 0 0 16px; font-weight: 700;">Verify Your Email</h1>
                    
                    <p style="color: #9ca3af; font-size: 16px; line-height: 1.6; margin: 0 0 24px;">
                        Hi <strong style="color: #f9fafb;">{username}</strong>,<br>
                        Thanks for signing up! Please verify your email address using the code below.
                    </p>
                    
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
                    © 2026 Schema Drift Detector
                </p>
            </div>
        </body>
        </html>
        """

        r = resend.Emails.send({
            "from": FROM_EMAIL,
            "to": [to_email],
            "subject": "Verify Your Email - Schema Drift Detector",
            "html": html_content
        })

        print(f"✅ Verification email sent to {to_email} via Resend")
        return True

    except Exception as e:
        print(f"❌ Failed to send verification email: {str(e)}")
        return False


def send_reset_email(to_email: str, reset_token: str, username: str) -> bool:
    """
    Send password reset email using Resend API.
    Returns True if email sent successfully, False otherwise.
    """
    if not RESEND_API_KEY:
        print(f"⚠️ RESEND_API_KEY not configured. Reset token: {reset_token}")
        return False

    try:
        import resend
        resend.api_key = RESEND_API_KEY

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
                    
                    <div style="width: 60px; height: 60px; background: linear-gradient(135deg, #6366f1, #a855f7); border-radius: 12px; margin: 0 auto 24px; display: flex; align-items: center; justify-content: center;">
                        <span style="font-size: 28px;">🔐</span>
                    </div>
                    
                    <h1 style="color: #f9fafb; font-size: 24px; margin: 0 0 16px; font-weight: 700;">Password Reset Request</h1>
                    
                    <p style="color: #9ca3af; font-size: 16px; line-height: 1.6; margin: 0 0 24px;">
                        Hi <strong style="color: #f9fafb;">{username}</strong>,<br>
                        We received a request to reset your password. Use the token below to reset it.
                    </p>
                    
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
                    © 2026 Schema Drift Detector
                </p>
            </div>
        </body>
        </html>
        """

        r = resend.Emails.send({
            "from": FROM_EMAIL,
            "to": [to_email],
            "subject": "Password Reset Request - Schema Drift Detector",
            "html": html_content
        })

        print(f"✅ Reset email sent to {to_email} via Resend")
        return True

    except Exception as e:
        print(f"❌ Failed to send reset email: {str(e)}")
        return False
