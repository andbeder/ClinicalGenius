// Clinical Genius - CRM Analytics Prompt Execution Application

// Global state
let currentDataset = null;
let datasets = [];
let batches = [];
let currentBatch = null;
let datasetFields = [];
let promptConfig = {
    template: '',
    responseSchema: {},
    provider: 'lm_studio',
    endpoint: 'http://localhost:1234/v1/chat/completions',
    temperature: 0.7,
    maxTokens: 4000,
    timeout: 60
};
let provingBatch = null;
let provingResults = [];
let batchExecBatch = null;
let batchExecInterval = null;

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
    setupEventListeners();
});

function initializeApp() {
    // Authenticate with Salesforce
    authenticateSalesforce();

    // Load datasets
    loadDatasets();

    // Load recent batches
    loadBatches();
}

function setupEventListeners() {
    // Tab navigation
    document.querySelectorAll('.sidebar .nav-link').forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            switchTab(this.dataset.tab);
        });
    });

    // Dataset selection
    document.getElementById('dataset-select').addEventListener('change', function() {
        handleDatasetSelection(this.value);
    });

    // Refresh datasets button
    document.getElementById('refresh-datasets-btn').addEventListener('click', function() {
        loadDatasets();
    });

    // Create new analysis button
    document.getElementById('create-batch-btn').addEventListener('click', function() {
        showNewAnalysisModal();
    });

    // Save analysis button
    document.getElementById('save-analysis-btn').addEventListener('click', function() {
        createNewAnalysis();
    });

    // Prompt Builder - Batch selection
    document.getElementById('prompt-batch-select').addEventListener('change', function() {
        handlePromptBatchSelection(this.value);
    });

    // Prompt Builder - Save prompt
    document.getElementById('save-prompt-btn').addEventListener('click', function() {
        savePromptConfiguration();
    });

    // Prompt Builder - Preview prompt
    document.getElementById('preview-prompt-btn').addEventListener('click', function() {
        previewPrompt();
    });

    // Prompt Builder - Validate schema
    document.getElementById('validate-schema-btn').addEventListener('click', function() {
        validateResponseSchema();
    });

    // Prompt Builder - Model provider change
    document.getElementById('model-provider').addEventListener('change', function() {
        handleProviderChange(this.value);
    });

    // Prompt Builder - Generate schema from description
    document.getElementById('generate-schema-btn').addEventListener('click', function() {
        generateSchemaFromDescription();
    });

    // Proving Ground - Batch selection
    document.getElementById('proving-batch-select').addEventListener('change', function() {
        handleProvingBatchSelection(this.value);
    });

    // Proving Ground - Run prompt
    document.getElementById('proving-run-btn').addEventListener('click', function() {
        runProvingGroundPrompt();
    });

    // Proving Ground - Export CSV
    document.getElementById('proving-export-btn').addEventListener('click', function() {
        exportProvingCSV();
    });

    // Batch Execution - Batch selection
    document.getElementById('batch-exec-select').addEventListener('change', function() {
        handleBatchExecSelection(this.value);
    });

    // Batch Execution - Run batch
    document.getElementById('batch-exec-run-btn').addEventListener('click', function() {
        executeBatch();
    });

    // Batch Execution - Retry
    document.getElementById('batch-exec-retry-btn').addEventListener('click', function() {
        executeBatch();
    });

    // Batch Execution - Download CSV
    document.getElementById('batch-exec-download-csv').addEventListener('click', function() {
        downloadBatchCSV();
    });
}

function switchTab(tabName) {
    // Update nav links
    document.querySelectorAll('.sidebar .nav-link').forEach(link => {
        link.classList.remove('active');
    });
    document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');

    // Update tab content
    document.querySelectorAll('.tab-content').forEach(tab => {
        tab.style.display = 'none';
    });
    document.getElementById(`${tabName}-tab`).style.display = 'block';

    // Load tab-specific data
    if (tabName === 'prompt-builder') {
        loadPromptBuilderData();
    } else if (tabName === 'proving-ground') {
        loadProvingGroundData();
    } else if (tabName === 'batch-execution') {
        loadBatchExecutionData();
    }
}

function loadPromptBuilderData() {
    // Populate batch dropdown
    const batchSelect = document.getElementById('prompt-batch-select');
    batchSelect.innerHTML = '<option value="">-- Select an analysis batch --</option>';

    batches.forEach(batch => {
        const option = document.createElement('option');
        option.value = batch.id;
        option.textContent = `${batch.name} (${batch.dataset_name})`;
        batchSelect.appendChild(option);
    });

    // Load saved prompt if batch is already selected
    if (currentBatch) {
        batchSelect.value = currentBatch.id;
        handlePromptBatchSelection(currentBatch.id);
    }
}

