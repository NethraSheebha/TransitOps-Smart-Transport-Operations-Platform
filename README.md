# TransitOps: Smart Transport Operations Platform

TransitOps is an end-to-end transport operations and fleet management platform built to digitize vehicle logs, driver management, trip dispatch workflows, maintenance tracking, and financial insights. It replaces archaic spreadsheets with an automated system that strictly enforces logistics business rules in real-time.

---

## 🚀 Key Features

The platform features a fully responsive, modern **Glassmorphic UI Design System** equipped with:
*   **Dual Theme Engine:** LocalStorage-persistent Dark and Light modes synced across all viewports.
*   **Unified Navigation:** Persistent sidebar layout with active state indicators and collapsible mobile hamburger menu support.
*   **Real-Time Data Display:** Dynamic KPI metric cards, interactive status badges, and data visualization using Chart.js.
*   **Secure Authentication:** Role-Based Access Control (RBAC) supporting custom dashboards/actions tailored to specific fleet personas.

---

## 👤 Target User Personas & RBAC

*   **Fleet Manager:** Oversees full fleet assets, logs maintenance cycles, and manages asset lifecycle states.
*   **Driver:** Views assigned dispatches, executes lifecycle movements (Draft → Dispatched → Completed/Cancelled).
*   **Safety Officer:** Monitors driver behavior compliance scores, tracks driver license expiry parameters, and reviews system logs.
*   **Financial Analyst:** Evaluates operational fuel consumption metrics, tracks outstanding toll expenses, and monitors asset-specific ROI.

---

## 🏗️ System Architecture & Data Models

The platform relies on an architectural backend powered by **Flask** and **SQLAlchemy (SQLite)** mapping the following essential business entities:

<img width="1408" height="768" alt="Gemini_Generated_Image_9qqq8h9qqq8h9qqq" src="https://github.com/user-attachments/assets/77f50a3a-dff8-4aa0-8e2c-870925b0eb69" />


*   **User:** ID, Email, Hashed Password, Role.
*   **Vehicle:** Registration Number (Unique), Model Name, Type, Max Load Capacity, Odometer, Acquisition Cost, Operational Status, Region, Notes.
*   **Driver:** Name, License Number (Unique), License Category, Expiry Date, Contact Number, Safety Score, Status, Region.
*   **Trip:** Source, Destination, Cargo Weight, Planned Distance, State, Vehicle Link, Driver Link, Fuel Consumed, Revenue, Final Odometer.
*   **MaintenanceLog:** Vehicle Link, Service Description, Logged Costs, Timestamps (Opened/Closed), Status Boolean.
*   **FuelLog & Expense:** Vehicle Link, Aggregated Quantities/Amounts, Logs Timestamping.

---

## 🗄️ Database Architecture & Usage

TransitOps uses an **SQLite** database (`transitops.db`) managed through **Flask-SQLAlchemy** to enforce strict data constraints, map entities, and power the platform's analytical layers[cite: 1].

---

### 📋 Detailed Entity Schema

<img width="1536" height="1024" alt="ChatGPT Image Jul 12, 2026, 04_59_28 PM" src="https://github.com/user-attachments/assets/f2ed2179-cba8-43e3-9525-1422b61185b4" />



#### 1. `user` Table
Manages secure system authentication and Role-Based Access Control (RBAC) scopes.
*   **`id`** *(Integer, Primary Key)*: Unique identifier for each system user.
*   **`email`** *(String, Unique, Nullable=False)*: User authentication login identifier.
*   **`password`** *(String, Nullable=False)*: Salted and cryptographically hashed credentials using `scrypt` or `pbkdf2` algorithms.
*   **`role`** *(String, Default="Fleet Manager")*: Persona designation defining operational permissions (`Fleet Manager`, `Driver`, `Safety Officer`, or `Financial Analyst`).

