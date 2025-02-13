# app.py
import ssl
# Disable HTTPS certificate verification for development (use with caution in production)
ssl._create_default_https_context = ssl._create_unverified_context

from gevent import monkey
monkey.patch_all()

import os
import logging
import certifi
from datetime import datetime
from functools import wraps
from urllib.parse import urlparse

from flask import Flask, request, jsonify, render_template, redirect, url_for, send_file
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_caching import Cache
from redis import Redis
from rq import Queue, Retry
from rq.job import Job  # Use this import rather than: from rq import Job
import openai
logger.info("OpenAI version: %s", openai.__version__)

# Local modules
from youtube_transcript import get_transcript
from summarization import summarize_text
from ppt_generator import create_pptx, generate_pdf
from podcastfy.client import generate_podcast
from google_slides_creator import create_google_slides

# Import ProxyFix from Werkzeug
from werkzeug.middleware.proxy_fix import ProxyFix

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.info("PYTHONHTTPSVERIFY = %s", os.environ.get('PYTHONHTTPSVERIFY'))

# Initialize Flask application
app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.environ.get('FLASK_SECRET_KEY', os.urandom(24)),
    JSONIFY_PRETTYPRINT_REGULAR=False,
    CACHE_TYPE='RedisCache',
    CACHE_REDIS_URL=os.environ.get('REDIS_URL', 'redis://localhost:6379'),
    CACHE_REDIS_SSL=True,  # Enable SSL for the caching backend
    CACHE_REDIS_ARGS={'ssl_cert_reqs': ssl.CERT_NONE}  # Disable SSL certificate verification
)

# Apply ProxyFix so that request.is_secure is determined correctly when behind a proxy
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1, x_prefix=1)

# Allowed domains for podcast sources
ALLOWED_DOMAINS = {
    'youtube.com',
    'youtu.be',
    'soundcloud.com',
    'spoty.com',
    'your-school-domain.edu'  # Add institutional domains as needed
}

# Initialize caching
cache = Cache()
cache.init_app(app)

# Initialize Flask-Limiter using a two-step process:
limiter = Limiter(key_func=get_remote_address)
limiter.init_app(app)
# Optionally, set a storage backend:
limiter.storage_url = os.environ.get('REDIS_URL', 'redis://localhost:6379')

# Configure Redis connection for RQ (using SSL but disabling certificate verification)
def get_redis_connection():
    unverified_context = ssl._create_unverified_context()
    return Redis.from_url(
        os.environ.get('REDIS_URL', 'redis://localhost:6379'),
        ssl=True,
        ssl_context=unverified_context,  # Use the custom SSL context
        decode_responses=False
    )
try:
    redis_conn = get_redis_connection()
    q = Queue(connection=redis_conn, default_timeout=600)
    logger.info("Connected to Redis successfully")
except Exception as e:
    logger.critical("Redis connection failed: %s", e)
    raise

# Enforce HTTPS in production
@app.before_request
def enforce_https():
    if os.environ.get('FLASK_ENV') == 'production' and not request.is_secure:
        # Use ProxyFix to help detect secure requests correctly.
        return redirect(request.url.replace('http://', 'https://'))

# (Optional) Add rate limit headers if desired.
@app.after_request
def add_rate_limit_headers(response):
    return response

# Routes
@app.route('/')
@limiter.limit("10/minute")
@cache.cached(timeout=300)
def home():
    return render_template('landing.html', 
                           current_year=datetime.now().year,
                           active_page="home")

@app.route('/health')
def health_check():
    return jsonify(status="ok", timestamp=datetime.utcnow()), 200

@app.route('/generate_summary', methods=['POST'])
@limiter.limit("10/hour")
@cache.cached(timeout=3600, query_string=True)
def generate_summary():
    data = request.get_json()
    youtube_url = data.get('youtube_url')
    if not youtube_url:
        return jsonify({"error": "No URL provided"}), 400

    transcript_result = get_transcript(youtube_url)
    if not transcript_result.get("success", False):
        return jsonify({"error": transcript_result.get("error", "Error fetching transcript")}), 400

    transcript = transcript_result["transcript"]
    try:
        summary = summarize_text(transcript)
        ppt_file = create_pptx(summary)
        slides_link = create_google_slides(summary)
        return jsonify({
            "transcript": transcript,
            "summary": summary,
            "ppt_file": ppt_file,
            "google_slides_link": slides_link
        })
    except Exception as e:
        logger.error(f"Summary generation failed: {str(e)}")
        return jsonify({"error": "Processing failed"}), 500

