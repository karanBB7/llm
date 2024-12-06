from functools import wraps
from flask import jsonify, request
from base64 import b64decode
from config.scraper_config import AUTH_TOKEN

def require_basic_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return jsonify({'error': 'No authorization header'}), 401
        
        try:
            auth_type, auth_string = auth_header.split(' ', 1)
            if auth_type.lower() != 'basic':
                return jsonify({'error': 'Invalid authorization type'}), 401
            
            decoded = b64decode(auth_string).decode('utf-8')
            username, password = decoded.split(':', 1)
            
            if password != AUTH_TOKEN:
                return jsonify({'error': 'Invalid credentials'}), 401
                
        except Exception as e:
            return jsonify({'error': 'Invalid authorization format'}), 401
            
        return f(*args, **kwargs)
    return decorated