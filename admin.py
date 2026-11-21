from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.database import get_db

router = APIRouter(prefix="/admin", tags=["Admin"])


def _split_csv(val: Optional[str]) -> list[str]:
    if not val:
        return []
    return [item.strip() for item in str(val).split(",") if item.strip()]


class UserCreateOrAssign(BaseModel):
    full_name: Optional[str] = ""
    name: Optional[str] = ""
    email: str
    password: Optional[str] = "mgmcen"
    role: Optional[str] = "faculty"
    department: Optional[str] = ""
    branch: Optional[str] = ""
    assign_class: Optional[str] = ""
    student_class: Optional[str] = ""
    class_name: Optional[str] = ""
    subject_name: Optional[str] = ""
    subject: Optional[str] = ""
    lecture_time: Optional[str] = ""
    lecture_days: Optional[str] = ""
    hall: Optional[str] = ""


class TimetableSlotCreate(BaseModel):
    faculty_email: str
    day_of_week: str
    lecture_time: str
    assign_class: str
    department: Optional[str] = ""
    subject_name: str
    hall: Optional[str] = ""


@router.get("/users")
def get_all_users(db: Session = Depends(get_db)):
    rows = db.execute(
        text("""
            SELECT
                id,
                full_name,
                email,
                role,
                department,
                assign_class,
                subject_name
            FROM public.users
            ORDER BY id ASC
        """)
    ).fetchall()

    return [
        {
            "id": r[0],
            "full_name": r[1] or "",
            "name": r[1] or "",
            "email": r[2] or "",
            "role": r[3] or "",
            "department": r[4] or "",
            "branch": r[4] or "",
            "assign_class": r[5] or "",
            "student_class": r[5] or "",
            "class_name": r[5] or "",
            "subject_name": r[6] or "",
            "subject": r[6] or "",
        }
        for r in rows
    ]


@router.post("/users")
def create_or_assign_user(payload: UserCreateOrAssign, db: Session = Depends(get_db)):
    email_clean = (payload.email or "").strip().lower()
    if not email_clean:
        raise HTTPException(status_code=400, detail="Email is required.")

    full_name_val = (payload.full_name or payload.name or "").strip()
    role_val = (payload.role or "faculty").strip().lower()
    dept_val = (payload.department or payload.branch or "").strip()
    class_val = (payload.assign_class or payload.student_class or payload.class_name or "").strip()
    subject_val = (payload.subject_name or payload.subject or "").strip()
    password_val = (payload.password or "mgmcen").strip()

    # Faculty साठी same class आणि same subject आधीपासून assign आहे का ते तपासा
    if role_val == "faculty" and class_val and subject_val:
        target_cls_norm = class_val.lower()
        target_sub_norm = subject_val.lower()

        all_faculties = db.execute(
            text("""
                SELECT id, full_name, email, assign_class, subject_name
                FROM public.users
                WHERE LOWER(TRIM(role)) = 'faculty'
            """)
        ).fetchall()

        tt_rows = []
        try:
            tt_rows = db.execute(
                text("""
                    SELECT faculty_email, assign_class, subject_name
                    FROM public.faculty_timetable
                """)
            ).fetchall()
        except Exception:
            tt_rows = []

        for fac in all_faculties:
            _, fac_name, fac_email, fac_cls_raw, fac_sub_raw = fac
            fac_email_norm = (fac_email or "").strip().lower()
            fac_display_name = (fac_name or fac_email or "another faculty").strip()

            fac_slots = [
                (
                    (r[1] or "").strip().lower(),
                    (r[2] or "").strip().lower(),
                )
                for r in tt_rows
                if (r[0] or "").strip().lower() == fac_email_norm
            ]

            if fac_slots:
                has_exact_pair = any(
                    c == target_cls_norm and s == target_sub_norm for c, s in fac_slots
                )
                if has_exact_pair:
                    raise HTTPException(
                        status_code=400,
                        detail=f"The subject '{subject_val}' for class '{class_val}' is already assigned to '{fac_display_name}'.",
                    )
            else:
                fac_classes = [c.lower() for c in _split_csv(fac_cls_raw)]
                fac_subjects = [s.lower() for s in _split_csv(fac_sub_raw)]

                if target_cls_norm in fac_classes and target_sub_norm in fac_subjects:
                    raise HTTPException(
                        status_code=400,
                        detail=f"The subject '{subject_val}' for class '{class_val}' is already assigned to '{fac_display_name}'.",
                    )

    existing = db.execute(
        text("""
            SELECT id, role, COALESCE(subject_name, ''), COALESCE(assign_class, '')
            FROM public.users
            WHERE LOWER(TRIM(email)) = :email
            LIMIT 1
        """),
        {"email": email_clean},
    ).fetchone()

    if existing:
        existing_id = existing[0]
        existing_role = (existing[1] or "").strip().lower()
        old_subjects = _split_csv(existing[2])
        old_classes = _split_csv(existing[3])

        if existing_role == "student" and role_val == "student":
            raise HTTPException(
                status_code=400,
                detail="This student email is already registered.",
            )

        if subject_val and subject_val.lower() not in [s.lower() for s in old_subjects]:
            old_subjects.append(subject_val)

        if class_val and class_val.lower() not in [c.lower() for c in old_classes]:
            old_classes.append(class_val)

        merged_subjects = ", ".join(old_subjects) if old_subjects else existing[2]
        merged_classes = ", ".join(old_classes) if old_classes else existing[3]

        db.execute(
            text("""
                UPDATE public.users
                SET
                    full_name = CASE WHEN :full_name <> '' THEN :full_name ELSE full_name END,
                    role = CASE WHEN :role <> '' THEN :role ELSE role END,
                    department = CASE WHEN :department <> '' THEN :department ELSE department END,
                    assign_class = :assign_class,
                    subject_name = :subject_name
                WHERE id = :user_id
            """),
            {
                "user_id": existing_id,
                "full_name": full_name_val,
                "role": role_val,
                "department": dept_val,
                "assign_class": merged_classes,
                "subject_name": merged_subjects,
            },
        )
        db.commit()

        return {
            "id": existing_id,
            "email": email_clean,
            "role": role_val or existing_role,
            "assign_class": merged_classes,
            "subject_name": merged_subjects,
            "department": dept_val,
            "message": "Faculty updated and assigned to new class/subject successfully.",
        }

    inserted = db.execute(
        text("""
            INSERT INTO public.users
                (full_name, email, password, role, department, assign_class, subject_name)
            VALUES
                (:full_name, :email, :password, :role, :department, :assign_class, :subject_name)
            RETURNING id
        """),
        {
            "full_name": full_name_val,
            "email": email_clean,
            "password": password_val,
            "role": role_val,
            "department": dept_val,
            "assign_class": class_val,
            "subject_name": subject_val,
        },
    ).fetchone()
    db.commit()

    return {
        "id": inserted[0] if inserted else None,
        "email": email_clean,
        "role": role_val,
        "assign_class": class_val,
        "subject_name": subject_val,
        "department": dept_val,
        "message": "User created successfully.",
    }


