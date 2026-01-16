import pandas as pd
from fastapi import FastAPI, UploadFile, File, HTTPException, Request, Depends, status
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
import os
import requests
from dotenv import load_dotenv
from sqlalchemy.orm import Session

# Load environment variables
load_dotenv()
OPENROUTER_API_KEY = (os.getenv("OPENROUTER_API_KEY") or "").strip()
if OPENROUTER_API_KEY.startswith("Bearer "):
    OPENROUTER_API_KEY = OPENROUTER_API_KEY[7:].strip()

from compare import compare_schemas, build_schema_changes_from_df
from backend.database import SessionLocal, User, PasswordResetToken, EmailVerificationToken, ComparisonHistory, init_db
from backend.auth import get_password_hash, verify_password, create_access_token, get_current_user, create_reset_token_record, validate_reset_token, mark_token_used, create_verification_token_record, validate_verification_token, mark_verification_token_used
from backend.email import send_reset_email, send_verification_email

# Initialize database
init_db()

print("🔥 app.py LOADED (AUTH MODE)")

# =================================================
# APP INIT
# =================================================
app = FastAPI()
templates = Jinja2Templates(directory="templates")

latest_comparison_df = None
latest_fix_options = None
last_server_error = "No error recorded yet"

# =================================================
# SECURITY: Rate Limiting for Password Reset
# =================================================
from datetime import datetime, timedelta
from collections import defaultdict

password_reset_attempts = defaultdict(list)  # {email: [timestamps]}
MAX_RESET_ATTEMPTS = 3  # Max attempts per hour
RESET_WINDOW_HOURS = 1

def check_rate_limit(email: str) -> bool:
    """Check if email has exceeded rate limit. Returns True if allowed."""
    now = datetime.utcnow()
    cutoff = now - timedelta(hours=RESET_WINDOW_HOURS)
    
    # Clean old attempts
    password_reset_attempts[email] = [
        t for t in password_reset_attempts[email] if t > cutoff
    ]
    
    if len(password_reset_attempts[email]) >= MAX_RESET_ATTEMPTS:
        return False
    
    password_reset_attempts[email].append(now)
    return True

# =================================================
# SECURITY: Secure HTTP Headers Middleware
# =================================================
from starlette.middleware.base import BaseHTTPMiddleware

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response

app.add_middleware(SecurityHeadersMiddleware)

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# =================================================
# HELPERS
# =================================================
def read_schema_file(upload: UploadFile) -> pd.DataFrame:
    name = upload.filename.lower()
    if name.endswith((".xlsx", ".xls")):
        return pd.read_excel(upload.file, dtype=str).fillna("")
    return pd.read_csv(upload.file, dtype=str).fillna("")

def normalize_mssql_datatype(dtype: str, length: str = "") -> str:
    if not dtype:
        return "VARCHAR(255)"

    dt = dtype.upper()

    mapping = {
        "INT": "INT",
        "INTEGER": "INT",
        "BIGINT": "BIGINT",
        "SMALLINT": "SMALLINT",
        "BOOLEAN": "BIT",
        "BOOL": "BIT",
        "BIT": "BIT",
        "DATE": "DATE",
        "DATETIME": "DATETIME",
        "TIMESTAMP": "DATETIME2",
        "TEXT": "VARCHAR(MAX)",
    }

    base = mapping.get(dt, dt)

    if base in ["VARCHAR", "NVARCHAR"] and length:
        return f"{base}({length})"

    if base in ["DECIMAL", "NUMERIC"] and length:
        return f"{base}({length})"

    return base

# =================================================
# SQL GENERATOR (TEMPLATE ONLY)
# =================================================
def generate_mssql_sql(changes: list) -> str:
    if not changes:
        return "-- No schema changes required"

    sql = []

    by_table = {}
    for c in changes:
        by_table.setdefault(c["table"], []).append(c)

    for table, items in by_table.items():
        sql.append(f"-- Changes for table {table}")

        for c in items:
            if c["change_type"] == "missing_column":
                sql.append(
                    f"ALTER TABLE {table} ADD {c['column']} {c['datatype']};\nGO"
                )

            elif c["change_type"] == "datatype_mismatch":
                sql.append(
                    f"ALTER TABLE {table} ALTER COLUMN {c['column']} {c['to']};\nGO"
                )

            elif c["change_type"] == "column_rename":
                sql.append(
                    f"EXEC sp_rename '{table}.{c['from']}', '{c['to']}', 'COLUMN';\nGO"
                )

        sql.append("")

    return "\n".join(sql)

