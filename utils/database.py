import os
import re
import sqlite3
from config import Config

# Track active database mode ('mysql' or 'sqlite_fallback')
DB_MODE = 'mysql'
_mysql_pool = None
_sqlite_conn = None

SQLITE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'database', 'gym_management.sqlite')

def get_mysql_pool():
    """Attempts to establish or return the MySQL Connection Pool."""
    global _mysql_pool
    if _mysql_pool is not None:
        return _mysql_pool

    import mysql.connector
    from mysql.connector import Error, pooling

    try:
        _mysql_pool = pooling.MySQLConnectionPool(
            pool_name="gym_pool",
            pool_size=5,
            pool_reset_session=True,
            host=Config.MYSQL_HOST,
            port=Config.MYSQL_PORT,
            user=Config.MYSQL_USER,
            password=Config.MYSQL_PASSWORD,
            database=Config.MYSQL_DB
        )
        return _mysql_pool
    except Error as e:
        if e.errno == 1049:  # ER_BAD_DB_ERROR: database doesn't exist yet
            try:
                temp_conn = mysql.connector.connect(
                    host=Config.MYSQL_HOST,
                    port=Config.MYSQL_PORT,
                    user=Config.MYSQL_USER,
                    password=Config.MYSQL_PASSWORD
                )
                temp_cursor = temp_conn.cursor()
                temp_cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{Config.MYSQL_DB}` CHARACTER SET utf8mb4;")
                temp_conn.commit()
                temp_cursor.close()
                temp_conn.close()

                _mysql_pool = pooling.MySQLConnectionPool(
                    pool_name="gym_pool",
                    pool_size=5,
                    pool_reset_session=True,
                    host=Config.MYSQL_HOST,
                    port=Config.MYSQL_PORT,
                    user=Config.MYSQL_USER,
                    password=Config.MYSQL_PASSWORD,
                    database=Config.MYSQL_DB
                )
                return _mysql_pool
            except Exception as ex:
                raise ex
        raise e

import socket

_mysql_checked = False
_mysql_available = False

def is_mysql_available():
    """Tests if MySQL Server is reachable on port 3306 using ultra-fast socket probe."""
    global _mysql_checked, _mysql_available
    if _mysql_checked:
        return _mysql_available
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.3)
        host = '127.0.0.1' if Config.MYSQL_HOST in ['localhost', '127.0.0.1'] else Config.MYSQL_HOST
        s.connect((host, Config.MYSQL_PORT))
        s.close()
        _mysql_available = True
    except Exception:
        _mysql_available = False
    _mysql_checked = True
    return _mysql_available

def get_db_connection():
    """
    Returns an active database connection.
    Attempts MySQL first; falls back to embedded SQLite if MySQL server is not running.
    """
    global DB_MODE
    if is_mysql_available():
        try:
            pool = get_mysql_pool()
            conn = pool.get_connection()
            DB_MODE = 'mysql'
            return conn
        except Exception:
            pass

    # Fallback to local SQLite if MySQL is offline
    DB_MODE = 'sqlite_fallback'
    os.makedirs(os.path.dirname(SQLITE_PATH), exist_ok=True)
    conn = sqlite3.connect(SQLITE_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn

def adapt_query_for_sqlite(query):
    """Translates common MySQL dialect syntax to SQLite for the local fallback."""
    q = query
    # Replace parameter placeholder %s with ?
    q = q.replace('%s', '?')
    # Replace MySQL CURDATE() with SQLite date('now')
    q = re.sub(r'CURDATE\(\)', "date('now')", q, flags=re.IGNORECASE)
    # Replace DATE_SUB(date('now'), INTERVAL 6 MONTH)
    q = re.sub(r"DATE_SUB\(date\('now'\),\s*INTERVAL\s*6\s*MONTH\)", "date('now', '-6 months')", q, flags=re.IGNORECASE)
    # Replace DATE_ADD(date('now'), INTERVAL ? DAY)
    q = re.sub(r"DATE_ADD\(date\('now'\),\s*INTERVAL\s*\?\s*DAY\)", "date('now', '+' || ? || ' days')", q, flags=re.IGNORECASE)
    # Replace DATEDIFF(a, b) with (julianday(a) - julianday(b))
    q = re.sub(r"DATEDIFF\(([^,]+),\s*date\('now'\)\)", r"CAST(julianday(\1) - julianday(date('now')) AS INTEGER)", q, flags=re.IGNORECASE)
    # Replace DATE_FORMAT(payment_date, '%b %Y')
    q = re.sub(r"DATE_FORMAT\(([^,]+),\s*'%b %Y'\)", r"strftime('%m-%Y', \1)", q, flags=re.IGNORECASE)
    q = re.sub(r"DATE_FORMAT\(([^,]+),\s*'%Y-%m'\)", r"strftime('%Y-%m', \1)", q, flags=re.IGNORECASE)
    q = re.sub(r"DATE_FORMAT\(([^,]+),\s*'%M %Y'\)", r"strftime('%m/%Y', \1)", q, flags=re.IGNORECASE)
    # Replace MONTH(x) = MONTH(date('now'))
    q = re.sub(r"MONTH\(([^)]+)\)\s*=\s*MONTH\(date\('now'\)\)", r"strftime('%m', \1) = strftime('%m', 'now')", q, flags=re.IGNORECASE)
    q = re.sub(r"YEAR\(([^)]+)\)\s*=\s*YEAR\(date\('now'\)\)", r"strftime('%Y', \1) = strftime('%Y', 'now')", q, flags=re.IGNORECASE)
    return q

def query_db(query, args=(), one=False):
    """
    Executes a SELECT query with parameters and returns dictionary rows.
    Uses parameterized execution to prevent SQL injection.
    """
    conn = get_db_connection()
    try:
        if DB_MODE == 'mysql':
            cursor = conn.cursor(dictionary=True)
            cursor.execute(query, args)
            result = cursor.fetchall()
            cursor.close()
            return (result[0] if result else None) if one else result
        else:
            adapted_query = adapt_query_for_sqlite(query)
            cursor = conn.cursor()
            cursor.execute(adapted_query, args)
            rows = cursor.fetchall()
            result = [dict(row) for row in rows]
            cursor.close()
            return (result[0] if result else None) if one else result
    finally:
        conn.close()

def modify_db(query, args=()):
    """
    Executes an INSERT, UPDATE, or DELETE query with parameters.
    Returns the lastrowid or rowcount.
    """
    conn = get_db_connection()
    try:
        if DB_MODE == 'mysql':
            cursor = conn.cursor()
            cursor.execute(query, args)
            conn.commit()
            last_id = cursor.lastrowid
            count = cursor.rowcount
            cursor.close()
            return last_id if last_id else count
        else:
            adapted_query = adapt_query_for_sqlite(query)
            cursor = conn.cursor()
            cursor.execute(adapted_query, args)
            conn.commit()
            last_id = cursor.lastrowid
            count = cursor.rowcount
            cursor.close()
            return last_id if last_id else count
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def initialize_database():
    """
    Initializes database schema and sample data.
    If MySQL is available, verifies tables in MySQL.
    If MySQL is offline, initializes local fallback database so app is immediately testable.
    """
    if is_mysql_available():
        print("[Database] MySQL Server detected! Bootstrapping MySQL tables...")
        try:
            sql_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'database', 'gym_management.sql')
            if os.path.exists(sql_file):
                import mysql.connector
                conn = mysql.connector.connect(
                    host=Config.MYSQL_HOST,
                    port=Config.MYSQL_PORT,
                    user=Config.MYSQL_USER,
                    password=Config.MYSQL_PASSWORD,
                    database=Config.MYSQL_DB
                )
                cursor = conn.cursor()
                cursor.execute("SHOW TABLES LIKE 'members';")
                if not cursor.fetchone():
                    with open(sql_file, 'r', encoding='utf-8') as f:
                        commands = f.read().split(';')
                    for cmd in commands:
                        stmt = cmd.strip()
                        if stmt and not stmt.lower().startswith(('create database', 'use ')):
                            try:
                                cursor.execute(stmt)
                            except Exception as err:
                                pass
                    conn.commit()
                    print("[Database] MySQL gym_management schema and sample records loaded.")
                cursor.close()
                conn.close()
        except Exception as e:
            print(f"[Database Notice] MySQL setup notice: {e}")
    else:
        print("[Database Notice] Local MySQL service is currently stopped or not responding on port 3306.")
        print("[Database Notice] Starting with transparent local SQLite fallback so the application is immediately testable!")
        init_sqlite_fallback()

def init_sqlite_fallback():
    """Sets up the fallback SQLite schema and initial seed data if not present."""
    os.makedirs(os.path.dirname(SQLITE_PATH), exist_ok=True)
    conn = sqlite3.connect(SQLITE_PATH)
    cursor = conn.cursor()

    cursor.executescript("""
    CREATE TABLE IF NOT EXISTS admins (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        full_name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS trainers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        phone TEXT NOT NULL,
        gender TEXT NOT NULL,
        specialization TEXT NOT NULL,
        experience INTEGER NOT NULL DEFAULT 1,
        salary REAL NOT NULL DEFAULT 0.00,
        joining_date TEXT NOT NULL,
        status TEXT DEFAULT 'Active',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS membership_plans (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        plan_name TEXT UNIQUE NOT NULL,
        duration_months INTEGER NOT NULL,
        price REAL NOT NULL,
        description TEXT,
        status TEXT DEFAULT 'Active',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS members (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        full_name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        phone TEXT NOT NULL,
        gender TEXT NOT NULL,
        dob TEXT,
        address TEXT,
        joining_date TEXT NOT NULL,
        trainer_id INTEGER,
        plan_id INTEGER,
        membership_start TEXT NOT NULL,
        membership_end TEXT NOT NULL,
        status TEXT DEFAULT 'Active',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (trainer_id) REFERENCES trainers(id) ON DELETE SET NULL,
        FOREIGN KEY (plan_id) REFERENCES membership_plans(id) ON DELETE SET NULL
    );

    CREATE TABLE IF NOT EXISTS memberships (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        member_id INTEGER NOT NULL,
        plan_id INTEGER,
        start_date TEXT NOT NULL,
        end_date TEXT NOT NULL,
        amount REAL NOT NULL,
        status TEXT DEFAULT 'Active',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        member_id INTEGER NOT NULL,
        amount REAL NOT NULL,
        payment_date TEXT NOT NULL,
        payment_method TEXT NOT NULL,
        transaction_id TEXT,
        status TEXT DEFAULT 'Paid',
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (member_id) REFERENCES members(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS attendance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        member_id INTEGER NOT NULL,
        attendance_date TEXT NOT NULL,
        check_in_time TEXT,
        check_out_time TEXT,
        status TEXT DEFAULT 'Present',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE (member_id, attendance_date),
        FOREIGN KEY (member_id) REFERENCES members(id) ON DELETE CASCADE
    );
    """)

    # Seed Admin if not exists
    cursor.execute("SELECT id FROM admins WHERE username = 'admin'")
    if not cursor.fetchone():
        cursor.execute("""
            INSERT INTO admins (id, username, password, full_name, email)
            VALUES (1, 'admin', 'scrypt:32768:8:1$m9bC6j9w0Uv0oRsm$36a2a2259160d28362629676ecae0762a123689c16503c733795123d46ba1ec81e9b2520377e8a93e36e1a499d690a618e7d23d8c2aa5b642ec367e9b04fc92b', 'Master Admin', 'admin@ironpulse.com')
        """)

    # Seed Plans if not exists
    cursor.execute("SELECT COUNT(*) FROM membership_plans")
    if cursor.fetchone()[0] == 0:
        cursor.executescript("""
        INSERT INTO membership_plans (id, plan_name, duration_months, price, description, status) VALUES
        (1, 'Monthly Plan', 1, 1500.00, 'Full gym access, locker room, free fitness orientation.', 'Active'),
        (2, 'Quarterly Plan', 3, 4000.00, '3 months gym access + 1 complimentary body composition assessment.', 'Active'),
        (3, 'Half-Yearly Plan', 6, 7000.00, '6 months gym access + 2 personal trainer consultation sessions.', 'Active'),
        (4, 'Yearly Plan', 12, 12000.00, '365 days VIP access, sauna, personalized nutrition chart & towel service.', 'Active');

        INSERT INTO trainers (id, name, email, phone, gender, specialization, experience, salary, joining_date, status) VALUES
        (1, 'Vikram Rathore', 'vikram.trainer@ironpulse.com', '9876543210', 'Male', 'Strength & Hypertrophy', 6, 45000.00, '2023-01-15', 'Active'),
        (2, 'Ananya Sharma', 'ananya.fit@ironpulse.com', '9876543211', 'Female', 'Yoga & Functional Mobility', 4, 38000.00, '2023-04-10', 'Active'),
        (3, 'David Miller', 'david.crossfit@ironpulse.com', '9876543212', 'Male', 'CrossFit & Olympic Lifting', 8, 55000.00, '2022-09-01', 'Active'),
        (4, 'Priya Nair', 'priya.pilates@ironpulse.com', '9876543213', 'Female', 'Pilates & Core Conditioning', 5, 42000.00, '2023-08-20', 'Active'),
        (5, 'Rohan Verma', 'rohan.hiit@ironpulse.com', '9876543214', 'Male', 'HIIT & Weight Loss Coaching', 3, 35000.00, '2024-02-01', 'Active');

        INSERT INTO members (id, full_name, email, phone, gender, dob, address, joining_date, trainer_id, plan_id, membership_start, membership_end, status) VALUES
        (1, 'Rahul Verma', 'rahul.verma@gmail.com', '9123456780', 'Male', '1996-05-14', 'Flat 402, Skyline Heights, MG Road', '2024-01-10', 1, 4, '2024-01-10', '2025-01-10', 'Active'),
        (2, 'Sneha Patel', 'sneha.patel@yahoo.com', '9123456781', 'Female', '1998-11-22', '12 Lakeview Enclave, Indiranagar', '2024-02-01', 2, 2, '2024-02-01', '2024-05-01', 'Active'),
        (3, 'Arjun Reddy', 'arjun.reddy@gmail.com', '9123456782', 'Male', '1994-08-30', '77 Jubilee Hills, Phase 2', '2024-01-15', 3, 3, '2024-01-15', '2024-07-15', 'Active'),
        (4, 'Kavita Sundaram', 'kavita.s@outlook.com', '9123456783', 'Female', '1992-03-18', '24 Palm Meadows, Whitefield', '2023-11-01', 4, 1, '2023-11-01', '2023-12-01', 'Expired'),
        (5, 'Aditya Malhotra', 'aditya.m@gmail.com', '9123456784', 'Male', '2000-09-05', 'B-14 Green Park Ext, Sector 5', '2024-03-01', 5, 2, '2024-03-01', '2024-06-01', 'Active'),
        (6, 'Pooja Hegde', 'pooja.hegde@hotmail.com', '9123456785', 'Female', '1997-07-12', 'Villa 8, Oasis Palms, Koramangala', '2024-03-10', 2, 4, '2024-03-10', '2025-03-10', 'Active'),
        (7, 'Sameer Khan', 'sameer.k@gmail.com', '9123456786', 'Male', '1995-12-03', '304 Silver Crest, Bandra West', '2023-10-05', 1, 3, '2023-10-05', '2024-04-05', 'Active'),
        (8, 'Tanvi Deshmukh', 'tanvi.d@gmail.com', '9123456787', 'Female', '2001-01-25', '88 Sunrise Apartments, Powai', '2024-01-05', 4, 1, '2024-01-05', '2024-02-05', 'Expired'),
        (9, 'Karthik Raja', 'karthik.raja@gmail.com', '9123456788', 'Male', '1993-04-19', '15 Royal Palm Residency, Anna Nagar', '2024-02-15', 3, 4, '2024-02-15', '2025-02-15', 'Active'),
        (10, 'Meera Sen', 'meera.sen@gmail.com', '9123456789', 'Female', '1999-06-11', '502 Orchid Towers, Salt Lake', '2024-03-15', NULL, 1, '2024-03-15', '2024-04-15', 'Active'),
        (11, 'Nikhil Joshi', 'nikhil.joshi@gmail.com', '9123456790', 'Male', '1991-10-08', '45 Ashok Vihar, Phase 1', '2023-08-10', 1, 2, '2023-08-10', '2023-11-10', 'Expired'),
        (12, 'Divya Nair', 'divya.nair@gmail.com', '9123456791', 'Female', '1995-02-17', '18 Marine Drive, Kochi', '2024-03-20', 5, 3, '2024-03-20', '2024-09-20', 'Active');

        INSERT INTO payments (id, member_id, amount, payment_date, payment_method, transaction_id, status, notes) VALUES
        (1001, 1, 12000.00, '2024-01-10', 'UPI', 'UPI-240110-89324', 'Paid', 'Annual VIP membership fee'),
        (1002, 2, 4000.00, '2024-02-01', 'Card', 'TXN-CARD-9921', 'Paid', 'Quarterly subscription renewal'),
        (1003, 3, 7000.00, '2024-01-15', 'Bank Transfer', 'NEFT-0029104', 'Paid', 'Half yearly membership payment'),
        (1004, 4, 1500.00, '2023-11-01', 'Cash', 'CASH-REC-104', 'Paid', 'Monthly plan joining fee'),
        (1005, 5, 4000.00, '2024-03-01', 'UPI', 'UPI-240301-44120', 'Paid', 'Quarterly membership fee'),
        (1006, 6, 12000.00, '2024-03-10', 'Card', 'TXN-CARD-7812', 'Paid', 'Full 1-year premium package'),
        (1007, 7, 7000.00, '2023-10-05', 'UPI', 'UPI-231005-11029', 'Paid', 'Half-yearly plan fee'),
        (1008, 8, 1500.00, '2024-01-05', 'Cash', 'CASH-REC-205', 'Paid', '1 month trial fee'),
        (1009, 9, 12000.00, '2024-02-15', 'Bank Transfer', 'RTGS-240215-998', 'Paid', 'Yearly plan payment via online banking'),
        (1010, 10, 1500.00, '2024-03-15', 'UPI', 'UPI-240315-77218', 'Paid', 'March monthly plan'),
        (1011, 11, 4000.00, '2023-08-10', 'Card', 'TXN-CARD-4421', 'Paid', 'Quarterly fee'),
        (1012, 12, 7000.00, '2024-03-20', 'UPI', 'UPI-240320-99432', 'Paid', 'Half-yearly plan fee');

        INSERT INTO attendance (member_id, attendance_date, check_in_time, check_out_time, status) VALUES
        (1, date('now'), '06:30:00', '08:00:00', 'Present'),
        (2, date('now'), '07:00:00', '08:15:00', 'Present'),
        (3, date('now'), '07:15:00', '08:45:00', 'Present'),
        (5, date('now'), '08:00:00', '09:30:00', 'Present'),
        (6, date('now'), '09:00:00', NULL, 'Present'),
        (7, date('now'), '17:30:00', '19:00:00', 'Present'),
        (9, date('now'), '18:00:00', NULL, 'Present'),
        (10, date('now'), '18:30:00', '20:00:00', 'Present'),
        (12, date('now'), '19:00:00', NULL, 'Present'),
        (4, date('now'), NULL, NULL, 'Absent'),
        (8, date('now'), NULL, NULL, 'Absent'),
        (11, date('now'), NULL, NULL, 'Absent');
        """)
    conn.commit()
    conn.close()
