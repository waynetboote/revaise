# Fix for Python 3.13: pydub expects a module named 'pyaudioop'
import audioop
import sys
sys.modules["pyaudioop"] = audioop

from flask import Flask, request, jsonify, render_template, redirect, url_for
from youtube_transcript import get_transcript
from summarization import summarize_text
from ppt_generator import create_pptx
from google_slides_creator import create_google_slides
from podcastfy.client import generate_podcast
import os
import openai
import logging
from datetime import datetime

# Import Redis and RQ
from redis import Redis
from rq import Queue
from rq.job import Job

app = Flask(__name__)
logging.basicConfig(level=logging.DEBUG)

# Configure OpenAI API key from environment variables
openai.api_key = os.environ.get("OPENAI_API_KEY")

# Setup Redis connection and RQ queue using the REDIS_URL provided by your add-on (or default locally)
redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379")
redis_conn = Redis.from_url(redis_url)
q = Queue(connection=redis_conn)

@app.route('/')
def home():
    # Render the landing page which provides links to all tools.
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

# Updated podcast endpoint to enqueue the task instead of processing synchronously
@app.route('/podcast', methods=['GET', 'POST'])
def podcast_tool():
    if request.method == 'POST':
        # Retrieve the input from the form (assumed to be one or more URLs separated by newlines)
        input_urls = request.form.get("urls")
        if not input_urls:
            return render_template('podcast.html', error="Please enter one or more URLs.",
                                   current_year=datetime.now().year, active_page="podcast")
        urls = [url.strip() for url in input_urls.splitlines() if url.strip()]
        try:
            # Enqueue the podcast generation task using RQ
            job = q.enqueue(generate_podcast, urls=urls)
            app.logger.info("Enqueued podcast generation job with ID: %s", job.get_id())
            # Return a page informing the user that the job has been queued along with the job id.
            return render_template('podcast_submitted.html', job_id=job.get_id(),
                                   current_year=datetime.now().year, active_page="podcast")
        except Exception as e:
            app.logger.error("Error enqueuing podcast generation job: %s", str(e))
            return render_template('podcast.html', error=str(e),
                                   current_year=datetime.now().year, active_page="podcast")
    else:
        return render_template('podcast.html', current_year=datetime.now().year, active_page="podcast")

# Endpoint to check the status of a job by its ID
@app.route('/job/<job_id>')
def get_job_status(job_id):
    try:
        job = Job.fetch(job_id, connection=redis_conn)
    except Exception as e:
        return jsonify({"error": "Job not found", "details": str(e)}), 404

    if job.is_finished:
        # If your generate_podcast returns a file path or URL, pass it here.
        return jsonify({"job_id": job.get_id(), "status": "finished", "result": str(job.result)})
    elif job.is_failed:
        return jsonify({"job_id": job.get_id(), "status": "failed"}), 500
    else:
        # job status can be 'queued', 'started', etc.
        return jsonify({"job_id": job.get_id(), "status": job.get_status()}), 202

@app.route('/privacy')
def privacy_policy():
    return render_template('privacy.html', current_year=datetime.now().year)

@app.route('/generate_summary', methods=['POST'])
def generate_summary():
    data = request.get_json()
    youtube_url = data.get("youtube_url")
    if not youtube_url:
        app.logger.error("No YouTube URL provided")
        return jsonify({"error": "No URL provided"}), 400

    transcript = get_transcript(youtube_url)
    if transcript.startswith("Error"):
        app.logger.error(f"Transcript error: {transcript}")
        return jsonify({"error": transcript}), 400

    summary = summarize_text(transcript)
    app.logger.debug("Text successfully summarized.")
    ppt_file = create_pptx(summary)
    app.logger.debug(f"PowerPoint generated: {ppt_file}")
    slides_link = create_google_slides(summary)
    app.logger.debug(f"Google Slides link: {slides_link}")

    response = {
        "transcript": transcript,
        "summary": summary,
        "ppt_file": ppt_file,
        "google_slides_link": slides_link
    }
    return jsonify(response)

@app.route('/convert_text', methods=['POST'])
def convert_text():
    data = request.get_json()
    input_text = data.get("input_text")
    year_group = data.get("year_group")
    if not input_text or not year_group:
        app.logger.error("Missing input text or year group")
        return jsonify({"error": "Missing input text or year group"}), 400

    prompt = (
        f"Adapt the following text to be appropriate for {year_group}. "
        "Ensure that the vocabulary, sentence structure, and style are suitable for the reading level typically expected at that year group. "
        f"Text: {input_text}"
    )

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that specializes in adapting text for different reading levels."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
        )
        converted_text = response.choices[0].message["content"].strip()
        app.logger.debug("Text conversion successful")
        return jsonify({"converted_text": converted_text})
    except Exception as e:
        app.logger.error("Error during text conversion: %s", str(e))
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)
