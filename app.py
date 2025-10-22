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

# Network access control middleware
@app.before_request
def check_localhost_access():
    """Restrict access to localhost only"""
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


# Initialize database on startup
init_db()
migrate_db()


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 4000))
    debug = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'

    print(f"Starting Clinical Genius on localhost:{port}")
    print(f"Access restricted to: localhost only (127.0.0.1)")
    print(f"Debug mode: {debug}")

    app.run(host='127.0.0.1', port=port, debug=debug)
