from datetime import datetime
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship, Mapped, mapped_column
from app.database import Base


class Patient(Base):
    __tablename__ = "patients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(160))
    mobile: Mapped[str] = mapped_column(String(20), index=True)
    patient_code: Mapped[str] = mapped_column(String(40), unique=True)


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_ref: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"))
    test_name: Mapped[str] = mapped_column(String(160))
    doctor_name: Mapped[str] = mapped_column(String(160), default="")
    status: Mapped[str] = mapped_column(String(30), default="Processing")
    pdf_path: Mapped[str] = mapped_column(String(300), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    signed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    patient = relationship("Patient")


class ResultValue(Base):
    __tablename__ = "result_values"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"))
    analyte: Mapped[str] = mapped_column(String(100))
    value: Mapped[float] = mapped_column(Float)
    unit: Mapped[str] = mapped_column(String(40))
    low: Mapped[float] = mapped_column(Float)
    high: Mapped[float] = mapped_column(Float)
    critical: Mapped[bool] = mapped_column(Boolean, default=False)
    flag: Mapped[str] = mapped_column(String(20), default="NORMAL")


class OTPChallenge(Base):
    __tablename__ = "otp_challenges"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    mobile: Mapped[str] = mapped_column(String(20), index=True)
    code_hash: Mapped[str] = mapped_column(String(128))
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    consumed: Mapped[bool] = mapped_column(Boolean, default=False)


class AccessEvent(Base):
    __tablename__ = "access_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    actor: Mapped[str] = mapped_column(String(100))
    action: Mapped[str] = mapped_column(String(100))
    order_ref: Mapped[str] = mapped_column(String(40), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class DeliveryEvent(Base):
    __tablename__ = "delivery_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_ref: Mapped[str] = mapped_column(String(40))
    channel: Mapped[str] = mapped_column(String(20), default="MOCK")
    status: Mapped[str] = mapped_column(String(30), default="QUEUED")
    destination: Mapped[str] = mapped_column(String(30), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class CallbackTask(Base):
    __tablename__ = "callback_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_ref: Mapped[str] = mapped_column(String(40))
    reason: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(30), default="OPEN")


class SummaryFeedback(Base):
    __tablename__ = "summary_feedback"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id")
    )

    patient_code: Mapped[str] = mapped_column(String(40))

    category: Mapped[str] = mapped_column(String(100))

    comment: Mapped[str] = mapped_column(Text, default="")

    status: Mapped[str] = mapped_column(String(30), default="OPEN")

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow
    )


class NotificationMessage(Base):
    __tablename__ = "notification_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_ref: Mapped[str] = mapped_column(String(40), index=True)
    channel: Mapped[str] = mapped_column(String(30), default="MOCK_WHATSAPP")
    destination: Mapped[str] = mapped_column(String(30), default="")
    message: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default="QUEUED")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class PathologistReview(Base):
    __tablename__ = "pathologist_reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id"),
        unique=True,
        index=True
    )

    summary_text: Mapped[str] = mapped_column(Text)

    summary_source: Mapped[str] = mapped_column(
        String(40),
        default="LOCKED_TEMPLATE"
    )

    status: Mapped[str] = mapped_column(
        String(30),
        default="PENDING"
    )

    reviewer: Mapped[str] = mapped_column(
        String(160),
        default=""
    )

    decision_note: Mapped[str] = mapped_column(
        Text,
        default=""
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow
    )

    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True
    )


class PatientConsent(Base):
    __tablename__ = "patient_consents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    patient_id: Mapped[int] = mapped_column(
        ForeignKey("patients.id"),
        index=True
    )

    action: Mapped[str] = mapped_column(String(20))

    policy_version: Mapped[str] = mapped_column(
        String(30),
        default="LABFLOW-DPDP-1.0"
    )

    recorded_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow
    )

    verified_mobile: Mapped[str] = mapped_column(
        String(20)
    )
