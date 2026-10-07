from flask import Flask
from app.extensions import db, migrate

def create_app(config_class='config.Config'):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)    
    # Register blueprints (including Jaiharini's intelligence routes)
    from app.routes.link_routes import link_bp
    from app.routes.import_routes import import_bp
    from app.routes.health_routes import health_bp
    from app.routes.inbox_routes import inbox_bp
    app.register_blueprint(link_bp)
    app.register_blueprint(import_bp)
    app.register_blueprint(health_bp)
    app.register_blueprint(inbox_bp)
    
    with app.app_context():
        # Auto-create tables for local development
        db.create_all()

    @app.route('/')
    def index():
        return {"success": True, "message": "Welcome to LinkVault API. The backend is running successfully!"}, 200
        
    return app
