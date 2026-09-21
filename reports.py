import csv
from datetime import datetime
from pathlib import Path

from analyzer import assessment_progress, peak_time_analysis, stickiness_score, topic_timeline
from db import fetch_topics, get_connection

try:
    from rich.console import Console
    from rich.table import Table
except ImportError:
    Console = None
    Table = None

try:
    from tabulate import tabulate
except ImportError:
    tabulate = None


console = Console() if Console else None


def _print(message):
    if console:
        console.print(message)
    else:
        print(message)


def _print_table(title, headers, rows):
    if console and Table is not None:
        table = Table(title=title)
        for header in headers:
            table.add_column(header)
        for row in rows:
            table.add_row(*["" if value is None else str(value) for value in row])
        console.print(table)
        return

    _print(title)
    if tabulate is not None:
        _print(tabulate(rows, headers=headers, tablefmt="grid"))
        return

    _print(" | ".join(headers))
    for row in rows:
        _print(" | ".join("" if value is None else str(value) for value in row))


def show_topics(student_id):
    topics = fetch_topics(student_id=student_id)
    rows = [[topic["subject_name"], topic["name"], topic["id"]] for topic in topics]
    _print_table("Tracked Topics", ["Subject", "Topic", "Topic ID"], rows)


def show_stuck_topics_report(student_id):
    from analyzer import stuck_topics

    results = stuck_topics(student_id)
    if not results:
        _print("No stuck topics found yet. Keep logging sessions.")
        return

    rows = [
        [item["subject_name"], item["topic_name"], item["sessions"], item["stickiness_score"], item["reason"]]
        for item in results
    ]
    _print_table("Weak Topic Analysis", ["Subject", "Topic", "Sessions", "Stickiness", "Why it looks weak"], rows)


def show_peak_performance_report(student_id):
    results = peak_time_analysis(student_id)
    if not results:
        _print("No sessions logged yet.")
        return []

    rows = [
        [item["time_slot"], item["session_count"], item["average_gain"], item["average_energy"], item["average_duration"]]
        for item in results
    ]
    _print_table("Peak Performance Report", ["Time Slot", "Sessions", "Avg Gain", "Avg Energy", "Avg Duration"], rows)
    return results


def show_drain_pattern_report(student_id):
    from analyzer import drain_pattern

    results = drain_pattern(student_id)
    if not results:
        _print("No clear drain pattern found yet.")
        return

    rows = [
        [item["previous_subject"], item["current_subject"], item["transition_count"], item["average_delta"], item["pattern"]]
        for item in results
    ]
    _print_table("Drain Pattern Report", ["From", "To", "Count", "Avg Delta", "Observation"], rows)


def show_progress_timeline(student_id, topic_id):
    sessions = topic_timeline(student_id, topic_id)
    from db import fetch_topic_by_id

    topic = fetch_topic_by_id(topic_id)
    if not topic:
        _print("Topic not found.")
        return
    if not sessions:
        _print("No sessions found for this topic.")
        return

    try:
        import matplotlib.pyplot as plt
    except ImportError:
        _print("Matplotlib is not installed, so the graph cannot be displayed.")
        return

    dates = [row["date"] for row in sessions]
    before = [float(row["confidence_before"]) for row in sessions]
    after = [float(row["confidence_after"]) for row in sessions]

    assessment_rows = assessment_progress(student_id, topic_id)
    assessment_dates = [row["date"] for row in assessment_rows]
    assessment_scores = [round((float(row["score"]) / float(row["max_score"])) * 10, 2) for row in assessment_rows]

    plt.figure(figsize=(10, 5))
    plt.plot(dates, before, marker="o", linewidth=2, label="Confidence before")
    plt.plot(dates, after, marker="o", linewidth=2, label="Confidence after")
    if assessment_rows:
        plt.plot(assessment_dates, assessment_scores, marker="s", linewidth=1.5, label="Assessment score (scaled)")
    plt.title("Progress Timeline - %s / %s" % (topic["subject_name"], topic["name"]))
    plt.xlabel("Date")
    plt.ylabel("Score / Confidence")
    plt.xticks(rotation=45)
    plt.legend()
    plt.tight_layout()
    plt.show()


def export_to_csv(student_id, export_type="all", output_path=None):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    target = Path(output_path) if output_path else Path.cwd() / ("study_tracker_export_%s_%s.csv" % (export_type, timestamp))
    rows = []

    if export_type in {"all", "sessions"}:
        rows.extend(_session_export_rows(student_id))
    if export_type in {"all", "assessments"}:
        rows.extend(_assessment_export_rows(student_id))
    if export_type == "reports":
        rows.extend(_report_export_rows(student_id))

    if not rows:
        rows = [{"message": "No data available for the selected export type"}]

    fieldnames = sorted({key for row in rows for key in row.keys()})
    with target.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    _print("CSV exported to %s" % target)
    return target


def _session_export_rows(student_id):
    con = get_connection()
    cursor = con.cursor(dictionary=True)
    cursor.execute(
        """
        SELECT sessions.id, students.name AS student_name, subjects.name AS subject_name,
               topics.name AS topic_name, sessions.date, sessions.time_slot,
               sessions.duration_mins, sessions.confidence_before, sessions.confidence_after,
               sessions.energy_level, sessions.notes
        FROM sessions
        JOIN students ON students.id = sessions.student_id
        JOIN topics ON topics.id = sessions.topic_id
        JOIN subjects ON subjects.id = topics.subject_id
        WHERE sessions.student_id = %s
        ORDER BY sessions.date, sessions.id
        """,
        (student_id,),
    )
    rows = cursor.fetchall()
    cursor.close()
    con.close()
    return rows


def _assessment_export_rows(student_id):
    con = get_connection()
    cursor = con.cursor(dictionary=True)
    cursor.execute(
        """
        SELECT assessments.id, students.name AS student_name, subjects.name AS subject_name,
               topics.name AS topic_name, assessments.score, assessments.max_score, assessments.date
        FROM assessments
        JOIN students ON students.id = assessments.student_id
        JOIN topics ON topics.id = assessments.topic_id
        JOIN subjects ON subjects.id = topics.subject_id
        WHERE assessments.student_id = %s
        ORDER BY assessments.date, assessments.id
        """,
        (student_id,),
    )
    rows = cursor.fetchall()
    cursor.close()
    con.close()
    return rows


def _report_export_rows(student_id):
    rows = []
    for topic in fetch_topics(student_id=student_id):
        report = stickiness_score(student_id, int(topic["id"]))
        rows.append(
            {
                "report_type": "stickiness",
                "subject_name": report.get("subject_name"),
                "topic_name": report.get("topic_name"),
                "sessions": report.get("sessions"),
                "stickiness_score": report.get("stickiness_score"),
                "reason": report.get("reason"),
            }
        )
    return rows
