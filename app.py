# app.py

import os
import logging
import certifi
import ssl
from datetime import datetime
from functools import wraps
from urllib.parse import urlparse

# Disable SSL certificate verification globally (for testing only)
ssl._create_default_https_context = ssl._create_unverified_context

# Patch gevent for asynchronous support
from gevent import monkey
monkey.patch_all()

from flask import Flask, request, jsonify, render_template, redirect, url_for, send_file
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_caching import Cache
from redis import Redis
from rq import Queue
from rq.job import Job, Retry
import openai

# Local modules
from youtube_transcript import get_transcript
from summarization import summarize_text
from ppt_generator import create_pptx, generate_pdf
from podcastfy.client import generate_podcast
from google_slides_creator import create_google_slides

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
    # Enable built-in rate limit headers provided by flask-limiter
    RATELIMIT_HEADERS_ENABLED=True
)

# Allowed domains for podcast sources
ALLOWED_DOMAINS = {
    'youtube.com',
    'youtu.be',
    'soundcloud.com',
    'spoty.com',
    'your-school-domain.edu'
}

# Initialize caching and rate limiting
cache = Cache()
limiter = Limiter(app=app, key_func=get_remote_address)

# Configure Redis connection (certificate verification disabled for testing)
def get_redis_connection():
    return Redis.from_url(
        os.environ.get('REDIS_URL', 'redis://localhost:6379'),
        ssl=True,
        ssl_cert_reqs=ssl.CERT_NONE,
        decode_responses=False
    )

try:
    redis_conn = get_redis_connection()
    q = Queue(connection=redis_conn, default_timeout=600)
    logger.info("Connected to Redis successfully")
except Exception as e:
    logger.critical("Redis connection failed: %s", e)
    raise

# Initialize extensions with app context
cache.init_app(app)
limiter.storage_url = os.environ.get('REDIS_URL', 'redis://localhost:6379')

# Security middleware: enforce HTTPS in production
@app.before_request
def enforce_https():
    if os.environ.get('FLASK_ENV') == 'production' and not request.is_secure:
        return redirect(request.url.replace('http://', 'https://'))

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
    try:
        transcript_result = get_transcript(youtube_url)
        if not transcript_result.get("success", False):
            return jsonify({"error": transcript_result.get("error", "Transcript error")}), 400
        transcript = transcript_result.get("transcript")
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
        topic = request.form.get("topic")
        year_group = request.form.get("year_group")
        additional = request.form.get("additional")
        if not topic or not year_group:
            return render_template('ideas.html',
                                   error="Please provide both topic and year group",
                                   current_year=datetime.now().year)
        try:
            prompt = (
                f"Generate 5 creative classroom activities for {year_group} students about {topic}.\n"
                f"Include learning objectives, materials needed, and time estimates.\n"
                f"Format as numbered items with clear sections.\n"
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
            logger.error(f"Activity generation error: {str(e)}")
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
            parsed = urlparse(url)
            if not parsed.scheme:
                url = f"https://{url}"
                parsed = urlparse(url)
            if parsed.netloc not in ALLOWED_DOMAINS:
                return render_template('podcast.html',
                                       error=f"Invalid domain: {parsed.netloc}",
                                       current_year=datetime.now().year)
            validated_urls.append(url)
        try:
            job = q.enqueue(
                generate_podcast,
                urls=validated_urls,
                job_timeout=600,
                retry=Retry(max=3, interval=[10, 30, 60])
            )
            return redirect(url_for('podcast_status', job_id=job.id))
        except Exception as e:
            logger.error(f"Podcast job failed: {str(e)}")
            return render_template('podcast.html',
                                   error="Failed to start generation",
                                   current_year=datetime.now().year)
    return render_template('podcast.html', current_year=datetime.now().year)

@app.route('/podcast_status/<job_id>')
def podcast_status(job_id):
    try:
        job = Job.fetch(job_id, connection=redis_conn)
        if job.is_finished:
            return render_template('podcast_result.html',
                                   audio_file=job.result,
                                   current_year=datetime.now().year)
        elif job.is_failed:
            return render_template('podcast.html',
                                   error="Generation failed. Please try again.",
                                   current_year=datetime.now().year)
        return render_template('podcast_wait.html',
                               job_id=job.id,
                               current_year=datetime.now().year)
    except Exception as e:
        logger.error(f"Status check error: {str(e)}")
        return redirect(url_for('podcast_tool'))

# Error Handlers
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(429)
def ratelimit_handler(e):
    return render_template('429.html'), 429

@app.errorhandler(500)
def internal_error(e):
    return render_template('500.html'), 500

@app.route('/privacy')
def privacy_policy():
    return render_template("privacy.html")

@app.route('/terms')
def terms():
    return render_template("terms.html")

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
