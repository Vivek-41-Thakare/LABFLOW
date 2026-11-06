from datetime import datetime, timedelta
from pathlib import Path
import csv
import secrets

from fastapi import (
    FastAPI,
    Depends,
    HTTPException,
    UploadFile,
    File,
    Header
)
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.database import Base, engine, get_db, SessionLocal
from app.models import (
    Patient,
    Order,
    ResultValue,
    OTPChallenge,
    AccessEvent,
    DeliveryEvent,
    CallbackTask,
    SummaryFeedback,
    NotificationMessage
)
from app.models import PathologistReview, PatientConsent
from app.security import otp, digest, expires, token
from app.config import settings
from app.summary import summarize
from app.seed import seed


# --------------------------------------------------
# APPLICATION
# --------------------------------------------------

app = FastAPI(
    title="LABFLOW API",
    version="1.0.0"
)

SESSIONS = {}
LINKS = {}


@app.on_event("startup")
def startup():
    Base.metadata.create_all(engine)
    seed()

    db = SessionLocal()

    try:
        ready_orders = (
            db.query(Order)
            .filter(
                Order.status == "Ready",
                Order.signed_at.isnot(None)
            )
            .all()
        )

        for order in ready_orders:
            existing = (
                db.query(PathologistReview)
                .filter(PathologistReview.order_id == order.id)
                .first()
            )

            if existing:
                continue

            values = (
                db.query(ResultValue)
                .filter(ResultValue.order_id == order.id)
                .all()
            )

            if not values:
                continue

            summary_result = summarize(values)

            if summary_result["status"] == "SUPPRESSED_CRITICAL":
                continue

            db.add(
                PathologistReview(
                    order_id=order.id,
                    summary_text=summary_result["text"],
                    summary_source=summary_result["source"],
                    status="PENDING"
                )
            )

        db.commit()

    finally:
        db.close()


app.mount(
    "/static",
    StaticFiles(directory="app/static"),
    name="static"
)


@app.get("/", response_class=HTMLResponse)
def home():
    return Path("app/static/index.html").read_text(
        encoding="utf-8"
    )


# --------------------------------------------------
# COMMON HELPERS
# --------------------------------------------------

def audit(db, actor, action, ref=""):
    db.add(
        AccessEvent(
            actor=actor,
            action=action,
            order_ref=ref
        )
    )
    db.commit()



def create_report_notification(order, db, actor):
    t = token()
    expiry = datetime.utcnow() + timedelta(
        hours=settings.report_link_ttl_hours
    )

    LINKS[t] = {
        "ref": order.order_ref,
        "mobile": order.patient.mobile,
        "expiry": expiry,
        "verified": False
    }

    secure_url = "/secure/" + t

    message = (
        f"LABFLOW: Your report {order.order_ref} is ready. "
        f"Open {secure_url}. "
        f"This link expires in {settings.report_link_ttl_hours} hours. "
        "OTP verification is required to view the report."
    )

    destination = "******" + order.patient.mobile[-4:]

    db.add(
        NotificationMessage(
            order_ref=order.order_ref,
            channel="MOCK_WHATSAPP",
            destination=destination,
            message=message,
            status="SIMULATED"
        )
    )

    db.add(
        DeliveryEvent(
            order_ref=order.order_ref,
            channel="MOCK_WHATSAPP",
            status="SIMULATED",
            destination=destination
        )
    )

    db.add(
        AccessEvent(
            actor=actor,
            action="CREATE_EXPIRING_LINK",
            order_ref=order.order_ref
        )
    )

    return secure_url

def staff(auth):
    if (
        not auth
        or not auth.startswith("Bearer ")
        or SESSIONS.get(auth[7:]) != "STAFF"
    ):
        raise HTTPException(
            status_code=401,
            detail="Front-desk login required"
        )


def patient(auth):
    if (
        not auth
        or not auth.startswith("Bearer ")
        or SESSIONS.get(auth[7:]) in (None, "STAFF")
    ):
        raise HTTPException(
            status_code=401,
            detail="OTP login required"
        )

    return SESSIONS[auth[7:]]


def get_secure_link(t):
    x = LINKS.get(t)

    if not x:
        raise HTTPException(
            status_code=410,
            detail="Secure link not found or expired"
        )

    if x["expiry"] < datetime.utcnow():
        LINKS.pop(t, None)

        raise HTTPException(
            status_code=410,
            detail="Secure link expired"
        )

    return x


# --------------------------------------------------
# STAFF LOGIN
# --------------------------------------------------

@app.post("/api/staff/login")
def staff_login(p: dict):

    if (
        p.get("email") != "desk@labflow.demo"
        or p.get("password") != "LabflowDemo!2026"
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid demo credentials"
        )

    t = token()
    SESSIONS[t] = "STAFF"

    return {
        "token": t
    }


# --------------------------------------------------
# DOCTOR LOGIN
# --------------------------------------------------

