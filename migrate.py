#!/usr/bin/env python3
"""
Database migration script for Render deployment
"""
from app import create_app, db
from app.models import User, Employee, WorkRecord, PayrollRecord
from app.config import Config

def init_database():
    """Initialize database tables and create admin user"""
    app = create_app()
    
    with app.app_context():
        # Create all tables
        db.create_all()
        
        # Check if admin user exists
        admin_user = User.query.filter_by(username=Config.ADMIN_USERNAME).first()
        if not admin_user:
            # Create admin user
            admin_user = User(
                username=Config.ADMIN_USERNAME,
                password=Config.ADMIN_PASSWORD,
                role='admin'
            )
            db.session.add(admin_user)
            db.session.commit()
            print(f"Admin user '{Config.ADMIN_USERNAME}' created successfully!")
        else:
            print(f"Admin user '{Config.ADMIN_USERNAME}' already exists!")
        
        print("Database initialization completed!")

if __name__ == '__main__':
    init_database() 