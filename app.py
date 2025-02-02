# app.py
import os
import logging
import certifi
import ssl
from datetime import datetime
from functools import wraps

from flask import Flask, request, jsonify, render_template, redirect, url_for
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from redis import Redis
from rq import Queue
from rq.job import Job
import openai

# Local modules
from youtube_transcript import get_transcript
from summarization import summarize_text
from ppt_generator import create_pptx
from podcastfy.client import generate_podcast

# Initialize Flask app
app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.environ.get('FLASK_SECRET_KEY', os.urandom(24)),
    RATELIMIT_STORAGE_URI=os.environ.get('REDIS_URL', 'redis://localhost:6379'),
    JSONIFY_PRETTYPRINT_REGULAR=False  # Disable in production
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize rate limiter
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

# Configure Redis connection
def get_redis_connection():
    return Redis.from_url(
        os.environ.get('REDIS_URL', 'redis://localhost:6379'),
        ssl=True,
        ssl_cert_reqs=ssl.CERT_REQUIRED,
        ssl_ca_certs=certifi.where(),
        decode_responses=False
    )

try:
    redis_conn = get_redis_connection()
    q = Queue(connection=redis_conn, default_timeout=600)
    logger.info("Redis connection established")
except Exception as e:
    logger.critical("Failed to connect to Redis: %s", e)
    raise

# Security middleware
@app.before_request
def enforce_https():
    if os.environ.get('FLASK_ENV') == 'production' and not request.is_secure:
        return redirect(request.url.replace('http://', 'https://'))

# Routes
@app.route('/')
@limiter.limit("10/minute")
def home():
    return render_template('landing.html', 
                         current_year=datetime.now().year,
                         active_page="home")

@app.route('/health')
def health_check():
    return jsonify(status="ok"), 200

@app.route('/podcast', methods=['GET', 'POST'])
@limiter.limit("3/hour")
def podcast_tool():
    if request.method == 'POST':
        # Validate input URLs
        urls = [url.strip() for url in request.form.get("urls", "").splitlines() if url.strip()]
        validated_urls = []
        
        for url in urls:
            parsed = urlparse(url)
            if not parsed.scheme:
                url = f"https://{url}"
            if parsed.netloc not in ALLOWED_PODCAST_DOMAINS:
                return render_template('podcast.html', 
                                     error=f"Invalid domain in URL: {parsed.netloc}",
                                     current_year=datetime.now().year)
            validated_urls.append(url)

        try:
            job = q.enqueue(
                generate_podcast,
                urls=validated_urls,
                voice="en-US-AriaNeural",
                output_format="mp3",
                job_timeout=600,
                retry=Retry(max=3, interval=[10, 30, 60])
            )
            return redirect(url_for('podcast_status', job_id=job.id))
        except Exception as e:
            logger.error("Podcast job failed: %s", e)
            return render_template('podcast.html', 
                                 error="Failed to start podcast generation",
                                 current_year=datetime.now().year)
    
    return render_template('podcast.html', 
                         current_year=datetime.now().year)

# Error handlers
@app.errorhandler(429)
def ratelimit_handler(e):
    return render_template('429.html'), 429

@app.errorhandler(500)
def internal_error(e):
    return render_template('500.html'), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
