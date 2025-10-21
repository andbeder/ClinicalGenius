# Development Notes - Clinical Genius

## Latest Update: Multiple Dataset Management (October 21, 2025)

### Major Changes: Dataset Configuration Refactoring

#### 1. Datasets Tab - Complete Redesign
**Previous Implementation**: Single dataset configuration stored in JSON file
**New Implementation**: Multiple dataset configurations stored in SQLite database

- **Dataset List View**: Table displaying all configured datasets with:
  - Dataset name (user-friendly identifier)
  - CRM Analytics dataset name
  - Record ID field
  - Number of selected fields
  - SAQL filter status (applied/none)
  - Edit and Delete action buttons

- **Create/Edit Modal**: Full-featured modal dialog for dataset configuration:
  - Dataset Name: Custom user-provided name
  - CRM Analytics Dataset: Dropdown of available datasets (sorted alphabetically)
  - Record ID Field: Dropdown populated from selected dataset fields
  - SAQL Filter: Optional filter with "Test Filter" validation button
  - Field Selection: Searchable checkbox list with select all/deselect all
  - All modal interactions properly isolated from main page state

- **CRUD Operations**:
  - Create: Click "New Dataset" button to open modal
  - Read: List automatically loads on page load
  - Update: Click "Edit" button to open modal with pre-populated values
  - Delete: Click "Delete" button with confirmation dialog

#### 2. Database Schema Updates
Added new `dataset_configs` table to SQLite database:
```sql
CREATE TABLE dataset_configs (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    crm_dataset_id TEXT NOT NULL,
    crm_dataset_name TEXT NOT NULL,
    record_id_field TEXT NOT NULL,
    saql_filter TEXT,
    selected_fields TEXT NOT NULL,  -- JSON array
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
)
```

#### 3. API Endpoint Changes
**Removed**:
- `GET/POST /api/dataset-config` (single config file-based)

**Added**:
- `GET /api/dataset-configs` - List all dataset configurations
- `POST /api/dataset-configs` - Create or update dataset configuration
- `GET /api/dataset-configs/<id>` - Get specific configuration
- `DELETE /api/dataset-configs/<id>` - Delete configuration

**Retained**:
- `POST /api/dataset-config/test-filter` - Test SAQL filter validation

#### 4. Analysis Tab Updates
- **Dataset Selection**: Changed from raw Salesforce datasets to configured datasets
- **New Analysis Modal**: Dropdown now shows user-configured datasets from Datasets tab
- **Validation**: Warns user if no datasets are configured before allowing analysis creation
- **Integration**: Uses configured dataset's CRM dataset ID and name when creating batches

#### 5. LLM Provider Fixes
- **Provider Name Handling**: Fixed issue where `lm_studio` (with underscore) was not recognized
  - Updated code to handle both `lm_studio` and `lmstudio` formats
  - Strips underscores before provider comparison
- **JSON Mode**: Added `response_format: {"type": "json_object"}` to LM Studio requests
  - Forces model to return pure JSON without markdown or explanatory text
  - Prevents issues with models adding commentary around JSON output

### Technical Implementation Details

#### Frontend (JavaScript)
- **New Global Variables**:
  - `datasetConfigs`: Array of all configured datasets
  - `modalDatasetFields`: Fields for the modal (isolated from main page)
  - `modalSelectedFields`: Selected fields in modal (isolated from main page)
  - `currentEditingConfigId`: Tracks which config is being edited

- **Modal State Management**: Completely separate state for modal vs main page
  - Prevents interference between dataset configuration and other operations
  - Modal fields reload from API when editing existing configuration

- **Dynamic Dropdown Population**:
  - Analysis modal populates with configured datasets on open
  - Dataset config modal populates with CRM datasets on open
  - Record ID dropdown populates when dataset is selected

#### Backend (Python)
- **SQLite Integration**: All dataset configs stored in database for persistence
- **JSON Field Storage**: `selected_fields` stored as JSON string, parsed on retrieval
- **Atomic Operations**: Each config operation (create/update/delete) is atomic

### Migration Path
**From**: Single `dataset_config.json` file
**To**: SQLite `dataset_configs` table

Users with existing `dataset_config.json` will need to:
1. Go to Datasets tab
2. Click "New Dataset"
3. Re-configure their dataset using the modal
4. Old file can be safely deleted

### User Workflow Changes

**Previous Workflow**:
1. Configure single dataset in Datasets tab
2. Create analysis using that dataset
3. To use different dataset, reconfigure Datasets tab

