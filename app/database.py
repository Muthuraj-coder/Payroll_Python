from flask import g, current_app
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash
import os
from datetime import datetime
from app.config import Config

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=True)
    
    def set_password(self, password):
        self.password = generate_password_hash(password)
    
    def check_password(self, password):
        from werkzeug.security import check_password_hash
        return check_password_hash(self.password, password)

class Employee(db.Model):
    __tablename__ = 'employees'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    hourly_rate = db.Column(db.Float, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    # Relationship
    user = db.relationship('User', backref='employee', uselist=False)
    work_records = db.relationship('WorkRecord', backref='employee', lazy=True)

class WorkRecord(db.Model):
    __tablename__ = 'work_records'
    
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    hours_worked = db.Column(db.Float, nullable=False)
    amount_earned = db.Column(db.Float, nullable=False)

class Report(db.Model):
    __tablename__ = 'reports'
    
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=True)
    report_type = db.Column(db.String(50), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    content = db.Column(db.Text, nullable=False)
    date_created = db.Column(db.DateTime, default=datetime.utcnow)

def get_db_path():
    """Get the path to the SQLite database file."""
    return Config.DATABASE_PATH

def get_db():
    """Get the database connection for the current application context."""
    if not hasattr(g, 'db'):
        # Ensure the instance directory exists
        os.makedirs(os.path.dirname(get_db_path()), exist_ok=True)
        
        g.db = SQLAlchemy(app)
    return g.db

def close_db(e=None):
    """Close the database connection."""
    db = g.pop('db', None)
    if db is not None:
        db.session.close()

def init_db():
    """Initialize the database with required tables and admin user."""
    from app.config import Config
    
    # Create all tables
    db.create_all()
    
    # Check if admin user exists
    admin_user = User.query.filter_by(username=Config.ADMIN_USERNAME).first()
    
    if not admin_user:
        # Create default admin user
        admin_user = User(
            username=Config.ADMIN_USERNAME,
            is_admin=True
        )
        admin_user.set_password(Config.ADMIN_PASSWORD)
        
        db.session.add(admin_user)
        db.session.commit()
        print(f"Admin user '{Config.ADMIN_USERNAME}' created successfully!")
    else:
        print(f"Admin user '{Config.ADMIN_USERNAME}' already exists!")
    
    print("Database initialization completed!")

def query_db(query, args=(), one=False):
    """Execute a query and return the results."""
    db = get_db()
    cursor = db.session.execute(query, args)
    rv = cursor.fetchall()
    cursor.close()
    return (rv[0] if rv else None) if one else rv

def execute_db(query, args=()):
    """Execute a query that modifies the database."""
    db = get_db()
    cursor = db.session.execute(query, args)
    db.session.commit()
    cursor.close()
    return cursor.lastrowid 