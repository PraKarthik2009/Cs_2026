from datetime import date
import hashlib
import sys

from db import (
    ensure_subject,
    ensure_topic,
    fetch_student_by_username,
    fetch_topics,
    get_connection,
)
from ui import banner, error, info, show_menu


def prompt_text(message):
    while True:
        value = input(message).strip()
        if value:
            return value
        error("Input cannot be empty.")


def prompt_integer(message, minimum=None, maximum=None):
    while True:
        raw_value = input(message).strip()
        try:
            value = int(raw_value)
        except ValueError:
            error("Please enter a whole number.")
            continue
        if minimum is not None and value < minimum:
            error("Enter a value of at least %s." % minimum)
            continue
        if maximum is not None and value > maximum:
            error("Enter a value of at most %s." % maximum)
            continue
        return value


def prompt_float(message, minimum=None, maximum=None):
    while True:
        raw_value = input(message).strip()
        try:
            value = float(raw_value)
        except ValueError:
            error("Please enter a number.")
            continue
        if minimum is not None and value < minimum:
            error("Enter a value of at least %s." % minimum)
            continue
        if maximum is not None and value > maximum:
            error("Enter a value of at most %s." % maximum)
            continue
        return value


def save_student(name, grade, board, username, password_hash):
    con = get_connection()
    cursor = con.cursor()
    cursor.execute(
        "INSERT INTO students (name, grade, board, username, password_hash) VALUES (%s, %s, %s, %s, %s)",
        (name.strip(), grade.strip(), board.strip(), username.strip().lower(), password_hash),
    )
    con.commit()
    student_id = cursor.lastrowid
    cursor.close()
    con.close()
    return student_id


def _normalize_username(username):
    return username.strip().lower()


def _password_hash(password):
    return hashlib.sha256(password.encode()).hexdigest()


def _student_to_dict(student_row):
    if student_row is None:
        return None
    return dict(student_row)


def _fetch_student_with_auth(username):
    return _student_to_dict(fetch_student_by_username(_normalize_username(username)))


def login():
    attempts = 0
    while attempts < 3:
        username = prompt_text("Username: ")
        password = prompt_text("Password: ")
        student = _fetch_student_with_auth(username)
        entered_hash = _password_hash(password)
        if student is not None and student.get("password_hash") == entered_hash:
            info("Welcome back, %s!" % student["name"])
            return student
        attempts += 1
        error("Incorrect username or password.")
    sys.exit()


def create_account():
    name = prompt_text("Name: ")
    while True:
        username = _normalize_username(prompt_text("Username: "))
        if _fetch_student_with_auth(username) is not None:
            error("Username already exists. Choose another one.")
            continue
        break

    while True:
        password = prompt_text("Password: ")
        confirm = prompt_text("Confirm password: ")
        if password != confirm:
            error("Passwords do not match. Try again.")
            continue
        break

    pw_hash = _password_hash(password)
    student_id = save_student(name, "", "", username, pw_hash)
    collect_subjects_and_baseline(student_id)
    student = _student_to_dict(fetch_student_by_username(username))
    if student is None:
        student = {
            "id": student_id,
            "name": name.strip(),
            "grade": "",
            "board": "",
            "username": username,
            "password_hash": pw_hash,
        }
    return student


def show_auth_menu():
    while True:
        banner("STUDY TRACKER", "Personal study insights")
        choice = show_menu(
            "Welcome",
            [("1", "Login"), ("2", "Create account"), ("0", "Exit")],
        )

        if choice == "1":
            return login()
        if choice == "2":
            return create_account()
        if choice == "0":
            info("Goodbye.")
            sys.exit()
        error("Invalid option. Try again.")


def load_or_onboard_student():
    return show_auth_menu()


def collect_subjects_and_baseline(student_id):
    subject_count = prompt_integer("How many subjects do you want to track? ", minimum=1)
    for _ in range(subject_count):
        subject_name = prompt_text("Subject name: ")
        subject_id = ensure_subject(subject_name)
        topic_count = prompt_integer("How many topics under %s? " % subject_name, minimum=1)
        for _ in range(topic_count):
            topic_name = prompt_text("Topic name: ")
            topic_id = ensure_topic(subject_id, topic_name)
            baseline = prompt_float("Baseline confidence for %s (0-10): " % topic_name, minimum=0, maximum=10)
            con = get_connection()
            cursor = con.cursor()
            cursor.execute(
                """
                INSERT INTO sessions (
                    student_id, topic_id, date, time_slot, duration_mins,
                    confidence_before, confidence_after, energy_level, notes
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    student_id,
                    topic_id,
                    date.today().isoformat(),
                    "baseline",
                    0,
                    baseline,
                    baseline,
                    5,
                    "baseline confidence",
                ),
            )
            con.commit()
            cursor.close()
            con.close()


def list_topics_for_student(student_id):
    topics = fetch_topics(student_id=student_id)
    formatted = []
    for topic in topics:
        formatted.append(
            {
                "subject": topic["subject_name"],
                "topic": topic["name"],
                "topic_id": topic["id"],
                "subject_id": topic["subject_id"],
            }
        )
    return formatted


def refresh_profile_from_input(student):
    student["name"] = prompt_text("Student name: ")
    student["grade"] = prompt_text("Grade: ")
    student["board"] = prompt_text("Board: ")
    con = get_connection()
    cursor = con.cursor()
    cursor.execute(
        "UPDATE students SET name = %s, grade = %s, board = %s WHERE id = %s",
        (student["name"], student["grade"], student["board"], student["id"]),
    )
    con.commit()
    cursor.close()
    con.close()
    return student
