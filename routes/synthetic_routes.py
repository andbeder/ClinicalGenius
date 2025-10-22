"""
Synthetic claims data generator routes (legacy functionality)
These routes support the original synthetic data generation feature
"""
from flask import Blueprint, request, jsonify
import json
import os


synthetic_bp = Blueprint('synthetic', __name__)

# Mutable container for client getter functions (set by main app)
_client_funcs = {
    'get_sf_client': None,
    'get_lm_client': None
}


def get_sf_client_func():
    """Get Salesforce client using configured function"""
    if _client_funcs['get_sf_client'] is None:
        raise NotImplementedError("SF client getter not configured")
    return _client_funcs['get_sf_client']()


def get_lm_client_func():
    """Get LM client using configured function"""
    if _client_funcs['get_lm_client'] is None:
        raise NotImplementedError("LM client getter not configured")
    return _client_funcs['get_lm_client']()


@synthetic_bp.route('/api/authenticate', methods=['POST'])
def authenticate():
    """Authenticate to Salesforce"""
    try:
        client = get_sf_client_func()
        success = client.authenticate()
        if success:
            return jsonify({'success': True, 'message': 'Successfully authenticated to Salesforce'})
        else:
            return jsonify({'success': False, 'error': 'Authentication failed'}), 401
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@synthetic_bp.route('/api/settings', methods=['GET'])
def get_settings():
    """Get application settings"""
    try:
        settings_file = 'settings.json'
        if os.path.exists(settings_file):
            with open(settings_file, 'r') as f:
                settings = json.load(f)
        else:
            # Default settings
            settings = {
                'provider': os.getenv('LLM_PROVIDER', 'lm_studio'),
                'endpoint': os.getenv('LM_STUDIO_ENDPOINT', 'http://localhost:1234'),
                'model': os.getenv('LLM_MODEL', 'gpt-4o-mini'),
                'temperature': float(os.getenv('LLM_TEMPERATURE', '0.7')),
                'max_tokens': int(os.getenv('LLM_MAX_TOKENS', '4000')),
                'timeout': 60
            }
        return jsonify({'success': True, 'settings': settings})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@synthetic_bp.route('/api/settings', methods=['POST'])
def save_settings():
    """Save application settings"""
    try:
        data = request.json
        settings_file = 'settings.json'

        # Save to file
        with open(settings_file, 'w') as f:
            json.dump(data, f, indent=2)

        # Update LM client configuration
        lm_client = get_lm_client_func()
        lm_client.update_config(data)

        return jsonify({'success': True, 'message': 'Settings saved successfully'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@synthetic_bp.route('/api/test-connection', methods=['POST'])
def test_connection():
    """Test connection to LLM provider"""
    try:
        lm_client = get_lm_client_func()
        result = lm_client.test_connection()
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@synthetic_bp.route('/api/fields', methods=['GET'])
def get_fields():
    """Get all fields from Claim__c object"""
    try:
        client = get_sf_client_func()
        fields = client.get_claim_fields()
        return jsonify({'success': True, 'fields': fields})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@synthetic_bp.route('/api/records', methods=['GET'])
def get_records():
    """Get all Claim__c records"""
    try:
        client = get_sf_client_func()
        records = client.get_all_records()
        return jsonify({'success': True, 'records': records, 'count': len(records)})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@synthetic_bp.route('/api/record/<record_id>', methods=['GET'])
def get_record(record_id):
    """Get a specific Claim__c record"""
    try:
        client = get_sf_client_func()
        record = client.get_record(record_id)
        return jsonify({'success': True, 'record': record})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# NOTE: The following routes (test-prompt, batch-generate, create-record, lm-studio/config)
# would be fully implemented here by copying from app.py lines 212-352
# For now, providing stubs to demonstrate the structure

@synthetic_bp.route('/api/test-prompt', methods=['POST'])
def test_prompt():
    """Test prompt on a single record - to be migrated"""
    return jsonify({'success': False, 'error': 'Not yet implemented'}), 501


@synthetic_bp.route('/api/batch-generate', methods=['POST'])
def batch_generate():
    """Batch generate synthetic data - to be migrated"""
    return jsonify({'success': False, 'error': 'Not yet implemented'}), 501


@synthetic_bp.route('/api/create-record', methods=['POST'])
def create_record():
    """Create a new Claim__c record - to be migrated"""
    return jsonify({'success': False, 'error': 'Not yet implemented'}), 501


@synthetic_bp.route('/api/lm-studio/config', methods=['GET', 'POST'])
def lm_studio_config():
    """Get or update LM Studio configuration - to be migrated"""
    return jsonify({'success': False, 'error': 'Not yet implemented'}), 501
