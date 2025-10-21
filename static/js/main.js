// Clinical Genius - CRM Analytics Prompt Execution Application

// Global state
let currentDataset = null;
let datasets = [];
let batches = [];
let currentBatch = null;
let datasetFields = [];
let modalDatasetFields = []; // Fields for the modal
let modalSelectedFields = []; // Fields selected in the modal
let selectedFields = []; // Fields selected in the Datasets tab
let datasetConfigs = []; // All dataset configurations
let datasetConfig = null; // Configured dataset from Datasets tab
let currentEditingConfigId = null; // ID of config being edited
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

    // Load dataset configurations
    loadDatasetConfigurations();

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

    // Datasets Tab - Create new dataset
    document.getElementById('create-dataset-btn').addEventListener('click', function() {
        showDatasetConfigModal();
    });

    // Dataset Modal - CRM Dataset selection
    document.getElementById('modal-crm-dataset-select').addEventListener('change', function() {
        handleModalDatasetSelection(this.value);
    });

    // Dataset Modal - Field search
    document.getElementById('modal-field-search').addEventListener('input', function() {
        filterModalFieldList(this.value);
    });

    // Dataset Modal - Select all fields
    document.getElementById('modal-select-all-fields-btn').addEventListener('click', function() {
        toggleModalAllFields(true);
    });

    // Dataset Modal - Deselect all fields
    document.getElementById('modal-deselect-all-fields-btn').addEventListener('click', function() {
        toggleModalAllFields(false);
    });

    // Dataset Modal - Test filter
    document.getElementById('modal-test-filter-btn').addEventListener('click', function() {
        testModalSaqlFilter();
    });

    // Dataset Modal - Save button
    document.getElementById('save-dataset-modal-btn').addEventListener('click', function() {
        saveDatasetConfigModal();
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

    // Settings - Provider change
    document.getElementById('settings-provider').addEventListener('change', function() {
        updateSettingsProviderUI();
    });

    // Settings - Save settings
    document.getElementById('save-settings-btn').addEventListener('click', function() {
        saveSettings();
    });

    // Settings - Test connection
    document.getElementById('test-connection-btn').addEventListener('click', function() {
        testConnection();
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
    } else if (tabName === 'settings') {
        loadSettings();
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
        } else {
            console.error('Failed to load datasets:', data.error);
            showAlert('danger', 'Failed to load datasets: ' + data.error);
        }
    } catch (error) {
        console.error('Error loading datasets:', error);
        showAlert('danger', 'Error loading datasets: ' + error.message);
    }
}


// ========================================
// Dataset Configuration Functions
// ========================================

async function loadDatasetConfigurations() {
    document.getElementById('datasets-loading').style.display = 'block';
    document.getElementById('datasets-list-container').style.display = 'none';
    document.getElementById('no-datasets').style.display = 'none';

    try {
        const response = await fetch('/api/dataset-configs');
        const data = await response.json();

        if (data.success) {
            datasetConfigs = data.configs;
            displayDatasetConfigs();
        } else {
            console.error('Failed to load dataset configs:', data.error);
            document.getElementById('datasets-loading').style.display = 'none';
            showAlert('danger', 'Failed to load dataset configurations: ' + data.error);
        }
    } catch (error) {
        console.error('Error loading dataset configs:', error);
        document.getElementById('datasets-loading').style.display = 'none';
        showAlert('danger', 'Error loading dataset configurations: ' + error.message);
    }
}

function displayDatasetConfigs() {
    const tbody = document.getElementById('datasets-list-tbody');
    tbody.innerHTML = '';

    document.getElementById('datasets-loading').style.display = 'none';

    if (datasetConfigs.length === 0) {
        document.getElementById('no-datasets').style.display = 'block';
        return;
    }

    document.getElementById('datasets-list-container').style.display = 'block';

    datasetConfigs.forEach(config => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${config.name}</td>
            <td>${config.crm_dataset_name || config.crm_dataset_id}</td>
            <td>${config.record_id_field}</td>
            <td>${config.selected_fields.length} field(s)</td>
            <td>${config.saql_filter ? '<span class="badge bg-info">Applied</span>' : '<span class="badge bg-secondary">None</span>'}</td>
            <td>
                <button class="btn btn-sm btn-primary me-1" onclick="editDatasetConfig('${config.id}')">
                    <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" fill="currentColor" viewBox="0 0 16 16">
                        <path d="M12.146.146a.5.5 0 0 1 .708 0l3 3a.5.5 0 0 1 0 .708l-10 10a.5.5 0 0 1-.168.11l-5 2a.5.5 0 0 1-.65-.65l2-5a.5.5 0 0 1 .11-.168zM11.207 2.5 13.5 4.793 14.793 3.5 12.5 1.207zm1.586 3L10.5 3.207 4 9.707V10h.5a.5.5 0 0 1 .5.5v.5h.5a.5.5 0 0 1 .5.5v.5h.293zm-9.761 5.175-.106.106-1.528 3.821 3.821-1.528.106-.106A.5.5 0 0 1 5 12.5V12h-.5a.5.5 0 0 1-.5-.5V11h-.5a.5.5 0 0 1-.468-.325"/>
                    </svg>
                    Edit
                </button>
                <button class="btn btn-sm btn-danger" onclick="deleteDatasetConfig('${config.id}')">
                    <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" fill="currentColor" viewBox="0 0 16 16">
                        <path d="M5.5 5.5A.5.5 0 0 1 6 6v6a.5.5 0 0 1-1 0V6a.5.5 0 0 1 .5-.5m2.5 0a.5.5 0 0 1 .5.5v6a.5.5 0 0 1-1 0V6a.5.5 0 0 1 .5-.5m3 .5a.5.5 0 0 0-1 0v6a.5.5 0 0 0 1 0z"/>
                        <path d="M14.5 3a1 1 0 0 1-1 1H13v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V4h-.5a1 1 0 0 1-1-1V2a1 1 0 0 1 1-1H6a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1h3.5a1 1 0 0 1 1 1zM4.118 4 4 4.059V13a1 1 0 0 0 1 1h6a1 1 0 0 0 1-1V4.059L11.882 4zM2.5 3h11V2h-11z"/>
                    </svg>
                    Delete
                </button>
            </td>
        `;
        tbody.appendChild(row);
    });
}

function showDatasetConfigModal(configId = null) {
    currentEditingConfigId = configId;
    modalSelectedFields = [];
    modalDatasetFields = [];

    const modal = new bootstrap.Modal(document.getElementById('datasetConfigModal'));
    const title = document.getElementById('dataset-modal-title');

    if (configId) {
        title.textContent = 'Edit Dataset Configuration';
        loadConfigIntoModal(configId);
    } else {
        title.textContent = 'New Dataset Configuration';
        clearModalForm();
    }

    // Populate CRM dataset dropdown
    populateModalDatasetDropdown();

    modal.show();
}

function populateModalDatasetDropdown() {
    const select = document.getElementById('modal-crm-dataset-select');
    select.innerHTML = '<option value="">-- Choose a dataset --</option>';

    const sortedDatasets = [...datasets].sort((a, b) => {
        const aLabel = a.label || a.name || a.id;
        const bLabel = b.label || b.name || b.id;
        return aLabel.localeCompare(bLabel);
    });

    sortedDatasets.forEach(ds => {
        const option = document.createElement('option');
        option.value = ds.id;
        option.textContent = ds.label || ds.name || ds.id;
        select.appendChild(option);
    });
}

function clearModalForm() {
    document.getElementById('modal-dataset-id').value = '';
    document.getElementById('modal-dataset-name').value = '';
    document.getElementById('modal-crm-dataset-select').value = '';
    document.getElementById('modal-record-id-field').innerHTML = '<option value="">-- Select dataset first --</option>';
    document.getElementById('modal-saql-filter').value = '';
    document.getElementById('modal-filter-test-result').style.display = 'none';
    document.getElementById('modal-field-selection-list').innerHTML = '<p class="text-muted small">Select a dataset to see available fields</p>';
    modalSelectedFields = [];
    modalDatasetFields = [];
}

async function loadConfigIntoModal(configId) {
    try {
        const response = await fetch(`/api/dataset-configs/${configId}`);
        const data = await response.json();

        if (data.success) {
            const config = data.config;
            document.getElementById('modal-dataset-id').value = config.id;
            document.getElementById('modal-dataset-name').value = config.name;
            document.getElementById('modal-crm-dataset-select').value = config.crm_dataset_id;
            document.getElementById('modal-saql-filter').value = config.saql_filter || '';
            modalSelectedFields = config.selected_fields;

            // Load fields for the selected dataset
            await handleModalDatasetSelection(config.crm_dataset_id);
            document.getElementById('modal-record-id-field').value = config.record_id_field;
        }
    } catch (error) {
        console.error('Error loading config:', error);
        showAlert('danger', 'Error loading configuration: ' + error.message);
    }
}

async function handleModalDatasetSelection(datasetId) {
    if (!datasetId) {
        document.getElementById('modal-record-id-field').innerHTML = '<option value="">-- Select dataset first --</option>';
        document.getElementById('modal-field-selection-list').innerHTML = '<p class="text-muted small">Select a dataset to see available fields</p>';
        modalDatasetFields = [];
        return;
    }

    try {
        const response = await fetch(`/api/crm-analytics/datasets/${datasetId}/fields`);
        const data = await response.json();

        if (data.success) {
            modalDatasetFields = data.fields;
            populateModalRecordIdFieldDropdown();
            populateModalFieldSelectionList();
        } else {
            showAlert('danger', 'Failed to load dataset fields: ' + data.error);
        }
    } catch (error) {
        console.error('Error loading dataset fields:', error);
        showAlert('danger', 'Error loading dataset fields: ' + error.message);
    }
}

function populateModalRecordIdFieldDropdown() {
    const select = document.getElementById('modal-record-id-field');
    select.innerHTML = '<option value="">-- Select a field --</option>';

    const sortedFields = [...modalDatasetFields].sort((a, b) => a.name.localeCompare(b.name));

    sortedFields.forEach(field => {
        const option = document.createElement('option');
        option.value = field.name;
        option.textContent = `${field.label || field.name} (${field.name})`;
        select.appendChild(option);
    });
}

function populateModalFieldSelectionList() {
    const container = document.getElementById('modal-field-selection-list');
    container.innerHTML = '';

    const sortedFields = [...modalDatasetFields].sort((a, b) => a.name.localeCompare(b.name));

    sortedFields.forEach(field => {
        const div = document.createElement('div');
        div.className = 'form-check';
        div.dataset.fieldName = field.name;

        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.className = 'form-check-input modal-field-checkbox';
        checkbox.id = `modal-field-${field.name}`;
        checkbox.value = field.name;
        checkbox.checked = modalSelectedFields.includes(field.name);

        checkbox.addEventListener('change', function() {
            if (this.checked) {
                if (!modalSelectedFields.includes(field.name)) {
                    modalSelectedFields.push(field.name);
                }
            } else {
                modalSelectedFields = modalSelectedFields.filter(f => f !== field.name);
            }
        });

        const label = document.createElement('label');
        label.className = 'form-check-label';
        label.htmlFor = `modal-field-${field.name}`;
        label.textContent = `${field.label || field.name} (${field.name}) - ${field.type}`;

        div.appendChild(checkbox);
        div.appendChild(label);
        container.appendChild(div);
    });
}

function filterModalFieldList(searchTerm) {
    const container = document.getElementById('modal-field-selection-list');
    const fieldDivs = container.querySelectorAll('.form-check');

    const lowerSearch = searchTerm.toLowerCase();

    fieldDivs.forEach(div => {
        const label = div.querySelector('label').textContent.toLowerCase();
        div.style.display = label.includes(lowerSearch) ? 'block' : 'none';
    });
}

function toggleModalAllFields(select) {
    const checkboxes = document.querySelectorAll('.modal-field-checkbox');
    checkboxes.forEach(checkbox => {
        if (checkbox.closest('.form-check').style.display !== 'none') {
            checkbox.checked = select;
            const fieldName = checkbox.value;
            if (select) {
                if (!modalSelectedFields.includes(fieldName)) {
                    modalSelectedFields.push(fieldName);
                }
            } else {
                modalSelectedFields = modalSelectedFields.filter(f => f !== fieldName);
            }
        }
    });
}

async function testModalSaqlFilter() {
    const datasetId = document.getElementById('modal-crm-dataset-select').value;
    const saqlFilter = document.getElementById('modal-saql-filter').value.trim();
    const resultDiv = document.getElementById('modal-filter-test-result');

    if (!datasetId) {
        resultDiv.className = 'alert alert-warning mt-2';
        resultDiv.textContent = 'Please select a dataset first';
        resultDiv.style.display = 'block';
        return;
    }

    if (!saqlFilter) {
        resultDiv.className = 'alert alert-warning mt-2';
        resultDiv.textContent = 'Please enter a filter statement to test';
        resultDiv.style.display = 'block';
        return;
    }

    resultDiv.className = 'alert alert-info mt-2';
    resultDiv.textContent = 'Testing filter...';
    resultDiv.style.display = 'block';

    try {
        const response = await fetch('/api/dataset-config/test-filter', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ dataset_id: datasetId, saql_filter: saqlFilter })
        });

        const data = await response.json();

        if (data.success) {
            resultDiv.className = 'alert alert-success mt-2';
            resultDiv.innerHTML = `<strong>✓ Filter is valid!</strong><br><small>Query executed successfully and returned ${data.record_count} record(s).</small>`;
        } else {
            resultDiv.className = 'alert alert-danger mt-2';
            resultDiv.innerHTML = `<strong>✗ Filter syntax error:</strong><br><small>${data.error}</small>`;
        }
    } catch (error) {
        console.error('Error testing filter:', error);
        resultDiv.className = 'alert alert-danger mt-2';
        resultDiv.innerHTML = `<strong>✗ Error testing filter:</strong><br><small>${error.message}</small>`;
    }
}

async function saveDatasetConfigModal() {
    const name = document.getElementById('modal-dataset-name').value.trim();
    const crmDatasetId = document.getElementById('modal-crm-dataset-select').value;
    const recordIdField = document.getElementById('modal-record-id-field').value;
    const saqlFilter = document.getElementById('modal-saql-filter').value.trim();

    if (!name) {
        showAlert('danger', 'Please enter a dataset name');
        return;
    }

    if (!crmDatasetId) {
        showAlert('danger', 'Please select a CRM Analytics dataset');
        return;
    }

    if (!recordIdField) {
        showAlert('danger', 'Please select a Record ID field');
        return;
    }

    if (modalSelectedFields.length === 0) {
        showAlert('danger', 'Please select at least one field');
        return;
    }

    const dataset = datasets.find(ds => ds.id === crmDatasetId);
    const crmDatasetName = dataset ? dataset.label : crmDatasetId;

    const config = {
        name: name,
        crm_dataset_id: crmDatasetId,
        crm_dataset_name: crmDatasetName,
        record_id_field: recordIdField,
        saql_filter: saqlFilter,
        selected_fields: modalSelectedFields
    };

    if (currentEditingConfigId) {
        config.id = currentEditingConfigId;
    }

    try {
        const response = await fetch('/api/dataset-configs', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(config)
        });

        const data = await response.json();

        if (data.success) {
            showAlert('success', 'Dataset configuration saved successfully!');
            bootstrap.Modal.getInstance(document.getElementById('datasetConfigModal')).hide();
            loadDatasetConfigurations();
        } else {
            showAlert('danger', 'Failed to save dataset configuration: ' + data.error);
        }
    } catch (error) {
        console.error('Error saving dataset configuration:', error);
        showAlert('danger', 'Error saving dataset configuration: ' + error.message);
    }
}

function editDatasetConfig(configId) {
    showDatasetConfigModal(configId);
}

async function deleteDatasetConfig(configId) {
    if (!confirm('Are you sure you want to delete this dataset configuration?')) {
        return;
    }

    try {
        const response = await fetch(`/api/dataset-configs/${configId}`, {
            method: 'DELETE'
        });

        const data = await response.json();

        if (data.success) {
            showAlert('success', 'Dataset configuration deleted successfully');
            loadDatasetConfigurations();
        } else {
            showAlert('danger', 'Failed to delete dataset configuration: ' + data.error);
        }
    } catch (error) {
        console.error('Error deleting dataset configuration:', error);
        showAlert('danger', 'Error deleting dataset configuration: ' + error.message);
    }
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
    // Populate dataset dropdown with configured datasets
    const select = document.getElementById('analysis-dataset');
    select.innerHTML = '<option value="">-- Choose a configured dataset --</option>';

    if (datasetConfigs.length === 0) {
        select.innerHTML = '<option value="">-- No datasets configured --</option>';
        showAlert('warning', 'Please configure a dataset in the Datasets tab first');
        return;
    }

    datasetConfigs.forEach(config => {
        const option = document.createElement('option');
        option.value = config.id;
        option.textContent = config.name;
        select.appendChild(option);
    });

    const modal = new bootstrap.Modal(document.getElementById('newAnalysisModal'));
    modal.show();
}

async function createNewAnalysis() {
    const name = document.getElementById('analysis-name').value;
    const configId = document.getElementById('analysis-dataset').value;
    const description = document.getElementById('analysis-description').value;

    if (!name || !configId) {
        showAlert('warning', 'Please fill in all required fields');
        return;
    }

    // Find the selected dataset configuration
    const config = datasetConfigs.find(c => c.id === configId);
    if (!config) {
        showAlert('danger', 'Selected dataset configuration not found');
        return;
    }

    try {
        const response = await fetch('/api/analysis/batches', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                name: name,
                dataset_id: config.crm_dataset_id,
                dataset_name: config.crm_dataset_name,
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

    // Gather configuration (model settings are now in global Settings tab)
    const config = {
        batch_id: currentBatch.id,
        prompt_template: document.getElementById('prompt-template').value,
        response_schema: document.getElementById('response-schema').value,
        schema_description: document.getElementById('schema-description').value
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
            // Populate form fields (model config is now in Settings tab)
            document.getElementById('prompt-template').value = data.config.prompt_template || '';
            document.getElementById('response-schema').value = data.config.response_schema || '';
            document.getElementById('schema-description').value = data.config.schema_description || '';
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

    // Show modal
    const modal = new bootstrap.Modal(document.getElementById('previewPromptModal'));
    modal.show();

    // Reset modal state
    document.getElementById('preview-loading').style.display = 'block';
    document.getElementById('preview-content').style.display = 'none';
    document.getElementById('preview-error').style.display = 'none';

    try {
        // Model config is now global, backend will use settings.json
        const response = await fetch('/api/analysis/preview-prompt-execute', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                batch_id: currentBatch.id,
                prompt_template: promptTemplate,
                response_schema: responseSchema
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

// handleProviderChange removed - model config now in Settings tab

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

    // Extract all unique keys from responses
    const allKeys = new Set();
    provingResults.forEach(result => {
        if (result.response && typeof result.response === 'object') {
            Object.keys(result.response).forEach(key => allKeys.add(key));
        }
    });

    const columns = ['claim_name', ...Array.from(allKeys)];

    // Build CSV content (structured format - one record per row)
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

// ============================================================================
// Settings Functions
// ============================================================================

async function loadSettings() {
    try {
        const response = await fetch('/api/settings');
        if (response.ok) {
            const data = await response.json();
            if (data.success) {
                const settings = data.settings;

                // Populate form fields
                document.getElementById('settings-provider').value = settings.provider || 'lm_studio';
                document.getElementById('settings-endpoint').value = settings.endpoint || 'http://localhost:1234';
                document.getElementById('settings-model').value = settings.model || 'gpt-4o-mini';
                document.getElementById('settings-temperature').value = settings.temperature || 0.7;
                document.getElementById('settings-max-tokens').value = settings.max_tokens || 4000;
                document.getElementById('settings-timeout').value = settings.timeout || 60;

                // Show/hide endpoint and API key fields based on provider
                updateSettingsProviderUI();
            }
        }
    } catch (error) {
        console.error('Error loading settings:', error);
    }
}

function updateSettingsProviderUI() {
    const provider = document.getElementById('settings-provider').value;
    const endpointGroup = document.getElementById('settings-endpoint-group');

    // Show endpoint field only for LM Studio
    if (provider === 'lm_studio') {
        endpointGroup.style.display = 'block';
    } else {
        endpointGroup.style.display = 'none';
    }
}

async function saveSettings() {
    const settings = {
        provider: document.getElementById('settings-provider').value,
        endpoint: document.getElementById('settings-endpoint').value,
        model: document.getElementById('settings-model').value,
        temperature: parseFloat(document.getElementById('settings-temperature').value),
        max_tokens: parseInt(document.getElementById('settings-max-tokens').value),
        timeout: parseInt(document.getElementById('settings-timeout').value)
    };

    try {
        const response = await fetch('/api/settings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(settings)
        });

        const data = await response.json();

        if (data.success) {
            showAlert('success', 'Settings saved successfully');
            document.getElementById('settings-status').style.display = 'none';
        } else {
            showAlert('danger', 'Failed to save settings: ' + data.error);
        }
    } catch (error) {
        console.error('Error saving settings:', error);
        showAlert('danger', 'Error saving settings: ' + error.message);
    }
}

async function testConnection() {
    const statusDiv = document.getElementById('settings-status');
    statusDiv.style.display = 'block';
    statusDiv.className = 'mt-3 alert alert-info';
    statusDiv.innerHTML = '<div class="spinner-border spinner-border-sm me-2"></div>Testing connection...';

    try {
        const response = await fetch('/api/test-connection', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });

        const data = await response.json();

        if (data.success) {
            statusDiv.className = 'mt-3 alert alert-success';
            statusDiv.innerHTML = `<strong>Success!</strong> ${data.message}<br><small>Response: ${data.response}</small>`;
        } else {
            statusDiv.className = 'mt-3 alert alert-danger';
            statusDiv.innerHTML = `<strong>Failed!</strong> ${data.message}`;
        }
    } catch (error) {
        console.error('Error testing connection:', error);
        statusDiv.className = 'mt-3 alert alert-danger';
        statusDiv.innerHTML = `<strong>Error!</strong> ${error.message}`;
    }
}
