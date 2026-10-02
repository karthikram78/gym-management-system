# IronPulse Gym Management System 🏋️‍♂️

A modern, responsive, and robust **Gym Management & Administration Web Application** built with **Python 3 Flask**, **MySQL**, and a responsive **Dark Navy Dashboard UI** with **Chart.js** analytics.

Developed to be full-featured and suitable for college final-year or mini-project demonstrations and vivas.

---

## 🌟 Key Features

1. **Secure Admin Authentication**:
   - Session-based authentication with `werkzeug.security` password hashing.
   - Protected routes with a custom `@login_required` decorator.
   - Default master admin credentials included (`admin` / `admin123`).

2. **Executive Real-time Dashboard**:
   - Real-time stat cards: **Total Members**, **Active Members**, **Expired Members**, **Total Trainers**, **Today's Attendance**, and **Monthly Revenue**.
   - **Chart.js Doughnut Chart**: Interactive Membership Status breakdown.
   - **Chart.js Line Chart**: 6-Month Monthly Revenue trends.
   - Recent members and payment transactions tables.
   - Today's live attendance summary banner.

3. **Complete Member Management (CRUD)**:
   - Full CRUD: Add, View, Edit, Delete (with safety confirmations).
   - Dynamic search by name, email, or phone.
   - Multi-filtering by Membership Status (Active, Expired, Pending, Inactive) and Membership Plan.
   - Automatic calculation of membership expiry date based on plan duration.
   - Comprehensive member profile view with active trainer, complete payment ledger, and past attendance logs.

4. **Trainer Management (CRUD)**:
   - Add, Edit, Delete, and Search trainers.
   - Tracks specialization, years of experience, monthly salary compensation, contact details, and joining dates.
   - Dedicated trainer profile showing all currently assigned member clients.

5. **Membership Plans & Packages**:
   - Manage plans: Name, Duration (Months), Pricing (₹), Description, and Status.
   - Pre-configured with standard plans:
     - **Monthly Plan**: 1 Month - ₹1,500
     - **Quarterly Plan**: 3 Months - ₹4,000
     - **Half-Yearly Plan**: 6 Months - ₹7,000
     - **Yearly Plan**: 12 Months - ₹12,000
   - Live counter showing enrolled member count per plan.

6. **Billing & Payment Management**:
   - Record payments via **Cash**, **UPI**, **Credit/Debit Card**, and **Bank Transfer / Net Banking**.
   - Filter by payment method, transaction status, and date.
   - **Printable Tax Invoice Receipt** (`/payments/receipt/<id>`): Formatted with gym branding, member details, transaction reference, and print-optimized CSS (`window.print()`).

7. **Attendance & Check-In Desk**:
   - Daily attendance logging with Member Search, Check-In time, and Check-Out time.
   - Status tracking: **Present**, **Late**, and **Absent**.
   - **Duplicate Attendance Prevention**: Enforces a unique constraint (`member_id` + `attendance_date`) in the database to prevent duplicate entries for the same member on the same day.
   - Date picker to view and manage past or future attendance records.

8. **Comprehensive Reports & Analytics**:
   - 6 specialized reports with date range and status filters:
     1. **Member Roster Report**
     2. **Trainer Performance & Payroll Report**
     3. **Revenue & Collections Report**
     4. **Attendance Activity Report**
     5. **Membership Expiry Watchlist** (Members expiring within 30 days)
     6. **Monthly Revenue Aggregation Report**
   - Single-click print & PDF export for all reports.

9. **Robust Dual-Mode Database Architecture**:
   - Primary: **MySQL 8.0+** with connection pooling (`mysql-connector-python`).
   - Resilient Fallback: If MySQL service is offline or not configured yet, the app gracefully falls back to an embedded SQLite local database with identical seed data so that the app can be immediately tested and demonstrated anywhere without crashing!

---

## 🛠️ Technology Stack

| Layer | Technology |
|---|---|
| **Backend** | Python 3.10+ & Flask 3.x |
| **Database** | MySQL 8.0+ (`mysql-connector-python`) |
| **Authentication** | Flask Session + Werkzeug Security (Scrypt) |
| **Frontend Templates** | Flask Jinja2 Template Inheritance |
| **Styling & Theme** | Custom Vanilla CSS3 (Dark Navy `#0a0f1d`, Glassmorphism, Responsive Grid) |
| **Charts** | Chart.js 4.x (CDN) |
| **Icons** | Font Awesome 6.5 (CDN) |

---

## 📁 Project Structure