DOCTOR_CREDENTIALS = {
    "Dr. S. Ramanaiah": "Ramanaiah@2026",
    "Dr. P. Anitha": "Anitha@2026",
    "Dr. K. Suresh": "Suresh@2026"
}


@app.post("/api/doctor/login")
def doctor_login(p: dict):

    doctor_name = str(p.get("doctor_name", "")).strip()
    password = str(p.get("password", ""))

    if DOCTOR_CREDENTIALS.get(doctor_name) != password:
        raise HTTPException(
            status_code=401,
            detail="Invalid doctor credentials"
        )

    t = token()
    SESSIONS[t] = "DOCTOR:" + doctor_name

    return {
        "token": t,
        "doctor": doctor_name
    }


# --------------------------------------------------
# PATHOLOGIST LOGIN
# --------------------------------------------------

PATHOLOGIST_CREDENTIALS = {
    "Dr. Meera Pathologist": "Pathologist@2026"
}


@app.post("/api/pathologist/login")
def pathologist_login(p: dict):

    name = str(p.get("name", "")).strip()
    password = str(p.get("password", ""))

    if PATHOLOGIST_CREDENTIALS.get(name) != password:
        raise HTTPException(
            status_code=401,
            detail="Invalid pathologist credentials"
        )

    t = token()
    SESSIONS[t] = "PATHOLOGIST:" + name

    return {
        "token": t,
        "pathologist": name
    }


# --------------------------------------------------# DOCTOR REPORTS — LAST 90 DAYS
# --------------------------------------------------

@app.get("/api/doctor/reports")
def doctor_reports(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db)
):

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Doctor login required"
        )

    session_role = SESSIONS.get(authorization[7:], "")

    if not session_role.startswith("DOCTOR:"):
        raise HTTPException(
            status_code=403,
            detail="Doctor access required"
        )

    doctor_name = session_role.replace("DOCTOR:", "", 1)
    cutoff = datetime.utcnow() - timedelta(days=90)

    orders = (
        db.query(Order)
        .filter(
            Order.doctor_name == doctor_name,
            Order.status == "Ready",
            Order.signed_at >= cutoff
        )
        .order_by(Order.signed_at.desc())
        .all()
    )

    reports = []

    for order in orders:
        values = (
            db.query(ResultValue)
            .filter_by(order_id=order.id)
            .all()
        )

        reports.append({
            "order_ref": order.order_ref,
            "patient_name": order.patient.name,
            "patient_code": order.patient.patient_code,
            "test_name": order.test_name,
            "status": order.status,
            "signed_at": order.signed_at.isoformat() if order.signed_at else None,
            "results": [
                {
                    "analyte": value.analyte,
                    "value": value.value,
                    "unit": value.unit,
                    "reference_range": f"{value.low}–{value.high}",
                    "flag": value.flag,
                    "critical": value.critical
                }
                for value in values
            ]
        })

        audit(
            db,
            "doctor:" + doctor_name,
            "VIEW_DOCTOR_REPORT",
            order.order_ref
        )

    return {
        "doctor": doctor_name,
        "period_days": 90,
        "count": len(reports),
        "reports": reports
    }


# --------------------------------------------------
# --------------------------------------------------
# PATHOLOGIST REVIEW QUEUE
# --------------------------------------------------

@app.get("/api/pathologist/reviews")
def pathologist_reviews(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db)
):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Pathologist login required")

    session_role = SESSIONS.get(authorization[7:], "")

    if not session_role.startswith("PATHOLOGIST:"):
        raise HTTPException(status_code=403, detail="Pathologist access required")

    reviewer_name = session_role.replace("PATHOLOGIST:", "", 1)

    pending = (
        db.query(PathologistReview)
        .filter(PathologistReview.status == "PENDING")
        .order_by(PathologistReview.created_at.asc())
        .all()
    )

    reviews = []

    for review in pending:
        order = db.query(Order).filter_by(id=review.order_id).first()

        if order:
            reviews.append({
                "order_ref": order.order_ref,
                "test_name": order.test_name,
                "patient_name": order.patient.name,
                "summary_text": review.summary_text,
                "summary_source": review.summary_source,
                "status": review.status,
                "created_at": review.created_at.isoformat()
            })

    now = datetime.utcnow()
    week_start = (now - timedelta(days=now.weekday())).replace(
        hour=0, minute=0, second=0, microsecond=0
    )

    reviewed_this_week = (
        db.query(PathologistReview)
        .filter(
            PathologistReview.reviewed_at >= week_start,
            PathologistReview.status.in_(["APPROVED", "REJECTED"])
        )
        .count()
    )

    return {
        "pathologist": reviewer_name,
        "pending_count": len(reviews),
        "weekly_target": 50,
        "reviewed_this_week": reviewed_this_week,
        "reviews": reviews
    }


