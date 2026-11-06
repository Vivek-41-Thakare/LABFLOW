# LABFLOW
## Technical Design Document (TDD)

**GitHub Repository:** https://github.com/Vivek-41-Thakare/LABFLOW
**Submission Type:** Development MVP

**Project:** LABFLOW — Diagnostic Report Delivery Portal
**Organization:** Isocode Labs
**Document Type:** Technical Design Document
**Application Type:** Web-based Diagnostic Report Management System
**Status:** Development MVP

---

## 1. Introduction

LABFLOW is a web-based diagnostic report delivery portal designed to support communication between diagnostic laboratory staff, doctors, pathologists, and patients.

The application provides role-specific workflows for report management, patient access, report delivery, clinical summary review, and audit event visibility.

The system is developed as a runnable development MVP using FastAPI, SQLite, SQLAlchemy, and a browser-based frontend.

## 2. Technology Stack

| Component | Technology |
|---|---|
| Backend | Python, FastAPI |
| Frontend | HTML5, CSS3, JavaScript |
| Database | SQLite |
| ORM | SQLAlchemy |
| Configuration | Pydantic Settings |
| API Documentation | FastAPI / OpenAPI |
| Testing | Pytest |
| HTTP Client | HTTPX |
| File Import | Python CSV processing |
| AI Integration | OpenAI-compatible API |
| Report Files | PDF |

## 3. System Architecture

LABFLOW follows a client-server architecture.

### 3.1 Frontend Layer

The browser-based frontend provides role-specific interfaces.

Main files:

- `app/static/index.html`
- `app/static/app.js`
- `app/static/style.css`

Responsibilities:

- Display application interfaces.
- Handle user interactions.
- Submit API requests.
- Display reports and workflow information.
- Handle login and role-specific dashboards.
- Display patient feedback and review decisions.

### 3.2 Backend Layer

The backend is implemented using FastAPI.

Main file:

- `app/main.py`

Responsibilities:

- Expose REST API endpoints.
- Process authentication requests.
- Manage patient and staff workflows.
- Handle report access and PDF delivery.
- Process CSV imports.
- Manage pathologist review decisions.
- Provide staff event information.

### 3.3 Database Layer

Main files:

- `app/database.py`
- `app/models.py`

SQLite is used as the development database, with SQLAlchemy providing database interaction.

The database stores application information required by the implemented workflows.

### 3.4 Security Layer

Main file:

- `app/security.py`

This module contains security-related functionality used by the application.

Authentication, role-specific access, OTP workflows, and secure report access are handled through the backend.

### 3.5 Summary Layer

Main file:

- `app/summary.py`

This module handles clinical summary generation and related logic.

Critical detection is deterministic. AI integration is used for explanations of non-critical abnormal values.

Fallback multilingual templates are available when an AI provider is not configured.

## 4. Application Roles

The application provides four primary user workflows.

### 4.1 Front Desk / Staff

Responsibilities:

- Staff authentication.
- Dashboard overview.
- Patient and order search.
- Report delivery and resend workflow.
- CSV-based laboratory data import.
- PDF report access.
- Delivery, access, callback, and feedback event visibility.

### 4.2 Patient

Responsibilities:

- OTP-based authentication.
- Consent management.
- Viewing available orders.
- Accessing diagnostic reports.
- Requesting secure report links.
- Downloading PDF reports.
- Submitting feedback.

### 4.3 Doctor

Responsibilities:

- Doctor authentication.
- Viewing assigned reports.
- Reviewing signed report information.
- Viewing test results and reference ranges.

### 4.4 Pathologist

Responsibilities:

- Pathologist authentication.
- Viewing pending clinical summary reviews.
- Approving summaries.
- Rejecting summaries.
- Submitting optional decision notes.
- Viewing review progress metrics.

## 5. API Design

The backend exposes REST endpoints through FastAPI.

### 5.1 Staff APIs

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/api/staff/login` | Staff authentication |
| GET | `/api/staff/overview` | Dashboard overview |
| GET | `/api/staff/search` | Search records |
| POST | `/api/staff/resend/{ref}` | Resend report workflow |
| POST | `/api/staff/import-csv` | Import laboratory CSV |
| GET | `/api/staff/events` | Retrieve application events |
| GET | `/api/staff/pdf/{ref}` | Access report PDF |

### 5.2 Doctor APIs

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/api/doctor/login` | Doctor authentication |
| GET | `/api/doctor/reports` | Retrieve assigned reports |

