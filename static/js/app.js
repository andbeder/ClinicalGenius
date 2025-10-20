// Global state
let currentFields = [];
let currentRecords = [];
let config = {};

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    loadConfig();
    loadFields();
    loadRecords();

    // Initialize UI based on provider
    updateProviderUI();

    // Set up provider change handler
    document.getElementById('llm-provider').addEventListener('change', function() {
        updateProviderUI();
    });

    // Set up batch mode change handler
    document.getElementById('batch-update').addEventListener('change', function() {
        document.getElementById('insert-count-group').style.display = 'none';
    });

    document.getElementById('batch-insert').addEventListener('change', function() {
        document.getElementById('insert-count-group').style.display = 'block';
    });
});

// API Helper
async function apiCall(endpoint, options = {}) {
    try {
        const response = await fetch(endpoint, {
            ...options,
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            }
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || 'API request failed');
        }

        return data;
    } catch (error) {
        console.error('API Error:', error);
        showError(error.message);
        throw error;
    }
}

// Update UI based on provider selection
function updateProviderUI() {
    const provider = document.getElementById('llm-provider').value;
    const endpointGroup = document.getElementById('lm-endpoint-group');

    if (provider === 'lmstudio') {
        endpointGroup.style.display = 'block';
    } else {
        endpointGroup.style.display = 'none';
    }
}

// Load LLM configuration
async function loadConfig() {
    try {
        const data = await apiCall('/api/lm-studio/config');
        config = data.config;

        document.getElementById('llm-provider').value = config.provider || 'lmstudio';
        document.getElementById('lm-endpoint').value = config.endpoint || 'http://localhost:1234';
        document.getElementById('temperature').value = config.temperature || 0.7;
        document.getElementById('max-tokens').value = config.max_tokens || 4000;

        // Update UI after loading config
        updateProviderUI();
    } catch (error) {
        console.error('Failed to load config:', error);
    }
}

// Save LLM configuration
async function saveConfig() {
    const newConfig = {
        provider: document.getElementById('llm-provider').value,
        endpoint: document.getElementById('lm-endpoint').value,
        temperature: parseFloat(document.getElementById('temperature').value),
        max_tokens: parseInt(document.getElementById('max-tokens').value)
    };

    try {
        await apiCall('/api/lm-studio/config', {
            method: 'POST',
            body: JSON.stringify(newConfig)
        });

        config = newConfig;
        showSuccess('Configuration updated successfully', 'connection-status');
    } catch (error) {
        showError('Failed to update configuration: ' + error.message, 'connection-status');
    }
}

// Test LLM connection
async function testConnection() {
    await saveConfig();

    showInfo('Testing connection...', 'connection-status');

    try {
        const data = await apiCall('/api/test-prompt', {
            method: 'POST',
            body: JSON.stringify({
                prompt_template: 'Say "Connection successful!"',
                record_id: currentRecords[0]?.Id || 'test'
            })
        });

        showSuccess('✓ Connection successful! Response: ' + data.completion, 'connection-status');
    } catch (error) {
        showError('✗ Connection failed: ' + error.message, 'connection-status');
    }
}

// Load Salesforce fields
async function loadFields() {
    try {
        const data = await apiCall('/api/fields');
        currentFields = data.fields;

        // Populate target field dropdown
        const targetField = document.getElementById('target-field');
        targetField.innerHTML = '<option value="">-- Select a field --</option>';

        // Populate fields container
        const fieldsContainer = document.getElementById('fields-container');
        fieldsContainer.innerHTML = '';

        data.fields.forEach(field => {
            // Add to target field dropdown if updateable and is a long text field
            // Salesforce returns 'textarea' for Long Text Area fields
            const isLongText = field.type && field.type.toLowerCase() === 'textarea';

            if (field.updateable && isLongText) {
                const option = document.createElement('option');
                option.value = field.name;
                option.textContent = `${field.label} (${field.name})`;
                targetField.appendChild(option);
            }

            // Add to fields container
            const fieldTag = document.createElement('div');
            fieldTag.className = 'field-tag';
            fieldTag.innerHTML = `
                <span class="field-name">${field.name}</span>
                <span class="field-label">${field.label} - ${field.type}</span>
            `;
            fieldTag.onclick = () => insertFieldVariable(field.name);
            fieldsContainer.appendChild(fieldTag);
        });

        showSuccess(`Loaded ${data.fields.length} fields`, 'records-info');
    } catch (error) {
        showError('Failed to load fields: ' + error.message, 'records-info');
    }
}

// Load Salesforce records
async function loadRecords() {
    try {
        const data = await apiCall('/api/records');
        currentRecords = data.records;

        // Populate test record dropdown
        const testRecord = document.getElementById('test-record');
        testRecord.innerHTML = '<option value="">-- Select a record --</option>';

        data.records.forEach((record, index) => {
            const option = document.createElement('option');
            option.value = record.Id;
            option.textContent = `Record ${index + 1}: ${record.Id}`;
            testRecord.appendChild(option);
        });

        showSuccess(`Loaded ${data.count} records`, 'records-info');
    } catch (error) {
        showError('Failed to load records: ' + error.message, 'records-info');
    }
}

// Create new record
async function createNewRecord() {
    if (!confirm('Create a new empty Claim__c record?')) {
        return;
    }

    try {
        const data = await apiCall('/api/create-record', {
            method: 'POST',
            body: JSON.stringify({})
        });

        showSuccess(`Created new record: ${data.record_id}`, 'records-info');
        await loadRecords();
    } catch (error) {
        showError('Failed to create record: ' + error.message, 'records-info');
    }
}

