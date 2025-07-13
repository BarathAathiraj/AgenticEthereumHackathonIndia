
from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS
import os
import tempfile
import uuid
from datetime import datetime, timedelta
import time
import threading
import logging
from google.cloud import speech
from google.cloud import translate_v2 as translate
from werkzeug.utils import secure_filename
import requests
import json
from keybert import KeyBERT
import re
from dotenv import load_dotenv
from twitter_agent import TwitterAgent  # Import real TwitterAgent

load_dotenv()

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*", "allow_headers": ["Content-Type", "Authorization"]}})

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Configuration
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['UPLOAD_FOLDER'] = 'Uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Google Cloud credentials
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = r'F:\VoiceForAll\gcloud-key.json'

# Initialize Google clients
try:
    speech_client = speech.SpeechClient()
    translate_client = translate.Client()
except Exception as e:
    logger.error(f"Google Cloud initialization failed: {e}")
    speech_client = None
    translate_client = None

# Supported Languages
LANGUAGE_CODES = {
    'en': 'en-US', 'hi': 'hi-IN', 'ta': 'ta-IN', 'te': 'te-IN',
    'ml': 'ml-IN', 'kn': 'kn-IN', 'bn': 'bn-IN', 'gu': 'gu-IN',
    'pa': 'pa-IN', 'mr': 'mr-IN'
}

# Indian States
INDIAN_STATES = [
    'Andhra Pradesh', 'Arunachal Pradesh', 'Assam', 'Bihar', 'Chhattisgarh',
    'Goa', 'Gujarat', 'Haryana', 'Himachal Pradesh', 'Jharkhand', 'Karnataka',
    'Kerala', 'Madhya Pradesh', 'Maharashtra', 'Manipur', 'Meghalaya',
    'Mizoram', 'Nagaland', 'Odisha', 'Punjab', 'Rajasthan', 'Sikkim',
    'Tamil Nadu', 'Telangana', 'Tripura', 'Uttar Pradesh', 'Uttarakhand',
    'West Bengal', 'Andaman and Nicobar Islands', 'Chandigarh', 'Dadra and Nagar Haveli and Daman and Diu',
    'Delhi', 'Jammu and Kashmir', 'Ladakh', 'Lakshadweep', 'Puducherry'
]

# Mock Firebase Utils
class MockFirebaseUtils:
    def __init__(self):
        self.complaints = []
        self.vote_threshold = 2
        self.twitter_posts = 0
        self.twitter_post_limit = 100
        self.month_start = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    def save_complaint(self, complaint):
        complaint['id'] = str(uuid.uuid4())
        self.complaints.append(complaint)
        return {'success': True, 'complaint_id': complaint['id']}

    def get_complaints(self, state_filter='ALL'):
        if state_filter == 'ALL':
            return self.complaints
        return [c for c in self.complaints if c.get('state') == state_filter]

    def get_complaint(self, complaint_id):
        for complaint in self.complaints:
            if complaint['id'] == complaint_id:
                return complaint
        return None

    def update_complaint(self, complaint):
        for i, c in enumerate(self.complaints):
            if c['id'] == complaint['id']:
                self.complaints[i] = complaint
                return True
        return False

    def delete_complaint(self, complaint_id):
        complaint = self.get_complaint(complaint_id)
        if complaint:
            for photo_url in complaint.get('photo_urls', []):
                filename = photo_url.split('/')[-1]
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                try:
                    if os.path.exists(file_path):
                        os.remove(file_path)
                        logger.info(f"Deleted image: {file_path}")
                except Exception as e:
                    logger.error(f"Failed to delete image {file_path}: {e}")
            self.complaints = [c for c in self.complaints if c['id'] != complaint_id]
            return True
        return False

    def get_stats(self):
        total_complaints = len(self.complaints)
        total_votes = sum(c.get('votes', 0) for c in self.complaints)
        posted_complaints = len([c for c in self.complaints if c.get('posted_on_x', False)])
        active_complaints = len([c for c in self.complaints if not c.get('posted_on_x', False)])
        return {
            'total_complaints': total_complaints,
            'total_votes': total_votes,
            'posted_complaints': posted_complaints,
            'active_complaints': active_complaints,
            'twitter_posts_remaining': self.twitter_post_limit - self.twitter_posts
        }

    def can_post_to_twitter(self):
        now = datetime.now()
        if now.month != self.month_start.month or now.year != self.month_start.year:
            self.twitter_posts = 0
            self.month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        return self.twitter_posts < self.twitter_post_limit

    def increment_twitter_post(self):
        self.twitter_posts += 1

