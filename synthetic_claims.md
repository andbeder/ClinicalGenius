# Synthetic Claims Data Generator
**Version:** 1.0
**Author:** Andrew Beder
**Date:** October 19, 2025

---

## 1. Overview
This Flask-based web application generates synthetic clinical data for Salesforce Claim__c records using a local LM Studio instance. The system enables users to design prompts that reference existing field values and incrementally populate target fields with AI-generated content across all records.

This tool serves as a data preparation system for the main CRM Analytics Prompt Execution Application, generating realistic non-HIPAA test data that can be safely accessed and analyzed.

---

## 2. Objectives

- Provide a web interface to read and display all fields from the Salesforce Claim__c object
- Enable users to select a target field to populate with synthetic data
- Support prompt templates that can reference values from other fields using variable placeholders
- Allow single-record testing to preview generated content before batch execution
- Execute batch generation across all Claim__c records to populate the selected field
- Support incremental field-by-field data generation (both inserts and updates)
- Integrate with local LM Studio endpoint for text generation

---

## 3. Functional Requirements

### 3.1 Salesforce Object Introspection
The system shall connect to Salesforce using JWT authentication and retrieve the complete field schema for the Claim__c object, including:
- Field API names
- Field labels
- Field types
- Field lengths
- Current field values for existing records

### 3.2 Target Field Selection
The system shall provide a dropdown interface allowing users to select which Claim__c field to populate with synthetic data.

### 3.3 Prompt Template Builder
The system shall provide a text area where users can write prompt templates containing:
- Static instruction text
- Variable placeholders in the format `{{Field_API_Name__c}}` that reference other field values
- Example: "Generate a clinical summary for patient {{Patient_Name__c}} with diagnosis {{Diagnosis__c}} and treatment {{Treatment_Type__c}}"

### 3.4 Single Record Test Mode
The system shall allow users to:
- Select a specific Claim__c record by ID or index
- Preview the prompt with variables replaced by actual field values
- Execute the prompt against LM Studio and display the generated result
- Review and validate the output before committing to batch execution

### 3.5 Batch Generation Execution
The system shall:
- Retrieve all existing Claim__c records from Salesforce
- For each record:
  - Populate prompt template variables with the record's field values
  - Send the completed prompt to LM Studio for generation
  - Receive the generated text response
  - Update the target field in Salesforce with the generated content
- Display progress indicators showing records processed and completion status
- Log any errors or failures during batch processing

### 3.6 Incremental Field Population
The system shall support incremental workflows:
- **Field-by-field execution**: Users can run batch generation for one field, then select another field and run again
- **Update existing values**: Users can re-run generation to update fields that already contain data
- **Insert new records**: If no records exist, provide option to create initial records with base field values before generation

### 3.7 LM Studio Integration
The system shall:
- Connect to a local LM Studio instance via REST API (default: http://localhost:1234/v1/completions)
- Allow users to configure the LM Studio endpoint URL
- Send prompts with configurable parameters (temperature, max_tokens, etc.)
- Handle API errors and timeouts gracefully

### 3.8 Record Management
The system shall provide functionality to:
- View all existing Claim__c records in a table format
- See which fields are populated vs empty
- Create new empty Claim__c records if needed for initial data generation
- Delete test records if needed

### 3.9 Error Handling and Logging
The system shall:
- Display clear error messages for Salesforce connection failures
- Show which records failed during batch processing and why
- Log all generation attempts with timestamps, prompts, and results
- Allow retry of failed records

---

## 4. Non-Functional Requirements

- **Security:**
  Salesforce credentials shall be loaded from environment variables using the existing sfdcJwtAuth.js authentication module

- **Performance:**
  The system should process batch generation efficiently, with progress updates after each record

- **Usability:**
  The interface should provide a clear workflow: Select Target Field → Write Prompt → Test on One Record → Run Batch

- **Reliability:**
  Failed record updates should not halt batch processing; the system should continue and report failures at the end

- **Compatibility:**
  The system must work with the existing Salesforce authentication setup and local LM Studio instance

---

## 5. User Workflow

1. **Launch Application**: Start Flask app, auto-authenticate to Salesforce
2. **View Object Schema**: See all Claim__c fields and their current population status
3. **Select Target Field**: Choose which field to populate (e.g., Clinical_Summary__c)
4. **Write Prompt Template**: Create prompt with placeholders like "Generate a clinical summary for {{Patient_Name__c}}"
5. **Test on Single Record**: Select a record and preview the generated output
6. **Adjust and Retest**: Refine prompt template based on test results
7. **Execute Batch**: Run generation across all records
8. **Monitor Progress**: View real-time progress of batch execution
9. **Review Results**: See success/failure counts and any errors
10. **Repeat for Next Field**: Select another field and repeat the process

---

## 6. Technical Architecture

### 6.1 Backend (Flask)
- **Authentication Module**: Reuse existing sfdcJwtAuth.js via Node.js subprocess
- **Salesforce API Client**: REST API calls for schema introspection and record CRUD
- **LM Studio Client**: HTTP client for completion API calls
- **Template Engine**: Variable substitution for prompt templates
- **Batch Processor**: Async processing with progress tracking

### 6.2 Frontend (HTML/JS)
- **Schema Viewer**: Display all fields in table format
- **Prompt Builder**: Text area with syntax highlighting for variable placeholders
- **Test Panel**: Record selector and preview output display
- **Batch Executor**: Start/stop controls with progress bar
- **Results Dashboard**: Success/failure metrics and logs

---

## 7. Data Flow

```
User → Flask App → Salesforce (get schema & records)
                 ↓
              Prompt Template + Record Data
                 ↓
              Variable Substitution
                 ↓
              LM Studio API
                 ↓
              Generated Text
                 ↓
              Salesforce (update record)
```

---

## 8. Future Enhancements

- Support for creating related objects (e.g., generating multiple claim line items per claim)
- Prompt template library with saved templates for common fields
- Advanced filtering to run batch generation on record subsets
- Export generated data to CSV for offline review
- Support for additional LLM providers (OpenAI, Claude, etc.)
- Parallel batch processing for faster execution

---

**End of Document**
