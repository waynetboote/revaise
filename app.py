# app.py
from flask import Flask, request, jsonify, render_template, redirect, url_for
from youtube_transcript import get_transcript
from summarization import summarize_text
from ppt_generator import create_pptx
from google_slides_creator import create_google_slides
import os
import openai
import logging
from datetime import datetime

app = Flask(__name__)
logging.basicConfig(level=logging.DEBUG)

# Configure OpenAI API key from environment
openai.api_key = os.environ.get("OPENAI_API_KEY")

@app.route('/')
def home():
    # You can choose a landing page or redirect to one of the tools; here, we'll redirect to the YouTube tool.
    return redirect(url_for('youtube_tool'))

@app.route('/youtube')
def youtube_tool():
    return render_template('youtube.html', active_page='youtube', current_year=datetime.now().year)

@app.route('/convert')
def convert_tool():
    return render_template('convert.html', active_page='convert', current_year=datetime.now().year)

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

    # Construct a prompt for ChatGPT
    prompt = (
        f"Adapt the following text to be appropriate for {year_group}. "
        "Ensure that the vocabulary, sentence structure, and style are suitable for the reading level typically expected at that year group. "
        f"Text: {input_text}"
    )

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful assistant that specializes in adapting text for different reading levels."
                },
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
