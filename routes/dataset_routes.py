"""
Dataset and dataset configuration routes
Handles CRM Analytics datasets and user-defined dataset configurations
"""
from flask import Blueprint, request, jsonify
import json
import uuid
import requests
from datetime import datetime
from database.db import get_connection


dataset_bp = Blueprint('dataset', __name__)

# Mutable container for client getter function (set by main app)
_client_funcs = {
    'get_sf_client': None
}


def get_sf_client_func():
    """Get Salesforce client using configured function"""
    if _client_funcs['get_sf_client'] is None:
        raise NotImplementedError("SF client getter not configured")
    return _client_funcs['get_sf_client']()


@dataset_bp.route('/api/crm-analytics/datasets', methods=['GET'])
def get_crm_datasets():
    """Get all CRM Analytics datasets"""
    try:
        client = get_sf_client_func()
        datasets = client.get_crm_analytics_datasets()
        return jsonify({'success': True, 'datasets': datasets})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@dataset_bp.route('/api/crm-analytics/datasets/<dataset_id>/fields', methods=['GET'])
def get_dataset_fields(dataset_id):
    """Get fields from a CRM Analytics dataset"""
    try:
        client = get_sf_client_func()
        fields = client.get_dataset_fields(dataset_id)
        return jsonify({'success': True, 'fields': fields})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@dataset_bp.route('/api/crm-analytics/datasets/<dataset_id>/query', methods=['POST'])
def query_dataset(dataset_id):
    """Query a CRM Analytics dataset"""
    try:
        data = request.json
        fields = data.get('fields', [])
        limit = data.get('limit', 100)
        filters = data.get('filters')

        client = get_sf_client_func()
        results = client.query_dataset(dataset_id, fields, limit, filters)

        return jsonify({'success': True, 'results': results})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@dataset_bp.route('/api/dataset-configs', methods=['GET', 'POST'])
