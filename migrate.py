#!/usr/bin/env python3
"""
Database migration script for Render deployment
"""
from app import create_app
from app.database import init_db
from app.config import Config

def setup_database():
    """Initialize database tables and create admin user"""
    app = create_app()
    
    with app.app_context():
        # Initialize database (this will create tables and admin user)
        init_db()
        print("Database initialization completed!")
        print(f"Admin user '{Config.ADMIN_USERNAME}' is ready!")

if __name__ == '__main__':
    setup_database() 