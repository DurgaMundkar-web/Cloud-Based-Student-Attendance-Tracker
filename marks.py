from typing import Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.database import get_db

router = APIRouter(prefix="/api", tags=["Marks"])


class MarkCreate(BaseModel):
    student_email: str
    subject_name: str
    subject_code: Optional[str] = ""
    out_of_marks: int = 100
    obtained_marks: int = 0
    faculty_email: Optional[str] = ""


@router.post("/marks")
def save_marks(payload: MarkCreate, db: Session = Depends(get_db)):
    user_row = db.execute(
        text(
            "SELECT id FROM public.users WHERE LOWER(TRIM(email)) = LOWER(TRIM(:email)) LIMIT 1"
        ),
        {"email": payload.student_email},
    ).fetchone()

    student_id = user_row[0] if user_row else None

    db.execute(
        text("""
            INSERT INTO public.marks
                (student_id, student_email, subject_name, subject_code, out_of_marks, obtained_marks, faculty_email)
            VALUES
                (:student_id, LOWER(TRIM(:student_email)), TRIM(:subject_name), :subject_code, :out_of_marks, :obtained_marks, :faculty_email)
        """),
        {
            "student_id": student_id,
            "student_email": payload.student_email,
            "subject_name": payload.subject_name,
            "subject_code": payload.subject_code,
            "out_of_marks": payload.out_of_marks,
            "obtained_marks": payload.obtained_marks,
            "faculty_email": payload.faculty_email,
        },
    )
    db.commit()
    return {"message": "Marks saved successfully"}


@router.get("/get-marks")
def get_marks(email: str, db: Session = Depends(get_db)):
    rows = db.execute(
        text("""
            SELECT id, student_id, student_email, subject_name, subject_code, out_of_marks, obtained_marks, faculty_email
            FROM public.marks
            WHERE LOWER(TRIM(student_email)) = LOWER(TRIM(:email))
            ORDER BY id DESC
        """),
        {"email": email},
    ).fetchall()

    return [
        {
            "id": r[0],
            "student_id": r[1],
            "student_email": r[2],
            "subject_name": r[3],
            "subject": r[3],
            "subject_code": r[4],
            "code": r[4],
            "out_of_marks": r[5],
            "outOf": r[5],
            "obtained_marks": r[6],
            "obtained": r[6],
            "marks": r[6],
            "faculty_email": r[7],
        }
        for r in rows
    ]