# LABFLOW — Deployment Notes

## 1. Overview

LABFLOW is a FastAPI-based diagnostic report delivery portal.

This document describes the local development setup and deployment requirements.

**Current deployment status:** Local development deployment. No public production deployment is configured.

## 2. Prerequisites

- Python 3.10 or later.
- Git.
- VS Code (recommended).
- PowerShell on Windows.

## 3. Project Setup

Open PowerShell in the LABFLOW project directory.

Create a virtual environment:

```powershell
python -m venv .venv
```

Activate the environment:

```powershell
.\.venv\Scripts\Activate.ps1
```

If script execution is blocked:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

## 4. Environment Configuration

Create the local environment file:

```powershell
Copy-Item .env.example .env
```

Configure the following variables in `.env`:

```env
APP_ENV=development
SECRET_KEY=change-this-secret
DATABASE_URL=sqlite:///./labflow.db
REPORT_LINK_TTL_HOURS=72
OTP_TTL_MINUTES=5

AI_API_BASE_URL=
AI_API_KEY=
AI_MODEL=
```

For local development, the provided SQLite configuration can be used.

If AI integration is required, configure a compatible AI provider and its credentials.

**Security:** Never commit `.env` or actual API keys to Git.

## 5. Start the Application

Run:

```powershell
python -m uvicorn app.main:app --reload
```

The development server will be available at:

Application:

`http://127.0.0.1:8000`

API documentation:

`http://127.0.0.1:8000/docs`

The `--reload` option is intended for development, not production.

## 6. Demo Access

### Front Desk

- Email: `desk@labflow.demo`
- Password: `LabflowDemo!2026`

### Patient

- Mobile: `9000000001`
- Request OTP through the application.
- Check the development terminal for the mocked OTP.

All demonstration data is fictional.

## 7. Sample Data

Sample laboratory CSV files are available under:

`sample_data/`

Primary import sample:

`sample_data/lis_export.csv`

Sample report PDFs are available under:

`sample_data/reports/`

## 8. Testing

Install dependencies and run:

```powershell
python -m pytest -v
```

This executes the available Pytest suite.

## 9. Database

The current development configuration uses SQLite.

Configured database URL:

`sqlite:///./labflow.db`

The database is stored locally in the project directory.

Production deployment should use a managed database service with appropriate access controls, backups, and recovery procedures.

## 10. Production Deployment Requirements

The current project does not have a configured public production deployment.

Before production deployment, the following requirements must be addressed:

- Production-grade authentication and session management.
- Persistent one-time secure-link verification.
- Rate limiting.
- Secure cookie and session configuration.
- Managed PostgreSQL or another approved production database.
- HTTPS/TLS.
- Secure secret management.
- Database backups and recovery.
- Real SMS/WhatsApp provider integration.
- Production monitoring and logging.
- Security assessment.
- Verified hosting region and data residency.

Clinical workflows and medical thresholds must also undergo appropriate validation.

## 11. Troubleshooting

### Application does not start

Verify that the virtual environment is activated and dependencies are installed.

```powershell
python -m pip install -r requirements.txt
```

### Port 8000 is already in use

Start the application on another port:

```powershell
python -m uvicorn app.main:app --reload --port 8001
```

### Patient OTP is not received by SMS

OTP is mocked in the development environment. Check the server terminal for the generated OTP.

### AI summary provider is unavailable

Verify the AI provider endpoint, API key, and model configuration. The application also supports its implemented fallback templates.

## 12. Deployment Status

LABFLOW is currently configured for local development.

No public production deployment or live SMS/WhatsApp integration is configured.