@app.post("/api/pathologist/reviews/{ref}/decision")
def pathologist_review_decision(
    ref: str,
    p: dict,
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db)
):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Pathologist login required")

    session_role = SESSIONS.get(authorization[7:], "")

    if not session_role.startswith("PATHOLOGIST:"):
        raise HTTPException(status_code=403, detail="Pathologist access required")

    reviewer_name = session_role.replace("PATHOLOGIST:", "", 1)

    decision = str(p.get("decision", "")).strip().upper()
    note = str(p.get("note", "")).strip()

    if decision not in ("APPROVED", "REJECTED"):
        raise HTTPException(
            status_code=400,
            detail="Decision must be APPROVED or REJECTED"
        )

    review = (
        db.query(PathologistReview)
        .join(Order, PathologistReview.order_id == Order.id)
        .filter(Order.order_ref == ref)
        .first()
    )

    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    if review.status != "PENDING":
        raise HTTPException(status_code=409, detail="Review already completed")

    review.status = decision
    review.reviewer = reviewer_name
    review.decision_note = note
    review.reviewed_at = datetime.utcnow()

    audit(
        db,
        "pathologist:" + reviewer_name,
        "PATHOLOGIST_REVIEW_" + decision,
        ref
    )

    return {
        "order_ref": ref,
        "decision": decision,
        "reviewer": reviewer_name,
        "reviewed_at": review.reviewed_at.isoformat()
    }


# PATIENT OTP LOGIN
# --------------------------------------------------

@app.post("/api/patient/request-otp")
def request_otp(
    p: dict,
    db: Session = Depends(get_db)
):
    mobile = str(p.get("mobile", "")).strip()

    if not mobile.isdigit() or len(mobile) < 10:
        raise HTTPException(
            status_code=400,
            detail="Enter valid mobile number"
        )

    registered = (
        db.query(Patient)
        .filter_by(mobile=mobile)
        .first()
    )

    if not registered:
        return {
            "message": "If registered, an OTP was generated."
        }

    code = otp()

    db.query(OTPChallenge).filter_by(
        mobile=mobile,
        consumed=False
    ).update(
        {"consumed": True}
    )

    db.add(
        OTPChallenge(
            mobile=mobile,
            code_hash=digest(code),
            expires_at=expires(settings.otp_ttl_minutes)
        )
    )

    db.commit()

    print(
        f"\n[MOCK OTP] Mobile ending {mobile[-4:]} => {code}\n"
    )

    return {
        "message": "Demo OTP is printed in your VS Code terminal."
    }


@app.post("/api/patient/verify-otp")
def verify_otp(
    p: dict,
    db: Session = Depends(get_db)
):
    mobile = str(p.get("mobile", "")).strip()
    code = str(p.get("otp", "")).strip()

    ch = (
        db.query(OTPChallenge)
        .filter_by(
            mobile=mobile,
            consumed=False
        )
        .order_by(OTPChallenge.id.desc())
        .first()
    )

    if (
        not ch
        or ch.expires_at < datetime.utcnow()
        or not secrets.compare_digest(
            ch.code_hash,
            digest(code)
        )
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired OTP"
        )

    ch.consumed = True
    db.commit()

    t = token()
    SESSIONS[t] = mobile

    audit(
        db,
        "patient:" + mobile[-4:],
        "OTP_LOGIN"
    )

    profiles = (
        db.query(Patient)
        .filter_by(mobile=mobile)
        .all()
    )

    return {
        "token": t,
        "profiles": [
            {
                "patient_code": x.patient_code,
                "name": x.name
            }
            for x in profiles
        ]
    }


# --------------------------------------------------

# --------------------------------------------------
# PATIENT PRIVACY CONSENT
# --------------------------------------------------

CONSENT_POLICY_VERSION = "LABFLOW-DPDP-1.0"


def current_consent(db, patient_id):
    return (
        db.query(PatientConsent)
        .filter_by(patient_id=patient_id)
        .order_by(PatientConsent.id.desc())
        .first()
    )


def require_patient_consent(db, profile):
    consent = current_consent(db, profile.id)

    if not consent or consent.action != "ACCEPTED":
        raise HTTPException(
            status_code=403,
            detail="Patient privacy consent is required before accessing reports."
        )

    return consent


@app.get("/api/patient/consent-status")
def patient_consent_status(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db)
):
    mobile = patient(authorization)

    profiles = (
        db.query(Patient)
        .filter_by(mobile=mobile)
        .all()
    )

    result = []

    for profile in profiles:
        consent = current_consent(db, profile.id)

        result.append({
            "patient_code": profile.patient_code,
            "name": profile.name,
            "consented": bool(
                consent and consent.action == "ACCEPTED"
            ),
            "action": consent.action if consent else None,
            "policy_version": consent.policy_version if consent else None,
            "recorded_at": (
                consent.recorded_at.isoformat()
                if consent else None
            )
        })

    return {"profiles": result}