# =================================================
# AUTH ROUTES
# =================================================
class UserCreate(BaseModel):
    username: str
    email: str
    password: str
    confirm_password: str

@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

import re

@app.post("/register")
def register(user: UserCreate, db: Session = Depends(get_db)):
    try:
        # Basic email validation
        if not re.match(r"[^@]+@[^@]+\.[^@]+", user.email):
            raise HTTPException(status_code=400, detail="Invalid email format")
        
        # Password length validation
        if len(user.password) < 6:
            raise HTTPException(status_code=400, detail="Password must be at least 6 characters long")
        
        if user.password != user.confirm_password:
            raise HTTPException(status_code=400, detail="Passwords do not match")
        
        db_user = db.query(User).filter(User.username == user.username).first()
        if db_user:
            raise HTTPException(status_code=400, detail="Username already registered")
        
        db_email = db.query(User).filter(User.email == user.email).first()
        if db_email:
            raise HTTPException(status_code=400, detail="Email already registered")
        
        hashed_password = get_password_hash(user.password)
        # Auto-verify users so they can login immediately
        new_user = User(username=user.username, email=user.email, hashed_password=hashed_password, is_verified=True)
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        # Try to send verification email in background (non-blocking, optional)
        try:
            verification_token = create_verification_token_record(db, new_user.id)
            send_verification_email(user.email, verification_token, user.username)
        except Exception as email_err:
            print(f"Warning: Could not send verification email: {email_err}")
        
        return {"status": "ok", "message": "Registration successful! You can now login.", "requires_verification": False}
    except Exception as e:
        import traceback
        error_msg = traceback.format_exc()
        global last_server_error
        last_server_error = error_msg
        print(error_msg)
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/token")
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check if email is verified
    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Please verify your email before logging in. Check your inbox for the verification code.",
            headers={"X-Requires-Verification": "true"},
        )
    
    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}

# =================================================
# EMAIL VERIFICATION ROUTES
# =================================================
class VerifyEmailRequest(BaseModel):
    code: str

class ResendVerificationRequest(BaseModel):
    email: str

@app.post("/verify-email")
def verify_email(request: VerifyEmailRequest, db: Session = Depends(get_db)):
    """Verify email with the verification code."""
    try:
        user = validate_verification_token(db, request.code)
        if not user:
            raise HTTPException(status_code=400, detail="Invalid or expired verification code")
        
        # Mark user as verified
        user.is_verified = True
        mark_verification_token_used(db, request.code)
        db.commit()
        
        print(f"✅ Email verified for {user.username}")
        return {"status": "ok", "message": "Email verified successfully! You can now login."}
    
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"❌ Verify email error: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/resend-verification")
def resend_verification(request: ResendVerificationRequest, db: Session = Depends(get_db)):
    """Resend verification email."""
    try:
        user = db.query(User).filter(User.email == request.email).first()
        
        if not user:
            # Don't reveal if email exists
            return {"status": "ok", "message": "If this email is registered, a new verification code will be sent."}
        
        if user.is_verified:
            raise HTTPException(status_code=400, detail="This email is already verified. You can login.")
        
        # Generate new verification token
        verification_token = create_verification_token_record(db, user.id)
        send_verification_email(user.email, verification_token, user.username)
        
        return {"status": "ok", "message": "A new verification code has been sent to your email."}
    
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"❌ Resend verification error: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

# =================================================
# ROUTES
# =================================================
@app.get("/", response_class=HTMLResponse)
def landing_page(request: Request):
    """Public landing page - first thing visitors see."""
    return templates.TemplateResponse("landing.html", {"request": request})

@app.get("/landing", response_class=HTMLResponse)
def landing_redirect(request: Request):
    """Redirect /landing to root for backwards compatibility."""
    return templates.TemplateResponse("landing.html", {"request": request})

