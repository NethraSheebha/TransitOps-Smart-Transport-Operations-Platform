# TransitOps: Smart Transport Operations Platform

TransitOps is an end-to-end transport operations and fleet management platform built to digitize vehicle logs, driver management, trip dispatch workflows, maintenance tracking, and financial insights. It replaces archaic spreadsheets with an automated system that strictly enforces logistics business rules in real-time.

---

## 🚀 Key Features & UI Modernization

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

*   **User:** ID, Email, Hashed Password, Role.
*   **Vehicle:** Registration Number (Unique), Model Name, Type, Max Load Capacity, Odometer, Acquisition Cost, Operational Status, Region, Notes.
*   **Driver:** Name, License Number (Unique), License Category, Expiry Date, Contact Number, Safety Score, Status, Region.
*   **Trip:** Source, Destination, Cargo Weight, Planned Distance, State, Vehicle Link, Driver Link, Fuel Consumed, Revenue, Final Odometer.
*   **MaintenanceLog:** Vehicle Link, Service Description, Logged Costs, Timestamps (Opened/Closed), Status Boolean.
*   **FuelLog & Expense:** Vehicle Link, Aggregated Quantities/Amounts, Logs Timestamping.

---

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
