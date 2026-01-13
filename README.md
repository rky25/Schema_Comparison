# Schema Drift Detector

Professional-grade database schema comparison tool with AI-powered migration scripts.

## Features
- 📊 Compare database schemas (CSV/Excel)
- 🤖 AI-generated SQL migration scripts
- 🔐 User authentication with email verification
- 📜 Comparison history tracking
- 🔒 Password reset via email

## Quick Start

### 1. Install Python
Download Python 3.10+ from [python.org](https://python.org)

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure Environment
```bash
# Copy example config
copy .env.example .env   # Windows
cp .env.example .env     # Mac/Linux

# Edit .env with your credentials:
# - OPENROUTER_API_KEY: Your AI API key from openrouter.ai
# - SMTP_USER: Your Gmail address
# - SMTP_PASSWORD: Your Gmail App Password
```

### 4. Run the Server
```bash
uvicorn app:app --reload
```

### 5. Open in Browser
Go to: http://localhost:8000

## First Time Setup

1. Register a new account
2. Check your email for verification code
3. Enter the code to verify
4. Login and start comparing schemas!

## Project Structure
```
schema/
├── app.py              # Main FastAPI application
├── compare.py          # Schema comparison logic
├── backend/
│   ├── auth.py         # Authentication functions
│   ├── database.py     # SQLAlchemy models
│   └── email.py        # Email sending functions
├── templates/          # HTML templates
│   ├── index.html      # Main upload page
│   ├── login.html      # Login/Register page
│   ├── history.html    # Comparison history
│   └── sql_preview.html
├── requirements.txt    # Python dependencies
├── .env.example        # Example configuration
└── users.db           # SQLite database (auto-created)
```

## Tech Stack
- **Backend**: FastAPI + SQLAlchemy
- **Frontend**: Vanilla JS + CSS
- **Database**: SQLite
- **Auth**: JWT + bcrypt
- **Email**: Gmail SMTP

## License
MIT