#### 2. `vehicle` Table
Acts as the central asset registry tracking physical asset configurations and real-time operational availability.
*   **`id`** *(Integer, Primary Key)*: Unique tracking ID.
*   **`registration_number`** *(String, Unique, Nullable=False)*: Mandatory unique license plate or identification string.
*   **`name`** *(String, Nullable=False)*: Make and model of the vehicle.
*   **`vehicle_type`** *(String, Nullable=False)*: Classification category (e.g., `Van`, `Box Truck`, `Heavy Truck`).
*   **`max_load_capacity`** *(Float, Nullable=False)*: Maximum structural cargo weight payload threshold utilized for validation triggers.
*   **`odometer`** *(Float, Default=0)*: Cumulative physical mileage, automatically aggregated upon successful trip completion.
*   **`acquisition_cost`** *(Float, Default=0)*: Base procurement price utilized to evaluate life-cycle Return on Investment (ROI).
*   **`status`** *(String, Default="Available")*: State-machine restricted values: `Available`, `On Trip`, `In Shop`, or `Retired`.
*   **`region`** *(String, Default="North")*: Regional sorting bucket used for dashboard localization filters.
*   **`notes`** *(Text, Default="")*: Fleet manager remarks and operational history tracking.

#### 3. `driver` Table
Stores operator profiles, license compliance status, and safety metrics.
*   **`id`** *(Integer, Primary Key)*: Unique operator identifier.
*   **`name`** *(String, Nullable=False)*: Full legal name of the operator.
*   **`license_number`** *(String, Unique, Nullable=False)*: Unique driver authorization document number.
*   **`license_category`** *(String, Default="B")*: Classification level defining vehicle operation authorizations.
*   **`license_expiry`** *(Date, Nullable=False)*: License expiry date used to check validity during dispatch routines.
*   **`contact_number`** *(String, Nullable=False)*: Phone number or communication link.
*   **`safety_score`** *(Float, Default=90)*: Numerical driving score audited by the Safety Officer.
*   **`status`** *(String, Default="Available")*: Restricted pipeline states: `Available`, `On Trip`, `Off Duty`, or `Suspended`.
*   **`region`** *(String, Default="North")*: Geographic operational base assignment.
*   **`notes`** *(Text, Default="")*: Notes concerning compliance anomalies or safety citations.

#### 4. `trip` Table
Tracks transit lifecycle milestones, capacity parameters, and asset link associations.
*   **`id`** *(Integer, Primary Key)*: Unique tracking ID.
*   **`source`** *(String, Nullable=False)*: Origin dispatch terminal.
*   **`destination`** *(String, Nullable=False)*: Target delivery terminal.
*   **`cargo_weight`** *(Float, Nullable=False)*: Absolute payload weight evaluated against vehicle structural capacities.
*   **`planned_distance`** *(Float, Nullable=False)*: Estimated point-to-point mileage metrics.
*   **`state`** *(String, Default="Draft")*: Workflow status sequence: `Draft`, `Dispatched`, `Completed`, or `Cancelled`.
*   **`vehicle_id`** *(Integer, Foreign Key $\rightarrow$ `vehicle.id`)*: Linked operational equipment profile.
*   **`driver_id`** *(Integer, Foreign Key $\rightarrow$ `driver.id`)*: Linked vehicle operator profile.
*   **`fuel_consumed`** *(Float, Default=0)*: Cumulative metric logged dynamically when completing dispatches.
*   **`final_odometer`** *(Float, Default=0)*: Mileage snapshot captured upon arrival.

#### 5. `maintenance_log` Table
Tracks repair orders, scheduled checkups, and direct technical resource costs.
*   **`id`** *(Integer, Primary Key)*: Maintenance entry tracking number.
*   **`vehicle_id`** *(Integer, Foreign Key $\rightarrow$ `vehicle.id`, Nullable=False)*: Reference pointing directly to the asset under repair.
*   **`description`** *(String, Nullable=False)*: System diagnostic or task breakdown (e.g., "Oil Change").
*   **`cost`** *(Float, Default=0)*: Hard financial layout billed per maintenance event.
*   **`created_at`** *(DateTime, Default=UTCnow)*: Ticket creation and intake window snapshot.
*   **`closed_at`** *(DateTime, Nullable)*: Work order resolution timestamp.
*   **`is_open`** *(Boolean, Default=True)*: Boolean indicating whether the asset is currently localized in an inoperative workshop loop.

#### 6. `fuel_log` Table
Records precise fueling metrics crucial for auditing consumption metrics and running performance analytics.
*   **`id`** *(Integer, Primary Key)*: Unique log entry.
*   **`vehicle_id`** *(Integer, Foreign Key $\rightarrow$ `vehicle.id`, Nullable=False)*: Linked vehicular target.
*   **`liters`** *(Float, Nullable=False)*: Total volume of fuel injected.
*   **`cost`** *(Float, Nullable=False)*: Gross expenditure per fill-up event.
*   **`logged_at`** *(Date, Default=Today)*: Calendar entry capturing transaction occurrence.