### 5.3 Pathologist APIs

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/api/pathologist/login` | Pathologist authentication |
| GET | `/api/pathologist/reviews` | Retrieve pending reviews |
| POST | `/api/pathologist/reviews/{ref}/decision` | Submit review decision |

### 5.4 Patient APIs

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/api/patient/request-otp` | Request OTP |
| POST | `/api/patient/verify-otp` | Verify OTP |
| GET | `/api/patient/consent-status` | Retrieve consent status |
| POST | `/api/patient/consent` | Update consent |
| GET | `/api/patient/orders` | Retrieve patient orders |
| GET | `/api/patient/report/{ref}` | Retrieve report information |
| POST | `/api/patient/feedback/{ref}` | Submit feedback |
| GET | `/api/patient/pdf/{ref}` | Download report PDF |
| POST | `/api/patient/secure-link/{ref}` | Request secure report link |

### 5.5 Secure Report APIs

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/secure/{t}` | Open secure report page |
| POST | `/api/secure/{t}/request-otp` | Request OTP for secure access |
| POST | `/api/secure/{t}/verify-otp` | Verify secure access OTP |
| GET | `/api/secure/{t}/pdf` | Retrieve secure report PDF |

## 6. Data Flow

### 6.1 Patient Authentication

1. Patient submits their registered mobile number.
2. Frontend sends an OTP request.
3. Backend processes the OTP workflow.
4. Patient submits the received development OTP.
5. Backend verifies the OTP.
6. Authorized patient workflows become accessible.

### 6.2 Report Delivery

1. Laboratory staff access the staff dashboard.
2. Staff search for the relevant order.
3. Staff initiate the report delivery workflow.
4. The system records delivery-related events.
5. Patients can access reports through the implemented patient workflows.

### 6.3 Clinical Summary Review

1. Clinical summaries are generated using the implemented summary logic.
2. Pending summaries are presented to the pathologist.
3. The pathologist reviews the summary.
4. The pathologist approves or rejects the summary.
5. The backend processes the decision.

### 6.4 CSV Import

1. Staff select a laboratory CSV file.
2. The frontend submits the file to the import API.
3. Backend processes the uploaded data.
4. Imported records are handled by the application's data processing workflow.

## 7. Security Design

Security-related functionality is implemented through the backend security module and role-specific API workflows.

The application includes:

- Role-specific authentication workflows.
- Patient OTP verification.
- Consent management.
- Secure report access workflows.
- Report access and delivery event visibility.
- Input handling and validation.
- Protection of sensitive configuration through environment variables.

The current implementation is a development MVP and must not be treated as a production clinical deployment.

## 8. AI Integration

LABFLOW supports an optional OpenAI-compatible AI provider.

Configuration:

- `AI_API_BASE_URL`
- `AI_API_KEY`
- `AI_MODEL`

The application uses deterministic critical-result detection. AI is used only for explanations of non-critical abnormal values.

When an AI provider is unavailable or not configured, the application uses its implemented fallback multilingual templates.

## 9. Configuration Management

Application configuration is maintained through environment variables.

The `.env.example` file provides the development configuration template.

Important variables:

- `APP_ENV`
- `SECRET_KEY`
- `DATABASE_URL`
- `REPORT_LINK_TTL_HOURS`
- `OTP_TTL_MINUTES`
- `AI_API_BASE_URL`
- `AI_API_KEY`
- `AI_MODEL`

Actual secrets must never be committed to version control.

## 10. Testing Strategy

The project includes a Pytest-based test suite.

Test location:

`tests/test_summary.py`

Testing should cover:

- Summary generation behavior.
- Critical-result handling.
- Non-critical abnormal-result explanations.
- Fallback summary behavior.

The application also underwent manual workflow and security verification during development.

## 11. Deployment Architecture

The current application supports local development deployment.

Components:

- FastAPI application server.
- SQLite development database.
- Static browser frontend.
- Local PDF report files.
- Optional external AI provider.

Application startup:

`python -m uvicorn app.main:app --reload`

Application URL:

`http://127.0.0.1:8000`

API documentation:

`http://127.0.0.1:8000/docs`

No public production deployment is currently configured.

## 12. Limitations and Future Improvements

The following items require attention before production use:

- Replace development session handling with production-grade persistent session management.
- Replace demo credentials with managed identity and authentication.
- Implement persistent one-time secure-link verification.
- Introduce appropriate rate limiting.
- Implement secure cookie and session management.
- Migrate from SQLite to managed PostgreSQL where required.
- Configure HTTPS/TLS.
- Implement automated backups and recovery.
- Integrate real SMS and WhatsApp providers.
- Complete production security review.
- Verify hosting region and data residency requirements.
- Conduct clinical validation of medical workflows and thresholds.

## 13. Conclusion

LABFLOW provides a working development implementation of a diagnostic report delivery portal with staff, patient, doctor, and pathologist workflows.

Its modular structure separates frontend presentation, backend APIs, database operations, security functionality, and clinical summary processing.

The current implementation provides a foundation for further testing, documentation, and production-readiness improvements.
