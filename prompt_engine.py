"""
Prompt Template Engine
Handles variable substitution in prompt templates
"""

import re
from typing import Dict, List

class PromptEngine:
    def __init__(self):
        # Pattern to match {{Field_Name__c}} placeholders
        self.variable_pattern = re.compile(r'\{\{([^}]+)\}\}')

    def build_prompt(self, template: str, record: Dict) -> str:
        """
        Build a prompt by replacing variables with record field values

        Args:
            template: Prompt template with {{Field_Name__c}} placeholders
            record: Salesforce record dictionary

        Returns:
            Completed prompt with variables replaced
        """
        def replace_variable(match):
            field_name = match.group(1).strip()

            # Get the field value from the record
            value = record.get(field_name)

            # Handle null/None values
            if value is None or value == '':
                return f"[{field_name}: not provided]"

            # Convert to string if needed
            return str(value)

        # Replace all variables in the template
        completed_prompt = self.variable_pattern.sub(replace_variable, template)

        return completed_prompt

    def extract_variables(self, template: str) -> List[str]:
        """
        Extract all variable names from a template

        Args:
            template: Prompt template with {{Field_Name__c}} placeholders

        Returns:
            List of field names referenced in the template
        """
        matches = self.variable_pattern.findall(template)
        return [match.strip() for match in matches]

    def validate_template(self, template: str, available_fields: List[str]) -> Dict:
        """
        Validate that all variables in template correspond to available fields

        Args:
            template: Prompt template
            available_fields: List of valid field API names

        Returns:
            Dictionary with 'valid' boolean and 'missing_fields' list
        """
        variables = self.extract_variables(template)
        missing_fields = [var for var in variables if var not in available_fields]

        return {
            'valid': len(missing_fields) == 0,
            'missing_fields': missing_fields,
            'used_fields': variables
        }

    def preview_prompt(self, template: str, record: Dict) -> Dict:
        """
        Preview a prompt with variable substitution details

        Args:
            template: Prompt template
            record: Salesforce record

        Returns:
            Dictionary with completed prompt and substitution details
        """
        variables = self.extract_variables(template)
        substitutions = {}

        for var in variables:
            value = record.get(var)
            substitutions[var] = {
                'value': value,
                'present': value is not None and value != ''
            }

        completed = self.build_prompt(template, record)

        return {
            'template': template,
            'completed_prompt': completed,
            'variables': variables,
            'substitutions': substitutions
        }
