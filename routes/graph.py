from flask import Blueprint, render_template, jsonify
from models import Target, Connection, FileHash, URL
from collections import defaultdict
from routes.auth import login_required

graph_bp = Blueprint('graph', __name__)

@graph_bp.route('/graph')
@login_required
def graph():
    return render_template('graph.html')

@graph_bp.route('/api/graph_data')
@login_required
def graph_data():
    nodes = []
    edges = []
    
    targets = Target.query.all()
    ip_to_connections = defaultdict(list)
    
    for target in targets:
        connections = Connection.query.filter_by(target_id=target.id).all()
        for conn in connections:
            ip_to_connections[target.ip].append(conn.id)
    
    for ip in ip_to_connections:
        nodes.append({
            'id': ip,
            'label': ip,
            'group': 'ip'
        })
    
    hash_to_ips = defaultdict(set)
    url_to_ips = defaultdict(set)
    
    for ip, conn_ids in ip_to_connections.items():
        for conn_id in conn_ids:
            file_hashes = FileHash.query.filter_by(connection_id=conn_id).all()
            for fh in file_hashes:
                hash_to_ips[fh.file_hash].add(ip)
            
            urls = URL.query.filter_by(connection_id=conn_id).all()
            for url in urls:
                url_to_ips[url.url].add(ip)
    
    for file_hash, ips in hash_to_ips.items():
        if len(ips) > 1:
            hash_label = file_hash[:32]
            nodes.append({
                'id': f'hash_{file_hash}',
                'label': hash_label,
                'group': 'hash'
            })
            for ip in ips:
                edges.append({
                    'from': ip,
                    'to': f'hash_{file_hash}'
                })
    
    for url, ips in url_to_ips.items():
        if len(ips) > 1:
            url_label = url[:64]
            nodes.append({
                'id': f'url_{url}',
                'label': url_label,
                'group': 'url'
            })
            for ip in ips:
                edges.append({
                    'from': ip,
                    'to': f'url_{url}'
                })
    
    return jsonify({'nodes': nodes, 'edges': edges})