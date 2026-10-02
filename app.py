from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from datetime import datetime, date, timedelta
import os

from config import Config
from utils.database import query_db, modify_db, initialize_database
from utils.helpers import (
    login_required, hash_password, verify_password,
    validate_email, validate_phone, validate_date,
    calculate_membership_end, format_currency, format_date_display
)

app = Flask(__name__)
app.config.from_object(Config)

# Register custom Jinja filters
@app.template_filter('currency')
def currency_filter(amount):
    return format_currency(amount)

@app.template_filter('format_date')
def date_filter(d):
    return format_date_display(d)

@app.context_processor
def inject_globals():
    """Inject standard variables available across all templates."""
    return {
        'current_date': date.today().strftime('%A, %d %B %Y'),
        'today_ymd': date.today().strftime('%Y-%m-%d'),
        'current_admin': session.get('admin_name', 'Administrator'),
        'current_admin_user': session.get('admin_username', 'admin')
    }

# -------------------------------------------------------------
# Routine to auto-update expired memberships
# -------------------------------------------------------------
def refresh_membership_statuses():
    """Marks active members whose end date has passed as Expired."""
    try:
        modify_db("""
            UPDATE members 
            SET status = 'Expired' 
            WHERE membership_end < CURDATE() AND status = 'Active'
        """)
    except Exception as e:
        # Silently log if DB not connected yet
        pass


# =============================================================
# AUTHENTICATION ROUTES
# =============================================================

@app.route('/')
def index():
    if session.get('admin_logged_in'):
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('admin_logged_in'):
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        if not username or not password:
            flash('Please enter both username and password.', 'danger')
            return render_template('login.html')

        try:
            admin = query_db("SELECT * FROM admins WHERE username = %s LIMIT 1", (username,), one=True)
            if admin and verify_password(admin['password'], password):
                session['admin_logged_in'] = True
                session['admin_id'] = admin['id']
                session['admin_username'] = admin['username']
                session['admin_name'] = admin['full_name']
                flash(f"Welcome back, {admin['full_name']}!", 'success')
                return redirect(url_for('dashboard'))
            else:
                flash('Invalid username or password. Please try again.', 'danger')
        except Exception as e:
            flash(f'Database connection error: Could not verify login. Check MySQL connection.', 'danger')

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been successfully logged out.', 'info')
    return redirect(url_for('login'))


# =============================================================
# DASHBOARD ROUTE
# =============================================================

@app.route('/dashboard')
@login_required
def dashboard():
    refresh_membership_statuses()
    
    # Initialize default fallback statistics
    stats = {
        'total_members': 0,
        'active_members': 0,
        'expired_members': 0,
        'total_trainers': 0,
        'today_attendance': 0,
        'monthly_revenue': 0.00
    }
    recent_members = []
    recent_payments = []
    membership_breakdown = {'Active': 0, 'Expired': 0, 'Pending': 0, 'Inactive': 0}
    revenue_chart = {'labels': [], 'data': []}
    attendance_summary = {'present': 0, 'absent': 0, 'late': 0}

    try:
        # Dynamic stats from MySQL
        row = query_db("SELECT COUNT(*) AS count FROM members", one=True)
        stats['total_members'] = row['count'] if row else 0

        row = query_db("SELECT COUNT(*) AS count FROM members WHERE status = 'Active'", one=True)
        stats['active_members'] = row['count'] if row else 0

        row = query_db("SELECT COUNT(*) AS count FROM members WHERE status = 'Expired'", one=True)
        stats['expired_members'] = row['count'] if row else 0

        row = query_db("SELECT COUNT(*) AS count FROM trainers WHERE status = 'Active'", one=True)
        stats['total_trainers'] = row['count'] if row else 0

        row = query_db("SELECT COUNT(*) AS count FROM attendance WHERE attendance_date = CURDATE() AND status = 'Present'", one=True)
        stats['today_attendance'] = row['count'] if row else 0

        row = query_db("""
            SELECT COALESCE(SUM(amount), 0) AS total 
            FROM payments 
            WHERE status = 'Paid' 
            AND MONTH(payment_date) = MONTH(CURDATE()) 
            AND YEAR(payment_date) = YEAR(CURDATE())
        """, one=True)
        stats['monthly_revenue'] = float(row['total']) if row else 0.00

        # Recent 5 Members
        recent_members = query_db("""
            SELECT m.*, p.plan_name, t.name AS trainer_name
            FROM members m
            LEFT JOIN membership_plans p ON m.plan_id = p.id
            LEFT JOIN trainers t ON m.trainer_id = t.id
            ORDER BY m.id DESC LIMIT 5
        """)

        # Recent 5 Payments
        recent_payments = query_db("""
            SELECT p.*, m.full_name AS member_name
            FROM payments p
            JOIN members m ON p.member_id = m.id
            ORDER BY p.id DESC LIMIT 5
        """)

        # Membership status distribution
        status_rows = query_db("SELECT status, COUNT(*) AS count FROM members GROUP BY status")
        for sr in status_rows:
            if sr['status'] in membership_breakdown:
                membership_breakdown[sr['status']] = sr['count']

        # Last 6 Months Revenue Trend
        revenue_rows = query_db("""
            SELECT 
                DATE_FORMAT(payment_date, '%b %Y') AS month_name,
                DATE_FORMAT(payment_date, '%Y-%m') AS ym,
                SUM(amount) AS total_revenue
            FROM payments
            WHERE status = 'Paid' AND payment_date >= DATE_SUB(CURDATE(), INTERVAL 6 MONTH)
            GROUP BY ym, month_name
            ORDER BY ym ASC
        """)
        for rr in revenue_rows:
            revenue_chart['labels'].append(rr['month_name'])
            revenue_chart['data'].append(float(rr['total_revenue']))

        # Attendance breakdown for today
        att_rows = query_db("""
            SELECT status, COUNT(*) AS count 
            FROM attendance 
            WHERE attendance_date = CURDATE() 
            GROUP BY status
        """)
        for ar in att_rows:
            if ar['status'].lower() in attendance_summary:
                attendance_summary[ar['status'].lower()] = ar['count']

    except Exception as e:
        flash(f"Notice: Database statistics query notice: {e}", 'warning')

    return render_template(
        'dashboard.html',
        stats=stats,
        recent_members=recent_members,
        recent_payments=recent_payments,
        membership_breakdown=membership_breakdown,
        revenue_chart=revenue_chart,
        attendance_summary=attendance_summary
    )