@app.post("/api/patient/consent")
def record_patient_consent(
    p: dict,
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db)
):
    mobile = patient(authorization)

    patient_code = str(
        p.get("patient_code", "")
    ).strip()

    accepted = p.get("accepted")

    if not patient_code:
        raise HTTPException(
            status_code=400,
            detail="Patient profile is required"
        )

    if not isinstance(accepted, bool):
        raise HTTPException(
            status_code=400,
            detail="Explicit consent decision is required"
        )

    profile = (
        db.query(Patient)
        .filter_by(
            patient_code=patient_code,
            mobile=mobile
        )
        .first()
    )

    if not profile:
        raise HTTPException(
            status_code=404,
            detail="Patient profile not found"
        )

    action = "ACCEPTED" if accepted else "WITHDRAWN"

    record = PatientConsent(
        patient_id=profile.id,
        action=action,
        policy_version=CONSENT_POLICY_VERSION,
        verified_mobile=mobile
    )

    db.add(record)
    db.commit()
    db.refresh(record)

    audit(
        db,
        "patient:" + mobile[-4:],
        "CONSENT_" + action,
        patient_code
    )

    return {
        "patient_code": patient_code,
        "action": record.action,
        "consented": accepted,
        "policy_version": record.policy_version,
        "recorded_at": record.recorded_at.isoformat()
    }

# PATIENT ORDERS
# --------------------------------------------------

@app.get("/api/patient/orders")
def patient_orders(
    patient_code: str,
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db)
):
    mobile = patient(authorization)

    profile = (
        db.query(Patient)
        .filter_by(
            patient_code=patient_code,
            mobile=mobile
        )
        .first()
    )

    if not profile:
        raise HTTPException(
            status_code=403,
            detail="Profile not linked to verified mobile"
        )

    require_patient_consent(db, profile)
    orders = (
        db.query(Order)
        .filter_by(patient_id=profile.id)
        .all()
    )

    return [
        {
            "order_ref": o.order_ref,
            "test_name": o.test_name,
            "status": o.status
        }
        for o in orders
    ]


# --------------------------------------------------
# PATIENT REPORT
# --------------------------------------------------

@app.get("/api/patient/report/{ref}")
def patient_report(
    ref: str,
    patient_code: str,
    language: str = "en",
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db)
):
    mobile = patient(authorization)

    profile = (
        db.query(Patient)
        .filter_by(
            patient_code=patient_code,
            mobile=mobile
        )
        .first()
    )

    order = (
        db.query(Order)
        .filter_by(order_ref=ref)
        .first()
    )

    if (
        not profile
        or not order
        or order.patient_id != profile.id
    ):
        raise HTTPException(
            status_code=404,
            detail="Report not found"
        )

    require_patient_consent(db, profile)
    if order.status != "Ready":
        raise HTTPException(
            status_code=409,
            detail="Report not signed yet"
        )

    values = (
        db.query(ResultValue)
        .filter_by(order_id=order.id)
        .all()
    )

    audit(
        db,
        "patient:" + mobile[-4:],
        "VIEW_REPORT",
        ref
    )

    return {
        "order_ref": ref,
        "test_name": order.test_name,
        "doctor": order.doctor_name,
        "summary": summarize(values, language),
        "values": [
            {
                "analyte": v.analyte,
                "value": v.value,
                "unit": v.unit,
                "range": f"{v.low}–{v.high}",
                "flag": v.flag
            }
            for v in values
        ]
    }


# --------------------------------------------------
# PATIENT SUMMARY FEEDBACK
# --------------------------------------------------

@app.post("/api/patient/feedback/{ref}")
def submit_summary_feedback(
    ref: str,
    p: dict,
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db)
):
    mobile = patient(authorization)

    patient_code = str(p.get("patient_code", "")).strip()
    category = str(p.get("category", "")).strip()
    comment = str(p.get("comment", "")).strip()

    allowed_categories = {
        "Inaccurate information",
        "Unclear explanation",
        "Other"
    }

    if category not in allowed_categories:
        raise HTTPException(
            status_code=400,
            detail="Select a valid feedback category"
        )

    if len(comment) > 1000:
        raise HTTPException(
            status_code=400,
            detail="Comment must be 1000 characters or less"
        )

    profile = (
        db.query(Patient)
        .filter_by(
            patient_code=patient_code,
            mobile=mobile
        )
        .first()
    )

    order = (
        db.query(Order)
        .filter_by(order_ref=ref)
        .first()
    )

    if (
        not profile
        or not order
        or order.patient_id != profile.id
    ):
        raise HTTPException(
            status_code=404,
            detail="Report not found"
        )

    require_patient_consent(db, profile)
    if order.status != "Ready":
        raise HTTPException(
            status_code=409,
            detail="Report is not ready"
        )

    values = (
        db.query(ResultValue)
        .filter_by(order_id=order.id)
        .all()
    )

    summary = summarize(values)

    if summary.get("status") == "SUPPRESSED_CRITICAL":
        raise HTTPException(
            status_code=409,
            detail="Feedback is unavailable for safety-suppressed critical summaries"
        )

    feedback = SummaryFeedback(
        order_id=order.id,
        patient_code=patient_code,
        category=category,
        comment=comment,
        status="OPEN"
    )

    db.add(feedback)
    db.commit()
    db.refresh(feedback)

    audit(
        db,
        "patient:" + mobile[-4:],
        "SUMMARY_FEEDBACK",
        ref
    )

    return {
        "message": "Feedback submitted successfully",
        "feedback_id": feedback.id
    }


