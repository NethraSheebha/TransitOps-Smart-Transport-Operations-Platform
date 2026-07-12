from flask import Flask, render_template, request, redirect, url_for, jsonify, send_file, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date
import io
import os
import smtplib
from email.message import EmailMessage
from io import StringIO
import csv
from sqlalchemy import or_
import sqlalchemy as sa

if not hasattr(sa, "__all__"):
    sa.__all__ = [name for name in dir(sa) if not name.startswith("_")]
from werkzeug.security import generate_password_hash, check_password_hash
from business_rules import validate_trip_assignment, apply_trip_state, apply_maintenance_close

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///transitops.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = "hackathon-secret"
db = SQLAlchemy(app)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(50), default="Fleet Manager")


class Vehicle(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    registration_number = db.Column(db.String(80), unique=True, nullable=False)
    name = db.Column(db.String(120), nullable=False)
    vehicle_type = db.Column(db.String(80), nullable=False)
    max_load_capacity = db.Column(db.Float, nullable=False)
    odometer = db.Column(db.Float, default=0)
    acquisition_cost = db.Column(db.Float, default=0)
    status = db.Column(db.String(40), default="Available")
    region = db.Column(db.String(80), default="North")
    notes = db.Column(db.Text, default="")

    def as_dict(self):
        return {
            "id": self.id,
            "registration_number": self.registration_number,
            "name": self.name,
            "vehicle_type": self.vehicle_type,
            "max_load_capacity": self.max_load_capacity,
            "odometer": self.odometer,
            "acquisition_cost": self.acquisition_cost,
            "status": self.status,
            "region": self.region,
            "notes": self.notes,
        }


ALLOWED_VEHICLE_STATUSES = {"Available", "On Trip", "In Shop", "Retired"}


class Driver(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    license_number = db.Column(db.String(80), unique=True, nullable=False)
    license_category = db.Column(db.String(40), default="B")
    license_expiry = db.Column(db.Date, nullable=False)
    contact_number = db.Column(db.String(40), nullable=False)
    safety_score = db.Column(db.Float, default=90)
    status = db.Column(db.String(40), default="Available")
    region = db.Column(db.String(80), default="North")
    notes = db.Column(db.Text, default="")


class Trip(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    source = db.Column(db.String(120), nullable=False)
    destination = db.Column(db.String(120), nullable=False)
    cargo_weight = db.Column(db.Float, nullable=False)
    planned_distance = db.Column(db.Float, nullable=False)
    state = db.Column(db.String(40), default="Draft")
    vehicle_id = db.Column(db.Integer, db.ForeignKey("vehicle.id"))
    driver_id = db.Column(db.Integer, db.ForeignKey("driver.id"))
    fuel_consumed = db.Column(db.Float, default=0)
    final_odometer = db.Column(db.Float, default=0)
    revenue = db.Column(db.Float, default=0)


class MaintenanceLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    vehicle_id = db.Column(db.Integer, db.ForeignKey("vehicle.id"), nullable=False)
    description = db.Column(db.String(200), nullable=False)
    cost = db.Column(db.Float, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    closed_at = db.Column(db.DateTime)
    is_open = db.Column(db.Boolean, default=True)


class FuelLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    vehicle_id = db.Column(db.Integer, db.ForeignKey("vehicle.id"), nullable=False)
    liters = db.Column(db.Float, nullable=False)
    cost = db.Column(db.Float, nullable=False)
    logged_at = db.Column(db.Date, default=date.today)


class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    vehicle_id = db.Column(db.Integer, db.ForeignKey("vehicle.id"), nullable=False)
    description = db.Column(db.String(200), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    logged_at = db.Column(db.Date, default=date.today)


def is_hashed_password(password):
    if not isinstance(password, str):
        return False
    return password.startswith(("scrypt:", "pbkdf2:", "sha256$", "md5$", "argon2", "bcrypt$"))


def verify_password(stored_password, candidate_password):
    if not stored_password or not candidate_password:
        return False
    if is_hashed_password(stored_password):
        return check_password_hash(stored_password, candidate_password)
    return stored_password == candidate_password


def seed_default_users():
    seed_users = [
        ("admin@transitops.com", "admin123", "Fleet Manager"),
        ("safety@transitops.com", "admin123", "Safety Officer"),
        ("driver@transitops.com", "admin123", "Driver"),
        ("finance@transitops.com", "admin123", "Financial Analyst"),
    ]
    for email, password, role in seed_users:
        user = User.query.filter_by(email=email).first()
        if user is None:
            db.session.add(User(email=email, password=generate_password_hash(password), role=role))
            continue
        user.role = role
        if not is_hashed_password(user.password):
            user.password = generate_password_hash(user.password)
    for user in User.query.all():
        if not is_hashed_password(user.password):
            user.password = generate_password_hash(user.password)
    db.session.commit()


def seed_ten_vehicles():
    if Vehicle.query.count() != 0:
        return
    vehicles = [
        Vehicle(registration_number="VAN-05", name="Ford Transit", vehicle_type="Van", max_load_capacity=500, odometer=12000, acquisition_cost=35000, status="Available", region="North"),
        Vehicle(registration_number="TRK-01", name="Volvo FH16", vehicle_type="Heavy Truck", max_load_capacity=15000, odometer=85000, acquisition_cost=120000, status="Available", region="North"),
        Vehicle(registration_number="TRK-02", name="Isuzu NPR", vehicle_type="Box Truck", max_load_capacity=4000, odometer=45000, acquisition_cost=55000, status="On Trip", region="South"),
        Vehicle(registration_number="VAN-02", name="Mercedes Sprinter", vehicle_type="Van", max_load_capacity=1200, odometer=62000, acquisition_cost=42000, status="In Shop", region="West"),
        Vehicle(registration_number="VAN-03", name="Chevy Express", vehicle_type="Van", max_load_capacity=800, odometer=195000, acquisition_cost=28000, status="Retired", region="North"),
        Vehicle(registration_number="TRK-03", name="Scania R500", vehicle_type="Heavy Truck", max_load_capacity=18000, odometer=110000, acquisition_cost=135000, status="Available", region="South"),
        Vehicle(registration_number="TRK-04", name="Freightliner Cascadia", vehicle_type="Heavy Truck", max_load_capacity=20000, odometer=95000, acquisition_cost=145000, status="On Trip", region="West"),
        Vehicle(registration_number="VAN-04", name="RAM ProMaster", vehicle_type="Van", max_load_capacity=1000, odometer=28000, acquisition_cost=38000, status="Available", region="North"),
        Vehicle(registration_number="TRK-05", name="Hino 268", vehicle_type="Box Truck", max_load_capacity=5000, odometer=73000, acquisition_cost=62000, status="In Shop", region="South"),
        Vehicle(registration_number="VAN-06", name="Nissan NV2500", vehicle_type="Van", max_load_capacity=900, odometer=15000, acquisition_cost=31000, status="Available", region="West"),
    ]
    db.session.add_all(vehicles)
    db.session.commit()


with app.app_context():
    db.create_all()
    seed_default_users()
    seed_ten_vehicles()


@app.route("/")
def index():
    if not is_authenticated():
        return redirect(url_for("login"))
    return redirect(url_for("dashboard"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        # normalize and validate email
        raw_email = request.form.get("email", "").strip()
        email = raw_email.lower()
        password = request.form.get("password", "")
        selected_role = request.form.get("role", "").strip()

        # initialize failed attempts store in session
        failed = session.get("failed_attempts", {})
        attempts = failed.get(email, 0)
        locked_threshold = 5
        if attempts >= locked_threshold:
            return render_template("login.html", error="Account locked after 5 failed attempts.\nPlease contact your administrator.")

        # basic email format check (requires @ and a domain)
        if "@" not in email or "." not in email.split("@")[-1]:
            return render_template("login.html", error="Invalid email format. Please enter a valid email (eg. name@gmail.com)")

        user = User.query.filter_by(email=email).first()
        password_valid = False
        if user:
            password_valid = verify_password(user.password, password)
            # ensure stored passwords are hashed
            if password_valid and not is_hashed_password(user.password):
                user.password = generate_password_hash(password)
                db.session.commit()

        # enforce role match
        if not user or not password_valid or (selected_role and user.role != selected_role):
            # increment failed attempts for this email
            attempts += 1
            failed[email] = attempts
            session["failed_attempts"] = failed
            # locked message if threshold reached
            if attempts >= locked_threshold:
                return render_template("login.html", error="Invalid credentials.\nAccount locked after 5 failed attempts.")
            return render_template("login.html", error=f"Invalid credentials.\nFailed attempts: {attempts} of {locked_threshold}")

        # successful login
        session["user_id"] = user.id
        session["role"] = user.role
        # reset failed attempts for this user
        if email in failed:
            failed.pop(email, None)
            session["failed_attempts"] = failed
        return redirect(url_for("dashboard"))
    return render_template("login.html", error=None)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/dashboard")
def dashboard():
    if not is_authenticated():
        return redirect(url_for("login"))

    # filter params (vehicle_type, status, region)
    vehicle_type = request.args.get("vehicle_type")
    status_filter = request.args.get("status")
    region_filter = request.args.get("region")

    query = Vehicle.query
    if vehicle_type:
        query = query.filter(Vehicle.vehicle_type == vehicle_type)
    if status_filter:
        query = query.filter(Vehicle.status == status_filter)
    if region_filter:
        query = query.filter(Vehicle.region == region_filter)

    vehicles = query.order_by(Vehicle.id.desc()).all()
    # trips and drivers limited to selected vehicles for accurate KPIs
    vehicle_ids = [v.id for v in vehicles]
    trips = Trip.query.filter(Trip.vehicle_id.in_(vehicle_ids)).order_by(Trip.id.desc()).all() if vehicle_ids else []
    drivers = Driver.query.all()
    maintenance_logs = MaintenanceLog.query.filter_by(is_open=True).all()
    fuel_logs = FuelLog.query.all()
    expenses = Expense.query.all()

    # active_vehicles = vehicles currently out on delivery (status == "On Trip")
    active_vehicles = sum(1 for v in vehicles if v.status == "On Trip")
    # available = vehicles explicitly marked Available
    available_vehicles = sum(1 for v in vehicles if v.status == "Available")
    maintenance_vehicles = sum(1 for v in vehicles if v.status == "In Shop")
    active_trips = sum(1 for t in trips if t.state == "Dispatched")
    pending_trips = sum(1 for t in trips if t.state == "Draft")
    # drivers on duty: drivers whose status is "On Trip"
    drivers_on_duty = sum(1 for d in drivers if d.status == "On Trip")
    fleet_utilization = round((active_trips / len(vehicles) * 100) if vehicles else 0, 1)

    chart_data = {
        "statuses": {
            "Available": available_vehicles,
            "In Shop": maintenance_vehicles,
            # On Trip should reflect active_vehicles (vehicles currently out on delivery)
            "On Trip": active_vehicles,
        },
        "regions": {
            "North": sum(1 for v in vehicles if v.region == "North"),
            "South": sum(1 for v in vehicles if v.region == "South"),
            "West": sum(1 for v in vehicles if v.region == "West"),
        },
    }

    # used for populating filter dropdowns
    all_types = sorted({v.vehicle_type for v in Vehicle.query.all()})
    all_statuses = sorted({v.status for v in Vehicle.query.all()})
    all_regions = sorted({v.region for v in Vehicle.query.all()})

    return render_template(
        "dashboard.html",
        vehicles=vehicles,
        drivers=drivers,
        trips=trips,
        maintenance_logs=maintenance_logs,
        fuel_logs=fuel_logs,
        expenses=expenses,
        chart_data=chart_data,
        kpis={
            "active_vehicles": active_vehicles,
            "available_vehicles": available_vehicles,
            "maintenance_vehicles": maintenance_vehicles,
            "active_trips": active_trips,
            "pending_trips": pending_trips,
            "drivers_on_duty": drivers_on_duty,
            "fleet_utilization": fleet_utilization,
        },
        filters={"vehicle_type": vehicle_type or "", "status": status_filter or "", "region": region_filter or ""},
        filter_options={"types": all_types, "statuses": all_statuses, "regions": all_regions},
    )


@app.route('/api/kpis')
def api_kpis():
    if not is_authenticated():
        return jsonify({'error': 'unauthorized'}), 401

    vehicle_type = request.args.get("vehicle_type")
    status_filter = request.args.get("status")
    region_filter = request.args.get("region")

    query = Vehicle.query
    if vehicle_type:
        query = query.filter(Vehicle.vehicle_type == vehicle_type)
    if status_filter:
        query = query.filter(Vehicle.status == status_filter)
    if region_filter:
        query = query.filter(Vehicle.region == region_filter)

    vehicles = query.all()
    vehicle_ids = [v.id for v in vehicles]
    trips = Trip.query.filter(Trip.vehicle_id.in_(vehicle_ids)).all() if vehicle_ids else []

    # active_vehicles = vehicles currently out on delivery (status == "On Trip")
    active_vehicles = sum(1 for v in vehicles if v.status == "On Trip")
    available_vehicles = sum(1 for v in vehicles if v.status == "Available")
    maintenance_vehicles = sum(1 for v in vehicles if v.status == "In Shop")
    active_trips = sum(1 for t in trips if t.state == "Dispatched")
    pending_trips = sum(1 for t in trips if t.state == "Draft")
    # drivers_on_duty should reflect drivers whose status is "On Trip"
    drivers = Driver.query.all()
    drivers_on_duty = sum(1 for d in drivers if d.status == "On Trip")
    fleet_utilization = round((active_trips / len(vehicles) * 100) if vehicles else 0, 1)

    chart_data = {
        "statuses": {
            "Available": available_vehicles,
            "In Shop": maintenance_vehicles,
            "On Trip": active_vehicles,
        },
        "regions": {
            "North": sum(1 for v in vehicles if v.region == "North"),
            "South": sum(1 for v in vehicles if v.region == "South"),
            "West": sum(1 for v in vehicles if v.region == "West"),
        },
    }

    return jsonify({
        'kpis': {
            'active_vehicles': active_vehicles,
            'available_vehicles': available_vehicles,
            'maintenance_vehicles': maintenance_vehicles,
            'active_trips': active_trips,
            'pending_trips': pending_trips,
            'drivers_on_duty': drivers_on_duty,
            'fleet_utilization': fleet_utilization,
        },
        'chart_data': chart_data,
    })


@app.route("/vehicles", methods=["GET", "POST"])
def vehicles():
    if not is_authenticated():
        return redirect(url_for("login"))
    if not has_role(["Fleet Manager", "Safety Officer"]):
        return ("Forbidden", 403)
    if request.method == "POST":
        # server-side validation
        reg = request.form.get("registration_number", "").strip()
        name = request.form.get("name", "").strip()
        vtype = request.form.get("vehicle_type", "").strip()
        try:
            capacity = float(request.form.get("max_load_capacity", 0))
        except Exception:
            capacity = None
        try:
            odometer = float(request.form.get("odometer", 0))
        except Exception:
            odometer = 0
        try:
            acq = float(request.form.get("acquisition_cost", 0))
        except Exception:
            acq = 0
        status = request.form.get("status", "Available").strip()
        region = request.form.get("region", "North").strip()
        notes = request.form.get("notes", "")

        errors = []
        if not reg:
            errors.append("Registration number is required.")
        if not name:
            errors.append("Vehicle name/model is required.")
        if not vtype:
            errors.append("Vehicle type is required.")
        if capacity is None:
            errors.append("Max load capacity must be a number.")
        if status not in ALLOWED_VEHICLE_STATUSES:
            errors.append(f"Invalid status. Allowed: {', '.join(ALLOWED_VEHICLE_STATUSES)}")

        # uniqueness check
        if reg and Vehicle.query.filter_by(registration_number=reg).first():
            errors.append("Registration number already exists.")

        if errors:
            return render_template("vehicles.html", vehicles=Vehicle.query.order_by(Vehicle.id.desc()).all(), vehicle_to_edit=None, filters={"q": "", "status": "", "region": "", "sort": "id"}, error="\n".join(errors))

        vehicle = Vehicle(
            registration_number=reg,
            name=name,
            vehicle_type=vtype,
            max_load_capacity=capacity,
            odometer=odometer,
            acquisition_cost=acq,
            status=status,
            region=region,
            notes=notes,
        )
        db.session.add(vehicle)
        db.session.commit()
        return redirect(url_for("vehicles"))
    query = Vehicle.query
    search_query = request.args.get("q", "")
    status_filter = request.args.get("status")
    region_filter = request.args.get("region")
    sort_by = request.args.get("sort", "id")
    edit_id = request.args.get("edit_id", type=int)
    if search_query:
        query = query.filter(or_(Vehicle.name.ilike(f"%{search_query}%"), Vehicle.registration_number.ilike(f"%{search_query}%")))
    if status_filter:
        query = query.filter(Vehicle.status == status_filter)
    if region_filter:
        query = query.filter(Vehicle.region == region_filter)
    if sort_by == "capacity":
        query = query.order_by(Vehicle.max_load_capacity.desc())
    elif sort_by == "status":
        query = query.order_by(Vehicle.status)
    else:
        query = query.order_by(Vehicle.id.desc())

    vehicle_to_edit = Vehicle.query.get(edit_id) if edit_id else None
    return render_template(
        "vehicles.html",
        vehicles=query.all(),
        vehicle_to_edit=vehicle_to_edit,
        filters={"q": search_query, "status": status_filter or "", "region": region_filter or "", "sort": sort_by},
    )


@app.route("/vehicles/<int:vehicle_id>/edit", methods=["POST"])
def edit_vehicle(vehicle_id):
    if not is_authenticated():
        return redirect(url_for("login"))
    if not has_role(["Fleet Manager", "Safety Officer"]):
        return ("Forbidden", 403)
    vehicle = Vehicle.query.get_or_404(vehicle_id)
    # If the edit form was submitted with no fields, treat as no-op and redirect
    if not request.form:
        return redirect(url_for("vehicles"))
    # validate edits
    reg = request.form.get("registration_number", "").strip()
    name = request.form.get("name", "").strip()
    vtype = request.form.get("vehicle_type", "").strip()
    try:
        capacity = float(request.form.get("max_load_capacity", 0))
    except Exception:
        capacity = None
    try:
        odometer = float(request.form.get("odometer", vehicle.odometer))
    except Exception:
        odometer = vehicle.odometer
    try:
        acq = float(request.form.get("acquisition_cost", vehicle.acquisition_cost))
    except Exception:
        acq = vehicle.acquisition_cost
    status = request.form.get("status", vehicle.status).strip()
    region = request.form.get("region", vehicle.region).strip()
    notes = request.form.get("notes", vehicle.notes)

    errors = []
    if not reg:
        errors.append("Registration number is required.")
    if not name:
        errors.append("Vehicle name/model is required.")
    if not vtype:
        errors.append("Vehicle type is required.")
    if capacity is None:
        errors.append("Max load capacity must be a number.")
    if status not in ALLOWED_VEHICLE_STATUSES:
        errors.append(f"Invalid status. Allowed: {', '.join(ALLOWED_VEHICLE_STATUSES)}")

    # uniqueness check (exclude current vehicle)
    existing = Vehicle.query.filter_by(registration_number=reg).first()
    if existing and existing.id != vehicle.id:
        errors.append("Registration number already exists.")

    if errors:
        return render_template("vehicles.html", vehicles=Vehicle.query.order_by(Vehicle.id.desc()).all(), vehicle_to_edit=vehicle, filters={"q": "", "status": "", "region": "", "sort": "id"}, error="\n".join(errors))

    vehicle.registration_number = reg
    vehicle.name = name
    vehicle.vehicle_type = vtype
    vehicle.max_load_capacity = capacity
    vehicle.odometer = odometer
    vehicle.acquisition_cost = acq
    vehicle.status = status
    vehicle.region = region
    vehicle.notes = notes

    db.session.commit()
    return redirect(url_for("vehicles"))


@app.route("/vehicles/<int:vehicle_id>/delete", methods=["POST"])
def delete_vehicle(vehicle_id):
    if not is_authenticated():
        return redirect(url_for("login"))
    if not has_role(["Fleet Manager", "Safety Officer"]):
        return ("Forbidden", 403)
    vehicle = Vehicle.query.get_or_404(vehicle_id)
    db.session.delete(vehicle)
    db.session.commit()
    return redirect(url_for("vehicles"))


@app.route("/api/vehicles", methods=["GET", "POST"])
def api_vehicles():
    if not is_authenticated():
        return jsonify({"error": "unauthorized"}), 401
    if request.method == "POST":
        vehicle = Vehicle(
            registration_number=request.json.get("registration_number"),
            name=request.json.get("name"),
            vehicle_type=request.json.get("vehicle_type"),
            max_load_capacity=float(request.json.get("max_load_capacity", 0)),
            odometer=float(request.json.get("odometer", 0)),
            acquisition_cost=float(request.json.get("acquisition_cost", 0)),
            status=request.json.get("status", "Available"),
            region=request.json.get("region", "North"),
            notes=request.json.get("notes", ""),
        )
        db.session.add(vehicle)
        db.session.commit()
        return jsonify(vehicle.as_dict()), 201
    vehicles = Vehicle.query.order_by(Vehicle.id.desc()).all()
    return jsonify([vehicle.as_dict() for vehicle in vehicles])


@app.route("/api/drivers", methods=["GET", "POST"])
def api_drivers():
    if not is_authenticated():
        return jsonify({"error": "unauthorized"}), 401
    if request.method == "POST":
        driver = Driver(
            name=request.json.get("name"),
            license_number=request.json.get("license_number"),
            license_category=request.json.get("license_category", "B"),
            license_expiry=date.fromisoformat(request.json.get("license_expiry")),
            contact_number=request.json.get("contact_number"),
            safety_score=float(request.json.get("safety_score", 90)),
            status=request.json.get("status", "Available"),
            region=request.json.get("region", "North"),
            notes=request.json.get("notes", ""),
        )
        db.session.add(driver)
        db.session.commit()
        return jsonify({"id": driver.id, "name": driver.name, "license_number": driver.license_number}), 201
    drivers = Driver.query.order_by(Driver.id.desc()).all()
    return jsonify([{"id": d.id, "name": d.name, "license_number": d.license_number, "status": d.status} for d in drivers])


@app.route("/drivers", methods=["GET", "POST"])
def drivers():
    if not is_authenticated():
        return redirect(url_for("login"))
    if not has_role(["Fleet Manager", "Safety Officer"]):
        return ("Forbidden", 403)
    if request.method == "POST":
        driver = Driver(
            name=request.form["name"],
            license_number=request.form["license_number"],
            license_category=request.form.get("license_category", "B"),
            license_expiry=date.fromisoformat(request.form["license_expiry"]),
            contact_number=request.form["contact_number"],
            safety_score=float(request.form.get("safety_score", 90)),
            status=request.form.get("status", "Available"),
            region=request.form.get("region", "North"),
            notes=request.form.get("notes", ""),
        )
        db.session.add(driver)
        db.session.commit()
        return redirect(url_for("drivers"))
    query = Driver.query
    search_query = request.args.get("q", "")
    status_filter = request.args.get("status")
    sort_by = request.args.get("sort", "id")
    if search_query:
        query = query.filter(or_(Driver.name.ilike(f"%{search_query}%"), Driver.license_number.ilike(f"%{search_query}%")))
    if status_filter:
        query = query.filter(Driver.status == status_filter)
    if sort_by == "safety":
        query = query.order_by(Driver.safety_score.desc())
    else:
        query = query.order_by(Driver.id.desc())
    return render_template("drivers.html", drivers=query.all(), filters={"q": search_query, "status": status_filter or "", "sort": sort_by})


@app.route("/drivers/<int:driver_id>/edit", methods=["POST"])
def edit_driver(driver_id):
    if not is_authenticated():
        return redirect(url_for("login"))
    if not has_role(["Fleet Manager", "Safety Officer"]):
        return ("Forbidden", 403)
    driver = Driver.query.get_or_404(driver_id)
    driver.name = request.form["name"]
    driver.license_number = request.form["license_number"]
    driver.license_category = request.form.get("license_category", "B")
    driver.license_expiry = date.fromisoformat(request.form["license_expiry"])
    driver.contact_number = request.form["contact_number"]
    driver.safety_score = float(request.form.get("safety_score", 90))
    driver.status = request.form.get("status", "Available")
    driver.region = request.form.get("region", "North")
    driver.notes = request.form.get("notes", "")
    db.session.commit()
    return redirect(url_for("drivers"))


@app.route("/drivers/<int:driver_id>/delete", methods=["POST"])
def delete_driver(driver_id):
    if not is_authenticated():
        return redirect(url_for("login"))
    if not has_role(["Fleet Manager", "Safety Officer"]):
        return ("Forbidden", 403)
    driver = Driver.query.get_or_404(driver_id)
    db.session.delete(driver)
    db.session.commit()
    return redirect(url_for("drivers"))


@app.route("/trips", methods=["GET", "POST"])
def trips():
    if not is_authenticated():
        return redirect(url_for("login"))
    if not has_role(["Fleet Manager", "Driver"]):
        return ("Forbidden", 403)
    if request.method == "POST":
        vehicle = Vehicle.query.get(int(request.form["vehicle_id"]))
        driver = Driver.query.get(int(request.form["driver_id"]))
        errors = validate_trip_assignment(vehicle, driver, float(request.form["cargo_weight"]))
        if errors:
            return render_template("trips.html", vehicles=Vehicle.query.filter_by(status="Available").all(), drivers=Driver.query.filter_by(status="Available").all(), trips=Trip.query.all(), errors=errors)
        trip = Trip(
            source=request.form["source"],
            destination=request.form["destination"],
            cargo_weight=float(request.form["cargo_weight"]),
            planned_distance=float(request.form["planned_distance"]),
            state="Draft",
            vehicle_id=vehicle.id,
            driver_id=driver.id,
        )
        db.session.add(trip)
        db.session.commit()
        return redirect(url_for("trips"))
    return render_template("trips.html", vehicles=Vehicle.query.filter_by(status="Available").all(), drivers=Driver.query.filter_by(status="Available").all(), trips=Trip.query.all(), errors=[])


@app.route("/trips/<int:trip_id>/dispatch", methods=["POST"])
def dispatch_trip(trip_id):
    trip = Trip.query.get_or_404(trip_id)
    vehicle = Vehicle.query.get(trip.vehicle_id)
    driver = Driver.query.get(trip.driver_id)
    errors = validate_trip_assignment(vehicle, driver, trip.cargo_weight)
    if errors:
        return jsonify({"success": False, "errors": errors}), 400
    trip.state = "Dispatched"
    vehicle.status, driver.status = apply_trip_state("Dispatched")
    db.session.commit()
    return jsonify({"success": True})


@app.route("/trips/<int:trip_id>/complete", methods=["POST"])
def complete_trip(trip_id):
    trip = Trip.query.get_or_404(trip_id)
    vehicle = Vehicle.query.get(trip.vehicle_id)
    driver = Driver.query.get(trip.driver_id)
    trip.state = "Completed"
    vehicle.status, driver.status = apply_trip_state("Completed")
    vehicle.odometer = float(request.form.get("final_odometer", vehicle.odometer))
    trip.final_odometer = vehicle.odometer
    trip.fuel_consumed = float(request.form.get("fuel_consumed", trip.fuel_consumed))
    db.session.add(FuelLog(vehicle_id=vehicle.id, liters=trip.fuel_consumed, cost=float(request.form.get("fuel_cost", 0)), logged_at=date.today()))
    db.session.commit()
    return jsonify({"success": True})


@app.route("/trips/<int:trip_id>/cancel", methods=["POST"])
def cancel_trip(trip_id):
    trip = Trip.query.get_or_404(trip_id)
    vehicle = Vehicle.query.get(trip.vehicle_id)
    driver = Driver.query.get(trip.driver_id)
    trip.state = "Cancelled"
    vehicle.status, driver.status = apply_trip_state("Cancelled")
    db.session.commit()
    return jsonify({"success": True})


@app.route("/maintenance", methods=["GET", "POST"])
def maintenance():
    if not is_authenticated():
        return redirect(url_for("login"))
    if not has_role(["Fleet Manager", "Safety Officer"]):
        return ("Forbidden", 403)
    if request.method == "POST":
        vehicle = Vehicle.query.get(int(request.form["vehicle_id"]))
        maintenance = MaintenanceLog(vehicle_id=vehicle.id, description=request.form["description"], cost=float(request.form.get("cost", 0)))
        db.session.add(maintenance)
        vehicle.status = "In Shop"
        db.session.commit()
        return redirect(url_for("maintenance"))
    return render_template("maintenance.html", vehicles=Vehicle.query.all(), maintenance_logs=MaintenanceLog.query.all())


@app.route("/maintenance/<int:maintenance_id>/close", methods=["POST"])
def close_maintenance(maintenance_id):
    maintenance = MaintenanceLog.query.get_or_404(maintenance_id)
    vehicle = Vehicle.query.get(maintenance.vehicle_id)
    maintenance.is_open = False
    maintenance.closed_at = datetime.utcnow()
    vehicle.status = apply_maintenance_close(vehicle.status)
    db.session.commit()
    return jsonify({"success": True})


@app.route("/expenses", methods=["GET", "POST"])
def expenses():
    if not is_authenticated():
        return redirect(url_for("login"))
    if not has_role(["Fleet Manager", "Financial Analyst"]):
        return ("Forbidden", 403)
    if request.method == "POST":
        db.session.add(Expense(vehicle_id=int(request.form["vehicle_id"]), description=request.form["description"], amount=float(request.form["amount"])))
        db.session.commit()
        return redirect(url_for("expenses"))
    return render_template("expenses.html", vehicles=Vehicle.query.all(), expenses=Expense.query.all())


@app.route("/reports")
def reports():
    if not is_authenticated():
        return redirect(url_for("login"))
    if not has_role(["Fleet Manager", "Financial Analyst", "Safety Officer"]):
        return ("Forbidden", 403)
    vehicles = Vehicle.query.all()
    report_rows = []
    for vehicle in vehicles:
        fuel_logs = FuelLog.query.filter_by(vehicle_id=vehicle.id).all()
        expenses = Expense.query.filter_by(vehicle_id=vehicle.id).all()
        maintenance_logs = MaintenanceLog.query.filter_by(vehicle_id=vehicle.id).all()
        completed_trips = Trip.query.filter_by(vehicle_id=vehicle.id, state="Completed").all()
        fuel_total = sum(log.cost for log in fuel_logs)
        maintenance_total = sum(log.cost for log in maintenance_logs)
        total_revenue = sum(trip.revenue for trip in completed_trips)
        total_cost = fuel_total + maintenance_total + sum(exp.amount for exp in expenses)
        distance = vehicle.odometer
        fuel_efficiency = round(distance / sum(log.liters for log in fuel_logs), 2) if sum(log.liters for log in fuel_logs) else 0
        roi = round((total_revenue - (maintenance_total + fuel_total)) / vehicle.acquisition_cost, 2) if vehicle.acquisition_cost else 0
        report_rows.append({
            "vehicle": vehicle,
            "fuel_efficiency": fuel_efficiency,
            "operational_cost": total_cost,
            "roi": roi,
        })
    reminder_candidates = []
    for driver in Driver.query.all():
        if driver.license_expiry and (driver.license_expiry - date.today()).days <= 30:
            reminder_candidates.append(driver)
    return render_template("reports.html", report_rows=report_rows, reminders=reminder_candidates)


@app.route("/reminders/send")
def send_reminders():
    if not is_authenticated():
        return redirect(url_for("login"))
    sent = []
    smtp_server = os.getenv("SMTP_SERVER")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_username = os.getenv("SMTP_USERNAME")
    smtp_password = os.getenv("SMTP_PASSWORD")
    sender_email = os.getenv("SENDER_EMAIL", "transitops@example.com")
    for driver in Driver.query.all():
        if driver.license_expiry and (driver.license_expiry - date.today()).days <= 30:
            message = f"Reminder: {driver.name} license expires on {driver.license_expiry}."
            sent.append(message)
            if smtp_server and smtp_username and smtp_password:
                try:
                    msg = EmailMessage()
                    msg["Subject"] = "TransitOps License Reminder"
                    msg["From"] = sender_email
                    msg["To"] = driver.contact_number if "@" not in driver.contact_number else driver.contact_number
                    msg.set_content(message)
                    with smtplib.SMTP(smtp_server, smtp_port) as smtp:
                        smtp.starttls()
                        smtp.login(smtp_username, smtp_password)
                        smtp.send_message(msg)
                except Exception as exc:
                    sent.append(str(exc))
    return jsonify({"sent": sent})


@app.route("/export/csv")
def export_csv():
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["Vehicle", "Fuel Efficiency", "Operational Cost", "ROI"])
    vehicles = Vehicle.query.all()
    for vehicle in vehicles:
        fuel_logs = FuelLog.query.filter_by(vehicle_id=vehicle.id).all()
        expenses = Expense.query.filter_by(vehicle_id=vehicle.id).all()
        maintenance_logs = MaintenanceLog.query.filter_by(vehicle_id=vehicle.id).all()
        completed_trips = Trip.query.filter_by(vehicle_id=vehicle.id, state="Completed").all()
        fuel_total = sum(log.cost for log in fuel_logs)
        maintenance_total = sum(log.cost for log in maintenance_logs)
        total_revenue = sum(trip.revenue for trip in completed_trips)
        total_cost = fuel_total + maintenance_total + sum(exp.amount for exp in expenses)
        distance = vehicle.odometer
        fuel_efficiency = round(distance / sum(log.liters for log in fuel_logs), 2) if sum(log.liters for log in fuel_logs) else 0
        roi = round((total_revenue - (maintenance_total + fuel_total)) / vehicle.acquisition_cost, 2) if vehicle.acquisition_cost else 0
        writer.writerow([vehicle.name, fuel_efficiency, total_cost, roi])
    csv_data = output.getvalue()
    return send_file(
        io.BytesIO(csv_data.encode("utf-8")),
        mimetype="text/csv",
        as_attachment=True,
        download_name="transitops-report.csv",
    )


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


def is_authenticated():
    return "user_id" in session


def has_role(allowed_roles):
    return session.get("role") in allowed_roles


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