# Mock Blockchain Utils
class MockBlockchainUtils:
    def check_connection(self): return True
    def log_complaint(self, complaint): logger.debug(f"Logging complaint {complaint['id']} to blockchain"); return True
    def log_vote(self, complaint_id, anonymous_id): logger.debug(f"Logging vote for {complaint_id} with {anonymous_id}"); return True

# Label to Twitter handle mapping
label_to_twitter = {
    'Women Safety': '@Ministry_WCD',
    'Corruption': '@NHRCIndia',
    'Infrastructure': '@MinOfHUA_India',
    'Health': '@MinOfHFW_INDIA',
    'Electricity': '@MinistryOfEB',
    'Public Safety': '@HMO_India',
    'Karnataka Issue': '@CMOf_Karnataka',
    'General': '@PMof_India'
}

# Initialize TwitterAgent with label_to_twitter
twitter_agent = TwitterAgent(label_to_twitter)
firebase_utils = MockFirebaseUtils()
blockchain_utils = MockBlockchainUtils()

# Gemini AI function
def call_gemini_api(complaint_text):
    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
    headers = {
        'Content-Type': 'application/json',
        'X-goog-api-key': os.getenv('GEMINI_API_KEY')
    }
    payload = {
        'contents': [{
            'parts': [{
                'text': f"Analyze the complaint and generate a JSON object with: a 4-5 word description, the detected Indian state (default to 'India' if not identified), and relevant labels (e.g., 'Women Safety', 'Corruption', 'Infrastructure', 'Health', 'Electricity', 'Public Safety'). Complaint: '{complaint_text}'"
            }]
        }]
    }
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        result = response.json()
        gemini_data = json.loads(result['candidates'][0]['content']['parts'][0]['text'])
        return {
            'description': gemini_data.get('description', 'General issue reported'),
            'state': gemini_data.get('state', 'India'),
            'labels': gemini_data.get('labels', ['General'])
        }
    except (requests.RequestException, KeyError, json.JSONDecodeError) as e:
        logger.error(f"Gemini API error: {e}")
        return {
            'description': 'General issue reported',
            'state': 'India',
            'labels': ['General']
        }

# KeyBERT for hashtag generation
kw_model = KeyBERT(model='all-MiniLM-L6-v2')

def generate_hashtags(text):
    keywords = kw_model.extract_keywords(text, keyphrase_ngram_range=(1, 1), stop_words='english', top_n=7)
    hashtags = [f"#{re.sub(r'[^a-zA-Z0-9]', '', kw[0]).lower()}" for kw, _ in keywords]
    return hashtags[:7] if len(hashtags) >= 5 else hashtags + ['#complaint', '#issue', '#help'][:5-len(hashtags)]

# Define allowed file extensions
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def home():
    try:
        with open('index.html', 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return """
        <!DOCTYPE html>
        <html>
        <head><title>Complaint System</title></head>
        <body><h1>Complaint Submission System</h1><p>Please ensure index.html is present.</p></body>
        </html>
        """, 404

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'services': {
            'firebase': True,
            'blockchain': True,
            'ai': True,
            'twitter': firebase_utils.can_post_to_twitter()
        }
    })

