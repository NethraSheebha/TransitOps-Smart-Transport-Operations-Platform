import unittest
from app import app, db, User, Vehicle
from werkzeug.security import generate_password_hash


class BackendFeaturesTests(unittest.TestCase):
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

    def test_hashed_password_login(self):
        response = self.app.post(
            "/login",
            data={"email": "fleet@transitops.com", "password": "pass123"},
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("/dashboard", response.headers["Location"])

    def test_api_vehicle_crud(self):
        self.login()
        create_response = self.app.post(
            "/api/vehicles",
            json={
                "registration_number": "Van-77",
                "name": "API Van",
                "vehicle_type": "Van",
                "max_load_capacity": 600,
                "odometer": 2000,
                "acquisition_cost": 50000,
                "status": "Available",
                "region": "West",
                "notes": "API test",
            },
        )
        self.assertEqual(create_response.status_code, 201)
        data = create_response.get_json()
        self.assertEqual(data["registration_number"], "Van-77")

    def test_vehicle_page_filtering(self):
        self.login()
        with app.app_context():
            db.session.add(Vehicle(registration_number="Van-99", name="Filter Van", vehicle_type="Van", max_load_capacity=500, status="Available", region="North"))
            db.session.add(Vehicle(registration_number="Truck-01", name="Filter Truck", vehicle_type="Truck", max_load_capacity=800, status="Retired", region="South"))
            db.session.commit()
        response = self.app.get("/vehicles?status=Retired", follow_redirects=False)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Truck-01", response.data)
        self.assertNotIn(b"Van-99", response.data)


if __name__ == "__main__":
    unittest.main()
