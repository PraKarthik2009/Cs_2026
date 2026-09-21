import hashlib

import mysql.connector

DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "student",
    "database": "study_tracker",
}


def get_connection():
    return mysql.connector.connect(**DB_CONFIG)


def initialize_database():
    admin_db = mysql.connector.connect(host="localhost", user="root", password="student")
    admin_cur = admin_db.cursor()
    admin_cur.execute("CREATE DATABASE IF NOT EXISTS study_tracker")
    admin_cur.close()
    admin_db.close()

    con = get_connection()
    cursor = con.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS students (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            grade VARCHAR(50) NOT NULL,
            board VARCHAR(50) NOT NULL,
            username VARCHAR(50) NOT NULL UNIQUE,
            password_hash VARCHAR(64) NOT NULL
        )
        """
    )
    _ensure_student_auth_schema(cursor)
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS subjects (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(100) NOT NULL
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS topics (
            id INT AUTO_INCREMENT PRIMARY KEY,
            subject_id INT NOT NULL,
            name VARCHAR(100) NOT NULL,
            FOREIGN KEY (subject_id) REFERENCES subjects (id) ON DELETE CASCADE
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS sessions (
            id INT AUTO_INCREMENT PRIMARY KEY,
            student_id INT NOT NULL,
            topic_id INT NOT NULL,
            date VARCHAR(20) NOT NULL,
            time_slot VARCHAR(20) NOT NULL,
            duration_mins INT NOT NULL,
            confidence_before FLOAT NOT NULL,
            confidence_after FLOAT NOT NULL,
            energy_level INT,
            notes TEXT,
            FOREIGN KEY (student_id) REFERENCES students (id) ON DELETE CASCADE,
            FOREIGN KEY (topic_id) REFERENCES topics (id) ON DELETE CASCADE
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS assessments (
            id INT AUTO_INCREMENT PRIMARY KEY,
            student_id INT NOT NULL,
            topic_id INT NOT NULL,
            score FLOAT NOT NULL,
            max_score FLOAT NOT NULL,
            date VARCHAR(20) NOT NULL,
            FOREIGN KEY (student_id) REFERENCES students (id) ON DELETE CASCADE,
            FOREIGN KEY (topic_id) REFERENCES topics (id) ON DELETE CASCADE
        )
        """
    )
    con.commit()
    cursor.close()
    con.close()


def _ensure_student_auth_schema(cursor):
    cursor.execute("SHOW COLUMNS FROM students LIKE 'username'")
    has_username = cursor.fetchone() is not None
    cursor.execute("SHOW COLUMNS FROM students LIKE 'password_hash'")
    has_password_hash = cursor.fetchone() is not None

    if not has_username:
        cursor.execute("ALTER TABLE students ADD COLUMN username VARCHAR(50) NULL")
    if not has_password_hash:
        cursor.execute("ALTER TABLE students ADD COLUMN password_hash VARCHAR(64) NULL")

    cursor.execute("SELECT id FROM students WHERE username IS NULL OR username = ''")
    for row in cursor.fetchall():
        student_id = row[0]
        # Give old rows a login so the auth columns can become required.
        new_username = f"user_{student_id}"
        new_password_hash = hashlib.sha256(f"legacy:{student_id}".encode()).hexdigest()
        cursor.execute(
            "UPDATE students SET username = %s, password_hash = COALESCE(password_hash, %s) WHERE id = %s",
            (new_username, new_password_hash, student_id),
        )

    cursor.execute("ALTER TABLE students MODIFY username VARCHAR(50) NOT NULL")
    cursor.execute("ALTER TABLE students MODIFY password_hash VARCHAR(64) NOT NULL")
    try:
        cursor.execute("ALTER TABLE students ADD UNIQUE KEY username_unique (username)")
    except mysql.connector.Error:
        pass


def _fetch_one(query, params):
    con = get_connection()
    cursor = con.cursor(dictionary=True)
    cursor.execute(query, params)
    row = cursor.fetchone()
    cursor.close()
    con.close()
    return row


def fetch_latest_student(username):
    return _fetch_one("SELECT * FROM students WHERE LOWER(username) = LOWER(%s) LIMIT 1", (username.strip(),))


def fetch_student_by_username(username):
    return fetch_latest_student(username)


def fetch_student_by_id(student_id):
    return _fetch_one("SELECT * FROM students WHERE id = %s", (student_id,))