#### 7. `expense` Table
Logs incidental overhead expenditures such as toll routes or structural insurance penalties.
*   **`id`** *(Integer, Primary Key)*: Ledger row item marker.
*   **`vehicle_id`** *(Integer, Foreign Key $\rightarrow$ `vehicle.id`, Nullable=False)*: Target asset account.
*   **`description`** *(String, Nullable=False)*: Detailed statement outlining line-item causes.
*   **`amount`** *(Float, Nullable=False)*: Total transaction liability.
*   **`logged_at`** *(Date, Default=Today)*: Day transaction was finalized.

---

### 🔄 Dynamic Cross-Table Operations

The core application implements strict query constraints across relational tables to ensure database state transformations align with operational policies:

1. **Transactional Dispatches:** Moving a `trip.state` record to `Dispatched` executes an immediate state transition across the database, shifting the designated `vehicle.status` and `driver.status` indices to `On Trip`.
2. **Lifecycle Resolution:** Finalizing or canceling a dispatch frees up the associated relational IDs, rolling back both asset records back to an `Available` pooling pool.
3. **Maintenance Isolation:** Activating a new `maintenance_log` entry locks the target `vehicle.status` field to `In Shop`. While this flag is active, dynamic filtering in selection queries prevents the vehicle from being loaded onto dispatch selection pages.
4. **Analytical Aggregations:** When the `/reports` pipeline is requested, the system runs programmatic aggregations across the relational tables, calculating total operating cost and efficiency by matching vehicle records with their corresponding fuel, expense, and maintenance entries.

## 🔒 Implemented Business Logic Rules

The application uses a strict state-machine validation layer to guarantee operational integrity:

1.  **Unique Registry Constraint:** Vehicle registration numbers and driver license profiles are explicitly unique.
2.  **Dispatch Pool Filtering:** Vehicles with `In Shop` or `Retired` statuses, as well as drivers with `Suspended` status or an expired license, are automatically filtered out of active dispatch selection pools.
3.  **Concurrency Protections:** Assets or drivers currently flagged as `On Trip` cannot be assigned to another parallel trip.
4.  **Capacity Validation:** Trips cannot be saved if the Cargo Weight exceeds the selected vehicle's Maximum Load Capacity.
5.  **State Transitions Lifecycle:**
    *   *Dispatching a Trip:* Updates both Vehicle and Driver statuses instantly to `On Trip`.
    *   *Completing/Cancelling a Trip:* Automatically rolls back linked Vehicle and Driver statuses to `Available`.
    *   *Opening Maintenance:* Forcing a vehicle record into an active maintenance shop switches its status to `In Shop`.
    *   *Closing Maintenance:* Restores asset availability status to `Available` (unless manually flagged as `Retired`).

---

## 📊 Analytics & Reporting Formulations

The reports engine computes operational metrics across the fleet:

*   **Fuel Efficiency:** Calculated dynamically via:
    $$\text{Fuel Efficiency} = \frac{\text{Distance Traveled (Odometer)}}{\text{Total Fuel Consumed (Liters)}}$$
*   **Vehicle ROI:** Tracks real financial lifecycle performance using:
    $$\text{ROI} = \frac{\text{Generated Trip Revenue} - (\text{Maintenance Cost} + \text{Fuel Cost})}{\text{Acquisition Cost}}$$

---

## 🛠️ Installation & Setup

### Prerequisites
*   Python 3.10+
*   Pip environment manager

### Step 1: Clone the repository and navigate to the root directory
```bash
git clone <repository-url>
cd TransitOps-Smart-Transport-Operations-Platform
```

### Step 2: Set up a virtual environment and install requirements
```bash
python -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate
pip install -r requirements.txt
```

### Step 3: Run the Application
```bash
python app.py
```
The application will automatically initialize the database schema, seed default system users, append 10 default test vehicles, and start hosting on http://localhost:5000.

---

## 🧪 Default Authentication Seed Credentials

Use these pre-seeded accounts to explore different Role-Based Access Control paths:

| Email | Password | Assigned Role |
| --- | --- | --- |
| `admin@transitops.com` | `admin123` | Fleet Manager |
| `safety@transitops.com` | `admin123` | Safety Officer |
| `driver@transitops.com` | `admin123` | Driver |
| `finance@transitops.com` | `admin123` | Financial Analyst |