# --------------------------------------------------
# PATIENT PDF DOWNLOAD
# --------------------------------------------------

@app.get("/api/patient/pdf/{ref}")
def patient_pdf(
    ref: str,
    patient_code: str,
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db)
):
    mobile = patient(authorization)

    profile = (
        db.query(Patient)
        .filter_by(
            patient_code=patient_code,
            mobile=mobile
        )
        .first()
    )

    order = (
        db.query(Order)
        .filter_by(order_ref=ref)
        .first()
    )

    if (
        not profile
        or not order
        or order.patient_id != profile.id
    ):
        raise HTTPException(
            status_code=404,
            detail="Report not found"
        )

    require_patient_consent(db, profile)
    if order.status != "Ready":
        raise HTTPException(
            status_code=409,
            detail="Report not signed yet"
        )

    if (
        not order.pdf_path
        or not Path(order.pdf_path).is_file()
    ):
        raise HTTPException(
            status_code=404,
            detail="PDF file not found"
        )

    audit(
        db,
        "patient:" + mobile[-4:],
        "DOWNLOAD_REPORT",
        ref
    )

    return FileResponse(
        str(order.pdf_path),
        media_type="application/pdf",
        filename=ref + ".pdf"
    )


# --------------------------------------------------
# CREATE EXPIRING SECURE LINK
# --------------------------------------------------

@app.post("/api/patient/secure-link/{ref}")
def secure_link(
    ref: str,
    p: dict,
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db)
):
    mobile = patient(authorization)

    profile = (
        db.query(Patient)
        .filter_by(
            patient_code=p.get("patient_code"),
            mobile=mobile
        )
        .first()
    )

    order = (
        db.query(Order)
        .filter_by(order_ref=ref)
        .first()
    )

    if (
        not profile
        or not order
        or order.patient_id != profile.id
        or order.status != "Ready"
    ):
        raise HTTPException(
            status_code=404,
            detail="Report not found"
        )

    require_patient_consent(db, profile)
    t = token()

    LINKS[t] = {
        "ref": ref,
        "mobile": mobile,
        "expiry": datetime.utcnow() + timedelta(
            hours=settings.report_link_ttl_hours
        ),
        "verified": False
    }

    audit(
        db,
        "patient:" + mobile[-4:],
        "CREATE_EXPIRING_LINK",
        ref
    )

    return {
        "url": "/secure/" + t,
        "expires_hours": settings.report_link_ttl_hours,
        "otp_required_on_reopen": True
    }


# --------------------------------------------------
# SECURE LINK PAGE
# --------------------------------------------------