@app.get("/app", response_class=HTMLResponse)
def app_dashboard(request: Request):
    """Main app dashboard - requires authentication (handled by frontend)."""
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/compare")
async def compare(
    source_file: UploadFile = File(...), 
    target_file: UploadFile = File(...),
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    global latest_comparison_df

    source = read_schema_file(source_file)
    target = read_schema_file(target_file)

    df = compare_schemas(source, target)
    latest_comparison_df = df

    df.to_excel("FINAL_SCHEMA_COMPARISON.xlsx", index=False)
    
    # Save to history
    try:
        user = db.query(User).filter(User.username == current_user).first()
        if user:
            # Count changes (non-match rows)
            changes_count = len(df[df['status'] != 'match']) if 'status' in df.columns else len(df)
            
            history_entry = ComparisonHistory(
                user_id=user.id,
                source_filename=source_file.filename,
                target_filename=target_file.filename,
                changes_count=changes_count
            )
            db.add(history_entry)
            db.commit()
    except Exception as e:
        print(f"⚠️ Failed to save history: {e}")
    
    return FileResponse("FINAL_SCHEMA_COMPARISON.xlsx")

class FixOptions(BaseModel):
    database: str
    direction: str

class AISQLRequest(BaseModel):
    prompt: str

@app.post("/confirm-fix-options")
def confirm_fix_options(options: FixOptions, current_user: str = Depends(get_current_user)):
    global latest_fix_options
    latest_fix_options = options
    print("🔥 FIX OPTIONS:", latest_fix_options)
    return {"status": "ok"}

# =================================================
# COMPARISON HISTORY ROUTES
# =================================================
@app.get("/history")
def get_history(current_user: str = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get comparison history for current user."""
    user = db.query(User).filter(User.username == current_user).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    history = db.query(ComparisonHistory).filter(
        ComparisonHistory.user_id == user.id
    ).order_by(ComparisonHistory.created_at.desc()).limit(50).all()
    
    return {
        "status": "ok",
        "history": [
            {
                "id": h.id,
                "source_filename": h.source_filename,
                "target_filename": h.target_filename,
                "changes_count": h.changes_count,
                "database_type": h.database_type,
                "direction": h.direction,
                "created_at": h.created_at.isoformat() if h.created_at else None
            }
            for h in history
        ]
    }

@app.delete("/history/{history_id}")
def delete_history(history_id: int, current_user: str = Depends(get_current_user), db: Session = Depends(get_db)):
    """Delete a history entry."""
    user = db.query(User).filter(User.username == current_user).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    history = db.query(ComparisonHistory).filter(
        ComparisonHistory.id == history_id,
        ComparisonHistory.user_id == user.id
    ).first()
    
    if not history:
        raise HTTPException(status_code=404, detail="History entry not found")
    
    db.delete(history)
    db.commit()
    
    return {"status": "ok", "message": "History entry deleted"}

@app.get("/history-page", response_class=HTMLResponse)
def history_page(request: Request):
    return templates.TemplateResponse("history.html", {"request": request})

# =================================================
# SQL PREVIEW (FINAL – NO AI)
# =================================================
@app.get("/sql-preview")
def sql_preview(current_user: str = Depends(get_current_user)):
    print("🔥 TEMPLATE SQL PREVIEW")

    if latest_comparison_df is None or latest_fix_options is None:
        raise HTTPException(400, "Missing comparison data")

    raw = build_schema_changes_from_df(
        latest_comparison_df,
        latest_fix_options.direction
    )

    enhanced = []

    for c in raw:
        if c["change_type"] == "missing_table":
            continue

        row = latest_comparison_df[
            (latest_comparison_df["table_name"] == c["table"])
        ].iloc[0]

        if c["change_type"] == "missing_column":
            dtype = row["source_datatype"]
            length = row["source_length"]
            c["datatype"] = normalize_mssql_datatype(dtype, length)

        if c["change_type"] == "datatype_mismatch":
            c["to"] = normalize_mssql_datatype(c["to"])

        enhanced.append(c)

    # Rename/alias this if we have other generators, otherwise use the generic/MSSQL one as base
    # In a real app, we'd have generate_oracle_sql(enhanced), etc.
    # For now, we will use the existing generator but ensure the Preview UI knows the target DB.
    
    sql = generate_mssql_sql(enhanced)
    
    return {
        "database": latest_fix_options.database.upper(),
        "direction": latest_fix_options.direction.replace("_", " ").upper(),
        "sql": sql,
        "changes_count": len(enhanced),
        "changes": enhanced
    }

@app.get("/preview", response_class=HTMLResponse)
def preview_page(request: Request):
    return templates.TemplateResponse("sql_preview.html", {"request": request})

@app.post("/generate-ai-sql")
def generate_ai_sql(req: AISQLRequest, current_user: str = Depends(get_current_user)):
    if not OPENROUTER_API_KEY:
        raise HTTPException(status_code=500, detail="API Key not configured on server")

    try:
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
                "HTTP-Referer": "http://localhost:8000",
                "X-Title": "Schema Drift Detector"
            },
            json={
                "model": "deepseek/deepseek-chat",
                "messages": [
                    {"role": "user", "content": req.prompt}
                ]
            }
        )
        
        if not response.ok:
            print(f"❌ AI Error: {response.text}")
            raise HTTPException(status_code=response.status_code, detail="AI Generation failed")

        return response.json()
    except Exception as e:
        print(f"❌ AI Exception: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# =================================================
# PASSWORD RESET ROUTES
# =================================================
class ForgotPasswordRequest(BaseModel):
    email: str

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str
    confirm_password: str

@app.post("/forgot-password")
def forgot_password(request: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """Request a password reset email."""
    try:
        # SECURITY: Rate limiting check
        if not check_rate_limit(request.email.lower()):
            raise HTTPException(
                status_code=429, 
                detail="Too many reset attempts. Please try again in 1 hour."
            )
        
        # Find user by email
        user = db.query(User).filter(User.email == request.email).first()
        
        # Return error if email is not registered
        if not user:
            raise HTTPException(
                status_code=400, 
                detail="This email is not registered. Please create an account first."
            )
        
        # Generate reset token
        token = create_reset_token_record(db, user.id)
        
        # Send email
        email_sent = send_reset_email(request.email, token, user.username)
        
        if not email_sent:
            print(f"📧 Reset token for {user.email}: {token}")
        
        return {"status": "ok", "message": "Password reset email sent! Check your inbox."}
    
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"❌ Forgot password error: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/verify-reset-token/{token}")
def verify_reset_token(token: str, db: Session = Depends(get_db)):
    """Verify if a reset token is valid."""
    user = validate_reset_token(db, token)
    
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired token")
    
    return {"status": "ok", "valid": True, "username": user.username}

@app.post("/reset-password")
def reset_password(request: ResetPasswordRequest, db: Session = Depends(get_db)):
    """Reset password using the token."""
    try:
        # SECURITY: Stronger password validation
        password = request.new_password
        if len(password) < 8:
            raise HTTPException(status_code=400, detail="Password must be at least 8 characters long")
        
        if not any(c.isupper() for c in password):
            raise HTTPException(status_code=400, detail="Password must contain at least one uppercase letter")
        
        if not any(c.islower() for c in password):
            raise HTTPException(status_code=400, detail="Password must contain at least one lowercase letter")
        
        if not any(c.isdigit() for c in password):
            raise HTTPException(status_code=400, detail="Password must contain at least one number")
        
        if request.new_password != request.confirm_password:
            raise HTTPException(status_code=400, detail="Passwords do not match")
        
        # Validate token
        user = validate_reset_token(db, request.token)
        if not user:
            raise HTTPException(status_code=400, detail="Invalid or expired token")
        
        # Update password
        user.hashed_password = get_password_hash(request.new_password)
        
        # Mark token as used
        mark_token_used(db, request.token)
        
        db.commit()
        
        print(f"✅ Password reset successful for {user.username}")
        return {"status": "ok", "message": "Password has been reset successfully. You can now login."}
    
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"❌ Reset password error: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
def health_check():
    return {"status": "ok", "version": "2.3"}

@app.get("/last-error")
def get_last_error():
    return {"error": last_server_error}

