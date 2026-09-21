from collections import defaultdict
from statistics import mean

from db import fetch_assessments, fetch_sessions, fetch_topic_by_id, fetch_topics, get_connection


def _clean_session_rows(student_id):
    rows = fetch_sessions(student_id=student_id)
    return [dict(row) for row in rows if row["time_slot"] != "baseline"]


def _baseline_for_topic(student_id, topic_id):
    con = get_connection()
    cursor = con.cursor(dictionary=True)
    cursor.execute(
        """
        SELECT confidence_before
        FROM sessions
        WHERE student_id = %s AND topic_id = %s
        ORDER BY sessions.date, sessions.id
        LIMIT 1
        """,
        (student_id, topic_id),
    )
    row = cursor.fetchone()
    cursor.close()
    con.close()
    if row is None:
        return None
    return float(row["confidence_before"])


def stickiness_score(student_id, topic_id):
    topic = fetch_topic_by_id(topic_id)
    if topic is None:
        return {
            "topic_id": topic_id,
            "topic_name": "Unknown topic",
            "stickiness_score": 0.0,
            "sessions": 0,
            "reason": "Topic not found.",
        }

    con = get_connection()
    cursor = con.cursor(dictionary=True)
    cursor.execute(
        """
        SELECT *
        FROM sessions
        WHERE student_id = %s AND topic_id = %s AND time_slot != 'baseline'
        ORDER BY sessions.date, sessions.id
        """,
        (student_id, topic_id),
    )
    sessions = cursor.fetchall()
    cursor.close()
    con.close()

    if not sessions:
        return {
            "topic_id": topic_id,
            "topic_name": topic["name"],
            "subject_name": topic["subject_name"],
            "stickiness_score": 0.0,
            "sessions": 0,
            "reason": "No study sessions yet.",
        }

    sessions = [dict(row) for row in sessions]
    baseline = _baseline_for_topic(student_id, topic_id)
    if baseline is None:
        baseline = float(sessions[0]["confidence_before"])

    deltas = [float(row["confidence_after"]) - float(row["confidence_before"]) for row in sessions]
    latest_after = float(sessions[-1]["confidence_after"])
    gain_from_baseline = latest_after - baseline
    average_delta = mean(deltas)
    stagnation_count = sum(1 for delta in deltas if delta <= 0)
    revision_count = len(sessions)

    raw_score = 50 + (gain_from_baseline * 8) + (average_delta * 10) + (revision_count * 2) - (stagnation_count * 6)
    score = max(0.0, min(100.0, round(raw_score, 1)))

    if revision_count >= 5 and gain_from_baseline <= 1 and average_delta <= 0.5:
        reason = "Revised many times, but confidence has not moved much."
    elif average_delta <= 0:
        reason = "Study sessions are not producing positive confidence change."
    elif gain_from_baseline < 2:
        reason = "Confidence growth is very slow across repeated sessions."
    else:
        reason = "Topic is improving, but still worth watching."

    return {
        "topic_id": topic_id,
        "topic_name": topic["name"],
        "subject_name": topic["subject_name"],
        "stickiness_score": score,
        "sessions": revision_count,
        "gain_from_baseline": round(gain_from_baseline, 2),
        "average_delta": round(average_delta, 2),
        "reason": reason,
    }


def stuck_topics(student_id, min_sessions=2):
    topics = fetch_topics(student_id=student_id)
    results = []
    for topic in topics:
        detail = stickiness_score(student_id, int(topic["id"]))
        if detail["sessions"] >= min_sessions and detail["stickiness_score"] <= 55:
            detail["topic_id"] = int(topic["id"])
            results.append(detail)
    results.sort(key=lambda item: (item["stickiness_score"], -item["sessions"]))
    return results


def peak_time_analysis(student_id):
    sessions = _clean_session_rows(student_id)
    grouped = defaultdict(list)
    energy = defaultdict(list)
    durations = defaultdict(list)

    for row in sessions:
        time_slot = str(row["time_slot"])
        delta = float(row["confidence_after"]) - float(row["confidence_before"])
        grouped[time_slot].append(delta)
        if row["energy_level"] is not None:
            energy[time_slot].append(int(row["energy_level"]))
        durations[time_slot].append(int(row["duration_mins"]))

    result = []
    for time_slot, deltas in grouped.items():
        result.append(
            {
                "time_slot": time_slot,
                "session_count": len(deltas),
                "average_gain": round(mean(deltas), 2),
                "average_energy": round(mean(energy[time_slot]), 2) if energy[time_slot] else None,
                "average_duration": round(mean(durations[time_slot]), 2),
            }
        )

    result.sort(key=lambda item: (item["average_gain"], item["session_count"]), reverse=True)
    return result


def drain_pattern(student_id):
    sessions = _clean_session_rows(student_id)
    if len(sessions) < 2:
        return []

    transitions = defaultdict(list)
    subject_labels = {}
    for row in sessions:
        topic = fetch_topic_by_id(int(row["topic_id"]))
        if topic:
            subject_labels[int(row["topic_id"])] = str(topic["subject_name"])

    previous_row = None
    for row in sessions:
        if previous_row is None:
            previous_row = row
            continue
        previous_subject = subject_labels.get(int(previous_row["topic_id"]), "Unknown")
        current_subject = subject_labels.get(int(row["topic_id"]), "Unknown")
        if previous_subject != current_subject:
            delta = float(row["confidence_after"]) - float(row["confidence_before"])
            transitions[(previous_subject, current_subject)].append(delta)
        previous_row = row

    patterns = []
    for (previous_subject, current_subject), deltas in transitions.items():
        if len(deltas) < 2:
            continue
        average_delta = mean(deltas)
        if average_delta <= 0.5:
            patterns.append(
                {
                    "previous_subject": previous_subject,
                    "current_subject": current_subject,
                    "transition_count": len(deltas),
                    "average_delta": round(average_delta, 2),
                    "pattern": "Studying %s after %s tends to reduce your confidence gain." % (current_subject, previous_subject),
                }
            )

    patterns.sort(key=lambda item: (item["average_delta"], -item["transition_count"]))
    return patterns


def topic_timeline(student_id, topic_id):
    con = get_connection()
    cursor = con.cursor(dictionary=True)
    cursor.execute(
        """
        SELECT *
        FROM sessions
        WHERE student_id = %s AND topic_id = %s
        ORDER BY sessions.date, sessions.id
        """,
        (student_id, topic_id),
    )
    rows = cursor.fetchall()
    cursor.close()
    con.close()
    return [dict(row) for row in rows]


def assessment_progress(student_id, topic_id):
    rows = fetch_assessments(student_id=student_id, topic_id=topic_id)
    return [dict(row) for row in rows]
