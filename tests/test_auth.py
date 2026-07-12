import unittest
from app import app, db, User, seed_default_users, verify_password, is_hashed_password
from werkzeug.security import generate_password_hash


class AuthTests(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False
        with app.app_context():
            db.drop_all()
            db.create_all()
            db.session.add(User(email="fleet@transitops.com", password="pass123", role="Fleet Manager"))
            db.session.add(User(email="driver@transitops.com", password="pass123", role="Driver"))
            db.session.commit()

    def test_unauthenticated_user_is_redirected(self):
        response = self.app.get("/dashboard", follow_redirects=False)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response.headers["Location"])

    def test_login_sets_session_and_allows_dashboard(self):
        response = self.app.post(
            "/login",
            data={"email": "fleet@transitops.com", "password": "pass123"},
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("/dashboard", response.headers["Location"])

    def test_role_restriction_blocks_unauthorized_access(self):
        self.app.post(
            "/login",
            data={"email": "driver@transitops.com", "password": "pass123"},
            follow_redirects=False,
        )
        response = self.app.get("/vehicles", follow_redirects=False)
        self.assertEqual(response.status_code, 403)

    def test_seed_default_users_preserves_existing_hashed_passwords(self):
        with app.app_context():
            db.drop_all()
            db.create_all()
            db.session.add(User(email="seeded@example.com", password=generate_password_hash("demo123"), role="Fleet Manager"))
            db.session.commit()

        with app.app_context():
            seed_default_users()

        with app.app_context():
            user = User.query.filter_by(email="seeded@example.com").first()
            self.assertIsNotNone(user)
            self.assertTrue(is_hashed_password(user.password))
            self.assertTrue(verify_password(user.password, "demo123"))


if __name__ == "__main__":
    unittest.main()
