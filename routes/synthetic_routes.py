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


@synthetic_bp.route('/api/test-prompt', methods=['POST'])
def test_prompt():
    """Test prompt on a single record"""
    try:
        from prompt_engine import PromptEngine

        data = request.json
        record_id = data.get('record_id')
        prompt_template = data.get('prompt_template')
        target_field = data.get('target_field')

        if not all([record_id, prompt_template]):
            return jsonify({'success': False, 'error': 'Missing required parameters'}), 400

        # Get the record
        sf_client = get_sf_client_func()
        record = sf_client.get_record(record_id)

        # Build the prompt
        prompt_engine = PromptEngine()
        prompt = prompt_engine.build_prompt(prompt_template, record)

        # Generate completion
        lm_client = get_lm_client_func()
        completion = lm_client.generate(prompt)

        return jsonify({
            'success': True,
            'prompt': prompt,
            'completion': completion,
            'record': record
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@synthetic_bp.route('/api/batch-generate', methods=['POST'])
def batch_generate():
    """Run batch generation - either update existing or create new records"""
    try:
        from prompt_engine import PromptEngine

        data = request.json
        prompt_template = data.get('prompt_template')
        target_field = data.get('target_field')
        mode = data.get('mode', 'update')  # 'update' or 'insert'
        insert_count = data.get('insert_count', 10)

        if not all([prompt_template, target_field]):
            return jsonify({'success': False, 'error': 'Missing required parameters'}), 400

        sf_client = get_sf_client_func()
        lm_client = get_lm_client_func()
        prompt_engine = PromptEngine()

        results = {
            'total': 0,
            'success': 0,
            'failed': 0,
            'errors': []
        }

        if mode == 'update':
            # Update existing records
            records = sf_client.get_all_records()
            results['total'] = len(records)

            for i, record in enumerate(records):
                try:
                    # Build prompt
                    prompt = prompt_engine.build_prompt(prompt_template, record)

                    # Generate completion
                    completion = lm_client.generate(prompt)

                    # Update Salesforce
                    sf_client.update_record(record['Id'], {target_field: completion})

                    results['success'] += 1
                    print(f"Updated {i+1}/{len(records)}: {record['Id']}")

                except Exception as e:
                    results['failed'] += 1
                    results['errors'].append({
                        'record_id': record['Id'],
                        'error': str(e)
                    })
                    print(f"Error updating {record['Id']}: {str(e)}")

        elif mode == 'insert':
            # Create new records
            results['total'] = insert_count

            for i in range(insert_count):
                try:
                    # For new records, we'll use an empty record as context
                    # The prompt should be written to not depend on existing field values
                    empty_record = {'Id': f'NEW_{i+1}'}

                    # Build prompt
                    prompt = prompt_engine.build_prompt(prompt_template, empty_record)

                    # Generate completion
                    completion = lm_client.generate(prompt)

                    # Create new Salesforce record with generated content
                    record_id = sf_client.create_record({target_field: completion})

                    results['success'] += 1
                    print(f"Created {i+1}/{insert_count}: {record_id}")

                except Exception as e:
                    results['failed'] += 1
                    results['errors'].append({
                        'record_number': i + 1,
                        'error': str(e)
                    })
                    print(f"Error creating record {i+1}: {str(e)}")

        return jsonify({'success': True, 'results': results})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@synthetic_bp.route('/api/create-record', methods=['POST'])
def create_record():
    """Create a new empty Claim__c record"""
    try:
        data = request.json or {}
        sf_client = get_sf_client_func()
        record_id = sf_client.create_record(data)
        return jsonify({'success': True, 'record_id': record_id})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@synthetic_bp.route('/api/lm-studio/config', methods=['GET', 'POST'])
def lm_studio_config():
    """Get or update LM Studio configuration"""
    if request.method == 'GET':
        try:
            lm_client = get_lm_client_func()
            return jsonify({
                'success': True,
                'config': lm_client.get_config()
            })
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    else:
        try:
            data = request.json
            lm_client = get_lm_client_func()
            lm_client.update_config(data)
            return jsonify({'success': True, 'message': 'Configuration updated'})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