@app.route('/api/transcribe', methods=['POST'])
def transcribe_api_audio():
    if 'audio' not in request.files:
        return jsonify({'success': False, 'error': 'No audio file provided'}), 400

    audio_file = request.files['audio']
    language = request.form.get('language', 'en')

    with tempfile.NamedTemporaryFile(delete=False, suffix='.webm') as temp_file:
        audio_file.save(temp_file.name)
        temp_path = temp_file.name

    try:
        with open(temp_path, 'rb') as f:
            audio_bytes = f.read()
    finally:
        os.remove(temp_path)

    if not speech_client or not translate_client:
        return jsonify({'success': False, 'error': 'Google Cloud clients not initialized'}), 500

    audio = speech.RecognitionAudio(content=audio_bytes)
    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.WEBM_OPUS,
        sample_rate_hertz=48000,
        language_code=LANGUAGE_CODES.get(language, 'en-US'),
        enable_automatic_punctuation=True
    )

    try:
        response = speech_client.recognize(config=config, audio=audio)
    except Exception as e:
        logger.error(f"Speech-to-text failed: {e}")
        return jsonify({'success': False, 'error': 'Speech recognition failed'}), 500

    if not response.results:
        return jsonify({'success': False, 'error': 'No speech detected'}), 400

    transcript = response.results[0].alternatives[0].transcript
    confidence = response.results[0].alternatives[0].confidence
    detected_lang = language
    translated_text = transcript

    try:
        translation = translate_client.translate(transcript, target_language='en')
        translated_text = translation['translatedText']
        detected_lang = translation.get('detectedSourceLanguage', language)
    except Exception as e:
        logger.error(f"Translation failed: {e}")

    return jsonify({
        'success': True,
        'original_text': transcript,
        'english_text': translated_text,
        'detected_language': detected_lang,
        'confidence': confidence
    })

