import sqlite3
from pathlib import Path

"""Inicializacion de la Base de datos (DB) con sqlite3 (SQL crudo)"""
# Creando (Si no existe) y conectandose a la DB
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


# --- C: Create (Inserting students) ---
def add_student(name: str, age: int, birthday: str, course: str):
    cursor.execute(
        "INSERT INTO students (name,age,birthday,course) VALUES (?, ?, ?, ?)",
        (name, age, birthday, course),
    )
    db.commit()
    return cursor.lastrowid


# --- R: Read (Fetch the students) ---
def get_students():
    cursor.execute("SELECT * FROM students")
    students = cursor.fetchall()
    return students


# --- R: Read (Fetch a student) ---
def get_student(student_id):
    cursor.execute("SELECT * FROM students WHERE id = ?", (student_id,))
    student = cursor.fetchone()
    return student


# --- U: Update (Modify student) ---
def edit_student(student_id: int, **fields):
    if not fields:
        raise ValueError("You must provide at least one field for update")
    allowed_fields = {"name", "age", "birthday", "course"}
    if invalid_fields := set(fields.keys()) - allowed_fields:
        raise ValueError(f"Fields no valid for this update: {invalid_fields}")
    clauses = ", ".join(f"{key} = ?" for key in fields)
    cursor.execute(
        f"UPDATE students SET {clauses} WHERE id = ?",
        (*fields.values(), student_id),
    )
    db.commit()


# --- D: Delete (Remove student) ---
def delete_student(student_id):
    cursor.execute("DELETE FROM students WHERE id = ?", (student_id,))
    db.commit()
