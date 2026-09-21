from datetime import date, datetime

from db import fetch_sessions, fetch_topic_by_id, get_connection


def detect_time_slot(moment=None):
    moment = moment or datetime.now()
    hour = moment.hour
    if 5 <= hour < 12:
        return "morning"
    if 12 <= hour < 17:
        return "afternoon"
    if 17 <= hour < 21:
        return "evening"
    return "night"
def log_session(student_id, topic_id, duration_mins, confidence_before, confidence_after, energy_level, notes="", date_value=None, time_slot=None):
    sess_date = date_value or date.today().isoformat()
    slot = time_slot or detect_time_slot()
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
            sess_date,
            slot,
            duration_mins,
            confidence_before,
            confidence_after,
            energy_level,
            notes.strip(),
        ),
    )
    con.commit()
    sess_id = cursor.lastrowid
    cursor.close()
    con.close()
    return sess_id


def fetch_sessions_by_topic(student_id, topic_id):
    return fetch_sessions(student_id=student_id, topic_id=topic_id)


def fetch_all_sessions(student_id):
    return fetch_sessions(student_id=student_id)


def get_topic_label(topic_id):
    topic = fetch_topic_by_id(topic_id)
    if not topic:
        return "Unknown topic"
    return "%s - %s" % (topic["subject_name"], topic["name"])
