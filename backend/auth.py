from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import os
from dotenv import load_dotenv

load_dotenv()

import bcrypt

# SECRET_KEY and other config...
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-goes-here")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def verify_password(plain_password, hashed_password):
    if isinstance(hashed_password, str):
        hashed_password = hashed_password.encode('utf-8')
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password)

def get_password_hash(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        return username
    except JWTError:
        raise credentials_exception


# =================================================
# PASSWORD RESET TOKEN FUNCTIONS
# =================================================
import secrets
from datetime import datetime

RESET_TOKEN_EXPIRE_HOURS = 1

def generate_reset_token() -> str:
    """Generate a secure random token for password reset."""
    return secrets.token_urlsafe(32)

def create_reset_token_record(db, user_id: int) -> str:
    """Create a password reset token record in the database."""
    from backend.database import PasswordResetToken
    
    # Invalidate any existing unused tokens for this user
    db.query(PasswordResetToken).filter(
        PasswordResetToken.user_id == user_id,
        PasswordResetToken.used == False
    ).update({"used": True})
    
    # Generate new token
    token = generate_reset_token()
    expires_at = datetime.utcnow() + timedelta(hours=RESET_TOKEN_EXPIRE_HOURS)
    
    reset_token = PasswordResetToken(
        user_id=user_id,
        token=token,
        expires_at=expires_at,
        used=False
    )
    
    db.add(reset_token)
    db.commit()
    
    return token

def validate_reset_token(db, token: str):
    """
    Validate a password reset token.
    Returns the user if valid, None otherwise.
    """
    from backend.database import PasswordResetToken, User
    
    reset_token = db.query(PasswordResetToken).filter(
        PasswordResetToken.token == token,
        PasswordResetToken.used == False
    ).first()
    
    if not reset_token:
        return None
    
    # Check if token has expired
    if datetime.utcnow() > reset_token.expires_at:
        return None
    
    # Return the associated user
    return db.query(User).filter(User.id == reset_token.user_id).first()

def mark_token_used(db, token: str) -> bool:
    """Mark a reset token as used."""
    from backend.database import PasswordResetToken
    
    result = db.query(PasswordResetToken).filter(
        PasswordResetToken.token == token
    ).update({"used": True})
    
    db.commit()
    return result > 0


# =================================================
# EMAIL VERIFICATION TOKEN FUNCTIONS
# =================================================
import random
import string

VERIFICATION_TOKEN_EXPIRE_HOURS = 24

def generate_verification_code() -> str:
    """Generate a 6-digit verification code."""
    return ''.join(random.choices(string.digits, k=6))

def create_verification_token_record(db, user_id: int) -> str:
    """Create an email verification token record in the database."""
    from backend.database import EmailVerificationToken
    
    # Invalidate any existing unused tokens for this user
    db.query(EmailVerificationToken).filter(
        EmailVerificationToken.user_id == user_id,
        EmailVerificationToken.used == False
    ).update({"used": True})
    
    # Generate new token (6-digit code)
    token = generate_verification_code()
    expires_at = datetime.utcnow() + timedelta(hours=VERIFICATION_TOKEN_EXPIRE_HOURS)
    
    verification_token = EmailVerificationToken(
        user_id=user_id,
        token=token,
        expires_at=expires_at,
        used=False
    )
    
    db.add(verification_token)
    db.commit()
    
    return token

def validate_verification_token(db, token: str):
    """
    Validate an email verification token.
    Returns the user if valid, None otherwise.
    """
    from backend.database import EmailVerificationToken, User
    
    verification_token = db.query(EmailVerificationToken).filter(
        EmailVerificationToken.token == token,
        EmailVerificationToken.used == False
    ).first()
    
    if not verification_token:
        return None
    
    # Check if token has expired
    if datetime.utcnow() > verification_token.expires_at:
        return None
    
    return db.query(User).filter(User.id == verification_token.user_id).first()

def mark_verification_token_used(db, token: str) -> bool:
    """Mark a verification token as used."""
    from backend.database import EmailVerificationToken
    
    result = db.query(EmailVerificationToken).filter(
        EmailVerificationToken.token == token
    ).update({"used": True})
    
    db.commit()
    return result > 0
