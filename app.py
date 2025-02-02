# Fix for Python 3.13: pydub expects a module named 'pyaudioop'
import audioop
import sys
sys.modules["pyaudioop"] = audioop

import ssl  # Import ssl to modify certificate verification if needed
import os
import logging
from datetime import datetime

from flask import Flask, request, jsonify, render_template, redirect, url_for
from youtube_transcript import get_transcript
from summarization import summarize_text
from ppt_generator import create_pptx
from google_slides_creator import create_google_slides
from podcastfy.client import generate_podcast

import openai

# Additional imports for RQ
from redis import Redis
from rq import Queue
from rq.job import Job

app = Flask(__name__)
logging.basicConfig(level=logging.DEBUG)

# Configure OpenAI API key from environment variables
openai.api_key = os.environ.get("OPENAI_API_KEY")

# Initialize Redis connection and RQ queue
redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379")
try:
    redis_conn = Redis.from_url(redis_url, ssl_cert_reqs=ssl.CERT_NONE)
    q = Queue(connection=redis_conn)
    app.logger.info("Connected to Redis successfully.")
except Exception as e:
    app.logger.error(f"Failed to connect to Redis: {e}")

@app.route('/')
def home():
    return render_template('landing.html', current_year=datetime.now().year, active_page="home")

@app.route('/youtube')
def youtube_tool():
    return render_template('youtube.html', current_year=datetime.now().year, active_page="youtube")

@app.route('/convert')
def convert_tool():
    return render_template('convert.html', current_year=datetime.now().year, active_page="convert")

@app.route('/terms')
def terms():
    return render_template('terms.html', current_year=datetime.now().year)

@app.route('/podcast', methods=['GET', 'POST'])
def podcast_tool():
    if request.method == 'POST':
        input_urls = request.form.get("urls")
        if not input_urls:
            return render_template('podcast.html', error="Please enter one or more URLs.",
                                   current_year=datetime.now().year, active_page="podcast")
        urls = [url.strip() for url in input_urls.splitlines() if url.strip()]
        try:
            job = q.enqueue(generate_podcast, urls=urls)
            app.logger.debug(f"Enqueued podcast generation job with ID: {job.id}")
            return redirect(url_for('podcast_status', job_id=job.id))
        except Exception as e:
            app.logger.error(f"Error enqueuing podcast job: {e}")
            return render_template('podcast.html', error=str(e), current_year=datetime.now().year, active_page="podcast")
    return render_template('podcast.html', current_year=datetime.now().year, active_page="podcast")

@app.route('/podcast_status/<job_id>')
def podcast_status(job_id):
    try:
        job = Job.fetch(job_id, connection=redis_conn)
        if job.is_finished:
            app.logger.info(f"Podcast job {job_id} completed.")
            return render_template('podcast_result.html', audio_file=job.result, current_year=datetime.now().year, active_page="podcast")
        elif job.is_failed:
            app.logger.error(f"Podcast job {job_id} failed.")
            return render_template('podcast.html', error="Podcast generation failed.", current_year=datetime.now().year, active_page="podcast")
        return render_template('podcast_wait.html', job_id=job.id, current_year=datetime.now().year, active_page="podcast")
    except Exception as e:
        app.logger.error(f"Error fetching job status: {e}")
        return render_template('podcast.html', error="Error fetching job status.", current_year=datetime.now().year, active_page="podcast")

@app.route('/ideas', methods=['GET', 'POST'])
def ideas():
    if request.method == 'POST':
        topic = request.form.get("topic")
        year_group = request.form.get("year_group")
        additional = request.form.get("additional")
        if not topic or not year_group:
            return render_template('ideas.html', error="Please provide both a topic and a year group.", current_year=datetime.now().year)

        prompt = f"Generate a list of creative activity ideas for teaching '{topic}' to Year {year_group}. {additional if additional else ''} Provide ideas as a numbered list."
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
            )
            ideas_response = response['choices'][0]['message']['content'].strip()
            return render_template('ideas.html', ideas=ideas_response, topic=topic, year_group=year_group, additional=additional, current_year=datetime.now().year)
        except Exception as e:
            app.logger.error(f"Error generating activity ideas: {e}")
            return render_template('ideas.html', error=f"Error generating ideas: {e}", current_year=datetime.now().year)

    return render_template('ideas.html', current_year=datetime.now().year)

@app.route('/privacy')
def privacy_policy():
    return render_template('privacy.html', current_year=datetime.now().year)

@app.route('/generate_summary', methods=['POST'])
def generate_summary():
    data = request.get_json()
    youtube_url = data.get("youtube_url")
    if not youtube_url:
        return jsonify({"error": "No URL provided"}), 400

    transcript = get_transcript(youtube_url)
    if transcript.startswith("Error"):
        return jsonify({"error": transcript}), 400

    summary = summarize_text(transcript)
    ppt_file = create_pptx(summary)
    slides_link = create_google_slides(summary)

    return jsonify({
        "transcript": transcript,
        "summary": summary,
        "ppt_file": ppt_file,
        "google_slides_link": slides_link
    })

@app.route('/convert_text', methods=['POST'])
def convert_text():
    data = request.get_json()
    input_text = data.get("input_text")
    year_group = data.get("year_group")
    if not input_text or not year_group:
        return jsonify({"error": "Missing input text or year group"}), 400

    prompt = f"Adapt the following text for Year {year_group}. Ensure the vocabulary and sentence structure match the expected reading level. Text: {input_text}"

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "system", "content": "You are an assistant that adapts text for different reading levels."},
                      {"role": "user", "content": prompt}],
            temperature=0.7,
        )
        converted_text = response['choices'][0]['message']['content'].strip()
        return jsonify({"converted_text": converted_text})
    except Exception as e:
        app.logger.error(f"Error during text conversion: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)
