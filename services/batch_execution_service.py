"""
Batch execution service for running LLM prompts against CRM Analytics datasets
"""
import json
import time
import threading
from datetime import datetime
from database.db import get_connection
from utils.json_utils import extract_json_from_llm_response
from utils.csv_utils import generate_structured_csv
from prompt_engine import PromptEngine


# Global state for batch executions (in-memory for now)
batch_executions = {}


def persist_execution_status(batch_id, execution):
    """Persist execution status to database for resumption after server restart"""
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute('''
            INSERT OR REPLACE INTO execution_status
            (batch_id, execution_id, status, current, total, success_count, error_count,
             started_at, updated_at, complete, success, error)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            batch_id,
            execution['execution_id'],
            execution['status'],
            execution['current'],
            execution['total'],
            execution.get('success_count', 0),
            execution.get('error_count', 0),
            datetime.fromtimestamp(execution['start_time']).isoformat(),
            datetime.now().isoformat(),
            1 if execution['complete'] else 0,
            1 if execution.get('success', False) else 0,
            execution.get('error')
        ))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Warning: Failed to persist execution status: {str(e)}")


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


def run_batch_execution(execution_id, batch_id, sf_client, lm_client, settings_loader):
    """
    Background thread function to execute batch

    Args:
        execution_id: Unique execution identifier
        batch_id: Batch to execute
        sf_client: Salesforce client instance
        lm_client: LLM client instance
        settings_loader: Function to load global settings
    """
    try:
        execution = batch_executions[execution_id]
        execution['status'] = 'Initializing...'
        persist_execution_status(batch_id, execution)

        # Get batch info
        conn = get_connection()
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
            'id': batch_row[0],           # id
            'name': batch_row[1],         # name
            'dataset_id': batch_row[2],   # dataset_id
            'dataset_name': batch_row[3], # dataset_name
            'dataset_config_id': batch_row[4]  # dataset_config_id
        }

        # Get dataset configuration to find record ID field
        if batch['dataset_config_id']:
            c.execute('SELECT record_id_field FROM dataset_configs WHERE id = ?', (batch['dataset_config_id'],))
            config_row = c.fetchone()
            record_id_field = config_row[0] if config_row else None
            print(f"Using record ID field from config: {record_id_field}")
        else:
            record_id_field = None
            print("No dataset config found, using default ID fields")

        # Delete old execution history for this batch (only keep latest)
        c.execute('DELETE FROM execution_history WHERE batch_id = ?', (batch_id,))
        conn.commit()

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

        # Extract fields used in the prompt template
        prompt_engine = PromptEngine()
        template_fields = prompt_engine.extract_variables(prompt_config['template'])

        # Get all available fields from dataset to validate
        fields_data = sf_client.get_dataset_fields(batch['dataset_id'])
        available_field_names = [f['name'] for f in fields_data]

        # Start with template fields that exist in dataset
        query_fields = [f for f in template_fields if f in available_field_names]

        # Add common ID/Name fields if they exist
        for field in ['Name', 'Title', 'Id', 'RecordId', 'ClaimNumber']:
            if field in available_field_names and field not in query_fields:
                query_fields.append(field)

        # Get SAQL filter from dataset configuration
        saql_filter = ''
        if batch['dataset_config_id']:
            conn_temp = get_connection()
            c_temp = conn_temp.cursor()
            c_temp.execute('SELECT saql_filter FROM dataset_configs WHERE id = ?', (batch['dataset_config_id'],))
            filter_row = c_temp.fetchone()
            conn_temp.close()
            if filter_row and filter_row[0]:
                saql_filter = filter_row[0]

        # Ensure record ID field is in query fields
        if record_id_field and record_id_field not in query_fields:
            query_fields.append(record_id_field)

        print(f"Batch execution - Template fields: {template_fields}")
        print(f"Batch execution - Available fields: {available_field_names[:20]}")
        print(f"Batch execution - Query fields: {query_fields}")
        print(f"Batch execution - Record ID field: {record_id_field}")
        print(f"Batch execution - SAQL filter: {saql_filter}")

        # Check if we have filtered record IDs
        filtered_record_ids = execution.get('record_ids')

        if filtered_record_ids:
            # Query only the specified records using filters
            print(f"Batch execution - Filtering to {len(filtered_record_ids)} specific record IDs")
            filters = {record_id_field: filtered_record_ids} if record_id_field else None
            all_records = sf_client.query_dataset(
                batch['dataset_id'],
                query_fields,
                limit=len(filtered_record_ids),
                filters=filters,
                saql_filter=saql_filter
            )
        else:
            # Query all records (up to limit)
            print(f"Batch execution - Querying all records (no filter)")
            all_records = sf_client.query_dataset(
                batch['dataset_id'],
                query_fields,
                limit=10000,
                saql_filter=saql_filter
            )

        execution['total'] = len(all_records)
        execution['status'] = f'Processing {len(all_records)} records...'
        persist_execution_status(batch_id, execution)

        # Configure LLM client with global settings
        global_settings = settings_loader()
        lm_client.update_config(global_settings)

        # Process each record
        results = []
        success_count = 0
        error_count = 0
        start_time = time.time()

        for idx, record in enumerate(all_records):
            try:
                # Get record ID from configured field, fall back to common fields
                if record_id_field:
                    record_id = record.get(record_id_field) or f'Record_{idx}'
                    if idx == 0:  # Log first record for debugging
                        print(f"First record ID extracted from field '{record_id_field}': {record_id}")
                else:
                    record_id = record.get('Id') or record.get('id') or record.get('Name') or record.get('name') or f'Record_{idx}'
                    if idx == 0:
                        print(f"First record ID using fallback: {record_id}")

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

            # Persist status every 10 records
            if (idx + 1) % 10 == 0:
                persist_execution_status(batch_id, execution)

        # Generate structured CSV with dataset name and batch name
        execution['status'] = 'Generating CSV...'
        csv_data = generate_structured_csv(results, batch['dataset_name'], batch['name'], record_id_field)
        csv_filename = f"batch_{batch['name']}_{execution_id[:8]}.csv"

        # Save to execution history
        execution['status'] = 'Saving to history...'
        try:
            end_time = time.time()
            execution_time = end_time - start_time

            conn = get_connection()
            c = conn.cursor()
            c.execute('''
                INSERT OR REPLACE INTO execution_history
                (batch_id, batch_name, dataset_name, total_records, success_count,
                 error_count, execution_time, csv_data, executed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                batch['id'],
                batch['name'],
                batch['dataset_name'],
                execution['total'],
                success_count,
                error_count,
                execution_time,
                csv_data,
                datetime.now().isoformat()
            ))
            conn.commit()
            conn.close()
            print(f"Saved execution history for batch {batch['id']}")
        except Exception as hist_error:
            print(f"Warning: Failed to save execution history: {str(hist_error)}")

        # Upload to Salesforce CRM Analytics
        execution['status'] = 'Uploading to Salesforce...'
        try:
            upload_to_crm_analytics(sf_client, csv_data, csv_filename)
        except Exception as upload_error:
            print(f"Warning: Failed to upload to CRM Analytics: {str(upload_error)}")
            # Continue anyway, CSV is still available for download

        # Mark as complete
        execution['complete'] = True
        execution['success'] = True
        execution['csv_data'] = csv_data
        execution['csv_filename'] = csv_filename
        execution['status'] = 'Complete'
        persist_execution_status(batch_id, execution)

        # Clean up from memory after a delay (allow final status check)
        def cleanup_execution():
            time.sleep(30)  # Wait 30 seconds before cleanup
            if execution_id in batch_executions:
                print(f"Cleaning up completed execution {execution_id} from memory")
                del batch_executions[execution_id]

        cleanup_thread = threading.Thread(target=cleanup_execution)
        cleanup_thread.daemon = True
        cleanup_thread.start()

    except Exception as e:
        print(f"Error in batch execution: {str(e)}")
        import traceback
        traceback.print_exc()
        execution['complete'] = True
        execution['success'] = False
        execution['error'] = str(e)
        persist_execution_status(batch_id, execution)

        # Clean up from memory after a delay (even on error)
        def cleanup_execution():
            time.sleep(30)  # Wait 30 seconds before cleanup
            if execution_id in batch_executions:
                print(f"Cleaning up failed execution {execution_id} from memory")
                del batch_executions[execution_id]

        cleanup_thread = threading.Thread(target=cleanup_execution)
        cleanup_thread.daemon = True
        cleanup_thread.start()
