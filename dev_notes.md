# Development Notes - Clinical Genius

## Latest Update: Apply Dataset SAQL Filter to Proving Ground (October 21, 2025)

### Issue
Proving Ground was not applying the dataset's SAQL filter when querying records by ID. This caused problems in datasets with duplicate record IDs across different filtered subsets (e.g., Test vs Production data in same dataset).

**Example Problem:**
- Dataset has records with `Name = "REC-001"` in both Test and Production environments
- Dataset config has filter: `q = filter q by 'Environment' == "Production";`
- Proving Ground would return the Test record instead of Production record

### Fix

**1. Updated `query_dataset()` method (salesforce_client.py:249)**
- Added `saql_filter` parameter to accept raw SAQL filter string
- SAQL filter applied BEFORE programmatic filters (record ID filter)
- Ensures dataset configuration filter is always respected

**2. Updated Proving Ground endpoint (app.py:1219, 1256-1262)**
- Reads `saql_filter` from dataset configuration
- Passes filter to `query_dataset()` call
- Logs filter being applied for debugging

**SAQL Query Order:**
```saql
q = load "dataset_id/version_id";
q = filter q by 'Environment' == "Production";  # Dataset config filter
q = filter q by 'Name' in ["REC-001", "REC-002"];  # Record ID filter
q = foreach q generate Name, Status, Amount;
q = limit q 2;
```

**Result:**
- ✅ Proving Ground now respects dataset filters
- ✅ Only returns records matching both dataset filter AND record ID
- ✅ Prevents duplicate/incorrect records from being processed
- ✅ Consistent with Batch Execution behavior

---

## Previous Update: Nested Object Support with Dot Notation Flattening (October 21, 2025)

### Challenge
LLM responses often contain nested objects (e.g., conditional fields based on category):
```json
{
  "caseCategory": "Surgery Related | Diagnosis Related",
  "surgeryRelatedDetails": {
    "primaryProcedure": "string",
    "initialComplication": "string",
    "injuryPhaseOfCare": "Pre-operative | Intra-operative"
  },
  "diagnosisRelatedDetails": {
    "initialDiagnosis": "string",
    "diagnosticTestsOrdered": "Yes | No"
  }
}
```

This creates a problem for CSV export and analytics - can't have nested objects in tabular data.

### Solution: Dot Notation Flattening

**Backend (app.py:1763-1862)**
- Added `flatten_nested_dict()` function to recursively flatten nested objects
- Example: `{"surgeryRelatedDetails": {"primaryProcedure": "Appendectomy"}}`
  → `{"surgeryRelatedDetails.primaryProcedure": "Appendectomy"}`