@app.route('/api/submit-complaint', methods=['POST', 'OPTIONS'])
def submit_complaint():
    if request.method == 'OPTIONS':
        return jsonify({'status': 'ok'}), 200, {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type'
        }

    try:
        data = request.form.to_dict()
        complaint_text = data.get('complaint_text', '').strip()
        anonymous_id = data.get('anonymous_id', '')
        state = data.get('state', 'India')
        timestamp = data.get('timestamp', datetime.utcnow().isoformat() + 'Z')

        if not complaint_text or not anonymous_id:
            return jsonify({'success': False, 'error': 'Complaint text and anonymous ID are required'}), 400

        gemini_result = call_gemini_api(complaint_text)
        description = gemini_result['description']
        detected_state = gemini_result['state']
        labels = gemini_result['labels']

        if state == 'Karnataka' or detected_state == 'Karnataka':
            labels.append('Karnataka Issue')

        state = state if state in INDIAN_STATES else detected_state

        hashtags = generate_hashtags(complaint_text)

        photos = request.files.getlist('photos')
        photo_urls = []
        for photo in photos[:2]:
            if photo and allowed_file(photo.filename):
                try:
                    filename = secure_filename(f"photo_{int(time.time())}_{len(photo_urls)}.jpg")
                    photo.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                    photo_urls.append(f"/Uploads/{filename}")
                except Exception as e:
                    logger.error(f"Failed to save photo: {e}")
                    continue

        complaint = {
            'anonymous_id': anonymous_id,
            'complaint_text': complaint_text,
            'description': description,
            'state': state,
            'timestamp': timestamp,
            'votes': 0,
            'photo_urls': photo_urls,
            'hashtags': hashtags,
            'labels': labels,
            'voter_ids': [],
            'posted_on_x': False
        }
        result = firebase_utils.save_complaint(complaint)
        if not result['success']:
            return jsonify({'success': False, 'error': 'Failed to save complaint'}), 500

        blockchain_utils.log_complaint(complaint)
        logger.debug(f"Submitted complaint {result['complaint_id']}")
        return jsonify({'success': True, 'complaint_id': result['complaint_id']}), 200
    except Exception as e:
        logger.error(f"Error in submit_complaint: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': f'Failed to submit complaint: {str(e)}'}), 500

@app.route('/api/get-complaints', methods=['GET', 'OPTIONS'])
def get_complaints():
    if request.method == 'OPTIONS':
        return jsonify({'success': True}), 200, {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type'
        }

    try:
        state_filter = request.args.get('state', 'ALL')
        complaints = firebase_utils.get_complaints(state_filter)
        active_complaints = [c for c in complaints if not c.get('posted_on_x', False)]
        return jsonify({
            'success': True,
            'complaints': active_complaints,
            'count': len(active_complaints)
        })
    except Exception as e:
        logger.error(f"Error getting complaints: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': f'Failed to get complaints: {str(e)}'}), 500

@app.route('/api/vote-complaint', methods=['POST', 'OPTIONS'])
def vote_complaint():
    if request.method == 'OPTIONS':
        return jsonify({'status': 'ok'}), 200, {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type'
        }

    try:
        data = request.get_json()
        complaint_id = data.get('complaint_id')
        anonymous_id = data.get('anonymous_id')

        if not complaint_id or not anonymous_id:
            return jsonify({'success': False, 'error': 'Complaint ID and anonymous ID are required'}), 400

        complaint = firebase_utils.get_complaint(complaint_id)
        if not complaint:
            return jsonify({'success': False, 'error': f'Complaint {complaint_id} not found'}), 404

        if anonymous_id in complaint.get('voter_ids', []):
            return jsonify({'success': False, 'error': 'You have already voted on this complaint'}), 400

        complaint['votes'] += 1
        complaint['voter_ids'].append(anonymous_id)
        blockchain_utils.log_vote(complaint_id, anonymous_id)

        threshold_reached = complaint['votes'] >= firebase_utils.vote_threshold

        if threshold_reached and not complaint.get('posted_on_x', False) and firebase_utils.can_post_to_twitter():
            twitter_handle = label_to_twitter.get(complaint['labels'][0], '@Yuvi564321')
            complaint['labels'].append(f'Mentioned: {twitter_handle}')
            twitter_result = twitter_agent.post_complaint(complaint)
            if twitter_result.get('success'):
                complaint['posted_on_x'] = True
                firebase_utils.update_complaint(complaint)
                firebase_utils.delete_complaint(complaint_id)
                firebase_utils.increment_twitter_post()
                return jsonify({
                    'success': True,
                    'message': 'Vote recorded and complaint posted to Twitter!',
                    'threshold_reached': True,
                    'twitter_posted': True,
                    'votes': complaint['votes']
                })
            else:
                logger.error(f"Twitter posting failed: {twitter_result.get('error')}")
                return jsonify({'success': False, 'error': 'Failed to post to Twitter'}), 500

        firebase_utils.update_complaint(complaint)
        return jsonify({
            'success': True,
            'message': 'Vote recorded successfully',
            'votes': complaint['votes'],
            'threshold_reached': threshold_reached
        })
    except Exception as e:
        logger.error(f"Error voting on complaint {complaint_id}: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': f'Failed to record vote: {str(e)}'}), 500

@app.route('/api/stats', methods=['GET', 'OPTIONS'])
def get_stats():
    if request.method == 'OPTIONS':
        return jsonify({'success': True}), 200, {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type'
        }

    try:
        stats = firebase_utils.get_stats()
        return jsonify({'success': True, 'stats': stats})
    except Exception as e:
        logger.error(f"Error getting stats: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': f'Failed to get stats: {str(e)}'}), 500

@app.route('/Uploads/<filename>')
def uploaded_file(filename):
    try:
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
    except FileNotFoundError:
        logger.error(f"File not found: {filename}")
        return jsonify({'success': False, 'error': 'File not found'}), 404

def run_background_agent():
    while True:
        try:
            complaints = firebase_utils.get_complaints('ALL')
            for complaint in complaints:
                if complaint['votes'] >= firebase_utils.vote_threshold and not complaint.get('posted_on_x', False):
                    if complaint.get('processing', False):
                        continue
                    complaint['processing'] = True
                    twitter_handle = label_to_twitter.get(complaint['labels'][0], '@Raise_Vote_Fix')
                    complaint['labels'].append(f'Mentioned: {twitter_handle}')
                    twitter_result = twitter_agent.post_complaint(complaint)
                    if twitter_result.get('success'):
                        complaint['posted_on_x'] = True
                        firebase_utils.update_complaint(complaint)
                        firebase_utils.delete_complaint(complaint['id'])
                        firebase_utils.increment_twitter_post()
                        logger.info(f"Complaint {complaint['id']} posted to Twitter and deleted")
                    else:
                        logger.error(f"Twitter posting failed: {twitter_result.get('error')}")
                    del complaint['processing']
            time.sleep(300)
        except Exception as e:
            logger.error(f"Background agent error: {str(e)}", exc_info=True)
            time.sleep(60)

@app.errorhandler(404)
def not_found(error):
    logger.error(f"404 error: {str(error)}")
    return jsonify({'success': False, 'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"500 error: {str(error)}", exc_info=True)
    return jsonify({'success': False, 'error': 'Internal server error'}), 500

if __name__ == '__main__':
    logger.info("Starting Flask application...")
    agent_thread = threading.Thread(target=run_background_agent, daemon=True)
    agent_thread.start()
    app.run(debug=True, host='0.0.0.0', port=5000)
