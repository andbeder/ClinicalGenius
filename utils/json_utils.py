"""
JSON utility functions for parsing and cleaning LLM responses
"""
import json


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


def flatten_nested_dict(obj, parent_key='', sep='.'):
    """
    Flatten a nested dictionary into dot-notation keys.
    Example: {'a': {'b': 1}} -> {'a.b': 1}

    Args:
        obj: Dictionary or value to flatten
        parent_key: Parent key for recursion
        sep: Separator for nested keys (default: '.')

    Returns:
        Flattened dictionary
    """
    items = []

    if isinstance(obj, dict):
        for key, value in obj.items():
            new_key = f"{parent_key}{sep}{key}" if parent_key else key

            if isinstance(value, dict):
                # Recursively flatten nested dicts
                items.extend(flatten_nested_dict(value, new_key, sep=sep).items())
            elif isinstance(value, list):
                # Convert lists to JSON strings (can't easily flatten arrays)
                items.append((new_key, json.dumps(value)))
            else:
                items.append((new_key, value))
    else:
        # Not a dict, return as-is
        items.append((parent_key, obj))

    return dict(items)