# =============================================================
# MEMBER MANAGEMENT ROUTES
# =============================================================

@app.route('/members')
@login_required
def members():
    refresh_membership_statuses()
    search_query = request.args.get('q', '').strip()
    status_filter = request.args.get('status', '').strip()
    plan_filter = request.args.get('plan_id', '').strip()

    sql = """
        SELECT m.*, p.plan_name, p.price, t.name AS trainer_name
        FROM members m
        LEFT JOIN membership_plans p ON m.plan_id = p.id
        LEFT JOIN trainers t ON m.trainer_id = t.id
        WHERE 1=1
    """
    params = []

    if search_query:
        sql += " AND (m.full_name LIKE %s OR m.email LIKE %s OR m.phone LIKE %s)"
        like_term = f"%{search_query}%"
        params.extend([like_term, like_term, like_term])

    if status_filter:
        sql += " AND m.status = %s"
        params.append(status_filter)

    if plan_filter:
        sql += " AND m.plan_id = %s"
        params.append(plan_filter)

    sql += " ORDER BY m.id DESC"

    member_list = query_db(sql, tuple(params))
    all_plans = query_db("SELECT id, plan_name FROM membership_plans WHERE status = 'Active'")

    return render_template(
        'members/members.html',
        members=member_list,
        plans=all_plans,
        q=search_query,
        selected_status=status_filter,
        selected_plan=plan_filter
    )

@app.route('/members/add', methods=['GET', 'POST'])
@login_required
def add_member():
    plans = query_db("SELECT * FROM membership_plans WHERE status = 'Active'")
    trainers = query_db("SELECT * FROM trainers WHERE status = 'Active'")

    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()
        gender = request.form.get('gender', 'Male')
        dob = request.form.get('dob') or None
        address = request.form.get('address', '').strip()
        joining_date = request.form.get('joining_date') or date.today().strftime('%Y-%m-%d')
        trainer_id = request.form.get('trainer_id') or None
        plan_id = request.form.get('plan_id')
        membership_start = request.form.get('membership_start') or joining_date
        status = request.form.get('status', 'Active')

        # Backend validations
        if not full_name or not email or not phone or not plan_id:
            flash('Please fill in all required fields (Name, Email, Phone, Plan).', 'danger')
            return render_template('members/add_member.html', plans=plans, trainers=trainers, form_data=request.form)

        if not validate_email(email):
            flash('Invalid email address format.', 'danger')
            return render_template('members/add_member.html', plans=plans, trainers=trainers, form_data=request.form)

        if not validate_phone(phone):
            flash('Invalid phone number format.', 'danger')
            return render_template('members/add_member.html', plans=plans, trainers=trainers, form_data=request.form)

        # Check duplicate email/phone
        existing = query_db("SELECT id FROM members WHERE email = %s OR phone = %s LIMIT 1", (email, phone), one=True)
        if existing:
            flash('A member with this email or phone number already exists.', 'danger')
            return render_template('members/add_member.html', plans=plans, trainers=trainers, form_data=request.form)

        # Fetch selected plan details for calculating end date
        selected_plan = query_db("SELECT duration_months, price FROM membership_plans WHERE id = %s", (plan_id,), one=True)
        if not selected_plan:
            flash('Selected membership plan is invalid.', 'danger')
            return render_template('members/add_member.html', plans=plans, trainers=trainers, form_data=request.form)

        membership_end = calculate_membership_end(membership_start, selected_plan['duration_months'])

        try:
            member_id = modify_db("""
                INSERT INTO members 
                (full_name, email, phone, gender, dob, address, joining_date, trainer_id, plan_id, membership_start, membership_end, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                full_name, email, phone, gender, dob, address, joining_date,
                trainer_id if trainer_id else None,
                plan_id, membership_start, membership_end, status
            ))

            # Record initial membership log
            modify_db("""
                INSERT INTO memberships (member_id, plan_id, start_date, end_date, amount, status)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (member_id, plan_id, membership_start, membership_end, selected_plan['price'], 'Active'))

            # Optional automatic initial payment recording
            create_payment = request.form.get('record_payment')
            if create_payment:
                payment_method = request.form.get('payment_method', 'Cash')
                txn_id = request.form.get('transaction_id', '').strip() or f"INIT-{member_id}-{date.today().strftime('%Y%m%d')}"
                modify_db("""
                    INSERT INTO payments (member_id, amount, payment_date, payment_method, transaction_id, status, notes)
                    VALUES (%s, %s, %s, %s, %s, 'Paid', 'Initial plan payment on enrollment')
                """, (member_id, selected_plan['price'], membership_start, payment_method, txn_id))

            flash(f"Member '{full_name}' added successfully!", 'success')
            return redirect(url_for('members'))
        except Exception as e:
            flash(f"Error adding member: {e}", 'danger')

    return render_template('members/add_member.html', plans=plans, trainers=trainers, form_data={})

