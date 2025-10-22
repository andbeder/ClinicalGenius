"""
CSV generation utilities for structured LLM response data
"""
import csv
import io
import json
from .json_utils import flatten_nested_dict


def generate_structured_csv(results, dataset_name='', batch_name='', record_id_field='Record ID'):
    """
    Generate CSV in wide format: one row per record, one column per response field
    Format: Record ID, [response fields as columns]
    Nested objects are flattened with dot notation (e.g., surgeryRelatedDetails.primaryProcedure)
    This allows direct joins to analytical datasets

    Args:
        results: List of result dictionaries with 'record_id' and 'response'
        dataset_name: Name of the dataset (unused, kept for compatibility)
        batch_name: Name of the batch (unused, kept for compatibility)
        record_id_field: Name of the record ID field (e.g., 'Name', 'ClaimNumber')
    """
    output = io.StringIO()
    writer = csv.writer(output)

    # JSON Schema metadata fields to exclude
    schema_fields = {'$schema', 'type', 'properties', 'required', 'title', 'description',
                     'definitions', 'additionalProperties', '$id', '$ref', 'items'}

    # First pass: flatten all responses and collect unique field names
    flattened_results = []
    all_fields = set()

    for result in results:
        response = result.get('response', {})

        if isinstance(response, dict):
            # Flatten nested objects
            flattened_response = flatten_nested_dict(response)

            # Collect field names (excluding schema fields)
            for field_name in flattened_response.keys():
                if field_name not in schema_fields:
                    all_fields.add(field_name)
        else:
            flattened_response = {'raw_response': str(response)}
            all_fields.add('raw_response')

        flattened_results.append({
            'record_id': result['record_id'],
            'flattened_response': flattened_response
        })

    # Sort fields for consistent column order
    sorted_fields = sorted(all_fields)

    # Write header: Use actual record ID field name instead of generic "Record ID"
    record_id_header = record_id_field if record_id_field else 'Record ID'
    header = [record_id_header] + sorted_fields
    writer.writerow(header)

    # Write data rows
    for result in flattened_results:
        record_id = result['record_id']
        flattened_response = result['flattened_response']

        row = [record_id]

        # Add each field value in the same order as header
        for field_name in sorted_fields:
            value = flattened_response.get(field_name, '')

            # Convert to string
            if value is None:
                value_str = ''
            else:
                value_str = str(value)

            row.append(value_str)

        writer.writerow(row)

    return output.getvalue()
