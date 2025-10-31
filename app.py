from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import pdfplumber
import spacy
import re
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
CORS(app)

# Configuration
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Load spaCy model for NLP
nlp = spacy.load('en_core_web_sm')

# Ensure upload folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_text_from_pdf(pdf_path):
    """Extract text from PDF file"""
    text = ""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text += page.extract_text() or ""
    except Exception as e:
        print(f"Error extracting PDF: {e}")
    return text

def identify_clauses(text):
    """
    Identify and extract key contract clauses using pattern matching.
    Returns a dictionary of clause types and their content.
    """
    clauses = {
        'governing_law': [],
        'termination': [],
        'confidentiality': [],
        'indemnification': [],
        'liability': [],
        'payment': [],
        'dispute_resolution': [],
        'force_majeure': [],
        'assignment': [],
        'warranties': []
    }
    
    # Split text into sentences for better processing
    doc = nlp(text)
    sentences = [sent.text.strip() for sent in doc.sents]
    
    # Define patterns for each clause type
    patterns = {
        'governing_law': [
            r'governing law', r'governed by', r'laws of', r'jurisdiction',
            r'applicable law', r'legal venue'
        ],
        'termination': [
            r'termination', r'terminate', r'term of agreement', r'notice period',
            r'may be terminated', r'grounds for termination'
        ],
        'confidentiality': [
            r'confidential', r'non-disclosure', r'proprietary information',
            r'confidentiality obligation', r'trade secret'
        ],
        'indemnification': [
            r'indemnif', r'hold harmless', r'defend.*against', r'indemnity'
        ],
        'liability': [
            r'liability', r'liable for', r'limitation of liability',
            r'consequential damages', r'damages.*limited'
        ],
        'payment': [
            r'payment', r'compensation', r'fee', r'invoice', r'pay.*within',
            r'pricing', r'cost'
        ],
        'dispute_resolution': [
            r'arbitration', r'mediation', r'dispute resolution', r'litigation',
            r'settlement of disputes'
        ],
        'force_majeure': [
            r'force majeure', r'act of god', r'beyond.*control',
            r'unforeseeable circumstances'
        ],
        'assignment': [
            r'assignment', r'assign', r'transfer.*rights', r'successor'
        ],
        'warranties': [
            r'warrant', r'representation', r'warrants that', r'represents that',
            r'warranty'
        ]
    }
    
    # Search for patterns in sentences
    for sentence in sentences:
        sentence_lower = sentence.lower()
        for clause_type, pattern_list in patterns.items():
            for pattern in pattern_list:
                if re.search(pattern, sentence_lower):
                    # Avoid duplicates
                    if sentence not in clauses[clause_type]:
                        clauses[clause_type].append(sentence)
                    break  # Move to next sentence once matched
    
    # Filter out empty clause types
    clauses = {k: v for k, v in clauses.items() if v}
    
    return clauses

@app.route('/')
def index():
    """Serve the main page"""
    return render_template('index.html')

@app.route('/api/upload', methods=['POST'])
def upload_file():
    """Handle PDF upload and process it"""
    
    # Check if file was uploaded
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    
    # Check if filename is empty
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    # Validate file type
    if not allowed_file(file.filename):
        return jsonify({'error': 'Only PDF files are allowed'}), 400
    
    try:
        # Save file securely
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # Extract text from PDF
        text = extract_text_from_pdf(filepath)
        
        if not text:
            return jsonify({'error': 'Could not extract text from PDF'}), 400
        
        # Identify clauses
        clauses = identify_clauses(text)
        
        # Clean up - delete uploaded file
        os.remove(filepath)
        
        # Return results
        return jsonify({
            'success': True,
            'filename': filename,
            'clauses': clauses,
            'total_clauses_found': sum(len(v) for v in clauses.values())
        })
    
    except Exception as e:
        # Clean up on error
        if os.path.exists(filepath):
            os.remove(filepath)
        return jsonify({'error': f'Processing error: {str(e)}'}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Simple health check endpoint"""
    return jsonify({'status': 'healthy'})

if __name__ == '__main__':
    app.run(debug=True, port=5000)