@app.route('/members/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_member(id):
    member = query_db("SELECT * FROM members WHERE id = %s", (id,), one=True)
    if not member:
        flash('Member not found.', 'danger')
        return redirect(url_for('members'))

    plans = query_db("SELECT * FROM membership_plans")
    trainers = query_db("SELECT * FROM trainers WHERE status = 'Active'")

    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()
        gender = request.form.get('gender', 'Male')
        dob = request.form.get('dob') or None
        address = request.form.get('address', '').strip()
        joining_date = request.form.get('joining_date')
        trainer_id = request.form.get('trainer_id') or None
        plan_id = request.form.get('plan_id')
        membership_start = request.form.get('membership_start')
        membership_end = request.form.get('membership_end')
        status = request.form.get('status', 'Active')

        if not full_name or not email or not phone:
            flash('Full Name, Email, and Phone are required.', 'danger')
            return render_template('members/edit_member.html', member=member, plans=plans, trainers=trainers)

        if not validate_email(email):
            flash('Invalid email format.', 'danger')
            return render_template('members/edit_member.html', member=member, plans=plans, trainers=trainers)

        if not validate_phone(phone):
            flash('Invalid phone format.', 'danger')
            return render_template('members/edit_member.html', member=member, plans=plans, trainers=trainers)

        # Check duplicate excluding current member
        existing = query_db("SELECT id FROM members WHERE (email = %s OR phone = %s) AND id != %s LIMIT 1", (email, phone, id), one=True)
        if existing:
            flash('Email or Phone number is already taken by another member.', 'danger')
            return render_template('members/edit_member.html', member=member, plans=plans, trainers=trainers)

        # Recalculate end date if plan changed and no custom end date supplied
        if str(plan_id) != str(member['plan_id']) and not membership_end:
            plan_obj = query_db("SELECT duration_months FROM membership_plans WHERE id = %s", (plan_id,), one=True)
            if plan_obj:
                membership_end = calculate_membership_end(membership_start, plan_obj['duration_months'])

        try:
            modify_db("""
                UPDATE members 
                SET full_name = %s, email = %s, phone = %s, gender = %s, dob = %s, 
                    address = %s, joining_date = %s, trainer_id = %s, plan_id = %s, 
                    membership_start = %s, membership_end = %s, status = %s
                WHERE id = %s
            """, (
                full_name, email, phone, gender, dob, address, joining_date,
                trainer_id if trainer_id else None,
                plan_id if plan_id else None,
                membership_start, membership_end, status, id
            ))
            flash(f"Member '{full_name}' updated successfully!", 'success')
            return redirect(url_for('members'))
        except Exception as e:
            flash(f"Error updating member: {e}", 'danger')

    return render_template('members/edit_member.html', member=member, plans=plans, trainers=trainers)

@app.route('/members/delete/<int:id>', methods=['GET', 'POST'])
@login_required
def delete_member(id):
    member = query_db("SELECT full_name FROM members WHERE id = %s", (id,), one=True)
    if member:
        try:
            modify_db("DELETE FROM members WHERE id = %s", (id,))
            flash(f"Member '{member['full_name']}' was successfully deleted.", 'success')
        except Exception as e:
            flash(f"Error deleting member: {e}", 'danger')
    else:
        flash('Member not found.', 'danger')
    return redirect(url_for('members'))

@app.route('/members/<int:id>')
@login_required
def view_member(id):
    member = query_db("""
        SELECT m.*, p.plan_name, p.price, p.duration_months, t.name AS trainer_name, t.phone AS trainer_phone
        FROM members m
        LEFT JOIN membership_plans p ON m.plan_id = p.id
        LEFT JOIN trainers t ON m.trainer_id = t.id
        WHERE m.id = %s
    """, (id,), one=True)

    if not member:
        flash('Member not found.', 'danger')
        return redirect(url_for('members'))

    payments = query_db("SELECT * FROM payments WHERE member_id = %s ORDER BY payment_date DESC", (id,))
    attendance_records = query_db("SELECT * FROM attendance WHERE member_id = %s ORDER BY attendance_date DESC LIMIT 30", (id,))
    total_spent = query_db("SELECT COALESCE(SUM(amount), 0) AS total FROM payments WHERE member_id = %s AND status = 'Paid'", (id,), one=True)

    return render_template(
        'members/view_member.html',
        member=member,
        payments=payments,
        attendance=attendance_records,
        total_spent=total_spent['total'] if total_spent else 0
    )


# =============================================================
# TRAINER MANAGEMENT ROUTES
# =============================================================

@app.route('/trainers')
@login_required
def trainers():
    search_query = request.args.get('q', '').strip()
    sql = """
        SELECT t.*, COUNT(m.id) AS assigned_members_count
        FROM trainers t
        LEFT JOIN members m ON t.id = m.trainer_id
        WHERE 1=1
    """
    params = []
    if search_query:
        sql += " AND (t.name LIKE %s OR t.specialization LIKE %s OR t.email LIKE %s OR t.phone LIKE %s)"
        q = f"%{search_query}%"
        params.extend([q, q, q, q])

    sql += " GROUP BY t.id ORDER BY t.id DESC"
    trainer_list = query_db(sql, tuple(params))

    return render_template('trainers/trainers.html', trainers=trainer_list, q=search_query)

@app.route('/trainers/add', methods=['GET', 'POST'])
@login_required
def add_trainer():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()
        gender = request.form.get('gender', 'Male')
        specialization = request.form.get('specialization', '').strip()
        experience = request.form.get('experience', 1)
        salary = request.form.get('salary', 0.0)
        joining_date = request.form.get('joining_date') or date.today().strftime('%Y-%m-%d')
        status = request.form.get('status', 'Active')

        if not name or not email or not phone or not specialization:
            flash('Name, Email, Phone, and Specialization are required.', 'danger')
            return render_template('trainers/add_trainer.html', form_data=request.form)

        if not validate_email(email):
            flash('Invalid email address format.', 'danger')
            return render_template('trainers/add_trainer.html', form_data=request.form)

        if not validate_phone(phone):
            flash('Invalid phone format.', 'danger')
            return render_template('trainers/add_trainer.html', form_data=request.form)

        existing = query_db("SELECT id FROM trainers WHERE email = %s OR phone = %s LIMIT 1", (email, phone), one=True)
        if existing:
            flash('A trainer with this email or phone number already exists.', 'danger')
            return render_template('trainers/add_trainer.html', form_data=request.form)

        try:
            modify_db("""
                INSERT INTO trainers (name, email, phone, gender, specialization, experience, salary, joining_date, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (name, email, phone, gender, specialization, experience, salary, joining_date, status))
            flash(f"Trainer '{name}' added successfully!", 'success')
            return redirect(url_for('trainers'))
        except Exception as e:
            flash(f"Error adding trainer: {e}", 'danger')

    return render_template('trainers/add_trainer.html', form_data={})

@app.route('/trainers/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_trainer(id):
    trainer = query_db("SELECT * FROM trainers WHERE id = %s", (id,), one=True)
    if not trainer:
        flash('Trainer not found.', 'danger')
        return redirect(url_for('trainers'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()
        gender = request.form.get('gender', 'Male')
        specialization = request.form.get('specialization', '').strip()
        experience = request.form.get('experience', 1)
        salary = request.form.get('salary', 0.0)
        joining_date = request.form.get('joining_date')
        status = request.form.get('status', 'Active')

        if not name or not email or not phone or not specialization:
            flash('Name, Email, Phone, and Specialization are required.', 'danger')
            return render_template('trainers/edit_trainer.html', trainer=trainer)

        if not validate_email(email):
            flash('Invalid email format.', 'danger')
            return render_template('trainers/edit_trainer.html', trainer=trainer)

        if not validate_phone(phone):
            flash('Invalid phone format.', 'danger')
            return render_template('trainers/edit_trainer.html', trainer=trainer)

        existing = query_db("SELECT id FROM trainers WHERE (email = %s OR phone = %s) AND id != %s LIMIT 1", (email, phone, id), one=True)
        if existing:
            flash('Email or Phone is already used by another trainer.', 'danger')
            return render_template('trainers/edit_trainer.html', trainer=trainer)

        try:
            modify_db("""
                UPDATE trainers
                SET name = %s, email = %s, phone = %s, gender = %s, specialization = %s,
                    experience = %s, salary = %s, joining_date = %s, status = %s
                WHERE id = %s
            """, (name, email, phone, gender, specialization, experience, salary, joining_date, status, id))
            flash(f"Trainer '{name}' updated successfully!", 'success')
            return redirect(url_for('trainers'))
        except Exception as e:
            flash(f"Error updating trainer: {e}", 'danger')

    return render_template('trainers/edit_trainer.html', trainer=trainer)

@app.route('/trainers/delete/<int:id>', methods=['GET', 'POST'])
@login_required
def delete_trainer(id):
    trainer = query_db("SELECT name FROM trainers WHERE id = %s", (id,), one=True)
    if trainer:
        try:
            modify_db("DELETE FROM trainers WHERE id = %s", (id,))
            flash(f"Trainer '{trainer['name']}' deleted successfully.", 'success')
        except Exception as e:
            flash(f"Error deleting trainer: {e}", 'danger')
    else:
        flash('Trainer not found.', 'danger')
    return redirect(url_for('trainers'))

@app.route('/trainers/<int:id>')
@login_required
def view_trainer(id):
    trainer = query_db("SELECT * FROM trainers WHERE id = %s", (id,), one=True)
    if not trainer:
        flash('Trainer not found.', 'danger')
        return redirect(url_for('trainers'))

    assigned_members = query_db("""
        SELECT m.*, p.plan_name 
        FROM members m
        LEFT JOIN membership_plans p ON m.plan_id = p.id
        WHERE m.trainer_id = %s
        ORDER BY m.full_name ASC
    """, (id,))

    return render_template('trainers/view_trainer.html', trainer=trainer, members=assigned_members)


# =============================================================
# MEMBERSHIP PLANS ROUTES
# =============================================================

@app.route('/plans')
@login_required
def plans():
    sql = """
        SELECT p.*, COUNT(m.id) AS enrolled_members
        FROM membership_plans p
        LEFT JOIN members m ON p.id = m.plan_id
        GROUP BY p.id
        ORDER BY p.price ASC
    """
    plans_list = query_db(sql)
    return render_template('plans/plans.html', plans=plans_list)

@app.route('/plans/add', methods=['GET', 'POST'])
@login_required
def add_plan():
    if request.method == 'POST':
        plan_name = request.form.get('plan_name', '').strip()
        duration_months = request.form.get('duration_months', 1)
        price = request.form.get('price', 0.0)
        description = request.form.get('description', '').strip()
        status = request.form.get('status', 'Active')

        if not plan_name or not duration_months or not price:
            flash('Plan Name, Duration, and Price are required.', 'danger')
            return render_template('plans/add_plan.html')

        try:
            dur = int(duration_months)
            pr = float(price)
            if dur < 1 or pr < 0:
                flash('Duration must be at least 1 month and price cannot be negative.', 'danger')
                return render_template('plans/add_plan.html')
        except ValueError:
            flash('Duration and Price must be valid numbers.', 'danger')
            return render_template('plans/add_plan.html')

        existing = query_db("SELECT id FROM membership_plans WHERE plan_name = %s LIMIT 1", (plan_name,), one=True)
        if existing:
            flash(f"A plan named '{plan_name}' already exists. Please choose a different name.", 'danger')
            return render_template('plans/add_plan.html')

        try:
            modify_db("""
                INSERT INTO membership_plans (plan_name, duration_months, price, description, status)
                VALUES (%s, %s, %s, %s, %s)
            """, (plan_name, dur, pr, description, status))
            flash(f"Plan '{plan_name}' created successfully!", 'success')
            return redirect(url_for('plans'))
        except Exception as e:
            flash(f"Error creating plan: {e}", 'danger')

    return render_template('plans/add_plan.html')

@app.route('/plans/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_plan(id):
    plan = query_db("SELECT * FROM membership_plans WHERE id = %s", (id,), one=True)
    if not plan:
        flash('Plan not found.', 'danger')
        return redirect(url_for('plans'))

    if request.method == 'POST':
        plan_name = request.form.get('plan_name', '').strip()
        duration_months = request.form.get('duration_months', 1)
        price = request.form.get('price', 0.0)
        description = request.form.get('description', '').strip()
        status = request.form.get('status', 'Active')

        if not plan_name or not duration_months or not price:
            flash('Plan Name, Duration, and Price are required.', 'danger')
            return render_template('plans/edit_plan.html', plan=plan)

        try:
            dur = int(duration_months)
            pr = float(price)
            if dur < 1 or pr < 0:
                flash('Duration must be at least 1 month and price cannot be negative.', 'danger')
                return render_template('plans/edit_plan.html', plan=plan)
        except ValueError:
            flash('Duration and Price must be valid numbers.', 'danger')
            return render_template('plans/edit_plan.html', plan=plan)

        existing = query_db("SELECT id FROM membership_plans WHERE plan_name = %s AND id != %s LIMIT 1", (plan_name, id), one=True)
        if existing:
            flash(f"A plan named '{plan_name}' already exists.", 'danger')
            return render_template('plans/edit_plan.html', plan=plan)

        try:
            modify_db("""
                UPDATE membership_plans
                SET plan_name = %s, duration_months = %s, price = %s, description = %s, status = %s
                WHERE id = %s
            """, (plan_name, dur, pr, description, status, id))
            flash(f"Plan '{plan_name}' updated successfully!", 'success')
            return redirect(url_for('plans'))
        except Exception as e:
            flash(f"Error updating plan: {e}", 'danger')

    return render_template('plans/edit_plan.html', plan=plan)

@app.route('/plans/delete/<int:id>', methods=['GET', 'POST'])
@login_required
def delete_plan(id):
    plan = query_db("SELECT plan_name FROM membership_plans WHERE id = %s", (id,), one=True)
    if plan:
        try:
            modify_db("DELETE FROM membership_plans WHERE id = %s", (id,))
            flash(f"Plan '{plan['plan_name']}' deleted.", 'success')
        except Exception as e:
            flash(f"Error deleting plan (ensure no active members are linked): {e}", 'danger')
    else:
        flash('Plan not found.', 'danger')
    return redirect(url_for('plans'))


# =============================================================
# PAYMENT MANAGEMENT ROUTES
# =============================================================

@app.route('/payments')
@login_required
def payments():
    search_query = request.args.get('q', '').strip()
    method_filter = request.args.get('method', '').strip()
    status_filter = request.args.get('status', '').strip()

    sql = """
        SELECT p.*, m.full_name AS member_name, m.phone AS member_phone, pl.plan_name
        FROM payments p
        JOIN members m ON p.member_id = m.id
        LEFT JOIN membership_plans pl ON m.plan_id = pl.id
        WHERE 1=1
    """
    params = []

    if search_query:
        sql += " AND (m.full_name LIKE %s OR p.transaction_id LIKE %s OR m.phone LIKE %s)"
        q = f"%{search_query}%"
        params.extend([q, q, q])

    if method_filter:
        sql += " AND p.payment_method = %s"
        params.append(method_filter)

    if status_filter:
        sql += " AND p.status = %s"
        params.append(status_filter)

    sql += " ORDER BY p.id DESC"
    payment_list = query_db(sql, tuple(params))

    # Calculate total revenue of filtered list
    total_amount = sum(float(p['amount']) for p in payment_list if p['status'] == 'Paid')

    return render_template(
        'payments/payments.html',
        payments=payment_list,
        total_amount=total_amount,
        q=search_query,
        selected_method=method_filter,
        selected_status=status_filter
    )

@app.route('/payments/add', methods=['GET', 'POST'])
@login_required
def add_payment():
    members = query_db("SELECT id, full_name, phone, plan_id FROM members ORDER BY full_name ASC")

    if request.method == 'POST':
        member_id = request.form.get('member_id')
        amount = request.form.get('amount')
        payment_date = request.form.get('payment_date') or date.today().strftime('%Y-%m-%d')
        payment_method = request.form.get('payment_method', 'Cash')
        transaction_id = request.form.get('transaction_id', '').strip()
        status = request.form.get('status', 'Paid')
        notes = request.form.get('notes', '').strip()

        if not member_id or not amount:
            flash('Member and Amount are required.', 'danger')
            return render_template('payments/add_payment.html', members=members)

        try:
            amt = float(amount)
            if amt <= 0:
                flash('Payment amount must be greater than zero.', 'danger')
                return render_template('payments/add_payment.html', members=members)
        except ValueError:
            flash('Invalid numeric amount.', 'danger')
            return render_template('payments/add_payment.html', members=members)

        if not transaction_id:
            transaction_id = f"TXN-{payment_method[:2].upper()}-{datetime.now().strftime('%y%m%d%H%M%S')}"

        try:
            payment_id = modify_db("""
                INSERT INTO payments (member_id, amount, payment_date, payment_method, transaction_id, status, notes)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (member_id, amt, payment_date, payment_method, transaction_id, status, notes))

            flash('Payment recorded successfully!', 'success')
            return redirect(url_for('payment_receipt', id=payment_id))
        except Exception as e:
            flash(f"Error recording payment: {e}", 'danger')

    return render_template('payments/add_payment.html', members=members)

@app.route('/payments/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_payment(id):
    payment = query_db("""
        SELECT p.*, m.full_name AS member_name 
        FROM payments p 
        JOIN members m ON p.member_id = m.id 
        WHERE p.id = %s
    """, (id,), one=True)

    if not payment:
        flash('Payment record not found.', 'danger')
        return redirect(url_for('payments'))

    if request.method == 'POST':
        amount = request.form.get('amount')
        payment_date = request.form.get('payment_date')
        payment_method = request.form.get('payment_method')
        transaction_id = request.form.get('transaction_id', '').strip()
        status = request.form.get('status')
        notes = request.form.get('notes', '').strip()

        if not amount or not payment_date:
            flash('Amount and date are required.', 'danger')
            return render_template('payments/edit_payment.html', payment=payment)

        try:
            modify_db("""
                UPDATE payments
                SET amount = %s, payment_date = %s, payment_method = %s, transaction_id = %s, status = %s, notes = %s
                WHERE id = %s
            """, (amount, payment_date, payment_method, transaction_id, status, notes, id))
            flash('Payment updated successfully.', 'success')
            return redirect(url_for('payments'))
        except Exception as e:
            flash(f"Error updating payment: {e}", 'danger')

    return render_template('payments/edit_payment.html', payment=payment)

@app.route('/payments/delete/<int:id>', methods=['GET', 'POST'])
@login_required
def delete_payment(id):
    try:
        modify_db("DELETE FROM payments WHERE id = %s", (id,))
        flash('Payment record deleted.', 'success')
    except Exception as e:
        flash(f"Error deleting payment: {e}", 'danger')
    return redirect(url_for('payments'))

@app.route('/payments/receipt/<int:id>')
@login_required
def payment_receipt(id):
    payment = query_db("""
        SELECT p.*, m.full_name AS member_name, m.email AS member_email, m.phone AS member_phone,
               m.address AS member_address, pl.plan_name, pl.duration_months
        FROM payments p
        JOIN members m ON p.member_id = m.id
        LEFT JOIN membership_plans pl ON m.plan_id = pl.id
        WHERE p.id = %s
    """, (id,), one=True)

    if not payment:
        flash('Receipt not found.', 'danger')
        return redirect(url_for('payments'))

    return render_template('payments/receipt.html', payment=payment)


# =============================================================
# ATTENDANCE MANAGEMENT ROUTES
# =============================================================

@app.route('/attendance')
@login_required
def attendance():
    target_date = request.args.get('date', date.today().strftime('%Y-%m-%d'))
    search_q = request.args.get('q', '').strip()

    sql = """
        SELECT a.*, m.full_name AS member_name, m.phone AS member_phone, p.plan_name
        FROM attendance a
        JOIN members m ON a.member_id = m.id
        LEFT JOIN membership_plans p ON m.plan_id = p.id
        WHERE a.attendance_date = %s
    """
    params = [target_date]

    if search_q:
        sql += " AND (m.full_name LIKE %s OR m.phone LIKE %s)"
        q = f"%{search_q}%"
        params.extend([q, q])

    sql += " ORDER BY a.id DESC"
    attendance_records = query_db(sql, tuple(params))

    # All active members for check-in dropdown
    members_list = query_db("SELECT id, full_name, phone FROM members WHERE status = 'Active' ORDER BY full_name ASC")

    # Counts for selected date
    counts = query_db("""
        SELECT 
            COUNT(*) AS total_logged,
            SUM(CASE WHEN status = 'Present' THEN 1 ELSE 0 END) AS present_count,
            SUM(CASE WHEN status = 'Absent' THEN 1 ELSE 0 END) AS absent_count,
            SUM(CASE WHEN status = 'Late' THEN 1 ELSE 0 END) AS late_count
        FROM attendance 
        WHERE attendance_date = %s
    """, (target_date,), one=True)

    return render_template(
        'attendance/attendance.html',
        records=attendance_records,
        members=members_list,
        selected_date=target_date,
        q=search_q,
        counts=counts or {'total_logged': 0, 'present_count': 0, 'absent_count': 0, 'late_count': 0}
    )

@app.route('/attendance/check-in', methods=['POST'])
@login_required
def check_in():
    member_id = request.form.get('member_id')
    att_date = request.form.get('attendance_date') or date.today().strftime('%Y-%m-%d')
    check_in_time = request.form.get('check_in_time') or datetime.now().strftime('%H:%M:%S')
    status = request.form.get('status', 'Present')

    if not member_id:
        flash('Please select a member.', 'danger')
        return redirect(url_for('attendance', date=att_date))

    # Prevent duplicate attendance for the same member on the same day
    existing = query_db("""
        SELECT id FROM attendance 
        WHERE member_id = %s AND attendance_date = %s
    """, (member_id, att_date), one=True)

    if existing:
        flash('Attendance has already been marked for this member on this date!', 'warning')
        return redirect(url_for('attendance', date=att_date))

    try:
        modify_db("""
            INSERT INTO attendance (member_id, attendance_date, check_in_time, status)
            VALUES (%s, %s, %s, %s)
        """, (member_id, att_date, check_in_time, status))
        flash('Check-in recorded successfully!', 'success')
    except Exception as e:
        flash(f"Error marking attendance: {e}", 'danger')

    return redirect(url_for('attendance', date=att_date))

@app.route('/attendance/check-out', methods=['POST'])
@login_required
def check_out():
    record_id = request.form.get('record_id')
    att_date = request.form.get('attendance_date')
    check_out_time = request.form.get('check_out_time') or datetime.now().strftime('%H:%M:%S')

    if not record_id:
        flash('Invalid record selected.', 'danger')
        return redirect(url_for('attendance', date=att_date))

    try:
        modify_db("""
            UPDATE attendance 
            SET check_out_time = %s 
            WHERE id = %s
        """, (check_out_time, record_id))
        flash('Check-out time recorded successfully!', 'success')
    except Exception as e:
        flash(f"Error updating check-out: {e}", 'danger')

    return redirect(url_for('attendance', date=att_date))

@app.route('/attendance/mark-absent', methods=['POST'])
@login_required
def mark_absent():
    member_id = request.form.get('member_id')
    att_date = request.form.get('attendance_date') or date.today().strftime('%Y-%m-%d')

    if not member_id:
        flash('Please select a member.', 'danger')
        return redirect(url_for('attendance', date=att_date))

    existing = query_db("""
        SELECT id FROM attendance 
        WHERE member_id = %s AND attendance_date = %s
    """, (member_id, att_date), one=True)

    if existing:
        flash('Attendance already recorded for this member today.', 'warning')
        return redirect(url_for('attendance', date=att_date))

    try:
        modify_db("""
            INSERT INTO attendance (member_id, attendance_date, check_in_time, check_out_time, status)
            VALUES (%s, %s, NULL, NULL, 'Absent')
        """, (member_id, att_date))
        flash('Member marked Absent.', 'info')
    except Exception as e:
        flash(f"Error marking absent: {e}", 'danger')

    return redirect(url_for('attendance', date=att_date))

@app.route('/attendance/delete/<int:id>', methods=['GET', 'POST'])
@login_required
def delete_attendance(id):
    att_date = request.form.get('attendance_date', date.today().strftime('%Y-%m-%d'))
    try:
        modify_db("DELETE FROM attendance WHERE id = %s", (id,))
        flash('Attendance record removed.', 'success')
    except Exception as e:
        flash(f"Error deleting record: {e}", 'danger')
    return redirect(url_for('attendance', date=att_date))


# =============================================================
# REPORTS SECTION
# =============================================================

@app.route('/reports', methods=['GET'])
@app.route('/reports/<string:sub_report>', methods=['GET'])
@login_required
def reports(sub_report=None):
    report_type = sub_report or request.args.get('type', 'members')
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')
    status_filter = request.args.get('status', '')

    report_data = []
    summary_metric = None

    if report_type == 'members':
        sql = """
            SELECT m.*, p.plan_name, t.name AS trainer_name
            FROM members m
            LEFT JOIN membership_plans p ON m.plan_id = p.id
            LEFT JOIN trainers t ON m.trainer_id = t.id
            WHERE 1=1
        """
        params = []
        if status_filter:
            sql += " AND m.status = %s"
            params.append(status_filter)
        if start_date:
            sql += " AND m.joining_date >= %s"
            params.append(start_date)
        if end_date:
            sql += " AND m.joining_date <= %s"
            params.append(end_date)
        sql += " ORDER BY m.id DESC"
        report_data = query_db(sql, tuple(params))
        summary_metric = {'label': 'Total Listed Members', 'value': len(report_data)}

    elif report_type == 'trainers':
        sql = """
            SELECT t.*, COUNT(m.id) AS assigned_members_count
            FROM trainers t
            LEFT JOIN members m ON t.id = m.trainer_id
            WHERE 1=1
        """
        params = []
        if status_filter:
            sql += " AND t.status = %s"
            params.append(status_filter)
        sql += " GROUP BY t.id ORDER BY t.id DESC"
        report_data = query_db(sql, tuple(params))
        total_salary = sum(float(t['salary']) for t in report_data)
        summary_metric = {'label': 'Total Monthly Trainer Payroll', 'value': format_currency(total_salary)}

    elif report_type == 'payments':
        sql = """
            SELECT p.*, m.full_name AS member_name, m.phone AS member_phone
            FROM payments p
            JOIN members m ON p.member_id = m.id
            WHERE 1=1
        """
        params = []
        if status_filter:
            sql += " AND p.status = %s"
            params.append(status_filter)
        if start_date:
            sql += " AND p.payment_date >= %s"
            params.append(start_date)
        if end_date:
            sql += " AND p.payment_date <= %s"
            params.append(end_date)
        sql += " ORDER BY p.payment_date DESC"
        report_data = query_db(sql, tuple(params))
        total_rev = sum(float(p['amount']) for p in report_data if p['status'] == 'Paid')
        summary_metric = {'label': 'Total Collections in Period', 'value': format_currency(total_rev)}

    elif report_type == 'attendance':
        sql = """
            SELECT a.*, m.full_name AS member_name, m.phone AS member_phone
            FROM attendance a
            JOIN members m ON a.member_id = m.id
            WHERE 1=1
        """
        params = []
        if status_filter:
            sql += " AND a.status = %s"
            params.append(status_filter)
        if start_date:
            sql += " AND a.attendance_date >= %s"
            params.append(start_date)
        if end_date:
            sql += " AND a.attendance_date <= %s"
            params.append(end_date)
        sql += " ORDER BY a.attendance_date DESC"
        report_data = query_db(sql, tuple(params))
        summary_metric = {'label': 'Total Attendance Entries', 'value': len(report_data)}

    elif report_type == 'expiry':
        # Members expiring soon (within next 30 days) or already expired
        days = request.args.get('days', '30')
        sql = """
            SELECT m.*, p.plan_name, DATEDIFF(m.membership_end, CURDATE()) AS days_remaining
            FROM members m
            LEFT JOIN membership_plans p ON m.plan_id = p.id
            WHERE m.membership_end <= DATE_ADD(CURDATE(), INTERVAL %s DAY)
            ORDER BY m.membership_end ASC
        """
        report_data = query_db(sql, (days,))
        summary_metric = {'label': f'Expiring / Expired Members', 'value': len(report_data)}

    elif report_type == 'revenue':
        # Monthly Revenue grouped by month
        sql = """
            SELECT 
                DATE_FORMAT(payment_date, '%M %Y') AS month_name,
                DATE_FORMAT(payment_date, '%Y-%m') AS ym,
                COUNT(*) AS total_transactions,
                SUM(amount) AS total_collected
            FROM payments
            WHERE status = 'Paid'
            GROUP BY ym, month_name
            ORDER BY ym DESC
        """
        report_data = query_db(sql)
        cumulative = sum(float(r['total_collected']) for r in report_data)
        summary_metric = {'label': 'All-Time Total Collections', 'value': format_currency(cumulative)}

    return render_template(
        'reports/reports.html',
        report_type=report_type,
        start_date=start_date,
        end_date=end_date,
        status=status_filter,
        report_data=report_data,
        summary_metric=summary_metric
    )

# -------------------------------------------------------------
# CLI / App Initialization
# -------------------------------------------------------------
if __name__ == '__main__':
    print("=" * 60)
    print(" IronPulse Gym Management System Server Starting ")
    print("=" * 60)
    # Attempt auto database bootstrap if MySQL is reachable
    try:
        initialize_database()
    except Exception as e:
        print(f"[Warning] Auto-init skipped: {e}")
        
    app.run(debug=True, host='0.0.0.0', port=5000)
