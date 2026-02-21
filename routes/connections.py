from flask import Blueprint, render_template, request
from models import Target, ConnectionLog
from routes.auth import login_required

connections_bp = Blueprint('connections', __name__)

@connections_bp.route('/connections')
@login_required
def connections():
    status_filter = request.args.get('status', 'online')
    
    query = Target.query
    
    if status_filter in ['online', 'offline', 'connecting']:
        query = query.filter_by(status=status_filter)
    
    targets = query.all()
    
    return render_template('connections.html', targets=targets, status_filter=status_filter)

@connections_bp.route('/connection_logs/<int:target_id>')
@login_required
def connection_logs(target_id):
    target = Target.query.get_or_404(target_id)
    page = request.args.get('page', 1, type=int)
    per_page = 50
    
    pagination = ConnectionLog.query.filter_by(target_id=target_id).order_by(ConnectionLog.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return render_template('connection_logs.html', target=target, pagination=pagination)