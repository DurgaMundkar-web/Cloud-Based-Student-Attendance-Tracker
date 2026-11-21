from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from datetime import date as dt_date
from app.database import get_db
from app.models.user import User
from app.models.attendance import Attendance  # किंवा तुमच्या मॉडेलनुसार इम्पोर्ट तपासा
import traceback

router = APIRouter(prefix="/api", tags=["Attendance"])

class AttendanceRecord(BaseModel):
    name: str
    email: Optional[str] = None
    roll: Optional[int] = None
    status: str

class AttendanceBatchCreate(BaseModel):
    subject_name: str
    date: Optional[str] = None
    marked_by: Optional[str] = None
    attendance_records: List[AttendanceRecord]

@router.post("/save-attendance")
def save_attendance(payload: AttendanceBatchCreate, db: Session = Depends(get_db)):
    try:
        # तारीख सेट करणे
        if payload.date:
            parsed_date = dt_date.fromisoformat(payload.date)
        else:
            parsed_date = dt_date.today()
        
        saved_count = 0
        for record in payload.attendance_records:
            student_id = None
            if record.email:
                student = db.query(User).filter(User.email.ilike(record.email)).first()
                if student:
                    student_id = student.id

            new_record = Attendance(
                student_id=student_id,
                subject_name=payload.subject_name,
                faculty_name=payload.marked_by or "Shital",
                total_classes=1,
                attended_classes=1 if record.status.lower() == "present" else 0,
                status=record.status,
                date=parsed_date
            )
            db.add(new_record)
            saved_count += 1
            
        db.commit()
        return {"message": f"Successfully saved {saved_count} attendance records!"}
    except Exception as e:
        db.rollback()
        print("❌ ERROR:", traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))