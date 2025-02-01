# app.py
from flask import Flask, request, jsonify, render_template
from youtube_transcript import get_transcript
from summarization import summarize_text
from ppt_generator import create_pptx
from google_slides_creator import create_google_slides
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.DEBUG)

@app.route('/')
def index():
    # Ensure you have a 'templates/index.html' file.
    return render_template('index.html')

@app.route('/generate_summary', methods=['POST'])
def generate_summary():
    data = request.get_json()
    youtube_url = data.get("youtube_url")
    
    if not youtube_url:
        app.logger.error("No YouTube URL provided in the request")
        return jsonify({"error": "No URL provided"}), 400

    transcript = get_transcript(youtube_url)
    if transcript.startswith("Error"):
        app.logger.error(f"Transcript error: {transcript}")
        return jsonify({"error": transcript}), 400

    summary = summarize_text(transcript)
    app.logger.debug("Text successfully summarized.")

    # Generate a PowerPoint presentation with the summary.
    ppt_file = create_pptx(summary)
    app.logger.debug(f"PowerPoint generated: {ppt_file}")

    # Generate a Google Slides presentation and get its link.
    slides_link = create_google_slides(summary)
    app.logger.debug(f"Google Slides link: {slides_link}")

    response = {
        "transcript": transcript,
        "summary": summary,
        "ppt_file": ppt_file,
        "google_slides_link": slides_link
    }
    return jsonify(response)

if __name__ == "__main__":
    # For development only; disable debug mode in production.
    app.run(debug=True)
