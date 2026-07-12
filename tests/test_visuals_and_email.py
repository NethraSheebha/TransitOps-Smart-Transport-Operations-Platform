import unittest
from app import app, db, User
from werkzeug.security import generate_password_hash


class VisualsAndEmailTests(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False
        with app.app_context():
            db.drop_all()
            db.create_all()
            db.session.add(User(email="fleet@transitops.com", password=generate_password_hash("pass123"), role="Fleet Manager"))
            db.session.commit()

    def login(self):
        self.app.post(
            "/login",
            data={"email": "fleet@transitops.com", "password": "pass123"},
            follow_redirects=False,
        )

    def test_dashboard_renders_chart_data(self):
        self.login()
        response = self.app.get("/dashboard")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"chart-data", response.data)

    def test_dashboard_uses_chartjs_for_interactive_visuals(self):
        self.login()
        response = self.app.get("/dashboard")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"chart.js", response.data)
        self.assertIn(b"<canvas", response.data)

    def test_dashboard_includes_sidebar_and_dark_mode_toggle(self):
        self.login()
        response = self.app.get("/dashboard")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"sidebar", response.data)
        self.assertIn(b"dark-mode-toggle", response.data)

    def test_reminder_endpoint_returns_payload(self):
        self.login()
        response = self.app.get("/reminders/send")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"sent", response.data)


if __name__ == "__main__":
    unittest.main()
