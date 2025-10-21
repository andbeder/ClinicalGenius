#!/usr/bin/env python3
"""
Synthetic Claims Data Generator - Flask Application
Generates synthetic clinical data for Salesforce Claim__c records using LM Studio
"""

from flask import Flask, render_template, request, jsonify, send_file
import os
import json
import subprocess
import uuid
import csv
import io
import threading
import time
import re
import requests
from dotenv import load_dotenv
from salesforce_client import SalesforceClient
from lm_studio_client import LMStudioClient
from prompt_engine import PromptEngine

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

# Initialize clients
sf_client = None
lm_client = LMStudioClient()
prompt_engine = PromptEngine()

# Global state for batch executions (in-memory for now)
batch_executions = {}

def extract_json_from_llm_response(response: str) -> str:
    """
    Extract JSON from LLM response, handling special tokens and extra text.

    Handles:
    - Special tokens like <|end|>, <|start|>, <|channel|>, <|message|>, <|constrain|>
    - Markdown code blocks (```json ... ```)
    - Extra explanatory text before/after JSON

    Strategy: Find the last '}' and work backwards to find its matching '{'.
    This assumes the JSON object is the last thing in the response.

    Returns cleaned JSON string ready for parsing.
    """
    # Find the last '}' in the response
    last_brace = response.rfind('}')
    if last_brace == -1:
        # No closing brace found, return as-is
        return response.strip()

    # Work backwards to find the matching '{'
    brace_count = 0
    for i in range(last_brace, -1, -1):
        if response[i] == '}':
            brace_count += 1
        elif response[i] == '{':
            brace_count -= 1
            if brace_count == 0:
                # Found the matching opening brace
                json_str = response[i:last_brace+1]

                # Parse and clean the JSON to remove schema metadata
                try:
                    parsed = json.loads(json_str)
                    # Remove JSON schema fields if they exist
                    schema_fields = {'$schema', 'type', 'properties', 'required', 'title',
                                   'description', 'definitions', 'additionalProperties', '$id', '$ref', 'items'}
                    cleaned = {k: v for k, v in parsed.items() if k not in schema_fields}
                    return json.dumps(cleaned)
                except json.JSONDecodeError:
                    # If parsing fails, return as-is
                    return json_str

    # If no matching brace found, return original
    return response.strip()

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

@app.route('/')
def index():
    """Main CRM Analytics Prompt Execution Application"""
    return render_template('main.html')

@app.route('/synthetic')
def synthetic():
    """Synthetic Claims Data Generator"""
    return render_template('index.html')

@app.route('/api/authenticate', methods=['POST'])
def authenticate():
    """Authenticate to Salesforce"""
    try:
        client = get_sf_client()
        success = client.authenticate()
        if success:
            return jsonify({'success': True, 'message': 'Successfully authenticated to Salesforce'})
        else:
            return jsonify({'success': False, 'error': 'Authentication failed'}), 401
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/settings', methods=['GET'])
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

