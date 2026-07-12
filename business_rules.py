from datetime import date


VALID_VEHICLE_STATUSES = {"Available", "On Trip", "In Shop", "Retired"}
VALID_DRIVER_STATUSES = {"Available", "On Trip", "Off Duty", "Suspended"}


def validate_trip_assignment(vehicle, driver, cargo_weight):
    errors = []
    if not vehicle:
        errors.append("Vehicle is required")
        return errors
    if not driver:
        errors.append("Driver is required")
        return errors

    if vehicle.status in {"In Shop", "Retired"}:
        errors.append("Vehicle is unavailable for dispatch")

    if vehicle.max_load_capacity < cargo_weight:
        errors.append("Cargo weight exceeds vehicle capacity")

    if driver.status == "Suspended":
        errors.append("Driver is not eligible for dispatch")

    if driver.license_expiry and driver.license_expiry < date.today():
        errors.append("Driver license is expired")

    if vehicle.status == "On Trip":
        errors.append("Vehicle is already on a trip")

    if driver.status == "On Trip":
        errors.append("Driver is already on a trip")

    return errors


def apply_trip_state(state):
    if state == "Dispatched":
        return "On Trip", "On Trip"
    return "Available", "Available"


def apply_maintenance_close(vehicle_status):
    if vehicle_status == "Retired":
        return "Retired"
    return "Available"
