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

def generate_overview(text, clauses):
    """
    Generate an AI-style overview of the contract.
    Analyzes the document to extract key information.
    """
    doc = nlp(text)
    
    overview = {
        'summary': '',
        'parties': [],
        'key_points': [],
        'potential_concerns': []
    }
    
    # Extract potential party names (organizations and people)
    parties = set()
    for ent in doc.ents:
        if ent.label_ in ['ORG', 'PERSON'] and len(ent.text) > 2:
            # Filter out common words that might be misidentified
            if not ent.text.lower() in ['agreement', 'contract', 'party', 'section']:
                parties.add(ent.text)
    
    overview['parties'] = list(parties)[:6]  # Limit to 6 parties
    
    # Generate summary based on clause types found
    clause_types = list(clauses.keys())
    if clause_types:
        summary_parts = []
        
        # Determine contract type based on clauses
        if 'confidentiality' in clause_types:
            summary_parts.append("appears to contain confidentiality provisions")
        if 'payment' in clause_types:
            summary_parts.append("includes payment terms")
        if 'termination' in clause_types:
            summary_parts.append("specifies termination conditions")
        if 'indemnification' in clause_types:
            summary_parts.append("contains indemnification clauses")
            
        if summary_parts:
            overview['summary'] = f"This contract {', '.join(summary_parts)}."
        else:
            overview['summary'] = "This document appears to be a legal agreement or contract."
    
    # Extract key points from first few sentences
    sentences = [sent.text.strip() for sent in doc.sents][:10]
    key_sentences = []
    
    keywords = ['shall', 'agree', 'obligation', 'right', 'must', 'require', 'provide', 'responsible']
    for sentence in sentences:
        if any(keyword in sentence.lower() for keyword in keywords) and len(sentence) > 30:
            key_sentences.append(sentence)
            if len(key_sentences) >= 3:
                break
    
    overview['key_points'] = key_sentences
    
    # Identify potential concerns based on clause presence/absence
    concerns = []
    
    # Check for missing important clauses
    important_clauses = ['termination', 'liability', 'dispute_resolution']
    missing = [clause for clause in important_clauses if clause not in clause_types]
    
    if 'termination' not in clause_types:
        concerns.append("No clear termination clause identified - consider reviewing exit terms")
    
    if 'liability' not in clause_types:
        concerns.append("Liability limitations not clearly defined - potential risk exposure")
    
    if 'dispute_resolution' not in clause_types:
        concerns.append("No dispute resolution mechanism specified - litigation may be the only option")
    
    # Check for one-sided indemnification
    if 'indemnification' in clauses:
        indem_text = ' '.join(clauses['indemnification']).lower()
        if 'mutual' not in indem_text and 'both parties' not in indem_text:
            concerns.append("Indemnification may be one-sided - review carefully for balanced obligations")
    
    # Check for broad confidentiality
    if 'confidentiality' in clauses:
        conf_text = ' '.join(clauses['confidentiality']).lower()
        if 'perpetual' in conf_text or 'indefinite' in conf_text:
            concerns.append("Confidentiality obligations may extend indefinitely - consider time limitations")
    
    overview['potential_concerns'] = concerns[:4]  # Limit to 4 concerns
    
    return overview
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
    
    print("Upload request received")  # Debug output
    
    # Check if file was uploaded
    if 'file' not in request.files:
        print("No file in request")  # Debug output
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
        
        if not text or len(text.strip()) < 50:
            return jsonify({'error': 'Could not extract text from PDF. The file may be a scanned image or empty.'}), 400
        
        print(f"Extracted {len(text)} characters from PDF")  # Debug output
        
        # Identify clauses
        clauses = identify_clauses(text)
        
        # Generate overview
        overview = generate_overview(text, clauses)
        
        # Clean up - delete uploaded file
        os.remove(filepath)
        
        # Return results
        return jsonify({
            'success': True,
            'filename': filename,
            'clauses': clauses,
            'overview': overview,
            'total_clauses_found': sum(len(v) for v in clauses.values())
        })
    
    except Exception as e:
        print(f"Error occurred: {str(e)}")  # Debug output
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