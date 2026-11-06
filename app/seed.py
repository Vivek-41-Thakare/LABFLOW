from datetime import datetime
from app.database import Base,engine,SessionLocal
from app.models import Patient,Order,ResultValue,CallbackTask
def seed():
    Base.metadata.create_all(engine); db=SessionLocal()
    try:
        if db.query(Order).count(): return
        people=[Patient(name="Lakshmi Prasanna K",mobile="9000000001",patient_code="PAT-001"),Patient(name="Venkata Rao M",mobile="9000000002",patient_code="PAT-002"),Patient(name="Farzana Begum",mobile="9000000003",patient_code="PAT-003")]
        db.add_all(people); db.flush()
        orders=[Order(order_ref="ORD-71204",patient_id=people[0].id,test_name="Haemoglobin",doctor_name="Dr. S. Ramanaiah",status="Ready",pdf_path="sample_data/reports/ORD-71204.pdf",signed_at=datetime.utcnow()),Order(order_ref="ORD-71219",patient_id=people[1].id,test_name="LDL Cholesterol",doctor_name="Dr. P. Anitha",status="Processing"),Order(order_ref="ORD-71233",patient_id=people[2].id,test_name="Potassium",doctor_name="Dr. K. Suresh",status="Ready",pdf_path="sample_data/reports/ORD-71233.pdf",signed_at=datetime.utcnow())]
        db.add_all(orders); db.flush()
        db.add_all([ResultValue(order_id=orders[0].id,analyte="Haemoglobin",value=10.2,unit="g/dL",low=12,high=15.5,flag="LOW"),ResultValue(order_id=orders[1].id,analyte="LDL cholesterol",value=142,unit="mg/dL",low=0,high=100,flag="HIGH"),ResultValue(order_id=orders[2].id,analyte="Potassium",value=6.8,unit="mmol/L",low=3.5,high=5.1,critical=True,flag="CRITICAL")])
        db.add(CallbackTask(order_ref="ORD-71233",reason="Critical sample result — call patient per lab protocol")); db.commit()
    finally: db.close()