async function authenticateSalesforce() {
    try {
        const response = await fetch('/api/authenticate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });

        const data = await response.json();

        if (data.success) {
            updateConnectionStatus('connected');
        } else {
            updateConnectionStatus('error', data.error);
        }
    } catch (error) {
        console.error('Authentication error:', error);
        updateConnectionStatus('error', error.message);
    }
}

function updateConnectionStatus(status, message = '') {
    const statusElement = document.getElementById('connection-status');

    if (status === 'connected') {
        statusElement.innerHTML = '<span class="badge bg-success">Connected</span>';
    } else if (status === 'error') {
        statusElement.innerHTML = `<span class="badge bg-danger" title="${message}">Error</span>`;
    } else {
        statusElement.innerHTML = '<span class="badge bg-secondary">Not Connected</span>';
    }
}

async function loadDatasets() {
    try {
        const response = await fetch('/api/crm-analytics/datasets');
        const data = await response.json();

        if (data.success) {
            datasets = data.datasets;
            populateDatasetDropdowns();
        } else {
            console.error('Failed to load datasets:', data.error);
            showAlert('danger', 'Failed to load datasets: ' + data.error);
        }
    } catch (error) {
        console.error('Error loading datasets:', error);
        showAlert('danger', 'Error loading datasets: ' + error.message);
    }
}

function populateDatasetDropdowns() {
    const selects = ['dataset-select', 'analysis-dataset'];

    selects.forEach(selectId => {
        const select = document.getElementById(selectId);
        const currentValue = select.value;

        // Clear existing options (except first one)
        select.innerHTML = '<option value="">-- Choose a dataset --</option>';

        // Add dataset options
        datasets.forEach(dataset => {
            const option = document.createElement('option');
            option.value = dataset.id;
            option.textContent = dataset.name;
            select.appendChild(option);
        });

        // Restore selection if it still exists
        if (currentValue) {
            select.value = currentValue;
        }
    });
}

function handleDatasetSelection(datasetId) {
    if (!datasetId) {
        document.getElementById('dataset-info').style.display = 'none';
        currentDataset = null;
        return;
    }

    const dataset = datasets.find(ds => ds.id === datasetId);
    if (dataset) {
        currentDataset = dataset;
        displayDatasetInfo(dataset);
    }
}

function displayDatasetInfo(dataset) {
    document.getElementById('dataset-name').textContent = dataset.name;
    document.getElementById('dataset-api-name').textContent = dataset.developerName || dataset.id;
    document.getElementById('dataset-rows').textContent = dataset.rowCount ? dataset.rowCount.toLocaleString() : 'Unknown';
    document.getElementById('dataset-modified').textContent = dataset.lastModifiedDate ?
        new Date(dataset.lastModifiedDate).toLocaleString() : 'Unknown';

    document.getElementById('dataset-info').style.display = 'block';
}

async function loadBatches() {
    document.getElementById('batches-loading').style.display = 'block';
    document.getElementById('batches-list').style.display = 'none';
    document.getElementById('no-batches').style.display = 'none';

    try {
        const response = await fetch('/api/analysis/batches');
        const data = await response.json();

        if (data.success) {
            batches = data.batches;
            displayBatches();
        } else {
            console.error('Failed to load batches:', data.error);
            document.getElementById('batches-loading').style.display = 'none';
            showAlert('danger', 'Failed to load batches: ' + data.error);
        }
    } catch (error) {
        console.error('Error loading batches:', error);
        document.getElementById('batches-loading').style.display = 'none';
        showAlert('danger', 'Error loading batches: ' + error.message);
    }
}

function displayBatches() {
    document.getElementById('batches-loading').style.display = 'none';

    if (batches.length === 0) {
        document.getElementById('no-batches').style.display = 'block';
        return;
    }

    const tbody = document.getElementById('batches-tbody');
    tbody.innerHTML = '';

    batches.forEach(batch => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${escapeHtml(batch.name)}</td>
            <td>${escapeHtml(batch.dataset_name)}</td>
            <td><span class="badge bg-${getStatusBadgeClass(batch.status)}">${batch.status}</span></td>
            <td>${batch.record_count || 0}</td>
            <td>${new Date(batch.created_at).toLocaleString()}</td>
            <td>
                <button class="btn btn-sm btn-primary" onclick="viewBatch('${batch.id}')">View</button>
                <button class="btn btn-sm btn-outline-danger" onclick="deleteBatch('${batch.id}')">Delete</button>
            </td>
        `;
        tbody.appendChild(row);
    });

    document.getElementById('batches-list').style.display = 'block';
}

function getStatusBadgeClass(status) {
    const statusMap = {
        'pending': 'secondary',
        'running': 'primary',
        'completed': 'success',
        'failed': 'danger',
        'partial': 'warning'
    };
    return statusMap[status] || 'secondary';
}

function showNewAnalysisModal() {
    const modal = new bootstrap.Modal(document.getElementById('newAnalysisModal'));
    modal.show();
}

async function createNewAnalysis() {
    const name = document.getElementById('analysis-name').value;
    const datasetId = document.getElementById('analysis-dataset').value;
    const description = document.getElementById('analysis-description').value;

    if (!name || !datasetId) {
        showAlert('warning', 'Please fill in all required fields');
        return;
    }

    try {
        const response = await fetch('/api/analysis/batches', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                name: name,
                dataset_id: datasetId,
                description: description
            })
        });

        const data = await response.json();

        if (data.success) {
            showAlert('success', 'Analysis created successfully');
            bootstrap.Modal.getInstance(document.getElementById('newAnalysisModal')).hide();

            // Clear form
            document.getElementById('new-analysis-form').reset();

            // Reload batches
            loadBatches();
        } else {
            showAlert('danger', 'Failed to create analysis: ' + data.error);
        }
    } catch (error) {
        console.error('Error creating analysis:', error);
        showAlert('danger', 'Error creating analysis: ' + error.message);
    }
}

function viewBatch(batchId) {
    console.log('View batch:', batchId);

    // Find the batch
    const batch = batches.find(b => b.id === batchId);
    if (!batch) {
        showAlert('danger', 'Batch not found');
        return;
    }

    // Set current batch
    currentBatch = batch;

    // Switch to prompt builder tab
    switchTab('prompt-builder');

    // The loadPromptBuilderData function will be called by switchTab
    // and it will populate the batch dropdown and select the current batch
}

async function deleteBatch(batchId) {
    if (!confirm('Are you sure you want to delete this analysis batch?')) {
        return;
    }

    try {
        const response = await fetch(`/api/analysis/batches/${batchId}`, {
            method: 'DELETE'
        });

        const data = await response.json();

        if (data.success) {
            showAlert('success', 'Batch deleted successfully');
            loadBatches();
        } else {
            showAlert('danger', 'Failed to delete batch: ' + data.error);
        }
    } catch (error) {
        console.error('Error deleting batch:', error);
        showAlert('danger', 'Error deleting batch: ' + error.message);
    }
}

function showAlert(type, message) {
    // Create alert element
    const alert = document.createElement('div');
    alert.className = `alert alert-${type} alert-dismissible fade show`;
    alert.setAttribute('role', 'alert');
    alert.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;

    // Insert at top of main content
    const mainContent = document.querySelector('.main-content');
    mainContent.insertBefore(alert, mainContent.firstChild);

    // Auto-dismiss after 5 seconds
    setTimeout(() => {
        alert.remove();
    }, 5000);
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ==================== Prompt Builder Functions ====================

async function handlePromptBatchSelection(batchId) {
    if (!batchId) {
        document.getElementById('prompt-batch-info').style.display = 'none';
        document.getElementById('dataset-fields-container').style.display = 'none';
        document.getElementById('no-batch-selected').style.display = 'block';
        currentBatch = null;
        return;
    }

    // Find the batch
    const batch = batches.find(b => b.id === batchId);
    if (!batch) {
        showAlert('danger', 'Batch not found');
        return;
    }

    currentBatch = batch;

    // Display batch info
    document.getElementById('prompt-dataset-name').textContent = batch.dataset_name;
    document.getElementById('prompt-batch-status').innerHTML =
        `<span class="badge bg-${getStatusBadgeClass(batch.status)}">${batch.status}</span>`;
    document.getElementById('prompt-batch-info').style.display = 'block';

    // Load dataset fields
    await loadDatasetFieldsForPrompt(batch.dataset_id);

    // Load saved prompt configuration
    await loadPromptConfig(batchId);
}

async function loadDatasetFieldsForPrompt(datasetId) {
    document.getElementById('no-batch-selected').style.display = 'none';
    document.getElementById('dataset-fields-loading').style.display = 'block';
    document.getElementById('dataset-fields-container').style.display = 'none';

    try {
        const response = await fetch(`/api/crm-analytics/datasets/${datasetId}/fields`);
        const data = await response.json();

        if (data.success) {
            datasetFields = data.fields;
            displayDatasetFields(data.fields);
        } else {
            showAlert('danger', 'Failed to load dataset fields: ' + data.error);
            document.getElementById('dataset-fields-loading').style.display = 'none';
        }
    } catch (error) {
        console.error('Error loading dataset fields:', error);
        showAlert('danger', 'Error loading dataset fields: ' + error.message);
        document.getElementById('dataset-fields-loading').style.display = 'none';
    }
}

function displayDatasetFields(fields) {
    document.getElementById('dataset-fields-loading').style.display = 'none';
    document.getElementById('dataset-fields-container').style.display = 'block';

    const dimensionsContainer = document.getElementById('dimension-fields');
    const measuresContainer = document.getElementById('measure-fields');

    dimensionsContainer.innerHTML = '';
    measuresContainer.innerHTML = '';

    fields.forEach(field => {
        const fieldItem = createFieldItem(field);

        if (field.type === 'dimension') {
            dimensionsContainer.appendChild(fieldItem);
        } else {
            measuresContainer.appendChild(fieldItem);
        }
    });
}

function createFieldItem(field) {
    const item = document.createElement('div');
    item.className = 'field-item';
    item.innerHTML = `
        <div>
            <div class="field-item-label">${escapeHtml(field.label)}</div>
            <div class="field-item-name">{{${field.name}}}</div>
        </div>
        <span class="field-item-type ${field.type}">${field.type}</span>
    `;

    item.addEventListener('click', function() {
        insertFieldIntoPrompt(field.name);
    });

    return item;
}

function insertFieldIntoPrompt(fieldName) {
    const textarea = document.getElementById('prompt-template');
    const cursorPos = textarea.selectionStart;
    const textBefore = textarea.value.substring(0, cursorPos);
    const textAfter = textarea.value.substring(textarea.selectionEnd);

    textarea.value = textBefore + `{{${fieldName}}}` + textAfter;

    // Move cursor after inserted text
    const newCursorPos = cursorPos + fieldName.length + 4;
    textarea.setSelectionRange(newCursorPos, newCursorPos);
    textarea.focus();

    showAlert('success', `Inserted {{${fieldName}}} into prompt`);
}

async function savePromptConfiguration() {
    if (!currentBatch) {
        showAlert('warning', 'Please select a batch first');
        return;
    }

    // Gather configuration
    const config = {
        batch_id: currentBatch.id,
        prompt_template: document.getElementById('prompt-template').value,
        response_schema: document.getElementById('response-schema').value,
        schema_description: document.getElementById('schema-description').value,
        provider: document.getElementById('model-provider').value,
        endpoint: document.getElementById('lm-studio-endpoint').value,
        temperature: parseFloat(document.getElementById('model-temperature').value),
        max_tokens: parseInt(document.getElementById('model-max-tokens').value),
        timeout: parseInt(document.getElementById('model-timeout').value)
    };

    if (!config.prompt_template) {
        showAlert('warning', 'Please enter a prompt template');
        return;
    }

    // Validate response schema if provided
    if (config.response_schema) {
        try {
            JSON.parse(config.response_schema);
        } catch (e) {
            showAlert('danger', 'Invalid JSON in response schema: ' + e.message);
            return;
        }
    }

    try {
        const response = await fetch('/api/analysis/prompts', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(config)
        });

        const data = await response.json();

        if (data.success) {
            showAlert('success', 'Prompt configuration saved successfully');
            promptConfig = config;
        } else {
            showAlert('danger', 'Failed to save prompt: ' + data.error);
        }
    } catch (error) {
        console.error('Error saving prompt:', error);
        showAlert('danger', 'Error saving prompt: ' + error.message);
    }
}

async function loadPromptConfig(batchId) {
    try {
        const response = await fetch(`/api/analysis/prompts/${batchId}`);
        const data = await response.json();

        if (data.success && data.config) {
            // Populate form fields
            document.getElementById('prompt-template').value = data.config.prompt_template || '';
            document.getElementById('response-schema').value = data.config.response_schema || '';
            document.getElementById('schema-description').value = data.config.schema_description || '';
            document.getElementById('model-provider').value = data.config.provider || 'lm_studio';
            document.getElementById('lm-studio-endpoint').value = data.config.endpoint || 'http://localhost:1234/v1/chat/completions';
            document.getElementById('model-temperature').value = data.config.temperature || 0.7;
            document.getElementById('model-max-tokens').value = data.config.max_tokens || 4000;
            document.getElementById('model-timeout').value = data.config.timeout || 60;

            handleProviderChange(data.config.provider || 'lm_studio');
        }
    } catch (error) {
        console.error('Error loading prompt config:', error);
    }
}

async function previewPrompt() {
    if (!currentBatch) {
        showAlert('warning', 'Please select a batch first');
        return;
    }

    const promptTemplate = document.getElementById('prompt-template').value;
    if (!promptTemplate) {
        showAlert('warning', 'Please enter a prompt template');
        return;
    }

    // Get response schema (optional)
    const responseSchema = document.getElementById('response-schema').value;

    // Get model configuration
    const modelConfig = {
        provider: document.getElementById('model-provider').value,
        endpoint: document.getElementById('lm-studio-endpoint').value,
        temperature: parseFloat(document.getElementById('model-temperature').value),
        max_tokens: parseInt(document.getElementById('model-max-tokens').value),
        timeout: parseInt(document.getElementById('model-timeout').value)
    };

    // Show modal
    const modal = new bootstrap.Modal(document.getElementById('previewPromptModal'));
    modal.show();

    // Reset modal state
    document.getElementById('preview-loading').style.display = 'block';
    document.getElementById('preview-content').style.display = 'none';
    document.getElementById('preview-error').style.display = 'none';

    try {
        const response = await fetch('/api/analysis/preview-prompt-execute', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                batch_id: currentBatch.id,
                prompt_template: promptTemplate,
                response_schema: responseSchema,
                model_config: modelConfig
            })
        });

        const data = await response.json();

        if (data.success) {
            // Hide loading, show content
            document.getElementById('preview-loading').style.display = 'none';
            document.getElementById('preview-content').style.display = 'block';

            // Populate modal with data
            document.getElementById('preview-record-data').textContent =
                JSON.stringify(data.sample_record, null, 2);
            document.getElementById('preview-rendered-prompt').textContent =
                data.rendered_prompt;
            document.getElementById('preview-model-response').textContent =
                data.model_response;
        } else {
            // Show error
            document.getElementById('preview-loading').style.display = 'none';
            document.getElementById('preview-error').style.display = 'block';
            document.getElementById('preview-error-message').textContent = data.error;
        }
    } catch (error) {
        console.error('Error previewing prompt:', error);
        document.getElementById('preview-loading').style.display = 'none';
        document.getElementById('preview-error').style.display = 'block';
        document.getElementById('preview-error-message').textContent =
            'Error executing preview: ' + error.message;
    }
}

function validateResponseSchema() {
    const schemaText = document.getElementById('response-schema').value;

    if (!schemaText) {
        showAlert('warning', 'Please enter a response schema');
        return;
    }

    try {
        const schema = JSON.parse(schemaText);
        showAlert('success', 'Valid JSON schema!');
        console.log('Parsed schema:', schema);
    } catch (e) {
        showAlert('danger', 'Invalid JSON: ' + e.message);
    }
}

function handleProviderChange(provider) {
    const endpointGroup = document.getElementById('lm-studio-endpoint-group');

    if (provider === 'lm_studio') {
        endpointGroup.style.display = 'block';
    } else {
        endpointGroup.style.display = 'none';
    }
}

async function generateSchemaFromDescription() {
    const description = document.getElementById('schema-description').value.trim();

    if (!description) {
        showAlert('warning', 'Please enter a schema description');
        return;
    }

    // Disable button and show loading state
    const button = document.getElementById('generate-schema-btn');
    const originalHtml = button.innerHTML;
    button.disabled = true;
    button.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Generating...';

    try {
        const response = await fetch('/api/analysis/generate-schema', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ description: description })
        });

        const data = await response.json();

        if (data.success) {
            // Populate the schema textarea with generated JSON
            document.getElementById('response-schema').value = data.schema;
            showAlert('success', 'JSON schema generated successfully!');
        } else {
            showAlert('danger', 'Failed to generate schema: ' + data.error);
        }
    } catch (error) {
        console.error('Error generating schema:', error);
        showAlert('danger', 'Error generating schema: ' + error.message);
    } finally {
        // Re-enable button
        button.disabled = false;
        button.innerHTML = originalHtml;
    }
}

// ==================== Proving Ground Functions ====================

function loadProvingGroundData() {
    // Populate batch dropdown
    const batchSelect = document.getElementById('proving-batch-select');
    batchSelect.innerHTML = '<option value="">-- Select an analysis batch --</option>';

    batches.forEach(batch => {
        const option = document.createElement('option');
        option.value = batch.id;
        option.textContent = `${batch.name} (${batch.dataset_name})`;
        batchSelect.appendChild(option);
    });

    // Load saved batch if available
    if (provingBatch) {
        batchSelect.value = provingBatch.id;
        handleProvingBatchSelection(provingBatch.id);
    }
}

async function handleProvingBatchSelection(batchId) {
    if (!batchId) {
        document.getElementById('proving-prompt-display').textContent = 'No prompt configured';
        document.getElementById('proving-schema-display').textContent = 'No schema configured';
        document.getElementById('proving-run-btn').disabled = true;
        provingBatch = null;
        return;
    }

    // Find the batch
    const batch = batches.find(b => b.id === batchId);
    if (!batch) {
        showAlert('danger', 'Batch not found');
        return;
    }

    provingBatch = batch;

    // Load and display the prompt configuration
    try {
        const response = await fetch(`/api/analysis/prompts/${batchId}`);
        const data = await response.json();

        if (data.success && data.config) {
            // Display prompt template
            const promptTemplate = data.config.prompt_template || 'No prompt configured';
            document.getElementById('proving-prompt-display').textContent = promptTemplate;

            // Display response schema
            const responseSchema = data.config.response_schema || 'No schema configured';
            document.getElementById('proving-schema-display').textContent = responseSchema;

            // Enable run button if we have a prompt
            document.getElementById('proving-run-btn').disabled = !data.config.prompt_template;
        } else {
            document.getElementById('proving-prompt-display').textContent = 'No prompt configured for this batch';
            document.getElementById('proving-schema-display').textContent = 'No schema configured';
            document.getElementById('proving-run-btn').disabled = true;
            showAlert('warning', 'No prompt configuration found for this batch. Please configure in Prompt Builder.');
        }
    } catch (error) {
        console.error('Error loading prompt config:', error);
        showAlert('danger', 'Error loading prompt configuration: ' + error.message);
        document.getElementById('proving-run-btn').disabled = true;
    }
}

async function runProvingGroundPrompt() {
    if (!provingBatch) {
        showAlert('warning', 'Please select an analysis batch first');
        return;
    }

    // Get comma-delimited claim names
    const claimNamesText = document.getElementById('proving-claim-names').value.trim();
    if (!claimNamesText) {
        showAlert('warning', 'Please enter at least one claim name');
        return;
    }

    // Parse comma-delimited names
    const claimNames = claimNamesText.split(',').map(name => name.trim()).filter(name => name.length > 0);
    if (claimNames.length === 0) {
        showAlert('warning', 'No valid claim names found');
        return;
    }

    // Show loading state
    const runButton = document.getElementById('proving-run-btn');
    const originalHtml = runButton.innerHTML;
    runButton.disabled = true;
    runButton.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Running...';

    document.getElementById('proving-results-loading').style.display = 'block';
    document.getElementById('proving-results-table').style.display = 'none';
    document.getElementById('proving-results-error').style.display = 'none';

    try {
        const response = await fetch('/api/analysis/execute-proving-ground', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                batch_id: provingBatch.id,
                claim_names: claimNames
            })
        });

        const data = await response.json();

        if (data.success) {
            provingResults = data.results;
            displayProvingResults(data.results);
            showAlert('success', `Successfully executed prompt on ${data.results.length} records`);
        } else {
            document.getElementById('proving-results-loading').style.display = 'none';
            document.getElementById('proving-results-error').style.display = 'block';
            document.getElementById('proving-results-error-message').textContent = data.error;
            showAlert('danger', 'Failed to execute prompt: ' + data.error);
        }
    } catch (error) {
        console.error('Error executing prompt:', error);
        document.getElementById('proving-results-loading').style.display = 'none';
        document.getElementById('proving-results-error').style.display = 'block';
        document.getElementById('proving-results-error-message').textContent = error.message;
        showAlert('danger', 'Error executing prompt: ' + error.message);
    } finally {
        runButton.disabled = false;
        runButton.innerHTML = originalHtml;
    }
}

function displayProvingResults(results) {
    document.getElementById('proving-results-loading').style.display = 'none';
    document.getElementById('proving-results-error').style.display = 'none';

    if (results.length === 0) {
        document.getElementById('proving-results-error').style.display = 'block';
        document.getElementById('proving-results-error-message').textContent = 'No results to display';
        return;
    }

    // Extract all unique keys from all results to build table columns
    const allKeys = new Set();
    results.forEach(result => {
        if (result.response && typeof result.response === 'object') {
            Object.keys(result.response).forEach(key => allKeys.add(key));
        }
    });

    const columns = ['claim_name', ...Array.from(allKeys)];

    // Build table header
    const thead = document.getElementById('proving-results-thead');
    thead.innerHTML = '';
    const headerRow = document.createElement('tr');
    columns.forEach(col => {
        const th = document.createElement('th');
        th.textContent = col;
        headerRow.appendChild(th);
    });
    thead.appendChild(headerRow);

    // Build table body
    const tbody = document.getElementById('proving-results-tbody');
    tbody.innerHTML = '';

    results.forEach(result => {
        const row = document.createElement('tr');

        columns.forEach(col => {
            const td = document.createElement('td');
            if (col === 'claim_name') {
                td.textContent = result.claim_name || 'Unknown';
            } else {
                const value = result.response?.[col];
                if (value !== undefined && value !== null) {
                    td.textContent = typeof value === 'object' ? JSON.stringify(value) : value;
                } else {
                    td.textContent = '-';
                }
            }
            row.appendChild(td);
        });

        tbody.appendChild(row);
    });

    // Show table and export button
    document.getElementById('proving-results-table').style.display = 'block';
    document.getElementById('proving-export-btn').style.display = 'inline-block';
}

function exportProvingCSV() {
    if (provingResults.length === 0) {
        showAlert('warning', 'No results to export');
        return;
    }

    // Extract all unique keys
    const allKeys = new Set();
    provingResults.forEach(result => {
        if (result.response && typeof result.response === 'object') {
            Object.keys(result.response).forEach(key => allKeys.add(key));
        }
    });

    const columns = ['claim_name', ...Array.from(allKeys)];

    // Build CSV content
    let csv = columns.join(',') + '\n';

    provingResults.forEach(result => {
        const row = columns.map(col => {
            let value;
            if (col === 'claim_name') {
                value = result.claim_name || '';
            } else {
                value = result.response?.[col];
            }

            // Handle different value types
            if (value === undefined || value === null) {
                return '';
            } else if (typeof value === 'object') {
                return '"' + JSON.stringify(value).replace(/"/g, '""') + '"';
            } else {
                return '"' + String(value).replace(/"/g, '""') + '"';
            }
        });
        csv += row.join(',') + '\n';
    });

    // Create download link
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `proving-ground-results-${new Date().toISOString().slice(0, 10)}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);

    showAlert('success', 'CSV exported successfully');
}

// ==================== Batch Execution Functions ====================

function loadBatchExecutionData() {
    // Populate batch dropdown
    const batchSelect = document.getElementById('batch-exec-select');
    batchSelect.innerHTML = '<option value="">-- Select an analysis batch --</option>';

    batches.forEach(batch => {
        const option = document.createElement('option');
        option.value = batch.id;
        option.textContent = `${batch.name} (${batch.dataset_name})`;
        batchSelect.appendChild(option);
    });

    // Load saved batch if available
    if (batchExecBatch) {
        batchSelect.value = batchExecBatch.id;
        handleBatchExecSelection(batchExecBatch.id);
    }
}

async function handleBatchExecSelection(batchId) {
    if (!batchId) {
        document.getElementById('batch-exec-info').style.display = 'none';
        batchExecBatch = null;
        return;
    }

    // Find the batch
    const batch = batches.find(b => b.id === batchId);
    if (!batch) {
        showAlert('danger', 'Batch not found');
        return;
    }

    batchExecBatch = batch;

    // Display batch info
    document.getElementById('batch-exec-dataset-name').textContent = batch.dataset_name;
    document.getElementById('batch-exec-status').innerHTML =
        `<span class="badge bg-${getStatusBadgeClass(batch.status)}">${batch.status}</span>`;

    // Check if prompt is configured
    try {
        const response = await fetch(`/api/analysis/prompts/${batchId}`);
        const data = await response.json();

        const hasPrompt = data.success && data.config && data.config.prompt_template;
        const promptStatus = document.getElementById('batch-exec-prompt-status');

        if (hasPrompt) {
            promptStatus.textContent = 'Yes';
            promptStatus.className = 'badge bg-success';
            document.getElementById('batch-exec-run-btn').disabled = false;
        } else {
            promptStatus.textContent = 'No';
            promptStatus.className = 'badge bg-danger';
            document.getElementById('batch-exec-run-btn').disabled = true;
            showAlert('warning', 'No prompt configured for this batch. Please configure in Prompt Builder first.');
        }
    } catch (error) {
        console.error('Error checking prompt config:', error);
        document.getElementById('batch-exec-prompt-status').textContent = 'Unknown';
        document.getElementById('batch-exec-prompt-status').className = 'badge bg-secondary';
        document.getElementById('batch-exec-run-btn').disabled = true;
    }

    document.getElementById('batch-exec-info').style.display = 'block';
}

async function executeBatch() {
    if (!batchExecBatch) {
        showAlert('warning', 'Please select a batch first');
        return;
    }

    // Hide previous results/errors
    document.getElementById('batch-exec-results-section').style.display = 'none';
    document.getElementById('batch-exec-error-section').style.display = 'none';

    // Show progress section
    document.getElementById('batch-exec-progress-section').style.display = 'block';
    document.getElementById('batch-exec-current').textContent = '0';
    document.getElementById('batch-exec-total').textContent = '...';
    document.getElementById('batch-exec-eta').textContent = 'Calculating...';
    document.getElementById('batch-exec-progress-bar').style.width = '0%';
    document.getElementById('batch-exec-progress-bar').textContent = '0%';
    document.getElementById('batch-exec-status-message').textContent = 'Starting batch execution...';

    // Disable run button
    document.getElementById('batch-exec-run-btn').disabled = true;

    try {
        // Start batch execution
        const response = await fetch('/api/analysis/execute-batch', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ batch_id: batchExecBatch.id })
        });

        const data = await response.json();

        if (data.success) {
            // Start polling for progress
            const executionId = data.execution_id;
            pollBatchProgress(executionId);
        } else {
            // Show error
            document.getElementById('batch-exec-progress-section').style.display = 'none';
            document.getElementById('batch-exec-error-section').style.display = 'block';
            document.getElementById('batch-exec-error-message').textContent = data.error;
            document.getElementById('batch-exec-run-btn').disabled = false;
        }
    } catch (error) {
        console.error('Error starting batch execution:', error);
        document.getElementById('batch-exec-progress-section').style.display = 'none';
        document.getElementById('batch-exec-error-section').style.display = 'block';
        document.getElementById('batch-exec-error-message').textContent = error.message;
        document.getElementById('batch-exec-run-btn').disabled = false;
    }
}