@app.get("/secure/{t}", response_class=HTMLResponse)
def secure_page(t: str):

    x = get_secure_link(t)

    x["verified"] = False

    return HTMLResponse("""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">

<title>LABFLOW Secure Report</title>

<style>
* {
    box-sizing: border-box;
}

body {
    font-family: Arial, sans-serif;
    background: #f4f7fb;
    margin: 0;
    padding: 30px 16px;
    color: #172033;
}

.card {
    max-width: 650px;
    margin: 35px auto;
    background: white;
    padding: 28px;
    border-radius: 16px;
    box-shadow: 0 8px 30px #17203312;
}

input, button {
    width: 100%;
    padding: 13px;
    margin-top: 12px;
    border-radius: 8px;
    font-size: 15px;
}

input {
    border: 1px solid #ccd5e2;
}

button {
    border: 0;
    background: #176b55;
    color: white;
    cursor: pointer;
}

button:disabled {
    opacity: .6;
    cursor: wait;
}

#report {
    display: none;
    margin-top: 25px;
    border-top: 1px solid #e4e9f0;
    padding-top: 20px;
}

.result {
    padding: 12px;
    margin: 8px 0;
    background: #f4f7fb;
    border-radius: 8px;
}

#message {
    margin-top: 14px;
    color: #176b55;
    overflow-wrap: anywhere;
}
</style>
</head>

<body>

<div class="card">

    <h2>LABFLOW Secure Report</h2>

    <p>
        Your diagnostic report is protected by OTP verification.
    </p>

    <div id="verification">

        <button id="send" onclick="sendOTP()">
            Send OTP
        </button>

        <input
            id="otp"
            type="text"
            inputmode="numeric"
            maxlength="6"
            placeholder="Enter 6-digit OTP"
        >

        <button id="verify" onclick="verifyOTP()">
            Verify OTP
        </button>

    </div>

    <p id="message"></p>

    <div id="report">

        <h2 id="testName"></h2>

        <p id="orderRef"></p>

        <h3>Report Summary</h3>

        <p id="summary"></p>

        <h3>Test Results</h3>

        <div id="values"></div>

        <button onclick="downloadPDF()">
            Download Full Report PDF
        </button>

    </div>

</div>

<script>

const linkToken = location.pathname.split("/").pop();


async function sendOTP() {

    const button = document.getElementById("send");
    const message = document.getElementById("message");

    button.disabled = true;
    message.textContent = "Sending OTP...";

    try {

        const response = await fetch(
            "/api/secure/" + linkToken + "/request-otp",
            {
                method: "POST"
            }
        );

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || "OTP request failed");
        }

        message.textContent = data.message;

        alert(
            "Demo OTP is printed in your VS Code terminal."
        );

    } catch (error) {

        message.textContent = error.message;

    } finally {

        button.disabled = false;

    }
}


async function verifyOTP() {

    const code = document.getElementById("otp").value.trim();

    const message = document.getElementById("message");

    if (!/^\\d{6}$/.test(code)) {

        message.textContent = "Enter a valid 6-digit OTP.";

        return;
    }

    message.textContent = "Verifying OTP...";

    try {

        const response = await fetch(
            "/api/secure/" + linkToken + "/verify-otp",
            {
                method: "POST",

                headers: {
                    "Content-Type": "application/json"
                },

                body: JSON.stringify({
                    otp: code
                })
            }
        );

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || "Verification failed");
        }

        document.getElementById("verification").style.display = "none";

        document.getElementById("report").style.display = "block";

        document.getElementById("testName").textContent =
            data.test_name;

        document.getElementById("orderRef").textContent =
            "Order: " + data.order_ref;

        document.getElementById("summary").textContent =
            data.summary.text;

        const values = document.getElementById("values");

        values.replaceChildren();

        data.values.forEach(item => {

            const div = document.createElement("div");

            div.className = "result";

            div.textContent =
                item.analyte + ": " +
                item.value + " " +
                item.unit +
                " | Range: " + item.range +
                " | " + item.flag;

            values.appendChild(div);

        });

        message.textContent =
            "OTP verified. Report unlocked.";

    } catch (error) {

        message.textContent = error.message;

    }

}


async function downloadPDF() {

    const message = document.getElementById("message");

    try {

        const response = await fetch(
            "/api/secure/" + linkToken + "/pdf"
        );

        if (!response.ok) {

            const data = await response.json();

            throw new Error(
                data.detail || "PDF download failed"
            );

        }

        const blob = await response.blob();

        const url = URL.createObjectURL(blob);

        const a = document.createElement("a");

        a.href = url;

        a.download = "LABFLOW-Report.pdf";

        document.body.appendChild(a);

        a.click();

        a.remove();

        URL.revokeObjectURL(url);

    } catch (error) {

        message.textContent = error.message;

    }

}

</script>

</body>
</html>
""")


# --------------------------------------------------
# SECURE LINK OTP REQUEST
# --------------------------------------------------

@app.post("/api/secure/{t}/request-otp")
def secure_request_otp(
    t: str,
    db: Session = Depends(get_db)
):
    x = get_secure_link(t)

    x["verified"] = False

    mobile = x["mobile"]

    code = otp()

    db.query(OTPChallenge).filter_by(
        mobile=mobile,
        consumed=False
    ).update(
        {"consumed": True}
    )

    db.add(
        OTPChallenge(
            mobile=mobile,
            code_hash=digest(code),
            expires_at=expires(settings.otp_ttl_minutes)
        )
    )

    db.commit()

    print(
        f"\n[SECURE LINK OTP] Mobile ending {mobile[-4:]} => {code}\n"
    )

    return {
        "message": "OTP generated. Check your VS Code terminal."
    }


# --------------------------------------------------
# SECURE LINK OTP VERIFICATION
# --------------------------------------------------