// Insert field variable into prompt template
function insertFieldVariable(fieldName) {
    const promptTemplate = document.getElementById('prompt-template');
    const cursorPos = promptTemplate.selectionStart;
    const textBefore = promptTemplate.value.substring(0, cursorPos);
    const textAfter = promptTemplate.value.substring(cursorPos);

    promptTemplate.value = textBefore + `{{${fieldName}}}` + textAfter;
    promptTemplate.focus();
    promptTemplate.selectionStart = promptTemplate.selectionEnd = cursorPos + fieldName.length + 4;
}

// Test prompt on single record
async function testPrompt() {
    const recordId = document.getElementById('test-record').value;
    const promptTemplate = document.getElementById('prompt-template').value;
    const targetField = document.getElementById('target-field').value;

    if (!recordId) {
        alert('Please select a record to test');
        return;
    }

    if (!promptTemplate) {
        alert('Please enter a prompt template');
        return;
    }

    await saveConfig();

    const resultsDiv = document.getElementById('test-results');
    resultsDiv.innerHTML = '<div class="spinner-border text-primary" role="status"><span class="visually-hidden">Loading...</span></div> Generating...';
    resultsDiv.className = 'show';

    try {
        const data = await apiCall('/api/test-prompt', {
            method: 'POST',
            body: JSON.stringify({
                record_id: recordId,
                prompt_template: promptTemplate,
                target_field: targetField
            })
        });

        resultsDiv.innerHTML = `
            <div class="alert alert-secondary">
                <h5 class="alert-heading"><i class="bi bi-code-square"></i> Completed Prompt</h5>
                <pre class="mb-0">${escapeHtml(data.prompt)}</pre>
            </div>
            <div class="alert alert-success">
                <h5 class="alert-heading"><i class="bi bi-check-circle"></i> Generated Completion</h5>
                <pre class="mb-0">${escapeHtml(data.completion)}</pre>
            </div>
        `;
    } catch (error) {
        resultsDiv.innerHTML = `
            <div class="alert alert-danger">
                <h5 class="alert-heading"><i class="bi bi-x-circle"></i> Error</h5>
                <pre class="mb-0">${escapeHtml(error.message)}</pre>
            </div>
        `;
    }
}

// Run batch generation
async function runBatchGeneration() {
    const promptTemplate = document.getElementById('prompt-template').value;
    const targetField = document.getElementById('target-field').value;
    const batchMode = document.querySelector('input[name="batchMode"]:checked').value;
    const insertCount = parseInt(document.getElementById('insert-count').value);

    if (!targetField) {
        alert('Please select a target field');
        return;
    }

    if (!promptTemplate) {
        alert('Please enter a prompt template');
        return;
    }

    let confirmMsg;
    if (batchMode === 'update') {
        confirmMsg = `This will update ${currentRecords.length} existing records. Continue?`;
    } else {
        confirmMsg = `This will create ${insertCount} new records. Continue?`;
    }

    if (!confirm(confirmMsg)) {
        return;
    }

    await saveConfig();

    const progressDiv = document.getElementById('batch-progress');
    const resultsDiv = document.getElementById('batch-results');

    progressDiv.className = 'show';
    progressDiv.innerHTML = `
        <div class="progress">
            <div class="progress-bar progress-bar-striped progress-bar-animated" id="progress-bar" style="width: 0%">0%</div>
        </div>
        <p class="text-center mt-2">Processing records...</p>
    `;

    resultsDiv.innerHTML = '';
    resultsDiv.className = '';

    try {
        const data = await apiCall('/api/batch-generate', {
            method: 'POST',
            body: JSON.stringify({
                prompt_template: promptTemplate,
                target_field: targetField,
                mode: batchMode,
                insert_count: batchMode === 'insert' ? insertCount : undefined
            })
        });

        // Update progress to 100%
        const progressBar = document.getElementById('progress-bar');
        progressBar.style.width = '100%';
        progressBar.textContent = '100%';
        progressBar.classList.remove('progress-bar-animated');

        // Show results
        resultsDiv.className = 'show';
        resultsDiv.innerHTML = `
            <div class="alert alert-success">
                <h5 class="alert-heading"><i class="bi bi-check-circle"></i> Batch Generation Complete</h5>
                <hr>
                <p class="mb-1"><strong>Total Records:</strong> ${data.results.total}</p>
                <p class="mb-1"><strong>Successful:</strong> <span class="badge bg-success">${data.results.success}</span></p>
                <p class="mb-1"><strong>Failed:</strong> <span class="badge bg-danger">${data.results.failed}</span></p>
                ${data.results.errors.length > 0 ? `
                    <hr>
                    <h6>Errors:</h6>
                    <pre class="mb-0">${escapeHtml(JSON.stringify(data.results.errors, null, 2))}</pre>
                ` : ''}
            </div>
        `;

        await loadRecords();
    } catch (error) {
        resultsDiv.className = 'show';
        resultsDiv.innerHTML = `
            <div class="alert alert-danger">
                <h5 class="alert-heading"><i class="bi bi-x-circle"></i> Batch Generation Failed</h5>
                <hr>
                <pre class="mb-0">${escapeHtml(error.message)}</pre>
            </div>
        `;
    }
}

// Utility functions
function showSuccess(message, elementId = 'connection-status') {
    const el = document.getElementById(elementId);
    el.className = 'show alert-success';
    el.innerHTML = `<i class="bi bi-check-circle"></i> ${message}`;
    setTimeout(() => el.className = '', 5000);
}

function showError(message, elementId = 'connection-status') {
    const el = document.getElementById(elementId);
    el.className = 'show alert-danger';
    el.innerHTML = `<i class="bi bi-x-circle"></i> ${message}`;
}

function showInfo(message, elementId = 'connection-status') {
    const el = document.getElementById(elementId);
    el.className = 'show alert-info';
    el.innerHTML = `<i class="bi bi-info-circle"></i> ${message}`;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