```text
gym_management/
│
├── app.py                      # Flask routes and core controllers
├── config.py                   # Environment and database configuration
├── requirements.txt            # Python dependencies
├── README.md                   # Documentation and viva guide
├── .env.example                # Template for environment variables
│
├── database/
│   └── gym_management.sql      # Complete MySQL DDL schema and sample records
│
├── templates/
│   ├── base.html               # Master layout with sidebar and topbar
│   ├── login.html              # Modern dark login page
│   ├── dashboard.html          # Executive analytics dashboard
│   │
│   ├── members/
│   │   ├── members.html        # Member directory, search & filters
│   │   ├── add_member.html     # Member registration form
│   │   ├── edit_member.html    # Member update form
│   │   └── view_member.html    # Detailed member profile
│   │
│   ├── trainers/
│   │   ├── trainers.html       # Trainer directory & stats
│   │   ├── add_trainer.html    # Trainer registration form
│   │   ├── edit_trainer.html   # Trainer update form
│   │   └── view_trainer.html   # Trainer profile & assigned clients
│   │
│   ├── plans/
│   │   ├── plans.html          # Pricing cards & packages
│   │   ├── add_plan.html       # Create new membership plan
│   │   └── edit_plan.html      # Update existing plan
│   │
│   ├── payments/
│   │   ├── payments.html       # Transaction history ledger
│   │   ├── add_payment.html    # Record new payment
│   │   ├── edit_payment.html   # Update payment entry
│   │   └── receipt.html        # Printable invoice receipt
│   │
│   ├── attendance/
│   │   └── attendance.html     # Check-in desk and daily log
│   │
│   └── reports/
│       └── reports.html        # Multi-tab printable reporting suite
│
├── static/
│   ├── css/
│   │   └── style.css           # Dark navy responsive design & print styles
│   └── js/
│       └── script.js           # Chart.js initialization & dynamic UI logic
│
└── utils/
    ├── database.py             # MySQL connector pool and query helpers
    └── helpers.py              # Auth decorators, validators & date utilities
```

---

## 🚀 Setup & Installation Guide

### Step 1: Clone or Navigate to the Project Directory
Open PowerShell or Terminal:
```bash
cd "C:\Users\karthik\Gym Management System"
```

### Step 2: Create and Activate Virtual Environment
```bash
# Windows PowerShell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

*(If execution policy restricts scripts, run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` first)*

### Step 3: Install Required Dependencies
```bash
pip install -r requirements.txt
```

### Step 4: Setup MySQL Database
1. Make sure your MySQL Server or XAMPP MySQL service is running.
2. Log into the MySQL command line client or phpMyAdmin:
   ```bash
   mysql -u root -p
   ```
3. Import the SQL file:
   ```sql
   SOURCE database/gym_management.sql;
   ```
   *(Alternatively, copy and run the contents of `database/gym_management.sql` in MySQL Workbench or phpMyAdmin).*

### Step 5: Configure Credentials
Create a `.env` file in the root directory (or modify `config.py`):
```env
SECRET_KEY=gym_management_super_secret_key_2026
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_mysql_password
MYSQL_DB=gym_management
```

### Step 6: Launch the Application
```bash
python app.py
```

### Step 7: Open in Browser
Open your browser and navigate to:
```text
http://127.0.0.1:5000
```

---

## 🔑 Default Login Credentials

| Role | Username | Password |
|---|---|---|
| **Master Admin** | `admin` | `admin123` |

---

## 🎓 College Viva & Project Presentation Q&A

### Q1: Why did you choose Flask over Django for this project?
**Answer**: Flask is a lightweight micro-framework that provides full control over the application architecture, database connections, and session management. It allows us to explicitly write SQL queries with `mysql-connector-python` rather than relying on an opaque ORM, demonstrating direct knowledge of relational database design, indexing, and parameterized query security.

### Q2: How is SQL Injection prevented in this system?
**Answer**: We use parameterized queries exclusively through `cursor.execute(sql, params)`. User input is passed as separate tuple arguments (`%s` in MySQL) rather than string concatenation or f-strings. The MySQL driver automatically escapes and treats all inputs strictly as literal values.

### Q3: How is duplicate attendance handled?
**Answer**: At the database level, the `attendance` table has a composite unique constraint `UNIQUE KEY (member_id, attendance_date)`. At the application level in `app.py`, the backend checks whether a record already exists for the given member and date before attempting insertion, providing a friendly warning to the administrator.

### Q4: How are passwords stored securely?
**Answer**: Passwords are never stored in plaintext. We utilize `werkzeug.security`'s `scrypt` hashing algorithm with randomized salt. During login, `check_password_hash` calculates the hash of the input and securely verifies it against the database record using constant-time comparison to prevent timing attacks.

### Q5: How does the dashboard stay dynamic?
**Answer**: Every time `/dashboard` is accessed, the Flask backend executes aggregation queries (`COUNT(*)`, `SUM(amount)`, `GROUP BY status`) directly on MySQL. The computed figures are rendered into HTML cards and serialized into JSON datasets consumed by Chart.js.

---

## 📄 License
This project is open-source and intended for academic, college demonstration, and personal gym management purposes.
