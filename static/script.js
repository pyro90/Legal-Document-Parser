// Get DOM elements
const uploadForm = document.getElementById('uploadForm');
const fileInput = document.getElementById('fileInput');
const fileName = document.getElementById('fileName');
const analyzeBtn = document.getElementById('analyzeBtn');
const loadingSpinner = document.getElementById('loadingSpinner');
const errorMessage = document.getElementById('errorMessage');
const resultsSection = document.getElementById('results');
const clausesContainer = document.getElementById('clausesContainer');
const resultFileName = document.getElementById('resultFileName');
const totalClauses = document.getElementById('totalClauses');

// Update file label when file is selected
fileInput.addEventListener('change', (e) => {
    if (e.target.files.length > 0) {
        fileName.textContent = e.target.files[0].name;
    } else {
        fileName.textContent = 'Choose PDF file...';
    }
});

// Handle form submission
uploadForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    // Validate file is selected
    if (!fileInput.files[0]) {
        showError('Please select a PDF file first');
        return;
    }
    
    // Prepare form data
    const formData = new FormData();
    formData.append('file', fileInput.files[0]);
    
    // Show loading, hide previous results/errors
    showLoading();
    hideError();
    hideResults();
    
    try {
        // Send file to backend
        const response = await fetch('/api/upload', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Upload failed');
        }
        
        // Display results
        displayResults(data);
        
    } catch (error) {
        showError(error.message || 'An error occurred while processing the file');
    } finally {
        hideLoading();
    }
});

function showLoading() {
    loadingSpinner.style.display = 'block';
    analyzeBtn.disabled = true;
}

function hideLoading() {
    loadingSpinner.style.display = 'none';
    analyzeBtn.disabled = false;
}

function showError(message) {
    errorMessage.textContent = message;
    errorMessage.style.display = 'block';
}

function hideError() {
    errorMessage.style.display = 'none';
}

function hideResults() {
    resultsSection.style.display = 'none';
}

function displayResults(data) {
    // Update summary
    resultFileName.textContent = data.filename;
    totalClauses.textContent = data.total_clauses_found;
    
    // Clear previous clauses
    clausesContainer.innerHTML = '';
    
    // Check if any clauses were found
    if (data.total_clauses_found === 0) {
        clausesContainer.innerHTML = '<p style="text-align: center; color: #718096; padding: 40px;">No standard contract clauses were identified in this document.</p>';
    } else {
        // Display each clause category
        for (const [clauseType, sentences] of Object.entries(data.clauses)) {
            const clauseDiv = createClauseElement(clauseType, sentences);
            clausesContainer.appendChild(clauseDiv);
        }
    }
    
    // Show results section
    resultsSection.style.display = 'block';
    
    // Smooth scroll to results
    resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function createClauseElement(clauseType, sentences) {
    // Create main container
    const container = document.createElement('div');
    container.className = 'clause-category';
    
    // Create header
    const header = document.createElement('div');
    header.className = 'clause-header';
    
    const title = document.createElement('div');
    title.className = 'clause-title';
    title.textContent = clauseType.replace(/_/g, ' ');
    
    const count = document.createElement('div');
    count.className = 'clause-count';
    count.textContent = `${sentences.length} instance${sentences.length > 1 ? 's' : ''}`;
    
    header.appendChild(title);
    header.appendChild(count);
    container.appendChild(header);
    
    // Create clause items
    sentences.forEach(sentence => {
        const item = document.createElement('div');
        item.className = 'clause-item';
        item.textContent = sentence;
        container.appendChild(item);
    });
    
    return container;
}