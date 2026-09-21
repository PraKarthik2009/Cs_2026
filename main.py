from datetime import date
import sys

import mysql.connector

from db import fetch_topics, get_connection, initialize_database
from reports import export_to_csv, show_peak_performance_report, show_progress_timeline, show_stuck_topics_report, show_topics
from sessions import log_session
from student import prompt_float, prompt_integer, prompt_text, show_auth_menu
from ui import banner, error, info, section, show_menu, success


def _choose_topic(student):
    topics = fetch_topics(student_id=student["id"])
    if not topics:
        info("No topics found for this account. Run onboarding first.")
        return None

    section("Your topics")
    for topic in topics:
        print("%s. %s - %s" % (topic['id'], topic['subject_name'], topic['name']))

    topic_id = prompt_integer("Choose topic ID: ", minimum=1)
    for topic in topics:
        if int(topic["id"]) == topic_id:
            return topic_id
    error("Invalid topic ID.")
    return None


def _log_session(student):
    topic_id = _choose_topic(student)
    if topic_id is None:
        return

    duration = prompt_integer("Duration in minutes: ", minimum=1)
    confidence_before = prompt_float("Confidence before (0-10): ", minimum=0, maximum=10)
    confidence_after = prompt_float("Confidence after (0-10): ", minimum=0, maximum=10)
    energy_level = prompt_integer("Energy level (1-10): ", minimum=1, maximum=10)
    notes = prompt_text("Notes: ")
    sess_id = log_session(
        student_id=student["id"],
        topic_id=topic_id,
        duration_mins=duration,
        confidence_before=confidence_before,
        confidence_after=confidence_after,
        energy_level=energy_level,
        notes=notes,
    )
    success("Session saved with ID %s." % sess_id)


def _log_assessment(student):
    topic_id = _choose_topic(student)
    if topic_id is None:
        return

    score = prompt_float("Score: ", minimum=0)
    max_score = prompt_float("Max score: ", minimum=1)
    assessment_date = input("Date (YYYY-MM-DD, leave blank for today): ").strip() or date.today().isoformat()

    con = get_connection()
    cursor = con.cursor()
    cursor.execute(
        "INSERT INTO assessments (student_id, topic_id, score, max_score, date) VALUES (%s, %s, %s, %s, %s)",
        (student["id"], topic_id, score, max_score, assessment_date),
    )
    con.commit()
    success("Assessment saved with ID %s." % cursor.lastrowid)
    cursor.close()
    con.close()


def _export_csv(student):
    choice = show_menu(
        "Export CSV",
        [
            ("1", "Sessions"),
            ("2", "Assessments"),
            ("3", "Reports"),
            ("4", "All data"),
            ("0", "Cancel"),
        ],
    )
    if choice == "0":
        info("Export cancelled.")
        return
    mapping = {"1": "sessions", "2": "assessments", "3": "reports", "4": "all"}
    export_type = mapping.get(choice)
    if export_type is None:
        error("Invalid export choice.")
        return
    export_to_csv(student["id"], export_type=export_type)


def main():
    initialize_database()
    student = show_auth_menu()
    while True:
        banner("Study Tracker", "Signed in as %s" % student["username"])
        choice = show_menu(
            "Main Menu",
            [
                ("1", "Log study session"),
                ("2", "Log assessment"),
                ("3", "View topics"),
                ("4", "Progress timeline"),
                ("5", "Weak topic analysis"),
                ("6", "Peak performance report"),
                ("7", "Export data"),
                ("0", "Exit"),
            ],
        )

        if choice == "1":
            _log_session(student)
        elif choice == "2":
            _log_assessment(student)
        elif choice == "3":
            show_topics(student["id"])
        elif choice == "4":
            topic_id = _choose_topic(student)
            if topic_id is not None:
                show_progress_timeline(student["id"], topic_id)
        elif choice == "5":
            show_stuck_topics_report(student["id"])
        elif choice == "6":
            show_peak_performance_report(student["id"])
        elif choice == "7":
            _export_csv(student)
        elif choice == "0":
            info("Goodbye.")
            break
        else:
            error("Invalid option. Try again.")


if __name__ == "__main__":
    try:
        main()
    except mysql.connector.Error:
        error("Database unavailable. Start MySQL on localhost:3306 and try again.")
        sys.exit(1)