@app.route('/api/settings', methods=['POST'])
def save_settings():
    """Save application settings"""
    try:
        data = request.json
        settings_file = 'settings.json'

        # Save to file
        with open(settings_file, 'w') as f:
            json.dump(data, f, indent=2)

        # Update LM client configuration
        lm_client.update_config(data)

        return jsonify({'success': True, 'message': 'Settings saved successfully'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/test-connection', methods=['POST'])
def test_connection():
    """Test connection to LLM provider"""
    try:
        result = lm_client.test_connection()
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/fields', methods=['GET'])
def get_fields():
    """Get all fields from Claim__c object"""
    try:
        client = get_sf_client()
        fields = client.get_claim_fields()
        return jsonify({'success': True, 'fields': fields})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/records', methods=['GET'])
def get_records():
    """Get all Claim__c records"""
    try:
        client = get_sf_client()
        records = client.get_all_records()
        return jsonify({'success': True, 'records': records, 'count': len(records)})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/record/<record_id>', methods=['GET'])
def get_record(record_id):
    """Get a single Claim__c record by ID"""
    try:
        client = get_sf_client()
        record = client.get_record(record_id)
        return jsonify({'success': True, 'record': record})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/test-prompt', methods=['POST'])
def test_prompt():
    """Test prompt on a single record"""
    try:
        data = request.json
        record_id = data.get('record_id')
        prompt_template = data.get('prompt_template')
        target_field = data.get('target_field')

        if not all([record_id, prompt_template]):
            return jsonify({'success': False, 'error': 'Missing required parameters'}), 400

        # Get the record
        client = get_sf_client()
        record = client.get_record(record_id)

        # Build the prompt
        prompt = prompt_engine.build_prompt(prompt_template, record)

        # Generate completion
        completion = lm_client.generate(prompt)

        return jsonify({
            'success': True,
            'prompt': prompt,
            'completion': completion,
            'record': record
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/batch-generate', methods=['POST'])
def batch_generate():
    """Run batch generation - either update existing or create new records"""
    try:
        data = request.json
        prompt_template = data.get('prompt_template')
        target_field = data.get('target_field')
        mode = data.get('mode', 'update')  # 'update' or 'insert'
        insert_count = data.get('insert_count', 10)

        if not all([prompt_template, target_field]):
            return jsonify({'success': False, 'error': 'Missing required parameters'}), 400

        client = get_sf_client()

        results = {
            'total': 0,
            'success': 0,
            'failed': 0,
            'errors': []
        }

        if mode == 'update':
            # Update existing records
            records = client.get_all_records()
            results['total'] = len(records)

            for i, record in enumerate(records):
                try:
                    # Build prompt
                    prompt = prompt_engine.build_prompt(prompt_template, record)

                    # Generate completion
                    completion = lm_client.generate(prompt)

                    # Update Salesforce
                    client.update_record(record['Id'], {target_field: completion})

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
                    record_id = client.create_record({target_field: completion})

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

@app.route('/api/create-record', methods=['POST'])
def create_record():
    """Create a new empty Claim__c record"""
    try:
        data = request.json or {}
        client = get_sf_client()
        record_id = client.create_record(data)
        return jsonify({'success': True, 'record_id': record_id})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/lm-studio/config', methods=['GET', 'POST'])
def lm_studio_config():
    """Get or update LM Studio configuration"""
    if request.method == 'GET':
        return jsonify({
            'success': True,
            'config': lm_client.get_config()
        })
    else:
        try:
            data = request.json
            lm_client.update_config(data)
            return jsonify({'success': True, 'message': 'Configuration updated'})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

# CRM Analytics API endpoints
@app.route('/api/crm-analytics/datasets', methods=['GET'])
def get_crm_datasets():
    """Get all CRM Analytics datasets"""
    try:
        client = get_sf_client()
        datasets = client.get_crm_analytics_datasets()
        return jsonify({'success': True, 'datasets': datasets})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/crm-analytics/datasets/<dataset_id>/fields', methods=['GET'])
def get_dataset_fields(dataset_id):
    """Get fields from a CRM Analytics dataset"""
    try:
        client = get_sf_client()
        fields = client.get_dataset_fields(dataset_id)
        return jsonify({'success': True, 'fields': fields})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/crm-analytics/datasets/<dataset_id>/query', methods=['POST'])
def query_dataset(dataset_id):
    """Query a CRM Analytics dataset"""
    try:
        data = request.json
        fields = data.get('fields', [])
        limit = data.get('limit', 100)
        filters = data.get('filters')

        client = get_sf_client()
        results = client.query_dataset(dataset_id, fields, limit, filters)

        return jsonify({'success': True, 'results': results})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# Dataset Configuration API endpoints (using SQLite)
@app.route('/api/dataset-configs', methods=['GET', 'POST'])
def dataset_configs():
    """Get all dataset configurations or create a new one"""
    if request.method == 'GET':
        try:
            conn = sqlite3.connect('analysis_batches.db')
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            c.execute('SELECT * FROM dataset_configs ORDER BY created_at DESC')
            rows = c.fetchall()
            conn.close()

            configs = []
            for row in rows:
                config = dict(row)
                config['selected_fields'] = json.loads(config['selected_fields'])
                configs.append(config)

            return jsonify({'success': True, 'configs': configs})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    elif request.method == 'POST':
        try:
            data = request.json

            # Validate required fields
            if not data.get('name'):
                return jsonify({'success': False, 'error': 'Dataset name is required'}), 400
            if not data.get('crm_dataset_id'):
                return jsonify({'success': False, 'error': 'CRM dataset ID is required'}), 400
            if not data.get('record_id_field'):
                return jsonify({'success': False, 'error': 'Record ID field is required'}), 400
            if not data.get('selected_fields'):
                return jsonify({'success': False, 'error': 'At least one field must be selected'}), 400

            config_id = data.get('id', str(uuid.uuid4()))
            now = datetime.utcnow().isoformat()

            conn = sqlite3.connect('analysis_batches.db')
            c = conn.cursor()

            # Check if updating existing config
            if data.get('id'):
                c.execute('''
                    UPDATE dataset_configs
                    SET name=?, crm_dataset_id=?, crm_dataset_name=?, record_id_field=?,
                        saql_filter=?, selected_fields=?, updated_at=?
                    WHERE id=?
                ''', (
                    data['name'],
                    data['crm_dataset_id'],
                    data.get('crm_dataset_name', ''),
                    data['record_id_field'],
                    data.get('saql_filter', ''),
                    json.dumps(data['selected_fields']),
                    now,
                    config_id
                ))
            else:
                c.execute('''
                    INSERT INTO dataset_configs
                    (id, name, crm_dataset_id, crm_dataset_name, record_id_field,
                     saql_filter, selected_fields, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    config_id,
                    data['name'],
                    data['crm_dataset_id'],
                    data.get('crm_dataset_name', ''),
                    data['record_id_field'],
                    data.get('saql_filter', ''),
                    json.dumps(data['selected_fields']),
                    now,
                    now
                ))

            conn.commit()
            conn.close()

            return jsonify({'success': True, 'id': config_id, 'message': 'Dataset configuration saved successfully'})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/dataset-configs/<config_id>', methods=['GET', 'DELETE'])
def dataset_config_detail(config_id):
    """Get or delete a specific dataset configuration"""
    if request.method == 'GET':
        try:
            conn = sqlite3.connect('analysis_batches.db')
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            c.execute('SELECT * FROM dataset_configs WHERE id=?', (config_id,))
            row = c.fetchone()
            conn.close()

            if row:
                config = dict(row)
                config['selected_fields'] = json.loads(config['selected_fields'])
                return jsonify({'success': True, 'config': config})
            else:
                return jsonify({'success': False, 'error': 'Dataset configuration not found'}), 404
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    elif request.method == 'DELETE':
        try:
            conn = sqlite3.connect('analysis_batches.db')
            c = conn.cursor()
            c.execute('DELETE FROM dataset_configs WHERE id=?', (config_id,))
            conn.commit()
            conn.close()

            return jsonify({'success': True, 'message': 'Dataset configuration deleted successfully'})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/dataset-config/test-filter', methods=['POST'])
def test_saql_filter():
    """Test a SAQL filter to validate syntax"""
    try:
        data = request.json
        dataset_id = data.get('dataset_id')
        saql_filter = data.get('saql_filter', '').strip()

        if not dataset_id:
            return jsonify({'success': False, 'error': 'Dataset ID is required'}), 400

        client = get_sf_client()

        # Get dataset info to retrieve currentVersionId
        dataset_url = f"{client.instance_url}/services/data/{client.api_version}/wave/datasets/{dataset_id}"
        dataset_response = requests.get(dataset_url, headers=client._get_headers())
        dataset_response.raise_for_status()
        dataset_data = dataset_response.json()

        version_id = dataset_data.get('currentVersionId')
        if not version_id:
            return jsonify({'success': False, 'error': 'Could not find dataset version'}), 400

        # Build SAQL query with filter
        saql = f'q = load "{dataset_id}/{version_id}";'
        if saql_filter:
            saql += f'\n{saql_filter}'
        # Add simple SAQL after filter to test syntax
        saql += '\nq = group q by all;'
        saql += '\nq = foreach q generate "Test" as test;'
        saql += '\nq = limit q 1;'  # Only get 1 record to test

        # Execute query
        url = f"{client.instance_url}/services/data/{client.api_version}/wave/query"
        response = requests.post(url, headers=client._get_headers(), json={'query': saql})

        if not response.ok:
            error_detail = response.text
            try:
                error_json = response.json()
                if 'message' in error_json:
                    error_detail = error_json['message']
            except:
                pass
            return jsonify({'success': False, 'error': error_detail})

        # Get record count from response
        result_data = response.json()
        record_count = 0
        if 'results' in result_data and 'records' in result_data['results']:
            record_count = len(result_data['results']['records'])

        return jsonify({
            'success': True,
            'record_count': record_count,
            'message': 'Filter is valid'
        })

    except requests.exceptions.HTTPError as e:
        error_msg = str(e)
        if e.response is not None:
            try:
                error_data = e.response.json()
                error_msg = error_data.get('message', str(e))
            except:
                error_msg = e.response.text
        return jsonify({'success': False, 'error': error_msg}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# Analysis Batch API endpoints (using SQLite for local storage)
import sqlite3
from datetime import datetime

def init_db():
    """Initialize SQLite database for analysis batches and dataset configurations"""
    conn = sqlite3.connect('analysis_batches.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS dataset_configs (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            crm_dataset_id TEXT NOT NULL,
            crm_dataset_name TEXT NOT NULL,
            record_id_field TEXT NOT NULL,
            saql_filter TEXT,
            selected_fields TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS batches (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            dataset_id TEXT NOT NULL,
            dataset_name TEXT NOT NULL,
            dataset_config_id TEXT,
            description TEXT,
            status TEXT DEFAULT 'pending',
            record_count INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS prompts (
            batch_id TEXT PRIMARY KEY,
            prompt_template TEXT NOT NULL,
            response_schema TEXT,
            schema_description TEXT,
            provider TEXT DEFAULT 'lm_studio',
            endpoint TEXT,
            temperature REAL DEFAULT 0.7,
            max_tokens INTEGER DEFAULT 4000,
            timeout INTEGER DEFAULT 60,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (batch_id) REFERENCES batches(id)
        )
    ''')
    conn.commit()
    conn.close()

# Initialize database on startup
init_db()

def migrate_db():
    """Migrate database schema for existing installations"""
    conn = sqlite3.connect('analysis_batches.db')
    c = conn.cursor()

    # Check if dataset_config_id column exists
    c.execute("PRAGMA table_info(batches)")
    columns = [col[1] for col in c.fetchall()]

    if 'dataset_config_id' not in columns:
        print("Running migration: Adding dataset_config_id column to batches table")
        c.execute('ALTER TABLE batches ADD COLUMN dataset_config_id TEXT')
        conn.commit()

    conn.close()

migrate_db()

@app.route('/api/analysis/batches', methods=['GET', 'POST'])
def analysis_batches():
    """Get all batches or create a new batch"""
    if request.method == 'GET':
        try:
            conn = sqlite3.connect('analysis_batches.db')
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            c.execute('SELECT * FROM batches ORDER BY created_at DESC LIMIT 50')
            rows = c.fetchall()
            conn.close()

            batches = [dict(row) for row in rows]
            return jsonify({'success': True, 'batches': batches})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    else:
        try:
            data = request.json
            name = data.get('name')
            dataset_id = data.get('dataset_id')
            dataset_config_id = data.get('dataset_config_id')
            description = data.get('description', '')

            if not name or not dataset_id:
                return jsonify({'success': False, 'error': 'Missing required fields'}), 400

            # Get dataset info
            client = get_sf_client()
            datasets = client.get_crm_analytics_datasets()
            dataset = next((d for d in datasets if d['id'] == dataset_id), None)

            if not dataset:
                return jsonify({'success': False, 'error': 'Dataset not found'}), 404

            # Create batch
            batch_id = f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            now = datetime.now().isoformat()

            conn = sqlite3.connect('analysis_batches.db')
            c = conn.cursor()
            c.execute('''
                INSERT INTO batches (id, name, dataset_id, dataset_name, dataset_config_id, description, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (batch_id, name, dataset_id, dataset['name'], dataset_config_id, description, 'pending', now, now))
            conn.commit()
            conn.close()

            return jsonify({'success': True, 'batch_id': batch_id})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/analysis/batches/<batch_id>', methods=['GET', 'DELETE'])
def analysis_batch(batch_id):
    """Get or delete a specific batch"""
    if request.method == 'GET':
        try:
            conn = sqlite3.connect('analysis_batches.db')
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            c.execute('SELECT * FROM batches WHERE id = ?', (batch_id,))
            row = c.fetchone()
            conn.close()

            if not row:
                return jsonify({'success': False, 'error': 'Batch not found'}), 404

            return jsonify({'success': True, 'batch': dict(row)})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    else:
        try:
            conn = sqlite3.connect('analysis_batches.db')
            c = conn.cursor()
            c.execute('DELETE FROM batches WHERE id = ?', (batch_id,))
            conn.commit()
            conn.close()

            return jsonify({'success': True})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/analysis/batches/<batch_id>/fields', methods=['GET'])
def get_batch_fields(batch_id):
    """Get fields for a batch from its dataset configuration"""
    try:
        conn = sqlite3.connect('analysis_batches.db')
        conn.row_factory = sqlite3.Row
        c = conn.cursor()

        # Get batch to find dataset_config_id
        c.execute('SELECT * FROM batches WHERE id = ?', (batch_id,))
        batch = c.fetchone()

        if not batch:
            conn.close()
            return jsonify({'success': False, 'error': 'Batch not found'}), 404

        dataset_config_id = batch['dataset_config_id']

        # If no dataset config ID, fall back to all fields from CRM dataset
        if not dataset_config_id:
            conn.close()
            client = get_sf_client()
            fields = client.get_dataset_fields(batch['dataset_id'])
            return jsonify({'success': True, 'fields': fields})

        # Get dataset configuration
        c.execute('SELECT * FROM dataset_configs WHERE id = ?', (dataset_config_id,))
        config = c.fetchone()
        conn.close()

        if not config:
            return jsonify({'success': False, 'error': 'Dataset configuration not found'}), 404

        # Get all fields from CRM dataset
        client = get_sf_client()
        all_fields = client.get_dataset_fields(config['crm_dataset_id'])

        # Parse selected fields from config
        import json
        selected_field_names = json.loads(config['selected_fields'])

        # Filter to only selected fields
        filtered_fields = [f for f in all_fields if f['name'] in selected_field_names]

        return jsonify({'success': True, 'fields': filtered_fields})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# Prompt Configuration API endpoints
@app.route('/api/analysis/prompts', methods=['POST'])
def save_prompt_config():
    """Save prompt configuration for a batch"""
    try:
        data = request.json
        batch_id = data.get('batch_id')
        prompt_template = data.get('prompt_template')
        response_schema = data.get('response_schema', '')
        schema_description = data.get('schema_description', '')
        provider = data.get('provider', 'lm_studio')
        endpoint = data.get('endpoint', 'http://localhost:1234/v1/chat/completions')
        temperature = data.get('temperature', 0.7)
        max_tokens = data.get('max_tokens', 4000)
        timeout = data.get('timeout', 60)

        if not batch_id or not prompt_template:
            return jsonify({'success': False, 'error': 'Missing required fields'}), 400

        now = datetime.now().isoformat()

        conn = sqlite3.connect('analysis_batches.db')
        c = conn.cursor()

        # Check if prompt config already exists
        c.execute('SELECT batch_id FROM prompts WHERE batch_id = ?', (batch_id,))
        existing = c.fetchone()

        if existing:
            # Update existing
            c.execute('''
                UPDATE prompts
                SET prompt_template = ?, response_schema = ?, schema_description = ?, provider = ?, endpoint = ?,
                    temperature = ?, max_tokens = ?, timeout = ?, updated_at = ?
                WHERE batch_id = ?
            ''', (prompt_template, response_schema, schema_description, provider, endpoint, temperature, max_tokens, timeout, now, batch_id))
        else:
            # Insert new
            c.execute('''
                INSERT INTO prompts (batch_id, prompt_template, response_schema, schema_description, provider, endpoint,
                                   temperature, max_tokens, timeout, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (batch_id, prompt_template, response_schema, schema_description, provider, endpoint, temperature, max_tokens, timeout, now, now))

        conn.commit()
        conn.close()

        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/analysis/prompts/<batch_id>', methods=['GET'])
def get_prompt_config(batch_id):
    """Get prompt configuration for a batch"""
    try:
        conn = sqlite3.connect('analysis_batches.db')
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute('SELECT * FROM prompts WHERE batch_id = ?', (batch_id,))
        row = c.fetchone()
        conn.close()

        if not row:
            return jsonify({'success': True, 'config': None})

        return jsonify({'success': True, 'config': dict(row)})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/analysis/preview-prompt', methods=['POST'])
def preview_prompt():
    """Preview prompt with sample dataset record"""
    try:
        data = request.json
        batch_id = data.get('batch_id')
        prompt_template = data.get('prompt_template')

        if not batch_id or not prompt_template:
            return jsonify({'success': False, 'error': 'Missing required fields'}), 400

        # Get batch info
        conn = sqlite3.connect('analysis_batches.db')
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute('SELECT * FROM batches WHERE id = ?', (batch_id,))
        batch = c.fetchone()
        conn.close()

        if not batch:
            return jsonify({'success': False, 'error': 'Batch not found'}), 404

        # Get sample record from dataset
        client = get_sf_client()
        fields_data = client.get_dataset_fields(batch['dataset_id'])
        field_names = [f['name'] for f in fields_data[:20]]  # Limit to first 20 fields

        # Query a single sample record
        sample_records = client.query_dataset(batch['dataset_id'], field_names, limit=1)

        if not sample_records:
            return jsonify({'success': False, 'error': 'No records found in dataset'}), 404

        sample_record = sample_records[0]

        # Render prompt using prompt engine
        rendered_prompt = prompt_engine.build_prompt(prompt_template, sample_record)

        return jsonify({
            'success': True,
            'sample_record': sample_record,
            'rendered_prompt': rendered_prompt
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/analysis/preview-prompt-execute', methods=['POST'])
def preview_prompt_execute():
    """Execute prompt with model on a specific or random sample record"""
    try:
        data = request.json
        batch_id = data.get('batch_id')
        prompt_template = data.get('prompt_template')
        response_schema = data.get('response_schema', '')
        record_id = data.get('record_id', '')  # Optional specific record ID

        if not batch_id or not prompt_template:
            return jsonify({'success': False, 'error': 'Missing required fields'}), 400

        # Load global LLM settings
        global_settings = load_settings()

        # Get batch info
        conn = sqlite3.connect('analysis_batches.db')
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute('SELECT * FROM batches WHERE id = ?', (batch_id,))
        batch = c.fetchone()

        # Get dataset configuration to find record ID field
        c.execute('SELECT * FROM dataset_configs WHERE crm_dataset_id = ?', (batch['dataset_id'],))
        dataset_config = c.fetchone()
        conn.close()

        if not batch:
            return jsonify({'success': False, 'error': 'Batch not found'}), 404

        if not dataset_config:
            return jsonify({'success': False, 'error': 'Dataset configuration not found'}), 404

        # Get sample record from dataset
        client = get_sf_client()
        fields_data = client.get_dataset_fields(batch['dataset_id'])

        # Extract all field names from the prompt template
        prompt_fields = prompt_engine.extract_variables(prompt_template)
        print(f"Fields referenced in prompt: {prompt_fields}")

        # Get all available field names from dataset
        all_field_names = [f['name'] for f in fields_data]
        print(f"Available fields in dataset: {all_field_names}")

        # Use fields from prompt if they exist, otherwise use all fields (up to 50)
        if prompt_fields:
            # Only query fields that exist in the dataset
            field_names = [f for f in prompt_fields if f in all_field_names]
            if not field_names:
                # Fallback to first 50 fields if none of the prompt fields exist
                field_names = all_field_names[:50]
        else:
            field_names = all_field_names[:50]

        # Make sure record ID field is included
        record_id_field = dataset_config['record_id_field']
        if record_id_field not in field_names:
            field_names.append(record_id_field)

        print(f"Querying fields: {field_names}")

        # Query specific record or random sample
        if record_id:
            # Query specific record by ID
            filters = {record_id_field: record_id}
            sample_records = client.query_dataset(batch['dataset_id'], field_names, limit=1, filters=filters)
            if not sample_records:
                return jsonify({'success': False, 'error': f'Record with {record_id_field}="{record_id}" not found'}), 404
        else:
            # Query a random sample record
            import random
            offset = random.randint(0, 10)  # Random offset for variety
            sample_records = client.query_dataset(batch['dataset_id'], field_names, limit=1)
            if not sample_records:
                return jsonify({'success': False, 'error': 'No records found in dataset'}), 404

        sample_record = sample_records[0]

        print(f"Sample record structure: {json.dumps(sample_record, indent=2)}")
        print(f"Sample record keys: {list(sample_record.keys())}")

        # Render prompt using prompt engine
        rendered_prompt = prompt_engine.build_prompt(prompt_template, sample_record)

        # If response schema is provided, add it to the prompt
        if response_schema:
            # Add JSON schema instructions to the prompt
            rendered_prompt += f"\n\nPlease respond ONLY with valid JSON matching this exact schema:\n{response_schema}\n\nDo not include any explanatory text, only the JSON object."

        print(f"Rendered prompt: {rendered_prompt}")

        # Configure LM client with global settings
        lm_client.update_config(global_settings)

        # Execute the prompt with the model
        try:
            model_response = lm_client.generate(rendered_prompt)
        except Exception as model_error:
            return jsonify({
                'success': False,
                'error': f'Model execution failed: {str(model_error)}'
            }), 500

        return jsonify({
            'success': True,
            'sample_record': sample_record,
            'rendered_prompt': rendered_prompt,
            'model_response': model_response
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/analysis/search-records', methods=['POST'])
def search_records():
    """Search records in a CRM Analytics dataset"""
    try:
        data = request.json
        dataset_id = data.get('dataset_id')
        name_search = data.get('name_search', '')
        limit = data.get('limit', 10)

        if not dataset_id:
            return jsonify({'success': False, 'error': 'Missing dataset_id'}), 400

        client = get_sf_client()

        # Get all fields from dataset
        fields_data = client.get_dataset_fields(dataset_id)
        field_names = [f['name'] for f in fields_data]

        # Build filters for name search if provided
        filters = None
        if name_search:
            # Try to filter by name field (SAQL filter will be built in query_dataset)
            # Note: SAQL doesn't support LIKE, so we'll filter after retrieval
            pass

        # Query records
        records = client.query_dataset(dataset_id, field_names, limit=limit * 2)  # Get more to filter

        # Filter by name on client side if search term provided
        if name_search:
            search_lower = name_search.lower()
            filtered = []
            for record in records:
                # Check various name fields
                name_value = str(record.get('Name', '') or record.get('name', '') or
                               record.get('Title', '') or record.get('title', '') or '')
                if search_lower in name_value.lower():
                    filtered.append(record)
                    if len(filtered) >= limit:
                        break
            records = filtered
        else:
            records = records[:limit]

        return jsonify({'success': True, 'records': records})

    except Exception as e:
        print(f"Error searching records: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/analysis/generate-schema', methods=['POST'])
def generate_schema():
    """Generate JSON schema from English description using AI"""
    try:
        data = request.json
        description = data.get('description')

        if not description:
            return jsonify({'success': False, 'error': 'Missing description'}), 400

        # Create a prompt for the LLM to generate the schema
        system_prompt = """You are a JSON schema generator. Given a natural language description of a data structure,
generate a clean, valid JSON schema example. The output should be ONLY valid JSON, with no additional text,
explanations, or markdown formatting. Use proper JSON data types and include example structures for arrays and objects."""

        user_prompt = f"""Generate a JSON schema based on this description:

{description}

Return ONLY the JSON schema, nothing else. Use descriptive field names and appropriate data types (string, number, boolean, array, object)."""

        # Use the configured LLM client to generate the schema
        try:
            # Build the prompt for LM Studio
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]

            # Generate using LM Studio client
            response = lm_client.generate_chat(messages, temperature=0.3, max_tokens=2000)

            # Clean up the response to extract just the JSON
            schema_text = response.strip()

            # Extract JSON from LLM response (handles special tokens and markdown)
            schema_text = extract_json_from_llm_response(schema_text)

            # Validate that it's valid JSON
            json.loads(schema_text)

            # Format it nicely
            schema_obj = json.loads(schema_text)
            formatted_schema = json.dumps(schema_obj, indent=2)

            return jsonify({'success': True, 'schema': formatted_schema})

        except Exception as llm_error:
            print(f"LLM generation error: {str(llm_error)}")
            # Fallback to a basic schema structure
            basic_schema = {
                "field1": "string",
                "field2": "number",
                "note": "Unable to generate from LLM. Please edit this schema."
            }
            return jsonify({'success': True, 'schema': json.dumps(basic_schema, indent=2)})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/analysis/execute-proving-ground', methods=['POST'])
def execute_proving_ground():
    """Execute prompt on a list of claim names"""
    try:
        data = request.json
        batch_id = data.get('batch_id')
        claim_names = data.get('claim_names', [])

        if not batch_id:
            return jsonify({'success': False, 'error': 'Missing batch_id'}), 400

        if not claim_names:
            return jsonify({'success': False, 'error': 'Missing claim_names'}), 400

        # Get batch info
        conn = sqlite3.connect('analysis_batches.db')
        c = conn.cursor()
        c.execute('SELECT * FROM batches WHERE id = ?', (batch_id,))
        batch_row = c.fetchone()

        if not batch_row:
            conn.close()
            return jsonify({'success': False, 'error': 'Batch not found'}), 404

        # Parse batch data
        batch = {
            'id': batch_row[0],
            'dataset_id': batch_row[2]
        }

        # Get prompt configuration
        c.execute('SELECT * FROM prompts WHERE batch_id = ?', (batch_id,))
        prompt_row = c.fetchone()
        conn.close()

        if not prompt_row:
            return jsonify({'success': False, 'error': 'No prompt configuration found for this batch'}), 404

        prompt_config = {
            'template': prompt_row[1],
            'response_schema': prompt_row[2],
            'provider': prompt_row[4] or 'lm_studio',
            'endpoint': prompt_row[5],
            'temperature': prompt_row[6] or 0.7,
            'max_tokens': prompt_row[7] or 4000,
            'timeout': prompt_row[8] or 60
        }

        # Get Salesforce client
        client = get_sf_client()

        # Extract fields used in the prompt template
        prompt_engine = PromptEngine()
        template_fields = prompt_engine.extract_variables(prompt_config['template'])

        # Get all available fields from dataset to validate
        fields_data = client.get_dataset_fields(batch['dataset_id'])
        available_field_names = [f['name'] for f in fields_data]

        # Start with template fields that exist in dataset
        query_fields = [f for f in template_fields if f in available_field_names]

        # Add common ID/Name fields if they exist
        for field in ['Name', 'Title', 'Id', 'RecordId', 'ClaimNumber']:
            if field in available_field_names and field not in query_fields:
                query_fields.append(field)

        print(f"Template fields: {template_fields}")
        print(f"Available fields: {available_field_names[:20]}")
        print(f"Query fields: {query_fields}")

        # Query records with only the fields we need
        all_records = client.query_dataset(batch['dataset_id'], query_fields, limit=1000)

        print(f"Searching for claim names: {claim_names}")
        print(f"Retrieved {len(all_records)} records from dataset")

        # Filter records by claim names
        matched_records = []
        all_record_names = []
        for record in all_records:
            # Try various name fields
            record_name = (record.get('Name') or record.get('name') or
                          record.get('Title') or record.get('title') or '')

            all_record_names.append(record_name)

            if record_name in claim_names:
                matched_records.append(record)

        print(f"Sample record names from dataset: {all_record_names[:10]}")
        print(f"Matched {len(matched_records)} records")

        if not matched_records:
            return jsonify({
                'success': False,
                'error': f'No records found matching the provided claim names. Found {len(all_records)} total records in dataset. Sample names: {", ".join(all_record_names[:5])}'
            }), 404

        # Load global settings for LLM
        global_settings = load_settings()

        # Execute prompt on each matched record
        results = []
        for record in matched_records:
            try:
                # Get record name
                record_name = (record.get('Name') or record.get('name') or
                              record.get('Title') or record.get('title') or 'Unknown')

                # Render prompt with record data
                rendered_prompt = prompt_engine.build_prompt(prompt_config['template'], record)

                # Append schema instructions if schema is provided
                if prompt_config['response_schema']:
                    rendered_prompt += f"\n\nPlease respond ONLY with valid JSON matching this exact schema:\n{prompt_config['response_schema']}\n\nDo not include any explanatory text, only the JSON object."

                # Execute with model using global settings
                lm_client.update_config(global_settings)

                model_response = lm_client.generate(rendered_prompt)

                # Try to parse JSON response
                try:
                    # Extract JSON from LLM response (handles special tokens and markdown)
                    clean_response = extract_json_from_llm_response(model_response)
                    response_json = json.loads(clean_response)
                except json.JSONDecodeError:
                    # If not valid JSON, use raw text
                    response_json = {'raw_response': model_response}

                results.append({
                    'claim_name': record_name,
                    'response': response_json
                })

            except Exception as record_error:
                print(f"Error processing record {record_name}: {str(record_error)}")
                results.append({
                    'claim_name': record_name,
                    'response': {'error': str(record_error)}
                })

        return jsonify({'success': True, 'results': results})

    except Exception as e:
        print(f"Error executing proving ground: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/analysis/execute-batch', methods=['POST'])
def execute_batch():
    """Start batch execution in background thread"""
    try:
        data = request.json
        batch_id = data.get('batch_id')

        if not batch_id:
            return jsonify({'success': False, 'error': 'Missing batch_id'}), 400

        # Generate execution ID
        execution_id = str(uuid.uuid4())

        # Initialize execution state
        batch_executions[execution_id] = {
            'batch_id': batch_id,
            'execution_id': execution_id,
            'status': 'starting',
            'current': 0,
            'total': 0,
            'complete': False,
            'success': False,
            'error': None,
            'csv_filename': None,
            'csv_data': None,
            'success_count': 0,
            'error_count': 0,
            'start_time': time.time()
        }

        # Start background thread
        thread = threading.Thread(target=run_batch_execution, args=(execution_id, batch_id))
        thread.daemon = True
        thread.start()

        return jsonify({'success': True, 'execution_id': execution_id})

    except Exception as e:
        print(f"Error starting batch execution: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/analysis/batch-progress/<execution_id>', methods=['GET'])
def get_batch_progress(execution_id):
    """Get progress of batch execution"""
    try:
        if execution_id not in batch_executions:
            return jsonify({'success': False, 'error': 'Execution not found'}), 404

        execution = batch_executions[execution_id]

        # Calculate duration
        duration = int(time.time() - execution['start_time'])

        progress = {
            'execution_id': execution_id,
            'status': execution['status'],
            'current': execution['current'],
            'total': execution['total'],
            'complete': execution['complete'],
            'success': execution.get('success', False),
            'error': execution.get('error'),
            'csv_filename': execution.get('csv_filename'),
            'success_count': execution.get('success_count', 0),
            'error_count': execution.get('error_count', 0),
            'duration': duration
        }

        return jsonify({'success': True, 'progress': progress})

    except Exception as e:
        print(f"Error getting batch progress: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/analysis/download-batch-csv/<execution_id>', methods=['GET'])
def download_batch_csv(execution_id):
    """Download CSV file from completed batch execution"""
    try:
        if execution_id not in batch_executions:
            return jsonify({'success': False, 'error': 'Execution not found'}), 404

        execution = batch_executions[execution_id]

        if not execution.get('complete'):
            return jsonify({'success': False, 'error': 'Execution not complete'}), 400

        if not execution.get('csv_data'):
            return jsonify({'success': False, 'error': 'CSV data not available'}), 404

        # Create a file-like object from the CSV data
        csv_io = io.BytesIO(execution['csv_data'].encode('utf-8'))
        csv_io.seek(0)

        return send_file(
            csv_io,
            mimetype='text/csv',
            as_attachment=True,
            download_name=execution.get('csv_filename', 'batch_results.csv')
        )

    except Exception as e:
        print(f"Error downloading CSV: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

def run_batch_execution(execution_id, batch_id):
    """Background thread function to execute batch"""
    try:
        execution = batch_executions[execution_id]
        execution['status'] = 'Initializing...'

        # Get batch info
        conn = sqlite3.connect('analysis_batches.db')
        c = conn.cursor()
        c.execute('SELECT * FROM batches WHERE id = ?', (batch_id,))
        batch_row = c.fetchone()

        if not batch_row:
            execution['complete'] = True
            execution['success'] = False
            execution['error'] = 'Batch not found'
            conn.close()
            return

        batch = {
            'id': batch_row[0],
            'name': batch_row[1],
            'dataset_id': batch_row[2]
        }

        # Get prompt configuration
        c.execute('SELECT * FROM prompts WHERE batch_id = ?', (batch_id,))
        prompt_row = c.fetchone()
        conn.close()

        if not prompt_row:
            execution['complete'] = True
            execution['success'] = False
            execution['error'] = 'No prompt configuration found'
            return

        prompt_config = {
            'template': prompt_row[1],
            'response_schema': prompt_row[2],
            'provider': prompt_row[4] or 'lm_studio',
            'endpoint': prompt_row[5],
            'temperature': prompt_row[6] or 0.7,
            'max_tokens': prompt_row[7] or 4000,
            'timeout': prompt_row[8] or 60
        }

        execution['status'] = 'Loading dataset records...'

        # Get Salesforce client
        client = get_sf_client()

        # Extract fields used in the prompt template
        prompt_engine = PromptEngine()
        template_fields = prompt_engine.extract_variables(prompt_config['template'])

        # Get all available fields from dataset to validate
        fields_data = client.get_dataset_fields(batch['dataset_id'])
        available_field_names = [f['name'] for f in fields_data]

        # Start with template fields that exist in dataset
        query_fields = [f for f in template_fields if f in available_field_names]

        # Add common ID/Name fields if they exist
        for field in ['Name', 'Title', 'Id', 'RecordId', 'ClaimNumber']:
            if field in available_field_names and field not in query_fields:
                query_fields.append(field)

        print(f"Batch execution - Template fields: {template_fields}")
        print(f"Batch execution - Available fields: {available_field_names[:20]}")
        print(f"Batch execution - Query fields: {query_fields}")

        # Query records with only the fields we need
        all_records = client.query_dataset(batch['dataset_id'], query_fields, limit=10000)

        execution['total'] = len(all_records)
        execution['status'] = f'Processing {len(all_records)} records...'

        # Configure LLM client with global settings
        global_settings = load_settings()
        lm_client.update_config(global_settings)

        # Process each record
        results = []
        success_count = 0
        error_count = 0

        for idx, record in enumerate(all_records):
            try:
                # Get record ID
                record_id = record.get('Id') or record.get('id') or record.get('Name') or record.get('name') or f'Record_{idx}'

                # Render prompt
                rendered_prompt = prompt_engine.build_prompt(prompt_config['template'], record)

                # Append schema if provided
                if prompt_config['response_schema']:
                    rendered_prompt += f"\n\nPlease respond ONLY with valid JSON matching this exact schema:\n{prompt_config['response_schema']}\n\nDo not include any explanatory text, only the JSON object."

                # Execute with model
                model_response = lm_client.generate(rendered_prompt)

                # Parse JSON response
                try:
                    # Extract JSON from LLM response (handles special tokens and markdown)
                    clean_response = extract_json_from_llm_response(model_response)
                    response_json = json.loads(clean_response)
                    success_count += 1
                except json.JSONDecodeError:
                    response_json = {'raw_response': model_response}
                    error_count += 1

                results.append({
                    'record_id': record_id,
                    'batch_name': batch['name'],
                    'response': response_json
                })

            except Exception as record_error:
                print(f"Error processing record {idx}: {str(record_error)}")
                error_count += 1
                results.append({
                    'record_id': record.get('Id') or record.get('id') or f'Record_{idx}',
                    'batch_name': batch['name'],
                    'response': {'error': str(record_error)}
                })

            # Update progress
            execution['current'] = idx + 1
            execution['success_count'] = success_count
            execution['error_count'] = error_count
            execution['status'] = f'Processing record {idx + 1} of {len(all_records)}'

        # Generate structured CSV
        execution['status'] = 'Generating CSV...'
        csv_data = generate_structured_csv(results)
        csv_filename = f"batch_{batch['name']}_{execution_id[:8]}.csv"

        # Upload to Salesforce CRM Analytics
        execution['status'] = 'Uploading to Salesforce...'
        try:
            upload_to_crm_analytics(client, csv_data, csv_filename)
        except Exception as upload_error:
            print(f"Warning: Failed to upload to CRM Analytics: {str(upload_error)}")
            # Continue anyway, CSV is still available for download

        # Mark as complete
        execution['complete'] = True
        execution['success'] = True
        execution['csv_data'] = csv_data
        execution['csv_filename'] = csv_filename
        execution['status'] = 'Complete'

    except Exception as e:
        print(f"Error in batch execution: {str(e)}")
        import traceback
        traceback.print_exc()
        execution['complete'] = True
        execution['success'] = False
        execution['error'] = str(e)

def generate_structured_csv(results):
    """Generate CSV with structure: Record ID, Batch Name, Parameter Name, Value"""
    output = io.StringIO()
    writer = csv.writer(output)

    # Write header
    writer.writerow(['Record ID', 'Batch Name', 'Parameter Name', 'Value'])

    # JSON Schema metadata fields to exclude
    schema_fields = {'$schema', 'type', 'properties', 'required', 'title', 'description',
                     'definitions', 'additionalProperties', '$id', '$ref', 'items'}

    # Write data
    for result in results:
        record_id = result['record_id']
        batch_name = result['batch_name']
        response = result.get('response', {})

        if isinstance(response, dict):
            for param_name, value in response.items():
                # Skip JSON schema metadata fields
                if param_name in schema_fields:
                    continue

                # Convert value to string
                if isinstance(value, (dict, list)):
                    value_str = json.dumps(value)
                else:
                    value_str = str(value)

                writer.writerow([record_id, batch_name, param_name, value_str])
        else:
            # Handle non-dict response
            writer.writerow([record_id, batch_name, 'raw_response', str(response)])

    return output.getvalue()

def upload_to_crm_analytics(client, csv_data, filename):
    """Upload CSV to Salesforce CRM Analytics dataset"""
    # Note: This is a placeholder. Actual implementation requires CRM Analytics Data API
    # For now, we'll use the external data API

    try:
        # The Structured_Response dataset should already exist in CRM Analytics
        # We'll use the Analytics External Data API to upload the CSV

        dataset_name = 'Structured_Response'

        # Create a temporary file
        temp_file = f'/tmp/{filename}'
        with open(temp_file, 'w') as f:
            f.write(csv_data)

        # Use sf CLI to upload (if available)
        # This is a simplified approach - production should use the REST API
        print(f"CSV data prepared for upload to {dataset_name}")
        print(f"CSV saved to {temp_file} for manual upload if needed")

        # TODO: Implement actual CRM Analytics Data API upload
        # For now, the CSV is available for download

    except Exception as e:
        print(f"Error uploading to CRM Analytics: {str(e)}")
        raise

if __name__ == '__main__':
    print("Starting Synthetic Claims Data Generator...")
    print("Authenticating to Salesforce...")
    try:
        client = get_sf_client()
        client.authenticate()
        print("✓ Salesforce authentication successful")
    except Exception as e:
        print(f"✗ Salesforce authentication failed: {e}")
        print("  You can retry authentication from the web interface")

    print("\nStarting Flask server on http://localhost:4000")
    app.run(host='0.0.0.0', port=4000, debug=True)
