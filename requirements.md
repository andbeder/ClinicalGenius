# CRM Analytics Prompt Execution Application
**Version:** 2.0
**Author:** Andrew Beder
**Date:** October 20, 2025

---

## 1. Overview
This Flask-based web application enables users to design, test, and execute prompt-driven data transformations using text fields from Salesforce CRM Analytics datasets.
Users can iteratively develop prompts, test them on selected records, define structured JSON response schemas, and run large-scale batch executions through either a local LM Studio model, OpenAI ChatGPT, or Microsoft Copilot API integration.

The system bridges CRM Analytics data with structured AI model outputs, enabling natural-language-driven data enrichment and analysis workflows. Results are exported in a consistent CSV format and uploaded to the Salesforce CRM Analytics "Structured_Response" dataset for downstream analysis.

---

## 2. Objectives  

- Provide an interface for users to build, test, and execute text-generation prompts tied to CRM Analytics dataset fields.  
- Support structured JSON response validation for downstream analytics integration.  
- Offer flexibility to execute prompts using either a local LM Studio instance or a remote Copilot API endpoint.  
- Enable safe, iterative “design mode” testing before committing to large batch runs.  
- Provide clean export of structured results in CSV format.

---

## 3. Functional Requirements  

### 3.1 Prompt Builder  
The system shall provide a web-based interface for users to create, edit, and save prompt templates containing text instructions and variable placeholders for CRM Analytics dataset fields.

### 3.2 Dataset Field Selection  
The system shall allow users to select one or more fields from a connected Salesforce CRM Analytics dataset to include in the prompt execution context.

### 3.3 Record-Level Testing  
The system shall allow users to test a prompt against an individual record by selecting a dataset row (by ID) and previewing the generated prompt and its model response.

### 3.4 Structured Response Specification  
The system shall allow users to define a JSON-based structured response format through a separate “Response Schema” area.  
This schema will be used to validate and parse model outputs for consistency and downstream export.

### 3.5 Analysis Management
The system shall provide an Analysis tab where users can:
- Create new analysis batches linked to specific CRM Analytics datasets
- View all existing analysis batches with status, record counts, and creation dates
- Delete batches that are no longer needed
- Navigate directly from Analysis view to Prompt Builder for selected batches

### 3.6 Proving Ground Testing
The system shall provide a Proving Ground tab where users can:
- Enter a comma-delimited list of claim/record names to test against
- View the configured prompt template and response schema from the Prompt Builder
- Execute the prompt against the specified records
- View results in a dynamic table with all JSON response fields as columns
- Export results to CSV for analysis

### 3.7 Batch Execution
The system shall provide a Batch Execution tab where users can:
- Select an analysis batch for execution
- View batch information including dataset, status, and prompt configuration
- Execute the prompt against **all records** in the dataset
- Monitor real-time progress with:
  - Progress bar showing percentage complete
  - Current/total record counter
  - Estimated time to completion (ETA)
  - Status messages indicating current operation
- View completion statistics including total processed, success count, error count, and duration
- Download the generated CSV file
- Automatically upload results to the Salesforce CRM Analytics "Structured_Response" dataset

### 3.8 Structured CSV Export
The system shall generate CSV files with a consistent structure:
- **Header:** Record ID, Batch Name, Parameter Name, Value
- Each JSON response field becomes a separate row
- Complex values (objects/arrays) are serialized as JSON strings
- This structure ensures consistent CSV format across batches with different response schemas

### 3.9 AI-Powered Schema Generation
The system shall provide an AI-powered JSON schema generator that:
- Accepts natural language descriptions of desired response structure
- Generates valid JSON schema examples using the configured LLM
- Automatically validates and formats the generated schema
- Populates the Response Schema field with the generated JSON

### 3.10 Model Execution Options
The system shall support executing prompts through **three model integration options**:
- **Local LM Studio Endpoint:**
  The user can specify an IP address (or use localhost by default) for a locally running LM Studio instance. Prompts will be sent to its REST API for inference.
- **OpenAI ChatGPT API:**
  The user can provide an OpenAI API key to execute prompts through ChatGPT models (gpt-3.5-turbo, gpt-4, etc.).
- **Microsoft Copilot API Integration:**
  The user can provide an API key for a remote Copilot (or compatible OpenAI API) endpoint. Prompts will be executed through the remote model service using secure HTTPS requests.

The interface shall allow users to choose the execution mode (LM Studio, OpenAI, or Copilot) for each batch and configure model parameters including temperature, max tokens, and timeout values.

### 3.11 Prompt Preview and Testing
The system shall provide a preview modal that:
- Executes the prompt against a random sample record from the dataset
- Displays the sample record data used for execution
- Shows the rendered prompt with all variables substituted
- Displays the model's response
- Automatically includes the response schema in the prompt instructions

### 3.12 Automatic Token Refresh
The system shall automatically re-authenticate with Salesforce when access tokens expire:
- Detect 401 Unauthorized errors from Salesforce API calls
- Automatically re-authenticate using JWT bearer token flow
- Retry the failed request with the new access token
- Provide seamless user experience without manual re-login

### 3.13 Error Handling and Logging
The system shall provide clear feedback for failed executions, network errors, invalid responses, or schema validation issues, and log each execution event with timestamp, dataset, selected model endpoint, and execution status.

---

## 4. Non-Functional Requirements  

- **Security:**  
  All stored credentials (API keys, IP addresses) must be handled securely using environment variables or session storage.  
- **Performance:**  
  The system should efficiently handle prompt execution across hundreds to thousands of records in batch mode without timeouts or UI blocking.  
- **Scalability:**  
  The design should allow for future integration with additional model endpoints (e.g., Claude, Gemini) with minimal code changes.  
- **Usability:**  
  The interface should guide users through prompt design, test execution, schema definition, and batch run configuration in a clear, intuitive workflow.  
- **Auditability:**  
  All prompt runs should be logged with timestamp, dataset ID, user, model endpoint, and outcome (success/failure).  

---

## 5. Application Architecture

### 5.1 Frontend (HTML/CSS/JavaScript)
- **Bootstrap 5** for responsive UI components
- Single-page application with tab-based navigation
- Real-time progress updates via polling
- Dynamic table generation from JSON responses

### 5.2 Backend (Python/Flask)
- Flask web framework for API routing
- SQLite database for batch and prompt storage
- Threading for background batch execution
- RESTful API endpoints for all operations

### 5.3 Integrations
- **Salesforce Authentication:** JWT bearer token flow via Python script with AES-256 key decryption
- **CRM Analytics API:** Dataset metadata, field discovery, SAQL queries
- **LLM Providers:** LM Studio, OpenAI, Microsoft Copilot
- **Prompt Engine:** Variable substitution with `{{field_name}}` syntax

### 5.4 Data Flow
1. User creates analysis batch linked to CRM Analytics dataset
2. User builds prompt template with field variables in Prompt Builder
3. User defines response schema (manual or AI-generated)
4. User tests prompt in Proving Ground with sample records
5. User executes full batch with progress tracking
6. System generates structured CSV and uploads to CRM Analytics

---

## 6. Future Enhancements

- Implement full CRM Analytics External Data API integration for CSV upload
- Add execution history tab with past run details and re-execution capability
- Include visual JSON schema editor for structured response definition
- Add automated validation metrics (e.g., schema compliance rate, token usage)
- Enable dataset updates directly back into Salesforce via API after batch completion
- Support for additional LLM providers (Claude, Gemini)
- Batch execution resumption after interruption

---

**End of Document**

