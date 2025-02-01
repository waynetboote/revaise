import os
from flask import Flask, render_template, request, send_file
from youtube_transcript import get_transcript
from summarization import summarize_text
from generate_pptx import create_pptx
from google_slides import create_google_slides

app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        youtube_url = request.form.get("youtube_url")
        
        # Step 1: Get Transcript
        transcript_text = get_transcript(youtube_url)
        
        # Step 2: Summarize the Transcript
        summary = summarize_text(transcript_text)
        
        # Step 3: Generate PowerPoint
        pptx_file = create_pptx(summary)

        # Step 4: Create Google Slides Presentation
        google_slides_link = create_google_slides(summary)

        return render_template("result.html", pptx_link=pptx_file, slides_link=google_slides_link)

    return render_template("index.html")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))  # Use Render's assigned port
    app.run(host="0.0.0.0", port=port)