**New Workflow**:
1. Configure multiple datasets in Datasets tab (create once, use many times)
2. Create analysis by selecting from configured datasets
3. Each analysis can use different configured dataset
4. Edit/delete dataset configurations as needed

### Benefits of New Approach
- **Multiple Datasets**: Manage many dataset configurations simultaneously
- **Reusability**: Configure once, use in multiple analyses
- **Organization**: Named datasets easier to identify than raw CRM dataset IDs
- **Consistency**: Field selections and filters stored with dataset configuration
- **Flexibility**: Quickly switch between different dataset configurations
- **Persistence**: SQLite storage more robust than JSON files

---

## Major Update: CRM Analytics Prompt Execution Application (October 20, 2025)

### Application Restructured
- **Main Application** (/) - CRM Analytics Prompt Execution Application (Version 2.0)
- **Synthetic Generator** (/synthetic) - Legacy synthetic data generator (preserved)
- Port: 4000

### New Features Implemented

#### 1. Analysis Tab
- **Batch Management**: Create, view, and delete analysis batches
- **Dataset Selection**: Choose from available CRM Analytics datasets
- **Navigation**: Click "View" on a batch to jump to Prompt Builder with that batch selected
- **SQLite Database**:
  - `batches` table: id, name, dataset_id, dataset_name, description, status, record_count, created_at
  - `prompts` table: batch_id, prompt_template, response_schema, schema_description, provider, endpoint, temperature, max_tokens, timeout, created_at, updated_at

#### 2. Prompt Builder Tab
- **Field Discovery**: Automatically loads dataset fields (dimensions and measures)
- **Click-to-Insert**: Click field names to insert `{{field_name}}` variables into prompt
- **Schema Description**: Natural language description of desired response structure
- **AI Schema Generation**: Click "Generate JSON Schema" to create structured response format using configured LLM
- **Response Schema**: JSON editor with syntax validation
- **Model Configuration**:
  - Provider selection (LM Studio, OpenAI, Copilot)
  - Temperature (0.0-1.0)
  - Max tokens (1-8000)
  - Timeout (seconds)
- **Preview Modal**: Test prompt on random sample record, displays:
  - Sample record data
  - Rendered prompt with variables substituted
  - Model response (including JSON schema if provided)
- **Prompt Persistence**: All configurations saved to SQLite and restored when batch is reselected

#### 3. Proving Ground Tab (formerly "Design Mode")
- **Purpose**: Test prompts on specific records by name before full batch execution
- **Batch Selection**: Choose analysis batch to test
- **Claim Names Input**: Comma-delimited list of record names (e.g., "CLM-001, CLM-042, CLM-137")
- **Configuration Display**: Shows prompt template and response schema from Prompt Builder
- **Run Prompt**: Executes prompt against specified records
- **Results Table**: Dynamic table with all JSON response fields as columns
- **CSV Export**: Download results for analysis

#### 4. Batch Execution Tab
- **Batch Selection**: Choose analysis batch for full execution
- **Prompt Validation**: Green/red badge indicates if prompt is configured
- **Execute Batch Button**: Starts background execution of all dataset records
- **Real-Time Progress**:
  - Progress bar with percentage complete
  - Current/total record counter
  - Estimated time to completion (ETA)
  - Status messages (e.g., "Processing record 42 of 1000")
  - Polling every 2 seconds for updates
- **Completion Statistics**:
  - Total processed count
  - Success count
  - Error count
  - Total duration
- **CSV Generation**: Structured format with columns:
  - Record ID
  - Batch Name
  - Parameter Name
  - Value
- **CRM Analytics Upload**: Automatic upload to `Structured_Response` dataset (placeholder implementation)
- **CSV Download**: Download generated CSV file

### Technical Implementation

#### Backend Architecture
- **Threading**: Background threads for batch execution to prevent UI blocking
- **Progress Tracking**: In-memory dict (`batch_executions`) stores execution state
- **API Endpoints**:
  - `/api/analysis/batches` - CRUD for batches
  - `/api/analysis/prompts` - CRUD for prompt configurations
  - `/api/analysis/execute-batch` - Start batch execution
  - `/api/analysis/batch-progress/<execution_id>` - Poll progress
  - `/api/analysis/download-batch-csv/<execution_id>` - Download CSV
  - `/api/analysis/execute-proving-ground` - Execute on specific records
  - `/api/analysis/generate-schema` - AI-powered schema generation

