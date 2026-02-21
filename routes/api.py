from flask import Blueprint, jsonify
from models import db, Target, Connection
from sqlalchemy import func
from routes.auth import login_required

api_bp = Blueprint('api', __name__)

@api_bp.route('/api/country_data')
@login_required
def country_data():
    country_stats = db.session.query(
        Connection.country,
        func.count(Connection.id).label('count')
    ).filter(Connection.country.isnot(None)).group_by(Connection.country).all()
    
    data = [{'country': row.country, 'count': row.count} for row in country_stats]
    return jsonify(data)

@api_bp.route('/api/connection_stats')
@login_required
def connection_stats():
    country_stats = db.session.query(
        Connection.country,
        func.count(Connection.id).label('count')
    ).filter(Connection.country.isnot(None)).group_by(Connection.country).all()
    
    target_stats = db.session.query(
        Target.ip,
        func.count(Connection.id).label('count')
    ).join(Connection, Connection.target_id == Target.id).group_by(Target.ip).all()
    
    return jsonify({
        'by_country': [{'label': row.country, 'value': row.count} for row in country_stats],
        'by_target': [{'label': row.ip, 'value': row.count} for row in target_stats]
    })