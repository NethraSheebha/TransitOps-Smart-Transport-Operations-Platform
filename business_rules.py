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

    # helper to support both SQLAlchemy model objects and plain dicts used by tests
    def _get(obj, key, default=None):
        if obj is None:
            return default
        # try attribute access
        try:
            return getattr(obj, key)
        except Exception:
            pass
        # try dict-like access
        try:
            return obj.get(key, default)
        except Exception:
            return default

    v_status = _get(vehicle, "status")
    v_capacity = _get(vehicle, "max_load_capacity")
    d_status = _get(driver, "status")
    d_license_expiry = _get(driver, "license_expiry")

    if v_status in {"In Shop", "Retired"}:
        errors.append("Vehicle is unavailable for dispatch")

    try:
        if v_capacity is not None and float(v_capacity) < float(cargo_weight):
            errors.append("Cargo weight exceeds vehicle capacity")
    except Exception:
        errors.append("Invalid vehicle capacity")

    if d_status == "Suspended":
        errors.append("Driver is not eligible for dispatch")

    if d_license_expiry and isinstance(d_license_expiry, date) and d_license_expiry < date.today():
        errors.append("Driver license is expired")

    if v_status == "On Trip":
        errors.append("Vehicle is already on a trip")

    if d_status == "On Trip":
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
