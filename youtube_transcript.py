# youtube_transcript.py
import re
from youtube_transcript_api import YouTubeTranscriptApi

def extract_video_id(youtube_url):
    """
    Extract the 11-character video ID from a YouTube URL.
    Returns the video ID if found; otherwise, returns None.
    """
    # Use a non-capturing group for known URL patterns.
    match = re.search(r"(?:v=|youtu\.be/|embed/|v/|watch\?v=)([\w-]{11})", youtube_url)
    return match.group(1) if match else None

def get_transcript(youtube_url):
    """
    Retrieve the transcript text from a YouTube URL.
    Returns the transcript as a string or an error message.
    """
    video_id = extract_video_id(youtube_url)
    if not video_id:
        return "Error: Invalid YouTube URL."
    
    try:
        transcript_entries = YouTubeTranscriptApi.get_transcript(video_id)
        transcript_text = " ".join(entry["text"] for entry in transcript_entries)
        return transcript_text
    except Exception as e:
        return f"Error fetching transcript: {str(e)}"