#### Frontend Architecture
- **Single-Page Application**: Tab-based navigation with dynamic content loading
- **State Management**: Global JavaScript variables for batches, datasets, fields, current batch
- **Polling**: setInterval for progress updates every 2 seconds
- **Dynamic Tables**: Build table headers/rows from JSON response keys
- **CSV Export**: Client-side CSV generation with proper escaping

#### Salesforce Integration
- **CRM Analytics API**:
  - Dataset discovery via `/services/data/v60.0/wave/datasets`
  - Field metadata via `/services/data/v60.0/wave/datasets/<id>/versions/<version_id>/xmds/main`
  - SAQL queries via `/services/data/v60.0/wave/query`
- **Automatic Token Refresh**:
  - `_make_request()` method detects 401 errors
  - Re-authenticates automatically
  - Retries failed request with new token
- **SAQL Query Fixes**:
  - Use `currentVersionId` in load statement: `load "dataset_id/version_id"`
  - Don't quote field names in `foreach generate` clause
  - Flatten response: Extract values from CRM Analytics format `{"value": actual_value}`

#### LLM Integration
- **Multi-Provider Support**: LM Studio, OpenAI ChatGPT, Microsoft Copilot
- **Prompt Engine**: Variable substitution with regex replacement
- **Schema Enforcement**: Appends JSON schema instructions to prompts
- **Response Parsing**: Cleans markdown code blocks, parses JSON, handles errors

### Database Schema
```sql
CREATE TABLE batches (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    dataset_id TEXT NOT NULL,
    dataset_name TEXT NOT NULL,
    description TEXT,
    status TEXT DEFAULT 'pending',
    record_count INTEGER DEFAULT 0,
    created_at TEXT NOT NULL
);

CREATE TABLE prompts (
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
);
```

### CSV Structure
Consistent format ensures all batches produce compatible data:
```
Record ID, Batch Name, Parameter Name, Value
CLM-001, Claims Analysis, condition, Diabetes Type 2
CLM-001, Claims Analysis, severity, High
CLM-001, Claims Analysis, risk_factors, ["Obesity", "Hypertension"]
CLM-002, Claims Analysis, condition, Hypertension
CLM-002, Claims Analysis, severity, Medium
```

This allows:
- Filtering by batch name
- Pivoting on parameter names
- Joining back to source data via Record ID
- Consistent schema as new parameters are added

### Key Technical Decisions

1. **In-Memory Progress Tracking**: Used dict instead of database for simplicity and performance
2. **Polling vs WebSockets**: Polling chosen for simpler implementation, acceptable latency
3. **CSV Structure**: Normalized format (one param per row) vs wide format (one record per row)
4. **Background Threading**: Python threading module instead of Celery for lightweight deployment
5. **SQLite**: Local database sufficient for single-user deployment
6. **Tab Navigation**: Single-page app vs multi-page for better UX

### Error Handling Improvements
- Automatic Salesforce token refresh on 401 errors
- JSON parsing with fallback to raw text on parse errors
- Record-level error handling in batch execution (continue on failure)
- Clear error messages in UI with retry buttons

### Performance Optimizations
- Field metadata cached after first load
- Progress polling rate: 2 seconds (balance between responsiveness and server load)
- CSV generation uses StringIO for memory efficiency
- Background threads prevent UI blocking

---

## Previous Development (October 19-20, 2025) - Synthetic Generator

### Application Setup
- Created Flask-based **Synthetic Claims Data Generator** application
- Port: 4000
- Purpose: Generate AI-powered synthetic medical malpractice claim data for Salesforce

### Authentication
- Implemented JWT-based Salesforce authentication via `sfdcJwtAuth.py`
- Credentials stored in `.env` file:
  - Username: (configured in .env)
  - Connected App Client ID configured
  - JWT key stored in `../jwt.key.enc`
  - Login URL: https://login.salesforce.com
- OpenAI API integration configured with API key in `.env`
- Model: gpt-4o-mini

### Salesforce Custom Fields Created
Successfully deployed 4 Long Text Area fields to Claim__c object:
1. **Clinical_Summary__c** - 32,768 characters
2. **Claim_Summary__c** - 32,768 characters
3. **Clinical_Review__c** - 32,768 characters
4. **Expert_Review__c** - 32,768 characters

**Important**: Field visibility must be set in Salesforce for fields to appear in API describe calls

