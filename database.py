import sqlite3
from pathlib import Path

"""Database (DB) initialization with sqlite3 (raw SQL)."""
# Creating (if it does not exist) and connecting to the DB
DB_PATH = Path(__file__).resolve().parent / "db.sqlite3"
db = sqlite3.connect(DB_PATH)
cursor = db.cursor()

cursor.execute("""
    CREATE TABLE IF NOT EXISTS students(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        age INTEGER NOT NULL,
        birthday TEXT NOT NULL,
        course TEXT NOT NULL
    )
""")


# --- C: Create (inserting students) ---
def add_student(name: str, age: int, birthday: str, course: str):
    cursor.execute(
        "INSERT INTO students (name,age,birthday,course) VALUES (?, ?, ?, ?)",
        (name, age, birthday, course),
    )
    db.commit()
    return cursor.lastrowid


# --- R: Read (fetch every student) ---
def get_students():
    cursor.execute("SELECT * FROM students")
    students = cursor.fetchall()
    return students


# --- R: Read (fetch a single student) ---
def get_student(student_id):
    cursor.execute("SELECT * FROM students WHERE id = ?", (student_id,))
    student = cursor.fetchone()
    return student


# --- U: Update (modify a student) ---
def edit_student(student_id: int, **fields):
    if not fields:
        raise ValueError("You must provide at least one field to update")
    allowed_fields = {"name", "age", "birthday", "course"}
    if invalid_fields := set(fields.keys()) - allowed_fields:
        raise ValueError(f"Invalid fields for this update: {invalid_fields}")
    clauses = ", ".join(f"{key} = ?" for key in fields)
    cursor.execute(
        f"UPDATE students SET {clauses} WHERE id = ?",
        (*fields.values(), student_id),
    )
    db.commit()


# --- D: Delete (remove a student) ---
def delete_student(student_id):
    cursor.execute("DELETE FROM students WHERE id = ?", (student_id,))
    db.commit()
