from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app.database import query_db, execute_db

class User(UserMixin):
    def __init__(self, user_id, username, password, is_admin, employee_id=None):
        self.id = user_id
        self.username = username
        self.password = password
        self.is_admin = bool(is_admin)  # Convert to boolean
        self.employee_id = employee_id

    @staticmethod
    def get(user_id):
        user_data = query_db(
            "SELECT * FROM users WHERE id = ?",
            (user_id,),
            one=True
        )
        if user_data:
            return User(
                user_id=user_data['id'],
                username=user_data['username'],
                password=user_data['password'],
                is_admin=bool(user_data['is_admin']),
                employee_id=user_data['employee_id']
            )
        return None

    @staticmethod
    def get_by_username(username):
        user_data = query_db(
            "SELECT * FROM users WHERE username = ?",
            (username,),
            one=True
        )
        if user_data:
            return User(
                user_id=user_data['id'],
                username=user_data['username'],
                password=user_data['password'],
                is_admin=bool(user_data['is_admin']),
                employee_id=user_data['employee_id']
            )
        return None

    def set_password(self, password):
        """Hash and set the user's password"""
        self.password = generate_password_hash(password)
        execute_db(
            "UPDATE users SET password = ? WHERE id = ?",
            (self.password, self.id)
        )
        
    def check_password(self, password):
        """Check if the provided password matches the hashed password"""
        return check_password_hash(self.password, password)

    def get_employee(self):
        """Get the associated employee record if this is an employee user"""
        if self.employee_id:
            employee_data = query_db(
                "SELECT * FROM employees WHERE id = ?",
                (self.employee_id,),
                one=True
            )
            if employee_data:
                return Employee(**dict(employee_data))
        return None

class Employee:
    def __init__(self, id, name, hourly_rate, user_id):
        self.id = id
        self.name = name
        self.hourly_rate = hourly_rate
        self.user_id = user_id

    @staticmethod
    def get_all():
        employees = query_db("SELECT * FROM employees ORDER BY name")
        return [Employee(**dict(emp)) for emp in employees]

    @staticmethod
    def get_by_id(employee_id):
        employee = query_db(
            "SELECT * FROM employees WHERE id = ?",
            (employee_id,),
            one=True
        )
        if employee:
            return Employee(**dict(employee))
        return None

    @staticmethod
    def create(name, hourly_rate, user_id):
        employee_id = execute_db(
            "INSERT INTO employees (name, hourly_rate, user_id) VALUES (?, ?, ?)",
            (name, hourly_rate, user_id)
        )
        return Employee(employee_id, name, hourly_rate, user_id)

class DailyWorkRecord:
    def __init__(self, id, employee_id, date, hours_worked, amount_earned):
        self.id = id
        self.employee_id = employee_id
        self.date = date
        self.hours_worked = hours_worked
        self.amount_earned = amount_earned

    @staticmethod
    def get_all():
        records = query_db("SELECT * FROM daily_work_records ORDER BY date DESC")
        return [DailyWorkRecord(**dict(record)) for record in records]

    @staticmethod
    def get_by_employee(employee_id):
        records = query_db(
            "SELECT * FROM daily_work_records WHERE employee_id = ? ORDER BY date DESC",
            (employee_id,)
        )
        return [DailyWorkRecord(**dict(record)) for record in records]

    @staticmethod
    def create(employee_id, date, hours_worked, amount_earned):
        record_id = execute_db(
            "INSERT INTO daily_work_records (employee_id, date, hours_worked, amount_earned) VALUES (?, ?, ?, ?)",
            (employee_id, date, hours_worked, amount_earned)
        )
        return DailyWorkRecord(record_id, employee_id, date, hours_worked, amount_earned) 