@app.post("/api/secure/{t}/verify-otp")
def secure_verify_otp(
    t: str,
    p: dict,
    db: Session = Depends(get_db)
):
    x = get_secure_link(t)

    code = str(p.get("otp", "")).strip()

    if not code.isdigit() or len(code) != 6:
        raise HTTPException(
            status_code=400,
            detail="Enter a valid 6-digit OTP"
        )

    mobile = x["mobile"]

    challenge = (
        db.query(OTPChallenge)
        .filter_by(
            mobile=mobile,
            consumed=False
        )
        .order_by(OTPChallenge.id.desc())
        .first()
    )

    if (
        not challenge
        or challenge.expires_at < datetime.utcnow()
        or not secrets.compare_digest(
            challenge.code_hash,
            digest(code)
        )
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired OTP"
        )

    order = (
        db.query(Order)
        .filter_by(order_ref=x["ref"])
        .first()
    )

    if not order or order.status != "Ready":
        raise HTTPException(
            status_code=404,
            detail="Report not found"
        )

    profile = db.query(Patient).filter_by(id=order.patient_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Patient profile not found")
    require_patient_consent(db, profile)

    challenge.consumed = True
    db.commit()

    x["verified"] = True

    values = (
        db.query(ResultValue)
        .filter_by(order_id=order.id)
        .all()
    )

    audit(
        db,
        "secure-link:" + mobile[-4:],
        "VERIFY_SECURE_LINK",
        x["ref"]
    )

    return {
        "order_ref": order.order_ref,
        "test_name": order.test_name,
        "summary": summarize(values),
        "values": [
            {
                "analyte": v.analyte,
                "value": v.value,
                "unit": v.unit,
                "range": f"{v.low}–{v.high}",
                "flag": v.flag
            }
            for v in values
        ]
    }


# --------------------------------------------------
# SECURE LINK PDF DOWNLOAD
# --------------------------------------------------

@app.get("/api/secure/{t}/pdf")
def secure_pdf(
    t: str,
    db: Session = Depends(get_db)
):
    x = get_secure_link(t)

    if not x["verified"]:
        raise HTTPException(
            status_code=403,
            detail="OTP verification required"
        )

    order = (
        db.query(Order)
        .filter_by(order_ref=x["ref"])
        .first()
    )

    if (
        not order
        or order.status != "Ready"
        or not order.pdf_path
        or not Path(order.pdf_path).is_file()
    ):
        raise HTTPException(
            status_code=404,
            detail="PDF not found"
        )

    profile = db.query(Patient).filter_by(id=order.patient_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Patient profile not found")
    require_patient_consent(db, profile)

    audit(
        db,
        "secure-link:" + x["mobile"][-4:],
        "DOWNLOAD_SECURE_REPORT",
        x["ref"]
    )

    return FileResponse(
        order.pdf_path,
        media_type="application/pdf",
        filename=order.order_ref + ".pdf"
    )


# --------------------------------------------------
# STAFF OVERVIEW
# --------------------------------------------------

@app.get("/api/staff/overview")
def overview(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db)
):
    staff(authorization)

    return {
        "orders": db.query(Order).count(),

        "ready": db.query(Order)
        .filter_by(status="Ready")
        .count(),

        "processing": db.query(Order)
        .filter_by(status="Processing")
        .count(),

        "callbacks": db.query(CallbackTask)
        .filter_by(status="OPEN")
        .count()
    }


# --------------------------------------------------
# STAFF SEARCH
# --------------------------------------------------

@app.get("/api/staff/search")
def search(
    q: str,
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db)
):
    staff(authorization)

    rows = (
        db.query(Order)
        .join(Patient)
        .filter(
            or_(
                Order.order_ref.ilike(f"%{q}%"),
                Patient.name.ilike(f"%{q}%"),
                Patient.mobile.ilike(f"%{q}%")
            )
        )
        .all()
    )

    return [
        {
            "order_ref": o.order_ref,
            "patient": o.patient.name,
            "mobile": "******" + o.patient.mobile[-4:],
            "test_name": o.test_name,
            "status": o.status
        }
        for o in rows
    ]


# --------------------------------------------------
# FRONT-DESK RESEND
# --------------------------------------------------

@app.post("/api/staff/resend/{ref}")
def resend(
    ref: str,
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db)
):
    staff(authorization)

    order = (
        db.query(Order)
        .filter_by(order_ref=ref)
        .first()
    )

    if not order:
        raise HTTPException(
            status_code=404,
            detail="Order not found"
        )

    if order.status != "Ready":
        raise HTTPException(
            status_code=409,
            detail="Report not signed"
        )

    secure_url = create_report_notification(
        order,
        db,
        "front-desk"
    )

    audit(db, "front-desk", "RESEND", ref)

    return {
        "status": "SIMULATED",
        "channel": "MOCK_WHATSAPP",
        "url": secure_url,
        "expires_hours": settings.report_link_ttl_hours,
        "otp_required_on_reopen": True
    }


# --------------------------------------------------
# LIS CSV IMPORT
# --------------------------------------------------

