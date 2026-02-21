from flask import Blueprint, render_template, jsonify, Response, stream_with_context
from flask_cors import cross_origin
from models import db, Target, Connection, FileHash, PacketLog
from sqlalchemy import func, text
from datetime import datetime, timezone
from routes.auth import login_required
from events import network_events
import json
import queue

dashboard_bp = Blueprint('dashboard', __name__)

def get_target_location(ip):
    result = db.session.execute(
        text("SELECT country_code FROM ip_geolocation WHERE ip = :ip LIMIT 1"),
        {"ip": ip}
    ).fetchone()
    
    if result and result[0]:
        return result[0]
    return None

@dashboard_bp.route('/dashboard')
@login_required
def dashboard():
    total_targets = Target.query.count()
    online_targets = Target.query.filter_by(status='online').count()
    total_connections = Connection.query.count()
    total_files = PacketLog.query.count()
    
    return render_template('dashboard.html',
                         total_targets=total_targets,
                         online_targets=online_targets,
                         total_connections=total_connections,
                         total_files=total_files)

@dashboard_bp.route('/api/dashboard_stats')
@cross_origin()
def dashboard_stats():
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    
    files_by_country = db.session.query(
        Connection.country,
        func.count(FileHash.id).label('count')
    ).join(FileHash, Connection.id == FileHash.connection_id)\
     .filter(Connection.country.isnot(None))\
     .group_by(Connection.country)\
     .order_by(func.count(FileHash.id).desc())\
     .limit(5)\
     .all()
    
    connections_today = db.session.query(
        Target.ip,
        func.count(Connection.id).label('count')
    ).join(Connection, Target.id == Connection.target_id)\
     .filter(Connection.connected_at >= today_start)\
     .group_by(Target.ip)\
     .order_by(func.count(Connection.id).desc())\
     .limit(5)\
     .all()
    
    files_result = [{'label': row[0] or 'Unknown', 'value': row[1]} for row in files_by_country]
    
    if not files_result:
        files_result = [{'label': 'NooooOO files yet>:3', 'value': 0}]
    
    return jsonify({
        'files_by_country': files_result,
        'connections_today': [{'label': row[0], 'value': row[1]} for row in connections_today]
    })

@dashboard_bp.route('/api/map_data')
@login_required
def map_data():
    return jsonify([])

@dashboard_bp.route('/api/targets')
@cross_origin()
def targets():
    targets = Target.query.all()
    
    data = []
    for target in targets:
        country = get_target_location(target.ip)
        if country:
            data.append({
                'ip': target.ip,
                'country': country,
                'online': target.status == 'online'
            })
    
    return jsonify(data)

@dashboard_bp.route('/api/live_updates')
@cross_origin()
def live_updates():
    def generate():
        yield f"data: {json.dumps({'type': 'connected', 'status': 'ok'})}\n\n"
        
        try:
            last_file_id = PacketLog.query.order_by(PacketLog.id.desc()).first()
            last_file_id = last_file_id.id if last_file_id else 0
            
            last_connection_id = Connection.query.order_by(Connection.id.desc()).first()
            last_connection_id = last_connection_id.id if last_connection_id else 0
            
            last_target_check = {}
            targets = Target.query.all()
            for target in targets:
                last_target_check[target.id] = target.status
            
            import time
            last_keepalive = time.time()
            
            while True:
                try:
                    event = network_events.get(timeout=1)
                    yield f"data: {json.dumps(event)}\n\n"
                except queue.Empty:
                    if time.time() - last_keepalive > 15:
                        yield ": keepalive\n\n"
                        last_keepalive = time.time()
                except GeneratorExit:
                    raise
                
                new_files = PacketLog.query.filter(PacketLog.id > last_file_id)\
                    .order_by(PacketLog.id.asc()).limit(5).all()
                
                if new_files:
                    last_file_id = new_files[-1].id
                    for log in new_files:
                        country = get_target_location(log.ip)
                        event_data = {
                            'type': 'new_file',
                            'ip': log.ip,
                            'hash': log.file_hash,
                            'timestamp': log.captured_at.isoformat(),
                            'country': country
                        }
                        yield f"data: {json.dumps(event_data)}\n\n"
                
                new_connections = Connection.query.filter(Connection.id > last_connection_id)\
                    .order_by(Connection.id.asc()).limit(10).all()
                
                if new_connections:
                    last_connection_id = new_connections[-1].id
                    for conn in new_connections:
                        target = Target.query.get(conn.target_id)
                        if target:
                            country = get_target_location(target.ip)
                            if country:
                                event_data = {
                                    'type': 'new_connection',
                                    'country': country,
                                    'ip': target.ip
                                }
                                yield f"data: {json.dumps(event_data)}\n\n"
                
                targets = Target.query.all()
                for target in targets:
                    if target.id not in last_target_check or last_target_check[target.id] != target.status:
                        last_target_check[target.id] = target.status
                        country = get_target_location(target.ip)
                        if country:
                            event_data = {
                                'type': 'target_status_change',
                                'ip': target.ip,
                                'country': country,
                                'online': target.status == 'online'
                            }
                            yield f"data: {json.dumps(event_data)}\n\n"
                        
        except GeneratorExit:
            raise
    
    return Response(stream_with_context(generate()), mimetype='text/event-stream', headers={
        'Cache-Control': 'no-cache',
        'X-Accel-Buffering': 'no',
        'Connection': 'keep-alive'
    })