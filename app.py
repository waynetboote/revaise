from flask import Flask, request, jsonify, render_template
from youtube_transcript import get_transcript
from summarization import summarize_text

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate_summary', methods=['POST'])
def generate_summary():
    data = request.json
    youtube_url = data.get("youtube_url")

    if not youtube_url:
        return jsonify({"error": "No URL provided"}), 400

    transcript = get_transcript(youtube_url)
    if "Error" in transcript:
        return jsonify({"error": transcript}), 400

    summary = summarize_text(transcript)
    return jsonify({"transcript": transcript, "summary": summary})

if __name__ == "__main__":
    app.run(debug=True)
