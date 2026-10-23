from pathlib import Path
import sqlite3

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.database import get_connection, initialize_database
from app.models import StudentCreate, StudentUpdate


BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

app = FastAPI(
    title="Students Database CRUD Application",
    description="Manage student records using FastAPI and SQLite.",
    version="1.0.0"
)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

initialize_database()


@app.get("/")
def home():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/stats")
def get_stats():
    with get_connection() as connection:
        total = connection.execute(
            "SELECT COUNT(*) FROM students"
        ).fetchone()[0]

        courses = connection.execute("""
            SELECT COUNT(DISTINCT course)
            FROM students
            WHERE course IS NOT NULL AND TRIM(course) != ''
        """).fetchone()[0]

        recent = connection.execute("""
            SELECT COUNT(*) FROM students
            WHERE created_at >= datetime('now', '-7 days')
        """).fetchone()[0]

    return {
        "total_students": total,
        "total_courses": courses,
        "recently_added": recent
    }


@app.get("/students")
def list_students(
    search: str = Query(default="", max_length=100),
    course: str = Query(default="", max_length=100)
):
    sql = "SELECT * FROM students WHERE 1=1"
    params = []

    if search.strip():
        pattern = f"%{search.strip()}%"
        sql += """
            AND (
                student_id LIKE ? OR
                name LIKE ? OR
                email LIKE ? OR
                phone LIKE ?
            )
        """
        params.extend([pattern, pattern, pattern, pattern])

    if course.strip():
        sql += " AND course = ?"
        params.append(course.strip())

    sql += " ORDER BY name COLLATE NOCASE"

    with get_connection() as connection:
        rows = connection.execute(sql, params).fetchall()

    return [dict(row) for row in rows]


@app.get("/students/{student_id}")
def get_student(student_id: str):
    with get_connection() as connection:
        row = connection.execute(
            "SELECT * FROM students WHERE student_id = ?",
            (student_id,)
        ).fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail="Student not found.")

    return dict(row)


@app.post("/students", status_code=201)
def create_student(student: StudentCreate):
    data = student.model_dump(mode="json")

    data["student_id"] = data["student_id"].strip()
    data["name"] = data["name"].strip()

    if not data["student_id"] or not data["name"]:
        raise HTTPException(
            status_code=422,
            detail="Student ID and name cannot be blank."
        )

    if data["email"]:
        data["email"] = str(data["email"]).strip().lower()

    if data["phone"]:
        data["phone"] = data["phone"].strip()

    if not data["email"] and not data["phone"]:
        raise HTTPException(
            status_code=422,
            detail="Provide an email address or phone number."
        )

    try:
        with get_connection() as connection:
            connection.execute("""
                INSERT INTO students (
                    student_id, name, date_of_birth, email,
                    phone, course, address, enrollment_date
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                data["student_id"],
                data["name"],
                data["date_of_birth"],
                data["email"],
                data["phone"],
                data["course"],
                data["address"],
                data["enrollment_date"]
            ))
            connection.commit()

    except sqlite3.IntegrityError:
        raise HTTPException(
            status_code=409,
            detail="That student ID already exists."
        )

    return get_student(data["student_id"])


@app.patch("/students/{student_id}")
def update_student(student_id: str, changes: StudentUpdate):
    updates = changes.model_dump(exclude_unset=True, mode="json")

    with get_connection() as connection:
        existing = connection.execute(
            "SELECT * FROM students WHERE student_id = ?",
            (student_id,)
        ).fetchone()

        if existing is None:
            raise HTTPException(
                status_code=404,
                detail="Student not found."
            )

        current = dict(existing)

        for key, value in updates.items():
            if key in ("name", "phone", "course", "address") and value is not None:
                value = value.strip()
            if key == "email" and value:
                value = str(value).strip().lower()
            current[key] = value

        if not current["name"] or not current["name"].strip():
            raise HTTPException(
                status_code=422,
                detail="Student name cannot be blank."
            )

        if not current["date_of_birth"]:
            raise HTTPException(
                status_code=422,
                detail="Date of birth is required."
            )

        if not current["email"] and not current["phone"]:
            raise HTTPException(
                status_code=422,
                detail="Provide an email address or phone number."
            )

        allowed_fields = {
            "name", "date_of_birth", "email", "phone",
            "course", "address", "enrollment_date"
        }
        updates = {
            key: value for key, value in updates.items()
            if key in allowed_fields
        }

        for key in updates:
            updates[key] = current[key]

        if updates:
            assignments = ", ".join(
                f"{key} = ?" for key in updates
            )
            values = list(updates.values()) + [student_id]

            connection.execute(
                f"UPDATE students SET {assignments} WHERE student_id = ?",
                values
            )
            connection.commit()

    return get_student(student_id)


@app.delete("/students/{student_id}")
def delete_student(student_id: str):
    with get_connection() as connection:
        cursor = connection.execute(
            "DELETE FROM students WHERE student_id = ?",
            (student_id,)
        )
        connection.commit()

    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="Student not found.")

    return {"message": "Student deleted successfully."}