### Application Features
1. **LLM Provider Support**:
   - LM Studio (local/remote)
   - OpenAI ChatGPT (gpt-4o-mini)
   - Microsoft Copilot
   - API keys configured via .env, not UI

2. **Batch Generation Modes**:
   - **Update Existing Records**: Updates all existing Claim__c records
   - **Create New Records**: Creates specified number of new records (1-100)

3. **Prompt Template Engine**:
   - Use `{{Field_Name__c}}` syntax to reference field values
   - Supports variable substitution from Salesforce records
   - Designed for medical malpractice claim descriptions

4. **Target Field Selection**:
   - Automatically detects all Long Text Area (textarea type) fields
   - Currently showing 6 fields available for population
   - Field type displayed in sidebar for easy identification

5. **UI Design**:
   - Bootstrap 5 styling
   - Responsive layout with sidebar and main content
   - Color-coded sections (Configuration, Salesforce Data, Prompt Builder, Test, Batch)
   - Real-time progress tracking for batch operations

### Technical Architecture
```
app.py                  - Flask routes and main application
salesforce_client.py    - Salesforce API integration (describe, query, CRUD)
sfdcJwtAuth.py          - JWT authentication for Salesforce
lm_studio_client.py     - LLM provider clients (LM Studio, OpenAI, Copilot)
prompt_engine.py        - Template variable substitution
templates/index.html    - Bootstrap UI
static/css/style.css   - Custom styling
static/js/app.js       - Frontend logic
```

### Configuration Files
- `.env` - Environment variables (credentials, API keys)
- `.gitignore` - Excludes .env, keys, temp files, venv
- `requirements.txt` - Python dependencies (Flask, requests, python-dotenv)
- `sfdx-project.json` - Salesforce DX project configuration
- `force-app/` - Salesforce metadata (custom fields)

### Known Issues & Resolutions
1. **Field Visibility**: Custom fields must have Field-Level Security set for user profile to appear in API
2. **Session Expiration**: Flask app caches Salesforce token but may need restart for fresh auth
3. **LM Studio Endpoint**: Only shown when LM Studio provider selected
4. **Max Tokens**: Default 4000, max 8000 for longer claim descriptions

### Example Use Case
Generate comprehensive medical malpractice claim descriptions with:
- Patient background and medical history
- Detailed incident description
- Immediate and long-term consequences
- Medical expert opinions and evidence
- Impact on quality of life and ability to work
- Specific damages claimed (medical expenses, lost wages, pain and suffering)

### Startup Commands
```bash
# Start application
./start.sh

# Or manually
source venv/bin/activate
python app.py

# Deploy fields to Salesforce
sf project deploy start --source-dir force-app/main/default/objects/Claim__c/fields

# Test Salesforce connection
SFDC_USERNAME="your-email@example.com" KEY_PASS="your-key-password" SFDC_CLIENT_ID="your-connected-app-client-id" python3 sfdcJwtAuth.py
```

### Known Issues & Future Enhancements

#### Current Limitations
1. **CRM Analytics Upload**: Placeholder implementation - saves CSV to `/tmp/` instead of uploading via External Data API
2. **Progress Persistence**: In-memory tracking means progress is lost on server restart
3. **History Tab**: Stub only - no execution history tracking yet
4. **Concurrent Executions**: Only one batch execution can run at a time per server instance
5. **Record Limit**: SAQL queries limited to 10,000 records (CRM Analytics constraint)

#### Future Work
1. **CRM Analytics Integration**:
   - Implement full External Data API upload workflow
   - Create/update Structured_Response dataset automatically
   - Handle dataset versioning and appends

2. **History & Audit**:
   - Execution history tab with past runs
   - Re-run capability from history
   - Audit log of all executions with timestamps

3. **Performance**:
   - Batch execution resumption after interruption
   - Parallel processing of records (thread pool)
   - Caching of dataset metadata
   - Database persistence of progress

4. **UI Enhancements**:
   - Visual JSON schema editor
   - Prompt template library/versioning
   - Dark mode support
   - Mobile-responsive improvements

5. **Advanced Features**:
   - Scheduled batch executions (cron-like)
   - Email notifications on completion
   - Webhook callbacks for integration
   - Support for additional LLM providers (Claude, Gemini)

6. **Security**:
   - Multi-user support with authentication
   - Role-based access control
   - Encrypted credential storage
   - API rate limiting

---

**Last Updated**: October 20, 2025
