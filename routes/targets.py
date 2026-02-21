from flask import Blueprint, render_template, request, redirect, url_for, current_app, jsonify
from models import db, Target
from monitor import start_monitor, stop_monitor
from routes.auth import login_required

targets_bp = Blueprint('targets', __name__)

API_KEY = "meowmeowmeow"

@targets_bp.route('/api/targets', methods=['POST'])
def api_add_target():
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({'error': 'Unauthorized'}), 401
    
    provided_key = auth_header[7:]
    if provided_key != API_KEY:
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Invalid JSON'}), 400
    
    ip = data.get('ip', '').strip()
    port = data.get('port')
    key = data.get('key', '').strip()
    delimiter = data.get('delimiter', '').strip()
    
    if not ip or not port or not key or not delimiter:
        return jsonify({'error': 'Missing required fields: ip, port, key, delimiter'}), 400
    
    try:
        port = int(port)
        if port < 1 or port > 65535:
            return jsonify({'error': 'Port must be between 1 and 65535'}), 400
    except (ValueError, TypeError):
        return jsonify({'error': 'Invalid port number'}), 400
    
    existing = Target.query.filter_by(ip=ip, port=port).first()
    if existing:
        return jsonify({'error': 'Target already exists', 'target_id': existing.id}), 409
    
    target = Target(ip=ip, port=port, key=key, delimiter=delimiter)
    db.session.add(target)
    db.session.commit()
    
    start_monitor(target, current_app._get_current_object())
    
    return jsonify({
        'success': True,
        'target_id': target.id,
        'ip': target.ip,
        'port': target.port
    }), 201

@targets_bp.route('/add_target', methods=['GET', 'POST'])
@login_required
def add_target():
    if request.method == 'POST':
        bulk_input = request.form.get('bulk_input', '').strip()
        
        if bulk_input:
            lines = bulk_input.split('\n')
            added_count = 0
            errors = []
            added_targets = []
            
            for line_num, line in enumerate(lines, 1):
                line = line.strip()
                if not line:
                    continue
                
                parts = [p.strip() for p in line.split(',')]
                
                if len(parts) != 4:
                    errors.append(f"Line {line_num}: Invalid format (expected ip,port,key,delimiter)")
                    continue
                
                ip, port, key, delimiter = parts
                
                try:
                    port_int = int(port)
                    if port_int < 1 or port_int > 65535:
                        raise ValueError
                except ValueError:
                    errors.append(f"Line {line_num}: Invalid port")
                    continue
                
                if not ip or not key or not delimiter:
                    errors.append(f"Line {line_num}: Missing required fields")
                    continue
                
                target = Target(ip=ip, port=port_int, key=key, delimiter=delimiter)
                db.session.add(target)
                added_targets.append(target)
                added_count += 1
            
            db.session.commit()
            
            for target in added_targets:
                start_monitor(target, current_app._get_current_object())
            
            if errors:
                return render_template('add_target.html', 
                                     success=f"{added_count} targets added successfully", 
                                     errors=errors)
            else:
                return redirect(url_for('connections.connections'))
        
        ip = request.form.get('ip', '').strip()
        port = request.form.get('port', '').strip()
        
        delimiter_type = request.form.get('delimiter_type', '')
        custom_delimiter = request.form.get('custom_delimiter', '').strip()
        
        key_type = request.form.get('key_type', '')
        custom_key = request.form.get('custom_key', '').strip()
        
        if delimiter_type == 'custom':
            delimiter = custom_delimiter
        else:
            delimiter = delimiter_type
        
        if key_type == 'custom':
            key = custom_key
        else:
            key = key_type
        
        if not ip or not port or not delimiter or not key:
            return render_template('add_target.html', error='All fields required')
        
        try:
            port = int(port)
            if port < 1 or port > 65535:
                raise ValueError
        except ValueError:
            return render_template('add_target.html', error='Invalid port')
        
        target = Target(ip=ip, port=port, key=key, delimiter=delimiter)
        db.session.add(target)
        db.session.commit()
        
        start_monitor(target, current_app._get_current_object())
        
        return redirect(url_for('connections.connections'))
    
    return render_template('add_target.html')

@targets_bp.route('/target/<int:target_id>/start', methods=['POST'])
@login_required
def start_target(target_id):
    target = Target.query.get_or_404(target_id)
    start_monitor(target, current_app._get_current_object())
    return redirect(url_for('connections.connections'))

@targets_bp.route('/target/<int:target_id>/stop', methods=['POST'])
@login_required
def stop_target(target_id):
    target = Target.query.get_or_404(target_id)
    stop_monitor(target.id)
    return redirect(url_for('connections.connections'))

@targets_bp.route('/target/<int:target_id>/reconnect', methods=['POST'])
@login_required
def reconnect_target(target_id):
    target = Target.query.get_or_404(target_id)
    stop_monitor(target.id)
    start_monitor(target, current_app._get_current_object())
    return redirect(url_for('connections.connections'))

@targets_bp.route('/target/<int:target_id>/delete', methods=['POST'])
@login_required
def delete_target(target_id):
    target = Target.query.get_or_404(target_id)
    stop_monitor(target.id)
    db.session.delete(target)
    db.session.commit()
    return redirect(url_for('connections.connections'))