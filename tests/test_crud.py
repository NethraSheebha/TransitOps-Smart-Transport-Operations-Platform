import unittest
from app import app, db, User, Vehicle


class CrudTests(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False
        with app.app_context():
            db.drop_all()
            db.create_all()
            db.session.add(User(email="fleet@transitops.com", password="pass123", role="Fleet Manager"))
            db.session.commit()

    def login(self):
        self.app.post(
            "/login",
            data={"email": "fleet@transitops.com", "password": "pass123"},
            follow_redirects=False,
        )

    def test_vehicle_can_be_created_and_updated(self):
        self.login()
        response = self.app.post(
            "/vehicles",
            data={
                "registration_number": "Van-05",
                "name": "Transit Van",
                "vehicle_type": "Van",
                "max_load_capacity": 500,
                "odometer": 1000,
                "acquisition_cost": 40000,
                "status": "Available",
            },
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 302)

        with app.app_context():
            vehicle = Vehicle.query.filter_by(registration_number="Van-05").first()
            self.assertIsNotNone(vehicle)

        response = self.app.post(
            f"/vehicles/{vehicle.id}/edit",
            data={
                "registration_number": "Van-05",
                "name": "Updated Van",
                "vehicle_type": "Van",
                "max_load_capacity": 550,
                "odometer": 1100,
                "acquisition_cost": 42000,
                "status": "Available",
            },
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 302)

        with app.app_context():
            updated_vehicle = Vehicle.query.get(vehicle.id)
            self.assertEqual(updated_vehicle.name, "Updated Van")
            self.assertEqual(updated_vehicle.max_load_capacity, 550.0)

    def test_vehicle_edit_without_form_fields_preserves_existing_values(self):
        self.login()
        response = self.app.post(
            "/vehicles",
            data={
                "registration_number": "Van-06",
                "name": "Transit Van",
                "vehicle_type": "Van",
                "max_load_capacity": 500,
                "odometer": 1000,
                "acquisition_cost": 40000,
                "status": "Available",
            },
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 302)

        with app.app_context():
            vehicle = Vehicle.query.filter_by(registration_number="Van-06").first()
            self.assertIsNotNone(vehicle)

        response = self.app.post(f"/vehicles/{vehicle.id}/edit", follow_redirects=False)
        self.assertEqual(response.status_code, 302)

        with app.app_context():
            unchanged_vehicle = Vehicle.query.get(vehicle.id)
            self.assertEqual(unchanged_vehicle.name, "Transit Van")
            self.assertEqual(unchanged_vehicle.max_load_capacity, 500.0)

    def test_vehicle_edit_page_renders_inline_form(self):
        self.login()
        response = self.app.post(
            "/vehicles",
            data={
                "registration_number": "Van-07",
                "name": "Transit Van",
                "vehicle_type": "Van",
                "max_load_capacity": 500,
                "odometer": 1000,
                "acquisition_cost": 40000,
                "status": "Available",
            },
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 302)

        with app.app_context():
            vehicle = Vehicle.query.filter_by(registration_number="Van-07").first()
            self.assertIsNotNone(vehicle)

        response = self.app.get(f"/vehicles?edit_id={vehicle.id}")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Edit Vehicle", response.data)
        self.assertIn(b"Van-07", response.data)


if __name__ == "__main__":
    unittest.main()