@app.post("/api/staff/import-csv")
async def import_csv(
    file: UploadFile = File(...),
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db)
):
    staff(authorization)

    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="CSV only")

    try:
        content = (await file.read()).decode("utf-8-sig")
        rows = csv.DictReader(content.splitlines())

        required = {
            "order_ref", "patient_name", "mobile", "patient_code",
            "test_name", "analyte", "value", "unit", "low", "high"
        }

        if not rows.fieldnames or not required.issubset(set(rows.fieldnames)):
            raise HTTPException(
                status_code=400,
                detail="CSV is missing required columns"
            )

        grouped = {}

        for row in rows:
            ref = (row.get("order_ref") or "").strip()
            if ref:
                grouped.setdefault(ref, []).append(row)

        count = 0

        for ref, order_rows in grouped.items():

            existing = db.query(Order).filter_by(order_ref=ref).first()
            if existing:
                continue

            first = order_rows[0]

            mobile = (first.get("mobile") or "").strip()
            patient_code = (first.get("patient_code") or "").strip()

            if not mobile.isdigit() or len(mobile) < 10:
                raise ValueError(f"Invalid mobile for order {ref}")

            if not patient_code:
                raise ValueError(f"Missing patient code for order {ref}")

            for row in order_rows:
                if (
                    row.get("mobile", "").strip() != mobile
                    or row.get("patient_code", "").strip() != patient_code
                    or row.get("test_name", "").strip() != first["test_name"].strip()
                    or row.get("status", "Processing").strip()
                    != first.get("status", "Processing").strip()
                ):
                    raise ValueError(
                        f"Inconsistent order details across rows for {ref}"
                    )

            profile = (
                db.query(Patient)
                .filter_by(patient_code=patient_code)
                .first()
            )

            if profile:
                if profile.mobile != mobile:
                    raise ValueError(
                        f"Patient mobile mismatch for order {ref}"
                    )
            else:
                profile = Patient(
                    name=first["patient_name"].strip(),
                    mobile=mobile,
                    patient_code=patient_code
                )
                db.add(profile)
                db.flush()

            ready = first.get("status", "").strip() == "Ready"

            order = Order(
                order_ref=ref,
                patient_id=profile.id,
                test_name=first["test_name"].strip(),
                doctor_name=(first.get("doctor_name") or "").strip(),
                status=(first.get("status") or "Processing").strip(),
                pdf_path=(first.get("pdf_path") or "").strip(),
                signed_at=datetime.utcnow() if ready else None
            )

            db.add(order)
            db.flush()

            result_values = []
            seen_analytes = set()

            for row in order_rows:
                analyte = row["analyte"].strip()

                if not analyte:
                    raise ValueError(f"Missing analyte for order {ref}")

                if analyte.lower() in seen_analytes:
                    raise ValueError(
                        f"Duplicate analyte {analyte} in order {ref}"
                    )

                seen_analytes.add(analyte.lower())

                result_value = ResultValue(
                    order_id=order.id,
                    analyte=analyte,
                    value=float(row["value"]),
                    unit=row["unit"].strip(),
                    low=float(row["low"]),
                    high=float(row["high"]),
                    critical=(row.get("critical") or "false").lower() == "true",
                    flag=(row.get("flag") or "NORMAL").strip().upper()
                )

                db.add(result_value)
                result_values.append(result_value)

            if ready:
                summary_result = summarize(result_values)

                if summary_result["status"] == "SUPPRESSED_CRITICAL":
                    db.add(
                        CallbackTask(
                            order_ref=ref,
                            reason="Critical sample result — call patient per lab protocol"
                        )
                    )
                else:
                    db.add(
                        PathologistReview(
                            order_id=order.id,
                            summary_text=summary_result["text"],
                            summary_source=summary_result["source"],
                            status="PENDING"
                        )
                    )

                create_report_notification(order, db, "lis-import")

            count += 1

        db.commit()

    except HTTPException:
        db.rollback()
        raise

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail=f"CSV import failed: {str(e)}"
        )

    audit(db, "front-desk", "CSV_IMPORT")

    return {"imported": count}


# STAFF EVENTS / AUDIT LOGS
# --------------------------------------------------

@app.get("/api/staff/events")
def events(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db)
):
    staff(authorization)

    return {
        "delivery": [
            {
                "ref": x.order_ref,
                "status": x.status,
                "destination": x.destination
            }
            for x in (
                db.query(DeliveryEvent)
                .order_by(DeliveryEvent.id.desc())
                .limit(30)
                .all()
            )
        ],

        "access": [
            {
                "actor": x.actor,
                "action": x.action,
                "ref": x.order_ref
            }
            for x in (
                db.query(AccessEvent)
                .order_by(AccessEvent.id.desc())
                .limit(30)
                .all()
            )
        ],

        "callbacks": [
            {
                "ref": x.order_ref,
                "reason": x.reason
            }
            for x in (
                db.query(CallbackTask)
                .filter_by(status="OPEN")
                .all()
            )
        ],

        "feedback": [
            {
                "ref": db.query(Order.order_ref).filter(Order.id == x.order_id).scalar(),
                "patient_code": x.patient_code,
                "category": x.category,
                "comment": x.comment,
                "status": x.status,
                "created_at": x.created_at.isoformat()
            }
            for x in (
                db.query(SummaryFeedback)
                .join(Order)
                .order_by(SummaryFeedback.id.desc())
                .limit(30)
                .all()
            )
        ]
    }


# --------------------------------------------------
# STAFF PDF ACCESS
# --------------------------------------------------

@app.get("/api/staff/pdf/{ref}")
def staff_pdf(
    ref: str,
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db)
):
    staff(authorization)

    order = (
        db.query(Order)
        .filter_by(order_ref=ref)
        .first()
    )

    if (
        not order
        or not order.pdf_path
        or not Path(order.pdf_path).is_file()
    ):
        raise HTTPException(
            status_code=404,
            detail="PDF not found"
        )

    audit(
        db,
        "front-desk",
        "STAFF_DOWNLOAD_REPORT",
        ref
    )

    return FileResponse(
        order.pdf_path,
        media_type="application/pdf",
        filename=ref + ".pdf"
    )
