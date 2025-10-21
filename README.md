# Clinical Genius - CRM Analytics Prompt Execution Application

[![Version](https://img.shields.io/badge/version-2.0-blue.svg)](https://github.com/yourusername/clinical-genius)
[![Python](https://img.shields.io/badge/python-3.8+-green.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/flask-3.0+-red.svg)](https://flask.palletsprojects.com/)

A Flask-based web application that bridges Salesforce CRM Analytics datasets with Large Language Models (LLMs), enabling AI-powered data enrichment and analysis workflows.

## Business Purpose

Clinical Genius enables organizations to enrich their Salesforce CRM Analytics data with AI-generated insights by:

- **Designing AI Prompts**: Create sophisticated prompts that reference fields from CRM Analytics datasets
- **Testing Iteratively**: Validate prompts against sample records in a safe "Proving Ground" environment
- **Executing at Scale**: Run prompts across thousands of records with real-time progress tracking
- **Structuring Results**: Define JSON response schemas for consistent, analyzable outputs
- **Integrating Seamlessly**: Export structured results back to CRM Analytics for downstream analysis

### Use Cases

- **Claims Processing**: Extract medical codes, severity indicators, or risk factors from claim descriptions
- **Customer Insights**: Generate sentiment analysis, categorization, or recommendations from customer feedback
- **Data Enrichment**: Add computed fields, classifications, or summaries to existing analytics datasets
- **Quality Assurance**: Validate data completeness, accuracy, or compliance using AI-powered rules

## Features

- 📊 **Analysis Management**: Create and manage analysis batches linked to CRM Analytics datasets
- ✏️ **Prompt Builder**: Design prompts with field variable substitution (`{{Field_Name}}`)
- 🤖 **AI Schema Generation**: Generate JSON response schemas from natural language descriptions
- 🧪 **Proving Ground**: Test prompts on specific records before full execution
- 🚀 **Batch Execution**: Process thousands of records with real-time progress tracking and ETA
- 📥 **Structured CSV Export**: Consistent format (Record ID, Batch Name, Parameter, Value)
- ☁️ **CRM Analytics Integration**: Automatic upload to Structured_Response dataset
- 🔄 **Auto Token Refresh**: Seamless re-authentication when Salesforce tokens expire
- 🤖 **Multi-Provider LLM Support**:
  - LM Studio (local or remote)
  - OpenAI ChatGPT API
  - Microsoft Copilot API

## Project Architecture

### High-Level Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     User Interface (Browser)                     │
│  ┌──────────┬───────────────┬────────────────┬──────────────┐  │
│  │ Analysis │ Prompt Builder│ Proving Ground │Batch Execution│  │
│  └──────────┴───────────────┴────────────────┴──────────────┘  │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTP/REST API
┌────────────────────────────▼────────────────────────────────────┐
│                     Flask Backend (Python)                       │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ API Routes │ Batch Manager │ Progress Tracker │ CSV Gen  │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────┬─────────────────┬────────────────────┬───────────────────┘
      │                 │                    │
      ▼                 ▼                    ▼
┌──────────┐   ┌─────────────────┐   ┌──────────────┐
│ SQLite   │   │   Salesforce    │   │ LLM Providers│
│ Database │   │  CRM Analytics  │   │ (LM Studio,  │
└──────────┘   │      API        │   │ OpenAI, etc) │
               └─────────────────┘   └──────────────┘
```

### Component Details

- **Frontend**: Bootstrap 5, vanilla JavaScript, single-page app with tabs
- **Backend**: Flask 3.0+, RESTful API, background threading for batch execution
- **Database**: SQLite for analysis batches and prompt configurations
- **Integrations**: Salesforce JWT auth, CRM Analytics SAQL queries, multi-provider LLM clients

### Data Flow

1. User creates analysis batch linked to CRM Analytics dataset
2. User builds prompt template with field variables in Prompt Builder
3. User defines response schema (manual or AI-generated)
4. User tests prompt in Proving Ground with sample records
5. User executes full batch with progress tracking
6. System generates structured CSV and uploads to CRM Analytics

---

## Installation

### Prerequisites

- **Python 3.8+**
- **Salesforce CLI** (`sf` command) - for JWT authentication
- **Salesforce Developer Edition** or Enterprise org with CRM Analytics enabled
- **LLM Provider** (one of):
  - LM Studio running locally
  - OpenAI API key
  - Microsoft Copilot API key

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/clinical-genius.git
cd clinical-genius
```

### 2. Install Python Dependencies

```bash
pip install -r requirements.txt
```

**requirements.txt:**
```
Flask==3.0.0
python-dotenv==1.0.0
requests==2.31.0
cryptography==41.0.7
```

### 3. Configure Salesforce Connected App

1. In Salesforce Setup, create a new Connected App:
   - Enable OAuth Settings
   - Enable "Use digital signatures"
   - Upload your certificate (generate with OpenSSL)
   - Add OAuth Scopes: `api`, `refresh_token`, `offline_access`
   - Note the Consumer Key (Client ID)

2. Generate certificate files:
```bash
# Generate private key
openssl genrsa -des3 -out server.pass.key 4096
openssl rsa -in server.pass.key -out server.key

# Generate certificate
openssl req -new -key server.key -out server.csr
openssl x509 -req -days 365 -in server.csr -signkey server.key -out server.crt

# Convert to PKCS8 format
openssl pkcs8 -topk8 -inform PEM -outform PEM -in server.key -out server.pem -nocrypt
```

### 5. Set Environment Variables

Create a `.env` file in the project root:

```env
# Salesforce Configuration
SFDC_USERNAME=your-salesforce-username@example.com
SFDC_CLIENT_ID=your-connected-app-consumer-key
SFDC_LOGIN_URL=https://login.salesforce.com
KEY_PASS=your-certificate-passphrase

# LLM Configuration (choose one or more)
LLM_PROVIDER=lmstudio  # or 'openai' or 'copilot'
LM_STUDIO_ENDPOINT=http://localhost:1234
OPENAI_API_KEY=sk-your-openai-api-key
COPILOT_API_KEY=your-copilot-api-key

# Model Configuration
LLM_MODEL=gpt-3.5-turbo
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=4000

# Flask Configuration
SECRET_KEY=your-secret-key-change-in-production
```

### 6. Start the Application

```bash
python app.py
```

The application will start on `http://localhost:4000`

- **Main Application**: http://localhost:4000/
- **Synthetic Data Generator** (legacy): http://localhost:4000/synthetic

---

## Usage Guide

### 1. Analysis Tab - Create a Batch

1. Click **"Create New Analysis"**
2. Enter a batch name (e.g., "Claims Severity Analysis")
3. Select a CRM Analytics dataset
4. Add an optional description
5. Click **"Create Analysis"**

### 2. Prompt Builder Tab - Design Your Prompt

1. Select your analysis batch from the dropdown
2. Click on dataset fields to insert them into your prompt template
   - Fields are inserted as `{{Field_Name}}`
3. Write your prompt instructions:
   ```
   Analyze this claim description: {{Claim_Description__c}}

   Identify the primary medical condition, severity (Low/Medium/High),
   and any risk factors mentioned.
   ```
4. (Optional) Describe your desired response structure in natural language
5. Click **"Generate JSON Schema"** to create a structured response format
6. Review and edit the JSON schema as needed
7. Configure model settings (provider, temperature, max tokens)
8. Click **"Save Prompt"**
9. Click **"Preview with Sample Record"** to test your prompt

### 3. Proving Ground Tab - Test with Specific Records

1. Select your analysis batch
2. Enter comma-delimited record names to test:
   ```
   CLM-001, CLM-042, CLM-137
   ```
3. Review the displayed prompt and schema
4. Click **"Run Prompt"**
5. Review results in the dynamic table
6. Export to CSV if needed

### 4. Batch Execution Tab - Execute at Scale

1. Select your analysis batch
2. Verify prompt is configured (green badge)
3. Click **"Execute Batch"**
4. Monitor real-time progress:
   - Progress bar with percentage
   - Current/total record counter
   - Estimated time to completion
   - Status messages
5. When complete, review statistics
6. Download the CSV file
7. Results are automatically uploaded to the `Structured_Response` CRM Analytics dataset

### 5. Analyze Results in CRM Analytics

The structured CSV format ensures consistency:

| Record ID | Batch Name | Parameter Name | Value |
|-----------|------------|----------------|-------|
| CLM-001 | Claims Analysis | condition | Diabetes Type 2 |
| CLM-001 | Claims Analysis | severity | High |
| CLM-001 | Claims Analysis | risk_factors | ["Obesity", "Hypertension"] |

This format allows you to:
- Filter by batch name to isolate specific runs
- Pivot on parameter names to analyze trends
- Join back to source data using Record ID

---

## API Endpoints

### Main Application
- `GET /` - Main application UI
- `GET /synthetic` - Synthetic data generator (legacy)

### Authentication
- `POST /api/authenticate` - Salesforce JWT authentication

### CRM Analytics
- `GET /api/crm-analytics/datasets` - List all datasets
- `GET /api/crm-analytics/datasets/<id>/fields` - Get dataset fields
- `POST /api/crm-analytics/datasets/<id>/query` - Query dataset records

### Analysis Management
- `GET /api/analysis/batches` - List all batches
- `POST /api/analysis/batches` - Create new batch
- `GET /api/analysis/batches/<id>` - Get batch details
- `DELETE /api/analysis/batches/<id>` - Delete batch

### Prompt Management
- `GET /api/analysis/prompts/<batch_id>` - Get prompt configuration
- `POST /api/analysis/prompts` - Save prompt configuration
- `POST /api/analysis/preview-prompt-execute` - Preview prompt with sample
- `POST /api/analysis/generate-schema` - AI-powered schema generation

### Execution
- `POST /api/analysis/execute-proving-ground` - Execute on specific records
- `POST /api/analysis/execute-batch` - Start batch execution
- `GET /api/analysis/batch-progress/<execution_id>` - Get progress status
- `GET /api/analysis/download-batch-csv/<execution_id>` - Download CSV

---

## Project Structure

```
clinical-genius/
├── app.py                      # Main Flask application
├── salesforce_client.py        # Salesforce CRM Analytics client
├── sfdcJwtAuth.py              # Salesforce JWT authentication
├── lm_studio_client.py         # Multi-provider LLM client
├── prompt_engine.py            # Prompt template engine
├── templates/
│   ├── main.html               # Main application UI
│   └── index.html              # Synthetic data generator UI
├── static/
│   ├── css/
│   │   └── main.css            # Application styles
│   └── js/
│       └── main.js             # Application logic
├── force-app/                  # Salesforce metadata
├── requirements.txt            # Python dependencies
├── requirements.md             # Technical requirements
├── dev_notes.md                # Development notes
├── README.md                   # This file
└── .env                        # Environment configuration

```

## Troubleshooting

### Salesforce Authentication Fails

**Error**: "Authentication failed: invalid_grant"
- **Solution**: Verify certificate uploaded to Connected App matches `server.crt`
- **Check**: User is authorized for the Connected App in Salesforce Setup
- **Verify**: `SFDC_USERNAME`, `SFDC_CLIENT_ID`, `KEY_PASS` in `.env`

### LM Studio Connection Fails

**Error**: "Could not connect to LM Studio at http://localhost:1234"
- **Solution**: Ensure LM Studio is running and has a model loaded
- **Check**: LM Studio → Local Server → Server Status = Running
- **Verify**: Port 1234 is not blocked by firewall

### SAQL Query Errors

**Error**: "Need to use currentVersionId"
- **Solution**: This is handled automatically by the application
- **If persists**: Check CRM Analytics dataset permissions and versioning

### Progress Tracking Stops

**Symptom**: Polling stops before batch completion
- **Solution**: Check browser console for JavaScript errors
- **Restart**: Return to Batch Execution tab to resume monitoring

### CSV Upload to CRM Analytics Fails

**Note**: Current implementation saves CSV to `/tmp/` for manual upload
- **TODO**: Implement full CRM Analytics External Data API integration
- **Workaround**: Download CSV and upload manually via CRM Analytics UI

---

## Development

### Running in Development Mode

```bash
export FLASK_ENV=development
export FLASK_DEBUG=1
python app.py
```

### Adding New LLM Providers

1. Add provider-specific methods to `lm_studio_client.py`
2. Update `generate()` and `generate_chat()` to route to new provider
3. Add provider option to Prompt Builder UI dropdown
4. Update environment variable documentation

---

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Commit your changes: `git commit -m 'Add amazing feature'`
4. Push to the branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

---

## License

MIT License - see LICENSE file for details

---

## Support

For questions, issues, or feature requests:

- **GitHub Issues**: https://github.com/yourusername/clinical-genius/issues
- **Documentation**: See `requirements.md` for detailed technical specifications
- **Development Notes**: See `dev_notes.md` for implementation details

---

**Built with ❤️ by Andrew Beder - October 2025**
