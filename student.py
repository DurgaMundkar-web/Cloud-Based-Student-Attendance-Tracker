from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Attendance, User

router = APIRouter(prefix="/student", tags=["Student"])

@router.get("/attendance")
def get_student_attendance(email: str = Query(None), roll: str = Query(None), db: Session = Depends(get_db)):
    student = None
    
    # 1. Email kiva Roll nusar student shofta
    if email:
        student = db.query(User).filter(User.email.ilike(email.strip())).first()
    if not student and roll:
        # Jar roll nsar shoftay asal tar user table madhe roll column asel tarva
        student = db.query(User).filter(User.id == int(roll) if roll.isdigit() else 0).first()

    if not student:
        # Fallback: Jar direct user sapdla nahi, tar attendance madhye bagha
        pass

    # 2. Student ID nusar attendance records fetch kara
    query = db.query(Attendance)
    if student:
        query = query.filter(Attendance.student_id == student.id)
    elif email:
        # Direct email match hot nsel tar attendance records join karun bagha
        pass

    # Better approach: Direct email/roll sathi attendance table madhun records kadhne
    records = []
    if student:
        records = db.query(Attendance).filter(Attendance.student_id == student.id).all()
    elif email:
        # Email dwara user shoftun tyacha id vaprun records kadhne
        user_obj = db.query(User).filter(User.email.ilike(email)).first()
        if user_obj:
            records = db.query(Attendance).filter(Attendance.student_id == user_obj.id).all()

    formatted_records = [
        {
            "date": str(r.date),
            "subject": r.subject_name,
            "topic": "-",
            "status": r.status
        }
        for r in records
    ]

    return formatted_records