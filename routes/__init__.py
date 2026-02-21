from routes.auth import auth_bp
from routes.dashboard import dashboard_bp
from routes.connections import connections_bp
from routes.targets import targets_bp
from routes.files import files_bp
from routes.graph import graph_bp
from routes.api import api_bp

def register_blueprints(app):
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(connections_bp)
    app.register_blueprint(targets_bp)
    app.register_blueprint(files_bp)
    app.register_blueprint(graph_bp)
    app.register_blueprint(api_bp)