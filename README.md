# LABFLOW — Diagnostic Report Delivery Portal

LABFLOW is a web-based diagnostic report delivery portal developed for the Isocode Labs assignment.

It provides role-specific workflows for laboratory staff, patients, doctors, and pathologists.

The application is built using FastAPI, SQLite, SQLAlchemy, and a responsive HTML/CSS/JavaScript frontend.

## Features

### Staff
- Staff authentication.
- Dashboard overview.
- Patient and order search.
- Report delivery and resend workflow.
- Laboratory CSV import.
- PDF report access.
- Delivery and access event visibility.
- Callback and patient feedback visibility.

### Patients
- OTP-based authentication.
- Consent management.
- Patient order listing.
- Diagnostic report access.
- Secure report link workflow.
- PDF downloads.
- Patient feedback submission.

### Doctors
- Doctor authentication.
- Assigned report listing.
- Signed report information.
- Test results and reference ranges.

### Pathologists
- Pathologist authentication.
- Pending summary review.
- Summary approval and rejection.
- Optional review notes.
- Review metrics.

### Clinical Summaries
- Deterministic critical-result detection.
- AI-assisted explanations for non-critical abnormal values.
- Multilingual fallback templates.

## Technology Stack

- Python
- FastAPI
- SQLite
- SQLAlchemy
- HTML5
- CSS3
- JavaScript
- Pytest
- HTTPX
- Pydantic Settings

## Project Structure

```text
LABFLOW/
│
├── app/
│   ├── main.py
│   ├── database.py
│   ├── models.py
│   ├── security.py
│   ├── config.py
│   ├── seed.py
│   ├── summary.py
│   │
│   └── static/
│       ├── index.html
│       ├── app.js
│       └── style.css
│
├── tests/
│   └── test_summary.py
│
├── sample_data/
│   ├── lis_export.csv
│   └── reports/
│
├── .env.example
├── requirements.txt
├── README.md
├── TDD.md
└── deployment.md
```

## Requirements

- Python 3.10 or later.
- Git.
- VS Code (recommended).

Node.js is not required for the standard application setup.

## Installation

Clone or extract the project and open the project directory in PowerShell.

Create a virtual environment:

```powershell
python -m venv .venv
```

Activate it:

```powershell
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

Create the environment configuration:

```powershell
Copy-Item .env.example .env
```

## Run the Application

```powershell
python -m uvicorn app.main:app --reload
```

Open:

- Application: http://127.0.0.1:8000
- API documentation: http://127.0.0.1:8000/docs

## Demo Credentials

**Front Desk**

- Email: `desk@labflow.demo`
- Password: `LabflowDemo!2026`

**Patient**

- Mobile: `9000000001`
- Request an OTP and check the development server terminal.

The development OTP is printed in the server terminal. No real SMS is sent.

Sample orders include:

- `ORD-71204`
- `ORD-71219`
- `ORD-71233`

Sample CSV:

`sample_data/lis_export.csv`

## Environment Variables

The application uses the following configuration variables:

| Variable | Purpose |
|---|---|
| `APP_ENV` | Application environment |
| `SECRET_KEY` | Application secret |
| `DATABASE_URL` | Database connection |
| `REPORT_LINK_TTL_HOURS` | Report link validity configuration |
| `OTP_TTL_MINUTES` | OTP validity configuration |
| `AI_API_BASE_URL` | AI provider endpoint |
| `AI_API_KEY` | AI provider API key |
| `AI_MODEL` | AI model identifier |

Never commit `.env` or actual API credentials.

## Testing

Run the test suite:

```powershell
python -m pytest -v
```

The project includes tests under the `tests/` directory.

## Important Notes

- All sample data is fictional.
- OTP is mocked for development.
- WhatsApp/SMS delivery is not a live integration.
- Critical-result detection is deterministic.
- AI is used only for non-critical abnormal-result explanations.
- Multilingual fallback templates are available when an AI provider is not configured.
- The potassium example is marked critical according to the assignment sample and is not a universal clinical threshold.

## Production Readiness

LABFLOW is a development prototype, not a production clinical system.

Production use requires persistent session management, managed database infrastructure, secure authentication, rate limiting, HTTPS/TLS, backups, real messaging provider integration, security review, and verified data residency.

## License

Developed for the Isocode Labs assignment.