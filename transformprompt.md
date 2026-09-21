# Study Tracker — Transform + MySQL Migration Agent Prompt

You are refactoring an existing Python project called **Study Tracker + Weak Topic Analyzer**.
The project currently uses SQLite and has some complexity that needs to be simplified.
Your job is to apply two transformations simultaneously:

1. **Simplify the code** (mild simplification — remove dataclasses, drop type hints, keep structure)
2. **Migrate from SQLite to MySQL** using `mysql-connector-python`

---

## Project files to transform

Work on these files in this order:
`db.py` → `sessions.py` → `student.py` → `analyzer.py` → `reports.py` → `main.py`

Remove `home.py` entirely — it's redundant.

---

## RULE 1 — MySQL Migration (apply to all files)

Replace all SQLite logic with MySQL connector logic.

### Connection setup (rewrite `db.py` entirely)

```python
import mysql.connector

DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "your_password",
    "database": "study_tracker"
}

def get_connection():
    return mysql.connector.connect(**DB_CONFIG)
```

### Syntax changes required across all files

| SQLite | MySQL replacement |
|---|---|
| `sqlite3.connect(...)` | `mysql.connector.connect(**DB_CONFIG)` |
| `connection.row_factory = sqlite3.Row` | Use `cursor = connection.cursor(dictionary=True)` |
| `AUTOINCREMENT` | `AUTO_INCREMENT` |
| `cursor.lastrowid` | stays the same |
| `connection.execute(sql, params)` | `cursor = connection.cursor(dictionary=True)` then `cursor.execute(sql, params)` |
| `with get_connection() as connection` | Remove `with` — mysql connector context manager doesn't auto-commit. Use `con = get_connection()` and `con.close()` manually |
| `?` placeholders | `%s` placeholders |
| `date(sessions.date)` in ORDER BY | `sessions.date` (MySQL handles DATE natively) |
| `connection.executescript(...)` | Split into individual `cursor.execute()` calls, one statement at a time |

### Database initialization

`initialize_database()` must be rewritten to:
- First create the database if it doesn't exist (connect without specifying database, then CREATE DATABASE IF NOT EXISTS)
- Then reconnect with the database specified
- Run each CREATE TABLE statement separately, not as a script

---

## RULE 2 — Simplification (apply to all files)

### Remove completely
- All `from __future__ import annotations`
- All type hints (`: int`, `-> str`, `Optional[...]`, `list[dict[str, Any]]` etc.)
- All `@dataclass` decorators and `dataclasses` imports
- `from typing import ...` imports
- The `Session` class in `sessions.py` — replace with plain `log_session()` function
- The `Student` class in `student.py` — replace with a plain dict or just variables
- `home.py` — delete this file

### Keep
- All function names exactly as they are (other modules depend on them)
- The `detect_time_slot()` function logic
- All SQL queries — do not change the logic, only the syntax (? → %s, sqlite quirks → mysql)
- The `rich` + `tabulate` fallback pattern in `reports.py`
- `requirements.txt` — replace `rich matplotlib tabulate` with `rich matplotlib tabulate mysql-connector-python`

### Simplify function signatures
Remove type annotations but keep all parameters:
```python
# before
def log_session(student_id: int, topic_id: int, duration_mins: int, ...) -> int:

# after
def log_session(student_id, topic_id, duration_mins, ...):
```

---

## RULE 3 — Student handling after removing the class

`student.py` currently uses a `Student` dataclass. Replace it with a plain dict pattern:

```python
def load_or_onboard_student():
    # fetch from DB, return as plain dict
    # {"id": 1, "name": "Karthik", "grade": "12", "board": "CBSE"}
    ...

def save_student(name, grade, board):
    # insert into DB, return the new id
    ...
```

In `main.py`, replace all `student.id`, `student.name` with `student["id"]`, `student["name"]`.

---

## RULE 4 — Cursor handling pattern (important for MySQL)

Every DB operation must follow this exact pattern:

```python
def some_db_function():
    con = get_connection()
    cursor = con.cursor(dictionary=True)
    cursor.execute("SELECT * FROM table WHERE id = %s", (value,))
    rows = cursor.fetchall()
    cursor.close()
    con.close()
    return rows
```

For INSERT/UPDATE/DELETE:
```python
def insert_something():
    con = get_connection()
    cursor = con.cursor()
    cursor.execute("INSERT INTO table (col) VALUES (%s)", (value,))
    con.commit()
    last_id = cursor.lastrowid
    cursor.close()
    con.close()
    return last_id
```

Never use `with get_connection()` — MySQL connector's context manager does not behave the same as SQLite.

---

## RULE 5 — What NOT to change

- Do not touch the analyzer logic in `analyzer.py` — the stickiness score formula, drain pattern, peak time analysis all stay exactly as written. Only fix the DB calls inside it.
- Do not change the menu structure in `main.py`
- Do not change report formatting logic in `reports.py`
- Do not add new features

---

## RULE 6 — Database setup script

Create a new file called `setup_db.py` that:
- Connects to MySQL as root (no database selected)
- Runs `CREATE DATABASE IF NOT EXISTS study_tracker`
- Reconnects with the database
- Creates all 5 tables: `students`, `subjects`, `topics`, `sessions`, `assessments`
- Prints "Database ready." on success

This file is run once before `main.py`. It should be standalone.

---

## RULE 7 — Final file structure expected

```
study_tracker/
├── setup_db.py       ← NEW: run once to create DB and tables
├── db.py             ← rewritten for MySQL
├── student.py        ← class removed, plain functions
├── sessions.py       ← Session class removed, plain functions  
├── analyzer.py       ← only DB calls updated, logic untouched
├── reports.py        ← only DB calls updated
├── main.py           ← student dict access updated
└── requirements.txt  ← add mysql-connector-python
```

---

## Verification checklist

After making all changes, verify:
- [ ] No `import sqlite3` anywhere
- [ ] No `@dataclass` anywhere
- [ ] No type hints anywhere
- [ ] All `?` placeholders replaced with `%s`
- [ ] All `with get_connection()` replaced with explicit open/close
- [ ] `home.py` deleted
- [ ] `setup_db.py` exists and creates DB cleanly
- [ ] `requirements.txt` includes `mysql-connector-python`
- [ ] `main.py` accesses student as dict not object