from flask import Flask
from flask_login import LoginManager
from app.database import init_db
from app.config import Config

login_manager = LoginManager()

def create_app():
    app = Flask(__name__)
    
    # Load configuration
    app.config.from_object(Config)
    
    # Initialize Flask-Login
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    
    # Initialize database within application context
    with app.app_context():
        init_db()
    
    # Register blueprints
    from app.routes import auth, main, admin, employee
    app.register_blueprint(auth.bp)
    app.register_blueprint(main.bp)
    app.register_blueprint(admin.bp)
    app.register_blueprint(employee.bp)
    
    return app

@login_manager.user_loader
def load_user(user_id):
    from app.models import User
    return User.get(user_id) 