from flask import Flask
from models import db, User, Target
from monitor import start_all_monitors, monitors, start_monitor
import os
import threading
import time

app = Flask(__name__)
app.config['SECRET_KEY'] = 'xJ8kL9mN2pQ4rS6tU8vW0yZ1aB3cD5eF7gH9iJ0kL2mN4pQ6rS8tU0vW2yZ4aB6c'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///c2monitor.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

retry_thread = None
retry_running = False

def retry_failed_connections():
    global retry_running
    retry_running = True
    
    while retry_running:
        time.sleep(120)
        
        try:
            with app.app_context():
                targets = Target.query.filter_by(status='offline').all()
                
                for target in targets:
                    if target.id not in monitors:
                        start_monitor(target, app)
        except:
            pass

def init_db():
    with app.app_context():
        db.create_all()
        if not User.query.filter_by(username='admin').first():
            admin = User(username='admin')
            admin.set_password('xwormhatermeow123092')
            db.session.add(admin)
            db.session.commit()
        
        if os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
            start_all_monitors(app)
            
            global retry_thread
            if retry_thread is None:
                retry_thread = threading.Thread(target=retry_failed_connections, daemon=True)
                retry_thread.start()

from routes import register_blueprints
register_blueprints(app)

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)