def dataset_configs():
    """Get all dataset configurations or create a new one"""
    if request.method == 'GET':
        try:
            conn = get_connection()
            conn.row_factory = lambda cursor, row: dict(zip([col[0] for col in cursor.description], row))
            c = conn.cursor()
            c.execute('SELECT * FROM dataset_configs ORDER BY created_at DESC')
            rows = c.fetchall()
            conn.close()

            configs = []
            for row in rows:
                config = dict(row)
                config['selected_fields'] = json.loads(config['selected_fields'])
                config['picklist_fields'] = json.loads(config.get('picklist_fields') or '[]')
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

            conn = get_connection()
            c = conn.cursor()

            # Check if updating existing config
            if data.get('id'):
                c.execute('''
                    UPDATE dataset_configs
                    SET name=?, crm_dataset_id=?, crm_dataset_name=?, record_id_field=?,
                        saql_filter=?, selected_fields=?, picklist_fields=?, updated_at=?
                    WHERE id=?
                ''', (
                    data['name'],
                    data['crm_dataset_id'],
                    data.get('crm_dataset_name', ''),
                    data['record_id_field'],
                    data.get('saql_filter', ''),
                    json.dumps(data['selected_fields']),
                    json.dumps(data.get('picklist_fields', [])),
                    now,
                    config_id
                ))
            else:
                c.execute('''
                    INSERT INTO dataset_configs
                    (id, name, crm_dataset_id, crm_dataset_name, record_id_field,
                     saql_filter, selected_fields, picklist_fields, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    config_id,
                    data['name'],
                    data['crm_dataset_id'],
                    data.get('crm_dataset_name', ''),
                    data['record_id_field'],
                    data.get('saql_filter', ''),
                    json.dumps(data['selected_fields']),
                    json.dumps(data.get('picklist_fields', [])),
                    now,
                    now
                ))

            conn.commit()
            conn.close()

            return jsonify({'success': True, 'id': config_id, 'message': 'Dataset configuration saved successfully'})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500


@dataset_bp.route('/api/dataset-configs/<config_id>', methods=['GET', 'DELETE'])
def dataset_config_detail(config_id):
    """Get or delete a specific dataset configuration"""
    if request.method == 'GET':
        try:
            conn = get_connection()
            conn.row_factory = lambda cursor, row: dict(zip([col[0] for col in cursor.description], row))
            c = conn.cursor()
            c.execute('SELECT * FROM dataset_configs WHERE id=?', (config_id,))
            row = c.fetchone()
            conn.close()

            if row:
                config = dict(row)
                config['selected_fields'] = json.loads(config['selected_fields'])
                config['picklist_fields'] = json.loads(config.get('picklist_fields') or '[]')
                return jsonify({'success': True, 'config': config})
            else:
                return jsonify({'success': False, 'error': 'Dataset configuration not found'}), 404
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    elif request.method == 'DELETE':
        try:
            conn = get_connection()
            c = conn.cursor()
            c.execute('DELETE FROM dataset_configs WHERE id=?', (config_id,))
            conn.commit()
            conn.close()

            return jsonify({'success': True, 'message': 'Dataset configuration deleted successfully'})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500


@dataset_bp.route('/api/dataset-config/test-filter', methods=['POST'])
def test_saql_filter():
    """Test a SAQL filter to validate syntax"""
    try:
        data = request.json
        dataset_id = data.get('dataset_id')
        saql_filter = data.get('saql_filter', '').strip()

        if not dataset_id:
            return jsonify({'success': False, 'error': 'Dataset ID is required'}), 400

        client = get_sf_client_func()

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
        try:
            error_json = e.response.json()
            if 'message' in error_json:
                error_msg = error_json['message']
        except:
            pass
        return jsonify({'success': False, 'error': error_msg}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@dataset_bp.route('/api/crm-analytics/datasets/<dataset_id>/distinct-values', methods=['POST'])
def get_distinct_values(dataset_id):
    """Get distinct values for a field in a CRM Analytics dataset"""
    try:
        data = request.json
        field_name = data.get('field_name')
        saql_filter = data.get('saql_filter', '').strip()

        if not field_name:
            return jsonify({'success': False, 'error': 'Field name is required'}), 400

        client = get_sf_client_func()

        # Get dataset info to retrieve currentVersionId
        dataset_url = f"{client.instance_url}/services/data/{client.api_version}/wave/datasets/{dataset_id}"
        dataset_response = requests.get(dataset_url, headers=client._get_headers())
        dataset_response.raise_for_status()
        dataset_data = dataset_response.json()

        version_id = dataset_data.get('currentVersionId')
        if not version_id:
            return jsonify({'success': False, 'error': 'Could not find dataset version'}), 400

        # Build SAQL query to get distinct values
        saql = f'q = load "{dataset_id}/{version_id}";'

        # Apply dataset filter if provided
        if saql_filter:
            saql += f'\n{saql_filter}'

        # Group by the field to get distinct values
        saql += f'\nq = group q by \'{field_name}\';'
        saql += f'\nq = foreach q generate \'{field_name}\' as value;'
        saql += '\nq = order q by value asc;'  # Sort alphabetically
        saql += '\nq = limit q 10000;'  # Limit to prevent too many values

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
            return jsonify({'success': False, 'error': error_detail}), 400

        # Extract distinct values from response
        result_data = response.json()
        distinct_values = []

        if 'results' in result_data and 'records' in result_data['results']:
            for record in result_data['results']['records']:
                # CRM Analytics returns values in format {"value": actual_value}
                if 'value' in record and record['value'] is not None:
                    value = record['value']
                    # Handle both direct values and wrapped values
                    if isinstance(value, dict) and 'value' in value:
                        value = value['value']
                    # Convert to string and filter out empty/null
                    if value is not None and str(value).strip():
                        distinct_values.append(str(value))

        return jsonify({
            'success': True,
            'values': distinct_values,
            'count': len(distinct_values)
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
