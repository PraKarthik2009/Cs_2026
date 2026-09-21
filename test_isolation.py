import unittest
from unittest.mock import Mock, patch

import db


class TopicIsolationTests(unittest.TestCase):
    def test_fetch_topics_scopes_results_to_student(self):
        cursor = Mock()
        cursor.fetchall.return_value = []
        connection = Mock()
        connection.cursor.return_value = cursor

        with patch.object(db, "get_connection", return_value=connection):
            db.fetch_topics(student_id=42)

        query, params = cursor.execute.call_args.args
        self.assertIn("EXISTS", query)
        self.assertIn("student_sessions.student_id = %s", query)
        self.assertEqual(params, (42,))

    def test_fetch_topics_keeps_subject_and_student_filters_composable(self):
        cursor = Mock()
        cursor.fetchall.return_value = []
        connection = Mock()
        connection.cursor.return_value = cursor

        with patch.object(db, "get_connection", return_value=connection):
            db.fetch_topics(subject_id=7, student_id=42)

        query, params = cursor.execute.call_args.args
        self.assertIn("topics.subject_id = %s", query)
        self.assertIn("student_sessions.student_id = %s", query)
        self.assertEqual(params, (7, 42))


if __name__ == "__main__":
    unittest.main()
