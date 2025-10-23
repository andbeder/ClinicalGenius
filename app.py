#!/usr/bin/env python3
"""
Clinical Genius - Flask Application
Refactored version with modular blueprints
"""

from flask import Flask, render_template, request, abort
import os
from dotenv import load_dotenv

# Import database initialization
from database.db import init_db, migrate_db

# Import clients
from salesforce_client import SalesforceClient
from lm_studio_client import LMStudioClient
from prompt_engine import PromptEngine

# Import audit logger
from audit_logger import get_audit_logger, AuditLogger

# Import blueprints
from routes.dataset_routes import dataset_bp
from routes.analysis_routes import analysis_bp
from routes.synthetic_routes import synthetic_bp

# Load environment variables
load_dotenv()

# Create Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

# Initialize audit logger
audit_logger = get_audit_logger()

# User context middleware
@app.before_request
def set_user_context():
    """
    Set current user context for audit logging
    Uses SFDC_USERNAME from environment as the authenticated user
    """
    # Skip check for health endpoint
    if request.endpoint == 'health_check':
        return None

    # Get client IP
    client_ip = request.remote_addr

    # Allow localhost only
    if client_ip not in ['127.0.0.1', 'localhost', '::1']:
        app.logger.warning(f"Access denied from {client_ip} - only localhost allowed")
        audit_logger.log_access_denied(
            f"Non-localhost access attempt from {client_ip}",
            ip_address=client_ip
        )
        abort(403, description="Access denied: Only localhost access is permitted")

    # Set user context from SFDC_USERNAME for audit logging
    # This satisfies HIPAA unique user identification requirement
    from flask import g
    g.current_user = os.environ.get('SFDC_USERNAME', 'unknown')
    g.user_ip = client_ip


# Security headers middleware
@app.after_request
def set_security_headers(response):
    """
    Add HIPAA-compliant security headers to all responses
    Provides defense-in-depth protection
    """
    # HTTP Strict Transport Security (HSTS)
    # Forces HTTPS for 1 year, includes subdomains
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'

    # Prevent MIME type sniffing
    response.headers['X-Content-Type-Options'] = 'nosniff'

    # Prevent clickjacking - don't allow embedding in frames
    response.headers['X-Frame-Options'] = 'DENY'

    # XSS Protection (legacy header, but still useful)
    response.headers['X-XSS-Protection'] = '1; mode=block'

    # Content Security Policy
    # Restrict resource loading to prevent XSS attacks
    csp_policy = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
        "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
        "font-src 'self' https://cdn.jsdelivr.net; "
        "img-src 'self' data:; "
        "connect-src 'self'; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self'"
    )
    response.headers['Content-Security-Policy'] = csp_policy

    # Referrer Policy - don't leak URLs to external sites
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'

    # Permissions Policy (formerly Feature-Policy)
    # Disable unnecessary browser features
    permissions_policy = (
        "geolocation=(), "
        "microphone=(), "
        "camera=(), "
        "payment=(), "
        "usb=(), "
        "magnetometer=(), "
        "gyroscope=(), "
        "accelerometer=()"
    )
    response.headers['Permissions-Policy'] = permissions_policy

    return response

# Initialize clients
sf_client = None
lm_client = LMStudioClient()
prompt_engine = PromptEngine()


def get_sf_client():
    """Get or create Salesforce client with authentication"""
    global sf_client
    if sf_client is None:
        sf_client = SalesforceClient()
        # Authenticate on first use
        sf_client.authenticate()
    return sf_client


def load_settings():
    """Load settings from settings.json file"""
    import json
    settings_file = 'settings.json'
    if os.path.exists(settings_file):
        with open(settings_file, 'r') as f:
            settings = json.load(f)
    else:
        # Default settings from environment
        settings = {
            'provider': os.getenv('LLM_PROVIDER', 'lm_studio'),
            'endpoint': os.getenv('LM_STUDIO_ENDPOINT', 'http://localhost:1234'),
            'model': os.getenv('LLM_MODEL', 'gpt-4o-mini'),
            'temperature': float(os.getenv('LLM_TEMPERATURE', '0.7')),
            'max_tokens': int(os.getenv('LLM_MAX_TOKENS', '4000')),
            'timeout': 60
        }
    return settings


# Configure blueprints with client accessor functions
from routes import dataset_routes, analysis_routes, synthetic_routes
dataset_routes._client_funcs['get_sf_client'] = get_sf_client
analysis_routes._client_funcs['get_sf_client'] = get_sf_client
analysis_routes._client_funcs['get_lm_client'] = lambda: lm_client
analysis_routes._client_funcs['load_settings'] = load_settings
synthetic_routes._client_funcs['get_sf_client'] = get_sf_client
synthetic_routes._client_funcs['get_lm_client'] = lambda: lm_client

# Register blueprints
app.register_blueprint(dataset_bp)
app.register_blueprint(analysis_bp)
app.register_blueprint(synthetic_bp)


# Main page routes
@app.route('/')
def index():
    """Main CRM Analytics Prompt Execution Application"""
    return render_template('main.html')


@app.route('/synthetic')
def synthetic():
    """Synthetic Claims Data Generator"""
    return render_template('index.html')


@app.route('/health')
def health_check():
    """Health check endpoint (no auth required)"""
    return {'status': 'healthy', 'localhost_only': True}, 200


@app.route('/api/current-user')
def get_current_user():
    """Get current user information for UI display"""
    from flask import g, jsonify
    user = getattr(g, 'current_user', 'unknown')
    return jsonify({
        'username': user,
        'source': 'SFDC_USERNAME environment variable',
        'authenticated': user != 'unknown'
    })


# Initialize database on startup
init_db()
migrate_db()


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 4000))
    debug = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    use_https = os.environ.get('USE_HTTPS', 'True').lower() == 'true'

    # SSL configuration
    ssl_context = None
    if use_https:
        ssl_cert_path = 'ssl/localhost.crt'
        ssl_key_path = 'ssl/localhost.key'

        if os.path.exists(ssl_cert_path) and os.path.exists(ssl_key_path):
            ssl_context = (ssl_cert_path, ssl_key_path)
            protocol = 'https'
            print("[SSL] SSL/TLS Enabled - Using self-signed certificate")
        else:
            print(f"[WARNING] SSL certificate not found at {ssl_cert_path}")
            print(f"          Run: python generate_ssl_cert.py")
            print(f"          Starting without HTTPS...")
            protocol = 'http'
    else:
        protocol = 'http'
        print("[WARNING] HTTPS disabled via USE_HTTPS=false in environment")

    print(f"Starting Clinical Genius on localhost:{port}")
    print(f"Access URL: {protocol}://localhost:{port}")
    print(f"Access restricted to: localhost only (127.0.0.1)")
    print(f"Debug mode: {debug}")

    app.run(host='127.0.0.1', port=port, debug=debug, ssl_context=ssl_context)