def fetch_subjects():
    con = get_connection()
    cursor = con.cursor(dictionary=True)
    cursor.execute("SELECT * FROM subjects ORDER BY name")
    rows = cursor.fetchall()
    cursor.close()
    con.close()
    return rows


def fetch_topics(subject_id=None, student_id=None):
    query = "SELECT topics.*, subjects.name AS subject_name FROM topics JOIN subjects ON subjects.id = topics.subject_id"
    params = []
    clauses = []
    if subject_id is not None:
        clauses.append("topics.subject_id = %s")
        params.append(subject_id)
    if student_id is not None:
        # Topics are shared in the DB, but only show ones this student used.
        clauses.append(
            "EXISTS (SELECT 1 FROM sessions student_sessions "
            "WHERE student_sessions.topic_id = topics.id AND student_sessions.student_id = %s)"
        )
        params.append(student_id)
    if clauses:
        query += " WHERE " + " AND ".join(clauses)
    query += " ORDER BY subjects.name, topics.name"
    con = get_connection()
    cursor = con.cursor(dictionary=True) 
    cursor.execute(query, tuple(params))
    rows = cursor.fetchall()
    cursor.close()
    con.close()
    return rows


def fetch_topic_by_id(topic_id):
    return _fetch_one(
        "SELECT topics.*, subjects.name AS subject_name FROM topics JOIN subjects ON subjects.id = topics.subject_id WHERE topics.id = %s",
        (topic_id,),
    )


def fetch_topic_by_name(subject_id, topic_name):
    return _fetch_one("SELECT * FROM topics WHERE subject_id = %s AND LOWER(name) = LOWER(%s)", (subject_id, topic_name))


def fetch_subject_by_name(subject_name):
    return _fetch_one("SELECT * FROM subjects WHERE LOWER(name) = LOWER(%s)", (subject_name,))


def ensure_subject(subject_name):
    existing = fetch_subject_by_name(subject_name)
    if existing:
        return existing["id"]

    con = get_connection()
    cursor = con.cursor()
    cursor.execute("INSERT INTO subjects (name) VALUES (%s)", (subject_name.strip(),))
    con.commit()
    subject_id = cursor.lastrowid
    cursor.close()
    con.close()
    return subject_id


def ensure_topic(subject_id, topic_name):
    existing = fetch_topic_by_name(subject_id, topic_name)
    if existing:
        return existing["id"]

    con = get_connection()
    cursor = con.cursor()
    cursor.execute("INSERT INTO topics (subject_id, name) VALUES (%s, %s)", (subject_id, topic_name.strip()))
    con.commit()
    topic_id = cursor.lastrowid
    cursor.close()
    con.close()
    return topic_id


def fetch_sessions(student_id=None, topic_id=None):
    query = (
        "SELECT sessions.*, topics.name AS topic_name, subjects.name AS subject_name "
        "FROM sessions JOIN topics ON topics.id = sessions.topic_id "
        "JOIN subjects ON subjects.id = topics.subject_id"
    )
    clauses = []
    params = []
    if student_id is not None:
        clauses.append("sessions.student_id = %s")
        params.append(student_id)
    if topic_id is not None:
        clauses.append("sessions.topic_id = %s")
        params.append(topic_id)
    if clauses:
        query += " WHERE " + " AND ".join(clauses)
    query += " ORDER BY sessions.date, sessions.id"
    con = get_connection()
    cursor = con.cursor(dictionary=True) 
    cursor.execute(query, tuple(params))
    rows = cursor.fetchall()
    cursor.close()
    con.close()
    return rows


def fetch_assessments(student_id=None, topic_id=None):
    query = (
        "SELECT assessments.*, topics.name AS topic_name, subjects.name AS subject_name "
        "FROM assessments JOIN topics ON topics.id = assessments.topic_id "
        "JOIN subjects ON subjects.id = topics.subject_id"
    )
    clauses = []
    params = []
    if student_id is not None:
        clauses.append("assessments.student_id = %s")
        params.append(student_id)
    if topic_id is not None:
        clauses.append("assessments.topic_id = %s")
        params.append(topic_id)
    if clauses:
        query += " WHERE " + " AND ".join(clauses)
    query += " ORDER BY assessments.date, assessments.id"
    con = get_connection()
    cursor = con.cursor(dictionary=True)
    cursor.execute(query, tuple(params))
    rows = cursor.fetchall()
    cursor.close()
    con.close()
    return rows
