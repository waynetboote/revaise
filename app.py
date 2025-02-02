# app.py
from flask import Flask, request, jsonify, render_template, redirect, url_for
from youtube_transcript import get_transcript
from summarization import summarize_text
from ppt_generator import create_pptx
from google_slides_creator import create_google_slides
import os, openai, logging
from datetime import datetime

# Import Podcastfy’s function
from podcastfy.client import generate_podcast

app = Flask(__name__)
logging.basicConfig(level=logging.DEBUG)

# Configure environment variables (example for OpenAI; Podcastfy may need others)
openai.api_key = os.environ.get("OPENAI_API_KEY")

@app.route('/')
def home():
    # You can choose to have a landing page or redirect to one tool.
    return render_template('landing.html', current_year=datetime.now().year, active_page="home")

@app.route('/youtube')
def youtube_tool():
    return render_template('youtube.html', current_year=datetime.now().year, active_page="youtube")

@app.route('/convert')
def convert_tool():
    return render_template('convert.html', current_year=datetime.now().year, active_page="convert")

# New route for Podcastfy integration
@app.route('/podcast', methods=['GET', 'POST'])
def podcast_tool():
    if request.method == 'POST':
        # Expecting a comma‐separated list of URLs or a newline‐separated list.
        input_urls = request.form.get("urls")
        if not input_urls:
            return render_template('podcast.html', error="Please enter one or more URLs.", current_year=datetime.now().year, active_page="podcast")
        # Split the input into a list of URLs; adjust the separator as needed
        urls = [url.strip() for url in input_urls.splitlines() if url.strip()]
        try:
            # Use Podcastfy to generate the podcast
            audio_file = generate_podcast(urls=urls)
            # audio_file will typically be the path or URL of the generated audio.
            return render_template('podcast_result.html', audio_file=audio_file, current_year=datetime.now().year, active_page="podcast")
        except Exception as e:
            app.logger.error("Error generating podcast feed: %s", str(e))
            return render_template('podcast.html', error=str(e), current_year=datetime.now().year, active_page="podcast")
    else:
        return render_template('podcast.html', current_year=datetime.now().year, active_page="podcast")

# Existing routes for transcript and text conversion remain unchanged...

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
