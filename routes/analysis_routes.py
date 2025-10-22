"""
Analysis routes for batch management, prompt building, execution, and history
This is the main set of routes for the CRM Analytics Prompt Execution Application
"""
from flask import Blueprint, request, jsonify, send_file
import json
import uuid
import threading
import time
import io
import csv
from datetime import datetime
from database.db import get_connection
from services.batch_execution_service import batch_executions, run_batch_execution
from services.schema_service import generate_schema_from_description
from utils.json_utils import extract_json_from_llm_response
from prompt_engine import PromptEngine
from audit_logger import get_audit_logger, AuditLogger


analysis_bp = Blueprint('analysis', __name__)

# Mutable container for client getter functions (set by main app)
_client_funcs = {
    'get_sf_client': None,
    'get_lm_client': None,
    'load_settings': None
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


def load_settings_func():
    """Load settings using configured function"""
    if _client_funcs['load_settings'] is None:
        raise NotImplementedError("Settings loader not configured")
    return _client_funcs['load_settings']()


@analysis_bp.route('/api/analysis/batches', methods=['GET', 'POST'])
def analysis_batches():
    """Get all analysis batches or create a new one"""
    if request.method == 'GET':
        try:
            conn = get_connection()
            conn.row_factory = lambda cursor, row: dict(zip([col[0] for col in cursor.description], row))
            c = conn.cursor()
            c.execute('''
                SELECT b.*,
                       CASE WHEN p.batch_id IS NOT NULL THEN 1 ELSE 0 END as has_prompt
                FROM batches b
                LEFT JOIN prompts p ON b.id = p.batch_id
                ORDER BY b.created_at DESC
            ''')
            batches = c.fetchall()
            conn.close()
            return jsonify({'success': True, 'batches': batches})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    elif request.method == 'POST':
        try:
            data = request.json
            batch_id = str(uuid.uuid4())
            now = datetime.utcnow().isoformat()

            conn = get_connection()
            c = conn.cursor()
            c.execute('''
                INSERT INTO batches (id, name, dataset_id, dataset_name, dataset_config_id, description, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                batch_id,
                data['name'],
                data['dataset_id'],
                data['dataset_name'],
                data.get('dataset_config_id'),
                data.get('description', ''),
                now,
                now
            ))
            conn.commit()
            conn.close()

            return jsonify({'success': True, 'batch_id': batch_id, 'message': 'Analysis batch created successfully'})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500


@analysis_bp.route('/api/analysis/batches/<batch_id>', methods=['GET', 'DELETE'])
def analysis_batch(batch_id):
    """Get or delete a specific analysis batch"""
    if request.method == 'GET':
        try:
            conn = get_connection()
            conn.row_factory = lambda cursor, row: dict(zip([col[0] for col in cursor.description], row))
            c = conn.cursor()
            c.execute('SELECT * FROM batches WHERE id=?', (batch_id,))
            batch = c.fetchone()
            conn.close()

            if batch:
                return jsonify({'success': True, 'batch': batch})
            else:
                return jsonify({'success': False, 'error': 'Batch not found'}), 404
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    elif request.method == 'DELETE':
        try:
            conn = get_connection()
            c = conn.cursor()
            c.execute('DELETE FROM prompts WHERE batch_id=?', (batch_id,))
            c.execute('DELETE FROM batches WHERE id=?', (batch_id,))
            conn.commit()
            conn.close()

            return jsonify({'success': True, 'message': 'Batch deleted successfully'})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500


@analysis_bp.route('/api/analysis/batches/<batch_id>/fields', methods=['GET'])
def get_batch_fields(batch_id):
    """Get fields for a specific batch (filtered by dataset configuration)"""
    try:
        conn = get_connection()
        conn.row_factory = lambda cursor, row: dict(zip([col[0] for col in cursor.description], row))
        c = conn.cursor()

        # Get batch info
        c.execute('SELECT dataset_id, dataset_config_id FROM batches WHERE id=?', (batch_id,))
        batch = c.fetchone()

        if not batch:
            conn.close()
            return jsonify({'success': False, 'error': 'Batch not found'}), 404

        # Get Salesforce client
        client = get_sf_client_func()

        # Get all fields from dataset
        all_fields = client.get_dataset_fields(batch['dataset_id'])

        # If batch has a dataset_config_id, filter fields
        if batch['dataset_config_id']:
            c.execute('SELECT selected_fields FROM dataset_configs WHERE id=?', (batch['dataset_config_id'],))
            config = c.fetchone()

            if config:
                selected_field_names = json.loads(config['selected_fields'])
                # Filter to only selected fields
                filtered_fields = [f for f in all_fields if f['name'] in selected_field_names]
                conn.close()
                return jsonify({'success': True, 'fields': filtered_fields})

        # Fall back to all fields if no config
        conn.close()
        return jsonify({'success': True, 'fields': all_fields})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@analysis_bp.route('/api/analysis/prompts', methods=['POST'])
def save_prompt():
    """Save or update prompt configuration for a batch"""
    try:
        data = request.json
        batch_id = data.get('batch_id')
        now = datetime.utcnow().isoformat()

        conn = get_connection()
        c = conn.cursor()

        # Check if prompt exists
        c.execute('SELECT batch_id FROM prompts WHERE batch_id=?', (batch_id,))
        existing = c.fetchone()

        if existing:
            # Update existing prompt
            c.execute('''
                UPDATE prompts
                SET prompt_template=?, response_schema=?, schema_description=?,
                    provider=?, endpoint=?, temperature=?, max_tokens=?, timeout=?, updated_at=?
                WHERE batch_id=?
            ''', (
                data.get('prompt_template', ''),
                data.get('response_schema', ''),
                data.get('schema_description', ''),
                data.get('provider', 'lm_studio'),
                data.get('endpoint', ''),
                data.get('temperature', 0.7),
                data.get('max_tokens', 4000),
                data.get('timeout', 60),
                now,
                batch_id
            ))
        else:
            # Insert new prompt
            c.execute('''
                INSERT INTO prompts
                (batch_id, prompt_template, response_schema, schema_description,
                 provider, endpoint, temperature, max_tokens, timeout, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                batch_id,
                data.get('prompt_template', ''),
                data.get('response_schema', ''),
                data.get('schema_description', ''),
                data.get('provider', 'lm_studio'),
                data.get('endpoint', ''),
                data.get('temperature', 0.7),
                data.get('max_tokens', 4000),
                data.get('timeout', 60),
                now,
                now
            ))

        conn.commit()
        conn.close()

        return jsonify({'success': True, 'message': 'Prompt configuration saved successfully'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@analysis_bp.route('/api/analysis/prompts/<batch_id>', methods=['GET'])
def get_prompt(batch_id):
    """Get prompt configuration for a batch"""
    try:
        conn = get_connection()
        conn.row_factory = lambda cursor, row: dict(zip([col[0] for col in cursor.description], row))
        c = conn.cursor()
        c.execute('SELECT * FROM prompts WHERE batch_id=?', (batch_id,))
        prompt = c.fetchone()
        conn.close()

        if prompt:
            return jsonify({'success': True, 'prompt': prompt, 'config': prompt})  # Return both for compatibility
        else:
            return jsonify({'success': False, 'error': 'Prompt configuration not found'}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@analysis_bp.route('/api/analysis/generate-schema', methods=['POST'])
def generate_schema():
    """Generate JSON schema from English description using AI"""
    try:
        data = request.json
        description = data.get('description')

        lm_client = get_lm_client_func()
        success, schema, error = generate_schema_from_description(description, lm_client)

        if success:
            return jsonify({'success': True, 'schema': schema})
        else:
            return jsonify({'success': False, 'error': error}), 400

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# NOTE: The remaining routes (preview, execution, proving ground, history) would continue here
# Due to their length, I'm providing stubs that reference the original implementation
# These can be filled in from app.py in a similar manner

@analysis_bp.route('/api/analysis/preview-prompt', methods=['POST'])
def preview_prompt():
    """Preview prompt (opens modal) - stub for now"""
    return jsonify({'success': True, 'message': 'Preview initiated'})


@analysis_bp.route('/api/analysis/preview-prompt-execute', methods=['POST'])
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
        global_settings = load_settings_func()

        # Get batch info
        conn = get_connection()
        conn.row_factory = lambda cursor, row: dict(zip([col[0] for col in cursor.description], row))
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
        client = get_sf_client_func()
        fields_data = client.get_dataset_fields(batch['dataset_id'])

        # Extract all field names from the prompt template
        prompt_engine = PromptEngine()
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

        # Get LM client and configure with global settings
        lm_client = get_lm_client_func()
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


@analysis_bp.route('/api/analysis/execute-proving-ground', methods=['POST'])
def execute_proving_ground():
    """Execute prompt on a list of record IDs"""
    try:
        data = request.json
        batch_id = data.get('batch_id')
        record_ids = data.get('claim_names', [])  # Keep 'claim_names' for backward compatibility

        if not batch_id:
            return jsonify({'success': False, 'error': 'Missing batch_id'}), 400

        if not record_ids:
            return jsonify({'success': False, 'error': 'Missing record IDs'}), 400

        # Get batch info
        conn = get_connection()
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
        client = get_sf_client_func()

        # Get dataset configuration to find the record ID field
        conn = get_connection()
        conn.row_factory = lambda cursor, row: dict(zip([col[0] for col in cursor.description], row))
        c = conn.cursor()
        c.execute('SELECT * FROM dataset_configs WHERE crm_dataset_id = ?', (batch['dataset_id'],))
        dataset_config = c.fetchone()
        conn.close()

        if not dataset_config:
            return jsonify({'success': False, 'error': 'Dataset configuration not found. Please configure the dataset first.'}), 404

        record_id_field = dataset_config['record_id_field']
        saql_filter = dataset_config['saql_filter'] if dataset_config['saql_filter'] else ''  # Get SAQL filter from dataset config

        # Extract fields used in the prompt template
        prompt_engine = PromptEngine()
        template_fields = prompt_engine.extract_variables(prompt_config['template'])

        # Get all available fields from dataset to validate
        fields_data = client.get_dataset_fields(batch['dataset_id'])
        available_field_names = [f['name'] for f in fields_data]

        # Start with template fields that exist in dataset
        query_fields = [f for f in template_fields if f in available_field_names]

        # Ensure record ID field is included
        if record_id_field not in query_fields:
            query_fields.append(record_id_field)

        print(f"Template fields: {template_fields}")
        print(f"Record ID field: {record_id_field}")
        print(f"Query fields: {query_fields}")
        print(f"SAQL filter from config: {saql_filter}")

        # Filter out empty record IDs (from trailing newlines, etc.)
        record_ids = [rid.strip() for rid in record_ids if rid and rid.strip()]

        if not record_ids:
            return jsonify({
                'success': False,
                'error': 'No valid record IDs provided after filtering empty values'
            }), 400

        print(f"Querying {len(record_ids)} record IDs: {record_ids[:10]}...")  # Show first 10

        # Query all records at once using 'in' filter (much more efficient than individual queries)
        # Also apply the dataset's SAQL filter to ensure we only get the configured subset
        try:
            filters = {record_id_field: record_ids}  # Pass list for 'in' operator
            matched_records = client.query_dataset(
                batch['dataset_id'],
                query_fields,
                limit=len(record_ids),
                filters=filters,
                saql_filter=saql_filter  # Apply dataset filter
            )
            print(f"Found {len(matched_records)} matching records")
        except Exception as e:
            print(f"Error querying records: {str(e)}")
            return jsonify({
                'success': False,
                'error': f'Error querying records: {str(e)}'
            }), 500

        # Determine which IDs were not found
        found_ids = {record.get(record_id_field) for record in matched_records}
        not_found = [rid for rid in record_ids if rid not in found_ids]

        print(f"Matched {len(matched_records)} records, {len(not_found)} not found")
        if not_found:
            print(f"Not found IDs: {not_found[:10]}")  # Show first 10

        if not matched_records:
            return jsonify({
                'success': False,
                'error': f'No records found matching the provided IDs. Not found: {", ".join(not_found[:10])}'
            }), 404

        # Get LM client and load settings
        lm_client = get_lm_client_func()
        global_settings = load_settings_func()

        # Execute prompt on each matched record
        results = []
        for record in matched_records:
            try:
                # Get record ID
                record_id = record.get(record_id_field) or 'Unknown'

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
                    'record_id': record_id,
                    'response': response_json
                })

            except Exception as record_error:
                print(f"Error processing record {record_id}: {str(record_error)}")
                results.append({
                    'record_id': record_id,
                    'response': {'error': str(record_error)}
                })

        return jsonify({'success': True, 'results': results})

    except Exception as e:
        print(f"Error executing proving ground: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@analysis_bp.route('/api/analysis/execute-batch', methods=['POST'])
def execute_batch():
    """Execute batch processing in background"""
    try:
        data = request.json
        batch_id = data.get('batch_id')
        record_ids = data.get('record_ids')  # Optional filter

        # Create execution
        execution_id = str(uuid.uuid4())
        execution = {
            'execution_id': execution_id,
            'batch_id': batch_id,
            'status': 'Starting...',
            'current': 0,
            'total': 0,
            'complete': False,
            'start_time': time.time(),
            'record_ids': record_ids  # Store filtered record IDs if provided
        }
        batch_executions[execution_id] = execution

        # Start background thread
        sf_client = get_sf_client_func()
        lm_client = get_lm_client_func()
        settings_loader = load_settings_func

        thread = threading.Thread(
            target=run_batch_execution,
            args=(execution_id, batch_id, sf_client, lm_client, settings_loader)
        )
        thread.daemon = True
        thread.start()

        return jsonify({'success': True, 'execution_id': execution_id})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@analysis_bp.route('/api/analysis/batch-status/<batch_id>', methods=['GET'])
def get_batch_status(batch_id):
    """Get execution status for a batch (checks both active and persisted)"""
    try:
        # Check active executions first
        for exec_id, execution in batch_executions.items():
            if execution.get('batch_id') == batch_id:
                return jsonify({
                    'success': True,
                    'has_active_execution': True,
                    'execution_id': exec_id,
                    'execution': execution
                })

        # Check persisted status
        conn = get_connection()
        conn.row_factory = lambda cursor, row: dict(zip([col[0] for col in cursor.description], row))
        c = conn.cursor()
        c.execute('SELECT * FROM execution_status WHERE batch_id=? ORDER BY updated_at DESC LIMIT 1', (batch_id,))
        status = c.fetchone()
        conn.close()

        if status:
            return jsonify({
                'success': True,
                'has_active_execution': False,
                'has_persisted_status': True,
                'status': status
            })

        return jsonify({
            'success': True,
            'has_active_execution': False,
            'has_persisted_status': False
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@analysis_bp.route('/api/analysis/batch-progress/<execution_id>', methods=['GET'])
def get_batch_progress(execution_id):
    """Poll batch execution progress"""
    if execution_id in batch_executions:
        execution = batch_executions[execution_id]
        return jsonify({'success': True, 'execution': execution})
    else:
        return jsonify({'success': False, 'error': 'Execution not found'}), 404


@analysis_bp.route('/api/analysis/download-batch-csv/<execution_id>', methods=['GET'])
def download_batch_csv(execution_id):
    """Download CSV from completed batch execution"""
    if execution_id not in batch_executions:
        return jsonify({'success': False, 'error': 'Execution not found'}), 404

    execution = batch_executions[execution_id]

    if not execution.get('complete'):
        return jsonify({'success': False, 'error': 'Execution not complete'}), 400

    if not execution.get('csv_data'):
        return jsonify({'success': False, 'error': 'CSV data not available'}), 404

    # Create file-like object from CSV string
    csv_data = execution['csv_data']
    csv_file = io.BytesIO(csv_data.encode('utf-8'))
    filename = execution.get('csv_filename', f'batch_results_{execution_id[:8]}.csv')

    return send_file(
        csv_file,
        mimetype='text/csv',
        as_attachment=True,
        download_name=filename
    )


@analysis_bp.route('/api/analysis/history', methods=['GET'])
def get_execution_history():
    """Get all execution history"""
    try:
        conn = get_connection()
        conn.row_factory = lambda cursor, row: dict(zip([col[0] for col in cursor.description], row))
        c = conn.cursor()
        c.execute('''
            SELECT batch_id, batch_name, dataset_name, total_records,
                   success_count, error_count, execution_time, executed_at
            FROM execution_history
            ORDER BY executed_at DESC
        ''')
        history = c.fetchall()
        conn.close()

        return jsonify({'success': True, 'history': history})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@analysis_bp.route('/api/analysis/history/<batch_id>/csv', methods=['GET'])
def download_history_csv(batch_id):
    """Download CSV from execution history"""
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute('SELECT csv_data, batch_name FROM execution_history WHERE batch_id=?', (batch_id,))
        result = c.fetchone()
        conn.close()

        if not result:
            return jsonify({'success': False, 'error': 'Execution history not found'}), 404

        csv_data, batch_name = result
        csv_file = io.BytesIO(csv_data.encode('utf-8'))
        filename = f"{batch_name}_results.csv"

        return send_file(
            csv_file,
            mimetype='text/csv',
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@analysis_bp.route('/api/analysis/history/combined-csv', methods=['GET'])
def download_combined_csv():
    """Download combined CSV from all batch executions, merging columns by Record ID"""
    try:
        conn = get_connection()
        conn.row_factory = lambda cursor, row: dict(zip([col[0] for col in cursor.description], row))
        c = conn.cursor()
        c.execute('''
            SELECT batch_name, dataset_name, csv_data
            FROM execution_history
            ORDER BY dataset_name, executed_at DESC
        ''')
        rows = c.fetchall()
        conn.close()

        if not rows:
            return jsonify({'success': False, 'error': 'No execution history found'}), 404

        # Parse all CSVs and merge by Record ID
        # Structure: {record_id: {column_name: value}}
        merged_data = {}
        all_columns = set(['Record ID'])  # Start with Record ID column

        for row in rows:
            batch_name = row['batch_name']
            csv_data = row['csv_data']

            # Parse CSV
            lines = csv_data.strip().split('\n')
            if len(lines) < 2:
                continue

            reader = csv.DictReader(io.StringIO(csv_data))

            for csv_row in reader:
                record_id = csv_row.get('Record ID', '')
                if not record_id:
                    continue

                # Initialize record if not exists
                if record_id not in merged_data:
                    merged_data[record_id] = {'Record ID': record_id}

                # Add all columns from this CSV (prefixed with batch name to avoid conflicts)
                for col_name, value in csv_row.items():
                    if col_name == 'Record ID':
                        continue

                    # Prefix column with batch name for uniqueness
                    prefixed_col = f"{batch_name}_{col_name}"
                    all_columns.add(prefixed_col)
                    merged_data[record_id][prefixed_col] = value

        # Sort columns for consistent output (Record ID first, then alphabetically)
        sorted_columns = ['Record ID'] + sorted([col for col in all_columns if col != 'Record ID'])

        # Generate combined CSV
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=sorted_columns, extrasaction='ignore')
        writer.writeheader()

        for record_id in sorted(merged_data.keys()):
            # Fill missing columns with empty strings
            row_data = {col: merged_data[record_id].get(col, '') for col in sorted_columns}
            writer.writerow(row_data)

        # Return combined CSV
        csv_bytes = io.BytesIO(output.getvalue().encode('utf-8'))

        return send_file(
            csv_bytes,
            mimetype='text/csv',
            as_attachment=True,
            download_name=f'all_batches_combined_results.csv'
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@analysis_bp.route('/api/analysis/history/<batch_id>', methods=['DELETE'])
def delete_execution_history(batch_id):
    """Delete execution history for a batch"""
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute('DELETE FROM execution_history WHERE batch_id=?', (batch_id,))
        conn.commit()
        conn.close()

        return jsonify({'success': True, 'message': 'Execution history deleted'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
