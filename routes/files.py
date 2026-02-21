from flask import Blueprint, render_template, request, send_file
from models import PacketLog
from pathlib import Path
from routes.auth import login_required

files_bp = Blueprint('files', __name__)

@files_bp.route('/files')
@login_required
def files():
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    pagination = PacketLog.query.order_by(PacketLog.captured_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return render_template('files.html', pagination=pagination)

@files_bp.route('/download/<int:log_id>')
@login_required
def download_file(log_id):
    log = PacketLog.query.get_or_404(log_id)
    
    if not log.file_path:
        return 'No file available', 404
    
    file_path = Path(log.file_path)
    if not file_path.exists():
        return 'File not found', 404
    
    return send_file(file_path, as_attachment=True, download_name=file_path.name)

@files_bp.route('/preview/<int:log_id>')
@login_required
def preview_file(log_id):
    log = PacketLog.query.get_or_404(log_id)
    return render_template('preview.html', log=log)