@router.get("/timetable/{faculty_email}")
def get_faculty_timetable(faculty_email: str, db: Session = Depends(get_db)):
    rows = db.execute(
        text("""
            SELECT id, faculty_email, day_of_week, lecture_time, assign_class, department, subject_name, hall
            FROM public.faculty_timetable
            WHERE LOWER(TRIM(faculty_email)) = LOWER(TRIM(:email))
            ORDER BY id ASC
        """),
        {"email": faculty_email},
    ).fetchall()

    return [
        {
            "id": r[0],
            "faculty_email": r[1] or "",
            "day_of_week": r[2] or "",
            "day": r[2] or "",
            "lecture_time": r[3] or "",
            "time": r[3] or "",
            "assign_class": r[4] or "",
            "class_name": r[4] or "",
            "department": r[5] or "",
            "subject_name": r[6] or "",
            "subject": r[6] or "",
            "hall": r[7] or "",
        }
        for r in rows
    ]


@router.post("/timetable")
def add_timetable_slot(payload: TimetableSlotCreate, db: Session = Depends(get_db)):
    inserted = db.execute(
        text("""
            INSERT INTO public.faculty_timetable
                (faculty_email, day_of_week, lecture_time, assign_class, department, subject_name, hall)
            VALUES
                (LOWER(TRIM(:faculty_email)), TRIM(:day_of_week), TRIM(:lecture_time), TRIM(:assign_class), TRIM(:department), TRIM(:subject_name), TRIM(:hall))
            RETURNING id
        """),
        {
            "faculty_email": payload.faculty_email,
            "day_of_week": payload.day_of_week,
            "lecture_time": payload.lecture_time,
            "assign_class": payload.assign_class,
            "department": payload.department or "",
            "subject_name": payload.subject_name,
            "hall": payload.hall or "",
        },
    ).fetchone()
    db.commit()

    return {
        "id": inserted[0] if inserted else None,
        "message": "Timetable slot saved successfully.",
    }


@router.delete("/users/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db)):
    result = db.execute(
        text("DELETE FROM public.users WHERE id = :user_id"),
        {"user_id": user_id},
    )
    db.commit()

    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="User not found.")

    return {"message": "User deleted successfully."}