- Updated `generate_structured_csv()` to flatten all responses before writing CSV
- Arrays converted to JSON strings (can't easily flatten)

**Frontend (static/js/main.js:1338-1488)**
- Added `flattenNestedObject()` JavaScript function (mirrors backend logic)
- Updated `displayProvingResults()` to flatten objects before displaying in table
- Updated `exportProvingCSV()` to use flattened structure

**Result:**
CSV columns now look like:
```csv
Record ID,caseCategory,diagnosisRelatedDetails.diagnosticTestsOrdered,diagnosisRelatedDetails.finalDiagnosis,surgeryRelatedDetails.primaryProcedure
REC-001,Surgery Related,Yes,Infection,Appendectomy
REC-002,Diagnosis Related,No,Diabetes,
```

**Benefits:**
- ✅ Works with complex nested schemas
- ✅ Each nested field becomes its own column
- ✅ Analytics-ready - can aggregate/filter on any nested field
- ✅ Consistent between Proving Ground display and Batch CSV export
- ✅ Empty nested objects don't break CSV structure

---

## Previous Update: Fixed Proving Ground SAQL Query with Multiple Record IDs (October 21, 2025)

### Issue
When copying/pasting multiple record IDs from Excel (newline-delimited), the SAQL query would:
1. Include empty strings from trailing newlines, creating invalid `'field' == ""` filters
2. Query each record individually in a loop (inefficient for 10+ records)

### Fix
1. **Filter empty values** (app.py:1239-1246)
   - Strip whitespace and filter out empty record IDs before querying
   - Prevents invalid SAQL syntax from blank values

2. **Use SAQL `in` operator** (salesforce_client.py:272-276)
   - Changed from: `'Name' == "REC-001" && 'Name' == "REC-002"` (invalid)
   - Changed to: `'Name' in ["REC-001", "REC-002", "REC-003"]` (correct)
   - Detects list values in filters dictionary and generates proper SAQL array syntax

3. **Single query instead of loop** (app.py:1250-1254)
   - Queries all record IDs in one SAQL call instead of N individual queries
   - Much faster for 10+ records (1 query vs 10+ queries)

**Example SAQL Generated**:
```saql
q = load "dataset_id/version_id";
q = filter q by 'Name' in ["REC-001", "REC-002", "REC-003"];
q = foreach q generate Name, Condition, Severity;
q = limit q 3;
```

---

## Previous Update: Server-Side Execution Status Persistence (October 21, 2025)

### View Execution Feature

**Purpose**: Allow users to navigate from History tab to Batch Execution tab and check execution status even hours later after closing the browser.

**Implementation**:
1. **"View Execution" Button on History Tab**
   - Added button with play-circle icon to each history record
   - Calls `viewBatchExecution(batchId)` to navigate to Batch Execution tab
   - Automatically loads batch details and checks for active/persisted execution status

2. **Server-Side Execution Status Persistence**
   - New `execution_status` table in database:
     ```sql
     CREATE TABLE execution_status (
         batch_id TEXT PRIMARY KEY,
         execution_id TEXT NOT NULL,
         status TEXT NOT NULL,
         current INTEGER DEFAULT 0,
         total INTEGER DEFAULT 0,
         success_count INTEGER DEFAULT 0,
         error_count INTEGER DEFAULT 0,
         started_at TEXT NOT NULL,
         updated_at TEXT NOT NULL,
         complete INTEGER DEFAULT 0,
         success INTEGER DEFAULT 0,
         error TEXT,
         FOREIGN KEY (batch_id) REFERENCES batches(id) ON DELETE CASCADE
     )
     ```
   - Status persisted at execution start, every 10 records, and at completion/error
   - Survives server restarts and browser closures

3. **API Endpoint**:
   - `GET /api/analysis/batch-status/<batch_id>` - Returns both active (in-memory) and persisted status
   - Checks `batch_executions` dictionary first for active executions
   - Falls back to database for persisted status

4. **Frontend Updates**:
   - `handleBatchExecSelection()` now checks for active/persisted execution on load
   - If active execution found, starts polling automatically
   - If persisted incomplete execution found, displays last known status with timestamp
   - `showPersistedExecutionStatus()` displays server-side status with last updated time

**User Workflow**:
1. User starts a long-running batch (1000+ records)
2. User closes browser or navigates away
3. Hours later, user returns to **Batch Execution tab**
4. System automatically detects active execution and shows alert at top with current progress
5. User clicks "View Progress Below" to see detailed execution status
6. Alternatively, user can go to **History tab** after completion and click "View Execution"

**Active Execution Detection**:
- When Batch Execution tab loads, `checkForActiveExecutions()` queries all batches
- If active execution found, shows prominent alert with batch name and progress
- "View Progress Below" button auto-selects the batch and scrolls to progress section
- Works even if user closed browser - detects in-memory active executions on server

---

## Previous Update: History Tab & Wide-Format CSV Export (October 21, 2025)

### 1. History Tab Implementation

**Features**:
- View all batch execution history in a table
- Download individual batch CSVs
- Download combined CSV merging all batches
- Automatic history cleanup (one record per batch)
- Execution statistics: total records, success/error counts, duration

**Database Schema** (`execution_history` table):
- `batch_id` (PRIMARY KEY) - ensures one history record per batch
- `batch_name`, `dataset_name` - for display and filtering
- `total_records`, `success_count`, `error_count` - statistics
- `execution_time` - duration in seconds
- `csv_data` - complete CSV stored as TEXT
- `executed_at` - timestamp

**API Endpoints**:
- `GET /api/analysis/history` - Get all execution history
- `GET /api/analysis/history/<batch_id>/csv` - Download batch CSV
- `GET /api/analysis/history/combined-csv` - Download merged CSV
- `DELETE /api/analysis/history/<batch_id>` - Delete history (auto on re-run)

**UI Features**:
- Tabular display with batch name, dataset, execution time, statistics
- Download buttons for each batch
- "Download Combined CSV" button merges all batches
- Auto-loads when History tab is opened

### 2. CSV Format Changed to Wide Format (Analytics-Ready)

**Problem**: The previous "long" format (Record ID, Parameter Name, Value) doesn't work for analytics because:
- Cannot pivot on text fields in CRM Analytics
- Difficult to join back to source data
- Not suitable for analytical queries

**Old Format** (Long/Narrow):
```csv
Record ID,Batch Name,Dataset Name,Parameter Name,Value
REC-001,Batch1,Dataset1,condition,Diabetes
REC-001,Batch1,Dataset1,severity,High
REC-001,Batch1,Dataset1,risk_score,8.5
```

**New Format** (Wide):
```csv
Record ID,condition,risk_score,severity
REC-001,Diabetes,8.5,High
REC-002,Hypertension,6.2,Medium
REC-003,COPD,9.1,High
```

**Benefits**:
- ✅ One row per record - easy to join to source data
- ✅ Each JSON response field becomes a column
- ✅ Direct import into analytics tools
- ✅ Can join multiple batch results using Record ID
- ✅ Measures (numbers) and dimensions (text) in proper columns

**Implementation** (`app.py:1602-1654`):
- Two-pass algorithm: collect all unique fields, then write rows
- Columns sorted alphabetically for consistency
- Complex values (arrays, objects) stored as JSON strings
- Missing values filled with empty strings

### 3. Combined CSV Export with Column Merging

**Feature**: Download all batch executions merged into one CSV file

**How It Works**:
1. Loads all execution history CSVs
2. Merges by Record ID (like a SQL JOIN)
3. Prefixes columns with batch name to avoid conflicts
4. Fills missing values with empty strings

**Example Combined CSV**:
```csv
Record ID,Batch1_condition,Batch1_severity,Batch2_risk_score,Batch2_complications
REC-001,Diabetes,High,8.5,Retinopathy
REC-002,Hypertension,Medium,6.2,
REC-003,COPD,,9.1,Respiratory Failure
```

**Use Case**: Run multiple analysis batches on the same dataset, download one CSV with all results, join to source data for comprehensive analysis.

### 4. Record ID Field from Dataset Configuration

**Change**: CSV now uses the `record_id_field` configured in the Dataset tab, not Salesforce's literal `Id` field.

**Why**: Different datasets may use different identifier fields (ClaimNumber, CaseID, etc.)

**Implementation** (`app.py:1433-1439`, `1509-1513`):
- Loads `record_id_field` from dataset configuration
- Uses that field as the Record ID in CSV exports
- Falls back to common fields (Id, Name) if no config

**Benefit**: CSV Record IDs match your analytical dataset's primary key for easy joins.

---

## Previous Update: Prompt Builder & Proving Ground Improvements (October 21, 2025)

### 1. Fixed: Prompt Builder Now Shows Only Selected Fields

**Problem**: Prompt Builder was displaying all fields from the CRM Analytics dataset, not just the fields selected in the dataset configuration.

**Solution**: Implemented batch-to-config linking and field filtering:

**Changes Made**:

1. **Database Schema Update** (`app.py`):
   - Added `dataset_config_id` column to `batches` table
   - Created migration function to add column to existing databases
   - Updated batch creation to store the dataset configuration ID

2. **New API Endpoint** (`app.py`):
   - Added `GET /api/analysis/batches/<batch_id>/fields`
   - Returns only the fields selected in the dataset configuration
   - Falls back to all fields if no config is linked (backward compatibility)

3. **Frontend Updates** (`main.js`):
   - Updated `createNewAnalysis()` to pass `dataset_config_id` when creating batch
   - Modified `loadDatasetFieldsForPrompt()` to use new batch-specific fields endpoint
   - Changed parameter from `datasetId` to `batchId`

**Technical Details**:
```python
# New endpoint filters fields based on dataset configuration
@app.route('/api/analysis/batches/<batch_id>/fields')
def get_batch_fields(batch_id):
    # Get batch -> find dataset_config_id
    # Get config -> parse selected_fields JSON
    # Filter all_fields to only selected fields
    # Return filtered list
```

**Migration**:
- Existing batches without `dataset_config_id` will fall back to showing all fields
- New batches created after this update will only show configured fields
- No data loss or breaking changes

**Benefits**:
- Cleaner prompt builder interface with only relevant fields
- Consistency between dataset configuration and prompt building
- Reduces confusion when working with datasets that have many fields

### 2. Enhanced: Proving Ground Record ID Input

**Problem**: Proving Ground only accepted comma-delimited record IDs, making it difficult to paste from Excel.

**Solution**: Updated input parsing to accept multiple delimiter types.

**Changes Made**:

1. **Frontend UI** (`main.html`):
   - Updated label and placeholder text to indicate multiple delimiter support
   - Changed card title from "Claim Names" to "Record IDs" (more generic)
   - Increased textarea rows from 3 to 5 for better visibility
   - Added help text: "You can paste directly from Excel"

2. **JavaScript Parsing** (`main.js`):
   - Updated regex to split on comma, tab, space, or newline: `/[\s,\t\n]+/`
   - Handles any combination of delimiters
   - Trims whitespace from each value
   - Filters out empty values

**Supported Input Formats**:
```
Comma-separated:     Record-001, Record-002, Record-003
Space-separated:     Record-001 Record-002 Record-003
Tab-separated:       Record-001	Record-002	Record-003
Newline-separated:   Record-001
                     Record-002
                     Record-003
Mixed:               Record-001, Record-002
                     Record-003	Record-004 Record-005
```

**Excel Copy/Paste**:
- Copy single column: Works (newline-delimited)
- Copy single row: Works (tab-delimited)
- Copy from multiple cells: Works (mixed tab/newline)

**Benefits**:
- Seamless Excel integration
- Flexible input format
- No need to manually reformat data before pasting

### 3. Optimized: Proving Ground for Large Datasets

**Problem**: Proving Ground was loading up to 1000 records into memory and filtering client-side, which doesn't scale for large datasets (10,000+ records).

**Solution**: Use SAQL filters to query specific records directly by their ID field, avoiding in-memory filtering.

**Changes Made**:

1. **Backend** (`app.py:1173-1234`):
   - Get dataset configuration to find the record ID field
   - Query each record individually using SAQL filters: `filter q by 'RecordID' == "value"`
   - Only loads the exact records requested (not all 1000+)
   - Returns `record_id` instead of generic `claim_name`

2. **Frontend** (`main.js`):
   - Updated table display to show `Record ID` column
   - Updated CSV export to use `record_id`

**Before**:
```python
# Load 1000 records into memory
all_records = query_dataset(dataset_id, all_fields, limit=1000)
# Filter in Python
matched = [r for r in all_records if r['Name'] in record_ids]
```

**After**:
```python
# Query each record directly
for record_id in record_ids:
    records = query_dataset(dataset_id, fields, limit=1,
                           filters={record_id_field: record_id})
```

**Benefits**:
- Works with datasets of any size (10,000+ records)
- No memory overhead for large datasets
- Faster execution (only queries needed records)
- Uses dataset configuration's record ID field

### 4. Optimized: Query Only Fields Used in Prompt Template

**Problem**: Batch Execution was querying ALL fields from the dataset, even if the prompt only used a few fields.

**Solution**: Extract field names from prompt template using `{{field_name}}` syntax and only query those fields.

**Changes Made**:

1. **Batch Execution** (`app.py:1432-1453`):
   - Extract template fields using `PromptEngine.extract_variables()`
   - Validate fields exist in dataset before querying
   - Only query fields that are actually used in the template
   - Include record ID field from dataset configuration

**Example**:
```python
# Prompt template:
"Analyze claim {{ClaimNumber}} with diagnosis {{Diagnosis}}"

# Before: Query 50+ fields
# After: Query only ['ClaimNumber', 'Diagnosis', 'Name', 'Id']
```

**Benefits**:
- Faster query execution (smaller SAQL payload)
- Reduced network bandwidth
- Better performance with datasets that have many fields
- Only retrieves data that's actually used

**Note**: Preview execution already had this optimization (lines 937-958).

---

## Previous Update: LLM Response Parsing & Preview Enhancements (October 21, 2025)

### Major Changes: LM Studio JSON Extraction & Preview Record Selection

#### 1. LM Studio Response Parsing Improvements
**Problem**: LM Studio models were returning extra text, special tokens, and JSON schema metadata mixed with actual response data.

**Solution**: Implemented robust JSON extraction in `extract_json_from_llm_response()` function:

- **Brace-Matching Algorithm**: Finds the last `}` in the response and works backwards to find its matching `{`, extracting the complete JSON object
- **Schema Metadata Removal**: Automatically filters out JSON schema fields (`$schema`, `type`, `properties`, `required`, etc.) from responses
- **Special Token Handling**: Works with any LM Studio output format, regardless of special tokens like `<|constrain|>`, `<|end|>`, `<|start|>`, `<|channel|>`, etc.
- **Thinking Text Ignored**: All reasoning/thinking text before the JSON is automatically discarded

**Example Transformation**:
```
Input (from LM Studio):
Could be "Cholecystitis"... Let's choose "Acute appendicitis".<|constrain|>JSON code:<|end|>
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {...},
  "required": ["primaryDiagnosis"],
  "primaryDiagnosis": "Acute appendicitis"
}

Output (cleaned):
{"primaryDiagnosis": "Acute appendicitis"}
```

**Applied To**:
- Prompt preview execution
- Proving Ground execution
- Batch execution
- Schema generation

#### 2. Preview Modal Enhancement
**Previous Behavior**: Preview button immediately executed on random sample record
**New Behavior**: Two-step preview process with record selection

**Features**:
- **Record ID Input**: Optional text field to specify exact record to preview
- **Random Fallback**: Leave blank to use random sample (original behavior)
- **Execute Button**: Explicit button to run preview after choosing record
- **Dataset Configuration Integration**: Uses the Record ID field defined in dataset configuration

**Implementation**:
- Frontend: Split `previewPrompt()` into modal opening and `executePreview()` for execution
- Backend: Updated `/api/analysis/preview-prompt-execute` to accept optional `record_id` parameter
- Database: Queries `dataset_configs` table to get Record ID field name for filtering

#### 3. SAQL Filter Syntax Fix
**Issue**: SAQL filters were using incorrect quote syntax
**Fix**: Changed field names from double quotes to single quotes in filter conditions

```sql
-- Before (incorrect):
q = filter q by "Name" == "020162";

-- After (correct):
q = filter q by 'Name' == "020162";
```

**Location**: `salesforce_client.py` - `query_dataset()` method

#### 4. LM Studio Timeout Extension
**Previous**: 60 seconds (1 minute)
**New**: 600 seconds (10 minutes)

**Reason**: Complex prompts with large context can take several minutes to process
**Affected Methods**:
- `_generate_lmstudio()`
- `_generate_lmstudio_chat()`

### Technical Implementation Details

#### JSON Extraction Algorithm (app.py)
```python
def extract_json_from_llm_response(response: str) -> str:
    # Find last '}' and work backwards to matching '{'
    last_brace = response.rfind('}')
    brace_count = 0
    for i in range(last_brace, -1, -1):
        if response[i] == '}': brace_count += 1
        elif response[i] == '{':
            brace_count -= 1
            if brace_count == 0:
                json_str = response[i:last_brace+1]
                # Parse and remove schema fields
                parsed = json.loads(json_str)
                schema_fields = {'$schema', 'type', 'properties', ...}
                cleaned = {k: v for k, v in parsed.items() if k not in schema_fields}
                return json.dumps(cleaned)
```

#### Preview Modal Workflow (main.html + main.js)
1. User clicks "Preview with Sample Record" button
2. Modal opens with Record ID input field visible
3. User optionally enters specific Record ID or leaves blank
4. User clicks "Execute Preview" button
5. Backend queries for specific record or random sample
6. Results displayed in modal

#### Backend Preview Logic (app.py)
```python
# Get dataset configuration to find record ID field
dataset_config = get_dataset_config(batch['dataset_id'])
record_id_field = dataset_config['record_id_field']

# Query by specific record or random sample
if record_id:
    filters = {record_id_field: record_id}
    sample_records = client.query_dataset(batch['dataset_id'], field_names,
                                         limit=1, filters=filters)
else:
    sample_records = client.query_dataset(batch['dataset_id'], field_names, limit=1)
```

### Files Modified

1. **app.py**:
   - Enhanced `extract_json_from_llm_response()` with brace-matching algorithm
   - Added `import re` for pattern matching (though ultimately not needed)
   - Updated `preview_prompt_execute()` to support optional `record_id` parameter
   - Query dataset configuration to get Record ID field name

2. **lm_studio_client.py**:
   - Increased timeout from 60 to 600 seconds in `_generate_lmstudio()`
   - Increased timeout from 60 to 600 seconds in `_generate_lmstudio_chat()`

3. **salesforce_client.py**:
   - Fixed SAQL filter syntax: `'FieldName' == "value"` instead of `"FieldName" == "value"`

4. **templates/main.html**:
   - Added Record ID input field to preview modal
   - Added "Execute Preview" button
   - Changed preview loading state to be hidden by default
   - Added record selection section to modal

5. **static/js/main.js**:
   - Split `previewPrompt()` - now only opens modal and resets state
   - Created `executePreview()` - executes preview with optional record ID
   - Added event listener for "Execute Preview" button

### Benefits

1. **Reliable JSON Parsing**: No longer breaks on LM Studio's special tokens or thinking text
2. **Clean Response Data**: Automatic removal of JSON schema metadata fields
3. **Flexible Testing**: Can test prompts on specific records or random samples
4. **Longer Processing Time**: 10-minute timeout accommodates complex prompts
5. **Correct SAQL Queries**: Fixed syntax ensures filters work properly

---

## Previous Update: Multiple Dataset Management (October 21, 2025)

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
