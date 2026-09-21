import hashlib
import sys

import mysql.connector

from ui import error

DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "student",
}


def create_database():
    con = mysql.connector.connect(**DB_CONFIG)
    cursor = con.cursor()
    cursor.execute("CREATE DATABASE IF NOT EXISTS study_tracker")
    cursor.close()
    con.close()

    con = mysql.connector.connect(**DB_CONFIG, database="study_tracker")
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
        generated_username = f"user_{student_id}"
        generated_password_hash = hashlib.sha256(f"legacy:{student_id}".encode()).hexdigest()
        cursor.execute(
            "UPDATE students SET username = %s, password_hash = COALESCE(password_hash, %s) WHERE id = %s",
            (generated_username, generated_password_hash, student_id),
        )

    cursor.execute("ALTER TABLE students MODIFY username VARCHAR(50) NOT NULL")
    cursor.execute("ALTER TABLE students MODIFY password_hash VARCHAR(64) NOT NULL")
    try:
        cursor.execute("ALTER TABLE students ADD UNIQUE KEY username_unique (username)")
    except mysql.connector.Error:
        pass
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
    print("Database ready.")


if __name__ == "__main__":
    try:
        create_database()
    except mysql.connector.Error:
        error("Database unavailable. Start MySQL on localhost:3306 and try again.")
        sys.exit(1)