function pollBatchProgress(executionId) {
    // Clear any existing interval
    if (batchExecInterval) {
        clearInterval(batchExecInterval);
    }

    const startTime = Date.now();

    batchExecInterval = setInterval(async () => {
        try {
            const response = await fetch(`/api/analysis/batch-progress/${executionId}`);
            const data = await response.json();

            if (data.success) {
                const progress = data.progress;

                // Update progress bar
                const percentage = Math.round((progress.current / progress.total) * 100);
                document.getElementById('batch-exec-current').textContent = progress.current;
                document.getElementById('batch-exec-total').textContent = progress.total;
                document.getElementById('batch-exec-progress-bar').style.width = `${percentage}%`;
                document.getElementById('batch-exec-progress-bar').textContent = `${percentage}%`;

                // Calculate ETA
                if (progress.current > 0) {
                    const elapsed = (Date.now() - startTime) / 1000; // seconds
                    const rate = progress.current / elapsed;
                    const remaining = progress.total - progress.current;
                    const etaSeconds = Math.round(remaining / rate);
                    document.getElementById('batch-exec-eta').textContent = formatDuration(etaSeconds);
                }

                // Update status message
                document.getElementById('batch-exec-status-message').textContent = progress.status || 'Processing...';

                // Check if complete
                if (progress.complete) {
                    clearInterval(batchExecInterval);
                    batchExecInterval = null;

                    // Hide progress, show results
                    document.getElementById('batch-exec-progress-section').style.display = 'none';

                    if (progress.success) {
                        displayBatchResults(progress);
                    } else {
                        document.getElementById('batch-exec-error-section').style.display = 'block';
                        document.getElementById('batch-exec-error-message').textContent = progress.error || 'Unknown error';
                        document.getElementById('batch-exec-run-btn').disabled = false;
                    }
                }
            } else {
                // Error getting progress
                clearInterval(batchExecInterval);
                batchExecInterval = null;
                document.getElementById('batch-exec-progress-section').style.display = 'none';
                document.getElementById('batch-exec-error-section').style.display = 'block';
                document.getElementById('batch-exec-error-message').textContent = data.error || 'Failed to get progress';
                document.getElementById('batch-exec-run-btn').disabled = false;
            }
        } catch (error) {
            console.error('Error polling progress:', error);
            clearInterval(batchExecInterval);
            batchExecInterval = null;
            document.getElementById('batch-exec-progress-section').style.display = 'none';
            document.getElementById('batch-exec-error-section').style.display = 'block';
            document.getElementById('batch-exec-error-message').textContent = 'Failed to get progress: ' + error.message;
            document.getElementById('batch-exec-run-btn').disabled = false;
        }
    }, 2000); // Poll every 2 seconds
}

