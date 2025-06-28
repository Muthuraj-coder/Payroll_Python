from flask import g, current_app
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash
import os
from datetime import datetime
from app.config import Config

db = SQLAlchemy()

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
    """Initialize the database with required tables."""
    db = get_db()
    cursor = db.session.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            is_admin BOOLEAN DEFAULT 0,
            employee_id INTEGER
        )
    ''')

    cursor = db.session.execute('''
        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            hourly_rate REAL NOT NULL,
            user_id INTEGER,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')

    cursor = db.session.execute('''
        CREATE TABLE IF NOT EXISTS work_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id INTEGER NOT NULL,
            date DATE NOT NULL,
            hours_worked REAL NOT NULL,
            amount_earned REAL NOT NULL,
            FOREIGN KEY (employee_id) REFERENCES employees (id)
        )
    ''')

    cursor = db.session.execute('''
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id INTEGER,
            report_type TEXT NOT NULL,
            start_date DATE NOT NULL,
            end_date DATE NOT NULL,
            content TEXT NOT NULL,
            date_created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (employee_id) REFERENCES employees (id)
        )
    ''')

    try:
        # Start transaction
        db.session.execute("BEGIN")
        
        # Clean up any orphaned records
        db.session.execute("DELETE FROM work_records WHERE employee_id NOT IN (SELECT id FROM employees)")
        db.session.execute("DELETE FROM reports WHERE employee_id NOT IN (SELECT id FROM employees)")
        db.session.execute("DELETE FROM employees WHERE user_id NOT IN (SELECT id FROM users)")
        db.session.execute("UPDATE users SET employee_id = NULL WHERE employee_id NOT IN (SELECT id FROM employees)")
        
        # Check if admin user exists
        cursor = db.session.execute('SELECT id FROM users WHERE username = ? AND is_admin = 1', (Config.ADMIN_USERNAME,))
        admin_user = cursor.fetchone()
        
        if not admin_user:
            # Create default admin user
            admin_password_hash = generate_password_hash(Config.ADMIN_PASSWORD)
            db.session.execute('''
                INSERT INTO users (username, password, is_admin)
                VALUES (?, ?, 1)
            ''', (Config.ADMIN_USERNAME, admin_password_hash))
        
        # Commit all changes
        db.session.commit()
        
    except Exception as e:
        # Rollback on error
        db.session.rollback()
        raise e

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