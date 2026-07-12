import unittest
from datetime import date, timedelta

from business_rules import validate_trip_assignment, apply_trip_state, apply_maintenance_close


class BusinessRulesTests(unittest.TestCase):
    def test_trip_assignment_rejects_excess_capacity_and_suspended_driver(self):
        vehicle = {"status": "Available", "max_load_capacity": 400}
        driver = {"status": "Suspended", "license_expiry": date.today() + timedelta(days=30)}
        errors = validate_trip_assignment(vehicle, driver, cargo_weight=450)
        self.assertIn("Cargo weight exceeds vehicle capacity", errors)
        self.assertIn("Driver is not eligible for dispatch", errors)

    def test_dispatch_sets_vehicle_and_driver_to_on_trip(self):
        vehicle_status, driver_status = apply_trip_state("Dispatched")
        self.assertEqual(vehicle_status, "On Trip")
        self.assertEqual(driver_status, "On Trip")

    def test_closing_maintenance_restores_available(self):
        status = apply_maintenance_close("Retired")
        self.assertEqual(status, "Retired")


if __name__ == "__main__":
    unittest.main()