@app.route('/export_pdf', methods=['POST'])
@limiter.limit("10/hour")
def export_pdf():
    try:
        data = request.get_json()
        if not data or 'content' not in data:
            return jsonify({"error": "No content provided"}), 400
        pdf_buffer = generate_pdf(data['content'])
        return send_file(
            pdf_buffer,
            mimetype='application/pdf',
            download_name='lesson_plan.pdf',
            as_attachment=True
        )
    except Exception as e:
        logger.error(f"PDF Export Error: {str(e)}")
        return jsonify({"error": "Failed to generate PDF"}), 500

@app.route('/ideas', methods=['GET', 'POST'])
@limiter.limit("15/hour")
def ideas():
    if request.method == 'POST':
        data = request.get_json() or {}
        topic = data.get("topic") or request.form.get("topic")
        year_group = data.get("year_group") or request.form.get("year_group")
        additional = data.get("learning_goals") or request.form.get("learning_goals")
        if not topic or not year_group:
            return jsonify({"error": "Please provide both topic and year group"}), 400
        try:
            prompt = (
                f"Generate 5 creative classroom activities for {year_group} students about {topic}.\n"
                "Include learning objectives, materials needed, and time estimates.\n"
                "Format as numbered items with clear sections.\n"
                f"Additional requirements: {additional if additional else 'None'}"
            )
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are an assistant that generates creative classroom activities."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
            )
            ideas_response = response['choices'][0]['message']['content'].strip()
            return jsonify({"ideas": ideas_response})
        except Exception as e:
            logger.error(f"Activity generation error: {str(e)}")
            return jsonify({"error": "Failed to generate activities"}), 500
    return render_template('ideas.html', current_year=datetime.now().year)

@app.route('/podcast', methods=['GET', 'POST'])
@limiter.limit("5/hour")
def podcast_tool():
    if request.method == 'POST':
        urls = [url.strip() for url in request.form.get("urls", "").splitlines() if url.strip()]
        validated_urls = []
        for url in urls:
            parsed = urlparse(url)
            if not parsed.scheme:
                url = f"https://{url}"
                parsed = urlparse(url)
            if parsed.netloc.lower() not in ALLOWED_DOMAINS:
                return jsonify({"error": f"Invalid domain: {parsed.netloc}"}), 400
            validated_urls.append(url)
        try:
            job = q.enqueue(
                generate_podcast,
                urls=validated_urls,
                job_timeout=600,
                retry=Retry(max=3, interval=[10, 30, 60])
            )
            return jsonify({"job_id": job.id})
        except Exception as e:
            logger.error(f"Podcast job failed: {str(e)}")
            return jsonify({"error": "Failed to start generation"}), 500
    return render_template('podcast.html', current_year=datetime.now().year)

@app.route('/podcast_status/<job_id>')
def podcast_status(job_id):
    try:
        job = Job.fetch(job_id, connection=redis_conn)
        if job.is_finished:
            return render_template('podcast_result.html', audio_file=job.result, current_year=datetime.now().year)
        elif job.is_failed:
            return render_template('podcast.html', error="Generation failed. Please try again.", current_year=datetime.now().year)
        return render_template('podcast_wait.html', job_id=job.id)
    except Exception as e:
        logger.error(f"Status check error: {str(e)}")
        return redirect(url_for('podcast_tool'))

@app.route('/dashboard')
def dashboard():
    # This route is added to support URL building for 'dashboard'.
    # You should pass real data for recent activities as needed.
    return render_template('dashboard.html', current_year=datetime.now().year, recent_activities=[])

@app.route('/privacy')
def privacy_policy():
    return render_template("privacy.html")

@app.route('/terms')
def terms():
    return render_template("terms.html")

@app.route('/convert_text', methods=['GET', 'POST'])
def convert_text():
    if request.method == 'POST':
        data = request.get_json()
        input_text = data.get("input_text", "")
        year_group = data.get("year_group", "")
        
        prompt = (
            f"Rewrite the following text so that it is appropriate for {year_group} students:\n\n"
            f"{input_text}\n\n"
            "Ensure the language is clear and accessible."
        )
        
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a text simplification assistant."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
            )
            converted_text = response['choices'][0]['message']['content'].strip()
            # Replace this with your actual complexity analysis if available.
            complexity_stats = {"readability": "Calculated metric here"}
        except Exception as e:
            logger.error(f"Error in text conversion: {e}")
            return jsonify({"error": "Failed to convert text"}), 500
        
        return jsonify({
            "converted_text": converted_text,
            "complexity_stats": complexity_stats
        })
    
    return render_template('convert.html', current_year=datetime.now().year)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
