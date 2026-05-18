from app.db.db import SessionLocal
from app.db.models import DecisionLog


def log_decision(session_id: str, step: str, input_text: str, output_text: str, extra_data=None):
    db = SessionLocal()
    try:
        row = DecisionLog(
            session_id=session_id,
            step=step,
            input=input_text,
            output=output_text,
            extra_data=extra_data or {},
        )
        db.add(row)
        db.commit()
    finally:
        db.close()