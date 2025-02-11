# app.py
import os
import logging
import ssl
from datetime import datetime
from urllib.parse import urlparse
from functools import wraps

from flask import Flask, request, jsonify, render_template, redirect, url_for, send_file
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_caching import Cache
from redis import Redis
from rq import Queue, Retry  # Note: We import Queue and Retry here...
from rq.job import Job     # ...and import Job from rq.job
import openai

# Local modules
from youtube_transcript import get_transcript
from summarization import summarize_text
from ppt_generator import create_pptx, generate_pdf
from podcastfy.client import generate_podcast
from google_slides_creator import create_google_slides

# Configure logging early
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.info("Application starting...")

# Initialize Flask application
app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.environ.get('FLASK_SECRET_KEY', os.urandom(24)),
    JSONIFY_PRETTYPRINT_REGULAR=False,
    CACHE_TYPE='RedisCache',
    CACHE_REDIS_URL=os.environ.get('REDIS_URL', 'redis://localhost:6379')
)

# Allowed domains for podcast sources
ALLOWED_DOMAINS = {
    'youtube.com',
    'www.youtube.com',
    'youtu.be',
    'www.youtu.be',
    'soundcloud.com',
    'spotify.com',
    'your-school-domain.edu'
}

# Initialize extensions
cache = Cache(app)
limiter = Limiter(app, key_func=get_remote_address)

def get_redis_connection():
    """
    Create a Redis connection using the REDIS_URL from the environment.
    For production, it's recommended to use ssl_cert_reqs=ssl.CERT_REQUIRED.
    If you experience certificate issues with your Redis add-on (e.g. self-signed certificates),
    you can change this to ssl.CERT_NONE.
    """
    return Redis.from_url(
        os.environ.get('REDIS_URL', 'redis://localhost:6379'),
        ssl=True,
        ssl_cert_reqs=ssl.CERT_REQUIRED,  # Change to ssl.CERT_NONE if necessary
        ssl_ca_certs=ssl.get_default_verify_paths().cafile or None,
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
        return redirect(request.url.replace('http://', 'https://'))

# Append rate limit headers after each request
@app.after_request
def add_rate_limit_headers(response):
    view_func = app.view_functions.get(request.endpoint)
    if view_func and hasattr(limiter, 'limiters') and limiter.limiters:
        try:
            limit = limiter.limiters[0].check_request_limit(view_func)
            if limit:
                response.headers.extend({
                    'X-RateLimit-Limit': limit.limit,
                    'X-RateLimit-Remaining': limit.remaining,
                    'X-RateLimit-Reset': limit.reset_at
                })
        except Exception as e:
            logger.error("Error checking rate limits: %s", e)
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
    if not transcript_result.get('success'):
        return jsonify({"error": transcript_result.get('error', "Unknown error")}), 400

    transcript = transcript_result.get('transcript')
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
        logger.error("Summary generation failed: %s", e)
        return jsonify({"error": "Processing failed"}), 500

@app.route('/export_pdf', methods=['POST'])
@limiter.limit("10/hour")
def export_pdf():
    data = request.get_json()
    if not data or 'content' not in data:
        return jsonify({"error": "No content provided"}), 400
    try:
        pdf_buffer = generate_pdf(data['content'])
        return send_file(
            pdf_buffer,
            mimetype='application/pdf',
            download_name='lesson_plan.pdf',
            as_attachment=True
        )
    except Exception as e:
        logger.error("PDF export failed: %s", e)
        return jsonify({"error": "Failed to generate PDF"}), 500

@app.route('/ideas', methods=['GET', 'POST'])
@limiter.limit("15/hour")
def ideas():
    if request.method == 'POST':
        topic = request.form.get("topic")
        year_group = request.form.get("year_group")
        additional = request.form.get("additional")
        if not topic or not year_group:
            return render_template('ideas.html',
                                   error="Please provide both topic and year group",
                                   current_year=datetime.now().year)
        try:
            prompt = (
                f"Generate 5 creative classroom activities for {year_group} students about {topic}. "
                "Include learning objectives, materials needed, and time estimates. "
                "Format as numbered items with clear sections. "
                f"Additional requirements: {additional if additional else 'None'}"
            )
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
            )
            ideas_response = response['choices'][0]['message']['content'].strip()
            return render_template('ideas.html',
                                   ideas=ideas_response,
                                   topic=topic,
                                   year_group=year_group,
                                   current_year=datetime.now().year)
        except Exception as e:
            logger.error("Activity generation error: %s", e)
            return render_template('ideas.html',
                                   error="Failed to generate activities",
                                   current_year=datetime.now().year)
    return render_template('ideas.html', current_year=datetime.now().year)

@app.route('/podcast', methods=['GET', 'POST'])
@limiter.limit("5/hour")
def podcast_tool():
    if request.method == 'POST':
        urls = [url.strip() for url in request.form.get("urls", "").splitlines() if url.strip()]
        validated_urls = []
        for url in urls:
            