function displayBatchResults(progress) {
    document.getElementById('batch-exec-results-section').style.display = 'block';

    // Update statistics
    document.getElementById('batch-exec-total-processed').textContent = progress.total;
    document.getElementById('batch-exec-success-count').textContent = progress.success_count || 0;
    document.getElementById('batch-exec-error-count').textContent = progress.error_count || 0;
    document.getElementById('batch-exec-duration').textContent = formatDuration(progress.duration || 0);

    // Set CSV filename
    document.getElementById('batch-exec-csv-filename').textContent = progress.csv_filename || 'batch_results.csv';

    // Store execution ID for download
    document.getElementById('batch-exec-download-csv').dataset.executionId = progress.execution_id;

    // Re-enable run button
    document.getElementById('batch-exec-run-btn').disabled = false;

    showAlert('success', 'Batch execution completed successfully!');
}

function formatDuration(seconds) {
    if (seconds < 60) {
        return `${seconds}s`;
    } else if (seconds < 3600) {
        const mins = Math.floor(seconds / 60);
        const secs = seconds % 60;
        return `${mins}m ${secs}s`;
    } else {
        const hours = Math.floor(seconds / 3600);
        const mins = Math.floor((seconds % 3600) / 60);
        return `${hours}h ${mins}m`;
    }
}

async function downloadBatchCSV() {
    const executionId = document.getElementById('batch-exec-download-csv').dataset.executionId;

    if (!executionId) {
        showAlert('warning', 'No execution ID found');
        return;
    }

    try {
        const response = await fetch(`/api/analysis/download-batch-csv/${executionId}`);

        if (response.ok) {
            const blob = await response.blob();
            const filename = document.getElementById('batch-exec-csv-filename').textContent || 'batch_results.csv';

            // Create download link
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);

            showAlert('success', 'CSV downloaded successfully');
        } else {
            const data = await response.json();
            showAlert('danger', 'Failed to download CSV: ' + (data.error || 'Unknown error'));
        }
    } catch (error) {
        console.error('Error downloading CSV:', error);
        showAlert('danger', 'Error downloading CSV: ' + error.message);
    }
}
