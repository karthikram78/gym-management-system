"""
IronPulse Gym Management System - Automated Test Verification Script
Tests all core modules, authentication, routes, and database operations.
"""
import sys
from app import app
from utils.database import initialize_database

def run_tests():
    print("=" * 60)
    print(" Starting IronPulse Test Verification Suite ")
    print("=" * 60)

    initialize_database()

    with app.test_client() as client:
        # 1. Test Login Page GET
        res = client.get('/login')
        assert res.status_code == 200, f"Login GET failed: {res.status_code}"
        print("[PASS] 1. GET /login rendered successfully")

        # 2. Test Login POST (Authentication & Session)
        res = client.post('/login', data={'username': 'admin', 'password': 'admin123'}, follow_redirects=True)
        assert res.status_code == 200, f"Login POST failed: {res.status_code}"
        assert b'Executive Dashboard' in res.data or b'Dashboard' in res.data, "Dashboard not loaded"
        print("[PASS] 2. POST /login authenticated admin session successfully")

        # 3. Test Dashboard Data
        res = client.get('/dashboard')
        assert res.status_code == 200
        assert b'Active Members' in res.data
        assert b'Monthly Revenue' in res.data
        print("[PASS] 3. GET /dashboard dynamic statistics and charts loaded")

        # 4. Test Members Directory
        res = client.get('/members')
        assert res.status_code == 200
        assert b'Rahul Verma' in res.data
        print("[PASS] 4. GET /members directory rendered")

        # 5. Test Add Member (CRUD: Create)
        member_payload = {
            'full_name': 'Test Trainee Apex',
            'email': 'apex.trainee@example.com',
            'phone': '9876543299',
            'gender': 'Male',
            'dob': '1998-05-10',
            'address': 'Test Avenue, Suite 100',
            'joining_date': '2025-01-01',
            'plan_id': '1',
            'trainer_id': '1',
            'membership_start': '2025-01-01',
            'status': 'Active'
        }
        res = client.post('/members/add', data=member_payload, follow_redirects=True)
        assert res.status_code == 200
        assert b'Test Trainee Apex' in res.data
        print("[PASS] 5. POST /members/add successfully created new member")

        # 6. Test Trainers Management
        res = client.get('/trainers')
        assert res.status_code == 200
        assert b'Vikram Rathore' in res.data
        print("[PASS] 6. GET /trainers directory verified")

        # 7. Test Membership Plans
        res = client.get('/plans')
        assert res.status_code == 200
        assert b'Monthly Plan' in res.data
        assert b'Yearly Plan' in res.data
        print("[PASS] 7. GET /plans pricing packages verified")

        # 8. Test Payments and Printable Receipt
        res = client.get('/payments')
        assert res.status_code == 200
        res = client.get('/payments/receipt/1001')
        assert res.status_code == 200
        assert b'Official Payment Receipt' in res.data
        print("[PASS] 8. GET /payments and /payments/receipt verified")

        # 9. Test Attendance Desk
        res = client.get('/attendance')
        assert res.status_code == 200
        print("[PASS] 9. GET /attendance desk and logs verified")

        # 10. Test Reports (All 6 views)
        for rtype in ['members', 'trainers', 'payments', 'attendance', 'expiry', 'revenue']:
            res = client.get(f'/reports?type={rtype}')
            assert res.status_code == 200, f"Report {rtype} failed"
        print("[PASS] 10. All 6 report modules rendered successfully")

    print("=" * 60)
    print(" ALL 10 TEST SUITES COMPLETED WITH 100% SUCCESS! ")
    print("=" * 60)

if __name__ == '__main__':
    run_tests()
