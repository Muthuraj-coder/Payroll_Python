from datetime import datetime
from flask_login import UserMixin
from app.database import db, User as DBUser, Employee as DBEmployee, WorkRecord as DBWorkRecord

class User(UserMixin, DBUser):
    def get_id(self):
        return str(self.id)
    
    @staticmethod
    def get(user_id):
        return User.query.get(int(user_id))
    
    @staticmethod
    def get_by_username(username):
        return User.query.filter_by(username=username).first()

class Employee(DBEmployee):
    @staticmethod
    def get_all():
        return Employee.query.order_by(Employee.name).all()
    
    @staticmethod
    def get_by_id(employee_id):
        return Employee.query.get(employee_id)
    
    @staticmethod
    def create(name, hourly_rate, user_id):
        employee = Employee(name=name, hourly_rate=hourly_rate, user_id=user_id)
        db.session.add(employee)
        db.session.commit()
        return employee

class DailyWorkRecord(DBWorkRecord):
    @staticmethod
    def get_all():
        return DailyWorkRecord.query.order_by(DailyWorkRecord.date.desc()).all()
    
    @staticmethod
    def get_by_employee(employee_id):
        return DailyWorkRecord.query.filter_by(employee_id=employee_id).order_by(DailyWorkRecord.date.desc()).all()
    
    @staticmethod
    def create(employee_id, date, hours_worked, amount_earned):
        record = DailyWorkRecord(
            employee_id=employee_id,
            date=date,
            hours_worked=hours_worked,
            amount_earned=amount_earned
        )
        db.session.add(record)
        db.session.commit()
        return record 