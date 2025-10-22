"""
Schema generation service for creating JSON schemas from natural language descriptions
"""
import json
from utils.json_utils import extract_json_from_llm_response


def generate_schema_from_description(description, lm_client):
    """
    Generate JSON schema from English description using AI

    Args:
        description: Natural language description of desired data structure
        lm_client: LLM client instance to use for generation

    Returns:
        Tuple of (success: bool, schema: str or None, error: str or None)
    """
    if not description:
        return False, None, 'Missing description'

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

        return True, formatted_schema, None

    except Exception as llm_error:
        print(f"LLM generation error: {str(llm_error)}")
        # Fallback to a basic schema structure
        basic_schema = {
            "field1": "string",
            "field2": "number",
            "note": "Unable to generate from LLM. Please edit this schema."
        }
        return True, json.dumps(basic_schema, indent=2), None
